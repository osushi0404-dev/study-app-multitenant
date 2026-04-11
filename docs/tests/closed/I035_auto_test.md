# I035 自動テスト

## 対象イシュー
I035: Sequential Thinking・Web Search MCP の評価と導入

---

## 自動テスト一覧

| No | テスト内容 | コマンド | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|-----------|---------|---------|--------|--------|------|
| 1 | `docs/runbooks/mcp-usage.md` が存在すること | `test -f docs/runbooks/mcp-usage.md && echo OK` | `OK` | Claude | OK | |
| 2 | `mcp-usage.md` が空でないこと | `wc -l docs/runbooks/mcp-usage.md` | 1 行以上 | Claude | OK（120行） | |
| 3 | `.mcp.json` に `sequential-thinking` が含まれていないこと（設定変更なし確認） | `python3 -c "import json; d=json.load(open('.mcp.json')); assert 'sequential-thinking' not in d['mcpServers'], 'unexpected entry'"` | エラーなし（終了コード 0） | Claude | OK | |
| 4 | `.mcp.json` に `github` が含まれていること（既存設定が壊れていない確認） | `python3 -c "import json; d=json.load(open('.mcp.json')); assert 'github' in d['mcpServers']"` | エラーなし（終了コード 0） | Claude | OK | |
| 5 | `.mcp.json` JSON 構文チェック | `python3 -m json.tool .mcp.json` | エラーなし | Claude | OK | |
| 6 | `.claude/settings.local.json` JSON 構文チェック | `python3 -m json.tool .claude/settings.local.json` | エラーなし | Claude | OK | |
