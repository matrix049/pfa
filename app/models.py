from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class Property(models.Model):
    PROPERTY_TYPES = (
        ('house', 'House'),
        ('apartment', 'Apartment'),
        ('villa', 'Villa'),
        ('cottage', 'Cottage'),
        ('boat', 'Boat'),
        ('cabin', 'Cabin'),
        ('caravan', 'Caravan'),
        ('castle', 'Castle'),
        ('farm', 'Farm'),
        ('hotel', 'Hotel'),
        ('riad', 'Riad'),
        ('tent', 'Tent'),
        ('tiny', 'Tiny House'),
        ('tower', 'Tower'),
        ('treehouse', 'Treehouse'),
        ('other', 'Other'),
    )

    SPACE_TYPES = (
        ('entire', 'Entire Place'),
        ('room', 'Private Room'),
    )

    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='properties')
    title = models.CharField(max_length=200)
    description = models.TextField()
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES)
    space_type = models.CharField(max_length=20, choices=SPACE_TYPES, default='entire')
    location = models.CharField(max_length=200)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    bedrooms = models.PositiveIntegerField()
    bathrooms = models.PositiveIntegerField()
    beds = models.PositiveIntegerField(default=1)
    max_guests = models.PositiveIntegerField()
    cleaning_fee = models.DecimalField(max_digits=6, decimal_places=2)
    service_fee = models.DecimalField(max_digits=6, decimal_places=2)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_superhost = models.BooleanField(default=False)
    highlights = models.CharField(max_length=200, blank=True)  # Store comma-separated highlights
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @property
    def primary_image(self):
        primary = self.images.filter(is_primary=True).first()
        if primary:
            return primary.image.url
        # fallback to any image if no primary
        any_image = self.images.first()
        if any_image:
            return any_image.image.url
        return None

    def get_highlights_list(self):
        if self.highlights:
            return self.highlights.split(',')
        return []

    class Meta:
        verbose_name_plural = 'Properties'
        ordering = ['-created_at']

class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='properties/')
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.property.title}"

class Amenity(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50)
    properties = models.ManyToManyField(Property, related_name='amenities')

    def __str__(self):
        return self.name

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='bookings')
    guest = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    check_in = models.DateField()
    check_out = models.DateField()
    guests = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Booking for {self.property.title} by {self.guest.username}"

class Review(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review for {self.property.title} by {self.user.username}"

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('user', 'Regular User'),
        ('pending_host', 'Pending Host'),
        ('host', 'Host'),
        ('admin', 'Admin')
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='user')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.png', blank=True)
    
    # Additional profile fields
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    language = models.CharField(max_length=50, blank=True, default='English')
    currency = models.CharField(max_length=10, blank=True, default='USD')
    
    # Preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    marketing_emails = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def is_host(self):
        return self.role == 'host'

    @property
    def is_pending_host(self):
        return self.role == 'pending_host'

    def get_avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        return '/static/images/default-avatar.png'

    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username

class HostApplication(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='host_applications')
    business_name = models.CharField(max_length=100)
    business_address = models.TextField()
    business_phone = models.CharField(max_length=20)
    identity_document = models.FileField(upload_to='host_documents/')
    description = models.TextField(help_text="Tell us about your hosting experience and properties")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Host Application - {self.user.username}"

    class Meta:
        ordering = ['-created_at']

class Post(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined')
    )

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='posts')
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.property.title}"

    class Meta:
        ordering = ['-created_at']