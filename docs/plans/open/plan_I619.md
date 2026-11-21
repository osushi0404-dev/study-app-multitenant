# I619 計画書: パスキーでログイン

## 基本情報
- **計画書ID**: plan_I619
- **関連イシュー**: #619
- **Draft PR**: #625
- **作成根拠資料**: docs/issues/open/I619.md（起点イシュー・GitHub #619 の本文の写し）
- **実装後評価**: docs/reviews/open/I619_review.md
- **作成日**: 2026-11-22

## 1. 背景/目的
- 今のログインは「メールアドレス または ユーザーID ＋ パスワード」だけ。パスワードは漏れ・使い回し・偽のサイトへの入力（フィッシング）に弱い
- ログイン済みの利用者が自分のパスキー（WebAuthn）を登録・一覧・名前の変更・削除でき、パスキーだけでログインできるようにする。手元（localhost）でも同じに動き、E2E で自動で確かめる
- 移行期間（#622 まで）はパスワードのログインも残す

### 調査結果
**原因の概要**: 認証の手段がパスワードしか無く、登録したサイトでしか使えない（偽のサイトに渡らない）手段が無い。

**詳細**:
1. ログインは `backend/accounts/views.py:38` の `CustomTokenObtainPairView`。応答は `{"access", "refresh", "user"}`（`UserSerializer`）。`last_login` を更新する（views.py:49）。経路は `backend/accounts/urls.py:14`（`/api/auth/login/`）。パスキーの経路は無い
2. 利用者の無効化の入口は 3 つある: `AdminUserViewSet.toggle_active`（views.py:498）・`AdminUserViewSet.update`（`AdminUserSerializer` の `is_active` が書ける・serializers.py:230）・Django の管理画面（`UserAdmin` の `is_active`・admin.py:23）。組織の無効化の画面・API は無い（`Organization.is_active` を書き換えるのは shell・DB だけ。grep で `organization.is_active` の書き込みは 0 件）
3. パスワードのログインは組織の有効を見ていない（serializers.py:185 は `user.is_active` だけ）。パスキーのログインでは組織の有効も見る（下の 9）
4. 回数の制限は、新しいコードでは DRF のスロットル（`core/throttling.py`・Django 規約 §10）。DRF 3.18.3 の `parse_rate` は単位の 1 文字目だけを見る（`5/5m` は 5 回/1 分になる・スパイクで確かめた）ので、`/min` で書く
5. 規約と依存の照合: Django 規約 §2（置き場所: サービス・権限は `permissions.py`）・§5（組織の境界）・§6（`AllowAny` に理由・エラーの形・OpenAPI）・§7（サービスと `transaction.atomic`・シグナル）・§10（スロットル）・§11（ログに個人情報を出さない）・§13（必ず書くテスト）。React 規約 §2（置き場所）・§4（200 行で分ける）・§5（TanStack Query）・§6（`types/api`・`extractApiErrorMessage`）・§7（4 つの状態）・§11（トークンを localStorage に置かない）・§13（アクセシビリティ）・§16（yup・Jest・axios-mock-adapter・localStorage のトークンは移行のイシューで直す差。新しいコードもこれらの今の道具を使う）
6. **スパイク（未知リスク先行・2026-11-22 に実施）**:
   - 裏側のライブラリ `webauthn`（py_webauthn・Duo Labs）3.0.1 を試しの環境に入れた。`generate_registration_options`・`verify_registration_response`・`generate_authentication_options`・`verify_authentication_response`・`options_to_json` がある。要求する Python は 3.10 以上（今の backend は 3.11）。依存は cryptography・pyOpenSSL・cbor2・pyasn1・pyasn1-modules。`pip-audit` で既知の脆弱性 0 件（試しの環境の pip 自身を除く）
   - Playwright MCP の chromium に CDP の `WebAuthn.addVirtualAuthenticator`（ctap2・internal・resident key・UV あり）を付け、`http://localhost:18765` で py_webauthn が作った options から登録（`navigator.credentials.create`）とログイン（`navigator.credentials.get`・`allowCredentials` 空＝利用者名を入れない形）をし、応答を py_webauthn で検証して **成立**（`isSecureContext=true`・登録の署名回数 1・ログインの署名回数 2・`userHandle` が登録の user.id と一致）
   - 同じ応答で、署名回数の巻き戻り（今の回数＝応答の回数）・別の origin・別の challenge・別の RP ID を py_webauthn が `InvalidAuthenticationResponse` で拒むことを確かめた（署名回数の比べ方は「両方 0 なら通す・それ以外は応答が今より大きいこと」）
   - 画面のライブラリ `@simplewebauthn/browser` 14.0.0（MIT・依存 0・CommonJS の入口 `script/index.js` があるので今の Jest〔CRA〕で読める）。`npm audit` 0 件
   - 作業場所の中（サンドボックス）では chromium が起動しない（`socket() failed: Operation not permitted`）。ブラウザの確かめは Playwright MCP で行う
   - **未実証**: e2e コンテナ（`http://frontend:3000`・`--unsafely-treat-insecure-origin-as-secure`）で RP ID `frontend` が通るか。MCP のブラウザはこの起動オプションを持たず確かめられない。CI の E2E は `http://localhost:3000`（`.github/workflows/e2e.yml:55`）なので CI には影響しない。実装ステップ 1 で確かめ、通らなければ下の R3 の回避策にする
7. 一覧の台帳（`docs/reviews/backlog/`）で当たったのは `FILE=-` のハーネスの 5 行だけ（下の 9）

## 2. 受け入れ条件
- [ ] AC1: ログイン済みの利用者が設定画面からパスキーを登録・一覧・名前の変更・削除できる（複数登録できる・最後の 1 つも削除できる）
- [ ] AC2: 一覧に名前・登録日・最後に使った日が出る。名前は登録のときに自動で付き（例: 「Windows の Chrome」）、本人が 1〜64 文字で変えられる。最後に使った日はパスキーでのログインの成功で更新され、まだ無いときは「まだ使っていません」と出る
- [ ] AC3: 登録・削除は、直前の本人確認（パスワード または 登録済みのパスキー）が無いと拒み、確認から 5 分を過ぎても拒む。他人の本人確認の印でも拒む
- [ ] AC4: ログイン画面の「パスキーでログイン」ボタンから、登録したパスキーだけで（パスワードなしで）ログインでき、パスワードのログインと同じ形（`access`・`refresh`・`user`）が返り、その後の画面の動きも同じ
- [ ] AC5: 他人（同じ組織）・別の組織の利用者のパスキーは、一覧に出ず、名前の変更・削除ができない（404）。本人確認でも他人のパスキーは使えない
- [ ] AC6: challenge は使い捨てで期限（5 分）があり、使い回し・期限切れ・別の用途（登録用をログインに）・他人の challenge を拒む
- [ ] AC7: 署名回数が前回以下（両方 0 の認証器を除く）のログインを拒む
- [ ] AC8: 利用者を無効にするとその人のパスキーが、組織を無効にするとその組織の利用者のパスキーがすべて消え、有効に戻しても戻らない。無効の利用者・組織の利用者はパスキーでログインできない
- [ ] AC9: 手元（localhost）の実際のブラウザと端末で、人がパスキーの登録とログインをできる（人の手動テスト）
- [ ] AC10: Playwright の仮想の認証器で「登録 → ログアウト → パスキーでログイン → 削除」の E2E が CI で通る
- [ ] AC11: 今のパスワードのログインは変わらず動く
- [ ] AC12: パスキーに対応していないブラウザでは、ボタンが押せず「このブラウザはパスキーに未対応です」と出る（行き止まりのエラーにしない）

## 3. 影響範囲
- Backend: accounts アプリ（モデル 2 つ・サービス・権限・シリアライザ・ビュー・URL・シグナル）、`core/throttling.py`（スロットルのクラスを 1 つ足す）、`core/settings.py`（WebAuthn の設定・スロットルのレート・CORS のヘッダー 1 つ）、`core/openapi.py`（契約にパスを足す）、`backend/openapi.yaml`（作り直し）、`backend/requirements.txt`（`webauthn==3.0.1`）
- Frontend: `pages/Login.tsx`・`pages/Settings.tsx`・`contexts/AuthContext.tsx`、新しい `services/passkey.service.ts`・`hooks/usePasskeys.ts`・`hooks/usePasskeyReauth.ts`・`components/settings/PasskeysCard.tsx`・`components/settings/PasskeyReauthDialog.tsx`・`components/settings/PasskeyRenameDialog.tsx`・`utils/passkeyErrors.ts`、`types/api/schema.d.ts`（作り直し）・`types/api/index.ts`、`package.json`・`package-lock.json`（`@simplewebauthn/browser`）。テスト: 新しい `pages/__tests__/Login.test.tsx`・`components/settings/__tests__/PasskeysCard.test.tsx`・`components/settings/__tests__/PasskeyReauthDialog.test.tsx`、今の `pages/__tests__/Settings.test.tsx`（`PasskeysCard` を差し替える）。裏側のテスト: 新しい `backend/accounts/tests/test_I619_passkeys.py`・`backend/accounts/tests/webauthn_soft_authenticator.py`。E2E: 新しい `e2e/tests/passkey.spec.ts`
- DB: 表を 2 つ足す（`passkeys`・`webauthn_challenges`）。足すだけのマイグレーション `accounts/0024_passkey_webauthnchallenge.py`
- Config/Infra: 環境変数 `WEBAUTHN_RP_ID`（既定 `localhost`）・`WEBAUTHN_RP_NAME`（既定 `学習アプリ`）・`WEBAUTHN_ALLOWED_ORIGINS`（既定は `FRONTEND_URL`＝`http://localhost:3000`）。`docker-compose.yml` の backend にパススルー（`RATELIMIT_ENABLE` と同じ書き方）。`backend/.env.example` に 3 つを足す。依存の追加で backend・frontend のイメージの作り直しが要る（backend の Dockerfile は `requirements.txt` を `pip install`・frontend のコンテナは匿名の `/app/node_modules` を使うので、コンテナの中で `npm install` する）。本番の値は本番環境ができたときに決める（今は本番環境が無い）
- Docs: `docs/runbooks/frontend-verify.md` §8（e2e コンテナで流すときの WebAuthn の前置き）・§5（パスキーでのログインの確かめ方）

## 4. 変更点一覧（具体）

### 修正アプローチ
- 裏側は py_webauthn に検証を任せ、自前で暗号を書かない。challenge は DB の表に置き（使い捨て・5 分の期限・用途と利用者に結び付け）、使うときに行を消して使い回しを止める
- ログインは利用者名を入れない形（discoverable credential・`residentKey: required`・`allowCredentials` 空）。WebAuthn の user handle は利用者の UUID（`User.id` の 16 バイト）にし、メールアドレスに頼らない
- 本人確認（5 分）は、パスワードかパスキーで確かめたときに、署名つきの短い印（reauth token）を返し、登録・削除の API はヘッダー `X-Reauth-Token` でそれを求める。印は画面のメモリにだけ置く（localStorage に置かない）
- 画面は `@simplewebauthn/browser` の `startRegistration`・`startAuthentication`・`browserSupportsWebAuthn` を使う（ブラウザごとの JSON の変換と例外の名前の差を吸収する）
- 無効化でのパスキーの削除は、`User`・`Organization` の `post_save` のシグナルで行う（入口が 3 つ以上あり、組織は shell・DB だけのため。理由は 9）。加えて、ログインのときにも利用者・組織の有効を確かめる（`update()` でシグナルを通らずに無効にした場合の守り）

### 4-1. モデル（`backend/accounts/models.py`）
**達成すること**: パスキーと challenge を保存する。
```python
class Passkey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # CASCADE: 利用者を消したら、その人の鍵は意味が無い
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='passkeys')
    credential_id = models.BinaryField(max_length=1023)          # null=False
    public_key = models.BinaryField()                             # COSE の公開鍵
    sign_count = models.PositiveBigIntegerField(default=0)
    transports = models.JSONField(default=list, blank=True)       # 例: ["internal", "hybrid"]
    name = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)    # パスキーでのログインの成功で更新
    class Meta:
        db_table = 'passkeys'
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(fields=['credential_id'], name='passkey_credential_id_unique'),
            models.CheckConstraint(condition=~models.Q(name=''), name='passkey_name_not_empty'),
        ]
        indexes = [models.Index(fields=['user', 'created_at'])]

class WebAuthnChallenge(models.Model):
    class Purpose(models.TextChoices):
        REGISTER = 'register'
        LOGIN = 'login'
        REAUTH = 'reauth'
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purpose = models.CharField(max_length=16, choices=Purpose.choices)
    # CASCADE: 利用者を消したら、その人の未使用の challenge も要らない。ログイン用は null（まだ誰か分からない）
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    challenge = models.BinaryField()   # 64 バイト（py_webauthn の既定）
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'webauthn_challenges'
        indexes = [models.Index(fields=['expires_at'])]
```
- マイグレーション `accounts/0024_passkey_webauthnchallenge.py`（`makemigrations` で作る。足すだけ）

