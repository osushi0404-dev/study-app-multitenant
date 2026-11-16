# I491 レビュー: I473 のレビューの残り（科目のキャッシュ・連続日数・E2E の比べ方・境界値・QuizAnswer の見張り）

## 変更概要
- 科目のキャッシュを「選んだ科目の番号の全部（組織で絞る前）」・利用者ごとに 1 つのキーにし、組織を移っても消し残し・取り違えが起きないようにする（F5）
- 連続日数を 365 日の窓で読み、頭打ちにせず数える（F7）
- E2E の解答数を「前の値より大きい」で比べる（F6）・学習時間の上限の境界値のテスト（B1）
- `QuizAnswer` に組織の境界つきの取り出し口（`for_user`）を持たせ、見張りの対象にする（Q1）
- F8 は直さない（#492 で消す）

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB/Config: Backend（`core/subject_service.py`・`problems/signals.py`・`problems/querysets.py`・`problems/models.py`・`dashboard/selectors.py`・`dashboard/verify_data.py`・テスト）・E2E（`quiz-session.spec.ts`）。Frontend・DB・Config なし

## テスト結果
- 自動: （test-gate で記入）
- 手動: （test-gate で記入）

## 計画との差分
- （実装後に記入）

## ロールバック
- PR を revert する（DB の変更なし。キャッシュは名前が変わるので期限で消える）

## 自律判断の記録
- [plan] F5 はキャッシュの中身を組織で絞る前の番号に変える — キーから組織を外すだけでは、組織を移った直後に移った先の科目が出なくなる（計画の調査で発見）
- [plan] F7 の窓は 365 日・窓で読み足す方式 — ふつうの利用者は 1 回の読み出しのまま、頭打ちにせず数えられる
- [plan] F6 は「前の値より大きい」— 専用の利用者を作るのはこの 1 本には重い。目的（0 のままの再発防止）は守れる
- [plan] Q1 は `OrgScopedQuerySet` に持ち主への経路を足して `QuizAnswer` を載せる — 見張りが登録から自動で対象にする
- [plan] 範囲外の `problems/views.py:571`（無い項目 `created_at` で絞る）は直さず、retro で #460 に同梱する

STAGE_DONE: plan NEXT: plan-review
