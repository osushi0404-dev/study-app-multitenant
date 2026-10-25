# I166 手動テスト（dev DB の調査と画面からのクイズの確認）

- 関連: docs/issues/open/I166.md / docs/plans/open/plan_I166.md / GitHub #284 / Draft PR #330
- 前提: app-1 ワークツリーで `docker compose up -d db redis backend frontend`（ポートは `wt-ports.sh` の割当: backend 8020・frontend 3020）。画面の確認は Playwright MCP で `http://localhost:3020` を開く（`docs/runbooks/frontend-verify.md`）。
- 補足: 画面の見た目は変わらないため、Human の目視確認は不要。dev DB への書き込みは app-1 の dev DB（このワークツリー専用・I166 の確認用データ）にだけ行い、primary の dev DB は読み取りのみ。
- 使用アカウント: E2E 用のシードユーザー `e2e_user_a@example.com`（組織 E2E Org A・role=admin。パスワードは `e2e/.env.e2e` の `E2E_TEST_PASSWORD`）。No.2 で app-1 の dev DB に作る。ログインの失敗が続くと 5 分のログイン制限がかかるため、パスワードは `e2e/.env.e2e` から読んで 1 回で入れる。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | primary の dev DB の越境データを数える（読み取りのみ）: `docker exec study-app-multitenant-backend-1 python manage.py shell -c` で ①他組織の科目のセッション（`subject` があり `subject__organization_id != user__organization_id`）②他組織の問題への回答（`problem__subject__organization_id != session__user__organization_id`）③セッションの科目と違う問題への回答 の件数を出す | ①②③ とも 0 件（grill-me 時の実測と同じ）。0 でなければ実装を止めてユーザーに報告する | Claude | OK（2026-10-26）① 0 件 ② 0 件 ③ 0 件（セッション 124 件・回答 44 件。計画書「調査結果」と一致） | 結果を計画書「調査結果」と照合する |
| 2 | app-1 の dev DB に確認用データを作る: `docker compose exec -T backend python manage.py migrate` → `seed_e2e --scenario tenant_isolation --password <E2E_TEST_PASSWORD>` → `seed_e2e --scenario quiz_session --password <同じ>` → `manage.py shell -c` で E2E Org B に科目「I166 組織Bの科目」と、その科目の選択問題「I166 組織Bの問題文です。」（正解・不正解の選択肢付き）を 1 件作る | 各コマンドが exit 0。組織 A の未削除の問題は「E2E テスト用の問題文です。」の 1 件だけ、組織 B に「I166 組織Bの問題文です。」が 1 件ある | Claude | OK（2026-10-26）E2E の実行（`docker compose --profile e2e run --rm e2e`）の e2e-init が migrate と 2 つのシナリオのシードを行い、その後 scratchpad の `adv/seed_no2.py` で組織 B の科目と問題を作成。組織 A の問題は「E2E テスト用の問題文です。」の 1 件だけ・組織 B は「I166 組織Bの問題文です。」の 1 件 | app-1 の新しい dev DB（ワークツリー専用）への書き込み。シードは e2e-init で行ったため手順の個別コマンドは打っていない（内容は同じ） |
| 3 | 科目なしのクイズ（問題管理の「クイズを実行」）: `e2e_user_a` でログイン → 左のメニューの「問題管理」→「クイズを実行」をクリック → 表示された問題の選択肢「正解の選択肢」をクリック → 結果の表示を待つ | クイズ画面に問題文「E2E テスト用の問題文です。」が表示される（「I166 組織Bの問題文です。」は表示されない）。回答後に解説「E2E テスト用の解説文です。」が表示され、「次の問題」ボタンは表示されない（全 1 問を回答済み＝問題数が自組織の 1 件）。ブラウザのコンソールにエラーが出ない | Claude | OK（2026-10-26）「問題 1 / 1」・問題文は「E2E テスト用の問題文です。」（組織 B の問題は出ない）・回答後に「正解です！」と解説「E2E テスト用の解説文です。」・ボタンは「終了」だけ（「次の問題」なし）・コンソールのエラー 0 件（警告は React Router の既知 2 件） | 修正前は全組織の問題（2 件）から出題され、問題数も 2 になる。右上の「正解: 0 / 総回答: 0」が回答後も増えないのは、結果の表示中は回答前の値を出す意図した作り（`frontend/src/hooks/useQuizDisplayStats.ts`）で、I166 とは無関係 |
| 4 | 科目ありのクイズと「もう一度挑戦」（無退行）: ダッシュボードの「クイズを始める」→ 科目の選択で「E2E Quiz Subject」→ 選択肢「正解の選択肢」をクリック → `manage.py shell -c` で `e2e_user_a` の有効なセッションの id を調べる → 「終了」→ No.3 と同じ手順で科目なしのクイズを始め直す（前のセッションが終了する）→ `http://localhost:3020/quiz/<調べた id>` を開く → 「もう一度挑戦」をクリック | 科目ありの開始で問題文「E2E テスト用の問題文です。」と、回答後の解説が表示される。`/quiz/<id>` で「クイズ完了！」が表示され、「もう一度挑戦」の後に問題文「E2E テスト用の問題文です。」が表示される（科目「E2E Quiz Subject」で開始される）。ブラウザのコンソールにエラーが出ない | Claude | OK（2026-10-26）科目の選択の窓に「E2E Quiz Subject」「E2E Subject A」（自組織の科目だけ）→ `/quiz?subject=2` で問題文と回答後の解説を表示 → 有効なセッションは id 21（E2E Quiz Subject・回答 1・正解 1）→ 科目なしのクイズを始め直して 21 を終了 → `/quiz/21` で「クイズ完了！」（正答率 100%・正解 1・問題数 1）→「もう一度挑戦」で問題文を表示。DB の有効なセッションは id 23・科目 E2E Quiz Subject・問題数 1。コンソールのエラーはログイン前の `/api/settings/` の 401（手順書の既知）だけ | 完了画面の「もう一度挑戦」は終えたセッションの科目を送る経路（TC-08 と同じ検査を画面から通す） |

