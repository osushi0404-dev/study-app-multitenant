# I027 手動テスト: GitHub Actions の Lint / Test 失敗を PR 上に annotation で表示する

## 前提

PR を push して CI が実行された状態で確認する。
意図的に lint 違反を含むコードを push して annotation が表示されることを確認する。

| No | 手順 | 期待結果 | 実結果 | 備考 |
|---:|------|----------|--------|------|
| 1 | feature ブランチに flake8 違反（例: 末尾スペース）を含む Python ファイルを push する | PR の Files changed 上に該当行の annotation（赤いマーカー）が表示される | | |
| 2 | feature ブランチに ESLint 違反を含む TypeScript ファイルを push する | PR の Files changed 上に該当行の annotation が表示される | | |
| 3 | lint 違反を修正して push する | annotation が消え、CI が pass する | | |
| 4 | 違反がない通常の push を行う | annotation なし、CI pass | | |

結論: OK / NG
