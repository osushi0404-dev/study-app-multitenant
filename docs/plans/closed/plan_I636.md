# I636 計画書: 登録用リンクとメンバー管理のレビューの残りを直す（確かめの道具・通知の場所・テストの安定）

## 基本情報
- **計画書ID**: plan_I636
- **関連イシュー**: #636
- **Draft PR**: #638
- **作成根拠資料**: docs/issues/open/I636.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I636_review.md
- **作成日**: 2026-11-27

## 1. 背景/目的
- I620（組織の管理者の登録用リンク・メンバー管理）のレビューで残った、敵対的レビューの Medium 2 件・Low 1 件（M1・M2・L）と、コードレビューの台帳の Low 9 件（F4〜F12）を直す
- 確かめの道具（初期データ `seed_e2e` の運営と本人ひとりの組織の利用者）を足し、通知の場所（上の中央）と E2E の不安定さ（settings.spec の TC-28）を整える
- F7 の後半（Safari・iOS の実機の確かめ）は #637（このイシューでは扱わない）

### 調査結果
**原因の概要**: 止めるほどではない指摘を I620 の中で直さなかったもの。多くは「入力の形の誤りを 404 にする処理が無い」「画面と裏側で同じ判定を別々に書いている」「テストが本当に守りを確かめていない」の 3 種類。

**詳細**:
1. M1: `backend/accounts/views.py:253` の削除の URL は `passkey_id` を `[0-9a-f-]{36}` で受け、`backend/accounts/registration_links.py:155` の `Passkey.objects.filter(user=target, pk=passkey_id)` にそのまま渡す。`-` が 36 個などは UUIDField の変換で `ValidationError` になり、DRF の `get_object`（`get_object_or_404` が `ValidationError` を 404 にする）と違って 500 になる。メンバーの ID（`lookup_value_regex` が同じ形）は `get_object` を通るので 404 になる
2. M2: `complete_link_registration`（`registration_links.py:126-142`）は、鍵なしの `_usable_link` で引いた後、鍵つきの `_usable_link(token, lock=True)` で引き直す。テスト（`test_I620_registration_links.py:369-381`）は options の側だけで、complete の側の期限切れ・失効・無効は確かめていない。しかも、鍵なしの 1 回目で止まるので、鍵つきの引き直しを外してもテストは落ちない（1 回目と引き直しの間に状態が変わる場合だけ、引き直しが効く）
3. L: `test_tc07_concurrent_complete_only_once`（`:449-478`）は 2 本のスレッドを `Barrier` で同時に出すだけで、行の鍵を外しても、1 本目が使用の確定まで進んでから 2 本目が引き直す順なら通る
4. F4: `MemberViewSet.create`（`views.py:296-306`）は、シリアライザの `validate_user_id`（`serializers.py:246-249`）の `exists()` と `create_user` の INSERT が別の問い合わせ。間に同じ ID が作られると、`user_id` の一意制約（`models.py:129-131`）の `IntegrityError` で 500
5. F5: メニュー（`frontend/src/components/Layout.tsx:84`）は `role === 'admin' && !organization_is_individual` で出す。裏側の `IsOrgMemberManager`（`backend/accounts/permissions.py:16-25`）は `Organization.objects.invitable()`（`models.py:31-38`: 有効・本人ひとりでない・共有の personal でない）で判定する。無効な組織・共有の personal 組織の管理者にはメニューが出るのに 403。画面の `MemberManagement`（`frontend/src/pages/MemberManagement.tsx:56`）の入口の判定も同じずれ
6. F6: `MemberCreateSerializer.user_id`（`serializers.py:238-244`）の `error_messages` に `required`・`max_length`・`null`・`invalid` が無く、DRF の既定の英語（例: `This field is required.`・`Ensure this field has no more than 30 characters.`）が出る
7. F7: 登録画面（`frontend/src/pages/PasskeySetup.tsx:52-68`）は押すたびに options を取り直す。取り直しが 400（期限切れ・失効）だと `registrationErrorText` がサーバーの文を出すが、［パスキーを登録］は残り、押しても同じ失敗になる（開いたときに使えなかった場合の「文だけ・ボタン無し」と違う）
8. F8: リンクのダイアログ（`frontend/src/components/members/RegistrationLinkDialog.tsx:51`）は `open={link !== null}`。親が閉じた瞬間に値を `null` にするので、閉じるアニメーションの間に見出しが『』になり中身が消える（`MemberManagement.tsx:179`・`MemberCredentialActions.tsx:123`）。追加の流れの発行（`MemberManagement.tsx:75-87`）は `credentialApi(...).issueLink` を直接呼び、行の［登録用リンク］の `credentials.issueLink.isPending`（`MemberCredentialActions.tsx:90`）が効かない。作成の後に一覧が読み直されて新しい行が出るので、追加の流れの本人確認を待つ間に同じ人の行の［登録用リンク］を押すと 2 回発行できる
9. F9: `test_tc13_empty_origins_do_not_break_settings_loading`（`test_I620_registration_links.py:601-617`）は子のプロセスの環境から `REGISTRATION_LINK_BASE_URL` を消すが、`core/settings.py:14` の `load_dotenv()` が `backend/.env` から読み直す（コンテナの中では `/app/.env`）。土台の値（`FRONTEND_URL`）になったかも確かめていない（`settings.py:148`）
10. F10・F11: `e2e/tests/registration-link.spec.ts:89` が MUI の内部のクラス名 `.MuiTableContainer-root` で表の枠を探す。360px のボタンの高さはパスキーが登録済みの行（ボタン 2 つ）だけで、［リンクを取り消す］を含む 3 つの行を見ていない
11. F12: 表の `sx` の `'& td:first-of-type': { minWidth: 120 }`（`MemberManagement.tsx:136`）は表のセルの `min-width` で、CSS の仕様で効き方が決まっていない。`'& td:last-of-type > div'`（`:138`）は `MemberCredentialActions` の中の要素の入れ子に頼る
12. 初期データ: `backend/accounts/management/commands/seed_e2e.py` には運営（`is_staff`）と本人ひとりの組織の利用者がいない。`docs/runbooks/frontend-verify.md` §5 の表にも無い
13. 通知: `frontend/src/App.tsx:59-68` の `Toaster` は `position="top-right"`。右上のユーザーメニュー（`Layout.tsx:161` の `user-menu-button`）に重なり、通知の上にマウスがあると消えないので押せない。react-hot-toast の通知の既定の最大幅は 350px で、幅 360px の画面では上の中央に置いてもメニューのボタン（右端から約 56px）と左のメニューのボタンに重なる
14. settings.spec: TC-28 は `e2e_user_c` の目標時間だけを書く。同じ利用者を使う `dashboard-layout.spec.ts` の TC-27・`problem-management-authz.spec.ts` は設定を書かない（`grep` で確認）。設定画面は読み込みが終わってからフォームを出す（`Settings.tsx` の `loading`）ので、読み込みと入力の競合でもない。原因は未特定。考えられるのは、共有の `user_c.json`（`e2e/global-setup.ts:32`）の refresh トークンを並行の spec が同時に使い直すこと（`ROTATE_REFRESH_TOKENS`・`BLACKLIST_AFTER_ROTATION`・`settings.py:198-199`）・保存の応答と再読み込みの順序。実装のステップ 6 で並行の全体を `--retries=0` で流して再現し、トレースから原因を決める
15. 一覧（`docs/reviews/backlog/`）: 実装対象のファイルに当たる行は無い。`FILE=-` の行は I223・I224 のハーネスの行だけ（§9）
16. 依存: 追加・更新しない。MUI は 5.15（`frontend/package.json:10`）なので、ダイアログの閉じ終わりは `TransitionProps={{ onExited }}` で受ける
17. OpenAPI: `UserSerializer` はパスキーのログインの応答（`passkeys.py:264`・契約の `/api/auth/passkeys/login/` など）に入るので、変えたら `backend/openapi.yaml`・`frontend/src/types/api/schema.d.ts` を作り直す（`docs/runbooks/common-commands.md`）

## 2. 受け入れ条件
- [ ] AC1: 形の違う `passkey_id`（`-` が 36 個・16 進でない 36 文字）で削除を呼ぶと 404 で、パスキーは消えない（500 にならない）
- [ ] AC2: `complete` で期限切れ・失効・無効の利用者・無効の組織のリンクが、どれも 400・sub_message「このリンクは使えません。管理者に新しいリンクを発行してもらってください」になり、パスキーは増えず、リンクは未使用のまま。1 回目の確かめと鍵つきの引き直しの間に使えなくなった場合も同じ。鍵つきの引き直しを外すとテストが落ちる
- [ ] AC3: 同時使用のテストが、行の鍵を外すと必ず落ちる（鍵を外した状態を作るテストを 10 回流して、10 回とも 2 本とも 200 になる＝本来のテストが落ちる状態になることを確かめて記録する）
- [ ] AC4: 同じユーザー ID の同時の作成で、存在の確認の後に同じ ID の行ができていても 400・sub_message「このユーザーIDは既に使用されています」（500 にならない）
- [ ] AC5: メニューの「メンバー管理」と `/members` の画面の入口が出る条件と、API が通す条件が同じ（無効な組織・共有の personal 組織・本人ひとりの組織の管理者と一般の利用者では、メニューが出ず画面は「このページにアクセスする権限がありません」・API は 403。招待用の有効な組織の管理者は出て 200）
- [ ] AC6: メンバーの作成のエラー文（項目が無い・空・2 文字・31 文字以上・形・重複・null）がすべて日本語
- [ ] AC7: 設定の読み込みのテストが `.env` の値に左右されず、`REGISTRATION_LINK_BASE_URL` が無く origin の一覧が空のとき、土台の値が `FRONTEND_URL` になることを確かめる
- [ ] AC8: 登録画面で押したときにリンクが使えなくなっていたら（取り直しが 400）、「このリンクは使えません。…」が出て［パスキーを登録］が消える。400 以外の失敗（429・500・通信の失敗）では一般の失敗の文が出て、もう一度押せる
- [ ] AC9: リンクのダイアログを閉じる間も見出し『<ユーザーID>』の登録用リンク と中身が残り、閉じ終わったら値を捨てる。追加の流れの発行の間は、その人の行の［登録用リンク］と［メンバーを追加］が押せず、発行は 1 回だけ
- [ ] AC10: E2E が MUI の内部のクラス名に頼らずに表の枠を探し、幅 360px で 3 つのボタン（登録用リンク・パスキー・リンクを取り消す）の行の高さが 44〜56px
- [ ] AC11: `seed_e2e`（`tenant_isolation` の場面）が運営 `e2e_staff@example.com` と本人ひとりの組織の管理者 `e2e_solo@example.com` を作り、`docs/runbooks/frontend-verify.md` §5 の表に載っている
- [ ] AC12: 通知が上の中央に出て、幅 1280px と 360px のどちらでもユーザーメニューのボタンに重ならず、ログイン直後に通知が出ている間でもログアウトを押せる（E2E）
- [ ] AC13: settings.spec の TC-28 が、E2E 全体を並行・`--retries=0` で 3 回流して 3 回とも通る

## 3. 影響範囲
- Backend: accounts（`models.py` の判定の置き場所・`permissions.py`・`serializers.py`・`views.py`・`registration_links.py`・`management/commands/seed_e2e.py`・テスト）。`backend/openapi.yaml`（作り直し）
- Frontend: `App.tsx`（通知の場所）・`components/Layout.tsx`（メニュー）・`pages/MemberManagement.tsx`・`pages/PasskeySetup.tsx`・`components/members/RegistrationLinkDialog.tsx`・`components/members/MemberCredentialActions.tsx`・`services/types.ts`・`types/api/schema.d.ts`（作り直し）・`pages/Settings.tsx`（読み込みの効果の後片付け・fix-loop で足した）と、それぞれの Jest のテスト（`pages/__tests__/Settings.test.tsx` を含む）
- E2E: `e2e/tests/registration-link.spec.ts`・`e2e/tests/settings.spec.ts`（原因しだいで `e2e/global-setup.ts`・`e2e/tests/dashboard-layout.spec.ts`）
- DB: なし（マイグレーションなし。初期データのコマンドに利用者を足すだけ）
- Config/Infra: なし
- Docs: `docs/runbooks/frontend-verify.md` §5

## 4. 変更点一覧（具体）

