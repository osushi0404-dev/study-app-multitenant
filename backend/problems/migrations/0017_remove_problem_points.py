from django.db import migrations


class Migration(migrations.Migration):
    """
    problems_problem.points カラムを削除する。

    points は 0001_initial.py で IntegerField(default=10, NOT NULL) として作成されたが、
    その後 models.py から削除されたにもかかわらず DROP 用マイグレーションが存在しなかった。
    既存 DB では値が入っているため発現しないが、fresh DB（CI）では Django ORM の INSERT に
    points が含まれず NOT NULL 違反が発生する。

    データ安全性根拠:
    - points は現在の models.py に定義がなく ORM 経由で読み書き不可
    - raw SQL での参照もなし
    - 既存データの損失はアクセス不能なデータのみ（実質ゼロ）
    """

    dependencies = [
        ('problems', '0016_problem_is_deleted'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='problem',
            name='points',
        ),
    ]
