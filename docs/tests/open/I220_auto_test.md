# I220 自動テスト: イシューの起票は Claude が実行して事後に報告する決まり

実行コマンド（例）: なし（アプリのコード変更なし。pytest・Jest・E2E は CI が流す）

結果:
- backend: 対象外
- frontend: 対象外

## テストケース
| TC | 内容 | 合否の判定 | 結果 |
|---|---|---|---|
| TC-01 | この変更が触る文を見ている既存のテスト 4 本（`test_i193_official_flow.sh`・`test_i185_harness_docs.sh`・`test_i107_track_label_docs.sh`・`test_i179_worktree_docs.sh`）が合格する | 各スクリプトが exit 0（下の決定論ゲート） | 実装前のベースライン（2026-10-30・feature/I220 の 86b53400）: 4 本とも exit 0（174/17/6/16 件合格）。実装後は review-gate が流す |
| TC-02 | 固定の文章の作り直し（`test_i185_harness_docs.sh --update`）で変わったのが `scripts/claude/tests/fixtures/i185/workflow_stop_guidance.txt` だけ | review-gate の差分のレビューで読む（`git diff --name-only origin/develop -- scripts/claude/tests/fixtures/` が 1 本だけ） | 実装前のため未実行 |

新しい決定論テストは作らない（plan_I220.md §9: 手順書・スキルの文言は意図的な変更でしか消えず、レビューで見る。効き目は手動テスト M-03・M-04 の `claude -p` の実走で確かめる）。

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i193_official_flow.sh
bash scripts/claude/tests/test_i185_harness_docs.sh
bash scripts/claude/tests/test_i107_track_label_docs.sh
bash scripts/claude/tests/test_i179_worktree_docs.sh
```
