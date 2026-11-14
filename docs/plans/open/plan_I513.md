# I513 計画書: ダッシュボードの曜日ごと・直近 7 日の見せ方と、確かめ用データの管理コマンド

## 基本情報
- **計画書ID**: plan_I513
- **関連イシュー**: #513
- **Draft PR**: #521
- **作成根拠資料**: docs/issues/open/I513.md（GitHub #513 の本文の写し）
- **実装後評価**: docs/reviews/open/I513_review.md
- **作成日**: 2026-11-15

## 1. 背景/目的
- 2026-11-13 に確かめ用の利用者（`verify_i487@example.com`・2 科目）で `/dashboard` を確かめ、次の 3 つが分かった（証拠・再現はイシューの「現状の問題」）
  1. 科目を選ぶと、目標の残り・進み具合が選んだ科目の分だけで計算される（目標は 1 日全体の目標）
  2. 直近 7 日のグラフが曲線（`tension: 0.4`）で、日と日の間に値があるように見える
  3. 曜日ごとの解答数・正答率と、直近 7 日の合計が出ていない
- 目的: 「曜日ごとと週全体の学習状況」を、科目を選んでも選ばなくても誤解なく読める画面にする。あわせて、毎回変わる確かめ用のデータと、その期待値を出す管理コマンドを用意する（決め打ちの値を出していても気づける）

### 調査結果
- **原因の概要**: 目標（1 日全体）と、科目で絞った数字を、同じ応答（選んだ科目の overview）から出している。グラフの形・合計は I473・I487 の範囲外で決めていなかった
- **詳細**:
  - `frontend/src/pages/Dashboard.tsx:42` が `todayStudyMinutes(overview.data)`（選んだ科目の応答）を `StartQuizCard` の `todayMinutes` に渡す。`frontend/src/components/dashboard/DashboardStatCards.tsx:45-46` も同じ応答の `today.study_seconds` で進み具合を出す
  - `frontend/src/components/dashboard/DashboardCharts.tsx:71-84` は `Line`・`tension: 0.4`・値は `Math.round(study_seconds / 60)`（数字のカードの「今日の学習時間」は `Math.floor`〔`utils/dashboardAchievements.ts` の `todayStudyMinutes`〕なので、今日の棒と数字のカードが 1 分ずれることがある。例: 330 秒はカード 5 分・グラフ 6）
  - 応答 `last_7_days` には日ごとの `study_seconds`・`answered_count`・`correct_count` があり（`backend/dashboard/selectors.py` の `_last_days`）、裏側を変えずに画面で合計・tooltip を出せる
- **React Query のキャッシュ**: `useDashboardOverview(userId, subjectId)` のキーは `['dashboard','overview',userId,subjectId]`。「すべて」を選んでいるときに「すべて」をもう 1 つの `useQuery` で読んでも同じキーなので取得は 1 回（I487 の TC-08 の仕組み）。科目を選んでいる間は、「すべて」はキャッシュがあれば通信しない（既定の `staleTime` 0 のため、画面に入り直したとき・窓に戻ったときは裏で取り直す。これは今の「すべて」と同じ動き）
- **確かめ用のデータの今の中身**（開発の DB・app-1 の compose。2026-11-15 に読んだ）: 組織 `verify-i487-org`（分類 `verify-i487-cat`）・利用者 `verify_i487`（role user・目標 30 分）・科目 21 確かめ数学（`verify-i487-math`）・22 確かめ英語（`verify-i487-english`）・問題は科目ごとに 1 問・`UserSubjectAccess` 2 件・セッション 15・解答 15
- **モデルの制約**（`backend/problems/models.py`）: `QuizSession` は利用者ごとに有効（`is_active=True`）なものが 1 つまで（`uniq_active_quizsession_per_user`）。`QuizAnswer` は `(session, problem)` が一意で、`answered_at` は `auto_now_add`（作るときは今になる。`bulk_update` なら過去の時刻に直せる）。`QuizAnswer` を参照する FK は `QuizSession`→`QuizAnswer` の CASCADE だけ
- **環境の前提**（2026-11-15 に確かめた）: `docker compose ps` で backend・db・frontend・redis が稼働（app-1 のワークツリーの compose）。`e2e-init` サービス（backend のイメージ・`backend/.env` と `e2e/.env.e2e` を読む）の中で `DEBUG=True`・`TIME_ZONE=Asia/Tokyo`・`E2E_TEST_PASSWORD` が入っている（値は出さず有無だけを確かめた）
- **スパイク（承認画面が出るか・`scripts/claude/check-permission-prompt.sh`）**:
  - `docker compose --profile e2e run --rm --no-deps e2e-init python manage.py check` → **承認画面が出る**（exit 10。許可の `Bash(docker compose run *)` に `--profile` が前に来る形が当たらない）
  - `docker compose run --rm --no-deps e2e-init python manage.py check` → **承認なしで実行された**（exit 0。`run` で名指しすれば profile 付きのサービスも動く）。見張り（`pretooluse_guard.py`）も止めない。→ 流し方はこの形にする（成立）
