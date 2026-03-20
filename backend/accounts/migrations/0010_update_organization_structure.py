# Generated manually to update organization structure

from django.db import migrations, models
import django.db.models.deletion


def migrate_organization_data(apps, schema_editor):
    """既存のOrganizationデータを新しい構成に移行"""
    pass  # データは手動で復元する


def reverse_migrate_organization_data(apps, schema_editor):
    """逆マイグレーション用"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_organization_user_users_organiz_ca9165_idx_and_more'),
    ]

    operations = [
        # 1. UserモデルからOrganizationへの外部キー参照を削除
        migrations.RemoveIndex(
            model_name='user',
            name='users_organiz_ca9165_idx',
        ),
        migrations.RemoveField(
            model_name='user',
            name='organization',
        ),
        
        # 2. 既存のOrganizationテーブルを削除
        migrations.DeleteModel(
            name='Organization',
        ),
        
        # 3. 新しい構成でOrganizationテーブルを作成
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100, verbose_name='組織名')),
                ('slug', models.SlugField(help_text='URL用の識別子（半角英数字とハイフンのみ）', unique=True, verbose_name='URL識別子')),
                ('type', models.CharField(choices=[('school', 'School'), ('corporate', 'Corporate'), ('personal', 'Personal')], default='personal', max_length=20, verbose_name='組織タイプ')),
                ('is_active', models.BooleanField(default=True, verbose_name='有効')),
            ],
            options={
                'verbose_name': '組織',
                'verbose_name_plural': '組織',
                'db_table': 'organizations',
            },
        ),
        
        # 4. インデックスを追加
        migrations.AddIndex(
            model_name='organization',
            index=models.Index(fields=['slug'], name='organizatio_slug_idx'),
        ),
        
        # 5. UserモデルにOrganizationへの外部キー参照を再追加
        migrations.AddField(
            model_name='user',
            name='organization',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='users', to='accounts.organization', verbose_name='所属組織'),
        ),
        
        # 6. Userモデルのインデックスを再追加
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['organization'], name='users_organiz_idx'),
        ),
        
        # 7. データ移行（実際のデータ復元は手動で行う）
        migrations.RunPython(migrate_organization_data, reverse_migrate_organization_data),
    ]