# フロントエンド開発コーディング規約（React）

本ドキュメントは、**Cursor** と **Claude Code** を併用した Web アプリ開発におけるフロントエンド（React）の実装規約です。チーム/個人開発のいずれにも適用します。バックエンドやインフラの規約は別紙とします。

---

## 0. 対象と前提
- 対象：React 18 以降 / Vite または Next.js（App Router）
- 言語：**TypeScript 推奨**（JS の場合も型注釈コメントで整備）
- 状態管理：原則 **React Hooks + Context**。必要時に軽量ストア（Zustand など）を採用。Redux は要件次第。
- 非同期処理：標準 `fetch` / `async/await`。データ取得層は単一責務（API クライアント）へ集約。
- スタイル：**Tailwind CSS 推奨**。既存で CSS Modules/SCSS を採用済みのプロジェクトは継続を許可（混在禁止）。
- テスト：Vitest/Jest + React Testing Library。
- Lint/Format：ESLint + Prettier（CI で強制）。

> 注：Cursor/Claude による自動生成は **規約を上書きしない**。本規約に従うプロンプトテンプレートを後述。

---

## 1. ディレクトリ構成（例：Vite）
```
src/
  app/                 # ルーティング、ページ（Next.js は app/）
  components/          # 再利用 UI（純粋・副作用なしを基本）
  features/            # 機能単位の UI + ロジック（ドメイン駆動）
    <feature>/
      components/
      hooks/
      types.ts
      api.ts           # API クライアント（fetch ラッパ）
      index.ts         # 外部公開ポイント
  hooks/               # 横断的カスタムフック
  lib/                 # ユーティリティ（date, number, validator 等）
  styles/              # Tailwind グローバル, CSS Reset
  assets/              # 画像/フォント
  test/                # テストユーティリティ（msw ハンドラ等）
  types/               # グローバル型定義（env, api 共通型）
```
- **禁止**：`utils.ts` に何でも集約。→ 機能ごと/型ごとに分割。
- Barrel export（`index.ts`）は**階層 1 段**まで。

---

## 2. 命名規則
- ファイル/ディレクトリ：`kebab-case`、React コンポーネント：`PascalCase.tsx`
- フック：`useXxx`（返り値はタプル/オブジェクトで意味を明確化）
- 型：`XxxProps`, `XxxResponse`, `XxxPayload`
- 真偽：`is`, `has`, `can`, `should` で開始
- 定数：`UPPER_SNAKE_CASE`
- **禁止**：略語多用（`usr`, `cfg` 等）。可読性優先。

---

## 3. インポート順序（eslint-plugin-import）
1. Node/Polyfill（`fs`, `path` など）
2. 外部ライブラリ（`react`, `react-dom`, `zustand` など）
3. エイリアス（`@/lib`, `@/components`）
4. 相対パス（`./`, `../`）
- それぞれ**アルファベット昇順**、**拡張子省略**。

---

## 4. コンポーネント設計
- **関数コンポーネントのみ**。`React.FC` は使用しない（暗黙 children 回避）。
- 1 コンポーネント 1 ファイル、**200 行目安**。超える場合は分割。
- Props は **型を必須化**、オプショナルは `?` で明示。デフォルト値は分割代入で。
- 表示専用（Presentational）と容器（Container）を分離。Container は **データ取得と状態管理のみ**。
- 再レンダリング抑制：`memo`/`useMemo`/`useCallback` は必要最小限に限定。
- **副作用は useEffect に隔離**。クリーンアップを常に実装。
- **アクセシビリティ（a11y）** 属性を必須（`aria-*`, フォーカス管理, キーボード操作）。

### 4.1 Props/State の型例
```tsx
// components/UserCard.tsx
export type UserCardProps = {
  name: string;
  avatarUrl?: string;
  onClick?: () => void;
};

export function UserCard({ name, avatarUrl, onClick }: UserCardProps) {
  return (
    <button className="flex items-center gap-3" onClick={onClick} aria-label={`${name} を選択`}>
      <img src={avatarUrl ?? "/avatar.svg"} alt="avatar" className="h-8 w-8 rounded-full" />
      <span className="text-sm font-medium">{name}</span>
    </button>
  );
}
```

---

## 5. スタイリング規約
### 5.1 Tailwind 採用時
- **原則：ユーティリティ優先 + コンポーネント化**。
- 重複クラスは `cn()` ヘルパで条件結合。複雑化したら `components/ui/` に抽出。
- トークン：フォント/色/間隔は `tailwind.config.js` に定義。**謎数値（magic number）禁止**。
- shadcn/ui 採用時：**ローカルコピー**し、改変は `components/ui/` 配下のみ。

