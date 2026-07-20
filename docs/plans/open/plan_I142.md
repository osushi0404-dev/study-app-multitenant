# plan_I142: accounts API の広域 except Exception 丸めを解消 — 想定外例外はログ+500 で顕在化させる

## 基本情報
- **計画書ID**: plan_I142
- **関連イシュー**: #253
- **Draft PR**: #256
- **作成根拠資料**: docs/issues/open/I142.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I142_review.md
- **作成日**: 2026-07-20

---

## 1. 背景/目的

### 原因の概要（平易な説明）
`accounts/views.py` の 3 つの API は「何かエラーが起きたら、種類を問わずまとめて捕まえて、決まったエラーメッセージを返す」書き方（広域 `except Exception`）になっている。そのため、利用者の入力ミス（本来 4xx）と、プログラムの欠陥（本来 5xx）が同じ見た目のエラーに丸められ、障害が起きても「エラーが発生しました」としか出ず、監視・ログからも区別できない。実際に I131 では、新規登録が全件できない重大欠陥がこの丸めにより長期間潜伏していた。

### 詳細な原因分析
1. `UserRegistrationView.create`（`accounts/views.py:75-129`）: `try` が処理全体を包み、`except Exception` で **400** を返す。プログラム欠陥がクライアント起因エラーとして返る。
2. `OrganizationSlugValidationView.get`（`accounts/views.py:217-242`）: 単純な ORM 検索のみなのに `except Exception` で独自形式の 500（`{'valid': false, 'message': 'エラーが発生しました'}`）を返し、例外種別が消える。
3. `logout_view`（`accounts/views.py:419-429`）: `KeyError`（refresh 欠落）・`TokenError`（無効トークン）と想定外欠陥を区別せず一律 400。

根本原因は「想定内の例外は種別ごとに捕捉し、想定外の例外は捕捉せず例外ハンドラに委ねる」という規約が存在せず、防御的な広域捕捉が常態化していること。DRF の `EXCEPTION_HANDLER`（`core.exceptions.custom_exception_handler`）が全例外を受け取れる構造は既にあるため、ビュー側の広域捕捉は不要である。

### 計画時に実測で判明した追加の欠陥（本計画で対応）
- **logout は現在、有効な refresh トークンでも必ず 400 を返す**（実測・調査結果 4 参照）。`rest_framework_simplejwt.token_blacklist` が INSTALLED_APPS 未登録のため `token.blacklist()` が `AttributeError` になり、広域 except が握りつぶしていた。広域 except を外すとこの欠陥が毎回 500 として表面化するため、**blacklist アプリを有効化して根治する**（イシューで確定・2026-07-20）。

### 目的
- 想定外例外を 5xx として正しく可観測化する（品質基準 C7 信頼性・運用性）
- 想定内エラーの既存レスポンス契約を壊さない
- 同種の再発を防ぐ規約を `rules/ultimate_django_coding_standards.md` に明文化する

---

## 2. 調査結果

### 調査1: 環境前提確認
| 項目 | 結果 |
|------|------|
| Docker サービス稼働 | backend / db / redis / frontend いずれも Up（`docker compose ps`・2026-07-20） |
| バックエンドテスト実行系 | `docker compose exec backend python -m pytest`（`backend/pytest.ini`・`addopts = --no-migrations`） |
| flake8 | **コンテナ未導入**（`flake8: executable file not found`）。lint は pre-commit の **ruff**（`.pre-commit-config.yaml:18-21`）と **bandit**（同 :26-29）が担当 |
| 既存テスト baseline | **94 passed, 5 warnings**（`docker compose exec backend python -m pytest --tb=short -q`・2026-07-20 実測。失敗ゼロ） |

### 調査2: スパイク（DRF が非 APIException でもカスタムハンドラを呼ぶか）
**成立**。DRF `APIView.handle_exception` は全例外に対し `EXCEPTION_HANDLER` を呼び、戻り値が `None` のときだけ再送出する（`rest_framework/views.py`）。`rest_framework.views.exception_handler` は `Http404` / Django `PermissionDenied`（django-ratelimit の `Ratelimited` を含む）/ `APIException` を処理し、それ以外で `None` を返す。

