# I487 自動テスト: ダッシュボードの状態ごとの表示・並び順・スマホ幅の崩れの修正

実行コマンド（例）: `docker compose exec frontend npm test -- --watchAll=false src/pages/__tests__/Dashboard.test.tsx` / `docker compose --profile e2e run --rm e2e npx playwright test tests/dashboard-layout.spec.ts --retries=0`

- 全体（pytest・Jest・E2E）は CI が PR ごとに流す。手元では実装中に関係するファイルだけを流す
- 計画書: `docs/plans/open/plan_I487.md`（TC と受け入れ条件の対応は計画書の「2. 受け入れ条件」）

結果:
- backend: 手元では流していない（既存の `core/tests/test_I493_openapi_contract.py` を CI で流す。スキーマは `manage.py spectacular --validate --fail-on-warn` で作り直し、警告 0）
- frontend（2026-11-13・手元・関係するファイルだけ）: `Dashboard.test.tsx` 27 件・`dashboardAchievements.test.ts` 4 件・`Settings.test.tsx` 1 件・`NotificationContext.test.tsx` 2 件・`AccessibilityProvider.test.tsx` 3 件・`TodayReviewCard.test.tsx` 7 件 すべて合格。`npm run typecheck` 合格・変えたファイルの ESLint 0 件
- e2e（2026-11-13・手元の e2e コンテナ・`--retries=0`）: `dashboard-layout.spec.ts` 7 件・`settings.spec.ts` 1 件・`quiz-session.spec.ts` 3 件 すべて合格

## 共通の前提（Jest）
- `Dashboard.test.tsx` の既存のモック（`services/api`・`SubjectService`・`SubjectSelector`・`TodayReviewCard`・`react-chartjs-2`・`AuthContext`〔`user: { id: 'user-1', user_id: 'u_i473' }` に `id` を足す〕・`NotificationContext`）を使う
- `beforeEach` で `localStorage.clear()`
- 描くときは、テストごとに新しい `QueryClient`（`defaultOptions.queries.retry: false`）の `QueryClientProvider` で包む（2026-11-13 の React Query への置き換えから。テストの間でキャッシュを持ち越さない・失敗をすぐ出す）
- 設定 API（`/api/settings/`）の応答は、TC ごとに `mockGet` の URL の分岐で返す（指定の無い TC は `{ data: {} }` ＝ 目標なし）
- `overview()` は既存のひな形（has_data true・今日 330 秒・連続 2 日・解答 12・正答率 0.75・苦手 英語・おすすめ 数学）

## TC 一覧

