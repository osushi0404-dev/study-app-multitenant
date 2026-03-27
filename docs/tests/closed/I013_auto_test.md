# I013 自動テスト計画: GitHub Actions CI パイプライン導入

## テスト方針
CI ワークフロー自体が「自動テスト」として機能する。
各 job が green になることをもって自動テスト通過とみなす。

## テスト対象 jobs

| job 名 | 検証内容 | 通過条件 |
|--------|---------|---------|
| backend-lint | flake8 / bandit | exit code 0 |
| backend-test | pytest | 全テスト pass |
| frontend-typecheck | tsc --noEmit | 型エラーなし |
| frontend-lint | eslint | エラーなし |
| frontend-test | jest | 全テスト pass |

## 実行方法

```bash
# PR 作成後に自動起動、または手動確認
gh pr checks <PR番号>
gh run list
gh run view <run-id>
```

## 期待する出力

```
✓ Backend Lint & Security
✓ Backend Tests
✓ Frontend Type Check
✓ Frontend Lint & Security
✓ Frontend Tests
```
