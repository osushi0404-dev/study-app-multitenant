# I487 計画書: ダッシュボードの状態ごとの表示・並び順・スマホ幅の崩れの修正

## 基本情報
- **計画書ID**: plan_I487
- **関連イシュー**: #487
- **Draft PR**: #507
- **作成根拠資料**: docs/issues/open/I487.md（GitHub #487 の本文の写し・2 回の grill-me の設計確認メモを含む）
- **実装後評価**: docs/reviews/open/I487_review.md
- **作成日**: 2026-11-13

## 1. 背景/目的
- ダッシュボード（`/dashboard`）は、データが無い・科目が無い・読み込み中・失敗の状態を設計しておらず、スマホ幅で横にはみ出し、主な行動（クイズ・復習）が下の方にある（イシューの「現状の問題」1〜9）
- 目的: 開いたら次にやることが分かり、スマホでも崩れず、どの状態でも誤解を生まない画面にする。あわせて I473 から回ってきた F9・F10・F11 と、答え 0 件のグラフの縦軸を直す

## 2. 受け入れ条件
イシューの受け入れ条件をそのまま使う（確かめる TC を右に書く。TC は `docs/tests/open/I487_auto_test.md`・手動は `docs/tests/open/I487_manual_test.md`）。
- [ ] 幅 390px で横にはみ出さず、「復習を始める」（今日の復習のカード）「クイズを始める」が画面の中にある。ほかの画面の幅が崩れない → TC-21・TC-22・手動 No.1・No.6
- [ ] 学習データ 0 件で、数字のカード 4 枚とグラフ 2 つの中にそれぞれ「まだ記録がありません」、赤いドーナツ・空のグラフの枠が出ない → TC-02
- [ ] 科目を選んでその科目の解答が 0 件なら、「間違いやすい分野」の一番上に「この科目はまだ解答がありません。まずは問題を解いてみましょう！」、その下に全科目の一覧。2 つの見出しに「（全科目）」 → TC-03
- [ ] 科目を選んでいるときの「クイズを始める」はダイアログを出さずその科目へ。「すべて」は今と同じ → TC-04
- [ ] 答え 0 件のとき推移のグラフの縦軸がマイナスにならない → TC-11
- [ ] 科目 0 件のユーザーに画面の中で「科目がまだ登録されていません。組織の管理者に科目の登録を依頼してください」（toast だけにしない・「設定画面から科目を追加」が出ない） → TC-05・TC-27
- [ ] 並び順「挨拶 → 科目の選択 → クイズを始める・今日の復習 → 数字のカード → グラフ → 間違いやすい分野・おすすめ → 統計を見る（小さなリンク）」 → TC-01・手動 No.1・No.2
- [ ] 読み込み中はスケルトン、科目を切り替えても画面全体が置き換わらない。MUI の範囲外の値の警告が出ない。初回表示で `GET /api/dashboard/overview/` が 1 回 → TC-07・TC-08・TC-24・TC-25
- [ ] 取得に失敗したらエラーの表示と再試行のボタン、押すと取り直す → TC-09
- [ ] 目標時間が設定の `daily_study_goal_minutes` に従い、設定画面で保存した値を読み戻せる → TC-10・TC-10d・TC-17・TC-28
- [ ] お知らせの記録がユーザーごとに分かれ、連続日数は同じ連続で 1 回（途切れて再び届けばもう一度）、解答数は越えた中で一番大きい未表示の節目を 1 回、正答率 95%・目標達成は 1 日 1 回 → TC-12〜TC-16
- [ ] 1440×900 の最初の画面に主な行動が入る → TC-23・手動 No.1
- [ ] 1440px・390px でアクセシビリティ設定のボタンがダッシュボードのボタン・グラフ・数字に重ならない → TC-19・TC-26・手動 No.1・No.2
- [ ] 画面確認（`docs/runbooks/frontend-verify.md`）でデスクトップ幅・スマホ幅の両方の記録がある → 手動の「画面確認」の表
- [ ] 既存の機能に退行が無い → CI（Jest・pytest・E2E）

## 3. 影響範囲
| 区分 | 内容 |
|---|---|
| Backend | `backend/core/openapi.py`（契約に `/api/settings/` を足す）・`backend/openapi.yaml`（作り直し・手で直さない）。API の振る舞い・シリアライザ・ビューは変えない（スパイクで注釈なしに警告 0 を確認済み） |
| Frontend | `pages/Dashboard.tsx`（作り直し）・新しい部品 `components/dashboard/*`・新しいフック `hooks/useDashboardOverview.ts`・`hooks/useUserSubjects.ts`・`hooks/useDailyStudyGoal.ts`・`hooks/useDashboardAchievements.ts`・`utils/dashboardAchievements.ts`・`pages/Settings.tsx`・`contexts/NotificationContext.tsx`・`services/dashboard.service.ts`・`services/types.ts`・`types/api/index.ts`・`types/api/schema.d.ts`（作り直し）・`components/Layout.tsx`・`components/AccessibilityProvider.tsx`・`components/TodayReviewCard.tsx`・テスト |
| E2E | `e2e/tests/dashboard-layout.spec.ts`（新規）・`e2e/tests/settings.spec.ts`（新規） |
| DB | なし |
| Config/Infra | なし（依存の追加なし。Dockerfile・compose への波及なし） |

## 調査結果
### 環境の前提（確認済み・2026-11-13）
- `docker compose ps`: backend・db・frontend・redis が running。backend は本ワークツリーの `backend/` を `/app` にマウント（`docker inspect`）。画面は `http://localhost:3020`（`docker compose port frontend 3000`）
- 型の作り直しの道具は `tools/api-types`（`docs/runbooks/common-commands.md`「API の形を変えたとき」）

### 問題 1（スマホ幅のはみ出し）の原因 — スパイクで特定
- **原因の概要**: 画面を広い幅で開いた後に狭くすると、グラフ（Chart.js）の canvas が広い幅のまま残り、共通の枠の `main` がそれより狭く縮めないため、中身全体が広がる
- **詳細**:
  1. Chart.js は親の幅に合わせて canvas の幅を px で書き込む（1440px のとき 728px）
  2. `Layout.tsx:219-225` の `main` は横並び（`display: flex`）の子で、`min-width` の既定値 `auto` のため、中身（728px の canvas）より狭くなれない
  3. 狭くしても `main` が 808px のまま（`scrollWidth` 808・幅 390）になり、Chart.js の大きさの見張り（ResizeObserver）も親が縮まないので canvas を縮めない
