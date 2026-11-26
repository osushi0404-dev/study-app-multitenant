# I620 計画書: 組織の管理者が 1 回だけ使える登録用リンクを発行し、パスキーの初回登録と再登録に使う

## 基本情報
- **計画書ID**: plan_I620
- **関連イシュー**: #620
- **Draft PR**: #634
- **作成根拠資料**: docs/issues/open/I620.md（起点イシュー・設計確認メモ）
- **実装後評価**: docs/reviews/open/I620_review.md
- **作成日**: 2026-11-26

## 1. 背景/目的
- パスワードとメールアドレスをやめる（#622）と、新しい利用者の最初のパスキーの登録・端末をなくした人の再登録・無効から戻した人の登録し直しを、メールを使わずに行う手段が要る
- 組織の管理者（`role='admin'`）が、自分の組織の利用者に 1 回だけ使える登録用リンクを発行し、利用者はそのリンクからパスキーを登録してログインできるようにする。管理者は組織の利用者のパスキーを見て消せる。運営用の管理者（`is_staff`）も同じことを全組織に対してできる（本人ひとりの組織・運営のアカウントを除く）

### 調査結果
**原因の概要**: 今は利用者の登録と復旧がメール（本人確認メール・パスワード再設定メール）だけに頼っていて、アプリの中で管理者が復旧させる経路が無い。組織の管理者が利用者を管理する画面も API も無い。

**詳細**:
1. 利用者を作る API は `backend/accounts/views.py:537` の `AdminUserViewSet`（`IsAdminUser`＝`is_staff` だけ・`User.objects.all()` で組織で絞らない）。画面は `frontend/src/pages/UserManagement.tsx`・`UserEdit.tsx`・`UserCreate.tsx`（`AdminRoute`・`App.tsx:88〜90`）。組織の管理者（`role='admin'`）向けの利用者の API・画面は無い
2. パスキーの処理（I619）は `backend/accounts/passkeys.py`。challenge は DB の `WebAuthnChallenge`（用途 `register`・`login`・`reauth`）で、`consume_challenge` が自分の atomic で消してから返す。登録は `register_passkey`（検証は py_webauthn）。本人確認の印は `has_valid_reauth`（5 分）・権限 `HasRecentReauth`（`backend/accounts/permissions.py`）。ログインの応答は `complete_login`
3. **refresh トークンを失効させる仕組みが入っていない**: `backend/core/settings.py:34〜40` の `THIRD_PARTY_APPS` に `rest_framework_simplejwt.token_blacklist` が無い（`SIMPLE_JWT` の `BLACKLIST_AFTER_ROTATION=True` は効いていない。#501）。発行の時点で「ログイン中の状態を切る」（受け入れ条件）には、simplejwt の公式の失効の表（`OutstandingToken`・`BlacklistedToken`）が要る
4. 画面のトークン更新は `/api/auth/token/refresh/`（存在しない URL・`frontend/src/services/api.ts:141`）を呼ぶので毎回 404（#502）。失効の表を入れても画面の動きは変わらない（#501 の本文の「どちらを先に入れても安全」）
5. 本人ひとりの組織の利用者は、自分の組織の `role='admin'`（I539・`backend/accounts/serializers.py:113〜120`）。そのままでは新しい画面が出てしまう。共有の personal 組織（slug `personal`）には運営用のアカウントしか残っていない（マイグレーション 0023）。両方を外す判定は `OrganizationQuerySet.invitable()`（`backend/accounts/models.py:29`）と同じ
6. `UserManager.create_user(user_id=…, password=None)` は `set_password(None)` で使えないパスワードを付けて作れる（`backend/accounts/models.py:98`）。メールアドレスは null 可
7. 科目は組織で決まる（`backend/problems/services/tenant_scope.py` の `available_subjects`）ので、管理者が作った利用者は科目の割り当てなしに学べる
8. 画面: 管理画面 3 つは `useEffect` と `apiClient` の直呼び（TanStack Query ではない）。パスキーの画面（I619）は `hooks/usePasskeys.ts`（TanStack Query）・`hooks/usePasskeyReauth.ts`（印はメモリだけ・`withReauth`）・`components/settings/PasskeyReauthDialog.tsx`・`services/passkey.service.ts`（`createPasskeyCredential`）。ログインの保存は `contexts/AuthContext.tsx:160` の `establishSession`。テストは Jest（`react-scripts test`）で、サービスを `jest.mock` で差し替える。フォームは React Hook Form＋yup（`package.json:34`・zod は #552）。QR のライブラリは無い
9. QR のライブラリ: `qrcode.react` 4.2.0（npm の最新・依存なし・peer は React 16.8〜19）。SVG で描く（`QRCodeSVG`）
10. E2E: `e2e/tests/passkey.spec.ts` が CDP の仮想の認証器の付け方の手本。seed（`seed_e2e.py`）の `e2e_user_b` は org_b の管理者（`is_individual=False`）
11. 経路の表 `backend/core/tests/test_I446_cross_api_tenant_isolation.py` に新しい経路を足さないと `test_route_table_matches_urlconf` が落ちる。OpenAPI の対象は `backend/core/openapi.py` の `CONTRACT_PATHS`

