# plan_I028_Dependabot設定とPRテンプレート追加

## 基本情報
- **計画書ID**: plan_I028_Dependabot設定とPRテンプレート追加
- **関連イシュー**: #58
- **作成根拠資料**: docs/proposals/I026_ai_dev_improvement_proposal.md（改善候補 G・H）
- **実装後評価**: （未作成）
- **作成日**: 2026-04-08

---

## 背景/目的

- 依存パッケージの脆弱性を自動検出・更新 PR を自動作成する仕組みが未整備
- PR 作成時の本文にひな形がなく、記載内容の統一性・抜け漏れ防止ができていない

---

## 受け入れ条件

- [ ] `.github/dependabot.yml` が追加され、pip・npm・github-actions の 3 ecosystem が週次で監視される
- [ ] `open-pull-requests-limit` が各 ecosystem 5 に設定されている
- [ ] `.github/pull_request_template.md` が追加され、PR 作成時にひな形が自動挿入される
- [ ] PR テンプレートに概要・関連イシュー・変更点・テスト確認・ロールバック手順が含まれる
- [ ] `/close` スキルの step 2 が PR テンプレートを読み込んで PR 説明を構築する
- [ ] CI が通る

---

## 影響範囲

- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `.github/dependabot.yml`・`.github/pull_request_template.md` の新規追加、`.claude/skills/close/SKILL.md` の更新

---

## セキュリティ影響

バックエンド・フロントエンドのコード変更なし。追加するのは GitHub 設定ファイルのみ。

**セキュリティ影響なし**

---

## 変更点一覧

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `.github/dependabot.yml` | 新規追加 | pip・npm・github-actions の週次更新設定 |
| `.github/pull_request_template.md` | 新規追加 | PR 作成時のひな形 |
| `.claude/skills/close/SKILL.md` | 更新 | step 2 に PR テンプレート読み込みの指示を追加 |

---

## 実装手順

### ステップ 1: `.github/dependabot.yml` の作成

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
    target-branch: "develop"
    open-pull-requests-limit: 5

  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"
    target-branch: "develop"
    open-pull-requests-limit: 5

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    target-branch: "develop"
    open-pull-requests-limit: 5
```

**設計判断**:
- `target-branch: "develop"` — リポジトリのデフォルトブランチは `main` だが、依存更新は `develop` → `main` のフローに乗せるため明示指定（ユーザー確認済み）
- `open-pull-requests-limit: 5` — イシューの受け入れ条件「5件以下」に基づく
- `schedule.interval: "weekly"` — イシュー要件通り
- `groups` 未設定 — イシューのスコープ外

### ステップ 2: `.github/pull_request_template.md` の作成

```markdown
## 概要
<!-- 何をしたか・なぜしたか -->

## 関連イシュー
Closes #

## 変更点
-

## テスト確認
- [ ] CI（自動テスト）pass 確認
- [ ] 手動テスト確認（docs/tests/open/I###_manual_test.md 参照）

## ロールバック手順
<!-- 問題が発生した場合の手順 -->

## 参照ドキュメント
<!-- 関連する計画書・runbook 等 -->
```

**設計判断**:
- セクション形式 + チェックボックス — イシューに形式指定なし。既存レビュー文書（I027_review.md）に合わせた構成を採用（仮定）
- ロールバック手順を必須セクションとして含める — 提案書（I026）の要件に基づく

### ステップ 3: `.claude/skills/close/SKILL.md` の更新

step 2 の指示を以下のように変更する。

**変更前**:
```
2) PR説明に「目的/変更点/テスト/ロールバック/参照パス」を揃える
```

**変更後**:
```
2) PR テンプレートを読み込み、各セクションを実装内容で埋めて PR 説明を更新する:
   ```bash
   # テンプレートを確認
   cat .github/pull_request_template.md
   ```
   テンプレートの各セクション（概要・関連イシュー・変更点・テスト確認・ロールバック手順・参照ドキュメント）を
   イシュー・計画書・テスト結果をもとに埋め、gh pr edit で PR 説明を更新する:
   ```bash
   gh pr edit <PR番号> --body "$(cat <<'EOF'
   ## 概要
   ...（実装内容を記載）

   ## 関連イシュー
   Closes #...

   ## 変更点
   ...

   ## テスト確認
   - [x] CI（自動テスト）pass 確認
   - [x] 手動テスト確認

   ## ロールバック手順
   ...

   ## 参照ドキュメント
   ...
   EOF
   )"
   ```
```

**設計判断**:
- `gh pr edit --body` を使う — `/issue-bootstrap` で Draft PR が既に存在するため `gh pr create` ではなく編集
- テンプレートファイルが存在しない場合は従来通り手動で記載（後方互換）

---

## テスト計画

### 自動テスト
- CI が全ジョブ pass すること（設定ファイルの追加のみなので既存テストへの影響なし）

### 手動テスト
- `.github/dependabot.yml` の YAML 構文が正しいこと（GitHub が認識できること）
- `.github/pull_request_template.md` が PR 作成時に自動挿入されること

---

## ロールバック

- `.github/dependabot.yml` を削除する
- `.github/pull_request_template.md` を削除する
- `.claude/skills/close/SKILL.md` の step 2 を変更前の内容に戻す（`git revert` または手動編集）
- いずれも既存アプリ機能への影響なし

---

## Risk & 回避策

| リスク | 影響 | 回避策 |
|-------|------|-------|
| Dependabot が週次で大量 PR を作成する | develop が Dependabot PR で埋まる | `open-pull-requests-limit: 5` で上限制御 |
| `target-branch: "develop"` が GitHub 側で認識されない | Dependabot PR が main に向く | 設定後に GitHub の Dependabot 設定画面で確認 |
| `/close` スキルで `gh pr edit --body` のヒアドキュメントが正しく展開されない | PR 説明が空または不完全になる | 実装後に I028 の `/close` 実行時に実際の PR 説明を確認する |
