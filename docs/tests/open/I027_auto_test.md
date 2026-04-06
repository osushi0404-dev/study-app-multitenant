# I027 自動テスト: GitHub Actions の Lint / Test 失敗を PR 上に annotation で表示する

## 実行コマンド

```bash
# Frontend テスト（ローカル）
cd frontend && npm test -- --watchAll=false --passWithNoTests

# flake8 ローカル確認（annotation 形式で出力されるか）
cd backend && flake8 . --format='::error file=%(path)s,line=%(row)d,col=%(col)d::%(code)s %(text)s'

# ESLint ローカル確認（formatter インストール後）
cd frontend && npx eslint src/ --ext .ts,.tsx -f github-actions
```

## CI 確認項目

- [ ] `backend-lint` ジョブが pass する
- [ ] `frontend-lint` ジョブが pass する
- [ ] CI ログに annotation 形式の出力が含まれる（`::error file=...` の形式）

## 結果

- backend-lint:
- frontend-lint:
- frontend テスト:
