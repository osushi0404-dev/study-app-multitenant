# 計画書: I006 企業・団体ごとの科目追加機能（アコーディオン UI）

## 基本情報
- **計画書ID**: I006_plan
- **関連イシュー**: #006
- **作成日**: 2026-03-24
- **ステータス**: 承認待ち

---

## 1. 背景/目的

各企業・団体の管理者（`role='admin'` ユーザー）が、問題管理画面から
**自分の所属組織に対して科目を追加**できる機能を実装する。

### 前提整理

| 項目 | 現状 |
|------|------|
| 組織管理者の識別 | `User.role == 'admin'`（`is_staff` は超管理者用） |
| 問題管理画面の権限 | `AdminRoute` なし → 全認証ユーザーがアクセス可能 |
| 科目作成エンドポイント | 既存 `POST /api/subjects/` が `request.user.organization_id` を自動セット |
| UserSerializer | `organization_name` を含んでいない |

---

## 2. 受け入れ条件

- [ ] 問題管理画面（QuizManagement）で `role='admin'` ユーザーのみアコーディオン UI が表示される
- [ ] アコーディオンの見出しに自分の組織名が表示される
- [ ] アコーディオンを展開すると、自組織の科目一覧と「科目追加」フォームが表示される
- [ ] 科目名を入力して保存すると、自組織の科目として登録される
- [ ] 保存後、科目一覧が即時更新される
- [ ] 科目追加時に `problem/` と `explanation/` フォルダが自動作成される
- [ ] `role='user'` ではアコーディオン UI が表示されない
- [ ] `role='user'` が `POST /api/subjects/` を叩いても 403 が返る
- [ ] 既存の科目管理・問題管理の動作に影響がない

---

## 3. 影響範囲

| レイヤー | 変更内容 |
|---------|---------|
| Backend | `accounts/serializers.py` に `organization_name` フィールド追加 |
| Backend | `problems/views.py` の `SubjectViewSet` に role チェックを追加 |
| Backend | `problems/views.py` の `SubjectViewSet.perform_create` にフォルダ作成を統合（transaction.atomic） |
| Frontend | `services/types.ts` の `User` 型に `organization_name` 追加 |
| Frontend | `QuizManagement.tsx` にアコーディオン UI 追加 |
| DB | なし（既存 Subject / Organization モデルをそのまま使用） |
| Config/Infra | なし |

---

## 4. 変更点一覧

### 4-1. Backend: accounts/serializers.py（既存ファイル修正）

**修正方針**: `UserSerializer` に `organization_name` を追加し、
フロントエンドのアコーディオン見出しに組織名を表示できるようにする。

**修正対象**: `class UserSerializer` の `fields`

```python
class UserSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source='organization.name', read_only=True, default=None
    )

    class Meta:
        model = User
        fields = (
            'id', 'email', 'user_id', 'role',
            'is_email_verified', 'is_staff', 'is_superuser',
            'last_login', 'created_at',
            'organization_name',   # 追加
        )
        read_only_fields = (
            'id', 'user_id', 'role', 'is_staff', 'is_superuser',
            'last_login', 'created_at', 'organization_name',
        )
```

---

### 4-2. Backend: problems/views.py（既存ファイル修正）

**修正方針**: `SubjectViewSet` に `IsOrgAdmin` カスタムパーミッションを追加し、
`create` のみを `role='admin'` に制限する。
`update` / `partial_update` / `destroy` のパーミッション制限は**別イシュー対応**（I006 スコープ外）。
`list` / `retrieve` は既存通り全認証ユーザーが使用可能。

#### 追加するパーミッションクラス（ファイル先頭付近に追記）

```python
class IsOrgAdmin(permissions.BasePermission):
    """組織管理者（role='admin'）のみを許可するパーミッション"""
    message = '管理者権限が必要です'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
        )
```

#### SubjectViewSet への追加

```python
class SubjectViewSet(viewsets.ModelViewSet):
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """create は org admin のみ許可（update/destroy は別イシュー）"""
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsOrgAdmin()]
        return [permissions.IsAuthenticated()]

    # ... 以下既存のまま ...
```

---

### 4-3. Backend: problems/views.py（SubjectViewSet.perform_create に統合）

**修正方針**: シグナル方式は廃止。`perform_create` 内で `transaction.atomic()` を使い、
DB への科目保存とメディアフォルダ作成を同一トランザクションに含める。
フォルダ作成が失敗した場合は例外を送出して科目作成もロールバックする。

