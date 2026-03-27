# I012 計画書: クローズ済みイシューファイルの open フォルダ残留対応と根本原因修正

## 基本情報
- **計画書ID**: plan_I012_open_folder_cleanup
- **関連イシュー**: I012 (GitHub #28)
- **作成日**: 2026-03-27

---

## 背景/目的

クローズ済みイシュー（I006, I007, I010, I011）のファイルが `docs/*/open/` に残留している。
根本原因は `/close` スキル（SKILL.md）の手順が抽象的で具体的な `mv` コマンドが未定義なこと、
および `settings.json` で `Bash(mv *)` が `ask`（確認必要）のため誤って拒否された可能性が高いこと。

---

## 調査結果

### open に残っている stale ファイル一覧

| フォルダ | ファイル | closed に存在するか | 備考 |
|---------|---------|-------------------|------|
| `docs/issues/open/` | 006.md, 007.md, 010.md, 011.md | ✅ | closed 版と内容同一 |
| `docs/plans/open/` | I006_plan.md, I010_plan.md, I011_plan.md | ✅ | closed 版は I010/I011 に「完了情報」セクション追加済み |
| `docs/tests/open/` | I006_auto_test.md, I006_manual_test.md, I010_auto_test.md, I010_manual_test.md, I011_auto_test.md, I011_manual_test.md | ✅ | closed 版と同一 |
| `docs/reviews/open/` | I006_review.md, I010_review.md, I011_review.md | ✅ | closed 版と同一 |

### 根本原因

1. **`/close` SKILL.md が抽象的**: ステップ1「docs/*/open の対象 I### ファイルを closed へ移動」とだけ書かれており、具体的な `mv` コマンドが一切定義されていない
2. **`Bash(mv *)` が `ask` 権限**: `settings.json` にて `mv` は確認必要のため、実行時に毎回ダイアログが発生し、誤って拒否またはスキップされた

---

## 受け入れ条件

- [ ] `docs/issues/open/` に closed 済みイシューファイル（006, 007, 010, 011）が存在しない
- [ ] `docs/plans/open/` に closed 済み計画書（I006, I010, I011）が存在しない
- [ ] `docs/tests/open/` に closed 済みテストケース（I006, I010, I011 系）が存在しない
- [ ] `docs/reviews/open/` に closed 済みレビューファイル（I006, I010, I011）が存在しない
- [ ] `settings.json` に `Bash(mv docs/*/open/* docs/*/closed/)` と `Bash(rm docs/*/open/*)` が allow で追加されている
- [ ] `/close` SKILL.md にファイル種別ごとの具体的な `mv` コマンドが明記されている

---

## 影響範囲

- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `.claude/settings.json`（allow パターン追加）
- ドキュメント/スキル: `.claude/skills/close/SKILL.md`

---

## 変更点一覧

| # | 対象 | 変更内容 |
|---|------|---------|
| 1 | `docs/issues/open/` | 006.md, 007.md, 010.md, 011.md を削除 |
| 2 | `docs/plans/open/` | I006_plan.md, I010_plan.md, I011_plan.md を削除 |
| 3 | `docs/tests/open/` | I006_auto_test.md, I006_manual_test.md, I010_auto_test.md, I010_manual_test.md, I011_auto_test.md, I011_manual_test.md を削除 |
| 4 | `docs/reviews/open/` | I006_review.md, I010_review.md, I011_review.md を削除 |
| 5 | `.claude/settings.json` | allow に `Bash(mv docs/*/open/* docs/*/closed/)` と `Bash(rm docs/*/open/*)` を追加 |
| 6 | `.claude/skills/close/SKILL.md` | ステップ1をファイル種別ごとの具体的な `mv` コマンドに書き換え |

---

## 実装手順

### Step 1: stale ファイルの削除

```bash
# イシューファイル
rm docs/issues/open/006.md
rm docs/issues/open/007.md
rm docs/issues/open/010.md
rm docs/issues/open/011.md

# 計画書
rm docs/plans/open/I006_plan.md
rm docs/plans/open/I010_plan.md
rm docs/plans/open/I011_plan.md

# テストケース
rm docs/tests/open/I006_auto_test.md
rm docs/tests/open/I006_manual_test.md
rm docs/tests/open/I010_auto_test.md
rm docs/tests/open/I010_manual_test.md
rm docs/tests/open/I011_auto_test.md
rm docs/tests/open/I011_manual_test.md

# レビュー
rm docs/reviews/open/I006_review.md
rm docs/reviews/open/I010_review.md
rm docs/reviews/open/I011_review.md
```

### Step 2: settings.json に allow パターンを追加

`.claude/settings.json` の `allow` に以下を追加：

```json
"Bash(mv docs/*/open/* docs/*/closed/)",
"Bash(rm docs/*/open/*)"
```

### Step 3: /close SKILL.md を修正

`.claude/skills/close/SKILL.md` のステップ1を以下に書き換え：

```
1) docs/*/open の対象 I### ファイルを closed へ移動（以下を順番に実行）:
   ```bash
   ISSUE_NUM="###"  # 実際のイシュー番号（3桁）に置き換える

   # イシューファイル
   mv docs/issues/open/${ISSUE_NUM}.md docs/issues/closed/

   # 計画書（複数ある場合はパターンで対応）
   for f in docs/plans/open/I${ISSUE_NUM}_*.md; do
     [ -f "$f" ] && mv "$f" docs/plans/closed/
   done

   # テストケース
   for f in docs/tests/open/I${ISSUE_NUM}_*.md; do
     [ -f "$f" ] && mv "$f" docs/tests/closed/
   done

   # レビュー
   for f in docs/reviews/open/I${ISSUE_NUM}_*.md; do
     [ -f "$f" ] && mv "$f" docs/reviews/closed/
   done
   ```
   移動後、open に残留ファイルがないことを確認:
   ```bash
   ls docs/issues/open/ docs/plans/open/ docs/tests/open/ docs/reviews/open/
   ```
```

---

## テスト計画

- **自動テスト**: なし（ドキュメント整理・設定変更のみ）
- **手動テスト**: open フォルダに stale ファイルが残っていないことを ls で確認

---

## ロールバック

- stale ファイルの削除は git で復元可能（`git checkout HEAD -- docs/issues/open/006.md` 等）
- settings.json の変更は手動で該当行を削除
- SKILL.md の変更は git で復元可能

---

## Risk & 回避策

| リスク | 対策 |
|-------|------|
| 間違えて I012 のファイルを削除する | 削除対象ファイルを 1 つずつ明示してから実行 |
| closed 側の最終版を上書き/削除してしまう | 削除は open のみ。closed は一切触らない |