### 4-2. 設定（`backend/core/settings.py`）
```python
WEBAUTHN_RP_ID = os.getenv('WEBAUTHN_RP_ID', 'localhost')
WEBAUTHN_RP_NAME = os.getenv('WEBAUTHN_RP_NAME', '学習アプリ')
WEBAUTHN_ALLOWED_ORIGINS = [o for o in os.getenv('WEBAUTHN_ALLOWED_ORIGINS', FRONTEND_URL).split(',') if o]
WEBAUTHN_CHALLENGE_TTL_SECONDS = 300   # challenge の期限。options の timeout も同じ値（ミリ秒）にする
PASSKEY_REAUTH_MAX_AGE_SECONDS = 300   # 本人確認の有効時間（設計確認メモ: 5 分）
PASSKEY_MAX_PER_USER = 20              # 1 人のパスキーの上限（一覧の 1 ページ＝20 件に収める）
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] に 'passkey_login': '10/min', 'passkey_reauth': '5/min' を足す
CORS_ALLOW_HEADERS に 'x-reauth-token' を足す
```

### 4-3. スロットル（`backend/core/throttling.py`）
- `AppScopedRateThrottle(LiveSettingsRateMixin, ScopedRateThrottle)` を足す（有効スイッチ・レートを毎回 settings から読む。I127 と同じ）。`RATELIMIT_ENABLE=false`（E2E）で止まる

### 4-4. サービス（新しい `backend/accounts/passkeys.py`）
**達成すること**: 登録・ログイン・本人確認の業務の処理を 1 か所に置き、ビューを薄くする。全関数キーワード専用・型ヒントつき。失敗は `PasskeyError`（`rest_framework.exceptions.ValidationError` の子・利用者向けの決まった文）を投げ、理由はログに `reason=<短い記号>` で残す（個人情報・鍵・challenge の値は出さない）。
- `issue_challenge(*, purpose, user=None) -> WebAuthnChallenge`: 期限切れの行を消してから 64 バイトの乱数で 1 行作る（期限 `WEBAUTHN_CHALLENGE_TTL_SECONDS`）
- `consume_challenge(*, challenge_id, purpose, user) -> bytes`: `transaction.atomic` の中で、id・用途・利用者（ログインは null）が一致する行を `delete()` し、消せた件数が 1 で、かつ期限内のときだけ challenge を返す。それ以外（無い・使用済み・期限切れ・他人・別の用途）はすべて同じ `PasskeyError('パスキーを確かめられませんでした。もう一度お試しください')`
- `registration_options(*, user) -> tuple[WebAuthnChallenge, dict]`: `generate_registration_options(rp_id, rp_name, user_id=user.id.bytes, user_name=user.user_id or str(user.id), user_display_name=同じ, timeout=TTL*1000, authenticator_selection=AuthenticatorSelectionCriteria(resident_key=REQUIRED, user_verification=REQUIRED), attestation=NONE, exclude_credentials=本人のパスキー全部)`。上限（20 個）なら `PasskeyError('登録できるパスキーは 20 個までです')`
- `register_passkey(*, user, challenge_id, credential: dict, user_agent: str) -> Passkey`: 上限の確認 → `consume_challenge(REGISTER)` → `verify_registration_response(expected_rp_id, expected_origin=WEBAUTHN_ALLOWED_ORIGINS, require_user_verification=True)` → `Passkey` を作る（名前は `default_passkey_name(user_agent)`）。`credential_id` の一意の制約に当たったら `PasskeyError('この端末のパスキーはすでに登録されています')`。py_webauthn の `InvalidRegistrationResponse` は決まった文の `PasskeyError` に変える
- `default_passkey_name(user_agent: str) -> str`: OS（iPhone・iPad・Android・Windows・Mac・ChromeOS・Linux）と ブラウザ（Edge・Opera・Firefox・Chrome・Safari）を順に見て「{OS} の {ブラウザ}」。分からなければ「パスキー」。64 文字に収める
- `authentication_options(*, user=None) -> tuple[WebAuthnChallenge, dict]`: ログイン（user なし・`allow_credentials` 空）と本人確認（user あり・`allow_credentials`＝本人のパスキー。0 個なら `PasskeyError('登録済みのパスキーがありません')`）。`user_verification=REQUIRED`・`timeout=TTL*1000`
- `authenticate_passkey(*, challenge_id, credential: dict, purpose, user=None) -> Passkey`: `transaction.atomic` の中で `consume_challenge` → `rawId` で `Passkey` を `select_for_update().select_related('user__organization')` で引く（無ければ失敗）→ 本人確認（purpose=REAUTH）なら `passkey.user_id == user.id` でなければ失敗 → `userHandle` があれば `passkey.user.id.bytes` と一致しなければ失敗 → 利用者が無効・組織が無効なら失敗 → `verify_authentication_response(credential_current_sign_count=passkey.sign_count, require_user_verification=True)`（署名回数の巻き戻りはここで拒まれる）→ `sign_count` を更新。ログイン（purpose=LOGIN）のときは `last_used_at` と `user.last_login` も今の時刻にする。失敗の文はすべて `'パスキーでログインできませんでした'`（ログイン）／`'パスキーを確かめられませんでした。もう一度お試しください'`（本人確認）で、理由を見分けさせない
- `issue_reauth_token(*, user) -> str`: `signing.dumps({'uid': str(user.id), 'iat': int(timezone.now().timestamp())}, salt='accounts.passkeys.reauth')`
- `has_valid_reauth(*, user, token: str | None) -> bool`: `signing.loads(salt=…)` が通り、`uid` が本人で、`0 <= 今 - iat <= PASSKEY_REAUTH_MAX_AGE_SECONDS` のときだけ True（`BadSignature` は False）
- `verify_password_for_reauth(*, user, password) -> None`: `user.check_password` が偽なら `PasskeyError('パスワードが正しくありません')`
- `build_login_response(*, user) -> dict`: `RefreshToken.for_user(user)` から `{'access', 'refresh', 'user': UserSerializer(user).data}` を作る。`CustomTokenObtainPairView.post` もこれを使うように直す（同じ形を 1 か所で作る。AC4・AC11）

