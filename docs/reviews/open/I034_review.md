# I034 レビュー: pre-commit hooks の導入（シークレット検出・コード品質チェック）

## 基本情報
- **レビューID**: I034_review
- **対象計画書**: docs/plans/open/plan_I034.md
- **関連イシュー**: #78
- **作成日**: 2026-04-11

## 変更概要
`pre-commit` フレームワークを導入し、`git commit` 時にシークレット検出（detect-secrets）および基本的なコード品質チェックを自動実行する。

## 変更点
- `.pre-commit-config.yaml` 新規作成（detect-secrets + pre-commit-hooks）
- `.secrets.baseline` 新規生成（既存誤検知を除外）
- `docs/runbooks/pre-commit.md` 新規作成（インストール・運用手順）

## 影響範囲
- Backend/Frontend/DB: なし
- Config/Infra: リポジトリルートの設定ファイル追加、runbook 追加

## テスト結果
- 自動: Backend 25 passed / Frontend 7 passed（2026-04-11）
- 手動: 全 10 項目 OK（2026-04-11）

## 計画との差分
- なし

## ロールバック
- `pre-commit uninstall` → `.pre-commit-config.yaml` / `.secrets.baseline` / `docs/runbooks/pre-commit.md` を git rm してコミット