プロトタイプハンドラを `api_settings.EXCEPTION_HANDLER` に差し替え、`ValueError` を投げるビューを実行した結果（scratchpad `spike_i142.py`・コンテナ内 `/tmp` で実行・リポジトリ無改変）:
```
STATUS: 500
BODY: {"error":{"main_message":"サーバーエラー","sub_message":"しばらく時間をおいて再度お試しください","details":{}}}
```
→ 想定外例外を統一 JSON 500 に変換する設計は成立する。

### 調査3: スパイク（想定外例外のログをテストで捕捉できるか）
**caplog では捕捉できない**。`core/enhanced_logging.py:327-331` で `django.request` ロガーは `propagate: False` のため、pytest の `caplog`（root にハンドラを装着）には届かない（`spike_i142.py` で `RECORDS: []` を実測）。
**専用ハンドラ装着なら捕捉できる**。`logging.getLogger('django.request')` に検証用 `logging.Handler` を addHandler する方式で `RECORDS: [('django.request', 'ERROR', True)]`（exc_info あり）を実測（`spike_i142b.py`）。→ 自動テストはこの方式を採用する。

### 調査4: スパイク（logout の現行実挙動）
**現行 logout は有効な refresh トークンでも 400 を返す**（`spike_i142c.py` 実測）:
```
LOGOUT STATUS: 400 BODY: {"error":"ログアウトに失敗しました。"}
```
原因: `rest_framework_simplejwt.token_blacklist` が INSTALLED_APPS に無く（`core/settings.py:36` は `rest_framework_simplejwt` のみ）、`RefreshToken` に `blacklist` メソッドが生えない（`hasattr(RefreshToken, 'blacklist') == False` を実測）→ `AttributeError` → 広域 except が 400 に丸めていた。FE（`frontend/src/services/auth.service.ts:34-44`）は API 失敗時もローカルログアウトを継続するため、UI 上は表面化していなかった。

### 調査5: 想定内例外の洗い出し（登録ビュー try 節）
| 発生源 | 例外 | 現状 | 変更後 |
|--------|------|------|--------|
| `self._get_organization(slug)`（slug 指定・不在） | 例外なし（`None` 返却） | 400「組織の設定に失敗しました」 | **変更なし**（クライアント起因の 400 維持） |
| `self._get_organization(None)`（personal 不在） | 例外なし（`None` 返却） | 400 同上 | `EnvironmentMisconfiguredError`（500）を raise |
| `request.data.copy()` + キー代入（非 dict body） | `TypeError` | 400「エラーが発生しました」 | **事前 `isinstance` 判定で 400**（入力形式エラーとして明示） |
| `serializer.is_valid()` | 例外なし（`False` 返却） | 400「入力内容にエラーがあります」 | **変更なし** |
| `serializer.save()`（同時登録の競合等） | `IntegrityError` 等 | 400「エラーが発生しました」 | 想定外として伝播 → 500（極めて稀・重複は serializer で 400 済み） |
| `send_verification_email` | 各種 | 内側の狭域 except で握りつぶし（意図的） | **変更なし**（意図をコメントで明記） |

### 調査6: 規約ファイルの既存コード例（`rules/ultimate_django_coding_standards.md`）
| 行 | 内容 | 判定 |
|----|------|------|
| :689 | サービス層 `create_article` の `except Exception` → `ValidationError` へ変換（＝プログラム欠陥が 400 になる） | **規約と矛盾**。想定内例外の個別捕捉へ修正する |
| :1223 | Celery タスクの `except Exception` → `self.retry` | **意図的**（バックグラウンド処理のリトライ設計）。意図をコメントで明記 |
| :1403 | `LoggingMixin` の `except Exception` → ログ後に `raise` | **規約に適合**（握りつぶさない）。意図をコメントで明記 |

新規節の配置は **セクション 5「API設計（DRF）」配下の `### エラーハンドリング方針（例外設計）`** とする（同ファイル :24 が「API 設計（URL 設計・レスポンス形式・エラーハンドリング方針）」を手動レビュー対象に挙げており整合。目次番号の振り直しが不要）。

