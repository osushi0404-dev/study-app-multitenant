# I035 自動テスト

## 対象イシュー
I035: Sequential Thinking・Web Search MCP の評価と導入

---

## 自動テスト一覧

| No | テスト内容 | コマンド | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|-----------|---------|---------|--------|--------|------|
| 1 | `.mcp.json` JSON 構文チェック | `python3 -m json.tool .mcp.json` | エラーなし | Claude | - | |
| 2 | `.claude/settings.local.json` JSON 構文チェック | `python3 -m json.tool .claude/settings.local.json` | エラーなし | Claude | - | |
| 3 | `sequential-thinking` が `.mcp.json` に含まれること | `python3 -c "import json; d=json.load(open('.mcp.json')); assert 'sequential-thinking' in d['mcpServers']"` | エラーなし（終了コード 0） | Claude | - | |
| 4 | `sequential-thinking` が `enabledMcpjsonServers` に含まれること | `python3 -c "import json; d=json.load(open('.claude/settings.local.json')); assert 'sequential-thinking' in d['enabledMcpjsonServers']"` | エラーなし（終了コード 0） | Claude | - | |
| 5 | `docs/runbooks/mcp-usage.md` が存在すること | `test -f docs/runbooks/mcp-usage.md && echo OK` | `OK` | Claude | - | |
| 6 | `mcp-usage.md` が空でないこと | `wc -l docs/runbooks/mcp-usage.md` | 1 以上 | Claude | - | |
