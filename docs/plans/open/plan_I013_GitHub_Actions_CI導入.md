# plan_I013_GitHub_Actions_CI導入

## 基本情報
- **計画書ID**: plan_I013_GitHub_Actions_CI導入
- **関連イシュー**: I013
- **作成根拠資料**: 設計検討会話（2026-03-27）— 実装レビューフロー改善議論
- **実装後評価**: （未作成）
- **作成日**: 2026-03-27

---

## 背景/目的

CI/CD が未整備のため、品質ゲートが Claude Code の自己チェックのみに依存している。
GitHub Actions を導入し、PR 作成時に機械的・客観的な品質ゲートを設ける。

将来の `/implement` 細分化（`/code-review` スキル新設）の前提インフラ。

---

## 設計判断（イシューへの明記 / 仮定）

| 項目 | 決定内容 | 根拠 |
|------|---------|------|
| mypy | **Phase 1 対象外** | イシューに含むと記載されていたが、既存コードへの初回適用で大量エラーが出ることを確認・ユーザー承認済み（案B選択） |
| dev ツール配置 | `backend/requirements-dev.txt` を新規作成 | イシューで明記なし → 仮定。requirements.txt は本番依存のみに保つモダンな慣習 |
| flake8 設定 | `backend/setup.cfg` に記載、max-line-length=120 | イシューで明記なし → 仮定。Django コミュニティ標準 |
| bandit 除外対象 | migrations/ と tests/ を除外 | イシューで明記なし → 仮定。生成コード・テストコードはセキュリティスキャン対象外が慣例 |
| GHA postgres | postgres:15-alpine（docker-compose.yml と一致） | docker-compose.yml を確認 |
| Node バージョン | 18（Dockerfile.dev と一致） | Dockerfile.dev を確認 |
| Python バージョン | 3.11（Dockerfile と一致） | backend/Dockerfile を確認 |
| CI トリガー | push + pull_request（develop, main） | イシューで明記 |
| flake8 既存エラー修正 | **本イシュー内で修正**（ロジック変更なし） | CI が即日 fail するのを防ぐため |

---

## 受け入れ条件

- [ ] PR を作成すると GitHub Actions が自動起動する
- [ ] バックエンド lint（flake8）が CI 上で通過する
- [ ] バックエンド セキュリティスキャン（bandit）が CI 上で通過する
- [ ] バックエンド pytest が CI 上で通過する
- [ ] フロントエンド 型チェック（tsc --noEmit）が CI 上で通過する
- [ ] フロントエンド lint（eslint + eslint-plugin-security）が CI 上で通過する
- [ ] フロントエンド jest が CI 上で通過する
- [ ] `gh pr checks <PR番号>` で Claude Code から結果を確認できる

---

## 影響範囲

- Backend: `requirements-dev.txt` 追加、`setup.cfg` 追加、既存コードの lint エラー修正（ロジック変更なし）
- Frontend: `package.json` に `eslint-plugin-security` 追加、`eslintConfig` 更新
- DB: なし
- Config/Infra: `.github/workflows/ci.yml` 追加、`.claude/settings.json` に `gh run` 系コマンドを追加

---

## 変更点一覧

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `.github/workflows/ci.yml` | 新規作成 | CI ワークフロー本体 |
| `backend/requirements-dev.txt` | 新規作成 | flake8, bandit |
| `backend/setup.cfg` | 新規作成 | flake8 設定 |
| `backend/**/*.py` | 修正（lint 修正のみ） | 既存 flake8 エラーの修正 |
| `frontend/package.json` | 修正 | devDependencies に eslint-plugin-security 追加、eslintConfig 更新 |
| `.claude/settings.json` | 修正 | gh run list/view、gh pr checks を allow に追加 |

---

## 実装手順

### Step 1: `.github/workflows/ci.yml` 作成

