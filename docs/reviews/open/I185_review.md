# I185 レビュー: 開発環境の総点検と改善

## 変更概要
- 段 A: 開発環境の点検報告書 `docs/proposals/I185_dev_env_review.md` を作成し、改善案の採否を決める
- 段 B: 採用した改善 P1〜P5 を実装する（計画変更記録 2）
  - P1 編集直後の構文チェックの終了コードを 2 にする
  - P2 計画のレビューを人の承認の前に済ませる
  - P3 fix-loop の方針選びで、推奨案が 1 つに決まるときは止まらずに進める
  - P4 スキルの `allowed-tools` を外し、制限は `disallowed-tools` にする
  - P5 セッション開始時に状態をフックで渡す
- /close 時: 効果測定イシューの起票と、1 週間後のクラウドの 1 回限りの予約

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/settings.json`（SessionStart フック追加）・`scripts/claude/hooks/`（posttooluse_check.py の修正・sessionstart_context.py の新規）・`.claude/skills/*/SKILL.md`（11 本の frontmatter・plan-issue・fix-loop の手順）・`docs/runbooks/workflow.md`・`scripts/claude/tests/`（新規 3 本）

## テスト結果
- 自動:
- 手動:

## 計画との差分
- なし / あり（理由）

## ロールバック
- 段 A: 報告書のコミットを `git revert`
- 段 B: 改善ごとのコミットを `git revert`