### 調査7: FE 消費箇所の全件確認
| ファイル | 参照内容 | 影響 |
|----------|----------|------|
| `frontend/src/utils/apiError.ts` | `error.sub_message` → `error.main_message` → fallback | 500 でも統一 JSON を返すため**変更不要** |
| `frontend/src/contexts/AuthContext.tsx` | 登録・ログイン時のエラートースト（`main_message`） | 想定外欠陥時のみ文言が「サーバーエラー」に変わる |
| `frontend/src/pages/Register.tsx:117-122` | validate-slug の `status === 404` 分岐 | 404 契約は不変のため**影響なし** |
| `frontend/src/pages/Register.tsx:318-324` | 登録失敗時は AuthContext に委譲 | **影響なし** |
| `frontend/src/services/auth.service.ts:34-44` | logout 失敗時もローカルログアウト継続 | logout が 400→200 になるが FE 側は分岐不要（**変更なし**） |
| `frontend/src/pages/UserCreate.tsx` / `UserEdit.tsx` / `components/ErrorToast.tsx` | `main_message` 参照（管理者用画面） | accounts 登録 API とは別経路のため**影響なし** |

---

## 3. 受け入れ条件（イシューの AC に対応）
1. `backend/accounts/views.py` に広域 `except Exception` が意図的な 1 箇所（メール送信）以外残っていない → TC-DET-01
2. 想定内エラーの既存契約が不変（slug 指定組織不在 400・serializer 検証 400・validate-slug 404・logout のトークン欠落/無効 400） → TC-AUTO-05〜10・既存 I131 テスト
3. personal 組織不在は 400 でなく統一 JSON 500 で顕在化 → TC-AUTO-11〜12（I140 テスト更新）
4. 想定外例外が 500 として返り、`django.request` にスタックトレースが記録される → TC-AUTO-01〜02・04
5. `DEBUG=True` のときのみ 500 の `sub_message` に例外情報が含まれる → TC-AUTO-03
6. logout が有効トークンで 200 を返し、当該トークンが失効する → TC-AUTO-06
7. 既存テスト全 PASS（baseline 94） → TC-AUTO-14
8. 規約が明文化され、既存コード例が整合 → TC-DET-02
9. FE の登録・logout 導線が実動作で退行しない → 手動テスト

---

## 4. 影響範囲
- **Backend**: `accounts/views.py`（3 箇所の例外設計）・`core/exceptions.py`（分岐と例外クラスの追加）・`core/settings.py`（INSTALLED_APPS 1 行）・`accounts/tests/`（新規 1 ファイル・I140 テスト更新）
- **Frontend**: コード変更なし（調査7 のとおり全消費箇所で契約維持）
- **DB**: `token_blacklist` の追加テーブル 2 つ（`token_blacklist_outstandingtoken` / `token_blacklist_blacklistedtoken`）。既存テーブル・データの変更なし
- **Config/Infra**: デプロイ時に `manage.py migrate` が必要。ロギング設定・DRF 設定キーは不変更
- **ドキュメント**: `rules/ultimate_django_coding_standards.md`

---

## 5. 変更点一覧

### 対象 API と認可（すべて既存のまま変更しない）
| エンドポイント | メソッド | `permission_classes` | 正常系レスポンス |
|----------------|----------|----------------------|------------------|
| `/api/auth/register/` / `/api/auth/register/<organization_slug>/` | POST | `[permissions.AllowAny]` | 201 `{"message": str, "user_id": str, "organization": str}` |
| `/api/organizations/validate-slug/<slug>/` | GET | `[permissions.AllowAny]` | 200 `{"valid": true, "organization_name": str, "organization_id": int}` |
| `/api/auth/logout/` | POST | `[permissions.AllowAny]`（`@api_view` + `@permission_classes`） | 200 `{"message": "ログアウトしました。"}` |

エラー応答の形式は、統一 JSON（`{"error": {"main_message": str, "sub_message": str \| null, "details": obj}}`）と、validate-slug の 404 のみ既存の独自形式（`{"valid": false, "message": str}`）を維持する。