### 修正アプローチ
- 裏側は「入力の形の誤りは 404／400 にする」「判定は 1 か所に置いて、画面にはその結果を渡す」「テストは守りを外すと必ず落ちる形にする」の 3 つで直す
- 画面はダイアログの値を閉じ終わりまで持つ・送信中の印で二度押しを止める・MUI の中の構造に頼らない書き方にする
- 確かめの道具とテストの安定は、初期データの追加と E2E の書き方の直しで行う

### 4-1. M1: パスキー削除の ID の形の誤りを 404 に（`backend/accounts/views.py`）
- 達成: 形の違う `passkey_id` で 500 にしない
- `delete_member_passkey` で `uuid.UUID(passkey_id)` に直し、`ValueError` なら `Http404`（`django.http.Http404`。DRF が 404・`main_message: "リソースが見つかりません"` にする）。直した値を `registration_links.delete_passkey_of(passkey_id=<UUID>)` に渡す
- URL の正規表現は変えない（直す場所を 1 つにする）

### 4-2. M2・L: complete の側のテストと、同時使用のテスト（`backend/accounts/tests/test_I620_registration_links.py`）
- 達成: 鍵つきの引き直しと行の鍵を外すと、必ず落ちるテストにする
- `test_tc05_complete_unusable`（parametrize: expired・revoked・inactive_user・inactive_org）: options を取ってから `_make_unusable` → complete → 400・`LINK_UNUSABLE`・パスキー 0・`used_at` が `None`
- `test_tc05_complete_unusable_after_first_check`（同じ parametrize）: `accounts.registration_links.passkeys.consume_challenge` を、本物を呼んだ後に `_make_unusable` する包み（`mock.patch(..., side_effect=...)`）に替える（1 回目の確かめと鍵つきの引き直しの間に使えなくなる）→ 400・`LINK_UNUSABLE`・パスキー 0
- `test_tc05_complete_without_locked_recheck_would_pass`（失敗の注入。上のテストが引き直しを本当に確かめている証拠）: `_usable_link` を「`lock=True` のときは確かめずに行を返す」包みに替えると、上と同じ手順で 200 になる（＝引き直しを外せば上のテストは落ちる）
- `test_tc07_concurrent_complete_only_once` を作り直す: `accounts.registration_links.passkeys.verify_and_create_passkey`（鍵の中で呼ばれる）を、`threading.Barrier(2, timeout=2)` で待ってから本物を呼ぶ包みに替える。鍵があると 2 本目は `select_for_update` で待つので 1 本目の待ちが時間切れになり（`BrokenBarrierError` を受けて先に進む）、1 本目が確定 → 2 本目の引き直しが「used」で 400。結果は `[200, 400]`・パスキー 1・使用済みのリンク 1
- `test_tc07_without_row_lock_both_succeed`（失敗の注入）: 同じ包みに加え、`_usable_link` の `lock` を常に `False` にする包みを入れると、2 本とも待ち合わせを通って `[200, 200]`・パスキー 2 になる（＝行の鍵を外せば本来のテストは落ちる）。AC3 の 10 回はこのテストを 10 回流して記録する（手動テスト No.1）

### 4-3. F4: メンバーの作成の重複を 400 に（`backend/accounts/registration_links.py`・`views.py`）
- 達成: 存在の確認と作成の間に同じ ID ができても 500 にしない
- `registration_links.py` に `create_member(*, organization: Organization, user_id: str) -> User` を足す（メンバー管理の業務の処理の置き場所。I620 のメンバー管理・リンクの処理と同じファイル）。`transaction.atomic()` の中で `User.objects.create_user(user_id=..., password=None, organization=..., role='user')`、`IntegrityError` を受けたら `logger.info('member create duplicate organization_id=%s', organization.pk)` を残して `serializers.ValidationError({'user_id': [DUPLICATE_USER_ID]})`（`DUPLICATE_USER_ID = 'このユーザーIDは既に使用されています'`。シリアライザの `validate_user_id` も同じ定数を使う）
- `MemberViewSet.create` は `registration_links.create_member(...)` を呼ぶだけにする（Fat View にしない・規約 §6・§7）

### 4-4. F5: メンバー管理を使えるかを 1 か所で判定し、画面に渡す（`models.py`・`permissions.py`・`serializers.py`・画面）
- 達成: メニュー・画面の入口・API が同じ条件になる
- `User.can_manage_members`（property）: `self.role == 'admin'` かつ組織があり、`Organization.objects.invitable().filter(pk=self.organization_id).exists()`（組織の条件は `OrganizationQuerySet.invitable()` の 1 か所だけ。implement の /simplify で `Organization.is_invitable` の property をやめた・計画変更記録）
- `IsOrgMemberManager.has_permission`: `getattr(user, 'is_authenticated', False) and user.can_manage_members`（`organization` は `request.user` の外部キーを 1 回引く。これまでの `exists()` の問い合わせと同じ 1 回）
- `UserSerializer`: `can_manage_members = serializers.BooleanField(read_only=True)`（モデルの property を読む）を足し、`organization_is_individual` を外す（画面でこの用途にしか使っていないので、2 つの判定を残さない。`AdminUserSerializer` の `organization_is_individual` は運営の欄で使うので残す）
- 画面: `services/types.ts` の `User` に `can_manage_members?: boolean` を足し `organization_is_individual` を外す。`Layout.tsx` のメニューは `user?.can_manage_members` で出す。`MemberManagement.tsx` の入口は `!user?.can_manage_members` なら「このページにアクセスする権限がありません」（一覧の API を呼ばない）
- OpenAPI と画面の型を作り直す

### 4-5. F6: ユーザー ID のエラー文を日本語に（`backend/accounts/serializers.py`）
- 達成: 作成のどの入力の誤りでも日本語の文
- `MemberCreateSerializer.user_id` の `error_messages` に `required: 'ユーザーIDを入力してください'`・`null: 'ユーザーIDを入力してください'`・`invalid: 'ユーザーIDは文字で入力してください'`・`max_length: 'ユーザーIDは30文字以内で入力してください'` を足す（`blank`・`min_length` はあるまま）

### 4-6. F7: 押したときにリンクが使えなくなっていたら、使えないリンクの表示に切り替える（`frontend/src/pages/PasskeySetup.tsx`）
- 達成: 押したときの取り直しが 400 なら、開いたときに使えなかった場合と同じ「文だけ・ボタン無し」
- `const [linkGone, setLinkGone] = useState(false)`。`handleRegister` で options の取り直しだけを別の `try` にし、`axios.isAxiosError(e) && e.response?.status === 400` なら `setLinkGone(true)` して終える。それ以外は今までどおり `registrationErrorText` の文
- `renderBody` の最初の分岐を `token === null || options.isError || linkGone` にする（`LINK_UNUSABLE` の `Alert` だけ）
- 押すたびに取り直す作りは変えない（Safari・iOS は #637）

### 4-7. F8: リンクのダイアログの値を閉じ終わりまで持つ・追加の流れの二度押しを止める
- 達成: 閉じるアニメーションの間も見出しと中身が残る。追加の流れの発行は 1 回だけ
- `RegistrationLinkDialog.tsx`: 最後に見せた値（見出しのユーザー ID とリンク）を部品の state に覚え、親が `link` を `null` にして閉じても閉じるアニメーションの間はそれで描く。閉じ終わり（`TransitionProps.onExited`）で捨てる（保存領域には置かない）。親（`MemberManagement.tsx`・`MemberCredentialActions.tsx`）の props の形は I620 のまま（implement の /simplify で、親が値と開いているかを分けて持つ形からこの形にした・計画変更記録）
- 追加の流れ: `MemberManagement` に `issuingFor: string | null`（発行中のメンバーの ID）を持ち、`handleAdd` の発行の前後で立てて下ろす（`finally`）。行の `MemberCredentialActions` に `issueBusy={issuingFor === member.id}` を渡し、［登録用リンク］を `credentials.issueLink.isPending || issueBusy` で押せなくする。［メンバーを追加］も `issuingFor !== null` の間は押せなくする

### 4-8. F9: 設定の読み込みのテストを `.env` に左右されなくする（`test_I620_registration_links.py`）
- 達成: 土台の値の式を壊すと落ちるテストにする
- 子のプロセスのコードの先頭で `import dotenv; dotenv.load_dotenv = lambda *a, **k: False` としてから `django.setup()`（`core/settings.py` の `from dotenv import load_dotenv` が差し替えた関数を読む）。環境は `WEBAUTHN_ALLOWED_ORIGINS=""`・`FRONTEND_URL="http://frontend-base.i636.test"`・`REGISTRATION_LINK_BASE_URL` を消す
- 出力が `[] http://frontend-base.i636.test` と一致することを確かめる
- 設定のファイルを変えて差し替えを不要にする案（`.env` を読むかを環境変数で切る）は、本番の設定に試験のためだけの分岐を足すので採らない（§9）

### 4-9. F10・F11: E2E を MUI の中の構造に頼らない形に（`e2e/tests/registration-link.spec.ts`・`MemberManagement.tsx`）
- 達成: 表の枠を役割と名前で探し、3 つのボタンの行も 360px で確かめる
- `MemberManagement.tsx` の `TableContainer` に `role="region"`・`aria-label="メンバーの一覧の表（横に動かせます）"`・`tabIndex={0}` を付ける（横に流れる枠をキーボードで動かせるようにする。アクセシビリティの推奨の形）
- E2E は `page.getByRole('region', { name: 'メンバーの一覧の表（横に動かせます）' })` で枠を探す
- 360px の確かめを、リンクを発行した直後（行が「有効」で 3 つのボタンがある）に移し、［登録用リンク］［パスキー］［リンクを取り消す］の高さを 44〜56px で確かめてから幅を戻す（`page.setViewportSize({ width: 1280, height: 720 })`）。最後の「1 個・なし」の確かめはそのまま

### 4-10. F12: 列の幅と横に並べる指定を部品に（`MemberManagement.tsx`・`MemberCredentialActions.tsx`）
- 達成: 表のセルの `min-width` と、部品の中の構造に頼る指定をなくす
- ユーザー ID のセルは `<TableCell sx={{ whiteSpace: 'normal' }}><Box sx={{ minWidth: 120, overflowWrap: 'anywhere' }}>…</Box></TableCell>`（ブロックの要素の `min-width` は仕様で決まっている）
- `MemberCredentialActions` に `wrap?: boolean`（既定 `true`）を足し、ボタンの並びを `flexWrap: wrap ? 'wrap' : 'nowrap'` にする。メンバー管理の表では `wrap={false}` を渡す（運営の欄は既定のまま）
- 表の `sx` からは `'& td:first-of-type'`・`'& td:last-of-type > div'` を消す（`minWidth: 720` と `'& th, & td': { whiteSpace: 'nowrap' }` は残す）

### 4-11. 初期データ（`backend/accounts/management/commands/seed_e2e.py`・`docs/runbooks/frontend-verify.md`）
- 達成: 確かめに要る運営と本人ひとりの組織の利用者を、手で DB に作らずに使える
- `_seed_tenant_isolation` に足す（E2E の初期化と CI が流す場面）:
  - 運営: 組織 `e2e-org-staff`（「E2E Org Staff」・招待用）に `e2e_staff@example.com`・`user_id='e2e_staff'`・`is_staff=True`・`role='user'`（運営の権限は `is_staff` で決まる。組織 A・B のメンバーの一覧と人数に混ぜない）
  - 本人ひとりの組織の管理者: 組織 `e2e-org-solo`（「e2e_soloさんの学習」・`type=personal`・`is_individual=True`）に `e2e_solo@example.com`・`user_id='e2e_solo'`・`role='admin'`
  - どちらも今の E2E の利用者と同じく、メールで消してから作り直す（何度流しても同じ）。パスワードは `--password`（#622 の後はパスキーの形に合わせる）
- `handle` の最初で `settings.DEBUG` が偽なら `CommandError('seed_e2e は DEBUG が真の環境（開発・E2E）でだけ流せます')` で止まり、何も作らない（design-security-review の必須防御条件。既知のパスワードの運営アカウントを本番に作らない）
- `docs/runbooks/frontend-verify.md` §5 の表に 2 行を足し、`e2e_user_b` の役割の欄を「管理者」に直す（`seed_e2e.py` の `role='admin'` と食い違っている）

### 4-12. 通知の場所（`frontend/src/App.tsx`）
- 達成: 通知がユーザーメニューと左のメニューのボタンに重ならない
- `Toaster` の `position` を `top-center` に、`toastOptions.style` に `maxWidth: 'min(350px, calc(100vw - 128px))'` を足す（左右 64px ずつ空ける。上のバーの左右のボタンは端から 56px 以内）
- E2E（TC-30）の「通知が消えるのを待つ」2 行を外し、登録直後（通知が出ている間）にユーザーメニューを開いてログアウトする。登録の画面は幅 360px で開き、ダッシュボードで通知の枠とユーザーメニューのボタンの枠が重ならないことを確かめる

