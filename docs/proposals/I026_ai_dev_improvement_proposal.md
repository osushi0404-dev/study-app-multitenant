# AI駆動開発環境・プロセス改善提案

- **作成日**: 2026-04-03
- **関連イシュー**: I026 / #54
- **対象**: Claude Code を活用したバイブコーディング運用全般

---

## エグゼクティブサマリー

本プロジェクトは Claude Code + Django REST Framework + React TypeScript の構成で、  
「イシュー → 計画 → 実装 → テスト → レビュー → マージ」の安全寄りワークフローで開発している。

現状の運用は概ね機能しているが、以下の4領域に改善余地がある：

1. **Claude Code 設定**（`.claude/settings.json`）: 頻繁に使うコマンドが ask 扱いになっており作業が止まる
2. **MCP サーバー**: 未導入。GitHub MCP 等を活用することで gh CLI の限界を超えた操作が可能になる
3. **ワークフロー**: `/retro` の実施率が低い可能性
4. **ドキュメント**: `onboarding.md` の情報が古く、`issue-flow.md` の採番ロジックがスキル実装と不一致

優先度・期待効果に基づき、**settings.json 改善** と **GitHub MCP 導入** を最優先で実施することを推奨する。

---

## 1. 現状棚卸し

### 1-1. Claude Code 設定（`.claude/settings.json`）

| カテゴリ | 現状 |
|---------|------|
| permissions.allow | Read/Grep/Glob/Write(docs)/Edit(docs)、主要 git・gh・docker コマンド |
| permissions.ask | git push/merge/rebase/reset、docker exec/down、psql、rm/mv/cp |
| permissions.deny | curl/wget/ssh、破壊的 git 操作、直 push to develop/main、.env 読み書き |
| hooks.PreToolUse | `pretooluse_guard.py`（危険操作ブロック） |
| hooks.PostToolUse | **未設定** |

**問題**: 下記のコマンドが allow に未登録のため、日常的な作業でも確認ダイアログが発生し作業が止まる。

| 未登録コマンド | 発生シーン |
|-------------|-----------|
| `git fetch *` | リモートブランチ確認（plan/retro/close 等） |
| `git branch --show-current` / `git rev-parse --abbrev-ref HEAD` | ブランチ確認 |
| `git push -u origin *` | 新ブランチの初回 push |
| `Bash(python3 *)` | フック・スクリプトのテスト実行 |
| `Bash(npm *)` / `Bash(npx *)` | Docker 外でのフロントエンド操作 |

---

### 1-2. MCP サーバー

**現状**: プロジェクト・グローバルともに MCP サーバーの設定なし。

Claude Code は MCP（Model Context Protocol）を通じて外部ツールと連携できるが、現時点では未活用。

| MCP | 用途 | 優先度 |
|-----|------|--------|
| GitHub MCP | issue/PR/コメント/差分の高度な参照・操作 | 高 |
| Sequential Thinking MCP | 複雑な推論・計画立案の品質向上 | 中 |
| Web Search MCP | ライブラリ調査・ベストプラクティス確認 | 中 |
| Filesystem MCP | ファイル操作の拡張（現状ほぼカバー済み） | 低 |

---

### 1-3. ワークフロー

**現状スキル一覧**（9スキル）:

```
/issue-bootstrap → /plan-issue → /plan-issue-review
→ /implement → /code-review → /test → /fix-loop → /retro → /close
```

**問題**:

| 問題 | 詳細 |
|------|------|
| `/retro` の実施率が不明 | 「任意」扱いのため振り返りを経由せず `/close` に進むケースがある可能性 |
| `issue-bootstrap` と `issue-flow.md` の採番ロジック不一致 | スキル: FS最大値 と git履歴最大値の大きい方+1 ／ docs: ローカル最大 + GitHub件数 + 1 |

---

### 1-4. ドキュメント（CLAUDE.md・runbooks）