### 4-5. 権限（新しい `backend/accounts/permissions.py`）
- `HasRecentReauth(BasePermission)`: `has_valid_reauth(user=request.user, token=request.headers.get('X-Reauth-Token'))`。偽なら 403（`message = '続けるには、本人であることを確かめてください'`）

### 4-6. シリアライザ（`backend/accounts/serializers.py`）
- `PasskeySerializer`（出力・`name` だけ書ける）: `id`・`name`（1〜64 文字・前後の空白を除く・空は 400）・`created_at`・`last_used_at`。`credential_id`・`public_key`・`sign_count`・`transports` は出さない
- `WebAuthnOptionsSerializer`（出力）: `challenge_id`（UUID）・`options`（object）
- `WebAuthnCredentialSerializer`（入力）: `challenge_id`（UUID・必須）・`credential`（dict・必須）
- `PasskeyReauthSerializer`（入力）: `password`（任意）か `challenge_id`＋`credential` のちょうど片方（両方・どちらも無しは 400）
- `ReauthTokenSerializer`（出力）: `reauth_token`（文字列）・`expires_in`（整数・300）
- `LoginResponseSerializer`（出力・OpenAPI の注釈用）: `access`・`refresh`・`user`（`UserSerializer`）

### 4-7. ビュー・URL（`backend/accounts/views.py`・`urls.py`）
すべて `/api/auth/passkeys/` の下。エラーは `core.exceptions.custom_exception_handler` の形 `{"error": {"main_message", "sub_message", "details"}}`。

| URL | メソッド | 権限 | スロットル | 本文 | 成功 | 失敗 |
|---|---|---|---|---|---|---|
| `/api/auth/passkeys/login/options/` | POST | `AllowAny`（ログインの前に呼ぶため） | `passkey_login` | なし | 200 `{"challenge_id": UUID, "options": {…}}`（`rpId`・`challenge`・`allowCredentials: []`・`userVerification: "required"`・`timeout: 300000`） | 429 |
| `/api/auth/passkeys/login/` | POST | `AllowAny`（同上） | `passkey_login` | `{"challenge_id", "credential"}` | 200 `{"access", "refresh", "user"}` | 400 `sub_message: "パスキーでログインできませんでした"`・429 |
| `/api/auth/passkeys/reauth/options/` | POST | `IsAuthenticated` | なし（既定の user） | なし | 200 `{"challenge_id", "options"}`（`allowCredentials`＝本人のパスキー） | 400 `"登録済みのパスキーがありません"`・401 |
| `/api/auth/passkeys/reauth/` | POST | `IsAuthenticated` | `passkey_reauth` | `{"password"}` か `{"challenge_id", "credential"}` | 200 `{"reauth_token": "…", "expires_in": 300}` | 400（パスワード誤り・パスキー失敗・本文の形）・401・429 |
| `/api/auth/passkeys/` | GET | `IsAuthenticated` | なし | なし | 200 `{"count", "next", "previous", "results": [{"id", "name", "created_at", "last_used_at"}]}`（本人の分だけ・登録順） | 401 |
| `/api/auth/passkeys/register/options/` | POST | `IsAuthenticated`＋`HasRecentReauth` | なし | なし | 200 `{"challenge_id", "options"}`（`authenticatorSelection.residentKey: "required"`・`userVerification: "required"`・`attestation: "none"`・`excludeCredentials`＝本人のパスキー） | 400（上限）・401・403 |
| `/api/auth/passkeys/register/` | POST | `IsAuthenticated`＋`HasRecentReauth` | なし | `{"challenge_id", "credential"}` | 201 `{"id", "name", "created_at", "last_used_at": null}` | 400（検証失敗・重複・上限）・401・403 |
| `/api/auth/passkeys/{id}/` | PATCH | `IsAuthenticated` | なし | `{"name"}` | 200 `{"id", "name", "created_at", "last_used_at"}` | 400（空・65 文字以上）・401・404（他人・別の組織・無い） |
| `/api/auth/passkeys/{id}/` | DELETE | `IsAuthenticated`＋`HasRecentReauth` | なし | なし | 204 | 401・403・404（他人・別の組織・無い） |

- `PasskeyViewSet(ListModelMixin, UpdateModelMixin〔PATCH だけ・PUT は 405〕, DestroyModelMixin, GenericViewSet)`: `get_queryset()` は `Passkey.objects.filter(user=self.request.user)`（本人の分だけ。他人の id は 404・Django 規約 §5）。`get_permissions()` で action ごとに全部書く（`destroy`・`register_options`・`register` は `[IsAuthenticated(), HasRecentReauth()]`、ほかは `[IsAuthenticated()]`）。`register_options`・`register` は `@action(detail=False, methods=['post'], url_path='register/options')` など
- `PasskeyLoginOptionsView`・`PasskeyLoginView`・`PasskeyReauthOptionsView`・`PasskeyReauthView`（`GenericAPIView`）。`throttle_classes = [AppScopedRateThrottle]`・`throttle_scope` を指定
- すべてに `extend_schema` の注釈を付け、`core/openapi.py` の `CONTRACT_PATHS` に上の 8 つのパス（`/api/auth/passkeys/`・`/api/auth/passkeys/{id}/`・`…/register/options/`・`…/register/`・`…/login/options/`・`…/login/`・`…/reauth/options/`・`…/reauth/`）を足す。`backend/openapi.yaml` と `frontend/src/types/api/schema.d.ts` を作り直す（`docs/runbooks/common-commands.md` の手順・警告 0）
- `CustomTokenObtainPairView.post` の応答を `build_login_response(user=user)` で作る（中身は今と同じ）

### 4-8. 無効化での削除（`backend/accounts/signals.py`）
```python
@receiver(post_save, sender=User)
def delete_passkeys_of_inactive_user(sender, instance, **kwargs):
    if not instance.is_active:
        Passkey.objects.filter(user=instance).delete()

@receiver(post_save, sender=Organization)
def delete_passkeys_of_inactive_organization(sender, instance, **kwargs):
    if not instance.is_active:
        Passkey.objects.filter(user__organization=instance).delete()
```
- 有効に戻しても何もしない（消えたまま・登録し直し）

