# I035 手動テスト

## 対象イシュー
I035: Sequential Thinking・Web Search MCP の評価と導入

---

## 手動テスト一覧

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | Claude Code を完全に再起動する | 正常起動する | Human | - | |
| 2 | `claude mcp list` を実行する | `sequential-thinking` が一覧に表示され、ステータスが `connected` である | Human | - | |
| 3 | `github` MCP が引き続き `connected` であることを確認する | `github` が `connected` で表示される | Human | - | |
| 4 | Claude に「sequentialthinking ツールを使って何か簡単な問題を段階的に考えて」と指示する | `sequentialthinking` ツールが呼び出され、思考ステップが表示される | Human | - | |
| 5 | Claude に「WebSearch ツールを使って Django 最新バージョンを調べて」と指示する | WebSearch ツールが呼び出され、最新バージョン情報が返ってくる | Human | - | |
| 6 | `docs/runbooks/mcp-usage.md` を開き、Sequential Thinking MCP と Web Search の利用場面が記載されていることを確認する | 各 MCP の利用場面・使い方が分かりやすく記載されている | Human | - | |
