# I013 手動テスト計画: GitHub Actions CI パイプライン導入

## 手動確認項目

| # | 確認内容 | 操作手順 | 期待結果 | 結果(OK/NG) |
|---|---------|---------|---------|------------|
| 1 | CI が自動起動する | PR #31 に push する | GitHub Actions タブに実行が表示される | |
| 2 | 全 jobs が green | GitHub → PR #31 → Checks タブを確認 | 5 jobs すべて ✓ | |
| 3 | Claude Code から確認できる | `gh pr checks 31` を実行 | 各 job の pass/fail が表示される | |
| 4 | PR の merge ブロック機能 | （任意）意図的に flake8 エラーを入れて push | CI が fail し merge ブロックされることを確認 | |
