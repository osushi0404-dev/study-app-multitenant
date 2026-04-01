# I017 自動テスト文書

## テスト対象
科目管理画面UX刷新（一覧テーブル化・追加モーダル・詳細ページ）

---

## Backend テスト

### 対象ファイル
`backend/problems/tests/test_subject_views.py`（既存 or 新規追加）

### AT-BE-01: SubjectViewSet.list() の返却フィールド確認

```python
def test_list_returns_full_fields(self):
    """list() が description・problem_count・created_at・updated_at を返すこと"""
    # setUp でテストデータを事前作成しておくこと（空リストでアサーションをスキップしないよう保証）
    self.client.force_authenticate(user=self.admin_user)
    response = self.client.get('/api/organizations/subjects/')
    self.assertEqual(response.status_code, 200)
    data = response.json()
    self.assertGreater(len(data), 0, "テストデータが存在すること")
    subject = data[0]
    self.assertIn('description', subject)
    self.assertIn('problem_count', subject)
    self.assertIn('created_at', subject)
    self.assertIn('updated_at', subject)
```

### AT-BE-02: SubjectViewSet.retrieve() の返却確認

```python
def test_retrieve_returns_full_fields(self):
    """retrieve() が全フィールドを返すこと"""
    self.client.force_authenticate(user=self.admin_user)
    response = self.client.get(f'/api/subjects/{self.subject.id}/')
    self.assertEqual(response.status_code, 200)
    data = response.json()
    self.assertIn('description', data)
    self.assertIn('problem_count', data)
    self.assertIn('created_at', data)
    self.assertIn('updated_at', data)
```

### AT-BE-03: problem_count の正確性

```python
def test_problem_count_accuracy(self):
    """problem_count が実際の問題数と一致すること"""
    # 問題を2件作成
    Problem.objects.create(subject=self.subject, ...)
    Problem.objects.create(subject=self.subject, ...)

    self.client.force_authenticate(user=self.admin_user)
    response = self.client.get(f'/api/subjects/{self.subject.id}/')
    self.assertEqual(response.json()['problem_count'], 2)
```

---

## Frontend テスト

### 対象ファイル
`frontend/src/pages/__tests__/SubjectManagement.test.tsx`（新規）
`frontend/src/pages/__tests__/SubjectDetail.test.tsx`（新規）

### AT-FE-01: 一覧テーブルのレンダリング

```typescript
it('テーブルのヘッダーが正しく表示される', () => {
  render(<SubjectManagement />);
  expect(screen.getByText('科目名')).toBeInTheDocument();
  expect(screen.getByText('説明')).toBeInTheDocument();
  expect(screen.getByText('問題数')).toBeInTheDocument();
  expect(screen.getByText('登録日')).toBeInTheDocument();
});
```

### AT-FE-02: 追加モーダルのバリデーション

```typescript
it('科目名が空のとき保存ボタンでバリデーションエラーが出る', async () => {
  render(<SubjectManagement />);
  userEvent.click(screen.getByText('科目を追加'));
  userEvent.click(screen.getByText('保存'));
  expect(await screen.findByText('科目名は必須です')).toBeInTheDocument();
});
```

### AT-FE-03: 編集・削除ボタンの disabled 確認

```typescript
it('編集・削除ボタンが disabled である', () => {
  render(<SubjectManagement />);
  // API モックで科目1件を返す
  const editButtons = screen.getAllByLabelText('編集');
  const deleteButtons = screen.getAllByLabelText('削除');
  editButtons.forEach(btn => expect(btn).toBeDisabled());
  deleteButtons.forEach(btn => expect(btn).toBeDisabled());
});
```

### AT-FE-04: 詳細ページの表示確認

```typescript
it('科目の詳細情報が表示される', async () => {
  // API モック: GET /api/subjects/1/ → { id: 1, name: '数学', description: '説明', problem_count: 5 }
  render(<SubjectDetail />);
  expect(await screen.findByText('数学')).toBeInTheDocument();
  expect(screen.getByText('説明')).toBeInTheDocument();
  expect(screen.getByText('5件')).toBeInTheDocument();
});
```

