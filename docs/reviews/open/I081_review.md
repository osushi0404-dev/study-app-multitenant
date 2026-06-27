# I081 実装レビュー（計画段階・実装後に記入）

- 関連イシュー: #161
- 計画書: docs/plans/open/plan_I081.md
- PR: #163

## レビュー対象
- `scripts/claude/hooks/pretooluse_guard.py`: Bash 経路に「未コミット変更があるファイルへの `git checkout/restore <file>` を `DANGER_OK=1` 無しで `exit 2` block」する判定（ヘルパ `_worktree_dirty`/`_revert_targets`/`_git_revert_target_on_dirty`）を追加。既存の危険 bash `exit 2` は維持。
- `scripts/claude/tests/test_pretooluse_checkout_guard.sh`: 新規・決定論テスト（temp git repo）。
- `docs/runbooks/common-commands.md`: Bash 実行作法（原則単体・複合/パイプ/heredoc 禁止・Read 閲覧・例外許容）の明文化＋`danger-ops.md` 相互参照。
- `docs/runbooks/danger-ops.md`: 未コミット変更ファイルへの `git checkout/restore` のデータ消失注意。
- `.claude/review-agents/code-reviewer.md` / `plan-reviewer.md`: コマンド衛生・破壊的取り消しの gate 観点追加。

## レビュー観点（実装後に [x] 化）
- [ ] フックが dirty ファイルへの `git checkout/restore <file>` を `exit 2` block（TC-G3/G4/G5）
- [ ] clean ファイル・ブランチ切替（`<branch>`/`-b`/`git switch`）・untracked・`restore --staged` は素通し（TC-G1/G2/G6/G8a/G8b）
- [ ] `DANGER_OK=1` 前置で迂回可（TC-G7）
- [ ] 判定が失敗注入で NG＝false-green でない（TC-G-FALSEGREEN・TC-G1↔G3 対検証）
- [ ] トークナイズが `shlex.split()` で空白パスも検出（沈黙の穴なし・TC-G10）
- [ ] 危険 bash の `exit 2` ハードブロック維持（TC-G9）
- [ ] `subprocess` はリスト引数（shell=False）でコマンドインジェクションなし
- [ ] runbook に実行作法（原則単体・例外許容）・相互参照が明記（TC-D1〜D3）
- [ ] review-agents に gate 観点追加（TC-D4）
- [ ] 追記文言にイシュー番号が含まれない（TC-D5）
- [ ] `.claude/settings.json` の permissions を変更していない（I080 スコープ・本 PR で触らない）
- [ ] 計画外の変更なし

## 自動テスト結果
- **/implement（TDD・2026-06-28）**: `test_pretooluse_checkout_guard.sh` → **pass=14 fail=0**（TC-G1〜G11・FALSEGREEN）。Red→Green を確認（false-green でない）。
- TC-D1〜D5（runbook/review-agent 文言・イシュー番号不在）: **PASS**
- 既存 Edit/Write ask 経路・危険 bash exit2 の非退行: **PASS**（TC-G9・requirements.txt→ask）

## 手動テスト結果（/test 時に記入）
- 統合挙動（実セッションでの block/素通し）: ⏳

## 総合判定
- （コードレビュー後に記入）