## 2. 受け入れ条件
1. 組織の管理者は、自分の組織の利用者の一覧を見て、ユーザー ID だけで利用者を作れる。ほかの組織の利用者・運営のアカウントは一覧に出ず、番号を指しても 404
2. 組織の管理者は、自分の組織の利用者（ほかの組織の管理者を含む）に限って登録用リンクを発行・失効できる。ほかの組織の利用者・運営のアカウントは 404、自分自身・無効の利用者は 400
3. 本人ひとりの組織・共有の personal 組織の管理者には「メンバー管理」のメニューが出ず、その API は 403
4. 組織の管理者の API には、役割の変更・利用者の無効化の手段が無い
5. 運営用の管理者は、どの組織の利用者にも発行・失効・パスキーの一覧と削除ができる。運営のアカウント・本人ひとりの組織の利用者・自分自身・無効の利用者は 400。運営のアカウントあては管理コマンドでだけ発行できる
6. 組織の管理者は自分の組織の利用者の、運営用の管理者はどの組織の利用者の、パスキー（名前・登録日・最後に使った日）を見て消せる（範囲は発行と同じ）
7. 発行・失効・パスキーの削除は、管理者本人の直前（5 分以内）の本人確認が無いと 403
8. リンクの値は 256 ビットの乱数で、DB にはその SHA-256 だけが残り、元の値は発行の応答で一度だけ返る
9. 発行した直後の画面に、リンクの文字・コピーのボタン・QR コード・有効期限・「閉じると二度と表示できない」が出る
10. リンクの期限は 1 時間。1 人につき有効なリンクは 1 つで、出し直すと前のリンクは使えない
11. リンクは 1 回だけ使え、期限切れ・使用済み・失効・利用者か組織が無効のものは、どれも同じ文で拒まれる
12. 同じリンクを同時に使っても、登録は 1 回だけ成功する
13. 発行した時点で、その利用者の古いパスキーがすべて消え、その時点の refresh トークンでは更新できない（401）
14. リンクからパスキーを登録すると、その利用者としてログインした状態になる（無効から有効に戻した利用者も含む）。そのパスキーで次からログインできる
15. 設定画面のパスキーの欄と、リンクから開く登録画面に、2 台以上の端末で使うことの案内が出る
16. 発行・使用・失効・管理者によるパスキーの削除がログに残り、リンクの値はログにも DB にも平文で残らない
17. 発行 → 登録 → ログインの E2E が CI で通る

## 3. 影響範囲
- Backend: accounts（モデル・マイグレーション・サービス・権限・シリアライザ・ビュー・URL・管理コマンド）・core（設定〔`token_blacklist`・スロットル・期限〕・OpenAPI の対象・経路の表のテスト）
- Frontend: メンバー管理の画面（新規）・リンクから開く登録画面（新規）・運営の利用者の編集画面・設定画面のパスキーの欄・メニュー・ルート・AuthContext・サービス・フック・依存（`qrcode.react`）・API の型
- DB: 表 3 つの追加（`registration_links`・simplejwt の `token_blacklist_outstandingtoken`・`token_blacklist_blacklistedtoken`）・`webauthn_challenges.purpose` の選択肢の追加（列の型は変わらない）。どれも足すだけ
- Config/Infra: 依存の追加（`qrcode.react`）で frontend のコンテナの `npm install` が要る。`docker-compose.yml`・Dockerfile は変えない（`package.json` から入る）

## 4. 変更点一覧（具体）

### 修正アプローチ
- リンクは「推測できない乱数を 1 回だけ見せ、DB にはハッシュだけを置く」標準的な形（OWASP の Forgot Password・招待リンクと同じ）。値は URL の `#`（フラグメント）に入れ、サーバーのアクセスログ・Referer に載らないようにする。登録画面は開いたらすぐにアドレスバーから `#` 以降を消す
- 発行・使用の業務の処理は新しいサービス `backend/accounts/registration_links.py` に置き、ビューは薄くする（Django 規約 §6・§7）。パスキーの検証は I619 の処理を使い、自前の暗号は書かない
- 「ログイン中の状態を切る」は simplejwt の公式の失効の表を入れて行う（自作の仕組みを作らない・規約 §1「自作のトークン」を使わない）。入れるのは #501 の一部（アプリの追加とマイグレーション）だけで、ログアウトの例外の扱い・表の掃除は #501 に残す（#501 にコメントする）
- 組織の境界は `get_queryset()` で利用者の組織に絞り、範囲の外は 404（規約 §5）。対象にできない利用者（自分・無効・運営・本人ひとりの組織）は、範囲の中なら 400 で理由を返す
- 画面は I619 の本人確認の部品（`usePasskeyReauth`・`PasskeyReauthDialog`）をそのまま使い、メンバー管理と運営の編集画面で同じ部品（`components/members/`）を使う。新しいデータ取得は TanStack Query（React 規約 §5）

### 4-1. モデル（`backend/accounts/models.py`）とマイグレーション
**達成すること**: リンクをハッシュで持ち、1 人に有効なリンクが 1 つだけになることを DB で守る。
```python
class RegistrationLink(models.Model):
    """管理者が発行する、パスキーを登録するための 1 回だけのリンク（I620）。値は SHA-256 だけを持つ"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # CASCADE: 利用者を消したら、その人あてのリンクは意味が無い
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registration_links')
    # SET_NULL: 発行した管理者を消しても、記録（いつ・誰あてに）は残す。管理コマンドは null
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    token_hash = models.CharField(max_length=64)  # sha256 の 16 進
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'registration_links'
        constraints = [
            models.UniqueConstraint(fields=['token_hash'], name='registration_link_token_hash_unique'),
            # 1 人に「使っていない・失効していない」リンクは 1 つだけ（期限切れは発行のときに失効にする）
            models.UniqueConstraint(fields=['user'], condition=models.Q(used_at__isnull=True, revoked_at__isnull=True),
                                    name='registration_link_one_open_per_user'),
            models.CheckConstraint(condition=models.Q(used_at__isnull=True) | models.Q(revoked_at__isnull=True),
                                   name='registration_link_not_used_and_revoked'),
        ]
        indexes = [models.Index(fields=['expires_at'])]
```
- `WebAuthnChallenge.Purpose` に `LINK_REGISTER = 'link_register'` を足す（13 文字・`max_length=16` に収まる。`AlterField` は選択肢だけ）
- マイグレーション `0025_registration_link.py`（`RegistrationLink` の追加と `purpose` の選択肢）。`token_blacklist` は simplejwt のマイグレーションで入る

