from django.core.management.base import BaseCommand
from django.utils import timezone
from app.models import Booking
from datetime import timedelta

class Command(BaseCommand):
    help = 'Test reservation timer functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-test-booking',
            action='store_true',
            help='Create a test booking to demonstrate the timer',
        )
        parser.add_argument(
            '--check-expired',
            action='store_true',
            help='Check for expired bookings',
        )
        parser.add_argument(
            '--show-all',
            action='store_true',
            help='Show all pending bookings with their timer status',
        )

    def handle(self, *args, **options):
        if options['create_test_booking']:
            self.create_test_booking()
        elif options['check_expired']:
            self.check_expired_bookings()
        elif options['show_all']:
            self.show_all_pending_bookings()
        else:
            self.show_help()

    def create_test_booking(self):
        """Create a test booking to demonstrate the timer"""
        from app.models import Property, User
        
        # Get the first available property and user
        try:
            property = Property.objects.first()
            user = User.objects.first()
            
            if not property or not user:
                self.stdout.write(
                    self.style.ERROR('No properties or users found. Please create some first.')
                )
                return
            
            # Create a test booking
            booking = Booking.objects.create(
                property=property,
                guest=user,
                check_in=timezone.now().date() + timedelta(days=7),
                check_out=timezone.now().date() + timedelta(days=10),
                guests=2,
                total_price=300.00,
                status='pending',
                payment_status='pending'
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created test booking {booking.id} for {property.title}'
                )
            )
            self.stdout.write(
                f'  - Created at: {booking.created_at}'
            )
            self.stdout.write(
                f'  - Expires at: {booking.reservation_expires_at}'
            )
            self.stdout.write(
                f'  - Time remaining: {booking.time_remaining_seconds // 60} minutes'
            )
            self.stdout.write(
                f'  - Is expired: {booking.is_expired}'
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating test booking: {str(e)}')
            )

    def check_expired_bookings(self):
        """Check for expired bookings"""
        pending_bookings = Booking.objects.filter(
            status='pending',
            payment_status='pending'
        )
        
        expired_count = 0
        active_count = 0
        
        for booking in pending_bookings:
            if booking.is_expired:
                expired_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'EXPIRED: Booking {booking.id} for {booking.property_obj.title}'
                    )
                )
                self.stdout.write(
                    f'  - Created: {booking.created_at}'
                )
                self.stdout.write(
                    f'  - Expired: {booking.reservation_expires_at}'
                )
                self.stdout.write(
                    f'  - Time overdue: {abs(booking.time_remaining_seconds) // 60} minutes'
                )
            else:
                active_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Found {expired_count} expired and {active_count} active pending bookings'
            )
        )

    def show_all_pending_bookings(self):
        """Show all pending bookings with their timer status"""
        pending_bookings = Booking.objects.filter(
            status='pending',
            payment_status='pending'
        ).order_by('created_at')
        
        if not pending_bookings.exists():
            self.stdout.write('No pending bookings found.')
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'Found {pending_bookings.count()} pending bookings:')
        )
        
        for booking in pending_bookings:
            status = 'EXPIRED' if booking.is_expired else 'ACTIVE'
            color = self.style.WARNING if booking.is_expired else self.style.SUCCESS
            
            self.stdout.write(
                color(f'{status}: Booking {booking.id} - {booking.property_obj.title}')
            )
            self.stdout.write(
                f'  - Guest: {booking.guest.username}'
            )
            self.stdout.write(
                f'  - Dates: {booking.check_in} to {booking.check_out}'
            )
            self.stdout.write(
                f'  - Created: {booking.created_at}'
            )
            self.stdout.write(
                f'  - Expires: {booking.reservation_expires_at}'
            )
            
            if booking.is_expired:
                self.stdout.write(
                    f'  - Overdue: {abs(booking.time_remaining_seconds) // 60} minutes'
                )
            else:
                self.stdout.write(
                    f'  - Remaining: {booking.time_remaining_seconds // 60} minutes'
                )
            
            self.stdout.write('')

    def show_help(self):
        """Show usage help"""
        self.stdout.write(
            self.style.SUCCESS('Reservation Timer Test Commands:')
        )
        self.stdout.write('')
        self.stdout.write('  --create-test-booking: Create a test booking to demonstrate the timer')
        self.stdout.write('  --check-expired: Check for expired bookings')
        self.stdout.write('  --show-all: Show all pending bookings with their timer status')
        self.stdout.write('')
        self.stdout.write('Examples:')
        self.stdout.write('  python manage.py test_reservation_timer --create-test-booking')
        self.stdout.write('  python manage.py test_reservation_timer --check-expired')
        self.stdout.write('  python manage.py test_reservation_timer --show-all') 