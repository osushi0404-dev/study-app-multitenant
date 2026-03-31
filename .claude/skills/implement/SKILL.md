---
name: implement
description: Implement an approved plan, run type checks, push to PR.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /implement

必読:
- docs/plans/open/plan_$ARGUMENTS_*.md（glob; 複数ある場合は最新ファイルを使用）
- docs/tests/open/$ARGUMENTS_auto_test.md
- docs/tests/open/$ARGUMENTS_manual_test.md
- docs/reviews/open/$ARGUMENTS_review.md

ルール:
- 計画書に書いていない実装は禁止。必要なら停止→提案→承認→計画更新。
- Danger Ops は danger-approved + DANGER_OK=1 が必須。
- テストフレームワーク（pytest 等）が存在しない・追加が必要な場合はユーザーに承認を得てからインストールする。
- 既存テストファイルのフレームワーク・形式（pytest / Django TestCase 等）を変更する場合もユーザーの承認が必須。承認なしの形式変更は禁止。

前提:
- /plan-issue の承認（「OK」「承認」等）だけでは実装を開始しない
- ユーザーが明示的に /implement を実行して初めて実装を開始する

手順:
1) 計画どおり実装
2) ビルド・型チェックを実行してクリーンを確認（未使用変数・import の残留がないこと）
3) commit/push して PR を更新
4) 停止し以下を案内:
   ```
   ✅ push 完了。
   👉 `/code-review $ARGUMENTS` を実行してください。
   ```
