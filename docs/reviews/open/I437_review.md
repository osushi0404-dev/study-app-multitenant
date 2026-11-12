# I437 レビュー: 監視の記録から利用者のメールアドレスを外す（個人情報をログに残さない）

- 関連: docs/issues/open/I437.md / docs/plans/open/plan_I437.md / GitHub #437 / Draft PR #482

## 変更概要
監視の記録・API の呼び出しのログ・新規登録のログ・科目の取得のログ・開発時の表示から、メールアドレス（新規登録はパスワードも）を外して利用者 ID にした。エラーの送信内容の記録で個人情報の欄とリフレッシュトークンを伏せ、その場の変数を記録する印を開発環境だけで付けるようにした。

## 変更点
- `backend/core/monitoring.py`: `ErrorTracker.log_error`・`UserActivityMonitor.log_user_activity` から `user_email` を外した（`user_id` は元からある）
- `backend/core/middleware.py`: `RequestLoggingMiddleware.process_request` の `User:` を `str(request.user.id)` に
- `backend/accounts/views.py`: 新規登録で送信内容を丸ごと書く行を `Registration attempt for organization_id: <id>` に・成功のログと開発時の `print` を `user_id=<id>` に
- `backend/core/subject_service.py`: 43・91 行目の `User {user}` を `getattr(user, 'id', None)` に
- `backend/core/enhanced_logging.py`: 伏せる欄を、秘密は名前の一部（`SENSITIVE_BODY_WORDS`: `password`・`token`・`secret`・`refresh`・`api_key`）、個人情報と `value` は完全一致（`PERSONAL_BODY_FIELDS`: `email`・`first_name`・`last_name`・`user_id`・`value`）で照らす `_is_redacted_field` に（fix-loop F1）・`_log_exception` の `include_locals` を `settings.DEBUG` に
- `backend/core/tests/test_I437_no_pii_in_logs.py`（新規）: TC-01〜TC-08（10 件）

## 影響範囲
- ログ: `user_email` のキーが無くなり、`User:` の値が利用者 ID になる。新規登録のログに送信内容を書かない。エラーの送信内容で 5 つの欄が `[REDACTED]`。本番でその場の変数を書く印を付けない
- API・画面・DB・依存: 変わらない

## テスト結果
- 手元: 新しいテスト 11 件と I140・#446 が 150 passed（fix-loop の後）。Red（直す前に 8 件 FAIL）を確認（`docs/tests/open/I437_auto_test.md` の実行記録）
- CI: review-gate で確かめる

## 計画との差分
- AC4・TC-06 を「その場の変数を記録する印（`include_locals`）が `DEBUG` のときだけ付く」に直した（Red で、書く側の不具合で変数がどの環境でも書かれないと分かったため。計画の再レビュー OK）
- fix-loop（コードレビューの F1）で、秘密の欄を名前の一部で伏せる形に変え、`value` を足した（計画の再レビュー OK）
- /simplify で伏せる欄をつないだ定数を 1 回だけ作る形にし、テストの logger の捕まえ方とテスト名を直した（動きは同じ。計画変更記録）

## ロールバック
PR を revert する（コードとテストだけ・DB の形は変えない）。出力済みのログは消さない。

## 自律判断の記録
- [plan] 新規登録の送信内容を丸ごと書く行（パスワードが平文で入る・grill-me の後の全件確認で見つかった）は、伏せ字ではなく組織 ID だけを書く形にする — 欄が増えたときに漏れない
- [plan] `subject_service.py:43・91`（`str(user)` がメールアドレス）も直す — 全件確認で見つかった同じ型で、AC5 の範囲
- [plan] `user_agent`・`ip_address`・例外の文言・使われていない `logging_decorators.py` は直さない — 理由は plan_I437.md 1 章・9 章
- [plan] 決定論ゲート（ソースの grep）は置かず、動きを確かめる pytest で守る — 書き方が多様で文字の確かめでは捕まえられない
- [plan-review] 計画レビュー（OK・高リスク No）の Warning 2 件を直し、再レビューはしなかった — 記録の追記と観点の番号の直しだけで、方式・範囲・受け入れ条件を変えない
- [implement] Red で、その場の変数の記録は書く側（`DetailedFormatter`）の探し方の不具合でどの環境でも書かれていないと分かった。AC4・TC-06 を「印（`include_locals`）が `DEBUG` のときだけ付く」に直し、計画レビューをやり直した（OK） — 方針（`DEBUG` のときだけ）は変えない。書く側の不具合は直さず retro で扱いを決める
- [plan-review] 再レビューの Warning（イシューの AC と計画の AC4 の文言の違い）は、イシューの本文を直さない — イシューの AC「`DEBUG` が偽のとき変数が入らない」を計画の AC4 がそのまま含む（より細かく確かめるだけ）
- [implement] /simplify の 4 観点を 2 体にまとめて回した — 差分が小さく 4 体は過剰。`subject_service.py:125` の直しの指摘は誤り（来るのは未ログイン・なしだけ）として見送った。ほかの見送りは計画変更記録
- [fix-loop] コードレビューの F1（`confirm_password` が伏せられない）を、案 B（秘密は名前の一部・個人情報は完全一致）で直した。同型の `FieldValidationView` の `value` も同じ直しに入れた — 秘密は名前の揺れで漏れたのが原因で、名前の一部で止めると同型を根本から止められる。診断レビュー PASS・方式を変えたので計画レビューをやり直した（OK）
- [plan-review] fix-loop の再レビューの Warning 2 件は直さない — TC-10 は 1 回の pytest にファイルを並べるだけで束ねたコマンドではない。`user_actions` の追跡は retro で起票か同梱を決める（計画に記録済み）
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
