# I098 レビュー: 全 worktree 横断採番スクリプトへの一元化

## 基本情報
- 関連イシュー: #184 / Draft PR: #188
- 対象計画書: docs/plans/open/plan_I098.md
- レビュー目的: 採番の全 worktree 横断化により二重採番を根治し、採番権威を単一化する。人手規律（primary で採番）への依存を撤廃する。
- 期待する成果:
  - `scripts/claude/next-issue-num.sh` が全 worktree 横断＋git 履歴で一意番号を算出（再現ケース回避）。
  - 採番 bash の重複 4 箇所がスクリプト呼び出しに一元化。
  - worktree.md §8 の人手規律撤廃。
  - I094 decoy 反証を含む決定論テストが green。

## 変更概要
（実装後に記入）

## 変更点
（実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config/Infra: `scripts/claude/next-issue-num.sh`（新規）・`scripts/claude/tests/test_next_issue_num.sh`（新規）・`docs/runbooks/issue-flow.md`・`docs/runbooks/worktree.md`・`.claude/skills/issue-bootstrap/SKILL.md`

## テスト結果
- 自動: （実装後に記入・TC-N1〜N6・TC-DOC1〜4）
- 手動: （実装後に記入）

## 計画との差分
- なし / あり（理由）

## ロールバック
- 新規 2 ファイル削除 ＋ 文書 3 ファイルを revert（DB 非関与）