## 画面確認
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
| 2026-10-26 00:43 | ae65835 | `/quiz-management` の「クイズを実行」（科目なし）→ 正解の選択肢をクリック | e2e_user_a | 自組織の問題だけ・問題 1 / 1・解説が出る・「次の問題」なし | 期待どおり・コンソールのエラー 0 件 | quiz-no-subject-a-1.png |
| 2026-10-26 00:44 | ae65835 | ダッシュボード「クイズを始める」→「E2E Quiz Subject」→ 正解の選択肢をクリック | e2e_user_a | 自組織の科目だけが選べる・問題文と解説が出る | 期待どおり | quiz-subject-a-2.png |
| 2026-10-26 00:44 | ae65835 | 終えたセッション `/quiz/21` を開く | e2e_user_a | 「クイズ完了！」が出る | 期待どおり（正答率 100%） | quiz-complete-a-3.png |
| 2026-10-26 00:44 | ae65835 | 完了画面の「もう一度挑戦」 | e2e_user_a | 同じ科目で新しいクイズが始まり、問題文が出る | 期待どおり（新しいセッション id 23・E2E Quiz Subject） | quiz-retry-a-4.png |

## /test 実施記録（2026-10-26）
- 自動: TC-20 **14 passed**・TC-21 **137 passed**・TC-22 pre-commit（ruff・bandit 含む）全 Passed・TC-23 E2E **8 passed**・CI（PR #330）7 ジョブすべて pass。
- 手動: No.1〜No.4 すべて OK（すべて Claude 実施・Human 実施項目なし）。`check-manual-test-executor.sh` 合格・`check-frontend-evidence.sh` は対象外（frontend/src の変更なし）。
- I187 の手順（`docs/runbooks/frontend-verify.md`）の効き方（ユーザー依頼で確認）: 3.（`docker compose port frontend 3000` で URL）・4.（`npm run typecheck`）・5.（パスワード欄に名前 `E2E_TEST_PASSWORD` を入れると `--secrets` が本当の値に置き換えて入力。ログイン成功）・6.（`browser_snapshot`・クリック・`.evidence/I166/` への画面キャプチャ・`browser_console_messages`）・自動で保存される記録が `.evidence/` 直下に入ること・ログイン前の `/api/settings/` 401 が既知として区別できること、のすべてが手順書どおりに動いた。手順書と違った点は 1 つ: このセッションは自動承認モードのため、手順書の「画面確認は通常モードで行う」を満たしていない（任意のコードを動かす操作〔`browser_evaluate` など〕は使っていない）。
