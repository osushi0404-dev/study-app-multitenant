# plan_I039: スキル間のファイル名参照の不整合修正

## 基本情報
- **計画書ID**: plan_I039
- **関連イシュー**: #66
- **作成根拠資料**: I039（スキル間ファイル名参照不整合の発見）
- **実装後評価**: （未作成）
- **作成日**: 2026-04-10

---

## 1. 背景/目的

各ワークフロースキルが参照するファイルパスの変数パターンが実態の命名規則と一致していない問題を修正する。
また計画書ファイルの命名規則（`plan_I###_{概要}.md`）が他ファイル種別（イシュー: `I###.md`、テスト: `I###_*.md`、レビュー: `I###_*.md`）と統一されておらず、スキル間で参照パターンがバラついている。

**目的**: 全ファイル種別を「概要なし」に統一し、スキル間のファイル名参照を一致させる。またクローズ済みイシューのopen残留重複ファイルも合わせてクリーンアップする。

---

## 2. 受け入れ条件（Acceptance Criteria）

- [ ] `plan-writing-rules.md` の命名規則が `plan_I###.md`（概要なし）に更新されている
- [ ] 各スキルの計画書・イシューファイル参照パスが実態の命名規則と一致している
- [ ] `issue-bootstrap/SKILL.md` にイシューファイル名形式（`I${ISSUE_NUM}.md`、概要なし）が明示されている
- [ ] 新規作成される計画書ファイル名が `plan_I###.md` 形式になる
- [ ] クローズ済みイシューの open 残留重複ファイルが削除されている

---

## 3. 影響範囲

- **Backend**: なし
- **Frontend**: なし
- **DB**: なし
- **Config/Infra**: `.claude/skills/` 配下 6 ファイル、`docs/runbooks/plan-writing-rules.md`、`docs/*/open/` 残留重複ファイル

---

## 4. 変更点一覧

### 4-A: スキル・ルール修正

| ファイル | 変更内容 |
|----------|---------|
| `docs/runbooks/plan-writing-rules.md` | 計画書命名規則を `plan_I###.md`（概要なし）に変更 |
| `.claude/skills/plan-issue/SKILL.md` | 必読パス `$ARGUMENTS_*.md` → `$ARGUMENTS.md`、生成物 `plan_$ARGUMENTS_{概要}.md` → `plan_$ARGUMENTS.md` |
| `.claude/skills/plan-issue-review/SKILL.md` | 計画書パス → `plan_$ARGUMENTS.md`、`allowed-tools` に `Edit` を追加 |
| `.claude/skills/code-review/SKILL.md` | 計画書パス → `plan_$ARGUMENTS.md` |
| `.claude/skills/implement/SKILL.md` | 計画書パス `plan_$ARGUMENTS_*.md` → `plan_$ARGUMENTS.md` |
| `.claude/skills/close/SKILL.md` | 計画書パス: `plan_I${ISSUE_NUM}_*.md` glob を削除し `plan_I${ISSUE_NUM}.md` 単ファイルに変更 |
| `.claude/skills/issue-bootstrap/SKILL.md` | イシューファイル名形式 `I${ISSUE_NUM}.md`（概要なし）を明示 |

### 4-B: open 残留重複ファイルの削除

クローズ済みイシューの open ディレクトリに残留する重複ファイルを削除する。
（すべて closed/ にも同一ファイルが存在するため、closed 側は変更しない）

**削除対象 - イシューファイル（11件）**:
- `docs/issues/open/014.md`
- `docs/issues/open/I015.md`
- `docs/issues/open/I017.md`
- `docs/issues/open/I022.md`
- `docs/issues/open/I023.md`
- `docs/issues/open/I024.md`
- `docs/issues/open/I026.md`
- `docs/issues/open/I027.md`
- `docs/issues/open/I028.md`
- `docs/issues/open/I029.md`
- `docs/issues/open/I038.md`

**削除対象 - 計画書（8件）**:
- `docs/plans/open/plan_I017_科目管理画面UX刷新.md`
- `docs/plans/open/plan_I022_onboarding_ドキュメント追加.md`
- `docs/plans/open/plan_I023_スキル品質向上.md`
- `docs/plans/open/plan_I024_Docker_webpack_キャッシュ失効対処.md`
- `docs/plans/open/plan_I026_AI駆動開発環境・プロセス総合見直し.md`
- `docs/plans/open/plan_I027_CI_annotation対応.md`
- `docs/plans/open/plan_I029_settings_json_allow拡充とPostToolUseフック追加.md`
- `docs/plans/open/plan_I038_retro スキル改善 5Whys 導入 予防処置フロー整備.md`