- 既存テストの事前実行・lint の事前計測: 本イシューは CI・lint の変更ではないので省く（pytest・Jest は CI が PR ごとに流す）

## 2. 受け入れ条件
- [ ] AC1: 科目を選んでいても、「今日の目標（全科目）達成まであと◯分です」と目標の進み具合（「目標（全科目）: ◯分 (◯%)」・バー）は、全科目の今日の合計で計算される。FE テストで固定（全科目の今日 10 分・選んだ科目 5 分・目標 30 分 → 「あと20分」・33%）。確かめ用のデータで、画面の値がコマンドの出す全科目の目標の行と一致する
- [ ] AC2: 直近 7 日の学習時間が棒グラフで出る（縦軸 0 から・整数の目盛り）
- [ ] AC3: 棒の tooltip に、その日の日付（曜日）・学習時間・解答数・正答率（答えが無い日は「—」）が出る
- [ ] AC4: グラフの見出しの下に「直近 7 日の合計: ◯分・◯問・正答率◯%」が出る（学習時間は `study_seconds` の合計を分に切り捨て・60 分以上も「◯分」、正答率は `correct_count` の合計 ÷ `answered_count` の合計を整数の % に四捨五入。答えが無ければ「—」・データ無しのときは行を出さない）。FE テストで固定。確かめ用のデータで、画面の値がコマンドの期待値と一致する
- [ ] AC5: 管理コマンドは毎回違う確かめ用のデータを作り、境目（範囲の外・300 秒超え・解答の無い日・今日）を毎回含む。`--seed` が同じなら同じデータ。期待値を出し、その期待値は overview の応答と一致する（テストで固定）。作り直しでほかの利用者のデータは変わらない。`DEBUG` が偽のときは何も作らずに止まる
- [ ] AC6: 画面確認で、管理コマンドを 2 回（違う種で）流し、それぞれ画面の値がコマンドの期待値と一致した記録がある
- [ ] AC7: 画面確認で、確かめ用のデータの「すべて」「科目ごと」を 1440・390 で確かめた記録がある
- [ ] AC8: Playwright で画面からクイズを解いた後、今日の解答数と直近 7 日の合計の解答数が、解いた問題の数だけ増えた記録がある
- [ ] AC9: `docs/runbooks/frontend-verify.md` に、確かめ用のデータの作り方・見比べ方・今日の分を Playwright で足す手順がある
- [ ] AC10: 既存の機能に退行が無い

## 3. 影響範囲
- Backend: 管理コマンドとその中身の追加だけ（`backend/dashboard/verify_data.py`・`backend/dashboard/management/`）。API・集計（`backend/dashboard/selectors.py`）は変えない
- Frontend: ダッシュボードの部品（`DashboardCharts.tsx`・`DashboardStatCards.tsx`・`StartQuizCard.tsx`）・`Dashboard.tsx`・新しい計算の小さなファイル（`weeklySummary.ts`）・テスト
- DB: なし（マイグレーションなし。管理コマンドは開発の DB の確かめ用の利用者のデータを作り直すだけ）
- Config/Infra: なし（`docker-compose.yml` は変えない。既存の `e2e-init` サービスで流す）
- 変えないもの: `backend/dashboard/selectors.py`・`frontend/src/components/statistics/format.ts`（`formatRate` を読むだけ）・`frontend/src/hooks/useDashboardOverview.ts`（今の作りのまま 2 回呼ぶ）

## 4. 変更点一覧（具体）

### 修正アプローチ
画面は「全科目の overview をいつも読む」ことで目標を 1 日全体の値にし、グラフは同じ応答の `last_7_days` から棒・tooltip・合計を作る（裏側は変えない）。確かめ用データは、乱数（種つき）で解答の計画を作り、その計画から集計を使わずに期待値を数え、計画どおりに DB に書く管理コマンドにする。

### 4-1. 目標を全科目の今日の時間で出す
修正方針: 科目の選択に関係なく「すべて」の overview を読み、目標の行・進み具合・達成のお知らせの判定をそれで行う。「すべて」が読み込み中・失敗・データ無しのときは、目標の行と進み具合を出さない（仮の値で埋めない）。

| ファイル | 変更 |
|---|---|
| `frontend/src/pages/Dashboard.tsx` | `const allOverview = useDashboardOverview(userId, ALL_SUBJECTS);` を足す（「すべて」を選んでいるときは同じキーなので取得は 1 回）。`useDashboardAchievements(user?.id, allOverview.data, goal)` にする（今は「すべて」を選んでいるときだけ渡していた。同じ応答なので判定は変わらず、分岐が要らなくなる）。`allTodayMinutes = allOverview.data ? todayStudyMinutes(allOverview.data) : null` を `StartQuizCard` の `todayMinutes` に渡す。`goalProgress`（`{ todayMinutes, goalMinutes }` か `null`。`allOverview.data?.has_data` が真で、目標が読めたときだけ）を `DashboardStatCards` に渡す |
| `frontend/src/components/dashboard/DashboardStatCards.tsx` | 引数 `goalMinutes` を `goalProgress: GoalProgress \| null` に替える。進み具合（バーと「目標（全科目）: ◯分 (◯%)」）は `goalProgress` があるときだけ出す（選んだ科目の `has_data` には依らない。目標は 1 日全体のものなので、選んだ科目にまだ記録が無くても全科目の進み具合は出す）。% は今どおり `Math.floor`、バーは 100 まで。`GoalProgress` 型をここから export する |
| `frontend/src/components/dashboard/StartQuizCard.tsx` | `todayMinutes` の意味を「全科目の今日の分」にし（コメントを直す）、文言を `今日の目標（全科目）達成まであと${goal - today}分です`／`今日の目標（全科目・${goal}分）を達成しました！` にする |

### 4-2. 推移を棒グラフにし、tooltip と直近 7 日の合計を出す
修正方針: 同じ `last_7_days` から、棒の値（分の切り捨て）・tooltip の 3 行・7 日の合計を、純粋な関数で作る。棒の値を切り捨てにして、数字のカード・tooltip・合計と同じ丸めにそろえる。

| ファイル | 変更 |
|---|---|
| `frontend/src/components/dashboard/weeklySummary.ts`（新規） | `type DashboardDay = DashboardOverview['last_7_days'][number]`。`studyMinutes(seconds) = Math.floor(seconds / 60)`。`dayRate(correct, answered) = answered > 0 ? correct / answered : null`。`dayTitle(date)` → `11/13（金）`（'YYYY-MM-DD' を分けて読み、曜日は `toLocaleDateString('ja-JP', { weekday: 'short' })`）。`dayLines(day)` → `['学習時間: ◯分', '解答数: ◯問', '正答率: ◯%' か '正答率: —']`。`weeklyTotal(days)` → `{ minutes, answered, rateText }`（秒・解答・正解をそれぞれ足してから切り捨て・割り算）。`weeklyTotalText(days)` → `直近 7 日の合計: ◯分・◯問・正答率◯%`。正答率の書式は統計画面の `formatRate`（`components/statistics/format.ts`・null は「—」・`Math.round`）を使う |
| `frontend/src/components/dashboard/DashboardCharts.tsx` | `Line`・`LineElement`・`PointElement` を `Bar`・`BarElement` に替える（`Title`・`Legend` は使っていないので登録から外さず今のまま）。データは `studyMinutes(day.study_seconds)`。`barOptions` = `{ responsive, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false }, plugins: { legend: { display: false }, tooltip: { callbacks: { title: (items) => dayTitle(lastDays[items[0].dataIndex].date), label: (item) => dayLines(lastDays[item.dataIndex]) } } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }`（`interaction` を index にして、棒の高さが 0 の日〔答えはあるが 1 分未満・答えが無い日〕も、その日の列を押せば tooltip が出るようにする。tooltip は日ごとの値を閉じ込めるので `useMemo` で `lastDays` から作る）。`ChartCard` に任意の `subtitle` を足し、推移のカードの見出しの下に `weeklyTotalText(lastDays)`（`Typography variant="body2" color="text.secondary" data-testid="weekly-total"`）を出す。データ無しのときは今どおり「まだ記録がありません」だけで、合計の行も出さない。`Bar` に `aria-label`（各日の `dayTitle`・学習時間・解答数を `11/13（金） 5分・3問` の形で読点でつないだ文）を付け、画面読み上げでも日ごとの値が分かるようにする |

### 4-3. 確かめ用のデータの管理コマンド
修正方針: 書き込みの中身は `dashboard/verify_data.py` に置き、コマンドは引数の読み取りと出力だけにする（規約の「薄いコマンド・処理はモジュールに」）。計画（乱数）→ 期待値（計画から数える）→ DB への書き込み、の順で、期待値は `dashboard/selectors.py` を読まない。

`backend/dashboard/verify_data.py`（新規）:
- 定数: `ORG_SLUG='verify-i487-org'`・`ORG_NAME='確かめI487組織'`・`CATEGORY_SLUG='verify-i487-cat'`・`USER_EMAIL='verify_i487@example.com'`・`USER_ID='verify_i487'`・`SUBJECTS=(('verify-i487-math','確かめ数学'),('verify-i487-english','確かめ英語'))`・`PROBLEMS_PER_SUBJECT=5`・`HISTORY_DAYS=14`（今日を含む 14 日。前半 7 日が範囲の外）・`RECENT_DAYS=7`・`CAP_SECONDS=300`。名前・slug は今のデータと同じ（引き継ぐ）
- `@dataclass(frozen=True) PlannedAnswer(subject_slug, answered_at: datetime, is_correct: bool, time_taken: int)`
- `plan_answers(rng: random.Random, now: datetime) -> list[PlannedAnswer]`（純粋な関数・DB を読まない）:
  - `today = timezone.localdate(now)`。範囲の日 `today-13 … today`
  - 順番: 境目（a〜d）を先に確定し、その後で乱数の日・科目を足す（乱数で選んだ後に境目を後から足す作りにしない。どの種でも境目が入ることを作りで保つ）
  - 必ず入れる境目: (a) 直近 7 日の中（`today-6 … today-1`）から 1〜2 日を「解答の無い日」に選ぶ (b) 今日に 1 問以上 (c) 範囲の外（`today-13 … today-7`）のどこか 1 日に 1 問以上 (d) 直近 7 日の中の解答のどれか 1 問を `time_taken` 301〜900 秒にする
  - 乱数: 解答の無い日以外の各日について、範囲の外の日は 50%・範囲の中の日は必ず、解く。解く日は科目ごとに 70% で解き（最低 1 科目）、1 科目あたり 1〜`PROBLEMS_PER_SUBJECT` 問（同じセッションで同じ問題は 1 回まで）・正解 60%・`time_taken` 20〜240 秒
  - 時刻: その日の日本時間 7:00〜22:59 の乱数。今日は 0:00〜`now` の 1 分前の間（`now` より後の解答を作らない。0:01 より前なら 0:00）
