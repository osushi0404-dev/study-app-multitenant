# Django/Python バックエンド コーディング規約

このプロジェクト（マルチテナントの学習アプリ・Django＋DRF の API）でのコードの書き方の決まり。計画を書く工程・計画レビュー役・コードレビュー役が照合に使う。

- 書いてあるのは「このプロジェクトではこうする」という決まりと、よくある間違いの例だけ。一般的な書き方の解説は、各節の「参照」の公式の文書を読む
- あるべき姿を書いている。今のコードがまだ追いついていない決まりは §16 の移行のイシューで直す（どの決まりをいつから守るかは §16）
- 決まりを変えるときは、前提の版と点検した日もあわせて見直す（I545）

## 0. 前提の版（点検した日: 2026-11-17）

方針: 長期サポート版（LTS）の区分がある道具は、公式がサポート中の最新の LTS。区分が無い道具は最新の安定版。前提の版どうしは、公式が組み合わせに対応をうたうものにする。

| 道具 | 前提の版 | 区分 | サポートの終わり | 出典 |
|---|---|---|---|---|
| Django | 5.2 | LTS（最新の LTS） | 2028-04（延長サポートの終わり） | https://www.djangoproject.com/download/ |
| Python | 3.14 | 最新の安定版のうち Django 5.2 が対応する最新（5.2.8 から対応） | 2030-10 | https://devguide.python.org/versions/ ・ https://docs.djangoproject.com/en/5.2/faq/install/ |
| PostgreSQL | 18 | 最新の安定版（Django 5.2 は 14 以上に対応） | 2030-11-14 | https://www.postgresql.org/support/versioning/ ・ https://docs.djangoproject.com/en/5.2/ref/databases/ |
| psycopg | 3.3 | 最新の安定版（Django が psycopg 3 を推奨） | 公開の予定なし | https://pypi.org/project/psycopg/ ・ https://docs.djangoproject.com/en/5.2/ref/databases/ |
| Django REST framework | 3.18 | 最新の安定版（Django 5.2〜6.1 に対応） | 公開の予定なし | https://pypi.org/project/djangorestframework/ |
| Celery | 5.7 | 最新の安定版（Python 3.10〜3.14） | 公開の予定なし | https://pypi.org/project/celery/ |
| Redis | 8.10 | 最新の安定版 | 公開の予定なし | https://github.com/redis/redis/releases |

ここに無い依存（simplejwt・drf-spectacular・django-filter など）と、表の道具の小さな版は `backend/requirements.txt` の固定の版に従い、Dependabot で上げる（`docs/runbooks/dependency-audit.md`）。今の環境との差は §16。

## 1. 使う道具（このプロジェクトではこれ）

| 用途 | 使うもの | 使わないもの |
|---|---|---|
| Web の枠組み | Django＋DRF（同期のビュー・WSGI〔gunicorn〕） | async のビュー・ASGI（時間のかかる処理は Celery に回す） |
| DB とドライバ | PostgreSQL＋psycopg 3 | psycopg2（Django が将来の非推奨を予告）・生 SQL（ORM で書けないときだけ、パラメータで渡す） |
| 非同期の処理 | Celery＋Redis（`core/celery.py`） | スレッド・`asyncio` での自前の非同期 |
| API の仕様 | drf-spectacular で `backend/openapi.yaml` を作り、画面の型をそこから作る（I493） | 手で書いた API の説明 |
| 認証 | djangorestframework-simplejwt | 自作のトークン |
| 絞り込み | django-filter・DRF の SearchFilter／OrderingFilter | 自前のクエリの組み立て |
| テスト | pytest＋pytest-django | Django の `manage.py test` ランナー |
| リントと整形 | Ruff（`backend/pyproject.toml`）・bandit・pip-audit | flake8・black・isort を別に入れる |
| 型チェック | 型ヒント＋mypy（django-stubs・djangorestframework-stubs） | 型ヒント無しの公開関数 |
| ログ | 標準の `logging`（設定は `core/enhanced_logging.py`） | `print`・structlog などを別に入れる |

参照: https://docs.djangoproject.com/en/5.2/ref/databases/#postgresql-notes

## 2. 構成と置き場所

