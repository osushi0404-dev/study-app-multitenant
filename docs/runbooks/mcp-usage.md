# MCP 利用ガイドライン

このプロジェクトで評価・導入した MCP（Model Context Protocol）サーバーの一覧と、利用場面・使い方を記載する。

---

## 1. MCP 一覧と評価結果

| MCP | 評価結果 | 根拠 |
|-----|---------|------|
| GitHub MCP | ✅ 導入済み（I030） | PR/issue 高度操作の実現。`docs/runbooks/mcp-github-setup.md` 参照 |
| Sequential Thinking MCP | ❌ 導入不要（I035） | Claude 4.x では冗長。供給チェーンリスクあり（詳細は後述） |
| Web Search MCP | ❌ 導入不要（I035） | built-in `WebSearch` ツールで対応可能。外部 API キー管理不要 |

---

## 2. built-in WebSearch ツール

### 概要

Claude Code には `WebSearch` ツールが組み込み機能として存在し、追加 MCP なしでリアルタイムの Web 検索が可能。

### 利用場面

| フェーズ | 利用例 |
|---------|-------|
| `/plan-issue` | 使用ライブラリの最新バージョン確認 |
| `/plan-issue` | CVE・既知脆弱性の確認（`pip-audit` 補完として） |
| `/plan-issue` | Django・React の最新推奨パターン確認 |
| `/fix-loop` | エラーメッセージの最新情報・Stack Overflow 調査 |

### 使い方

Claude に自然言語で指示する:

```
WebSearch ツールを使って Django REST framework の最新バージョンを調べて
```

```
WebSearch ツールを使って [ライブラリ名] の既知 CVE を確認して
```

### 注意事項

- **環境依存**: `WebSearch` ツールは Claude Code の環境によって利用不可の場合がある
  - `claude.ai/code`（Web アプリ）: 利用可能
  - Claude Code CLI（ローカル）: 設定・プランによって利用不可の場合あり
- **フォールバック**: CLI 環境で利用不可の場合は公式ドキュメント・npm/PyPI を手動で確認する
- **情報の最終確認**: WebSearch の結果は公式ドキュメントで裏取りしてから計画書に記載する（Web 検索結果は古い・誤りの場合がある）

---

## 3. GitHub MCP

セットアップ手順・利用方法は `docs/runbooks/mcp-github-setup.md` を参照。

### 主な利用場面

| フェーズ | 利用例 |
|---------|-------|
| `/code-review` | PR に付いたレビューコメントを直接参照 |
| `/plan-issue` | 関連 issue のコメント・経緯を参照して精度の高い計画書を作成 |
| `/close` | issue への完了コメント投稿 |

---

## 4. Sequential Thinking MCP を導入しない理由

将来の参照のために、導入不要と判断した根拠を記録する。

### 評価パッケージ

`@modelcontextprotocol/server-sequential-thinking`（バージョン 2025.12.18）

### 起動確認

```bash
npx -y @modelcontextprotocol/server-sequential-thinking
# → "Sequential Thinking MCP Server running on stdio"（起動は成功）
```

### 導入不要の根拠

1. **Claude 4.x では冗長**: このMCPはClaude 2/3向けの補助ツールとして設計された。Claude claude-sonnet-4-6（本プロジェクト使用中）はモデル内部で高精度の段階的推論を行っており、外部ツールで補う必要がない
2. **供給チェーンリスク**: バージョン未固定（`npx -y`）で実行すると、パッケージの悪意ある更新が自動適用されるリスクがある。既存の GitHub MCP は `@2025.4.8` と固定しており、一貫性がなく安全でない
3. **依存増加のコスト超過**: 実質的な品質向上なしに npm 依存・保守コスト・攻撃面が増加する

---

## 5. 将来 MCP を追加する際の評価観点

新しい MCP を追加する前に、以下の観点で評価すること。

### 必須確認項目

| 観点 | 確認内容 |
|------|---------|
| **代替手段の有無** | Claude Code の built-in 機能や既存ツール（`gh` CLI 等）で代替できないか |
| **供給チェーンリスク** | バージョン固定が可能か（`@x.y.z` 形式で指定できるか） |
| **シークレット管理** | 外部 API キーが不要か。必要な場合、環境変数管理の運用コストは許容できるか |
| **Claude モデルとの適合** | 現在使用している Claude モデルに対して実質的な追加価値があるか |
| **公式性・信頼性** | Anthropic 公式または実績あるサードパーティか |

### 追加する場合の設定ルール

`.mcp.json` に追加する際は必ずバージョンを固定する:

```json
{
  "mcpServers": {
    "new-server": {
      "command": "npx",
      "args": ["-y", "@scope/server-name@x.y.z"]
    }
  }
}
```

`-y` オプションはバージョン固定している場合のみ使用可（未固定の場合はインストール後にパスを指定）。
