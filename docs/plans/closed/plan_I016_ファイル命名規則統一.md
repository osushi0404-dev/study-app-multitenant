# plan_I016_ファイル命名規則統一

## 基本情報
- **計画書ID**: plan_I016_ファイル命名規則統一
- **関連イシュー**: I016 / GitHub #36
- **作成根拠資料**: docs/issues/open/I016.md
- **実装後評価**: （未作成）
- **作成日**: 2026-03-30

---

## 背景/目的

I015 の調査で判明した、スキルファイル間・runbook 間のファイル命名規則不統一を解消する。

### 調査結果（現状の不一致）

| ドキュメント種別 | plan-writing-rules.md | plan-issue/SKILL.md（生成物欄） | implement/SKILL.md（読み取り先） | close/SKILL.md（移動パターン） | 実際のファイル例 |
|---|---|---|---|---|---|
| **計画書** | `plan_I###_概要.md` | `$ARGUMENTS_plan.md` = `I016_plan.md` ❌ | `$ARGUMENTS_plan.md` = `I016_plan.md` ❌ | `I${ISSUE_NUM}_*.md` = `I016_*.md` ❌ | `plan_I015_スキルレビュー観点追加_採番バグ修正.md` ✓ |
| **手動テスト** | 未定義 | `$ARGUMENTS_manual_test.md` = `I016_manual_test.md` ✓ | `$ARGUMENTS_manual_test.md` ✓ | `I${ISSUE_NUM}_*.md` ✓ | `I015_manual_test.md` ✓ |
| **自動テスト** | 未定義 | `$ARGUMENTS_auto_test.md` = `I016_auto_test.md` ✓ | `$ARGUMENTS_auto_test.md` ✓ | `I${ISSUE_NUM}_*.md` ✓ | `I015_auto_test.md` ✓ |
| **レビュー** | 未定義 | `$ARGUMENTS_review.md` = `I016_review.md` ✓ | `$ARGUMENTS_review.md` ✓ | `I${ISSUE_NUM}_*.md` ✓ | `I015_review.md` ✓ |

**結論**: 問題は計画書ファイル名のみ。テスト・レビューは既に統一されている。

加えて `issue-flow.md` の詳細ステップに旧形式の記述が残っている：
- テスト命名: `test_IXXX_manual.md` / `test_IXXX_auto.md`（旧）→ 実態は `I###_manual_test.md`
- レビュー命名: `reviewXXX_IYYY.md`（旧）→ 実態は `I###_review.md`

また `docs/plans/open/` に closed 済みファイルが残留している：
- `plan_I013_GitHub_Actions_CI導入.md`（`docs/plans/closed/` にも存在）
- `plan_I015_スキルレビュー観点追加_採番バグ修正.md`（同上）

### 命名規則の決定

**計画書の正式命名規則: `plan_I###_概要.md`**

根拠：
1. `docs/runbooks/plan-writing-rules.md` が明示的に `plan_I###_概要.md` を規定している
2. I004, I005, I007, I013, I015（全て最近のイシュー）がこの形式を使用
3. `_2`, `_3` 連番により複数計画書に対応できる

---

## 受け入れ条件（Acceptance Criteria）

- [ ] `plan-issue/SKILL.md` の生成物欄に正しい計画書命名（`plan_$ARGUMENTS_概要.md`）が記載されている
- [ ] `implement/SKILL.md` が `plan_I###_*.md` パターンで計画書を検索・読み込める
- [ ] `close/SKILL.md` が `plan_I${ISSUE_NUM}_*.md` パターンで計画書を移動できる
- [ ] `issue-flow.md` のテスト・レビュー命名記述が実態（`I###_manual_test.md` 等）と一致している
- [ ] `docs/plans/open/` の残留ファイル（I013, I015）が削除されている
- [ ] `docs/runbooks/review-rules.md` に Claude Code BP チェックリストが追加されている
- [ ] `plan-issue-review/SKILL.md` のレビュー観点に Claude Code BP チェックが含まれている

---

## 影響範囲

- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: なし
- スキルファイル: `.claude/skills/plan-issue/SKILL.md`, `implement/SKILL.md`, `close/SKILL.md`, `plan-issue-review/SKILL.md`
- runbooks: `docs/runbooks/issue-flow.md`, `docs/runbooks/review-rules.md`
- 既存ドキュメント: `docs/plans/open/` の残留 2 ファイル削除

---

## 変更点一覧

### 1. `.claude/skills/plan-issue/SKILL.md`

**変更箇所**: 生成物欄の計画書ファイル名

```
変更前:
- docs/plans/open/$ARGUMENTS_plan.md

変更後:
- docs/plans/open/plan_$ARGUMENTS_{概要}.md（plan-writing-rules.md の命名規則に準拠）
```

### 2. `.claude/skills/implement/SKILL.md`

**変更箇所**: 必読セクションの計画書パス

計画書は `plan_I###_概要.md` 形式のため、glob 検索で読み込む。

```
変更前:
- docs/plans/open/$ARGUMENTS_plan.md

変更後:
- docs/plans/open/plan_$ARGUMENTS_*.md（glob; 複数ある場合は最新ファイルを使用）
```

### 3. `.claude/skills/close/SKILL.md`

**変更箇所**: ステップ1 の計画書移動パターン

```bash
# 変更前
for f in docs/plans/open/I${ISSUE_NUM}_*.md; do

# 変更後
for f in docs/plans/open/plan_I${ISSUE_NUM}_*.md; do
```

### 4. `docs/runbooks/issue-flow.md`

**変更箇所**: ステップ7・ステップ8・ステップ21・ステップ26 の命名記述

