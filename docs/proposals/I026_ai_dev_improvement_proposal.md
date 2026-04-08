# AI駆動開発環境・プロセス改善提案

- **作成日**: 2026-04-03
- **関連イシュー**: I026 / #54
- **対象**: Claude Code を活用したバイブコーディング運用全般

---

## エグゼクティブサマリー

本プロジェクトは Claude Code + Django REST Framework + React TypeScript の構成で、  
「イシュー → 計画 → 実装 → テスト → レビュー → マージ」の安全寄りワークフローで開発している。

現状の運用は概ね機能しているが、以下の5領域に改善余地がある：

1. **Claude Code 設定**（`.claude/settings.json`）: 頻繁に使うコマンドが ask 扱いになっており作業が止まる
2. **MCP サーバー**: 未導入。GitHub MCP 等を活用することで gh CLI の限界を超えた操作が可能になる
3. **GitHub 未活用機能**: Dependabot・PR テンプレート・Branch protection rules・Projects 等が未設定
4. **ワークフロー**: `/retro` の実施率が低い可能性
5. **ドキュメント**: `onboarding.md` の情報が古く、`issue-flow.md` の採番ロジックがスキル実装と不一致

優先度・期待効果に基づき、**settings.json 改善**・**Dependabot**・**PR テンプレート** を最優先で実施することを推奨する。

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

### 1-3b. GitHub 未活用機能

**現状**: 以下の GitHub 機能が未設定。

| 機能 | 現状 | 設定者 |
|------|------|--------|
| Dependabot | 未設定 | Claude（`.github/dependabot.yml` 追加のみ） |
| PR テンプレート | 未設定 | Claude（`.github/pull_request_template.md` 追加のみ） |
| Branch protection rules | 未設定（hooks で代替中） | ユーザー（Settings 画面操作）+ Claude（手順書作成） |
| GitHub Projects / Milestones | 未設定 | Claude（gh CLI で作成可能） |

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

### G: Dependabot 設定

**優先度**: 高 ／ **概算規模**: 小（30分）

#### 何をするか

`.github/dependabot.yml` を追加し、pip（Backend）と npm（Frontend）の依存パッケージを自動監視する。

**設定イメージ**:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"
```

#### なぜ必要か・どんなメリットがあるか

- **セキュリティ脆弱性の自動検出**: 依存パッケージに既知の CVE が発見されると GitHub が自動アラートを出す
- **自動更新 PR**: 週次で依存パッケージの更新 PR を自動作成してくれるため、手動で `pip list --outdated` や `npm outdated` を確認する手間がなくなる
- **CI との連携**: 自動作成された PR にも CI が走るため、更新で壊れた場合にすぐ検知できる
- **設定コストが極めて低い**: ファイル1つ追加するだけで有効化でき、メンテナンスも不要

---

### H: PR テンプレート追加

**優先度**: 高 ／ **概算規模**: 小（15分）

#### 何をするか

`.github/pull_request_template.md` を追加し、PR 作成時に本文のひな形を自動挿入する。

**テンプレート内容（案）**:
- 概要（何をしたか）
- 関連イシュー（Closes #XXX）
- 変更点
- テスト確認内容
- ロールバック手順
- 参照ドキュメント

#### なぜ必要か・どんなメリットがあるか

- **Claude の `/close` 品質向上**: 現状 Claude は PR 本文を毎回ゼロから書くが、テンプレートがあると「埋めるべき項目」が強制される
- **レビュー効率向上**: 本文の構成が統一されることで、何が変わったのかをすぐに把握できる
- **抜け漏れ防止**: ロールバック手順や関連イシュー番号の記載忘れを防げる

---

### I: Branch protection rules 設定

**優先度**: 中 ／ **概算規模**: 小（手順書作成 30分 + ユーザー操作 5分）

#### 何をするか

GitHub リポジトリの Settings > Branches で `develop` と `main` に対して以下を設定する（ユーザーが Settings 画面で操作）。Claude が手順書を作成する。

**設定内容（案）**:
- Require a pull request before merging（直 push 禁止）
- Require status checks to pass（CI 全 pass 必須）
- Do not allow bypassing the above settings（管理者も対象）

#### なぜ必要か・どんなメリットがあるか

現状は `.claude/settings.json` の deny ルールと `pretooluse_guard.py` で直 push をブロックしているが、これらは **Claude Code 経由の操作のみ** を対象にしている。

Branch protection rules を設定することで：
- **GitHub Web UI・他のツール経由の push も防止**できる二重ガードになる
- CI が通らない状態でのマージを GitHub 側で物理的に防止できる
- 設定は Claude がコードを書かずユーザーが GUI で5分で完了できる

---

### J: GitHub Projects + Milestones 設定

**優先度**: 中 ／ **概算規模**: 小（30分）

#### 何をするか

`gh` CLI を使い、改善イシュー A〜H を管理する GitHub Projects（カンバンボード）と Milestones（Phase 1〜3）を作成する。

**Milestones（案）**:
- Phase 1: settings.json・Dependabot・PR テンプレート（A・G・H）
- Phase 2: GitHub MCP・採番ロジック修正・Branch protection・Projects（B・C・I・J）
- Phase 3: Web Search MCP・/retro 推奨化（D・E）

#### なぜ必要か・どんなメリットがあるか

- **改善の進捗が一目でわかる**: カンバンボードで「未着手 / 進行中 / 完了」が可視化される
- **Milestone でフェーズ管理**: Phase 1 完了率が何%かを GitHub 上で確認できる
- **issue 起票との連動**: 各改善イシューを作成するときに Milestone を設定するだけでグルーピングできる

---

## 3. 改善候補一覧（優先度サマリー）

| # | 改善内容 | 優先度 | 期待効果 | 概算規模 | 状態 |
|---|---------|--------|---------|---------|------|
| A | settings.json 改善（allow 追加・PostToolUse フック） | **高** | 日常作業の確認ダイアログを大幅削減・編集後の自動品質チェック | 小（1〜2h） | 進行中（I029） |
| B | GitHub MCP 導入・設定 | **高** | PR/issue の高度参照・差分分析・レビュー対応の自動化 | 中（半日） | イシュー作成済み（I030） |
| C | issue-flow.md 採番ロジック修正 | 中 | docs とスキル実装の乖離解消・採番ミス防止 | 小（30分） | イシュー作成済み（I031） |
| D | Sequential Thinking / Web Search MCP 導入検討 | 中 | 計画立案品質の向上・最新情報のリアルタイム参照 | 中（半日） | イシュー作成済み（I035） |
| E | workflow.md /retro 推奨化 | 低 | 振り返りルーティン化による運用改善サイクルの確立 | 小（30分） | イシュー作成済み（I036） |
| G | Dependabot 設定（pip・npm 自動更新 PR・セキュリティアラート） | **高** | 依存パッケージの脆弱性を自動検出・更新 PR を自動作成 | 小（30分） | ✅ 完了（I028） |
| H | PR テンプレート追加 | **高** | Claude が /close で書く PR 本文の品質・統一性向上 | 小（15分） | ✅ 完了（I028） |
| I | Branch protection rules 設定 | 中 | hooks に加え GitHub 側でも直 push・CI 未通過マージを防止 | 小（手順書作成 30分 + ユーザー操作 5分） | イシュー作成済み（I032） |
| J | GitHub Projects + Milestones 設定 | 中 | 改善イシュー A〜H の進捗をカンバンで一元管理 | 小（30分） | イシュー作成済み（I033） |
| K | pre-commit hooks 導入（シークレット検出・品質チェック） | 中 | コミット前のシークレット検出・基本品質チェック自動化 | 小（1h） | イシュー作成済み（I034） |

---

## 4. 推奨ロードマップ

```
Phase 1（即実施・高効果）         設定者
  └─ A: settings.json 改善       Claude          ← 次はここ
  └─ G: Dependabot 設定          Claude          ✅ 完了（I028）
  └─ H: PR テンプレート追加       Claude          ✅ 完了（I028）
  └─ B: GitHub MCP 導入          Claude

