<!--
## 自動テスト品質基準
各テストケースが以下を満たすことを確認してください:
- アサーションに具体的な期待値（status_code の数値・body の具体フィールド等）があるか
- 「正常レスポンスを確認」のような曖昧な記述になっていないか
- 他テナントデータへのアクセス拒否テストが含まれているか（認可変更がある場合）
- テストが実装詳細をトレースするだけでなく、仕様を検証する形になっているか
-->

# I636 自動テスト: 登録用リンクとメンバー管理のレビューの残りを直す

実行コマンド（例）: `docker compose exec backend pytest accounts/tests/test_I620_registration_links.py accounts/tests/test_I636_member_access.py core/tests/test_I493_openapi_contract.py` / `docker compose exec frontend npm test -- --watchAll=false src/components/__tests__/Layout.members.test.tsx src/pages/__tests__/MemberManagement.test.tsx src/pages/__tests__/PasskeySetup.test.tsx` / e2e は `docs/runbooks/frontend-verify.md` §8（pytest・Jest・E2E の正は CI）

結果:
- backend（2026-11-27・手元）: `accounts`・`core/tests/test_I493_openapi_contract.py`・`core/tests/test_I446_cross_api_tenant_isolation.py` の 271 件が通過（`test_I620_registration_links.py`・`test_I636_member_access.py` を含む）
- frontend（2026-11-27・手元）: 関係する 8 ファイル 69 件・`tsc --noEmit`・`npm run lint` が通過
- e2e（2026-11-27・手元の e2e コンテナ・RP ID `frontend`・`--retries=0`）: 全体 21 件が通過。`--repeat-each=2` の 42 件も通過（TC-28 は再現せず）
- 失敗の注入: TC-01・TC-04・TC-06・TC-08・TC-10・TC-11 は直す前に落ちた。TC-02・TC-03 の注入の版は 200・`[200, 200]` になる。TC-09 はダイアログの直しを外すと落ち、TC-13 は通知を右上に戻すと落ちた（どちらも戻して通過）

## 前提（テストの道具）
- 裏側は I620 の下準備（`test_I620_registration_links.py` の `people`・`issued_token`・`link_options`・`complete`・`_make_unusable`・`reauth`）を使う。WebAuthn の応答は I619 の `SoftAuthenticator` で作り、py_webauthn の検証は差し替えない
- エラーの形: 400 は `{"error": {"main_message": "入力内容にエラーがあります", "sub_message": <文>, ...}}`、403 は `main_message: "アクセスが拒否されました"`、404 は `main_message: "リソースが見つかりません"`
- 文: `LINK_UNUSABLE` = 「このリンクは使えません。管理者に新しいリンクを発行してもらってください」・`DUPLICATE_USER_ID` = 「このユーザーIDは既に使用されています」・`NO_ACCESS` = 「このページにアクセスする権限がありません」
- 画面は Jest＋Testing Library（今のテストの作り・サービスを `jest.mock` で差し替える）

## 裏側（pytest）

### TC-01（M1）: 形の違うパスキーの ID・メンバーの ID は 404
- `test_i636_delete_passkey_malformed_id_is_404`（parametrize: `"-" * 36`・`"g" * 36`・`"0" * 36`）: `admin_a` が `alice`（パスキー 1 個）に `DELETE /api/members/<alice.id>/passkeys/<値>/`（本人確認の印つき）→ `status_code == 404`・`main_message == "リソースが見つかりません"`・`Passkey.objects.filter(user=alice).count() == 1`
- `test_i636_delete_passkey_other_org_member_is_404`: `admin_a` が `bob`（組織 B）のパスキーの正しい ID で削除 → 404・bob のパスキーは 1 個のまま
- `test_i636_staff_delete_passkey_malformed_id_is_404`: `staff` が `DELETE /api/admin/users/<alice.id>/passkeys/<"-" * 36>/`（本人確認の印つき）→ 404・alice のパスキーは 1 個のまま
- `test_i636_malformed_member_id_is_404`: `admin_a` が `GET /api/members/<"-" * 36>/passkeys/` → 404
- 直す前は 1 本目が 500（`ValidationError`）で落ちることを確かめてから直す

