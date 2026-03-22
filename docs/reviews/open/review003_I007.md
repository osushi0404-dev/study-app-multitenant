# I007 レビュー: backend/media をリポジトリに含める

## 基本情報
- **レビューID**: review003_I007
- **レビュー目的**: 実装結果評価
- **対象計画書**: docs/plans/open/plan_I007_mediaディレクトリのリポジトリ追加.md
- **実装完了日**: （未記入）

## 変更概要
`.gitignore` の修正により `backend/media/` を git 管理下に追加し、画像ファイルの参照が `git clone` 後から正常に動作することを確認する。

## 変更点
- `.gitignore`: `!backend/media/` を追加・`backend/media/` エントリを削除
- `backend/media/**`: git 管理下に追加

## 影響範囲
- Backend: `.gitignore` 変更のみ
- Frontend: なし
- DB: なし
- Config/Infra: なし

## テスト結果
- 自動:
- 手動:

## 計画との差分
- （実装後に記入）

## ロールバック
- `.gitignore` を元に戻し `git rm -r --cached backend/media/` で管理外に戻せる
