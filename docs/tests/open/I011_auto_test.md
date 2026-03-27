# 自動テスト: I011 Service Worker・PWA コンポーネントを完全撤去

## 方針

今回の変更はファイル削除と import 除去のみ。新規ロジックはないため、新規自動テストは不要。
既存テストが壊れていないことの確認が主目的。

---

## 既存テストへの影響確認

実装後に以下を実行:

```bash
cd frontend
npm test -- --watchAll=false
```

**実行結果（2026-03-27）**: 既存失敗 2 件（`vitest` 未インストール・axios ESM 問題）。今回の変更前から存在する問題であり、本イシューの変更による新規失敗ではない。

---

## ビルド確認

```bash
cd frontend
npm run build
```

**期待値**: TypeScript エラーなし、ビルド成功