### TC-02（M2）: complete の側でも使えないリンクは 400（鍵つきの引き直しを外すと落ちる）
- `test_i636_complete_unusable`（parametrize: `expired`・`revoked`・`inactive_user`・`inactive_org`）: `token = issued_token(admin_a, alice)` → `options = link_options(token).json()` → `_make_unusable(kind, people, token)` → `complete(token, options=options)` → `status_code == 400`・`sub_message == LINK_UNUSABLE`・`Passkey.objects.filter(user=alice).count() == 0`・`RegistrationLink.objects.get(user=alice).used_at is None`
- `test_i636_complete_unusable_after_first_check`（同じ parametrize）: `accounts.registration_links.passkeys.consume_challenge` を「本物を呼んで、戻る前に `_make_unusable(kind, …)`」の包みにして complete → 400・`LINK_UNUSABLE`・パスキー 0・`used_at is None`
- `test_i636_complete_without_locked_recheck_would_pass`（失敗の注入）: 上の包みに加え、`accounts.registration_links._usable_link` を「`lock=True` なら確かめずに `RegistrationLink.objects.get(token_hash=hash_token(token))` を返す」包みにして、kind=`expired` で complete → `status_code == 200`（引き直しを外すと上のテストが落ちることの証拠。`revoked` は「使用済みかつ失効」を禁じる DB の制約が別に止めるので、引き直しの有無を見分けられない）

### TC-03（L）: 同時使用は 1 回だけ（行の鍵を外すと必ず落ちる）
- 前提: I620 の今のテストと同じく `@pytest.mark.django_db(transaction=True)`（スレッドから互いの COMMIT が見える）で、スレッドの終わりに `connections.close_all()`
- `test_tc07_concurrent_complete_only_once`（作り直す）: `accounts.registration_links.passkeys.verify_and_create_passkey` を「`threading.Barrier(2, timeout=2)` で待ち（`BrokenBarrierError` は受けて先へ）、本物を呼ぶ」包みにする。2 本のスレッドで complete → `sorted(results) == [200, 400]`・`Passkey.objects.filter(user=alice).count() == 1`・`RegistrationLink.objects.filter(user=alice, used_at__isnull=False).count() == 1`・待ち合わせが時間切れになった（包みが記録した `broken` が 1 回以上）
- `test_i636_concurrent_without_row_lock_both_succeed`（失敗の注入）: 同じ包みに加え、`_usable_link` を `lock` を常に `False` にして呼ぶ包みにする → `sorted(results) == [200, 200]`・パスキー 2・待ち合わせは時間切れにならない（2 本とも鍵の中に入れた）。手動テスト No.1 でこれを 10 回流す

### TC-04（F4）: 存在の確認の後に同じ ID ができても 400
- `test_i636_create_member_race_is_400`: `MemberCreateSerializer.validate_user_id` を「本物を呼んでから、同じ `user_id` の利用者を組織 B に作る」包みにして、`admin_a` が `POST /api/members/ {"user_id": "racer"}` → `status_code == 400`・`sub_message == "このユーザーIDは既に使用されています"`・`User.objects.filter(user_id="racer").count() == 1`（組織 B の 1 人だけ）・ログ（caplog）に `racer` が出ない
- 直す前は 500（`IntegrityError`）で落ちることを確かめてから直す
- `test_tc02_create_member`（I620）が通ったまま（201・役割 `user`・組織 A）

### TC-05（F5）: メンバー管理を使える条件が、判定・API で同じ（新しいファイル `test_I636_member_access.py`）
- `test_i636_can_manage_members_matches_api`（parametrize: 上の 5 つの組織の管理者・有効な招待用の一般の利用者・有効な招待用の組織の運営〔`is_staff=True`・`role='admin'`〕・組織なしの管理者）: `GET /api/auth/me/` の `can_manage_members` と、`GET /api/members/` が 200 か（`True` ⇔ 200、`False` ⇔ 403・`main_message == "アクセスが拒否されました"`）が一致する。期待値は 管理者の 5 つ: `True`・`False`・`False`・`False`・`True`、一般: `False`、運営の管理者: `True`（I620 と同じ）、組織なし: `False`
- `test_i636_user_serializer_has_no_individual_flag`: `GET /api/auth/me/` の応答に `organization_is_individual` が無い（I620 の TC-12 を置き換える）
- 判定は `User.can_manage_members`（組織の条件は `OrganizationQuerySet.invitable()` の 1 か所・implement の /simplify で property をやめた）。画面（`/api/auth/me/`）と API（`IsOrgMemberManager`）が同じこれを読むので、上の 8 通りの期待値で条件のずれを止める

