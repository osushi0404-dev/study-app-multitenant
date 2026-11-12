# I437 自動テスト: 監視の記録から利用者のメールアドレスを外す（個人情報をログに残さない）

- 関連: docs/issues/open/I437.md / docs/plans/open/plan_I437.md / GitHub #437 / Draft PR #482
- 対象: `backend/core/tests/test_I437_no_pii_in_logs.py`（新規）と、守りにする既存のテスト
- 実行場所: app-1 ワークツリーのコンテナ（`docker compose exec -T backend ...`）。全テストは CI（PR #482）が正。手元では下の TC のファイルだけを流す
- 合否は終了コード（合格=0・不合格=非ゼロ）。回帰を止める TC は、直す前のコード（Red）で非ゼロになることを確かめる
- 下の表の `PYT` は `docker compose exec -T backend python -m pytest core/tests/test_I437_no_pii_in_logs.py -q` の略
- 下準備の利用者: `user_id="u_i437"`・`email="u_i437@example.com"`・`first_name="太郎I437"`・`last_name="山田I437"`（組織 slug `org-i437`・`role="user"`）。「ログ」は対象の logger（root・`django.request`。`django` は root に届く）に付けたハンドラーが集めた記録を、`DetailedFormatter` で整形した文字（`django.request` 以外は `record.getMessage()` も）とする

結果:
- backend: 新しいテスト 10 件と守りのテスト（I140・#446）が 149 passed。Red（直す前に 8 件 FAIL）を確かめた。CI は review-gate で確かめる
- frontend: 対象なし（画面の変更なし）

## 決定論ゲート（自動実走）
決定論ゲート（grep などの文字の確かめ）は置かない。ログに個人情報を書く形（`user.email`・`str(user)`・送信内容の丸ごと・その場の変数）は多様で、文字の確かめでは捕まえられない（plan_I437.md 9 章）。守る決まりは、動きを確かめる pytest（TC-01〜TC-08）が CI で毎回止める。

## 実行記録
| 日時 | コマンド | 終了コード | 結果 |
|---|---|---|---|
| 2026-11-12 | TC-01〜TC-10（実装前） | — | 実装前のため未実行（テストのファイルがまだ無い） |
| 2026-11-12 23:43 | Red: `PYT`（テストだけ足し、直す前のコード） | 1 | 8 failed・2 passed。TC-01〜TC-05・TC-07 の 1 件目・TC-08 が落ちた。TC-06 は 1 件目（DEBUG=False で変数なし）が通り 2 件目（DEBUG=True で変数あり）が落ちた → 書く側の探し方の不具合で変数がどの環境でも書かれないと分かり、TC-06 を「印（`include_locals`）」の確かめに直した（plan_I437.md 計画変更記録・計画の再レビュー OK） |
| 2026-11-12 23:44 | Red（TC-06 を直した後）: `PYT -k exception_log` | 1 | 1 failed（DEBUG=False で `include_locals` が `True`）・1 passed（DEBUG=True は直す前から通る） |
| 2026-11-12 23:5x | Green: `PYT` | 0 | 10 passed |
| 2026-11-12 23:5x | TC-09: I140・#446 | 0 | 139 passed |
| 2026-11-12 23:5x | TC-10（/simplify の後）: `PYT` と TC-09 のコマンドをまとめて | 0 | 149 passed |

## TC 一覧

