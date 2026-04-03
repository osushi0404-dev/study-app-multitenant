# 計画書: I025 frontend ESLint no-unused-vars 警告の解消

## 基本情報
- **計画書ID**: plan_I025_ESLint_no-unused-vars警告解消
- **関連イシュー**: #52
- **作成根拠資料**: I019 振り返り（2026-04-03）
- **実装後評価**: （未作成）
- **作成日**: 2026-04-03

---

## 背景/目的

I019 の実装後、`@typescript-eslint/no-unused-vars` 警告が 13 ファイル・38 件残存していることが確認された。
未使用の import・変数はバンドルサイズの無駄・可読性の低下につながるため、削除する。

---

## 調査結果

### ESLint 警告件数（実測）

| ルール | 件数 |
|--------|------|
| `@typescript-eslint/no-unused-vars` | 38 件 |
| `@typescript-eslint/no-redeclare` | 1 件（`Monitoring.tsx` — `Alert` の二重定義） |
| **合計** | **39 件** |

### Jest ベースライン

- 2 suites, **7 passed, 0 failed**

### 警告一覧（ファイル別）

| ファイル | 対象 | 種別 |
|---------|------|------|
| `src/App.tsx:3` | `ThemeProvider`, `createTheme` | 未使用 import |
| `src/components/AIQuestionGenerator.tsx:29` | `SettingsIcon` | 未使用 import |
| `src/pages/Dashboard.tsx:26` | `Link` | 未使用 import |
| `src/pages/Login.tsx:10,19` | `Alert`, `toast` | 未使用 import |
| `src/pages/Monitoring.tsx:27,38,39` | `Fab`, `PeopleIcon`, `NotificationsIcon` | 未使用 import |
| `src/pages/Monitoring.tsx:76` | `Alert`（二重定義） | no-redeclare |
| `src/pages/QuizManagement.tsx:21,24,29,30,47,48,50,60` | `Alert`, `Switch`, `FormGroup`, `Divider`, `FilterList`, `Close`, `SmartToy`, `Choice` | 未使用 import |
| `src/pages/QuizSession.tsx:12,16-19,32,33,37,43,45` | `FormControl`, `Dialog`, `DialogTitle`, `DialogContent`, `DialogActions`, `Timer`, `QuestionAnswer`, `motion`, `AnimatePresence`, `Choice`, `SubmitAnswerData` | 未使用 import |
| `src/pages/QuizSession.tsx:164` | `completeSession` | 未使用変数 |
| `src/pages/Register.tsx:190` | `watch` | 未使用変数 |
| `src/pages/Statistics.tsx:24,32,51` | `Legend`, `TrendingUp`, `Assessment`, `StatisticsData` | 未使用 import |
| `src/pages/UserCreate.tsx:116` | `response` | 未使用変数 |
| `src/pages/UserManagement.tsx:56` | `loading` | 未使用変数 |
| `src/services/api.ts:167` | `data` | 未使用変数 |
| `src/services/auth.service.ts:8` | `TokenRefreshRequest` | 未使用 import |

---

## 受け入れ条件

- [ ] `@typescript-eslint/no-unused-vars` 警告が 0 件になること
- [ ] `@typescript-eslint/no-redeclare` 警告（`Monitoring.tsx`）が 0 件になること
- [ ] `tsc --noEmit` が exit 0 で通過すること
- [ ] Jest 7 passed, 0 failed（変化なし）

---

## 影響範囲

- Backend: なし
- Frontend: 上記 13 ファイル（import 削除・未使用変数削除のみ）
- DB: なし
- Config/Infra: なし

---

## 修正アプローチ

**未使用 import の削除**: 該当 import 名をimport 文から削除する。import 文の残りの名前がすべてなくなる場合は行ごと削除する。

**未使用変数の削除（代入系）**: `const xxx = await ...` のような代入は `const xxx =` 部分を削除し、式のみ残す（例: `await apiClient.post(...)`）。ただし、フックの戻り値の分割代入（`const { loading, setLoading } = useState()`）の場合は、未使用の変数名を削除して分割代入を整理する。

**`Monitoring.tsx` の `no-redeclare`**: `Alert` が MUI からの import（line 27 付近）とコンポーネント内での別定義（line 76）で二重になっている。import 側の `Alert` を削除することで解消する（コンポーネント内の定義が実際に使用されている方のため）。

---

## 変更点一覧

### 1. `src/App.tsx`
- `@mui/material` の import から `ThemeProvider`, `createTheme` を削除

