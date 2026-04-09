# plan_I037_issue-bootstrap軽量化とplan-issueへのブランチ管理移行

## 基本情報
- **計画書ID**: plan_I037_issue-bootstrap軽量化とplan-issueへのブランチ管理移行
- **関連イシュー**: I037 / GitHub #62
- **作成根拠資料**: I029 retro 議論（2026-04-08）
- **実装後評価**: （未作成）
- **作成日**: 2026-04-09

---

## 1. 背景/目的

`/issue-bootstrap` は現在「採番・イシューファイル作成・ブランチ作成・コミット・プッシュ・GitHub Issue 作成・Draft PR 作成」を一括して行っている。

問題: イシュー登録直後に計画書なしでブランチが切られるため、後から方向転換するとブランチが無駄になる。ブランチ・PR は実装計画が確定した `/plan-issue` のタイミングで作成するほうが責務として自然。

**目的**: `/issue-bootstrap` を「イシューの登録」に特化させ、ブランチ管理を `/plan-issue` に移行する。

---

## 2. 受け入れ条件

- [ ] `/issue-bootstrap` を実行すると、イシューファイルが `docs/issues/open/` に作成される
- [ ] `/issue-bootstrap` を実行すると、GitHub Issue が作成される
- [ ] `/issue-bootstrap` を実行すると、GitHub Issue 番号がイシューファイルに記録される
- [ ] `/issue-bootstrap` 実行後はブランチ切り替えが発生しない（現在のブランチのまま）
- [ ] `/plan-issue` を実行すると develop ベースのフィーチャーブランチが作成される
- [ ] `/plan-issue` を実行すると、イシューファイルがコミット・プッシュされる
- [ ] `/plan-issue` を実行すると、Draft PR が作成される
- [ ] `workflow.md`, `issue-flow.md` が新しい責務を反映している
- [ ] スキル一覧が `CLAUDE.md` から `docs/runbooks/workflow.md` に移管されている
- [ ] `CLAUDE.md` の `## 2. 使うスキル` は `workflow.md` への参照のみになっている

---

## 3. 影響範囲

- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra:
  - `.claude/skills/issue-bootstrap/SKILL.md`（変更）
  - `.claude/skills/plan-issue/SKILL.md`（変更）
  - `CLAUDE.md`（変更）
  - `docs/runbooks/workflow.md`（変更）
  - `docs/runbooks/issue-flow.md`（変更）

---

## 4. 調査結果

セキュリティ影響なし（バックエンド・フロントエンドのコード変更がない）。
対象はスキル定義ファイル（Markdown）とRunbookのみ。

既存テスト実行: 不要（コード変更なし）。

---

## 5. 変更点一覧と実装手順

### 5-1. `/issue-bootstrap` SKILL.md の軽量化

**変更前の責務（ステップ）**:
1. リポジトリ確認
2. 採番
3. イシューファイル作成
4. ブランチ作成 ← **削除**
5. コミット・プッシュ ← **削除**
6. GitHub Issue 作成
7. Draft PR 作成 ← **削除**
8. ユーザー報告

**変更後の責務（ステップ）**:
1. リポジトリ確認
2. 採番
3. イシューファイル作成
4. GitHub Issue 作成
5. イシューファイルに GitHub Issue 番号を記録 ← **新規追加**
6. ユーザー報告（ブランチ・PR の案内を削除、「/plan-issue を実行してください」のみ）

**変更内容**:
- フロントマター `description` を `Create issue doc and GitHub Issue only.` に変更
- Step 4（ブランチ作成）を削除
- Step 5（コミット・プッシュ）を削除
- GitHub Issue 作成後に「イシューファイルへの Issue 番号記録」ステップを追加
- Step 7（Draft PR）を削除
- ユーザー報告（Step 8 → Step 6）からブランチ・PR の行を削除

記録フォーマット（イシューファイルに追記）:
```bash
# 「## 関連資料」セクションに追記
# - GitHub Issue: #XX
```

### 5-2. `/plan-issue` SKILL.md へのブランチ管理移行

**追加する処理**（必読セクションの後、生成物作成の前に挿入）:

```
### ブランチ作成・プッシュ・Draft PR（必須）
イシューファイルを読んで GitHub Issue 番号を確認した後、以下を実行する:

1. develop ベースのフィーチャーブランチを作成
2. イシューファイルをコミット・プッシュ
3. Draft PR を作成

#### 1. ブランチ作成
```bash
git checkout develop
git pull origin develop
git checkout -b feature/I${ISSUE_NUM}-[概要を英語化したもの]
```

ブランチ命名規則:
- フォーマット: `feature/I{イシュー番号3桁}-{概要を英語化してケバブケース}`
- 例: `feature/I030-media-asset-models`

概要の英語化ルール:
- 日本語の概要をシンプルな英語に変換、スペースは - に変換、最大5単語程度

#### 2. イシューファイルのコミット・プッシュ
```bash
git add docs/issues/open/I${ISSUE_NUM}.md
git commit -m "docs: create issue I${ISSUE_NUM}"
git push -u origin feature/I${ISSUE_NUM}-[概要]
```

#### 3. Draft PR 作成
```bash
gh pr create \
  --title "feat: I${ISSUE_NUM} [イシュータイトル]" \
  --body "$(cat <<'EOF'
## 概要
I${ISSUE_NUM}: [概要]

