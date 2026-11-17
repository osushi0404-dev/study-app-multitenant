"""
I539: 共有の personal 組織（type='personal'・slug 'personal'）に残る一般の利用者を、
一人ずつ本人ひとりの組織（is_individual=True）に移し、その人を管理者にする。

- 運営用のアカウント（is_staff・is_superuser）は移さず、role も変えない
- 対象は「今、共有の組織にいる一般の利用者」なので、2 回目は何もしない
- 過去のモデルだけを使い、accounts.services は読み込まない（名前・slug の決まりはここに書く。
  後でサービスが変わってもこのマイグレーションの意味が変わらないように）
- 逆向きは何もしない（移した利用者の作った科目・問題を消さないため・plan_I539 の 7）
"""
import secrets

from django.db import migrations, transaction

SHARED_SLUG = 'personal'
PERSONAL_TYPE = 'personal'
PERSONAL_CATEGORY_SLUG = 'personal'


def _display_id(user):
    if user.user_id:
        return user.user_id
    if user.email:
        return user.email.split('@', 1)[0]
    return str(user.pk)[:8]


def _unused_slug(Organization):
    while True:
        slug = 'p-' + secrets.token_hex(6)
        if not Organization.objects.filter(slug=slug).exists():
            return slug


def move_shared_personal_users(apps, schema_editor):
    Organization = apps.get_model('accounts', 'Organization')
    OrganizationCategory = apps.get_model('accounts', 'OrganizationCategory')
    User = apps.get_model('accounts', 'User')

    shared = Organization.objects.filter(type=PERSONAL_TYPE, slug=SHARED_SLUG)
    targets = list(User.objects.filter(
        organization__in=shared, is_staff=False, is_superuser=False).order_by('created_at'))
    if not targets:
        return

    category = OrganizationCategory.objects.filter(slug=PERSONAL_CATEGORY_SLUG).first()
    if category is None:
        raise RuntimeError(
            "「個人利用」カテゴリ（slug='personal'）がありません。共有の personal 組織の利用者を移せません")

    for user in targets:
        with transaction.atomic():
            org = Organization.objects.create(
                name=f'{_display_id(user)}さんの学習',
                slug=_unused_slug(Organization),
                type=PERSONAL_TYPE,
                is_individual=True,
                category=category,
                is_active=True,
            )
            user.organization = org
            user.role = 'admin'
            user.save(update_fields=['organization', 'role'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0022_organization_is_individual'),
    ]

    operations = [
        migrations.RunPython(move_shared_personal_users, reverse_code=migrations.RunPython.noop),
    ]
