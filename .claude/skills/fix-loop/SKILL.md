---
name: fix-loop
description: When NG or tests fail: record facts, propose delta plan, get approval, fix, re-test.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /fix-loop

1) 失敗内容を「再現手順 / 期待値 / 実際値 / ログ」に分解して報告
2) 根本原因を調査・分析して報告（なぜ失敗したか）
3) 対応方法を複数案提示（各案にメリット・デメリットを添える）
4) 承認待ちで停止（ユーザーが案を選択）
5) 選択された案で修正
6) 自動テスト実行
   - 成功: 手順 7) へ
   - 失敗: 手順 1) に戻る（ループ）
7) 再発防止記録を docs/tests/open/$ARGUMENTS_auto_test.md に追記:
   - なぜ失敗したか
   - 何を変えたか
   - 次回どう防ぐか
