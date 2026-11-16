# I539 自動テスト: 招待なしの会員登録を完了できるようにする（利用者ごとの個人用の組織）

実行コマンド（例）: `docker compose exec -T backend pytest accounts/tests/test_I539_personal_org_signup.py accounts/tests/test_I140_personal_org_fallback.py accounts/tests/test_I131_org_id_rename.py problems/tests/test_I115_public_unauth.py core/tests/test_I446_cross_api_tenant_isolation.py core/tests/test_I437_no_pii_in_logs.py core/tests/test_I493_openapi_contract.py -q` / `docker compose exec -T frontend npx jest src/pages/__tests__/Register.test.tsx src/pages/__tests__/Dashboard.test.tsx --watchAll=false` / E2E は CI（`.github/workflows/e2e.yml`）

pytest・Jest・E2E は CI が PR ごとに流す（正）。実装中は上の関係するテストだけを手元で流す。

結果:
- backend: 実装中に手元で関係するテストを流して 200 passed（`accounts/tests/`・`test_I115`・`test_I446`・`test_I437`・`test_I493`）。CI の Backend Tests も合格（review-gate 2 回目・2026-11-16）
- frontend: 手元で `Register.test.tsx`・`Dashboard.test.tsx` の 46 passed。CI の Frontend Tests・Type Check・Lint も合格
- E2E: 1 回目の CI で TC-50 が落ち（パスワードの決まり・再発防止記録）、直した後の CI で 18 本すべて合格
- TC-21: `makemigrations --check --dry-run` → `No changes detected`（終了コード 0・2026-11-16）
- test-gate（2026-11-16）: 「## 決定論ゲート」に test-gate へ回す重いコマンドは無い。pytest・Jest・E2E は CI が正なので手元で流し直していない

## 共通の前提（backend）
- pytest は `--no-migrations`。テストの中で「個人利用」カテゴリ（`OrganizationCategory(slug='personal')`）を作る（TC-17 だけは作らない）
- 登録の回数制限は `settings.RATELIMIT_ENABLE = False`（I131・I140 と同じ方式）
- パスワードはテスト用のダミー値（`# pragma: allowlist secret`）
- 登録の本文の基本形: `{"user_id": <id>, "email": "<id>@example.com", "password": P, "password_confirm": P}`（`subject_ids` を入れるときは明記）
- 「個人用の組織」= `type='personal'` の組織。「共有の組織」= `type='personal'`・slug `personal` の組織（テストの中で作る）
- 個人用の組織の slug の形は、テストファイルの 1 つの定数 `PERSONAL_SLUG_RE = re.compile(r'^p-[0-9a-f]{12}$')` で TC-01 と TC-14 の両方が確かめる（4-2 と 0022 の規則のずれに気づけるように）

## backend: `backend/accounts/tests/test_I539_personal_org_signup.py`

| TC | 内容 | 期待値 | AC |
|---|---|---|---|
| TC-01 | `POST /api/auth/register/`（slug なし・`subject_ids` を入れない） | 201。本文の `organization == "i539_aさんの学習"`（ユーザー ID と「さん」の間に空白なし）。`User(user_id='i539_a')` の `role == 'admin'`・`organization.type == 'personal'`・`organization.name == 'i539_aさんの学習'`・`organization.slug` が `^p-[0-9a-f]{12}$` に一致・`organization.category.slug == 'personal'`・`organization.is_active is True`・`organization.is_individual is True`。その利用者の `UserSubjectAccess` は 0 件 | AC1・AC2 |
| TC-01b | 同じ登録を `subject_ids: []` で送る | TC-01 と同じく 201・学ぶ科目 0 件 | AC1 |
| TC-02 | 2 人（`i539_b1`・`i539_b2`）が slug なしで登録 | 両方 201。2 人の `organization_id` が異なり、slug も異なる。あわせて `accounts.services.pick_unused_slug(['p-aaaaaaaaaaaa', 'p-bbbbbbbbbbbb'])` を、slug `p-aaaaaaaaaaaa` の組織が既にある状態で呼ぶと `'p-bbbbbbbbbbbb'` を返す（乱数は差し替えない） | AC2 |
| TC-03 | slug なしで `subject_ids: [<学校の組織の科目の番号>]` と `subject_ids: [4539999]`（存在しない番号）をそれぞれ送る | どちらも 400・本文の `error.main_message == '入力内容にエラーがあります'`・`error.details.subject_ids == ['選択された科目の一部が無効です']`。2 つの応答の本文が同じ。利用者・組織の数が前後で変わらない | AC1・AC11 |
| TC-04 | 既にある `user_id` で slug なしの登録 | 400・`error.details.user_id == ['このユーザーIDは既に使用されています']`。組織の数が前後で変わらない（作りかけの組織が残らない） | AC2 |
| TC-05 | slug なしの登録の応答と、その利用者で `GET /api/auth/me/` | `me` の `organization_name == '<user_id>さんの学習'`・`role == 'admin'` | AC2 |
| TC-06 | slug なしで本文に `organization_id: <学校の組織の番号>` を入れて送る | 201。利用者の組織は新しい個人用の組織で、学校の組織ではない。学校の組織の利用者の数が前後で変わらない | AC2・AC11 |
| TC-07 | 個人用の組織（TC-01 で作ったもの）と共有の組織（slug `personal`）のそれぞれの slug で: `POST /api/auth/register/<slug>/`・`GET /api/organizations/validate-slug/<slug>/`・`GET /api/organizations/subjects/public/?slug=<slug>`・`GET /api/subjects/public/?slug=<slug>`（個人用の組織に科目を 1 件作っておく） | 登録は 400・本文が `{'error': {'main_message': '組織の設定に失敗しました', 'sub_message': '無効な組織URLまたはシステムエラー'}}` と完全一致・その組織の利用者の数が変わらない。slug の確認は 404・`{'valid': False, 'message': '組織 "<slug>" は見つかりません'}`。科目一覧は両方の経路で 200・`[]` | AC6 |
| TC-07b | `type` を渡さずに作った（種類が既定の `personal`・`is_individual=False`・カテゴリは「教育」）科目 1 件の招待用の組織 `e2e-like-i539` の slug で: 科目を選んで `POST /api/auth/register/e2e-like-i539/`・`GET /api/organizations/validate-slug/e2e-like-i539/`・`GET /api/organizations/subjects/public/?slug=e2e-like-i539` | 登録は 201・`role == 'user'`・組織は `e2e-like-i539`。slug の確認は 200・`valid is True`。科目一覧は 1 件 | AC6（招待用の組織の回帰） |
| TC-08 | 科目 0 件の学校の組織（`type='school'`）の slug で、`subject_ids` を入れずに登録 | 201。`role == 'user'`・組織はその学校の組織・学ぶ科目 0 件。組織の数が増えない | AC7 |
| TC-09 | 科目のある学校の組織の slug で、`subject_ids` を入れない／`[]` で登録 | どちらも 400・`error.details.subject_ids == ['科目を最低1つ選択してください']`・利用者が増えない | AC7（回帰） |
| TC-10 | 科目のある学校の組織の slug で、その組織の科目を選んで登録 | 201。`role == 'user'`・組織はその学校の組織・選んだ科目の `UserSubjectAccess` が 1 件（今の動きのまま） | AC7（回帰） |
| TC-11 | 個人用の組織の管理者（slug なしで登録した人）が `POST /api/subjects/`（`{"name": "科目I539", "description": ""}`） | 201。`UserSubjectAccess(user=本人, subject=作った科目)` が 1 件・`granted_by == 本人`。続く `GET /api/user/subjects/` の応答の `name` に `科目I539` が入る。同じ番号で 2 回目の `get_or_create` をしても 1 件のまま（関数を直接呼ぶ） | AC4 |
| TC-12 | 学校の組織（`type='school'`）の管理者と、種類が既定の `personal` の招待用の組織（`is_individual=False`）の管理者が、それぞれ `POST /api/subjects/` | どちらも 201。作った人の `UserSubjectAccess` は 0 件のまま | AC5 |
| TC-13 | 個人用の組織の管理者 A と B（どちらも slug なしで登録）。B が科目と問題を 1 件ずつ作る。A で `GET /api/subjects/`・`GET /api/user/subjects/available/`・`GET /api/problems/`・`GET /api/problems/<B の問題の番号>/`・`POST /api/subjects/`（A の科目）の後の `GET /api/user/subjects/` | A の一覧に B の科目・問題が入らない。B の問題の番号は 404。A の学ぶ科目は A の科目だけ | AC11 |
| TC-23 | `UserRegistrationSerializer(data=<正しい本文>, context={})` と `context={'organization': <学校の組織>, 'personal_category': <カテゴリ>}` で `is_valid()` | どちらも `django.core.exceptions.ImproperlyConfigured` が出る。組織・利用者の数が変わらない | AC2（fail-closed） |

### データマイグレーション（同じファイル）
マイグレーションのモジュール `accounts.migrations.0023_move_shared_personal_users` を `importlib.import_module` で読み込み、`move_shared_personal_users(django.apps.apps, None)` を直接呼ぶ（写しの関数を作らない）。

| TC | 内容 | 期待値 | AC |
|---|---|---|---|
| TC-14 | 共有の組織に、一般の利用者 `i539_m1`（`role='user'`）・`i539_m2`（`role='user'`）・運営 `i539_staff`（`is_staff=True`）・`i539_su`（`is_superuser=True, is_staff=False`）を置いて関数を呼ぶ | `i539_m1`・`i539_m2` はそれぞれ別の新しい組織（`type='personal'`・`is_individual=True`・名前「i539_m1さんの学習」など・slug `^p-[0-9a-f]{12}$`・カテゴリ `personal`）に移り、`role == 'admin'`。`i539_staff`・`i539_su` は共有の組織のまま・`role` も変わらない。共有の組織の一般の利用者は 0 人 | AC8・AC9 |
| TC-15 | TC-14 の後にもう一度関数を呼ぶ | 組織の数・各利用者の `organization_id`・`role` が 1 回目の後と同じ | AC10 |
| TC-16 | 共有の組織が無い／共有の組織に一般の利用者がいない（運営だけ）／「個人利用」カテゴリが無くて対象もいない、の 3 つで関数を呼ぶ | どれも例外なし・組織の数が変わらない。「個人利用」カテゴリが無いのに一般の利用者がいるときは `RuntimeError`（利用者は動かない） | AC10 |

## backend: 既存のテストの変更・確認

| TC | ファイル | 内容 | 期待値 | AC |
|---|---|---|---|---|
| TC-17 | `backend/accounts/tests/test_I140_personal_org_fallback.py` | 「個人利用」カテゴリが無い DB で slug なしの登録（今の TC-AUTO-01〜04 を読み替え）。TC-AUTO-04 は「非アクティブの共有の組織があってもカテゴリが無ければ 400」に読み替える | 400・本文が `{'error': {'main_message': '組織の設定に失敗しました', 'sub_message': '無効な組織URLまたはシステムエラー'}}` と完全一致。組織・利用者の数が変わらない。`django` のロガーに ERROR で `Personal organization category` を含む記録 | AC1（環境の異常の扱い） |
| TC-18 | `backend/accounts/tests/test_I131_org_id_rename.py` の TC-AUTO-06 | slug なしの登録（`subject_ids` なし・「個人利用」カテゴリを fixture で作る） | 201。利用者の組織は fixture の共有の組織（`personal`）ではなく、新しい個人用の組織 | AC2 |
| TC-19 | `backend/problems/tests/test_I115_public_unauth.py` | 変更なしで全件通る（TC-AUTO-05 の `''`・`register` は `[]`） | 全件 pass | AC6 |
| TC-20 | `backend/core/tests/test_I446_cross_api_tenant_isolation.py`・`backend/core/tests/test_I437_no_pii_in_logs.py` | 変更なしで全件通る（登録の 2 経路で、他組織の科目の番号と存在しない番号の応答が同じで利用者が増えない／登録のログにメール・パスワードが出ない・`Registration attempt for organization_id: <id>` が出る） | 全件 pass | AC11 |
| TC-21 | `docker compose exec -T backend python manage.py makemigrations --check --dry-run`（0022 を作った後） | モデルとマイグレーションの差分なし（0022 が `is_individual` の `AddField` を持つ） | 終了コード 0・`No changes detected` | — |
| TC-22 | `backend/core/tests/test_I493_openapi_contract.py` | 変更なしで通る（仕様書に載る経路を変えていない） | pass | — |

## frontend: `frontend/src/pages/__tests__/Register.test.tsx`（新規）
`AuthContext` の `register` と `apiClient.get`（slug の確認・科目一覧）を差し替える。`QueryClientProvider`（再試行なし）と `MemoryRouter` で描く。

| TC | 内容 | 期待値 | AC |
|---|---|---|---|
| TC-30 | `/register`（slug なし）で 1 段目を正しく入れて送る | 段の表示（「基本情報入力」「科目選択」）が無い。ボタンの名前は「登録する」。押すと `register(email, userId, password, firstName, lastName, undefined, [])` が 1 回呼ばれ、成功の文「登録が完了しました。メール認証を行ってからログインしてください。」が出る。科目一覧の API（`/api/organizations/subjects/public/`）は呼ばれない | AC1 |
| TC-31 | `/register/org-x`（slug の確認は `valid: true`・科目一覧は `[]`） | 段の表示が無い。ボタンは「登録する」。押すと `register(…, 'org-x', [])` が呼ばれる。「この組織には利用可能な科目がありません」は出ない | AC7 |
| TC-32 | `/register/org-x`（科目一覧が 2 件） | 段の表示がある。ボタンは「登録して次へ」。押すと 2 段目に科目のチェックが 2 つ出て、「登録を完了」は選ぶまで無効。1 つ選んで押すと `register(…, 'org-x', [<選んだ番号>])` | AC7（回帰） |
| TC-33 | `/register/org-x`（科目一覧の取得が 500） | 「科目を読み込めませんでした」と「再読み込み」が出る。送信のボタン「登録する」は無効で、入力欄で Enter を押しても `register` は呼ばれず、成功の文も出ない（送信の処理でも止める・止め方を外すと落ちることを確認済み）。「再読み込み」を押すと科目一覧をもう一度読み、2 件が返ると「登録して次へ」が押せるようになる | AC7 |

