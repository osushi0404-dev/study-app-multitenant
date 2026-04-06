# I027 レビュー: GitHub Actions の Lint / Test 失敗を PR 上に annotation で表示する

## 変更概要
CI の flake8 / ESLint 失敗を GitHub Actions annotation として PR の Files changed 上に表示する。

## 変更点
- `.github/workflows/ci.yml`: flake8 コマンドに `--format` フラグ追加、ESLint コマンドに `-f github` 追加
- `frontend/package.json`: devDependencies に `eslint-formatter-github` 追加
- `frontend/package-lock.json`: 上記に伴う更新

## 影響範囲
- Backend: なし
- Frontend: devDependencies のみ（アプリコード変更なし）
- DB: なし
- Config/Infra: `.github/workflows/ci.yml`

## テスト結果
- 自動: ✅ Backend 25 passed / Frontend 7 passed、全CI pass
- 手動: ✅ flake8・ESLint アノテーション表示確認、違反修正後 CI pass 確認

## 計画との差分
- なし

## ロールバック
- `.github/workflows/ci.yml` を変更前に戻す
- `frontend/package.json` から `eslint-formatter-github` を削除、`npm install` 実行
