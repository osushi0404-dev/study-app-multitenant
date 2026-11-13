# I487 自動テスト: ダッシュボードの状態ごとの表示・並び順・スマホ幅の崩れの修正

実行コマンド（例）: `docker compose exec frontend npm test -- --watchAll=false src/pages/__tests__/Dashboard.test.tsx` / `docker compose --profile e2e run --rm e2e npx playwright test tests/dashboard-layout.spec.ts --retries=0`

- 全体（pytest・Jest・E2E）は CI が PR ごとに流す。手元では実装中に関係するファイルだけを流す
- 計画書: `docs/plans/open/plan_I487.md`（TC と受け入れ条件の対応は計画書の「2. 受け入れ条件」）

結果:
- backend: 実装前のため未実行（既存の `core/tests/test_I493_openapi_contract.py` を CI で流す）
- frontend: 実装前のため未実行
- e2e: 実装前のため未実行

## 共通の前提（Jest）
- `Dashboard.test.tsx` の既存のモック（`services/api`・`SubjectService`・`SubjectSelector`・`TodayReviewCard`・`react-chartjs-2`・`AuthContext`〔`user: { id: 'user-1', user_id: 'u_i473' }` に `id` を足す〕・`NotificationContext`）を使う
- `beforeEach` で `localStorage.clear()`
- 設定 API（`/api/settings/`）の応答は、TC ごとに `mockGet` の URL の分岐で返す（指定の無い TC は `{ data: {} }` ＝ 目標なし）
- `overview()` は既存のひな形（has_data true・今日 330 秒・連続 2 日・解答 12・正答率 0.75・苦手 英語・おすすめ 数学）

## TC 一覧

