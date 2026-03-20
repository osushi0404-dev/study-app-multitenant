# Generated manually for Issue #028: Consolidate 2 columns into 1

from django.db import migrations, models


def migrate_image_directories_forward(apps, schema_editor):
    """2カラムから1カラムへデータ移行"""
    Subject = apps.get_model('problems', 'Subject')

    for subject in Subject.objects.all():
        if subject.question_image_directory:
            # 'problems/aws-clf/questions' → 'problems/aws-clf'
            base_path = subject.question_image_directory.replace('/questions', '')
            subject.image_directory = base_path
            subject.save(update_fields=['image_directory'])
        elif subject.explanation_image_directory:
            # 念のため explanation_image_directory もチェック
            base_path = subject.explanation_image_directory.replace('/explanations', '')
            subject.image_directory = base_path
            subject.save(update_fields=['image_directory'])


def migrate_image_directories_reverse(apps, schema_editor):
    """ロールバック用: 1カラムから2カラムへ"""
    Subject = apps.get_model('problems', 'Subject')

    for subject in Subject.objects.all():
        if subject.image_directory:
            subject.question_image_directory = f'{subject.image_directory}/questions'
            subject.explanation_image_directory = f'{subject.image_directory}/explanations'
            subject.save(update_fields=['question_image_directory', 'explanation_image_directory'])


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0009_optimize_image_path_management'),
    ]

    operations = [
        # 1. 新カラム追加
        migrations.AddField(
            model_name='subject',
            name='image_directory',
            field=models.CharField(
                blank=True,
                default='',
                help_text='科目の画像ベースディレクトリ（例: problems/aws-clf）。空の場合は科目名から自動生成。',
                max_length=200,
                verbose_name='画像ディレクトリ'
            ),
        ),

        # 2. データ移行
        migrations.RunPython(migrate_image_directories_forward, migrate_image_directories_reverse),

        # 3. 旧カラム削除
        migrations.RemoveField(
            model_name='subject',
            name='question_image_directory',
        ),
        migrations.RemoveField(
            model_name='subject',
            name='explanation_image_directory',
        ),
    ]
