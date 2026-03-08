---
name: implement
description: Implement an approved plan, run automated tests, update PR and docs.
argument-hint: "[issue_number]"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /implement

## 引数

`$ARGUMENTS` = GitHub Issue番号（例: `8`）

## 必読（実装前に必ず確認）

```bash
# 最新の計画書（差分計画があれば最大番号のものも読む）
ls docs/work/open/$ARGUMENTS/10_plan*.md
cat docs/work/open/$ARGUMENTS/10_plan.md

cat docs/work/open/$ARGUMENTS/20_test_auto.md
cat docs/work/open/$ARGUMENTS/21_test_manual.md
cat docs/work/open/$ARGUMENTS/30_review_*.md
```

## ルール

- 計画書に書いていない実装は禁止。必要なら停止 → 提案 → 承認 → 計画更新（`10_plan_2.md` を新規作成）。
- Danger Ops は `danger-approved` ラベル + `DANGER_OK=1` が必須。

## 手順

1. 計画どおり実装
2. 自動テスト実行（失敗時は `/fix-loop $ARGUMENTS` へ）
3. `docs/work/open/$ARGUMENTS/20_test_auto.md` に結果を記録
4. `docs/work/open/$ARGUMENTS/30_review_*.md` に実装サマリを記録
5. commit/push して PR を更新
6. 手動テスト要点を提示してユーザー検証（OK/NG）待ち