### 5-1. `backend/core/exceptions.py`（追加のみ・既存フォーマット維持）
**修正方針**: DRF が処理しない例外（＝プログラム欠陥）を握りつぶさずに顕在化させる受け皿を、全 API 共通の場所に 1 箇所だけ作る。加えて「環境構成の不備」を表す専用例外クラスを追加し、サーバー起因の異常をクライアント起因の 400 と取り違えないようにする。

```python
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback

logger = logging.getLogger('django.request')


class EnvironmentMisconfiguredError(APIException):
    """環境構成の不備（サーバー起因）。クライアント入力では回復できないため 500 を返す。

    例: 必須の既定組織（type='personal'）が存在しない等、マイグレーション/初期データの不備。
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'サーバー設定に問題があります'
    default_code = 'environment_misconfigured'


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        # DRF が処理しない例外＝想定外（プログラム欠陥）。
        # 握りつぶさずスタックトレースを記録し、統一 JSON の 500 で顕在化させる（I142）。
        view = context.get('view')
        logger.exception(
            "Unhandled exception in %s", view.__class__.__name__ if view else 'unknown view')
        set_rollback()  # ATOMIC_REQUESTS 有効時にトランザクションを確実にロールバックする
        return Response({
            'error': {
                'main_message': 'サーバーエラー',
                'sub_message': (f'{type(exc).__name__}: {exc}' if settings.DEBUG
                                else 'しばらく時間をおいて再度お試しください'),
                'details': {},
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 以降は既存ロジック（ValidationError / 404 / 403 / 401 / 429 / 500 の文言変換）を変更せず維持する。
    # ただし 5xx（APIException 由来）もスタックトレースを記録する（I142）。
    if response.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.exception("Server error response: %s", type(exc).__name__)

    ...（既存コードのまま）
```

### 5-2. `backend/core/settings.py`
**修正方針**: logout がトークンを実際に失効させられるよう、simplejwt の失効機能を有効化する。

```python
INSTALLED_APPS = [
    ...
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',  # logout での refresh トークン失効に必要（I142）
    ...
]
```

### 5-3. `backend/accounts/views.py`（登録ビュー）
**修正方針**: 全体を包む `try/except` を撤去し、想定内のケースだけを明示的な分岐で処理する。想定外は伝播させて 5-1 の受け皿に委ねる。

```python
    def create(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger('django')

        organization_slug = kwargs.get('organization_slug')
        logger.info(f"Registration attempt with slug: {organization_slug}")

        # 想定内: リクエスト形式が不正（クライアント起因）
        if not isinstance(request.data, dict):
            return Response({
                'error': {
                    'main_message': '入力内容にエラーがあります',
                    'sub_message': '不正なリクエスト形式です',
                    'details': {}
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # 想定内: slug 指定で組織が見つからない（クライアント起因）→ 既存 400 契約を維持
        # （slug なしで personal 組織が不在の場合は _get_organization が 500 を raise する）
        organization = self._get_organization(organization_slug)
        if not organization:
            return Response({
                'error': {
                    'main_message': '組織の設定に失敗しました',
                    'sub_message': '無効な組織URLまたはシステムエラー'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        mutable_data = request.data.copy()
        mutable_data['organization_id'] = organization.id

        logger.info(f"Registration attempt with data: {mutable_data}")

        with transaction.atomic():
            serializer = self.get_serializer(data=mutable_data)
            if not serializer.is_valid():
                ...（既存の 400 レスポンスのまま）

            user = serializer.save()
            ...
            try:
                self.send_verification_email(user)
                logger.info("Email verification sent")
            except Exception as email_error:
                # 意図的な狭域設計: メール送信の失敗では登録自体を失敗させない（I142 規約の例外・許容ケース）
                logger.error(f"Email sending failed: {str(email_error)}", exc_info=True)

            return Response({...}, status=status.HTTP_201_CREATED)
        # 想定外例外はここで捕捉せず伝播させる（custom_exception_handler がログ+500 に変換）
```
※ `logger.info(f"Registration attempt with data: {mutable_data}")` の平文パスワード出力は**本計画では変更しない**（別イシュー「I144」で対応・イシュー本文で除外済み）。

