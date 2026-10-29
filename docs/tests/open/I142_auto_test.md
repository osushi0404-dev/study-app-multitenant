# I142 自動テスト計画

- 対象: `backend/accounts/views.py`（登録 / validate-slug / logout）・`backend/core/exceptions.py`・`backend/core/settings.py`・`rules/ultimate_django_coding_standards.md`
- 実行: `docker compose exec backend python -m pytest accounts/tests/test_I142_error_handling.py -q`
- 新規テストファイル: `backend/accounts/tests/test_I142_error_handling.py`
- 更新テストファイル: `backend/accounts/tests/test_I140_personal_org_fallback.py`
- baseline: **94 passed**（2026-07-20 実測・`docker compose exec backend python -m pytest --tb=short -q`）

## 共通フィクスチャ（ファイルローカル）

```python
@pytest.fixture(autouse=True)
def _disable_django_ratelimit(settings):
    """登録・logout の @ratelimit は redis カウンタが実行間で共有され反復実行が flaky に
    なるため、公式スイッチで無効化する（I131/I140 と同方式）。"""
    settings.RATELIMIT_ENABLE = False


class _RequestLogCapture(logging.Handler):
    """django.request は propagate=False（core/enhanced_logging.py:327-331）のため
    pytest の caplog では捕捉できない（I142 計画時にスパイクで実証済み）。
    検証用ハンドラを直接装着して記録を取得する。"""
    def __init__(self):
        super().__init__(level=logging.ERROR)
        self.records = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture
def request_log():
    handler = _RequestLogCapture()
    logger = logging.getLogger('django.request')
    logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)
```

テストクライアントは通常の `APIClient()` を使う（`raise_request_exception=False` は**不要**。`custom_exception_handler` が Response を返すため、想定外例外はテストクライアントまで伝播しない。計画時のスパイクで実証済み）。

想定外例外の注入は次の形（本番コードに注入点を設けない）:
```python
with mock.patch.object(Organization.objects, 'filter', side_effect=RuntimeError('I142 injected')):
    resp = client.post('/api/auth/register/org-i142/', payload, format='json')
```

## テストケース（pytest）