### 4-2. 設定（`backend/core/settings.py`）
- `THIRD_PARTY_APPS` に `'rest_framework_simplejwt.token_blacklist'` を足す（#501 の一部を同梱。理由は 9）
- `REGISTRATION_LINK_TTL_SECONDS = 3600`（設計確認メモ: 1 時間）・`REGISTRATION_LINK_PATH = '/passkey-setup'`（画面の道筋。URL は `FRONTEND_URL + REGISTRATION_LINK_PATH + '#token=' + 値`）
- スロットル `DEFAULT_THROTTLE_RATES` に `'registration_link_options': '20/min'`・`'registration_link': '10/min'`（ログインと同じ考え方。認証なしで challenge の行を増やされないため）

### 4-3. サービス（新しい `backend/accounts/registration_links.py`）
**達成すること**: 発行・失効・使用・管理者のパスキー削除と、対象にできる利用者の判定を 1 か所に置く。全関数キーワード専用・型ヒントつき。利用者向けの失敗は `passkeys.PasskeyError`（400・決まった文）。ログは `logger.info('registration link issued user_id=%s link_id=%s issued_by=%s', …)` の形で、値・ハッシュは出さない。
- 定数: `LINK_UNUSABLE = 'このリンクは使えません。管理者に新しいリンクを発行してもらってください'`・`CANNOT_TARGET_SELF = '自分あてには操作できません。ほかの管理者か運営に依頼してください'`・`INACTIVE_TARGET = '無効の利用者には発行できません'`・`STAFF_TARGET = '運営のアカウントには画面から発行できません'`・`INDIVIDUAL_TARGET = '個人利用の利用者には発行できません'`
- `hash_token(token: str) -> str`: `hashlib.sha256(token.encode()).hexdigest()`（値は 256 ビットの乱数なので、遅いハッシュは要らない）
- `ensure_target(*, actor: User, target: User, scope: Literal['org', 'staff']) -> None`: 自分なら `CANNOT_TARGET_SELF`・無効なら `INACTIVE_TARGET`（発行のときだけ・パスキーの削除は無効の人にも許す）・`scope='staff'` で `target.is_staff or target.is_superuser` なら `STAFF_TARGET`・本人ひとりの組織なら `INDIVIDUAL_TARGET`（組織の管理者の範囲では、運営と本人ひとりの組織の人は `get_queryset` で外れて 404 になる）
- `revoke_sessions(*, user: User) -> int`: 期限内の `OutstandingToken`（`user=user`・未失効）をすべて `BlacklistedToken` にする（`bulk_create(ignore_conflicts=True)`）。数を返す
- `issue_link(*, target: User, issued_by: User | None) -> tuple[RegistrationLink, str]`: `transaction.atomic` の中で、対象の利用者の行を `select_for_update()` で押さえ（同じ人への同時の発行を一列にする）→ 開いているリンクに `revoked_at=今` → パスキーをすべて消す → `revoke_sessions` → `secrets.token_urlsafe(32)`（43 文字）で値を作り、ハッシュで 1 行作る（期限 `今 + REGISTRATION_LINK_TTL_SECONDS`）。値はこの戻り値だけで返す
- `link_url(token: str) -> str`: `f'{settings.FRONTEND_URL}{settings.REGISTRATION_LINK_PATH}#token={token}'`
- `revoke_link(*, target: User, revoked_by: User | None) -> bool`: 開いているリンクがあれば `revoked_at=今`。冪等（無ければ False）
- `_usable_link(token: str, *, lock: bool) -> RegistrationLink`: ハッシュで引き（`lock` なら `select_for_update(of=('self',))`・`select_related('user__organization')`）、無い・使用済み・失効・期限切れ・利用者か組織が無効なら、ログに `reason=` を残して `PasskeyError(LINK_UNUSABLE)`（理由を見分けさせない）
- `link_registration_options(*, token: str) -> tuple[WebAuthnChallenge, dict, User]`: `_usable_link(lock=False)` → `passkeys.registration_options` と同じ options を用途 `LINK_REGISTER` で作る（`passkeys.py` の options の組み立てを `_registration_options(user, purpose)` に切り出して両方で使う）
- `complete_link_registration(*, token: str, challenge_id: UUID, credential: dict, user_agent: str) -> dict`: まず `_usable_link(lock=False)` で利用者を知る → `consume_challenge(purpose=LINK_REGISTER, user=その利用者)`（コミット済み）→ `transaction.atomic` の中で `_usable_link(lock=True)` で引き直し（同時の 2 回目はここで使用済みを見て拒む）→ 利用者が変わっていないか確かめる → `passkeys` の検証と作成（`register_passkey` の検証・作成の部分を `verify_and_create_passkey(*, user, challenge, credential, user_agent)` に切り出して両方で使う。重複は今と同じ文で 400・そのときリンクは未使用のまま）→ `used_at=今` → 終わったら `passkeys.complete_login(user=…)` を返す
- `list_passkeys_of(*, target)`・`delete_passkey_of(*, target, passkey_id, deleted_by) -> None`: 対象の利用者のパスキーだけから引く（無ければ `Http404`）。ログ `passkey deleted by admin user_id=… passkey_id=… deleted_by=…`

### 4-4. `backend/accounts/passkeys.py` の切り出し（振る舞いは変えない）
- `registration_options(*, user)` の中身を `_registration_options(*, user, purpose)` に移し、`registration_options` はそれを `Purpose.REGISTER` で呼ぶ
- `register_passkey` の検証と作成を `verify_and_create_passkey(*, user, challenge: bytes, credential, user_agent) -> Passkey` に移す。`register_passkey` は上限の確認・`consume_challenge(REGISTER)`・それを呼ぶ。I619 のテスト（`test_I619_passkeys.py`）がそのまま通ること

### 4-5. 権限（`backend/accounts/permissions.py`）
- `IsOrgMemberManager(BasePermission)`: 認証済み・`role == 'admin'`・組織があり有効・`Organization.objects.invitable()` に入る組織（本人ひとりの組織と共有の personal 組織を外す）。`message = 'メンバーを管理する権限がありません'`