### Dashboard（`frontend/src/pages/__tests__/Dashboard.test.tsx` に追記）
| TC | 内容 | 期待値 |
|---|---|---|
| TC-01 | 並び順 | 次の要素が文書の中でこの順に並ぶ（`compareDocumentPosition` の `DOCUMENT_POSITION_FOLLOWING`）: 見出し（`role=heading` level 1）「おかえりなさい、u_i473さん！」→ 科目の選択（モックのボタン「科目5を選ぶ」）→ `start-quiz-button` → 「今日の復習のカード」→ `stat-answered-count` → 見出し「直近 7 日の学習時間」→ 見出し「間違いやすい分野（全科目）」→ 見出し「おすすめ練習問題（全科目）」→ リンク「統計を見る」（`href="/statistics"`）。文字「今日も学習を頑張りましょう」と見出し「詳細統計」が無い |
| TC-02 | データ 0 件（すべて） | `has_data: false`・数字 0・`last_7_days` すべて 0 の応答で、「まだ記録がありません」がちょうど 6 個（`getAllByText` の長さ 6）。`line-chart`・`doughnut-chart` が無い。「目標:」の文字・`role=progressbar` が無い。「データがありません。まずは問題を解いてみましょう！」がある |
| TC-03 | 選んだ科目だけ 0 件 | 「すべて」は `overview()`、`subject_id=5` は `has_data: false` の応答。「科目5を選ぶ」の後、「この科目はまだ解答がありません。まずは問題を解いてみましょう！」があり、その後ろ（`DOCUMENT_POSITION_FOLLOWING`）に「英語」がある。「5 問以上解いた科目のうち…」「データがありません。まず…」が無い。苦手の一覧が空（`weak_subjects: []`）の科目 0 件の応答では、案内の文だけがあり「5 問以上解いた科目のうち…」が無い |
| TC-04 | 「クイズを始める」の行き先 | (a) 科目 2 件（id 5・6）・選択「すべて」→ 押すと `role=dialog` が出て、`navigate` は呼ばれない。(b) 科目 2 件・「科目5を選ぶ」の後 → 押すとダイアログが出ず `navigate('/quiz?subject=5')`。(c) 科目 1 件（id 7）・「すべて」→ `navigate('/quiz?subject=7')` |
| TC-05 | 科目 0 件 | `getUserSubjects` が `[]`。`role=status` の中に「科目がまだ登録されていません。組織の管理者に科目の登録を依頼してください」。`start-quiz-button` が `disabled`。`toast.error` が呼ばれない。「設定画面から科目を追加」の文字が無い。「今日の目標達成まで」の文字が無い |
| TC-06 | 科目の一覧の取得に失敗 | `getUserSubjects` が reject。クイズのカードに「科目を読み込めませんでした」とボタン「再読み込み」、`start-quiz-button` が `disabled`、「科目がまだ登録されていません」が無い。2 回目は `[{ id: 7, name: '数学' }]` を返すようにして「再読み込み」（クイズのカードの中のもの）を押すと、`start-quiz-button` が押せるようになり、「科目を読み込めませんでした」が消える |
| TC-07 | 読み込み中と科目の切り替え | overview の応答を手で解決する Promise にする。初回: `dashboard-skeleton` があり、見出し「おかえりなさい、u_i473さん！」・`start-quiz-button`・「科目5を選ぶ」がある。解決すると `stat-answered-count` が「12」になり、スケルトンが消える。「科目5を選ぶ」を押すと、`stat-answered-count` が消えて `dashboard-skeleton` が出る間も、見出し・`start-quiz-button`・「今日の復習のカード」が出たまま（同じ DOM の要素〔押す前に取った参照と `toBe` で同じ〕）。文字「ダッシュボードを読み込み中...」が出ない |
| TC-08 | StrictMode で 1 回 | `<React.StrictMode><Dashboard /></React.StrictMode>` を描き、`stat-answered-count` が「12」になった後、`mockGet` の `'/api/dashboard/overview/'` への呼び出しがちょうど 1 回 |
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
| TC-17 | `frontend/src/pages/__tests__/Settings.test.tsx` | 読み込みと保存の項目名 | GET `/api/settings/` の応答 `{ daily_study_goal_minutes: 45, study_reminders_enabled: false, reminder_time: '19:00:00', theme_preference: 'dark', notification_settings: { email: false, push: true, achievements: true, reminders: false } }`。「1日の学習目標時間（分）」の入力欄の値が「45」。値を「50」にして「設定を保存」相当のボタン（既存の保存ボタン）を押すと、PATCH `/api/settings/` の本文が `{ daily_study_goal_minutes: 50, study_reminders_enabled: false, reminder_time: '19:00', theme_preference: 'dark', notification_settings: { email: false, push: true, achievements: true, reminders: false } }`（`toEqual`）。本文に `daily_study_goal`・`study_reminder_enabled`・`theme` のキーが無い。`toast.success('設定を保存しました')` が呼ばれる |
| TC-18 | `frontend/src/contexts/__tests__/NotificationContext.test.tsx` | リマインダーの項目名 | `notificationService` をモック（`isEnabled` true・`getPermissionStatus` `'granted'`）。`scheduleReminders({ daily_study_goal_minutes: 40, study_reminders_enabled: true, reminder_time: '19:00:00', theme_preference: 'light', notification_settings: {} })` を呼ぶと、`scheduleStudyReminder` が `('19:00:00', '今日の学習目標は40分です。一緒に頑張りましょう！')` で 1 回呼ばれる。`study_reminders_enabled: false` なら呼ばれない |
| TC-19 | `frontend/src/components/__tests__/AccessibilityProvider.test.tsx` | 上のバーのボタンと浮いたボタン | (a) `<AccessibilityProvider><div /></AccessibilityProvider>`: 「アクセシビリティ設定」のボタンが 1 つあり、`MuiFab-root` のクラスを持つ。(b) `<AccessibilityProvider><AccessibilityToggleButton /></AccessibilityProvider>`: 「アクセシビリティ設定」のボタンがちょうど 1 つで、`MuiFab-root` を持たない。押すと `role=dialog`「アクセシビリティ設定パネル」が出る。(c) (b) の `AccessibilityToggleButton` を外して描き直すと、浮いたボタン（`MuiFab-root`）が戻る |

