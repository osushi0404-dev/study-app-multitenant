---
name: plan
description: Create plan + tests + review docs for an issue. No code changes.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /plan

必読:
- docs/issues/open/$ARGUMENTS_*.md
- docs/runbooks/plan-writing-rules.md
- rules/ultimate_django_coding_standards.md
- rules/react-coding-standards-integrated.md

生成物:
- docs/plans/open/$ARGUMENTS_plan.md
- docs/tests/open/$ARGUMENTS_manual_test.md
- docs/tests/open/$ARGUMENTS_auto_test.md
- docs/reviews/open/$ARGUMENTS_review.md

禁止:
- コード変更（承認前のEdit/Write開始は禁止）

完了したら「承認ポイント」を提示して停止する。
