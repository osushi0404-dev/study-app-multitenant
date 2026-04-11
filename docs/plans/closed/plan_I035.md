# plan_I035: Sequential Thinking・Web Search MCP の評価と導入

## 基本情報
- **計画書ID**: plan_I035
- **関連イシュー**: #79
- **作成根拠資料**: docs/proposals/I026_ai_dev_improvement_proposal.md（改善案 D）
- **実装後評価**: （未作成）
- **作成日**: 2026-04-11

---

## 背景/目的

I026 改善提案の改善案 D として、以下 2 つの MCP の評価・導入検討を行う。

- **Sequential Thinking MCP**: 複雑な問題での推論過程の構造化
- **Web Search MCP**: Claude の知識カットオフ以降の情報のリアルタイム参照

---

## 受け入れ条件（Acceptance Criteria）

- [ ] Sequential Thinking MCP の動作確認ができている（または導入不要と判断した根拠が記録されている）
- [ ] Web Search MCP の動作確認ができている（または導入不要と判断した根拠が記録されている）
- [ ] 導入した MCP の設定が `.claude/` 配下または `.mcp.json` に追加されている（導入不要の場合は根拠を記録）
- [ ] 利用場面が runbook に記載されている

---

## 影響範囲

- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `docs/runbooks/mcp-usage.md`（新規）のみ。設定ファイル変更なし

---

## 調査結果

### 環境前提確認

| ツール | バージョン | 状態 |
|--------|-----------|------|
| Node.js | v24.14.1 | ✅ インストール済み |
| npx | 11.11.0 | ✅ インストール済み |

### Sequential Thinking MCP 評価

| 項目 | 内容 |
|------|------|
| パッケージ | `@modelcontextprotocol/server-sequential-thinking` |
| 最新バージョン | 2025.12.18 |
| 起動確認 | `npx -y @modelcontextprotocol/server-sequential-thinking` → 起動は成功 |
| **評価結果** | **導入不要** |

**導入不要と判断した根拠:**

1. **Claude 4.x では冗長** — このMCPはClaude 2/3向けの補助ツールとして設計された。Claude claude-sonnet-4-6（本プロジェクト使用中）はモデル内部で高精度の段階的推論を行っており、外部ツールで補う必要がない
2. **供給チェーンリスク** — バージョン未固定（`npx -y`）で実行すると、パッケージの悪意ある更新が自動適用されるリスクがある。既存の GitHub MCP は `@2025.4.8` と固定しており、一貫性がなく安全でない
3. **依存増加のコスト超過** — 実質的な品質向上なしに npm 依存・保守コスト・攻撃面が増加する

### Web Search MCP 評価

| 項目 | 内容 |
|------|------|
| 候補パッケージ | `@modelcontextprotocol/server-brave-search`（API キー要） |
| **評価結果** | **導入不要** |

**導入不要と判断した根拠:**

1. **built-in WebSearch ツールが利用可能** — Claude Code には `WebSearch` ツールが組み込み機能として存在し、追加 MCP なしで Web 検索が可能
2. **外部 API キー管理不要** — Brave Search MCP 等を導入すると API キーの発行・環境変数管理・ローテーション運用が必要になり、セキュリティリスクと運用コストが増加する
3. **重複によるデメリット** — 同等機能の二重化は設定の複雑性を上げるだけ

**注意事項（runbook に明記する）:**
- `WebSearch` ツールは Claude Code の環境によって利用不可の場合がある（claude.ai/code では利用可能、CLI 環境では設定依存）
- 利用不可の場合のフォールバック手順を runbook に記載する

### 現在の MCP 設定状況（変更なし）

`.mcp.json`:
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github@2025.4.8"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}" }
    }
  }
}
```

---

## 変更点一覧

| ファイル | 変更内容 |
|---------|---------|
| `docs/runbooks/mcp-usage.md` | 新規作成: MCP 一覧・評価結果・利用場面・Web Search 使い方と注意事項 |

設定ファイル（`.mcp.json`、`settings.local.json`）は変更しない。

---

## 実装手順

### ステップ 1: `docs/runbooks/mcp-usage.md` を新規作成

以下の内容で作成する:

1. **MCP 一覧と評価結果**
   - GitHub MCP: 導入済み（I030 で設定済み）
   - Sequential Thinking MCP: 評価済み・導入不要（Claude 4.x では冗長・供給チェーンリスクあり）
   - Web Search MCP: 評価済み・導入不要（built-in WebSearch で対応）

2. **built-in WebSearch の使い方**
   - 利用方法（Claude に指示する形式）
   - 利用場面（`/plan-issue` でのライブラリバージョン確認・CVE 確認等）
   - 注意事項（環境依存・情報の最終確認は公式ドキュメントで行う）

3. **GitHub MCP の利用場面**（`mcp-github-setup.md` への参照）

4. **将来の MCP 追加指針**
   - 追加前に評価すべき観点（供給チェーンリスク・バージョン固定・代替手段の有無等）

---

## テスト計画

### 自動テスト
- `docs/runbooks/mcp-usage.md` のファイル存在確認
- `.mcp.json` が変更されていないこと（GitHub MCP のみ含まれること）の確認

### 手動テスト
- `docs/runbooks/mcp-usage.md` の内容確認（評価結果・利用場面が記載されているか）
- Claude に `WebSearch` ツールで Web 検索させて動作確認

---

## ロールバック

`docs/runbooks/mcp-usage.md` の削除のみ。設定ファイル変更がないため、設定のロールバックは不要。

---

## Risk & 回避策

| リスク | 影響 | 回避策 |
|--------|------|--------|
| WebSearch ツールが CLI 環境で使えない | Web 検索ができない | runbook にフォールバック手順（手動での公式サイト確認）を記載 |
| 将来 MCP が必要になった際に評価フローが不明確 | 場当たり的な MCP 追加によるリスク増 | runbook に MCP 追加前の評価観点を明記 |

---

## セキュリティ影響

- 設定ファイル変更なし
- runbook（ドキュメント）追加のみ
- **セキュリティ影響なし**

---

## 承認ポイント（ユーザー確認事項）

### 設計判断の明示

| 判断項目 | 判断内容 | 根拠区分 |
|---------|---------|---------|
| Sequential Thinking MCP を追加しない | Claude 4.x で冗長・供給チェーンリスク | 調査結果 |
| Web Search MCP を追加しない | built-in WebSearch で対応・API キー管理不要 | 調査結果 |
| 実装内容は runbook 整備のみ | 設定ファイル変更なし | 上記判断から導出 |
| runbook は `mcp-usage.md` として新規作成 | `mcp-github-setup.md` と同パターン | **仮定**（既存ファイルへの追記でもよい） |

### チェックリスト

- [ ] 両 MCP とも「導入不要」という評価結果に同意する
- [ ] 実装内容を「runbook 整備のみ」に絞ることに同意する
- [ ] `docs/runbooks/mcp-usage.md` を新規作成することに同意する（または既存ファイルへの追記を指示する）
