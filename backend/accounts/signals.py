from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserSettings, StudyStreak


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create UserSettings and StudyStreak when a new user is created
    """
    if created:
        UserSettings.objects.get_or_create(user=instance)
        StudyStreak.objects.get_or_create(user=instance)