# I459 自動テスト: 学習統計の画面が、解いた問題が 0 件の日があると 500 になる不具合を直す（dashboard/analytics）

- 関連: docs/issues/open/I459.md / docs/plans/open/plan_I459.md / GitHub #459 / Draft PR #478
- 対象: `backend/dashboard/tests/test_I459_analytics_zero_division.py`（新規）・`backend/core/tests/test_I446_cross_api_tenant_isolation.py`（下準備の変更）と、守りにする既存のテスト
- 実行場所: app-1 ワークツリーのコンテナ（`docker compose exec -T backend ...`）。全テストは CI（PR #478）が正。手元では下の TC のファイルだけを流す
- 合否は終了コード（合格=0・不合格=非ゼロ）。回帰を止める TC は、直す前のコード（Red）または失敗の注入（FG）で非ゼロになることを確かめる
- 下の表の `PYT` は `docker compose exec -T backend python -m pytest dashboard/tests/test_I459_analytics_zero_division.py -q` の略
- 日付は `timezone.now().date()`（ビューと同じ）を `today` とする。下準備の利用者は `user_id="u_i459"`（組織 slug `org-i459`・`role="user"`）

結果:
- backend:
- frontend: 対象なし（画面の変更なし）

## 決定論ゲート（自動実走）
決定論ゲート（grep などの文字の確かめ）は置かない。守る決まり（正答率の出し方・`days` の範囲・おすすめの 0 問の扱い）は、動きを確かめる pytest（TC-01〜TC-07）が CI で毎回止める。

## 実行記録
| 日時 | コマンド | 終了コード | 結果 |
|---|---|---|---|
| 2026-11-12 | TC-01〜TC-08（実装前） | — | 実装前のため未実行（テストのファイルがまだ無い）。直す前の 500 は、計画の調査で使い捨てのテストを流して再現済み（plan_I459.md「エラーの詳細」） |

## TC 一覧

| TC | 内容 | コマンド | 期待値 | 対応 AC |
|---|---|---|---|---|
| TC-01 | `test_zero_problem_day_in_week`: 日々のまとめを 3 件作る（`today-6`: 解いた 10・正解 8 ／ `today-5`: 解いた 1・正解 0 ／ `today-4`: 解いた 0・正解 0・学習時間 600）。`GET /api/dashboard/analytics/?days=6`（週は `today-6`〜`today` の 1 つ） | `PYT -k zero_problem_day_in_week` | exit 0。応答 200・`performance_trends` が 1 件で `avg_accuracy == 72.73`（8 ÷ 11 × 100 を小数第 2 位で丸め）・`week_start == (today-6).isoformat()`。`daily_data` の `today-4` の行が `problems_attempted == 0`・`accuracy == 0`。Red: 直す前のコードでは 500（`DataError: division by zero`）で exit 非ゼロ | AC1・AC2・AC5 |
| TC-02 | `test_week_without_problems_is_zero`: 日々のまとめを 1 件だけ作る（`today-13`: 解いた 0・正解 0・学習時間 600）。`GET /api/dashboard/analytics/?days=13`（週は `today-13`〜`today-7` と `today-6`〜`today` の 2 つ） | `PYT -k week_without_problems_is_zero` | exit 0。応答 200・`performance_trends` が 2 件で、どちらも `avg_accuracy == 0`（1 つ目は 0 問の日だけの週・2 つ目はまとめが無い週）。Red: 直す前のコードでは 500 で exit 非ゼロ | AC1・AC3・AC5 |
| TC-03 | `test_invalid_days_returns_400`（パラメータ化）: `days` に `abc`・`1.5`・`0`・`-1`・`366` を入れて `GET /api/dashboard/analytics/?days=<値>` | `PYT -k invalid_days_returns_400` | exit 0。5 件とも応答 400・body が `{"error": {"main_message": "期間の指定が正しくありません", "sub_message": "日数は 1〜365 の整数で指定してください", "details": {}}}` と一致。Red: 直す前のコードでは `abc`・`1.5` が 500、`0`・`-1`・`366` が 200 で exit 非ゼロ | AC4・AC5 |
| TC-04 | `test_valid_days_returns_200`（パラメータ化）: `days` なし・`days=`（空）・`1`・`365` で `GET /api/dashboard/analytics/` | `PYT -k valid_days_returns_200` | exit 0。4 件とも応答 200。`daily_data` の件数が順に 31・31・2・366（`start_date`〜`end_date` の両端を含む） | AC4・AC5 |
| TC-05 | `test_recommendations_with_zero_problem_log`: 同じ組織の科目を 2 つ作り、学習記録を 2 件作る（科目 1: 解いた 0・正解 0 ／ 科目 2: 解いた 4・正解 1）。`GET /api/dashboard/recommendations/` | `PYT -k recommendations_with_zero_problem_log` | exit 0。応答 200・`recommendations` の中に科目 2 の 1 件（`current_accuracy == 25.0`）があり、科目 1 の正答率の項目（`current_accuracy` を持つ項目）は無い。FG: `backend/dashboard/views.py` のおすすめの `.filter(total_problems__gt=0)` を一時的に外すと 500 で exit 非ゼロ（確かめたら戻す） | スコープ「ほかの割り算の確認」・AC5 |
| TC-06 | `test_analytics_requires_login`: ログインしないで `GET /api/dashboard/analytics/` | `PYT -k analytics_requires_login` | exit 0。応答 401 | 認可（変えないことの確かめ） |
| TC-07 | 守りのテスト: #446 の横断テスト（下準備に 0 件の日を足した後）と I431 のテスト（dashboard の経路を含む） | `docker compose exec -T backend python -m pytest core/tests/test_I446_cross_api_tenant_isolation.py studylogs/tests/test_I431_studylogs_tenant_isolation.py -q` | exit 0（全件 passed）。#446 の下準備に `today-1` の 0 件の日のまとめ（学習時間 600）が入っていて、避ける注記（「0 で割る不具合は境界と関係ないので踏まない」）が無い | AC6 |
| TC-08 | /simplify の後の流し直し | `PYT` と TC-07 のコマンド | どちらも exit 0 | AC5・AC6 |

- CI: 上の 2 ファイルは CI の Backend Tests（`pytest`・PostgreSQL）で毎回流れる（AC5）。review-gate が `gh pr checks 478` で確かめる
