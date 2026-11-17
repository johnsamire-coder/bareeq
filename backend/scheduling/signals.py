from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import User

from .models import TechnicianProfile


@receiver(post_save, sender=User)
def create_technician_profile(sender, instance, **kwargs):
    if instance.role == User.Role.TECHNICIAN:
        TechnicianProfile.objects.get_or_create(user=instance)