### 2. `src/components/AIQuestionGenerator.tsx`
- import から `SettingsIcon` を削除

### 3. `src/pages/Dashboard.tsx`
- import から `Link` を削除

### 4. `src/pages/Login.tsx`
- `@mui/material` の import から `Alert` を削除
- `import { toast }` の行を削除（他に使用がない場合）

### 5. `src/pages/Monitoring.tsx`
- import から `Fab`, `PeopleIcon`, `NotificationsIcon` を削除
- `Alert`（MUI import）は削除しない（JSX で実際に使用されている）
- `interface Alert` → `interface MonitoringAlert` に rename
- `useState<Alert[]>` → `useState<MonitoringAlert[]>` に更新（2箇所）

### 6. `src/pages/QuizManagement.tsx`
- import から `Alert`, `Switch`, `FormGroup`, `Divider`, `FilterList`, `Close`, `SmartToy` を削除
- `Choice` 型の import を削除

### 7. `src/pages/QuizSession.tsx`
- import から `FormControl`, `Dialog`, `DialogTitle`, `DialogContent`, `DialogActions`, `Timer`, `QuestionAnswer` を削除
- `framer-motion` の import から `motion`, `AnimatePresence` を削除（他に使用がない場合は行ごと削除）
- `Choice`, `SubmitAnswerData` 型の import を削除
- `completeSession` の代入を削除（`const completeSession = ...` → 代入不要か、呼び出しのみ残す）

### 8. `src/pages/Register.tsx`
- `watch` の代入を削除（`const { ..., watch } = useForm(...)` から `watch` を除外）

### 9. `src/pages/Statistics.tsx`
- import から `Legend` を削除
- import から `TrendingUp`, `Assessment` を削除
- `StatisticsData` 型の import を削除

### 10. `src/pages/UserCreate.tsx`
- `const response = await ...` → `await ...`（代入を削除）

### 11. `src/pages/UserManagement.tsx`
- `const { loading, ... } = ...` から `loading` を除外、または `_loading` 等に変更せず削除

### 12. `src/services/api.ts`
- `const data = ...` → 代入を削除（式のみ残す）

### 13. `src/services/auth.service.ts`
- import から `TokenRefreshRequest` を削除

---

## 実装手順

1. 各ファイルを順番に修正（import 削除 → 変数削除）
2. 変数削除時は呼び出し式自体は保持し、代入のみ除去する（機能変更なし）
3. 全修正後、コンテナ内で ESLint・tsc を確認

---

## テスト計画

### 自動テスト
- `docker-compose exec frontend npx eslint src --format=compact 2>&1 | grep "no-unused-vars\|no-redeclare"` → 0 件
- `docker-compose exec frontend npx tsc --noEmit` → exit 0
- Jest: 7 passed

### 手動テスト
- 不要（機能変更なし・import 削除のみ）

---

## ロールバック

`git revert` で本コミットを取り消す。機能変更なしのため影響なし。

---

## Risk & 回避策

| リスク | 可能性 | 回避策 |
|--------|--------|--------|
| import 削除により実は使用されていた箇所が壊れる | 低（ESLint が未使用と判定済み） | tsc + Jest で確認 |
| `completeSession` の削除で将来実装の意図が消える | 低（未使用のため削除が正） | コミットメッセージに記録 |
| `Monitoring.tsx` の `interface Alert` rename で型不一致が起きる | 低（2箇所のみ修正） | tsc --noEmit で確認 |

---

## セキュリティ影響

セキュリティ影響なし（import 削除・未使用変数削除のみ、認証・認可・入力処理に変更なし）。

---

## 承認ポイント

### 設計判断の確認

| 判断事項 | 根拠 |
|---------|------|
| `completeSession` は代入を削除し、必要なら呼び出し式のみ残す | イシューに明記（削除のみ） |
| `Monitoring.tsx` の `Alert`: `interface Alert` を `interface MonitoringAlert` に rename（MUI Alert は JSX で使用中のため削除しない） | 実装時にファイルを読んで確認済み・ユーザー承認済み |
| `watch`（Register.tsx）: `useForm` の分割代入から除外 | イシューに明記（削除のみ） |

**`Monitoring.tsx` の `Alert` 対応は仮定が含まれます。** 修正前にファイルを読んで確認します。

### チェックリスト
- [ ] 未使用 import の削除のみ（機能追加・変更なし）
- [ ] 未使用変数は代入除去のみ（呼び出し式は保持）
- [x] `Monitoring.tsx` の `Alert` 対応方針（`interface MonitoringAlert` への rename）に同意
