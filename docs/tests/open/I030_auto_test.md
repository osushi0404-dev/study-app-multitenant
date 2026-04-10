# I030 自動テスト

## 概要

本イシューは設定ファイル追加・runbook 作成のみであり、バックエンド・フロントエンドのコード変更はない。
既存 CI の通過確認と、設定ファイルの形式チェックのみを対象とする。

## 既存テストへの影響

- Backend テスト: 影響なし
- Frontend テスト: 影響なし

## CI チェック項目

- [ ] Backend CI（pytest）pass（既存テストへの影響なしを確認）
- [ ] Frontend CI（npm test）pass（既存テストへの影響なしを確認）

## JSON 形式チェック

`.mcp.json` が有効な JSON であることを確認する：

```bash
python3 -m json.tool .mcp.json > /dev/null && echo "JSON valid"
```

- [ ] JSON バリデーション OK

## PAT 漏洩チェック

コミット内容に PAT 値（`ghp_` で始まる文字列）が含まれていないことを確認する：

```bash
git log -p --all | grep -E "ghp_|github_pat_" && echo "WARNING: PAT found!" || echo "OK: no PAT in git history"
```

- [ ] git 履歴に PAT 値なし

## 環境変数参照形式チェック

`.mcp.json` の env 値が環境変数参照形式（`${...}`）になっていることを確認する：

```bash
grep "ghp_\|github_pat_" .mcp.json && echo "WARNING: hardcoded PAT!" || echo "OK: no hardcoded PAT"
```

- [ ] `.mcp.json` に PAT 値のハードコードなし
