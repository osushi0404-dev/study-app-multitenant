# I446 手動テスト: 問題の管理画面とクイズの画面の無退行

- 関連: docs/issues/open/I446.md / docs/plans/open/plan_I446.md / GitHub #446 / Draft PR #456
- 前提: app-1 ワークツリーで `docker compose up -d db redis backend frontend` を起こし、Playwright MCP で画面を開く（ポートは `docker compose port frontend 3000` で確かめる・`docs/runbooks/frontend-verify.md`）
- 使用アカウント: E2E 用のシードユーザー `e2e_user_a@example.com`（組織 E2E Org A・`role='admin'`。パスワードは `e2e/.env.e2e` の `E2E_TEST_PASSWORD`）。app-1 の dev DB に無ければ、`docker compose --profile e2e run --rm e2e` の e2e-init（migrate とシード）で作る。ログインの失敗が続くと 5 分の制限がかかるため、パスワードは 1 回で入れる
- 画面のコードは変えない。変わるのはバックエンドの、問題の科目の入力の検証（4-2）とクイズの回の読み出し（4-4）だけなので、その 2 つを画面から通す

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `e2e_user_a` でログイン → 左のメニュー「問題管理」（`/quiz-management`）→ 自組織の科目を選んで問題を 1 つ新しく作る（問題文 `I446手動確認`・選択肢 2 つ・正解 1 つ）→ 一覧で作った問題を開いて解説を書き換えて保存 → `browser_console_messages` と backend のログを見る → 画面キャプチャを `.evidence/I446/` に保存 | 作成の後、一覧に `I446手動確認` が出る。編集の保存の後、書き換えた解説が出る。backend のログで `POST /api/problems/` が 201・`PUT` または `PATCH /api/problems/<id>/` が 200。コンソールに `/api/problems/` の 4xx・5xx が出ない | Claude |  | 4-2（`OrgSubjectField`）の後も、画面から送る自組織の科目が受け付けられること。作った問題は確認の後に画面から削除する（dev DB を元に戻す） |
| 2 | 同じアカウントでダッシュボードからクイズを始める → 1 問答える → 「終了」を押す → 結果の画面を見る → backend のログとコンソールを見る → 画面キャプチャを `.evidence/I446/` に保存 | 出題の画面に問題文と選択肢が出て、回答の後に正誤と解説が出る。終了の後に結果の画面（回答数 1・正答数）が出る。backend のログで `POST /api/quiz/` が 201（または 200）・`GET /api/quiz/<id>/next_problem/` が 200・`POST …/submit_answer/` が 200・`POST …/end/` が 200 | Claude |  | 4-4（`QuizSessionViewSet.get_queryset` の絞り込みと回答の先読み）の後も、自組織の回が使えること |

## 画面確認
<!-- frontend/src を変えないイシューのため、check-frontend-evidence.sh の対象外。No.1・No.2 の画面キャプチャは任意の証跡として残す。 -->
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

結論: 未実施
