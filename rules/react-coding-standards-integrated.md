# React フロントエンド コーディング規約 統合版 v2.0

> Cursor/Claude Code を使用した React アプリケーション開発のための包括的コーディング規約
> ChatGPT版とClaude版の良いところを統合

## 自動強制範囲（linter が担当）

以下の規約項目は **ESLint / TypeScript** が pre-commit（commit 時）と CI（PR 時）に自動検出・ブロックします。設定の詳細は `frontend/package.json`（eslintConfig）を参照してください。

- 命名規則・未使用変数・型エラー（ESLint, TypeScript）
- セキュリティパターン（eslint-plugin-security: `detect-object-injection` 等）
- アクセシビリティ（eslint-plugin-jsx-a11y）
- フロントエンド依存関係の既知 CVE（`npm audit --audit-level=critical`、CI の frontend-lint で実行）

## 手動レビュー対象（linter が検出できない項目）

以下は AI レビュー（/plan-issue-review・/code-review）および人間によるレビューの対象です:

- コンポーネント設計（Props drilling 排除・責務分離）
- マルチテナント制約（組織スコープ・閲覧範囲の制御）
- パフォーマンス設計（不要な再レンダリング・N+1 API 呼び出し）
- UX・アクセシビリティの意図的な設計判断
- API 設計との整合性

---

## 目次

