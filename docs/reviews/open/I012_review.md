# I012 レビュー: クローズ済みイシューファイルの open フォルダ残留対応と根本原因修正

## 変更概要
- `docs/*/open/` に残留していた closed 済みイシューファイルを削除
- `.claude/settings.json` に docs mv/rm 操作の allow パターンを追加
- `.claude/skills/close/SKILL.md` のステップ1を具体的な mv コマンドに書き換え

## 変更点
- `docs/issues/open/` : 006.md, 007.md, 010.md, 011.md を削除
- `docs/plans/open/` : I006_plan.md, I010_plan.md, I011_plan.md を削除
- `docs/tests/open/` : I006/I010/I011 系テストケース 6 ファイルを削除
- `docs/reviews/open/` : I006_review.md, I010_review.md, I011_review.md を削除
- `.claude/settings.json` : allow に mv/rm パターン追加
- `.claude/skills/close/SKILL.md` : ステップ1を具体的 mv コマンドに修正

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/settings.json`
- スキル: `.claude/skills/close/SKILL.md`

## テスト結果
- 自動:（対象なし）
- 手動:（実装後に記入）

## 計画との差分
- なし / あり（理由）

## ロールバック
- git で全変更を復元可能
