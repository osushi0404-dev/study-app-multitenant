# React/TypeScript フロントエンド コーディング規約

このプロジェクト（マルチテナントの学習アプリの画面・React の SPA）でのコードの書き方の決まり。計画を書く工程・計画レビュー役・コードレビュー役が照合に使う。

- 書いてあるのは「このプロジェクトではこうする」という決まりと、よくある間違いの例だけ。一般的な書き方の解説は、各節の「参照」の公式の文書を読む
- あるべき姿を書いている。今のコードがまだ追いついていない決まりは §16 の移行のイシューで直す（どの決まりをいつから守るかは §16）
- 画面の使い勝手の原則（エラー・待ち・フォーム・移動）は `docs/runbooks/ux-rules.md`。この規約はコードの書き方を決める
- 決まりを変えるときは、前提の版と点検した日もあわせて見直す（I545）

## 0. 前提の版（点検した日: 2026-11-17）

方針: 長期サポート版（LTS）の区分がある道具は、公式がサポート中の最新の LTS。区分が無い道具は最新の安定版。前提の版どうしは、公式が組み合わせに対応をうたうものにする。

| 道具 | 前提の版 | 区分 | サポートの終わり | 出典 |
|---|---|---|---|---|
| Node.js | 26 | LTS（最新の Active LTS） | 2029-04-30 | https://nodejs.org/en/about/previous-releases ・ https://github.com/nodejs/release#release-schedule |
| React | 19.3 | 最新の安定版 | 公開の予定なし | https://registry.npmjs.org/react/latest ・ https://react.dev/blog/2024/12/05/react-19 |
| TypeScript | 7.0（`tsc`）＋6.x（API を使う道具用） | 最新の安定版。7.0 は API を持たないので、typescript-eslint などには 6.x を並べて入れる（公式の勧め） | 公開の予定なし | https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/ |
| Vite | 8.3 | 最新の安定版（Node.js ^20.19 か 22.12 以上） | 公開の予定なし | https://registry.npmjs.org/vite/latest |
| Vitest | 5.1 | 最新の安定版（Vite 6.4 以上・Node.js 22.12 以上） | 公開の予定なし | https://vitest.dev/guide/ |
| MSW | 3.0 | 最新の安定版（Node.js 22 以上） | 公開の予定なし | https://mswjs.io/docs/migrations/2.x-to-3.x |
| TanStack Query | 5.107 | 最新の安定版 | 公開の予定なし | https://registry.npmjs.org/@tanstack/react-query/latest |
| MUI（@mui/material） | 9.5 | 最新の安定版 | 公開の予定なし | https://registry.npmjs.org/@mui/material/latest |
| React Router | 8.5（`react-router` の包み） | 最新の安定版 | 公開の予定なし | https://reactrouter.com/start/declarative/installation |
| React Hook Form | 7.92 | 最新の安定版 | 公開の予定なし | https://registry.npmjs.org/react-hook-form/latest |
| Zod | 4.6 | 最新の安定版 | 公開の予定なし | https://registry.npmjs.org/zod/latest |
| @hookform/resolvers | 7.0 | 最新の安定版 | 公開の予定なし | https://registry.npmjs.org/@hookform/resolvers/latest |

ここに無い依存（axios・chart.js・react-hot-toast・Testing Library など）と、表の道具の小さな版は `frontend/package.json` の版に従い、Dependabot で上げる（`docs/runbooks/dependency-audit.md`）。今の環境との差は §16。

## 1. 使う道具（このプロジェクトではこれ）