| ファイル | 問題 |
|---------|------|
| `docs/runbooks/onboarding.md` | フロー図に `/plan-issue-review` が欠落、`docs/` 構成が古い、参照先に複数の runbook が未記載 |
| `docs/runbooks/issue-flow.md` | 採番ロジックが `issue-bootstrap` スキルの実装と異なる |
| `docs/runbooks/workflow.md` | `in_progress` の扱いが未記述、`/retro` が「任意」表記のまま |
| `CLAUDE.md` | スキル一覧の説明文が概要のみ（トリガー条件の補足余地あり） |

---

## 2. 改善候補の詳細

### A: settings.json 改善（allow 拡充・PostToolUse フック追加）

**優先度**: 高 ／ **概算規模**: 小（1〜2h）

#### 何をするか

`.claude/settings.json` の `permissions.allow` に、日常的なワークフローで頻繁に必要になるコマンドを追加する。また、`hooks.PostToolUse` にファイル編集後の自動チェックフックを設定する。

**具体的な追加対象**:

```json
"allow": [
  "Bash(git fetch *)",
  "Bash(git branch --show-current)",
  "Bash(git rev-parse --abbrev-ref HEAD)",
  "Bash(git push -u origin *)",
  "Bash(python3 *)",
  "Bash(npm *)",
  "Bash(npx *)"
]
```

**PostToolUse フックの例**（Edit/Write 後に自動で lint を実行）:

```json
"PostToolUse": [
  {
    "matcher": "Edit|Write",
    "hooks": [{ "type": "command", "command": "..." }]
  }
]
```

#### なぜ必要か・どんなメリットがあるか

現状、`git fetch` や `git branch --show-current` のような**読み取り専用の安全なコマンド**でも毎回確認ダイアログが表示される。これにより：

- **作業の中断**: Claude がコマンドを実行するたびにユーザーが承認操作を求められ、フロー状態（Flow state）が破られる
- **スキル内での待ち時間増加**: `/plan-issue`・`/retro`・`/close` 等のスキルがリモート状態確認のたびに止まる

allow に追加することで：
- **承認不要で即実行**される安全なコマンドが増え、スキルが途切れなく動く
- ユーザーの介入が「本当に重要な判断」（push・merge 等）のみに絞られる

PostToolUse フックを追加することで：
- ファイル編集後に自動で lint・型チェックが走り、**問題を即座に検出**できる
- `/implement` 終了後の手動チェック工数が減る

---

### B: GitHub MCP 導入・設定

**優先度**: 高 ／ **概算規模**: 中（半日）

#### 何をするか

GitHub が公式に提供する MCP サーバー（`@modelcontextprotocol/server-github`）を導入し、Claude Code が GitHub の API を直接活用できるようにする。

MCP（Model Context Protocol）とは、Claude が外部ツール・サービスと標準化されたプロトコルで連携するための仕組み。設定ファイルに MCP サーバーを登録すると、Claude のツールとして GitHub 操作が追加される。