### TC-06（F6）: 作成のエラー文がすべて日本語
- `test_i636_create_member_error_messages`（parametrize）: `{}` → 「ユーザーIDを入力してください」・`{"user_id": None}` → 「ユーザーIDを入力してください」・`{"user_id": ""}` → 「ユーザーIDを入力してください」・`{"user_id": "ab"}` → 「ユーザーIDは3文字以上で入力してください」・`{"user_id": "a" * 31}` → 「ユーザーIDは30文字以内で入力してください」・`{"user_id": "bad-id"}` → 「ユーザーIDは半角英数字とアンダースコアのみ使用できます」・`{"user_id": ["x"]}` → 「ユーザーIDは文字で入力してください」・`{"user_id": "alice"}`（既存）→ 「このユーザーIDは既に使用されています」。どれも `status_code == 400`・`sub_message` が期待の文と一致

### TC-07（F9）: 設定の読み込みが `.env` に左右されず、土台の値が `FRONTEND_URL`
- `test_tc13_empty_origins_do_not_break_settings_loading`（作り直す）: 子のプロセスで `load_dotenv` を止め、`WEBAUTHN_ALLOWED_ORIGINS=""`・`FRONTEND_URL="http://frontend-base.i636.test"`・`REGISTRATION_LINK_BASE_URL` なしで設定を読む → `returncode == 0`・`stdout.strip() == "[] http://frontend-base.i636.test"`
- 失敗の注入: `settings.py:148` の既定値の式を `WEBAUTHN_ALLOWED_ORIGINS[0]` に戻した写し（一時の変更）で落ちる（`IndexError`）こと、`load_dotenv` を止めない版で、`backend/.env` に `REGISTRATION_LINK_BASE_URL` があると一致しないことを、実装の時に確かめて記録する（本物のファイルは戻す）

### TC-12（初期データ）: `seed_e2e` が運営と本人ひとりの組織の管理者を作る
- `test_i636_seed_e2e_creates_staff_and_solo`: `call_command("seed_e2e", "--scenario", "tenant_isolation", "--password", TEST_PASSWORD)` を 2 回 → `e2e_staff@example.com` は 1 人・`is_staff is True`・`role == "user"`・組織の slug `e2e-org-staff`、`e2e_solo@example.com` は 1 人・`role == "admin"`・組織の `is_individual is True`・`can_manage_members is False`。組織 `e2e-org-solo` は 1 つだけ。`e2e_user_a`・`e2e_user_b`・`e2e_user_c` もいる
- `test_i636_seed_e2e_refuses_without_debug`: `settings.DEBUG = False` で同じコマンド → `CommandError`（文「seed_e2e は DEBUG が真の環境（開発・E2E）でだけ流せます」）・`User.objects.filter(email__startswith="e2e_").count() == 0`

### OpenAPI
- `core/tests/test_I493_openapi_contract.py` が通る（`backend/openapi.yaml` と `frontend/src/types/api/schema.d.ts` を作り直してコミットする）

## 画面（Jest）

### TC-08（F7）: 押したときにリンクが使えなくなっていたら、使えないリンクの表示
- `PasskeySetup.test.tsx` に足す: 開いたときの options は成功・押したときの options が 400 → 「このリンクは使えません。管理者に新しいリンクを発行してもらってください」が出て、`getByRole('button', { name: 'パスキーを登録' })` が無い。WebAuthn の作成（`createPasskeyCredential`）は呼ばれない
- 押したときの options が 500・429 → 「パスキーを登録できませんでした。もう一度お試しください」（`role="alert"`）が出て、ボタンは押せる（もう一度押すと options をもう一度取る）
- 直す前は 1 つ目のテストが（ボタンが残るので）落ちることを確かめてから直す