### 5-4. `backend/accounts/views.py`（`_get_organization`）
**修正方針**: 環境異常（既定組織が無い）をクライアント起因の 400 に混ぜず、専用例外で 500 に分類する。

```python
            if not personal:
                # personal 組織は migration 0014/0017/0018 で常に存在する前提。
                # 不在は環境異常（サーバー起因）のため 400 ではなく 500 で顕在化させる（I142）
                logger.error(
                    "Personal organization (type='personal', is_active=True) not found. "
                    "Environment is misconfigured; slug-less registration rejected."
                )
                raise EnvironmentMisconfiguredError()
```
（`from core.exceptions import EnvironmentMisconfiguredError` を追加）

### 5-5. `backend/accounts/views.py`（validate-slug）
**修正方針**: 想定内例外が存在しない処理なので `try/except` ごと撤去する。

```python
    def get(self, request, slug):
        import logging
        logger = logging.getLogger('django')
        logger.info(f"Organization slug validation request: {slug}")

        organization = Organization.objects.filter(slug=slug, is_active=True).first()

        if organization:
            logger.info(f"Valid organization found: {organization.name}")
            return Response({...})   # 既存 200 body のまま

        logger.warning(f"No active organization found for slug: {slug}")
        return Response({...}, status=status.HTTP_404_NOT_FOUND)  # 既存 404 body のまま
        # 想定外例外は伝播（custom_exception_handler が統一 JSON 500 に変換）
```

### 5-6. `backend/accounts/views.py`（logout）
**修正方針**: 「入っているべき値が無い」は例外ではなく分岐で判定し、例外捕捉はトークン不正だけに限定する。

```python
from rest_framework_simplejwt.exceptions import TokenError  # 追加 import


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@ratelimit(key='ip', rate='5/5m', method='POST')
def logout_view(request):
    # 想定内: refresh 欠落・不正なリクエスト形式（クライアント起因）
    refresh_token = request.data.get('refresh') if isinstance(request.data, dict) else None
    if not refresh_token:
        return Response({'error': 'ログアウトに失敗しました。'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        RefreshToken(refresh_token).blacklist()
    except TokenError:
        # 想定内: 無効・失効・既にブラックリスト済みのトークン（クライアント起因）
        return Response({'error': 'ログアウトに失敗しました。'}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'message': 'ログアウトしました。'})
    # 想定外例外は伝播（custom_exception_handler がログ+500 に変換）
```

### 5-7. `backend/accounts/tests/test_I142_error_handling.py`（新規）
TC-AUTO-01〜10 を実装する（詳細な期待値は `docs/tests/open/I142_auto_test.md`）。想定外例外の注入は `unittest.mock.patch.object(Organization.objects, 'filter', side_effect=RuntimeError(...))`、ログ検証は `django.request` への専用 `logging.Handler` 装着（調査3 の実証方式）。

### 5-8. `backend/accounts/tests/test_I140_personal_org_fallback.py`（期待値更新）
`EXPECTED_400_BODY` を統一 JSON 500 の期待値に置き換え、TC-AUTO-01/04 相当の 2 関数を 500 期待へ更新する（関数名も `..._returns_500` に改名）。組織非作成（TC-AUTO-02）・error ログ（TC-AUTO-03）の検証は維持。

### 5-9. `rules/ultimate_django_coding_standards.md`
セクション 5「API設計（DRF）」に `### エラーハンドリング方針（例外設計）` を新設し、以下を明文化する。
- 想定内の失敗（クライアント起因）は**種別ごとに個別捕捉**し、適切な 4xx と既存レスポンス形式で返す
- 想定外の例外（プログラム欠陥）は**捕捉しない**。`EXCEPTION_HANDLER` に委ね、スタックトレース記録 + 5xx で顕在化させる
- **広域 `except Exception` は禁止**。例外的に許容するのは「失敗しても処理継続が業務上正しい副作用」（メール送信等）と「ログ後に必ず `raise` する」ケースのみで、その場合は意図をコメントで明記する
- 環境構成の不備は `core.exceptions.EnvironmentMisconfiguredError`（500）で表現する
あわせて既存コード例 :689 を規約準拠へ修正、:1223 / :1403 に許容理由のコメントを追加する（調査6）。

---

## 6. 実装手順

