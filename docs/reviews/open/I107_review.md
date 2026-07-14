# I107 レビュー: GitHubイシューのトラック軸ラベル分類（track:app / track:harness）導入

## 基本情報
- **対象計画書**: docs/plans/open/plan_I107.md
- **関連イシュー**: docs/issues/open/I107.md（GitHub Issue: #200 / Draft PR: #202）
- **レビュー目的**: トラック軸ラベル（track:app / track:harness）の新設・起票フロー文書の2軸必須化・オープンイシュー25件のバックフィルが、承認済み分類表・イシューのACどおりに実施されたかを評価する
- **期待する成果**: `gh issue list --label track:*` でトラック別一覧が取得でき、以後の起票で両軸ラベルが必須付与される運用が文書で担保されること

## 変更概要
- （実装後に記入）

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: GitHubラベル定義・オープンイシューのラベル・運用文書2ファイル（.claude/skills/issue-bootstrap/SKILL.md / docs/runbooks/issue-flow.md）

## テスト結果
- 自動: （実装後に記入。AT-01〜07・決定論ゲート G1〜G4）
- 手動: （テスト後に記入。No1〜4 = Claude / No5 = Human）

## 計画との差分
- （実装後に記入）

## ロールバック
- ラベル: `gh label delete "track:app" --yes` / `gh label delete "track:harness" --yes`（付与済みイシューからも自動で外れる）。個別解除は `gh issue edit <番号> --remove-label`。
- 文書: git revert または feature ブランチ破棄。