### 4-13. settings.spec の不安定さ（`e2e/tests/settings.spec.ts` ほか）
- 達成: 並行で流しても TC-28 が落ちない
- ステップ 6 で再現し、原因で直し方を決める:
  - 共有の `user_c.json` のトークンの使い直しが原因なら、TC-28 を専用の文脈（その場でパスワードでログイン）で流すか、`e2e/global-setup.ts` で TC-28 用の別の保存を作る
  - 保存と再読み込みの順序が原因なら、保存の応答（`PATCH /api/settings/`）を待ってから再読み込みする
  - それ以外・ここに無いファイルが要るときは、計画変更記録に書いて計画レビューを通し直す
- 3 回流しても再現しないときは、上の 2 つのうち副作用の無い「保存の応答を待つ」だけを入れ、原因は未特定と記録する（§8 R5）
- （fix-loop で特定・計画変更記録）原因は設定画面の読み込みの効果に後片付けが無いこと。開発の StrictMode で取得が 2 回走り、遅れた 2 回目の応答が `reset` で入力を保存済みの値に戻す。`frontend/src/pages/Settings.tsx` の効果に `ignore` の後片付けを付け、古い応答では state もフォームも変えない（React の公式の形）。Jest（`Settings.test.tsx`）で StrictMode の下で 1 回目の取得を遅らせて再現し、直しを外すと落ちることを確かめる → TC-15

## 5. 実装手順（ステップ）
1. 裏側の M1・M2・L（テストを先に書き、落ちることを確かめてから直す）→ TC-01〜TC-03
2. 裏側の F4・F6・F9 → TC-04・TC-06・TC-07
3. F5 の縦の 1 本（モデルの判定 → 権限 → シリアライザ → OpenAPI と画面の型 → メニューと画面の入口）→ TC-05・TC-10。ステップ 1・2 の後（同じファイルを触る）
4. 画面の F7・F8・F12（Jest を先に）→ TC-08・TC-09・TC-11。ステップ 3 の後（`MemberManagement.tsx` の入口を先に直す）
5. 初期データと手順書 → TC-12。ステップ 1〜4 と並行してよい
6. 通知の場所と E2E（F10・F11・TC-30 の通知待ちの撤去）、settings.spec の再現と直し → TC-13・TC-14・手動テスト No.2〜No.4。ステップ 4・5 の後（画面と初期データを使う）

## 6. テスト計画
### 自動
- 裏側（結合・API を通す）: `backend/accounts/tests/test_I620_registration_links.py` に足し・直す（同じ下準備を使うため新しいファイルにしない。イシュー番号は関数名の `i636` で分かるようにする）。新しく `backend/accounts/tests/test_I636_member_access.py` に、組織の種類ごとの `is_invitable` と `invitable()` の一致・`can_manage_members` と `/api/members/` の 200/403 の一致を書く
- 画面（Jest＋Testing Library。今のテストの道具に合わせる・規約 §16 の #551 までは Jest）: `Layout.members.test.tsx`・`MemberManagement.test.tsx`・`PasskeySetup.test.tsx` に足し・直す
- E2E（Playwright）: `registration-link.spec.ts` を直す。settings.spec は原因しだい
- 失敗の注入: TC-02・TC-03 はテストの中で守りを外した版も流す（CI で毎回）。TC-05 は条件を 1 つずらした組織で一致が崩れることを確かめる
- 認可のテスト: TC-05（組織の種類ごとの 200/403 と画面の出し分け）・TC-01（他の組織のメンバーの ID でも 404 のまま）
### 手動
- `docs/tests/open/I636_manual_test.md`（実施者はすべて Claude。AC3 の 10 回・E2E の並行 3 回・画面確認）