### 4-9. 画面（frontend）
- `services/passkey.service.ts`: 上の 9 つの API を呼ぶ関数（`apiClient` だけを使い、`types/api` の型を返す。登録・削除は引数の reauth token を `X-Reauth-Token` に付ける）
- `types/api/index.ts`: `Passkey`・`WebAuthnOptions`・`ReauthToken`・`LoginResponse` などの短い名前
- `utils/passkeyErrors.ts`: `@simplewebauthn/browser` の例外（`WebAuthnError` の `code`・`NotAllowedError`〔取り消し・時間切れ〕・`InvalidStateError`／`ERROR_AUTHENTICATOR_PREVIOUSLY_REGISTERED`〔同じ端末で 2 回目〕）と API の 400（`extractApiErrorMessage`）を、決まった文に変える
- `contexts/AuthContext.tsx`: `loginWithPasskey()` を足す（options → `startAuthentication({ optionsJSON })` → `/login/` → 今の `login()` と同じ保存の処理〔`establishSession(response)` に切り出して両方で使う〕→「ログインしました」）。失敗は「パスキーでログインできませんでした。もう一度試すか、パスワードでログインしてください」のトーストを出し、例外を投げ直す
- `pages/Login.tsx`: フォームの上に「パスキーでログイン」ボタン（`variant="outlined"`・鍵のアイコン・全幅・`data-testid="passkey-login-button"`）、その下に `Divider`「または」。押している間はボタンを止めて回転の印を出す。成功で今と同じ行き先（`from`）へ。`browserSupportsWebAuthn()` が偽なら、ボタンを `disabled` にして下に「このブラウザはパスキーに未対応です」を出す
- `hooks/usePasskeys.ts`: 一覧（`useQuery`・キー `['passkeys', userId]`）・名前の変更・削除・登録（`useMutation`・成功で `invalidateQueries`）
- `hooks/usePasskeyReauth.ts`: reauth token と期限（受け取った時刻＋`expires_in`−10 秒）を `useRef` で持つ（メモリだけ）。`ensureReauth()` は有効な印があればそれを返し、無ければ本人確認のダイアログを開いて結果を待つ。API が 403 を返したら印を捨てて、もう一度ダイアログを出す
- `components/settings/PasskeysCard.tsx`: 見出し「パスキー」・説明「指紋・顔・PIN でパスワードなしにログインできます」・一覧（名前／「登録 YYYY/MM/DD」／「最後に使った日 YYYY/MM/DD」か「まだ使っていません」・日付は `Intl.DateTimeFormat('ja-JP', { timeZone: 'Asia/Tokyo' })`）・各行に「名前を変える」（鉛筆・`aria-label="『名前』の名前を変える"`）と「削除」（ごみ箱・`aria-label="『名前』を削除"`）・「＋ パスキーを登録」ボタン。読み込み中（スケルトン）・失敗（「パスキーを読み込めませんでした」＋「再読み込み」）・空（「パスキーはまだありません」）・データありの 4 つ。削除は確認のダイアログ「『名前』を削除しますか？このパスキーではログインできなくなります」［キャンセル］［削除］→ 本人確認（要るとき）→ 削除 →「パスキーを削除しました」。登録は 本人確認（要るとき）→ `startRegistration({ optionsJSON })` → 登録 →「パスキーを登録しました」。非対応のブラウザでは登録のボタンを止めて同じ文を出す
- `components/settings/PasskeyReauthDialog.tsx`: MUI の `Dialog`。見出し「本人の確認」・文「続けるには、本人であることを確かめます」。パスキーがあるときだけ［パスキーで確かめる］、その下に「または」とパスワードの欄（React Hook Form＋yup・必須）［確かめる］［キャンセル］。誤りはその欄に「パスワードが正しくありません」
- `components/settings/PasskeyRenameDialog.tsx`: 名前の欄（1〜64 文字・前後の空白を除いて空はだめ）［キャンセル］［保存］→「名前を変えました」
- `pages/Settings.tsx`: 「アカウント情報」「学習設定」の行のすぐ後（「学ぶ科目」の前）に `<Grid item xs={12}><PasskeysCard /></Grid>` を置く
- `package.json`: `"@simplewebauthn/browser": "14.0.0"`（版を固定する。認証の部品なので、上げるときは Dependabot の PR で中身を見る）

### 4-10. E2E（`e2e/tests/passkey.spec.ts`）
- `chromium-authed` の project で動くが、`test.use({ storageState: { cookies: [], origins: [] } })` で空の状態から始め、`e2e_user_b` でパスワードのログインをする（ログアウトで共有の storageState のリフレッシュトークンを無効にしないため）。CDP で仮想の認証器を付ける → 設定画面 →「パスキーを登録」→ 本人確認（パスワード）→ 一覧が 1 つ増える → ログアウト → ログイン画面で「パスキーでログイン」→ `/dashboard` → 設定画面 → 増やした行を削除（本人確認は新しいセッションなので出る。［パスキーで確かめる］を使う）→ 一覧が元の数に戻る

### 4-11. 手順書
- `docs/runbooks/frontend-verify.md` §8: e2e コンテナで流すときの前置き `WEBAUTHN_RP_ID=frontend WEBAUTHN_ALLOWED_ORIGINS=http://frontend:3000`（ステップ 1 の結果で書き方を決める）。§5: Playwright MCP でパスキーを確かめるときは `browser_run_code_unsafe` で CDP の仮想の認証器を付ける

