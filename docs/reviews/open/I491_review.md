# I491 レビュー: I473 のレビューの残り（科目のキャッシュ・連続日数・E2E の比べ方・境界値・QuizAnswer の見張り）

## 変更概要
- 科目のキャッシュを「選んだ科目の番号の全部（組織で絞る前）」・利用者ごとに 1 つのキーにし、組織を移っても消し残し・取り違えが起きないようにする（F5）
- 連続日数を 365 日の窓で読み、頭打ちにせず数える（F7）
- E2E の解答数を「前の値より大きい」で比べる（F6）・学習時間の上限の境界値のテスト（B1）
- `QuizAnswer` に組織の境界つきの取り出し口（`for_user`）を持たせ、見張りの対象にする（Q1）
- F8 は直さない（#492 で消す）

## 変更点
- `backend/core/subject_service.py`: `user_subjects_cache_key(user_id)` → `user_selected_subject_ids_{id}`。`get_user_selected_subjects` はキャッシュに選んだ科目の番号（組織で絞る前）だけを入れ、組織の条件は毎回 DB で掛ける
- `backend/problems/signals.py`: 消すキーを 1 つに
- `backend/problems/querysets.py`: `OrgScopedQuerySet.user_path`（既定 `'user'`）
- `backend/problems/models.py`: `QuizAnswerQuerySet`（`session__user`・`problem__subject`）と `QuizAnswer.objects`
- `backend/dashboard/selectors.py`: `_answers` は `QuizAnswer.objects.for_user`。`_answer_days`・`_current_streak`（365 日の窓・`window_days` 引数）・`STREAK_WINDOW_DAYS`
- `backend/dashboard/verify_data.py`: `QuizAnswer.objects.bulk_update` の前に理由のコメント
- テスト: `dashboard/tests/test_I473_overview.py`（I491 の TC-01〜TC-06・クエリ数 8）・`problems/tests/test_I494_user_subjects.py`（TC-05 のキー）・`studylogs/tests/test_I455_org_scoped_querysets.py`（`SPECS` に `QuizAnswer`・TC-09・表現）
- `e2e/tests/quiz-session.spec.ts`: 「前の値より大きい」で比べる

## 影響範囲
- Backend/Frontend/DB/Config: Backend（`core/subject_service.py`・`problems/signals.py`・`problems/querysets.py`・`problems/models.py`・`dashboard/selectors.py`・`dashboard/verify_data.py`・テスト）・E2E（`quiz-session.spec.ts`）。Frontend・DB・Config なし

## テスト結果
- 自動: （test-gate で記入）
- 手動: （test-gate で記入）

## 計画との差分
- ダッシュボードの 1 回の表示のクエリ数が 9 → 8（計画は「変わらない」）。F5 でキャッシュを作るときの 2 本が 1 本になったため（計画変更記録）

## ロールバック
- PR を revert する（DB の変更なし。キャッシュは名前が変わるので期限で消える）

## 自律判断の記録
- [plan] F5 はキャッシュの中身を組織で絞る前の番号に変える — キーから組織を外すだけでは、組織を移った直後に移った先の科目が出なくなる（計画の調査で発見）
- [plan] F7 の窓は 365 日・窓で読み足す方式 — ふつうの利用者は 1 回の読み出しのまま、頭打ちにせず数えられる
- [plan] F6 は「前の値より大きい」— 専用の利用者を作るのはこの 1 本には重い。目的（0 のままの再発防止）は守れる
- [plan] Q1 は `OrgScopedQuerySet` に持ち主への経路を足して `QuizAnswer` を載せる — 見張りが登録から自動で対象にする
- [plan] 範囲外の `problems/views.py:571`（無い項目 `created_at` で絞る）は直さず、retro で #460 に同梱する
- [plan-review] Info 3 件（表現・コメント・並びの期待値）を直し、再レビューはしない — 方式・範囲・受け入れ条件を変えないため
- [design-security-review] Blocker・High なし。Medium 2 件（キャッシュの中身を読むのは 1 か所・`user_path` はクラスの定数だけ）を実装の必須条件にした — どちらも計画の作りのまま守れ、TC-02・TC-08 で確かめる
- [implement] クエリ数のテストの期待値を 9 → 8 に直した — 減った理由が F5 の作りの結果で、計画レビューのやり直しは要らない（計画変更記録）
- [implement] /simplify の 4 観点の指摘のうち直したもの: キャッシュを使わない読み出しはサブクエリのまま 1 本に戻す・連続日数のループの初回の分岐をループの前に出す・テストのキャッシュの片付けを 1 つの関数とフィクスチャにまとめる・I494 TC-05 を 1 つのキーの形に・不要なコメントと重複の確かめを消す・テストから private 関数を読まない — どれも動きを変えない整理
- [implement] /simplify の指摘で見送ったもの: LOCMEM の設定を conftest で 2 ファイル共有（計画の外のファイルを触るため・写しは 4 行）／空の選択もキャッシュする（動きが変わる）／TC-05 を 366 の 1 通りに絞る（365 ちょうども計画の確かめ）／E2E を専用の利用者で厳密に（計画の R5 で受け入れ済み。答える spec を足すときに見直す）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
