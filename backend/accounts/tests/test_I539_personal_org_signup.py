"""
I539: 招待なしの会員登録を完了できるようにする（利用者ごとの個人用の組織）。

- 組織を指定しない登録は、その人だけの組織（is_individual=True）を作り、その人を管理者にする
- 招待で引き当てる組織から、本人ひとりの組織と共有の personal 組織を外す
- 科目 0 件の組織への招待登録は科目なしで通す
- 本人ひとりの組織で作った科目は、作った人の学ぶ科目に入る
- データマイグレーション 0023 は共有の personal 組織の一般の利用者を一人ずつ移す

TC-01〜TC-16・TC-23（docs/tests/open/I539_auto_test.md）に対応。
"""
import importlib
import re

import pytest
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory
from accounts.serializers import UserRegistrationSerializer
from accounts.services import pick_unused_slug
from problems.models import Problem, Subject, UserSubjectAccess

User = get_user_model()

# 個人用の組織の slug の形（accounts.services と 0023 の両方の規則をこの 1 つで確かめる）
PERSONAL_SLUG_RE = re.compile(r'^p-[0-9a-f]{12}$')
PASSWORD = "I539TestPass123!"  # pragma: allowlist secret（テスト用ダミー値）
ORG_SETUP_FAILED = {
    'error': {
        'main_message': '組織の設定に失敗しました',
        'sub_message': '無効な組織URLまたはシステムエラー',
    }
}
MIGRATION = importlib.import_module('accounts.migrations.0023_move_shared_personal_users')


@pytest.fixture(autouse=True)
def _settings(settings, tmp_path):
    settings.RATELIMIT_ENABLE = False
    settings.API_THROTTLE_ENABLED = False
    settings.MEDIA_ROOT = str(tmp_path)  # 科目の作成が作る画像の置き場所をテストの外に出さない


@pytest.fixture
def personal_category(db):
    return OrganizationCategory.objects.create(name='個人利用', slug=OrganizationCategory.PERSONAL_SLUG)


@pytest.fixture
def edu_category(db):
    return OrganizationCategory.objects.create(name='教育I539', slug='edu-i539')


@pytest.fixture
def school(edu_category):
    return Organization.objects.create(
        name='学校I539', slug='school-i539', type='school', category=edu_category)


@pytest.fixture
def school_subject(school):
    return Subject.objects.create(name='学校の科目I539', slug='school-subj-i539', organization=school)


def _payload(user_id, **extra):
    body = {
        'user_id': user_id,
        'email': f'{user_id}@example.com',
        'password': PASSWORD,
        'password_confirm': PASSWORD,
    }
    body.update(extra)
    return body


def _register(user_id, slug=None, **extra):
    path = f'/api/auth/register/{slug}/' if slug else '/api/auth/register/'
    return APIClient().post(path, _payload(user_id, **extra), format='json')


def _client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ---- TC-01 / TC-01b: slug なしの登録で、本人だけの組織と管理者 ----
@pytest.mark.django_db
@pytest.mark.parametrize('extra', [{}, {'subject_ids': []}])
def test_register_without_slug_creates_individual_org(personal_category, extra):
    resp = _register('i539_a', **extra)

    assert resp.status_code == status.HTTP_201_CREATED, resp.content
    assert resp.json()['organization'] == 'i539_aさんの学習'
    user = User.objects.get(user_id='i539_a')
    org = user.organization
    assert user.role == 'admin'
    assert org.type == 'personal'
    assert org.is_individual is True
    assert org.is_active is True
    assert org.name == 'i539_aさんの学習'
    assert PERSONAL_SLUG_RE.match(org.slug)
    assert org.category.slug == 'personal'
    assert UserSubjectAccess.objects.filter(user=user).count() == 0


# ---- TC-02: 2 人は別の組織・slug の重なりを避ける ----
@pytest.mark.django_db
def test_two_registrations_get_different_orgs(personal_category):
    assert _register('i539_b1').status_code == status.HTTP_201_CREATED
    assert _register('i539_b2').status_code == status.HTTP_201_CREATED
    org1 = User.objects.get(user_id='i539_b1').organization
    org2 = User.objects.get(user_id='i539_b2').organization
    assert org1.id != org2.id
    assert org1.slug != org2.slug


