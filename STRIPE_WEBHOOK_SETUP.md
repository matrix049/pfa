# Stripe Webhook Implementation Guide

## Overview

This implementation adds secure Stripe webhook handling to your booking system, providing reliable payment confirmation and failure handling.

## Features Implemented

### 1. Webhook Endpoint
- **URL**: `/webhooks/stripe/`
- **Method**: POST only
- **Security**: Signature verification using `STRIPE_WEBHOOK_SECRET`

### 2. Supported Events
- `checkout.session.completed` - Payment successful
- `payment_intent.succeeded` - Payment intent succeeded
- `payment_intent.payment_failed` - Payment failed

### 3. Security Features
- Webhook signature verification
- Comprehensive error handling
- Detailed logging
- Transaction safety with atomic operations

## Configuration

### 1. Environment Variables
Add to your `.env` file:
```bash
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

### 2. Settings Configuration
The webhook secret is automatically loaded from environment variables:
```python
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_test_webhook_secret')
```

## Stripe Dashboard Setup

### 1. Create Webhook Endpoint
1. Go to [Stripe Dashboard](https://dashboard.stripe.com/webhooks)
2. Click "Add endpoint"
3. Set endpoint URL: `https://yourdomain.com/webhooks/stripe/`
4. Select events to listen for:
   - `checkout.session.completed`
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
5. Copy the webhook signing secret

### 2. Update Environment
Replace `whsec_your_webhook_secret_here` with your actual webhook secret.

## Webhook Flow

### 1. Payment Success Flow
```
User completes payment → Stripe sends webhook → Webhook verifies signature → 
Updates booking status to 'confirmed' → Returns success response
```

### 2. Payment Failure Flow
```
Payment fails → Stripe sends webhook → Webhook verifies signature → 
Updates booking status to 'cancelled' → Returns success response
```

### 3. Availability Check
Before confirming any booking, the webhook:
1. Checks if the date range is still available
2. Cancels booking if dates are no longer available
3. Logs the conflict for monitoring

## Error Handling

### 1. Signature Verification
- Invalid payload: Returns 400
- Invalid signature: Returns 400
- Missing signature: Returns 400

### 2. Booking Processing
- Booking not found: Returns 404
- Availability conflict: Cancels booking and logs warning
- Database errors: Returns 500 with detailed logging

### 3. Logging
All webhook events are logged with:
- Event type
- Booking ID
- Success/failure status
- Error details (if any)

## Testing

### 1. Using Management Command
```bash
# Test successful payment
python manage.py test_stripe_webhook --booking-id 1 --event-type checkout.session.completed

# Test payment failure
python manage.py test_stripe_webhook --booking-id 1 --event-type payment_intent.payment_failed
```

### 2. Using Stripe CLI
```bash
# Install Stripe CLI
stripe listen --forward-to localhost:8000/webhooks/stripe/

# Trigger test events
stripe trigger checkout.session.completed
stripe trigger payment_intent.payment_failed
```

## Monitoring

### 1. Log Monitoring
Monitor these log patterns:
- `Processing webhook event: checkout.session.completed`
- `Booking {id} confirmed successfully via webhook`
- `Booking {id} cancelled due to availability conflict`

### 2. Database Monitoring
Query for webhook-processed bookings:
```sql
-- Successful webhook confirmations
SELECT * FROM app_booking 
WHERE status = 'confirmed' AND payment_status = 'paid';

-- Failed payments
SELECT * FROM app_booking 
WHERE status = 'cancelled' AND payment_status = 'failed';
```

## Security Considerations

### 1. Webhook Secret
- Never commit the webhook secret to version control
- Use environment variables for production
- Rotate secrets regularly

### 2. Signature Verification
- Always verify webhook signatures
- Use the exact webhook secret from Stripe dashboard
- Reject requests without valid signatures

### 3. Idempotency
- Webhook handlers are idempotent
- Duplicate events won't cause issues
- Already processed bookings are ignored

## Troubleshooting

### 1. Webhook Not Receiving Events
- Check webhook endpoint URL in Stripe dashboard
- Verify webhook is active and not disabled
- Check server logs for connection errors

### 2. Signature Verification Failing
- Verify webhook secret matches Stripe dashboard
- Check if webhook secret was updated
- Ensure no proxy/load balancer is modifying headers

### 3. Bookings Not Updating
- Check database connection
- Verify booking exists with correct session_id
- Review webhook logs for specific errors

## Production Deployment

### 1. HTTPS Required
- Stripe requires HTTPS for webhook endpoints
- Configure SSL certificate
- Update webhook URL in Stripe dashboard

### 2. Environment Variables
```bash
# Production environment
STRIPE_WEBHOOK_SECRET=whsec_live_your_actual_secret
STRIPE_SECRET_KEY=sk_live_your_live_key
STRIPE_PUBLIC_KEY=pk_live_your_live_key
```

### 3. Monitoring Setup
- Set up log aggregation (e.g., Sentry, Loggly)
- Configure alerts for webhook failures
- Monitor booking confirmation rates

## Backup Payment Flow

The system maintains the existing redirect-based flow as a backup:
- If webhook fails, users can still complete payment via redirect
- Both flows update booking status correctly
- No duplicate confirmations occur

## API Response Format

### Success Response
```json
{
  "status": "success"
}
```

### Error Response
```json
{
  "error": "Error description"
}
```

### Ignored Event
```json
{
  "status": "ignored"
}
```

## Migration from Redirect-Only

1. Deploy webhook endpoint
2. Configure webhook in Stripe dashboard
3. Test with management command
4. Monitor webhook success rates
5. Gradually reduce reliance on redirect flow

The webhook implementation provides a more reliable and secure payment confirmation system while maintaining backward compatibility with the existing redirect-based flow. 