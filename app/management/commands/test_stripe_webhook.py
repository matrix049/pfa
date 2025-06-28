from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse
import json
import stripe
from django.conf import settings

class Command(BaseCommand):
    help = 'Test Stripe webhook functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--event-type',
            type=str,
            default='checkout.session.completed',
            help='Type of webhook event to test (default: checkout.session.completed)',
        )
        parser.add_argument(
            '--booking-id',
            type=int,
            help='Booking ID to use in the test event',
        )

    def handle(self, *args, **options):
        event_type = options['event_type']
        booking_id = options['booking_id']
        
        if not booking_id:
            self.stdout.write(
                self.style.ERROR('Please provide a booking ID with --booking-id')
            )
            return
        
        # Create test webhook event
        if event_type == 'checkout.session.completed':
            event_data = {
                'id': 'evt_test_webhook',
                'object': 'event',
                'api_version': '2020-08-27',
                'created': 1234567890,
                'data': {
                    'object': {
                        'id': 'cs_test_session',
                        'object': 'checkout.session',
                        'metadata': {
                            'booking_id': str(booking_id),
                            'property_id': '1'
                        },
                        'payment_status': 'paid',
                        'status': 'complete'
                    }
                },
                'livemode': False,
                'pending_webhooks': 1,
                'request': {
                    'id': 'req_test',
                    'idempotency_key': None
                },
                'type': event_type
            }
        elif event_type == 'payment_intent.succeeded':
            event_data = {
                'id': 'evt_test_webhook',
                'object': 'event',
                'api_version': '2020-08-27',
                'created': 1234567890,
                'data': {
                    'object': {
                        'id': 'pi_test_payment_intent',
                        'object': 'payment_intent',
                        'metadata': {
                            'session_id': 'cs_test_session'
                        },
                        'status': 'succeeded'
                    }
                },
                'livemode': False,
                'pending_webhooks': 1,
                'request': {
                    'id': 'req_test',
                    'idempotency_key': None
                },
                'type': event_type
            }
        elif event_type == 'payment_intent.payment_failed':
            event_data = {
                'id': 'evt_test_webhook',
                'object': 'event',
                'api_version': '2020-08-27',
                'created': 1234567890,
                'data': {
                    'object': {
                        'id': 'pi_test_payment_intent',
                        'object': 'payment_intent',
                        'metadata': {
                            'session_id': 'cs_test_session'
                        },
                        'status': 'requires_payment_method'
                    }
                },
                'livemode': False,
                'pending_webhooks': 1,
                'request': {
                    'id': 'req_test',
                    'idempotency_key': None
                },
                'type': event_type
            }
        else:
            self.stdout.write(
                self.style.ERROR(f'Unsupported event type: {event_type}')
            )
            return
        
        # Create webhook signature
        payload = json.dumps(event_data).encode('utf-8')
        timestamp = '1234567890'
        signed_payload = f'{timestamp}.{payload.decode()}'
        
        # Generate signature (this is a simplified version for testing)
        import hmac
        import hashlib
        signature = hmac.new(
            settings.STRIPE_WEBHOOK_SECRET.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Create webhook signature header
        sig_header = f't={timestamp},v1={signature}'
        
        # Send test webhook
        client = Client()
        response = client.post(
            reverse('stripe_webhook'),
            data=payload,
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE=sig_header
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Webhook test completed for {event_type}')
        )
        self.stdout.write(f'Response status: {response.status_code}')
        self.stdout.write(f'Response content: {response.content.decode()}')
        
        if response.status_code == 200:
            self.stdout.write(
                self.style.SUCCESS('Webhook test PASSED')
            )
        else:
            self.stdout.write(
                self.style.ERROR('Webhook test FAILED')
            ) 