- `summarize(planned, today, goal_minutes) -> dict`（純粋な関数・selectors を使わずに数える）: 全科目と科目ごとに `today`（秒・分・問）・`days`（直近 7 日の日ごとの日付・秒・分・問・正）・`week`（秒・分・問・正・正答率の文字）・`totals`（問・正・正答率の文字）・`streak`（答えのある日が今日〔今日が無ければ昨日〕から続く日数）。分は 1 問 300 秒までにしてから足し、`//60`。正答率の文字は `math.floor(correct / answered * 100 + 0.5)` + `%`（画面の `Math.round` と同じ）・0 件は `—`。全科目には目標の行（`goal_minutes`・あと◯分か達成・`floor(今日の分/目標*100)`%）も入れる
- `format_summary(summary, seed) -> list[str]`: 画面の表記どおりの行（例 `直近 7 日の合計: 78分・9問・正答率78%`・tooltip と同じ `11/13（金） 学習時間: 12分・解答数: 5問・正答率: 80%`・`目標（全科目）: 30分 → あと18分（40%）`）と、`種: <seed>（同じデータを作り直すには --seed <seed>）`
- `ensure_debug()`: `settings.DEBUG` が偽なら `CommandError('DEBUG が偽のため、確かめ用のデータは作りません')`
- `seed_verify_data(*, seed: int, password: str, now: datetime) -> dict`（`transaction.atomic()` の中）:
  1. `ensure_debug()`（何よりも先）
  2. 分類・組織を `get_or_create`（slug で）。利用者を email で探し、いれば組織が `verify-i487-org` でなければ `CommandError`（ほかの組織の利用者に触らない）。いなければ `create_user(role='user')`。`set_password(password)` して保存
  3. 科目を `get_or_create`（組織・slug）。問題を科目ごとに `確かめ問題 1`〜`5`（`get_or_create`・`problem_type='single'`・選択肢「正解」「不正解」）。`UserSubjectAccess` を `get_or_create`。既存の問題（I487 の 1 問）は消さない
  4. この利用者の `QuizSession` を消す（`QuizSession.objects.filter(user=user).delete()`。解答は CASCADE で消える。ほかの利用者は条件に入らない）
  5. `plan_answers(random.Random(seed), now)` → (日・科目) ごとに `QuizSession(is_active=False, mode='normal', total_problems=5, completed_problems=n, correct_answers=c, ended_at=最後の解答の時刻)` を作り、`QuizAnswer` を `bulk_create` → `answered_at` を計画の時刻にして `bulk_update(['answered_at'])`。セッションの `started_at` も最初の解答の時刻に `bulk_update`
  6. `summarize(planned, today, UserSettings の daily_study_goal_minutes〔無ければ作る・既定 30〕)` を返す
- `password` が空なら `CommandError`（1 より先に確かめる。何も作らない）

`backend/dashboard/management/__init__.py`・`backend/dashboard/management/commands/__init__.py`（新規・空）

`backend/dashboard/management/commands/seed_dashboard_verify.py`（新規）:
- 引数: `--seed`（int・省略時は `secrets.randbelow(2**31)`）・`--password-env`（必須・パスワードを読む環境変数の名前。値そのものは引数で受けない〔プロセスの一覧・シェルの履歴に残さない〕）
- `handle`: `os.environ.get(name, '')` を読み、`seed_verify_data(seed=…, password=…, now=timezone.now())` を呼び、`format_summary` の行を `self.stdout` に出す。パスワードは出さない
- 流し方（runbook に書く）: `docker compose run --rm --no-deps e2e-init python manage.py seed_dashboard_verify --password-env E2E_TEST_PASSWORD`（`e2e-init` は `e2e/.env.e2e` を読むので、パスワードは会話にもファイルにも出ない。Playwright MCP では同じ名前 `E2E_TEST_PASSWORD` を秘密の名前として入力する）

### 4-4. テスト・手順書
| ファイル | 変更 |
|---|---|
| `frontend/src/pages/__tests__/Dashboard.test.tsx` | `react-chartjs-2` のモックを `Bar` に替え（`data-points` と `options` を取り出す）、TC-30〜TC-35 を足す。目標の文言の変更に合わせて TC-10a・TC-10b を直し、文言の不在を見る TC-02・TC-05・TC-10c の正規表現を `/目標（全科目）/`・`/今日の目標/` にする（古い `/目標:/` のままだと新しい文言を見逃して素通りするため）。TC-11 を棒のオプションに、TC-20 の棒の値を切り捨て（`0,0,0,0,0,2,5`）に直す |
| `backend/dashboard/tests/test_I513_seed_dashboard_verify.py`（新規） | TC-40〜TC-48（auto_test） |
| `docs/runbooks/frontend-verify.md` | 「5. ログイン」の表に確かめ用の利用者を足し、「11. 確かめ用のデータ（ダッシュボード）」の節を足す（流し方・出力の読み方・見比べ方・Playwright で今日の分を足す手順・種で作り直す） |

