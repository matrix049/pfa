from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.utils.translation import activate, gettext as _
from django.conf import settings
from .models import Property, PropertyImage, Booking, Review, UserProfile, HostApplication, Post, Wishlist
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .forms import ProfileForm, PropertyCreationForm
from .forms import RegistrationForm
from .forms import HostApplicationForm
from django.core.paginator import Paginator
from django.db.models import Q
import stripe
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from django.contrib.auth.backends import ModelBackend

stripe.api_key = settings.STRIPE_SECRET_KEY

def check_user_active(view_func):
    """Decorator to check if user is still active"""
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_active:
            messages.error(request, 'Your account has been deactivated. Please contact an administrator.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

def home(request):
    featured_properties = Property.objects.all()[:6]
    return render(request, 'home.html', {'featured_properties': featured_properties})

def properties(request):
    properties = Property.objects.prefetch_related('images', 'amenities').all()
    property_types = Property._meta.get_field('property_type').choices

    # Get user's wishlist if authenticated
    user_wishlist = []
    if request.user.is_authenticated:
        user_wishlist = list(request.user.wishlist_items.values_list('property_id', flat=True))

    # Filtering
    location = request.GET.get('location')
    if location:
        properties = properties.filter(location__icontains=location)

    min_price = request.GET.get('min_price')
    if min_price:
        properties = properties.filter(price_per_night__gte=min_price)
    max_price = request.GET.get('max_price')
    if max_price:
        properties = properties.filter(price_per_night__lte=max_price)

    type_filters = request.GET.getlist('type')
    if type_filters:
        properties = properties.filter(property_type__in=type_filters)

    space_types = request.GET.getlist('space_type')
    if space_types:
        properties = properties.filter(space_type__in=space_types)

    amenities = request.GET.getlist('amenities')
    if amenities:
        for amenity in amenities:
            properties = properties.filter(amenities__name__iexact=amenity)

    bedrooms = request.GET.get('bedrooms')
    if bedrooms:
        if bedrooms == '4':
            properties = properties.filter(bedrooms__gte=4)
        else:
            properties = properties.filter(bedrooms=bedrooms)

    if request.GET.get('superhost'):
        properties = properties.filter(host__userprofile__role='host', host__userprofile__is_superhost=True)

    guests = request.GET.get('guests')
    if guests:
        properties = properties.filter(max_guests__gte=guests)

    # Sorting
    sort = request.GET.get('sort')
    if sort == 'price_asc':
        properties = properties.order_by('price_per_night')
    elif sort == 'price_desc':
        properties = properties.order_by('-price_per_night')
    elif sort == 'rating':
        # Property does not have average_rating, fallback to default ordering
        pass
    elif sort == 'newest':
        properties = properties.order_by('-id')

    # Pagination
    paginator = Paginator(properties, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'properties.html', {
        'properties': page_obj,
        'property_types': property_types,
        'user_wishlist': user_wishlist,
        'request': request,
    })

def property_detail(request, pk):
    property = get_object_or_404(
        Property.objects.prefetch_related('images', 'amenities', 'reviews', 'host__userprofile'),
        pk=pk
    )
    return render(request, 'property_detail.html', {
        'property': property,
        'today': timezone.now().date(),
    })

@login_required
@check_user_active
def dashboard(request):
    user_bookings = request.user.bookings.all()
    user_properties = request.user.properties.all()
    user_reviews = request.user.reviews.all()
    wishlist_properties = Property.objects.filter(wishlisted_by__user=request.user)
    
    # Get host application if exists
    host_application = None
    if request.user.userprofile.role == 'pending_host':
        host_application = request.user.host_applications.last()
    
    # Get properties for host/admin
    managed_properties = []
    if request.user.userprofile.role in ['host', 'admin']:
        managed_properties = Property.objects.filter(host=request.user)
    
    # Get pending host applications for admin
    pending_applications = []
    if request.user.userprofile.role == 'admin':
        pending_applications = HostApplication.objects.filter(status='pending')
    
    return render(request, 'dashboard.html', {
        'bookings': user_bookings,
        'properties': user_properties,
        'reviews': user_reviews,
        'wishlist_properties': wishlist_properties,
        'host_application': host_application,
        'managed_properties': managed_properties,
        'pending_applications': pending_applications,
        'user_role': request.user.userprofile.role,
    })

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def create_booking(request, pk):
    property = get_object_or_404(Property, pk=pk)
    if request.method == 'POST':
        check_in = request.POST.get('check_in')
        check_out = request.POST.get('check_out')
        guests = int(request.POST.get('guests', 1))
        # Calculate total price (simple version)
        nights = (timezone.datetime.strptime(check_out, '%Y-%m-%d').date() - timezone.datetime.strptime(check_in, '%Y-%m-%d').date()).days
        if nights < 1:
            messages.error(request, 'Check-out must be after check-in.')
            return redirect('property_detail', pk=pk)
        total_price = (property.price_per_night * nights) + property.cleaning_fee + property.service_fee
        # Create Stripe Checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'Booking for {property.title}',
                    },
                    'unit_amount': int(total_price * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=request.build_absolute_uri(f'/booking/success/?property={property.id}&check_in={check_in}&check_out={check_out}&guests={guests}&total={total_price}'),
            cancel_url=request.build_absolute_uri(request.path),
            customer_email=request.user.email,
        )
        return redirect(session.url)
    return redirect('property_detail', pk=pk)