### Dashboard（`frontend/src/pages/__tests__/Dashboard.test.tsx` に追記）
| TC | 内容 | 期待値 |
|---|---|---|
| TC-01 | 並び順 | 次の要素が文書の中でこの順に並ぶ（`compareDocumentPosition` の `DOCUMENT_POSITION_FOLLOWING`）: 見出し（`role=heading` level 1）「おかえりなさい、u_i473さん！」→ 科目の選択（モックのボタン「科目5を選ぶ」）→ `start-quiz-button` → 「今日の復習のカード」→ `stat-answered-count` → 見出し「直近 7 日の学習時間」→ 見出し「間違いやすい分野（全科目）」→ 見出し「おすすめ練習問題（全科目）」→ リンク「統計を見る」（`href="/statistics"`）。文字「今日も学習を頑張りましょう」と見出し「詳細統計」が無い |
| TC-02 | データ 0 件（すべて） | `has_data: false`・数字 0・`last_7_days` すべて 0 の応答で、「まだ記録がありません」がちょうど 6 個（`getAllByText` の長さ 6）。`line-chart`・`doughnut-chart` が無い。「目標:」の文字・`role=progressbar` が無い。「データがありません。まずは問題を解いてみましょう！」がある |
| TC-03 | 選んだ科目だけ 0 件 | 「すべて」は `overview()`、`subject_id=5` は `has_data: false` の応答。「科目5を選ぶ」の後、「この科目はまだ解答がありません。まずは問題を解いてみましょう！」があり、その後ろ（`DOCUMENT_POSITION_FOLLOWING`）に「英語」がある。「5 問以上解いた科目のうち…」「データがありません。まず…」が無い。苦手の一覧が空（`weak_subjects: []`）の科目 0 件の応答では、案内の文だけがあり「5 問以上解いた科目のうち…」が無い |
| TC-03b | 選んだ科目だけ 0 件で一覧も空 | 案内の文だけがあり、「5 問以上解いた科目のうち…」が無い（TC-03 の後半を別の TC に分けた） |
| TC-04 | 「クイズを始める」の行き先 | (a) 科目 2 件（id 5・6）・選択「すべて」→ 押すと `role=dialog` が出て、`navigate` は呼ばれない。(b) 科目 2 件・「科目5を選ぶ」の後 → 押すとダイアログが出ず `navigate('/quiz?subject=5')`。(c) 科目 1 件（id 7）・「すべて」→ `navigate('/quiz?subject=7')` |
| TC-05 | 科目 0 件 | `getUserSubjects` が `[]`。`role=status` の中に「科目がまだ登録されていません。組織の管理者に科目の登録を依頼してください」。`start-quiz-button` が `disabled`。`toast.error` が呼ばれない。「設定画面から科目を追加」の文字が無い。「今日の目標達成まで」の文字が無い |
| TC-06 | 科目の一覧の取得に失敗 | `getUserSubjects` が reject。クイズのカードに「科目を読み込めませんでした」とボタン「再読み込み」、`start-quiz-button` が `disabled`、「科目がまだ登録されていません」が無い。2 回目は `[{ id: 7, name: '数学' }]` を返すようにして「再読み込み」（クイズのカードの中のもの）を押すと、`start-quiz-button` が押せるようになり、「科目を読み込めませんでした」が消える |
| TC-07 | 読み込み中と科目の切り替え | overview の応答を手で解決する Promise にする。初回: `dashboard-skeleton` があり、見出し「おかえりなさい、u_i473さん！」・`start-quiz-button`・「科目5を選ぶ」がある。解決すると `stat-answered-count` が「12」になり、スケルトンが消える。「科目5を選ぶ」を押すと、`stat-answered-count` が消えて `dashboard-skeleton` が出る間も、見出し・`start-quiz-button`・「今日の復習のカード」が出たまま（同じ DOM の要素〔押す前に取った参照と `toBe` で同じ〕）。文字「ダッシュボードを読み込み中...」が出ない |
| TC-08 | StrictMode で 1 回（React Query が同じキーの取得を重ねる） | `<React.StrictMode><Dashboard /></React.StrictMode>` を描き、`stat-answered-count` が「12」になった後、`mockGet` の `'/api/dashboard/overview/'` への呼び出しがちょうど 1 回 |
| TC-09 | 取得の失敗と再試行 | 1 回目の overview は reject、2 回目は `overview()`。`role=alert` に「ダッシュボードの数字を読み込めませんでした」とボタン「再読み込み」。`toast.error` が呼ばれない。押すと overview の呼び出しが 2 回になり、`stat-answered-count` が「12」、`role=alert` が無くなる |
| TC-10 | 目標時間 | (a) 設定の応答 `{ daily_study_goal_minutes: 45 }`（今日 330 秒 = 5 分）: 「目標: 45分 (11%)」と「今日の目標達成まであと40分です」があり、「60」を含む「目標: 60分」が無い。`role=progressbar` の `aria-valuenow` が「11」（MUI の `LinearProgress` は渡した値 `5/45*100` を丸めて出す）。(b) 今日 2700 秒（45 分）: 「今日の目標（45分）を達成しました！」。(c) 設定の取得が reject: 「目標:」「今日の目標達成まで」の文字が無く、`role=progressbar` が無い。「5分」は出る |
| TC-11 | グラフの縦軸 | `react-chartjs-2` の `Line` のモックが受け取った `options` を保存し、`options.scales.y.beginAtZero === true`・`options.scales.y.ticks.precision === 0` |
| TC-16 | お知らせの関数が変わっても取り直さない（F11） | `useNotifications` のモックが描くたびに新しい関数を返すようにする（`jest.fn()` を毎回作る）。`stat-answered-count` が「12」になった後、`rerender(<Dashboard />)` を 2 回しても、overview の呼び出しが 1 回のまま |

