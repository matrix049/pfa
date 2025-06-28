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
        
        # Validate dates
        try:
            check_in_date = timezone.datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = timezone.datetime.strptime(check_out, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format.')
            return redirect('property_detail', pk=pk)
        
        if check_in_date >= check_out_date:
            messages.error(request, 'Check-out must be after check-in.')
            return redirect('property_detail', pk=pk)
        
        # Check availability with database transaction
        with transaction.atomic():
            # Double-check availability before creating booking
            if not Booking.check_availability(property, check_in_date, check_out_date):
                messages.error(request, 'Selected dates are no longer available. Please choose different dates.')
                return redirect('property_detail', pk=pk)
            
            # Calculate total price
            nights = (check_out_date - check_in_date).days
            total_price = (property.price_per_night * nights) + property.cleaning_fee + property.service_fee
            
            # Create a temporary booking to hold the slot
            temp_booking = Booking.objects.create(
                property=property,
                guest=request.user,
                check_in=check_in_date,
                check_out=check_out_date,
                guests=guests,
                total_price=total_price,
                status='pending',
                payment_status='pending'
            )
            
            # Create Stripe Checkout session
            try:
                session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': f'Booking for {property.title}',
                                'description': f'{nights} nights from {check_in} to {check_out}',
                            },
                            'unit_amount': int(total_price * 100),
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    success_url=request.build_absolute_uri(f'/booking/success/?booking_id={temp_booking.id}'),
                    cancel_url=request.build_absolute_uri(f'/booking/cancel/?booking_id={temp_booking.id}'),
                    customer_email=request.user.email,
                    metadata={
                        'booking_id': str(temp_booking.id),
                        'property_id': str(property.id),
                    }
                )
                
                # Update booking with session ID
                temp_booking.stripe_session_id = session.id
                temp_booking.save()
                
                # Redirect to payment processing page instead of directly to Stripe
                return redirect('payment_processing', booking_id=temp_booking.id)
                
            except stripe.error.StripeError as e:
                # If Stripe fails, delete the temporary booking
                temp_booking.delete()
                messages.error(request, f'Payment processing error: {str(e)}')
                return redirect('property_detail', pk=pk)
    
    return redirect('property_detail', pk=pk)

@csrf_exempt
def booking_success(request):
    """Handle successful payment and confirm booking"""
    booking_id = request.GET.get('booking_id')
    if not booking_id:
        messages.error(request, 'Invalid booking reference.')
        return redirect('dashboard')
    
    try:
        with transaction.atomic():
            booking = get_object_or_404(Booking, id=booking_id, guest=request.user)
            
            # Verify the booking is still available
            if not Booking.check_availability(booking.property_obj, booking.check_in, booking.check_out, exclude_booking=booking):
                # Cancel the booking if no longer available
                booking.status = 'cancelled'
                booking.payment_status = 'failed'
                booking.save()
                messages.error(request, 'The selected dates are no longer available. Your payment will be refunded.')
                return redirect('dashboard')
            
            # Update booking status
            booking.status = 'confirmed'
            booking.payment_status = 'paid'
            booking.save()
            
            messages.success(request, 'Booking confirmed and payment successful!')
            return redirect('dashboard')
            
    except Exception as e:
        messages.error(request, f'Error processing booking: {str(e)}')
        return redirect('dashboard')

@login_required
def booking_cancel(request):
    """Handle cancelled payment"""
    booking_id = request.GET.get('booking_id')
    if booking_id:
        try:
            booking = get_object_or_404(Booking, id=booking_id, guest=request.user)
            booking.status = 'cancelled'
            booking.payment_status = 'failed'
            booking.save()
            messages.info(request, 'Booking cancelled.')
        except Booking.DoesNotExist:
            pass
    
    return redirect('dashboard')