- アプリ: `accounts`（利用者・組織）・`problems`（科目・問題・クイズ）・`studylogs`（学習記録・間隔反復）・`dashboard`（集計の表示）・`core`（設定・ミドルウェア・共通の例外・ログ）・`common`（ビューの共通のミックスイン）
- 設定は `core/settings.py` の 1 つ。環境で変わる値は環境変数から読む（12-factor）。秘密の値を既定値に書かない
- アプリの中の置き場所:

| 置くもの | 場所 |
|---|---|
| モデル | `models.py` |
| 組織で絞る取り出し方 | `querysets.py`（`problems/querysets.py` の `OrgScopedQuerySet` を土台にする） |
| 書き込みと業務の処理 | `services.py`、大きくなったら `services/`（例: `problems/services/`） |
| 読み取りの組み立て（集計など） | `selectors.py`（例: `dashboard/selectors.py`） |
| 入出力の形と検証 | `serializers.py` |
| HTTP の受け口 | `views.py`（§6） |
| 権限 | `permissions.py` |
| Celery のタスク | `tasks.py` |
| テスト | `tests/test_I<番号>_<内容>.py`（イシュー番号を付ける） |

## 3. 命名と書き方

- PEP 8 に従う（クラス `PascalCase`・関数と変数 `snake_case`・定数 `UPPER_SNAKE_CASE`）。真偽値は `is_`・`has_`・`can_` で始める
- 公開する関数（サービス・セレクタ・タスク）には型ヒントを付ける。サービスの引数はキーワード専用（`def create_x(*, user, subject)`）にして、呼び出しの取り違えを防ぐ
- 入れ子は早期リターンで浅くする。1 つの関数・クラスは 1 つの役目にする
- 公式が非推奨にした API（`DeprecationWarning` が出るもの。例: §4 の `CheckConstraint(check=)`）を使わない
- 参照: https://peps.python.org/pep-0008/

## 4. モデルとマイグレーション

- 選択肢は `models.TextChoices`、お金・点数の割合など誤差が困る値は `DecimalField` を使う
- 外部キーには `on_delete` を必ず書き、`PROTECT`・`CASCADE`・`SET_NULL` のどれにしたかの理由をコメントか計画書に残す
- 制約は DB に置く: `Meta.constraints` の `UniqueConstraint`・`CheckConstraint`。`CheckConstraint` は `condition=` で書く（`check=` は Django 5.1 で非推奨）
  ```python
  # ❌ 悪い例
  models.CheckConstraint(check=models.Q(score__gte=0), name="score_non_negative")
  # ✅ 良い例
  models.CheckConstraint(condition=models.Q(score__gte=0), name="score_non_negative")
  ```
- 索引は絞り込み・並べ替えに使う列の組み合わせで `Meta.indexes` に書く
- `save()` を上書きして業務の処理を書かない（サービスに書く）。`save()` で守るのは、その行だけで決まる値の整え方まで
- マージしたマイグレーションは書き換えない。直すときは新しいマイグレーションを足す
- データを書き換えるマイグレーションは、スキーマの変更と分け、`RunPython` に戻す処理（`reverse_code`）を書く
- 外部キーを足すマイグレーションで、参照先の表が別のマイグレーションで `DeleteModel` → `CreateModel` と作り直されているときは、その作り直しのマイグレーションを `dependencies` に明示する（I050。書かないと外部キーが作り直しより先に流れ、`ProgrammingError` になる）
  ```python
  # ✅ 良い例（problems/0004 が accounts.Organization に外部キーを足す）
  dependencies = [
      ("accounts", "0009_organization_user_users_organiz_ca9165_idx_and_more"),
      ("accounts", "0010_update_organization_structure"),  # Organization を作り直したもの
      ("problems", "0003_field_problem_field_usersubjectaccess_and_more"),
  ]
  ```
- 参照: https://docs.djangoproject.com/en/5.2/ref/models/constraints/ ・ https://docs.djangoproject.com/en/5.2/topics/migrations/

## 5. 組織の境界（マルチテナント）— いちばん大事

