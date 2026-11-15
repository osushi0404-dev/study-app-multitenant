# I513 自動テスト: ダッシュボードの曜日ごと・直近 7 日の見せ方と、確かめ用データの管理コマンド

実行コマンド（例）: `docker compose exec backend python -m pytest dashboard/tests/test_I513_seed_dashboard_verify.py` / `docker compose exec frontend npm test -- --watchAll=false src/pages/__tests__/Dashboard.test.tsx`
（CI が PR ごとに全体を流す。手元では流し直さない）

結果（implement 段階の手元の実行・2026-11-15。正は CI）:
- backend: `test_I513_seed_dashboard_verify.py` 65 passed（Red: 実装前は import で失敗を確かめた）
- frontend: `Dashboard.test.tsx` 37 passed（Red: 実装前は `Bar` が無く失敗を確かめた）。`npm run typecheck`・変えたファイルの ESLint はエラー・警告 0

FG の結果（2026-11-15・どれも元に戻して `cmp`・`grep` で戻ったことを確かめた）:
- FG-1: TC-30 が落ちた（「あと25分」）／FG-2: TC-31 の 2 件が落ちた（「あと30分」が出る）。古い `/目標:/` の正規表現は新しい文言 `目標（全科目）:` に当たらないので、直さないと TC-02・TC-10c が素通りする（新しい正規表現に直した）／FG-3: TC-32（`…,2,6`）・TC-34（a）（`79分`）が落ちた
- FG-4: TC-45 の 2 件が落ちた／FG-5: TC-44 が落ちた／FG-6: TC-43 の 3 件と TC-48 が落ちた／FG-7: TC-47 が落ちた

## Frontend（`frontend/src/pages/__tests__/Dashboard.test.tsx`）
共通: `react-chartjs-2` のモックの `Bar` が `data-testid="bar-chart"`・`data-points`（棒の値をカンマでつなぐ）・`aria-label` を出し、`options` を変数に取る。`days()` の日付は 2026-11-07（土）〜11-13（金）。

| TC | 内容 | 期待値 |
|---|---|---|
| TC-30 | 「すべて」の今日 600 秒・科目 5 の今日 300 秒・目標 30 分・科目 2 件。科目 5 を選ぶ | 数字のカード「5分」（選んだ科目）。`今日の目標（全科目）達成まであと20分です`・`目標（全科目）: 30分 (33%)`・`progressbar` の `aria-valuenow` が `33`。overview の取得は `params: {}` が 1 回・`params: { subject_id: '5' }` が 1 回 |
| TC-30b | TC-30 の後で、科目 5 の応答が `has_data: false`（全科目は記録あり） | 数字のカードは「まだ記録がありません」で、`目標（全科目）: 30分 (33%)` は出る |
| TC-31 | （a）「すべて」の取得が失敗（b）「すべて」が返らないまま、科目 5 は成功。科目 5 を選ぶ（科目 2 件・目標 30 分） | 科目 5 の数字（「5分」）は出る。`/今日の目標/`・`/目標（全科目）/` の文と `progressbar` が無い |
| TC-32 | 既定の応答（`last_7_days` の秒 `0,0,0,0,0,120,330`） | `bar-chart` の `data-points` が `0,0,0,0,0,2,5`（分の切り捨て）。`line-chart` は無い。`options.interaction` が `{ mode: 'index', intersect: false }`。`options.scales.y.beginAtZero` が `true`・`ticks.precision` が `0`（TC-11 を棒に置き換え） |
| TC-33 | `options.plugins.tooltip.callbacks` を呼ぶ。日 6（11/13・330 秒・3 問・2 正）と日 0（11/7・0 問） | `title([{ dataIndex: 6 }])` が `11/13（金）`。`label({ dataIndex: 6 })` が `['学習時間: 5分', '解答数: 3問', '正答率: 67%']`。`label({ dataIndex: 0 })` が `['学習時間: 0分', '解答数: 0問', '正答率: —']`。日 1 を 30 秒・1 問・1 正にした応答で `label({ dataIndex: 1 })` が `['学習時間: 0分', '解答数: 1問', '正答率: 100%']`（棒は 0 でも解答数が出る）、`aria-label` に `11/8（日） 0分・1問` を含む |
| TC-34 | 合計の行（it.each）: （a）秒 125/0/2785/1800/0/0/0・問 3/0/5/1/0/0/0・正 2/0/4/1/0/0/0（b）8 問 1 正（c）`has_data: true` で 7 日の答えが 0 件（d）`has_data: false` | （a）`直近 7 日の合計: 78分・9問・正答率78%`（4710 秒＝78.5 分を切り捨て・60 分以上も分）（b）`正答率13%`（12.5 を切り上げ）を含む（c）`直近 7 日の合計: 0分・0問・正答率—`（d）`weekly-total` が無い |
| TC-35 | 既定の応答 | 合計の行 `weekly-total` が見出し「直近 7 日の学習時間」の後・`bar-chart` の前にある。`bar-chart` の `aria-label` が `11/7（土） 0分` で始まり `11/13（金） 5分` を含む |
| 直す | TC-10a: `目標（全科目）: 45分 (11%)`・`今日の目標（全科目）達成まであと40分です`。TC-10b: `今日の目標（全科目・45分）を達成しました！`。TC-02・TC-10c: 不在を `/目標（全科目）/`・`/今日の目標/` で見る。TC-05: `/今日の目標/`。TC-11: TC-32 へ統合（棒のオプション）。TC-20: `bar-chart` の `data-points` が `0,0,0,0,0,2,5` | 直した後も通る |

FG（失敗の注入。実装の中で一時的に壊して落ちることを確かめ、結果をここに書く。コミットしない）:
- FG-1（TC-30）: `Dashboard.tsx` で `StartQuizCard` に選んだ科目の今日の分を渡す → TC-30 が落ちる（「あと25分」になる）
- FG-2（TC-31・TC-02・TC-10c）: 「すべて」が読めないときも目標を 0 分で出す → TC-31 が落ちる。古い `/目標:/` の正規表現のままにすると TC-02 が通ってしまうことも確かめ、新しい正規表現で落ちることを確かめる
- FG-3（TC-32・TC-34）: 棒・合計を `Math.round` にする → TC-32（`…,2,6`）・TC-34（a）（`79分`）が落ちる

## Backend（`backend/dashboard/tests/test_I513_seed_dashboard_verify.py`）
共通: `override_settings(DEBUG=True)`（テストの実行は既定で `DEBUG` が偽のため）。`NOW = 2026-11-15 15:00 JST`。パスワードの環境変数は `mock.patch.dict(os.environ, {'VERIFY_PW': 'pw-for-test'})`。コマンドは `call_command('seed_dashboard_verify', '--seed', '<n>', '--password-env', 'VERIFY_PW', stdout=StringIO())`、中身は `seed_verify_data(seed=…, password=…, now=NOW)` で呼ぶ。

