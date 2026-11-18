# MCP 利用ガイドライン

このプロジェクトで評価・導入した MCP（Model Context Protocol）サーバーの一覧と、追加するときの決まりを記載する。

---

## 1. MCP 一覧と評価結果

| MCP | 評価結果 | 根拠 |
|-----|---------|------|
| GitHub MCP | ❌ 廃止（I223・I030 で導入） | GitHub の操作は `gh`（GitHub App の鍵）だけにする。MCP は別の個人の鍵（PAT）で動き、名義と鍵が 2 つになっていた。長く効く個人の鍵を持たない。`docs/runbooks/github-app-setup.md` |
| Playwright MCP | ✅ 導入済み（I187） | Claude が画面を確かめる。`docs/runbooks/frontend-verify.md` |
| Sequential Thinking MCP | ❌ 導入不要（I035） | 今の Claude の推論で足りる。供給チェーンリスクあり（§3） |
| Web Search MCP | ❌ 導入不要（I035） | built-in の `WebSearch` で足りる。外部 API キー管理不要 |

---

## 2. built-in の WebSearch・WebFetch

- Claude Code の組み込みの道具。追加の MCP は要らない。使えるかは提供元による（公式: Amazon Bedrock では使えない）
- 最新の版・CVE・推奨を調べるときは、`WebSearch` で探し、`WebFetch` で公式の文書を読んで裏を取る（検索の結果だけで決めない）
- 計画書・点検の表には、出典の URL と読んだ日付を書く

---

## 3. Sequential Thinking MCP を導入しない理由

評価したパッケージ: `@modelcontextprotocol/server-sequential-thinking`（2025.12.18）

1. **冗長**: 段階的に考える補助で、今の Claude はモデルの中で段階的な推論を行うので、外から補う必要がない
2. **供給チェーンリスク**: 版を固定せずに（`npx -y`）実行すると、パッケージの悪意ある更新がそのまま入る
3. **依存増加のコスト超過**: 品質の向上なしに npm 依存・保守コスト・攻撃面が増える

---

## 4. 将来 MCP を追加する際の評価観点

新しい MCP を追加する前に、以下の観点で評価すること。

### 必須確認項目

| 観点 | 確認内容 |
|------|---------|
| **代替手段の有無** | Claude Code の built-in 機能や既存ツール（`gh` CLI 等）で代替できないか |
| **供給チェーンリスク** | バージョン固定が可能か（`@x.y.z` 形式で指定できるか） |
| **シークレット管理** | 外部 API キーが不要か。必要な場合、環境変数管理の運用コストは許容できるか |
| **Claude モデルとの適合** | 今の Claude に対して実質的な追加価値があるか |
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

- `-y` オプションはバージョン固定している場合のみ使用可（未固定の場合はインストール後にパスを指定）
- `.mcp.json` の MCP は、`claude -p`（レビュー役など）では承認なしで読み込まれる（公式）。`scripts/claude/` が Claude を起こす行は `--strict-mcp-config` を保つ（決まりの正は `docs/runbooks/github-app-setup.md`「1. 仕組み」）
- 新しい MCP の道具は、PreToolUse の見張りの対象（`.claude/settings.json` の `hooks` の matcher。今は `mcp__playwright__.*`）と allow に足すかを決める。足さないと見張りが掛からない。`.claude/settings.json` の変更は `docs/runbooks/workflow.md`「止めて聞く条件」2 に当たる