### 5.2 CSS Modules/SCSS 採用時
- BEM 風：`.Block__elem--mod`
- 変数/ミックスインは `styles/` に集約し、**グローバル汚染禁止**。

---

## 6. データ取得・エラーハンドリング
- API クライアントは `features/<feature>/api.ts` に集約。
- `fetch` ラッパで **ベース URL と共通ヘッダ**、**エラー正規化**（`{ status, code, message }`）。
- UI は `loading / error / empty / success` の 4 状態を必ず表現。
- 冪等 GET はキャッシュ検討（HTTP キャッシュ / SWR パターン）。

```ts
// features/user/api.ts
export async function getUser(id: string) {
  const res = await fetch(`/api/users/${id}`);
  if (!res.ok) throw new Error(`USER_FETCH_FAILED:${res.status}`);
  return (await res.json()) as { id: string; name: string };
}
```

---

## 7. フォーム
- **React Hook Form 推奨**。スキーマ検証は Zod/Yup。
- バリデーションは **即時 + サブミット時** の双方で実施。
- エラーメッセージは日本語/英語の i18n 対応（`errors.required` 等のキー運用）。

---

## 8. グラフ（Recharts など）
- 受け取るデータ型を厳密化（`ChartPoint { x: number; y: number; }` 等）。
- 軸/単位/凡例/アクセシビリティ（`role="img"`、`aria-label`）を明示。
- **0 除算や欠損値の描画保護**（`isFinite` チェック）。

---

## 9. ロギングと監視
- 画面単位で `page_view`、主要操作で `ui_action` を送出。
- 開発時は `console.*` 可。ただし **リリースビルドで除去**（babel/tsconfig + ESLint ルール）。
- 例外は `window.onerror` / `unhandledrejection` を集約してレポート。

---

## 10. セキュリティ
- **危険な HTML 挿入禁止**（`dangerouslySetInnerHTML` は厳禁、やむを得ない場合はサニタイズ）。
- 秘匿値は **.env でクライアントへ配布しない**（公開前提の値のみ）。
- CSRF/Clickjacking 対策はバックエンドと連携（Origin/Referer 検証、`X-Frame-Options`）。
- 外部リンクは `rel="noopener noreferrer"` + `target="_blank"`。

---

## 11. パフォーマンス
- 画像最適化（`srcset`/`sizes`、遅延読込）。
- 大型依存の遅延読込（`import()`）と **ルート分割**。
- **再レンダリング計測**（React DevTools Profiler）を定期実施。
- リストは `key` を **安定 ID** に限定（インデックス禁止）。

---

## 12. i18n
- 文字列は **ハードコード禁止**。`t('page.home.title')` のようにキー管理。
- 数値/日付のローカライズは `Intl.*` を優先使用。

---

## 13. アクセシビリティ（最低限）
- 画像：`alt` 必須。装飾は空文字。
- フォーカスリングは **必ず可視**。`outline: none` 禁止。
- フォーム：`label` と `id` を関連付け。エラーはテキストで通知。
- キーボード操作：全操作を Tab/Enter/Space/矢印で可能に。

---

## 14. テスト方針
- **優先度**：ユニット（ロジック） > コンポーネント（主要 UI） > 統合（画面遷移/フォーム送信）。
- 命名：`<name>.test.tsx`。1 ファイル 1 コンポーネント。境界値を含む。
- カバレッジ目標：**Lines 80% / Branches 70%**（機能モジュールは 90%）
- モック：HTTP は **msw**。時間/乱数は固定化。

---

## 15. Git / PR / CI ルール
- ブランチ：`feat/<scope>`, `fix/<scope>`, `chore/<scope>`
- コミット：Conventional Commits（例：`feat(user): add avatar upload`）
- PR テンプレート（要約/スクショ/テスト観点/影響範囲/リリースノート）
- CI：`lint`→`typecheck`→`test`→`build` を直列。`main` マージで自動デプロイ。

---

## 16. Cursor / Claude Code 運用規約
### 16.1 プロンプト基本形（抜粋）
- **ガードレール**：
  - 「本規約（命名/構成/テスト/アクセシビリティ）を遵守せよ」
  - 「既存 API 型・フォルダ構造を変更しない」
  - 「不足要件は TODO コメントで明示し、人手タスクを列挙」
- **出力形式**：diff/patch かファイル全量のいずれかを指定。部分改変は **パッチ形式** を優先。
- **検証**：生成後に `eslint --fix` と `typecheck` を自動実行させる。

