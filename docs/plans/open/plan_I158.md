## 基本情報
- **計画書ID**: plan_I158
- **関連イシュー**: #275
- **Draft PR**: #317
- **作成根拠資料**: docs/issues/open/I158.md（起点イシュー・grill-me 2 回実施済み）
- **実装後評価**: docs/reviews/open/I158_review.md
- **作成日**: 2026-10-24

---

## 1. 背景/目的

クイズを 1 回開始すると QuizSession が 2 件作られ、両方が有効（`is_active=True`）のまま残る不具合を、フロント・サーバーの両方で根治する。

- **原因の概要**: 画面が開始リクエストを 2 回送ってしまう（開発モードの React の仕様で開始処理が 2 回動く）うえに、サーバー側にも「同時に 2 回来ても有効なセッションは 1 件だけ」という守りが無い。
- **詳細な原因分析**:
  1. `frontend/src/index.tsx:11` で `<React.StrictMode>` が有効。開発ビルドでは effect が mount→unmount→mount で 2 回実行される。
  2. `frontend/src/pages/QuizSession.tsx:203-211` の `useEffect` は `id` が無いと `createNewSession()` を呼ぶ。重複防止が無いため `POST /api/quiz/` がほぼ同時に 2 回送られる。
  3. `backend/problems/views.py:820-845` の `QuizSessionViewSet.create` は「既存の有効セッションを `update(is_active=False)` → 新規作成」をトランザクション・ロック無しで行う。2 リクエストの `update` がどちらも相手の新規行より先に走るため、新規行が 2 件とも有効のまま残る。
  4. DB にも「1 ユーザー 1 有効セッション」の制約が無いため、誤りがそのまま保存される。
  5. 本番ビルドでは StrictMode の二重実行は起きないが、ダブルクリック・ネットワーク再送・401 時の自動再送（`frontend/src/services/api.ts:82-113` は同じリクエストを再送する）・複数タブでも同じ競合が起き得る。
- **根本原因（コードレベル）**: 開始処理が「冪等でない書き込み」を「重複防止の無い effect」から呼んでおり、サーバー側も不変条件をアプリの手順（update → create）だけに頼っていて、直列化と DB 制約で保証していない。

**解決方針（grill-me で確定・2026-10-24）**:
- サーバー: `transaction.atomic` ＋ ユーザー行の `select_for_update` で同一ユーザーの開始処理を直列化し、DB の条件付き UniqueConstraint を最後の守りにする。重複送信は `Idempotency-Key` ヘッダ（UUID）で判定し、同じキーなら作成済みのセッションを 200 で返す。
- API の締め: 未使用の PUT/PATCH/DELETE を閉じ、`is_active` を読み取り専用にする。
- フロント: `useRef` ガードで開始リクエストを 1 回に限定し、UUID を `Idempotency-Key` として送る。
- 既存の重複有効セッションはデータマイグレーションで「最新以外」を終了扱いにする。

## 調査結果

### 環境前提確認（2026-10-24 実施）
- `docker compose ps` → backend（healthy）/ db（healthy）/ redis / celery / celery-beat 稼働中。frontend コンテナは停止中（手動テスト No.4 の E2E 実行時に `docker compose up -d frontend` で起動する）。
- DB は PostgreSQL（`backend/core/settings.py:89`・CI も `postgres:15-alpine`）。条件付き UniqueConstraint（部分ユニークインデックス）と `select_for_update` をそのまま使える。
- Frontend: react-scripts 5.0.1（Jest 27.5.1・jsdom 16.7.0）・TypeScript 4.9.5（`lib.dom` に `crypto.randomUUID` の型あり）。
- E2E: `.github/workflows/e2e.yml` は `docker compose up -d db backend frontend`（`frontend/Dockerfile.dev` = 開発サーバー）に対して Playwright を実行する。**開発ビルドのため StrictMode が有効**で、二重送信を実ブラウザで再現・検証できる。フロントは同一オリジン（`REACT_APP_API_BASE_URL=` 空・開発サーバーのプロキシ経由）のため、E2E では CORS は通らない（CORS は backend テストで検証する）。
- ローカルの E2E 用パスワードは `e2e/.env.e2e` に存在（Claude が E2E を実行できる）。

### 既存テストの事前実行（baseline・2026-10-24）
- Backend: `docker compose exec -T backend python -m pytest --tb=short -q` → **103 passed**。
- Frontend: `CI=true npx react-scripts test --watchAll=false` → **3 suites / 10 passed**。
- `docker compose exec -T backend python manage.py makemigrations --check --dry-run` → `No changes detected`（exit 0・モデルとマイグレーションが一致）。

### 既存データ（dev DB・読み取りのみ・2026-10-24）
- 有効セッション 10 件。有効が 2 件以上のユーザー 5 人・解消対象（最新以外）5 件。

### コード読解による確定事項
- `QuizSessionViewSet`（`backend/problems/views.py:808-974`）は `ModelViewSet`。`get_queryset` は `QuizSession.objects.filter(user=self.request.user)`（本人のセッションのみ）・`permission_classes = [permissions.IsAuthenticated]`。
- `QuizSessionSerializer`（`backend/problems/serializers.py:306-334`）の `read_only_fields` に `is_active` が無く、PUT/PATCH で書き換えられる。`started_at` は `auto_now_add`（`editable=False`）のため DRF が自動で読み取り専用にするが、明示する。
- 画面からの `/api/quiz/` 呼び出しは `POST /api/quiz/`・`GET /api/quiz/<id>/`・`GET .../next_problem/`・`POST .../submit_answer/`・`POST .../end/` のみ。PUT/PATCH/DELETE は `frontend/src`・`backend/problems/tests/`・`e2e/tests` のどこからも使われていない（grep 済み）。
- エラー応答の統一ヘルパー `core.exceptions.create_error_response(main_message, sub_message, status_code)`（`backend/core/exceptions.py:74-84`）が存在し、`{"error": {"main_message", "sub_message", "details": {}}}` を返す。`custom_exception_handler` と同じ形。
- 業務ロジックの置き場所として `backend/problems/services/quiz_service.py` の `QuizService` が既にある（`get_next_problem` 等）。
- CORS は `CORS_ALLOW_HEADERS` の明示列挙（`backend/core/settings.py:193-205`）。`idempotency-key` を足さないと別オリジン構成で preflight が通らない。
- テスト DB は `--no-migrations`（`backend/pytest.ini`）。制約はモデルの `Meta.constraints` から作られるため、通常のテストでも有効。マイグレーション自体の検証は `--migrations --create-db` で別途行う（TC-21）。
- フロントの既存テスト `frontend/src/pages/__tests__/QuizSession.test.tsx` はファイル先頭で `useParams` を `{ id: 'test-session-id' }` に固定している（既存セッション読み込み経路専用）。開始経路（`id` 無し）のテストは別ファイルにする。
- jsdom 16 には `crypto`（Web Crypto）が無い。テストで `crypto.randomUUID` を使うには `setupTests.ts` で Node の `crypto.webcrypto` を補う必要がある。

