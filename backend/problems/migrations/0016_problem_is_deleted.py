from django.db import migrations, models


def migrate_is_active_to_is_deleted(apps, schema_editor):
    """is_active=False → is_deleted=True に変換"""
    Problem = apps.get_model('problems', 'Problem')
    # is_active=False（削除済み）のレコードをis_deleted=Trueに
    Problem.objects.filter(is_active=False).update(is_deleted=True)
    # is_active=True（有効）のレコードはis_deleted=False（デフォルト値）のまま


def reverse_migrate(apps, schema_editor):
    """ロールバック用: is_deleted=True → is_active=False に変換"""
    Problem = apps.get_model('problems', 'Problem')
    Problem.objects.filter(is_deleted=True).update(is_active=False)
    Problem.objects.filter(is_deleted=False).update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [
        ('problems', '0015_add_is_deleted_to_problem_media_asset'),
    ]

    operations = [
        # Step 1: is_deletedカラム追加
        migrations.AddField(
            model_name='problem',
            name='is_deleted',
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text='論理削除フラグ'
            ),
        ),
        # Step 2: データ移行
        migrations.RunPython(migrate_is_active_to_is_deleted, reverse_migrate),
        # Step 3: is_activeカラム削除
        migrations.RemoveField(
            model_name='problem',
            name='is_active',
        ),
    ]
