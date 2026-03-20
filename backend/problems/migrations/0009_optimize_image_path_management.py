# Generated manually for Issue #028: Optimize image path management

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0008_add_problem_images'),
    ]

    operations = [
        # 1. Subjectモデルに画像ディレクトリ管理フィールドを追加
        migrations.AddField(
            model_name='subject',
            name='question_image_directory',
            field=models.CharField(
                blank=True,
                default='',
                help_text='問題画像のディレクトリパス（例: problems/questions/aws-saa）。空の場合は科目名から自動生成。',
                max_length=200,
                verbose_name='問題画像ディレクトリ'
            ),
        ),
        migrations.AddField(
            model_name='subject',
            name='explanation_image_directory',
            field=models.CharField(
                blank=True,
                default='',
                help_text='解説画像のディレクトリパス（例: problems/explanations/aws-saa）。空の場合は科目名から自動生成。',
                max_length=200,
                verbose_name='解説画像ディレクトリ'
            ),
        ),

        # 2. ProblemモデルのImageFieldをCharFieldに変更
        migrations.AlterField(
            model_name='problem',
            name='question_image',
            field=models.CharField(
                blank=True,
                help_text='問題文に添付する画像のファイル名（例: diagram_01.png）',
                max_length=255,
                null=True,
                verbose_name='問題画像ファイル名'
            ),
        ),
        migrations.AlterField(
            model_name='problem',
            name='explanation_image',
            field=models.CharField(
                blank=True,
                help_text='解説に添付する画像のファイル名（例: explanation_01.png）',
                max_length=255,
                null=True,
                verbose_name='解説画像ファイル名'
            ),
        ),
    ]
