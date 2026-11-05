This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Claude Code 運用（プロジェクト憲法）

## プロジェクト概要
学習アプリ - Django REST Framework + React TypeScript

このリポジトリでは Claude Code（Cursor 経由）に実装を委任します。
安全性と再現性のため、作業は「イシュー → 計画（レビュー） → 実装 → レビュー → テスト → 振り返り → クローズ → マージ」の順でのみ進めます。ユーザーが打つのは `/plan-issue`（・任意の `/grill-me`・途中から再開する `/proceed`）だけで、その間の段階は Claude が順に進めます（docs/runbooks/workflow.md）。起票（`issue-bootstrap`）は、会話の中で別イシューにすると決まったら Claude が自分で行い、後で報告します（ユーザーが `/issue-bootstrap` を打ってもよい）。

## 0. 参照先（このファイルは短く保つ）
詳細ルールは以下へ集約します（この CLAUDE.md にルールを増やさないこと）。

運用・ルール:
- 運用フロー: docs/runbooks/workflow.md
- 並行トラック運用（worktree）: docs/runbooks/worktree.md
- 計画書の書き方: docs/runbooks/plan-writing-rules.md
- 危険操作（破壊的変更）: docs/runbooks/danger-ops.md
- よく使うコマンド: docs/runbooks/common-commands.md
- イシューフロー: docs/runbooks/issue-flow.md
- UXルール: docs/runbooks/ux-rules.md
- バックエンドチェック: docs/runbooks/backend-check.md
- 依存監査と Dependabot: docs/runbooks/dependency-audit.md
- レビュールール: docs/runbooks/review-rules.md
- テンプレート同期: docs/runbooks/template-sync.md
- pre-commit 運用: docs/runbooks/pre-commit.md
- フロントの画面確認（アプリ起動・Playwright MCP）: docs/runbooks/frontend-verify.md

セットアップ・環境構築:
- オンボーディング（全体の進め方）: docs/runbooks/onboarding.md
- ブランチ保護設定: docs/runbooks/branch-protection-setup.md
- GitHub MCP セットアップ: docs/runbooks/mcp-github-setup.md
- MCP 利用ガイドライン: docs/runbooks/mcp-usage.md

コーディング規約（必読）:
- Backend: rules/ultimate_django_coding_standards.md
- Frontend: rules/react-coding-standards-integrated.md

プロダクト品質基準（設計の北極星）:
- 良い学習アプリの品質基準（C1〜C8）: docs/proposals/learning_app_quality_criteria.md

## 1. 絶対ルール（破ったら中断）
1) 計画書に書いていない実装はしない。必要になったら計画書を先に直し、計画レビューを通してから行う。
2) ユーザーに確認するのは「人がやる手動テスト」「マージ」と、docs/runbooks/workflow.md「止めて聞く条件」に当たるとき（要件・基本設計・UI/UX の価値判断／取り消せない操作・安全装置そのものの変更／安全側の選択肢も取れない上限到達）だけ。それ以外は Claude が決めて「自律判断の記録」に残す。
3) develop/main への直 push 禁止。イシューごとにブランチを作り、PR 経由で develop にマージする。
4) 危険操作は承認制（例：データ削除/トランケート/破壊的マイグレーション/大量更新/強制 push 等）。
5) すべての作業は「記録（plan / tests / review）」が残る形で進める。

## 2. 使うスキル（/ で実行）
詳細は `docs/runbooks/workflow.md` の「使うスキル」セクションを参照。

## 3. 権限と二重ガード
- 権限（allow/ask/deny）は .claude/settings.json
- hooks（PreToolUse）で危険操作をブロックする（scripts/claude/hooks/pretooluse_guard.py）
- hooks（PostToolUse）で Edit/Write 直後の .py/.json/.yaml 構文を検証する（scripts/claude/hooks/posttooluse_check.py）