### 適用規約（rules/ 抽出）
- Django: 業務ロジック・トランザクション境界はサービス層（`ultimate_django_coding_standards.md` §6「サービス（書き込み・業務ロジック）」・§14「トランザクション境界: サービス層で明確化」）。Fat View にしない。テストは pytest・fixture・`rest_framework.status` 定数で assert。
- React: effect の重複実行に耐える書き方（StrictMode 前提）・`react-hooks/exhaustive-deps` 準拠・ハードコードした文字列定数は名前付き定数にする。

## 2. 受け入れ条件（Acceptance Criteria）
イシューの AC そのまま（具体値はテスト文書で固定）:
- [ ] dev 環境（StrictMode 有効）でクイズを 1 回開始したとき、`POST /api/quiz/` が 1 回だけ送られ、QuizSession が 1 件だけ作成される（TC-30・TC-40）
- [ ] 同一ユーザーが `POST /api/quiz/` を同時に 2 回送っても、有効な QuizSession は 1 件だけになる（TC-07・TC-08）
- [ ] 同じ `Idempotency-Key` で再送すると新規作成されず既存セッションが 200 で返る（異なるキーなら既存を終了して新規作成・201。UUID でないキーは 400、同じキーで `subject` が異なる再送は 422）（TC-03・TC-04・TC-05・TC-06）
- [ ] DB 制約により、1 ユーザーに有効セッションが 2 件以上存在できない（制約違反時は 500 ではなく 409）（TC-09・TC-10）
- [ ] `/api/quiz/<id>/` への PUT/PATCH/DELETE は 405 になり、`is_active` をクライアントから書き換えられない（TC-11・TC-12）
- [ ] 既存データの重複有効セッションがマイグレーションで解消され、マイグレーションがまっさらな DB と既存 dev DB の両方で通る（TC-14・TC-21・手動 No.1〜3）
- [ ] 既存のクイズ機能（出題・回答・中断・再開・完了）が退行しない（既存テスト・E2E 全件 pass）（TC-22・TC-33・TC-41）

## 3. 影響範囲
- **Backend**: `problems/models.py`（QuizSession）・`problems/services/quiz_service.py`（開始処理を追加）・`problems/views.py`（`QuizSessionViewSet`）・`problems/serializers.py`（`QuizSessionSerializer`）・`core/settings.py`（CORS 許可ヘッダ）
- **Frontend**: `pages/QuizSession.tsx`（開始処理）・`setupTests.ts`（テスト環境の Web Crypto 補完）
- **DB**: QuizSession に `client_request_id`（UUID・null 可）列、部分ユニーク制約 2 つを追加。既存の重複有効セッション（dev で 5 件）を `is_active=False`・`ended_at` 設定に更新（Danger Ops・削除なし）
- **API 契約**: `POST /api/quiz/` に任意ヘッダ `Idempotency-Key` を追加・応答に 200（既存返却）/400/409/422 が増える。`/api/quiz/<id>/` の PUT/PATCH/DELETE が 405 になる（画面・テストからの利用なし）
- **Config/Infra**: CORS 許可ヘッダに `idempotency-key` を追加。依存関係ファイルの変更なし → Dockerfile / compose への波及なし
- **Docs**: なし（I166 への引き継ぎ追記は grill-me 時に実施済み）

## 4. 変更点一覧

| ファイル | 対象 | 変更内容 |
|---------|------|---------|
| `backend/problems/models.py` | `QuizSession`（198〜212 行目） | `client_request_id = UUIDField(null=True, blank=True)` を追加。`Meta.constraints` に部分ユニーク制約 2 つを追加 |
| `backend/problems/migrations/0019_quizsession_client_request_id.py`（新規） | — | `AddField`（`client_request_id`） |
| `backend/problems/migrations/0020_deactivate_duplicate_active_quizsessions.py`（新規） | — | `RunPython(deactivate_duplicate_active_sessions, RunPython.noop)`（データマイグレーション） |
| `backend/problems/migrations/0021_quizsession_constraints.py`（新規） | — | `AddConstraint` × 2 |
| `backend/problems/services/quiz_service.py` | `QuizService` | `start_session()`・例外クラス `IdempotencyKeyReusedError`・`ActiveSessionConflictError` を追加 |
| `backend/problems/views.py` | `QuizSessionViewSet`（808 行目〜）・`create`（820〜845 行目）・`submit_answer`（942 行目）・`end`（969〜971 行目） | `http_method_names` の限定。`create` は `Idempotency-Key` の解析・入力検証・サービス呼び出し・例外→HTTP 応答の対応付けのみにする。`submit_answer`・`end` の `session.save()` を `update_fields` 指定にする（修正項目 8・security-review 由来） |
| `backend/problems/serializers.py` | `QuizSessionSerializer.Meta.read_only_fields`（320〜323 行目） | `is_active`・`started_at` を追加 |
| `backend/core/settings.py` | `CORS_ALLOW_HEADERS`（193〜205 行目） | `'idempotency-key'` を追加 |
| `frontend/src/pages/QuizSession.tsx` | `createNewSession`（108〜130 行目）・開始 effect（203〜211 行目）・完了画面の「もう一度挑戦」ボタン（計画変更 2） | `useRef` ガード・`Idempotency-Key` ヘッダの送信 |
| `frontend/src/pages/__tests__/QuizSession.test.tsx` | — | TC-34（「もう一度挑戦」からの開始にキーが付く・計画変更 2） |
| `frontend/src/setupTests.ts` | — | `crypto.randomUUID` が無い Jest 環境で Node の `crypto.webcrypto` を割り当てる |
| `backend/problems/tests/test_I158_quiz_session_start.py`（新規） | — | TC-01〜TC-18 |
| `frontend/src/pages/__tests__/QuizSession.start.test.tsx`（新規） | — | TC-30・TC-31 |
| `e2e/tests/quiz-session.spec.ts` | — | TC-40（開始時の POST 回数とヘッダ）を追加 |