### 4-6. シリアライザ（`backend/accounts/serializers.py`）
- `MemberSerializer`（出力）: `id`・`user_id`・`role`・`is_active`・`last_login`・`created_at`・`passkey_count`（int・注釈）・`registration_link_expires_at`（開いていて期限内のリンクの期限・無ければ null）・`is_self`（bool）
- `MemberCreateSerializer`（入力）: `user_id` だけ（3〜30 文字・`^[a-zA-Z0-9_]+$`・既にあれば 400「このユーザーIDは既に使用されています」。検証は `UserRegistrationSerializer` と同じ文）
- `RegistrationLinkIssuedSerializer`（出力）: `url`（文字列）・`expires_at`（日時）
- `RegistrationLinkTokenSerializer`（入力）: `token`（`^[A-Za-z0-9_-]{43}$`。違えば 400 で `LINK_UNUSABLE` と同じ文）
- `RegistrationLinkOptionsSerializer`（出力）: `challenge_id`・`options`・`user_id`
- `RegistrationLinkCompleteSerializer`（入力）: `token`・`challenge_id`・`credential`
- `UserSerializer` に読み取りだけの `organization_is_individual`（`source='organization.is_individual'`・組織が無ければ false）を足す（画面がメニューを出し分ける）

### 4-7. ビュー・URL（`backend/accounts/views.py`・`urls.py`）
エラーは `core.exceptions.custom_exception_handler` の形 `{"error": {"main_message", "sub_message", "details"}}`。

| URL | メソッド | 権限 | スロットル | 本文 | 成功 | 失敗 |
|---|---|---|---|---|---|---|
| `/api/members/` | GET | `IsAuthenticated`＋`IsOrgMemberManager` | 既定 | なし（`?page=`） | 200 `{"count","next","previous","results":[MemberSerializer]}`（自分の組織・運営を除く・`user_id` 順・20 件） | 401・403 |
| `/api/members/` | POST | 同上 | 既定 | `{"user_id"}` | 201 `MemberSerializer`（`role: "user"`・自分の組織・使えないパスワード） | 400（形・重複）・401・403 |
| `/api/members/{id}/passkeys/` | GET | 同上 | 既定 | なし | 200 `{"count","next","previous","results":[{"id","name","created_at","last_used_at"}]}` | 401・403・404 |
| `/api/members/{id}/passkeys/{passkey_id}/` | DELETE | 同上＋`HasRecentReauth` | 既定 | なし | 204 | 400（自分）・401・403・404 |
| `/api/members/{id}/registration-link/` | POST | 同上＋`HasRecentReauth` | 既定 | なし | 201 `{"url","expires_at"}` | 400（自分・無効）・401・403・404 |
| `/api/members/{id}/registration-link/` | DELETE | 同上＋`HasRecentReauth` | 既定 | なし | 204（開いたリンクが無くても 204） | 400（自分）・401・403・404 |
| `/api/admin/users/{id}/passkeys/` | GET | `IsAdminUser` | 既定 | なし | 200（上と同じ形） | 400（運営・本人ひとり）・401・403・404 |
| `/api/admin/users/{id}/passkeys/{passkey_id}/` | DELETE | `IsAdminUser`＋`HasRecentReauth` | 既定 | なし | 204 | 400（自分・運営・本人ひとり）・401・403・404 |
| `/api/admin/users/{id}/registration-link/` | POST | `IsAdminUser`＋`HasRecentReauth` | 既定 | なし | 201 `{"url","expires_at"}` | 400（自分・無効・運営・本人ひとり）・401・403・404 |
| `/api/admin/users/{id}/registration-link/` | DELETE | `IsAdminUser`＋`HasRecentReauth` | 既定 | なし | 204 | 400（自分・運営・本人ひとり）・401・403・404 |
| `/api/auth/registration-links/options/` | POST | `AllowAny`（ログイン前に開くため） | `registration_link_options` | `{"token"}` | 200 `{"challenge_id","options","user_id"}`（`authenticatorSelection.residentKey: "required"`・`userVerification: "required"`・`excludeCredentials: []`） | 400 `sub_message: LINK_UNUSABLE`・429 |
| `/api/auth/registration-links/complete/` | POST | `AllowAny`（同上） | `registration_link` | `{"token","challenge_id","credential"}` | 200 `{"access","refresh","user"}` | 400（`LINK_UNUSABLE`・検証失敗・重複）・429 |

- `MemberViewSet(ListModelMixin, CreateModelMixin, GenericViewSet)`（`router.register(r'members', …)`）: `get_queryset()` は `User.objects.filter(organization_id=request.user.organization_id, is_staff=False, is_superuser=False)` に `annotate(passkey_count=Count('passkeys'))` と、開いていて期限内のリンクの期限の `Subquery` を付ける（N+1 を作らない）。`get_permissions()` で action ごとに全部書く（`destroy_passkey`・`registration_link` の POST/DELETE は `HasRecentReauth` を足す・規約 §6）。`perform_create` は `User.objects.create_user(user_id=…, password=None, organization=request.user.organization, role='user')`
- `MemberViewSet` の `@action(detail=True, methods=['get'], url_path='passkeys')`・`@action(detail=True, methods=['delete'], url_path=r'passkeys/(?P<passkey_id>[0-9a-f-]{36})')`・`@action(detail=True, methods=['post', 'delete'], url_path='registration-link')`
- `AdminUserViewSet` に同じ 3 つの action を足し、`get_permissions()` を足す（今の action は `[IsAdminUser()]` のまま。新しい書き込みの action だけ `HasRecentReauth` を足す）
- `RegistrationLinkOptionsView`・`RegistrationLinkCompleteView`（`GenericAPIView`・`AllowAny`・`AppScopedRateThrottle`）。`path()` は router の `include` より前に置く
- `MemberViewSet.lookup_value_regex = '[0-9a-f-]{36}'`
- すべてに `extend_schema`。`backend/core/openapi.py` の `CONTRACT_PATHS` に新しい 6 つのパス（`/api/members/`・`/api/members/{id}/passkeys/`・`/api/members/{id}/passkeys/{passkey_id}/`・`/api/members/{id}/registration-link/`・`/api/auth/registration-links/options/`・`/api/auth/registration-links/complete/`）を入れ（`UserSerializer` の変更は、契約に入っている `/api/auth/passkeys/login/` の `LoginResponse` を通してスキーマに出る）、`backend/openapi.yaml`・`frontend/src/types/api/schema.d.ts` を作り直す（`docs/runbooks/common-commands.md` の手順）。運営の 3 つの action は今の `AdminUserViewSet` と同じく契約の外（画面は手で型を付けず `types/api` の `RegistrationLinkIssued`・`Passkey` を使う）

