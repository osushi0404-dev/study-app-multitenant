"""
I587: 今ある画像ファイルを DB（media_asset_contents）に移す。ファイルの無い画像の行と紐づけは消す（Danger Ops・承認済み）

中身は problems.media_migration にある（試しは manage.py check_media_migration）。
"""
import logging
import sys

from django.db import migrations

from problems import media_migration

logger = logging.getLogger(__name__)


def _models(apps):
    return {
        'asset_model': apps.get_model('problems', 'MediaAsset'),
        'link_model': apps.get_model('problems', 'ProblemMediaAsset'),
        'content_model': apps.get_model('problems', 'MediaAssetContent'),
    }


def forward(apps, schema_editor):
    result = media_migration.move_media_files_to_db(
        **_models(apps), media_root=media_migration.LEGACY_MEDIA_ROOT, dry_run=False)
    sys.stdout.write(f'\n  I587 media: {result.summary()}\n')
    # 古い /media/ の URL を含む一覧のキャッシュを捨てる。捨てられなくても最長 1 時間で切れる
    try:
        from core.cache_service import cache_service
        cache_service.invalidate_problems_cache()
    except Exception:
        logger.warning('I587 media: problems cache invalidation failed', exc_info=True)


def backward(apps, schema_editor):
    models = _models(apps)
    media_migration.write_back_media_files(
        asset_model=models['asset_model'], content_model=models['content_model'],
        media_root=media_migration.LEGACY_MEDIA_ROOT)


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0024_mediaassetcontent'),
    ]

    operations = [
        migrations.RunPython(forward, reverse_code=backward),
    ]
