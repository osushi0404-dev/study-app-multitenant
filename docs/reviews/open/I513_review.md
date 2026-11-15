# I513 レビュー: ダッシュボードの曜日ごと・直近 7 日の見せ方と、確かめ用データの管理コマンド

## 変更概要
- 科目を選んでいても、目標の残り・進み具合を全科目の今日の合計で出す（「全科目」と添える）
- 直近 7 日の推移を棒グラフにし、tooltip に日ごとの学習時間・解答数・正答率、見出しの下に直近 7 日の合計を出す
- 確かめ用のデータを毎回乱数で作り直し、集計を使わずに数えた期待値を出す管理コマンド `seed_dashboard_verify` を足す。手順書に確かめ方を書く

## 変更点
- `backend/dashboard/verify_data.py`（新規）: 計画（`plan_answers`・境目を先に確定）・期待値（`summarize`・`format_summary`・selectors を使わない）・書き込み（`seed_verify_data`・`ensure_debug`・確かめ用の組織の外の同じメールで止まる・この利用者のセッションだけを消す）
- `backend/dashboard/management/commands/seed_dashboard_verify.py`（新規）: `--seed`・`--password-env`（値は引数で受けない）
- `backend/dashboard/tests/test_I513_seed_dashboard_verify.py`（新規）: TC-40〜TC-48
- `frontend/src/pages/Dashboard.tsx`: 「すべて」の overview をもう 1 回読み（同じキー）、目標の行・進み具合・達成のお知らせをそれで出す
- `frontend/src/components/dashboard/DashboardStatCards.tsx`: `goalProgress`（`GoalProgress | null`）を受け、`目標（全科目）: ◯分 (◯%)`
- `frontend/src/components/dashboard/StartQuizCard.tsx`: 文言を `今日の目標（全科目）…` に
- `frontend/src/components/dashboard/weeklySummary.ts`（新規）: 分の切り捨て・tooltip の題と行・読み上げ・7 日の合計
- `frontend/src/components/dashboard/DashboardCharts.tsx`: `Bar`・`interaction: index`・tooltip・合計の行・`aria-label`
- `frontend/src/pages/__tests__/Dashboard.test.tsx`: TC-30〜TC-35 を足し、TC-02・TC-05・TC-10a〜c・TC-11・TC-20 を直した
- `docs/runbooks/frontend-verify.md`: ログインの表に確かめ用の利用者・「11. 確かめ用のデータ（ダッシュボード）」

## 影響範囲
- Backend/Frontend/DB/Config: Backend は管理コマンドの追加だけ（API・集計は変えない）。Frontend はダッシュボードの部品とテスト。DB・Config の変更なし

## テスト結果
- 自動: 手元で backend `test_I513_seed_dashboard_verify.py`・`test_I473_overview.py` 87 passed、frontend `Dashboard.test.tsx` 37 passed、`npm run typecheck`・`npm run lint` 0、`react-scripts build` 成功。FG-1〜FG-9 はすべて落ちることを確かめた（`docs/tests/open/I513_auto_test.md`）。CI（PR #521・HEAD ee4bbeb3）は全部合格
- 手動: test-gate で No.1〜No.7 すべて OK（実施者はすべて Claude）。違う種（1082476175・1030046851）で 2 回作り直し、どちらも 1440・390 の「すべて」と科目ごとの値がコマンドの期待値と一致。画面から 3 問解くと今日と直近 7 日の合計の解答数がちょうど 3 増えた（`docs/tests/open/I513_manual_test.md`）

## 計画との差分
- なし（`/simplify` の整理は動作を変えない書き換えだけ）

## ロールバック
- PR を revert する（マイグレーション・依存の変更なし）

## 自律判断の記録
- [plan-review] 計画レビュー OK。Warning 2 件（境目を乱数より先に決める順・1 分未満で解答のある日の tooltip）は計画とテスト文書に反映し、再レビューはしない — 方式・範囲・受け入れ条件を変えない追記のため
- [implement] ESLint の pre-commit フックを `SKIP=eslint` で飛ばした — ワークツリーのホストで動かない既知の問題（#468）。frontend コンテナで `npm run lint`（`--max-warnings 0`）を流して違反 0 を確かめた
- [implement] テストの仮のパスワードに `# pragma: allowlist secret` を付けた — detect-secrets の誤検知（テスト用の仮の値）
- [implement] `/simplify` で直したもの: 目標の条件の重複・進み具合の割合の 2 回計算・7 日の合計の 3 回の走査・正答率の文字を作る場所の統一（`_counts`）・`dataclasses.replace`・`timezone.localdate` の包み関数を外した。いずれも動作は変えない
- [implement] `/simplify` で見送ったもの: (1) 秒→分の切り捨てを `dashboardAchievements.ts`・`statistics/format.ts` と 1 か所にまとめる案と、日付の分解を `format.ts` の `partsOf` に寄せる案 — 計画で変えないとしたファイル（`format.ts`）と計画外のファイル（`dashboardAchievements.ts`）を触るため。グラフまわりの共通化は #516 で扱う (2) 目標の値を 1 つのフック（`useDailyGoalProgress`）に束ねる案 — 2 枚のカードの出す条件（記録が無いときに「学習を開始」の目標の行は出す）は I487 からの動きで、束ねると動作が変わる (3) 組織を `get_or_create` にする案 — 組織の slug は一意でなく、重複があると例外になるため `filter().first()` のまま (4) `useMemo`・`Intl.DateTimeFormat` の使い回し — 7 件の計算で差が無い
- [review-gate] CI の Backend Tests が失敗した（`CI_WAIT: FAIL`・Actions run 43664045176）ので fix-loop へ回す — review-gate の決まりどおり
- [fix-loop] 案 A（`verify_data.py` の QuizSession の 2 行に `# 組織で絞らない: <理由>` を書く）で直した — 診断レビュー PASS。動作を変えず I455 の決まりどおり。`for_user` 案は `bulk_update` に挟めず結局コメントが要るため、決まりのテストから外す案は安全装置を弱めるため採らない
- [review-gate] コードレビュー（`docs/reviews/I513_code_review_20261115_1045.md`）が止める指摘 F1・F2（Medium・再現あり）で HIGH。fix-loop へ回す — 決まりどおり
- [fix-loop] F1 は案 A（時刻を `rng.random()` 1 回で決める・TC-49）、F2 は案 A（数字のカードの進み具合は選んだ科目に記録があるときだけ出す・TC-30b を直す）で直した — 診断レビュー PASS。F2 は計画 9 章の自律判断の細部を直したもので、受け入れ条件・方式・範囲は変えないので計画レビューは通り直さない（計画変更記録に記載）。UI の判断は設計確認メモの委任の範囲
- [review-gate] 差分のレビュー（`docs/reviews/I513_code_review_20261115_1057.md`）OK・CI 全部合格・高リスクではない（敵対的レビューは不要）。test-gate へ
- [test-gate] 棒の tooltip は、グラフの中央の列（MCP の hover・click が当てる位置）で出して撮り、ほかの日は同じ値から作る棒の読み上げの文で見比べた — 座標を指定してマウスを動かすには任意のコードを動かす操作（`browser_run_code_unsafe`）が要り、手順書 §9 で避ける決まりのため。tooltip の文の作り方は TC-33 が固定している

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
