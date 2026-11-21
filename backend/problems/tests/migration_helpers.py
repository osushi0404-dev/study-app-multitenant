"""
マイグレーションを本物で流すテストの補助（I602）

使っているテスト: studylogs/tests/test_I492_remove_legacy_study_logs.py・
problems/tests/test_I587_media_migration.py・problems/tests/test_I590_review_leftovers.py

pytest は --no-migrations で、テストの DB は今のモデルから作られる。本物のマイグレーションを
apply／unapply して確かめるときは、ここの関数を使う（写しを作らない）。
ファイル名が test_ で始まらないので、pytest はこのファイルをテストとして集めない。
"""
from django.db import connection
from django.db.migrations.loader import MigrationLoader


def load_migrations(settings) -> MigrationLoader:
    """pytest の --no-migrations を外し、本物のマイグレーションを読む"""
    settings.MIGRATION_MODULES = {}
    return MigrationLoader(connection)


def run_migration(step, state):
    """遅延の外部キーの検査を済ませてから DDL を流す（残っていると ALTER TABLE が失敗する）

    step は migration.apply か migration.unapply。state は流す前の ProjectState（写しは中で作るので、そのまま渡す）。
    """
    with connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    with connection.schema_editor() as editor:
        step(state.clone(), editor)


def table_names() -> set:
    with connection.cursor() as cursor:
        return set(connection.introspection.table_names(cursor))


def column_names(table) -> set:
    with connection.cursor() as cursor:
        return {c.name for c in connection.introspection.get_table_description(cursor, table)}
