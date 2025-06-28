from django.core.management.base import BaseCommand
from app.models import Property
from decimal import Decimal

class Command(BaseCommand):
    help = 'Reduce all property prices by 50%'

    def handle(self, *args, **options):
        properties = Property.objects.all()
        updated_count = 0
        
        for property in properties:
            # Calculate new price (50% reduction)
            new_price = property.price_per_night * Decimal('0.5')
            old_price = property.price_per_night
            
            # Update the price
            property.price_per_night = new_price
            property.save()
            
            updated_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'Updated {property.title}: ${old_price} → ${new_price}'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {updated_count} properties with 50% price reduction'
            )
        ) 