- **再現（Playwright MCP・e2e_user_a）**: 390px で直接開くと `scrollWidth` 390（はみ出さない）。1440px にしてから 390px にすると `scrollWidth` 808・`main` 808・canvas 728px（はみ出す）。2026-11-13 にイシューを起票したときの観測（約 808px）と一致
- **直し方の実証**: `main` に `min-width: 0` を足すだけで、同じ手順（1440 → 390）が `scrollWidth` 390・canvas 310px になった（グラフの親に `position: relative` を足さなくても直る）。Chart.js の公式の注意（グラフの入れ物は position: relative・グラフ専用にする）に合わせて、グラフの入れ物にも `position: relative` を付ける
- 設定画面ではみ出さなかったのは、広い固定の幅の要素（canvas）が無いため

### 問題 4（ちらつき・警告・2 回の呼び出し）の原因
- 読み込み中は画面全体を「読み込み中...」に置き換える（`Dashboard.tsx:198-204`）。そのたびに `SubjectSelector` が外れて付け直され、科目の一覧を取り直す間に今の値（例 `2`）が選択肢に無い状態になり、MUI が範囲外の値の警告を出す
- 初回の 2 回の呼び出しは、開発時の `React.StrictMode`（`frontend/src/index.tsx:11`）が effect を 2 回動かすため（2 回目の前に 1 回目の結果は捨てている）。CI の E2E も開発サーバーで動く（`quiz-session.spec.ts:54` の記載）
- `mountKey`（`Dashboard.tsx:67・75-78`）は、表示のたびにセレクタを付け直すだけで役割が無い

### 設定（目標時間）の項目名のずれ — 目標時間だけでなく全項目
- 裏側の `UserSettingsSerializer`（`backend/accounts/serializers.py:221-235`）の項目: `daily_study_goal_minutes`（既定 30・5〜480 の検証）・`study_reminders_enabled`・`reminder_time`（既定 `19:00:00`）・`theme_preference`（light/dark/auto）・`notification_settings`（JSON・既定 `{}`）
- 画面の手書きの型 `UserSettings`（`frontend/src/services/types.ts:156-165`）の項目: `daily_study_goal`・`study_reminder_enabled`・`study_reminder_time`・`theme`・`email_notifications`・`push_notifications`・`difficulty_preference` — **5 項目とも名前が合っていない**
- そのため設定画面（`Settings.tsx:121-149`）は読み込み時にどの値も `undefined` になり、yup の検証（目標時間・テーマ・通知の真偽値が必須）で保存できない。保存しても裏側は知らない項目を無視する（DRF の部分更新）。目標時間だけ名前を直しても、ほかの項目の検証で保存できず受け入れ条件「保存した値を読み戻せる」を満たせない
- 同じ型を `NotificationContext.tsx:60・94-97` も読む（リマインダーの有無・時刻・目標時間）。こちらも名前がずれていて、リマインダーが一度も組まれない
- `/api/settings/` は契約（`backend/core/openapi.py` の `CONTRACT_PATHS`）に入っていない。**スパイク（2026-11-13）**: 契約に `/api/settings/` を足したスキーマをメモリの上で作り、警告 0・エラー 0、GET・PUT・PATCH、`UserSettings` の 5 項目が出ることを確かめた（ファイルは書き換えていない）。ビュー・シリアライザへの注釈は要らない

### 達成のお知らせ
- 今の判定（`Dashboard.tsx:80-125`）: 連続日数は 7 の倍数、解答数は節目と**ちょうど同じ**ときに、応答のたびに出す（回数の制限なし・I473 F10）。正答率・目標達成は `localStorage` のユーザー共通のキーで 1 日 1 回
- `showAchievement`・`showStreakNotification`（`NotificationContext.tsx:126-136`）はブラウザの通知が許可されているときだけ出る
- 取得の effect の依存に `checkForAchievements` が入っている（I473 F11）

### アクセシビリティ設定のボタン
- `AccessibilityProvider.tsx:162-177` の丸いボタンは画面に固定（右下 `bottom: 80`）で、スクロールすると下にある中身に必ず重なる（位置を変えるだけでは、どの位置でもスクロールの途中に重なる）。ログイン後の画面には上のバー（`Layout.tsx:125-157`・ダークモードの切り替え・利用者のメニューがある）がある

### E2E の前提
- `e2e/playwright.config.ts`: 認証済みの既定は `e2e_user_a`（`.auth/user_a.json`）。`e2e_user_c`（科目 0 件の一般ユーザー）の `.auth/user_c.json` も global-setup が作る。CI の DB では組織 A に科目が 2 件（`quiz-session.spec.ts:10-13`）
- 既存の E2E（`quiz-session.spec.ts`）は「すべて」の状態で「クイズを始める」→ ダイアログ、を前提にしている。本計画は「すべて」のときの動きを変えないので影響しない

### 既存のテスト
- `frontend/src/pages/__tests__/Dashboard.test.tsx`（I473 の TC-20〜28）。TC-21・TC-26 は、本イシューの受け入れ条件で文言が変わる部分（「まだ解答の記録がありません」）を確かめている（下の「9. 確定事項と自律判断」）
- `Settings.tsx`・`NotificationContext.tsx`・`Layout.tsx`・`AccessibilityProvider.tsx` のテストは無い

### 軽い指摘の一覧（docs/reviews/backlog/）
- 実装対象のファイルに当たる行は無い。`FILE=-` の行（I224 F9・I223 B1〜B4）はハーネスの件で本イシューと関係ない（9. に記録）

## 4. 変更点一覧（具体）
### 4.1 スマホ幅のはみ出し（問題 1）
- **修正方針**: 共通の枠の `main` が中身より狭く縮めるようにする（原因そのものを直す）。グラフの入れ物も Chart.js の推奨の形にする
- `frontend/src/components/Layout.tsx` の `component="main"` の `sx` に `minWidth: 0` を足す（ほかの画面は、中身が枠より広いときに縮めるようになるだけで、広い画面での見た目は変わらない。手動 No.6 でほかの画面も見る）
- グラフの入れ物（下の `DashboardCharts.tsx`）に `position: 'relative'` を付ける