@csrf_exempt
def booking_success(request):
    # Create the booking after successful payment
    property_id = request.GET.get('property')
    check_in = request.GET.get('check_in')
    check_out = request.GET.get('check_out')
    guests = int(request.GET.get('guests', 1))
    total_price = request.GET.get('total')
    property = get_object_or_404(Property, pk=property_id)
    Booking.objects.create(
        property=property,
        guest=request.user,
        check_in=check_in,
        check_out=check_out,
        guests=guests,
        total_price=total_price,
        status='confirmed',
    )
    messages.success(request, 'Booking created and payment successful!')
    return redirect('dashboard')

@login_required
def cancel_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, guest=request.user)
    if request.method == 'POST':
        booking.status = 'cancelled'
        booking.save()
        messages.success(request, 'Booking cancelled successfully!')
    return redirect('dashboard')

@login_required
def create_listing(request):
    if request.method == 'POST':
        form = PropertyCreationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create the property
                    property = form.save(commit=False)
                    property.host = request.user
                    property.save()
                    
                    # Handle multiple image uploads
                    files = request.FILES.getlist('photos')
                    for index, file in enumerate(files):
                        PropertyImage.objects.create(
                            property=property,
                            image=file,
                            is_primary=(index == 0)  # First image is primary
                        )
                    
                    messages.success(request, 'Property listed successfully!')
                    return redirect('dashboard')
            except Exception as e:
                messages.error(request, f'Error creating property: {str(e)}')
    else:
        form = PropertyCreationForm()
    
    return render(request, 'create_listing.html', {'form': form})

@login_required
def edit_listing(request, pk):
    property = get_object_or_404(Property, pk=pk, host=request.user)
    # Add property editing logic here
    return render(request, 'edit_listing.html', {'property': property})

@login_required
def delete_listing(request, pk):
    property = get_object_or_404(Property, pk=pk, host=request.user)
    if request.method == 'POST':
        property.delete()
        messages.success(request, 'Property deleted successfully!')
    return redirect('dashboard')

@login_required
def property_bookings(request, pk):
    property = get_object_or_404(Property, pk=pk, host=request.user)
    bookings = property.bookings.all()
    return render(request, 'property_bookings.html', {'property': property, 'bookings': bookings})

@login_required
def edit_review(request, pk):
    review = get_object_or_404(Review, pk=pk, user=request.user)
    # Add review editing logic here
    return redirect('dashboard')

@login_required
def delete_review(request, pk):
    review = get_object_or_404(Review, pk=pk, user=request.user)
    if request.method == 'POST':
        review.delete()
        messages.success(request, 'Review deleted successfully!')
    return redirect('dashboard')

@login_required
def edit_profile(request):
    user = request.user
    
    # Create UserProfile if it doesn't exist
    try:
        profile = user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)

    if request.method == 'POST':
        try:
            form = ProfileForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Please correct the errors below.')
                # Debugging: print form errors to console
                print('ProfileForm errors:', form.errors)
        except Exception as e:
            messages.error(request, f'An error occurred while updating your profile: {str(e)}')
            # Debugging: print exception to console
            print('Exception in edit_profile:', str(e))
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'edit_profile.html', {'form': form})

