# I016 手動テスト: ファイル命名規則統一

## テスト対象
- `.claude/skills/plan-issue/SKILL.md`
- `.claude/skills/implement/SKILL.md`
- `.claude/skills/close/SKILL.md`
- `docs/runbooks/issue-flow.md`

## テスト項目

### MT-01: plan-issue/SKILL.md の生成物欄確認

| 確認項目 | 期待値 | 結果 |
|----------|--------|------|
| 計画書の生成物欄が `plan_$ARGUMENTS_{概要}.md` 形式になっている | 記載あり | [ ] |
| テスト・レビュー欄は変更なし（`$ARGUMENTS_auto_test.md` 等） | 変更なし | [ ] |

### MT-02: implement/SKILL.md の計画書読み込み記述確認

| 確認項目 | 期待値 | 結果 |
|----------|--------|------|
| 必読欄の計画書が `plan_$ARGUMENTS_*.md` (glob) 形式になっている | 記載あり | [ ] |
| 旧形式 `$ARGUMENTS_plan.md` が残っていない | 残っていない | [ ] |

### MT-03: close/SKILL.md の計画書移動パターン確認

| 確認項目 | 期待値 | 結果 |
|----------|--------|------|
| `for f in docs/plans/open/plan_I${ISSUE_NUM}_*.md` になっている | 記載あり | [ ] |
| 旧形式 `I${ISSUE_NUM}_*.md` パターンが残っていない | 残っていない | [ ] |

### MT-04: issue-flow.md のテスト命名記述確認

| 確認項目 | 期待値 | 結果 |
|----------|--------|------|
| `test_IXXX_manual.md` の記述が `IXXX_manual_test.md` に置き換わっている | 置き換わり済み | [ ] |
| `test_IXXX_auto.md` の記述が `IXXX_auto_test.md` に置き換わっている | 置き換わり済み | [ ] |
| `reviewXXX_IYYY.md` の記述が `IXXX_review.md` に置き換わっている | 置き換わり済み | [ ] |

### MT-05: orphaned ファイル削除確認

| 確認項目 | 期待値 | 結果 |
|----------|--------|------|
| `docs/plans/open/plan_I013_GitHub_Actions_CI導入.md` が存在しない | 削除済み | [ ] |
| `docs/plans/open/plan_I015_スキルレビュー観点追加_採番バグ修正.md` が存在しない | 削除済み | [ ] |
| 各ファイルは `docs/plans/closed/` に同内容が存在する | 存在する | [ ] |

## 合否基準

全項目 ✓ → OK
1 項目でも ✗ → NG（/fix-loop へ）
