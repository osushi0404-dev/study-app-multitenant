# I035 レビュー

## 対象イシュー
I035: Sequential Thinking・Web Search MCP の評価と導入

## レビュー観点

### 受け入れ条件の充足
- [ ] Sequential Thinking MCP の動作確認ができている（または導入不要と判断した根拠が記録されている）
- [ ] Web Search MCP の動作確認ができている（または導入不要と判断した根拠が記録されている）
- [ ] 導入した MCP の設定が `.mcp.json` に追加されている
- [ ] 利用場面が runbook に記載されている

### 設定ファイルの正確性
- [ ] `.mcp.json` の JSON が正しい構文である
- [ ] `.claude/settings.local.json` の `enabledMcpjsonServers` に `sequential-thinking` が追加されている
- [ ] 既存の `github` MCP 設定が壊れていない

### ドキュメントの品質
- [ ] `docs/runbooks/mcp-usage.md` に各 MCP の利用場面が明記されている
- [ ] Web Search 組み込みについて「導入不要と判断した根拠」が計画書に記録されている

### セキュリティ
- [ ] `.mcp.json` に PAT や機密情報が直接記載されていない
- [ ] Sequential Thinking MCP は外部 API キー不要であることが確認されている

## レビュー結果
（実装完了後に記入）

| 項目 | 結果 | 備考 |
|------|------|------|
| 受け入れ条件 | - | |
| 設定ファイル | - | |
| ドキュメント | - | |
| セキュリティ | - | |

**総合判定**: （OK / NG）

## 指摘事項
（あれば記入）
