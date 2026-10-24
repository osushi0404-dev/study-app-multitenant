# I158 手動テスト（dev DB への適用と実ブラウザでの開始確認）

- 関連: docs/issues/open/I158.md / docs/plans/open/plan_I158.md / GitHub #275 / Draft PR #317
- 前提: `docker compose up -d backend db redis`（No.4 のみ `docker compose up -d frontend` も起動）
- 補足: 画面の見た目は変わらないため、Human の目視確認は不要。**No.2（dev DB への `migrate`）は Danger Ops のため、No.1 の結果を示してユーザー承認を得てから実行する。**
- 使用アカウント: No.4 は E2E 用シードユーザー（`seed_e2e --scenario quiz_session` が作成・パスワードは `e2e/.env.e2e` の `E2E_TEST_PASSWORD`）。No.1〜3 はアカウントを使わない（DB の読み取りと migrate のみ）。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | 適用前の対象確認（読み取りのみ）: `docker compose exec -T backend python manage.py shell -c` で、有効セッションが 2 件以上あるユーザーごとに「残す 1 件（`started_at`・id の降順で先頭）」と「終了扱いにする id 一覧」を出力し、本ファイルの実結果欄に記録する | 終了扱いにする件数が 5 件前後（2026-10-24 の計画時点で 5 件・ユーザー 5 人）。件数が大きく違う場合は No.2 に進まずユーザーに報告 | Claude | | ロールバック時の追跡用に id を記録する |
| 2 | **ユーザー承認後に** `docker compose exec -T backend python manage.py migrate problems` を実行 | exit 0。出力に `Applying problems.0019_quizsession_client_request_id... OK`・`0020_deactivate_duplicate_active_quizsessions... OK`・`0021_quizsession_constraints... OK` が並ぶ | Claude | | Danger Ops（大量更新に該当・削除なし） |
| 3 | 適用後の確認: `manage.py shell -c` で ①有効セッションが 2 件以上あるユーザー数 ②No.1 で記録した id の `is_active`・`ended_at` ③`showmigrations problems` の末尾 | ① 0 ② すべて `is_active=False`・`ended_at` が設定済み ③ `[X] 0021_quizsession_constraints` | Claude | | |
| 4 | 実ブラウザ相当の確認: `docker compose up -d frontend` の後、`cd e2e && npx playwright test tests/quiz-session.spec.ts` を実行。実行前後で E2E 用ユーザーの QuizSession 件数を `manage.py shell -c` で数える | Playwright が exit 0（TC-40 含む）。E2E 用ユーザーの QuizSession 件数の増加が「開始した回数」と同じ（テスト 2 件 = 2 件増）で、有効セッションは 1 件 | Claude | | 開発サーバー（StrictMode 有効）での実測 |
