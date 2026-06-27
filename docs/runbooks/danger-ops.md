# 危険操作（Danger Ops）ルール

以下は原則「計画書に明記」＋「ユーザー明示承認」＋「PRに danger-approved」＋「実行時 DANGER_OK=1」でのみ実行する。

## 例
- DB: DROP / TRUNCATE / WHEREなし UPDATE・DELETE / 大量更新・削除 / 破壊的マイグレーション
- Git: force push / reset --hard / 大規模rebase / **未コミット変更があるファイルへの `git checkout/restore <file>`**（下記注記）
- Docker: down -v / --volumes（データ消失）
- Files: rm -rf / secrets 操作

## 未コミット変更の取り消し（`git checkout/restore <file>`）

作業ツリーに**未コミット変更があるファイル**の一時変更を取り消す際、`git checkout/restore <file>` を使わない。同ファイルの未コミット分も HEAD に戻り**消失**する（一時的なテスト注入を戻すつもりが、未コミットの実装ごと失う事故になる）。

- 一時変更は **Edit ツールで元に戻す**（取り消したい行だけをピンポイントで復元する）。
- clean なファイルの revert やブランチ切替（`git checkout <branch>` / `-b` / `git switch`）は通常どおり可。
- PreToolUse フック（`scripts/claude/hooks/pretooluse_guard.py`）が、未コミット変更があるファイルへの `git checkout/restore <file>` を `DANGER_OK=1` 無しでブロックする。どうしても必要な場合のみ `DANGER_OK=1` を前置する。

## 実行テンプレ
- 影響範囲:
- 代替案:
- ロールバック:
- 実行コマンド（DANGER_OK=1 付き）:
