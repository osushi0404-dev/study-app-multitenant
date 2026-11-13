# I473 レビュー: ダッシュボードの数字をクイズの記録から出す

## 変更概要
- ダッシュボードの数字の出どころを、どこからも書かれていなかった学習ログ（`StudyLog`・`DailyStudySummary`）から、クイズの答えの記録（`QuizAnswer`）に 1 本化した。応答の形をシリアライザで固定し、画面は形を確かめて、違えば 0 で埋めずにエラーの文を出す
- 科目の選択（`subject_id`）を効かせ、不正な値は同じ 400。おすすめを overview に入れ、`/api/dashboard/recommendations/` を消した
- #467 の引き継ぎ 3 件（おすすめの NOT IN に NULL・学習記録を作るときの閉じる範囲・科目のキャッシュの並び順とキー）を直した

## 変更点
- `backend/dashboard/selectors.py`（新設）: `build_overview(user, subject=None, *, now=None)`。`QuizAnswer` を読むのは `_answers()` の 1 か所（本人・自組織の科目の問題に絞る）。今日・全期間・直近 7 日・連続日数・間違いやすい分野・おすすめ。1 回の表示で 9 クエリ（データの量で変わらない）
- `backend/dashboard/serializers.py`: `OverviewQuerySerializer`（`OrgSubjectField`）・`OverviewSerializer` と入れ子のシリアライザ
- `backend/dashboard/views.py`・`urls.py`: overview を入力の確かめ → セレクタ → シリアライザだけにした。`SubjectRecommendationView` と経路を削除。analytics は変えない（#488）
- `backend/studylogs/views.py`: `StudyLogViewSet.create` で閉じる対象を `for_user`（自組織の科目・科目なし）に絞った
- `backend/core/subject_service.py`・`backend/problems/signals.py`: キャッシュのキーを関数 `user_subjects_cache_key`（組織入り）にし、無効化と共有。キャッシュの経路と DB の経路で組み立てを 1 か所にした（並び順のずれの根治）
- `frontend/src/services/types.ts`・`dashboard.service.ts`: `DashboardOverview` 型・`getOverview`（応答の形を一覧の中身まで確かめる）。`getRecommendations` を削除
- `frontend/src/pages/Dashboard.tsx`: 既定値で 0 を埋める処理を削除。失敗・形の違いはエラーの文。データ無しは赤い円の代わりに「まだ解答の記録がありません」・正答率「—」。見出し「直近 7 日の学習時間」。おすすめの「練習する」はその科目のクイズへ
- テスト: `backend/dashboard/tests/test_I473_overview.py`（新設・22 件）、`frontend/src/pages/__tests__/Dashboard.test.tsx`（新設・7 件）、`e2e/tests/quiz-session.spec.ts`（1 本追加）、I431・I446・I459 のテストを新しい形に合わせた

## 影響範囲
- Backend: dashboard（overview・recommendations の削除）、studylogs の学習記録の作成、科目のキャッシュ
- Frontend: ダッシュボードの画面・サービス・型
- DB: 変更なし（マイグレーション無し）
- Config: 変更なし

## テスト結果
- 自動（手元・implement）: backend `dashboard/`・`test_I431`・`test_I455`・`test_I446` 215 件 pass／frontend `Dashboard.test.tsx` 7 件 pass／型チェック・本番ビルド OK／E2E は CI。false-green の確かめ 4 件（TC-12・13・03・22）を実施し、TC-22 の false-green を見つけて直した（自動テスト文書）
- 手動: （test-gate で行う）

## 計画との差分
- あり（どれも方式・範囲・受け入れ条件は変えない）: 計画書の「計画変更記録」の implement・`/simplify` の行のとおり（signals の消し方を読む側と同じ経路に・TC-22 の補強・TC-12 の本数 9・形の確かめを要素まで・`loadError` の削除・科目のキャッシュの組み立ての 1 本化・選んだ科目の問題だけを調べる）

## ロールバック
- PR を revert する（DB・設定の変更なし）

## 自律判断の記録
- [plan] 集計の置き場所を `backend/dashboard/selectors.py` にした — 規約 6 章で読み取り専用の処理はセレクタに置くため（イシューは services.py の名前で書いていた）
- [plan] 他組織の問題への答えは数だけの集計でも除く — `Problem.subject` は必須で、絞っても自組織の数字が変わらない。土台を 1 つにして漏れを防ぐ
- [plan] データ無し・失敗・苦手 0 件の文言を最小限で決めた — 作り込みは #487。ユーザーの指示「BP・UI/UX の観点で問題ないやり方で」の範囲
- [plan] おすすめの苦手の判定を間違いやすい分野と同じ決まり（5 問以上・70% 未満）にそろえた — 1 問の間違いで苦手と出さないため
- [plan-review] 計画レビューの Warning・Info 6 件のうち 5 件を直し、TC-12 の上限は実装後に書く — どれも方式・範囲・受け入れ条件を変えないので再レビューしない。「科目別の進み具合」の読み方は close でユーザーに伝える
- [design-security-review] Blocker・High なし。Medium の必須条件（QuizAnswer を読むのは範囲の土台 1 か所だけ）を計画書に書き、TC-13 に組織なしの利用者を足した — QuizAnswer は I455 の見張りの対象外のモデルなので、作りで防ぎ review-gate で確かめる
- [implement] TC-22 の false-green を直した — `totals` を欠く応答は別の例外でたまたまエラー表示になり、形の確かめを外しても通っていた。`last_7_days` を欠く応答を足して、確かめを外すと落ちることを確かめた
- [implement] クエリ数を 9 で固定した — 実装後に数えた本数。データを増やしても同じであることも同じテストで見る
- [implement] `/simplify` の 4 観点の指摘 15 件のうち 7 件を直し、8 件を見送った（理由は計画変更記録）— 振る舞いを変えるもの・契約を変えるもの・範囲外の既存の借りは見送り
- [implement] E2E は手元で流さず CI に任せた — 1 本の追加で、CI が PR ごとに全部流すため（手元で CI と同じものを流し直さない）
- [implement] 実装のコミットだけ `SKIP=eslint` にした — ワークツリーのホストに eslint が無くフックが exit 127 で止まる既知の問題（#468・I452 と同じ）。同じ `npm run lint` を frontend コンテナで流して違反 0 件を確かめた上で使った。CI の ESLint は通常どおり流れる
- [review-gate] 1 回目のコードレビューは CI 待ちの 20 分切れ（exit 3）で、CI は遅れて始まり全部合格していた。決まりどおり 1 回だけやり直した — CI の実行の待ち行列の遅れで、直すものは無い
- [review-gate] 止める指摘 F1〜F4（Medium・画面）で fix-loop へ。F5〜F8（Low）は台帳に残し retro へ — スクリプトの判定どおり
- [fix-loop] F1〜F4 を診断メモの推奨案（API の契約は変えず画面の出し分け・判定・取得の書き方だけを直す）で直した — 診断レビュー PASS。全科目の has_data を API に足す案は、この食い違いのためだけに契約を増やすので採らなかった
- [fix-loop] TC-28 は、読み込み中に画面全体が置き換わってセレクタが消えるため、テストのモックで「科目 5 を選んだ直後にすべてへ」をまとめて起こす形にした — 実際の画面で起こりうる順番（選択の直後に別の切り替えが届く）を再現するため

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