1. [対象と前提](#1-対象と前提)
2. [プロジェクト構成](#2-プロジェクト構成)
3. [TypeScript/型定義](#3-typescript型定義)
4. [命名規則](#4-命名規則)
5. [コンポーネント設計](#5-コンポーネント設計)
6. [状態管理](#6-状態管理)
7. [スタイリング](#7-スタイリング)
8. [データ取得・API通信](#8-データ取得api通信)
9. [フォーム処理](#9-フォーム処理)
10. [エラーハンドリング](#10-エラーハンドリング)
11. [パフォーマンス最適化](#11-パフォーマンス最適化)
12. [テスト戦略](#12-テスト戦略)
13. [アクセシビリティ（a11y）](#13-アクセシビリティa11y)
14. [セキュリティ](#14-セキュリティ)
15. [AI支援開発のベストプラクティス](#15-ai支援開発のベストプラクティス)
16. [Git/PR/CI運用](#16-gitprci運用)
17. [コード例とテンプレート](#17-コード例とテンプレート)
18. [設定ファイル](#18-設定ファイル)
19. [チェックリスト](#19-チェックリスト)

---

## 1. 対象と前提

### 技術スタック
- **フレームワーク**: React 18以降
- **ビルドツール**: Vite または Next.js (App Router)
- **言語**: TypeScript（必須）
- **状態管理**: React Hooks + Context API（基本）、Zustand（中規模）、Redux Toolkit（大規模）
- **スタイリング**: Tailwind CSS（推奨）、CSS Modules（既存プロジェクト）
- **フォーム**: React Hook Form + Zod/Yup
- **テスト**: Vitest/Jest + React Testing Library + MSW
- **Lint/Format**: ESLint + Prettier（CI で強制）

### 基本原則
- **型安全性優先**: any型の使用を最小限に
- **責務分離**: 単一責任の原則を遵守
- **再利用性**: DRY原則の徹底
- **保守性**: 可読性とメンテナンス性を重視

---

## 2. プロジェクト構成

### ディレクトリ構造（推奨）

```
src/
├── app/                    # ルーティング、ページ（Next.js は app/）
├── components/             # 再利用可能なUIコンポーネント
│   ├── common/            # 汎用コンポーネント（Button, Input等）
│   └── ui/                # shadcn/ui等のUIライブラリ
├── features/              # 機能単位のモジュール（ドメイン駆動）
│   └── <feature>/
│       ├── components/    # 機能固有のコンポーネント
│       ├── hooks/         # 機能固有のカスタムフック
│       ├── api.ts         # API クライアント
│       ├── types.ts       # 型定義
│       └── index.ts       # バレルエクスポート
├── contexts/              # グローバルContext
├── hooks/                 # 共通カスタムフック
├── services/              # API通信層、外部サービス統合
├── lib/                   # ユーティリティ関数
├── types/                 # グローバル型定義
│   ├── api.ts            # API共通型
│   ├── models.ts         # ドメインモデル
│   └── env.d.ts          # 環境変数型
├── styles/                # グローバルスタイル
├── constants/             # 定数定義
├── test/                  # テストユーティリティ、MSWハンドラ
└── assets/                # 画像、フォント等
```

### ファイル命名規則
- **コンポーネント**: PascalCase.tsx（例: `UserProfile.tsx`）
- **フック**: use*.ts（例: `useAuth.ts`）
- **ユーティリティ**: kebab-case.ts（例: `format-date.ts`）
- **型定義**: types.ts または *Types.ts
- **定数**: UPPER_SNAKE_CASE（例: `API_ENDPOINTS.ts`）
- **テスト**: *.test.tsx または *.spec.tsx

### バレルエクスポート
- 階層は**1段まで**（深いネストは避ける）
- features配下は必ずindex.tsでエクスポート管理

---

## 3. TypeScript/型定義

### 3.1 型定義の一元管理（最重要）

```typescript
// ❌ 悪い例: 型の重複定義
// components/UserList.tsx
interface User {
  id: string;
  name: string;
}

// pages/UserDetail.tsx
interface User {  // 重複！
  id: string;
  name: string;
}

// ✅ 良い例: 共通の型定義ファイルから import
// types/models.ts
export interface User {
  id: string;
  name: string;
  email: string;
  createdAt: string;
}

// どこでも同じ型を使用
import { User } from '@/types/models';
```

### 3.2 型定義の配置ルール

```typescript
// グローバル型: src/types/
export interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

// 機能固有型: src/features/<feature>/types.ts
export interface CreateUserDTO {
  name: string;
  email: string;
  role: UserRole;
}

// コンポーネント固有型: コンポーネントと同じファイル
interface UserCardProps {
  user: User;
  onClick?: (id: string) => void;
}
```

### 3.3 ジェネリック型の活用

```typescript
// API レスポンス
interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
  timestamp: string;
}

// ページネーション
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
  hasPrev: boolean;
}

// フォーム
type FormData<T> = {
  [K in keyof T]: T[K] | undefined;
};
```

### 3.4 型安全性のベストプラクティス

```typescript
// ✅ 良い例: 明示的な型定義
const fetchUser = async (id: string): Promise<User> => {
  const response = await api.get<User>(`/users/${id}`);
  return response.data;
};

// ✅ 良い例: ユニオン型で状態を表現
type LoadingState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error };

// ❌ 悪い例: any型の使用
const handleData = (data: any) => {  // 避ける
  console.log(data.someProperty);  // 型チェックなし
};

// ✅ 良い例: unknown型 + 型ガード
const isUser = (data: unknown): data is User => {
  return (
    typeof data === 'object' &&
    data !== null &&
    'id' in data &&
    'name' in data
  );
};
```

---

## 4. 命名規則

### 4.1 基本ルール

| 対象 | 規則 | 例 |
|------|------|-----|
| コンポーネント | PascalCase | `UserProfile` |
| 関数・変数 | camelCase | `getUserById` |
| 定数 | UPPER_SNAKE_CASE | `API_BASE_URL` |
| 型・インターフェース | PascalCase | `UserResponse` |
| enum | PascalCase（値はUPPER_SNAKE） | `UserRole.ADMIN` |
| ファイル（コンポーネント） | PascalCase | `UserCard.tsx` |
| ファイル（その他） | kebab-case | `format-date.ts` |

### 4.2 意味のある命名

```typescript
// ✅ 良い例: 明確で説明的
const getUsersByRole = async (role: UserRole): Promise<User[]> => {};
const isUserActive = (user: User): boolean => {};
const handleFormSubmit = (data: FormData): void => {};

// ❌ 悪い例: 曖昧または略語
const getData = () => {};  // 何のデータ？
const usr = {};  // 略語は避ける
const flag = true;  // 何のフラグ？
```

### 4.3 イベントハンドラー命名

```typescript
// コンポーネント内: handle + 対象 + アクション
const handleUserDelete = () => {};
const handleFormSubmit = () => {};
const handleInputChange = () => {};

// Props: on + 対象 + アクション
interface Props {
  onUserSelect: (user: User) => void;
  onFormSubmit: (data: FormData) => void;
  onDeleteConfirm: () => void;
}
```

### 4.4 真偽値の命名

```typescript
// is/has/can/should で開始
const isLoading = true;
const hasError = false;
const canEdit = true;
const shouldUpdate = false;
```

---

## 5. コンポーネント設計

### 5.1 基本原則

```typescript
// ✅ 推奨: 関数コンポーネント + TypeScript（React.FC は使用しない）
interface ButtonProps {
  label: string;
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  children?: React.ReactNode;  // 明示的に定義
}

export const Button = ({
  label,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  onClick,
  children
}: ButtonProps) => {
  return (
    <button
      className={cn(
        'btn',
        `btn-${variant}`,
        `btn-${size}`,
        loading && 'btn-loading'
      )}
      disabled={disabled || loading}
      onClick={onClick}
      aria-busy={loading}
    >
      {children || label}
    </button>
  );
};
```

### 5.2 コンポーネントの責務分離

```typescript
// Container Component（ロジック担当）
const UserListContainer = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchUsers = async () => {
      setLoading(true);
      try {
        const data = await userService.getAll();
        setUsers(data);
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, []);

  return (
    <UserListView
      users={users}
      loading={loading}
      error={error}
    />
  );
};

// Presentational Component（表示担当）
interface UserListViewProps {
  users: User[];
  loading: boolean;
  error: Error | null;
}

const UserListView = ({ users, loading, error }: UserListViewProps) => {
  // 4状態UI（loading/error/empty/success）
  if (loading) return <Spinner />;
  if (error) return <ErrorMessage error={error} />;
  if (users.length === 0) return <EmptyState message="ユーザーが見つかりません" />;

  return (
    <ul className="divide-y divide-gray-200">
      {users.map(user => (
        <UserItem key={user.id} user={user} />
      ))}
    </ul>
  );
};
```

### 5.3 コンポーネントサイズ制限

- **200行**を目安に分割
- 複雑なロジックはカスタムフックへ
- 繰り返し部分は別コンポーネントへ

### 5.4 Props設計のベストプラクティス

```typescript
// ✅ 良い例: 必須とオプションを明確に
interface CardProps {
  // 必須プロパティ
  title: string;
  description: string;

  // オプションプロパティ（デフォルト値あり）
  variant?: 'default' | 'highlighted';
  showActions?: boolean;

  // コールバック（オプション）
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;

  // 子要素（明示的に定義）
  children?: React.ReactNode;
  footer?: React.ReactElement;
}

// ❌ 悪い例: 曖昧なProps
interface BadProps {
  data: any;  // 型が不明
  config?: object;  // 構造が不明
  callback: Function;  // 引数と戻り値が不明
}
```

---

## 6. 状態管理

### 6.1 状態の適切な配置

```typescript
// 1. ローカル状態（単一コンポーネント）
const [isOpen, setIsOpen] = useState(false);

// 2. リフトアップ（親子間共有）
const ParentComponent = () => {
  const [sharedState, setSharedState] = useState('');
  return <ChildComponent value={sharedState} onChange={setSharedState} />;
};

// 3. Context（複数階層での共有）
const ThemeContext = createContext<ThemeContextType>({
  theme: 'light',
  toggleTheme: () => {},
});

// 4. グローバル状態（アプリ全体）
// Zustand の例
const useAuthStore = create<AuthState>((set) => ({
  user: null,
  login: async (credentials) => {
    const user = await authService.login(credentials);
    set({ user });
  },
  logout: () => set({ user: null }),
}));
```

### 6.2 カスタムフックの設計

```typescript
// hooks/useApi.ts
interface UseApiOptions {
  immediate?: boolean;
  onSuccess?: (data: any) => void;
  onError?: (error: Error) => void;
}

export const useApi = <T>(
  url: string,
  options: UseApiOptions = {}
) => {
  const [state, setState] = useState<LoadingState<T>>({
    status: 'idle'
  });

  const fetchData = useCallback(async () => {
    setState({ status: 'loading' });

    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      setState({ status: 'success', data });
      options.onSuccess?.(data);
    } catch (error) {
      setState({ status: 'error', error: error as Error });
      options.onError?.(error as Error);
    }
  }, [url]);

  useEffect(() => {
    if (options.immediate !== false) {
      fetchData();
    }
  }, [fetchData, options.immediate]);

  return {
    ...state,
    refetch: fetchData,
    isLoading: state.status === 'loading',
    isError: state.status === 'error',
    isSuccess: state.status === 'success',
  };
};
```

### 6.3 状態管理の選定基準

| 状態の種類 | 使用する技術 | 例 |
|------------|-------------|-----|
| UI状態（一時的） | useState | モーダル開閉、フォーム入力 |
| 派生状態 | useMemo | フィルター結果、計算値 |
| 非同期データ | useQuery/SWR | APIレスポンス |
| 認証情報 | Context + useReducer | ユーザー情報、トークン |
| アプリ全体 | Zustand/Redux | テーマ、言語設定 |

---

## 7. スタイリング

### 7.1 Tailwind CSS（推奨）

```typescript
// ✅ 良い例: ユーティリティクラス + cn()ヘルパー
import { cn } from '@/lib/utils';

interface ButtonProps {
  variant?: 'primary' | 'secondary';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const Button = ({ variant = 'primary', size = 'md', className, ...props }: ButtonProps) => {
  return (
    <button
      className={cn(
        // ベーススタイル
        'inline-flex items-center justify-center rounded-lg font-medium transition-colors',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2',

        // バリアント
        {
          'bg-blue-600 text-white hover:bg-blue-700': variant === 'primary',
          'bg-gray-100 text-gray-900 hover:bg-gray-200': variant === 'secondary',
        },

        // サイズ
        {
          'h-8 px-3 text-sm': size === 'sm',
          'h-10 px-4 text-sm': size === 'md',
          'h-12 px-6 text-base': size === 'lg',
        },

        // カスタムクラス
        className
      )}
      {...props}
    />
  );
};
```

### 7.2 CSS Modules（既存プロジェクト）

```typescript
// Button.module.css
.button {
  @apply inline-flex items-center justify-center rounded-lg;
}

.button--primary {
  @apply bg-blue-600 text-white hover:bg-blue-700;
}

// Button.tsx
import styles from './Button.module.css';

const Button = ({ variant }: ButtonProps) => (
  <button className={cn(styles.button, styles[`button--${variant}`])}>
    Click me
  </button>
);
```

### 7.3 デザイントークン

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          900: '#1e3a8a',
        },
      },
      spacing: {
        '18': '4.5rem',
      },
    },
  },
};
```

---

## 8. データ取得・API通信

### 8.1 API クライアントの設計

```typescript
// services/api-client.ts
class ApiClient {
  private baseURL: string;
  private headers: HeadersInit;

  constructor(baseURL: string = import.meta.env.VITE_API_URL) {
    this.baseURL = baseURL;
    this.headers = {
      'Content-Type': 'application/json',
    };
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;

    const config: RequestInit = {
      ...options,
      headers: {
        ...this.headers,
        ...options.headers,
      },
    };

    const response = await fetch(url, config);

    if (!response.ok) {
      throw new ApiError(response.status, `API Error: ${response.statusText}`);
    }

    return response.json();
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  async post<T>(endpoint: string, body: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  async put<T>(endpoint: string, body: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

// エラークラス
class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export const apiClient = new ApiClient();
```

### 8.2 Feature ごとの API 定義

```typescript
// features/user/api.ts
import { apiClient } from '@/services/api-client';
import { User, CreateUserDTO, UpdateUserDTO } from './types';

export const userApi = {
  getAll: () =>
    apiClient.get<User[]>('/users'),

  getById: (id: string) =>
    apiClient.get<User>(`/users/${id}`),

  create: (data: CreateUserDTO) =>
    apiClient.post<User>('/users', data),

  update: (id: string, data: UpdateUserDTO) =>
    apiClient.put<User>(`/users/${id}`, data),

  delete: (id: string) =>
    apiClient.delete<void>(`/users/${id}`),
};
```

### 8.3 4状態UIの実装

```typescript
// 必ず4つの状態を表現
const UserList = () => {
  const { data, isLoading, isError, isEmpty } = useUsers();

  // 1. Loading状態
  if (isLoading) {
    return <Skeleton className="h-64" />;
  }

  // 2. Error状態
  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          データの取得に失敗しました。再度お試しください。
        </AlertDescription>
      </Alert>
    );
  }

  // 3. Empty状態
  if (isEmpty) {
    return (
      <EmptyState
        icon={<Users className="h-12 w-12" />}
        title="ユーザーが見つかりません"
        description="新しいユーザーを追加してください"
        action={
          <Button onClick={handleAddUser}>
            ユーザーを追加
          </Button>
        }
      />
    );
  }

  // 4. Success状態（データあり）
  return (
    <div className="grid gap-4">
      {data.map(user => (
        <UserCard key={user.id} user={user} />
      ))}
    </div>
  );
};
```

---

## 9. フォーム処理

### 9.1 React Hook Form + Zod

```typescript
// schemas/user.schema.ts
import { z } from 'zod';

export const createUserSchema = z.object({
  email: z
    .string()
    .min(1, 'メールアドレスは必須です')
    .email('有効なメールアドレスを入力してください'),

  password: z
    .string()
    .min(8, 'パスワードは8文字以上で入力してください')
    .regex(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      'パスワードは大文字、小文字、数字を含む必要があります'
    ),

  confirmPassword: z
    .string()
    .min(1, 'パスワード確認は必須です'),

  age: z
    .number()
    .min(18, '18歳以上である必要があります')
    .max(100, '有効な年齢を入力してください'),
})
.refine((data) => data.password === data.confirmPassword, {
  message: 'パスワードが一致しません',
  path: ['confirmPassword'],
});

export type CreateUserFormData = z.infer<typeof createUserSchema>;
```

```typescript
// components/UserForm.tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

const UserForm = () => {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<CreateUserFormData>({
    resolver: zodResolver(createUserSchema),
    defaultValues: {
      email: '',
      password: '',
      confirmPassword: '',
      age: 20,
    },
  });

  const onSubmit = async (data: CreateUserFormData) => {
    try {
      await userApi.create(data);
      toast.success('ユーザーを作成しました');
      router.push('/users');
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setError('email', {
          message: 'このメールアドレスは既に使用されています',
        });
      } else {
        toast.error('エラーが発生しました');
      }
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <Label htmlFor="email">メールアドレス</Label>
        <Input
          id="email"
          type="email"
          {...register('email')}
          aria-invalid={!!errors.email}
          aria-describedby="email-error"
        />
        {errors.email && (
          <ErrorMessage id="email-error">
            {errors.email.message}
          </ErrorMessage>
        )}
      </div>

      {/* 他のフィールド... */}

      <Button
        type="submit"
        disabled={isSubmitting}
        className="w-full"
      >
        {isSubmitting ? (
          <>
            <Spinner className="mr-2" />
            送信中...
          </>
        ) : (
          '登録'
        )}
      </Button>
    </form>
  );
};
```

---

## 10. エラーハンドリング

### 10.1 Error Boundary の実装

```typescript
// components/ErrorBoundary.tsx
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ComponentType<{ error: Error }> },
  ErrorBoundaryState
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // エラーログをサービスに送信
    console.error('Error caught by boundary:', error, errorInfo);

    // Sentryなどのエラー監視サービスに送信
    if (import.meta.env.PROD) {
      // Sentry.captureException(error, { contexts: { react: errorInfo } });
    }
  }

  render() {
    if (this.state.hasError) {
      const FallbackComponent = this.props.fallback || DefaultErrorFallback;
      return <FallbackComponent error={this.state.error!} />;
    }

    return this.props.children;
  }
}

// デフォルトのエラー表示
const DefaultErrorFallback = ({ error }: { error: Error }) => (
  <div className="flex min-h-screen flex-col items-center justify-center">
    <div className="text-center">
      <h1 className="mb-4 text-4xl font-bold">エラーが発生しました</h1>
      <p className="mb-8 text-gray-600">
        申し訳ございません。予期しないエラーが発生しました。
      </p>
      {import.meta.env.DEV && (
        <details className="mb-8 text-left">
          <summary className="cursor-pointer">エラー詳細</summary>
          <pre className="mt-2 whitespace-pre-wrap text-sm">
            {error.message}
            {error.stack}
          </pre>
        </details>
      )}
      <Button onClick={() => window.location.reload()}>
        ページを再読み込み
      </Button>
    </div>
  </div>
);
```

### 10.2 非同期エラーハンドリング

```typescript
// hooks/useAsyncError.ts
export const useAsyncError = () => {
  const [, setError] = useState();

  return useCallback(
    (error: Error) => {
      setError(() => {
        throw error;
      });
    },
    [setError]
  );
};

// 使用例
const MyComponent = () => {
  const throwAsyncError = useAsyncError();

  const handleClick = async () => {
    try {
      await riskyAsyncOperation();
    } catch (error) {
      // Error Boundaryでキャッチされる
      throwAsyncError(error as Error);
    }
  };
};
```

### 10.3 API エラーハンドリング

```typescript
// utils/error-handler.ts
export const handleApiError = (error: unknown): string => {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 400:
        return '入力内容に誤りがあります';
      case 401:
        return 'ログインが必要です';
      case 403:
        return 'アクセス権限がありません';
      case 404:
        return 'データが見つかりません';
      case 409:
        return 'データが既に存在します';
      case 429:
        return 'リクエストが多すぎます。しばらくお待ちください';
      case 500:
        return 'サーバーエラーが発生しました';
      default:
        return 'エラーが発生しました';
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  return '予期しないエラーが発生しました';
};
```

---

## 11. パフォーマンス最適化

### 11.1 メモ化の適切な使用

```typescript
// ✅ 良い例: 重い計算処理のメモ化
const ExpensiveComponent = ({ data }: { data: Item[] }) => {
  const sortedData = useMemo(() => {
    console.log('Sorting data...');
    return [...data].sort((a, b) => b.value - a.value);
  }, [data]);

  const processedData = useMemo(() => {
    console.log('Processing data...');
    return sortedData.map(item => ({
      ...item,
      label: `${item.name} (${item.value})`,
      percentage: (item.value / total) * 100,
    }));
  }, [sortedData]);

  return <DataVisualization data={processedData} />;
};

// ✅ 良い例: 参照の安定化が必要な場合
const DataTable = ({ onRowClick }: Props) => {
  const handleClick = useCallback((row: Row) => {
    // 子コンポーネントの不要な再レンダリングを防ぐ
    onRowClick(row.id);
  }, [onRowClick]);

  return <Table onRowClick={handleClick} />;
};

// ❌ 悪い例: 過度な最適化
const SimpleComponent = ({ value }: { value: number }) => {
  // 単純な計算にuseMemoは不要
  const doubled = useMemo(() => value * 2, [value]);

  // プリミティブ値にuseCallbackは不要
  const handleClick = useCallback(() => {
    console.log('clicked');
  }, []);
};
```

### 11.2 コード分割と遅延ロード

```typescript
// routes/index.tsx
import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';

// 遅延ロード
const Dashboard = lazy(() => import('@/pages/Dashboard'));
const UserProfile = lazy(() => import('@/pages/UserProfile'));
const Settings = lazy(() => import('@/pages/Settings'));

// 重いライブラリの動的インポート
const loadChartLibrary = () => import('recharts');

export const AppRoutes = () => (
  <Suspense fallback={<PageLoader />}>
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/profile" element={<UserProfile />} />
      <Route path="/settings" element={<Settings />} />
    </Routes>
  </Suspense>
);
```

### 11.3 リスト最適化

```typescript
// ✅ 良い例: 安定したキーと仮想スクロール
import { FixedSizeList } from 'react-window';

const LargeList = ({ items }: { items: Item[] }) => {
  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => (
    <div style={style}>
      {/* keyは安定したIDを使用 */}
      <ItemCard key={items[index].id} item={items[index]} />
    </div>
  );

  return (
    <FixedSizeList
      height={600}
      itemCount={items.length}
      itemSize={80}
      width="100%"
    >
      {Row}
    </FixedSizeList>
  );
};

// ❌ 悪い例: インデックスをキーに使用
{items.map((item, index) => (
  <ItemCard key={index} item={item} />  // 並び替え時に問題
))}
```

### 11.4 画像最適化

```typescript
// components/OptimizedImage.tsx
interface OptimizedImageProps {
  src: string;
  alt: string;
  width: number;
  height: number;
  priority?: boolean;
}

const OptimizedImage = ({ src, alt, width, height, priority = false }: OptimizedImageProps) => {
  return (
    <picture>
      <source
        srcSet={`${src}?w=${width * 2}&q=75 2x, ${src}?w=${width}&q=75 1x`}
        type="image/webp"
      />
      <img
        src={`${src}?w=${width}&q=75`}
        alt={alt}
        width={width}
        height={height}
        loading={priority ? 'eager' : 'lazy'}
        decoding="async"
        className="h-auto w-full"
      />
    </picture>
  );
};
```

---

## 12. テスト戦略

### 12.1 テストの優先順位

1. **ユニットテスト**（ロジック、ユーティリティ）- 80%
2. **統合テスト**（カスタムフック、API）- 15%
3. **E2Eテスト**（主要フロー）- 5%

### 12.2 コンポーネントテスト

```typescript
// components/UserCard.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UserCard } from './UserCard';

describe('UserCard', () => {
  const mockUser = {
    id: '1',
    name: '田中太郎',
    email: 'tanaka@example.com',
    role: 'admin' as const,
  };

  it('ユーザー情報を正しく表示する', () => {
    render(<UserCard user={mockUser} />);

    expect(screen.getByText('田中太郎')).toBeInTheDocument();
    expect(screen.getByText('tanaka@example.com')).toBeInTheDocument();
    expect(screen.getByText('管理者')).toBeInTheDocument();
  });

  it('クリック時にコールバックが呼ばれる', async () => {
    const handleClick = vi.fn();
    const user = userEvent.setup();

    render(<UserCard user={mockUser} onClick={handleClick} />);

    await user.click(screen.getByRole('button'));

    expect(handleClick).toHaveBeenCalledWith(mockUser.id);
  });

  it('ローディング状態を表示する', () => {
    render(<UserCard user={mockUser} loading />);

    expect(screen.getByTestId('skeleton')).toBeInTheDocument();
    expect(screen.queryByText('田中太郎')).not.toBeInTheDocument();
  });
});
```

### 12.3 カスタムフックのテスト

```typescript
// hooks/useCounter.test.ts
import { renderHook, act } from '@testing-library/react';
import { useCounter } from './useCounter';

describe('useCounter', () => {
  it('初期値を設定できる', () => {
    const { result } = renderHook(() => useCounter(10));
    expect(result.current.count).toBe(10);
  });

  it('インクリメントが正しく動作する', () => {
    const { result } = renderHook(() => useCounter());

    act(() => {
      result.current.increment();
    });

    expect(result.current.count).toBe(1);
  });

  it('最大値を超えない', () => {
    const { result } = renderHook(() => useCounter(9, { max: 10 }));

    act(() => {
      result.current.increment();
      result.current.increment(); // 11になろうとする
    });

    expect(result.current.count).toBe(10);
  });
});
```

### 12.4 MSW によるAPIモック

```typescript
// test/mocks/handlers.ts
import { rest } from 'msw';

export const handlers = [
  rest.get('/api/users', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json([
        { id: '1', name: '田中太郎', email: 'tanaka@example.com' },
        { id: '2', name: '鈴木花子', email: 'suzuki@example.com' },
      ])
    );
  }),

  rest.post('/api/users', async (req, res, ctx) => {
    const body = await req.json();

    // バリデーションエラーのテスト
    if (!body.email) {
      return res(
        ctx.status(400),
        ctx.json({ error: 'Email is required' })
      );
    }

    return res(
      ctx.status(201),
      ctx.json({ id: '3', ...body })
    );
  }),
];

// test/setup.ts
import { setupServer } from 'msw/node';
import { handlers } from './mocks/handlers';

export const server = setupServer(...handlers);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

---

## 13. アクセシビリティ（a11y）

### 13.1 基本要件

```typescript
// ✅ 良い例: アクセシブルなフォーム
const LoginForm = () => {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <form aria-label="ログインフォーム">
      <div>
        <label htmlFor="email">
          メールアドレス
          <span aria-label="必須" className="text-red-500">*</span>
        </label>
        <input
          id="email"
          type="email"
          required
          aria-required="true"
          aria-describedby="email-error"
          aria-invalid={!!errors.email}
        />
        {errors.email && (
          <span id="email-error" role="alert" className="text-red-500">
            {errors.email}
          </span>
        )}
      </div>

      <div>
        <label htmlFor="password">
          パスワード
          <span aria-label="必須" className="text-red-500">*</span>
        </label>
        <div className="relative">
          <input
            id="password"
            type={showPassword ? 'text' : 'password'}
            required
            aria-required="true"
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            aria-label={showPassword ? 'パスワードを隠す' : 'パスワードを表示'}
            aria-pressed={showPassword}
          >
            {showPassword ? <EyeOff /> : <Eye />}
          </button>
        </div>
      </div>

      <button
        type="submit"
        aria-busy={isSubmitting}
        disabled={isSubmitting}
      >
        {isSubmitting ? 'ログイン中...' : 'ログイン'}
      </button>
    </form>
  );
};
```

### 13.2 キーボードナビゲーション

```typescript
// ✅ 良い例: キーボード操作対応モーダル
const Modal = ({ isOpen, onClose, children }: ModalProps) => {
  const modalRef = useRef<HTMLDivElement>(null);

  // ESCキーで閉じる
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // フォーカストラップ
  useEffect(() => {
    if (isOpen && modalRef.current) {
      const previouslyFocused = document.activeElement as HTMLElement;
      modalRef.current.focus();

      return () => {
        previouslyFocused?.focus();
      };
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      ref={modalRef}
      tabIndex={-1}
      className="fixed inset-0 z-50"
    >
      <div
        className="fixed inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
};
```

### 13.3 スクリーンリーダー対応

```typescript
// ✅ 良い例: スクリーンリーダーフレンドリー
const DataTable = ({ data }: { data: TableData[] }) => {
  return (
    <table role="table" aria-label="ユーザー一覧">
      <caption className="sr-only">
        登録済みユーザーの一覧。名前、メールアドレス、役割を表示。
      </caption>
      <thead>
        <tr role="row">
          <th role="columnheader" scope="col">名前</th>
          <th role="columnheader" scope="col">メールアドレス</th>
          <th role="columnheader" scope="col">役割</th>
          <th role="columnheader" scope="col">
            <span className="sr-only">操作</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {data.map((row) => (
          <tr key={row.id} role="row">
            <td role="cell">{row.name}</td>
            <td role="cell">{row.email}</td>
            <td role="cell">{row.role}</td>
            <td role="cell">
              <button
                aria-label={`${row.name}を編集`}
                onClick={() => handleEdit(row.id)}
              >
                編集
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};
```

---

## 14. セキュリティ

### 14.1 XSS対策

```typescript
// ❌ 危険: dangerouslySetInnerHTML の使用
<div dangerouslySetInnerHTML={{ __html: userContent }} />

// ✅ 安全: サニタイズしてから使用（やむを得ない場合のみ）
import DOMPurify from 'dompurify';

const SafeHTML = ({ html }: { html: string }) => {
  const sanitized = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p'],
    ALLOWED_ATTR: ['href'],
  });

  return <div dangerouslySetInnerHTML={{ __html: sanitized }} />;
};
```

### 14.2 環境変数の管理

```typescript
// .env.local
VITE_API_URL=http://localhost:3000
VITE_PUBLIC_KEY=public_key_12345  # 公開可能な値のみ
# VITE_SECRET_KEY=secret123  # ❌ 秘密情報は含めない

// types/env.d.ts
interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_PUBLIC_KEY: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

### 14.3 認証トークンの管理

```typescript
// ❌ 悪い例: localStorage に保存
localStorage.setItem('token', token);

// ✅ 良い例: httpOnly Cookie または メモリ管理
class TokenManager {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  getToken(): string | null {
    return this.token;
  }

  clearToken() {
    this.token = null;
  }

  // APIリクエスト時にヘッダーに追加
  getAuthHeader(): HeadersInit {
    return this.token
      ? { Authorization: `Bearer ${this.token}` }
      : {};
  }
}
```

---

## 15. AI支援開発のベストプラクティス

### 15.1 AI生成コードの管理

```typescript
/**
 * AUTOGEN: 2024-01-15
 * Generated by: Claude/Cursor
 * Purpose: ユーザー管理機能のCRUD操作
 * Limitations:
 *   - ページネーションは未実装
 *   - ソート機能は名前のみ対応
 * TODO:
 *   - [ ] ページネーション実装
 *   - [ ] 複数項目でのソート対応
 */
```

### 15.2 AI理解しやすいコード構造

```typescript
// ✅ 良い例: 明確な責務と型定義
interface UserService {
  getAll(): Promise<User[]>;
  getById(id: string): Promise<User>;
  create(data: CreateUserDTO): Promise<User>;
  update(id: string, data: UpdateUserDTO): Promise<User>;
  delete(id: string): Promise<void>;
}

// ✅ 良い例: 具体的なエラーメッセージ
if (!user) {
  throw new Error(`User with ID ${userId} not found in database`);
}

// ❌ 悪い例: 複雑で曖昧な処理
const process = (d: any, t: string) => {
  return d?.[t] ?? (t === 'x' ? [] : {});
};
```

### 15.3 プロンプトテンプレート

```markdown
あなたは React/TypeScript のシニアエンジニアです。
以下の規約に従ってコードを生成してください：

## 必須要件
- TypeScript の strict モードでエラーが出ないこと
- 型定義は types/ または features/<feature>/types.ts に配置
- コンポーネントは 200行以内
- 4状態UI（loading/error/empty/success）を実装
- アクセシビリティ属性（aria-*）を適切に付与

## スタイル
- Tailwind CSS を使用
- cn() ヘルパーで条件付きクラスを管理
- デザイントークンを使用（magic number 禁止）

## 状態管理
- ローカル状態は useState
- 共有状態は Context または Zustand
- フォームは React Hook Form + Zod

## エラーハンドリング
- try-catch で適切にエラーをキャッチ
- ユーザーフレンドリーなエラーメッセージ
- Error Boundary でコンポーネントエラーを処理

不明な点は TODO コメントで明示してください。
```

### 15.4 AI生成コードのレビューポイント

```typescript
// レビューチェックリスト
const AI_CODE_REVIEW_CHECKLIST = {
  types: [
    '型定義が重複していないか',
    'any型が使われていないか',
    '既存の型定義を再利用しているか',
  ],

  security: [
    'XSS脆弱性がないか',
    '環境変数が適切に管理されているか',
    'APIキーが露出していないか',
  ],

  performance: [
    '不要な再レンダリングが発生しないか',
    'メモ化が適切に使用されているか',
    '大きなリストに仮想スクロールが必要か',
  ],

  a11y: [
    'aria属性が適切に設定されているか',
    'キーボード操作が可能か',
    'フォーカス管理が適切か',
  ],

  consistency: [
    '既存のコードスタイルと一致しているか',
    '命名規則に従っているか',
    'インポート順序が正しいか',
  ],
};
```

---

## 16. Git/PR/CI運用

### 16.1 ブランチ戦略

```bash
main                    # 本番環境
├── develop            # 開発環境
    ├── feat/user-auth    # 機能追加
    ├── fix/login-error   # バグ修正
    └── chore/deps-update # その他
```

### 16.2 コミットメッセージ

```bash
# Conventional Commits形式
feat(auth): add OAuth2.0 login support
fix(ui): resolve modal close button alignment issue
docs(readme): update installation instructions
test(api): add unit tests for user service
refactor(components): extract common button styles
perf(images): implement lazy loading for gallery
chore(deps): update React to v18.2.0
```

### 16.3 PR テンプレート

```markdown
## 📝 概要
<!-- 変更の目的と背景を簡潔に -->

## 🔄 変更内容
<!-- 主な変更点をリストで -->
-
-

## 📸 スクリーンショット
<!-- UIの変更がある場合は必須 -->

## ✅ テスト
- [ ] ユニットテスト追加/更新
- [ ] 統合テスト実行
- [ ] 手動テスト完了

## 📊 パフォーマンス
<!-- パフォーマンスへの影響がある場合 -->
- Bundle size: 前 100KB → 後 102KB (+2KB)
- Lighthouse score: 95 → 94 (-1)

## 🔍 レビューポイント
<!-- 特に注意深く見てほしい箇所 -->

## 📚 関連情報
<!-- 関連するIssue、ドキュメント等 -->
- Closes #123
- 設計書: [link]
```

### 16.4 CI パイプライン

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: 18
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Type check
        run: npm run typecheck

      - name: Test
        run: npm run test:ci

      - name: Build
        run: npm run build

      - name: Bundle size check
        uses: andresz1/size-limit-action@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

---

## 17. コード例とテンプレート

### 17.1 カスタムフックテンプレート

```typescript
/**
 * AUTOGEN: 2024-01-15
 * Hook: useLocalStorage
 * Purpose: localStorage との同期を保った状態管理
 */
import { useState, useEffect, useCallback } from 'react';

type SetValue<T> = (value: T | ((prev: T) => T)) => void;

export function useLocalStorage<T>(
  key: string,
  initialValue: T,
  options?: {
    serializer?: (value: T) => string;
    deserializer?: (value: string) => T;
  }
): [T, SetValue<T>, () => void] {
  const serializer = options?.serializer ?? JSON.stringify;
  const deserializer = options?.deserializer ?? JSON.parse;

  // 初期値の取得
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? deserializer(item) : initialValue;
    } catch (error) {
      console.error(`Error loading localStorage key "${key}":`, error);
      return initialValue;
    }
  });

  // 値の更新
  const setValue: SetValue<T> = useCallback(
    (value) => {
      try {
        setStoredValue((prev) => {
          const nextValue = value instanceof Function ? value(prev) : value;
          window.localStorage.setItem(key, serializer(nextValue));
          return nextValue;
        });
      } catch (error) {
        console.error(`Error setting localStorage key "${key}":`, error);
      }
    },
    [key, serializer]
  );

  // 値の削除
  const removeValue = useCallback(() => {
    try {
      window.localStorage.removeItem(key);
      setStoredValue(initialValue);
    } catch (error) {
      console.error(`Error removing localStorage key "${key}":`, error);
    }
  }, [key, initialValue]);

  // 他のタブでの変更を監視
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === key && e.newValue !== null) {
        setStoredValue(deserializer(e.newValue));
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [key, deserializer]);

  return [storedValue, setValue, removeValue];
}
```

### 17.2 コンポーネントテンプレート（Tailwind）

```typescript
/**
 * AUTOGEN: 2024-01-15
 * Component: Card
 * Responsibility: 汎用カードコンポーネント
 * Limitations: アニメーション未対応
 */
import { forwardRef } from 'react';
import { cn } from '@/lib/utils';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'outlined' | 'elevated';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  interactive?: boolean;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({
    className,
    variant = 'default',
    padding = 'md',
    interactive = false,
    children,
    ...props
  }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          // ベーススタイル
          'rounded-lg',

          // バリアント
          {
            'bg-white border border-gray-200': variant === 'default',
            'bg-transparent border-2 border-gray-300': variant === 'outlined',
            'bg-white shadow-lg': variant === 'elevated',
          },

          // パディング
          {
            'p-0': padding === 'none',
            'p-3': padding === 'sm',
            'p-4': padding === 'md',
            'p-6': padding === 'lg',
          },

          // インタラクティブ
          interactive && [
            'cursor-pointer transition-all duration-200',
            'hover:shadow-md hover:-translate-y-0.5',
            'active:translate-y-0 active:shadow-sm',
          ],

          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

// サブコンポーネント
export const CardHeader = forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('mb-4 pb-4 border-b border-gray-200', className)}
    {...props}
  />
));

CardHeader.displayName = 'CardHeader';

export const CardTitle = forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn('text-lg font-semibold text-gray-900', className)}
    {...props}
  />
));

CardTitle.displayName = 'CardTitle';

export const CardContent = forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('text-gray-600', className)} {...props} />
));

