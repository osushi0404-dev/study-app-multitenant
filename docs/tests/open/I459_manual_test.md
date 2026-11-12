# I459 手動テスト: 学習統計の画面が、解いた問題が 0 件の日があると 500 になる不具合を直す（dashboard/analytics）

- 関連: docs/plans/open/plan_I459.md / Draft PR #478
- 環境: app-1 ワークツリーのコンテナ（dev）。画面は Playwright MCP（`docs/runbooks/frontend-verify.md`）
- アカウント: `e2e_user_c@example.com`（組織 A・一般ユーザー。パスワード欄には名前 `E2E_TEST_PASSWORD` を入れる）
- データの作り方: スクラッチパッドに Python のファイルを書き、`docker compose cp` でコンテナの `/tmp/` に入れ、`docker compose exec -T backend python manage.py shell --command "exec(open('/tmp/<ファイル>').read())"` で 1 コマンドずつ流す。作ったまとめは残す（plan_I459.md 7 章）

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | dev DB で `e2e_user_c@example.com` の日々のまとめのうち、`today-1`〜`today-29` で行が無い日を 1 つ選び（`today` は `timezone.now().date()`）、その日に `DailyStudySummary(total_problems_attempted=0, total_problems_correct=0, total_study_time=600)` を 1 件作る。作った後に、その利用者の過去 30 日のまとめの件数と、解いた数 0 の行の件数を出す | 解いた数 0 の行が 1 件以上ある（出力に件数が出る） | Claude |  |  |
| 2 | Playwright MCP で `http://localhost:3000/login` から `e2e_user_c@example.com` でログインし、`http://localhost:3000/statistics` を開く。`browser_network_requests` で `/api/dashboard/analytics/` の応答を、`browser_console_messages` でコンソールを見る。`.evidence/I459/statistics-c-1.png` に画面を撮る | `/api/dashboard/analytics/` が 200。コンソールに `Error fetching analytics data` が出ない。画面に学習統計の見出しが出て、エラーの表示が無い | Claude |  |  |
| 3 | No.2 と同じログインの状態で、`browser_evaluate` から、No.2 の `browser_network_requests` に出た analytics の URL と同じ origin の `<origin>/api/dashboard/analytics/?days=abc` を `fetch(url, {headers: {Authorization: 'Bearer ' + localStorage.getItem('accessToken')}})` で呼び（画面の `frontend/src/services/api.ts:28-30` と同じ付け方。鍵の値は返り値に入れず、状態コードと body だけを返す）、状態コードと body を見る | 400 で、body の `error.main_message` が `期間の指定が正しくありません` | Claude |  |  |

## 画面確認
<!-- frontend/src は変えないイシュー。統計の画面が 500 にならずに開けることを No.2 で確かめる -->
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

結論: OK / NG