### AT-FE-05: 詳細ページの編集ボタン disabled 確認

```typescript
it('詳細ページの編集ボタンが disabled である', async () => {
  render(<SubjectDetail />);
  const editButton = await screen.findByText('編集');
  expect(editButton.closest('button')).toBeDisabled();
});
```

---

### AT-FE-06: 重複科目名登録時のエラーメッセージ確認（fix-loop 2026-04-01）

```typescript
it('重複科目名登録時に「同名の科目が既に存在します」が表示される', async () => {
  // API モック: POST /api/subjects/ → 400 { name: ['同名の科目が既に存在します'] }
  server.use(
    rest.post('/api/subjects/', (_req, res, ctx) =>
      res(ctx.status(400), ctx.json({ name: ['同名の科目が既に存在します'] }))
    )
  );

  render(<SubjectManagement />);
  userEvent.click(screen.getByText('科目を追加'));
  userEvent.type(screen.getByLabelText('科目名'), '数学');
  userEvent.click(screen.getByText('保存'));

  expect(await screen.findByText('同名の科目が既に存在します')).toBeInTheDocument();
  // グローバルインターセプターの誤ったメッセージが出ないこと
  expect(screen.queryByText('リクエストが無効です')).not.toBeInTheDocument();
  expect(screen.queryByText('予期しないエラーが発生しました')).not.toBeInTheDocument();
});
```

---

## fix-loop 再発防止記録（2026-04-01）

### 何が失敗したか
重複科目名を登録したとき「同名の科目が既に存在します」ではなく「リクエストが無効です」と表示された。

### 根本原因
`api.ts` のグローバルインターセプターが 400 エラーを先に処理し、`data.message` / `data.detail` がない場合にフォールバックメッセージを表示していた。バックエンドが返す DRF 形式のフィールドエラー（`{name: ['同名の科目が既に存在します']}`）はこの条件に該当せず、誤ったメッセージが出ていた。

### 何を変えたか
`api.ts` の `handleApiError` から 400 ケースの toast 処理を削除。4xx バリデーションエラーは業務ロジックであり、呼び出し元コンポーネントの catch で処理する設計に統一した。

### 次回どう防ぐか
- POST/PUT/PATCH を行うコンポーネントは必ず自前の catch でエラーメッセージを処理する
- グローバルインターセプターは「予期しないエラー」（5xx、ネットワークエラー）のみ担当する
- 400 を catch していない箇所はサイレント失敗になるため、新規エンドポイント追加時はコンポーネント側の catch 実装を必須とする

---

## fix-loop 再発防止記録2（2026-04-01）

### 何が失敗したか
重複科目名登録時に「同名の科目が既に存在します」ではなく「科目の追加に失敗しました」と「予期しないエラーが発生しました」の2枚トーストが表示された。

### 根本原因（2点）
1. `api.ts` の `case 400:` 削除後、400 が `default:` にフォールスルーし「予期しないエラーが発生しました」が表示された（switch 前の早期 return が抜けていた）
2. バックエンドの `DRFValidationError({'name': '...'})` が文字列で返るため、フロントエンドの `Array.isArray(data?.name)` が false となりフォールバックが表示された

### 何を変えたか
- `api.ts`: `switch` 前に `if (status === 400) return;` を追加し `default:` へのフォールスルーを防止
- `views.py`: `DRFValidationError({'name': ['...']})` の値を配列形式に修正し DRF 標準慣習に統一

### 次回どう防ぐか
- DRF で `ValidationError` を手動で raise する場合は値を必ず配列（list）で渡す
- グローバルインターセプターで switch から case を削除する際は `default:` へのフォールスルーがないか確認する
- フロントエンドで `data.name` を対症療法的に文字列・配列の両対応にするのではなく、バックエンドの API 形式を DRF 標準に統一することを優先する

---

## 実行コマンド

```bash
# Backend
cd backend && python -m pytest problems/tests/test_subject_views.py -v

# Frontend
cd frontend && npm test -- --watchAll=false --testPathPattern="SubjectManagement|SubjectDetail"
```