**ステップ間の依存**: ステップ1 → 2 → 3 は順に依存（1 の受け皿が無いと 2 の伝播が Django 標準 500 になる／2 の実装が無いと 3 のテストが失敗する）。ステップ4（規約文書）はステップ1〜3 と独立で並行実施可能。

### ステップ1: 想定外例外の受け皿を用意する（未知リスク先行）
1. `backend/core/exceptions.py` に `EnvironmentMisconfiguredError` と非 APIException 分岐を追加（5-1）
2. `backend/core/settings.py` の INSTALLED_APPS に `rest_framework_simplejwt.token_blacklist` を追加（5-2）
3. `docker compose exec backend python manage.py migrate` を実行し、`token_blacklist` のテーブルを作成する
→ 検証は TC-AUTO-01・TC-DET-03 参照

### ステップ2: accounts の 3 ビューを再設計する
1. 登録ビュー `create` の広域 try/except 撤去と非 dict body の明示分岐（5-3）
2. `_get_organization` の personal 不在を `EnvironmentMisconfiguredError` に変更（5-4）
3. validate-slug の try/except 撤去（5-5）
4. logout の明示分岐化と `TokenError` 限定捕捉（5-6）
→ 検証は TC-AUTO-01〜10・TC-DET-01 参照

### ステップ3: 回帰テストを追加・更新する
1. `backend/accounts/tests/test_I142_error_handling.py` を新規作成（5-7）
2. `backend/accounts/tests/test_I140_personal_org_fallback.py` の期待値を 500 へ更新（5-8）
→ 検証は TC-AUTO-01〜14 参照

### ステップ4: 規約を明文化する（ステップ1〜3 と並行可）
1. `rules/ultimate_django_coding_standards.md` に `### エラーハンドリング方針（例外設計）` を追加（5-9）
2. 既存コード例 :689 の修正、:1223 / :1403 への意図コメント追加
→ 検証は TC-DET-02 参照

### ステップ5: 全体回帰と手動確認
1. バックエンド全体テスト・決定論チェックの実行（TC-AUTO-14・TC-DET-01〜03）
2. 手動テスト（`docs/tests/open/I142_manual_test.md`）の実施
※ backend のコード変更後は `docker compose restart backend` が必要（settings 変更を反映するため）

---

## 7. テスト計画

### テストレベルの選択
| レベル | 対象 | 理由 |
|--------|------|------|
| ユニット/結合（pytest + APIClient） | 例外種別ごとのステータス・body・ログ | エラー応答契約は body 完全一致で固定するのが最も安価かつ確実 |
| 決定論チェック（grep・exit code） | 広域 except の不在・規約節の存在・settings の登録 | 「不在」「無改変」はテスト関数より grep のほうが直接的 |
| E2E（Playwright・既存 7 件） | 登録・ログイン・ログアウト導線 | 実ブラウザでの退行検知（新規追加はしない） |
| 手動 | FE の表示文言・ログアウト後の再ログイン | 画面表示は自動化対象外 |

- **再発防止テスト**: TC-AUTO-01〜04（想定外例外の 500 化・ログ記録）が I131 型の潜伏バグの再発防止に対応
- **認可テスト**: 本変更は認証・認可のルールを変更しないため新規追加なし（登録・validate-slug は `AllowAny`、logout も `AllowAny` のまま）
- 詳細は `docs/tests/open/I142_auto_test.md` / `docs/tests/open/I142_manual_test.md`

---

## 8. ロールバック
1. コードは PR 単位で revert（`git revert`）
2. `token_blacklist` は INSTALLED_APPS から 1 行削除すれば無効化できる（テーブルは残置して無害。完全に戻す場合は `manage.py migrate token_blacklist zero`）
3. DB のデータ変更は行わないため、データ復旧作業は不要

---

