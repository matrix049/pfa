# Reservation Timer Feature Documentation

## Overview

The reservation timer feature adds a 30-minute countdown timer to pending bookings, automatically cancelling them if payment is not completed within the time limit. This prevents double-booking issues and ensures properties remain available for other guests.

## Features

### 1. Automatic Expiry Calculation
- **30-minute reservation window**: All pending bookings expire 30 minutes after creation
- **Built on existing `created_at` field**: No additional database fields required
- **Real-time expiry checking**: Properties can check if a booking has expired

### 2. Visual Countdown Timer
- **Live countdown display**: Shows minutes and seconds remaining
- **Progress bar**: Visual indicator of time remaining
- **Color-coded urgency**: 
  - Green: >10 minutes remaining
  - Yellow: 5-10 minutes remaining  
  - Red: <5 minutes remaining (with pulsing animation)

### 3. Payment Processing Page
- **Dedicated payment page**: Shows booking details and countdown timer
- **Proceed to payment button**: Redirects to Stripe checkout
- **Cancel booking option**: Allows users to cancel before payment
- **Real-time status updates**: Checks booking status every 5 seconds

### 4. Automatic Cleanup
- **Management command**: `cleanup_expired_bookings` automatically cancels expired bookings
- **Admin interface**: Shows expiry times and allows manual management
- **API endpoints**: For checking booking status and time remaining

## Database Changes

### Booking Model Properties

The `Booking` model now includes these calculated properties:

```python
@property
def reservation_expires_at(self):
    """Calculate when the reservation expires (30 minutes from creation)"""
    return self.created_at + timedelta(minutes=30)

@property
def is_expired(self):
    """Check if the reservation has expired"""
    return timezone.now() > self.reservation_expires_at

@property
def time_remaining_seconds(self):
    """Get time remaining in seconds (negative if expired)"""
    remaining = self.reservation_expires_at - timezone.now()
    return int(remaining.total_seconds())
```

## API Endpoints

### 1. Booking Status API
**URL**: `/api/booking/<booking_id>/status/`
**Method**: GET
**Response**:
```json
{
    "success": true,
    "booking_id": 123,
    "status": "pending",
    "payment_status": "pending",
    "time_remaining_seconds": 1200,
    "is_expired": false,
    "reservation_expires_at": "2024-01-15T14:30:00Z",
    "created_at": "2024-01-15T14:00:00Z"
}
```

### 2. Stripe Session URL API
**URL**: `/api/booking/<booking_id>/stripe-session/`
**Method**: GET
**Response**:
```json
{
    "url": "https://checkout.stripe.com/pay/cs_test_..."
}
```

## Views and Templates

### 1. Payment Processing View
**URL**: `/booking/<booking_id>/processing/`
**Template**: `payment_processing.html`
**Features**:
- Shows booking details
- Displays countdown timer
- Provides payment and cancellation buttons
- Real-time status updates

### 2. Updated Booking Flow
1. User creates booking → Redirected to payment processing page
2. Payment processing page shows countdown timer
3. User clicks "Proceed to Payment" → Redirected to Stripe
4. After payment → Redirected to success page
5. If expired → Automatically cancelled

## JavaScript Components

### PaymentProcessor Class
Located in `app/static/js/payment_processing.js`

**Key Methods**:
- `init()`: Initialize countdown and status checking
- `updateTimerDisplay()`: Update timer and progress bar
- `checkBookingStatus()`: Poll for booking status changes
- `proceedToPayment()`: Redirect to Stripe checkout
- `handleExpiration()`: Handle expired bookings

**Features**:
- Real-time countdown timer
- Automatic status polling (every 5 seconds)
- Visual feedback for different time ranges
- Clean error handling

## Management Commands

### 1. Cleanup Expired Bookings
```bash
python manage.py cleanup_expired_bookings
```

**Options**:
- `--dry-run`: Show what would be cleaned up without doing it

**What it does**:
- Finds all pending bookings that have expired
- Cancels them (status='cancelled', payment_status='failed')
- Marks past confirmed bookings as completed

### 2. Test Reservation Timer
```bash
python manage.py test_reservation_timer --create-test-booking
python manage.py test_reservation_timer --check-expired
python manage.py test_reservation_timer --show-all
```

