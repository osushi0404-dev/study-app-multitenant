# I032 自動テスト: GitHub Branch protection rules 設定手順書の作成と適用

対象が GitHub Settings（GUI 操作）のため、コードの自動テストは不要。
以下のコマンドで手順書ファイルの存在を確認する。

実行コマンド:
```bash
# 手順書ファイルの存在確認（ファイルが存在すれば OK）
ls docs/runbooks/branch-protection-setup.md && echo "OK: 手順書存在" || echo "NG: 手順書なし"
```

結果:
- 手順書存在確認: OK（docs/runbooks/branch-protection-setup.md 存在確認済み）
