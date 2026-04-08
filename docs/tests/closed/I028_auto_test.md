# I028 自動テスト: Dependabot 設定と PR テンプレート追加

## 実行コマンド

```bash
# CI 確認（push 後に GitHub Actions で確認）
# ローカルでの YAML 構文チェック（python-yaml が使える場合）
python3 -c "import yaml; yaml.safe_load(open('.github/dependabot.yml'))" && echo "OK"
```

## CI 確認項目

- [ ] `backend-lint` ジョブが pass する
- [ ] `backend-test` ジョブが pass する
- [ ] `frontend-typecheck` ジョブが pass する
- [ ] `frontend-lint` ジョブが pass する
- [ ] `frontend-test` ジョブが pass する

## 結果

- Backend: ✅ 25 passed, 3 warnings（DeprecationWarning のみ、既存の警告）
- Frontend: ✅ 7 passed, 2 suites
- CI（GitHub Actions）: ✅ 全5ジョブ pass
