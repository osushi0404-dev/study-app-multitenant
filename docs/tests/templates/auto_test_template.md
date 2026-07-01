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

## 決定論ゲート（自動実走）
<!--
  I084: `/code-review`（code-review.sh）がこの見出し直後の**単一 ```bash ブロック**を
  1 行 1 コマンドで抽出し、実走して実 exit code を VERDICT に注入する。
  - 許可（実走）: `bash scripts/claude/tests/*.sh` / `grep -q 文言 file`（存在）/
    `! grep -q 文言 file`（不在）/ `python3 -m json.tool file` / `bash -n file` / `python3 -m py_compile file`
  - 1 行 1 コマンド・チェーン（; && || | ` $( > 等）不可。
  - heavy（pytest/Jest/E2E・docker/npm）はここに書かず /test に委譲する。
  - このセクション外の fenced ```bash に許可コマンドを書くと omission-lint が HIGH を出す（宣言漏れ防止）。
  - 決定論ゲートが無いイシューはこのセクションを空（または省略）にしてよい。
-->
```bash
bash scripts/claude/tests/test_xxx.sh
```
