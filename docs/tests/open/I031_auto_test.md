# I031 自動テスト: issue-flow.md の採番ロジックを issue-bootstrap スキルの実装に統一

対象が docs・スキルファイルのみのため、コードの自動テストは不要。
以下のコマンドで旧ロジックの記述が削除されていることを機械的に確認する。

実行コマンド:
```bash
# 旧採番ロジックのキーワードが残っていないことを確認（0件が期待値）
grep -n "GITHUB_COUNT\|gh issue list.*number\|LOCAL_MAX + GITHUB" docs/runbooks/issue-flow.md
echo "Exit code: $? (1=OK: no matches found)"

# I039 残留ファイルがないことを確認（0件が期待値）
ls docs/tests/open/I039_*.md 2>/dev/null && echo "NG: 残留あり" || echo "OK: 残留なし"
```

結果:
- 旧キーワード検索:
- I039 残留確認:
