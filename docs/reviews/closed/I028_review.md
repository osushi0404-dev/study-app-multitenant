# I028 レビュー: Dependabot 設定と PR テンプレート追加

## 変更概要
`.github/dependabot.yml` と `.github/pull_request_template.md` を新規追加する。

## 変更点
- `.github/dependabot.yml`: pip・npm・github-actions の週次更新設定（target-branch: develop、limit: 5）
- `.github/pull_request_template.md`: PR 作成時のひな形（概要・関連イシュー・変更点・テスト確認・ロールバック手順）
- `.claude/skills/close/SKILL.md`: step 2 に PR テンプレート読み込みの指示を追加

## 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `.github/` 以下に 2 ファイル追加のみ

## テスト結果
- 自動: ✅ Backend 25 passed / Frontend 7 passed / CI 全5ジョブ pass
- 手動: （実施後に記録）

## 計画との差分
- （実施後に記録）

## ロールバック
- `.github/dependabot.yml` を削除する
- `.github/pull_request_template.md` を削除する