CardContent.displayName = 'CardContent';
```

---

## 18. 設定ファイル

### 18.1 ESLint設定（.eslintrc.json）

```json
{
  "root": true,
  "env": {
    "browser": true,
    "es2023": true,
    "node": true
  },
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "ecmaVersion": "latest",
    "sourceType": "module",
    "project": "./tsconfig.json"
  },
  "plugins": [
    "@typescript-eslint",
    "react",
    "react-hooks",
    "import",
    "jsx-a11y"
  ],
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:@typescript-eslint/recommended-requiring-type-checking",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
    "plugin:jsx-a11y/recommended",
    "plugin:import/recommended",
    "plugin:import/typescript",
    "prettier"
  ],
  "settings": {
    "react": {
      "version": "detect"
    },
    "import/resolver": {
      "typescript": {
        "alwaysTryTypes": true
      }
    }
  },
  "rules": {
    "react/react-in-jsx-scope": "off",
    "react/prop-types": "off",
    "react/display-name": "off",

    "@typescript-eslint/explicit-module-boundary-types": "off",
    "@typescript-eslint/no-unused-vars": [
      "error",
      { "argsIgnorePattern": "^_" }
    ],
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/consistent-type-imports": "error",

    "import/order": [
      "error",
      {
        "groups": [
          "builtin",
          "external",
          "internal",
          "parent",
          "sibling",
          "index"
        ],
        "alphabetize": {
          "order": "asc",
          "caseInsensitive": true
        },
        "newlines-between": "always"
      }
    ],

    "no-console": [
      "warn",
      { "allow": ["warn", "error"] }
    ]
  }
}
```

### 18.2 Prettier設定（.prettierrc）

```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100,
  "arrowParens": "always",
  "endOfLine": "lf",
  "bracketSpacing": true,
  "jsxBracketSameLine": false,
  "jsxSingleQuote": false
}
```

### 18.3 TypeScript設定（tsconfig.json）

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,

    /* Paths */
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

### 18.4 EditorConfig（.editorconfig）

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
indent_style = space
indent_size = 2
insert_final_newline = true
trim_trailing_whitespace = true

[*.md]
trim_trailing_whitespace = false

[*.{json,yml,yaml}]
indent_size = 2
```

