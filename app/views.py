from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from .models import Property, PropertyImage, Booking, Review, UserProfile, HostApplication, Post
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .forms import ProfileForm, PropertyCreationForm
from .forms import RegistrationForm
from .forms import HostApplicationForm

def home(request):
    featured_properties = Property.objects.all()[:6]
    return render(request, 'home.html', {'featured_properties': featured_properties})

def properties(request):
    properties = Property.objects.prefetch_related('images', 'amenities').all()
    return render(request, 'properties.html', {'properties': properties})

def property_detail(request, pk):
    property = get_object_or_404(
        Property.objects.prefetch_related('images', 'amenities', 'reviews'),
        pk=pk
    )
    return render(request, 'property_detail.html', {
        'property': property,
        'today': timezone.now().date(),
    })

@login_required
def dashboard(request):
    user_bookings = request.user.bookings.all()
    user_properties = request.user.properties.all()
    user_reviews = request.user.reviews.all()
    
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
    if request.method == 'POST':
        property = get_object_or_404(Property, pk=pk)
        # Add booking creation logic here
        messages.success(request, 'Booking created successfully!')
        return redirect('dashboard')
    return redirect('property_detail', pk=pk)

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
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
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