from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0018_remove_obsolete_fields_and_fix_schema'),
    ]

    operations = [
        migrations.AddField(
            model_name='quizsession',
            name='client_request_id',
            field=models.UUIDField(blank=True, null=True),
        ),
    ]
