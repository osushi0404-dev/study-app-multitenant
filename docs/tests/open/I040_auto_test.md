# I040 自動テスト

## テスト対象
- `.claude/skills/grill-me/SKILL.md`（新規作成）
- `docs/runbooks/workflow.md`（追記）

## 自動テスト方針

スキルファイル（プロンプト定義）とドキュメントの変更のため、pytest / Jest による自動テスト対象外。

手動テストのみで検証する（`I040_manual_test.md` 参照）。

## 静的チェック

| No | チェック内容 | 手順 | 期待結果 | 実施者 | 実結果 |
|---:|------------|------|----------|--------|--------|
| 1 | grill-me SKILL.md の存在確認 | `cat .claude/skills/grill-me/SKILL.md` | ファイルが存在し、Markdown 構文が正しい | Claude | |
| 2 | フロントマターの確認 | SKILL.md の先頭を確認 | `name`, `description`, `argument-hint`, `disable-model-invocation: true`, `allowed-tools` がすべて設定されている | Claude | |
| 3 | workflow.md への追記確認 | `grep -n "grill-me" docs/runbooks/workflow.md` | スキル一覧・フロー図・移行テーブルの3箇所に `/grill-me` が記載されている | Claude | |