@pytest.mark.django_db
def test_pick_unused_slug_skips_taken(personal_category):
    Organization.objects.create(
        name='既存', slug='p-aaaaaaaaaaaa', type='school', category=personal_category)
    assert pick_unused_slug(['p-aaaaaaaaaaaa', 'p-bbbbbbbbbbbb']) == 'p-bbbbbbbbbbbb'


# ---- TC-03: slug なしで科目の番号を送ると、他組織・存在しないの区別なく 400 ----
@pytest.mark.django_db
def test_register_without_slug_rejects_subject_ids(personal_category, school_subject):
    users_before, orgs_before = User.objects.count(), Organization.objects.count()
    foreign = _register('i539_c1', subject_ids=[school_subject.id])
    missing = _register('i539_c2', subject_ids=[4539999])

    for resp in (foreign, missing):
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        body = resp.json()
        assert body['error']['main_message'] == '入力内容にエラーがあります'
        assert body['error']['details']['subject_ids'] == ['選択された科目の一部が無効です']
    assert foreign.json() == missing.json()
    assert User.objects.count() == users_before
    assert Organization.objects.count() == orgs_before


# ---- TC-04: 検証の失敗で、作りかけの組織が残らない ----
@pytest.mark.django_db
def test_failed_registration_leaves_no_org(personal_category):
    assert _register('i539_dup').status_code == status.HTTP_201_CREATED
    orgs_before = Organization.objects.count()

    resp = APIClient().post(
        '/api/auth/register/',
        _payload('i539_dup', email='other_i539@example.com'), format='json')

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json()['error']['details']['user_id'] == ['このユーザーIDは既に使用されています']
    assert Organization.objects.count() == orgs_before


# ---- TC-05: 本人の情報に組織名と管理者が出る ----
@pytest.mark.django_db
def test_me_shows_individual_org(personal_category):
    _register('i539_me')
    user = User.objects.get(user_id='i539_me')
    data = _client_for(user).get('/api/auth/me/').json()
    assert data['organization_name'] == 'i539_meさんの学習'
    assert data['role'] == 'admin'


# ---- TC-06: 本文の organization_id で他の組織に入れない ----
@pytest.mark.django_db
def test_register_ignores_organization_id_in_body(personal_category, school):
    school_users_before = school.users.count()
    resp = _register('i539_f', organization_id=school.id)

    assert resp.status_code == status.HTTP_201_CREATED
    user = User.objects.get(user_id='i539_f')
    assert user.organization_id != school.id
    assert user.organization.is_individual is True
    assert school.users.count() == school_users_before


# ---- TC-07: 本人ひとりの組織と共有の personal 組織は招待で引き当てない ----
@pytest.mark.django_db
def test_individual_and_shared_orgs_are_not_invitable(personal_category):
    _register('i539_owner')
    individual = User.objects.get(user_id='i539_owner').organization
    Subject.objects.create(name='個人の科目I539', slug='ind-subj-i539', organization=individual)
    shared = Organization.objects.create(
        name='個人利用', slug='personal', type='personal', category=personal_category)

    for org in (individual, shared):
        users_before = org.users.count()
        reg = _register(f'i539_g_{org.id}', slug=org.slug)
        assert reg.status_code == status.HTTP_400_BAD_REQUEST
        assert reg.json() == ORG_SETUP_FAILED
        assert org.users.count() == users_before

        check = APIClient().get(f'/api/organizations/validate-slug/{org.slug}/')
        assert check.status_code == status.HTTP_404_NOT_FOUND
        assert check.json() == {'valid': False, 'message': f'組織 "{org.slug}" は見つかりません'}

        for route in ('/api/organizations/subjects/public/', '/api/subjects/public/'):
            listed = APIClient().get(f'{route}?slug={org.slug}')
            assert listed.status_code == status.HTTP_200_OK
            assert listed.json() == []


# ---- TC-07b: 種類が既定の personal のままの招待用の組織は、今のまま招待できる ----
@pytest.mark.django_db
def test_default_type_invite_org_stays_invitable(edu_category):
    org = Organization.objects.create(name='E2E風I539', slug='e2e-like-i539', category=edu_category)
    assert org.type == 'personal' and org.is_individual is False
    subject = Subject.objects.create(name='E2E風の科目', slug='e2e-like-subj', organization=org)

    reg = _register('i539_h', slug=org.slug, subject_ids=[subject.id])
    assert reg.status_code == status.HTTP_201_CREATED, reg.content
    user = User.objects.get(user_id='i539_h')
    assert user.role == 'user'
    assert user.organization_id == org.id

    check = APIClient().get(f'/api/organizations/validate-slug/{org.slug}/')
    assert check.status_code == status.HTTP_200_OK
    assert check.json()['valid'] is True
    listed = APIClient().get(f'/api/organizations/subjects/public/?slug={org.slug}')
    assert len(listed.json()) == 1


# ---- TC-08: 科目 0 件の招待用の組織は科目なしで登録できる ----
@pytest.mark.django_db
def test_invite_to_org_without_subjects(school):
    orgs_before = Organization.objects.count()
    resp = _register('i539_i', slug=school.slug)

    assert resp.status_code == status.HTTP_201_CREATED, resp.content
    user = User.objects.get(user_id='i539_i')
    assert user.role == 'user'
    assert user.organization_id == school.id
    assert UserSubjectAccess.objects.filter(user=user).count() == 0
    assert Organization.objects.count() == orgs_before


# ---- TC-09: 科目のある招待用の組織は、科目を選ばないと 400（回帰） ----
@pytest.mark.django_db
@pytest.mark.parametrize('extra', [{}, {'subject_ids': []}])
def test_invite_with_subjects_requires_selection(school, school_subject, extra):
    users_before = User.objects.count()
    resp = _register('i539_j', slug=school.slug, **extra)

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json()['error']['details']['subject_ids'] == ['科目を最低1つ選択してください']
    assert User.objects.count() == users_before


# ---- TC-10: 科目のある招待用の組織で選べば今のまま登録できる（回帰） ----
@pytest.mark.django_db
def test_invite_with_selected_subject(school, school_subject):
    resp = _register('i539_k', slug=school.slug, subject_ids=[school_subject.id])

    assert resp.status_code == status.HTTP_201_CREATED
    user = User.objects.get(user_id='i539_k')
    assert user.role == 'user'
    assert user.organization_id == school.id
    assert UserSubjectAccess.objects.filter(user=user, subject=school_subject).count() == 1


# ---- TC-11: 本人ひとりの組織で作った科目は、作った人の学ぶ科目に入る ----
@pytest.mark.django_db
def test_subject_created_in_individual_org_is_selected(personal_category):
    _register('i539_l')
    user = User.objects.get(user_id='i539_l')
    client = _client_for(user)

    resp = client.post('/api/subjects/', {'name': '科目I539', 'description': ''}, format='json')

    assert resp.status_code == status.HTTP_201_CREATED, resp.content
    subject = Subject.objects.get(name='科目I539', organization=user.organization)
    access = UserSubjectAccess.objects.get(user=user, subject=subject)
    assert access.granted_by_id == user.id
    names = [s['name'] for s in client.get('/api/user/subjects/').json()]
    assert '科目I539' in names


# ---- TC-12: 学校・種類が既定の招待用の組織では、学ぶ科目は増えない ----
@pytest.mark.django_db
def test_subject_created_in_shared_orgs_is_not_selected(school, edu_category):
    default_type_org = Organization.objects.create(
        name='既定の種類I539', slug='default-type-i539', category=edu_category)
    for org in (school, default_type_org):
        admin = User.objects.create_user(
            email=f'admin_{org.id}@example.com', user_id=f'i539_adm_{org.id}',
            password=PASSWORD, organization=org, role='admin')
        resp = _client_for(admin).post(
            '/api/subjects/', {'name': f'管理者の科目{org.id}', 'description': ''}, format='json')
        assert resp.status_code == status.HTTP_201_CREATED, resp.content
        assert UserSubjectAccess.objects.filter(user=admin).count() == 0


# ---- TC-13: 別の個人用の組織の科目・問題は見えない ----
@pytest.mark.django_db
def test_individual_admins_are_isolated(personal_category):
    _register('i539_ma')
    _register('i539_mb')
    user_a = User.objects.get(user_id='i539_ma')
    user_b = User.objects.get(user_id='i539_mb')
    subject_b = Subject.objects.create(name='Bの科目', slug='b-subj-i539', organization=user_b.organization)
    problem_b = Problem.objects.create(
        subject=subject_b, organization=user_b.organization, created_by=user_b,
        question='Bの問題', explanation='Bの解説')

    client_a = _client_for(user_a)
    assert client_a.post('/api/subjects/', {'name': 'Aの科目', 'description': ''},
                         format='json').status_code == status.HTTP_201_CREATED

    def names(resp):
        data = resp.json()
        items = data['results'] if isinstance(data, dict) else data
        return {item.get('name') or item.get('question') for item in items}

    assert 'Bの科目' not in names(client_a.get('/api/subjects/'))
    assert 'Bの科目' not in names(client_a.get('/api/user/subjects/available/'))
    assert 'Bの問題' not in names(client_a.get('/api/problems/'))
    assert client_a.get(f'/api/problems/{problem_b.id}/').status_code == status.HTTP_404_NOT_FOUND
    assert names(client_a.get('/api/user/subjects/')) == {'Aの科目'}


