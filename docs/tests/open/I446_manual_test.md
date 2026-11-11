# I446 手動テスト: 問題の管理画面とクイズの画面の無退行

- 関連: docs/issues/open/I446.md / docs/plans/open/plan_I446.md / GitHub #446 / Draft PR #456
- 前提: app-1 ワークツリーで `docker compose up -d db redis backend frontend` を起こし、Playwright MCP で画面を開く（ポートは `docker compose port frontend 3000` で確かめる・`docs/runbooks/frontend-verify.md`）
- 使用アカウント: E2E 用のシードユーザー `e2e_user_a@example.com`（組織 E2E Org A・`role='admin'`。パスワードは `e2e/.env.e2e` の `E2E_TEST_PASSWORD`）。app-1 の dev DB に無ければ、`docker compose --profile e2e run --rm e2e` の e2e-init（migrate とシード）で作る。ログインの失敗が続くと 5 分の制限がかかるため、パスワードは 1 回で入れる
- 画面のコードは変えない。変わるのはバックエンドの、問題の科目の入力の検証（4-2）とクイズの回の読み出し（4-4）だけなので、その 2 つを画面から通す

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `e2e_user_a` でログイン → 左のメニュー「問題管理」（`/quiz-management`）→ 自組織の科目を選んで問題を 1 つ新しく作る（問題文 `I446手動確認`・選択肢 2 つ・正解 1 つ）→ 一覧で作った問題を開いて解説を書き換えて保存 → `browser_console_messages` と backend のログを見る → 画面キャプチャを `.evidence/I446/` に保存 | 作成の後、一覧に `I446手動確認` が出る。編集の保存の後、書き換えた解説が出る。backend のログで `POST /api/problems/` が 201・`PUT` または `PATCH /api/problems/<id>/` が 200。コンソールに `/api/problems/` の 4xx・5xx が出ない | Claude | OK（2026-11-12 08:35〜08:39・86bfbb61）。作成の後に一覧に `I446手動確認` が出た。編集の後のプレビューで解説が「I446 編集後の解説」になった。backend のログで `POST /api/problems/` 201・`PUT /api/problems/38/` 200。コンソールの error は、ログイン前の `/api/settings/` 401（既知）と開発サーバーの WebSocket 接続（`ws://localhost:3000/ws`）だけで、`/api/problems/` の 4xx・5xx は無い | 4-2（`OrgSubjectField`）の後も、画面から送る自組織の科目が受け付けられること。作った問題は No.2 の後に画面から削除した（一覧から消えたことを確かめた） |
| 2 | 同じアカウントでダッシュボードの「学習を開始」から `E2E Quiz Subject` のクイズを始める → 1 問答える → 画面の URL を回の番号つき（`/quiz/<id>`）で開き直して続きから 1 問答える → backend のログとコンソールを見る → 画面キャプチャを `.evidence/I446/` に保存 | 出題の画面に問題文と選択肢が出て、回答の後に正誤と解説が出る。開き直した後も回答数が引き継がれる（`総回答: 1`）。backend のログで `POST /api/quiz/` が 201・`GET /api/quiz/<id>/` が 200・`GET /api/quiz/<id>/next_problem/` が 200・`POST …/submit_answer/` が 200 | Claude | OK（2026-11-12 08:37〜08:38・86bfbb61）。`POST /api/quiz/` 201・`next_problem` 200・`submit_answer` 200（正解）→ `/quiz/27` を開き直すと `GET /api/quiz/27/` 200・`next_problem` 200 で「正解: 1 / 総回答: 1」が引き継がれ、2 問目（`I446手動確認`・編集後の解説）に答えて `submit_answer` 200（不正解の表示と解説）。コンソールの error は WebSocket 接続だけ | 4-4（`QuizSessionViewSet.get_queryset` の絞り込みと回答の先読み）の後も、自組織の回が使えること。手順と期待結果を test-gate で直した: 今の画面は `POST …/end/` を呼ばない（「終了」はダッシュボードへ戻るだけで、解き終えても復習の出題が続く。このイシューで変えていない既存の作り）ため、終了の経路は画面から通せない。代わりに、4-4 で回答の先読みを足した回の詳細（`GET /api/quiz/<id>/`）を、画面の続きからの読み込みで通した。終了の経路の自組織・越境の振る舞いは CI の新しいテスト（`OwnCheck` の `POST api/quiz/<pk>/end/`・TC-01）が確かめている |

## 画面確認
<!-- frontend/src を変えないイシューのため、check-frontend-evidence.sh の対象外。No.1・No.2 の画面キャプチャは任意の証跡として残す。 -->
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
| 2026-11-12 08:35 | 86bfbb61 | `/quiz-management` で問題を新しく作る（`E2E Quiz Subject`・選択肢 2 つ） | e2e_user_a | 作成できて一覧に出る | 作成でき一覧に出た（201） | quiz-management-create-a-1.png |
| 2026-11-12 08:36 | 86bfbb61 | 作った問題の解説を編集して保存し、プレビューを開く | e2e_user_a | 書き換えた解説が出る | 「I446 編集後の解説」が出た（200） | quiz-management-edit-a-2.png |
| 2026-11-12 08:37 | 86bfbb61 | ダッシュボードからクイズを始めて 1 問答える | e2e_user_a | 正誤と解説が出る | 「正解です！」と解説が出た | quiz-answer-a-3.png |
| 2026-11-12 08:38 | 86bfbb61 | `/quiz/27` を開き直して続きから答える | e2e_user_a | 回答数が引き継がれ、次の問題に答えられる | 「正解: 1 / 総回答: 1」で 2 問目が出て、不正解と解説が出た | quiz-resume-a-4.png |

結論: OK（No.1・No.2 とも Claude が実施。Human の項目なし）
