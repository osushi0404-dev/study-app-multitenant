"""
ダッシュボードの確かめ用のデータを作り直し、画面に出るはずの値（期待値）を出す（開発の DB だけ・I513）

流し方（パスワードは e2e/.env.e2e の E2E_TEST_PASSWORD を、e2e-init のコンテナの中で読む）:
    docker compose run --rm --no-deps e2e-init python manage.py seed_dashboard_verify --password-env E2E_TEST_PASSWORD
開発の起動のたびに、compose の dashboard-verify-seed が --soft-stop 付きで流す
（I524。出力は docker compose logs dashboard-verify-seed）
手順: docs/runbooks/frontend-verify.md「11. 確かめ用のデータ（ダッシュボード）」
"""
import os
import secrets

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from dashboard.verify_data import VerifyDataError, VerifyDataUnavailable, format_summary, seed_verify_data

SEED_LIMIT = 2 ** 31


class Command(BaseCommand):
    help = 'ダッシュボードの確かめ用のデータを乱数で作り直し、期待値を出す（DEBUG のときだけ）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--seed', type=int, default=None,
            help='乱数の種（省略すると毎回違う。出力の種を渡すと同じデータを作り直せる）',
        )
        parser.add_argument(
            '--password-env', required=True,
            help='確かめ用の利用者のパスワードを読む環境変数の名前（値そのものは引数で渡さない）',
        )
        parser.add_argument(
            '--soft-stop', action='store_true',
            help=('作れる環境にない（DEBUG が偽・パスワードが空）ときは、作らずに警告を出して正常に終わる'
                  '（開発の起動の処理から呼ぶため。起きてはいけない状態はエラーで終わる）'),
        )

    def handle(self, *args, **options):
        seed = options['seed'] if options['seed'] is not None else secrets.randbelow(SEED_LIMIT)
        password = os.environ.get(options['password_env'], '')
        try:
            summary = seed_verify_data(seed=seed, password=password, now=timezone.now())
        except VerifyDataUnavailable as error:
            if not options['soft_stop']:
                raise CommandError(str(error)) from error
            self.stderr.write(self.style.WARNING(f'確かめ用のデータは作りませんでした: {error}'))
            return
        except VerifyDataError as error:
            raise CommandError(str(error)) from error
        for line in format_summary(summary, seed):
            self.stdout.write(line)