## 7. ロールバック
- PR を revert する。マイグレーションは無い。`seed_e2e` で作った利用者（`e2e_staff`・`e2e_solo`）と組織（`e2e-org-staff`・`e2e-org-solo`）は E2E 用で、残っても他に影響しない（消すなら管理画面から）

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: `organization_is_individual` を `UserSerializer` から外すと、保存済みの `localStorage` の `user` に `can_manage_members` が無い間、管理者のメニューが出ない | 起動時に `AuthContext` が `getCurrentUser` で取り直して保存し直す（`AuthContext.tsx:61-63`）。出ない側に倒れる（安全側） | 受け入れ |
| R2: 画面の判定と API の判定が将来ずれる | 両方が `User.can_manage_members`（条件は `invitable()` の 1 か所）を読む。TC-05 で組織の種類ごとに `/api/auth/me/` と `/api/members/` の一致を確かめる | 回避 |
| R3: 同時使用のテストの待ち合わせの時間切れ（2 秒）で CI が遅くなる | 1 本 2 秒だけ。時間切れの側が本来の動き（鍵で待つ）なので外さない | 受け入れ |
| R4: 通知を上の中央にすると、上の中央に出る画面の要素（見出しなど）に一時的に重なる | 通知は 4 秒で消え、押す要素（ボタン）は上のバーの左右にしかない。手動テスト No.3 で主な画面を見る | 受け入れ |
| R5: settings.spec の原因が 3 回で再現しない | 副作用の無い「保存の応答を待つ」だけを入れ、原因は未特定として記録。再発したら retro で起票 | 受け入れ |
| R6: 初期データに運営を足すと、運営の一覧（`/admin/users`）の件数を見ている E2E が変わる | 今の E2E は運営の画面を見ていない（`grep admin/users e2e/tests` で 0 件）。CI の E2E 全体で確かめる | 回避 |
| R7: `TableContainer` に `tabIndex={0}` を付けると、Tab の順に表の枠が 1 つ増える | 横に流れる枠をキーボードで動かすための推奨の形。手動テスト No.3 で Tab の順を見る | 受け入れ |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 通知は上の中央（`Toaster` の `position` を `top-center`）。右下は選ばない
- F7 はこのイシューでは「使えないリンク」の案内だけ。押すたびに取り直す作りは変えない。Safari・iOS は #637
- settings.spec の原因の調査は計画（実装のステップ 6）で行う
- F5 は裏側の判定の結果を API で返し、画面と二重に書かない
- 着手の順は M1・M2・L が先
Claude が決めた（技術的な選択と理由）:
- 判定の置き場所: `Organization.is_invitable`・`User.can_manage_members` をモデルの property に置く。`permissions.py` に置くと `serializers.py` → `permissions.py` → `passkeys.py` → `serializers.py` の循環の import になる。`invitable()` の QuerySet は slug の引き当て（I539）で使うので残し、一致をテストで守る（仮定で決めた・技術）
- `UserSerializer` の `organization_is_individual` を外す: 画面での用途はメニューと入口だけで、残すと同じ判定が 2 つになる（仮定で決めた・技術）
- F4 の `create_member` は `registration_links.py` に置く: I620 のメンバー管理の業務の処理のファイルで、イシューの実装対象に挙がっている（仮定で決めた・技術）
- M1 は URL の正規表現でなく view で UUID に直す: 直す場所を 1 つにし、メンバーの ID と同じく 404 にする（イシューに明記）
- 同時使用のテストは待ち合わせ（`Barrier` の時間切れ）で順序を作る: 鍵があれば必ず時間切れの側、鍵が無ければ必ず両方通る側になり、順序に頼らない（イシューで「方式は計画で決める」）
- F9 は子のプロセスの中だけで `load_dotenv` を止める: `settings.py` に試験のための分岐を足さない。差し替えは試験のプロセスの中だけ（plan-writing-rules「テスト計画」の第一候補〔本番の設計を変える〕を比べて、本番に分岐を足すほうが悪いと判断）
- F10 の枠に `role="region"` と名前を付ける: 役割と名前で探せるようにし、横に流れる枠をキーボードで動かせるようにする（画面の見た目は変わらない。Tab の順に 1 つ増える・R7）
- 通知の最大幅 `min(350px, calc(100vw - 128px))`: 幅 360px で上のバーの左右のボタンに重ねないため（イシューで「重なるなら最大幅を抑える」と決まっている値の具体化）
- 初期データの運営は専用の組織、本人ひとりの組織は固定の slug: 組織 A・B のメンバーの一覧と件数に混ぜない・何度流しても組織が増えない
- `TC-28` の直し方は原因しだい（§4-13）
UI の変更（配置・順序・ラベル）:
- 通知の場所: 右上 → 上の中央（イシューで確定）。文言は変えない
- メンバー管理の表の枠: 見た目は変えない。読み上げの名前「メンバーの一覧の表（横に動かせます）」を足す（画面に出る文ではない）
- 登録画面: 押したときにリンクが使えなかったら、開いたときと同じ文（既存の `LINK_UNUSABLE`）を出してボタンを消す（イシューで確定）
- 追加の流れの発行中は［メンバーを追加］と、その人の行の［登録用リンク］を押せない（見た目は MUI の無効のボタン）
- 新しい文言: エラー文 3 つ（「ユーザーIDは30文字以内で入力してください」「ユーザーIDは文字で入力してください」と、既存の「ユーザーIDを入力してください」の流用）。AC6 で「日本語にそろえる」と決まっている範囲の具体化
要件適合性・業務ロジック:
- 受け入れ条件の外の仕様の追加・変更は無い（読み上げの名前は E2E の探し方のための付随）
- マルチテナント: メンバー管理を使える組織の条件は変えない（`invitable()` と同じ）。一覧・作成・削除はこれまでどおり `request.user.organization_id` で絞る。M1 の 404 は他の組織のメンバーでも同じ（`get_object` が先に 404）
- 境界値: ユーザー ID 2 文字・3 文字・30 文字・31 文字（AC6 の TC で 2・31 を見る。3・30 は I620 の TC-02 で通る）
セキュリティ・BP:
- 入力の検証: `passkey_id` の形（M1）・ユーザー ID のエラー文（F6）・重複の `IntegrityError` は決まった文で返し、例外の中身を出さない（規約 §7）
- 認可: `IsOrgMemberManager` の条件は変えない（置き場所だけ）。最小権限のまま。画面の出し分けは API の結果に従う（画面は表示のためだけで、守りは API）
- 機密: リンクの値は今までどおり画面のメモリだけ（閉じ終わりまで持つだけで、保存領域に置かない）。ログにユーザー ID を出さない（F4 のログは組織の ID だけ・規約 §11）
- OWASP: XSS（文言は React の文字として出す・`dangerouslySetInnerHTML` なし）・SQL（ORM だけ）・CSRF（変更なし）
- 依存: 追加・更新なし（npm audit・pip-audit の対象の変化なし）
- 検査の基準: bandit は MEDIUM 以上を直す・LOW は `# nosec` で理由を書いて抑える（F9 のテストの `subprocess` は既存の `# nosec B404・B603` のまま）。npm audit は high/critical を直す
P3/P5/P8: DB の変更・外部 API・非同期処理・新しいインフラは無い（P3/P5/P8 影響なし）
P6: 画面の変更があるので §13 を書く
P9: 個人情報・未成年データを新しく扱わない。初期データの利用者は E2E 用の架空のアカウント（P9 影響なし）
一覧（`docs/reviews/backlog/`）:
- 一覧 I223.md B1〜B4: 残す — ハーネスの bot の後片付けで、このイシューのファイルに関係しない
- 一覧 I224.md F9: 残す — ハーネスの測定の行で、このイシューのファイルに関係しない
Danger Ops:
- 無（データの削除・破壊的なマイグレーション・強制 push は無い。`seed_e2e` は E2E 用の利用者をメールで消して作り直す既存の動きと同じ）

