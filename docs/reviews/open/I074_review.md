# I074 レビュー: fix-loop 多段サブエージェントレビュー順次ゲートの導入

## 基本情報
- 関連イシュー: #152 / Draft PR: #194
- 対象計画書: docs/plans/open/plan_I074.md
- レビュー目的: fix-loop に診断/実装/テストの独立サブエージェントレビュー順次ゲートを導入し、誤った診断・方針・影響調査漏れ・不十分なテストのまま次段へ進むのを構造的に防ぐ（I073 由来の予防処置）。
- 期待する成果:
  - SKILL.md に手順3.5（診断）・5.5（実装・fail-safe 再判定含む）・6.5（テスト）が追加され、順次ゲート（`OK` のみ次段・`BLOCKER`＋`HIGH` 差し戻し）・差し戻し導線（診断=停止／実装→手順5／テスト→手順5/6）・連続 NG 上限=2・軽微例外条件・非ブロック skip が明記される。
  - 共有 lib `fix-review-lib.sh` ＋ 3 エントリポイント（`fix-{diagnosis,implementation,test}-review.sh`）が `claude -p`＋`--tools "Read,Grep,Glob"` で起動し VERDICT を解析。
  - 3 reviewer 定義が読み取り専用・prompt-injection ガード付きで新設。
  - `test_fix_review.sh`（TC-01〜23・false-green 反証込み）が green。既存手順1〜7 が非後退。

## 変更概要
（実装後に記入）

## 変更点
（実装後に記入。予定: 新規 `fix-review-lib.sh`・`fix-diagnosis-review.sh`・`fix-implementation-review.sh`・`fix-test-review.sh`・`fix-diagnosis-reviewer.md`・`fix-implementation-reviewer.md`・`fix-test-reviewer.md`・`test_fix_review.sh` ／ 追記 `fix-loop/SKILL.md`）

## 影響範囲
- Backend/Frontend/DB: なし
- Config/Infra: `.claude/skills/fix-loop/SKILL.md`・`.claude/review-agents/fix-{diagnosis,implementation,test}-reviewer.md`・`scripts/claude/fix-review-lib.sh`・`scripts/claude/fix-{diagnosis,implementation,test}-review.sh`・`scripts/claude/tests/test_fix_review.sh`

## テスト結果
- 自動（専用）: `bash scripts/claude/tests/test_fix_review.sh` → **pass=66 fail=0**（TC-01〜25＋07b/12/13/17/24 の false-green 反証含む）。pytest/Jest/E2E は非該当（bash＋md のみ）。
- コードレビュー: **FINAL VERDICT OK**（決定論ゲート exit0 注入・omission-lint OK・高リスク No）。Low 1件（tail-1 反証の明示化）対応済み。
- 手動: Claude 5 項目（No1-4,6）**OK**。特に No3 でライブ `claude -p` により「良い診断→PASS/exit0・不十分な診断→BLOCKER/REMAND/exit1」を実証。No5（SKILL.md 記述品質の目視）は Human 実施待ち。

## 計画との差分
- （実装後に記入）

## ロールバック
- 新設 8 ファイル（lib・3 スクリプト・3 reviewer・test）削除 ＋ SKILL.md 追記分を revert（DB 非関与・非破壊追記のため復元容易）
