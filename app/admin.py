from django.contrib import admin
from django.contrib import messages
from .models import Property, PropertyImage, Amenity, Booking, Review, UserProfile, HostApplication, Post
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'role']
    list_filter = ['role']
    search_fields = ['user__username', 'user__email', 'phone_number']

@admin.register(HostApplication)
class HostApplicationAdmin(admin.ModelAdmin):
    list_display = ['user', 'business_name', 'status', 'created_at', 'action_buttons']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'business_name', 'business_phone']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    actions = ['approve_applications', 'reject_applications']
    
    change_list_template = 'admin/app/hostapplication/change_list.html'
    
    def action_buttons(self, obj):
        """Display approve/reject buttons for pending applications"""
        if obj.status == 'pending':
            return format_html(
                '<div class="action-buttons">'
                '<a href="{}" class="button approve-btn" data-id="{}">Approve</a>'
                '<a href="{}" class="button reject-btn" data-id="{}">Reject</a>'
                '</div>',
                reverse('approve_host_application', args=[obj.id]),
                obj.id,
                reverse('reject_host_application', args=[obj.id]),
                obj.id
            )
        elif obj.status == 'approved':
            return format_html('<span class="status-approved">✓ Approved</span>')
        elif obj.status == 'rejected':
            return format_html('<span class="status-rejected">✗ Rejected</span>')
        return '-'
    action_buttons.short_description = 'Actions'
    
    def approve_applications(self, request, queryset):
        approved_count = 0
        for application in queryset.filter(status='pending'):
            application.status = 'approved'
            application.save()
            
            # Update user profile role
            profile = application.user.userprofile
            profile.role = 'host'
            profile.save()
            approved_count += 1
            
        messages.success(request, f'Successfully approved {approved_count} application(s)')
    approve_applications.short_description = "Approve selected applications"
    
    def reject_applications(self, request, queryset):
        rejected_count = 0
        for application in queryset.filter(status='pending'):
            application.status = 'rejected'
            application.save()
            
            # Update user profile role back to regular user if they were pending
            profile = application.user.userprofile
            if profile.role == 'pending_host':
                profile.role = 'user'
                profile.save()
            rejected_count += 1
            
        messages.success(request, f'Successfully rejected {rejected_count} application(s)')
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

