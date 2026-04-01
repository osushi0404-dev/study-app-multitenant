# plan_I017_科目管理画面UX刷新

## 基本情報
- **計画書ID**: plan_I017_科目管理画面UX刷新
- **関連イシュー**: I017
- **作成根拠資料**: docs/issues/open/I017.md
- **実装後評価**: （未作成）
- **作成日**: 2026-04-01

---

## 背景/目的

現在の SubjectManagement.tsx は最小構成（テキスト一覧＋追加のみ）で、今後の CRUD 機能追加を見据えた UX に刷新する。
本イシューでは「一覧テーブル化・追加モーダル・詳細ページ」を実装し、編集・削除ボタンはUI配置のみ行う（機能は別イシュー）。

---

## 受け入れ条件（Acceptance Criteria）

- [ ] 科目一覧がテーブル形式で表示される（科目名・説明・問題数・登録日・操作）
- [ ] 「科目を追加」ボタンからモーダルで科目を追加できる（科目名は必須、説明は任意）
- [ ] 各行に詳細（Info）・編集（Edit）・削除（Delete）ボタンが表示される
- [ ] 編集・削除ボタンは disabled で、ホバー時に「この機能は近日対応予定です」と表示される
- [ ] 詳細ボタン（または科目名クリック）で `/subject-management/:id` へ遷移できる
- [ ] 詳細ページに科目名・説明・問題数・登録日・更新日が表示される
- [ ] 詳細ページに編集ボタンが表示される（disabled + Tooltip）
- [ ] 詳細ページから一覧に戻れる（戻るボタン）

---

## 調査結果

### 既存コードの確認

| 項目 | 現状 | 対応 |
|------|------|------|
| Subject.description | モデル・シリアライザー共に既存フィールド | マイグレーション不要 |
| SubjectSerializer | id, name, description, problem_count, created_at, updated_at を網羅 | そのまま使用 |
| SubjectViewSet.list() | `.values('id', 'name')` のみ返す独自実装 | 削除して ModelViewSet デフォルトに委譲 |
| SubjectViewSet.retrieve() | ModelViewSet デフォルト（SubjectSerializer 使用） | 変更不要 |
| get_queryset() | annotate_count=True で problem_count をアノテート済み | 変更不要 |
| Subject 型定義（types.ts） | description, problem_count, created_at, updated_at を含む | 変更不要 |
| App.tsx routing | subject-management は AdminRoute なし（コンポーネント内で isOrgAdmin チェック） | 同パターンで詳細ページも追加 |

### list() 変更の影響確認

`/api/subjects/` および `/api/organizations/subjects/` は同一 SubjectViewSet が処理する。
現在 `list()` は `id, name` のみ返しているが、QuizManagement.tsx のドロップダウンは `id` と `name` のみ使用しており、追加フィールドが返っても影響なし（フロントエンドで無視される）。

---

## 影響範囲

- **Backend**: `backend/problems/views.py`（SubjectViewSet.list() 削除、fix-loop: ValidationError 配列形式に統一）
- **Frontend**:
  - `frontend/src/pages/SubjectManagement.tsx`（全面刷新）
  - `frontend/src/pages/SubjectDetail.tsx`（新規作成）
  - `frontend/src/App.tsx`（ルート・インポート追加）
  - `frontend/src/services/api.ts`（fix-loop: 400 グローバル toast 削除）
- **DB**: なし
- **Config/Infra**: なし

---

## 変更点一覧

### Backend

#### `backend/problems/views.py`

**変更方針**: `SubjectViewSet.list()` の独自実装（lines 46-50）を削除し、ModelViewSet のデフォルト `list()` に委譲する。
これにより SubjectSerializer が使われ、description・problem_count・created_at・updated_at が返るようになる。

削除対象コード:
```python
def list(self, request, *args, **kwargs):
    # 問題管理画面用：組織の全科目を取得
    queryset = self.get_queryset()
    subjects = list(queryset.values('id', 'name').order_by('name'))
    return Response(subjects)
```

削除後は ModelViewSet デフォルトの `list()` が動作し、`get_queryset()` → `SubjectSerializer(many=True)` の流れで全フィールドを返す。

### Frontend

#### `frontend/src/pages/SubjectManagement.tsx`（全面刷新）

**変更方針**: 既存の List コンポーネントを廃し、UserManagement・QuizManagement と同様のテーブルレイアウトに刷新する。追加モーダルは react-hook-form + yup で実装する。

**コンポーネント構成**:
```
SubjectManagement（ページ）
├── ヘッダー（タイトル + 「科目を追加」ボタン）
├── TableContainer
│   └── Table
│       ├── TableHead（科目名・説明・問題数・登録日・操作）
│       └── TableBody（SubjectRow × n）
│           └── 各行: 科目名（リンク）・説明（truncate）・問題数・登録日・操作ボタン3つ
└── SubjectFormModal（追加モーダル）
```

**追加モーダルのフォームスキーマ（yup）**:
```typescript
const schema = yup.object({
  name: yup.string().required('科目名は必須です').max(100, '100文字以内で入力してください'),
  description: yup.string().max(500, '500文字以内で入力してください'),
});
```

**テーブル列定義**:
| 列 | 内容 | 備考 |
|----|------|------|
| 科目名 | クリックで詳細ページへ（テキストリンク） | |
| 説明 | 最大2行で truncate | overflow: hidden, textOverflow: ellipsis |
| 問題数 | 数値 | problem_count |
| 登録日 | YYYY/MM/DD | created_at |
| 操作 | Info / Edit / Delete ボタン | Edit・Delete は disabled + Tooltip |