## 5. 実装手順（ステップ）
1. **未知リスク: e2e コンテナでの RP ID**（他のステップを止めない・結果で R3 の回避策を選ぶ）: 4-1〜4-4 の最小（ログインの options と検証）を入れた後、e2e コンテナで `passkey.spec.ts` の登録までを流し、RP ID `frontend` が通るかを確かめる → TC-30（手元）。通らなければ、spec の頭で `baseURL` の host が `localhost` でないときは `test.skip`（理由のコメントつき）にし、frontend-verify.md §8 にそう書く
2. **縦の 1 本目（ログイン）**: モデル・マイグレーション・設定・スロットル・サービス（challenge・ログイン・`build_login_response`）・ログインの 2 つの API・`CustomTokenObtainPairView` の切り替え → TC-01・TC-07・TC-08・TC-10・TC-11・TC-13。ステップ 3 の前
3. **縦の 2 本目（本人確認・登録・一覧・名前・削除）**: 権限 `HasRecentReauth`・本人確認の 2 つの API・`PasskeyViewSet`・既定の名前 → TC-02〜TC-06・TC-12。認証・認可（本人確認・本人の分だけ）は守る対象の API と同じステップで入れる。ステップ 2 の後
4. **無効化での削除**: シグナル 2 つ → TC-09。ステップ 2 の後（ステップ 3 と並行してよい）
5. **OpenAPI と画面の型**: `CONTRACT_PATHS`・`extend_schema`・`openapi.yaml`・`schema.d.ts`・`types/api/index.ts` → TC-14。ステップ 3 の後
6. **画面（ログイン）**: `@simplewebauthn/browser` を入れる・`passkey.service.ts`・`passkeyErrors.ts`・`AuthContext.loginWithPasskey`・`Login.tsx` → TC-20。ステップ 5 の後
7. **画面（設定）**: `usePasskeys`・`usePasskeyReauth`・`PasskeysCard`・`PasskeyReauthDialog`・`PasskeyRenameDialog`・`Settings.tsx`（`Settings.test.tsx` は `PasskeysCard` を差し替える）→ TC-21・TC-22・TC-23。ステップ 6 の後
8. **E2E・設定・手順書**: `passkey.spec.ts`・`docker-compose.yml`・`backend/.env.example`・frontend-verify.md → TC-30。ステップ 7 の後
- 依存の追加があるので、実装後に backend のイメージの作り直し（`docker compose build backend`）と frontend のコンテナの中の `npm install` が要る（サービスの再起動が要る）

## 6. テスト計画
### 自動
- テストのレベル: 裏側の業務の規則（challenge・署名回数・本人確認・組織の境界・無効化）は pytest の結合テスト（API を通す）。WebAuthn の応答はテスト用のソフトの認証器（`backend/accounts/tests/webauthn_soft_authenticator.py`・cryptography の EC P-256 と cbor2 で attestation `none` と assertion を作る）で作り、本物の py_webauthn の検証を通す（検証を差し替えない）。画面の部品は Jest＋React Testing Library（`@simplewebauthn/browser` と `passkey.service` を `jest.mock` で差し替える・今のテストの書き方に合わせる）。通しの流れは Playwright の E2E（仮想の認証器）
- 認可・テナントの境界のテスト: 未認証 401・他人（同じ組織）と別の組織の利用者のパスキーの一覧・名前・削除・本人確認（TC-03〜TC-06）
- 期限のテストは、期限切れの行・印を直接作る（challenge は `expires_at` を過去にした行・reauth token は `iat` を 301 秒前にした印を `signing.dumps` で作る）ので、時刻の差し替えは要らない
- 詳細は `docs/tests/open/I619_auto_test.md`（TC-01〜TC-14・TC-20〜TC-23・TC-30）
### 手動
- Claude が Playwright MCP（`http://localhost:3000`・仮想の認証器）で画面の表示・流れ・非対応のブラウザ・360px の幅を確かめる。実際の端末（指紋・顔・PIN）での登録とログインだけを人に頼む（`docs/tests/open/I619_manual_test.md`）

## 7. ロールバック
- PR を revert する。マイグレーション 0024 は表を足すだけなので `python manage.py migrate accounts 0023` で戻せる（パスキーと challenge の行は消える。利用者はパスワードでログインできるので困らない）
- 依存（`webauthn`・`@simplewebauthn/browser`）は revert で外れる。イメージの作り直しが要る

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: challenge の使い回し・期限切れ・他人の challenge で通る | DB の行を `delete()` で消せたときだけ使う（同時の 2 回でも 1 回だけ通る）・期限と用途と利用者を条件に入れる。TC-02・TC-08 | 回避 |
| R2: 盗まれたアクセストークンで攻撃者が自分のパスキーを足し、居座る | 登録・削除に 5 分の本人確認（パスワードかパスキー）を求める。印は署名つき・本人に結び付け・画面のメモリだけ。TC-01・TC-05・TC-06 | 回避 |
| R3: e2e コンテナ（`http://frontend:3000`）で RP ID `frontend` を chromium が拒む | ステップ 1 で確かめ、拒まれたら手元のコンテナでは passkey.spec を `test.skip`（CI は localhost で流れる） | 回避 |
| R4: 利用者を `QuerySet.update()` で無効にしてシグナルを通らず、パスキーが残る | ログインのときに利用者・組織の有効を確かめて拒む。TC-08 | 回避 |
| R5: ログインの API（認証なし）を叩いて challenge の行を増やす | スロットル `passkey_login`（10/min・IP ごと）・行を作る前に期限切れの行を消す・期限 5 分 | 回避 |
| R6: 失敗の理由（パスキーが無い・無効の利用者など）を応答で見分けられる | ログインの失敗の文をすべて同じにし、理由はログ（`reason=`）だけに残す。TC-08 | 回避 |
| R7: `@simplewebauthn/browser` の型が TypeScript 4.9 で読めない | ステップ 6 で型チェック（`npm run typecheck`）を通す。読めなければ、使う関数の型だけを `src/types/` に書いて `skipLibCheck` に頼らない形を計画変更で決める | 回避 |
| R8: 署名回数を持たない認証器（いつも 0・iCloud キーチェーンなど）が拒まれる | py_webauthn は両方 0 なら通す（スパイクで確かめた比べ方）。TC-08 に 0/0 で通る場合を入れる | 回避 |
| R9: 本人確認の印は 5 分の間は何度でも使える（登録・削除を続けてできる） | 設計確認メモの決定（5 分は確かめ直さずに続けて操作できる）どおり。印は本人だけ・画面のメモリだけ | R9: 受け入れ |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- ログイン画面は「パスキーでログイン」ボタンだけ（入力欄の候補〔conditional UI〕は作らない）。今の ID・パスワードの欄の上に置く
- 登録・削除の前に本人確認（パスワード または 登録済みのパスキー）。有効は 5 分
- 一覧は 名前＋登録日＋最後に使った日。名前は自動で付き、本人が変えられる。最後に使った日はパスキーでのログインの成功で更新
- 利用者・組織を無効にしたらパスキーをすべて消す。有効に戻しても戻らない
- 管理者が利用者のパスキーを見る・消す操作は作らない（#620）。登録の勧めはしない（#622）。最後の 1 つも消せる
- 画面の配置・流れ・文言は、計画の前にユーザーに案（ログイン画面・設定画面の「パスキー」の欄・削除と本人確認の流れ・成功と失敗の文）を見せて「この案で進める」と確定（2026-11-22）。設定画面の欄は「アカウント情報」と「学習設定」の行のすぐ後（「学ぶ科目」の前）に横幅いっぱいで置く（「アカウント情報のすぐ下」を、md の幅で 2 列の行を崩さない置き方にした）

Claude が決めた（技術的な選択と理由）:
- 裏側のライブラリは py_webauthn（`webauthn==3.0.1`）。理由: WebAuthn の検証（attestation・署名・origin・RP ID・UV・署名回数）を持ち、Django に縛られない小さな部品で、スパイクで仮想の認証器と通しで動いた。django-otp-webauthn は django-otp の枠組み（2 段階目の認証）を前提にし、JWT のログインに合わない
- 画面のライブラリは `@simplewebauthn/browser` 14.0.0（版を固定）。理由: ブラウザの `parseCreationOptionsFromJSON` は新しいブラウザにしか無く、例外の名前もブラウザで違う。依存 0・MIT
- challenge は Redis でなく DB の表に置く。理由: 今の Redis は `allkeys-lru` で消されることがあり、`IGNORE_EXCEPTIONS=True` で失敗が見えない。DB なら `delete()` の件数で使い捨てを決められ、テストで期限切れを直接作れる（`EmailVerification` と同じ考え方）
- 本人確認は、署名つきの印（`django.core.signing`・salt 付き・`uid` と `iat`）をヘッダー `X-Reauth-Token` で受ける。理由: アクセストークン（盗まれうる）だけでは足りず、印はパスワードかパスキーを知っている人しか得られない。DB に状態を持たず、期限は `iat` で決めるのでテストで時刻を差し替えなくてよい
- 失敗の応答は 400（`ValidationError` の子の `PasskeyError`）で、文を理由ごとに分けない（R6）。本人確認が無い・切れたは 403（`HasRecentReauth`）。他人・別の組織のパスキーは 404（`get_queryset` で本人に絞る）
- 回数の制限は DRF のスロットル（Django 規約 §10）。`passkey_login` 10/min（options と検証の両方・IP ごと）・`passkey_reauth` 5/min（利用者ごと）。DRF のレートは単位が 1 つ（1 分）しか書けないので、今のパスワードのログイン（django-ratelimit の 5/5m）より緩いが、パスキーは推測できない（署名を作れない）ので総当たりの心配はなく、行を増やす攻撃を止めれば足りる
- パスキーのログインは、パスワードの失敗でかかるアカウントのロック（`account_locked_until`）を見ない。理由: ロックはパスワードの総当たりを止めるためのもので、パスキーは推測できない。見ると、攻撃者がパスワードを 5 回間違えるだけで本人がパスキーでも入れなくなる
- パスキーのログインは組織の有効も見る（パスワードのログインは見ていない。パスワードのログインを直すのはこのイシューの範囲外）。理由: 組織を無効にしたらパスキーで入れないという決定（AC8）を、シグナルを通らない無効化でも守るため（R4）
- 無効化での削除はシグナル（`post_save`）に置く。Django 規約 §7 は「シグナルに業務の処理を書かない」だが、ここは例外にする。理由: 利用者の無効化の入口が 3 つ（`toggle_active`・`AdminUserViewSet.update`・Django の管理画面）あり、組織の無効化は shell・DB にしか入口が無い。どの入口でも必ず消える（後片付けで、呼び忘れの事故が起きない）ことを、入口ごとにサービスを呼ぶ形より優先する。処理は「無効なら消す」1 行だけで、呼び出しの流れを追う必要がない
- 1 人のパスキーの上限は 20（`PASSKEY_MAX_PER_USER`）。理由: 一覧のページ分け（20 件）の 1 ページに収め、画面にページ送りを作らずに済む。上限の文「登録できるパスキーは 20 個までです」・欄の置き場所・本人確認のダイアログの見出し「本人の確認」・パスキーでの確認の失敗の文・一覧の読み込みの失敗の文と「再読み込み」は、画面の案に無かったので 2026-11-22 にユーザーに確かめ「このとおりでよい」と確定
- WebAuthn の user handle は `User.id`（UUID の 16 バイト）、端末に見せる名前は `user_id`（無ければ UUID）。理由: メールアドレスに頼らず（#622 で消す）、個人情報を端末に渡さない
- 署名つきの印の有効は、画面では「受け取った時刻＋300 秒−10 秒」で切れたとみなす（時計のずれで 403 を受けにくくする）。403 を受けたら印を捨ててダイアログを出し直す
- `CustomTokenObtainPairView` の応答を `build_login_response` に切り出す（中身は今と同じ。パスワードとパスキーで同じ形を 1 か所で作る）
- 画面の通知は今の設定画面と同じく react-hot-toast を直接使う（`NotificationContext` にトーストの関数が無い。React 規約 §1 との差は今の設定画面と同じ）
- フォームは今の画面と同じく React Hook Form＋yup（zod は #552 で入れる・React 規約 §16）。テストは Jest（#551）・API の差し替えは `jest.mock`（#511 の MSW は入れない）
- トークンの保存場所（localStorage）は今のログインと同じ（#553・#502 で直す）。パスキーのログインも同じ `establishSession` を通す
- 一覧の台帳: `docs/reviews/backlog/I223.md` B1〜B4・`docs/reviews/backlog/I224.md` F9（`FILE=-`）: 残す — どれもハーネスの項目（bot の後片付け・測定）で、このイシューの変更と関係ない

セキュリティ・BP の確認（plan-issue の必須チェック）:
- 入力の検証: 本文はすべてシリアライザで検証（UUID・dict・名前の長さ）。WebAuthn の応答の中身は py_webauthn の解析と検証に任せ、自前で解かない
- 認証・認可: 最小の権限（`AllowAny` はログインの 2 つだけ・理由をコメント）。登録・削除は本人確認つき。本人の分だけ（`get_queryset`）
- 機密データ: 保存するのは公開鍵・認証器の ID・署名回数・transports・名前・日時だけ。秘密鍵・生体の情報は端末から出ない。ログに鍵・challenge・印・個人情報を出さない（Django 規約 §11・`core/tests/test_I437_no_pii_in_logs.py` が止める範囲）
- OWASP: CSRF は JWT のヘッダー認証で Cookie を使わない（今と同じ）。XSS は名前を React のテキストとして出す（`dangerouslySetInnerHTML` を使わない）。フィッシングはパスキーの RP ID と origin の検証で止まる。リプレイは challenge の使い捨てと署名回数で止まる
- 依存の脆弱性: `webauthn==3.0.1` と依存は `pip-audit` 0 件・`@simplewebauthn/browser@14.0.0` は `npm audit` 0 件（2026-11-22）。基準: bandit は MEDIUM 以上を直す（LOW は `# nosec` と理由）・npm audit は high/critical を直す・pip-audit は全件
- 高リスク判定: Yes の見込み（認証の追加・認可・新しい公開 API・DB の表の追加）。design-security-review の対象

Danger Ops（有無）:
- 無（表を足すだけのマイグレーション。無効化のときの削除は、利用者ごとの通常の業務の処理）

## 10. データ整合性設計
- 制約: `passkeys.credential_id` は UNIQUE（同じ認証器の 2 回の登録・別の利用者への付け替えを DB で止める）。`name` は空でない（CHECK）。外部キーは CASCADE（理由は 4-1）
- トランザクション: 登録（challenge の消費＋行の作成）・ログインと本人確認（challenge の消費＋パスキーの行の `select_for_update`＋署名回数・最後に使った日・`last_login` の更新）をそれぞれ `transaction.atomic` で囲む。同じパスキーで同時に 2 回ログインしても、行の鍵で順番になり、2 回目は署名回数の比べで拒まれる
- 冪等: challenge は 1 回しか使えないので、二重送信の 2 回目は 400（パスキーが 2 つできない）
- マイグレーション: 表を 2 つ足すだけ。今の行に触れない。戻すと 2 つの表が消える（7）

## 11. 運用設計
- 外部 API・非同期処理・バッチは無い。ログ: 成功は `logger.info("passkey login ok user_id=%s passkey_id=%s", …)`、失敗は `logger.warning("passkey login failed reason=%s", reason)`（`reason` は `challenge`・`unknown_credential`・`inactive`・`user_handle`・`verify` など）。個人情報・鍵・challenge・印は出さない
- Feature Flag は使わない（パスワードのログインが残るので、パスキーが動かなくてもログインはできる）

## 12. コスト・保守見積もり
- インフラの費用は増えない（DB の小さな表 2 つ）。依存が 2 つ増える（`webauthn` と、その依存の cryptography など・`@simplewebauthn/browser`）。Dependabot の対象になる
- 運用者の手作業: 本番を作るときに `WEBAUTHN_RP_ID`・`WEBAUTHN_ALLOWED_ORIGINS` を決める（本番のドメイン）。RP ID を後で変えると、登録済みのパスキーが全部使えなくなる（手順書に書く）

## 13. 性能・UX設計
- 一覧は本人の分だけ（上限 20）で N+1 は無い（関連をたどらない）。ログインは `select_related('user__organization')`
- 4 つの状態: 一覧は読み込み中（スケルトン）・失敗（文＋再読み込み）・空（「パスキーはまだありません」）・データあり
- 待つとき: ログイン・登録・本人確認の間はボタンを止めて回転の印を出す（二重に押せない）
- 破壊的な操作: 削除は確認のダイアログ（名前を出す）→ 本人確認 → 削除。取り消しのボタンを置く
- エラー: 失敗の文は次にすること（もう一度・パスワードで）を書く（ux-rules §1）。パスワードの欄は誤っても消さない
- アクセシビリティ: アイコンだけのボタンに `aria-label`（どのパスキーかを入れる）・ダイアログは MUI の `Dialog`・キーボードで操作できる・スマホの幅（360px）で行の文字が折り返してはみ出さない・押す的は 44px 以上
- 非対応のブラウザ: ボタンを止めて理由を出す（行き止まりのエラーにしない・AC12）

## 15. プライバシー・コンプライアンス設計
- 新しく持つ個人に関わる値は、パスキーの名前（端末の種類から作る・本人が変えられる）・登録日・最後に使った日だけ。公開鍵と認証器の ID は個人を表さない。生体の情報は持たない（WebAuthn の性質・C2）
- 端末に渡すのは `user_id`（表示名）と UUID（user handle）で、メールアドレス・氏名は渡さない
- 削除: 本人が消せる・無効化で全部消える・利用者を消すと CASCADE で消える
- テナントの境界: 一覧・名前・削除は本人の分だけで、組織を越えて読めない（TC-03〜TC-05）。未成年のデータの新しい扱いは無い

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | challenge が 1 回しか使えない（同じ challenge_id の 2 回目・期限切れ・別の用途・他人の challenge が 400）。TC-02・TC-08 が本物の py_webauthn の検証を通した応答で確かめているか |
| V2 | 1 | 読んで可 | 登録・削除が本人確認の印なし・期限切れ（`iat` 301 秒前）・他人の印・改ざんした印で 403 になる。TC-01・TC-05 |
| V3 | 1 | 読んで可 | 他人（同じ組織）・別の組織のパスキーの一覧・名前・削除・本人確認ができない（404／400）。TC-03〜TC-06 |
| V4 | 2 | 読んで可 | ソフトの認証器で作った応答が本物の検証を通っていて、検証を差し替えていない（`verify_*` を `mock` していない）。署名回数の巻き戻り（5→5）が 400・0/0 が 200 になることを TC-08 が実際の値で確かめているか |
| V5 | 3 | 読んで可 | 無効化の 3 つの入口（`toggle_active`・`AdminUserViewSet.update`・`save()`）と組織の `save()` で消え、`update()` で無効にした利用者・組織はログインで拒まれる。TC-09・TC-08 |
| V6 | 3 | 読んで可 | ログインの応答の形がパスワードのログインと同じ（キーと `user` の中身）で、アクセストークンで `/api/auth/me/` が読める。TC-07・TC-10 |
| V7 | 1 | 実験必須 | 実際のブラウザ（仮想の認証器）で、登録 → ログアウト → パスキーでログイン → 削除が通る（E2E の TC-30 が CI で通ったことで確かめる） |

## 計画変更記録
-
