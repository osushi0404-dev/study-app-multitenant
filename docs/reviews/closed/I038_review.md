# I038 レビュー: retro スキル改善: 5 Whys 導入・予防処置フロー整備

## 変更概要
`/retro` SKILL.md に 5 Whys ステップを追加し、是正処置と予防処置を別テーブルに分離する。予防処置は `/issue-bootstrap` → `/plan-issue` の正規フローを経由するルールを明記する。

## 変更点
- `.claude/skills/retro/SKILL.md`:
  - ステップ 2.5（5 Whys）を追加
  - 報告フォーマットを是正/予防に分離
  - 予防処置への対応ガイドを追加
  - SKILL.md 変更案の提示・承認ゲートを追加

## 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `.claude/skills/retro/SKILL.md` のみ

## テスト結果
- 自動: Backend 25 passed / Frontend 7 passed（2026-04-10）
- 手動: MT-1〜MT-5 全項目 OK（2026-04-10）

## 計画との差分
- なし

## ロールバック
`git revert` または手動編集で即時対応可能（Markdown のみ）
