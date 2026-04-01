# I017 レビュー文書

## レビュー対象
科目管理画面UX刷新（一覧テーブル化・追加モーダル・詳細ページ）

---

## コードレビューチェックリスト

### Backend
- [x] `SubjectViewSet.list()` の独自実装が削除されている
- [x] 削除後に ModelViewSet デフォルトの list() が正常動作している（全フィールド返却）
- [x] 既存の QuizManagement・統計画面への影響がないこと

### Frontend: SubjectManagement.tsx
- [x] テーブル列が計画書通りに実装されている（科目名・説明・問題数・登録日・操作）
- [x] 科目名がクリッカブルリンクとして実装されている
- [x] 追加モーダルが react-hook-form + yup で実装されている
- [x] バリデーション（科目名必須・100文字以内、説明500文字以内）が動作する
- [x] Edit・Delete ボタンが disabled かつ Tooltip テキストが正しい
- [x] ローディング状態・エラー状態が適切に処理されている
- [x] トースト通知が成功・失敗で適切に表示される（fix-loop で修正済み）

### Frontend: SubjectDetail.tsx
- [x] `/subject-management/:id` ルートで表示される
- [x] 科目名・説明・問題数・登録日・更新日が表示される
- [x] 存在しない ID でアクセスした場合のエラーハンドリングがある
- [x] 編集ボタンが disabled かつ Tooltip テキストが正しい
- [x] 戻るボタンで `/subject-management` に遷移できる

### App.tsx
- [x] `subject-management/:id` ルートが追加されている
- [x] SubjectDetail のインポートが追加されている

### 共通
- [x] TypeScript 型エラーがないこと（`npx tsc --noEmit` 通過）
- [x] 既存の Subject 型定義を流用している（新規型追加なし）
- [x] コーディング規約（react-coding-standards-integrated.md）に準拠している

---

## UX レビューチェックリスト

- [x] テーブルが UserManagement・QuizManagement と一貫したスタイルである
- [x] 空の一覧（科目0件）で適切なメッセージが表示される
- [x] 説明が長い場合にテーブルが崩れない（truncate）
- [x] ローディング中に CircularProgress が表示される

---

## セキュリティチェック

- [x] 管理者以外がアクセスした場合にエラーメッセージが表示される
- [x] `/api/subjects/:id/` へのアクセスが認証必須になっている（既存動作の確認）

---

## 自動テスト結果（2026-04-01）

- Backend: 25 passed ✅
- Frontend: 7 passed ✅

## 自動テスト結果（fix-loop 後 2026-04-01）

- Backend: 25 passed ✅
- Frontend: 7 passed ✅

## 回帰テスト結果

- [ ] MT-06（回帰テスト）: 問題管理画面の科目ドロップダウンが正常に動作する
- [ ] MT-06（回帰テスト）: 統計画面の科目フィルタが正常に動作する