| TC | 観点 | 手順 | 期待結果 |
|----|------|------|----------|
| TC-AUTO-01 | 想定外例外 → 統一 JSON 500（DEBUG=False） | `settings.DEBUG=False`。`Organization.objects.filter` に `RuntimeError('I142 injected')` を注入し `POST /api/auth/register/org-i142/` | `status_code == 500` かつ body 完全一致 `{"error": {"main_message": "サーバーエラー", "sub_message": "しばらく時間をおいて再度お試しください", "details": {}}}`（旧: 400「エラーが発生しました」でないこと） |
| TC-AUTO-02 | 想定外例外のスタックトレース記録 | TC-AUTO-01 と同条件で `request_log` フィクスチャを使用 | `django.request` に levelno=ERROR かつ `exc_info[0] is RuntimeError` のレコードが 1 件以上 |
| TC-AUTO-03 | DEBUG 時のみ例外詳細を露出 | `settings.DEBUG=True` で TC-AUTO-01 と同じ注入 | `status_code == 500` かつ `body['error']['sub_message'] == 'RuntimeError: I142 injected'` |
| TC-AUTO-04 | validate-slug の想定外例外 | `settings.DEBUG=False`。同じ注入で `GET /api/organizations/validate-slug/org-i142/` | `status_code == 500` かつ body 完全一致 `{"error": {"main_message": "サーバーエラー", "sub_message": "しばらく時間をおいて再度お試しください", "details": {}}}`（旧 `{"valid": false, "message": "エラーが発生しました"}` でないこと） |
| TC-AUTO-05 | 登録: 不正なリクエスト形式 | `POST /api/auth/register/org-i142/` に JSON 配列 `[1, 2]` を送信 | `status_code == 400` かつ body 完全一致 `{"error": {"main_message": "入力内容にエラーがあります", "sub_message": "不正なリクエスト形式です", "details": {}}}` |
| TC-AUTO-06 | logout 正常系＋トークン失効 | 有効ユーザーの refresh トークンで `POST /api/auth/logout/` → 同じトークンで再度 POST | 1 回目: `status_code == 200` かつ body 完全一致 `{"message": "ログアウトしました。"}`。2 回目: `status_code == 400` かつ body 完全一致 `{"error": "ログアウトに失敗しました。"}`（失効済みのため） |
| TC-AUTO-07 | logout: refresh 欠落 | `POST /api/auth/logout/` に `{}` | `status_code == 400` かつ body 完全一致 `{"error": "ログアウトに失敗しました。"}` |
| TC-AUTO-08 | logout: 無効トークン | `POST /api/auth/logout/` に `{"refresh": "not-a-valid-token"}` | `status_code == 400` かつ body 完全一致 `{"error": "ログアウトに失敗しました。"}` |
| TC-AUTO-09 | logout: 不正なリクエスト形式 | `POST /api/auth/logout/` に JSON 配列 `[]` | `status_code == 400` かつ body 完全一致 `{"error": "ログアウトに失敗しました。"}`（500 でないこと） |
| TC-AUTO-10 | 登録: serializer 検証 400 の契約維持 | 既存ユーザーと同じ `user_id` で `POST /api/auth/register/org-i142/` | `status_code == 400` かつ `body['error']['main_message'] == '入力内容にエラーがあります'` かつ `'user_id' in body['error']['details']` |
| TC-AUTO-15 | logout の想定外例外は 500（狭域捕捉の固定） | `BlacklistMixin.blacklist` に `RuntimeError` を注入して有効トークンで `POST /api/auth/logout/` | `status_code == 500` かつ body 完全一致 `EXPECTED_500_BODY`、`django.request` に `exc_info[0] is RuntimeError` のレコード（`except TokenError` を広い捕捉に戻す改変を検知する） |
| TC-AUTO-16 | personal 不在の分類（例外型の固定） | `UserRegistrationView()._get_organization(None)` を personal 不在状態で直接呼ぶ | `EnvironmentMisconfiguredError` が raise される（body 一致だけでは無関係なクラッシュと区別できないため型で固定） |
| TC-AUTO-17 | APIException 由来 5xx のスタックトレース記録 | personal 不在で `POST /api/auth/register/` | `status_code == 500` かつ `django.request` に `exc_info[0] is EnvironmentMisconfiguredError` のレコード |
| TC-AUTO-18 | ListField の 2 要素目以降の検証エラー | `subject_ids = [有効ID, "not-an-int"]` で `POST /api/auth/register/org-i142/` | `status_code == 400` かつ `main_message == '入力内容にエラーがあります'`、`sub_message` が **文字列**（従来は index キー dict への添字アクセスで KeyError → 500） |
| TC-AUTO-19 | refresh ローテーションで旧トークンを失効させない | login → 同一 refresh で `POST /api/auth/refresh/` を 2 回 → `POST /api/auth/logout/` | 1 回目・2 回目とも `200`（`BLACKLIST_AFTER_ROTATION=False` の固定）、logout は `200` |
| TC-AUTO-20 | 失効管理テーブルを admin に露出しない | `django.contrib.admin.site.is_registered()` を確認 | `OutstandingToken` / `BlacklistedToken` とも未登録（refresh トークン全文の露出面を作らない） |
| TC-AUTO-11 | personal 不在 → 500（I140 テスト更新） | personal 組織なしで `POST /api/auth/register/`（`test_I140_personal_org_fallback.py`） | `status_code == 500` かつ body 完全一致 `{"error": {"main_message": "サーバーエラー", "sub_message": "しばらく時間をおいて再度お試しください", "details": {}}}` |
| TC-AUTO-12 | personal が非アクティブのみ → 500（I140 テスト更新） | 非アクティブ personal のみ存在する状態で同 POST | TC-AUTO-11 と同じ 500 body。かつ組織が新規作成されない・active 化されない（既存アサート維持） |
| TC-AUTO-13 | I131 契約テストの GREEN 維持 | `docker compose exec backend python -m pytest accounts/tests/test_I131_org_id_rename.py -q` | **6 passed**（validate-slug 200/404×2・登録 201×2・無効 slug 400） |
| TC-AUTO-14 | 全体回帰 | `docker compose exec backend python -m pytest --tb=short -q` | 既存 **94 件** + 新規 TC が全 PASS（回帰なし） |

補足:
- 独立したテスト関数を書くのは **TC-AUTO-01〜10**（新規ファイル）と **TC-AUTO-11/12**（I140 ファイルの更新）。TC-AUTO-13/14 は pytest コマンド実行であり関数は書かない。
- TC-AUTO-11/12 は既存関数 `test_register_without_personal_org_returns_400` / `test_register_with_only_inactive_personal_org_returns_400` を 500 期待に更新し、関数名を `..._returns_500` に改名する（`EXPECTED_400_BODY` → `EXPECTED_500_BODY`）。

## 決定論チェック（exit code 判定・合格=exit 0）