Phase 2（中期・品質改善）
  └─ C: issue-flow.md 採番ロジック修正          Claude
  └─ I: Branch protection rules 設定           ユーザー（Claude が手順書作成）
  └─ J: GitHub Projects + Milestones 設定      Claude
  └─ D: Sequential Thinking / Web Search MCP  Claude

Phase 3（長期・運用改善）
  └─ E: workflow.md /retro 推奨化              Claude
```

**実施順序の根拠**:
- A・G・H は設定コストが極めて低く即効性が高いため最優先
- B（GitHub MCP）は認証設定が必要なため Phase 1 の後半
- I はユーザー操作が必要なため、Claude 側の準備（手順書）と合わせて Phase 2
- E は他の改善が安定してから振り返りを強制する順序が自然

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

### G: Dependabot 設定

**タイトル案**: `Dependabot 設定（pip・npm 依存パッケージ自動更新）`

**スコープ（含む）**:
- `.github/dependabot.yml` の作成（pip・npm 週次更新設定）
- セキュリティアラートの有効確認

**スコープ（含まない）**:
- Dependabot が作成した PR のマージ（CI 通過後はユーザーが判断）

---

### H: PR テンプレート追加

**タイトル案**: `PR テンプレート追加（.github/pull_request_template.md）`

**スコープ（含む）**:
- `.github/pull_request_template.md` の作成
- `/close` スキルが参照するよう案内を追記（任意）

**スコープ（含まない）**:
- 既存 PR の遡及的な修正

---

### I: Branch protection rules 設定

**タイトル案**: `GitHub Branch protection rules 設定手順書の作成と適用`

**スコープ（含む）**:
- `develop`・`main` への設定手順書を Claude が作成
- ユーザーが Settings 画面で適用

**スコープ（含まない）**:
- main の保護ルール緩和（リリース時フローへの影響を別途確認）

---

### J: GitHub Projects + Milestones 設定

**タイトル案**: `GitHub Projects カンバンと Milestones（Phase 1〜3）の設定`

**スコープ（含む）**:
- `gh` CLI で Milestones 3件（Phase 1〜3）を作成
- GitHub Projects ボードを作成し各改善イシューを登録

**スコープ（含まない）**:
- Projects の自動化ルール設定（issue クローズ時の自動移動等）

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