### 4.2 取得と状態のフック（React Query・2026-11-13 に自作の取得から置き換え）
- **修正方針**: API から取るデータ（数字・科目の一覧・設定）は、規約 6.3（非同期データは useQuery/SWR）に沿って、すでに入っていて `App.tsx` で設定済みの `@tanstack/react-query`（v5・`QueryClient` は `retry: 1`・`refetchOnWindowFocus: false`）の `useQuery` で取る。取得の重ね合わせ（開発時の StrictMode の 2 回の effect でも 1 回）・古い応答の破棄・再試行・キャッシュは React Query に任せ、自作しない。4 つの状態（読み込み中・失敗・データあり・データ無し）は、画面の部品が読みやすい形に写して返す
- クエリのキーはユーザーの id を含める（同じタブで別のユーザーで入り直したときに、前のユーザーのキャッシュを出さない）。キーは各フックのファイルで定数・関数として書き出す
- `frontend/src/hooks/useDashboardOverview.ts`（新規）
  ```ts
  type OverviewState =
    | { status: 'loading'; data: null }
    | { status: 'error'; data: null }
    | { status: 'success'; data: DashboardOverview };
  export const dashboardOverviewKey = (userId: string, subjectId: string) =>
    ['dashboard', 'overview', userId, subjectId] as const;
  export const useDashboardOverview = (userId: string, subjectId: string) => {
    const query = useQuery({ queryKey: dashboardOverviewKey(userId, subjectId), queryFn: ... });
    // 読み込み中 = 初回の取得中（isPending）か、失敗の後の取り直し中（isError && isFetching）
    return { ...state, retry: () => query.refetch() };
  };
  ```
  - `subjectId` が `'all'` なら `{}`、それ以外は `{ subject_id: subjectId }` で `dashboardService.getOverview` を呼ぶ（今と同じ）
  - 科目を切り替えるとキーが変わり、新しいキーは読み込み中（`isPending`）になる。前の科目の数字は出さない（`placeholderData` は使わない・C7）。古い応答は React Query がキーごとに分けるので、今の科目の表示を上書きしない（I473 F3）
  - `retry()` は `refetch()`。失敗の後の取り直しの間は読み込み中（スケルトン）として返す
  - 失敗の toast は出さず、画面の中の表示だけにする。`console.error` は `queryFn` の中で残す
- `frontend/src/hooks/useUserSubjects.ts`（新規）: `useQuery`（キー `['user-subjects', userId]`）で `SubjectService.getUserSubjects()` を取り、`{ status: 'loading' } | { status: 'error' } | { status: 'success'; subjects: Subject[] }` と `retry`（`refetch`）を返す。失敗を「科目 0 件」と取り違えない（失敗の toast はやめ、クイズのカードの中に出す）。引数は `userId`
- `frontend/src/hooks/useDailyStudyGoal.ts`（新規）: `useQuery`（キー `['user-settings', userId]`・`userSettingsKey` として書き出す）で `dashboardService.getUserSettings()` を取り、`daily_study_goal_minutes` が 1 以上の整数なら分の数、それ以外（失敗・欠け）は `null` を返す（`{ status: 'loading' } | { status: 'done'; minutes: number | null }`）。`null` のときは目標の表示を出さない（仮の値で埋めない・C7）。引数は `userId`
- `frontend/src/pages/Settings.tsx`: 保存に成功したら、PATCH の応答で設定のキャッシュを書き換える（`queryClient.setQueryData(userSettingsKey(user.id), updatedSettings)`。利用者が無いときだけ `invalidateQueries`）。古いことにするだけだと、ダッシュボードに戻ったときに取り直しが終わるまで古い目標で判定・表示してしまう（コードレビュー F7）。設定画面の読み込みは今のまま（`useQuery` への置き換えは #496 の範囲）
- テスト: 画面のテストは、テストごとに新しい `QueryClient`（`retry: false`）の `QueryClientProvider` で包む（テストの間でキャッシュを持ち越さない・失敗をすぐ出す）

### 4.3 部品に分ける（`Dashboard.tsx` は組み立てだけ・200 行以下）
- **修正方針**: 規約 5.3（200 行目安・ロジックはフック・繰り返しは部品）と 8.3（4 状態）に合わせる。見た目の部品は受け取った値を出すだけにする
- 新しい部品（`frontend/src/components/dashboard/`）:
  | ファイル | 役割 |
  |---|---|
  | `StartQuizCard.tsx` | 見出し「学習を開始」・目標の 1 行・「クイズを始める」・科目を選ぶダイアログ（今の `Dashboard.tsx:526-554` を移す） |
  | `DashboardStatCards.tsx` | 数字のカード 4 枚（今日の学習時間・連続学習日数・解答問題数・正答率） |
  | `DashboardCharts.tsx` | 直近 7 日の学習時間・正答率のグラフ（Chart.js の登録もここへ移す） |
  | `WeakSubjectsCard.tsx` | 間違いやすい分野（全科目） |
  | `RecommendationsCard.tsx` | おすすめ練習問題（全科目） |
  | `DashboardSkeleton.tsx` | 数字のカードとグラフの形のスケルトン |
- `frontend/src/pages/Dashboard.tsx`: 上のフックと部品を組み立てる。`mountKey` を消す。読み込み中に画面全体を置き換える分岐（`:198-204`）を消す

### 4.4 画面の並びと状態ごとの表示
上から次の順に置く（設計確認メモ・2 回目）。

| 順 | 中身 | 状態ごとの表示 |
|---|---|---|
| 1 | 挨拶 `おかえりなさい、{user_id または email}さん！`（`variant="h5"`・`component="h1"`・1 行。2 行目の「今日も学習を頑張りましょう 🚀」は消す。長い名前は折り返す `overflowWrap: 'anywhere'`） | — |
| 2 | 科目の選択（`SubjectSelector`・ラベル「科目を選択」・`xs=12 sm=6 md=3`） | 常に出す（外して付け直さない） |
| 3 | 横並び（`Grid` `xs=12 md=6`・スマホでは縦）: 左「クイズを始める」のカード（`StartQuizCard`）・右「今日の復習」のカード（`TodayReviewCard`・選択に従う。今と同じ） | 下の 4.5 |
| 4 | 数字のカード 4 枚（`xs=12 sm=6 md=3`） | 読み込み中: スケルトン／失敗: エラー（下）／`has_data` が false: 4 枚とも値の代わりに「まだ記録がありません」（見出しは残す・目標の進み具合のバーも出さない）／データあり: 今と同じ（目標は設定の値。下の 4.6） |
| 5 | グラフ 2 つ（`xs=12 md=8`・`xs=12 md=4`） | 読み込み中: スケルトン／`has_data` が false: どちらもグラフを描かず、見出しの下に「まだ記録がありません」（高さ 120px の枠の中央。300px の空の枠は出さない）／データあり: 推移のグラフの縦軸は 0 から（`scales.y.beginAtZero: true`・`ticks.precision: 0`） |
| 6 | 「間違いやすい分野（全科目）」「おすすめ練習問題（全科目）」（`xs=12 md=6`） | 読み込み中・失敗のときは出さない（今と同じ）。下の 4.7 |
| 7 | 「統計を見る」（MUI の `Link`＋`react-router-dom` の `Link`・`/statistics`・右寄せ・`variant="body2"`。大きなカード「詳細統計」はやめる） | 常に出す |

