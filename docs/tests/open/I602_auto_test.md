# I602 自動テスト: I590 のレビューの残り（テストの守りの抜け・0027 の戻し方・補助の集約）

実行コマンド（例）: `docker compose exec -T backend python -m pytest problems/tests/test_I590_review_leftovers.py problems/tests/test_I587_media_migration.py studylogs/tests/test_I492_remove_legacy_study_logs.py`（正は CI の backend の pytest）

結果:
- backend: 実装前のため未実行
- frontend: 変更なし

| TC | 対象 | 手順 | 期待値 | 結果 |
|---|---|---|---|---|
| TC-01 | 配信の見出しの全項目（4-(1)） | `test_media_security_headers_on_all_statuses`（200・304・412）と `test_missing_security_headers_detects_each_header`（`MEDIA_SECURITY_HEADERS` の各見出しで parametrize） | 3 つの状態コード（200・304・412）で `missing_security_headers(response) == []`・`Cache-Control == "private, max-age=3600"`。失敗の注入: 全部を付けた `HttpResponse` から 1 つ消すと `[その見出し]`・値を `"x"` に変えると `[その見出し]`・全部そろうと `[]`（`Content-Disposition` を含む 3 件すべて） | 実装前のため未実行 |
| TC-02 | 相対の読み込みも数える（4-(2)） | `test_media_migration_imports_no_app_module` | `app_imports(media_migration.py の中身) == []`。失敗の注入: `"from problems.utils import detect_mime\nimport os\n"` → `["problems.utils"]`・`"from .utils import x\n"` → `[".utils"]`・`"from . import utils\n"` → `[".utils"]` | 実装前のため未実行 |
| TC-03 | 補助の写しが 3 つのテストに無い（4-(3)） | 下の「決定論ゲート」の 9 行 | 9 行とも exit 0。失敗の注入: 実装前の 3 ファイル（写しがある）で 9 行とも exit 1 になることを 2026-11-20 に確かめた | 失敗の注入済み（実装前は 9 行とも exit 1）・実装後は未実行 |
| TC-04 | 3 つのテストが変わらず通る（4-(1)〜(4)） | CI の backend の pytest | `test_I590_review_leftovers.py`・`test_I587_media_migration.py`・`test_I492_remove_legacy_study_logs.py` の全テストが passed（失敗・エラー 0） | 実装前のため未実行 |
| TC-05 | 手順書の空にする SQL で 0027 が通る（4-(4)） | `test_0027_refuses_values_then_removes_column`（値 `"problems/x"`・`" "`） | 値がある間は `RuntimeError`（「1 件」）で止まり列が残る。`CLEAR_IMAGE_DIRECTORY_SQL` を流した後の apply で `image_directory` の列が無くなる | 実装前のため未実行 |

## 決定論ゲート（自動実走）
```bash
! grep -q "MIGRATION_MODULES" backend/problems/tests/test_I590_review_leftovers.py
! grep -q "SET CONSTRAINTS ALL IMMEDIATE" backend/problems/tests/test_I590_review_leftovers.py
! grep -q "get_table_description" backend/problems/tests/test_I590_review_leftovers.py
! grep -q "MIGRATION_MODULES" backend/problems/tests/test_I587_media_migration.py
! grep -q "SET CONSTRAINTS ALL IMMEDIATE" backend/problems/tests/test_I587_media_migration.py
! grep -q "get_table_description" backend/problems/tests/test_I587_media_migration.py
! grep -q "MIGRATION_MODULES" backend/studylogs/tests/test_I492_remove_legacy_study_logs.py
! grep -q "SET CONSTRAINTS ALL IMMEDIATE" backend/studylogs/tests/test_I492_remove_legacy_study_logs.py
! grep -q "get_table_description" backend/studylogs/tests/test_I492_remove_legacy_study_logs.py
```
