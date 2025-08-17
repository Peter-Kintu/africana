from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
# REMOVED: from .models import Student # No longer needed here for Student creation

@receiver(post_save, sender=User)
def create_auth_token(sender, instance, created, **kwargs):
    """
    Signal receiver to create an Auth Token whenever a new User is created.
    Student profile creation is now handled in views.py.
    """
    if created:
        # Create Auth Token
        Token.objects.create(user=instance)

        # REMOVED: Student.objects.create(user=instance) # Student creation moved to views.py