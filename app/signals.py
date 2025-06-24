from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        role = 'admin' if instance.is_superuser else 'user'
        UserProfile.objects.create(user=instance, role=role)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        profile = instance.userprofile
        # Update role if user becomes a superuser
        if instance.is_superuser and profile.role != 'admin':
            profile.role = 'admin'
        profile.save()
    except UserProfile.DoesNotExist:
        role = 'admin' if instance.is_superuser else 'user'
        UserProfile.objects.create(user=instance, role=role) 