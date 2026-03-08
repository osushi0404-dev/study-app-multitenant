---
name: fix-loop
description: When NG or tests fail: record facts, propose delta plan, get approval, fix, re-test.
argument-hint: "[issue_number]"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /fix-loop

## 引数

`$ARGUMENTS` = GitHub Issue番号（例: `8`）

## 手順

1. NG 内容を「再現手順 / 期待 / 実際 / ログ」に分解して記録
   → `docs/work/open/$ARGUMENTS/40_error_log.md` に追記（ファイルがなければ作成）

2. 差分計画を**上書き禁止**で新規ファイルとして作成
   ```bash
   # 既存の計画書番号を確認して次の番号で作成
   ls docs/work/open/$ARGUMENTS/10_plan*.md
   # 例: 10_plan.md が存在 → 10_plan_2.md を作成
   #     10_plan_2.md も存在 → 10_plan_3.md を作成
   ```
   → `docs/work/open/$ARGUMENTS/10_plan_2.md`（または `10_plan_3.md` ...）

3. 承認待ちで停止

4. 承認後に修正 → 再テスト → `20_test_auto.md` に記録更新 → 再検証
