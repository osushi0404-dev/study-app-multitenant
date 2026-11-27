# I547 自動テスト: レビュー役 5 つの指示の BP 見直し

実行コマンド（例）: 定義の文字を読むテストは下の決定論ゲート。pytest・Jest・E2E はアプリの変更が無いので CI に任せる（`bash scripts/claude/tests/run-all.sh` も CI が流す）

結果:
- backend: 変更なし（CI）
- frontend: 変更なし（CI）

## 方針
- 今回の変更は文書と、写しの一致・有無を見るテストの項目 3 つ（`test_i181_review_slim.sh` の D9・`test_i593_review_from_base.sh` の TC-02・`test_i185_harness_docs.sh` の TC-14⑧b）だけ。新しいテストのスクリプトは足さない（前置きの制約は既存の `test_i593_review_from_base.sh` の TC-03 が守り、ほかは意図的な変更でしか戻らない・`docs/runbooks/plan-writing-rules.md`「決定論テストの対象の選び方」）
- 守るのは「直した後も、定義の文字を読む既存のテスト 11 本がすべて合格すること」（TC-01。前置きが入口の変換を通ること・出力の形を含む）と、受け入れ条件のうち文字で確かめられる点（TC-02〜TC-05）
- TC-04・TC-05 は文言の有無を見るので、この PR の実装の確かめだけに使う（常設のテストのスクリプトにはしない・`plan-writing-rules.md`「決定論テストの対象の選び方」）

## テストケース
| TC | 内容 | 合格の条件 | 実装前の結果（2026-11-27） |
|---|---|---|---|
| TC-01 | 定義の文字を読む既存のテスト 11 本（下のゲートの `bash scripts/claude/tests/*.sh`）が書き換えの後も合格する。`test_i593_review_from_base.sh` の TC-03 は本物の 5 つの定義を入口の変換に通す（R1） | 全部 exit 0 | 11 本とも exit 0（基準） |
| TC-02 | 高リスク判定の条件の一覧が `review-rules.md` の 1 か所だけにあり、レビュー役の定義に写しが無い（AC4・PR15・CR9） | exit 0 | exit 1（実装前は 2 つの定義にあり、review-rules に無い。失敗の注入の確認） |
| TC-03 | `review-rules.md` に「## 高リスク判定の条件」の節がある（PR15） | exit 0 | exit 1（実装前は無い） |
| TC-04 | 同梱 A・B・D・E・F の観点が定義にあり、E・F・H の 1 文ずつが手順書・規約にある（AC3） | exit 0 | exit 1（実装前は無い） |
| TC-06 | 計画レビュー役が高リスク判定に要る範囲（「高リスク判定の条件」の節と (b) の 2 つの一覧）を読み、2 つのレビュー役が review-rules を節だけに絞って読まない（fix-loop・F1。この PR の確かめだけ） | exit 0 | 直す前の版（`git show` の写し）で 2 つとも exit 1 |
| TC-05 | 古い言い方（「プレーン default」・「step 3.5」・「Read / Bash」）が定義に無い（AC2・PR5・IR1・CR1） | exit 0 | exit 1（実装前は有る） |

## 実行記録
- 2026-11-27 fix-loop の後に手元で決定論ゲート 29 行を流し、29 行とも exit 0（既存のテスト 11 本・TC-02〜TC-06）
- 2026-11-27 test-gate: `bash scripts/claude/gate-check.sh I547` exit 0（`GATE_CHECK: OK`・REVIEWED_COMMIT 9cfab29a）。委ねられた重いテストは無い
- 2026-11-27 review-gate（`docs/reviews/I547_code_review_20261127_0946.md`・差分のレビュー `docs/reviews/I547_code_review_20261127_1001.md`）: 決定論ゲートはスクリプトが実走（記録の「決定論ゲート実行結果」）・CI は `CI_WAIT: OK`