- **失敗のとき（4・5 の場所）**: `Alert severity="error"`（role="alert"）に「ダッシュボードの数字を読み込めませんでした」と、右側に「再読み込み」ボタン（`TodayReviewCard` の再試行の文言にそろえる）。押すと `retry()`。数字のカード・グラフは出さない（0 で埋めない・I473 TC-22 を保つ）
- **読み込み中（4・5 の場所）**: `DashboardSkeleton`（MUI の `Skeleton`。`data-testid="dashboard-skeleton"`・`aria-busy="true"`・見えない文字「ダッシュボードの数字を読み込み中」）。1〜3 と 7 はそのまま出し続ける（科目の切り替えで画面全体を置き換えない）。科目を切り替えた直後は、前の科目の数字を残さずスケルトンにする（別の科目の数字を今の科目の数字と見せない・C7）

### 4.5 「クイズを始める」のカード（`StartQuizCard`）
- 見出し「学習を開始」
- 目標の 1 行（`overview` があり、科目が 1 件以上で、目標 `goal` が `null` でないときだけ）: まだ届いていなければ「今日の目標達成まであと{goal - 今日の分}分です」、届いていれば「今日の目標（{goal}分）を達成しました！」。今日の分は `overview.today.study_seconds` を分に切り捨て（今と同じ）
- ボタン「クイズを始める」（`data-testid="start-quiz-button"`・`variant="contained"`・`size="large"`・`fullWidth`）:
  | 状態 | 動き |
  |---|---|
  | 科目の取得中 | 押せない（今と同じ） |
  | 科目の取得に失敗 | 押せない。カードの中に「科目を読み込めませんでした」と「再読み込み」ボタン（`useUserSubjects` の `retry`） |
  | 科目 0 件 | 押せない。カードの中に `Alert severity="info" role="status"`「科目がまだ登録されていません。組織の管理者に科目の登録を依頼してください」（リンクなし・toast は出さない） |
  | 科目を選んでいる（`'all'` 以外） | ダイアログを出さず `/quiz?subject={選んだ科目}` へ |
  | 「すべて」で 1 件 | `/quiz?subject={その科目}` へ（今と同じ） |
  | 「すべて」で 2 件以上 | 科目を選ぶダイアログ（今と同じ・文言と `aria-label` も同じ） |

### 4.6 目標時間（問題 5）
- 数字のカード「今日の学習時間」: `goal` があれば進み具合のバー（`今日の分 / goal`・100% で止める）と「目標: {goal}分 ({割合}%)」。`goal` が `null` ならバーと目標の行を出さない（「60」を出さない）
- `const dailyGoalMinutes = 60` を消す

### 4.7 間違いやすい分野・おすすめ（F9）
- 見出しを「間違いやすい分野（全科目）」「おすすめ練習問題（全科目）」にする
- 「間違いやすい分野」の中身:
  1. 科目を選んでいて `has_data` が false なら、一番上に「この科目はまだ解答がありません。まずは問題を解いてみましょう！」
  2. 続けて、一覧があれば今と同じ一覧（全科目）
  3. 一覧が空のとき: 1 を出していればそれだけ。「すべて」で `has_data` が false なら「データがありません。まずは問題を解いてみましょう！」（今と同じ）。それ以外は「5 問以上解いた科目のうち、正答率が 70% 未満の科目はありません」（今と同じ・I473 F4）
- おすすめ: 今と同じ（「練習する」で `/quiz?subject={id}`）

### 4.8 達成のお知らせ（問題 7・F10・F11）
- **修正方針**: 判定を純粋な関数に出し（日付と記録を引数で受ける）、取得の effect から切り離す。記録はユーザーごとのキー 1 つにまとめる
- `frontend/src/utils/dashboardAchievements.ts`（新規）
  ```ts
  export interface AchievementRecord {
    answeredMilestone: number;          // 出した解答数の節目の最大（0 = まだ）
    streakRuns: Record<string, string>; // 連続日数の節目 → その連続の始まりの日（YYYY-MM-DD）
    highAccuracyDate: string | null;    // 正答率 95% を出した日
    dailyGoalDate: string | null;       // 目標達成を出した日
  }
  export const ANSWER_MILESTONES = [10, 50, 100, 250, 500, 1000] as const;
  export const STREAK_STEP_DAYS = 7;
  export const HIGH_ACCURACY_RATE = 0.95;
  export const HIGH_ACCURACY_MIN_ANSWERED = 20;
  export const decideAchievements = (input: {
    overview: DashboardOverview; goalMinutes: number | null; today: string; record: AchievementRecord;
  }): { streakDays: number | null; messages: string[]; record: AchievementRecord } => ...
  export const achievementStorageKey = (userId: string) => `dashboardAchievements:${userId}`;
  export const loadRecord / saveRecord（localStorage。読めない・壊れた値は空の記録として扱う）
  ```
  - 連続日数: `streak.current_days` が 7 の倍数（0 を除く）のとき、その連続の始まりの日 = `today` の `current_days - 1` 日前。記録の同じ節目の始まりの日と違えば出す（同じ連続の間は 1 回。途切れて新しい連続で同じ節目に届けば始まりの日が変わるのでもう一度出す）
  - 解答数: `totals.answered_count` 以下の節目のうち一番大きいもの `m` が、記録の `answeredMilestone` より大きければ「{m}問解答達成！おめでとうございます！🎉」を 1 回出し、`answeredMilestone = m`（小さい未表示の節目はまとめて出したことにする）
  - 正答率: 今の条件（`accuracy_rate` が null でない・0.95 以上・解答 20 問以上）で、`highAccuracyDate !== today` なら出す
  - 目標達成: `goalMinutes` が `null` でなく、今日の分が `goalMinutes` 以上で、`dailyGoalDate !== today` なら出す
  - 文言は今と同じ
  - `today` は端末の日付（`YYYY-MM-DD`）。アプリの「今日」の日付のずれは #481 の範囲
- `frontend/src/hooks/useDashboardAchievements.ts`（新規）: 「すべて」の応答（`subjectId === 'all'` かつ `status === 'success'`）が来て、ユーザー（`useAuth().user.id`）と目標の取得が終わったら、`decideAchievements` を呼んで出し、記録を保存する。ユーザーが無ければ何もしない。お知らせの関数は `useRef` で持ち、effect の依存に入れない（F11）。取得の effect（`useDashboardOverview`）はお知らせを知らない
- 古いキー `lastHighAccuracyNotification`・`lastDailyGoalNotification` は、新しい記録を保存するときに `localStorage.removeItem` で消す（ユーザーの区別が無い古い記録を残さない）

