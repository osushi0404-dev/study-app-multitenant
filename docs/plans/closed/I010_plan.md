# 計画書: I010 科目管理画面の独立

## 基本情報
- **計画書ID**: I010_plan
- **関連イシュー**: #I010
- **作成根拠資料**: docs/issues/open/010.md
- **実装後評価**: （未作成）
- **作成日**: 2026-03-27

---

## 1. 背景/目的

I006 で実装した科目管理機能（科目一覧表示・科目追加）が、問題管理画面内のアコーディオン UI として配置されており UX が悪い。本イシューでは**機能を変えずに**、科目管理を独立した画面として切り出し、左サイドメニューから直接アクセスできるようにする。

---

## 2. 受け入れ条件

- [ ] 左サイドメニューに「科目管理」が表示される（`role='admin'` のみ）
- [ ] 「科目管理」リンクから `/subject-management` 画面に遷移できる
- [ ] 科目管理画面に組織ごとの科目一覧が表示される
- [ ] 科目管理画面から科目を追加できる（既存 API を使用）
- [ ] 科目追加後、一覧が即時更新される
- [ ] 問題管理画面からアコーディオン UI（科目管理）が削除されている
- [ ] 問題管理画面の既存機能（フィルタ、問題追加フォームの科目選択など）に影響がない

---

## 3. 影響範囲

| 層 | 影響 |
|----|------|
| Backend | なし（既存 API をそのまま使用） |
| Frontend | Layout.tsx / App.tsx / 新規 SubjectManagement.tsx / QuizManagement.tsx |
| DB | なし |
| Config/Infra | なし |

---

## 4. 調査結果

### 現状

#### Layout.tsx (`frontend/src/components/Layout.tsx`)
- `menuItems` 配列でサイドメニューを定義（行 69-78）
- スタッフ限定項目は `user?.is_staff` で条件分岐
- `isOrgAdmin` の判定は Layout 内には存在しない（QuizManagement.tsx で定義）

#### App.tsx (`frontend/src/App.tsx`)
- Protected Routes は `<Layout />` の子として定義（行 86-99）
- ページコンポーネントは lazy import ではなく直接 import

#### QuizManagement.tsx (`frontend/src/pages/QuizManagement.tsx`)
- `isOrgAdmin = user?.role === 'admin'`（行 99）
- 科目管理関連の state: `subjects`、`newSubjectName`、`addingSubject`
- 科目管理関連の関数: `fetchSubjects`（行 196-206）、`handleAddSubject`（行 327-343）
- アコーディオン UI（行 488-526）
- `subjects` は科目管理 UI 以外にも使用:
  - フィルタ用 Select（行 461）
  - 問題追加フォームの科目選択（行 709）
  - AIQuestionGenerator への props 渡し（行 932）

削除できる要素（アコーディオン削除時）:
- `newSubjectName` state
- `addingSubject` state
- `handleAddSubject` 関数
- Accordion / AccordionSummary / AccordionDetails の MUI import
- ExpandMoreIcon の import
- List / ListItem / ListItemText の import（アコーディオン内でのみ使用）

残す要素（他で使用中）:
- `subjects` state
- `fetchSubjects` 関数

---

## 5. 変更点一覧

### 5-1. `frontend/src/components/Layout.tsx`

**修正方針**: org admin（`user?.role === 'admin'`）にのみ表示される「科目管理」メニュー項目を追加する。

変更箇所:
- `School` アイコンを `@mui/icons-material` からインポートに追加
- `isOrgAdmin` 変数を `Layout` コンポーネント内で定義（`const isOrgAdmin = user?.role === 'admin'`）
- `menuItems` に条件付きで「科目管理」を追加

```typescript
// import 追加
import {
  // 既存 ...
  School,
} from '@mui/icons-material';

// コンポーネント内
const isOrgAdmin = user?.role === 'admin';

const menuItems = [
  { text: 'ダッシュボード', icon: <Dashboard />, path: '/dashboard' },
  { text: '問題管理', icon: <Quiz />, path: '/quiz-management' },
  { text: '学習統計', icon: <BarChart />, path: '/statistics' },
  { text: '設定', icon: <Settings />, path: '/settings' },
  ...(isOrgAdmin ? [
    { text: '科目管理', icon: <School />, path: '/subject-management' },
  ] : []),
  ...(user?.is_staff ? [
    { text: '監視', icon: <Speed />, path: '/monitoring' },
    { text: 'ユーザー管理', icon: <People />, path: '/admin/users' },
  ] : []),
];
```

### 5-2. `frontend/src/App.tsx`

**修正方針**: `SubjectManagement` ページを import し、`/subject-management` ルートを追加する。

変更箇所:
- `import SubjectManagement from './pages/SubjectManagement';` を追加
- Protected Routes 内に `<Route path="subject-management" element={<SubjectManagement />} />` を追加

```typescript
// import 追加（既存の import 群と同じ場所）
import SubjectManagement from './pages/SubjectManagement';

// Routes 内（monitoring の後など）
<Route path="subject-management" element={<SubjectManagement />} />
```

