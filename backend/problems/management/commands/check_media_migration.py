"""
I587: 画像のファイルを DB に移す前の試し（読むだけ・何も書かない）

    python manage.py check_media_migration

行ごとの判定（移す・済み・消す〔ファイル無し〕）と件数を出す。
古い画像の列に値のある問題は、マイグレーション 0026 が数えて止める。
"""
from django.core.management.base import BaseCommand, CommandError

from problems.media_migration import (
    LEGACY_MEDIA_ROOT, MediaMigrationError, move_media_files_to_db,
)
from problems.models import MediaAsset, MediaAssetContent, ProblemMediaAsset


class Command(BaseCommand):
    help = '画像のファイルを DB に移す前の試し（読むだけ・I587）'

    def handle(self, *args, **options):
        try:
            result = move_media_files_to_db(
                asset_model=MediaAsset, link_model=ProblemMediaAsset,
                content_model=MediaAssetContent, media_root=LEGACY_MEDIA_ROOT, dry_run=True)
        except MediaMigrationError as error:
            raise CommandError(str(error)) from error
        for asset_id, key, action in result.planned:
            self.stdout.write(f'{action}\t{asset_id}\t{key}')
        self.stdout.write(f'I587 media（試し）: {result.summary()}')
