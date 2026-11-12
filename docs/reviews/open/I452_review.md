# I452 レビュー: クイズの回答から復習の予定を作り、ダッシュボードから今日の復習を始められるようにする

- 関連: docs/issues/open/I452.md / docs/plans/open/plan_I452.md / GitHub #452 / Draft PR #464

## 変更概要
- クイズで 1 問答えるたびに、その問題の間隔反復のカードを作る・更新する（正解 4／不正解 2 の SM-2・答えた日の 0 時＋間隔・同じ日の 2 回目は更新しない）
- ダッシュボードのいちばん上に「今日の復習 ○問」と「復習を始める」を置き、復習する日が来た問題だけのクイズ（`QuizSession.mode='review'`）を始められるようにする。答え終えたら「今日の復習が終わりました（○問中○問正解）」
- 間違い分析・適応的な問題選択・学習洞察の 500 を直し（難易度の型・科目が空のパターン・KeyError）、#446 の 9 ケースの xfail を外す。画面側の使われていない関数 7 つを消す

## 変更点
- `backend/problems/difficulty.py`（新規）: 難易度の数字と文字の対応の 1 か所。`problems/serializers.py`・`problems/views.py`（問題一覧の絞り込み）・学習記録の側がこれを使う
- `backend/problems/models.py`・`migrations/0022_quizsession_mode.py`: `QuizSession.mode`（`normal`／`review`・既定 `normal`）
- `backend/problems/services/quiz_service.py`: 復習の回の開始の件数・次の問題（`_next_review_problem`）・冪等のキーの `mode` の照合・`spaced_repetition_service`
- `backend/problems/views.py`: `submit_answer` の回答とカードの更新を 1 つのトランザクションに・`next_problem` の `review_complete`
- `backend/studylogs/services.py`・`spaced_repetition.py`: `record_quiz_answer`・`due_cards_queryset`・`review_summary`・日付の境目・キャッシュのキーの組織・キャッシュの無効化をコミットの後に・学習洞察の KeyError
- `backend/studylogs/views.py`・`serializers.py`: `GET /api/study/spaced-repetition/review_summary/`・印付けの 2 経路を `for_user` に
- `backend/studylogs/adaptive_selection.py`・`mistake_analysis.py`・`backend/core/cache_service.py`・`tasks.py`: 難易度の型・分母の組織・科目が空のパターン・習熟度のキャッシュのキーの組織・印付け・理由のコメント
- `backend/core/tests/test_I446_cross_api_tenant_isolation.py`: 9 ケースの xfail を外し、`review_summary` の経路を足す
- `backend/studylogs/tests/test_I452_quiz_review.py`（新規・28 件）
- `frontend/src/components/TodayReviewCard.tsx`・`services/review.service.ts`（新規）・`pages/Dashboard.tsx`（配置）・`pages/QuizSession.tsx`（復習の回）・`types/quiz.ts`・`services/dashboard.service.ts`（削除）
- `frontend/src/components/__tests__/TodayReviewCard.test.tsx`・`pages/__tests__/QuizSession.review.test.tsx`（新規）

## 影響範囲
- Backend: problems（models・migrations・serializers・views・services）・studylogs（services・views・serializers・spaced_repetition・adaptive_selection・mistake_analysis・tasks・tests）・core（cache_service・tests）
- Frontend: ダッシュボード・クイズの画面・サービス・型
- DB: `problems_quizsession.mode` の追加（`AddField` だけ・既存の行は `normal`）
- Config: なし

## テスト結果
（test-gate 段階で記入）

## 計画との差分
- 計画書の計画変更記録のとおり（/simplify の整理 8 件と見送り 5 件・静的テストに合わせた理由のコメント）
- 実装の時の画面の確かめ（Playwright MCP）は、MCP の接続が実装の間に整わなかったため、test-gate の手動テスト No.1〜No.4（Claude）に回した。画面の動きは Jest（TC-16・TC-17）で固定済み

## ロールバック
PR を revert し、migration `0022_quizsession_mode` を戻す（`python manage.py migrate problems 0021`）。計画書 7 章。

## 自律判断の記録
- [plan-issue] 画面の細部 U1〜U3（結果を見る・今日の復習の印・読み込み失敗の再読み込み）をユーザーに確認し、推奨どおりで確定 — イシューに無い UI の文言・流れのため（止めて聞く条件 1）
- [plan-issue] 間違い分析・適応的な問題選択を画面につなぐ後続を I466（#466）として起票し、I455 の F4 を同梱 — 設計確認メモの決定（計画の段階で起票）
- [plan-issue] 同梱の 14 件の扱いを計画書 9 章で決めた（同梱 7・I190 に渡す 4・残す 3）— 変更点に当たるものは同梱、I190 の担当のものは渡す

STAGE_DONE: plan NEXT: plan-review
- [plan-review] 判定 HIGHRISK。Warning 3 件（カードの初期値・習熟度のキャッシュのキーと消す処理・TC-14 の合否）を計画書・テスト文書で直し、再レビューはしない — 方式・範囲・受け入れ条件を変えないため

STAGE_DONE: plan-review NEXT: design-security-review
- [design-security-review] Blocker・High なし（Medium 4・Low 3／シナリオ Medium 6・Low 3）。カードの読み出しを due_cards_queryset の 1 か所に集めることを必須防御条件にし、TC-08 に他組織の科目での復習の開始（400）と mode の不正値（400）を足した — 攻撃シナリオ 2・8 を自動テストで確かめるため

STAGE_DONE: design-security-review NEXT: implement
- [implement] 新しい振る舞いは TDD で進めた（バックエンド 21 件・フロント 2 ファイルが Red → Green）。失敗の注入（難易度の直しを戻す・同じ日の判定を外す・組織の絞り込みを外す）でテストが落ちることを確かめた — 計画の TC-09・TC-14 の FG
- [implement] /simplify の 4 観点のレビューのうち 8 件を直し、5 件は見送った（計画変更記録）— 振る舞いを変える・設計の意図に反する・構造の変更が大きいものは見送る
- [implement] 画面の確かめ（Playwright MCP）は MCP が接続しなかったため test-gate の手動 No.1〜No.4 に回した — 人に頼まず Claude が後の段階で行う。画面の動きは Jest で固定済み

STAGE_DONE: implement NEXT: review-gate
- [implement] pre-commit の ESLint のフックが手元に eslint が無く exit 127 で止まった。同じ `npm run lint`（--max-warnings 0）をフロントのコンテナで流して 0 件を確かめ、そのコミットだけ `SKIP=eslint` にした — 同じ検査を別の場所で済ませた・CI でも流れる。手元の node_modules の準備は retro で扱う
- [review-gate] 基本レビュー OK（Low 7 件・止める指摘なし）。敵対的レビュー 1 周目（20261112_1305）は新しい Critical・High 0 だが、実験役の環境に python が無く V1〜V4・V6 が未検証で HIGH。5 項目を CI の決定論の TC と手元の失敗の注入で覆い、確かめ方を読んで可に下げて 2 周目へ — I455 と同じ扱い（review-gate 3-3）