### 達成の判定（`frontend/src/utils/__tests__/dashboardAchievements.test.ts`・新規）
`decideAchievements` を直接呼ぶ（日付と記録は引数で渡す。時刻の差し替えはしない）。空の記録 = `{ answeredMilestone: 0, streakRuns: {}, highAccuracyDate: null, dailyGoalDate: null }`。
| TC | 内容 | 期待値 |
|---|---|---|
| TC-12 | ユーザーごとのキー | `achievementStorageKey('user-1')` が `'dashboardAchievements:user-1'`。user-1 の記録を `saveRecord` した後でも、`loadRecord('user-2')` は空の記録。壊れた値（`'{'`）が入ったキーの `loadRecord` も空の記録で、例外を投げない。`saveRecord` の後、古いキー `lastHighAccuracyNotification`・`lastDailyGoalNotification` が `localStorage` に無い |
| TC-13 | 解答数の節目 | 空の記録・解答 12 → `messages` が `['10問解答達成！おめでとうございます！🎉']`・`record.answeredMilestone` 10。その記録で解答 12 → `[]`。解答 55 → 50 の文 1 つ。空の記録で解答 9 → `[]`（記録は 0 のまま）。空の記録で解答 120 → 100 の文だけ 1 つ（10・50 は出ない）・記録 100、続けて解答 130 → `[]` |
| TC-14 | 連続日数の節目 | 空の記録・連続 7・today `2026-11-13` → `streakDays` 7・`record.streakRuns['7']` が `'2026-11-07'`。同じ記録・連続 7・同じ日 → `streakDays` null。連続 8・`2026-11-14` → null。連続 14・`2026-11-20` → 14（始まり `2026-11-07`）。途切れた後: 記録 `{ '7': '2026-11-07' }`・連続 7・today `2026-11-30` → 7（始まり `2026-11-24` に更新）。連続 0 → null |
| TC-15 | 正答率と目標は 1 日 1 回 | 解答 20・正答率 0.95 → 正答率の文 1 つ・`highAccuracyDate` が today。同じ日にもう一度 → 出ない。翌日 → 出る。解答 19・0.95 → 出ない。正答率 null → 出ない。目標: `goalMinutes` 30・今日 1800 秒 → 目標の文 1 つ、同じ日 → 出ない、翌日 → 出る。`goalMinutes` null・今日 99999 秒 → 出ない。今日 1799 秒 → 出ない |

### 設定・通知・アクセシビリティ（新規）
| TC | 置き場所 | 内容 | 期待値 |
|---|---|---|---|
| TC-10d | `frontend/src/pages/__tests__/Settings.test.tsx` | 保存のときに設定のキャッシュを保存した値にする（F7） | `QueryClient` に `['user-settings', 'user-1']` の古いデータ（`daily_study_goal_minutes: 30`）を入れておき、設定画面で 60 にして保存すると、取り直しを待たずにそのキャッシュの `daily_study_goal_minutes` が `60` になる |
| TC-17 | `frontend/src/pages/__tests__/Settings.test.tsx` | 読み込みと保存の項目名 | GET `/api/settings/` の応答 `{ daily_study_goal_minutes: 45, study_reminders_enabled: false, reminder_time: '19:00:00', theme_preference: 'dark', notification_settings: { email: false, push: true, achievements: true, reminders: false } }`。「1日の学習目標時間（分）」の入力欄の値が「45」。値を「50」にして「設定を保存」相当のボタン（既存の保存ボタン）を押すと、PATCH `/api/settings/` の本文が `{ daily_study_goal_minutes: 50, study_reminders_enabled: false, reminder_time: '19:00', theme_preference: 'dark', notification_settings: { email: false, push: true, achievements: true, reminders: false } }`（`toEqual`）。本文に `daily_study_goal`・`study_reminder_enabled`・`theme` のキーが無い。`toast.success('設定を保存しました')` が呼ばれる |
| TC-18 | `frontend/src/contexts/__tests__/NotificationContext.test.tsx` | リマインダーの項目名 | `notificationService` をモック（`isEnabled` true・`getPermissionStatus` `'granted'`）。`scheduleReminders({ daily_study_goal_minutes: 40, study_reminders_enabled: true, reminder_time: '19:00:00', theme_preference: 'light', notification_settings: {} })` を呼ぶと、`scheduleStudyReminder` が `('19:00:00', '今日の学習目標は40分です。一緒に頑張りましょう！')` で 1 回呼ばれる。`study_reminders_enabled: false` なら呼ばれない |
| TC-19 | `frontend/src/components/__tests__/AccessibilityProvider.test.tsx` | 上のバーのボタンと浮いたボタン | (a) `<AccessibilityProvider><div /></AccessibilityProvider>`: 「アクセシビリティ設定」のボタンが 1 つあり、`MuiFab-root` のクラスを持つ。(b) `<AccessibilityProvider><AccessibilityToggleButton /></AccessibilityProvider>`: 「アクセシビリティ設定」のボタンがちょうど 1 つで、`MuiFab-root` を持たない。押すと `role=dialog`「アクセシビリティ設定パネル」が出る。(c) (b) の `AccessibilityToggleButton` を外して描き直すと、浮いたボタン（`MuiFab-root`）が戻る |

