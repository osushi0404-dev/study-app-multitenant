"""
I590: 使われなくなった Subject.image_directory を外す（Danger Ops・2026-11-20 承認済み）

画像は I587 から DB に保存し、科目ごとの画像の置き場を使わない。
値のある科目が 1 件でもあれば、黙って消さずに止める（C7）。
"""
from django.db import migrations


def refuse_if_image_directory_set(apps, schema_editor):
    Subject = apps.get_model('problems', 'Subject')
    count = Subject.objects.exclude(image_directory='').count()  # 列は NOT NULL
    if count:
        raise RuntimeError(
            f'I590: image_directory に値のある科目が {count} 件あります。'
            '値の使い道を確かめて空にしてから、もう一度 migrate してください')


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0026_remove_problem_legacy_images'),
    ]

    operations = [
        migrations.RunPython(refuse_if_image_directory_set, reverse_code=migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='subject',
            name='image_directory',
        ),
    ]
