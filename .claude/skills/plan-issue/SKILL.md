---
name: plan-issue
description: Create plan + tests + review docs for an issue. No code changes.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /plan-issue

必読:
- docs/issues/open/$ARGUMENTS_*.md
- docs/runbooks/plan-writing-rules.md
- rules/ultimate_django_coding_standards.md
- rules/react-coding-standards-integrated.md

生成物:
- docs/plans/open/plan_$ARGUMENTS_{概要}.md（plan-writing-rules.md の命名規則に準拠）
- docs/tests/open/$ARGUMENTS_manual_test.md
- docs/tests/open/$ARGUMENTS_auto_test.md
- docs/reviews/open/$ARGUMENTS_review.md

禁止:
- コード変更（承認前のEdit/Write開始は禁止）

承認ポイント提示前に必ず以下を実施する:

**設計判断の明示チェック（必須）**
計画書に書いた設計判断（権限範囲・エラー時の挙動・ディレクトリ構成・使用ライブラリ等）を列挙し、
それぞれについて「イシューに明記されている / 仮定で決めた」を区別して承認ポイントに記載する。
「仮定で決めた」項目が1つでもある場合は、承認ポイントより先にユーザーへ確認する。

完了したら「承認ポイント」を提示して停止する。

承認後の次のステップ: `/plan-issue-review $ARGUMENTS` を実行して計画書・テスト文書をレビューしてください。