- 利用者の記録・科目・問題を読むクエリは、必ず組織で絞る。記録は `OrgScopedQuerySet` のサブクラスの `for_user(user)` で取り、科目・問題の候補は `problems/services/tenant_scope.py` で決める
- 絞る組織は `request.user` から決める。リクエストの値（クエリ・本文・URL）から組織を決めない
- どうしても絞らずに読むときは、呼び出しの直前に `# 組織で絞らない: <理由>` を書く（`studylogs/tests/test_I455_org_scoped_querysets.py` が付け忘れを止める）
- 他の組織の物を詳細・更新・削除で指したときは、`get_queryset()` で絞った結果として 404 を返す（他の組織の物があることを知らせない）
- 応答・集計・ログ・Celery のタスク（§12）の中でも、組織を越えた値を混ぜない
- 他の組織の利用者で読めない・書けないことのテストは §13 の必ず書くテストに入れる（例: `core/tests/test_I446_cross_api_tenant_isolation.py`・`problems/tests/test_I166_quiz_tenant_isolation.py`）
- 由来: #431（学習記録の API で他組織の問題文が取れた）・#461

## 6. API（DRF）

- ビューは `ViewSet`／`GenericAPIView` を使い、薄く保つ。処理はサービス・セレクタに書く（Fat View にしない）
- 一覧を返さない `GenericAPIView` にも全体の設定の絞り込み・並べ替え・ページ分けが効く（`?ordering=` などで 500 になりうる・I587）。使わないなら `filter_backends = []`・`pagination_class = None` にする
- 認証の既定は `IsAuthenticated` にする（`REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]`）。認証なしで開く API は、ビューに `AllowAny` を書いて理由をコメントに残す
- `permission_classes` はビューごとに具体的なクラスで書く。`get_permissions()` を上書きするときは、`@action(permission_classes=...)` の指定が使われなくなることに注意し、action ごとの権限を `get_permissions()` の中で全部書く（一覧 I209 F8）
  ```python
  # ❌ 悪い例: get_permissions が @action の permission_classes を上書きして、stats が誰でも読める
  def get_permissions(self):
      return [IsAuthenticated()] if self.action == "list" else [AllowAny()]
  @action(detail=False, permission_classes=[IsOrgAdmin])
  def stats(self, request): ...
  # ✅ 良い例: action ごとの権限を get_permissions の中でそろえる
  def get_permissions(self):
      if self.action == "stats":
          return [IsAuthenticated(), IsOrgAdmin()]
      return [IsAuthenticated()]
  ```
- 入力は必ずシリアライザーで検証する。クエリの値も `int()` で直接変換しない。一覧の絞り込みに使うクエリの値は django-filter の FilterSet で、それ以外のクエリの値（`?days=`・`?limit=` など）はクエリ用のシリアライザーで、型・範囲を検証してから使う（由来: #479。数字でない値で 500・大きな値で重い処理）
- 応答に、その時点の利用者に見せてはいけない項目を入れない。action ごとに出力のシリアライザーを分ける（例: 回答の前のクイズの応答に正解・解説・解説画像を入れない。由来: #476・I078）
- 一覧は必ずページ分けする（既定 `PageNumberPagination`・20 件）。上限なしの全件の応答を作らない
- エラーの応答は `core.exceptions.custom_exception_handler` の形（`{"error": {"main_message", "sub_message", "details"}}`）にそろえる。ビューで独自の形のエラーを返さない
- 画面と API の受け渡しの形は OpenAPI（`backend/openapi.yaml`）を正にする。シリアライザーを変えたら、`docs/runbooks/common-commands.md` の手順で `backend/openapi.yaml` と `frontend/src/types/api/schema.d.ts` を作り直す（CI と `core/tests/test_I493_openapi_contract.py` が食い違いを止める。由来: #460・#473・#488）
- 参照: https://www.django-rest-framework.org/api-guide/viewsets/ ・ https://www.django-rest-framework.org/api-guide/permissions/ ・ https://drf-spectacular.readthedocs.io/

## 7. サービスとセレクタ

