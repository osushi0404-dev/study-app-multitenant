# I022 自動テスト: onboarding ドキュメント追加

ドキュメントのみの変更のため、自動テストの追加はなし。
既存テストが壊れていないことのみ確認する。

実行コマンド:
```bash
# Backend
docker compose exec backend python -m pytest --tb=short -q

# Frontend
docker compose exec frontend npm test -- --watchAll=false --passWithNoTests
```

結果:
- backend: 25 passed ✅
- frontend: 7 passed ✅
