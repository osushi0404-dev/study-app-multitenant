# I023 自動テスト

## 対象スキル
- `.claude/skills/fix-loop/SKILL.md`
- `.claude/skills/plan-issue/SKILL.md`
- `.claude/skills/implement/SKILL.md`

## 自動テスト（内容検証）

スキルファイルはテキストファイルのため、自動テストは grep による内容存在確認で行う。

```bash
# /fix-loop: セキュリティ観点の追加確認
grep -q "セキュリティ観点" .claude/skills/fix-loop/SKILL.md && echo "OK" || echo "NG"
grep -q "OWASP" .claude/skills/fix-loop/SKILL.md && echo "OK" || echo "NG"
grep -q "bandit" .claude/skills/fix-loop/SKILL.md && echo "OK" || echo "NG"
grep -q "npm audit" .claude/skills/fix-loop/SKILL.md && echo "OK" || echo "NG"
grep -q "セキュリティ上の考慮点" .claude/skills/fix-loop/SKILL.md && echo "OK" || echo "NG"

# /plan-issue: セキュリティ・ベストプラクティスチェックの追加確認
grep -q "セキュリティ・ベストプラクティスチェック" .claude/skills/plan-issue/SKILL.md && echo "OK" || echo "NG"
grep -q "OWASP" .claude/skills/plan-issue/SKILL.md && echo "OK" || echo "NG"
grep -q "最小権限" .claude/skills/plan-issue/SKILL.md && echo "OK" || echo "NG"

# /implement: セキュリティ・ベストプラクティス採用指針の追加確認
grep -q "セキュリティ・ベストプラクティス" .claude/skills/implement/SKILL.md && echo "OK" || echo "NG"
grep -q "bandit" .claude/skills/implement/SKILL.md && echo "OK" || echo "NG"
grep -q "npm audit" .claude/skills/implement/SKILL.md && echo "OK" || echo "NG"
```

## 期待結果
全項目 `OK` であること

## NG 時の記録
（NG 発生時に追記）

## 実施記録
- **実施日**: 2026-04-03
- **Backend**: 25 passed, 3 warnings（DeprecationWarning のみ・エラーなし）
- **Frontend**: 7 passed（2 suites）
- **結果**: 全項目 OK