@login_required
def payment_processing(request, booking_id):
    """Show payment processing page with countdown timer"""
    try:
        booking = get_object_or_404(Booking, id=booking_id, guest=request.user)
        
        # Only show for pending bookings
        if booking.status != 'pending' or booking.payment_status != 'pending':
            messages.info(request, 'This booking is no longer pending payment.')
            return redirect('dashboard')
        
        # Check if booking has expired
        if booking.is_expired:
            booking.status = 'cancelled'
            booking.payment_status = 'failed'
            booking.save()
            messages.warning(request, 'Your reservation has expired. Please try booking again.')
            return redirect('dashboard')
        
        return render(request, 'payment_processing.html', {'booking': booking})
        
    except Booking.DoesNotExist:
        messages.error(request, 'Booking not found.')
        return redirect('dashboard')

@login_required
def get_stripe_session_url(request, booking_id):
    """Get Stripe session URL for a booking"""
    try:
        booking = get_object_or_404(Booking, id=booking_id, guest=request.user)
        
        if not booking.stripe_session_id:
            return JsonResponse({'error': 'No payment session found'}, status=404)
        
        # Retrieve the session from Stripe
        session = stripe.checkout.Session.retrieve(booking.stripe_session_id)
        
        if session.status == 'open':
            return JsonResponse({'url': session.url})
        else:
            return JsonResponse({'error': 'Payment session is no longer valid'}, status=400)
            
    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)
    except stripe.error.StripeError as e:
        return JsonResponse({'error': str(e)}, status=500)

