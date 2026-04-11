# I035 手動テスト

## 対象イシュー
I035: Sequential Thinking・Web Search MCP の評価と導入

---

## 手動テスト一覧

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `docs/runbooks/mcp-usage.md` を開き、Sequential Thinking MCP が「導入不要」とその根拠が記載されていることを確認する | 評価結果と根拠が明記されている | Human | - | |
| 2 | `docs/runbooks/mcp-usage.md` を開き、Web Search MCP が「導入不要」とその根拠が記載されていることを確認する | 評価結果と根拠が明記されている | Human | - | |
| 3 | `docs/runbooks/mcp-usage.md` に built-in WebSearch の利用場面・使い方・注意事項が記載されていることを確認する | 利用方法が分かりやすく記載されている | Human | - | |
| 4 | Claude に「WebSearch ツールを使って Django の最新バージョンを調べて」と指示する | WebSearch ツールが呼び出され、結果が返ってくる | Human | - | 環境によっては利用不可の場合あり（runbook 記載の注意事項を確認） |
| 5 | `claude mcp list` を実行し、`github` のみが表示され `sequential-thinking` が追加されていないことを確認する | `github` のみ表示される | Human | - | |
