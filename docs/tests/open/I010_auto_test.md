# 自動テスト: I010 科目管理画面の独立

## 方針

本イシューは Frontend のみの変更（UI 移動・UX 改善）であり、Backend API に変更はない。
既存の API テストは変更不要。
Frontend の自動テストは `frontend/src/pages/__tests__/` に配置する。

---

## 既存テストへの影響確認

実装後に以下を実行して既存テストが壊れていないことを確認:

```bash
cd frontend
npm test -- --watchAll=false
```

---

## 新規自動テスト

### AT-01: SubjectManagement — org admin でマウントするとコンテンツが表示される

**ファイル**: `frontend/src/pages/__tests__/SubjectManagement.test.tsx`

```typescript
// モックパターンは既存の QuizManagement テストに準拠
// - useAuth を mock し role='admin' を返す
// - apiClient.get('/api/organizations/subjects/') を mock
// - 科目一覧と追加フォームが表示されることを assert
```

検証項目:
- 「科目管理」タイトルが表示される
- 科目一覧（モックデータ）が表示される
- 「科目名」入力フィールドと「追加」ボタンが表示される

### AT-02: SubjectManagement — org admin でない場合はアクセス拒否メッセージが表示される

```typescript
// useAuth を mock し role='user' を返す
// 「このページには組織管理者のみアクセスできます。」が表示されることを assert
```

### AT-03: SubjectManagement — 科目追加成功時に一覧が更新される

```typescript
// apiClient.post('/api/subjects/') をモック
// handleAddSubject 呼び出し後に fetchSubjects が再実行されることを assert
// 新しい科目名が一覧に追加されることを assert
```

---

## ビルド確認

TypeScript コンパイルエラーがないことを確認:

```bash
cd frontend
npm run build
```

---

## 実行コマンドまとめ

```bash
# テスト実行
cd frontend && npm test -- --watchAll=false

# ビルド確認
cd frontend && npm run build
```
