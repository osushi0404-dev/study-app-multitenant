---
name: fix-loop
description: When NG or tests fail: record facts, propose delta plan, get approval, fix, re-test.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /fix-loop

1) NG内容を「再現手順/期待/実際/ログ」に分解して記録
2) 差分計画を docs/plans/open/$ARGUMENTS_plan.md に追記（または更新）
3) 承認待ちで停止
4) 承認後に修正→再テスト→記録更新→再検証