### TC-09（F8）: リンクのダイアログの値を閉じ終わりまで持つ・追加の流れの二度押し
- 閉じる操作は `fireEvent.click`（`@testing-library/react`・act の中で動く）で行う。user-event 13 の `click` は描き直しを待たないので、「押した直後」の確かめが直す前でも通ってしまう（実装の時に、直しを外して落ちることを確かめた）
- ダイアログは最後に見せた値を自分で覚え、閉じ終わり（`onExited`）で捨てる（implement の /simplify で、親が値と開いているかを分けて持つ形からこの形にした。直しを外す〔中身を `link` があるときだけ描く〕と落ちることを確かめた）
- `MemberManagement.test.tsx` に足す: 行の発行 → ［閉じる］を押した直後（閉じ終わる前）にも、ダイアログの見出し「『taro』の登録用リンク」がある。閉じ終わった後（`waitForElementToBeRemoved`）は見出しもリンクの欄も無い
- 追加の流れ（`members.create` は成功・本人確認の後の `mockApi.issueLink` は解決を待たせる）で、待っている間に 一覧の新しい行の［登録用リンク］が `disabled`・［メンバーを追加］が `disabled`。解決した後、`mockApi.issueLink` の呼び出しは 1 回
- 追加の流れ（`members.create` が `NEW`〔`user_id: 'hanako2'`〕を返す）のリンクのダイアログで［閉じる］を押した直後（閉じ終わる前）に、見出し「『hanako2』の登録用リンク」がある（「『』の登録用リンク」は無い）。閉じ終わった後は見出しもリンクの欄も無い

### TC-10（F5）: メニューと画面の入口は `can_manage_members` に従う
- `Layout.members.test.tsx` を直す: `{ role: 'admin', can_manage_members: true }` → 「科目管理」の後に「メンバー管理」。`{ role: 'admin', can_manage_members: false }`（本人ひとり・無効の組織・共有の personal の管理者の代表）→ 出ない（「科目管理」は出る）。`{ role: 'user', can_manage_members: false }` → 出ない
- `MemberManagement.test.tsx` を直す: `can_manage_members: false` の管理者 → 「このページにアクセスする権限がありません」・`members.list` は呼ばれない。`true` → 一覧が出る

### TC-11（F12）: 表の中ではボタンを横に並べ、運営の欄では折り返す
- `MemberManagement.test.tsx`: 行の操作の並び（`getByRole('group', { name: '『taro』の操作' })`）が `toHaveStyle({ flexWrap: 'nowrap' })`。ユーザー ID のセルの中の要素が `toHaveStyle({ minWidth: '120px' })`
- `StaffCredentialsCard.test.tsx`（既存の運営の欄）: `getByRole('group', { name: '『alice』の操作' })` が `toHaveStyle({ flexWrap: 'wrap' })`

## E2E（Playwright）

### TC-13（F10・F11・通知）: `e2e/tests/registration-link.spec.ts` の TC-30 を直す
- 表の枠は `page.getByRole('region', { name: 'メンバーの一覧の表（横に動かせます）' })` で探す（`.MuiTableContainer-root` を使わない）
- リンクを発行して行が「有効」になった直後に幅 360px にし、枠が横に流れる（`scrollWidth > clientWidth`）・［登録用リンク］［パスキー］［リンクを取り消す］の高さが 44〜56px。確かめたら 1280×720 に戻す
- 登録の画面（別の文脈）は幅 360px で開く。登録の後のダッシュボードで「パスキーを登録しました」が見えている間に、その通知の枠とユーザーメニューのボタン（`[data-testid="user-menu-button"]`）の枠が重ならない（`boundingBox` で左右・上下の重なりが無い）
- 通知が消えるのを待たずに、ユーザーメニュー → ログアウトで `/login` に移る（通知が消えるのを待つ 2 行を消す）
- 通知は上から滑り込んで出るので、`boundingBox().y >= 0`（画面の中に止まった）になるまで待ってから測る
- 直す前（右上のまま）は、通知の枠とメニューのボタンの枠が重なって落ちることを確かめてから直す（実装の時に確かめた: 右上に戻すと `overlaps == true` で落ち、上の中央で通る）

