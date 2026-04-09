# I037 レビュー: issue-bootstrap 軽量化と plan-issue へのブランチ管理移行

## 変更概要
`/issue-bootstrap` の責務を「採番・イシューファイル作成・GitHub Issue 作成」に絞り、ブランチ作成・コミット・プッシュ・Draft PR 作成を `/plan-issue` へ移行する。

## 変更点
- `.claude/skills/issue-bootstrap/SKILL.md`: ブランチ作成・コミット・プッシュ・Draft PR ステップを削除、GitHub Issue 番号のイシューファイルへの記録を追加
- `.claude/skills/plan-issue/SKILL.md`: ブランチ作成・コミット・プッシュ・Draft PR ステップを追加
- `docs/runbooks/workflow.md`: スキル説明を新しい責務に合わせて更新
- `docs/runbooks/issue-flow.md`: 該当ステップを更新

## 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: スキル定義ファイル（Markdown）と Runbook のみ

## テスト結果
- 自動: pytest 25 passed / Jest 7 passed（2026-04-09）
- 手動: MT-7 OK・MT-8 OK（2026-04-09）。MT-1〜6 は develop マージ後・I038 着手時に確認予定

## 計画との差分
- なし

## ロールバック
git revert または手動編集で即時対応可能（Markdown ファイルのみ）
