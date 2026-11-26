"""登録用リンクをサーバーで発行する（I620）

運営のアカウント（is_staff・is_superuser）あては画面・API から発行できないので、このコマンドだけで出す。
URL は標準出力にだけ出す（ログには値を出さない）。
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import User
from accounts.registration_links import INACTIVE_TARGET, issue_link, link_url


class Command(BaseCommand):
    help = '利用者あての登録用リンク（1 時間・1 回だけ）を発行する。前のパスキーとログイン中の状態は使えなくなる'

    def add_arguments(self, parser):
        parser.add_argument('user_id', help='利用者のユーザー ID')

    def handle(self, *args, **options):
        user = User.objects.filter(user_id=options['user_id']).first()
        if user is None:
            raise CommandError('利用者が見つかりません')
        if not user.is_active:
            raise CommandError(INACTIVE_TARGET)
        link, token = issue_link(target=user, issued_by=None)
        expires = timezone.localtime(link.expires_at).strftime('%Y/%m/%d %H:%M')
        self.stdout.write(f'登録用リンク（{expires} まで・1 回だけ）:')
        self.stdout.write(link_url(token))