### 4.9 設定の項目名を裏側にそろえる（問題 5・設定画面）
- **修正方針**: 手書きの型を直すのではなく、`/api/settings/` を契約に足して、作った型（#493 の仕組み）を使う。#493 で決めた「残りは触る画面のイシューで順に置き換える」に合わせる（#496 の対象のうち設定の分を本イシューで行う）
- `backend/core/openapi.py`: `CONTRACT_PATHS` に `'/api/settings/'` を足す
- `backend/openapi.yaml`・`frontend/src/types/api/schema.d.ts`: `docs/runbooks/common-commands.md` の手順で作り直す（手で直さない）
- `frontend/src/types/api/index.ts`: `export type UserSettings = Schemas['UserSettings'];`・`export type PatchedUserSettings = Schemas['PatchedUserSettings'];`（作られる名前は作り直しの後に確かめ、違えばその名前にする）
- `frontend/src/services/types.ts`: 手書きの `UserSettings`（`:155-165`）を消す
- `frontend/src/services/dashboard.service.ts`: `getUserSettings(): Promise<UserSettings>`・`updateUserSettings(settings: PatchedUserSettings)` を作った型にする
- `frontend/src/pages/Settings.tsx`:
  - 読み込み: `dailyStudyGoalMinutes ← daily_study_goal_minutes`・`studyRemindersEnabled ← study_reminders_enabled`・`reminderTime ← reminder_time` の先頭 5 文字（`HH:MM`）・`themePreference ← theme_preference`・`notificationSettings ← notification_settings`（真偽値でない・欠けたキーは `email: true`・`push: true`・`achievements: true`・`reminders: studyRemindersEnabled` を使う。`notification_settings` は型が `unknown` なので小さな読み取りの関数で確かめる）
  - 保存: `{ daily_study_goal_minutes, study_reminders_enabled, reminder_time, theme_preference, notification_settings }` を PATCH する
  - 画面の項目・文言・検証（5〜480 分など）は変えない
- `frontend/src/contexts/NotificationContext.tsx`: `study_reminders_enabled`・`reminder_time`・`daily_study_goal_minutes` を読む（リマインダーの文言は「今日の学習目標は{分}分です。一緒に頑張りましょう！」のまま）

### 4.10 アクセシビリティ設定のボタン（問題 9）
- **修正方針**: 画面に浮いた丸いボタンは、どの位置でもスクロールの途中で中身に重なる。ログイン後の画面では上のバー（ダークモードの切り替えの隣）に置き、浮いたボタンを出さない。ログイン前の画面（上のバーが無い）は今の丸いボタンのまま
- `frontend/src/components/AccessibilityProvider.tsx`:
  - 部品 `AccessibilityToggleButton`（`IconButton`・`aria-label="アクセシビリティ設定"`・`Tooltip`「アクセシビリティ設定 (Alt+A)」・アイコンは今と同じ）を出す。付いている間は、文脈の値 `headerButtonMounted` を true にする（`useEffect` で付けたとき true・外れたとき false）
  - `headerButtonMounted` が true の間は浮いた丸いボタンを出さず、設定のパネルを上のバーの下（`top: 72`・`right: 16`）に出す。false のときは今と同じ（丸いボタン・パネルは `bottom: 140`）
  - Alt+A・Esc の動きは変えない
- `frontend/src/components/Layout.tsx`: 上のバーのダークモードの切り替えの前に `AccessibilityToggleButton` を置く

### 4.11 今日の復習のカード
- `frontend/src/components/TodayReviewCard.tsx`: `Card` に `data-testid="today-review-card"` と `sx={{ height: '100%' }}`（横並びで高さをそろえる）を足す。動きは変えない

## 5. 実装手順（ステップ）
1. **はみ出しの直し（未知リスクを先に）**: 4.1。→ TC-21・TC-22（E2E は CI）・画面で 1440 → 390 を確かめる（手動 No.1）
2. **設定の契約と型（ステップ 3 の前提）**: 4.9 の backend（`CONTRACT_PATHS`・スキーマと型の作り直し）→ 型の置き換え（`services/types.ts`・`dashboard.service.ts`・`Settings.tsx`・`NotificationContext.tsx`）→ TC-17・TC-18・TC-28
3. **フックと達成の判定**: 4.2・4.8（`useDashboardOverview`・`useUserSubjects`・`useDailyStudyGoal`・`dashboardAchievements`・`useDashboardAchievements`）→ TC-08・TC-12〜TC-16。ステップ 2 の後（目標の型を使う）
4. **部品と並び**: 4.3〜4.7・4.11 → TC-01〜TC-07・TC-09〜TC-11・TC-23〜TC-25・TC-27。ステップ 3 の後
5. **アクセシビリティ設定のボタン**: 4.10 → TC-19・TC-26。ステップ 1〜4 と並行してよい
6. **既存のテストの更新と E2E の追加**: 下の 6. の表のとおり。ステップ 1〜5 の後
7. **画面確認**: `docs/runbooks/frontend-verify.md` の手順で手動 No.1〜No.6 → 手動テスト文書の「画面確認」の表に記録

## 6. テスト計画
### 自動（詳細は `docs/tests/open/I487_auto_test.md`）
| レベル | 置き場所 | 内容 |
|---|---|---|
| ユニット（Jest） | `frontend/src/utils/__tests__/dashboardAchievements.test.ts`（新規） | TC-12〜TC-15（節目・日付・ユーザーごと） |
| 結合（Jest＋RTL・API はモック） | `frontend/src/pages/__tests__/Dashboard.test.tsx`（追記） | TC-01〜TC-11・TC-16 |
| 結合（Jest＋RTL） | `frontend/src/pages/__tests__/Settings.test.tsx`（新規）・`frontend/src/contexts/__tests__/NotificationContext.test.tsx`（新規）・`frontend/src/components/__tests__/AccessibilityProvider.test.tsx`（新規） | TC-17・TC-18・TC-19 |
| E2E（Playwright・開発サーバー） | `e2e/tests/dashboard-layout.spec.ts`（新規）・`e2e/tests/settings.spec.ts`（新規） | TC-21〜TC-28（実際の幅・レイアウト・コンソール・通信） |
| backend（pytest） | 既存の `backend/core/tests/test_I493_openapi_contract.py` | TC-01（スキーマの作り直し忘れ）・TC-04（契約のパスだけ）がそのまま通る。新しいテストは足さない（項目名のずれは、作った型と型の検査〔typecheck〕・CI の `API Types Up To Date` が止める。設定の項目をテストに書き写すと「写しのテスト」になる・plan-writing-rules） |

