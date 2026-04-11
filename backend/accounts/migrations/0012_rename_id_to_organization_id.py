# Generated manually to rename Organization id to organization_id

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_allow_duplicate_slug'),
    ]

    operations = [
        # 1. 外部キー制約を一時的に削除
        migrations.RunSQL(
            "ALTER TABLE users DROP CONSTRAINT users_organization_id_abe5d649_fk_organizations_id;",
            reverse_sql="ALTER TABLE users ADD CONSTRAINT users_organization_id_abe5d649_fk_organizations_id FOREIGN KEY (organization_id) REFERENCES organizations (id);"
        ),

        # 2. organizationsテーブルのidカラムをorganization_idにリネーム
        migrations.RunSQL(
            "ALTER TABLE organizations RENAME COLUMN id TO organization_id;",
            reverse_sql="ALTER TABLE organizations RENAME COLUMN organization_id TO id;"
        ),

        # 3. シーケンスもリネーム
        migrations.RunSQL(
            "ALTER SEQUENCE organizations_id_seq RENAME TO organizations_organization_id_seq;",
            reverse_sql="ALTER SEQUENCE organizations_organization_id_seq RENAME TO organizations_id_seq;"
        ),

        # 4. 外部キー制約を再作成（新しいカラム名で）
        migrations.RunSQL(
            "ALTER TABLE users ADD CONSTRAINT users_organization_id_fk_organizations_organization_id FOREIGN KEY (organization_id) REFERENCES organizations (organization_id);",
            reverse_sql="ALTER TABLE users DROP CONSTRAINT users_organization_id_fk_organizations_organization_id;"
        ),
    ]