| 用途 | 使うもの | 使わないもの |
|---|---|---|
| ビルドと開発のサーバー | Vite（React の公式が、枠組みを使わず作る SPA に勧めるビルドの道具の 1 つ） | Create React App（`react-scripts`。非推奨）・Next.js（API は Django が持つので SSR の枠組みは要らない） |
| 言語 | TypeScript（`strict`） | JavaScript のファイル |
| 部品とスタイル | MUI の部品と、その `sx`・`styled`・テーマ | Tailwind CSS・CSS Modules・部品ごとの素の CSS |
| サーバーの状態（API の値） | TanStack Query | `useEffect` の中での取得・SWR |
| 画面だけの状態 | `useState`・`useReducer`、画面全体で共有するものだけ Context（`contexts/`） | Zustand・Redux などの状態管理ライブラリ |
| 通信 | axios のインスタンス 1 つ（`services/api.ts`） | 部品からの直接の `fetch`・2 つ目の axios インスタンス |
| API の型 | `backend/openapi.yaml` から作った `types/api/schema.d.ts`（`types/api/index.ts` で短い名前を付ける・I493） | 手で書いた API の応答の型 |
| フォーム | React Hook Form＋Zod（`zodResolver`） | yup・手書きの検証 |
| ルーティング | React Router（`react-router` の包み・宣言型のモード） | `react-router-dom` の新しい import |
| グラフ | chart.js（react-chartjs-2。#516） | recharts |
| 通知（トースト） | `NotificationContext` 経由（中身は react-hot-toast） | 部品から直接 `toast()` を呼ぶ |
| 単体・部品のテスト | Vitest＋React Testing Library＋user-event 14 | Jest |
| API の差し替え（テスト） | MSW（通信の層で差し替える） | axios-mock-adapter・axios の中身の差し替え |
| 画面を通すテスト | Playwright（`e2e/`） | |

参照: https://react.dev/learn/creating-a-react-app ・ https://vite.dev/guide/

## 2. 構成と置き場所

| 置くもの | 場所 | 名前 |
|---|---|---|
| 画面（ルートに 1 対 1） | `src/pages/` | `PascalCase.tsx` |
| 部品 | `src/components/` | `PascalCase.tsx` |
| データ取得のフック・画面のフック | `src/hooks/` | `useXxx.ts` |
| API を呼ぶ関数 | `src/services/` | `xxx.service.ts`（通信の土台は `api.ts`） |
| 画面全体で共有する状態 | `src/contexts/` | `XxxContext.tsx` |
| API の型 | `src/types/api/`（作ったもの・手で直さない） | |
| 画面だけの型 | 1 つの部品だけが使う型（props など）はその部品のファイル。2 つ以上のファイルが使う型は `src/types/` | |
| 定数（道筋など） | `src/constants/`（例: `routes.ts`） | `UPPER_SNAKE_CASE` |
| 小さな関数 | `src/utils/` | `camelCase.ts` |
| テスト | 対象と同じフォルダの `__tests__/` | `*.test.ts(x)` |

- 同じ型・同じ定数を 2 か所に書かない。API の型は `types/api` から、画面の道筋は `constants/routes.ts` から読む

## 3. TypeScript

- `strict` を外さない。`any` を使わず、外から来た値は `unknown` で受けて型を確かめてから使う
- 状態は判別できる共用体で表す（`{ status: "loading" } | { status: "error"; error: Error } | ...`）
- 置き場所が分かっている型（API の応答）は推論させず、`types/api` の型を付ける
  ```ts
  // ❌ 悪い例: 手で API の応答の型を書く
  interface Overview { today: { study_time: number } }
  // ✅ 良い例: OpenAPI から作った型を使う
  import type { DashboardOverview } from '../types/api';
  ```
- 参照: https://www.typescriptlang.org/tsconfig/#strict

## 4. 部品

- 関数の部品で、props の型を引数に書く。`React.FC` は使わない（#510）
- `ref` は props として受け取る。新しい部品で `forwardRef` を使わない（React 19 から不要・将来廃止）
- 1 つの部品が 200 行を超えたら、表示の部品とフック（処理）に分ける
- 一覧の `key` は安定した ID にする。配列の添字を使わない
- props を 3 段以上受け渡しているときは、部品の分け方を見直す（Context に入れてよいのは §5 の 3 つだけ）
- 公式が非推奨にした API（例: `forwardRef`・`ReactDOM.render`）を使わない
  ```tsx
  // ❌ 悪い例
  const Card: React.FC<Props> = ({ items }) => items.map((x, i) => <Row key={i} item={x} />);
  // ✅ 良い例
  function Card({ items }: Props) {
    return items.map((x) => <Row key={x.id} item={x} />);
  }
  ```
- 参照: https://react.dev/reference/react/forwardRef ・ https://react.dev/learn/rendering-lists#keeping-list-items-in-order-with-key

## 5. 状態とデータ取得

- API の値は TanStack Query で持つ。取得は `hooks/useXxx.ts` にまとめ、部品は フックを呼ぶだけにする。`useEffect` の中で取得しない
- クエリのキーには、取得の関数が使う値（科目の ID・期間など）を全部入れる。同じキーと取得をいくつかの場所で使うときは `queryOptions` でまとめる
- 書き込み（`useMutation`）の後は、影響するキーを `invalidateQueries` で読み直す
- 利用者や組織が変わったら、キャッシュを捨てる（前の利用者・組織の値を見せない。由来: #491）
- 計算で出せる値は状態にしない（`useMemo` か、そのまま計算する）
- 画面全体で共有するのは認証・通知・テーマだけ（`contexts/`）。それ以外を Context に入れない
- 参照: https://tanstack.com/query/latest/docs/framework/react/guides/query-options ・ https://react.dev/learn/you-might-not-need-an-effect