## 5. 実装手順（ステップ）
1. **管理コマンド（未知リスク先行）**: 4-3 を作り、TC-40〜TC-48 を書く。開発の DB に流せることは手動 No.1（→ TC-40〜TC-48・手動 No.1）
2. **目標を全科目で**（ステップ 1 と並行可）: 4-1 を作り、TC-30・TC-31 と既存の TC の文言を直す（→ TC-30・TC-31）
3. **棒グラフ・tooltip・合計**（ステップ 2 の後。同じテストファイルのモックを替えるため）: 4-2 を作り、TC-32〜TC-35 を足し、TC-11・TC-20 を直す（→ TC-32〜TC-35）
4. **手順書**（ステップ 1〜3 の後）: 4-4 の `frontend-verify.md`
5. implement 段階の画面確認（`docs/runbooks/frontend-verify.md`）: ステップ 1 のコマンドで作ったデータで、1440・390 の「すべて」・科目ごとを確かめる（手動 No.2〜No.4 の下見。正式な記録は test-gate）
- ステップ 1 と 2〜4 は互いに依存しない。サービスの再起動は不要（frontend は開発サーバーの再読み込み・backend のコマンドは新しいコンテナで動く）

## 6. テスト計画
### 自動（`docs/tests/open/I513_auto_test.md`）
- テストのレベル: 画面の表示・計算は Jest（Dashboard の結合のテスト・chart.js はモックしてオプションと tooltip の関数を直接呼ぶ）。管理コマンドは pytest（DB を使う結合のテスト。期待値と `build_overview` の突き合わせ）。E2E は足さない（既存の `dashboard-layout.spec.ts` の canvas 2 つは棒でも変わらない。描かれることは画面確認で見る）
- 再発防止: 目標が選んだ科目の分で出ないこと（TC-30）・棒の値と合計の丸め（TC-32・TC-34）・期待値と overview の一致（TC-43）
- 認可・テナント: API は変えない。管理コマンドが確かめ用の利用者以外のデータに触らないこと（TC-44・TC-47）
- pytest・Jest は CI が PR ごとに流す（手元では流し直さない）。決定論ゲートは無し
### 手動（`docs/tests/open/I513_manual_test.md`・実施者はすべて Claude）
- 管理コマンドを違う種で 2 回流し、それぞれ画面（1440・390・すべて・科目ごと）とコマンドの期待値を見比べる。Playwright でクイズを解いて今日と 7 日の合計が増えることを見る

## 7. ロールバック
- PR を revert する（マイグレーション・依存の変更なし）。開発の DB の確かめ用データは、revert 後も残る（ユーザーの指示で残すデータ。消す必要は無い）

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 管理コマンドが本番やほかの利用者のデータを消す | `DEBUG` が偽なら最初に止める（TC-45）。消すのは確かめ用の利用者の `QuizSession` だけで、その利用者が確かめ用の組織にいなければ止める（TC-44・TC-47）。全体を 1 つのトランザクションにする | 回避 |
| R2: 「すべて」をもう 1 つ読むことで取得が増える | 同じキーの React Query のキャッシュで、「すべて」を選んでいるときは 1 回（TC-08 は今のまま通る）。科目を選んでいる間はキャッシュから読む（TC-30 で「すべて」の取得が 1 回のままを確かめる） | 回避 |
| R3: 文言を変えたのに、古い文言の不在を見るテストが素通りする（false-green） | TC-02・TC-05・TC-10c の正規表現を新しい文言に合わせて直す（4-4）。直した後、新しい文言を出す作りで落ちることを FG で確かめる | 回避 |
| R4: 棒の値を四捨五入から切り捨てに変えると、59 秒以下の日は棒が 0 になる | tooltip（index で列を押せば出る）と合計で解答数が分かる。数字のカード・tooltip・合計・コマンドの期待値と同じ丸めにそろえるほうを優先する | 受け入れ |
| R5: 画面確認の最中に日付が変わると、コマンドの期待値（流した時点の今日）と画面がずれる | 画面確認は流した直後に行い、日付をまたいだら流し直す（手順書に書く） | 回避 |
| R6: 端末の日付とサーバーの日付がずれる（#481） | 範囲外（#481）。コマンドも画面もサーバーの日本時間の日付で数える | 受け入れ |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 目標は 1 日全体の目標で、科目を選んでいても全科目の今日の合計で計算し、目標の行に「全科目」と添える。全科目の値は「すべて」の overview を React Query で読む（API は変えない）。読み込み中・失敗は出さない
- 推移は棒グラフ（縦軸 0 から・整数の目盛り）。tooltip に学習時間・解答数・正答率（答えが無い日は「—」）
- 直近 7 日の合計の行（分の切り捨て・正答率の四捨五入・答えが無ければ「—」・データ無しは出さない）。学習時間は 60 分以上も「◯分」。暦の週にしない
- 確かめ用データは管理コマンド（`backend/dashboard/management/commands/`）。毎回乱数・境目は必ず入れる・`--seed`・期待値は selectors を使わずに数える・`DEBUG` が偽で止まる・作り直しはこの利用者のセッションと解答だけ・今あるデータを引き継ぐ。今日の分は Playwright で画面から解いて足す
- #516 より先に行い、共通の部品は作らない