フォルダパスは既存の `problem_service.py` で使われているパターンに統一する:
```
backend/media/org/{org.slug}/subjects/{subject.slug}/problem/
backend/media/org/{org.slug}/subjects/{subject.slug}/explanation/
```

```python
def perform_create(self, serializer):
    import os
    import uuid as _uuid
    from django.conf import settings
    from django.db import transaction
    from django.utils.text import slugify

    name = serializer.validated_data.get('name', '')
    slug = slugify(name)
    if not slug:
        slug = f"s-{str(_uuid.uuid4())[:8]}"

    org_id = self.request.user.organization_id
    base_slug, counter = slug, 2
    while Subject.objects.filter(slug=slug, organization_id=org_id).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    with transaction.atomic():
        subject = serializer.save(organization_id=org_id, slug=slug)
        subject_service.invalidate_cache(org_id)

        org_slug = subject.organization.slug
        base = os.path.join(
            settings.MEDIA_ROOT, 'org', org_slug, 'subjects', slug
        )
        for folder in ('problem', 'explanation'):
            path = os.path.join(base, folder)
            os.makedirs(path, exist_ok=True)
            gitkeep = os.path.join(path, '.gitkeep')
            if not os.path.exists(gitkeep):
                open(gitkeep, 'w').close()
        # フォルダ作成で例外が発生した場合、transaction.atomic() により科目作成もロールバックされる
```

---

### 4-4. Frontend: services/types.ts（既存ファイル修正）

**修正方針**: `User` インターフェースに `organization_name` を追加する。

```typescript
export interface User {
  id: string;
  email: string;
  user_id: string;
  first_name: string;
  last_name: string;
  role: 'user' | 'admin';
  is_verified: boolean;
  is_staff?: boolean;
  is_superuser?: boolean;
  created_at: string;
  last_login: string;
  organization_name?: string;  // 追加
}
```

---

### 4-5. Frontend: QuizManagement.tsx（既存ファイル修正）

**修正方針**: `role === 'admin'` の場合のみ表示するアコーディオン UI を追加する。
科目一覧は**自組織の科目のみ**表示する（既存の `subjects` state が自組織フィルタ済みであれば再利用、
そうでなければ別途 `GET /api/subjects/` から自組織分のみ取得する）。
科目追加は既存の `POST /api/subjects/` エンドポイントを使用する。

#### 追加 import

```tsx
import { useAuth } from '../contexts/AuthContext';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
```

#### 追加 state・ロジック

```tsx
const { user } = useAuth();
const isOrgAdmin = user?.role === 'admin';

const [newSubjectName, setNewSubjectName] = useState('');
const [addingSubject, setAddingSubject] = useState(false);

const handleAddSubject = async () => {
  const name = newSubjectName.trim();
  if (!name) {
    toast.error('科目名を入力してください');
    return;
  }
  setAddingSubject(true);
  try {
    await apiClient.post('/api/subjects/', { name, slug: '' });
    // ※ slug はバックエンドで自動生成させるため空文字を渡すか、
    //    バックエンド側で slug の自動生成に対応する（4-2 の補足参照）
    toast.success('科目を追加しました');
    setNewSubjectName('');
    await fetchSubjects();  // 既存関数: 科目一覧を再取得
  } catch (e: any) {
    toast.error(e?.response?.data?.error || '科目追加に失敗しました');
  } finally {
    setAddingSubject(false);
  }
};
```

#### JSX（アコーディオンセクション）

既存の問題フィルターセクションの直後に追加:

```tsx
{isOrgAdmin && (
  <Box sx={{ mb: 4 }}>
    <Accordion>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography variant="subtitle1" fontWeight="bold">
          科目管理 — {user?.organization_name ?? ''}
        </Typography>
      </AccordionSummary>
      <AccordionDetails>
        <List dense>
          {subjects.map(s => (
            <ListItem key={s.id}>
              <ListItemText primary={s.name} />
            </ListItem>
          ))}
        </List>
        <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
          <TextField
            size="small"
            label="科目名"
            value={newSubjectName}
            onChange={e => setNewSubjectName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAddSubject()}
          />
          <Button
            variant="contained"
            size="small"
            disabled={addingSubject}
            onClick={handleAddSubject}
            startIcon={<Add />}
          >
            追加
          </Button>
        </Box>
      </AccordionDetails>
    </Accordion>
  </Box>
)}
```

---

### 4-6. Backend: slug 自動生成への対応（SubjectViewSet.perform_create 修正）

**修正方針**: フロントエンドから `slug` を送らなくてもよいよう、
`perform_create` 内でスラッグを自動生成する。

