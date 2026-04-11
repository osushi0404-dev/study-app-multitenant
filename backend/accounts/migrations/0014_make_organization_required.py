# Generated manually to make organization field required
from django.db import migrations, models
import django.db.models.deletion


def set_default_organization(apps, schema_editor):
    """既存のNULLレコードにデフォルト組織を設定"""
    from django.db import connection

    with connection.cursor() as cursor:
        # personal組織を取得
        cursor.execute("SELECT organization_id FROM organizations WHERE type = 'personal' AND is_active = true LIMIT 1")
        result = cursor.fetchone()

        if result:
            personal_org_id = result[0]
        else:
            # personal組織が存在しない場合は作成
            cursor.execute(
                "INSERT INTO organizations (name, slug, type, is_active, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, NOW(), NOW()) RETURNING organization_id",
                ['個人利用', 'personal', 'personal', True]
            )
            personal_org_id = cursor.fetchone()[0]
            print(f"Created personal organization with id: {personal_org_id}")

        # organization_idがNULLのユーザーを更新
        cursor.execute("SELECT COUNT(*) FROM users WHERE organization_id IS NULL")
        null_count = cursor.fetchone()[0]

        if null_count > 0:
            print(f"Updating {null_count} users with null organization_id")
            cursor.execute(
                "UPDATE users SET organization_id = %s WHERE organization_id IS NULL",
                [personal_org_id]
            )
            print(f"Updated {null_count} users with organization_id = {personal_org_id}")


def reverse_set_default_organization(apps, schema_editor):
    """ロールバック時の処理（何もしない）"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_auto_20250908_0132'),
    ]

    operations = [
        # Step 1: 既存のNULLデータを修正
        migrations.RunPython(
            set_default_organization,
            reverse_set_default_organization
        ),

        # Step 2: organization フィールドを必須に変更（外部キーは既存のまま）
        # 注: 実際のNOT NULL制約は既存データの更新後に別途追加する
    ]