### 5-3. `frontend/src/pages/SubjectManagement.tsx`（新規作成）

**修正方針**: QuizManagement のアコーディオン UI を独立ページとして移植する。org admin でない場合はアクセス拒否メッセージを表示。

```typescript
import React, { useState, useEffect } from 'react';
import {
  Box, Typography, List, ListItem, ListItemText,
  TextField, Button, CircularProgress, Alert, Paper,
} from '@mui/material';
import { Add } from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import { Subject } from '../services/types';
import apiClient from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const SubjectManagement: React.FC = () => {
  const { user } = useAuth();
  const isOrgAdmin = user?.role === 'admin';

  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [newSubjectName, setNewSubjectName] = useState('');
  const [loading, setLoading] = useState(true);
  const [addingSubject, setAddingSubject] = useState(false);

  useEffect(() => {
    if (isOrgAdmin) fetchSubjects();
  }, [isOrgAdmin]);

  const fetchSubjects = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/api/organizations/subjects/');
      const data = Array.isArray(response.data) ? response.data : response.data.results || [];
      setSubjects(data);
    } catch {
      toast.error('科目一覧の取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const handleAddSubject = async () => {
    const name = newSubjectName.trim();
    if (!name) { toast.error('科目名を入力してください'); return; }
    setAddingSubject(true);
    try {
      await apiClient.post('/api/subjects/', { name });
      toast.success('科目を追加しました');
      setNewSubjectName('');
      await fetchSubjects();
    } catch (e: any) {
      toast.error(e?.response?.data?.error || '科目追加に失敗しました');
    } finally {
      setAddingSubject(false);
    }
  };

  if (!isOrgAdmin) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">このページには組織管理者のみアクセスできます。</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        科目管理 — {user?.organization_name ?? ''}
      </Typography>
      <Paper sx={{ p: 2, maxWidth: 480 }}>
        {loading ? (
          <CircularProgress size={24} />
        ) : (
          <List dense>
            {subjects.map(s => (
              <ListItem key={s.id}>
                <ListItemText primary={s.name} />
              </ListItem>
            ))}
          </List>
        )}
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
      </Paper>
    </Box>
  );
};

export default SubjectManagement;
```

### 5-4. `frontend/src/pages/QuizManagement.tsx`

**修正方針**: 科目管理アコーディオン UI（行 488-526）と、それ専用の state・関数・import を削除する。`subjects`・`fetchSubjects` は他で使用中なので残す。

削除する要素:

**imports（行 40-45 の MUI import）**:
- `Accordion`
- `AccordionSummary`
- `AccordionDetails`
- `List`
- `ListItem`
- `ListItemText`
- `ExpandMoreIcon`（行 47）

**state（行 103-104）**:
```typescript
// 削除
const [newSubjectName, setNewSubjectName] = useState('');
const [addingSubject, setAddingSubject] = useState(false);
```

**関数（行 327-343）**:
```typescript
// 削除: handleAddSubject 関数全体
```

**JSX（行 488-526）**:
```typescript
// 削除: {/* Subject Management Accordion (org admin only) */} ブロック全体
```

---

## 6. 実装手順

1. `SubjectManagement.tsx` を新規作成
2. `Layout.tsx` を修正（アイコン import + isOrgAdmin + menuItems）
3. `App.tsx` を修正（import + route 追加）
4. `QuizManagement.tsx` を修正（アコーディオン UI 削除、不要な state/関数/import を削除）

---

## 7. テスト計画

- 自動テスト: `docs/tests/open/I010_auto_test.md` 参照
- 手動テスト: `docs/tests/open/I010_manual_test.md` 参照

---

## 8. ロールバック

Frontend のみの変更のため、ロールバックは git revert で対応。
バックエンド・DB への変更はないため、データ影響なし。

---

## 9. Risk & 回避策

| リスク | 回避策 |
|--------|--------|
| QuizManagement の subjects state を誤って削除 | 削除前にフィルタ・フォーム・AIGenerator での利用を確認済み → 残す |
| org admin 以外が `/subject-management` に直接アクセス | ページ内で `isOrgAdmin` チェックし Alert を表示。バックエンド API も `IsOrgAdmin` で保護済み |
| MUI import の削除漏れでビルドエラー | 実装後 `npm run build` でビルド確認 |

---

## 10. 承認ポイント

- [ ] 計画の方針（4 ファイル変更・バックエンド変更なし）に同意
- [ ] `SubjectManagement.tsx` のページ構成（Paper にリスト＋入力フォーム）に同意
- [ ] 科目管理メニューを `設定` の後、スタッフ専用メニューの前に配置することに同意
- [ ] `AdminRoute` を使わず、ページ内で `role === 'admin'` を確認する方式に同意

## 完了情報
- **完了日時**: 2026-03-27
- **対応者**: Claude Code
- **レビュー結果**: OK（ユーザー検証済み）
