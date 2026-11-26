from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Organization, User, UserSettings, StudyStreak
from .passkeys import delete_passkeys_of_inactive_organization, delete_passkeys_of_inactive_user


# 無効化でのパスキーの削除（I619）。無効化の入口（toggle_active・管理者の API の更新・Django の管理画面・
# 組織は shell と DB だけ）のどれからでも必ず消えるよう、シグナルで後片付けする（計画書 9）
def _may_change_is_active(update_fields) -> bool:
    """update_fields を指定した保存で is_active を含まないもの（last_login だけ等）は見なくてよい"""
    return update_fields is None or 'is_active' in update_fields


@receiver(post_save, sender=User)
def delete_passkeys_when_user_deactivated(sender, instance, update_fields=None, **kwargs):
    if _may_change_is_active(update_fields):
        delete_passkeys_of_inactive_user(user=instance)


@receiver(post_save, sender=Organization)
def delete_passkeys_when_organization_deactivated(sender, instance, update_fields=None, **kwargs):
    if _may_change_is_active(update_fields):
        delete_passkeys_of_inactive_organization(organization=instance)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create UserSettings and StudyStreak when a new user is created
    """
    if created:
        UserSettings.objects.get_or_create(user=instance)
        StudyStreak.objects.get_or_create(user=instance)
