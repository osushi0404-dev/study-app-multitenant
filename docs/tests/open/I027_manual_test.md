# I027 手動テスト: GitHub Actions の Lint / Test 失敗を PR 上に annotation で表示する

## 前提

PR を push して CI が実行された状態で確認する。
意図的に lint 違反を含むコードを push して annotation が表示されることを確認する。

| No | 手順 | 期待結果 | 実結果 | 備考 |
|---:|------|----------|--------|------|
| 1 | feature ブランチに flake8 違反（末尾スペース）を含む Python ファイルを push する | PR の Files changed 上に該当行の annotation が表示される | `./test_annotation_check.py:3:8 W291 trailing whitespace` のアノテーションが API で確認 | OK |
| 2 | feature ブランチに ESLint 違反を含む TypeScript ファイルを push する | PR の Files changed 上に該当行の annotation が表示される | `frontend/src/Login.tsx:50:9` 等のアノテーションが API で確認 | OK |
| 3 | lint 違反を修正して push する | annotation が消え、CI が pass する | 違反ファイル削除後、全ジョブ pass を確認 | OK |
| 4 | 違反がない通常の push を行う | annotation なし、CI pass | 全ジョブ pass、flake8/ESLint エラーアノテーションなしを確認 | OK |

結論: OK
