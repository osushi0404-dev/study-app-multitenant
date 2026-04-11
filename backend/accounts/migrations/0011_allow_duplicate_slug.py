# Generated manually to allow duplicate slugs in Organization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_update_organization_structure'),
    ]

    operations = [
        # slugフィールドのunique制約を削除
        migrations.AlterField(
            model_name='organization',
            name='slug',
            field=models.SlugField(
                help_text='URL用の識別子（半角英数字とハイフンのみ）',
                max_length=50,
                verbose_name='URL識別子'
            ),
        ),
    ]