@login_required
def change_password(request):
    # Add password change logic here
    return redirect('dashboard')

@login_required
def become_host(request):
    # Check if user already has a pending or approved application
    if request.user.userprofile.role in ['host', 'admin']:
        messages.error(request, 'You are already a host or admin.')
        return redirect('dashboard')
    
    if request.user.userprofile.role == 'pending_host':
        messages.info(request, 'Your host application is pending approval.')
        return redirect('dashboard')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Extract form data
                property_type = request.POST.get('property_type')
                space_type = request.POST.get('space_type')
                guests = int(request.POST.get('guests', 1))
                bedrooms = int(request.POST.get('bedrooms', 1))
                beds = int(request.POST.get('beds', 1))
                bathrooms = int(request.POST.get('bathrooms', 1))
                highlights = request.POST.get('highlights', '')
                title = request.POST.get('title')
                description = request.POST.get('description')
                address = request.POST.get('address')
                price = request.POST.get('price')
                
                # Validate required fields
                if not all([property_type, space_type, title, description, address, price]):
                    messages.error(request, 'Please fill in all required fields.')
                    return render(request, 'become_host.html')
                
                # Create the property
                property = Property.objects.create(
                    host=request.user,
                    title=title,
                    description=description,
                    property_type=property_type,
                    space_type=space_type,
                    location=address,
                    price_per_night=float(price),
                    bedrooms=bedrooms,
                    bathrooms=bathrooms,
                    beds=beds,
                    max_guests=guests,
                    cleaning_fee=50.00,  # Default values
                    service_fee=30.00,   # Default values
                    highlights=highlights
                )
                
                # Handle multiple image uploads
                files = request.FILES.getlist('photos')
                if files:
                    for index, file in enumerate(files):
                        PropertyImage.objects.create(
                            property=property,
                            image=file,
                            is_primary=(index == 0)  # First image is primary
                        )
                
                # Update user profile to host
                profile = request.user.userprofile
                profile.role = 'host'
                profile.save()
                
                messages.success(request, 'Congratulations! Your property has been listed and you are now a host.')
                return redirect('dashboard')
                
        except Exception as e:
            messages.error(request, f'Error creating listing: {str(e)}')
            return render(request, 'become_host.html')

    return render(request, 'become_host.html')

def terms(request):
    return render(request, 'terms.html')

def privacy(request):
    return render(request, 'privacy.html')

def is_admin(user):
    return user.userprofile.role == 'admin'

def is_host(user):
    return user.userprofile.role == 'host'

@login_required
@user_passes_test(is_host)
def create_post(request):
    if request.method == 'POST':
        property_id = request.POST.get('property')
        title = request.POST.get('title')
        content = request.POST.get('content')

        if property_id and title and content:
            property_obj = get_object_or_404(Property, id=property_id, host=request.user)
            Post.objects.create(
                property=property_obj,
                host=request.user,
                title=title,
                content=content
            )
            messages.success(request, 'Your post has been submitted for review.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please fill in all required fields.')

    properties = Property.objects.filter(host=request.user)
    return render(request, 'posts/create_post.html', {'properties': properties})

@login_required
@user_passes_test(is_admin)
def manage_posts(request):
    posts = Post.objects.all().order_by('-created_at')
    return render(request, 'posts/manage_posts.html', {'posts': posts})