### 16.2 生成物レビュー
- 生成差分は **200 行超なら分割**。
- 変更理由を PR 説明に **要約**（Claude に要約させて良い）。
- 生成物に `AUTOGEN: <yyyy-mm-dd>` ヘッダコメントを付与（責務/前提/制限を記録）。

### 16.3 禁止事項
- 規約未満のコーディングスタイルを許可するプロンプト。
- ハードコードされた秘密情報/URL。ベース URL は `.env` から注入。
- ライブラリ大量追加（1 PR 1~2 つまで）。

---

## 17. 例：コンポーネント雛形（TypeScript + Tailwind）
```tsx
/**
 * AUTOGEN: 2025-08-23
 * Component: Button
 * Responsibility: アクションボタン（サイズ/バリアント切替、ローディング対応）
 */
import { ButtonHTMLAttributes, memo } from 'react';

type Variant = 'primary' | 'secondary' | 'ghost';
type Size = 'sm' | 'md' | 'lg';

export type ButtonProps = {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
} & ButtonHTMLAttributes<HTMLButtonElement>;

const base = 'inline-flex items-center justify-center rounded-lg font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2';
const variants: Record<Variant, string> = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300',
  secondary: 'bg-gray-100 text-gray-900 hover:bg-gray-200 disabled:bg-gray-200',
  ghost: 'bg-transparent text-gray-900 hover:bg-gray-100',
};
const sizes: Record<Size, string> = {
  sm: 'h-8 px-3 text-sm',
  md: 'h-10 px-4 text-sm',
  lg: 'h-12 px-6 text-base',
};

export const Button = memo(function Button({ variant = 'primary', size = 'md', loading = false, className = '', disabled, children, ...rest }: ButtonProps) {
  return (
    <button
      aria-busy={loading}
      disabled={disabled || loading}
      className={[base, variants[variant], sizes[size], className].join(' ')}
      {...rest}
    >
      {children}
    </button>
  );
});
```

---

## 18. ESLint/Prettier/Editor 設定（推奨）
### 18.1 .eslintrc.json（抜粋）
```json
{
  "root": true,
  "env": { "browser": true, "es2023": true, "node": true },
  "parser": "@typescript-eslint/parser",
  "plugins": ["@typescript-eslint", "react", "react-hooks", "import", "jsx-a11y"],
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
    "plugin:jsx-a11y/recommended",
    "plugin:import/recommended",
    "plugin:import/typescript",
    "prettier"
  ],
  "settings": { "react": { "version": "detect" }, "import/resolver": { "typescript": true } },
  "rules": {
    "react/react-in-jsx-scope": "off",
    "import/order": ["error", { "groups": [["builtin", "external"], ["internal"], ["parent", "sibling", "index"]], "alphabetize": { "order": "asc", "caseInsensitive": true }, "newlines-between": "always" }],
    "@typescript-eslint/explicit-module-boundary-types": "off",
    "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }]
  }
}
```

### 18.2 .prettierrc
```json
{ "singleQuote": true, "semi": true, "trailingComma": "all", "printWidth": 100 }
```

### 18.3 .editorconfig
```
root = true
[*]
charset = utf-8
end_of_line = lf
indent_style = space
indent_size = 2
insert_final_newline = true
trim_trailing_whitespace = true
```

---

## 19. PR テンプレート（.github/pull_request_template.md）
```
## 概要
- 変更の目的/背景

## 変更点
-

## 動作確認
- [ ] 主要フローが動作
- [ ] 画面読み上げ/キーボード操作
- [ ] レスポンシブ（sm/md/lg）

## テスト
- [ ] ユニット/コンポーネント追加・更新

## 影響範囲
-

## リリースノート
-
```

---

## 20. リリース判定チェックリスト
- [ ] ESLint/Prettier パス
- [ ] TypeScript 型エラー 0
- [ ] `loading/error/empty/success` の 4 状態 UI
- [ ] a11y 確認（フォーカス/alt/role/label）
- [ ] 主要パフォーマンス計測完了
- [ ] エラーロギング/監視にイベント追加

---

## 21. 付録：Claude/Cursor 向けプロンプト断片
```
あなたは React/TypeScript のシニアフロントエンド開発者です。以下の規約を厳守して変更を行ってください：
- ディレクトリ構成：src/features/<feature> 配下に api.ts/hooks/components/types.ts を作成
- スタイリング：Tailwind を使用、謎数値を避けて config のトークンを利用
- UI 状態：loading/error/empty/success の 4 状態を必ず実装
- a11y：aria-* を適切に付与し、フォーカスリングを保持
- テスト：msw を用いた API モック、境界値を含むユニット/コンポーネントテスト
不足情報は TODO コメントで明示し、PR 説明に列挙してください。
```

---

以上。