### 4-8. 管理コマンド（新しい `backend/accounts/management/commands/issue_registration_link.py`）
- `python manage.py issue_registration_link <user_id>`: 利用者を `user_id` で引き（無ければ `CommandError('利用者が見つかりません')`）、無効なら `CommandError(INACTIVE_TARGET)`、`issue_link(target=…, issued_by=None)` → 標準出力に URL と期限を出す（ログには値を出さない）。運営のアカウント（`is_staff`・`is_superuser`）にも使える（画面・API からは出せないため）

### 4-9. 経路の表（`backend/core/tests/test_I446_cross_api_tenant_isolation.py`）
- `/api/admin/users/<pk>/` の下の新しい 4 つ（GET・DELETE passkeys、POST・DELETE registration-link）は `ROUTE_TABLE` に `DRF_STAFF`（組織の管理者・一般の利用者は 403）
- `/api/members/` の下と `/api/auth/registration-links/` の下は `OUT_OF_SCOPE` に理由「利用者の番号は利用者の組織で絞る／リンクの値で本人を決め、問題・科目・記録の番号を受け取らない（境界は accounts/tests/test_I620_registration_links.py）」

### 4-10. 画面（frontend）
- `package.json`: `"qrcode.react": "4.2.0"`（版を固定）
- `constants/routes.ts`: `MEMBER_MANAGEMENT_PATH = '/members'`・`PASSKEY_SETUP_PATH = '/passkey-setup'`
- `types/api/index.ts`: `Member`・`PaginatedMemberList`・`MemberCreate`・`RegistrationLinkIssued`・`RegistrationLinkOptions` の短い名前
- `services/member.service.ts`: `memberService`（`list(page)`・`create(userId)`）と、`credentialApi(base: '/api/members/' | '/api/admin/users/')` が返す `passkeys(id)`・`deletePasskey(reauthToken, id, passkeyId)`・`issueLink(reauthToken, id)`・`revokeLink(reauthToken, id)`（`X-Reauth-Token` を付ける）。`registrationLinkService`（`options(token)`・`complete(token, challengeId, credential)`）
- `hooks/useMembers.ts`: 一覧（`useQuery`・キー `['members', userId, page]`）・作成（`useMutation`・成功で一覧を読み直す）
- `hooks/useMemberCredentials.ts`: `base` と相手の id を受け、パスキーの一覧（キー `['member-passkeys', base, id]`）・削除・発行・失効（成功で一覧と `['members']` を読み直す）
- `components/members/RegistrationLinkDialog.tsx`: MUI の `Dialog`。見出し「『{user_id}』の登録用リンク」・`QRCodeSVG`（`value=url`・`size=192`・`aria-label="登録用リンクの QR コード"`）・読み取りだけの `TextField`（`label="リンク"`）と「コピー」ボタン（`navigator.clipboard.writeText` → トースト「リンクをコピーしました」。失敗は「コピーできませんでした。リンクを選んでコピーしてください」）・「有効期限: YYYY/MM/DD HH:MM（1 時間・1 回だけ）」（`Intl.DateTimeFormat('ja-JP', { timeZone: 'Asia/Tokyo' })`）・警告の `Alert`「この画面を閉じると、リンクは二度と表示できません」・［閉じる］。値は親の state にだけ置き、閉じたら捨てる
- `components/members/IssueLinkConfirmDialog.tsx`: 「『{user_id}』の登録用リンクを発行しますか？」「今のパスキーはすべて使えなくなり、ログイン中の端末もログアウトされます。」［キャンセル］［発行する］
- `components/members/MemberPasskeysDialog.tsx`: 「『{user_id}』のパスキー」・一覧（名前／登録日／最後に使った日・I619 の `PasskeysCard` と同じ書き方）・各行のごみ箱（`aria-label="『名前』を削除"`・44px）→ 確認「『名前』を削除しますか？このパスキーではログインできなくなります」→ 本人確認 → トースト「パスキーを削除しました」。4 つの状態（読み込み中・失敗・空「パスキーはまだありません」・あり）
- `components/members/MemberCredentialActions.tsx`: 1 人分の［登録用リンク］［パスキー］［リンクを取り消す］（リンクが開いているときだけ）と、上の 3 つのダイアログ・本人確認（`usePasskeyReauth`・`PasskeyReauthDialog` を使う）をまとめる。`base` を受けてメンバー管理と運営の編集画面の両方で使う。成功のトースト「登録用リンクを発行しました」「登録用リンクを取り消しました」
- `components/members/AddMemberDialog.tsx`: 「メンバーを追加」・`ユーザーID` の欄（React Hook Form＋yup・`mode: 'onTouched'`・必須・3〜30 文字・半角英数字と `_`・サーバーの誤りは `setError`）［キャンセル］［追加してリンクを発行］→ 作成 → 本人確認 → 発行 → `RegistrationLinkDialog`。送信中はボタンを止める
- `pages/MemberManagement.tsx`: 見出し「メンバー管理」・［＋ メンバーを追加］・表（ユーザーID／役割〔管理者・メンバー〕／パスキー〔n 個〕／登録用リンク〔「有効（HH:MM まで）」か「なし」〕／操作）。自分の行は操作の代わりに「（自分は操作できません）」。4 つの状態（`toLoadState`）。20 件を超えたら MUI の `Pagination`。幅 360px では表を横に流せる `TableContainer`
- `pages/PasskeySetup.tsx`（ログイン不要）: 開いたら `location.hash` から `token` を読み、`window.history.replaceState` で `#` 以降を消す → `registrationLinkService.options` → 見出し「パスキーの登録」・「ユーザーID『{user_id}』のパスキーを登録します」・案内の `Alert`（info）「2 台以上の端末で使えるようにしてください。iCloud キーチェーンや Google パスワード マネージャーなど、端末どうしで同期されるパスキーがおすすめです」・［パスキーを登録］→ `createPasskeyCredential` → `AuthContext.completeRegistrationLink` → `/dashboard`・トースト「パスキーを登録しました」。使えないリンク（値が無い・400）は `Alert`（error）「このリンクは使えません。管理者に新しいリンクを発行してもらってください」。非対応のブラウザは I619 と同じ「このブラウザはパスキーに未対応です」でボタンを止める。登録の取り消し・失敗は I619 の `passkeyErrors` の文（もう一度押せる。challenge は押すたびに取り直す）
- `contexts/AuthContext.tsx`: `completeRegistrationLink({ token, challengeId, credential })` を足す（`registrationLinkService.complete` → `establishSession`）
- `components/Layout.tsx`: `isOrgAdmin && !user.organization_is_individual` のとき「科目管理」の後に「メンバー管理」（アイコン `Group`・`/members`）
- `App.tsx`: 公開のルート `/passkey-setup`、保護のルート `members`（`OrgAdminRoute`＋本人ひとりの組織なら「このページにアクセスする権限がありません」）
- `pages/UserEdit.tsx`（運営）: 「パスキーと登録用リンク」の `Card` を 1 つ足し、`MemberCredentialActions`（`base='/api/admin/users/'`）を置く。運営・本人ひとりの組織の利用者には「この利用者には画面から発行できません」を出して部品を置かない（裏側も 400）
- `components/settings/PasskeysCard.tsx`: 説明の下に案内の `Alert`（info・上と同じ文）