| TC | 内容 | 期待値 |
|---|---|---|
| TC-40 | 同じ種（7）で `seed_verify_data` を 2 回 | 確かめ用の利用者の解答の並び `(科目 slug, answered_at, is_correct, time_taken)`（`answered_at` 順）が 2 回で同じ。セッション数・解答数も同じ |
| TC-41 | 種 1 と種 2 | 解答の並びが違う |
| TC-42 | 種 0〜49 で `plan_answers`（DB を使わない） | どの種でも: 範囲の外（`today-7` より前）の解答が 1 件以上・直近 7 日の中に `time_taken > 300` が 1 件以上・`today-6`〜`today-1` に解答の無い日が 1 日以上・今日の解答が 1 件以上・どの解答も `answered_at < NOW`・`(日, 科目)` ごとの問題数が 5 以下 |
| TC-43 | 種 3・11・29 で `seed_verify_data` → 返った期待値と `build_overview(user, now=NOW)`・`build_overview(user, subject, now=NOW)`（科目ごと）を突き合わせ | 全科目・科目ごとに: `today.study_seconds`・`today.answered_count` が一致。`last_7_days` の 7 日の `date`・`study_seconds`・`answered_count`・`correct_count` が一致。7 日の合計の秒・問・正が `last_7_days` の和と一致。`totals.answered_count`・`correct_count` が一致。`streak.current_days` が一致。`verify_data` のソースに `dashboard.selectors` の import が無い（`inspect.getsource` で確かめる） |
| TC-44 | 確かめ用の組織のほかの利用者（`other@`）と、ほかの組織の利用者（`outside@`）に、それぞれセッションと解答を作ってから、コマンドを 2 回（種 5・6） | `other@`・`outside@` のセッションと解答の id の集合が前と同じ。確かめ用の利用者の 1 回目の解答の id は 2 回目の後に 1 件も残っていない |
| TC-45 | `override_settings(DEBUG=False)` で、確かめ用データが無い DB と、1 回作った後の DB でコマンドを流す | `CommandError`（`DEBUG が偽` を含む）。無い DB では組織・利用者・科目・解答が 0 件のまま。作った後の DB では解答の id の集合が前と同じ |
| TC-46 | 環境変数が無い・空 | `CommandError`。組織・利用者・解答が増えない（作った後の DB では解答の id の集合が同じ）。環境変数があるときは `user.check_password('pw-for-test')` が真で、出力に `pw-for-test` が無い |
| TC-47 | `verify_i487@example.com` がほかの組織（`other-org`）にいる | `CommandError`。その利用者の組織・パスワード・セッション・解答が変わらない |
| TC-48 | `summarize`・`format_summary` に手で作った計画（今日: 数学 400 秒正解・英語 100 秒不正解。昨日: なし。2 日前: 数学 59 秒正解。10 日前: 英語 60 秒正解）と目標 30 分 | 全科目: `今日: 6分・2問`（300＋100 秒）・`直近 7 日の合計: 7分・3問・正答率67%`（459 秒）・`全期間: 4問・正答率75%`・`連続日数: 1日`・`目標（全科目）: 30分 → あと24分（20%）`・昨日の行 `… 学習時間: 0分・解答数: 0問・正答率: —`。英語: `直近 7 日の合計: 1分・1問・正答率0%`。出力の 1 行目に `種: 123（同じデータを作り直すには --seed 123）` |

FG（失敗の注入。実装の中で一時的に壊して落ちることを確かめ、結果をここに書く。コミットしない）:
- FG-4（TC-45）: `ensure_debug()` を呼ぶ行を外す → TC-45 が落ちる
- FG-5（TC-44）: 削除の条件を `QuizSession.objects.filter(user__organization=org)` に広げる → TC-44 が落ちる
- FG-6（TC-43）: `summarize` の 300 秒の上限を外す → TC-43 が落ちる（どの種にも 300 秒超えがある＝TC-42）
- FG-7（TC-47）: 組織の確かめを外す → TC-47 が落ちる

## 決定論ゲート（自動実走）
- なし（pytest・Jest は CI が流す）

## 再発防止記録（fix-loop・2026-11-15）
- なぜ失敗したか: CI の Backend Tests で `studylogs/tests/test_I455_org_scoped_querysets.py::test_unscoped_reads_have_reason_comment`（I455 の TC-06）が落ちた。`dashboard/verify_data.py` の `QuizSession.objects.bulk_update`・`QuizSession.objects.filter(user=user).delete()` に、絞らずに扱う理由のコメント（`# 組織で絞らない: <理由>`）が無かった。実装の段階で手元では `dashboard/tests/` だけを流し、`dashboard` のコードにも掛かる `studylogs` の決まりのテストを流していなかった
- 何を変えたか: 2 行の直前に理由のコメントを書いた（動作は変えない。診断メモ `docs/reviews/I513_fix_diagnosis_20261115_1043.md`・案 A）
- セキュリティ上の考慮点: 消す・直す範囲は確かめ用の組織にいることを確かめた利用者 1 人のセッションだけで、中身を返さない（TC-44・TC-47 が固定）。認可・露出は変わらない
- 次回どう防ぐか: `backend/dashboard/`・`backend/studylogs/` のコードを足す・変えるときは、手元の「関係するテスト」に `studylogs/tests/test_I455_org_scoped_querysets.py` を含める
- 確かめた結果: `studylogs/tests/test_I455_org_scoped_querysets.py`・`dashboard/tests/test_I513_seed_dashboard_verify.py` 86 passed。コメントが無いと落ちることは、この CI の失敗そのもの（run 43664045176）で確かめた