| TC | 目的 | コマンド（リポジトリルートで実行） | 合格条件 |
|----|------|----------------------------------|----------|
| TC-DET-01 | accounts/views.py に広域 except が意図的な 1 箇所（メール送信）のみ。**AST 判定**（`except Exception` の文字列 grep では `except BaseException` / bare `except:` / タプル指定を見逃すため）。名前（`Exception`）・属性アクセス（`builtins.Exception`）・bare の 3 形態を検出する | `docker compose exec -T backend python -c "import ast; tree = ast.parse(open('accounts/views.py').read()); name = lambda n: n.attr if isinstance(n, ast.Attribute) else (n.id if isinstance(n, ast.Name) else None); is_broad = lambda h: h.type is None or any(name(n) in ('Exception','BaseException') for n in ([h.type] if not isinstance(h.type, ast.Tuple) else h.type.elts)); broad = [h for h in ast.walk(tree) if isinstance(h, ast.ExceptHandler) and is_broad(h)]; assert len(broad) == 1 and broad[0].name == 'email_error', [(h.lineno, h.name) for h in broad]"` | exit 0 |
| TC-DET-02 | 規約の新規節が存在する | `grep -q '^### エラーハンドリング方針' rules/ultimate_django_coding_standards.md` | exit 0 |
| TC-DET-03 | token_blacklist が有効かつローテート後失効が無効であること。**設定値の意味論判定**（grep はコメントアウト行にもマッチするため） | `docker compose exec -T backend python manage.py shell -c "from django.conf import settings; assert 'rest_framework_simplejwt.token_blacklist' in settings.INSTALLED_APPS; assert settings.SIMPLE_JWT['BLACKLIST_AFTER_ROTATION'] is False"`（`python -c` では `DJANGO_SETTINGS_MODULE` 未設定で `ImproperlyConfigured` になるため `manage.py shell -c` を使う） | exit 0 |

### false-green 自己検証
判定ロジックが「壊れている状態」で確実に不合格になることを実測で確認する。

**初版（2026-07-20・grep 判定）**: 実装前の現状に対して TC-DET-01/02/03 とも `exit=1`、目標状態を模した合成ファイルに対して `exit=0` を確認。

**改訂版（2026-07-22・敵対的レビュー指摘反映）**: 旧 TC-DET-01/03 は素通りの穴があることが実測で判明したため判定方式を差し替えた。
- 旧 TC-DET-01（`grep -c 'except Exception'`）: `except TokenError` を `except BaseException` に改変した変異体でも `1/1` で **exit 0**（＝改悪を検知できない）。→ AST 判定に変更し、同じ変異体で `exit=1`（`[(430, None), (126, 'email_error')]` を検出）を実測。
- 旧 TC-DET-03（`grep -q`）: 該当行をコメントアウトした状態でも **exit 0**。→ settings の意味論判定に変更し、アプリ未登録相当の状態で `exit=1` を実測。
- 現行コードに対しては TC-DET-01/02/03 とも `exit=0` を実測。

## 実施記録

### 実装時（/implement・2026-07-21）
- TDD Red: 実装前に新規テストを実行 → **6 failed / 4 passed**（新しい振る舞い 6 件が失敗・既存 400 契約 4 件は先行 PASS）
- TC-AUTO-01〜10: **10 passed**（`pytest accounts/tests/test_I142_error_handling.py`）
- TC-AUTO-11/12: PASS（`test_I140_personal_org_fallback.py` を 500 期待へ更新済み）
- TC-AUTO-13/14: **104 passed**（baseline 94 + 新規 10・回帰なし）
- TC-DET-01: exit 0（実装前は exit 1）
- TC-DET-02: exit 0（実装前は exit 1）
- TC-DET-03: exit 0（実装前は exit 1）

### 敵対的レビュー第 1 周の指摘反映後（2026-07-22）
- TC-AUTO-01〜20: accounts 配下 **26 passed**
- 全体回帰: **110 passed**（実装時 104 + 追加 6）
- TC-DET-01（AST 判定）: exit 0 / 変異体（`except BaseException` 化）で exit 1 を実測
- TC-DET-02: exit 0
- TC-DET-03（設定の意味論判定）: exit 0 / アプリ未登録相当で exit 1 を実測

### /test 実行時（2026-07-22）
- TC-AUTO-01〜20（accounts/tests/test_I142_error_handling.py + test_I140 + test_I131 の該当分）: **26 passed**（-v で個別 PASSED を確認）
- TC-AUTO-14（全体回帰・`pytest --tb=short -q`）: **110 passed**（回帰なし）
- TC-DET-01（AST 判定）: exit 0
- TC-DET-02（規約節の存在）: exit 0
- TC-DET-03（設定の意味論判定）: exit 0
- Frontend Jest（`npm test -- --watchAll=false`）: **10 passed**（3 suites）
- E2E（`docker compose --profile e2e run --rm e2e`）: **7 passed**（auth.spec.ts のログイン/ログアウトフロー含む）
