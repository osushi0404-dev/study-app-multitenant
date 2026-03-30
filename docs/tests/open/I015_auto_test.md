# I015 自動テスト

## テスト対象
スキルファイル（Markdown）の変更のため、自動テスト対象は bash スニペット（採番ロジック）とファイル存在・キーワード確認のみ。

---

## AT-1: 採番ロジックの8進数誤解釈修正

```bash
FS_MAX=014
GIT_MAX=014
FS_NUM=$((10#${FS_MAX:-0}))
GIT_NUM=$((10#${GIT_MAX:-0}))
if [ "$FS_NUM" -gt "$GIT_NUM" ]; then LAST_NUM=$FS_NUM; else LAST_NUM=$GIT_NUM; fi
NEXT_NUM=$((LAST_NUM + 1))
ISSUE_NUM=$(printf "%03d" $NEXT_NUM)
[ "$ISSUE_NUM" = "015" ] && echo "PASS: ISSUE_NUM=015" || echo "FAIL: got $ISSUE_NUM"
```

期待結果: `PASS: ISSUE_NUM=015`

---

## AT-2: スキルファイルの必須キーワード存在確認

```bash
echo "=== code-review: 3観点キーワード確認 ==="
grep -qE "OWASP|XSS|SQLインジェクション" .claude/skills/code-review/SKILL.md \
  && echo "PASS: セキュリティキーワード存在" || echo "FAIL"
grep -qE "N\+1|アクセシビリティ|HTTPステータスコード" .claude/skills/code-review/SKILL.md \
  && echo "PASS: モダン開発キーワード存在" || echo "FAIL"

echo "=== plan-issue-review: ファイル存在確認 ==="
[ -f ".claude/skills/plan-issue-review/SKILL.md" ] \
  && echo "PASS: ファイル存在" || echo "FAIL: ファイルなし"

echo "=== plan-issue-review: 3観点キーワード確認 ==="
grep -qE "ベストプラクティス" .claude/skills/plan-issue-review/SKILL.md \
  && echo "PASS" || echo "FAIL"
grep -qE "セキュリティ" .claude/skills/plan-issue-review/SKILL.md \
  && echo "PASS" || echo "FAIL"
grep -qE "モダン" .claude/skills/plan-issue-review/SKILL.md \
  && echo "PASS" || echo "FAIL"

echo "=== issue-bootstrap: 修正スクリプト確認 ==="
grep -q '10#' .claude/skills/issue-bootstrap/SKILL.md \
  && echo "PASS: 10# 構文存在" || echo "FAIL: 修正スクリプトなし"
grep -qv 'printf "%d\\n%d\\n"' .claude/skills/issue-bootstrap/SKILL.md \
  && echo "PASS: 旧コードなし" || echo "FAIL: 旧コードが残存"

echo "=== CLAUDE.md: plan-issue-review 記載確認 ==="
grep -q "plan-issue-review" CLAUDE.md \
  && echo "PASS" || echo "FAIL"

echo "=== workflow.md: plan-issue-review 記載確認 ==="
grep -q "plan-issue-review" docs/runbooks/workflow.md \
  && echo "PASS" || echo "FAIL"

echo "=== workflow.md: retro がワークフロースキルリストに存在 ==="
grep -q "retro" docs/runbooks/workflow.md \
  && echo "PASS" || echo "FAIL"

echo "=== issue-flow.md: plan-issue-review 記載確認 ==="
grep -q "plan-issue-review" docs/runbooks/issue-flow.md \
  && echo "PASS" || echo "FAIL"

echo "=== issue-flow.md: retro 記載確認 ==="
grep -q "retro" docs/runbooks/issue-flow.md \
  && echo "PASS" || echo "FAIL"
```

期待結果: 全項目 `PASS`

---

## 備考
- Backend/Frontend テスト（pytest / Jest）は対象なし
