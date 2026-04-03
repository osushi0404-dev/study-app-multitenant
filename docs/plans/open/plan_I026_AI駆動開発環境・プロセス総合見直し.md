# plan_I026_AI駆動開発環境・プロセス総合見直し

## 基本情報
- **計画書ID**: plan_I026_AI駆動開発環境・プロセス総合見直し
- **関連イシュー**: #54
- **作成根拠資料**: docs/issues/open/I026.md
- **実装後評価**: （未作成）
- **作成日**: 2026-04-03

## 変更履歴

| 日付 | 変更内容 | 承認者 |
|------|---------|--------|
| 2026-04-03 | 初版作成 | ユーザー |
| 2026-04-03 | 実施対象を「runbooks修正」から「提案資料作成（案A）のみ」に変更 | ユーザー |
| 2026-04-03 | `docs/runbooks/onboarding.md` の最新化を実施対象に追加 | ユーザー |

---

## 1. 背景/目的

現在の Claude Code を活用したバイブコーディング運用について、ツール・MCP・外部サービス連携・設定・ワークフロー全般を棚卸しし、改善候補を優先度付きで文書化した包括的な提案資料を作成する。

即実施スコープ：
- 現状棚卸しと改善候補の文書化（提案資料の作成）

別イシューへ切り出すスコープ：
- MCP サーバーの実際の設定・導入
- `.claude/settings.json` の設定値変更
- runbooks・CLAUDE.md の記述修正

---

## 2. 受け入れ条件（Acceptance Criteria）

- [ ] 提案資料（`docs/proposals/I026_ai_dev_improvement_proposal.md`）が作成されている
- [ ] 現状棚卸し（settings.json / MCP / ワークフロー / ドキュメント）が文書化されている
- [ ] 改善候補が優先度付きでリストアップされている
- [ ] MCP・settings.json・runbooks 等の改善候補が別イシュー起票可能な粒度で整理されている
- [ ] 推奨する実施順序とロードマップが記載されている

---

## 3. 影響範囲

- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: なし（設定ファイルの変更なし）
- ドキュメント: `docs/proposals/`（新規ディレクトリ・ファイル作成のみ）

---

## 4. 現状棚卸し（調査結果）

### 4-1. Claude Code 設定（`.claude/settings.json`）

**現状**:
- permissions.allow: Read/Grep/Glob/Write(docs)/Edit(docs)、git・gh・docker 系コマンド
- permissions.ask: git push/merge/rebase/reset、docker exec/down、psql、rm/mv/cp
- permissions.deny: curl/wget/ssh/scp/rsync、dd/mkfs/shred/sudo、直 push to develop/main、.env・secrets の読み書き
- hooks.PreToolUse: `pretooluse_guard.py`（危険操作ブロック）
- PostToolUse フック: 未設定

**識別した改善候補（別イシューへ）**:
1. `git fetch *` が allow に未登録（リモート確認時に毎回 ask になる）
2. `git branch --show-current` / `git rev-parse --abbrev-ref HEAD` が未登録
3. `Bash(python3 *)` が未登録（hooks テスト・スクリプト実行で毎回 ask になる）
4. PostToolUse フック未設定（Edit/Write 後の自動 lint チェック等の余地あり）
5. `Bash(git push -u origin *)` が allow に未登録（新ブランチ push が毎回 ask）
6. `Bash(npm *)` / `Bash(npx *)` のローカル実行が未登録

### 4-2. MCP サーバー

**現状**: プロジェクト・グローバルともに MCP サーバーの設定なし

**導入候補（別イシューで検討）**:

| 優先度 | MCP | 用途 | 期待効果 |
|--------|-----|------|----------|
| 高 | GitHub MCP | issue/PR/レビューの高度操作 | gh CLI では難しいコメント参照・差分分析が可能に |
| 中 | Sequential Thinking MCP | 複雑な計画立案・設計判断 | plan-issue フェーズでの推論品質向上 |
| 中 | Web Search MCP | ライブラリ調査・ベストプラクティス確認 | 計画時の外部情報参照が高速化 |
| 低 | Filesystem MCP | ファイル操作の拡張 | 既存の Read/Write/Edit ツールで概ねカバー済み |

### 4-3. ワークフロー（issue → plan → implement → test → review → merge）

**現状**:
- 9スキル（issue-bootstrap, plan-issue, plan-issue-review, implement, code-review, test, fix-loop, retro, close）
- `docs/issues/in_progress/` ディレクトリが定義されているが未活用
- /retro スキルが「任意」扱いで実施率が低い可能性

**識別した改善候補（別イシューへ）**:
1. **in_progress ディレクトリの活用**: /implement 開始時にイシューファイルを open→in_progress へ移動するフローを明文化（スキル変更を伴う）
2. **/retro の推奨度を上げる**: workflow.md で「任意」→「推奨」に変更
3. **issue-bootstrap の採番ロジック不一致**: issue-bootstrap スキルは「FS + git 履歴の最大値」を使うが、issue-flow.md は「ローカル最大 + GitHub 件数」の別ロジックを定義 → 要統一

