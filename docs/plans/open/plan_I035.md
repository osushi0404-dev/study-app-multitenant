# plan_I035: Sequential Thinking・Web Search MCP の評価と導入

## 基本情報
- **計画書ID**: plan_I035
- **関連イシュー**: #79
- **作成根拠資料**: docs/proposals/I026_ai_dev_improvement_proposal.md（改善案 D）
- **実装後評価**: （未作成）
- **作成日**: 2026-04-11

---

## 背景/目的

I026 改善提案の改善案 D として、以下 2 つの MCP の評価・導入を行う。

- **Sequential Thinking MCP**: 複雑な問題（DB スキーマ変更・認証フロー設計等）で推論過程を構造化し、計画立案品質を向上させる
- **Web Search MCP**: Claude の知識カットオフ（2025年8月）以降の情報をリアルタイムで参照できるようにする

---

## 受け入れ条件（Acceptance Criteria）

- [ ] Sequential Thinking MCP の動作確認ができている（または導入不要と判断した根拠が記録されている）
- [ ] Web Search MCP の動作確認ができている（または導入不要と判断した根拠が記録されている）
- [ ] 導入した MCP の設定が `.claude/` または `.mcp.json` に追加されている
- [ ] 利用場面が runbook に記載されている

---

## 影響範囲

- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `.mcp.json`、`.claude/settings.local.json`、`docs/runbooks/mcp-usage.md`（新規）

---

## 調査結果

### 環境前提確認

| ツール | バージョン | 状態 |
|--------|-----------|------|
| Node.js | v24.14.1 | ✅ インストール済み |
| npx | 11.11.0 | ✅ インストール済み |

### Sequential Thinking MCP

| 項目 | 内容 |
|------|------|
| パッケージ | `@modelcontextprotocol/server-sequential-thinking` |
| バージョン | 2025.12.18 |
| 起動確認 | `npx -y @modelcontextprotocol/server-sequential-thinking` → "Sequential Thinking MCP Server running on stdio" ✅ |
| 評価 | **導入有効** |

**有効と判断した理由**:
- Claude の built-in 思考（内部処理）とは異なり、`sequentialthinking` ツール呼び出しとして**明示的・監査可能な形**で段階的推論が実行される
- `/plan-issue` での DB スキーマ設計・認証フロー設計など複雑な設計判断で、Claude が自発的にこのツールを呼び出すことで見落としが減る
- `/fix-loop` でのバグ根本原因分析でも有効

### Web Search MCP

| 項目 | 内容 |
|------|------|
| 現状 | Claude Code の**組み込み機能**として `WebSearch` ツールが既に利用可能 |
| 評価 | **別途 MCP 導入不要** |

**導入不要と判断した理由**:
- 現在のセッションで `WebSearch` がデファードツールとして確認済み（Claude Code の built-in 機能）
- 別途 Web Search MCP（Brave Search 等）を追加すると API キーの管理が必要になり、セキュリティリスク・運用コストが増加する
- 同等機能が重複することになり、設定の複雑性が上がるだけでメリットがない
- 運用面: `WebSearch` ツールを使う際のガイドラインを runbook に記載することで対応

### 現在の MCP 設定状況

`.mcp.json`（プロジェクトルート）:
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

`.claude/settings.local.json`:
```json
{
  "enabledMcpjsonServers": ["github"]
}
```

---

## 変更点一覧

| ファイル | 変更内容 |
|---------|---------|
| `.mcp.json` | `sequential-thinking` サーバーエントリを追加 |
| `.claude/settings.local.json` | `enabledMcpjsonServers` に `"sequential-thinking"` を追加 |
| `docs/runbooks/mcp-usage.md` | 新規作成: MCP 一覧・利用場面・使い方ガイドライン |

---

## 実装手順