## 13. 性能・UX設計
- 読み込み・空・エラー: メンバー管理の一覧の 4 つの状態は変えない。登録画面は「確かめ中・使えない・登録できる・失敗」の出し分けに、押したときに使えなくなった場合を「使えない」に足す
- 破壊的な操作の確認: 発行（今のパスキーを消す）・取り消し・削除の確認のダイアログは変えない。二度押しの防止を追加の流れにも広げる（AC9）
- 性能: `IsOrgMemberManager` の問い合わせは 1 回のまま（`exists()` → 外部キーの 1 回）。`UserSerializer` の `can_manage_members` は `organization_name` と同じ外部キーを使い、増えない
- アクセシビリティ: 横に流れる表の枠に名前と `tabIndex={0}`。無効のボタンは MUI の `disabled`（読み上げで無効と伝わる）。ダイアログは閉じ終わりまで名前（見出し）を保つ
- 幅 360px: 表は表の中で横に流れ、ボタンは 44〜56px（AC10）。通知は左右 64px を空ける（AC12）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | メンバー管理の API・メニュー・画面の入口が同じ条件か。TC-05 が組織の種類（有効な招待用・無効・本人ひとり・共有の personal・slug が共有でない personal）と役割（管理者・一般・組織なし）の組み合わせで、`can_manage_members`（`/api/auth/me/`）と `/api/members/` の 200/403 の一致を確かめているか。運営（`is_staff`）の管理者の扱いが前と変わらないか |
| V2 | 2 | 読んで可 | TC-02・TC-03 が本当に鍵つきの引き直しと行の鍵を確かめているか（失敗の注入の版が `[200, 200]`・200 になり、本来の版が落ちる形か。待ち合わせの包みが本物の検証を呼んでいるか） |
| V3 | 1 | 読んで可 | 形の違う `passkey_id`・メンバーの ID で 500 にならないか（TC-01）。別の組織のメンバーの ID と形の違う ID の両方で 404 か |
| V4 | 3 | 読んで可 | 作成の重複（TC-04）で、例外の中身・ユーザー ID がログと応答に出ないか。`transaction.atomic` の中で受けて、外側のトランザクションを壊さないか |

## 計画変更記録
- 2026-11-27 fix-loop: 計画書の記載: §4-13「原因で直し方を決める（…それ以外・ここに無いファイルが要るときは、計画変更記録に書いて計画レビューを通し直す）」→ 採った方法: 原因が分かった（test-gate の手動テスト No.2・診断メモ `docs/reviews/I636_fix_diagnosis_20261127_0420.md`）。設定画面 `frontend/src/pages/Settings.tsx` の読み込みの `useEffect` に後片付け（`let ignore = false`・後片付けで `ignore = true`。`ignore` なら `setSettings`・`resetSettingsForm`・`toast.error`・`setLoading` をしない）を付け、StrictMode で 2 回走る取得の古い応答が入力を戻さないようにする。実装対象に `Settings.tsx` と `frontend/src/pages/__tests__/Settings.test.tsx` を足す。E2E の「保存の応答を待つ」は残す — 理由: 診断レビューを通った案 A（React の公式の形・最小の変更）。TanStack Query への移行（案 B）は範囲を超えるので採らない。計画レビューのやり直し: 要（実装対象のファイルを足す）
- 2026-11-27 implement: 計画書の記載: §4-10「`MemberCredentialActions` に `wrap?: boolean` を足し、ボタンの並びを…」→ 採った方法: 同じ並びの `Box` に `role="group"`・`aria-label="『<ユーザーID>』の操作"` も付け、TC-11 はこの名前で並びを探す — 理由: テストが `parentElement`（部品の中の入れ子）に頼るとリント（`testing-library/no-node-access`）に止められ、F12 と同じ「内部の構造に頼る」形にもなる。読み上げで行の操作のまとまりが分かる（見た目は変わらない）。計画レビューのやり直し: 不要（読み上げの名前の付随の追加だけ）
- 2026-11-27 implement（/simplify）: 計画書の記載: §4-4「`Organization.is_invitable`（property）… 両者が同じことはテストで守る」→ 採った方法: property を作らず、`User.can_manage_members` が `Organization.objects.invitable().filter(pk=self.organization_id).exists()` を呼ぶ（条件は QuerySet の 1 か所だけ）。TC-05 の一致のテスト 2 本（`is_invitable` と QuerySet・その失敗の注入）は要らなくなったので消し、組織の種類ごとの `/api/auth/me/` と `/api/members/` の一致のテストは残す — 理由: /simplify の指摘（同じ条件を 2 か所に書き、一致をテストで守るより、1 か所に置くほうが簡単で直し忘れが起きない）。問い合わせの数は I620 の権限の判定と同じ 1 回。計画レビューのやり直し: 不要（判定の置き場所の実装の選び直しで、条件・範囲・受け入れ条件は変えない）
- 2026-11-27 implement（/simplify）: 計画書の記載: §4-7「`RegistrationLinkDialog` に `open`・`onExited` を足し、親が値と開いているかを分けて持つ」→ 採った方法: ダイアログが最後に見せた値（見出しのユーザー ID とリンク）を自分の state に覚え、閉じ終わり（`TransitionProps.onExited`）で捨てる。親（`MemberManagement`・`MemberCredentialActions`）は I620 と同じ `link`・`onClose` の形のまま — 理由: /simplify の指摘（同じ組の state を 2 つの親に書き写していた）。値を捨てる時点（閉じ終わり）は計画と同じ。計画レビューのやり直し: 不要（部品の中の作りの選び直しだけ）
- 2026-11-27 implement: 計画書の記載: 「`DUPLICATE_USER_ID` … シリアライザの `validate_user_id` も同じ定数を使う」（定数の置き場所は `registration_links.py`）→ 採った方法: 定数は `serializers.py` に置き、`registration_links.py` が import する — 理由: `serializers.py` が `registration_links.py` を import すると、`registration_links` → `passkeys` → `serializers` の循環になる。計画レビューのやり直し: 不要（定数の置き場所だけ）
- 2026-11-27 implement: 計画書の記載: TC-02 の失敗の注入を kind=`revoked` で → 採った方法: kind=`expired` — 理由: `revoked` は DB の制約（`registration_link_not_used_and_revoked`）が使用の確定を止めるので、引き直しを外しても 500 になり 200 にならない（引き直しの有無を見分けられない）。計画レビューのやり直し: 不要（注入の条件の選び直しだけ）
- 2026-11-27 implement: 計画書の記載: §4-13 の settings.spec → 採った方法: 並行の全体を 3 回分（21 件＋42 件）流して再現しなかったので、「保存の応答（PATCH の 200 と保存した値）を待ってから再読み込み」だけを入れた（R5 のとおり）。原因は未特定 — 理由: 計画どおり。計画レビューのやり直し: 不要
- 2026-11-27 design-security-review: 計画書の記載: §4-11 の初期データ・TC-01・TC-12 → 採った方法: `seed_e2e` を DEBUG が偽なら止める・TC-01 に運営の API の 404・TC-12 に DEBUG 偽の確かめを足した — 理由: セキュリティ設計レビューの Medium 1 件・Low 1 件の必須防御条件。計画レビューのやり直し: 不要（防御条件とテストの追記だけで、方式・範囲・受け入れ条件は変えない）
- 2026-11-27 plan-review: 計画書の記載: 自動テスト TC-03・TC-09・TC-14 → 採った方法: TC-03 に `transaction=True` の前提、TC-09 に追加の流れのダイアログの具体的な期待値、TC-14 に実装の時に期待値を書き戻すことを足した — 理由: 計画レビューの Warning 3 件（期待値の具体化だけ）。計画レビューのやり直し: 不要（findings への対応の追記だけ）