### TC-13b（fix-loop・通知と上のバー・パネル）: 通知が上のバーのどのボタンも、パネルの操作も塞がない
- `e2e/tests/registration-link.spec.ts` の TC-30 の登録の後（幅 360px・「パスキーを登録しました」が出ている間）: 通知の枠の上端（`y`）が上のバー（`getByRole('banner')`）の下端（`y + height`）以上（ユーザーメニューとの重なりの確かめは、これに置き換える）
- 続けて上のバーの「アクセシビリティ設定」（`getByRole('button', { name: 'アクセシビリティ設定' })`）を押し、パネル（`getByRole('dialog', { name: 'アクセシビリティ設定パネル' })`）が開いたら、パネルの中央の x・上端から 10px の点の一番手前の要素（`document.elementFromPoint`）がパネルの中にある。もう一度押してパネルを閉じてからログアウトに進む
- 直す前（通知が上から 16px・パネルの `zIndex` 1001）で、上のバーとの確かめが落ちることを確かめる。パネルの確かめは、パネルの `zIndex` を 1001 に戻すと落ちることを確かめる

### TC-14（settings.spec）: TC-28 が並行で落ちない
- `e2e/tests/settings.spec.ts` の TC-28: 保存の `PATCH /api/settings/` の応答を待ち、`status() == 200`・応答の `daily_study_goal_minutes == Number(next)` を確かめてから再読み込みし、`GET` の `daily_study_goal_minutes` と入力欄の値が保存した値（実装の時に決めた形。並行の全体を 3 回分〔21 件＋`--repeat-each=2` の 42 件〕流して再現しなかったので、計画書 §4-13 の「保存の応答を待つ」だけを入れた）。E2E 全体を `--retries=0` で 3 回流して 3 回とも通る（手動テスト No.2）

### TC-15（fix-loop・settings.spec の原因）: 設定画面の古い読み込みの応答が入力を戻さない
- `frontend/src/pages/__tests__/Settings.test.tsx` に足す: `<React.StrictMode>` の中で設定画面を描く。`dashboardService.getUserSettings` の 1 回目は解決を待たせ（後片付けされる方）、2 回目は `daily_study_goal_minutes: 30` で解決する。フォームが出たら目標時間を 45 にする → 1 回目を `daily_study_goal_minutes: 50` で解決させる → 入力欄の値は 45 のまま（50 に戻らない）
- 直しを外す（後片付けを消す）と、入力欄が 50 に戻って落ちることを確かめる

## 再発防止記録（fix-loop・2026-11-27・test-gate の手動テスト No.2）
- なぜ失敗したか: 設定画面（`Settings.tsx`）の読み込みの `useEffect` に後片付けが無かった。開発の StrictMode で取得が 2 回走り、遅れて届いた 1 回目の応答が `reset` で入力を保存済みの値に戻した。E2E を並行で流して裏側が混むと、その応答が入力の後に届き、TC-28 が保存した値と違う値を送って落ちた（I620 の「並行で 1 回だけ落ちた」の原因）
- 何を変えたか: 効果に `ignore` の後片付けを付け、後片付けの後の応答では state・フォーム・通知・読み込み中の表示を変えない。TC-15（Jest・StrictMode で 1 回目の取得を遅らせる）を足した
- セキュリティ上の考慮点: 該当なし（本人の設定の値の表示と保存の順序だけ）
- 次回どう防ぐか: 効果の中で非同期に取得して state やフォームを書き換えるときは、後片付けで古い応答を捨てる（React の公式の形）。新しい画面は取得を TanStack Query に寄せる（規約 §5）。E2E の同じ利用者の値を書くテストが並行で落ちたら、StrictMode の 2 回の取得を疑う
- 確かめた結果: TC-15 は直す前に落ちた（入力欄が 45 → 50 に戻った）。直した後は `Settings.test.tsx` の 7 件・リント・型チェックが通過。E2E 全体の 3 回は test-gate で流す

## 決定論ゲート（自動実走）
<!-- このイシューは pytest・Jest・E2E（CI が流す）で確かめる。決定論のゲートのスクリプトは無い -->
