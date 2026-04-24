# コードレビュー: I051 — e2e/.env.e2e.example を作成してローカル E2E セットアップを簡略化する

## レビュー対象
- `e2e/.env.e2e.example`（新規作成）

## チェックリスト

### セキュリティ
- [ ] `E2E_TEST_PASSWORD=` の値が空（プレースホルダーのみ）で実パスワードが含まれていない
- [ ] pre-commit の Detect secrets フックが検知しないこと

### 内容・フォーマット
- [ ] `E2E_TEST_PASSWORD=` の行が含まれている
- [ ] `BASE_URL` はコメントアウトで含まれており、オプションであることが明示されている
- [ ] コピー手順のコメントが冒頭に記載されている
- [ ] ファイルが `.gitignore` の対象外であること（`e2e/.env.e2e` のみが除外対象）

### ドキュメント整合性
- [ ] `docs/runbooks/common-commands.md` の `cp e2e/.env.e2e.example e2e/.env.e2e` コマンドと整合している

## 備考
- Backend・Frontend・DB の変更なし
- セキュリティ影響なし