# Custom filter for bookings expiring soon
class ExpiringSoonFilter(admin.SimpleListFilter):
    title = 'expiry status'
    parameter_name = 'expiry_status'

    def lookups(self, request, model_admin):
        return (
            ('expiring_soon', 'Expiring soon (< 10 min)'),
            ('expiring_very_soon', 'Expiring very soon (< 5 min)'),
            ('expired', 'Expired'),
            ('not_expiring', 'Not expiring soon'),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        
        if self.value() == 'expiring_soon':
            # Bookings expiring in less than 10 minutes
            cutoff_time = now + timedelta(minutes=10)
            return queryset.filter(
                status='pending',
                payment_status='pending',
                created_at__lt=cutoff_time - timedelta(minutes=30)
            )
        
        elif self.value() == 'expiring_very_soon':
            # Bookings expiring in less than 5 minutes
            cutoff_time = now + timedelta(minutes=5)
            return queryset.filter(
                status='pending',
                payment_status='pending',
                created_at__lt=cutoff_time - timedelta(minutes=30)
            )
        
        elif self.value() == 'expired':
            # Already expired bookings
            cutoff_time = now - timedelta(minutes=30)
            return queryset.filter(
                status='pending',
                payment_status='pending',
                created_at__lt=cutoff_time
            )
        
        elif self.value() == 'not_expiring':
            # Bookings not expiring soon (more than 10 minutes left)
            cutoff_time = now + timedelta(minutes=10)
            return queryset.filter(
                status='pending',
                payment_status='pending',
                created_at__gte=cutoff_time - timedelta(minutes=30)
            )

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['property_obj', 'guest', 'check_in', 'check_out', 'status', 'payment_status', 'created_at', 'reservation_expires_at_display']
    list_filter = ['status', 'payment_status', 'created_at', ExpiringSoonFilter]
    search_fields = ['property_obj__title', 'guest__username', 'stripe_session_id']
    readonly_fields = ['created_at', 'updated_at', 'stripe_session_id', 'reservation_expires_at', 'is_expired', 'time_remaining_seconds']
    ordering = ['-created_at']
    
    actions = [
        'confirm_pending_bookings', 
        'cancel_pending_bookings', 
        'mark_as_completed', 
        'cancel_expired_bookings',
        'resend_payment_link',
        'mark_as_paid_manual'
    ]
    
    def reservation_expires_at_display(self, obj):
        """Display reservation expiry time"""
        if obj.status == 'pending':
            if obj.is_expired:
                return f"EXPIRED ({obj.reservation_expires_at.strftime('%H:%M')})"
            else:
                return f"{obj.reservation_expires_at.strftime('%H:%M')} ({obj.time_remaining_seconds // 60}m left)"
        return "-"
    reservation_expires_at_display.short_description = "Expires At"
    
    def confirm_pending_bookings(self, request, queryset):
        """Manually confirm pending bookings"""
        updated = queryset.filter(status='pending').update(
            status='confirmed',
            payment_status='paid'
        )
        self.message_user(request, f'Successfully confirmed {updated} pending bookings.')
    confirm_pending_bookings.short_description = "Confirm selected pending bookings"
    
    def cancel_pending_bookings(self, request, queryset):
        """Cancel pending bookings"""
        updated = queryset.filter(status='pending').update(
            status='cancelled',
            payment_status='failed'
        )
        self.message_user(request, f'Successfully cancelled {updated} pending bookings.')
    cancel_pending_bookings.short_description = "Cancel selected pending bookings"
    
    def cancel_expired_bookings(self, request, queryset):
        """Cancel expired pending bookings"""
        expired_count = 0
        for booking in queryset.filter(status='pending'):
            if booking.is_expired:
                booking.status = 'cancelled'
                booking.payment_status = 'failed'
                booking.save()
                expired_count += 1
        
        self.message_user(request, f'Successfully cancelled {expired_count} expired bookings.')
    cancel_expired_bookings.short_description = "Cancel expired bookings"
    
    def mark_as_completed(self, request, queryset):
        """Mark confirmed bookings as completed"""
        updated = queryset.filter(status='confirmed').update(status='completed')
        self.message_user(request, f'Successfully marked {updated} bookings as completed.')
    mark_as_completed.short_description = "Mark selected bookings as completed"
    
    def resend_payment_link(self, request, queryset):
        """Resend payment link for pending bookings"""
        import stripe
        from django.conf import settings
        
        stripe.api_key = settings.STRIPE_SECRET_KEY
        success_count = 0
        error_count = 0
        
        for booking in queryset.filter(status='pending', payment_status='pending'):
            try:
                # Check if booking has expired
                if booking.is_expired:
                    self.message_user(
                        request, 
                        f'Booking {booking.id} has expired and cannot be resent. Please cancel and recreate.',
                        level=messages.WARNING
                    )
                    error_count += 1
                    continue
                
                # Calculate nights and total price
                nights = (booking.check_out - booking.check_in).days
                total_price = booking.total_price
                
                # Create new Stripe session
                session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': f'Booking for {booking.property_obj.title}',
                                'description': f'{nights} nights from {booking.check_in} to {booking.check_out}',
                            },
                            'unit_amount': int(total_price * 100),
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    success_url=request.build_absolute_uri(f'/booking/success/?booking_id={booking.id}'),
                    cancel_url=request.build_absolute_uri(f'/booking/cancel/?booking_id={booking.id}'),
                    customer_email=booking.guest.email,
                    metadata={
                        'booking_id': str(booking.id),
                        'property_id': str(booking.property_obj.id),
                    }
                )
                
                # Update booking with new session ID
                booking.stripe_session_id = session.id
                booking.save()
                
                success_count += 1
                
            except Exception as e:
                self.message_user(
                    request, 
                    f'Error resending payment link for booking {booking.id}: {str(e)}',
                    level=messages.ERROR
                )
                error_count += 1
        
        if success_count > 0:
            self.message_user(
                request, 
                f'Successfully resent payment links for {success_count} booking(s).'
            )
        
        if error_count > 0:
            self.message_user(
                request, 
                f'Failed to resend payment links for {error_count} booking(s).',
                level=messages.WARNING
            )
    
    resend_payment_link.short_description = "Resend payment link"
    
    def mark_as_paid_manual(self, request, queryset):
        """Mark bookings as paid manually (for offline payments)"""
        updated = queryset.filter(status='pending').update(
            status='confirmed',
            payment_status='paid'
        )
        self.message_user(
            request, 
            f'Successfully marked {updated} booking(s) as paid manually. '
            'Please ensure payment has been received offline.'
        )
    mark_as_paid_manual.short_description = "Mark as paid (manual payment)"

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