**削除対象 - テストファイル（20件）**:
- `docs/tests/open/I014_auto_test.md`
- `docs/tests/open/I015_auto_test.md`, `I015_manual_test.md`
- `docs/tests/open/I017_auto_test.md`, `I017_manual_test.md`
- `docs/tests/open/I022_auto_test.md`, `I022_manual_test.md`
- `docs/tests/open/I023_auto_test.md`, `I023_manual_test.md`
- `docs/tests/open/I024_auto_test.md`, `I024_manual_test.md`
- `docs/tests/open/I026_auto_test.md`, `I026_manual_test.md`
- `docs/tests/open/I027_auto_test.md`, `I027_manual_test.md`
- `docs/tests/open/I029_auto_test.md`, `I029_manual_test.md`
- `docs/tests/open/I038_auto_test.md`, `I038_manual_test.md`

**削除対象 - レビューファイル（10件）**:
- `docs/reviews/open/I014_review.md`
- `docs/reviews/open/I015_review.md`
- `docs/reviews/open/I017_review.md`
- `docs/reviews/open/I022_review.md`
- `docs/reviews/open/I023_review.md`
- `docs/reviews/open/I024_review.md`
- `docs/reviews/open/I026_review.md`
- `docs/reviews/open/I027_review.md`
- `docs/reviews/open/I029_review.md`
- `docs/reviews/open/I038_review.md`

**除外（I013）**: I013 のテスト/レビューファイルは closed にも存在するが、イシューファイル `013.md` が open のみ（クローズ未処理）のため対象外とする。

---

## 5. 実装手順

### ステップ 1: `docs/runbooks/plan-writing-rules.md` 変更

**変更箇所 1** (行頭の計画書定義):
```
変更前: 計画書（docs/plans/open/plan_[タイプ]_[概要]_[連番].md）に必ず含める:
変更後: 計画書（docs/plans/open/plan_I###.md）に必ず含める:
```

**変更箇所 2** (計画書ファイル名ルール セクション、行 88-111):
- `**計画書ファイル名ルール**` の記述を `plan_I###.md` 形式（イシュー番号のみ、概要/連番なし）に置き換える
- 例: 初回: `plan_I010.md`、再作成時: `plan_I010_2.md`
- ファイル名生成手順（bash スニペット）を `plan_I${ARGUMENTS}.md` 形式に更新

### ステップ 2: `.claude/skills/plan-issue/SKILL.md` 変更

```
変更前: - docs/issues/open/$ARGUMENTS_*.md
変更後: - docs/issues/open/$ARGUMENTS.md

変更前: - docs/plans/open/plan_$ARGUMENTS_{概要}.md（plan-writing-rules.md の命名規則に準拠）
変更後: - docs/plans/open/plan_$ARGUMENTS.md
```

### ステップ 3: `.claude/skills/plan-issue-review/SKILL.md` 変更

**変更箇所 1** (計画書パス):
```
変更前:    - docs/plans/open/$ARGUMENTS_plan.md（または plan_$ARGUMENTS_*.md）
変更後:    - docs/plans/open/plan_$ARGUMENTS.md
```

**変更箇所 2** (allowed-tools):
```
変更前: allowed-tools: Read, Glob, Grep
変更後: allowed-tools: Read, Edit, Glob, Grep
```
レビュー NG 時に計画書・テスト文書を自己修正できるようにするため。

### ステップ 4: `.claude/skills/code-review/SKILL.md` 変更

```
変更前:    - docs/plans/open/$ARGUMENTS_plan.md
変更後:    - docs/plans/open/plan_$ARGUMENTS.md
```

### ステップ 5: `.claude/skills/implement/SKILL.md` 変更

```
変更前: - docs/plans/open/plan_$ARGUMENTS_*.md（glob; 複数ある場合は最新ファイルを使用）
変更後: - docs/plans/open/plan_$ARGUMENTS.md
```

### ステップ 6: `.claude/skills/close/SKILL.md` 変更

```bash
# 変更前:
for f in docs/plans/open/plan_I${ISSUE_NUM}_*.md; do
  [ -f "$f" ] && mv "$f" docs/plans/closed/
done

# 変更後:
[ -f "docs/plans/open/plan_I${ISSUE_NUM}.md" ] && mv "docs/plans/open/plan_I${ISSUE_NUM}.md" docs/plans/closed/
```

### ステップ 7: `.claude/skills/issue-bootstrap/SKILL.md` 変更

