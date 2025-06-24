from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app.models import UserProfile

class Command(BaseCommand):
    help = 'Syncs superuser status with UserProfile admin role'

    def handle(self, *args, **options):
        superusers = User.objects.filter(is_superuser=True)
        count = 0
        
        for user in superusers:
            try:
                profile = UserProfile.objects.get(user=user)
                if profile.role != 'admin':
                    profile.role = 'admin'
                    profile.save()
                    count += 1
                    self.stdout.write(self.style.SUCCESS(f'Updated role for superuser: {user.username}'))
            except UserProfile.DoesNotExist:
                profile = UserProfile.objects.create(user=user, role='admin')
                count += 1
                self.stdout.write(self.style.SUCCESS(f'Created admin profile for superuser: {user.username}'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} superuser profiles')) 