## レビュー結果
- [20261127_0354 判定: ✅ 完了](../../reviews/closed/I636_plan_review_20261127_0354.md)
- [20261127_0229 判定: ✅ 完了](../../reviews/closed/I636_plan_review_20261127_0229.md)

## セキュリティレビュー結果

**実施日**: 2026-11-27

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Medium | 機密情報・セキュリティ設定ミス | `seed_e2e` に運営（`is_staff=True`）を足すと、E2E 用の既知のパスワードの運営アカウントが、誤って本番に近い DB で流したときにできる（今のコマンドには DEBUG の確かめが無い） | 必須防御条件: `seed_e2e` は `settings.DEBUG` が偽なら `CommandError` で止まり、何も作らない（運営だけでなくコマンド全体。E2E のデータは本番に要らない）。計画書 §4-11 と TC-12 に足す |
| Low | 入力検証・OWASP（IDOR） | M1 の削除の処理は運営の `AdminUserViewSet` も同じミックスインで使う。運営の側の形の誤りも 500 にしない | 必須防御条件: 同じ `delete_member_passkey` を直すので両方に効く。TC-01 に `/api/admin/users/<id>/passkeys/<"-"*36>/` の 404 を足す |
| Low | 認証・認可 | 判定を `IsOrgMemberManager` からモデルの property に移すとき、条件の取りこぼしで通す範囲が広がる | 禁止事項: 条件を変えない。`invitable()` と同じ 3 条件（有効・本人ひとりでない・共有の personal でない）と `role == 'admin'`・組織あり。TC-05 の一致と失敗の注入で守る（計画どおり） |
| Low | 機密情報 | `can_manage_members` をログインの応答と `/api/auth/me/` に出す | 本人の権限の真偽だけで、他人・他の組織の情報を含まない。許容（対処不要） |
| Low | 入力検証 | F4 の `IntegrityError` を受けるとき、外側のトランザクションを壊す・別の制約の違反を「重複」と誤って返す | 必須防御条件: `transaction.atomic()` の内側（セーブポイント）で受ける。`create_user` に渡すのは `user_id`・組織・役割だけで、一意の制約は `user_id` だけ（`email` は `None`）。応答とログに例外の中身・ユーザー ID を出さない（計画どおり・V4） |

マルチテナント: なし（一覧・作成・削除の絞り込み〔`request.user.organization_id`〕は変えない。M1 は `get_object` の 404 の後で、他の組織のメンバーには届かない）
ファイル操作: なし
外部通信: なし
依存ライブラリ: なし（追加・更新なし）

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | `DELETE /api/members/{id}/passkeys/{passkey_id}/`・`/api/admin/users/{id}/passkeys/{passkey_id}/` | 組織の管理者・運営 | 形の違う ID を送って 500 を起こし、エラーの監視を埋める・例外の情報を引き出す | 404・パスキーは消えない・例外の中身を返さない | Yes: TC-01 | No | なし | Low |
| 2 | `GET /api/members/`ほか | 無効な組織・共有の personal 組織・本人ひとりの組織の管理者 | 画面のメニューが出ないので API を直接呼ぶ | API が 403（判定は 1 か所） | Yes: TC-05 | Yes: 手動 No.4 | なし | Low |
| 3 | `POST /api/members/` | 組織の管理者 | 同じユーザー ID を同時に 2 回送り、500 や他の組織の利用者の存在を探る | 400 と決まった文。どの組織の ID かを出さない | Yes: TC-04 | No | 重複の文で「その ID が使われている」ことは分かる（I620 と同じ・登録の画面と同じ扱い） | Low |
| 4 | `POST /api/auth/registration-links/complete/` | 未認証（リンクを持つ人） | リンクを取り消された・期限が切れた直後に complete を送り込む／同じリンクを 2 本同時に使う | 鍵つきの引き直しで 400・使用は 1 回だけ | Yes: TC-02・TC-03（守りを外すと落ちる版つき） | No | なし | Low |
| 5 | `seed_e2e` | 運用者（コマンドを流せる人） | 本番の DB で誤って流して、既知のパスワードの運営アカウントを作る | DEBUG が偽なら止まる | Yes: TC-12（DEBUG 偽で `CommandError`・利用者が増えない） | No | DEBUG を真にした本番では止まらない（本番は DEBUG 偽が前提・`check --deploy`） | Medium |
| 6 | 登録画面（`/passkey-setup`） | 未認証 | 取り消された後に押して、案内の違いからリンクの状態を探る | 開いたときと同じ文（理由を見分けさせない） | Yes: TC-08 | Yes: 手動 No.6 | なし | Low |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 0件 | 0件 |
| Medium  | 1件 | 1件 |
| Low     | 4件 | 5件 |

### 残余リスク処遇
（retro・2026-11-27）
- Medium（`seed_e2e` に既知のパスワードの運営）: 回避済み（DEBUG が偽ならコマンド全体を止める・TC-12 の `test_i636_seed_e2e_refuses_without_debug`）。DEBUG を真にした本番では止まらない点は、本番は DEBUG 偽が前提（`check --deploy`）なので受け入れ
- Low（運営の API の形の違う ID）: 回避済み（TC-01 の `test_i636_staff_delete_passkey_malformed_id_is_404`）
- Low（条件の取りこぼし）: 回避済み（条件は `invitable()` の 1 か所・TC-05 の 8 通り）
- Low（`can_manage_members` を応答に出す）: 受け入れ（本人の権限の真偽だけ）
- Low（作成の重複の `IntegrityError`）: 回避済み（セーブポイントの中で受ける・TC-04）
- 残り（標準外の形の 36 文字の `passkey_id`・問い合わせが 1 回増える）: #643 で扱う
