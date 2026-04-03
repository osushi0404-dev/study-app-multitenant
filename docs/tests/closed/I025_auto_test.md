# I025 自動テスト計画

## 対象
`@typescript-eslint/no-unused-vars` / `no-redeclare` 警告の解消

---

## 自動テスト項目

### AT-01: ESLint 警告が 0 件になること

**コマンド:**
```bash
docker-compose exec frontend npx eslint src --format=compact 2>&1 | grep "no-unused-vars\|no-redeclare"
```

**期待結果:**
- 出力なし（0 件）

---

### AT-02: TypeScript 型チェックが通過すること

**コマンド:**
```bash
docker-compose exec frontend npx tsc --noEmit
```

**期待結果:**
- exit 0（型エラーなし）

---

### AT-03: 既存フロントエンドテストが通過すること

**コマンド:**
```bash
docker-compose exec frontend npm test -- --watchAll=false --passWithNoTests
```

**期待結果:**
- 7 passed, 0 failed（変化なし）

---

## ベースライン

| チェック | 実施前 | 実施後 |
|---------|--------|--------|
| no-unused-vars 件数 | 38 件 | 0 件 |
| no-redeclare 件数 | 1 件 | 0 件 |
| tsc --noEmit exit code | 0 | 0 |
| Jest pass/fail | 7 passed | 7 passed |

## 実施結果（2026-04-03）

| AT | 結果 | 備考 |
|----|------|------|
| AT-01 ESLint no-unused-vars/no-redeclare | ✅ PASS | 0 件、CI Frontend Lint green |
| AT-02 TypeScript 型チェック | ✅ PASS | tsc --noEmit exit 0、CI Frontend Type Check green |
| AT-03 Frontend Jest | ✅ PASS | 7 passed, 0 failed |
| Backend pytest | ✅ PASS | 25 passed, 3 warnings（既存） |