## 6. 通信と API の受け渡し

- 通信は `services/api.ts` の axios のインスタンスだけを使う。認証のヘッダー・トークンの更新・エラーの形の変換はここに置く
- `services/*.service.ts` の関数は、`types/api` の型を返す
- サーバーのエラーの応答（形は Django 規約 §6）からの文は `utils/apiError.ts` の `extractApiErrorMessage` で取り出す。部品で応答の形を直接読まない
- 送る形（JSON か multipart か）は OpenAPI の定義に合わせる（由来: #460。画面が JSON で送り、API が multipart だけを受けて 415）

## 7. 表示の 4 つの状態

- データを出す画面は、読み込み中・失敗・空・データありの 4 つを必ず出し分ける（`hooks/queryLoadState.ts` の `toLoadState`）
- 失敗と空のときに何を見せるか（やり直しの操作・次にすることへの導線）は `docs/runbooks/ux-rules.md` §1・§5

## 8. フォーム

- React Hook Form＋Zod で書く。スキーマから型を作り（`z.infer`）、フォームの型を二重に書かない
- 検証の時機は `mode: 'onTouched'`（最初に欄を離れたときに確かめ、その後は入力のたびに確かめ直す。`docs/runbooks/ux-rules.md` §3）。既定の送信のときだけの確かめにしない
- サーバーの検証のエラーは `setError` でその項目に出す
- 送信中はボタンを `formState.isSubmitting` で止める（二重送信を防ぐ）
  ```tsx
  const schema = z.object({ email: z.email('メールアドレスの形で入力してください') });
  type FormValues = z.infer<typeof schema>;
  const { register, handleSubmit, formState } = useForm<FormValues>({
    resolver: zodResolver(schema),
    mode: 'onTouched',
  });
  ```
- 参照: https://react-hook-form.com/docs/useform#mode ・ https://zod.dev/

## 9. スタイル

- MUI の部品を使い、見た目は `sx` かテーマで変える。色・間隔はテーマの値（`theme.palette`・`theme.spacing`）を使い、色の値を直接書かない
- 画面の幅への対応は MUI の区切り（`sx={{ width: { xs: '100%', md: 480 } }}`）で書く（スマホの幅の決まりは `docs/runbooks/ux-rules.md` §6）
- 参照: https://mui.com/material-ui/customization/how-to-customize/

## 10. エラー処理と性能

- 描画の例外は、ルートごとの Error Boundary で受けて、やり直しの操作を出す
- 非同期の失敗は、クエリ・ミューテーションの `error` で受けて画面に出す。`catch` して何もしないことをしない
- `useMemo`・`useCallback`・`memo` は、重い計算か、測って遅い再描画があるときだけ使う
- 画面ごとに `lazy` で分けて読み込む。画像は `loading="lazy"` を付ける

## 11. セキュリティ

- `dangerouslySetInnerHTML` を使わない。どうしても要るときは計画書に理由を書き、DOMPurify で消毒してから使う
- トークンを localStorage・sessionStorage に置かない。アクセストークンはメモリに置き、リフレッシュトークンはサーバーが `HttpOnly` の Cookie で持つ（理由と出典は Django 規約 §10）
- 画面の環境変数（`VITE_` で始まるもの）は誰でも読める。秘密の値を入れない
- 新しいタブで開く外部のリンクには `rel="noopener noreferrer"` を付ける
- `console` に個人情報・トークンを出さない
- 参照: https://react.dev/reference/react-dom/components/common#dangerously-setting-the-inner-html

## 12. 日付の表示

- 「今日」・日ごとの集計の日付は、サーバーが返した値（日本時間の日付）を使う。画面の `new Date()` から日付を作らない（端末の時計・時差で 1 日ずれる。由来: #481）
- 日時の表示は `Intl.DateTimeFormat('ja-JP', { timeZone: 'Asia/Tokyo', ... })` で日本時間に直す

## 13. アクセシビリティ（コードの書き方）