### 修正アプローチ
開始処理を「何度届いても結果が 1 つに定まる」形にする。画面はそもそも 1 回しか送らない（`useRef` ガード）。それでも届く再送（401 後の自動再送・ネットワーク再送）は同じキーなので、サーバーが作成済みのセッションを返す。キーの違う開始（別タブ・意図的なやり直し）は従来どおり後勝ちだが、同一ユーザー内で順番に処理されるため、有効なセッションは常に 1 件に収まる。最後に DB 制約が、どんな経路でも 2 件目の有効セッションを拒否する。

### 修正項目 1: モデルと DB 制約
**修正方針**: 「1 ユーザー 1 有効セッション」と「1 ユーザー内でキーは一意」を DB に持たせる。部分ユニーク制約にすることで、終了済みセッションやキー無しの行は制約の対象外になる。

```python
class QuizSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_sessions')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
    total_problems = models.IntegerField(default=0)
    completed_problems = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    # 開始リクエストの重複判定用（Idempotency-Key ヘッダの値）
    client_request_id = models.UUIDField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(is_active=True),
                name='uniq_active_quizsession_per_user',
            ),
            models.UniqueConstraint(
                fields=['user', 'client_request_id'],
                condition=models.Q(client_request_id__isnull=False),
                name='uniq_quizsession_user_request_id',
            ),
        ]
```
- `client_request_id`: `UUIDField`・`null=True`・`blank=True`・default なし（キー無しの開始と既存行は NULL）。
- 2 つ目の制約の `condition` は、PostgreSQL では NULL 同士が重複扱いにならないため意味は変わらないが、「キーがある行だけが対象」を明示し、部分インデックスとして小さく保つために付ける。

### 修正項目 2: マイグレーション（3 本に分ける）
**修正方針**: 列追加（スキーマ）→ 重複解消（データ）→ 制約追加（スキーマ）の順に、1 本ずつ別トランザクションで流す。PostgreSQL で同じトランザクション内に行の更新と `ALTER TABLE` を混ぜると「pending trigger events」エラーになり得るため、データ更新と制約追加を分ける。

`0020_deactivate_duplicate_active_quizsessions.py`:
```python
from django.db import migrations
from django.utils import timezone


def deactivate_duplicate_active_sessions(apps, schema_editor):
    """同一ユーザーの有効セッションが複数ある場合、最新（started_at・id の降順で先頭）以外を終了扱いにする。
    削除はしない（回答データは残る）。"""
    QuizSession = apps.get_model('problems', 'QuizSession')
    now = timezone.now()
    seen_users = set()
    for session in QuizSession.objects.filter(is_active=True).order_by('user_id', '-started_at', '-id'):
        if session.user_id in seen_users:
            session.is_active = False
            session.ended_at = session.ended_at or now
            session.save(update_fields=['is_active', 'ended_at'])
        else:
            seen_users.add(session.user_id)


class Migration(migrations.Migration):
    dependencies = [('problems', '0019_quizsession_client_request_id')]
    operations = [
        migrations.RunPython(deactivate_duplicate_active_sessions, migrations.RunPython.noop),
    ]
```
- 対象は有効セッションのみ（dev で 10 件）を 1 件ずつ更新するため、件数・性能の懸念は無い。
- `0019`（`AddField`）と `0021`（`AddConstraint` × 2）は `makemigrations` の生成物をそのまま使い、`0021` の依存を `0020` にする。

### 修正項目 3: サービス層 `QuizService.start_session`
**修正方針**: 開始処理の業務ロジックとトランザクション境界をサービスに置く（ビューを薄くする）。ユーザー行のロックで同一ユーザーの開始を直列化し、ロック取得後にキーの照合 → 既存有効セッションの終了 → 新規作成を行う。`IntegrityError`（直列化をすり抜けた場合の最後の守り）は業務例外に変換する。

```python
import uuid
from typing import Optional, Tuple

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from problems.models import Problem, QuizSession, Subject


class IdempotencyKeyReusedError(Exception):
    """同じ Idempotency-Key が別の内容（科目）で再利用された"""


class ActiveSessionConflictError(Exception):
    """有効セッションの一意制約に違反した（直列化をすり抜けた同時開始）"""


class QuizService:
    ...

    @staticmethod
    def start_session(
        *,
        user,
        subject: Optional[Subject],
        client_request_id: Optional[uuid.UUID],
    ) -> Tuple[QuizSession, bool]:
        """
        クイズセッションを開始する

        同一ユーザーの開始処理はユーザー行のロックで直列化する。
        同じ client_request_id の再送には作成済みのセッションを返す（冪等）。

        Returns:
            (セッション, 新規作成したかどうか)
        """
        try:
            with transaction.atomic():
                get_user_model().objects.select_for_update().only('pk').get(pk=user.pk)

                if client_request_id is not None:
                    existing = QuizSession.objects.filter(
                        user=user, client_request_id=client_request_id
                    ).first()
                    if existing is not None:
                        if existing.subject_id != (subject.pk if subject else None):
                            raise IdempotencyKeyReusedError()
                        return existing, False

                QuizSession.objects.filter(user=user, is_active=True).update(
                    is_active=False, ended_at=timezone.now()
                )

                problems_queryset = Problem.objects.filter(is_deleted=False)
                if subject is not None:
                    problems_queryset = problems_queryset.filter(subject=subject)

                session = QuizSession.objects.create(
                    user=user,
                    subject=subject,
                    client_request_id=client_request_id,
                    total_problems=problems_queryset.count(),
                )
                return session, True
        except IntegrityError as exc:
            raise ActiveSessionConflictError() from exc
```
- `total_problems` の数え方（科目未指定時に全組織を数える件）は現行のまま移すだけで変えない（I166 で是正・I166 本文に引き継ぎ済み）。
- 同じキーのセッションが終了済みでも、そのまま返す（新規作成しない）。

