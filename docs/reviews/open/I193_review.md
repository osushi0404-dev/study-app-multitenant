# I193 レビュー: 開発の流れを公式の道具を土台に組み直す

## 変更概要
- 公式の道具を土台にした流れの設計書 `docs/proposals/I193_official_base_flow.md`
- 同名スキルの改名（`code-review`→`review-gate`・`security-review`→`design-security-review`・`test`→`test-gate`・`plan-issue-review`→`plan-review`）と、段階のスキル化（`user-invocable: false`）
- レビュー役 7 本を `.claude/agents/` へ移し、`tools: Read, Grep, Glob`・`claude -p --agent`・`timeout` で呼ぶ
- レビュー段階で組み込み `/code-review`（高リスク時は `/security-review`）を実行し、自作レビュー役が判定に取り込む
- 段階のつなぎ（`STAGE_DONE:`・`flow-stage.sh`・`gate-check.sh`）と `/proceed`
- 承認待ちをなくし、止めて聞く 3 条件にそろえる（CLAUDE.md・runbook・スキル）
- ハーネスのテストを CI で動かす（`run-all.sh`・`Harness Tests` ジョブ）と、落ちていた 2 本の修正

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/skills/`・`.claude/agents/`（`.claude/review-agents/` から移動）・`scripts/claude/`・`scripts/claude/tests/`・`.github/workflows/ci.yml`・`CLAUDE.md`・`docs/runbooks/`・`docs/*/templates/`・`docs/claude-code-structure.md`・`docs/proposals/I193_official_base_flow.md`

## テスト結果
- （/test 時に記入）

## 計画との差分
- （実装後に記入）

## ロールバック
- ステップごとのコミットを `git revert`（改名は `git mv` なので元に戻る）。必須チェックに登録した `Harness Tests` は、ユーザーがブランチ保護の設定から外す