- 目標の水準と、利用者から見た決まり（押す的の大きさ・キーボード操作・色だけで伝えない）は `docs/runbooks/ux-rules.md` §6。ここはコードの書き方
- 見た目でなく意味の要素を使う（ボタンは `button`・リンクは `a`・見出しは順番どおりの `h1`〜）。クリックできる `div` を作らない
- 入力欄にはラベルを結び付ける（MUI の `TextField` の `label`）。ラジオボタン・チェックボックスのまとまりには、見出しや問題文を名前として結び付ける（`FormControl`＋`FormLabel`・`RadioGroup` の `aria-labelledby`。由来: #536）
- アイコンだけのボタンには `aria-label` を付ける
- ダイアログは MUI の `Dialog` を使う（フォーカスの閉じ込めと Esc での閉じ方を持っている）
- 色はテーマの値を使い、明るさの比（`ux-rules.md` §6）を満たす組み合わせをテーマで決める
- 参照: https://mui.com/material-ui/react-radio-button/#accessibility

## 14. テスト

- Vitest＋React Testing Library で、利用者の操作と見えるものを確かめる。要素は `getByRole`（名前つき）で探し、`getByTestId` は最後の手段にする
- 操作は `userEvent.setup()` で作った user で行う（user-event 14）
- API は MSW で差し替える。`http`・`HttpResponse` は `msw/http` から、`setupServer` は `msw/node` から読む（MSW 3）。差し替えていない通信が出たらテストを落とす（`onUnhandledFrame: 'error'`）
  ```ts
  import { http, HttpResponse } from 'msw/http';
  import { setupServer } from 'msw/node';
  const server = setupServer(
    http.get('/api/dashboard/overview/', () => HttpResponse.json(overviewFixture)),
  );
  beforeAll(() => server.listen({ onUnhandledFrame: 'error' }));
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());
  ```
- 4 つの状態（§7）と、入力の誤り・サーバーのエラーの出し方をテストする
- 画面を通す流れ（ログイン・クイズ・記録）は Playwright の E2E（`e2e/tests/`）で確かめる
- バグを直すときは、そのバグを再現するテストを先に書く
- 参照: https://testing-library.com/docs/queries/about#priority ・ https://testing-library.com/docs/user-event/intro

## 15. 自動で止める範囲／レビューで見る範囲

自動で止める（pre-commit と CI）: ESLint・TypeScript の型チェック・依存の既知の脆弱性（`npm audit`）・OpenAPI と画面の型の食い違い（I493）。対象と止める水準は `docs/runbooks/pre-commit.md`・`docs/runbooks/dependency-audit.md` と各設定ファイルが正。この規約の決まりのうち機械で止められるもの（§1 の「使わないもの」の import・§4 の `React.FC` と添字の `key`・§11 の `dangerouslySetInnerHTML` など）を ESLint の規則にするのは §16 のイシュー。書いた内容と実際の設定の食い違いの点検は #520。

レビューで見る（計画レビュー役・コードレビュー役）: §4 の部品の分け方・§5 のデータ取得とキャッシュ・§7 の 4 つの状態・§11 のトークンと HTML の扱い・§12 の日付・§13 のアクセシビリティ・§14 のテストの有無。

## 16. 今のコードとの差（移行・直しのイシュー）

規約はあるべき姿を書いている。今のコードとの差は次のイシューで直す。下の表の差に当たる決まり（その行のイシューで入れる道具・版を前提にするもの）は、その行のイシューで直し、ほかのイシューでその道具・版を先に入れない。それ以外の決まりは、新しく書くコードから守る。

| 差 | イシュー |
|---|---|
| Node.js 18（画面〔`frontend/`〕のビルド・テスト・監査。E2E のジョブ〔`e2e/`・画面と別に動く〕は Playwright の要求に合わせて先に 26 にした・#432）・Create React App・Jest・user-event 13（§0・§1・§14） | #551 |
| React 18・TypeScript 4.9（§0・§4） | #560 |
| MUI 5（§0・§9） | #561 |
| React Router 6・`react-router-dom`（§0・§1） | #562 |
| yup（§1・§8） | #552 |
| トークンを localStorage に置いている（§11） | #553・#502 |
| テストの API の差し替えが axios-mock-adapter（§1・§14） | #511 |
| `React.FC` を使っている部品（§4） | #510 |
| recharts が残っている（§1） | #516 |
| ESLint の規則（§15） | #517〜#519 |
| 画面の `new Date()` から日付を作っている箇所（§12） | #481 |
