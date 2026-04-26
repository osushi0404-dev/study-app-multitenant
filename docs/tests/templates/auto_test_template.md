<!--
## 自動テスト品質基準
各テストケースが以下を満たすことを確認してください:
- アサーションに具体的な期待値（status_code の数値・body の具体フィールド等）があるか
- 「正常レスポンスを確認」のような曖昧な記述になっていないか
- 他テナントデータへのアクセス拒否テストが含まれているか（認可変更がある場合）
- テストが実装詳細をトレースするだけでなく、仕様を検証する形になっているか
-->

# I### 自動テスト: <title>

実行コマンド（例）:
```bash
docker compose exec backend python manage.py test
docker compose exec frontend npm test
```

結果:
- backend:
- frontend:
