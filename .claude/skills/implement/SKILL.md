---
name: implement
description: Implement an approved plan, run automated tests, update PR and docs.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /implement

必読:
- docs/plans/open/$ARGUMENTS_plan.md
- docs/tests/open/$ARGUMENTS_auto_test.md
- docs/tests/open/$ARGUMENTS_manual_test.md
- docs/reviews/open/$ARGUMENTS_review.md

ルール:
- 計画書に書いていない実装は禁止。必要なら停止→提案→承認→計画更新。
- Danger Ops は danger-approved + DANGER_OK=1 が必須。

手順:
1) 計画どおり実装
2) 自動テスト実行（失敗時は /fix-loop へ）
3) docs/reviews と docs/tests に結果を記録
4) commit/push して PR を更新
5) 手動テスト要点を提示してユーザー検証（OK/NG）待ち