## 関連イシュー
Closes #[GitHubイシュー番号]
EOF
)" \
  --draft \
  --base develop
```
```

**挿入位置**: 「必読:」セクションと「生成物:」セクションの間（またはファイル冒頭の説明直後）。

**フロントマター description の更新**:

変更前:
```
description: Create plan + tests + review docs for an issue. No code changes.
```
変更後:
```
description: Create branch, push, draft PR, then plan + tests + review docs for an issue.
```

### 5-3. スキル一覧を `CLAUDE.md` から `docs/runbooks/workflow.md` へ移管

CLAUDE.md 自身に「このファイルは短く保つ」「詳細ルールは docs/runbooks/ に集約する」と定められている。
スキル一覧は変更頻度が高く（スキルの追加・説明変更のたびに更新が必要）、CLAUDE.md に置くことで保守性が下がる。
また、スキルの説明は `.claude/skills/*/SKILL.md` の `description` フロントマターにも存在しており、DRY 原則に反する。

**`CLAUDE.md` の変更**:
`## 2. 使うスキル（/ で実行）` セクションのスキル一覧を削除し、`workflow.md` への参照のみ残す。

変更前:
```
## 2. 使うスキル（/ で実行）
- /issue-bootstrap [title] : 採番、イシューファイル作成、ブランチ作成、Draft PR 作成
- /plan-issue I### : 計画書 + テスト文書 + レビュー文書 作成（承認待ち）
... （全スキル一覧）
```

変更後:
```
## 2. 使うスキル（/ で実行）
詳細は `docs/runbooks/workflow.md` の「使うスキル」セクションを参照。
```

**`docs/runbooks/workflow.md` の変更**:
`## 使うスキル（/ で実行）` セクションを新規追加し、スキル一覧を移管する（`/issue-bootstrap` と `/plan-issue` の説明は新しい責務を反映した内容で記載）。

### 5-4. `docs/runbooks/issue-flow.md` の更新

**変更箇所**: 「イシュー作成時の自動実行フロー」のステップ説明

- Step 3（ブランチ作成）: `/issue-bootstrap` の記述を削除し、`/plan-issue` の記述として移動
- Step 4（GitHub Issue 登録）: GitHub Issue 番号をイシューファイルに記録する手順を追記
- Step 5（Draft PR）: `/plan-issue` 配下の説明として移動
- 「フェーズ2: 計画・設計」セクションに /plan-issue のブランチ作成・プッシュ・PR の説明を追記

---

## 6. テスト計画

### 自動テスト
なし（スキル定義ファイルの変更のため）

### 手動テスト
| # | 確認内容 | 期待結果 |
|---|---------|---------|
| MT-1 | `/issue-bootstrap` 実行後のブランチ確認 | ブランチが変わらない（実行前のブランチのまま） |
| MT-2 | `/issue-bootstrap` 実行後のイシューファイル確認 | GitHub Issue 番号が記録されている |
| MT-3 | `/issue-bootstrap` 実行後にブランチが存在しない | 作成したイシュー番号のブランチが `git branch -a` に存在しない |
| MT-4 | `/plan-issue` 実行後のブランチ確認 | `feature/I###-...` ブランチが作成されている |
| MT-5 | `/plan-issue` 実行後のイシューファイル確認 | イシューファイルがコミット済み（`git log` で確認） |
| MT-6 | `/plan-issue` 実行後の GitHub 確認 | Draft PR が存在する |

---

## 7. ロールバック

変更対象はすべて Markdown ファイルのみ。ロールバックは git revert または手動編集で即時対応可能。

---

## 8. Risk & 回避策

| リスク | 回避策 |
|--------|--------|
| /issue-bootstrap 実行時にブランチが既存の場合（旧フロー残存） | 手順に「現在のブランチを確認」ステップを残す |
| /plan-issue でイシューファイルが untracked のまま /issue-bootstrap のブランチから実行された場合 | /plan-issue 冒頭に「develop からブランチを作成する」ことを明記し、issue ファイルは git add で追跡する |
| issue-flow.md の採番ルールが issue-bootstrap SKILL.md と不一致になる | 両方を同時に更新する |

---

## 9. 承認ポイント

### セキュリティ影響
セキュリティ影響なし（コード変更なし、Markdown ファイルのみ）。

### 設計判断の明示

| 判断内容 | 根拠 |
|---------|------|
| ブランチ作成を /plan-issue の「必読の後・生成物作成の前」に配置する | イシューファイルを読んで GitHub Issue 番号を把握した直後に実行するのが自然 |
| イシューファイルは /issue-bootstrap でコミットせず、/plan-issue でコミットする | ブランチができてから初めてコミット可能なため |
| GitHub Issue 番号の記録は `/issue-bootstrap` の最終ステップで行う | Draft PR 番号は /plan-issue で記録する（PRが /plan-issue で作成されるため） |
| `issue-flow.md` の採番ルール（旧: FS + GitHub count）はそのまま維持 | 採番ロジック自体は変更スコープ外 |

上記すべてはイシュー I037 の要件から導いた判断（仮定なし）。

---

📋 計画書を作成しました: `docs/plans/open/plan_I037_issue-bootstrap軽量化とplan-issueへのブランチ管理移行.md`

⏸️ **承認待ち中** - 修正作業は開始しません
✅ 承認いただけましたら「OK」または「承認」とお答えください
❌ 修正が必要でしたら具体的な指示をお願いします