- **既存の TC の扱い**（I473 の `Dashboard.test.tsx`）:
  - TC-21: 受け入れ条件で文言が「まだ解答の記録がありません」→「まだ記録がありません」（6 か所）に変わるので、期待値を新しい文言に直す。確かめる中身（赤い円を出さない・「データがありません。まずは問題を解いてみましょう！」）は保つ
  - TC-26: 同じ理由で「まだ解答の記録がありません」→「この科目はまだ解答がありません。まずは問題を解いてみましょう！」に直す。全科目の一覧（英語）が出ることは保つ
  - TC-27: 達成の記録が `localStorage` に残るようになるので、`beforeEach` で `localStorage.clear()` を足す（TC-20 の 12 問で 10 問の節目が記録され、TC-27 で出なくなるのを防ぐ）
  - TC-20・TC-22・TC-23・TC-25・TC-28: 変えずに通す（TC-22 の「エラーの文」は同じ文言を保つ。科目 0 件の案内は `role="status"` にして `findByRole('alert')` と重ならないようにする）
- **失敗の注入**（否定・不在・回帰の TC。実装時に一度だけ行い、結果を auto_test の結果欄に書く）: TC-08（React Query を使わず effect で取る形にすると 2 回・2026-11-13 の置き換えの後にやり直す）・TC-21/TC-22（`minWidth: 0` を外すと 1440 → 390 で `scrollWidth` が広がる。スパイクで 808 を確認済み）・TC-25（`SubjectSelector` を付け直す形に戻すと警告が出る）・TC-16（お知らせの関数を effect の依存に戻すと取得が 2 回）
- pytest・Jest・E2E は CI で流す（手元で全体を流し直さない）。実装中は関係するファイルだけを手元で流す

### 手動（`docs/tests/open/I487_manual_test.md`・実施者はすべて Claude・Playwright MCP）
- No.1 e2e_user_a・1440×900 → 390×844 に縮める（並び・はみ出し・重なり・最初の画面）
- No.2 e2e_user_a・390×844 で開く（並び・はみ出し・重なり）
- No.3 e2e_user_c・1440 と 390（科目 0 件の案内・押せないボタン・データ無しの表示）
- No.4 e2e_user_a で科目を切り替える（スケルトン・全体が置き換わらない・警告なし・通信 1 回）
- No.5 設定画面で目標時間を保存 → 再読み込み → ダッシュボードの目標の表示
- No.6 ほかの画面（設定・学習統計・問題管理）を 390px で開き、はみ出しが無く、1440px で見た目が変わらない

## 7. ロールバック
- PR を revert する（DB・データの変更なし）。`localStorage` の新しいキー `dashboardAchievements:{ユーザー}` は残っても害が無い（古い版は読まない）。消した古いキーは、古い版で次に達成したときにまた作られる
- `backend/openapi.yaml`・`schema.d.ts` も revert で元に戻る（CI の作り直し忘れのチェックと矛盾しない）

## 8. Risk & 回避策
| リスク | 回避策 |
|---|---|
| `main` の `minWidth: 0` がほかの画面の見た目を変える | 広い画面では中身が枠より狭いので変わらない。手動 No.6 で設定・学習統計・問題管理を 1440・390 で見る |
| 設定の項目名を直すと、通知を許可している人にリマインダー（既定は有効・19:00）が実際に組まれるようになる | 設定画面の「学習リマインダーを有効にする」の表示どおりの動きになるだけ（今は名前のずれで動いていない）。設定画面で切れる。レビュー文書の「自律判断の記録」に書き、close の報告で伝える |
| React Query のキャッシュで、古い数字・別のユーザーの値を出す | キーに科目とユーザーの id を入れ、`placeholderData` を使わない（科目を切り替えた直後はスケルトン）。設定は保存のときにキャッシュを古いことにする（TC-07・TC-09・TC-10d で確かめる） |
| アプリ全体の `retry: 1` で、失敗の表示が出るまで 1 回の取り直し（約 1 秒）待つ | アプリ全体の設定に合わせる（ほかの画面と同じ）。テストは `retry: false` で失敗をすぐ確かめる |
| 解答数の節目の初回: 今 300 問の人に、初めて開いたときに 250 問の節目が 1 回出る | 設計確認メモの決まりどおり（越えた中で一番大きい未表示の節目を 1 回）。それより小さい節目はまとめて出したことにするので、続けて出ない |
| `localStorage` が使えない（プライベートモードの制限など） | 読み書きの失敗は握りつぶして空の記録として扱い、画面を落とさない（お知らせが出すぎる側に倒れるが、表示は壊れない） |
| 上のバーのボタンが増えて、スマホの上のバーが窮屈になる | 390px の上のバー: メニュー・題名・アクセシビリティ・ダークモード・利用者のメニュー。題名は `noWrap` で省略される。手動 No.2 で崩れないことを見る |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ 1 回目・2 回目）:
- 並び順（挨拶 → 科目の選択 → クイズ・今日の復習 → 数字 → グラフ → 間違いやすい分野・おすすめ → 統計を見る）・科目の選択は画面全体の絞り込み・科目を選んでいるときの「クイズを始める」はダイアログなし
- データ 0 件の文言「まだ記録がありません」・科目 0 件の文言・選んだ科目の解答 0 件の文言・見出しの「（全科目）」
- お知らせの頻度の決まり（連続日数・解答数・正答率・目標）・記録をユーザーごとのキーにする・別の端末での再表示は許す
- 目標時間は `daily_study_goal_minutes`（既定 30）・設定画面の項目名を裏側にそろえる・目標を読めないときは目標の 1 行を隠す・グラフの縦軸は 0 から・F11 の直し・スマホ幅の直しを本イシューで行う・型は #493 の作った型を使う
- 科目 0 件の人には画面の中の案内（リンクなし）。自分で科目を選ぶ画面は #494

