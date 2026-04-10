---
name: implement
description: Implement an approved plan, run type checks, push to PR.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /implement

必読:
- docs/plans/open/plan_$ARGUMENTS.md
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
   - セキュリティ・ベストプラクティス・モダン開発の観点で最適な実装を採用する
   - より良い方法がある場合は plan-writing-rules.md の「改善提案フォーマット」に従い提案してから実装する
2) ビルド・型チェック・リント・セキュリティスキャンを実行してクリーンを確認:
   - Backend: flake8（全エラー修正）/ bandit（MEDIUM 以上を修正対象。LOW は # nosec で抑制・理由記載必須）/ 未使用変数・import の残留がないこと
   - Frontend: react-scripts build（型チェック）/ ESLint（error を修正対象、warning は記録）/ npm audit（high/critical を修正対象、moderate は記録・期限設定）
   - 修正対象の警告・エラーがある場合は修正してから次のステップへ
3) commit/push して PR を更新
4) 停止し以下を案内:
   ```
   ✅ push 完了。
   👉 `/code-review $ARGUMENTS` を実行してください。
   ```
