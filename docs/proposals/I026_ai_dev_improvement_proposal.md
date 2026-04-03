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
3. **ワークフロー**: `in_progress` ディレクトリが未活用、`/retro` の実施率が低い可能性
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
| `in_progress` ディレクトリ未活用 | `docs/issues/in_progress/` が定義済みだが、実装中のイシューは `open/` に留まったまま |
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

## 2. 改善候補一覧

| # | 改善内容 | 優先度 | 期待効果 | 概算規模 |
|---|---------|--------|---------|---------|
| A | settings.json 改善（allow 追加・PostToolUse フック） | **高** | 日常作業の確認ダイアログを大幅削減 | 小（1〜2h） |
| B | GitHub MCP 導入・設定 | **高** | PR/issue の高度参照・差分分析が可能に | 中（半日） |
| C | issue-flow.md 採番ロジック修正 | 中 | docs とスキル実装の乖離解消 | 小（30分） |
| D | Sequential Thinking / Web Search MCP 導入検討 | 中 | 計画立案品質・調査効率の向上 | 中（半日） |
| E | workflow.md /retro 推奨・in_progress 記述追加 | 低 | 振り返りルーティン化・状態管理の明確化 | 小（30分） |
| F | in_progress ディレクトリの運用開始（スキル側変更） | 低 | 実装中イシューの可視化 | 小（1h） |

---

## 3. 推奨ロードマップ

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

## 4. 別イシュー起票テンプレート

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

### E: workflow.md 記述改善

**タイトル案**: `workflow.md の /retro 推奨化と in_progress ディレクトリ記述追加`

**スコープ（含む）**:
- `/retro` を「任意」→「推奨（テスト OK 後は原則実施）」に変更
- `in_progress` ディレクトリの活用を「将来の改善候補」として明記

**スコープ（含まない）**:
- スキル本体の変更

---

### F: in_progress ディレクトリ運用開始

**タイトル案**: `/implement 開始時にイシューファイルを in_progress へ移動するフロー実装`

**スコープ（含む）**:
- `/implement` スキルの修正（open → in_progress 移動を追加）
- `/close` スキルの修正（in_progress → closed 移動に対応）
- `workflow.md` の更新

**スコープ（含まない）**:
- `in_progress` 状態での CI・通知連携

---

## 5. 参考：現在のディレクトリ・ファイル構成

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
