# I013 レビュー: GitHub Actions CI パイプライン導入

## 変更概要
- `.github/workflows/ci.yml` を新規作成（5 jobs: backend-lint / backend-test / frontend-typecheck / frontend-lint / frontend-test）
- `backend/requirements-dev.txt` 新規作成（flake8, bandit）
- `backend/setup.cfg` 新規作成（flake8 設定）
- `frontend/package.json` に eslint-plugin-security 追加
- `.claude/settings.json` に gh run / gh pr checks コマンドを追加

## 変更点
- `.github/workflows/ci.yml`: 新規
- `backend/requirements-dev.txt`: 新規
- `backend/setup.cfg`: 新規
- `backend/**/*.py`: lint エラー修正（ロジック変更なし）
- `frontend/package.json`: devDependencies + eslintConfig 更新
- `.claude/settings.json`: allow パターン追加

## 影響範囲
- Backend/Frontend/DB: なし（CI 設定と lint 修正のみ）
- Config/Infra: `.github/workflows/ci.yml` 追加

## テスト結果
- 自動: GitHub Actions 全 5 jobs ✓ パス（run ID: 23637450816）
  - ✓ Backend Lint & Security (flake8 0件, bandit High 0件)
  - ✓ Backend Tests (25 passed)
  - ✓ Frontend Type Check
  - ✓ Frontend Lint & Security
  - ✓ Frontend Tests (7 passed)
- 手動: 全4項目 OK（2026-03-27）
  1. PR に CI バッジ表示 ✓
  2. push で CI 自動起動（約10秒）✓
  3. PR Checks タブで全5ジョブ ✓
  4. `gh pr checks 31` で pass 確認 ✓

## 計画との差分
- 既存テスト修正が追加で必要だった（vitest→Jest 変換、Organization フィクスチャ修正、URL名修正、useQuizDisplayStats NaN バグ修正）
- flake8 エラーが想定より多かったが全修正完了（1432件→0件）

## ロールバック
- `ci.yml` 削除で CI 無効化。その他変更は git revert 可能。

## ユーザー承認
<!-- ⚠️ この欄は Claude が記入禁止。ユーザーが確認後に記入すること。 -->
- **承認日**:
- **手動テスト確認**: 未実施 / 確認済み