## 9. Risk & 回避策
| リスク | 影響 | 回避策 |
|--------|------|--------|
| 想定外例外の 500 化で、これまで 400 として黙って処理されていた経路がエラーとして表面化する | 監視上のエラー増加 | それが本イシューの目的。既存テスト（94 件）＋新規 TC で正常系・想定内 4xx の不変を確認する |
| `token_blacklist` 有効化で migrate 忘れ | logout が 500（テーブル不在） | 実装ステップ1 に migrate を組み込み、TC-AUTO-06 で 200 を固定。デプロイ手順にも migrate 必要を明記 |
| `DEBUG=True` の本番運用時に例外詳細が応答へ出る | 情報漏洩 | 既存実装（`views.py:126`）と同じ条件付き。`DEBUG=False` での非露出を TC-AUTO-01 で固定 |
| `set_rollback()` 追加による副作用 | 既存トランザクション挙動の変化 | `ATOMIC_REQUESTS` は未設定（デフォルト False）のため実質 no-op。登録ビューは明示的 `transaction.atomic()` で従来どおりロールバックする |
| ログ出力の増加（5xx ごとにスタックトレース） | ログ量増 | 5xx のみが対象で、通常運用では稀。`error_file` は TimedRotatingFileHandler でローテーション済み |

---

## 10. データ整合性設計（DB 変更があるため記載）
- **追加テーブル**: `token_blacklist_outstandingtoken`（発行済み refresh トークン）・`token_blacklist_blacklistedtoken`（失効済み）。simplejwt 同梱のマイグレーションをそのまま適用する（自作マイグレーションなし）
- **制約**: simplejwt 既定（`OutstandingToken.jti` は unique、`BlacklistedToken.token` は OneToOne + `on_delete=CASCADE`、`user` は `on_delete=CASCADE`）。既存テーブルへの FK 追加・カラム変更はなし
- **後方互換性**: 追加のみ。旧コード（blacklist を呼ばない状態）でもテーブルが存在するだけで無害
- **冪等性・同時更新**: 同一トークンで logout を 2 回叩いた場合、2 回目は `TokenError`（ブラックリスト済み）で 400 を返す（TC-AUTO-06 で固定）
- **マイグレーション安全性**: 追加テーブルのみでロック時間は無視できる。ロールバックは `migrate token_blacklist zero` で可能
- **運用上の注記**: 失効済みトークンは自動削除されない（`flushexpiredtokens` の定期実行は本イシューのスコープ外・イシュー本文に明記済み）

---

## 11. 運用設計（ログ・可観測性の変更があるため記載）
- **構造化ログ方針**: 既存 `ErrorContextMiddleware`（`core/enhanced_logging.py:111-`）が `request_id` / `user_id` / パス等を付けて 4xx・5xx を `django.request` に記録する。本変更で追加するのは**スタックトレース付きの例外ログ**（`logger.exception`）で、出力先は既存の `error_file` ハンドラ（ローテーション済み）
- **タイムアウト・リトライ**: 外部 API 呼び出しの追加はないため該当なし
- **Feature Flag・段階リリース**: 変更は 1 アプリ内の例外設計に閉じ、切り戻しは revert で完結するため不要

---

## 12. コスト・保守見積もり
新規インフラ・外部サービスの追加はなし。DB はテーブル 2 つの追加のみでコスト増は無視できる。保守面では「広域 except 禁止」の規約が rules に入ることでレビュー観点が明文化され、属人化リスクはむしろ下がる。→ **P8 影響は軽微**

---

## 13. 性能・UX設計
フロントエンドのコード変更なし。表示が変わるのは異常時のトースト文言のみ（「エラーが発生しました」「組織の設定に失敗しました」→「サーバーエラー」）で、ローディング・空状態・破壊的操作の導線に変更はない。N+1・ページネーション・キャッシュへの影響もなし。→ **P6 影響なし（表示文言の変化のみ）**

---

## 14. プライバシー・コンプライアンス
本変更は個人情報の新規収集・保存・越境を伴わない。`DEBUG=False` では例外詳細を応答に出さないため、エラー応答経由の情報漏洩も増えない。既存の平文パスワードログ出力は別イシュー（I144）で対応する。→ **P9 影響なし**

---

## 15. 承認ポイント（後述の会話で提示）
- 実装対象ファイルと変更内容（5-1〜5-9）
- 設計判断の出所（イシュー明記／計画時に確定）
- テスト計画（TC-AUTO-01〜14・TC-DET-01〜03・手動 5 件）
