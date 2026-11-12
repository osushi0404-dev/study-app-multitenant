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
- CI: PR #482 の 7 ジョブすべて pass（`7db26617`）
- 手動: No.1・No.2 とも OK（Claude が dev のコンテナでログのファイルを確かめた。`docs/tests/open/I437_manual_test.md`）

## 計画との差分
- AC4・TC-06 を「その場の変数を記録する印（`include_locals`）が `DEBUG` のときだけ付く」に直した（Red で、書く側の不具合で変数がどの環境でも書かれないと分かったため。計画の再レビュー OK）
- fix-loop（コードレビューの F1）で、秘密の欄を名前の一部で伏せる形に変え、`value` を足した（計画の再レビュー OK）
- /simplify で伏せる欄をつないだ定数を 1 回だけ作る形にし、テストの logger の捕まえ方とテスト名を直した（動きは同じ。計画変更記録）

## ロールバック
PR を revert する（コードとテストだけ・DB の形は変えない）。出力済みのログは消さない。

## 振り返り

### かんたんなまとめ
**良かった点**
- 設計確認のときにログを書く所を全部調べたので、イシューに書かれた 2 か所のほかに、新規登録でパスワードを丸ごとログに書いていた所など、より重い漏れを見つけて一緒に直せた（理由: 一部だけ直すと、同じ原因の漏れが残ったままになる）
- テストを先に書いて直す前のコードで流したので、「その場の変数を記録する」機能が実はどこでも動いていないことに、コードを書く前に気づけた（理由: 間違った前提の受け入れ条件のまま進まずに済んだ）
- レビューで見つかったパスワード確認欄の漏れは、欄を 1 つ足すだけでなく、名前の付け方が違っても伏せる形に直した（理由: 同じ型の漏れをまとめて止められる）

**今回の問題への直接の対処**
- レビューで止めなかった残り 5 件と、計画で「あとで決める」とした 3 件（使われていないログのコード・画面側の伏せ方・動かない変数の記録）を、後続のイシュー I484（#484）にまとめた。どれも今すぐの実害は小さいが、「ログに個人情報を残さない」決まりが場所によって割れたままになるため

**同じ問題を次回から防ぐ改善**
- 新しい決まりの追加は見送った。今回の 3 つのつまずき（受け入れ条件の前提違い・パスワード確認欄の漏れ・手動テストの期待値の書き誤り）は、どれも流れの中のテスト・レビューでその場で捕まり、手戻りは計画レビュー 1 回と修正 1 周で済んだため

### 詳細
**良かった点**
- grill-me の全件確認で P4（新規登録の送信内容の丸ごとログ・パスワード平文）・P7 を見つけて同梱した
- implement の Red で AC4 の前提違い（`DetailedFormatter` の変数の探し方の不具合）を実装前に見つけ、計画を直して再レビューした
- fix-loop で F1 を案 B（秘密は名前の一部）で根本から直し、同型の `value` も同梱した

**是正処置（Corrective）**
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | セキュリティ・残余 | ログを書くコードごとに伏せる決まりを個別に持ち、例外の文言・`query_params`・`user_actions`・JSON の本文の経路・使われていないコードが残った | I484（#484）に台帳の残り F2〜F6 と計画で retro に回した 3 件をまとめて起票 |

**予防処置（Preventive）**: なし（下の見送りを参照）

**見送り（手順 2.7 の 4 問）**
- 計画で AC4 を「開発では変数が入る」と書いた（既存機能が動いている前提を確かめなかった） — 実害: 計画レビュー 1 回のやり直し。implement の Red（テスト先行）でその場で捕まった。決まりは足さない
- 計画の全件確認がログを書く所だけを見て、伏せる一覧と API の欄の名前の突き合わせをしなかった（F1） — review-gate で捕まり fix-loop 1 周で直った。直し方（名前の一部で伏せる）で同型は今後も止まる。決まりは足さない
- 手動テストの期待値（No.1 の 200）を権限を確かめずに書いた — test-gate で捕まり、記録の書き誤りとして扱った（ログの確かめる点は満たす）。手戻りなし

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
- [test-gate] 手動テスト No.1 のトークンは、ログインの API ではなく dev DB の利用者から作った — パスワードの値がコンテナに無い。確かめるログは同じ。No.1 の応答の 403 は問題の一覧が管理者だけの API（I102）だからで、期待結果の 200 は計画の書き誤りとして OK にした（ログの確かめる点はすべて満たす）
- [retro] 台帳の残り F2・F3・F4・F5・F6 → #484（後続イシュー「ログの個人情報・秘密の残りを片付ける（I437 のレビューの残り）」・SECURITY=yes を含むので本文に「次のハーネスの作業で最優先」を書いた）。一覧（backlog）行きは 0 件
- [retro] 計画で retro に回した 3 件（`logging_decorators.py` の扱い・`user_actions` の送る側の伏せ字・`DetailedFormatter` の変数の記録の不具合）→ 同じ #484 に同梱 — 同じ原因（伏せる決まりが 1 か所に無い・動かないログのコード）で、まとめて決めるほうが安い
- [retro] 予防処置は足さない（AC4 の前提違い・F1・手動テストの期待値） — どれも流れの中でその場で捕まり、手戻りが小さい（「## 振り返り」の見送り）
- [close] develop への追従は不要（BEHIND でない）。`I437_fix_diagnosis_20261113_0002.md`（診断メモ）は close の回収の対象（`_review_` を含む記録）に当たらないので `docs/reviews/` に残した — I459 までの close と同じ扱い
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
STAGE_DONE: close NEXT: merge