**設定イメージ**（`.claude/mcp_servers.json` 等）:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "<token>" }
    }
  }
}
```

#### なぜ必要か・どんなメリットがあるか

現状の `gh` CLI では以下の操作が難しい・できない：

| 操作 | gh CLI | GitHub MCP |
|------|--------|------------|
| PR の全コメント一括取得 | ページネーション手動処理が必要 | ✅ 一発で取得可能 |
| PR の差分を Claude が直接解析 | ファイルに保存して渡す必要あり | ✅ Claude が直接参照 |
| issue のラベル・マイルストーン操作 | コマンド組み合わせが複雑 | ✅ 自然言語で指示可能 |
| レビューコメントへの返信 | gh API 直接叩く必要あり | ✅ シンプルに操作可能 |
| コミット単位の変更理由の参照 | git log + gh 組み合わせ | ✅ 統合して参照可能 |

**ワークフローへの具体的な効果**:

- **`/code-review` フェーズ**: Claude が PR に付いたレビューコメントを直接読み、対応漏れを自動検出できる
- **`/plan-issue` フェーズ**: 関連 issue のコメント・経緯を Claude が直接参照して、より精度の高い計画書を作成できる
- **`/close` フェーズ**: PR 本文の自動整備や、issue への完了コメント投稿が自動化できる

---

### C: issue-flow.md 採番ロジック修正

**優先度**: 中 ／ **概算規模**: 小（30分）

#### 何をするか

`docs/runbooks/issue-flow.md` に記載されている採番ロジックの説明を、`issue-bootstrap` スキルの実際の実装に合わせて修正する。

| | 現状の docs 記載 | スキルの実装 |
|-|----------------|------------|
| ロジック | ローカル最大番号 + GitHub issue 件数 + 1 | FS最大値 と git履歴最大値の**大きい方** + 1 |
| GitHub 参照 | 必要（gh コマンド実行） | 不要（git log で代替） |

#### なぜ必要か・どんなメリットがあるか

- **ドキュメントと実装の乖離**は、新しいセッションで Claude が docs を参照して採番したとき、スキルと異なる番号を算出するリスクがある
- 「docs を読んで理解した採番」と「スキルが実際に使う採番」が一致していないと、**番号の衝突や欠番**が生じる可能性がある
- docs を正とすることで、誰でも（将来の Claude も）正しい採番ロジックを把握できる

---

### D: Sequential Thinking / Web Search MCP 導入検討

**優先度**: 中 ／ **概算規模**: 中（半日）

#### Sequential Thinking MCP とは

複雑な問題を解くとき、Claude に「段階的な思考プロセス」を明示的に踏ませるためのツール。  
通常の Claude は 1 ターンで回答を生成するが、Sequential Thinking MCP を使うと：

```
思考ステップ1: 問題を分解する
思考ステップ2: 各要素の依存関係を整理する
思考ステップ3: リスクを洗い出す
思考ステップ4: 実装方針を決定する
→ 最終回答
```

のように、**推論の過程が構造化**される。

**このプロジェクトでの効果**:

- **`/plan-issue` フェーズ**: DB スキーマ変更・認証フロー設計など複雑な設計判断で、見落としが減る
- **`/fix-loop` フェーズ**: バグの根本原因分析を段階的に行うことで、表面的な修正に終わらない

#### Web Search MCP とは

Claude がリアルタイムで Web 検索を実行し、結果を回答に組み込めるようにするツール。  
Claude の学習データのカットオフ（2025年8月）以降の情報も参照できる。

**このプロジェクトでの効果**:

- **`/plan-issue` フェーズ**: 使用するライブラリの最新バージョン・既知の脆弱性・推奨パターンをリアルタイムで確認できる
- **セキュリティチェック**: OWASP 等の最新ガイドラインを参照して計画書に反映できる
- **ベストプラクティス確認**: Django・React の最新の推奨パターンを常に参照できる

---

### E: workflow.md /retro 推奨化

**優先度**: 低 ／ **概算規模**: 小（30分）

#### 何をするか

`docs/runbooks/workflow.md` の `/retro` の扱いを「任意」→「推奨（テスト OK 後は原則実施）」に変更する。

#### なぜ必要か・どんなメリットがあるか

`/retro` スキルは「テスト OK 後の振り返り」を行うフェーズで、以下を確認する：
- 実装中に気づいた runbooks・CLAUDE.md の改善点
- スキルの使い勝手の問題点
- 次回に活かせる教訓

現状「任意」扱いのため省略されがちだが、**振り返りを実施しないと問題が蓄積され、同じ失敗が繰り返される**。推奨化することで：
- 運用ルールの継続的改善サイクルが回る
- CLAUDE.md・runbooks が実態に合い続ける

---

## 3. 改善候補一覧（優先度サマリー）

| # | 改善内容 | 優先度 | 期待効果 | 概算規模 |
|---|---------|--------|---------|---------|
| A | settings.json 改善（allow 追加・PostToolUse フック） | **高** | 日常作業の確認ダイアログを大幅削減・編集後の自動品質チェック | 小（1〜2h） |
| B | GitHub MCP 導入・設定 | **高** | PR/issue の高度参照・差分分析・レビュー対応の自動化 | 中（半日） |
| C | issue-flow.md 採番ロジック修正 | 中 | docs とスキル実装の乖離解消・採番ミス防止 | 小（30分） |
| D | Sequential Thinking / Web Search MCP 導入検討 | 中 | 計画立案品質の向上・最新情報のリアルタイム参照 | 中（半日） |
| E | workflow.md /retro 推奨化 | 低 | 振り返りルーティン化による運用改善サイクルの確立 | 小（30分） |

---

## 4. 推奨ロードマップ

```
Phase 1（即実施・高効果）
  └─ A: settings.json 改善
  └─ B: GitHub MCP 導入

