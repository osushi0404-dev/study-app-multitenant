# I030 自動テスト

## 概要

本イシューは設定ファイル追加・runbook 作成のみであり、バックエンド・フロントエンドのコード変更はない。
そのため自動テストは対象外。

## 既存テストへの影響

- Backend テスト: 影響なし
- Frontend テスト: 影響なし

## CI チェック項目

- [ ] Backend CI（pytest）pass
- [ ] Frontend CI（npm test）pass
- [ ] lint エラーなし（既存テストの通過確認のみ）

## JSON 設定ファイル形式チェック（手動）

```bash
python3 -m json.tool .claude/settings.json > /dev/null && echo "JSON valid"
```

- `settings.json` が有効な JSON であることを確認
- [ ] JSON バリデーション OK
