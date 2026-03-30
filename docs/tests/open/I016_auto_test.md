# I016 自動テスト: ファイル命名規則統一

## テスト対象
スキルファイル・runbook のテキスト内容変更のみ。コード変更なし。

## 自動テスト項目

### AT-01: 旧命名の残留チェック（grep）

```bash
# plan-issue/SKILL.md に旧形式が残っていないこと
grep -n '\$ARGUMENTS_plan\.md' .claude/skills/plan-issue/SKILL.md
# → 0件であること

# implement/SKILL.md に旧形式が残っていないこと
grep -n '\$ARGUMENTS_plan\.md' .claude/skills/implement/SKILL.md
# → 0件であること

# close/SKILL.md に旧形式パターンが残っていないこと
grep -n 'plans/open/I\${ISSUE_NUM}_' .claude/skills/close/SKILL.md
# → 0件であること

# issue-flow.md に旧テスト命名が残っていないこと
grep -n 'test_I[0-9]*_manual\|test_I[0-9]*_auto' docs/runbooks/issue-flow.md
# → 0件であること

# issue-flow.md に旧レビュー命名が残っていないこと
grep -n 'review[0-9]*_I[0-9]*' docs/runbooks/issue-flow.md
# → 0件であること
```

### AT-02: 新命名の存在チェック（grep）

```bash
# plan-issue/SKILL.md に新形式が記載されていること
grep -n 'plan_\$ARGUMENTS' .claude/skills/plan-issue/SKILL.md
# → 1件以上

# implement/SKILL.md に glob 形式が記載されていること
grep -n 'plan_\$ARGUMENTS_\*' .claude/skills/implement/SKILL.md
# → 1件以上

# close/SKILL.md に新パターンが記載されていること
grep -n 'plans/open/plan_I\${ISSUE_NUM}_' .claude/skills/close/SKILL.md
# → 1件以上
```

### AT-03: orphaned ファイル削除チェック

```bash
# open/ に残留ファイルがないこと
ls docs/plans/open/plan_I013_*.md 2>/dev/null && echo "NG: I013 残留" || echo "OK"
ls docs/plans/open/plan_I015_*.md 2>/dev/null && echo "NG: I015 残留" || echo "OK"

# closed/ に同ファイルが存在すること
ls docs/plans/closed/plan_I013_*.md && echo "OK" || echo "NG: I013 closed なし"
ls docs/plans/closed/plan_I015_*.md && echo "OK" || echo "NG: I015 closed なし"
```

## 合否基準

全コマンドが期待通りの出力 → OK
1件でも期待と異なる → NG（/fix-loop へ）

## 備考

本イシューはドキュメント・スキルファイルのみの変更。
pytest / Jest は対象外。
