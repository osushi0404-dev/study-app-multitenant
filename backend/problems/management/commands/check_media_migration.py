"""
I587: 画像のファイルを DB に移す前の試し（読むだけ・何も書かない）

    python manage.py check_media_migration

行ごとの判定（移す・済み・消す〔ファイル無し〕）と件数、古い画像の列に値のある問題の件数を出す。
"""
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from problems.media_migration import (
    LEGACY_MEDIA_ROOT, MediaMigrationError, move_media_files_to_db,
)
from problems.models import MediaAsset, MediaAssetContent, Problem, ProblemMediaAsset

LEGACY_FIELDS = ('question_image', 'explanation_image')


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
        self.stdout.write(f'古い画像の列: {self._legacy_summary()}')

    @staticmethod
    def _legacy_summary() -> str:
        names = {f.name for f in Problem._meta.get_fields()}
        if not set(LEGACY_FIELDS) <= names:
            return '列なし（外し済み）'
        condition = Q()
        for name in LEGACY_FIELDS:
            condition |= ~Q(**{f'{name}__isnull': True}) & ~Q(**{name: ''})
        return f'値のある問題 {Problem.objects.filter(condition).count()} 件'
