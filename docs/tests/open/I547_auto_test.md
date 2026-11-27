# I547 自動テスト: レビュー役 5 つの指示の BP 見直し

実行コマンド（例）: 定義の文字を読むテストは下の決定論ゲート。pytest・Jest・E2E はアプリの変更が無いので CI に任せる（`bash scripts/claude/tests/run-all.sh` も CI が流す）

結果:
- backend: 変更なし（CI）
- frontend: 変更なし（CI）

## 方針
- 今回の変更は文書と、`test_i181_review_slim.sh` の D9 の読む場所だけ。新しいテストのスクリプトは足さない（前置きの制約は既存の `test_i593_review_from_base.sh` の TC-03 が守り、ほかは意図的な変更でしか戻らない・`docs/runbooks/plan-writing-rules.md`「決定論テストの対象の選び方」）
- 守るのは「直した後も、定義の文字を読む既存のテスト 11 本がすべて合格すること」（TC-01。前置きが入口の変換を通ること・出力の形を含む）と、受け入れ条件のうち文字で確かめられる点（TC-02〜TC-05）
- TC-04・TC-05 は文言の有無を見るので、この PR の実装の確かめだけに使う（常設のテストのスクリプトにはしない・`plan-writing-rules.md`「決定論テストの対象の選び方」）

## テストケース
| TC | 内容 | 合格の条件 | 実装前の結果（2026-11-27） |
|---|---|---|---|
| TC-01 | 定義の文字を読む既存のテスト 11 本（下のゲートの `bash scripts/claude/tests/*.sh`）が書き換えの後も合格する。`test_i593_review_from_base.sh` の TC-03 は本物の 5 つの定義を入口の変換に通す（R1） | 全部 exit 0 | 11 本とも exit 0（基準） |
| TC-02 | 高リスク判定の条件の一覧が `review-rules.md` の 1 か所だけにあり、レビュー役の定義に写しが無い（AC4・PR15・CR9） | exit 0 | exit 1（実装前は 2 つの定義にあり、review-rules に無い。失敗の注入の確認） |
| TC-03 | `review-rules.md` に「## 高リスク判定の条件」の節がある（PR15） | exit 0 | exit 1（実装前は無い） |
| TC-04 | 同梱 A・B・D・E・F の観点が定義にある（AC3） | exit 0 | exit 1（実装前は無い） |
| TC-05 | 古い言い方（「プレーン default」・「step 3.5」・「Read / Bash」）が定義に無い（AC2・PR5・IR1・CR1） | exit 0 | exit 1（実装前は有る） |

## 実行記録
-

## FG（失敗の注入）の実行記録
- 2026-11-27 計画時: TC-02〜TC-05 を実装前のファイルに対して流し、4 つとも exit 1（不合格）になることを確かめた（実装前の状態が失敗の注入にあたる）。計画レビューの後、ゲートを 1 語ずつの 13 行に分けて 1 行ずつ流し直し、13 行とも exit 1 を確かめた
- TC-01: 既存のテストはそれぞれのテストの中に FG を持つ（例: i181 の FG-D9・i593 の FG-TC-03）。D9 の読む場所を移した後も FG-D9 が不合格を出すこと（`FG-D9` の行が PASS）を実装の後に記録する

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
bash -c '[ "$(grep -l "画面制御していてもAPI直叩きで事故りうる変更" .claude/agents/*.md | wc -l)" -eq 0 ]'
grep -qF "画面制御していてもAPI直叩きで事故りうる変更" docs/runbooks/review-rules.md
grep -qx "## 高リスク判定の条件" docs/runbooks/review-rules.md
grep -qF "流れの途中" .claude/agents/plan-reviewer.md
grep -qF "§16" .claude/agents/plan-reviewer.md
grep -qF "まだ無いデータ" .claude/agents/plan-reviewer.md
grep -qF "設計確認メモ（grill-me の回答）に根拠" .claude/agents/plan-reviewer.md
grep -qF "§16" .claude/agents/code-reviewer.md
grep -qF "まだ無いデータ" .claude/agents/code-reviewer.md
grep -qF "docs/runbooks/ux-rules.md" .claude/agents/code-reviewer.md
! grep -qF "プレーン default" .claude/agents/plan-reviewer.md
! grep -qF "step 3.5" .claude/agents/issue-reviewer.md
! grep -qF "Read / Bash" .claude/agents/code-reviewer.md
```