### E2E（Playwright・開発サーバー・CI で流す）
`e2e/tests/dashboard-layout.spec.ts`（新規・既定のユーザー `e2e_user_a`）
- TC-21〜23・26 は `page.route` で overview の応答を固定する（`has_data: true`・解答 123456・長い科目名。E2E の利用者は解答 0 件から始まり、グラフが描かれないため・計画変更記録）。TC-24・25・27 は本物の API
| TC | 内容 | 期待値 |
|---|---|---|
| TC-21 | 390px で開く | `page.setViewportSize({ width: 390, height: 844 })` の後に `/dashboard`。`stat-answered-count` が「123456」になった後、`document.documentElement.scrollWidth <= document.documentElement.clientWidth`。`start-quiz-button` と `today-review-card` の `boundingBox()` が `x >= 0` かつ `x + width <= 390` |
| TC-22 | 1440 → 390 に縮める（はみ出しの原因の再発防止） | 1440×900 で `/dashboard` を開き、`stat-answered-count` と `canvas` 2 つが出た後に 390×844 にする。`expect.poll` で `scrollWidth <= clientWidth` になる（5 秒以内）。TC-21 と同じ 2 つのボタンの範囲の条件 |
| TC-23 | 1440×900 の最初の画面 | `start-quiz-button` と `today-review-card` の `boundingBox()` が `y >= 0` かつ `y + height <= 900`（スクロールしない状態） |
| TC-24 | 初回の呼び出し 1 回 | `page.on('request')` で GET の `pathname === '/api/dashboard/overview/'` を数える。`/dashboard` を開き「今日の学習時間」が見えた後、1 秒待っても数がちょうど 1 |
| TC-25 | 科目の切り替え | `page.on('console')` を集める。科目の選択（ダッシュボードで唯一の `role=combobox`。`SubjectSelector` の見出しは選択欄の名前に結び付いていない）を開き、2 番目の選択肢（「すべて」の次）を選ぶ。見出し level 1 が見えたまま、「今日の学習時間」が再び出る。集めたコンソールに `out-of-range` を含むものが無い。文字「ダッシュボードを読み込み中...」が一度も見えない（`page.getByText` の数が 0） |
| TC-26 | アクセシビリティ設定のボタンの位置 | 1440×900 と 390×844 の両方で、`getByRole('button', { name: 'アクセシビリティ設定' })` がちょうど 1 つで、その `boundingBox()` の `y + height <= 64`（上のバーの中）。`.MuiFab-root` が 0 個 |

`e2e/tests/dashboard-layout.spec.ts` の `test.describe` を分けて `test.use({ storageState: '.auth/user_c.json' })`（科目 0 件の一般ユーザー）
| TC | 内容 | 期待値 |
|---|---|---|
| TC-27 | 科目 0 件 | `/dashboard` で「科目がまだ登録されていません。組織の管理者に科目の登録を依頼してください」が見え、`start-quiz-button` が `toBeDisabled()`。「設定画面から科目を追加」の文字が無い |

`e2e/tests/settings.spec.ts`（新規・`test.use({ storageState: '.auth/user_c.json' })`）
- 共有ユーザーの前提: TC-27 と TC-28 はどちらも `e2e_user_c` を使う。TC-28 が書き換えるのは目標時間だけで、TC-27 は目標時間を見ない（科目 0 件のときは目標の 1 行を出さない）ので、並列に流しても互いに影響しない。`problem-management-authz.spec.ts` の `e2e_user_c` も目標時間を見ない
| TC | 内容 | 期待値 |
|---|---|---|
| TC-28 | 目標時間の保存と読み戻し | `/settings` で「1日の学習目標時間（分）」の今の値を読み、45 でなければ 45、45 なら 50 を入れて保存。「設定を保存しました」が見える。`page.reload()` の後、入力欄の値が保存した値。`GET /api/settings/` の応答の `daily_study_goal_minutes` も同じ値（`page.waitForResponse`） |

