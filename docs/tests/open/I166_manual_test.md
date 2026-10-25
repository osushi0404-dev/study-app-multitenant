# I166 手動テスト（dev DB の調査と画面からのクイズの確認）

- 関連: docs/issues/open/I166.md / docs/plans/open/plan_I166.md / GitHub #284 / Draft PR #330
- 前提: app-1 ワークツリーで `docker compose up -d db redis backend frontend`（ポートは `wt-ports.sh` の割当: backend 8020・frontend 3020）。画面の確認は Playwright MCP で `http://localhost:3020` を開く（`docs/runbooks/frontend-verify.md`）。
- 補足: 画面の見た目は変わらないため、Human の目視確認は不要。dev DB への書き込みは app-1 の dev DB（このワークツリー専用・I166 の確認用データ）にだけ行い、primary の dev DB は読み取りのみ。
- 使用アカウント: E2E 用のシードユーザー `e2e_user_a@example.com`（組織 E2E Org A・role=admin。パスワードは `e2e/.env.e2e` の `E2E_TEST_PASSWORD`）。No.2 で app-1 の dev DB に作る。ログインの失敗が続くと 5 分のログイン制限がかかるため、パスワードは `e2e/.env.e2e` から読んで 1 回で入れる。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | primary の dev DB の越境データを数える（読み取りのみ）: `docker exec study-app-multitenant-backend-1 python manage.py shell -c` で ①他組織の科目のセッション（`subject` があり `subject__organization_id != user__organization_id`）②他組織の問題への回答（`problem__subject__organization_id != session__user__organization_id`）③セッションの科目と違う問題への回答 の件数を出す | ①②③ とも 0 件（grill-me 時の実測と同じ）。0 でなければ実装を止めてユーザーに報告する | Claude | | 結果を計画書「調査結果」と照合する |
| 2 | app-1 の dev DB に確認用データを作る: `docker compose exec -T backend python manage.py migrate` → `seed_e2e --scenario tenant_isolation --password <E2E_TEST_PASSWORD>` → `seed_e2e --scenario quiz_session --password <同じ>` → `manage.py shell -c` で E2E Org B に科目「I166 組織Bの科目」と、その科目の選択問題「I166 組織Bの問題文です。」（正解・不正解の選択肢付き）を 1 件作る | 各コマンドが exit 0。組織 A の未削除の問題は「E2E テスト用の問題文です。」の 1 件だけ、組織 B に「I166 組織Bの問題文です。」が 1 件ある | Claude | | app-1 の新しい dev DB（ワークツリー専用）への書き込み |
| 3 | 科目なしのクイズ（問題管理の「クイズを実行」）: `e2e_user_a` でログイン → 左のメニューの「問題管理」→「クイズを実行」をクリック → 表示された問題の選択肢「正解の選択肢」をクリック → 結果の表示を待つ | クイズ画面に問題文「E2E テスト用の問題文です。」が表示される（「I166 組織Bの問題文です。」は表示されない）。回答後に解説「E2E テスト用の解説文です。」が表示され、「次の問題」ボタンは表示されない（全 1 問を回答済み＝問題数が自組織の 1 件）。ブラウザのコンソールにエラーが出ない | Claude | | 修正前は全組織の問題（2 件）から出題され、問題数も 2 になる |
| 4 | 科目ありのクイズと「もう一度挑戦」（無退行）: ダッシュボードの「クイズを始める」→ 科目の選択で「E2E Quiz Subject」→ 選択肢「正解の選択肢」をクリック → `manage.py shell -c` で `e2e_user_a` の有効なセッションの id を調べる → 「終了」→ No.3 と同じ手順で科目なしのクイズを始め直す（前のセッションが終了する）→ `http://localhost:3020/quiz/<調べた id>` を開く → 「もう一度挑戦」をクリック | 科目ありの開始で問題文「E2E テスト用の問題文です。」と、回答後の解説が表示される。`/quiz/<id>` で「クイズ完了！」が表示され、「もう一度挑戦」の後に問題文「E2E テスト用の問題文です。」が表示される（科目「E2E Quiz Subject」で開始される）。ブラウザのコンソールにエラーが出ない | Claude | | 完了画面の「もう一度挑戦」は終えたセッションの科目を送る経路（TC-08 と同じ検査を画面から通す） |
