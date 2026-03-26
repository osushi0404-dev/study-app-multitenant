This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Claude Code 運用（プロジェクト憲法）

## プロジェクト概要
学習アプリ - Django REST Framework + React TypeScript

このリポジトリでは Claude Code（Cursor 経由）に実装を委任します。
安全性と再現性のため、作業は「イシュー → 計画 → 実装 → テスト → レビュー → マージ」の順でのみ進めます。

## 0. 参照先（このファイルは短く保つ）
詳細ルールは以下へ集約します（この CLAUDE.md にルールを増やさないこと）。

- 運用フロー: docs/runbooks/workflow.md
- 計画書の書き方: docs/runbooks/plan-writing-rules.md
- 危険操作（破壊的変更）: docs/runbooks/danger-ops.md
- よく使うコマンド: docs/runbooks/common-commands.md
- イシューフロー: docs/runbooks/issue-flow.md
- UXルール: docs/runbooks/ux-rules.md
- バックエンドチェック: docs/runbooks/backend-check.md
- レビュールール: docs/runbooks/review-rules.md
- テンプレート同期: docs/runbooks/template-sync.md

コーディング規約（必読）:
- Backend: rules/ultimate_django_coding_standards.md
- Frontend: rules/react-coding-standards-integrated.md

## 1. 絶対ルール（破ったら中断）
1) 計画書に書いていない実装は禁止（より良い案がある場合は提案→承認→計画書更新が先）。
2) ユーザー承認なしにコード変更（Edit/Write/MultiEdit 等）を開始しない（読み取り・調査は可）。
3) develop/main への直 push 禁止。イシューごとにブランチを作り、PR 経由で develop にマージする。
4) 危険操作は承認制（例：データ削除/トランケート/破壊的マイグレーション/大量更新/強制 push 等）。
5) すべての作業は「記録（plan / tests / review）」が残る形で進める。

## 2. 使うスキル（/ で実行）
- /issue-bootstrap [title] : 採番、イシューファイル作成、ブランチ作成、Draft PR 作成
- /plan I### : 計画書 + テスト文書 + レビュー文書 作成（承認待ち）
- /implement I### : 承認済み計画に沿って実装 + 自動テスト + PR 更新（ユーザー検証待ち）
- /fix-loop I### : NG/失敗時の原因整理→差分計画→承認→修正→再テスト
- /retro I### : ユーザーテスト OK 後の振り返り（成果・プロセス・技術・スキル規約の改善点確認）
- /close I### : open→closed へ整理、PR 説明整備、クローズ作業

## 3. 権限と二重ガード
- 権限（allow/ask/deny）は .claude/settings.json
- さらに hooks（PreToolUse）で危険操作をブロックする（scripts/claude/hooks/pretooluse_guard.py）