### 修正項目 4: ビュー `QuizSessionViewSet`
**修正方針**: ビューは「ヘッダの解析・入力検証・サービス呼び出し・例外を HTTP 応答に対応付ける」だけにする。未使用の書き換え・削除を閉じる。

```python
import uuid

from core.exceptions import create_error_response
from problems.services.quiz_service import (
    ActiveSessionConflictError,
    IdempotencyKeyReusedError,
    QuizService,
)

IDEMPOTENCY_KEY_HEADER = 'Idempotency-Key'


class QuizSessionViewSet(viewsets.ModelViewSet):
    serializer_class = QuizSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    # セッションの書き換え・削除は API として提供しない（終了は end アクションのみ）
    http_method_names = ['get', 'post', 'head', 'options']

    ...

    def create(self, request):
        raw_key = request.headers.get(IDEMPOTENCY_KEY_HEADER)
        try:
            client_request_id = uuid.UUID(raw_key) if raw_key is not None else None
        except ValueError:
            return create_error_response(
                '入力内容にエラーがあります',
                'Idempotency-Key は UUID 形式で指定してください',
                status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            session, created = QuizService.start_session(
                user=request.user,
                subject=serializer.validated_data.get('subject'),
                client_request_id=client_request_id,
            )
        except IdempotencyKeyReusedError:
            return create_error_response(
                'Idempotency-Key が別の内容で使用されています',
                '新しいキーで再度お試しください',
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except ActiveSessionConflictError:
            return create_error_response(
                'クイズの開始が競合しました',
                'しばらくしてから再度お試しください',
                status.HTTP_409_CONFLICT,
            )

        return Response(
            self.get_serializer(session).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
```
- 空文字の `Idempotency-Key` は `uuid.UUID('')` が `ValueError` になるため 400（「送ったが壊れている」を「送っていない」と区別する）。
- `permission_classes` は `[permissions.IsAuthenticated]` のまま（変更なし）。対象は `get_queryset` により本人のセッションのみ。

**API 仕様（変更後）**

| URL | メソッド | 認可 | 応答 |
|-----|---------|------|------|
| `/api/quiz/` | POST（任意ヘッダ `Idempotency-Key: <UUID>`・body `{"subject": <科目ID> \| 省略}`） | `IsAuthenticated` | 201: 新規作成 `QuizSessionSerializer`／200: 同じキーの既存セッション `QuizSessionSerializer`／400: キーが UUID でない・`subject` 不正（`{"error": {"main_message", "sub_message", "details"}}`）／401: 未認証／409: 有効セッションの制約違反／422: 同じキーで `subject` が異なる |
| `/api/quiz/<id>/` | PUT / PATCH / DELETE | — | 405（`custom_exception_handler` の形 `{"error": {"main_message": "エラーが発生しました", ...}}`） |
| `/api/quiz/`・`/api/quiz/<id>/`・`next_problem`・`submit_answer`・`end` | GET / POST（従来どおり） | `IsAuthenticated` | 変更なし |

`QuizSessionSerializer` の応答フィールドは変更なし（`client_request_id` は応答に含めない）。

### 修正項目 5: シリアライザ
**修正方針**: `is_active` をクライアントから書き換えられないようにする（405 化と二重の守り）。`client_request_id` は応答に含めない。`QuizSessionSerializer.Meta.fields` は明示リスト（`serializers.py:315-319`・`'__all__'` ではない）のため、`fields` に足さないことで応答・入力のどちらにも出ない（`QuizSessionDetailSerializer` も同じ `fields` を継承）。TC-01 で応答に `client_request_id` が無いことを固定する。
```python
        read_only_fields = [
            'total_problems', 'completed_problems', 'correct_answers',
            'started_at', 'ended_at', 'is_active',
        ]
```

### 修正項目 6: CORS
**修正方針**: 別オリジン構成（`REACT_APP_API_BASE_URL` を設定した場合）でも preflight が通るようにする。`CORS_ALLOW_HEADERS` の末尾に `'idempotency-key',  # クイズ開始の重複送信防止（I158）` を追加する。

### 修正項目 7: フロントの開始処理
**修正方針**: 開始は「同じ科目に対して 1 回だけ」送る。記録は `useRef` に持つ（StrictMode の effect 再実行でも保持される）。キーはブラウザ標準の `crypto.randomUUID()` で作る。使えない環境（非 HTTPS・古いブラウザ）ではヘッダを付けずに送る（サーバーは後勝ちで受け付ける・`useRef` ガードは効く）。

```ts
const IDEMPOTENCY_KEY_HEADER = 'Idempotency-Key';

// crypto.randomUUID は安全なコンテキスト（HTTPS・localhost）でのみ使える
const generateIdempotencyKey = (): string | undefined =>
  typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : undefined;

...
  // 開始リクエストを科目ごとに 1 回へ限定する（StrictMode の effect 再実行でも送らない）
  const startedSubjectRef = useRef<string | null | undefined>(undefined);

  const createNewSession = useCallback(async (idempotencyKey: string | undefined) => {
    try {
      setLoading(true);
      const sessionData: any = {};

      if (subjectId) {
        sessionData.subject = subjectId;
      }
      // problem_count パラメータは送信しない（バックエンドが全問題数を設定）

      const response = await apiClient.post(
        '/api/quiz/',
        sessionData,
        idempotencyKey ? { headers: { [IDEMPOTENCY_KEY_HEADER]: idempotencyKey } } : undefined
      );
      ...（以降は現行どおり）
  }, [subjectId, navigate, loadNextProblem]);

  useEffect(() => {
    if (id) {
      // 既存のセッションを取得
      loadSession(id);
      return;
    }
    if (startedSubjectRef.current === subjectId) {
      return;
    }
    startedSubjectRef.current = subjectId;
    // 新しいセッションを作成
    createNewSession(generateIdempotencyKey());
  }, [id, subjectId, loadSession, createNewSession]);
```
- `startedSubjectRef` の初期値 `undefined` は「まだ開始していない」。`subjectId` は `string | null` のため、科目なし（`null`）の開始も 1 回に限定できる。
- エラー時の挙動は現行どおり（`toast.error('クイズセッションの作成に失敗しました')`＋`navigate('/dashboard')`）。400/409/422 も同じ扱い。

`frontend/src/setupTests.ts` に追加:
```ts
import { webcrypto } from 'crypto';

// jsdom 16（react-scripts 5 の Jest 環境）には Web Crypto が無いため Node の実装で補う
if (typeof globalThis.crypto?.randomUUID !== 'function') {
  Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true });
}
```

### 修正項目 8: 回答送信・終了の保存を必要な列だけにする（security-review 由来・2026-10-24 追加）
**修正方針**: `submit_answer` と `end` は、読み込んだセッションを `session.save()`（全列の上書き）で保存している。別タブでの開始がその間に割り込んで同じセッションを終了させると、回答送信の保存が `is_active=True` を書き戻す。これまでは「有効セッションが 2 件」に黙って戻っていたが、制約を足した後は `IntegrityError` で回答送信が 500 になる。保存する列を明示して、開始処理が終了させた状態を書き戻さないようにする。

```python
        # submit_answer（942 行目）
        session.save(update_fields=['completed_problems', 'correct_answers'])

        # end（969〜971 行目）
        session.is_active = False
        session.ended_at = timezone.now()
        session.save(update_fields=['is_active', 'ended_at'])
```
- `completed_problems += 1` の同時更新での取りこぼし（2 タブで同時に回答）は以前からある別問題で、本イシューでは扱わない（`F()` 式化は対象外）。
- `QuizSessionViewSet` 内に全列保存の `session.save()` が残っていないことを TC-19 で決定論的に固定する。

## 5. 実装手順（TDD・垂直スライス）

- **ステップ1: サーバーの不変条件（未知リスク先行・DB → サービス → API を 1 本で貫通）**
  1. `backend/problems/tests/test_I158_quiz_session_start.py` に TC-01〜TC-17 を書き、現行コードで実行して RED を記録する → auto_test「TDD RED 確認」参照。最大の未知リスクは「スレッド 2 本の同時実行テストが pytest-django（`transaction=True`）＋ PostgreSQL で決定論的に動くか」なので、TC-07・TC-08 を最初に書いて現行コードで RED（有効 2 件）になることを確かめる。決定論的に再現できなければ実装を中断して計画を見直す。
  2. 修正項目 1（モデル）・3（サービス）・4（ビュー）・5（シリアライザ）・6（CORS）・8（回答送信・終了の保存列）を実装する。
  3. 修正項目 2 のマイグレーション 3 本を作る（`0019`・`0021` は `makemigrations`、`0020` は手書き）。
  4. → TC-01〜TC-19・TC-20・TC-21 参照。false-green 注入検証 → auto_test「false-green 自己検証」参照。
- **ステップ2: フロントの重複送信防止（ステップ1 の完了が前提・UI まで貫通）**
  1. `frontend/src/pages/__tests__/QuizSession.start.test.tsx` に TC-30・TC-31 を書き、現行コードで TC-30 が RED（POST 2 回）になることを記録する。
  2. `setupTests.ts` と修正項目 7 を実装する → TC-30〜TC-33 参照。
  3. `e2e/tests/quiz-session.spec.ts` に TC-40 を追加する。
- **ステップ3: 全体回帰（ステップ1・2 の完了が前提）**
  1. → TC-22・TC-33 参照。
- **ステップ4: dev DB への適用（ステップ3 の完了が前提・Danger Ops）**
  1. 手動テスト No.1（対象件数の確認）→ **ユーザー承認** → No.2（`migrate`）→ No.3（適用後の確認）→ No.4（E2E をローカル実行）。

依存関係: ステップ1 → 2 → 3 → 4 は直列。サービス再起動: 不要（backend は開発サーバーの自動再読み込み・マイグレーションは手動テスト No.2 で適用）。

## 6. テスト計画

### 自動テスト（詳細: `docs/tests/open/I158_auto_test.md`）
- **テストレベル**:
  - API 結合（DRF `APIClient`・PostgreSQL のテスト DB）: 開始の振る舞い・キーの扱い・405・CORS preflight（TC-01〜TC-13・TC-15〜TC-17）。
  - 並行実行の結合（`pytest.mark.django_db(transaction=True)`＋`threading.Barrier`）: 同時開始（TC-07・TC-08）。行ロックと部分ユニーク制約は実 DB でしか検証できない。
  - DB 制約の単体（TC-09）・データマイグレーション関数の単体（TC-14）。
  - マイグレーションの通し実行（TC-21: `--migrations --create-db` でまっさらな DB に全マイグレーションを適用）。
  - フロント単体（Jest・`<React.StrictMode>` 下で描画）: POST 1 回とヘッダ（TC-30）・失敗時の扱い（TC-31）。
  - E2E（Playwright・開発サーバー = StrictMode 有効）: 実ブラウザで POST 1 回とヘッダ（TC-40）。
- **再発防止**: TC-07（同時 2 回で有効 1 件）・TC-30 / TC-40（StrictMode で POST 1 回）は現行コードで RED になることを記録してから実装する。
- **認可・境界**: 未認証は 401（TC-17）。別ユーザーが同じキーを使っても互いに影響しない（TC-16 = キーはユーザーごと）。`is_active` の書き換え経路が閉じている（TC-11・TC-12）。

### 手動テスト（詳細: `docs/tests/open/I158_manual_test.md`）
- すべて Claude 実施（dev DB の件数確認・マイグレーション適用・E2E のローカル実行）。画面の見た目は変わらないため Human の目視は不要。ただし No.2（dev DB への `migrate`）は Danger Ops のため、実行前にユーザー承認を得る。

## 7. ロールバック
- コード: 本 PR の revert で元に戻る。
- DB: `docker compose exec -T backend python manage.py migrate problems 0018` で制約 2 つと `client_request_id` 列が消える（`0020` の逆方向は何もしない）。データマイグレーションで終了扱いにしたセッションは有効に戻らないが、回答データは失われず、元々「同じ開始の重複」だったものなので戻す必要はない。念のため、適用前に対象セッションの id を手動テスト No.1 で記録する。

## 8. Risk & 回避策
- **リスク1（同時実行テストが不安定）**: スレッドの実行順やコネクション管理で TC-07・TC-08 が時々失敗する。→ 回避: `threading.Barrier(2)` で開始を揃え、各スレッドの最後で `connection.close()`。合否は「最終状態（有効 1 件・セッション総数）」だけで判定し、どちらが先かには依存しない。ステップ1 の最初に現行コードで RED を確認して、テストが本当に競合を再現できることを確かめる。
- **リスク2（ユーザー行ロックの副作用）**: 開始中に同じユーザーの行を更新する別処理（ログイン時の `last_login` 更新など）が待たされる。→ 回避: ロックの範囲は開始処理 1 回（数クエリ）のみで短い。ロックは同じユーザーの行だけで、他のユーザーには影響しない。
- **リスク3（マイグレーションが dev DB で失敗）**: 重複解消の漏れで `0021` の制約追加が失敗する。→ 回避: `0020` を `0021` と別トランザクションにする。手動テスト No.1 で対象件数を確認し、No.3 で適用後に重複が 0 件であることを確認する。失敗しても各マイグレーションはトランザクション内のため途中状態は残らない。
- **リスク4（`crypto.randomUUID` が無い環境）**: 非 HTTPS・古いブラウザで例外になる。→ 回避: `generateIdempotencyKey()` で存在を確かめ、無ければヘッダを付けずに送る（サーバーは後勝ちで受け付ける）。
- **リスク5（I166 との衝突）**: I166 も `create` を変更する。→ 回避: 後からマージする側が develop を取り込んで統合する（grill-me で決定済み）。本計画では開始処理をサービスへ移すため、I166 の組織チェックはサービスに足す形になる。
- **リスク6（API 契約の変化）**: 405 化・応答コードの追加で既存の呼び出し元が壊れる。→ 回避: PUT/PATCH/DELETE の利用箇所が無いことを grep で確認済み。画面は 200 と 201 を区別せず `response.data` だけを使う。
- **補足（スコープ外の既知事項）**: 409/422 のとき、共通のエラーハンドラ（`frontend/src/services/api.ts:197-204`）も「予期しないエラーが発生しました」を表示し、画面のトーストと合わせて 2 つ出る。これは既存の未対応ステータスと同じ挙動で、本イシューでは変えない（409 は直列化により通常は起きない）。

## 10. データ整合性設計
- **DB 制約**: `uniq_active_quizsession_per_user`（`user`・`is_active=True` の部分ユニーク）、`uniq_quizsession_user_request_id`（`user`＋`client_request_id`・`client_request_id IS NOT NULL` の部分ユニーク）。`client_request_id` は `UUIDField(null=True, blank=True)`。FK（`user` / `subject`・`on_delete=CASCADE`）は変更なし。
- **トランザクション境界**: `QuizService.start_session` の `transaction.atomic()` ブロック 1 つ。ロック取得 → キー照合 → 既存終了 → 新規作成を同じトランザクションで行う。
- **冪等性**: 同じユーザー・同じキーの再送は同じセッションを返す（200）。キーはユーザーごとに一意。
- **同時更新**: 同一ユーザーの開始処理は `select_for_update` で直列化。すり抜けは DB 制約で拒否し 409。
- **マイグレーション安全性**: 列追加（null 可・既定値なし = 既存行の書き換え無し）→ データ更新 → 制約追加の 3 段階・各段で別トランザクション。逆方向は `migrate problems 0018`。後方互換: キー無しのリクエストもこれまでどおり受け付ける。

## 13. 性能・UX設計
- **画面**: 見た目・ラベル・配置の変更なし。読み込み中表示（`CircularProgress`）・エラー時のトースト＋ダッシュボードへ戻る動きも現行どおり。
- **性能**: 開始処理に「ユーザー行のロック」と「キーでの検索」（部分ユニークインデックスを使う）が増えるだけで、N+1 等の懸念なし。
- **破壊的操作の確認導線・アクセシビリティ**: 該当なし（UI 変更なし）。

## セキュリティ・ベストプラクティスチェック
- **入力バリデーション**: `Idempotency-Key` は `uuid.UUID()` で解釈できるものだけを受け付け、それ以外は 400。値は DB にのみ保存し、応答・ログに出さない。`subject` は従来どおりシリアライザで検証（組織の境界チェックは I166 の範囲）。
- **認証・認可**: `permission_classes = [permissions.IsAuthenticated]` 変更なし。書き換え・削除を 405 にし、`is_active` を読み取り専用にすることで、API 直叩きでの状態改変の経路を減らす（最小権限の方向）。キーの照合は必ず `user` で絞るため、他人のキーで他人のセッションを取得できない（TC-16）。
- **機密データ**: 新規の個人情報なし。キーはランダムな UUID で、推測されても本人のセッションしか返らない。
- **OWASP**: SQL は ORM のみ。CSRF: JWT（Authorization ヘッダ）認証の API で変更なし。XSS: 表示の変更なし。CORS: 許可ヘッダに 1 つ足すだけで、許可オリジン（`CORS_ALLOWED_ORIGINS`）は変更なし。
- **依存ライブラリ**: 追加なし（UUID はブラウザ標準・Python 標準）→ pip-audit / npm audit の新規対象なし。
- **スキャン基準**: bandit は MEDIUM 以上を修正対象（LOW は `# nosec` で理由付き抑制）、npm audit は high/critical を修正対象（pre-commit / CI で検証）。

## 高リスク判定
- **判定: Yes**。理由: 外部公開 API（`POST /api/quiz/`）の契約変更（ヘッダ追加・応答コード追加・405 化）、画面制御に頼らず API 直叩きでも守るべき不変条件の追加、DB スキーマ変更（部分ユニーク制約）とデータマイグレーション（Danger Ops）を含む。
- **確定フロー**: `/plan-issue-review I158` → `/security-review I158` → `/implement I158`。code-review では敵対的レビューの対象（`docs/runbooks/review-rules.md`）。

## 各種チェック結果
- **P3（データ整合性）**: 上記「10. データ整合性設計」に記載。
- **P5（運用設計）影響なし**: 外部 API・非同期処理・バッチの追加なし。
- **P6（性能・UX）**: 上記「13. 性能・UX設計」に記載。
- **P8（コスト）影響なし**: 新規インフラ・外部サービスなし。
- **P9（プライバシー）影響なし**: 個人情報の新規取得・保存・露出なし（ランダムな UUID のみ）。テナントをまたぐ処理の追加なし。
- **学習効果設計（14）**: 出題・採点のロジックは変えない。空のセッションが学習履歴に混ざらなくなることで、学習記録の正確さ（品質基準 C1 の前提となるデータ品質）が上がる。

## 設計判断の明示
| 設計判断 | 出所 |
|---------|------|
| Idempotency-Key（UUID・`client_request_id`・ユーザーごとに一意）・同じキーは 200・異なるキーは後勝ち・キー無しも受け付ける | イシュー明記（grill-me） |
| `transaction.atomic`＋ユーザー行の `select_for_update`・部分ユニーク制約・`IntegrityError` は 409 | イシュー明記（grill-me） |
| `http_method_names = ['get', 'post', 'head', 'options']`・`is_active`/`started_at` を読み取り専用 | イシュー明記（grill-me） |
| CORS 許可ヘッダ・`crypto.randomUUID`＋`setupTests.ts` で補完・400/422 の扱い・並行テストの方法 | イシュー明記（grill-me 2 回目） |
| 開始処理を `QuizService.start_session` に置く（ビューから移す） | 仮定で決めた（規約 §6・§14「トランザクション境界はサービス層」に従う） |
| マイグレーションを 3 本（列追加 / データ / 制約）に分ける | 仮定で決めた（PostgreSQL の pending trigger events 回避・スキーマとデータの分離） |
| 2 つ目の制約に `condition=Q(client_request_id__isnull=False)` を付ける | 仮定で決めた（意味は同じ・対象を明示し部分インデックスを小さくする） |
| データマイグレーションで終了扱いにする行の `ended_at` は「未設定なら実行時刻」 | 仮定で決めた（現行 `create` が既存セッションを終了するときと同じ扱い） |
| エラー本文は `create_error_response` の統一形式・文言は計画の修正項目 4 のとおり | 仮定で決めた（既存の統一ヘルパーに合わせる） |
| `crypto.randomUUID` が無い環境ではヘッダを付けずに送る | 仮定で決めた（非 HTTPS でも開始できるようにする・`useRef` ガードは効く） |
| ガードは「科目ごとに 1 回」（`startedSubjectRef`） | 仮定で決めた（同じ画面のまま科目が変わった場合も正しく開始できる） |
| 開始経路のフロントテストは新規ファイル `QuizSession.start.test.tsx` | 仮定で決めた（既存ファイルは `useParams` を既存セッション用に固定しているため） |
| TC-10（409 の対応付け）だけは `unittest.mock.patch` で `IntegrityError` を起こす | 仮定で決めた（ロックがある限り実際には起きない守りの分岐で、実 DB で決定論的に起こす方法が無いため） |
| 高リスク判定 Yes（security-review を挟む） | 仮定で決めた（code-reviewer.md の条件「外部公開API変更」「API直叩きで事故りうる変更」「DBスキーマ重要変更」に該当） |

→ 「仮定で決めた」項目は、ユーザー指示「ベストプラクティス・モダンな Web アプリとして理想的なやり方で進めて」（2026-10-24）に基づき Claude が決定した。承認ポイントで一括確認する。

## 9. 承認ポイント（チェックリスト）
- [ ] 修正方式: サーバーは `QuizService.start_session`（ロック＋キー照合＋後勝ち＋409 変換）・ビューは解析と応答の対応付けのみ・405 化・`is_active` 読み取り専用・CORS 許可ヘッダ追加、フロントは `useRef` ガード＋`Idempotency-Key` 送信 — でよいか
- [ ] マイグレーション 3 本（`0019` 列追加・`0020` 重複解消・`0021` 制約追加）と、dev DB への適用は手動テスト No.2 の直前に改めて承認を得る運用 — でよいか
- [ ] エラー応答の文言（400「Idempotency-Key は UUID 形式で指定してください」・409「クイズの開始が競合しました」・422「Idempotency-Key が別の内容で使用されています」）— でよいか
- [ ] UI: 見た目・配置・ラベルの変更なし。エラー時は現行どおり「クイズセッションの作成に失敗しました」＋ダッシュボードへ戻る — でよいか
- [ ] 手動テスト: すべて Claude 実施（dev DB の件数確認・migrate・E2E のローカル実行）・Human の目視なし — でよいか
- [ ] 高リスク判定 Yes（plan-review の後に security-review） — でよいか

## レビュー結果
- [20261024_1648 判定: ✅ 完了](../../reviews/I158_plan_review_20261024_1648.md)（計画変更記録 1 のやり直しレビュー）
- 指摘への対応（2026-10-24・1648 分）: ① Warning（TC-10 のロールバック確認が弱い）→ 事前に有効セッション S0 を作り、409 の後も S0 が有効のまま（`create` の前の `update` が取り消されている）ことを確かめる形に変更。② Info（TC-07・TC-08 の応答の集め方）→ 共有リストへの追加・例外の収集・`join(timeout)` 後のハング検出を auto_test の注に明記。
- [20261024_1636 判定: ✅ 完了](../../reviews/I158_plan_review_20261024_1636.md)
- 指摘への対応（2026-10-24）: ① Warning（`client_request_id` の応答除外）→ `fields` が明示リストのため足さないことで除外される旨を修正項目 5 に追記し、TC-01 に「応答に `client_request_id` が無い」を追加。② Warning（TC-01 の問題数が 0 件一致になり得る）→ fixture で subject_a に未削除 2 件＋削除済み 1 件、subject_b に 1 件の問題を作り、TC-01 の期待値を `total_problems == 2` に具体化。③ Info（context なしのシリアライズ）→ `self.get_serializer(session).data` に変更（create アクションでは `QuizSessionSerializer` が返るため応答の形は同じ）。

## 計画変更記録
- **変更 1（2026-10-24・security-review 由来）**: 修正項目 8（`submit_answer`・`end` の `update_fields` 化）と TC-18・TC-19 を追加。理由: 制約の追加後、別タブの開始と回答送信が重なると、回答送信の全列保存が `is_active=True` を書き戻して `IntegrityError`（500）になる経路があるため。範囲が広がる変更のため、/code-review の前に /plan-issue-review をやり直す。
- **変更 2（2026-10-24・/implement 中に発見）**: `createNewSession` の呼び出し元がもう 1 か所あった（完了画面の「もう一度挑戦」ボタン・`QuizSession.tsx` の `onClick={createNewSession}`）。調査時の grep が `navigate(` だけで呼び出し元を全件洗っていなかった。引数を足したことで型エラーになり発覚。`onClick={() => createNewSession(generateIdempotencyKey())}` に変更し（クリックごとに新しいキー＝意図的なやり直しは後勝ち）、既存の `QuizSession.test.tsx` に TC-34 を追加。方式・AC は変わらない（呼び出し元の追従のみ）ため plan-review のやり直しは不要と判断。ユーザー指示「承認なしで進めて」（2026-10-24）により事後記録。
- **変更 3（2026-10-24・/implement 中に発見）**: TC-40 の期待値を「安全なコンテキストならキー付き・そうでなければキー無し」に変更。compose 内の e2e コンテナは `http://frontend:3000`（安全なコンテキストでない）で開くため `crypto.randomUUID` が無く、計画どおりの代替動作（キー無しで送る）になることを実測した。CI（`http://localhost:3000`）ではキー付きの経路を検証する。POST 1 回の判定は両環境で同じ。
- **変更 4（2026-10-24・/implement 中に発見）**: TC-14 は関数実行後に制約を付け直さず、有効件数で解消を確かめる形に変更（auto_test の注に理由を記録）。

## セキュリティレビュー結果

**実施日**: 2026-10-24

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Medium | OWASP Top 10（整合性・可用性） | `submit_answer`・`end` が読み込んだセッションを `session.save()`（全列上書き）で保存する。別タブの開始が間に割り込むと `is_active=True` を書き戻し、制約追加後は回答送信が 500 になる（追加前は有効 2 件に黙って戻っていた） | **必須防御条件**: 両アクションの保存を `update_fields` 指定にする（修正項目 8）。TC-18（書き戻さない）・TC-19（全列保存の不在を決定論 grep で固定・現行で exit 1 を確認済み）で担保 |
| Low | マルチテナント | 開始時の `subject` に他組織の科目 ID を指定できる・科目未指定の `total_problems` が全組織を数える（以前からの不備） | 本変更で悪化しない（サービスへ移すだけで判定は変えない）。I166（#284・優先度高）で是正。**禁止事項**: 本イシューで組織判定を部分的に足して I166 と二重実装にしない |
| Low | 入力検証 | `Idempotency-Key` に長大・不正な値が来る | `uuid.UUID()` で解釈できない値は 400（空文字含む・TC-05）。値は DB にだけ保存し、応答・ログに出さない（**禁止事項**: キーの値をログ出力しない） |
| Low | 認証・認可 | 同じキーの照合で他人のセッションが返る | 照合は必ず `user` で絞る（`filter(user=user, client_request_id=...)`）。制約もユーザー単位。TC-16 で担保 |
| Low | OWASP Top 10（DoS） | 開始の連打で自分のユーザー行のロックが続き、同じユーザーの他の更新（`last_login` 等）が待たされる | ロック範囲は同一ユーザーの行のみ・1 回の開始処理（数クエリ）で解放。既存の DRF ユーザー単位スロットル（I127）が連打を抑える |
| — | 機密情報 | なし（新規の個人情報なし。`client_request_id` は応答に含めない） | — |
| — | ファイル操作 | なし | — |
| — | 外部通信 | なし | — |
| — | 依存ライブラリ | なし（追加なし・UUID は標準機能） | — |
| — | セキュリティ設定（CORS） | 許可ヘッダに `idempotency-key` を足すのみ。許可オリジン・`CORS_ALLOW_CREDENTIALS` は不変更 | TC-13 |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | `POST /api/quiz/` | 未認証 | セッションを作る | 401・作成されない | Yes: TC-17 | No | なし | Low |
| 2 | `POST /api/quiz/` | 一般 | 他人が使った（推測した）キーで再送し、他人のセッションを取得する | キー照合はユーザー単位。他人のセッションは返らず、自分の新規セッションになる | Yes: TC-16 | No | なし | Low |
| 3 | `POST /api/quiz/` | 一般 | 同時に大量送信して有効セッションを 2 件以上作る | 行ロックで直列化・部分ユニーク制約で拒否・違反は 409 | Yes: TC-07・TC-08・TC-09・TC-10 | No | なし | Low |
| 4 | `PUT`/`PATCH /api/quiz/<id>/` | 一般 | 終了済みセッションを `is_active=true` に戻す・集計値を改ざんする | 405・`is_active` は読み取り専用 | Yes: TC-11・TC-12 | No | なし | Low |
| 5 | `DELETE /api/quiz/<id>/` | 一般 | 自分の学習履歴を消す | 405 | Yes: TC-11 | No | なし | Low |
| 6 | `POST /api/quiz/<id>/submit_answer/` と別タブの `POST /api/quiz/` | 一般 | 回答送信と開始を重ねて、終了済みセッションを有効に戻す／500 を起こす | 回答送信・終了は必要な列だけ保存し `is_active` を書き戻さない | Yes: TC-18・TC-19 | No | 終了直後の古いセッションに回答が 1 件記録され得る（以前からの挙動・有効化はしない） | Medium（対処後 Low） |
| 7 | `POST /api/quiz/`（`Idempotency-Key` ヘッダ） | 一般 | 不正形式・空・巨大な値を送る | 400・作成されない | Yes: TC-05 | No | なし | Low |
| 8 | `POST /api/quiz/`（`subject`） | 一般 | 他組織の科目 ID を指定する | （本イシューでは変更なし） | No（I166 で追加） | No | 以前からの不備が残る（I166 で是正） | Low |
| 9 | `OPTIONS /api/quiz/`（別オリジン） | 未認証 | 許可外オリジンから preflight を通す | 許可オリジンは不変更・ヘッダのみ追加 | Yes: TC-13（許可オリジンでヘッダが許可される） | No | なし | Low |
| 10 | Django 管理画面（QuizSession の編集） | 管理者 | 終了済みセッションを有効に戻して制約違反 | Django 5.2 の ModelForm が `UniqueConstraint`（条件付き含む）を検証し、フォームエラーで止まる（500 にならない） | No（フレームワーク標準の挙動） | No | なし | Low |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 0件 | 0件 |
| Medium  | 1件 | 1件（#6・設計レビューの Medium と同一。計画に対処を反映済み） |
| Low     | 4件 | 9件 |

### 残余リスク処遇
（/retro で決定する）