```yaml
name: CI

on:
  push:
    branches: [develop, main]
  pull_request:
    branches: [develop, main]

jobs:
  backend-lint:
    name: Backend Lint & Security
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
          cache-dependency-path: backend/requirements-dev.txt
      - name: Install dev dependencies
        run: pip install -r backend/requirements-dev.txt
      - name: flake8
        run: flake8 .
        working-directory: backend
      - name: bandit
        run: bandit -r . -x ./\*/migrations/,./\*/tests/ -ll
        working-directory: backend

  backend-test:
    name: Backend Tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_DB: learning_app
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: password
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
          cache-dependency-path: backend/requirements.txt
      - name: Install system dependencies
        run: sudo apt-get install -y libmagic1
      - name: Install Python dependencies
        run: pip install -r requirements.txt
        working-directory: backend
      - name: Run pytest
        run: pytest
        working-directory: backend
        env:
          DB_HOST: localhost
          DB_PORT: '5432'
          DB_NAME: learning_app
          DB_USER: postgres
          DB_PASSWORD: password

  frontend-typecheck:
    name: Frontend Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - name: Install dependencies
        run: npm ci
        working-directory: frontend
      - name: TypeScript check
        run: npx tsc --noEmit
        working-directory: frontend

  frontend-lint:
    name: Frontend Lint & Security
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - name: Install dependencies
        run: npm ci
        working-directory: frontend
      - name: ESLint
        run: npx eslint src/ --ext .ts,.tsx
        working-directory: frontend

  frontend-test:
    name: Frontend Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - name: Install dependencies
        run: npm ci
        working-directory: frontend
      - name: Jest
        run: CI=true npm test
        working-directory: frontend
```

### Step 2: `backend/requirements-dev.txt` 作成

```
flake8==7.0.0
bandit==1.7.9
```

### Step 3: `backend/setup.cfg` 作成（flake8 設定）

```ini
[flake8]
max-line-length = 120
exclude =
    */migrations/*,
    .git,
    __pycache__,
    .venv,
    staticfiles
extend-ignore =
    W503,
    E203
```

### Step 4: 既存 flake8 エラーの修正

```bash
# ローカルで先に確認
pip install flake8
cd backend && flake8 .
```

発見されたエラーをロジック変更なしで修正（未使用 import 削除、行長調整等）。

### Step 5: `frontend/package.json` 更新

devDependencies に追加:
```json
"eslint-plugin-security": "^3.0.0"
```

eslintConfig を更新:
```json
"eslintConfig": {
  "extends": [
    "react-app",
    "react-app/jest",
    "plugin:security/recommended"
  ]
}
```

### Step 6: `.claude/settings.json` 更新

allow リストに追加:
```json
"Bash(gh run list *)",
"Bash(gh run view *)",
"Bash(gh pr checks *)"
```

### Step 7: push して CI 動作確認

```bash
git add .github/ backend/requirements-dev.txt backend/setup.cfg frontend/package.json .claude/settings.json
git commit -m "feat(I013): GitHub Actions CI パイプライン導入"
git push
gh pr checks <PR番号>
```

---

## テスト計画

### 自動テスト
CI ワークフロー自体が成功することが証明。

### 手動テスト
- PR を作成して全 jobs が green になることを GitHub UI で確認
- `gh pr checks <PR番号>` で Claude Code からも確認

---

## ロールバック

- `.github/workflows/ci.yml` を削除すれば CI は完全に無効化
- `frontend/package.json` の変更は git revert 可能
- `backend/requirements-dev.txt`, `setup.cfg` は削除するだけ

---

## Risk & 回避策

| リスク | 確率 | 対策 |
|--------|------|------|
| 既存コードに多数の flake8 エラーがある | 高 | Step 4 で先にローカル確認・修正してから CI を有効化 |
| 既存テストが CI 環境で fail する（Redis 接続等） | 中 | `CELERY_TASK_ALWAYS_EAGER=True` を CI 環境変数に追加して対応。必要なら Redis service も追加 |
| `eslint-plugin-security` が既存コードで警告を出す | 中 | 警告が多い場合は `--max-warnings` を一時的に緩め、別イシューで解消 |
| `npm ci` が package-lock.json と不一致でエラー | 低 | `npm install` → `npm ci` の順で package-lock.json を更新してから commit |
