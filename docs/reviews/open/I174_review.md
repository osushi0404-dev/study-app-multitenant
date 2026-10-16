# I174 レビュー: 確認が必要な操作の見直し（docker compose exec 等の一律確認をやめ、コンテナ内の危険操作だけを見張りで止める）

- 関連: docs/issues/open/I174.md / docs/plans/open/plan_I174.md / GitHub #292 / Draft PR #293

## 変更概要
- （実装後に記入）

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/settings.json`・`scripts/claude/hooks/pretooluse_guard.py`・`scripts/claude/tests/test_pretooluse_*.sh`・`docs/runbooks/danger-ops.md`（新しいセッションから全セッションに効く）

## テスト結果
- 自動: （/test 後に記入）
- 手動: （/test 後に記入）

## 計画との差分
- （実装後に記入）

## 気づいた点（本イシューの範囲外）
- `DANGER_OK=1 bash scripts/claude/wt-remove.sh <track>` の中の `docker compose down -v` は、guard から見えない（スクリプト自身が DANGER_OK=1 を要求する既存の挙動）。DANGER_OK=1 を付けると人の承認なしで実行される（計画書 R7）
- `pretooluse_guard.py:437` の `\bdd\b` は、`dd` という単語（例: ファイル名やブランチ名）にも反応する止めすぎ（計画書 R8）

## ロールバック
- PR を revert する。一時的には `.claude/settings.json` の ask に `Bash(docker compose exec *)` などを戻し、セッションを開き直す