「3. イシューファイル作成」セクションの冒頭に明示を追加:
```
**イシューファイル名形式**: `I${ISSUE_NUM}.md`（概要なし）
```

### ステップ 8: open 残留重複ファイルの削除

```bash
# イシューファイル
rm docs/issues/open/014.md docs/issues/open/I015.md docs/issues/open/I017.md \
   docs/issues/open/I022.md docs/issues/open/I023.md docs/issues/open/I024.md \
   docs/issues/open/I026.md docs/issues/open/I027.md docs/issues/open/I028.md \
   docs/issues/open/I029.md docs/issues/open/I038.md

# 計画書
rm "docs/plans/open/plan_I017_科目管理画面UX刷新.md" \
   "docs/plans/open/plan_I022_onboarding_ドキュメント追加.md" \
   "docs/plans/open/plan_I023_スキル品質向上.md" \
   "docs/plans/open/plan_I024_Docker_webpack_キャッシュ失効対処.md" \
   "docs/plans/open/plan_I026_AI駆動開発環境・プロセス総合見直し.md" \
   "docs/plans/open/plan_I027_CI_annotation対応.md" \
   "docs/plans/open/plan_I029_settings_json_allow拡充とPostToolUseフック追加.md" \
   "docs/plans/open/plan_I038_retro スキル改善 5Whys 導入 予防処置フロー整備.md"

# テストファイル
rm docs/tests/open/I014_auto_test.md \
   docs/tests/open/I015_auto_test.md docs/tests/open/I015_manual_test.md \
   docs/tests/open/I017_auto_test.md docs/tests/open/I017_manual_test.md \
   docs/tests/open/I022_auto_test.md docs/tests/open/I022_manual_test.md \
   docs/tests/open/I023_auto_test.md docs/tests/open/I023_manual_test.md \
   docs/tests/open/I024_auto_test.md docs/tests/open/I024_manual_test.md \
   docs/tests/open/I026_auto_test.md docs/tests/open/I026_manual_test.md \
   docs/tests/open/I027_auto_test.md docs/tests/open/I027_manual_test.md \
   docs/tests/open/I029_auto_test.md docs/tests/open/I029_manual_test.md \
   docs/tests/open/I038_auto_test.md docs/tests/open/I038_manual_test.md

# レビューファイル
rm docs/reviews/open/I014_review.md docs/reviews/open/I015_review.md \
   docs/reviews/open/I017_review.md docs/reviews/open/I022_review.md \
   docs/reviews/open/I023_review.md docs/reviews/open/I024_review.md \
   docs/reviews/open/I026_review.md docs/reviews/open/I027_review.md \
   docs/reviews/open/I029_review.md docs/reviews/open/I038_review.md
```

---

## 6. テスト計画

### 自動テスト
- 対象なし（ドキュメント・スキルファイルのみの変更）

### 手動テスト
- 各スキルファイルの変更後、grep で変更前パターンが残っていないことを確認
- `plan-writing-rules.md` の命名規則セクションを目視確認
- open ディレクトリに削除対象ファイルが残っていないことを確認

---

## 7. ロールバック

- 変更はすべてドキュメント（`.md`）ファイルのみ
- git revert で即時ロールバック可能
- 削除ファイルも git で復元可能

---

## 8. Risk & 回避策

| リスク | 内容 | 回避策 |
|--------|------|--------|
| close スキルで旧形式計画書を移動できない | 既存 `plan_I###_{概要}.md` は close スキルの新パターンにマッチしない | 旧形式ファイルはすべてこの I039 でクリーンアップ済み（削除対象に含む） |
| 変更漏れ | スキルファイル 1 つでも変更漏れがあると不整合が残る | 受け入れ条件でファイルごとに確認 |
| 誤削除 | 削除前に closed に存在することを確認済み | 実装前に再度 ls で確認する |

---

## 9. 設計判断

| 判断項目 | 根拠 |
|----------|------|
| 計画書名を `plan_I###.md`（概要なし）とする | イシューに明記 |
| `issue-bootstrap/SKILL.md` に `I${ISSUE_NUM}.md` 形式を明示追記 | イシューに明記 |
| `close` スキルを新形式単ファイルのみに変更（案B） | ユーザー指示 |
| `plan-writing-rules.md` の BUG/FEAT/FIX 等のタイプ命名規則は維持 | イシューは I### のみ言及 |
| open 重複ファイルを「移動」でなく「削除」とする | closed に同一ファイルが存在するため移動は不要 |
| I013 は対象外 | イシューファイルが open のみ（クローズ未処理） |