---

## 19. チェックリスト

### 19.1 コードレビュー前

- [ ] TypeScript エラーが 0 件
- [ ] ESLint エラーが 0 件
- [ ] 不要な console.log を削除
- [ ] 型定義の重複がない
- [ ] any 型を使用していない（やむを得ない場合はコメント）
- [ ] 4状態UI（loading/error/empty/success）を実装
- [ ] エラーハンドリングを実装
- [ ] テストを追加/更新

### 19.2 パフォーマンス

- [ ] 不要な再レンダリングがない
- [ ] 大きなリストに仮想スクロール検討
- [ ] 画像の遅延読み込み設定
- [ ] バンドルサイズの確認

### 19.3 アクセシビリティ

- [ ] 適切な見出し階層
- [ ] フォームラベルの関連付け
- [ ] aria属性の設定
- [ ] キーボード操作可能
- [ ] フォーカスリング表示
- [ ] 色のコントラスト比 4.5:1以上

### 19.4 セキュリティ

- [ ] XSS対策（dangerouslySetInnerHTML未使用）
- [ ] 環境変数に秘密情報なし
- [ ] 外部リンクに rel="noopener noreferrer"
- [ ] ユーザー入力のサニタイズ

### 19.5 AI生成コード

- [ ] AUTOGEN コメント追加
- [ ] 制限事項を明記
- [ ] TODO事項をリスト化
- [ ] 既存コードスタイルと一致
- [ ] 型定義を適切に使用

---

## 更新履歴

- 2024-01-XX: v2.0 - ChatGPT版とClaude版を統合
- 2024-01-XX: v1.0 - 初版作成

---

## 参考資料

- [React 公式ドキュメント](https://react.dev/)
- [TypeScript 公式ドキュメント](https://www.typescriptlang.org/)
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/)
- [Testing Library](https://testing-library.com/)
- [Web Content Accessibility Guidelines (WCAG)](https://www.w3.org/WAI/WCAG21/quickref/)
- [MDN Web Docs - Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)