**操作ボタン**:
- Info（`<InfoOutlined />`、color="info"、`aria-label="詳細"`）: `/subject-management/{id}` へ navigate
- Edit（`<Edit />`、color="primary"、`aria-label="編集"`）: disabled, Tooltip「この機能は近日対応予定です」
- Delete（`<Delete />`、color="error"、`aria-label="削除"`）: disabled, Tooltip「この機能は近日対応予定です」

**API**: `GET /api/organizations/subjects/`（既存エンドポイント）、`POST /api/subjects/`（既存）

#### `frontend/src/services/api.ts`（fix-loop 修正）

**変更方針**: `handleApiError` の 400 ケースを削除。4xx バリデーションエラーは業務ロジックであり、呼び出し元コンポーネントの catch で処理する。グローバルインターセプターは 5xx・ネットワークエラーのみ担当する。

**修正背景**: 重複科目名登録時、バックエンドが `{name: ['同名の科目が既に存在します']}` を返しても、インターセプターが先に「リクエストが無効です」を表示してしまうバグ（fix-loop 2026-04-01）。

fix-loop2では `case 400:` 削除後に 400 が `default:` にフォールスルーしていたため、`switch` 前に `if (status === 400) return;` を追加した（fix-loop 2026-04-01）。

#### `backend/problems/views.py`（fix-loop 修正）

**変更方針**: `DRFValidationError` のフィールドエラー値を文字列から配列に修正し DRF 標準形式に統一する。

```python
# 修正前
raise DRFValidationError({'name': '同名の科目が既に存在します'})
# 修正後
raise DRFValidationError({'name': ['同名の科目が既に存在します']})
```

**修正背景**: 文字列形式だとフロントエンドの `Array.isArray(data?.name)` が false になりフォールバックメッセージが表示されていた（fix-loop 2026-04-01）。

#### `frontend/src/pages/SubjectDetail.tsx`（新規作成）

**変更方針**: `/subject-management/:id` のページ。`apiClient.get('/api/subjects/:id/')` で詳細を取得し、読み取り専用で表示する。

**レイアウト**:
```
[ ← 科目一覧に戻る ]
──────────────────────────────────
科目名: 数学
説明: 基礎から応用まで...
問題数: 12件
登録日: 2025/10/01
更新日: 2025/12/15
                      [ 編集（disabled + Tooltip） ]
```

具体的には MUI の `Paper` + `Box` を使ったカード形式で表示する。
戻るボタンは `useNavigate()` で `/subject-management` に戻る。

**API**: `GET /api/subjects/:id/`（ModelViewSet デフォルト、SubjectSerializer を使用）

#### `frontend/src/App.tsx`

**変更方針**: `SubjectDetail` のインポートとルート追加。

追加するルート:
```tsx
<Route path="subject-management/:id" element={<SubjectDetail />} />
```

既存の `subject-management` ルートと同じ位置（AdminRoute なし、コンポーネント内 isOrgAdmin チェック）に追加する。

---

## 実装手順

1. **Backend**: `SubjectViewSet.list()` 独自実装を削除
2. **Frontend**: `SubjectDetail.tsx` を新規作成
3. **Frontend**: `SubjectManagement.tsx` を全面刷新
4. **Frontend**: `App.tsx` にルート・インポートを追加
5. **動作確認**: ローカルで一覧・追加・詳細ページを確認
6. **型チェック**: `cd frontend && npx tsc --noEmit`
7. **push**

---

## テスト計画

詳細は `docs/tests/open/I017_auto_test.md`・`docs/tests/open/I017_manual_test.md` を参照。

---

## ロールバック

- フロントエンド変更のみ（バックエンドは list() 実装削除のみ）
- git revert または feature ブランチを develop にマージしないことでロールバック可能
- DB 変更なし

---

## Risk & 回避策

| リスク | 影響 | 回避策 |
|--------|------|--------|
| list() 変更で QuizManagement の科目ドロップダウンが壊れる | 低（既存 Subject 型は追加フィールドを許容、ドロップダウンは id/name のみ使用） | 実装後に QuizManagement で科目ドロップダウンが動作することを確認 |
| `/api/subjects/:id/` が 404 を返す（管理者以外のアクセス等） | 中 | 詳細ページで 404 ハンドリングを実装（エラー表示 + 一覧へ戻るリンク） |

---

## 承認ポイント

以下をすべて確認してから「OK」をお伝えください。

### イシューに明記されている項目
- [x] 一覧テーブル化（科目名・説明・問題数・登録日・操作）
- [x] 追加モーダル（科目名必須・説明任意）
- [x] 詳細ページ（/subject-management/:id）
- [x] 編集・削除ボタンは UI のみ（disabled）

### 仮定で決めた項目（確認済み）
- [x] Tooltip テキスト「この機能は近日対応予定です」→ ユーザー確認済み
- [x] 詳細ページへの遷移方法: Info ボタン OR 科目名クリック → 双方対応
- [x] `SubjectViewSet.list()` 独自実装を削除して ModelViewSet デフォルトに委譲する

### その他の設計判断（仮定）
- [ ] **説明列のカラム幅制限**: 2行 + ellipsis で truncate（長い説明文でもテーブルが崩れない）
- [ ] **詳細ページの編集ボタン位置**: カード右下（Paper 内の右寄せ）
- [ ] **科目名の必須チェック上限**: 100文字（Subject モデルの max_length に合わせる）
- [ ] **説明の文字数上限**: 500文字（モデルは TextField で上限なしだが UX で制限）
