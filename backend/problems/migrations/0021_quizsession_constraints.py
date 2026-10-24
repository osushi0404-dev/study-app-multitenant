from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('problems', '0020_deactivate_duplicate_active_quizsessions'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='quizsession',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_active', True)),
                fields=('user',),
                name='uniq_active_quizsession_per_user',
            ),
        ),
        migrations.AddConstraint(
            model_name='quizsession',
            constraint=models.UniqueConstraint(
                condition=models.Q(('client_request_id__isnull', False)),
                fields=('user', 'client_request_id'),
                name='uniq_quizsession_user_request_id',
            ),
        ),
    ]