### 4-11. E2E（新しい `e2e/tests/registration-link.spec.ts`）
- 空の storageState で `e2e_user_b`（org_b の管理者）がパスワードでログイン → `/members` → ［メンバーを追加］で `e2e_link_<時刻>` → 本人確認（パスワード）→ リンクのダイアログの「リンク」の欄の値を読む → ［閉じる］→ 新しいブラウザのコンテキスト（ログインなし）に仮想の認証器を付けてそのリンクを開く → 「ユーザーID『e2e_link_…』のパスキーを登録します」→［パスキーを登録］→ `/dashboard` → ログアウト →「パスキーでログイン」で `/dashboard`。最後に管理者の画面を読み直して、その行が「1 個」「なし」になっている

## 5. 実装手順（ステップ）
1. **未知リスク: 失効の表**: 設定に `token_blacklist` を入れて `migrate`、`RefreshToken.for_user` が `OutstandingToken` を作り、`BlacklistedToken` にしたトークンで `/api/auth/refresh/` が 401 になることを確かめる → TC-04（失効の部分）。ログアウト（`logout_view`）が 200 になることも見る（#501 へのコメントに書く）。ステップ 3 の前
2. **パスキーの処理の切り出し**: 4-4（振る舞いは変えない）→ I619 のテスト（TC-15）。ステップ 3 の前
3. **縦の 1 本目（発行と使用）**: モデル・マイグレーション・設定・サービス（発行・使用・失効）・公開の 2 つの API・組織の管理者の発行と失効・権限 `IsOrgMemberManager` → TC-03〜TC-07・TC-11。認可（組織の境界・本人確認）は同じステップで入れる
4. **縦の 2 本目（一覧・作成・パスキー）**: `MemberViewSet` の一覧・作成・パスキーの一覧と削除 → TC-01・TC-02・TC-08。ステップ 3 の後
5. **運営と管理コマンド**: `AdminUserViewSet` の 3 つの action・管理コマンド・経路の表 → TC-09・TC-10・TC-14。ステップ 3 の後（ステップ 4 と並行してよい）
6. **OpenAPI と画面の型**: `UserSerializer`・`CONTRACT_PATHS`・`openapi.yaml`・`schema.d.ts`・`types/api/index.ts` → TC-12・TC-13。ステップ 4・5 の後
7. **画面（登録画面）**: `qrcode.react` を入れる・`routes.ts`・`member.service.ts` の `registrationLinkService`・`AuthContext.completeRegistrationLink`・`PasskeySetup.tsx`・`App.tsx` の公開ルート・`PasskeysCard` の案内 → TC-24・TC-25。ステップ 6 の後
8. **画面（メンバー管理・運営）**: `member.service.ts` の残り・`useMembers`・`useMemberCredentials`・`components/members/` の 5 つ・`MemberManagement.tsx`・`Layout.tsx`・`App.tsx`・`UserEdit.tsx` → TC-20〜TC-23・TC-26。ステップ 7 の後
9. **E2E** → TC-30。ステップ 8 の後
- 依存の追加があるので、実装後に frontend のコンテナの中で `npm install`、backend は `migrate` が要る（サービスの再起動が要る）

## 6. テスト計画
### 自動
- テストのレベル: 裏側の業務の規則（リンクの寿命・同時使用・組織の境界・失効・本人確認）は pytest の結合テスト（API を通す・`backend/accounts/tests/test_I620_registration_links.py`）。WebAuthn の応答は I619 のソフトの認証器（`webauthn_soft_authenticator.py`）で作り、py_webauthn の検証を差し替えない。同時使用は `django_db(transaction=True)` とスレッド 2 本で本物の行の鍵を通す。画面の部品は Jest＋React Testing Library（サービスと `@simplewebauthn/browser`・`qrcode.react` は差し替えず、サービスだけ `jest.mock`。今の書き方に合わせる）。通しの流れは Playwright の E2E（仮想の認証器）
- 認可・テナントの境界のテスト: 未認証 401・一般の利用者 403・本人ひとりの組織の管理者 403・別の組織の利用者 404・運営のアカウント 404（組織の管理者）／400（運営）・自分 400（TC-01〜TC-03・TC-08・TC-09）
- 期限のテストは、行の `expires_at` を過去に書き換えて作る（時刻を差し替えない）
- 詳細は `docs/tests/open/I620_auto_test.md`（TC-01〜TC-15・TC-20〜TC-26・TC-30）
### 手動
- Claude が Playwright MCP（`http://localhost:3000`・仮想の認証器）で、メンバー管理の画面・発行のダイアログ・QR・登録画面・使えないリンク・運営の編集画面・メニューの出し分け・360px の幅・キーボード操作を確かめる（`docs/tests/open/I620_manual_test.md`）。人に頼む項目は無い（実際の端末での登録は I619 の No.12 で確かめた同じ登録の処理を使う。スマホで QR を読む確かめは、手元のアプリが `localhost` なのでスマホからは開けず、QR に入る値は TC-21 で確かめる）