Claude が決めた（技術的な選択と理由）:
- 「すべて」は `useDashboardOverview(userId, ALL_SUBJECTS)` をもう 1 回呼ぶ（新しいフックを作らない。同じキーで重複は React Query がまとめる）
- 達成のお知らせの判定も、いつも「すべて」の応答で行う（今は「すべて」を選んでいるときだけ。同じ応答・同じ記録なので出る回数は変わらず、選択による分岐を消せる。TC-27 はそのまま通る）
- 進み具合（バー）は、選んだ科目に記録が無くても、全科目に記録があれば出す（目標は 1 日全体のもの・イシューの決定から導いた。全科目に記録が無い〔`has_data` が偽〕ときは今どおり出さない＝TC-02）
- 目標の文言の「全科目」の置き方: `今日の目標（全科目）達成まであと◯分です`・`今日の目標（全科目・◯分）を達成しました！`・`目標（全科目）: ◯分 (◯%)`（イシューの「目標の行に『全科目』と添える」を、3 か所で同じ括弧書きにした）
- 棒の値を `Math.round` から `Math.floor` にする（数字のカード・tooltip・合計・コマンドと同じ丸め。今は今日の棒とカードが 1 分ずれうる）
- tooltip は `interaction.mode: 'index'`・`intersect: false`（高さ 0 の棒の日も出す・スマホで押しやすい）。題は `11/13（金）`、行は `学習時間: ◯分`・`解答数: ◯問`・`正答率: ◯%`（統計画面の tooltip の「◯分・◯問」と同じ単位の書き方）
- 横軸のラベルは今の曜日（`金`）のまま（7 本の棒が 390 幅でも詰まらない。日付は tooltip で出す）
- 正答率の書式は統計画面の `formatRate` を読んで使う（同じ規則の写しを増やさない。中身は変えない）
- 計算は `weeklySummary.ts` の純粋な関数に分ける（部品を小さく保つ・規約の「計算はコンポーネントの外」）
- 管理コマンドの名前 `seed_dashboard_verify`。処理は `dashboard/verify_data.py`（コマンドは薄く）。科目は今の 2 つ・問題は科目ごとに 5 問（同じセッションで同じ問題は 1 回までの制約の中で、1 日 1 科目 5 問まで作れる）
- 範囲は今日を含む 14 日（範囲の外を 7 日ぶん持てる）。乱数の割合（範囲の外の日 50%・科目 70%・正解 60%・20〜240 秒）は、日ごと・科目ごとに値がばらつき、どの種でも境目が入るように決めた
- パスワードは `--password-env <環境変数の名前>` で受け、値を引数に出さない（イシューの「引数（環境変数から渡す・`seed_e2e` と同じ形）」を、値がプロセスの一覧に残らない形にした）。流すのは既存の `e2e-init` サービス（`e2e/.env.e2e` を読む）で、Playwright MCP は同じ名前 `E2E_TEST_PASSWORD` を秘密の名前で入力する。スパイクで承認なしで流せることを確かめた（1 の調査結果）
- 時刻は日本時間 7〜22 時（日付の境目の扱いは I473・I488 のテストが見ている。ここでは画面の確かめ用なので、境目のすぐ近くを作らない）。今日の分は今より前だけ
- #508 との順: #513 を先（アプリのトラックの着手順）。重なるのは `Dashboard.tsx` の数行で、#508 が後から合わせる
- 一覧 docs/reviews/backlog/I223.md B1〜B4: 残す — ハーネスの行で、本イシューの変更点と関係が無い
- 一覧 docs/reviews/backlog/I224.md F9: 残す — 同上
- セキュリティ: API・認可は変えない。管理コマンドは `DEBUG` が偽で止まり、確かめ用の組織の利用者だけを扱う（最小権限）。パスワードは環境変数から読み、出力・引数・ファイルに出さない。入力は `--seed`（int で受ける・argparse が型を確かめる）と環境変数の名前だけ。画面は React の文字の差し込みだけで、`dangerouslySetInnerHTML` を使わない（XSS なし）。依存の追加なし（`chart.js` の `BarElement`・`react-chartjs-2` の `Bar` は入っている版にある）。bandit は MEDIUM 以上を直す・LOW は `# nosec` で抑える（`random` は確かめ用のデータで暗号の用途ではない＝B311 は LOW。`# nosec B311` と理由を書く）、npm audit は high/critical を直す対象（依存の変更が無いので新しく出ない）
- P3/P5/P8 影響なし（DB の変更・外部 API・非同期・新しいインフラ・依存の変更なし）
- P9 影響なし（個人情報を新しく集めない。確かめ用の架空の利用者だけを開発の DB に作る）
- 性能・UX: 13 章
- 要件・UI/UX の仮定で決めたものは無い（文言・配置は設計確認メモの委任〔「BP、UI/UX の観点でベストなやり方で進めて」〕の範囲で、メモの決定から導いた）

