# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0007_reorder_subject_group_columns'),
    ]

    operations = [
        migrations.AddField(
            model_name='problem',
            name='question_image',
            field=models.ImageField(
                blank=True,
                help_text='問題文に添付する画像（最大5MB、JPEG/PNG/WebP形式）',
                max_length=200,
                null=True,
                upload_to='problems/questions/',
                verbose_name='問題画像'
            ),
        ),
        migrations.AddField(
            model_name='problem',
            name='explanation_image',
            field=models.ImageField(
                blank=True,
                help_text='解説に添付する画像（最大5MB、JPEG/PNG/WebP形式）',
                max_length=200,
                null=True,
                upload_to='problems/explanations/',
                verbose_name='解説画像'
            ),
        ),
    ]
