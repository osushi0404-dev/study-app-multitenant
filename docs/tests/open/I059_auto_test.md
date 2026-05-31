# 自動テスト: I059 イシューファイルの自己完結度向上（テンプレート＋issue-review サブエージェント）

## テスト方針

変更対象のうち実行可能コードは新規 bash スクリプト `scripts/claude/issue-review.sh` のみ。
これに対し静的解析（shellcheck・正常系）を自動テストとして実施する。
テンプレート・サブエージェント指示・スキルの Markdown、および `claude -p` を伴うレビュー実行自体は
手動テスト（`I059_manual_test.md`）で確認する。

---

## テストケース

| TC | 対象 | コマンド | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|----------|--------|--------|------|
| AT1 | issue-review.sh の shellcheck | `pre-commit run shellcheck --files scripts/claude/issue-review.sh`（ローカルに shellcheck 単体がないため pre-commit 経由） | Passed（警告なし） | Claude | ✅ PASS | implement 時に確認。`shellcheck...Passed` |
| AT2 | issue-review.sh の構文 | `bash -n scripts/claude/issue-review.sh` | 終了コード 0（構文エラーなし） | Claude | ✅ PASS | implement 時に確認。exit=0 |
