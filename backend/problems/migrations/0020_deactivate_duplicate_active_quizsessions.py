from django.db import migrations
from django.utils import timezone


def deactivate_duplicate_active_sessions(apps, schema_editor):
    """同一ユーザーの有効セッションが複数ある場合、最新（started_at・id の降順で先頭）以外を終了扱いにする。
    削除はしない（回答データは残る）。"""
    QuizSession = apps.get_model('problems', 'QuizSession')
    now = timezone.now()
    seen_users = set()
    for session in QuizSession.objects.filter(is_active=True).order_by('user_id', '-started_at', '-id'):
        if session.user_id in seen_users:
            session.is_active = False
            session.ended_at = session.ended_at or now
            session.save(update_fields=['is_active', 'ended_at'])
        else:
            seen_users.add(session.user_id)


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0019_quizsession_client_request_id'),
    ]

    operations = [
        migrations.RunPython(deactivate_duplicate_active_sessions, migrations.RunPython.noop),
    ]