# ---- TC-23: context の渡し忘れ・両方の指定は止める（fail-closed） ----
@pytest.mark.django_db
@pytest.mark.parametrize('both', [False, True])
def test_serializer_requires_exactly_one_mode(personal_category, school, both):
    context = {'organization': school, 'personal_category': personal_category} if both else {}
    users_before, orgs_before = User.objects.count(), Organization.objects.count()
    serializer = UserRegistrationSerializer(data=_payload('i539_ctx'), context=context)
    with pytest.raises(ImproperlyConfigured):
        serializer.is_valid()
    assert User.objects.count() == users_before
    assert Organization.objects.count() == orgs_before


# ---------------------------------------------------- データマイグレーション ----
def _shared_org(category):
    return Organization.objects.create(
        name='個人利用', slug='personal', type='personal', category=category)


def _user_in(org, user_id, **extra):
    return User.objects.create_user(
        email=f'{user_id}@example.com', user_id=user_id, password=PASSWORD,
        organization=org, **extra)


def _snapshot():
    return (Organization.objects.count(),
            sorted(User.objects.values_list('user_id', 'organization_id', 'role')))


# ---- TC-14: 一般の利用者だけを一人ずつ移し、運営用のアカウントは動かさない ----
@pytest.mark.django_db
def test_migration_moves_general_users_only(personal_category):
    shared = _shared_org(personal_category)
    _user_in(shared, 'i539_m1', role='user')
    _user_in(shared, 'i539_m2', role='user')
    _user_in(shared, 'i539_staff', role='user', is_staff=True)
    _user_in(shared, 'i539_su', role='user', is_superuser=True)

    MIGRATION.move_shared_personal_users(django_apps, None)

    moved = [User.objects.get(user_id=uid) for uid in ('i539_m1', 'i539_m2')]
    assert moved[0].organization_id != moved[1].organization_id
    for user in moved:
        org = user.organization
        assert user.role == 'admin'
        assert org.type == 'personal'
        assert org.is_individual is True
        assert org.name == f'{user.user_id}さんの学習'
        assert PERSONAL_SLUG_RE.match(org.slug)
        assert org.category.slug == 'personal'
    for uid in ('i539_staff', 'i539_su'):
        kept = User.objects.get(user_id=uid)
        assert kept.organization_id == shared.id
        assert kept.role == 'user'
    assert not User.objects.filter(
        organization=shared, is_staff=False, is_superuser=False).exists()


# ---- TC-15: 2 回目は何も変えない ----
@pytest.mark.django_db
def test_migration_is_idempotent(personal_category):
    shared = _shared_org(personal_category)
    _user_in(shared, 'i539_n1', role='user')
    _user_in(shared, 'i539_staff2', role='user', is_staff=True)

    MIGRATION.move_shared_personal_users(django_apps, None)
    after_first = _snapshot()
    MIGRATION.move_shared_personal_users(django_apps, None)

    assert _snapshot() == after_first


# ---- TC-16: 対象がいなければ何もしない・カテゴリが無いのに対象がいれば止める ----
@pytest.mark.django_db
def test_migration_noop_cases(edu_category):
    before = _snapshot()
    MIGRATION.move_shared_personal_users(django_apps, None)  # 共有の組織が無い
    assert _snapshot() == before

    shared = Organization.objects.create(
        name='個人利用', slug='personal', type='personal', category=edu_category)
    _user_in(shared, 'i539_staff3', role='user', is_staff=True)
    before = _snapshot()
    MIGRATION.move_shared_personal_users(django_apps, None)  # 運営だけ・カテゴリも無い
    assert _snapshot() == before

    _user_in(shared, 'i539_o1', role='user')
    before = _snapshot()
    with pytest.raises(RuntimeError):
        MIGRATION.move_shared_personal_users(django_apps, None)  # カテゴリが無いのに対象がいる
    assert _snapshot() == before