## 7. ロールバック
- PR を revert する。マイグレーションは表を足すだけなので `python manage.py migrate accounts 0024` と `python manage.py migrate token_blacklist zero` で戻せる（リンクと失効の行は消える。消えても困らない: リンクは 1 時間で切れる・失効の表が無くなると #501 の前の状態に戻るだけ）
- 依存（`qrcode.react`）は revert で外れる。frontend のコンテナで `npm install` し直す

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 組織の管理者が自分の組織の人になりすます（リンクを発行して自分の端末で登録する） | 発行の時点で古いパスキーと refresh トークンを消す（本人が締め出されて気づける）・本人確認 5 分・ログに `issued_by` を残す。管理者の仕組みである以上なくせない（設計確認メモでユーザー了承） | 受け入れ |
| R2: 発行した後も、本人の端末のアクセストークンが最長 60 分使える | refresh は失効させる。アクセストークンの即時の失効は simplejwt の設計の外（#501 と同じ扱い）。パスキーの追加には本人確認（パスキーは消えている）が要るので、居座りの手段は無い | 受け入れ |
| R3: リンクの値が URL・ログ・Referer に漏れる | 値は `#` の後ろ（サーバーに送られない）・画面が開いたらすぐ消す・ログと DB に平文を置かない（TC-11）・1 時間・1 回だけ | 回避 |
| R4: 同じリンクの同時使用で 2 つ登録される | 使用の確定を行の鍵（`select_for_update`）の中で行い、使用済みを見たら拒む。TC-07 | 回避 |
| R5: 同じ人への同時の発行で開いたリンクが 2 つになる | 利用者の行の鍵で一列にし、DB の部分一意制約でも止める。TC-03 | 回避 |
| R6: 失効の表を入れると、画面のトークン更新の後の強制ログアウトが起きる | 画面の更新は今も毎回 404（`api.ts:141`・#502）なので、rotation の失効は起きない。#501 の本文どおり | 回避 |
| R7: 失効の表を入れると、E2E のログアウトが共有の storageState の refresh を失効させる | 画面は refresh を使えていない（R6）のでアクセストークン 60 分の中で通る。E2E が落ちたら共有の状態を使う spec を空の状態にする（計画変更で決める） | 回避 |
| R8: 認証なしの API を叩いて challenge の行を増やす | スロットル（20/min・10/min・IP ごと）・期限切れの行を消してから作る（I619 と同じ） | 回避 |
| R9: 使えない理由（期限切れ・失効・無効の利用者）を応答で見分けられる | 文を 1 つにそろえ、理由はログの `reason=` だけ。TC-05 | 回避 |
| R10: `qrcode.react` に脆弱性・悪い版が入る | 版を固定・implement で `npm audit` を見る（high/critical は直す） | 回避 |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 組織の管理者向けの「メンバー管理」の画面と API を作る（一覧・ユーザー ID だけの作成・リンクの発行と失効・パスキーの一覧と削除）。役割の変更と無効化は任せない
- 本人ひとりの組織の管理者にはメニューを出さず API も拒む
- 古いパスキーと refresh トークンは発行の時点で消す・期限 1 時間・1 人に 1 つ・出し直すと前のものは失効
- 発行・失効・パスキーの削除の前に 5 分以内の本人確認
- 組織の管理者自身の再登録は同じ組織のほかの管理者か運営。自分あてには出せない。運営のアカウントあては管理コマンドだけ
- 運営は全組織に発行できる（本人ひとりの組織の利用者・運営のアカウントを除く）
- 個人利用の人は案内だけ（復旧用のコードは #633）・記録はサーバーのログ
- 画面の配置と文言（メンバー管理・発行の確認・発行した直後・登録画面）は 2026-11-26 にユーザーが案を了承（このイシューの /plan-issue で確認）
Claude が決めた（技術的な選択と理由）:
- 失効の表（`token_blacklist`）を #501 から同梱する — 受け入れ条件の「ログイン中の状態を切る」に simplejwt の公式の仕組みが要る（規約 §10・自作の仕組みを作らない）。#501 の本文が「入れる順はどちらでも安全」としている。ログアウトの例外の扱い・表の掃除は #501 に残し、#501 にコメントする
- リンクの値は `secrets.token_urlsafe(32)`（256 ビット）・保存は SHA-256（値が十分長い乱数なので遅いハッシュは要らない・OWASP の Forgot Password と同じ）
- 値は URL の `#token=` に入れる（サーバーのログ・Referer に載らない）。画面は読み取ったらすぐ `replaceState` で消す
- 範囲の外（ほかの組織・運営）は 404、範囲の中で対象にできない人（自分・無効）は 400 で理由を出す（規約 §5・管理者に理由が分かる）
- 公開の 2 つの API の失敗の文は 1 つにそろえる（I619 と同じ・理由はログだけ）
- リンクの使用は「options → complete」の 2 回で、使用の確定は complete の中だけ（options だけでは使ったことにならない）。challenge は新しい用途 `link_register` にし、ログイン済みの登録の challenge と混ぜない
- 一覧の数とリンクの期限は `annotate`・`Subquery` で 1 回のクエリにする（TC-01 でクエリの数を確かめる）
- 管理者が作った利用者は使えないパスワードで作る（`create_user(password=None)`）。#622 まではパスワードでは入れない
- 運営の画面は今の `UserEdit.tsx` に部品を 1 つ足すだけにする（運営の画面全体の作り直し〔TanStack Query 化〕はしない・範囲を広げない）
- フォームの検証は yup（今の `package.json` にあり I619 も yup。zod への移行は #552）
- QR は `qrcode.react` 4.2.0 の `QRCodeSVG`（依存なし・React 18 に対応・SVG で拡大しても崩れない）
- 人の手動テストは置かない（理由は 6 手動）
- 一覧 `docs/reviews/backlog/I223.md` B1〜B4・`docs/reviews/backlog/I224.md` F9（`FILE=-`）: 残す — ハーネスの bot・計測の話で、このイシューの変更点と関係しない
セキュリティ・ベストプラクティス:
- 入力: リンクの値は形（43 文字の URL 安全な文字）をシリアライザで確かめる・ユーザー ID は今の登録と同じ規則・パスキーの応答の中身は py_webauthn が確かめる
- 認可: 最小権限（組織の管理者は自分の組織の一般の利用者と管理者だけ・運営は運営のアカウントと本人ひとりの組織の人を除く）。権限は `permissions.py` のクラスで止め、ビューの `if` だけにしない（規約 §10）
- 機密: リンクの値はハッシュだけを保存・ログに出さない・応答は発行の 1 回だけ・画面の state だけに置く。refresh の失効は公式の表
- OWASP: 総当たり（256 ビット＋スロットル）・CSRF（JWT のヘッダー認証で Cookie を使わない）・XSS（`dangerouslySetInnerHTML` を使わない・QR は SVG の部品）・情報の漏れ（失敗の文を 1 つに）
- 依存: `qrcode.react` を足す。`npm audit` は high/critical を直す対象・bandit は MEDIUM 以上を直す対象（LOW は `# nosec` と理由）
- 高リスク判定に当たる（認証・認可の変更）ので design-security-review の対象
P3/P5/P8: DB の変更あり（10）・外部 API や非同期の処理なし（P5 影響なし）・新しいインフラなし（依存 1 つだけ・P8 影響なし）
P6: 画面の変更あり（13）
P9: 個人情報は増えない（ユーザー ID だけ・15）
Danger Ops: 無（表の追加と選択肢の追加だけ。データの削除・破壊的なマイグレーションは無い。発行でのパスキーの削除は利用者ごとの通常の操作）