Danger Ops（有無/手順/ロールバック）:
- 無。管理コマンドの削除は、開発の DB の確かめ用の利用者のクイズのセッションと解答だけ（本番では `DEBUG` が偽で止まる）。戻すときは同じコマンドを `--seed` で流し直す

## 13. 性能・UX設計
- 性能: 取得の追加は、科目を選んでいる間の「すべて」の 1 本だけ（キャッシュがあれば通信なし）。裏側のクエリは変えない。計算は 7 件の足し算だけ
- 読み込み中・空・エラー: 選んだ科目の overview の扱いは今のまま（スケルトン・「まだ記録がありません」・エラーと再読み込み）。「すべて」が読み込み中・失敗のときは、目標の行と進み具合だけを出さない（TC-31）。データ無しは合計の行を出さない（TC-34）
- 破壊的な操作: 画面には無い
- アクセシビリティ: 合計は文字で出す。棒グラフの canvas に `aria-label`（各日の日付と学習時間）を付ける。tooltip はマウス・タップで出る（chart.js の既定。キーボードでは出ないが、同じ情報の合計と aria-label がある）

## 14. 学習効果設計
- C1: 曜日ごとの学習時間・解答数・正答率と 7 日の合計が読め、どの日に学習が抜けたか・週の量と正確さが分かる。指標は今の overview の値の見せ方だけで、新しい測定は足さない

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | `DEBUG` が偽のとき、コマンドが組織・利用者・科目・解答を 1 件も作らず、既存の確かめ用のデータも消さずに止まる（TC-45。`ensure_debug()` が書き込みより前にあることを読む） |
| V2 | 1 | 読んで可 | 削除の条件が確かめ用の利用者だけで、ほかの利用者（同じ組織・ほかの組織）のセッションと解答が残る（TC-44）。同じメールの利用者がほかの組織にいれば、何も消さずに止まる（TC-47） |
| V3 | 2 | 読んで可 | 期待値が selectors を使わずに数えられていて、`build_overview` の応答と突き合わせている（TC-43。期待値の関数が `dashboard.selectors` を import していない） |
| V4 | 3 | 読んで可 | 目標の行・進み具合が、選んだ科目の応答ではなく「すべて」の応答から計算される（TC-30）。「すべて」が読めないときは出さない（TC-31） |

## 計画変更記録
- 計画レビュー（`docs/reviews/I513_plan_review_20261115_0308.md`）の Warning 2 件への対応: `plan_answers` で境目を乱数より先に確定する順を明記した／TC-33 に 1 分未満で解答のある日の tooltip、aria-label に解答数を足した。計画レビューのやり直し: 不要（findings への対応の追記だけ。方式・範囲・受け入れ条件は変えない）

## レビュー結果
- [20261115_0308 判定: ✅ 完了](../../reviews/I513_plan_review_20261115_0308.md)