@login_required
@user_passes_test(is_admin)
def approve_post(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        post.status = 'approved'
        post.save()
        messages.success(request, 'Post has been approved.')
    return redirect('manage_posts')

@login_required
@user_passes_test(is_admin)
def decline_post(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        post.status = 'declined'
        post.save()
        messages.success(request, 'Post has been declined.')
    return redirect('manage_posts')

@login_required
@user_passes_test(is_admin)
def manage_users(request):
    users = User.objects.select_related('userprofile').all().order_by('username')
    query = request.GET.get('q')
    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(userprofile__phone_number__icontains=query)
        )
    return render(request, 'users/manage_users.html', {'users': users})

@login_required
@user_passes_test(is_admin)
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.is_active = request.POST.get('is_active') == 'on'
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.save()
        
        profile = user.userprofile
        profile.phone_number = request.POST.get('phone_number')
        profile.role = request.POST.get('role')
        profile.save()
        
        messages.success(request, f'User {user.username} updated successfully.')
        return redirect('manage_users')
    
    return render(request, 'users/edit_user.html', {'user_to_edit': user})

@login_required
@user_passes_test(is_admin)
@require_POST
def delete_user(request, user_id):
    try:
        user = get_object_or_404(User, id=user_id)
        if user == request.user:
            return JsonResponse({'success': False, 'error': 'Cannot delete yourself'})
        
        username = user.username
        user.delete()
        return JsonResponse({'success': True, 'message': f'User {username} deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(is_admin)
@require_POST
def toggle_user_status(request, user_id):
    try:
        user = get_object_or_404(User, id=user_id)
        if user == request.user:
            return JsonResponse({'success': False, 'error': 'Cannot deactivate yourself'})
        
        user.is_active = not user.is_active
        user.save()
        status = 'activated' if user.is_active else 'deactivated'
        message = f'User {user.username} has been {status}. '
        if not user.is_active:
            message += 'They will be logged out immediately if currently logged in.'
        return JsonResponse({'success': True, 'message': message})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(is_admin)
@require_POST
def bulk_action(request):
    try:
        data = json.loads(request.body)
        action = data.get('action')
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return JsonResponse({'success': False, 'error': 'No users selected'})
        
        users = User.objects.filter(id__in=user_ids)
        
        if action == 'activate':
            users.update(is_active=True)
            message = f'{users.count()} users activated'
        elif action == 'deactivate':
            # Don't allow deactivating yourself
            users = users.exclude(id=request.user.id)
            users.update(is_active=False)
            message = f'{users.count()} users deactivated'
        elif action == 'delete':
            # Don't allow deleting yourself
            users = users.exclude(id=request.user.id)
            count = users.count()
            users.delete()
            message = f'{count} users deleted'
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action'})
        
        return JsonResponse({'success': True, 'message': message})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def custom_authenticate(username, password):
    try:
        user = User.objects.get(username=username)
        if user.check_password(password):
            return user
    except User.DoesNotExist:
        pass
    return None

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = custom_authenticate(username, password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'registration/login.html')

@login_required
@require_POST
def add_to_wishlist(request, property_id):
    property = get_object_or_404(Property, pk=property_id)
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        property=property
    )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if created:
            return JsonResponse({
                'success': True,
                'message': f'{property.title} added to your wishlist!'
            })
        else:
            return JsonResponse({
                'success': True,
                'message': f'{property.title} is already in your wishlist!'
            })
    
    # Non-AJAX request handling
    if created:
        messages.success(request, f'{property.title} added to your wishlist!')
    else:
        messages.info(request, f'{property.title} is already in your wishlist!')
    
    # Redirect back to the previous page or property detail
    return redirect(request.META.get('HTTP_REFERER', 'properties'))

@login_required
@require_POST
def remove_from_wishlist(request, property_id):
    property = get_object_or_404(Property, pk=property_id)
    try:
        wishlist_item = Wishlist.objects.get(user=request.user, property=property)
        wishlist_item.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'{property.title} removed from your wishlist!'
            })
        
        messages.success(request, f'{property.title} removed from your wishlist!')
    except Wishlist.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Property not found in your wishlist!'
            })
        messages.error(request, 'Property not found in your wishlist!')
    
    # Redirect back to the previous page or dashboard
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def change_language(request, language_code):
    """Change user's language preference"""
    if language_code in ['en', 'fr']:
        # Update user's language preference in profile
        try:
            profile = request.user.userprofile
            profile.language = language_code
            profile.save()
        except UserProfile.DoesNotExist:
            # Create profile if it doesn't exist
            UserProfile.objects.create(user=request.user, language=language_code)
        
        # Store language preference in session
        request.session['user_language'] = language_code
        
        messages.success(request, 'Language changed successfully!' if language_code == 'en' else 'Langue changée avec succès!')
    else:
        messages.error(request, 'Invalid language selection.' if request.session.get('user_language', 'en') == 'en' else 'Sélection de langue invalide.')
    
    # Redirect back to the previous page or dashboard
    next_url = request.GET.get('next', 'dashboard')
    return redirect(next_url)