# I455 手動テスト: ダッシュボード・学習の画面の無退行

- 関連: docs/issues/open/I455.md / docs/plans/open/plan_I455.md / GitHub #455 / Draft PR #462
- 前提: app-1 ワークツリーで `docker compose up -d db redis backend frontend` を起こし、Playwright MCP で画面を開く（ポートは `docker compose port frontend 3000` で確かめる・`docs/runbooks/frontend-verify.md`）
- 使用アカウント: E2E 用のシードユーザー `e2e_user_a@example.com`（組織 E2E Org A。パスワードは `e2e/.env.e2e` の `E2E_TEST_PASSWORD`）。app-1 の dev DB に無ければ、`docker compose --profile e2e run --rm e2e` の e2e-init（migrate とシード）で作る。ログインの失敗が続くと 5 分の制限がかかるため、パスワードは 1 回で入れる
- 画面のコードは変えない。変わるのはバックエンドの読み出しの書き方だけ（結果は同じ）なので、画面から呼ぶ経路（`GET /api/dashboard/overview/`・`GET /api/dashboard/analytics/`・クイズの回）が今までどおり動くことを見る

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `e2e_user_a` でログイン → ダッシュボード（`/dashboard`）を開く → 分析の画面（ダッシュボードの分析の表示）を開く → `browser_console_messages` と backend のログを見る → 画面キャプチャを `.evidence/I455/` に保存 | ダッシュボードに今日の学習・最近のクイズの欄が出る（最近のクイズは科目名つき）。backend のログで `GET /api/dashboard/overview/` と `GET /api/dashboard/analytics/` が 200。コンソールに `/api/dashboard/` の 4xx・5xx が出ない | Claude | OK（2026-11-12 10:33〜10:34・3ccd40c5）。ダッシュボードに今日の学習時間・連続学習日数・解答問題数・正答率・今週の学習時間・正答率の欄が出た。左のメニュー「学習統計」（`/statistics`）も表示された。backend のログで `GET /api/dashboard/overview/` 200・`GET /api/dashboard/analytics/?period=weekly` 200。コンソールの error は、ログイン前の `/api/settings/` 401（既知）・開発サーバーの WebSocket 接続（既知）と、`/statistics` の React の key の警告（`Statistics` の一覧の描画。画面のコードはこのイシューで変えていない既存のもの）だけで、`/api/dashboard/` の 4xx・5xx は無い | 期待結果を test-gate で直した: 今の画面には「最近のクイズ」の欄が無い（API の `recent_quizzes` を表示しない既存の作り）。最近のクイズの中身は No.2 で API を直接読んで確かめた。「分析の画面」は左のメニューの「学習統計」 |
| 2 | 同じアカウントでダッシュボードの「学習を開始」からクイズを始める → 1 問答える → ダッシュボードへ戻り、最近のクイズに今の回が出ることを見る → backend のログとコンソールを見る → 画面キャプチャを `.evidence/I455/` に保存 | 出題の画面に問題文と選択肢が出て、回答の後に正誤と解説が出る。ダッシュボードの最近のクイズの先頭に今の回（科目名つき）が出る。backend のログで `POST /api/quiz/` 201・`submit_answer` 200・`GET /api/dashboard/overview/` 200 | Claude | OK（2026-11-12 10:34〜10:35・3ccd40c5）。「クイズを始める」→ 科目の選択で `E2E Quiz Subject` → 問題文「E2E テスト用の問題文です。」と選択肢 2 つが出て、「正解の選択肢」を選ぶと「正解です！」と解説が出た。backend のログで `POST /api/quiz/` 201・`GET /api/quiz/28/next_problem/` 200・`POST /api/quiz/28/submit_answer/` 200・戻った後の `GET /api/dashboard/overview/` 200（応答が 748 → 909 バイトに増えた）。同じ API を読み取りだけで直接呼ぶと（`manage.py shell` で `DashboardOverviewView` に `e2e_user_a` を渡す）、`recent_quizzes` の先頭が `('28', 'E2E Quiz Subject', 1)`（今の回・科目名つき・回答 1） | 「最近のクイズに今の回が出る」は、画面に欄が無いため API の応答で確かめた（No.1 の備考）。作ったクイズの回（28）は e2e のシードの組織の自分の記録で、ほかのテストを壊さないので残した |

## 画面確認
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
| 2026-11-12 10:33 | 3ccd40c5 | ログインして `/dashboard` を開く | e2e_user_a | ダッシュボードが出て、`/api/dashboard/overview/` が 200 | 表示された（200） | dashboard-a-1.png |
| 2026-11-12 10:34 | 3ccd40c5 | 左のメニュー「学習統計」（`/statistics`）を開く | e2e_user_a | 統計の画面が出て、`/api/dashboard/analytics/` が 200 | 表示された（200） | statistics-a-2.png |
| 2026-11-12 10:34 | 3ccd40c5 | 「クイズを始める」→ `E2E Quiz Subject` → 正解の選択肢を選ぶ | e2e_user_a | 問題文・選択肢・正誤・解説が出る | 「正解です！」と解説が出た（201・200・200） | quiz-answer-a-3.png |
| 2026-11-12 10:35 | 3ccd40c5 | `/dashboard` に戻る | e2e_user_a | ダッシュボードが出て、`/api/dashboard/overview/` が 200 | 表示された（200・`recent_quizzes` の先頭が今の回） | dashboard-after-quiz-a-4.png |

結論: OK（No.1・No.2 とも Claude が Playwright MCP で実施。Human の項目なし）