| 変更前 | 変更後 |
|--------|--------|
| `test_IXXX_manual.md` | `IXXX_manual_test.md` |
| `test_IXXX_auto.md` | `IXXX_auto_test.md` |
| `reviewXXX_IYYY.md` | `IXXX_review.md` |
| `for TEST_FILE in docs/tests/open/test_IXXX_*.md` | `for TEST_FILE in docs/tests/open/IXXX_*_test.md` |
| `mv docs/reviews/open/reviewXXX_IXXX.md docs/reviews/closed/` | `mv docs/reviews/open/IXXX_review.md docs/reviews/closed/` |

### 5. 残留ファイル削除（`docs/plans/open/`）

- `docs/plans/open/plan_I013_GitHub_Actions_CI導入.md` → 削除（closed に同ファイルあり）
- `docs/plans/open/plan_I015_スキルレビュー観点追加_採番バグ修正.md` → 削除（同上）

### 6. `docs/runbooks/review-rules.md`

**変更箇所**: 末尾に新セクションを追加

```markdown
## スキルファイル変更時の Claude Code ベストプラクティス準拠（必須）

`.claude/skills/` 配下のファイルを変更するイシューでは、
変更内容が以下の Claude Code 公式ベストプラクティスに準拠していることを確認する。

### チェックリスト

| # | チェック項目 | 観点 |
|---|---|---|
| 1 | `allowed-tools` で最小権限が設定されているか | セキュリティ |
| 2 | 副作用のある操作（commit・push・デプロイ等）に `disable-model-invocation: true` が設定されているか | 安全性 |
| 3 | `argument-hint` が記載されているか | 発見性 |
| 4 | `description` に「いつ使うか」が含まれているか（250文字以内） | 発見性 |
| 5 | 指示文に明確な停止条件・完了条件が記載されているか | 明確性 |
| 6 | `$ARGUMENTS` 等の変数が一貫して使われているか | 一貫性 |
| 7 | SKILL.md が 500行以内か（超える場合は supporting files への分割を推奨） | コンテキスト効率 |

このチェックは `/plan-issue-review` のレビュー観点に組み込まれている。
```

### 7. `.claude/skills/plan-issue-review/SKILL.md`

**変更箇所**: レビュー観点のセクションに「Claude Code ベストプラクティス」を追加

```markdown
**Claude Code ベストプラクティス（`.claude/skills/` 変更を含む場合のみ）:**
変更対象に `.claude/skills/` が含まれる場合、以下を確認する:
- [ ] `allowed-tools` で最小権限が設定されているか
- [ ] 副作用のある操作に `disable-model-invocation: true` が設定されているか
- [ ] `argument-hint` が記載されているか
- [ ] `description` に「いつ使うか」が含まれているか（250文字以内）
- [ ] 指示文に明確な停止条件・完了条件が記載されているか
- [ ] `$ARGUMENTS` 等の変数が一貫して使われているか
- [ ] SKILL.md が 500行以内か（超える場合は supporting files を推奨）
問題がなければ「問題なし」と記載する。
```

---

## 実装手順

1. `plan-issue/SKILL.md` の生成物欄を修正
2. `implement/SKILL.md` の必読セクションを修正
3. `close/SKILL.md` の計画書移動パターンを修正
4. `issue-flow.md` のテスト・レビュー命名記述を修正（4 箇所）
5. `docs/plans/open/` の残留ファイル 2 件を削除（事前に diff で同一性確認）
6. `review-rules.md` に Claude Code BP セクションを追加
7. `plan-issue-review/SKILL.md` にレビュー観点を追加
8. 変更をコミット・push

---

## テスト計画

- 自動テスト: なし（スキルファイル・runbook のみの変更）
- 手動テスト: `docs/tests/open/I016_manual_test.md` 参照

---

## ロールバック

git revert で対象コミットを戻す。ファイル変更のみのため副作用なし。

---

## Risk & 回避策

| リスク | 回避策 |
|--------|--------|
| issue-flow.md の他箇所に旧命名が残る | Grep で全文検索してから修正する |
| 削除するファイルが closed の内容と異なる | 削除前に diff で同一性を確認する |
| 他のスキルファイルにも同様の参照がある | 修正前に全スキルを grep して確認する |

---

## 承認ポイント

### 設計判断の明示

| 設計判断 | 根拠 |
|----------|------|
| 計画書の正式命名は `plan_I###_概要.md` | **イシューに明記されている**（plan-writing-rules.md が既に規定、I013/I015 の実ファイルで確認済み） |
| テスト命名は `I###_manual_test.md` / `I###_auto_test.md` | **イシューに明記されている**（実ファイル確認済み） |
| レビュー命名は `I###_review.md` | **イシューに明記されている**（実ファイル確認済み） |
| 既存の旧形式 closed ファイル（`I006_plan.md` 等）はリネームしない | **仮定で決めた**（スコープ外と判断） |
| open/ の残留ファイルは削除（closed に同内容あり） | **仮定で決めた**（既にクローズ済みのため） |

### 仮定で決めた項目の確認

以下 2 点についてユーザーの確認が必要です：

1. **既存の旧形式 closed ファイル（`I006_plan.md`, `I010_plan.md`, `I011_plan.md`, `I012_plan.md`, `I014_plan.md`）はリネームしない**
   - これらはすでにクローズ済みで将来の `/close` スキルに影響しないため、対象外としてよいか？

2. **`docs/plans/open/` 残留ファイル 2 件を削除してよいか**
   - `plan_I013_GitHub_Actions_CI導入.md`（closed に同じ内容あり）
   - `plan_I015_スキルレビュー観点追加_採番バグ修正.md`（同上）
   - 削除前に diff を取り、差分がないことを確認してから削除する

上記 2 点の確認後、承認をいただければ実装に進みます。