- 書き込みと業務の処理はサービスに置き、複数の行を書き換えるものは `transaction.atomic` で囲む。トランザクションの境界はサービスで決める
- 読み取りの組み立て（集計・一覧の絞り込み）はセレクタか QuerySet のメソッドに置く
- 同じ操作の 2 回目で壊れないようにする（冪等）。二重送信で記録が 2 つにならないよう、一意の制約か「すでにあれば返す」で守る
- サービスは業務の例外（`ValidationError` や、アプリの例外クラス）を投げる。`except Exception` で受けて `str(e)` を利用者向けの文に入れない（内部の情報が漏れる）
  ```python
  # ❌ 悪い例
  try:
      ...
  except Exception as e:
      raise ValidationError(f"作成に失敗しました: {e}")
  # ✅ 良い例: 想定できる例外だけを受け、ログに残して、利用者には決まった文を返す
  except IntegrityError:
      logger.warning("duplicate answer user_id=%s session_id=%s", user.id, session.id)
      raise ValidationError("同じ回答がすでに記録されています")
  ```
- シグナルに業務の処理を書かない（呼び出しの流れが追えなくなる）。シグナルは、別のアプリの都合で後片付けが要るときだけ使う

## 8. クエリと性能

- 関連をたどるときは `select_related`（1 対 1・多対 1）・`prefetch_related`（多対多・逆向き）で N+1 を避ける。件数は `annotate(Count(...))` で取り、ループの中で `.count()` しない
- N+1 が起きやすい一覧・集計の API には、`django_assert_num_queries`（pytest-django）でクエリの数のテストを書く（由来: #461）
- 大量の作成・更新は `bulk_create`・`bulk_update`・`update()` を使う
- 割り算の分母が 0 になりうる集計（正答率など）は、0 のときの値を決めてから計算する（由来: #459。解いた問題が 0 件の日で 500）
- 必要な列だけ読む（`only`・`values`）のは、測って遅いときだけにする
- 参照: https://docs.djangoproject.com/en/5.2/topics/db/optimization/

## 9. 日付と時刻

- `USE_TZ = True`・`TIME_ZONE = "Asia/Tokyo"` のまま使う。DB には aware な日時を保存する
- 「今日」は `timezone.localdate()`、今の時刻は `timezone.now()` で取る。`date.today()`・`datetime.now()`・`datetime.utcnow()` は使わない（由来: #481。日本時間の 0〜9 時に日付が 1 日ずれる）
- 日時を日付に変えるときは、先に `timezone.localtime()` で日本時間にしてから `.date()` を取る
- 参照: https://docs.djangoproject.com/en/5.2/topics/i18n/timezones/

## 10. 認証・認可・セキュリティ

- アクセストークンは短く、リフレッシュトークンは使い回しのたびに作り直して古いものを無効にする（`ROTATE_REFRESH_TOKENS`・`BLACKLIST_AFTER_ROTATION` と `rest_framework_simplejwt.token_blacklist` を入れる。由来: #501）
- リフレッシュトークンは、画面の JavaScript から読めない場所（`HttpOnly`・`Secure`・`SameSite` の Cookie）で受け渡す。応答の本文で返して画面の localStorage に置かせない（OWASP: セッションの識別子を localStorage に置かない。画面側は React 規約 §11）
- `SECRET_KEY`・DB のパスワードなどの秘密は環境変数から読み、コードと既定値に書かない。本番では `DEBUG = False`
- デプロイの前に `python manage.py check --deploy` を通す。廃止された設定を書かない（`SECURE_BROWSER_XSS_FILTER` は Django 4.0 で廃止され何もしない。代わりに Content-Security-Policy を付ける）
- 組織の管理者だけの操作は `IsOrgAdmin` などの権限クラスで止める。ビューの中の `if` だけで止めない。権限クラスは `permissions.py` に置く
- アップロードされたファイルは、拡張子でなく中身（`python-magic`）と大きさで検証する（I180）
- 回数の制限は DRF のスロットル（`core/throttling.py`・I127）を使う
- 参照: https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/ ・ https://docs.djangoproject.com/en/5.2/topics/security/ ・ https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html

## 11. ログ

- `logger = logging.getLogger(__name__)` を使い、値は `%s` の引数で渡す（`logger.info("x user_id=%s", user.id)`。f-string で組み立てない）
- ログに個人情報（メールアドレス・氏名）・トークン・パスワード・問題の本文を出さない。利用者は ID で書く（由来: #437・#484。`core/tests/test_I437_no_pii_in_logs.py`）
- 例外は `logger.exception(...)` で残し、握りつぶさない
- 参照: https://docs.python.org/3/howto/logging.html#optimization

