from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from app.models import Booking

class Command(BaseCommand):
    help = 'Clean up expired and abandoned bookings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually doing it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Find expired pending bookings using the new expiry logic
        expired_bookings = Booking.objects.filter(
            status='pending',
            payment_status='pending'
        )
        
        # Filter to only include actually expired bookings
        expired_bookings = [booking for booking in expired_bookings if booking.is_expired]
        
        # Find past bookings that should be marked as completed
        past_bookings = Booking.objects.filter(
            status='confirmed',
            check_out__lt=timezone.now().date()
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN - Would clean up {len(expired_bookings)} expired bookings and mark {past_bookings.count()} as completed'
                )
            )
            
            if expired_bookings:
                self.stdout.write('\nExpired bookings that would be cancelled:')
                for booking in expired_bookings[:10]:  # Show first 10
                    self.stdout.write(
                        f'  - Booking {booking.id}: {booking.property_obj.title} ({booking.check_in} to {booking.check_out}) - Expired at {booking.reservation_expires_at}'
                    )
                if len(expired_bookings) > 10:
                    self.stdout.write(f'  ... and {len(expired_bookings) - 10} more')
            
            if past_bookings.exists():
                self.stdout.write('\nPast bookings that would be marked as completed:')
                for booking in past_bookings[:10]:  # Show first 10
                    self.stdout.write(
                        f'  - Booking {booking.id}: {booking.property_obj.title} ({booking.check_in} to {booking.check_out})'
                    )
                if past_bookings.count() > 10:
                    self.stdout.write(f'  ... and {past_bookings.count() - 10} more')
        else:
            with transaction.atomic():
                # Cancel expired bookings
                expired_count = 0
                for booking in expired_bookings:
                    booking.status = 'cancelled'
                    booking.payment_status = 'failed'
                    booking.save()
                    expired_count += 1
                
                # Mark past bookings as completed
                completed_count = past_bookings.update(status='completed')
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully cleaned up {expired_count} expired bookings and marked {completed_count} as completed'
                    )
                ) 