from django.contrib import admin
from .models import Property, PropertyImage, Amenity, Booking, Review, UserProfile, HostApplication, Post
from django.contrib import messages

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'role']
    list_filter = ['role']
    search_fields = ['user__username', 'user__email', 'phone_number']

@admin.register(HostApplication)
class HostApplicationAdmin(admin.ModelAdmin):
    list_display = ['user', 'business_name', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['user__username', 'business_name', 'business_phone']
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['approve_applications', 'reject_applications']
    
    def approve_applications(self, request, queryset):
        for application in queryset.filter(status='pending'):
            application.status = 'approved'
            application.save()
            
            # Update user profile role
            profile = application.user.userprofile
            profile.role = 'host'
            profile.save()
            
        messages.success(request, f'Successfully approved {queryset.count()} application(s)')
    approve_applications.short_description = "Approve selected applications"
    
    def reject_applications(self, request, queryset):
        for application in queryset.filter(status='pending'):
            application.status = 'rejected'
            application.save()
            
            # Update user profile role back to regular user if they were pending
            profile = application.user.userprofile
            if profile.role == 'pending_host':
                profile.role = 'user'
                profile.save()
            
        messages.success(request, f'Successfully rejected {queryset.count()} application(s)')
    reject_applications.short_description = "Reject selected applications"

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ['title', 'host', 'price_per_night', 'location']
    list_filter = ['property_type', 'bedrooms', 'bathrooms']
    search_fields = ['title', 'description', 'location']

@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ['property', 'image']

@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['property', 'guest', 'check_in', 'check_out', 'status']
    list_filter = ['status']
    search_fields = ['property__title', 'guest__username']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['property', 'user', 'rating', 'created_at']
    list_filter = ['rating']
    search_fields = ['property__title', 'user__username', 'comment']

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'property', 'host', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'content', 'property__title', 'host__username')
    actions = ['approve_posts', 'decline_posts']

    def approve_posts(self, request, queryset):
        queryset.update(status='approved')
    approve_posts.short_description = "Approve selected posts"

    def decline_posts(self, request, queryset):
        queryset.update(status='declined')
    decline_posts.short_description = "Decline selected posts"