def check_availability_api(request, property_id):
    """API endpoint to check availability for a property"""
    if request.method == 'GET':
        try:
            property = get_object_or_404(Property, id=property_id)
            check_in = request.GET.get('check_in')
            check_out = request.GET.get('check_out')
            
            if not check_in or not check_out:
                return JsonResponse({
                    'success': False,
                    'error': 'Both check_in and check_out dates are required'
                })
            
            # Check availability
            is_available = Booking.check_availability(property, check_in, check_out)
            
            return JsonResponse({
                'success': True,
                'available': is_available,
                'property_id': property_id,
                'check_in': check_in,
                'check_out': check_out
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

def get_unavailable_dates_api(request, property_id):
    """API endpoint to get unavailable dates for a property"""
    if request.method == 'GET':
        try:
            property = get_object_or_404(Property, id=property_id)
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            
            # Convert dates if provided
            if start_date:
                start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
            
            unavailable_dates = Booking.get_unavailable_dates(property, start_date, end_date)
            
            # Convert dates to strings for JSON serialization
            unavailable_dates_str = [date.strftime('%Y-%m-%d') for date in unavailable_dates]
            
            return JsonResponse({
                'success': True,
                'property_id': property_id,
                'unavailable_dates': unavailable_dates_str
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

def get_booking_status_api(request, booking_id):
    """API endpoint to get booking status and time remaining"""
    if request.method == 'GET':
        try:
            booking = get_object_or_404(Booking, id=booking_id)
            
            # Check if user has permission to view this booking
            if not request.user.is_authenticated or booking.guest != request.user:
                return JsonResponse({
                    'success': False,
                    'error': 'Permission denied'
                }, status=403)
            
            time_remaining = booking.time_remaining_seconds
            is_expired = booking.is_expired
            
            return JsonResponse({
                'success': True,
                'booking_id': booking_id,
                'status': booking.status,
                'payment_status': booking.payment_status,
                'time_remaining_seconds': time_remaining,
                'is_expired': is_expired,
                'reservation_expires_at': booking.reservation_expires_at.isoformat(),
                'created_at': booking.created_at.isoformat()
            })
            
        except Booking.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Booking not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

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
                business_name = request.POST.get('business_name')
                business_address = request.POST.get('business_address')
                business_phone = request.POST.get('business_phone')
                description = request.POST.get('description')
                
                # Validate required fields
                if not all([business_name, business_address, business_phone, description]):
                    messages.error(request, 'Please fill in all required fields.')
                    return render(request, 'become_host.html')
                
                # Check if user already has a pending application
                existing_application = HostApplication.objects.filter(
                    user=request.user, 
                    status='pending'
                ).first()
                
                if existing_application:
                    messages.info(request, 'You already have a pending host application.')
                    return redirect('dashboard')
                
                # Create the host application
                host_application = HostApplication.objects.create(
                    user=request.user,
                    business_name=business_name,
                    business_address=business_address,
                    business_phone=business_phone,
                    description=description,
                    status='pending'
                )
                
                # Handle identity document upload if provided
                if 'identity_document' in request.FILES:
                    host_application.identity_document = request.FILES['identity_document']
                    host_application.save()
                
                # Update user profile to pending_host
                profile = request.user.userprofile
                profile.role = 'pending_host'
                profile.save()
                
                messages.success(request, 'Your host application has been submitted successfully! We will review it and get back to you soon.')
                return redirect('dashboard')
                
        except Exception as e:
            messages.error(request, f'Error submitting application: {str(e)}')
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

@csrf_exempt
def stripe_webhook(request):
    """
    Handle Stripe webhook events for payment confirmation and failure
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if request.method != 'POST':
        logger.warning(f"Webhook received non-POST request: {request.method}")
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Get the webhook payload
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    if not sig_header:
        logger.error("Webhook received without Stripe signature")
        return JsonResponse({'error': 'No signature provided'}, status=400)
    
    # Verify webhook signature
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    
    # Handle the event
    try:
        event_type = event['type']
        logger.info(f"Processing webhook event: {event_type}")
        
        if event_type == 'checkout.session.completed':
            return handle_checkout_session_completed(event)
        elif event_type == 'payment_intent.succeeded':
            return handle_payment_intent_succeeded(event)
        elif event_type == 'payment_intent.payment_failed':
            return handle_payment_intent_failed(event)
        else:
            logger.info(f"Unhandled event type: {event_type}")
            return JsonResponse({'status': 'ignored'})
            
    except Exception as e:
        logger.error(f"Error processing webhook event {event.get('type', 'unknown')}: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

def handle_checkout_session_completed(event):
    """
    Handle successful checkout session completion
    """
    import logging
    logger = logging.getLogger(__name__)
    
    session = event['data']['object']
    booking_id = session.get('metadata', {}).get('booking_id')
    
    if not booking_id:
        logger.error("Checkout session completed without booking_id in metadata")
        return JsonResponse({'error': 'No booking_id in metadata'}, status=400)
    
    try:
        with transaction.atomic():
            booking = Booking.objects.get(id=booking_id)
            
            # Verify the booking is still available
            if not Booking.check_availability(booking.property_obj, booking.check_in, booking.check_out, exclude_booking=booking):
                # Cancel the booking if no longer available
                booking.status = 'cancelled'
                booking.payment_status = 'failed'
                booking.save()
                logger.warning(f"Booking {booking_id} cancelled due to availability conflict")
                return JsonResponse({'status': 'booking_cancelled'})
            
            # Update booking status
            booking.status = 'confirmed'
            booking.payment_status = 'paid'
            booking.save()
            
            logger.info(f"Booking {booking_id} confirmed successfully via webhook")
            return JsonResponse({'status': 'success'})
            
    except Booking.DoesNotExist:
        logger.error(f"Booking {booking_id} not found")
        return JsonResponse({'error': 'Booking not found'}, status=404)
    except Exception as e:
        logger.error(f"Error processing checkout session for booking {booking_id}: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

def handle_payment_intent_succeeded(event):
    """
    Handle successful payment intent
    """
    import logging
    logger = logging.getLogger(__name__)
    
    payment_intent = event['data']['object']
    session_id = payment_intent.get('metadata', {}).get('session_id')
    
    if not session_id:
        logger.info("Payment intent succeeded without session_id, ignoring")
        return JsonResponse({'status': 'ignored'})
    
    try:
        booking = Booking.objects.get(stripe_session_id=session_id)
        
        # Only update if booking is still pending
        if booking.status == 'pending' and booking.payment_status == 'pending':
            with transaction.atomic():
                # Verify availability again
                if not Booking.check_availability(booking.property_obj, booking.check_in, booking.check_out, exclude_booking=booking):
                    booking.status = 'cancelled'
                    booking.payment_status = 'failed'
                    booking.save()
                    logger.warning(f"Booking {booking.id} cancelled due to availability conflict")
                    return JsonResponse({'status': 'booking_cancelled'})
                
                booking.status = 'confirmed'
                booking.payment_status = 'paid'
                booking.save()
                
                logger.info(f"Booking {booking.id} confirmed via payment intent webhook")
                return JsonResponse({'status': 'success'})
        else:
            logger.info(f"Booking {booking.id} already processed, ignoring")
            return JsonResponse({'status': 'already_processed'})
            
    except Booking.DoesNotExist:
        logger.error(f"Booking with session_id {session_id} not found")
        return JsonResponse({'error': 'Booking not found'}, status=404)
    except Exception as e:
        logger.error(f"Error processing payment intent for session {session_id}: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

def handle_payment_intent_failed(event):
    """
    Handle failed payment intent
    """
    import logging
    logger = logging.getLogger(__name__)
    
    payment_intent = event['data']['object']
    session_id = payment_intent.get('metadata', {}).get('session_id')
    
    if not session_id:
        logger.info("Payment intent failed without session_id, ignoring")
        return JsonResponse({'status': 'ignored'})
    
    try:
        booking = Booking.objects.get(stripe_session_id=session_id)
        
        # Update booking status to failed
        booking.status = 'cancelled'
        booking.payment_status = 'failed'
        booking.save()
        
        logger.info(f"Booking {booking.id} marked as failed due to payment failure")
        return JsonResponse({'status': 'booking_cancelled'})
        
    except Booking.DoesNotExist:
        logger.error(f"Booking with session_id {session_id} not found")
        return JsonResponse({'error': 'Booking not found'}, status=404)
    except Exception as e:
        logger.error(f"Error processing failed payment intent for session {session_id}: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

@login_required
@user_passes_test(is_admin)
def approve_host_application(request, application_id):
    """Approve a specific host application"""
    if request.method == 'POST':
        try:
            application = get_object_or_404(HostApplication, id=application_id, status='pending')
            
            # Update application status
            application.status = 'approved'
            application.save()
            
            # Update user profile role
            profile = application.user.userprofile
            profile.role = 'host'
            profile.save()
            
            messages.success(request, f'Host application for {application.user.username} has been approved.')
            
            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Host application for {application.user.username} has been approved.',
                    'application_id': application.id,
                    'new_status': 'approved'
                })
            
        except Exception as e:
            error_msg = f'Error approving application: {str(e)}'
            messages.error(request, error_msg)
            
            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': error_msg
                }, status=400)
    
    return redirect('dashboard')

@login_required
@user_passes_test(is_admin)
def reject_host_application(request, application_id):
    """Reject a specific host application"""
    if request.method == 'POST':
        try:
            application = get_object_or_404(HostApplication, id=application_id, status='pending')
            
            # Update application status
            application.status = 'rejected'
            application.save()
            
            # Update user profile role back to regular user if they were pending
            profile = application.user.userprofile
            if profile.role == 'pending_host':
                profile.role = 'user'
                profile.save()
            
            messages.success(request, f'Host application for {application.user.username} has been rejected.')
            
            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Host application for {application.user.username} has been rejected.',
                    'application_id': application.id,
                    'new_status': 'rejected'
                })
            
        except Exception as e:
            error_msg = f'Error rejecting application: {str(e)}'
            messages.error(request, error_msg)
            
            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': error_msg
                }, status=400)
    
    return redirect('dashboard')