| TC | 内容 | コマンド | 期待値 | 対応 AC |
|---|---|---|---|---|
| TC-01 | `test_error_tracker_has_no_email`: `ErrorTracker.log_error(ValueError("boom"), context={"path": "/api/x/"}, user=<下準備の利用者>)` と、`user=None` の呼び出し | `PYT -k error_tracker_has_no_email` | exit 0。戻り値の dict に `user_email` のキーが無く、`user_id == str(user.id)`（`user=None` では `None`・例外なし）。ログに `u_i437@example.com` が無い。Red: 直す前は `user_email` があり exit 非ゼロ | AC1 |
| TC-02 | `test_user_activity_has_no_email`: `UserActivityMonitor.log_user_activity(user, "view_problems", {"path": "/api/problems/"})` | `PYT -k user_activity_has_no_email` | exit 0。ログの `User Activity:` の行の JSON に `user_email` のキーが無く、`user_id == str(user.id)`。ログに `u_i437@example.com` が無い。Red: 直す前は exit 非ゼロ | AC1 |
| TC-03 | `test_request_logging_uses_user_id`: `RequestFactory().get("/api/problems/")` に `request.user = <利用者>` を入れて `RequestLoggingMiddleware(get_response).process_request(request)`。未ログイン（`AnonymousUser`）でも同じく呼ぶ | `PYT -k request_logging_uses_user_id` | exit 0。ログの `[START]` の行が `User: <user.id>` で終わり、`u_i437@example.com` が無い。未ログインでは `User: anonymous`。Red: 直す前は `User: u_i437@example.com` で exit 非ゼロ | AC2 |
| TC-04 | `test_registration_logs_have_no_email_or_password`: `POST /api/auth/register/org-i437/`（JSON・`user_id="i437_new"`・`email="i437_new@example.com"`・`password`／`password_confirm` は `I437TestPass123!`・`subject_ids=[科目]`）。`RATELIMIT_ENABLE=False` | `PYT -k registration_logs_have_no_email_or_password` | exit 0。応答 201。ログに `i437_new@example.com` と `I437TestPass123!` が無い。`Registration attempt for organization_id: <組織 ID>` と `User created successfully: user_id=<作られた利用者の id>` の行がある。Red: 直す前は送信内容とメールアドレスの行があり exit 非ゼロ | AC2 |
| TC-05 | `test_subject_service_logs_user_id`: 組織の無い利用者（`user_id="u_i437_noorg"`・`email="u_i437_noorg@example.com"`・`organization=None`）で `SubjectService.get_user_subjects(user)` と `SubjectService.get_subject_by_id(1, user)` | `PYT -k subject_service_logs_user_id` | exit 0。ログの `has no organization_id` の行が 2 件とも `User <user.id> has no organization_id` で、`u_i437_noorg@example.com` が無い。`user=None` でも `User None has no organization_id`（例外なし）。Red: 直す前は exit 非ゼロ | AC5 |
| TC-06 | 2 件: `test_exception_log_has_no_locals_when_not_debug`（`settings.DEBUG=False`）と `test_exception_log_has_locals_when_debug`（`settings.DEBUG=True`）。`get_response` の中で `user_email = request.user.email` を変数に置いてから `RuntimeError` を投げる関数で `ErrorContextMiddleware` を作り、`RequestFactory().get("/api/x/")`（`request.user` は利用者）で呼ぶ | `PYT -k exception_log_has` | exit 0。DEBUG=False: `RuntimeError` が外に出て、`django.request` の記録の `include_locals` が `False`。記録を整形した JSON の `error_context.stack_frames` のどれにも `locals` が無く、`u_i437@example.com` が無い。`stack_frames` の各要素に `file`・`line`・`function` がある。DEBUG=True: 記録の `include_locals` が `True`（切り替えが効く確かめ。変数そのものは今の書く側の不具合で書かれないので確かめない・plan_I437.md 計画変更記録）。Red: 直す前は DEBUG=False の 1 件が exit 非ゼロ（DEBUG=True の 1 件は直す前から通る） | AC4 |
| TC-07 | 2 件: `test_error_body_redacts_personal_fields`・`test_error_body_adds_no_missing_fields`。`RequestFactory().post("/api/auth/login/", data=<フォーム>)`（`email`・`first_name`・`last_name`・`user_id`・`refresh`・`password`・`subject_ids` に値）で、400 を返す `get_response` の `ErrorContextMiddleware` を呼ぶ。後者は `password` だけを送る呼び出しも足す | `PYT -k error_body` | exit 0。記録の `request.body` で `email`・`first_name`・`last_name`・`user_id`・`refresh`・`password` が `[REDACTED]`、`subject_ids` は送った値のまま。`password` だけを送ったときの body に `email` などのキーが足されない。ログに `u_i437@example.com`・`太郎I437`・`山田I437` が無い。Red: 直す前は 1 件目が exit 非ゼロ（2 件目は直す前から通る） | AC3 |
| TC-08 | `test_debug_print_has_no_email`: `settings.DEBUG=True` で `UserRegistrationView().send_verification_email(user)` を呼び、`capsys` で標準出力を取る | `PYT -k debug_print_has_no_email` | exit 0。出力に `u_i437@example.com` が無く、`user_id=<user.id>` がある。`EmailVerification` が 1 件できる。Red: 直す前は exit 非ゼロ | AC5 |
| TC-09 | 守りのテスト: I140 の登録（ログの確かめを含む）と #446 の横断 | `docker compose exec -T backend python -m pytest accounts/tests/test_I140_personal_org_fallback.py core/tests/test_I446_cross_api_tenant_isolation.py -q` | exit 0（全件 passed） | AC6 |
| TC-10 | /simplify の後の流し直し | `PYT` と TC-09 のコマンド | どちらも exit 0 | AC1〜AC6 |

- CI: 上のファイルは CI の Backend Tests（`pytest`・PostgreSQL）で毎回流れる（AC6）。review-gate が `gh pr checks 482` で確かめる
