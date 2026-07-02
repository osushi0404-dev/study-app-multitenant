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
PreToolUse フック `pretooluse_guard.py` に「対象パスが別 worktree ルート配下なら書込を exit 2 でブロック」する判定を追加。Edit/Write/MultiEdit/NotebookEdit と Bash 主要書込経路（`>`/`>>`/`>|`・`tee`・`cp`/`mv` 宛先・`sed -i`）を対象、読み取りは許可。fail-safe・エスケープ無し。settings.json マッチャを明示化し全書込ツールで発火を保証。

## 変更点
- `scripts/claude/hooks/pretooluse_guard.py`: `_worktree_roots`/`_current_worktree_root`/`_cross_worktree`/`_edit_path`/`_split_redir_target`/`_bash_write_targets`/`_has_write_intent`/`_block_cross_worktree` を追加。`main()` の書込ツール分岐（4ツール）と Bash 分岐（danger_ok ゲート外＝エスケープ無し）に横断書込判定を組込。`import os` 追加。
- `.claude/settings.json`: PreToolUse マッチャ `Edit|Write` → `Edit|Write|MultiEdit|NotebookEdit`。
- `scripts/claude/tests/test_pretooluse_worktree_guard.sh`: 新規（26 TC・兄弟名/シンボリックリンク decoy・false-green 注入・回帰）。
- `docs/runbooks/worktree.md`: §9 に技術強制済みを追記。

## 影響範囲
- Backend/Frontend/DB: なし
- Config/Infra: `scripts/claude/hooks/pretooluse_guard.py`・`.claude/settings.json`・`scripts/claude/tests/test_pretooluse_worktree_guard.sh`・`docs/runbooks/worktree.md`

## 実装結果評価
- 計画書 §4/§5 のとおり実装。TDD（Red: 15 fail → Green: 26 PASS）で進行。
- スパイク実証済みの境界一致ロジック（realpath＋末尾 os.sep 接頭辞）を移植し、兄弟名 decoy・シンボリックリンク decoy の両方でブロック挙動が正しいことをテストで確認。
- plan-review 指摘（W1 付着形/埋め込みリダイレクト・Info fail-safe on パス未取得）も実装に反映済み。

## テスト結果
- 自動: `test_pretooluse_worktree_guard.sh` **26/26 PASS**。回帰 `test_pretooluse_checkout_guard.sh`・`test_pretooluse_push_guard.sh` PASS。`py_compile`・`json.tool` OK。pre-commit（shellcheck 含む）PASS。
- 手動:（`/test` 後に記入。TC-M1〜M5 はプレーン default 新規セッションでの実ブロック目視が必要）

## 計画との差分
- なし（plan-review 指摘反映は計画書へ同時更新済みのため計画一致）。

## ロールバック
- settings.json マッチャを `Edit|Write` に戻し、`pretooluse_guard.py` の追加分・新規テスト・runbook 追記を revert すれば従来動作に戻る（DB・外部状態変更なし）。
