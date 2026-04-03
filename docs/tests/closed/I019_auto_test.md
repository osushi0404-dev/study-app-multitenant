# I019 自動テスト計画

## 対象
`react-hooks/exhaustive-deps` ルール有効化および依存配列修正

---

## 自動テスト項目

### AT-01: Frontend Lint が通過すること

**コマンド（CI 環境）:**
```bash
cd frontend && npx eslint src/ --ext .ts,.tsx
```

**期待結果:**
- exit code 0
- `react-hooks/exhaustive-deps` に関するエラーが 0 件（`error` レベル設定）

**確認方法:**
- GitHub Actions の `frontend-lint` ジョブが green になること

---

### AT-02: 既存フロントエンドテストが通過すること

**コマンド:**
```bash
cd frontend && npm test -- --watchAll=false --passWithNoTests
```

**期待結果:**
- テスト件数・合否が実装前と同一（機能変更なし）

---

### AT-03: TypeScript 型チェックが通過すること

**コマンド:**
```bash
cd frontend && npx tsc --noEmit
```

**期待結果:**
- exit code 0（型エラーなし）
- `useCallback` の型推論が正しく機能していること

---

## ベースライン（実装前に計測）

| チェック | 実施前 | 実施後 |
|---------|--------|--------|
| eslint exit code | 0（warn のため） | 0 |
| eslint exhaustive-deps エラー件数 | 0（warn レベル、CI 通過） | 0（error レベルでも 0） |
| フロントエンドテスト pass/fail | 7 passed | 7 passed（変化なし） |
| tsc --noEmit exit code | 0 | 0 |

## 実施結果（2026-04-03）

| AT | 結果 | 備考 |
|----|------|------|
| AT-01 Frontend Lint | ✅ PASS | CI frontend-lint green、exhaustive-deps エラー 0 件 |
| AT-02 Frontend テスト | ✅ PASS | 7 passed, 0 failed |
| AT-03 TypeScript 型チェック | ✅ PASS | tsc --noEmit exit 0 |
| Backend テスト | ✅ PASS | 25 passed, 3 warnings（既存） |
