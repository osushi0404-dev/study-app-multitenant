from django.core.management.base import BaseCommand
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
        )
        from problems.models import Subject
        org_a = Organization.objects.get(slug='e2e-org-a')
        Subject.objects.get_or_create(
            name='E2E Subject A',
            organization=org_a,
            defaults={'slug': 'e2e-subject-a'},
        )

    def _seed_quiz_session(self):
        self._seed_login()
        from problems.models import Subject, Problem, Choice
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
