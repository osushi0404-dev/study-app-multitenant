from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from accounts.models import Organization, OrganizationCategory

User = get_user_model()

SCENARIOS = {
    'login': '_seed_login',
    'tenant_isolation': '_seed_tenant_isolation',
    'quiz_session': '_seed_quiz_session',
}


class Command(BaseCommand):
    help = 'Seed E2E test data by scenario'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scenario', required=True, choices=SCENARIOS.keys(),
        )
        parser.add_argument(
            '--password',
            required=True,
            help='E2E test user password. Pass via env var; do not hardcode.',
        )
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Flush DB before seeding (use only on E2E test DB)',
        )

    def handle(self, *args, **options):
        # E2E の利用者（既知のパスワード・運営を含む）を本番に作らない（I636 design-security-review）
        if not settings.DEBUG:
            raise CommandError('seed_e2e は DEBUG が真の環境（開発・E2E）でだけ流せます')
        self.e2e_password = options['password']

        if options['flush']:
            from django.core.management import call_command
            call_command('flush', '--no-input')
            call_command('migrate', '--noinput')

        method = getattr(self, SCENARIOS[options['scenario']])
        method()
        self.stdout.write(
            self.style.SUCCESS(f"Seeded scenario: {options['scenario']}")
        )

    def _get_or_create_category(self):
        cat, _ = OrganizationCategory.objects.get_or_create(
            slug='education',
            defaults={
                'name': '教育',
                'description': 'E2E テスト用カテゴリー',
                'display_order': 99,
            },
        )
        return cat

    def _seed_login(self):
        cat = self._get_or_create_category()
        org_a, _ = Organization.objects.get_or_create(
            slug='e2e-org-a',
            defaults={'name': 'E2E Org A', 'category': cat},
        )
        User.objects.filter(email='e2e_user_a@example.com').delete()
        User.objects.create_user(
            email='e2e_user_a@example.com',
            user_id='e2e_user_a',
            password=self.e2e_password,
            organization=org_a,
            role='admin',  # /subject-management へのアクセスに admin ロールが必要
        )
        # I102: 問題管理 authz E2E 用の非admin ユーザー（org_a・role='user'）。
        # 「問題管理」メニュー非表示・/quiz-management 遮断を検証するために必要。
        User.objects.filter(email='e2e_user_c@example.com').delete()
        User.objects.create_user(
            email='e2e_user_c@example.com',
            user_id='e2e_user_c',
            password=self.e2e_password,
            organization=org_a,
            role='user',
        )

    def _seed_tenant_isolation(self):
        self._seed_login()
        cat = self._get_or_create_category()
        org_b, _ = Organization.objects.get_or_create(
            slug='e2e-org-b',
            defaults={'name': 'E2E Org B', 'category': cat},
        )
        User.objects.filter(email='e2e_user_b@example.com').delete()
        User.objects.create_user(
            email='e2e_user_b@example.com',
            user_id='e2e_user_b',
            password=self.e2e_password,
            organization=org_b,
            role='admin',  # org_b admin として /subject-management にアクセスし、org_a データが見えないことを検証
        )
        self._seed_verification_accounts(cat)
        from problems.models import Subject
        org_a = Organization.objects.get(slug='e2e-org-a')
        Subject.objects.get_or_create(
            name='E2E Subject A',
            organization=org_a,
            defaults={'slug': 'e2e-subject-a'},
        )

    def _seed_verification_accounts(self, cat):
        """確かめ用の運営と本人ひとりの組織の管理者（I636。I620 の test-gate で手で作ったもの）

        運営は専用の組織に置き、組織 A・B のメンバーの一覧と件数に混ぜない。運営の権限は is_staff で決まる。
        本人ひとりの組織は固定の slug にして、何度流しても組織を増やさない
        """
        org_staff, _ = Organization.objects.get_or_create(
            slug='e2e-org-staff',
            defaults={'name': 'E2E Org Staff', 'category': cat},
        )
        User.objects.filter(email='e2e_staff@example.com').delete()
        User.objects.create_user(
            email='e2e_staff@example.com',
            user_id='e2e_staff',
            password=self.e2e_password,
            organization=org_staff,
            role='user',
            is_staff=True,
        )
        org_solo, _ = Organization.objects.get_or_create(
            slug='e2e-org-solo',
            defaults={'name': 'e2e_soloさんの学習', 'category': cat,
                      'type': Organization.TYPE_PERSONAL, 'is_individual': True},
        )
        User.objects.filter(email='e2e_solo@example.com').delete()
        User.objects.create_user(
            email='e2e_solo@example.com',
            user_id='e2e_solo',
            password=self.e2e_password,
            organization=org_solo,
            role='admin',
        )

    def _seed_quiz_session(self):
        self._seed_login()
        from problems.models import Subject, Problem, Choice, UserSubjectAccess
        org_a = Organization.objects.get(slug='e2e-org-a')
        user_a = User.objects.get(email='e2e_user_a@example.com')

        subj, _ = Subject.objects.get_or_create(
            name='E2E Quiz Subject',
            organization=org_a,
            defaults={'slug': 'e2e-quiz-subject'},
        )
        problem, _ = Problem.objects.get_or_create(
            subject=subj,
            question='E2E テスト用の問題文です。',
            defaults={
                'problem_type': 'single',
                'difficulty': 1,
                'explanation': 'E2E テスト用の解説文です。',
                'organization': org_a,
                'created_by': user_a,
            },
        )
        # 選択肢を作成（選択問題には最低1件の正解選択肢が必要）
        Choice.objects.get_or_create(
            problem=problem,
            text='正解の選択肢',
            defaults={'is_correct': True, 'order': 0},
        )
        Choice.objects.get_or_create(
            problem=problem,
            text='不正解の選択肢',
            defaults={'is_correct': False, 'order': 1},
        )
        # E2E Subject A も idempotent に確保（tenant_isolation 由来だが累積実行で存在する）
        subj_a, _ = Subject.objects.get_or_create(
            name='E2E Subject A',
            organization=org_a,
            defaults={'slug': 'e2e-subject-a'},
        )
        # UserSubjectAccess: /api/user/subjects/ は UserSubjectAccess を参照するため、
        # 登録なしでは空配列が返り Dashboard でダイアログが表示されない。
        # user_a が両科目にアクセスできるよう登録し、subjects.length >= 2 を保証する。
        UserSubjectAccess.objects.get_or_create(
            user=user_a, subject=subj, defaults={'granted_by': None}
        )
        UserSubjectAccess.objects.get_or_create(
            user=user_a, subject=subj_a, defaults={'granted_by': None}
        )