Claude が決めた（技術・細部と理由）:
- **はみ出しの直し方**: `Layout.tsx` の `main` に `minWidth: 0`。理由: スパイクで原因（flex の子の `min-width: auto`）を特定し、これだけで直ることを確かめた。ダッシュボードの側で幅を抑える回避より原因を直すほうが、ほかの画面の同じ問題も防げる
- **設定の型を作った型に置き換え、全 5 項目の名前をそろえる**（イシューは目標時間の名前だけを挙げていた）: 理由: 5 項目とも名前がずれていて、目標時間だけ直しても検証で保存できず受け入れ条件を満たせない（イシューの目的の穴なのでこの PR で直す）。#493 の決定（触る画面で順に置き換える）に合わせ、手書きの型を直すのでなく契約に足す。#496 の設定の分を先に行うことになるので、retro で #496 に書く
- **`backend/core/openapi.py` に 1 行足す**（イシューの影響範囲は「Backend なし」）: 理由: 上の置き換えの仕組みの一部。API の振る舞いは変わらない（スパイクで注釈なしに警告 0）
- **リマインダーが実際に動くようになる**（`NotificationContext.tsx` の名前の直し）: 理由: 設定画面の表示どおりの動きに直すだけで、新しい機能ではない
- **取得のしくみ**: React Query（`useQuery`）を使う（2026-11-13 に自作の取得から置き換え）。理由: 規約 6.3 が非同期データに useQuery/SWR を求め、`@tanstack/react-query` はすでに入っていて `App.tsx` で設定済み（どの画面もまだ使っていなかった）。StrictMode での 1 回の取得・古い応答の破棄・再試行・キャッシュを自作せずに済む。最初の計画で「新しいライブラリを入れるほどではない」と書いたのは、入っていることを確かめなかった誤り
- **失敗の toast をやめ、画面の中だけで伝える**（ダッシュボードの数字・科目の一覧）: 理由: ux-rules「コンテキスト維持・明確な次のアクション」。同じことを 2 か所で伝えない
- **科目の一覧の取得に失敗したときの表示**（「科目を読み込めませんでした」＋「再読み込み」）: 理由: 失敗を「科目 0 件」と取り違えて誤った案内を出さない（C7）。文言は今日の復習のカードの失敗の表示にそろえた
- **科目 0 件のときは「クイズを始める」を押せなくし、カードの中に案内を出す**（grill-me の 3 回目の返答で伝えた）・案内は `role="status"`（急ぎの警告ではない）
- **科目を切り替えた直後は前の科目の数字を残さずスケルトン**: 理由: 別の科目の数字を今の科目の数字と見せない（C7）
- **目標の 1 行の文言**: 届いたときは「今日の目標（{goal}分）を達成しました！」（今の「あと0分です」を避ける）
- **達成の判定の形**（純粋な関数＋ユーザーごとの 1 キー・古いキーの削除）: 理由: 日付と記録を引数にするとテストで日付を差し替えずに済む（設計で検証しやすくする）
- **アクセシビリティ設定のボタンを、ログイン後の画面では上のバーに移す**（イシューの自律判断「位置か下の余白で重なりを解消」の範囲）: 理由: 浮いたボタンはどの位置でもスクロールの途中で重なり、受け入れ条件「重ならない」を位置の調整だけでは満たせない。上のバーにはダークモードの切り替えという同じ種類の操作がある。ログイン前の画面は上のバーが無いので今の丸いボタンのまま
- **ファイルの置き場所**: 部品は `frontend/src/components/dashboard/`、フックは `frontend/src/hooks/`、判定は `frontend/src/utils/`。理由: 今のリポジトリの構成（`components/`・`hooks/`・`utils/`）に合わせる（`features/` の構成は使っていない）
- **E2E の新しい spec を 2 つに分ける**（`dashboard-layout.spec.ts`・`settings.spec.ts`）: 理由: 画面の幅・並びの確かめと、設定の保存（`e2e_user_c` の値を書き換える）を分ける。設定の E2E は今の値と違う値（45 か 50）を保存して読み戻すので、何度流しても通る
- **新しい backend のテストを足さない**: 理由は 6. の表
- 一覧（docs/reviews/backlog/）: 実装対象のファイルに当たる行は無い。`FILE=-` の行 — 一覧 I224.md F9: 残す — ハーネスの効果測定で本イシューと無関係／一覧 I223.md B1〜B4: 残す — bot の停止の後始末で本イシューと無関係

要件・UI の仮定でユーザーに確認が要るもの: なし（UI の配置・文言・操作の流れは 2 回の grill-me で決まり、細部はユーザーの指示「BP・UI/UX の観点で問題ないやり方で進めて」の範囲で上に記録した）

要件適合性・業務ロジック:
- 受け入れ条件を超える仕様の追加は、上の「Claude が決めた」に挙げたもの（設定の全項目の名前・アクセシビリティのボタンの場所・科目の取得失敗の表示・目標達成の文言）だけ。どれも受け入れ条件を満たすため、または失敗を誤解させないための最小限
- マルチテナント: 閲覧範囲は変えない。ダッシュボード・設定・科目の API は今のまま利用者本人（組織で絞った）のデータだけを返す（`build_overview`・`UserSettingsView.get_object` は `request.user`）。画面は受け取った値を出すだけ
- エッジケース: 科目 0 件・科目の取得失敗・設定の取得失敗・データ 0 件・選んだ科目だけ 0 件・解答数の節目の飛び越し・連続の途切れ・ユーザーの切り替え・`localStorage` が使えない（8.）

セキュリティ・ベストプラクティス:
- 入力: 設定の値の検証は今のまま（画面の yup 5〜480・裏側の `validate_daily_study_goal_minutes`）。`notification_settings` は真偽値だけを読み取る
- 認証・認可: 変更なし（`IsAuthenticated`・本人のデータだけ）
- 機密データ: `localStorage` に置くのは、ユーザーの ID（UUID）をキーにした節目の数と日付だけ。個人情報・トークンは置かない
- XSS: 表示は React の文字の出力だけ（`dangerouslySetInnerHTML` は使わない）。科目名は今と同じく文字として出す
- 依存: 追加なし（npm audit・pip-audit の対象は変わらない）。重大度の基準は bandit MEDIUM 以上・npm audit high/critical（変更なし）

P3/P5/P8（データ整合性・運用・コスト）: 影響なし（DB・外部 API・非同期処理・インフラの変更なし）
P9（プライバシー）: 影響なし（新しい個人情報・テナントデータの扱いなし。`localStorage` の中身は上のとおり）

Danger Ops（有無/手順/ロールバック）:
- 無（E2E が `e2e_user_c` の目標時間を書き換えるのは E2E 用の DB だけ）

## 13. 性能・UX設計
### 性能
- 初回の通信: overview 1 回・科目の一覧（ダッシュボード 1 回＋`SubjectSelector` の 1 回は今のまま）・設定 1 回（`NotificationContext` も今のまま 1 回）・今日の復習 1 回。N+1 は無い。overview のクエリ数は I473 の 9 本のまま（裏側は変えない）
- 再描画: お知らせの関数を ref で持ち、取得を余計にやり直さない（F11）

### 現在の UX 課題
- イシューの「現状の問題」1〜9

### 改善後のユーザー体験
1. 開くと、挨拶・科目の選択・「クイズを始める」「今日の復習」がすぐ見える（1440×900 でもスマホでも最初の画面）
2. 数字とグラフはスケルトンの後に出る。記録が無ければ「まだ記録がありません」
3. 科目を選ぶと、数字・グラフ・今日の復習がその科目になり、「クイズを始める」はその科目ですぐ始まる
4. 下に苦手な科目とおすすめ（全科目）、一番下に「統計を見る」

### エラー・例外時の体験
- 数字の取得に失敗: その場所に「ダッシュボードの数字を読み込めませんでした」と「再読み込み」。上の挨拶・科目の選択・クイズ・今日の復習は使える
- 科目の一覧の取得に失敗: クイズのカードに「科目を読み込めませんでした」と「再読み込み」
- 科目 0 件: クイズのカードに管理者への依頼の案内（押せないボタン）
- 設定の取得に失敗: 目標の表示だけを隠す（ほかは出す）

### アクセシビリティ
- スケルトンは `aria-busy` と見えない文字で読み込み中を伝える。失敗は `role="alert"`、科目 0 件の案内は `role="status"`
- 上のバーのアクセシビリティ設定のボタンは `aria-label`・`Tooltip`・Alt+A を保つ。ボタンの大きさは 44px 以上（`IconButton` の既定 40px に `size="large"` で 48px）
- 見出しの階層: 挨拶を `h1`、カードの見出しを `h2`（今の `h6` の見た目のまま `component="h2"`）
- 破壊的な操作は無い（削除などの確認の導線は不要）

### 成功指標
- 受け入れ条件の TC がすべて通ること（E2E の幅・並び・通信の回数・警告なし）

## 計画変更記録
- 2026-11-13 計画レビュー（20261113_1632）の Warning 2・Info 1 への対応: 4.2 の使い回しのキーにユーザーの id を入れる・手動 No.5 に元の値の記録を足す・auto_test の TC-27/TC-28 に共有ユーザーの前提を 1 行足す。計画レビューのやり直し: 不要（findings への対応の追記だけで、方式・範囲・受け入れ条件は変えない）
- 2026-11-13 implement: E2E の幅の確かめ（TC-21〜23・26）は `page.route` で overview の応答を固定する。計画の記載は「`stat-answered-count` が出た後」だったが、E2E の利用者は種データを流すたびに作り直されて解答 0 件から始まり、グラフ（canvas）が描かれない（はみ出しの原因の再現に canvas が要る）。共有の利用者に解答を足すと `quiz-session.spec.ts` の「1 増える」と干渉するので、応答の固定を選んだ。通信の回数（TC-24）・科目の切り替え（TC-25）・科目 0 件（TC-27）は本物の API のまま。計画レビューのやり直し: 不要（確かめ方の手段の変更で、確かめる中身と受け入れ条件は変えない）
- 2026-11-13 implement: 既存の E2E `e2e/tests/quiz-session.spec.ts` の「解答問題数が 1 増える」を、数字が無い（「まだ記録がありません」）ときは 0 として読むように直す。計画の 4.4 で解答 0 件のときに数字の代わりに文を出すので、この spec が先頭で流れると数字を待って落ちるため（変更点の消費箇所の取りこぼし）。計画レビューのやり直し: 不要（受け入れ条件「既存の E2E が通る」を保つための追従）
- 2026-11-13（マージの前・ユーザーの指示「React Query に置き換えて進めて」）: 取得の 3 つのフックを、自作（進行中の Promise の使い回し・`useEffect` と `ignore`）から React Query の `useQuery` に置き換える（4.2 を書き直し）。きっかけは、マージの前の BP の確かめで、規約 6.3 と、`@tanstack/react-query` がすでに入って設定済みであることを見つけたこと（最初の計画で確かめていなかった）。画面の見た目・動き・受け入れ条件は変えない。あわせて、設定の保存のときに設定のキャッシュを古いことにする（`Settings.tsx`）・テストを `QueryClientProvider` で包む。計画レビューのやり直し: 要（方式を変える）
- 2026-11-13 implement: `useDashboardOverview` は、結果にどの取得（ユーザーと科目）の結果かを持たせ、今の科目と違えば読み込み中として返す。4.2 の「科目を切り替えた直後は前の科目の数字を残さずスケルトン」を effect の実行の順に頼らず確実にするため。計画レビューのやり直し: 不要（4.2 の方式の中の書き方）
- 2026-11-13 implement（/simplify の指摘）: `frontend/src/components/SubjectSelector.tsx` の見出し（`InputLabel`）を `useId` の id と `labelId` で選択欄に結び付ける（計画の変更点に無かったファイル）。選択欄の名前が無く、読み上げで「科目を選択」と伝わらず、E2E（TC-25）も名前なしで探す回避をしていたため。見た目・動きは変えない（学習統計の画面の科目の選択も同じく名前が付く）。計画レビューのやり直し: 不要（アクセシビリティの付け足しで、方式・範囲・受け入れ条件は変えない）
- 2026-11-13 implement: 達成の記録の `streakRuns` の読み書きは `Map` を通す（ESLint の `security/detect-object-injection` の警告を出さないため）。設定画面の `notification_settings` の読み取りも同じ理由で `Object.entries` を使う。計画レビューのやり直し: 不要
- 2026-11-13 fix-loop（コードレビュー F7）: 設定の保存のときのキャッシュの扱いを `invalidateQueries` から `setQueryData`（保存の応答で書き換え）に変えた（4.2）。診断: `docs/reviews/I487_fix_diagnosis_20261113_1824.md`（案 A・診断レビュー PASS）。計画レビューのやり直し: 不要（findings への対応で、方式・範囲・受け入れ条件は変えない）
- 2026-11-13 fix-loop（コードレビュー F10）: 設定のキャッシュを書き換える前に、同じキーの進行中の取得を `cancelQueries` で止める（4.2・`Settings.tsx`）。保存の前に始まった取得の古い応答が上書きしないため。診断: `docs/reviews/I487_fix_diagnosis_20261113_1839.md`（案 A・診断レビュー PASS）。計画レビューのやり直し: 不要（findings への対応）

## レビュー結果
- [20261113_1805 判定: ✅ 完了](../../reviews/I487_plan_review_20261113_1805.md)
- [20261113_1632 判定: ✅ 完了](../../reviews/I487_plan_review_20261113_1632.md)