### 既存のテストの更新（`Dashboard.test.tsx`・I473）
| 既存の TC | 変えること | 保つこと |
|---|---|---|
| TC-21 | 「まだ解答の記録がありません」→「まだ記録がありません」（`getAllByText`） | 赤い円（`doughnut-chart`）を出さない・正答率の「—」は「まだ記録がありません」に置き換わるので `'—'` の確かめを外す・「データがありません。まずは問題を解いてみましょう！」 |
| TC-26 | 「まだ解答の記録がありません」→「この科目はまだ解答がありません。まずは問題を解いてみましょう！」 | 全科目の一覧（英語）が出る・「データがありません。まず…」が出ない |
| TC-27 | `beforeEach` に `localStorage.clear()`（共通の前提） | 「すべて」の応答だけで判定する・科目の応答では出さない |
| TC-20・TC-22・TC-23・TC-25・TC-28 | 変えない（`AuthContext` のモックに `id` を足すだけ。描くときに `MemoryRouter` で包む〔「統計を見る」のリンクのため〕） | そのまま |

既存の E2E の更新（計画変更記録）: `e2e/tests/quiz-session.spec.ts` の「クイズに答えると、ダッシュボードの解答問題数が 1 増える」は、「解答問題数」の見出しが出た後、数字（`stat-answered-count`）が無ければ前の値を 0 とする。前後の差（+1）を確かめることは変えない

## 失敗の注入（否定・不在・回帰の TC・実装時に 1 回だけ）
| TC | 注入する壊れ方 | 期待（不合格になる） | 結果 |
|---|---|---|---|
| TC-08 | `useDashboardOverview` の Promise の使い回しを外す | 呼び出しが 2 回で不合格 | 2026-11-13 不合格になった（✕）→ 戻して合格（自作の取得のとき） |
| TC-08（React Query への置き換えの後） | `useDashboardOverview` の取得を `useQuery` から `useEffect` での直接の取得に戻す | 呼び出しが 2 回で不合格 | 2026-11-13 不合格になった（✕）→ 戻して合格 |
| TC-10d | 保存のときの `invalidateQueries` を外す | `isInvalidated` が `false` のままで不合格 | 2026-11-13 不合格になった（✕）→ 戻して合格（F7 の直しの前の形） |
| TC-10d（F7 の直しの後） | 保存のときの `setQueryData` を `invalidateQueries` に戻す | キャッシュが 30 のままで不合格 | 2026-11-13 直す前の実装（`invalidateQueries`）で不合格（✕）を確かめてから直し、合格 |
| TC-16 | お知らせの関数を取得の effect の依存に戻す | 呼び出しが 2 回以上で不合格 | 2026-11-13 不合格になった（✕・`useNotifications().showAchievement` を依存に入れた）→ 戻して合格 |
| TC-21・TC-22 | `Layout.tsx` の `minWidth: 0` を外す | TC-22 が不合格（スパイクで 1440 → 390 の `scrollWidth` 808 を確認済み） | 2026-11-13 TC-22 が不合格（`scrollWidth <= clientWidth` が 5 秒で true にならない）・TC-21 は合格（直接 390 で開くとはみ出さないため。想定どおり）→ 戻して合格 |
| TC-25 | 読み込み中に画面全体を置き換える形（`SubjectSelector` を外して付け直す）に戻す | 警告が出る、または「読み込み中...」が見えて不合格 | 2026-11-13 `SubjectSelector` に `key={selectedSubject}` を付けて切り替えのたびに付け直すと、MUI の `out-of-range value 2` の警告が 4 回出て不合格 → 戻して合格（画面全体を置き換える注入は開発サーバーの表示が壊れて確かめにならなかったので、原因そのもの〔付け直し〕を注入した） |
| TC-02・TC-05 | 「まだ記録がありません」の分岐を外す／科目 0 件の案内を消す | 不合格 | 2026-11-13 どちらも不合格になった（✕）→ 戻して合格 |

## 決定論ゲート（自動実走）
<!-- 本イシューはシェルの決定論ゲートを持たない（確かめは Jest・E2E・pytest で CI が流す）。 -->