Phase 2（中期・品質改善）
  └─ C: issue-flow.md 採番ロジック修正
  └─ D: Sequential Thinking / Web Search MCP 検討・導入

Phase 3（長期・運用改善）
  └─ E: workflow.md 記述改善
  └─ F: in_progress 運用開始（スキル変更を伴う）
```

**実施順序の根拠**:
- A・B は独立して実施可能かつ日常的な摩擦を直接解消するため最優先
- C は A・B の実施後でも問題なく、規模が小さいため Phase 2 で吸収可能
- F はスキル変更を伴うため、A〜E で運用が安定してから着手するのが安全

---

## 5. 別イシュー起票テンプレート

### A: settings.json 改善

**タイトル案**: `Claude Code settings.json の allow 拡充と PostToolUse フック追加`

**スコープ（含む）**:
- `git fetch *`・`git branch --show-current`・`git push -u origin *` を allow に追加
- `Bash(python3 *)` を allow に追加
- PostToolUse フック（Edit/Write 後の自動チェック）の設計・追加

**スコープ（含まない）**:
- deny ルールの変更
- hooks スクリプト本体の大幅改修

---

### B: GitHub MCP 導入

**タイトル案**: `GitHub MCP の導入・設定（issue/PR 高度操作の実現）`

**スコープ（含む）**:
- GitHub MCP のインストール・認証設定
- プロジェクト固有の MCP 設定ファイル作成
- 動作確認（issue 参照・PR コメント取得等）

**スコープ（含まない）**:
- 他 MCP（Sequential Thinking 等）の同時導入
- 既存スキルへの MCP 活用組み込み

---

### C: issue-flow.md 採番ロジック修正

**タイトル案**: `issue-flow.md の採番ロジックを issue-bootstrap スキルの実装に統一`

**スコープ（含む）**:
- `docs/runbooks/issue-flow.md` の採番説明を修正（FS最大値 + git履歴最大値 → 大きい方+1）
- 旧ロジック（ローカル最大 + GitHub件数 + 1）の記述を削除

**スコープ（含まない）**:
- `issue-bootstrap` スキル本体の変更

---

### D: Sequential Thinking / Web Search MCP 導入検討

**タイトル案**: `Sequential Thinking・Web Search MCP の評価と導入`

**スコープ（含む）**:
- 各 MCP の動作確認・効果測定
- 有効と判断した MCP の設定ファイルへの追加
- 利用場面の runbook への記載

**スコープ（含まない）**:
- GitHub MCP（別イシュー B で実施済み）

---

### E: workflow.md /retro 推奨化

**タイトル案**: `workflow.md の /retro 推奨化`

**スコープ（含む）**:
- `/retro` を「任意」→「推奨（テスト OK 後は原則実施）」に変更

**スコープ（含まない）**:
- スキル本体の変更

---

## 6. 参考：現在のディレクトリ・ファイル構成

```
.claude/
├── settings.json        # 権限・フック設定
├── skills/              # 9スキル（issue-bootstrap 等）
└── （MCP サーバー設定 未作成）

docs/
├── issues/      open / in_progress / closed / templates
├── plans/       open / closed
├── proposals/   （I026 で新設）
├── tests/       open / closed
├── reviews/     open / closed
└── runbooks/    workflow / plan-writing-rules / issue-flow / 他

scripts/
└── claude/hooks/pretooluse_guard.py   # 危険操作ブロック
```
