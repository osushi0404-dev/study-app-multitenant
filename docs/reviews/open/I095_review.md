# I095 レビュー: 別 worktree 配下への編集ハードブロック

## 基本情報
- **関連イシュー**: #181
- **対象計画書**: docs/plans/open/plan_I095.md
- **Draft PR**: #185
- **作成日**: 2026-07-02

## レビュー目的
worktree 横断の直接書込を PreToolUse フックで技術強制ブロックする実装が、計画書どおりに・誤ブロックなく・回帰なく行われたかを検証する。特に以下を重点確認する:
- 別 worktree 配下の書込ブロック（Edit/Write/MultiEdit/NotebookEdit・Bash 主要書込）と読み取り許可の両立
- 兄弟名部分一致 decoy で誤ブロックしないこと（境界一致の厳密性）
- fail-safe（境界確定不能時ブロック）・エスケープ無し（DANGER_OK 非解除）
- 既存ガード（push/checkout/高リスク）の非回帰
- 決定論テストが false-green でない（注入で NG になる）こと

## 期待する成果
- AC 全項目を満たす
- 自動テスト（`test_pretooluse_worktree_guard.sh` ＋既存2テスト）ALL PASS
- 手動テスト（プレーン新規セッションでの実ブロック目視）OK

## 変更概要
（実装後に記入）

## 変更点
（実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config/Infra: `scripts/claude/hooks/pretooluse_guard.py`・`.claude/settings.json`・`scripts/claude/tests/test_pretooluse_worktree_guard.sh`・`docs/runbooks/worktree.md`

## 実装結果評価
（実装後に記入）

## テスト結果
- 自動:（実装後に記入）
- 手動:（テスト後に記入）

## 計画との差分
- なし / あり（理由）（実装後に記入）

## ロールバック
- settings.json マッチャを `Edit|Write` に戻し、`pretooluse_guard.py` の追加分・新規テスト・runbook 追記を revert すれば従来動作に戻る（DB・外部状態変更なし）。
