# I034 自動テスト: pre-commit hooks の導入（シークレット検出・コード品質チェック）

## 対象
Backend/Frontend のコード変更なし。ユニットテスト・統合テストの追加対象外。

## pre-commit 動作確認コマンド（実施後に実行）

```bash
# 1. pipx による pre-commit・detect-secrets インストール確認
pipx list | grep -E "pre-commit|detect-secrets"
# 期待: 両ツールがリストに表示されること

# 2. フック登録確認
ls -la .git/hooks/pre-commit
# 期待: ファイルが存在すること

# 3. 設定ファイル確認
cat .pre-commit-config.yaml
# 期待: detect-secrets (rev: v1.5.0) / pre-commit-hooks (rev: v4.6.0) が定義されていること

# 4. ベースラインファイル確認（valid JSON かつリポジトリ全体がスキャン対象であること）
cat .secrets.baseline | python3 -m json.tool | head -20
# 期待: valid JSON であること

# 5. 全ファイルチェック実行（pragma: allowlist secret を含むドキュメントも passed になること）
pre-commit run --all-files
# 期待: 全フック passed

# 6. Backend 既存テスト（変更なしの確認）
cd backend && python -m pytest --tb=short -q 2>&1 | tail -5

# 7. Frontend 既存テスト（変更なしの確認）
cd frontend && npm test -- --watchAll=false --passWithNoTests 2>&1 | tail -5
```

## 結果（実施後に記入）
- pipx インストール確認:
- pre-commit run --all-files:
- Backend テスト:
- Frontend テスト:
