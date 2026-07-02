This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Claude Code 運用（プロジェクト憲法）

## プロジェクト概要
学習アプリ - Django REST Framework + React TypeScript

このリポジトリでは Claude Code（Cursor 経由）に実装を委任します。
安全性と再現性のため、作業は「イシュー → 計画 → 実装 → テスト → レビュー → マージ」の順でのみ進めます。

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
- レビュールール: docs/runbooks/review-rules.md
- テンプレート同期: docs/runbooks/template-sync.md
- pre-commit 運用: docs/runbooks/pre-commit.md

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
1) 計画書に書いていない実装は禁止（より良い案がある場合は提案→承認→計画書更新が先）。
2) ユーザー承認なしにコード変更（Edit/Write/MultiEdit 等）を開始しない（読み取り・調査は可）。
3) develop/main への直 push 禁止。イシューごとにブランチを作り、PR 経由で develop にマージする。
4) 危険操作は承認制（例：データ削除/トランケート/破壊的マイグレーション/大量更新/強制 push 等）。
5) すべての作業は「記録（plan / tests / review）」が残る形で進める。

## 2. 使うスキル（/ で実行）
詳細は `docs/runbooks/workflow.md` の「使うスキル」セクションを参照。

## 3. 権限と二重ガード
- 権限（allow/ask/deny）は .claude/settings.json
- hooks（PreToolUse）で危険操作をブロックする（scripts/claude/hooks/pretooluse_guard.py）
- hooks（PostToolUse）で Edit/Write 直後の .py/.json/.yaml 構文を検証する（scripts/claude/hooks/posttooluse_check.py）
