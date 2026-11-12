# I455 手動テスト: ダッシュボード・学習の画面の無退行

- 関連: docs/issues/open/I455.md / docs/plans/open/plan_I455.md / GitHub #455 / Draft PR #462
- 前提: app-1 ワークツリーで `docker compose up -d db redis backend frontend` を起こし、Playwright MCP で画面を開く（ポートは `docker compose port frontend 3000` で確かめる・`docs/runbooks/frontend-verify.md`）
- 使用アカウント: E2E 用のシードユーザー `e2e_user_a@example.com`（組織 E2E Org A。パスワードは `e2e/.env.e2e` の `E2E_TEST_PASSWORD`）。app-1 の dev DB に無ければ、`docker compose --profile e2e run --rm e2e` の e2e-init（migrate とシード）で作る。ログインの失敗が続くと 5 分の制限がかかるため、パスワードは 1 回で入れる
- 画面のコードは変えない。変わるのはバックエンドの読み出しの書き方だけ（結果は同じ）なので、画面から呼ぶ経路（`GET /api/dashboard/overview/`・`GET /api/dashboard/analytics/`・クイズの回）が今までどおり動くことを見る

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `e2e_user_a` でログイン → ダッシュボード（`/dashboard`）を開く → 分析の画面（ダッシュボードの分析の表示）を開く → `browser_console_messages` と backend のログを見る → 画面キャプチャを `.evidence/I455/` に保存 | ダッシュボードに今日の学習・最近のクイズの欄が出る（最近のクイズは科目名つき）。backend のログで `GET /api/dashboard/overview/` と `GET /api/dashboard/analytics/` が 200。コンソールに `/api/dashboard/` の 4xx・5xx が出ない | Claude | | 4-4 の dashboard/views.py の置き換え（`active_session`・`recent_quizzes`・`subject_distribution`）を画面から通す |
| 2 | 同じアカウントでダッシュボードの「学習を開始」からクイズを始める → 1 問答える → ダッシュボードへ戻り、最近のクイズに今の回が出ることを見る → backend のログとコンソールを見る → 画面キャプチャを `.evidence/I455/` に保存 | 出題の画面に問題文と選択肢が出て、回答の後に正誤と解説が出る。ダッシュボードの最近のクイズの先頭に今の回（科目名つき）が出る。backend のログで `POST /api/quiz/` 201・`submit_answer` 200・`GET /api/dashboard/overview/` 200 | Claude | | QuizSession の Manager の差し替えと `problems/views.py` の `for_user` の後も、自組織の回が使えること |

## 画面確認
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|

結論: （test-gate で記入）
