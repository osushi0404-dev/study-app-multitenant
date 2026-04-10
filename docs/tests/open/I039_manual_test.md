# I039 手動テスト仕様

## テスト対象
スキル間ファイル名参照の不整合修正（ドキュメント・スキルファイルのみ）

---

## MT-01: plan-writing-rules.md の命名規則確認

**手順**:
1. `docs/runbooks/plan-writing-rules.md` を開く
2. 計画書ファイル名ルールのセクションを確認

**確認項目**:
- [ ] `plan_I###.md`（概要なし）形式が命名規則として記載されている
- [ ] 旧形式 `plan_[タイプ]_[概要]_[連番].md` の記述が除去・更新されている
- [ ] ファイル名生成手順（bash スニペット）が `plan_I${ARGUMENTS}.md` 形式になっている

---

## MT-02: plan-issue/SKILL.md の参照パス確認

**手順**:
1. `.claude/skills/plan-issue/SKILL.md` を開く

**確認項目**:
- [ ] 必読パスが `docs/issues/open/$ARGUMENTS.md`（ワイルドカードなし）になっている
- [ ] 生成物の計画書パスが `docs/plans/open/plan_$ARGUMENTS.md` になっている

---

## MT-03: plan-issue-review/SKILL.md の参照パスと allowed-tools 確認

**手順**:
1. `.claude/skills/plan-issue-review/SKILL.md` を開く

**確認項目**:
- [ ] 計画書パスが `docs/plans/open/plan_$ARGUMENTS.md` になっている
- [ ] 旧パターン `$ARGUMENTS_plan.md` や `plan_$ARGUMENTS_*.md` の記述がない
- [ ] `allowed-tools` に `Edit` が追加されている（`Read, Edit, Glob, Grep`）

---

## MT-04: code-review/SKILL.md の参照パス確認

**手順**:
1. `.claude/skills/code-review/SKILL.md` を開く

**確認項目**:
- [ ] 計画書パスが `docs/plans/open/plan_$ARGUMENTS.md` になっている
- [ ] 旧パターン `$ARGUMENTS_plan.md` の記述がない

---

## MT-05: implement/SKILL.md の参照パス確認

**手順**:
1. `.claude/skills/implement/SKILL.md` を開く

**確認項目**:
- [ ] 計画書パスが `docs/plans/open/plan_$ARGUMENTS.md` になっている（glob なし）
- [ ] 旧パターン `plan_$ARGUMENTS_*.md` の記述がない

---

## MT-06: close/SKILL.md の計画書移動ロジック確認

**手順**:
1. `.claude/skills/close/SKILL.md` を開く

**確認項目**:
- [ ] `plan_I${ISSUE_NUM}.md`（新形式）が移動対象に含まれている
- [ ] glob パターン `plan_I${ISSUE_NUM}_*.md` は含まれていない（旧形式は不使用）

---

## MT-07: issue-bootstrap/SKILL.md のファイル名形式明示確認

**手順**:
1. `.claude/skills/issue-bootstrap/SKILL.md` を開く

**確認項目**:
- [ ] `I${ISSUE_NUM}.md`（概要なし）形式が明示されている

---

## MT-08: 旧形式パターンの残留チェック（grep）

**手順**:
```bash
# スキルファイルに旧パターンが残っていないことを確認
grep -r "\$ARGUMENTS_\*" .claude/skills/
grep -r "plan_\$ARGUMENTS_{" .claude/skills/
grep -r "\$ARGUMENTS_plan" .claude/skills/
```

**確認項目**:
- [ ] 上記 grep がすべて 0 件
