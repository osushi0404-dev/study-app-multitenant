# I031 手動テスト: issue-flow.md の採番ロジックを issue-bootstrap スキルの実装に統一

| No | 手順 | 期待結果 | 実結果 | 備考 |
|---:|------|----------|--------|------|
| 1 | `docs/runbooks/issue-flow.md` を開き、「採番ルール」セクションを確認する | `max(FS最大値, git履歴最大値) + 1` のロジックが記載されている | OK | |
| 2 | `grep -n "GITHUB_COUNT\|gh issue list" docs/runbooks/issue-flow.md` を実行する | 0件（マッチなし） | OK | 旧ロジック削除確認 |
| 3 | 採番ロジックのコードブロックが `find docs/issues` と `git log --all` を使用していることを確認する | 両コマンドが記載されている | OK | |
| 4 | 記載ロジックで手動採番をシミュレーション: `find` で FS最大、`git log` で git履歴最大を取得し、大きい方 + 1 を計算する | `issue-bootstrap` スキル実行結果と同じ番号になる | OK | |
| 5 | 旧採番ロジックの記述が 3 箇所すべて（採番ルールセクション・自動実行フロー・フェーズ1ステップ1）で置換されていることを確認する | 3 箇所すべて新ロジックになっている | OK | |
| 6 | `ls docs/tests/open/` を実行し I039 のファイルがないことを確認する | `I039_auto_test.md`・`I039_manual_test.md` が存在しない | OK | |
| 7 | `ls docs/tests/closed/` を実行し I039 のファイルがあることを確認する | `I039_auto_test.md`・`I039_manual_test.md` が存在する | OK | |
| 8 | `.claude/skills/close/SKILL.md` の `# テストケース` 行を確認する | `auto_test・manual_test の両ファイルを一括移動` などの説明が追記されている | OK | |

結論: OK