### 4-4. ドキュメント（CLAUDE.md・runbooks）

**識別した修正候補（別イシューへ）**:

| 対象ファイル | 問題 |
|------------|------|
| docs/runbooks/issue-flow.md | 採番ロジックが issue-bootstrap スキルと不一致 |
| docs/runbooks/workflow.md | in_progress の扱いが未記述、/retro が「任意」表記 |
| CLAUDE.md | スキル一覧の説明文が概要のみ（トリガー条件の補足余地あり） |

---

## 5. 変更点一覧

### 5-1. 本イシューで実施

| ファイル | 変更内容 |
|---------|---------|
| `docs/proposals/I026_ai_dev_improvement_proposal.md` | 包括的な改善提案レポートを新規作成 |
| `docs/runbooks/onboarding.md` | 現状に合わせて最新化（下記「onboarding.md 修正方針」参照） |

#### onboarding.md 修正方針

| 箇所 | 問題 | 修正内容 |
|------|------|---------|
| 「全体の流れ」図 | `/plan-issue-review` ステップが欠落 | `/plan-issue` の次に追加 |
| `docs/` 構成 | `proposals/`・`issues/in_progress` が未記載 | 追記 |
| 参照先 | `issue-flow.md`・`review-rules.md`・`ux-rules.md`・`backend-check.md`・`template-sync.md` が欠落 | 追記 |

### 5-2. 別イシューへ切り出す

| 改善内容 | 優先度 | 概算規模 |
|---------|--------|---------|
| settings.json 改善（git fetch 等の allow 追加、PostToolUse フック追加） | 高 | 小 |
| GitHub MCP 導入・設定 | 高 | 中 |
| Sequential Thinking / Web Search MCP 導入検討 | 中 | 中 |
| issue-flow.md 採番ロジック修正 | 中 | 小 |
| workflow.md /retro 推奨・in_progress 記述追加 | 低 | 小 |
| in_progress ディレクトリの運用開始（スキル側変更） | 低 | 小 |

---

## 6. 実装手順

### Step 1: `docs/proposals/` ディレクトリ作成
```bash
mkdir -p docs/proposals/
```

### Step 2: 提案資料の作成
`docs/proposals/I026_ai_dev_improvement_proposal.md` を新規作成。

**含める内容**:
1. エグゼクティブサマリー（現状と改善の方向性）
2. 現状棚卸し（settings.json / MCP / ワークフロー / ドキュメント）
3. 改善候補一覧（優先度・期待効果・概算規模）
4. 推奨する実施順序とロードマップ
5. 各改善の別イシュー起票テンプレート（タイトル案・スコープ案）

### Step 3: onboarding.md の最新化
`docs/runbooks/onboarding.md` を修正。

**修正箇所**:
1. 「全体の流れ」図：`/plan-issue` の次行に `/plan-issue-review` を追加
2. `docs/` 構成：`proposals/` と `issues/in_progress` を追記
3. 参照先：`issue-flow.md`・`review-rules.md`・`ux-rules.md`・`backend-check.md`・`template-sync.md` を追記

---

## 7. テスト計画

- 自動テスト: なし（ドキュメント作成のみ）
- 手動テスト: 提案資料を読み通して棚卸し内容の網羅性・優先度付けの妥当性を確認

---

## 8. ロールバック

新規ファイル作成のみのため、`git revert` または対象ファイルの削除で即時ロールバック可能。

---

## 9. Risk & 回避策

| リスク | 回避策 |
|--------|--------|
| 提案資料の内容が実態と乖離する | 4節の棚卸し結果（コード・設定の直接確認に基づく）をそのまま反映する |
| 別イシューの粒度が大きすぎて着手困難になる | 各改善を独立して実施可能な単位に分割して記述する |

---

## 10. セキュリティ影響

コード・設定ファイルの変更なし。提案資料（Markdown）の新規作成のみ。

**セキュリティ影響なし**

---

## 11. 設計判断の明示

| 設計判断 | 根拠 |
|---------|------|
| MCP・settings.json・runbooks 修正は別イシュー | ユーザーが明示的に指示（2026-04-03） |
| 提案資料の置き場を `docs/proposals/` とする | イシュー・計画書・テスト等と分けて管理するため |

---

## 12. 承認ポイント

- [ ] 棚卸し内容（4節）に抜け・誤りはないか
- [ ] 提案資料の作成のみを本イシューで実施する方針でよいか
- [ ] 別イシュー切り出し対象（5-2）の優先度・粒度は妥当か
- [ ] 提案資料の置き場（`docs/proposals/`）でよいか
