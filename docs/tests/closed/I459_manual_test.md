# I459 手動テスト: 学習統計の画面が、解いた問題が 0 件の日があると 500 になる不具合を直す（dashboard/analytics）

- 関連: docs/plans/open/plan_I459.md / Draft PR #478
- 環境: app-1 ワークツリーのコンテナ（dev）。画面は Playwright MCP（`docs/runbooks/frontend-verify.md`）。画面のポートは `docker compose port frontend 3000` の出力（2026-11-12 は 3020）
- アカウント: `e2e_user_c@example.com`（組織 A・一般ユーザー。パスワード欄には名前 `E2E_TEST_PASSWORD` を入れる）
- データの作り方: スクラッチパッドに Python のファイルを書き、`docker compose cp` でコンテナの `/tmp/` に入れ、`docker compose exec -T backend python manage.py shell --command "exec(open('/tmp/<ファイル>').read())"` で 1 コマンドずつ流す。作ったまとめは残す（plan_I459.md 7 章）
- 実施: 2026-11-12 18:48・コミット `5c5db24a`（レビュー済みの HEAD・gate-check OK）

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | dev DB で `e2e_user_c@example.com` の日々のまとめのうち、`today-1`〜`today-29` で行が無い日を 1 つ選び（`today` は `timezone.now().date()`）、その日に `DailyStudySummary(total_problems_attempted=0, total_problems_correct=0, total_study_time=600)` を 1 件作る。作った後に、その利用者の過去 30 日のまとめの件数と、解いた数 0 の行の件数を出す | 解いた数 0 の行が 1 件以上ある（出力に件数が出る） | Claude | OK | 2026-11-11 に作成。過去 30 日のまとめ 1 件・解いた数 0 の行 1 件 |
| 2 | Playwright MCP で `http://localhost:<ポート>/login` から `e2e_user_c@example.com` でログインし、`http://localhost:<ポート>/statistics` を開く。`browser_network_requests` で `/api/dashboard/analytics/` の応答を、`browser_console_messages` でコンソールを見る。`.evidence/I459/statistics-c-1.png` に画面を撮る | `/api/dashboard/analytics/` が 200。コンソールに `Error fetching analytics data` が出ない。画面に学習統計の見出しが出て、エラーの表示が無い | Claude | OK | `GET /api/dashboard/analytics/?period=weekly` が 2 回とも 200。コンソールの error は 2 件で、どちらも今回と関係ない既存のもの（開発サーバーの `ws://localhost:3000/ws` への接続失敗・`Statistics` の一覧の `key` の警告）。`Error fetching analytics data` は出ない。画面は「学習統計」の見出しと 4 つのカード（数値はどれも 0。画面が API の別の名前を読んでいるためで #473 の範囲） |
| 3 | dev の backend のコンテナで、`e2e_user_c@example.com` を `APIClient.force_authenticate` した状態で `GET /api/dashboard/analytics/?days=abc`・`?days=366`・`days` なしを呼び、状態コードと body を見る | `abc`・`366` は 400 で、body の `error.main_message` が `期間の指定が正しくありません`。`days` なしは 200 で `daily_data` が 31 件 | Claude | OK | `abc` 400・`366` 400（どちらも `期間の指定が正しくありません`）・なし 200（`daily_data` 31 件）。手順を計画の `browser_evaluate` から変えた（自律判断の記録） |

## 画面確認
<!-- frontend/src は変えないイシュー。統計の画面が 500 にならずに開けることを No.2 で確かめる -->
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
| 2026-11-12 18:48 | 5c5db24a | 解いた数 0 の日のまとめを持つ状態で `/statistics` を開く | e2e_user_c | analytics が 200 で、学習統計の画面がエラーなしで出る | analytics 200・見出しと 4 つのカードとタブが出た・エラーの表示なし | statistics-c-1.png |

結論: OK