### ステップ 1: `.mcp.json` に Sequential Thinking MCP を追加

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github@2025.4.8"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    }
  }
}
```

### ステップ 2: `.claude/settings.local.json` を更新

`enabledMcpjsonServers` に `"sequential-thinking"` を追加する。

```json
{
  "permissions": {
    "allow": [
      "Bash(npm show:*)",
      "Bash(npm search:*)",
      "Bash(npm install:*)",
      "Bash(npx eslint:*)",
      "Bash(git rm:*)"
    ]
  },
  "enabledMcpjsonServers": [
    "github",
    "sequential-thinking"
  ]
}
```

### ステップ 3: `docs/runbooks/mcp-usage.md` を新規作成

以下の内容で作成する:

- MCP 一覧（GitHub MCP / Sequential Thinking MCP / Web Search 組み込み）
- 各 MCP の利用場面（どのスキル・どのフェーズで使うか）
- Sequential Thinking MCP の使い方（`/plan-issue` での使用例）
- Web Search 組み込みツールの使い方と注意事項

### ステップ 4: 動作確認（手動）

Claude Code を再起動し、以下を確認する:

```bash
claude mcp list
# sequential-thinking が connected で表示されること
```

Claude に直接指示して動作確認:
```
sequentialthinking ツールを使って「DB スキーマ変更の設計判断」を段階的に考えてみて
```

---

## テスト計画

### 自動テスト
- JSON 構文チェック（`.mcp.json`、`settings.local.json`）
- `mcp-usage.md` のファイル存在確認

### 手動テスト
- Claude Code 再起動後に `claude mcp list` で `sequential-thinking` が `connected` になること
- Sequential Thinking MCP ツールが実際に呼び出せること
- Web Search 組み込みツールが利用可能なことの確認

---

## ロールバック

Sequential Thinking MCP が問題を引き起こした場合:
1. `.mcp.json` から `sequential-thinking` エントリを削除
2. `.claude/settings.local.json` の `enabledMcpjsonServers` から `"sequential-thinking"` を削除
3. Claude Code を再起動

Web Search 組み込みについては MCP 設定変更なし・runbook 記載のみのため、ロールバック不要。

---

## Risk & 回避策

| リスク | 影響 | 回避策 |
|--------|------|--------|
| npx 初回ダウンロードに時間がかかる | 起動遅延 | 初回接続時のみ。2回目以降はキャッシュ利用 |
| Sequential Thinking MCP がセッションで不安定になる | Claude の挙動が変わる | ロールバック手順が整備済み |
| Web Search の結果が古い・不正確 | 誤情報に基づく計画 | runbook に「最終確認は公式ドキュメントで行う」と明記 |

---

## セキュリティ影響

- Sequential Thinking MCP: PAT 等の機密情報を扱わない。`npx` でパブリックパッケージを実行するだけ。**セキュリティリスクなし**
- Web Search 組み込み: 設定変更なし。**セキュリティ影響なし**
- 追加・更新する依存ライブラリ: `@modelcontextprotocol/server-sequential-thinking` は npm 公式パッケージ。既知脆弱性は執筆時点（2026-04-11）で確認されていない

---

## 承認ポイント（ユーザー確認事項）

### 設計判断の明示

| 判断項目 | 判断内容 | 根拠 |
|---------|---------|------|
| Sequential Thinking MCP を追加する | 有効と判断・追加する | 調査で動作確認済み・明示的推論に価値あり |
| Web Search MCP は別途導入しない | 組み込み `WebSearch` で十分 | **仮定**（built-in 確認済みだが方針確認が必要） |
| runbook は新規 `mcp-usage.md` に記載 | 既存 `workflow.md` への追記ではなく新規ファイル | **仮定**（`mcp-github-setup.md` と同パターンで統一） |

### チェックリスト

- [ ] Sequential Thinking MCP を `.mcp.json` に追加することに同意する
- [ ] Web Search MCP は「別途導入不要（組み込み WebSearch を使う）」という判断に同意する
- [ ] MCP 利用ガイドラインを `docs/runbooks/mcp-usage.md` として新規作成することに同意する