## Admin Interface

### Booking Admin Updates
- **New column**: "Expires At" showing expiry time and remaining minutes
- **Read-only fields**: `reservation_expires_at`, `is_expired`, `time_remaining_seconds`
- **New actions**: 
  - "Cancel expired bookings"
  - Enhanced existing actions

### Display Format
- **Active bookings**: "14:30 (25m left)"
- **Expired bookings**: "EXPIRED (14:30)"

## Configuration

### Settings
No additional settings required. The 30-minute expiry is hardcoded but can be easily modified in the `reservation_expires_at` property.

### Customization
To change the expiry time, modify the `timedelta(minutes=30)` in the `reservation_expires_at` property.

## Usage Examples

### 1. Creating a Booking
```python
# Normal booking creation flow
booking = Booking.objects.create(
    property=property,
    guest=user,
    check_in=check_in_date,
    check_out=check_out_date,
    guests=2,
    total_price=300.00,
    status='pending',
    payment_status='pending'
)

# Check expiry
print(f"Expires at: {booking.reservation_expires_at}")
print(f"Time remaining: {booking.time_remaining_seconds} seconds")
print(f"Is expired: {booking.is_expired}")
```

### 2. Checking for Expired Bookings
```python
# Find all expired pending bookings
expired_bookings = [
    booking for booking in Booking.objects.filter(
        status='pending', 
        payment_status='pending'
    ) 
    if booking.is_expired
]

# Cancel expired bookings
for booking in expired_bookings:
    booking.status = 'cancelled'
    booking.payment_status = 'failed'
    booking.save()
```

### 3. Frontend Integration
```javascript
// Check booking status
fetch(`/api/booking/${bookingId}/status/`)
    .then(response => response.json())
    .then(data => {
        if (data.is_expired) {
            // Handle expired booking
            showExpiredMessage();
        } else {
            // Update countdown timer
            updateTimer(data.time_remaining_seconds);
        }
    });
```

## Security Considerations

### 1. Permission Checks
- Booking status API requires user authentication
- Users can only check their own bookings
- Admin actions are properly protected

### 2. Race Conditions
- Database transactions ensure atomic operations
- Status checking prevents double-processing
- Webhook handling includes proper error handling

### 3. Data Integrity
- Expired bookings are automatically cleaned up
- Status transitions are properly managed
- Payment status is synchronized with booking status

## Troubleshooting

### Common Issues

1. **Timer not updating**
   - Check if JavaScript is loading properly
   - Verify API endpoints are accessible
   - Check browser console for errors

2. **Bookings not expiring**
   - Run cleanup command manually: `python manage.py cleanup_expired_bookings`
   - Check server timezone settings
   - Verify `created_at` field is being set correctly

3. **Payment processing issues**
   - Check Stripe configuration
   - Verify webhook endpoints
   - Check booking status API responses

### Debug Commands
```bash
# Check for expired bookings
python manage.py test_reservation_timer --check-expired

# Show all pending bookings
python manage.py test_reservation_timer --show-all

# Create test booking
python manage.py test_reservation_timer --create-test-booking

# Clean up expired bookings
python manage.py cleanup_expired_bookings --dry-run
```

## Future Enhancements

### Potential Improvements
1. **Configurable expiry times**: Different times for different property types
2. **Email notifications**: Alert users before expiry
3. **Extension requests**: Allow users to request more time
4. **Analytics**: Track expiry rates and payment completion rates
5. **Mobile notifications**: Push notifications for countdown timer

### Integration Points
- **Email system**: Send expiry warnings
- **SMS notifications**: Text alerts for urgent payments
- **Analytics dashboard**: Track booking conversion rates
- **Host notifications**: Alert hosts of pending payments

## Testing

### Manual Testing
1. Create a booking and check the payment processing page
2. Wait for expiry and verify automatic cancellation
3. Test payment completion and status updates
4. Verify admin interface shows correct expiry times

### Automated Testing
- Unit tests for model properties
- Integration tests for API endpoints
- Frontend tests for countdown timer
- Management command tests

## Support

For issues or questions about the reservation timer feature:
1. Check the troubleshooting section above
2. Review the management commands for debugging
3. Check the admin interface for booking status
4. Verify API endpoints are responding correctly 