## 再発防止記録（fix-loop・コードレビュー F1・2026-11-13）
- なぜ失敗したか: 連続日数の節目の開始日を「今日 - (日数 - 1)」と、連続の終わりを常に今日と決め打ちしていた。裏側の `_current_streak`（`backend/dashboard/selectors.py:106`）は、今日に答えが無ければ昨日までを数えるので、答えていない翌日は開始日が 1 日ずれ、同じ連続でもう一度お知らせが出た
- 何を変えたか: `frontend/src/utils/dashboardAchievements.ts` で、同じ応答の `today.answered_count` が 0 なら連続の終わりを昨日として開始日を出す（裏側と同じ規則）。診断: `docs/reviews/I487_fix_diagnosis_20261113_1718.md`（案 A・診断レビュー PASS）
- セキュリティ上の考慮点: なし（端末の表示用の記録だけ）
- 次回どう防ぐか: 裏側の値を画面で読み直して計算するときは、裏側の数え方（境目の規則）をコメントで指し、境目の場合（今日まだ答えていない）を TC に入れる。TC-14b を追加
- 確かめた結果: TC-14b（追加）は直す前に不合格（✕）・直した後に合格。`dashboardAchievements.test.ts` 5 件・`Dashboard.test.tsx` 27 件 合格・`npm run lint` 0 件。既存の TC-14 は、今日に答えがある前提を明示した（`answeredToday: 1`）

## 実行記録（test-gate・2026-11-13）
- `bash scripts/claude/gate-check.sh I487` → exit 0（コードレビュー `docs/reviews/I487_code_review_20261113_1720.md` VERDICT OK・REVIEWED_COMMIT 5cd85647 以降は記録の場所だけ）
- 決定論ゲート（シェル）: 宣言なし（test-gate に回された heavy なものも無い）
- pytest・Jest・E2E: CI（PR #507・HEAD 5cd85647）で成功（review-gate の `CI_WAIT: OK`）。手元では流し直していない

## React Query への置き換えの記録（implement・2026-11-13）
- 手元・関係するファイルだけ: `Dashboard.test.tsx` 27 件・`Settings.test.tsx` 2 件（TC-10d を追加）・`dashboardAchievements.test.ts` 5 件・`NotificationContext.test.tsx` 2 件・`AccessibilityProvider.test.tsx` 3 件・`TodayReviewCard.test.tsx` 7 件 合格（46 件）。`npm run lint`（--max-warnings 0）・`npm run typecheck` 合格
- テストの変更: 画面のテストを `QueryClientProvider`（テストごとに新しい `QueryClient`・`retry: false`）で包んだ。TC-07 は、React Query が応答を少し遅れて画面に反映するので、数字が出るのを `findByTestId` で待つ形にした（確かめる中身は同じ）
- E2E（手元の e2e コンテナ・`--retries=0`）: `dashboard-layout.spec.ts` 7 件・`settings.spec.ts` 1 件・`quiz-session.spec.ts` 3 件 合格（TC-24 の初回の取得 1 回を含む）
- 失敗の注入: TC-08（`useEffect` での直接の取得に戻す → 2 回で不合格）・TC-10d（`invalidateQueries` を外す → 不合格）。どちらも戻して合格

## 再発防止記録（fix-loop・コードレビュー F7・2026-11-13）
- なぜ失敗したか: 設定の保存のときに、設定のキャッシュを「古い」と印を付けるだけ（`invalidateQueries`）にしていた。React Query は取り直しが終わるまで古い値を返すので、ダッシュボードに戻った直後に、古い目標で達成を判定して記録してしまいうる
- 何を変えたか: 保存の応答（裏側が保存した値）で設定のキャッシュを書き換える（`setQueryData`・`frontend/src/pages/Settings.tsx`）。React Query の公式の推奨（Updates from Mutation Responses）
- セキュリティ上の考慮点: なし（端末の表示用の記録だけ）
- 次回どう防ぐか: 画面で値を保存して、同じ値をほかの画面がキャッシュで持つときは、保存の応答でキャッシュを書き換える。TC-10d で固定
- 確かめた結果: TC-10d は直す前に不合格（✕）・直した後に合格。`Settings.test.tsx` 2 件・`Dashboard.test.tsx` 27 件 合格。`npm run lint`・`npm run typecheck` 合格