## 再発防止記録（fix-loop・2026-11-27）
- なぜ失敗したか: /simplify で「review-rules の中の一覧を (b) の 1 か所に」と「レビュー役は節だけを読む」を同時に入れ、節が自己完結でなくなったのに読む範囲を節に絞ったので、ハーネスの一覧が計画レビュー役の読む範囲の外に出た（基本レビュー F1・`docs/reviews/I547_fix_diagnosis_20261127_1010.md`）
- 何を変えたか: 2 つのレビュー役は `docs/runbooks/review-rules.md` を Read し、計画レビュー役は「高リスク判定の条件」の節と同じファイルの (b) の 2 つの一覧で判定する、と書いた（Grep で節だけを読む指示を消した。F3 も同時に消える）
- セキュリティ上の考慮点: 高リスクの見落としは敵対的レビューの起動の漏れにつながる。パスの判定はスクリプトも出すので二重に守られるが、計画レビューの判定を正しく出す
- 次回どう防ぐか: 読む範囲を絞る変更をするときは、判定に要る情報がその範囲の中にあるかを、参照の先までたどって確かめる（同じ整理で「参照にする」と「読む範囲を絞る」を同時に入れない）
- 確かめた結果: TC-06 の 2 つを直す前の版（`git show HEAD:` の写し）で流して exit 1、直した後で exit 0。決定論ゲート全体を手元で流して合格（下の実行記録）

## FG（失敗の注入）の実行記録
- 2026-11-27 計画時: TC-02〜TC-05 を実装前のファイルに対して流し、4 つとも exit 1（不合格）になることを確かめた（実装前の状態が失敗の注入にあたる）。計画レビューの後、ゲートを 1 語ずつの 13 行に分けて 1 行ずつ流し直し、13 行とも exit 1 を確かめた
- TC-01: 既存のテストはそれぞれのテストの中に FG を持つ（例: i181 の FG-D9・i593 の FG-TC-02・FG-TC-03）。変えた 3 項目について、実装の後に次を記録する: i181 の `FG-D9` が PASS（review-rules の語を消すと D9 が不合格）・i593 の `FG-TC-02`（review-rules から `scripts/claude/gate-check.sh` を消すと不合格）と足した 2 項目（定義に写しが無い）が PASS・i185 の TC-14⑧b が PASS

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_fix_review.sh
bash scripts/claude/tests/test_i181_review_slim.sh
bash scripts/claude/tests/test_i185_harness_docs.sh
bash scripts/claude/tests/test_i193_official_flow.sh
bash scripts/claude/tests/test_i197_adversarial_process.sh
bash scripts/claude/tests/test_i197_review_ledger.sh
bash scripts/claude/tests/test_i202_ledger_cleanup.sh
bash scripts/claude/tests/test_i205_stop_criteria.sh
bash scripts/claude/tests/test_i593_review_from_base.sh
bash scripts/claude/tests/test_review_verdict.sh
bash scripts/claude/tests/test_adversarial_trigger.sh
! grep -qF "画面制御していてもAPI直叩きで事故りうる変更" .claude/agents/plan-reviewer.md .claude/agents/code-reviewer.md .claude/agents/adversarial-reviewer.md .claude/agents/fix-diagnosis-reviewer.md .claude/agents/issue-reviewer.md
grep -qF "画面制御していてもAPI直叩きで事故りうる変更" docs/runbooks/review-rules.md
grep -qx "## 高リスク判定の条件" docs/runbooks/review-rules.md
grep -qF "流れの途中" .claude/agents/plan-reviewer.md
grep -qF "§16" .claude/agents/plan-reviewer.md
grep -qF "まだ無いデータ" .claude/agents/plan-reviewer.md
grep -qF "設計確認メモ（grill-me の回答）に根拠" .claude/agents/plan-reviewer.md
grep -qF "§16" .claude/agents/code-reviewer.md
grep -qF "まだ無いデータ" .claude/agents/code-reviewer.md
grep -qF "docs/runbooks/ux-rules.md" .claude/agents/code-reviewer.md
grep -qF "設計確認メモ（grill-me の回答）に根拠を書く" docs/runbooks/plan-writing-rules.md
grep -qF "pagination_class = None" rules/ultimate_django_coding_standards.md
grep -qF "部品の見直しのイシューを起票する" docs/runbooks/harness-audit.md
! grep -qF "プレーン default" .claude/agents/plan-reviewer.md
! grep -qF "step 3.5" .claude/agents/issue-reviewer.md
! grep -qF "Read / Bash" .claude/agents/code-reviewer.md
grep -qF "(b) の 2 つの一覧" .claude/agents/plan-reviewer.md
! grep -qF "Grep で見出し" .claude/agents/plan-reviewer.md .claude/agents/code-reviewer.md
```
