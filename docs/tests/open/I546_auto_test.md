# I546 自動テスト: 進め方の決まり（docs/runbooks・CLAUDE.md・記憶）の BP 見直し

実行コマンド（例）: 手順書の文字を読むテストは下の決定論ゲート。pytest・Jest・E2E はアプリの変更が無いので CI に任せる（`bash scripts/claude/tests/run-all.sh` も CI が流す）

結果:
- backend: 変更なし（CI）
- frontend: 変更なし（CI）

## 方針
- 今回の変更は文書と、文書の文字を見るテストの期待だけ。新しいテストのスクリプトは足さない（消した節・移した節は意図的な変更でしか戻らない・`docs/runbooks/plan-writing-rules.md`「決定論テストの対象の選び方」）
- 守るのは「直した後も、手順書の文字を読む既存のテストがすべて合格すること」（TC-01）と、受け入れ条件のうち文字で確かめられる 2 点（TC-02・TC-03）
- `scripts/claude/tests/test_i193_official_flow.sh` は下のゲートに入れない。手元では F9 の 3 項目（`run-all.sh` の動き）が、手元の道具の版の違い（`check-tools.sh` が PyYAML 6.0.1／正 6.0.3・pre-commit 4.5.1／正 4.7.0 で止める）で got=2 になり、文書と関係なく不合格になるため。i193 は CI の `run-all.sh`（uv が uv.lock の版を入れる）が全項目を流す

## テストケース
| TC | 内容 | 合格の条件 | 実装前の結果（2026-11-17） |
|---|---|---|---|
| TC-01 | 手順書の文字を読む既存のテスト 20 本（下のゲートの `bash scripts/claude/tests/*.sh`）が、書き換えの後も合格する | 全部 exit 0 | 20 本とも exit 0（基準）。i193 は F9 の 3 項目だけ不合格（上の方針のとおり環境の都合・CI で見る） |
| TC-02 | `CLAUDE.md` に「Cursor 経由」が無い（AC6） | `! grep -q` が exit 0 | exit 1（実装前は有るので不合格。失敗の注入の確認） |
| TC-03 | `docs/runbooks/ux-rules.md` に「流れの途中」の決まりがある（AC8） | `grep -q` が exit 0 | exit 1（実装前は無いので不合格。失敗の注入の確認） |

## FG（失敗の注入）の実行記録
- 2026-11-17 計画時: TC-02・TC-03 を実装前のファイルに対して `bash -c` で流し、どちらも exit 1（不合格）になることを確かめた（実装前の状態が失敗の注入にあたる）
- TC-01: 既存のテストはそれぞれのテストの中に FG を持つ（例: i193 の FG-D4・i181 の D 系）。直した項目には、その項目の FG が残っていることを確かめる

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_adversarial_trigger.sh
bash scripts/claude/tests/test_check_permission_prompt.sh
bash scripts/claude/tests/test_guard_must_stop_cases.sh
bash scripts/claude/tests/test_i107_track_label_docs.sh
bash scripts/claude/tests/test_i109_dependency_audit.sh
bash scripts/claude/tests/test_i179_worktree_docs.sh
bash scripts/claude/tests/test_i181_review_slim.sh
bash scripts/claude/tests/test_i182_docs.sh
bash scripts/claude/tests/test_i185_harness_docs.sh
bash scripts/claude/tests/test_i197_adversarial_process.sh
bash scripts/claude/tests/test_i197_review_ledger.sh
bash scripts/claude/tests/test_i202_ledger_cleanup.sh
bash scripts/claude/tests/test_i205_stop_criteria.sh
bash scripts/claude/tests/test_i223_gh_app.sh
bash scripts/claude/tests/test_i224_push_points.sh
bash scripts/claude/tests/test_i463_guard_optspec.sh
bash scripts/claude/tests/test_pretooluse_container_guard.sh
bash scripts/claude/tests/test_pretooluse_push_guard.sh
bash scripts/claude/tests/test_review_commit_lifecycle.sh
bash scripts/claude/tests/test_review_verdict.sh
! grep -q "Cursor 経由" CLAUDE.md
grep -q "流れの途中" docs/runbooks/ux-rules.md
```