## 12. Celery のタスク

- タスクにはモデルの物でなく ID を渡し、タスクの中で取り直して組織で絞る
- 同じタスクが 2 回流れても壊れないようにする（冪等）。そのうえで `acks_late=True` を付ける
- 自動の再試行は、一時的な失敗の例外だけ（`autoretry_for=(ConnectionError, ...)`）にし、`Exception` 全部を再試行しない。`retry_backoff` を付ける
- 時間の上限（`soft_time_limit`・`time_limit`）を付ける
- 参照: https://docs.celeryq.dev/en/stable/userguide/tasks.html

## 13. テスト

- API を足す・変えるときに必ず書くテスト（`@action` を含むすべての action について）: 認証なし（401）・他の組織の利用者（404 か 403。§5）・権限の足りない利用者（403）・入力の誤り（400 と `error` の形）・データが空・0 件のとき（§8 の 0 で割る集計を含む）・正常（状態コードと本文の具体的な値）
- バグを直すときは、そのバグを再現するテストを先に書き、落ちることを確かめてから直す
- 時刻に依存するテストは時刻を固定し、日本時間の 0〜9 時の境目も確かめる（§9）
- テストの中で本物の外部サービス（OpenAI・SendGrid）を呼ばない。呼び出しの境目のクライアントを差し替える
- 確かめの手順（手元で流すテストの選び方・コマンド）は `docs/runbooks/backend-check.md`
- 参照: https://pytest-django.readthedocs.io/

## 14. よくある間違い

```python
# ❌ 可変の既定値・例外の握りつぶし・print
def add(items=[]):
    try:
        ...
    except:
        pass
    print(items)

# ✅
def add(items: list[str] | None = None) -> list[str]:
    items = [] if items is None else items
    try:
        ...
    except KeyError:
        logger.exception("add failed")
        raise
    return items
```
- グローバル変数で状態を持たない（ワーカーが複数あり、値が食い違う）
- 外部の I/O（OpenAI・SendGrid・Redis）には必ずタイムアウトを付ける

## 15. 自動で止める範囲／レビューで見る範囲

自動で止める（pre-commit と CI）: Ruff・bandit・pip-audit・`makemigrations --check`・OpenAPI と画面の型の食い違い（I493）。対象と止める水準は `docs/runbooks/pre-commit.md`・`docs/runbooks/dependency-audit.md` と各設定ファイルが正。この規約の決まりのうち機械で止められるもの（§9 の日付・§11 の f-string・§14 の可変の既定値と `print` など）を Ruff の規則で止めるのは §16 のイシュー。書いた内容と実際の設定の食い違いの点検は #520。

レビューで見る（計画レビュー役・コードレビュー役）: §5 の組織の境界・§6 の権限と応答の項目・§7 の層の分け方・§8 の N+1・§9 の日付・§11 のログの中身・§13 のテストの有無。

## 16. 今のコードとの差（移行・直しのイシュー）

規約はあるべき姿を書いている。今のコードとの差は次のイシューで直す。下の表の差に当たる決まり（その行のイシューで入れる道具・版を前提にするもの）は、その行のイシューで直し、ほかのイシューでその道具・版を先に入れない。それ以外の決まりは、新しく書くコードから守る。

| 差 | イシュー |
|---|---|
| Python 3.11 → 3.14（§0） | #554 |
| PostgreSQL 15 → 18（§0） | #555 |
| psycopg2 → psycopg 3（§0・§1） | #556 |
| 型チェック（mypy）が無い（§1・§3） | #559 |
| 権限の既定が空・`SECURE_BROWSER_XSS_FILTER` が残っている・`IsOrgAdmin` が `views.py` にある（§6・§10） | #557 |
| Content-Security-Policy が無い（§10） | #558 |
| リフレッシュトークンを本文で返している（§10） | #553 |
| ログアウトの後もリフレッシュトークンが使える（§10） | #501 |
| 「今日」を `date.today()` などで決めている箇所（§9） | #481 |
| クエリの値を検証せずに変換している箇所（§6） | #479 |
| 機械で止められる決まり（§3・§7・§9・§10・§11・§14）が Ruff・pytest・CI で止まっていない（§15） | #563 |
