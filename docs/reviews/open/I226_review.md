# I226 レビュー: I225 のレビューの残り: 失効の確かめの取り違え・鍵を出す書き方の検査の狭さ

## 変更概要
- F1: `revoke.sh` が失効の前に鍵の有効を確かめ、もともと無効な鍵を「失効を確認」と出さない
- F6: G10 が `gh auth token` を落とし、行末の `\` で分けた `--json` 付きの書き方を通す
- 同梱: F2（ログインなしの `auth status` の置き換えを exit 1 に）・F4（`plan-writing-rules.md` の記述）・omission-lint を自動テスト文書を書いた直後に PostToolUse のフックで流す
- F5 は grill-me で見送り

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `scripts/claude/gh-app/revoke.sh`・`scripts/claude/gh-app/gh`・`scripts/claude/code-review.sh`・`scripts/claude/hooks/posttooluse_check.py`・`scripts/claude/tests/test_i223_gh_app.sh`・`scripts/claude/tests/test_posttooluse_check.sh`・`docs/runbooks/github-app-setup.md`・`docs/runbooks/plan-writing-rules.md`・`docs/reviews/backlog/I225.md`・`CLAUDE.md`

## テスト結果
- 自動: （test-gate で記入）
- 手動: （test-gate で記入）

## 計画との差分
- （実装後に記入）

## ロールバック
- PR を revert する。手元の入口を入れ直していれば `bash scripts/claude/gh-app/install.sh` をもう一度流す

## 自律判断の記録
- [plan] omission-lint を流す場所を PostToolUse のフックにした — pre-commit は CI の `--all-files` で古い open の I034 が落ち、避けると `ci.yml` も直すことになり高リスクのパスに当たる。スキルの手順は流し忘れる。フックは決定論で最も早く、高リスクのパスでない（plan_I226.md §9）
- [plan] F2 は終了コードだけ直す — スパイクで本物の `gh` が「ログインしていない」の案内を標準エラーに出すことを確かめた（文を足すと 2 回出る）
