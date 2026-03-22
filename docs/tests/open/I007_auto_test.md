# I007 自動テスト: backend/media をリポジトリに含める

実行コマンド:
```bash
# 1. backend/media/ が git 管理下にあることを確認
git ls-files backend/media/ | head -10

# 2. .gitignore に backend/media/ の除外エントリがないことを確認（0件なら OK）
grep -n '^backend/media/$' .gitignore | wc -l

# 3. !backend/media/ の否定エントリが存在することを確認
grep -n '^!backend/media/$' .gitignore

# 4. 画像ファイルへの HTTP アクセス確認（コンテナ起動済みの場合）
curl -o /dev/null -s -w "%{http_code}" http://localhost/media/org/personal/subjects/aws-saa/problem/q02_problem.png
# 期待値: 200

# 5. DB のファイルパスとファイルの存在を照合
docker compose exec db psql -U postgres learning_app -c \
  "SELECT image FROM problems_problem WHERE image IS NOT NULL AND image != '' LIMIT 5;"
# 出力されたパスに対して backend/media/<パス> が存在するか確認
```

結果:
- git ls-files 件数: 6件 ✅
- backend/media/ 除外エントリ数（0 が OK）: 0 ✅
- !backend/media/ エントリ: 18行目に存在 ✅
- HTTP ステータス: 未確認（Docker が WSL2 未連携のため手動テストに委ねる）
- DBパスとファイル一致: 未確認（同上）