### E2E（Playwright・開発サーバー・CI で流す）
`e2e/tests/dashboard-layout.spec.ts`（新規・既定のユーザー `e2e_user_a`）
| TC | 内容 | 期待値 |
|---|---|---|
| TC-21 | 390px で開く | `page.setViewportSize({ width: 390, height: 844 })` の後に `/dashboard`。`stat-answered-count` が出た後、`document.documentElement.scrollWidth <= document.documentElement.clientWidth`。`start-quiz-button` と `today-review-card` の `boundingBox()` が `x >= 0` かつ `x + width <= 390` |
| TC-22 | 1440 → 390 に縮める（はみ出しの原因の再発防止） | 1440×900 で `/dashboard` を開き、`stat-answered-count` と `canvas` 2 つが出た後に 390×844 にする。`expect.poll` で `scrollWidth <= clientWidth` になる（5 秒以内）。TC-21 と同じ 2 つのボタンの範囲の条件 |
| TC-23 | 1440×900 の最初の画面 | `start-quiz-button` と `today-review-card` の `boundingBox()` が `y >= 0` かつ `y + height <= 900`（スクロールしない状態） |
| TC-24 | 初回の呼び出し 1 回 | `page.on('request')` で GET の `pathname === '/api/dashboard/overview/'` を数える。`/dashboard` を開き `stat-answered-count` が出た後、1 秒待っても数がちょうど 1 |
| TC-25 | 科目の切り替え | `page.on('console')` を集める。科目の選択（`role=combobox` 名前「科目を選択」）を開き、2 番目の選択肢（「すべて」の次）を選ぶ。見出し level 1「おかえりなさい」が見えたまま、`stat-answered-count` が再び出る。集めたコンソールに `out-of-range` を含むものが無い。文字「ダッシュボードを読み込み中...」が一度も見えない（`page.getByText` の数が 0） |
| TC-26 | アクセシビリティ設定のボタンの位置 | 1440×900 と 390×844 の両方で、`getByRole('button', { name: 'アクセシビリティ設定' })` がちょうど 1 つで、その `boundingBox()` の `y + height <= 64`（上のバーの中）。`.MuiFab-root` が 0 個 |

`e2e/tests/dashboard-layout.spec.ts` の `test.describe` を分けて `test.use({ storageState: '.auth/user_c.json' })`（科目 0 件の一般ユーザー）
| TC | 内容 | 期待値 |
|---|---|---|
| TC-27 | 科目 0 件 | `/dashboard` で「科目がまだ登録されていません。組織の管理者に科目の登録を依頼してください」が見え、`start-quiz-button` が `toBeDisabled()`。「設定画面から科目を追加」の文字が無い |

`e2e/tests/settings.spec.ts`（新規・`test.use({ storageState: '.auth/user_c.json' })`）
| TC | 内容 | 期待値 |
|---|---|---|
| TC-28 | 目標時間の保存と読み戻し | `/settings` で「1日の学習目標時間（分）」の今の値を読み、45 でなければ 45、45 なら 50 を入れて保存。「設定を保存しました」が見える。`page.reload()` の後、入力欄の値が保存した値。`GET /api/settings/` の応答の `daily_study_goal_minutes` も同じ値（`page.waitForResponse`） |

### 既存のテストの更新（`Dashboard.test.tsx`・I473）
| 既存の TC | 変えること | 保つこと |
|---|---|---|
| TC-21 | 「まだ解答の記録がありません」→「まだ記録がありません」（`getAllByText`） | 赤い円（`doughnut-chart`）を出さない・正答率の「—」は「まだ記録がありません」に置き換わるので `'—'` の確かめを外す・「データがありません。まずは問題を解いてみましょう！」 |
| TC-26 | 「まだ解答の記録がありません」→「この科目はまだ解答がありません。まずは問題を解いてみましょう！」 | 全科目の一覧（英語）が出る・「データがありません。まず…」が出ない |
| TC-27 | `beforeEach` に `localStorage.clear()`（共通の前提） | 「すべて」の応答だけで判定する・科目の応答では出さない |
| TC-20・TC-22・TC-23・TC-25・TC-28 | 変えない（`AuthContext` のモックに `id` を足すだけ） | そのまま |

## 失敗の注入（否定・不在・回帰の TC・実装時に 1 回だけ）
| TC | 注入する壊れ方 | 期待（不合格になる） | 結果 |
|---|---|---|---|
| TC-08 | `useDashboardOverview` の Promise の使い回しを外す | 呼び出しが 2 回で不合格 | 実装前のため未実行 |
| TC-16 | お知らせの関数を取得の effect の依存に戻す | 呼び出しが 2 回以上で不合格 | 実装前のため未実行 |
| TC-21・TC-22 | `Layout.tsx` の `minWidth: 0` を外す | TC-22 が不合格（スパイクで 1440 → 390 の `scrollWidth` 808 を確認済み） | 実装前のため未実行 |
| TC-25 | 読み込み中に画面全体を置き換える形（`SubjectSelector` を外して付け直す）に戻す | 警告が出る、または「読み込み中...」が見えて不合格 | 実装前のため未実行 |
| TC-02・TC-05 | 「まだ記録がありません」の分岐を外す／科目 0 件の案内を消す | 不合格 | 実装前のため未実行 |

## 決定論ゲート（自動実走）
<!-- 本イシューはシェルの決定論ゲートを持たない（確かめは Jest・E2E・pytest で CI が流す）。 -->