## 10. データ整合性設計
- 制約: `token_hash` の一意・1 人に開いたリンクは 1 つ（部分一意）・使用と失効の同時は不可（CHECK）・外部キーは `user` CASCADE／`issued_by` SET_NULL（理由は 4-1）
- トランザクション: 発行は利用者の行の鍵の中で「前のリンクの失効 → パスキーの削除 → refresh の失効 → 新しいリンク」を 1 つにまとめる（途中で失敗すれば全部戻る）。使用は challenge の消費（先にコミット・I619 と同じ）→ リンクの行の鍵の中で「検証 → パスキー作成 → 使用済み」
- 冪等: 失効は何度呼んでも 204。発行は呼ぶたびに新しいリンク（前のものは失効）
- マイグレーション: 足すだけで戻せる（7）。既存の行の書き換えは無い

## 13. 性能・UX 設計
- N+1: 一覧は `annotate(Count('passkeys'))` と `Subquery` で 1 回（TC-01 で `django_assert_num_queries`）。ページ分け 20 件
- 4 つの状態: メンバー一覧・パスキーの一覧・登録画面（読み込み中「リンクを確かめています」・使えない・非対応・登録できる）
- 破壊的な操作の確認: 発行（パスキーが消えることを書いた確認）・パスキーの削除・リンクの取り消しは確認のダイアログ＋本人確認
- アクセシビリティ: ダイアログは MUI の `Dialog`・アイコンだけのボタンに `aria-label`・押す的 44px（I619 の No.10 の学び）・QR に `aria-label`・表の見出しは `th`
- 幅 360px: 表は `TableContainer` で横に流す・ダイアログは全幅

## 15. プライバシー・コンプライアンス設計
- 新しく持つ個人情報は無い（利用者の作成はユーザー ID だけ・メールアドレス・氏名の欄を作らない）
- ログは利用者・リンク・発行者の ID だけ（規約 §11・`core/tests/test_I437_no_pii_in_logs.py` の決まり）
- 組織の管理者が見られるのは自分の組織の利用者のユーザー ID・役割・パスキーの名前と日付だけ（テナントを越えない）
- 未成年データ・テナント越境の追加は無い

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | 組織の管理者が、ほかの組織の利用者・運営のアカウントに発行・失効・パスキーの一覧と削除ができない（TC-03・TC-08 の 404）。本人ひとりの組織の管理者は 403（TC-01） |
| V2 | 1 | 読んで可 | 同じリンクの同時使用で 1 回だけ成功する（TC-07・`transaction=True` とスレッド 2 本） |
| V3 | 1 | 読んで可 | 発行の後、前の refresh トークンで `/api/auth/refresh/` が 401・古いパスキーでログインできない（TC-03） |
| V4 | 3 | 読んで可 | リンクの値が DB の列とログに平文で残らない（TC-03 の全列の確かめ・TC-11 の caplog） |
| V5 | 2 | 読んで可 | 期限切れ・使用済み・失効・無効の利用者・無効の組織・別の用途の challenge のリンクの使用が、同じ文で拒まれる（TC-05・TC-06。各 TC は直しを外すと落ちることを確かめる） |
| V6 | 3 | 読んで可 | 運営の API で、運営のアカウント・本人ひとりの組織の利用者・自分が 400、組織の管理者が 403（TC-09・経路の表 TC-14） |
| V7 | 1 | 読んで可 | 発行・失効・パスキーの削除が本人確認なしで 403（TC-03・TC-04・TC-08・TC-09） |

## 計画変更記録
-
