# React フロントエンド コーディング規約

> Cursor/Claude Code を使用した React アプリケーション開発のための標準コーディング規約

## 目次
1. [プロジェクト構成](#1-プロジェクト構成)
2. [TypeScript/型定義](#2-typescript型定義)
3. [コンポーネント設計](#3-コンポーネント設計)
4. [状態管理](#4-状態管理)
5. [スタイリング](#5-スタイリング)
6. [命名規則](#6-命名規則)
7. [インポート/エクスポート](#7-インポートエクスポート)
8. [エラーハンドリング](#8-エラーハンドリング)
9. [パフォーマンス最適化](#9-パフォーマンス最適化)
10. [テスト](#10-テスト)
11. [AI支援開発のベストプラクティス](#11-ai支援開発のベストプラクティス)

---

## 1. プロジェクト構成

### ディレクトリ構造

```
src/
├── components/       # 再利用可能なUIコンポーネント
│   ├── common/      # 汎用コンポーネント
│   └── features/    # 機能別コンポーネント
├── contexts/        # React Context
├── hooks/           # カスタムフック
├── pages/           # ページコンポーネント
├── services/        # API通信層
├── types/           # 型定義ファイル
├── utils/           # ユーティリティ関数
├── constants/       # 定数定義
└── styles/          # グローバルスタイル
```

### ファイル命名規則

- **コンポーネント**: PascalCase (例: `UserProfile.tsx`)
- **フック**: camelCase で use プレフィックス (例: `useAuth.ts`)
- **ユーティリティ**: camelCase (例: `formatDate.ts`)
- **型定義**: camelCase または PascalCase (例: `types.ts`, `UserTypes.ts`)
- **定数**: UPPER_SNAKE_CASE をエクスポート (例: `API_ENDPOINTS.ts`)

---

## 2. TypeScript/型定義

### 2.1 型定義の一元管理

```typescript
// ❌ 悪い例: 各ファイルで同じ型を再定義
// components/UserList.tsx
interface User {
  id: string;
  name: string;
}

// pages/UserDetail.tsx
interface User {
  id: string;
  name: string;
}

// ✅ 良い例: 共通の型定義ファイルから import
// types/user.ts
export interface User {
  id: string;
  name: string;
  email: string;
  createdAt: string;
}

// components/UserList.tsx
import { User } from '../types/user';
```

### 2.2 型定義の原則

```typescript
// ✅ 良い例: 明示的な型定義
interface Props {
  userId: string;
  onUpdate: (user: User) => void;
  isLoading?: boolean;
}

const UserProfile: React.FC<Props> = ({ userId, onUpdate, isLoading = false }) => {
  // ...
};

// ❌ 悪い例: any 型の使用
const handleData = (data: any) => {  // any を避ける
  // ...
};
```

### 2.3 ジェネリック型の活用

```typescript
// API レスポンスの型定義
interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

// ページネーションの型定義
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}
```

---

## 3. コンポーネント設計

### 3.1 関数コンポーネントの使用

```typescript
// ✅ 推奨: 関数コンポーネント + TypeScript
interface ButtonProps {
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  label,
  onClick,
  variant = 'primary',
  disabled = false
}) => {
  return (
    <button
      className={`btn btn-${variant}`}
      onClick={onClick}
      disabled={disabled}
    >
      {label}
    </button>
  );
};
```

### 3.2 コンポーネントの責務分離

```typescript
// ✅ 良い例: 単一責任の原則
// Container Component (ロジック担当)
const UserListContainer: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchUsers();
  }, []);

  return <UserListView users={users} loading={loading} />;
};

// Presentational Component (表示担当)
const UserListView: React.FC<{ users: User[]; loading: boolean }> = ({
  users,
  loading
}) => {
  if (loading) return <Spinner />;
  return (
    <ul>
      {users.map(user => (
        <UserItem key={user.id} user={user} />
      ))}
    </ul>
  );
};
```

### 3.3 Props の分解代入

```typescript
// ✅ 推奨: 引数で分解代入
const UserCard: React.FC<UserCardProps> = ({ name, email, avatar }) => {
  // ...
};

// ❌ 非推奨: props をそのまま使用
const UserCard: React.FC<UserCardProps> = (props) => {
  return <div>{props.name}</div>;
};
```

---

## 4. 状態管理

### 4.1 状態の適切な配置

```typescript
// ローカル状態: コンポーネント内でのみ使用
const [isOpen, setIsOpen] = useState(false);

// Context: 複数のコンポーネントで共有
const ThemeContext = createContext<ThemeContextType>(defaultTheme);

// グローバル状態: アプリ全体で使用（Redux, Zustand など）
```

### 4.2 カスタムフックの活用

```typescript
// hooks/useApi.ts
export const useApi = <T>(url: string) => {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(url);
      const data = await response.json();
      setData(data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [url]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
};
```

---

## 5. スタイリング

### 5.1 CSS-in-JS vs CSS Modules

```typescript
// CSS Modules の使用
import styles from './Button.module.css';

const Button: React.FC = () => (
  <button className={styles.button}>Click me</button>
);

// Material-UI/Emotion の使用
import { styled } from '@mui/material/styles';

const StyledButton = styled('button')(({ theme }) => ({
  padding: theme.spacing(1, 2),
  backgroundColor: theme.palette.primary.main,
}));
```

### 5.2 条件付きスタイリング

```typescript
// ✅ 良い例: clsx または classnames ライブラリを使用
import clsx from 'clsx';

<div className={clsx(
  'base-class',
  isActive && 'active',
  isDisabled && 'disabled'
)} />

// ❌ 悪い例: 複雑な三項演算子
<div className={`base ${isActive ? 'active' : ''} ${isDisabled ? 'disabled' : ''}`} />
```

---

## 6. 命名規則

### 6.1 変数・関数名

```typescript
// ✅ 良い例
const getUserById = (id: string) => { /* ... */ };
const isUserActive = true;
const handleButtonClick = () => { /* ... */ };

// ❌ 悪い例
const getData = () => { /* ... */ };  // 曖昧
const flag = true;  // 意味不明
const click = () => { /* ... */ };  // 動詞のみ
```

### 6.2 イベントハンドラー

```typescript
// ✅ 推奨: handle + 名詞 + 動詞
const handleUserDelete = () => { /* ... */ };
const handleFormSubmit = () => { /* ... */ };
const handleInputChange = () => { /* ... */ };

// Props として渡す場合: on + 名詞 + 動詞
interface Props {
  onUserDelete: () => void;
  onFormSubmit: (data: FormData) => void;
}
```

---

## 7. インポート/エクスポート

### 7.1 インポートの順序

```typescript
// 1. React 関連
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

// 2. 外部ライブラリ
import axios from 'axios';
import { format } from 'date-fns';

// 3. 内部モジュール（絶対パス）
import { UserService } from '@/services/UserService';
import { useAuth } from '@/hooks/useAuth';

// 4. 内部モジュール（相対パス）
import { Button } from '../components/Button';
import { formatDate } from '../utils/date';

// 5. スタイル
import styles from './Component.module.css';
```

### 7.2 バレルエクスポート

```typescript
// components/index.ts
export { Button } from './Button';
export { Input } from './Input';
export { Modal } from './Modal';

// 使用側
import { Button, Input, Modal } from '../components';
```

---

## 8. エラーハンドリング

### 8.1 Error Boundary の使用

```typescript
class ErrorBoundary extends React.Component<Props, State> {
  static getDerivedStateFromError(error: Error) {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback />;
    }
    return this.props.children;
  }
}
```

### 8.2 非同期処理のエラーハンドリング

```typescript
// ✅ 良い例: try-catch と適切なエラー処理
const fetchUser = async (id: string) => {
  try {
    setLoading(true);
    const user = await userService.getById(id);
    setUser(user);
  } catch (error) {
    console.error('Failed to fetch user:', error);
    setError(error as Error);
    // ユーザーへの通知
    toast.error('ユーザー情報の取得に失敗しました');
  } finally {
    setLoading(false);
  }
};
```

---

## 9. パフォーマンス最適化

### 9.1 メモ化の適切な使用

```typescript
// ✅ 良い例: 重い計算処理のメモ化
const expensiveValue = useMemo(() => {
  return heavyComputation(data);
}, [data]);

// ✅ 良い例: 関数のメモ化
const handleClick = useCallback(() => {
  doSomething(id);
}, [id]);

// ❌ 悪い例: 単純な値のメモ化（過度な最適化）
const simpleValue = useMemo(() => x + 1, [x]);
```

### 9.2 遅延ロード

```typescript
// コンポーネントの遅延ロード
const LazyComponent = lazy(() => import('./HeavyComponent'));

// Suspense と組み合わせて使用
<Suspense fallback={<Loading />}>
  <LazyComponent />
</Suspense>
```

---

## 10. テスト

### 10.1 テストファイルの配置

```
src/
├── components/
│   ├── Button/
│   │   ├── Button.tsx
│   │   ├── Button.test.tsx
│   │   └── Button.module.css
```

### 10.2 テストの原則

```typescript
// ✅ 良い例: ユーザー視点のテスト
describe('LoginForm', () => {
  it('should display error message when login fails', async () => {
    render(<LoginForm />);

    const emailInput = screen.getByLabelText('Email');
    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: 'Login' });

    await userEvent.type(emailInput, 'invalid@email.com');
    await userEvent.type(passwordInput, 'wrongpassword');
    await userEvent.click(submitButton);

    expect(screen.getByText('ログインに失敗しました')).toBeInTheDocument();
  });
});
```

---

## 11. AI支援開発のベストプラクティス

### 11.1 コメントとドキュメント

```typescript
/**
 * ユーザー一覧を取得するカスタムフック
 * @param filters - 検索フィルター
 * @returns ユーザー一覧、ローディング状態、エラー
 *
 * @example
 * const { users, loading, error } = useUsers({ role: 'admin' });
 */
export const useUsers = (filters?: UserFilters) => {
  // 実装
};
```

### 11.2 AI に理解しやすいコード構造

```typescript
// ✅ 良い例: 明確な責務分離
// services/api/user.ts
export class UserAPI {
  static async getAll(): Promise<User[]> { /* ... */ }
  static async getById(id: string): Promise<User> { /* ... */ }
  static async create(data: CreateUserDTO): Promise<User> { /* ... */ }
  static async update(id: string, data: UpdateUserDTO): Promise<User> { /* ... */ }
  static async delete(id: string): Promise<void> { /* ... */ }
}

// ❌ 悪い例: 複雑で責務が不明確
export const doUserStuff = (action: string, data?: any) => {
  // 複雑な分岐処理
};
```

### 11.3 型安全性の確保

```typescript
// ✅ 推奨: 厳密な型定義
interface FormData {
  email: string;
  password: string;
  remember?: boolean;
}

const handleSubmit = (data: FormData) => {
  // 型安全な処理
};

// ❌ 非推奨: 型定義の省略
const handleSubmit = (data) => {  // 型が不明
  // AI が意図を理解しにくい
};
```

### 11.4 エラーメッセージの明確化

```typescript
// ✅ 良い例: 具体的なエラーメッセージ
if (!user) {
  throw new Error(`User with ID ${userId} not found in the database`);
}

// ❌ 悪い例: 曖昧なエラーメッセージ
if (!user) {
  throw new Error('Error');
}
```

---

## 付録: チェックリスト

### コードレビュー前の確認事項

- [ ] TypeScript の型エラーがない
- [ ] 不要な console.log が削除されている
- [ ] 適切なエラーハンドリングが実装されている
- [ ] コンポーネントの責務が明確に分離されている
- [ ] 重複する型定義がない
- [ ] any 型の使用を最小限に抑えている
- [ ] 適切な命名規則に従っている
- [ ] 必要に応じてメモ化が適用されている
- [ ] アクセシビリティが考慮されている
- [ ] レスポンシブデザインが実装されている

### AI 支援開発時の注意事項

- [ ] 生成されたコードの型定義を確認
- [ ] 既存のコードスタイルとの一貫性を確認
- [ ] 不要な依存関係が追加されていないか確認
- [ ] セキュリティ上の問題がないか確認
- [ ] パフォーマンスへの影響を考慮

---

## 更新履歴

- 2024-01-XX: 初版作成
- 規約は定期的に見直し、チーム全体で合意の上で更新すること

---

## 参考資料

- [React 公式ドキュメント](https://react.dev/)
- [TypeScript 公式ドキュメント](https://www.typescriptlang.org/)
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/)