```python
def perform_create(self, serializer):
    from django.utils.text import slugify
    import uuid as _uuid

    name = serializer.validated_data.get('name', '')
    slug = slugify(name)                         # ASCII slugify
    if not slug:
        slug = f"s-{str(_uuid.uuid4())[:8]}"    # 日本語 → UUID フォールバック

    # 同一組織内スラッグ重複回避
    org_id = self.request.user.organization_id
    base_slug, counter = slug, 2
    while Subject.objects.filter(slug=slug, organization_id=org_id).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    serializer.save(organization_id=org_id, slug=slug)
    subject_service.invalidate_cache(org_id)
```

---

## 5. 実装手順

1. **Backend: accounts/serializers.py** — `UserSerializer` に `organization_name` を追記
2. **Backend: problems/views.py** — `IsOrgAdmin` クラス追加 + `SubjectViewSet.get_permissions()` 追加（`create` のみ制限）+ `perform_create` にスラッグ自動生成 + フォルダ作成（`transaction.atomic`）を統合
3. **Frontend: services/types.ts** — `User.organization_name` 追加
4. **Frontend: QuizManagement.tsx** — import 追加・state 追加・アコーディオン JSX 追加（自組織科目のみ表示）
6. バックエンド再起動して動作確認
7. フロントエンド再ビルドして動作確認

---

## 6. テスト計画

### 自動テスト（pytest）

- `GET /api/subjects/` — 認証ユーザーで科目一覧が取得できる
- `POST /api/subjects/` — `role='admin'` で科目が作成される
- `POST /api/subjects/` — `role='user'` で 403 が返る
- `POST /api/subjects/` — slug が自動生成される（英語名）
- `POST /api/subjects/` — slug が自動生成される（日本語名 → UUID形式）
- `POST /api/subjects/` — 同名科目で 400 (unique_together 違反) が返る
- `POST /api/subjects/` — 科目作成時に `problem/` と `explanation/` フォルダが自動作成される
- `POST /api/subjects/` — フォルダ作成失敗時に科目が DB にコミットされない（ロールバック）
- `UserSerializer` — `organization_name` が含まれる

### 手動テスト

- `role='admin'` ユーザーでアコーディオン UI が表示される
- `role='user'` ユーザーでアコーディオン UI が表示されない
- アコーディオン見出しに組織名が表示される
- 科目追加後、アコーディオン内の一覧が即時更新される
- 科目追加後、`backend/media/org/{slug}/subjects/{slug}/problem/` が存在する

---

## 7. ロールバック

追記のみで既存機能への破壊的変更はない。ロールバックする場合は以下を削除:

- `accounts/serializers.py` の `organization_name` フィールド
- `problems/views.py` の `IsOrgAdmin` クラス・`get_permissions()` メソッド・`perform_create` のスラッグ生成＋フォルダ作成ロジック
- `QuizManagement.tsx` の追加コード
- `types.ts` の `organization_name` フィールド

DB マイグレーションは不要。

---

## 8. Risk & 回避策

| リスク | 対策 |
|--------|------|
| スラッグ重複（同一組織内） | while ループで `-2`, `-3` … を付与 |
| 日本語科目名でスラッグが空になる | UUID 短縮形にフォールバック |
| メディアフォルダ作成失敗 | `transaction.atomic()` により科目作成もロールバック。エラーは 500 として返す |
| `organization=None` のユーザーが POST する | `perform_create` で `organization_id=None` になるため Subject 作成は失敗（NOT NULL 制約） |
| `UserSerializer` の変更がログイン後の `user` オブジェクトに反映されない | ログイン時にトークン+ユーザー情報を返す `/api/auth/login/` が `UserSerializer` を使用しているため自動反映 |

---

## 9. 承認ポイント

以下を確認の上 OK をお願いします:

- [ ] 管理者の定義を `role='admin'` とする（`is_staff` ではない）
- [ ] 新規エンドポイントを作らず、既存 `POST /api/subjects/` を拡張する方針
- [ ] `create` のみ `IsOrgAdmin` で制限（`update`/`partial_update`/`destroy` は別イシュー）
- [ ] `UserSerializer` に `organization_name` を追加する（ログイン時のレスポンスに含まれるようになる）
- [ ] スラッグ自動生成ロジック（ASCII slugify → UUID フォールバック）
- [ ] フォルダ作成を `perform_create` の `transaction.atomic()` に統合（失敗時は科目もロールバック）
- [ ] アコーディオン内の科目一覧は**自組織の科目のみ**表示する
- [ ] フォルダパスは `org/{org.slug}/subjects/{subject.slug}/problem(explanation)/`（既存コードと統一）
