# I016 レビュー: ファイル命名規則統一

## 変更概要
スキルファイル・runbook 間のファイル命名規則不統一を解消する。

## 変更点
- `.claude/skills/plan-issue/SKILL.md`: 生成物欄の計画書ファイル名を正式形式に修正
- `.claude/skills/implement/SKILL.md`: 計画書読み込みを glob 形式に修正
- `.claude/skills/close/SKILL.md`: 計画書移動パターンを `plan_I###_*` に修正
- `docs/runbooks/issue-flow.md`: テスト・レビュー命名記述を実態に合わせて修正
- `docs/plans/open/` の orphaned ファイル 2 件を削除

## 影響範囲
- Backend/Frontend/DB/Config: なし
- スキルファイル: 3 件
- runbook: 1 件

## テスト結果
- 自動: （実装後記入）
- 手動: （実装後記入）

## 計画との差分
- なし / あり（理由）

## ロールバック
- git revert で対象コミットを戻す