## frontend: `frontend/src/pages/__tests__/Dashboard.test.tsx`（直す）
`useAuth` の利用者を変数（`mockUser`）にして、テストごとに `role` を変えられるようにする（既定は今のまま `{ id: 'user-1', user_id: 'u_i473' }`・`role` なし）。

| TC | 内容 | 期待値 | AC |
|---|---|---|---|
| TC-05（直す） | 管理者でない利用者・選んだ科目も組織の科目も 0 件 | `role="status"` の文が「科目がまだ用意されていません。管理者が科目を用意するまでお待ちください」。「クイズを始める」は無効。「科目を作る」「問題を作る」のリンクが無い。「組織の管理者に科目の登録を依頼してください」は出ない | AC7 |
| TC-43 | `role: 'admin'`・選んだ科目も組織の科目も 0 件 | `role="status"` の文が「まず科目と問題を作りましょう。科目管理で科目を作り、問題管理でその科目の問題を作ると、クイズを始められます」。リンク「科目を作る」の `href` が `/subject-management`、「問題を作る」の `href` が `/quiz-management`。「クイズを始める」は無効。「管理者が科目を用意するまでお待ちください」は出ない | AC3 |
| TC-44 | `role: 'admin'`・選んだ科目 0 件・組織の科目 1 件 | 今の TC-40 と同じ「学ぶ科目を選ぶ」の案内（管理者でも、科目があるときは作る案内を出さない） | AC3（回帰） |

既存の TC-40〜TC-42 ほかはそのまま通る。

## E2E: `e2e/tests/auth.spec.ts`（追加・未認証のプロジェクト `chromium-unauthed` で動く）

| TC | 内容 | 期待値 | AC |
|---|---|---|---|
| TC-50 | 1) `/login` で「アカウントをお持ちでない方はこちら」を押す 2) メール・ユーザーID（`i539_<Date.now()>`）・パスワード（テストの中で作る `Aa1-<乱数の 16 進>`。`E2E_TEST_PASSWORD` は小文字と数字だけなので使わない）・確認を入れて「登録する」 3) 成功の文の後、`/login` に移る 4) そのユーザー ID とパスワードでログイン 5) ダッシュボードに「まず科目と問題を作りましょう」 6) 「科目を作る」→ 科目管理で「最初の科目を追加」→ 科目名 `E2E I539 <時刻>` → 保存 7) 問題管理（`/quiz-management`）で追加のボタン（`aria-label="add"`）→ 問題文・科目・選択肢（全部）・正解（A）・解説を入れて「作成」 8) `/dashboard` で「クイズを始める」 | 2) で段の表示が無い。3) で `/login` に移る。5) の案内が見え、「クイズを始める」は無効。8) で「クイズを始める」が押せ、科目が 1 件なので科目のダイアログを出さずに `/quiz` に移り、`[data-testid="choice-option"]` が出る | AC1・AC3・AC4・AC12 |

## 再発防止記録（fix-loop・2026-11-16）
- なぜ失敗したか: TC-50 が登録のパスワードに CI の `E2E_TEST_PASSWORD` を使った。CI はこの値を `openssl rand -hex 24`（小文字と数字だけ）で作るので、登録画面のパスワードの決まり（大文字を含む）で入力の検証に止められ、成功の文が出なかった（run 43868042699・診断メモ `docs/reviews/I539_fix_diagnosis_20261116_2141.md`）。手元の値は大文字を含むので手元では通っていた
- 何を変えたか: TC-50 は登録に使うパスワードをテストの中で作る（`Aa1-` ＋ `crypto.randomBytes(16)` の 16 進。大文字・小文字・数字・記号を含む）。CI の値・手元の値に依らない
- セキュリティ上の考慮点: パスワードをテストに書き込まない（毎回の乱数）。CI は trace を作らず、画面キャプチャのパスワード欄は伏せ字
- 次回どう防ぐか: 登録画面など入力の検証を通る E2E では、環境の秘密の値の形に頼らず、決まりを満たす値をテストの中で作る（`E2E_TEST_PASSWORD` は `seed_e2e` の利用者のログインにだけ使う）
- 確かめた結果: `docker compose --profile e2e run --rm e2e npx playwright test tests/auth.spec.ts --retries=0 --grep I539` → 1 passed（7.3s）。直す前の小文字だけの値で落ちることは CI の失敗（3 回とも同じ）で確かめ済み

## 決定論ゲート（自動実走）
このイシューは、pytest・Jest・E2E（CI が流す）で受け入れ条件を確かめる。grep 等の決定論ゲートは置かない（`docs/runbooks/plan-writing-rules.md`「決定論テストの対象の選び方」: 守る決まりは CI のテストで覆える）。
