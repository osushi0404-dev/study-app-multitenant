# I045 自動テスト

## 対象
- `.claude/skills/plan-issue-review/SKILL.md`
- `.claude/skills/code-review/SKILL.md`

## 方針

本イシューの変更対象はスキルファイル（`.claude/skills/` 配下の Markdown）のみであり、
バックエンド・フロントエンドのコード変更はない。

自動テスト（pytest / Jest）の対象外とする。
検証は手動テスト（I045_manual_test.md）および Claude によるファイル内容確認で実施する。

## 実施する検証コマンド（/test スキルで Claude が実行）

```bash
# 行数確認
wc -l .claude/skills/plan-issue-review/SKILL.md
wc -l .claude/skills/code-review/SKILL.md

# P3/P5/P8 セクションの存在確認
grep -n "P3. データ整合性" .claude/skills/plan-issue-review/SKILL.md
grep -n "P5. 運用性" .claude/skills/plan-issue-review/SKILL.md
grep -n "P8. コスト" .claude/skills/plan-issue-review/SKILL.md
grep -n "P3. データ整合性" .claude/skills/code-review/SKILL.md
grep -n "P5. 運用性" .claude/skills/code-review/SKILL.md
grep -n "P8. コスト" .claude/skills/code-review/SKILL.md
```

期待値:
- 各 wc -l の結果が 500 以下
- 各 grep が1件以上ヒットする（セクションが存在する）
