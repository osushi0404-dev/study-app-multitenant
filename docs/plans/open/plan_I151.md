# plan_I151: Django 4.2 LTS → 5.2 LTS 更新による脆弱性解消（未使用の django-guardian / django-extensions の削除を含む）

## 基本情報
- **計画書ID**: plan_I151
- **関連イシュー**: #267
- **Draft PR**: #269
- **作成根拠資料**: docs/issues/open/I151.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I151_review.md
- **作成日**: 2026-08-22
- **ブランチ**: `feature/I151-django-52-lts-upgrade`（`origin/develop` 起点）

---

## 1. 背景/目的

### 背景
`pip-audit` がサポート終了した Django 4.2.30 に脆弱性を検出し、CI の `Backend Lint & Security` が失敗している。定期監査（Dependency Audit workflow）は 2026-08-07 から連日 failure で、#262 が自動起票済みのまま滞留している。backend を含む全 PR がマージ不能である。

### 目的
サポート対象内の Django 5.2 LTS へ更新して全 CVE を解消し、`pip-audit -r requirements.txt` を exit 0 に戻す。PR ゲートと定期監査の双方をグリーンにし、停止している全 PR のマージ経路を回復する。

### 原因の概要（平易な説明）
Django 4.2 は延長サポートを終えており、**4.2 系には修正版が出ない**。だからバージョンを上げる以外に直す手段がない。そして Django だけを上げても、周辺パッケージ（DRF など）が新しい Django に対応していないため動かない。だから関連パッケージをまとめて対応版に上げる必要がある。

### 詳細な原因分析
1. `pip-audit` は PyPI の脆弱性データベースを参照し、`requirements.txt` に固定された `Django==4.2.30` に該当する advisory を検出する。
2. 検出された advisory の Fix Versions に **4.2.x が 1 つも含まれない**。これは 4.2 LTS の延長サポート（セキュリティ修正の提供期間）が終了し、修正リリースが 4.2 系に出ないことを意味する。
3. したがってパッチ更新では解消できず、サポート対象系列（5.2 LTS / 6.0 / 6.1）への移行が唯一の手段となる。
4. さらに `requirements.txt` には Django 5.2 に非対応のパッケージが含まれる（DRF 3.15.2 は対応宣言が 5.0 まで、django-filter 23.4 は 5.0 まで、django-redis 5.4.0 と django-extensions 3.2.3 は 4.2 まで）。とくに DRF 3.18.0 は `django>=5.2` を要求するため、Django と DRF は同時更新が必須である。

### 根本原因（コードレベル）
- `backend/requirements.txt:1` `Django==4.2.30`（EOL 系列への固定）
- `backend/requirements.txt:2,7,8,12` DRF / django-extensions / django-filter / django-redis が Django 5.2 非対応バージョンに固定
- `backend/requirements.txt:14` `django-guardian==2.4.0`（Django 5.x 非対応。ただし後述のとおり**未使用**）

---

## 2. 調査結果（必須）

### 2-1. ベースライン計測（2026-08-22・`develop` 起点・Docker 実環境）

| 項目 | コマンド | 結果 |
|---|---|---|
| backend テスト | `docker compose exec -T backend python -m pytest --tb=short -q` | **94 passed**（5 warnings・13.21s） |
| frontend テスト | `docker compose exec -T frontend npm test -- --watchAll=false` | **10 passed / 3 suites**（11.18s） |
| 本体依存の監査 | `docker compose exec -T backend pip-audit -r requirements.txt` | **7 件検出・exit 1** |
| コンテナ稼働 | `docker compose ps` | 6 サービスすべて healthy |

> **注意（イシュー本文との差分）**: イシュー本文は backend テストを「110 件」と記載しているが、これは `feature/I142-*` ブランチ上での件数である。本イシューは `develop` 起点のため**ベースラインは 94 件**。受け入れ条件の「110 件 pass → 110 件 pass の形」は件数の記載形式を示したものであり、本計画では **94 件 pass → 94 件 pass** を判定基準とする。

### 2-2. 脆弱性が 6 件から 7 件に増えている（計画時点の再実測）

イシュー起票時（2026-08-15）は 6 件だったが、2026-08-22 の実測で **7 件**に増えている。

```
Found 7 known vulnerabilities in 1 package
Name   Version ID              Fix Versions
------ ------- --------------- ------------
django 4.2.30  PYSEC-2026-3717 5.2.17,6.0.8     <- 新規（起票後に公開）
django 4.2.30  CVE-2026-48587  5.2.15,6.0.6
django 4.2.30  CVE-2026-6873   5.2.15,6.0.6
django 4.2.30  CVE-2026-8404   5.2.15,6.0.6
django 4.2.30  CVE-2026-48588  5.2.16,6.0.7
django 4.2.30  CVE-2026-53877  5.2.16,6.0.7
django 4.2.30  CVE-2026-53878  5.2.16,6.0.7
```

**この増加は方針に影響しないが、バージョン選択の妥当性を強める。** 新規の `PYSEC-2026-3717` の Fix Versions は **5.2.17** であり、イシュー検討時の「最小限案」で候補に挙がっていた **5.2.16 では解消できない**。決定 3（最新一括＝5.2.17）を採用していたことで追加対応が不要になった。

### 2-3. 更新後セットの監査（計画時点で再実行・2026-08-22）

新しい advisory を含んだ状態でも、確定セットは 0 件である。

| 対象 | 結果 |
|---|---|
| 確定セット（本体依存） | `No known vulnerabilities found`・**exit 0** |
| 確定セット（開発依存） | `No known vulnerabilities found`・**exit 0** |

→ 受け入れ条件「`pip-audit` exit 0」は**達成可能**であることを計画時点で確定済み。

### 2-4. django-guardian が未使用であることの確認

| 確認項目 | 結果 |
|---|---|
| コードからの呼び出し（`assign_perm` 等） | 0 件 |
| `AUTHENTICATION_BACKENDS` への登録 | なし（`accounts.backends.EmailOrUserIdBackend` と `django.contrib.auth.backends.ModelBackend` の 2 つのみ） |
| マイグレーションからの参照 | 0 件 |
| テストコードからの参照 | 0 件 |
| `ANONYMOUS_USER_NAME` 等の専用設定 | 0 件 |
| 出現箇所 | `backend/core/settings.py:41` の `'guardian',` の 1 行のみ |
| `manage.py check` の出力 | `guardian.W001: Guardian authentication backend is not hooked.`（未接続の警告） |

→ **更新ではなく削除**が正しい。本更新で最もリスクの高い「認可パッケージのメジャー 2 段更新（2.4.0 → 3.3.3）」が丸ごと不要になる。

### 2-4b. django-extensions も未使用であることの確認（2026-08-22 の再調査）

当初計画では「4.1 へ更新し、本番依存 → 開発依存への移動は別イシュー」としていたが、前提が誤っていた。

| 確認項目 | 結果 |
|---|---|
| `shell_plus` / `graph_models` / `runserver_plus` / `show_urls` の使用 | コード・スクリプト・runbook・CI とも **0 件** |
| 出現箇所 | `backend/core/settings.py:38` の `'django_extensions',` の 1 行のみ |
| マイグレーションディレクトリ | **不在**（`django_extensions/migrations` が存在しない） |
| DB のテーブル | **0 件**（`pg_tables` に `django_extensions%` の該当なし） |

→ **guardian より安全に削除できる**（guardian は 2 テーブルを残置するが、こちらは残置物が一切ない）。更新は「使っていないものの互換性を検証する」作業であり、無駄の上にリスクが乗る。移動は「使っていないものを置き直す」だけで問題が消えない。**削除が最適**である。

### 2-5. 事前スパイク（ホスト venv・Python 3.12 / 3.11 の両方で実測）

ホスト venv 上の下見であり**テスト合否の根拠にはしない**が（イシュー決定 5）、計画の前提が成立することを実証済みである。

| 検証項目 | 結果 |
|---|---|
| 確定セットの依存解決 | 競合なし（Python 3.12 / 3.11 とも exit 0・解決バージョンは全パッケージ同一） |
| `manage.py check`（guardian あり） | エラー 0・警告 1（guardian.W001） |
| `manage.py check`（guardian を `INSTALLED_APPS` から除去） | **`System check identified no issues (0 silenced).`** |
| `makemigrations --check --dry-run`（guardian 除去済み） | **`No changes detected`** |
| Django 5.x で削除された API の使用 | 0 件（`DEFAULT_FILE_STORAGE` / `STATICFILES_STORAGE` / `get_storage_class` / `index_together` / `USE_L10N` / `timezone.utc` / `make_random_password` / `NullBooleanField` / `force_text`） |
| DRF 3.18.0 の API 互換 | `from rest_framework.views import exception_handler, set_rollback` が健在。`core.exceptions` と全ビューモジュールの import 成功 |
| django-ratelimit 4.1.0 | Django 5.2 で正常に読み込み（`backend/accounts/views.py` の `@ratelimit` 7 箇所を含む） |
| pytest-django 4.14.0 と pytest 8.3.4 の共存 | `Requires-Dist: pytest>=7.0.0`・依存解決 exit 0 ＝ **2 段コミットが成立** |

### 2-6. 環境前提の確認（`plan-writing-rules.md`「環境前提確認」）

| 前提 | 確認方法 | 結果 |
|---|---|---|
| Docker 稼働 | `docker compose ps` | 6 サービス healthy（2026-08-22 起動確認済み） |
| Python バージョン | `backend/Dockerfile:2` / `.github/workflows/ci.yml:17,70` | ともに **3.11**。Django 5.2 の要件（3.10 以上）を満たす。**変更不要** |
| PostgreSQL バージョン | `docker-compose.yml:4` / `.github/workflows/ci.yml:42` | ともに **postgres:15-alpine**。Django 5.2 の要件（14 以上）を満たす。**変更不要** |
| pre-commit の lint ピン | `.pre-commit-config.yaml:19,27` | ruff `v0.15.12` / bandit `1.7.9` で `requirements-dev.txt` と一致。本イシューでは更新しないため**ドリフトなし** |

### 2-7. 推移的依存の現況（イシュー決定 7-C の裏取り）

`requirements.txt` は celery 5.3.4 を固定するが kombu は固定していない。**現在稼働中のコンテナには既に kombu 5.6.2 が入っており**、celery worker はタスクを成功させている。

```
celery-1 | Task studylogs.tasks.update_daily_analytics_task[...] succeeded in 0.0103s: {'updated_count': 0, 'error_count': 0, 'total_users': 0}
celery-1 | Task studylogs.tasks.send_study_reminders_task[...] succeeded in 0.0145s: {'sent_count': 0}
```

→ kombu の浮動は本イシュー**以前から起きており、かつ現時点で正常動作している**。再ビルドで新たに kombu が上がるリスクは相対的に低い。イシュー決定 7-C（触らない・`pip freeze` を記録）を維持する。

### 2-8. 既知の非ブロッキング事項

- `backend/core/storage_service.py:2` の `import imghdr` に `DeprecationWarning`（Python 3.13 で削除予定）。**本イシューでは Python 3.11 のままなので影響なし**。将来の Python 更新時の課題として記録のみ。
- `rest_framework/pagination.py` の `UnorderedObjectListWarning`（`problems.models.Subject` の未ソート QuerySet）。ベースラインで既に出ている警告であり、本イシューの対象外。

---

## 3. 受け入れ条件

イシュー本文の受け入れ条件を、判定可能な形に落とし込んだもの。

| # | 条件 | 判定 |
|---|---|---|
| AC-01 | `backend/requirements.txt` が確定セットに更新され、未使用 2 件が削除されている（`==` 完全固定） | TC-AUTO-11A |
| AC-02 | `django-guardian` と `django-extensions` が `requirements.txt` と `core/settings.py` の双方から削除されている | TC-AUTO-05 |
| AC-03 | コード全体に guardian / django_extensions の参照が残っていない | TC-AUTO-06 |
| AC-04 | `ANONYMOUS_USER_NAME` 等の guardian 専用設定が残っていない | TC-AUTO-07 |
| AC-05 | `manage.py check` が**警告 0** で終了する | TC-AUTO-04 |
| AC-06 | まっさらな DB に対する `migrate` が最後まで通る（使い捨て DB 方式） | TC-AUTO-09 |
| AC-07 | マイグレーション drift がない | TC-AUTO-08 |
| AC-08 | `pip-audit -r requirements.txt` が exit 0 | TC-AUTO-01 |
| AC-09 | `pip-audit -r requirements-dev.txt` が exit 0（手元実行の記録。`ci.yml` は変更しない） | TC-AUTO-02 |
| AC-10 | `backend/requirements-dev.txt` が `pytest-django==4.14.0` ＋ `pytest==9.0.3` | TC-AUTO-11A（pytest-django）／TC-AUTO-11B（pytest） |
| AC-11 | backend テストが **94 件 pass**（ベースラインと同数・skip / 削除 / 条件緩和なし） | TC-AUTO-03 |
| AC-12 | frontend テストが **10 件 pass**（無退行） | TC-AUTO-12 |
| AC-13 | E2E（Playwright）が全件 pass | TC-AUTO-13 |
| AC-14 | CI の全 6 チェックが SUCCESS | TC-AUTO-14 |
| AC-15 | celery worker のログでタスクの**成功**が確認できる | TC-AUTO-10 |
| AC-16 | 再ビルド後の `pip freeze` をテスト記録に残している | TC-AUTO-15 |
| AC-17 | コミットが 2 段に分かれている | TC-AUTO-16 |
| AC-18 | 認可・テナント境界テストのモジュール名を列挙し、前後の件数を記録している | 手動 No.6 |
| AC-19 | 後続 3 件を起票している | 手動 No.8 |
| AC-20 | develop マージ後に #262 をクローズしている | `/close` 工程（本 PR の範囲外） |

---

## 4. 影響範囲

| 区分 | 対象 | 内容 |
|---|---|---|
| Backend（変更） | `backend/requirements.txt` | 5 パッケージのバージョン更新＋`django-guardian` / `django-extensions` の 2 行削除 |
| Backend（変更） | `backend/requirements-dev.txt` | `pytest-django` 4.9.0→4.14.0（1 段目）／`pytest` 8.3.4→9.0.3（2 段目） |
| Backend（変更） | `backend/core/settings.py` | `THIRD_PARTY_APPS` から `'django_extensions',`（38 行目）と `'guardian',`（41 行目）の**2 行**を削除 |
| Backend（変更なし・検証対象） | `backend/accounts/views.py` | `@ratelimit` を 7 箇所で使用。django-ratelimit の Django 5.2 互換の影響を最も受ける |
| Backend（変更なし・検証対象） | `backend/core/exceptions.py` | DRF の `exception_handler` / `set_rollback` を使用。DRF 3.18 の API 互換の影響を受ける |
| Backend（変更なし・検証対象） | `backend/core/celery.py` / `backend/core/tasks.py` / `backend/studylogs/tasks.py` | worker / beat が backend と同じイメージから作られるため再ビルドの影響を受ける |
| Backend（変更なし） | `backend/pytest.ini` | `--no-migrations` は意図的な高速化設定。維持する |
| Frontend | なし | API 契約は変わらない。無退行のみ確認（TC-AUTO-12 / TC-AUTO-13） |
| DB | マイグレーション新規生成なし（事前実測で `No changes detected`）。**`guardian_*` の 2 テーブルは残置**（削除は別イシュー）。django-extensions はテーブルを持たないため残置物なし。スキーマの破壊的変更なし |
| Config/Infra | `backend/Dockerfile` は**変更なし**（Python 3.11 のままで要件充足）。ただし `requirements.txt` 変更に伴い **イメージ再ビルドが必須**。`docker-compose.yml` の `backend` / `celery` / `celery-beat` / `e2e-init` が同じ Dockerfile（`target: dev`）を参照するため、**再ビルドは 4 サービスすべてに波及する** |
| CI | `.github/workflows/ci.yml` / `.github/workflows/e2e.yml` とも**変更しない**。ただし `ci.yml:27`（pip-audit）と `ci.yml:29-35`（migration drift）、`e2e.yml:17,25`（まっさらな DB への migrate）が本変更の判定に関わる |

---

## 5. 変更点一覧

### 5-1. `backend/requirements.txt`

| 行 | 現在 | 変更後 | 理由 |
|---|---|---|---|
| 1 | `Django==4.2.30` | `Django==5.2.17` | 7 件すべての Fix Versions を満たす 5.2 系最新（`PYSEC-2026-3717` の修正が 5.2.17） |
| 2 | `djangorestframework==3.15.2` | `djangorestframework==3.18.0` | 3.15 は 5.2 非対応（宣言は 5.0 まで） |
| 4 | `django-cors-headers==4.3.1` | `django-cors-headers==4.9.0` | 4.3.1 の宣言は 5.0 まで |
| 7 | `django-extensions==3.2.3` | **行ごと削除** | 未使用（§2-4b）。更新せず除去する |
| 8 | `django-filter==23.4` | `django-filter==26.1` | 23.4 の宣言は 5.0 まで |
| 12 | `django-redis==5.4.0` | `django-redis==7.0.0` | 5.4.0 の宣言は 4.2 まで |
| 14 | `django-guardian==2.4.0` | **行ごと削除** | 未使用（§2-4）。更新せず除去する |

据え置き: `djangorestframework-simplejwt==5.5.1` / `psycopg2-binary==2.9.9` / `python-dotenv==1.2.2` / `Pillow==12.3.0` / `celery==5.3.4` / `redis==5.0.1` / `django-ratelimit==4.1.0` / `sendgrid==6.10.0` / `pydantic==2.5.0` / `openai==1.3.0` / `gunicorn==22.0.0` / `psutil==5.9.6` / `python-magic==0.4.27`

### 5-2. `backend/requirements-dev.txt`

| 行 | 現在 | 変更後 | コミット |
|---|---|---|---|
| 5 | `pytest-django==4.9.0` | `pytest-django==4.14.0` | **1 段目**（Django 5.2 対応に必須） |
| 4 | `pytest==8.3.4` | `pytest==9.0.3` | **2 段目**（PYSEC-2026-1845 の解消・唯一の任意変更） |

据え置き: `ruff==0.15.12` / `bandit==1.7.9` / `pip-audit==2.10.0`

### 5-3. `backend/core/settings.py`

```python
# 変更前（34-42 行目）
THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',  # logout での refresh トークン失効に必要（I142）
    'corsheaders',
    'django_extensions',     # <- 削除（未使用・§2-4b）
    'django_filters',
    'guardian',              # <- 削除（未使用・§2-4）
]

# 変更後
THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',  # logout での refresh トークン失効に必要（I142）
    'corsheaders',
    'django_filters',
]
```

**修正アプローチ**: `INSTALLED_APPS` から未使用アプリ 2 件を外すだけで、認証・認可の設定（`AUTHENTICATION_BACKENDS`・`REST_FRAMEWORK` の権限クラス）には一切触れない。guardian は認証バックエンドに登録されていないため、削除しても認可の判定経路は変わらない。DB のテーブルは残置するため、データ損失も起きない。

---

## 6. 実装手順

**未知リスク先行原則の適用**: 本イシューで最も不確かなのは「更新後のイメージで既存テストが通るか」である。したがって**ステップ 1 で requirements の更新・再ビルド・全テスト実行までを一気に通す**。ここで失敗すれば以降のステップに進まない。

**依存関係**: ステップ 1 → 2 → 3 は順次実行（並行不可）。ステップ 4・5 はステップ 3 の完了後。

### ステップ 0: 事前確認（実装開始前のゲート）
- ベースライン（94 件 pass / 10 件 pass / pip-audit 7 件）は §2-1 に記録済み。
- Docker が稼働していること・6 サービスが healthy であることを確認する → TC-AUTO-00 参照。

### ステップ 1: 本体依存と guardian 削除（コミット 1）
1. `backend/requirements.txt` を §5-1 のとおり更新する（5 行の書き換え＋`django-guardian` / `django-extensions` の 2 行削除）。
2. `backend/requirements-dev.txt` の `pytest-django` を `4.14.0` に更新する（§5-2）。
3. `backend/core/settings.py` の `THIRD_PARTY_APPS` から `'django_extensions',` と `'guardian',` の 2 行を削除する（§5-3）。
4. backend イメージを再ビルドし、`backend` / `celery` / `celery-beat` を作り直す（`docker compose build backend celery celery-beat` → `docker compose up -d --wait`）。
5. 検証 → TC-AUTO-01 / 03 / 04 / 05 / 06 / 07 / 08 / 09 / 10 / 11A / 12 参照。**TC-AUTO-11B（pytest の固定値）はこの時点では対象外**（pytest は 8.3.4 のままが正しいため）。
6. すべて合格したら実装コミットとして記録する。
   - コミットメッセージ: `fix(I151): Django 5.2.17 へ更新し依存を対応版へ一括更新・未使用の django-guardian / django-extensions を削除`
   - 対象: `backend/requirements.txt` / `backend/requirements-dev.txt` / `backend/core/settings.py`

> **このステップが失敗した場合**: 計画をやり直す。テストの skip・削除・条件緩和による緑化は行わない（イシュー Danger Ops の承認条件）。

### ステップ 2: pytest 9 への更新（コミット 2）
1. `backend/requirements-dev.txt` の `pytest` を `9.0.3` に更新する。
2. backend イメージを再ビルドし、`backend` を作り直す。
3. 検証 → TC-AUTO-02 / 03 / 11B / 12 参照。
4. 合格したらコミットする。
   - コミットメッセージ: `chore(I151): pytest 9.0.3 へ更新（PYSEC-2026-1845 の解消）`
   - 対象: `backend/requirements-dev.txt`

> **このステップが失敗した場合**: **2 段目の変更のみを取り消す**（コミット前なら `backend/requirements-dev.txt` の `pytest` を 8.3.4 へ戻す。コミット後なら当該コミットを revert する）。ステップ 1 の成果は保持される。その場合は pytest の脆弱性解消を別イシューへ送り、受け入れ条件 AC-09 / AC-10 を「pytest は据え置き」に読み替える旨をレビュー記録に明記する。

### ステップ 3: CI での検証
1. Draft PR #269 に 2 コミットを push する。
2. CI の全 6 チェックの結果を確認する → TC-AUTO-13 / TC-AUTO-14 参照。
3. `pip freeze` の出力をテスト記録へ残す → TC-AUTO-15 参照。
4. コミットが 2 段に分かれていることを確認する → TC-AUTO-16 参照。

### ステップ 4: 後続イシューの起票
イシュー決定 2 / 7-C / 7-D に基づき 3 件を起票する（タイトル案はイシュー本文に記載済み）→ 手動テスト No.8 参照。**django-extensions の依存移動イシューは決定 7 の変更により不要になった**。

### ステップ 5: 記録の完成
`docs/tests/open/I151_auto_test.md` / `I151_manual_test.md` に結果を記入し、認可・テナント境界テストのモジュール名と前後の件数を記録する → 手動テスト No.6 参照。

---

## 7. テスト計画

### テストレベルの選択
| レベル | 対象 | 理由 |
|---|---|---|
| 静的検証（決定論 TC） | 依存の固定値・guardian 残存・設定 | 「存在しない」ことの検証は grep の exit code でしか決定論的に判定できない |
| ツール実行 | `pip-audit` / `manage.py check` / `makemigrations --check` / `migrate` | 受け入れ条件がツールの exit code で定義されている |
| 単体・API 結合 | 既存 backend テスト 94 件 | **新規テストは追加しない**（イシュー決定 6）。依存更新の影響は「既存テストが同じ結果を返すか」で測る |
| コンポーネント | 既存 frontend Jest 10 件 | 無退行の確認 |
| E2E | 既存 Playwright 一式 | まっさらな DB への `migrate` とログイン〜主要画面の通しを同時に担保する |

### 再発防止テストの要否
本イシューは**バグ修正ではなく依存更新**のため、新しい振る舞いに対する再発防止テストは追加しない。ただし「EOL 依存への逆戻り」を防ぐ決定論 TC（TC-AUTO-11A / 11B: 固定値の一致確認）を置く。

### 認可・テナント境界の検証（AC-18）
新規テストは追加せず、既存の以下のモジュールが更新後も同じ結果を返すことを記録する。

- `backend/problems/tests/test_I103_cross_org_create.py`（組織越境の作成拒否）
- `backend/problems/tests/test_I104_subject_authz.py`（教科の認可）
- `backend/problems/tests/test_I006_subject_org_admin.py`（組織管理者の権限範囲）
- `backend/problems/tests/test_I078_is_correct_exposure.py`（解答の露出制御）
- `backend/accounts/tests/test_I131_org_id_rename.py`（登録と組織割当）
- `backend/accounts/tests/test_I140_personal_org_fallback.py`（personal 組織フォールバック廃止）
- `backend/core/tests/test_I127_throttling.py`（レート制限＝django-ratelimit / DRF throttle）

### false-green 防止
否定・不在を判定する TC（TC-AUTO-05 / 06 / 07）は、失敗条件を注入して実際に非ゼロ終了することを確認してから採用する（手順は auto_test 文書に記載）。

---

## 8. ロールバック

| 段階 | 手順 |
|---|---|
| ステップ 2 で失敗 | 2 段目の変更のみを取り消す。`requirements-dev.txt` の `pytest` が 8.3.4 に戻り、ステップ 1 の成果は保持される。**取り消し後は必ず再ビルドする**（ファイルを戻してもイメージには pytest 9 が残るため、宣言と実インストールが食い違う） |
| ステップ 1 で失敗 | `backend/requirements.txt` / `backend/requirements-dev.txt` / `backend/core/settings.py` を更新前の内容へ戻し、backend / celery / celery-beat を再ビルドする |
| develop マージ後に判明 | revert PR で戻す。`guardian_*` テーブルは残置しているため、guardian を戻す場合も `INSTALLED_APPS` と依存の復元のみで足りる（データ復旧は不要） |
| DB | マイグレーションを新規生成しないため、DB のロールバックは不要。検証用の使い捨て DB（`migrate_check`）は検証後に破棄する |

---

## 9. Risk & 回避策

| # | リスク | 影響 | 回避策 |
|---|---|---|---|
| R1 | DRF 3.15 → 3.18 でシリアライザ・権限の挙動が変わる | 認可・エラー応答の退行 | 事前スパイクで `core/exceptions.py` と全ビューの import 互換を確認済み。実測は既存 94 件＋認可モジュール群（§7）で担保 |
| R2 | guardian を外すと `migrate` が失敗する | 全テストが落ちる／E2E が落ちる | 使い捨て DB での `migrate`（TC-AUTO-09）＋ drift チェック（TC-AUTO-08）＋ CI の E2E（TC-AUTO-13）の 3 経路で確認 |
| R3 | pytest 9 のメジャー更新でテスト基盤が壊れる | テストが落ちる | 2 段目のコミットに隔離。取り消せば 1 段目の成果は残る |
| R4 | 再ビルドで推移的依存（kombu 等）が変動し celery が壊れる | 非同期タスクの失敗 | worker ログでタスクの**成功**まで確認（TC-AUTO-10）。`pip freeze` を記録して誤帰属を防ぐ（TC-AUTO-15）。現況では kombu 5.6.2 で既に正常動作（§2-7） |
| R5 | 再ビルド対象の取りこぼし（celery / celery-beat が旧イメージのまま） | 本番相当構成での検証にならない | ビルド対象に `celery` `celery-beat` を明示（ステップ 1-4）。`e2e-init` は E2E 実行時に再ビルドされる |
| R6 | 新しい CVE が実装中に公開され `pip-audit` が再び落ちる | CI が赤のまま | 計画時点で 7 件へ増えた実績あり（§2-2）。発生時は Fix Versions を確認し 5.2 系の最新パッチへ再固定する（系列変更を伴わないため影響は局所） |
| R7 | ホスト venv の実測を合否根拠にしてしまう | 本番構成と異なる結論 | すべての TC を `docker compose exec` 経由で実行する。ホスト venv の結果は「下見」としてのみ記載 |

---

## 10. データ整合性設計（DB 変更があるため記載）

- **DB 制約の変更**: なし。モデル定義に変更がないため、NOT NULL / UNIQUE / FK / CHECK のいずれも変わらない。
- **マイグレーション**: 新規生成なし（事前実測で `No changes detected`・実装時に TC-AUTO-08 で再確認）。
- **`INSTALLED_APPS` からのアプリ除去の扱い**: guardian を外しても Django は既存テーブルに触れない。`django_migrations` テーブルに残る guardian の適用履歴も削除されないが、参照されなくなるだけで整合性に影響しない。
- **孤立テーブル**: `guardian_userobjectpermission` / `guardian_groupobjectpermission` の 2 テーブルが未参照のまま残る。**本イシューでは意図的に残置**し、除去は別イシュー（バックアップ取得のうえ実施）とする。
- **トランザクション境界・冪等性・同時更新**: 本変更はスキーマにもデータにも触れないため該当なし。
- **後方互換性**: guardian を戻す場合も `INSTALLED_APPS` と依存の復元のみで足り、テーブルが残っているためデータ復旧は不要。

---

## 11. 運用設計（非同期処理があるため記載）

- **構造化ログ方針**: 変更なし。`core/enhanced_logging.py` / `core/middleware.py` のログ出力に手を入れない。I142 で整備したエラーハンドリング規約（`custom_exception_handler` によるログ＋統一 JSON 500）も変更しない。
- **celery の検証方針**: worker と beat を再ビルド後に起動し、beat がスケジュールしたタスクが**成功**するまでをログで確認する（TC-AUTO-10）。`update_daily_analytics_task` は 30 秒間隔のため 1 分以内に判定できる。
- **タイムアウト・リトライ**: 変更なし（`studylogs/tasks.py` の `max_retries=3` 等はそのまま）。
- **Feature Flag・段階リリース**: 不要。依存更新は全体一括で適用され、部分的に有効化する意味がない。切り戻しは §8 のとおりコミット単位・revert PR で行う。
- **beat スケジュールの環境別切り替え**: `backend/core/celery.py` が開発用の短間隔で固定されている件は**本イシューの範囲外**（イシュー決定 7-D・別イシューで対応）。

---

## 12. コスト・保守見積もり

**P8 影響なし。** 新規インフラリソース・外部サービスの追加はない。既存パッケージのバージョン更新と 2 パッケージの除去のみで、むしろ依存が 2 つ減るため保守対象は縮小する。

---

## 13. 性能・UX 設計

**P6 影響なし。** フロントエンドのコード変更はなく、API 契約も変わらない。ローディング・空状態・エラー状態の表示、破壊的操作の確認導線、N+1・キャッシュ・ページネーションのいずれにも変更がない。無退行は TC-AUTO-12（Jest）と TC-AUTO-13（E2E）で確認する。

---

## 14. 学習効果設計

**該当なし。** 学習機能・学習データ・学習体験のロジックに変更がない。

---

## 15. プライバシー・コンプライアンス設計

**P9 影響なし。** 個人情報・未成年データ・テナントデータの取り扱いを変更しない。認可の判定経路にも変更がない（guardian は元から認証バックエンドに未登録）。高リスク判定（I043）には該当しないが、**認可ライブラリの依存を除去する変更を含むため、実装後に `/security-review` を実施する**（承認ポイント S-4）。

---

## 16. セキュリティチェック（必須項目への回答）

| 観点 | 回答 |
|---|---|
| 入力バリデーション・サニタイズ | 変更なし（シリアライザ・バリデータに手を入れない） |
| 認証・認可の変更 | **判定ロジックの変更なし**。guardian は `AUTHENTICATION_BACKENDS` に未登録のため、除去しても最小権限の設計は変わらない。django-extensions は認可に関与しない。`REST_FRAMEWORK` の権限クラス設定にも触れない |
| 機密データの扱い | 変更なし。本 PR で新たにログ出力・保存する機密データはない |
| OWASP Top 10 | **A06（脆弱で古くなったコンポーネント）を直接是正するのが本イシューの目的**。XSS / SQLi / CSRF に関わるコード変更はない。Django 5.2 へ上げることで 7 件の既知脆弱性が解消する |
| フレームワーク推奨パターン | Django のセキュリティ設定（`SecurityHeadersMiddleware` 等）に変更なし。サポート対象系列を使うこと自体が推奨パターンへの回帰 |
| 依存ライブラリの既知脆弱性 | `pip-audit` で本体・開発の双方が **0 件**であることを計画時点で実測済み（§2-3） |
| スキャンツールの重大度基準 | **bandit: MEDIUM 以上を修正対象・LOW は `# nosec` で抑制／npm audit: high・critical を修正対象**。本 PR の Python コード変更は `settings.py` の 2 行削除のみのため新規検出は想定しない |

---

## 17. 設計判断の明示

| # | 設計判断 | 根拠 |
|---|---|---|
| D-1 | Django を 5.2.17 に固定する | **イシューに明記**（決定 3）。計画時の再実測で 5.2.16 では新 CVE を解消できないことも判明（§2-2） |
| D-2 | django-guardian を更新せず除去する | **イシューに明記**（決定 1） |
| D-2b | django-extensions を更新せず除去する | **イシューに明記**（決定 7・2026-08-22 に「4.1 へ更新」から変更） |
| D-3 | `guardian_*` テーブルは残置する | **イシューに明記**（決定 2） |
| D-4 | 依存は最新一括・`==` 完全固定 | **イシューに明記**（決定 3） |
| D-5 | `requirements-dev.txt` を 2 段コミットに分ける（1 段目に pytest-django） | **イシューに明記**（決定 4） |
| D-6 | `ci.yml` を変更しない | **イシューに明記**（決定 4） |
| D-7 | 検証は Docker・代替は draft PR 経由の CI | **イシューに明記**（決定 5） |
| D-8 | 新規テストを追加しない | **イシューに明記**（決定 6） |
| D-9 | まっさらな DB の検証は使い捨て DB 方式 | **イシューに明記**（決定 7-A） |
| D-10 | celery はログでタスク成功まで確認 | **イシューに明記**（決定 7-B） |
| D-11 | kombu を固定せず `pip freeze` を記録 | **イシューに明記**（決定 7-C） |
| D-12 | ブランチ名を `feature/I151-django-52-lts-upgrade` とする | **仮定で決めた**（命名規則に沿った機械的な決定） |
| D-13 | 再ビルド対象に `celery` / `celery-beat` を明示する | **仮定で決めた**（`docker-compose.yml` が同一 Dockerfile を参照することから導出。イシューは backend のみ記載） |
| D-14 | ベースラインを 94 件とする（イシュー本文の 110 件は I142 ブランチの値） | **仮定で決めた**（実測に基づく読み替え） |
| D-15 | コミットメッセージの文言 | **仮定で決めた**（既存コミットの慣習に合わせた） |

---

## 18. 承認ポイント

### A. 更新するバージョンの組み合わせ（Danger Ops の承認条件）
- [ ] `requirements.txt`: Django 5.2.17 / DRF 3.18.0 / django-cors-headers 4.9.0 / django-filter 26.1 / django-redis 7.0.0。**`django-guardian` と `django-extensions` は行ごと削除**（いずれも未使用）
- [ ] `requirements-dev.txt`: pytest-django 4.14.0（1 段目）／pytest 9.0.3（2 段目）
- [ ] 上記以外のパッケージは据え置き（celery 5.3.4 を含む）

### B. 計画時に判明した差分（イシューとの読み替え）
- [ ] **脆弱性の件数はタイトル・受け入れ条件に固定しない**（2026-08-22 決定）。起票時 6 件 → 再実測 7 件と 1 週間で変動しており、直しても必ず古くなる。イシューのタイトルから件数を外し、**日付付きの実測値として本文に残す**形に変更済み。新規 `PYSEC-2026-3717` の修正版は 5.2.17 で、既に決めていたバージョンで解消できる（方針変更は不要）
- [ ] **テスト件数もイシューには固定しない**（2026-08-22 決定）。イシューの受け入れ条件は「実装直前に計測したベースラインと同数」という不変条件に変更し、**実測値 94 件は本計画書と自動テスト文書（TC-AUTO-03）に固定**して決定論を保つ。イシュー本文の 110 件は I142 ブランチの値だった

### C. 仮定で決めた事項（D-12 〜 D-15）
- [ ] **django-extensions を「4.1 へ更新」から「削除」へ変更**（2026-08-22 決定・§2-4b の実測に基づく）。当初の「本番イメージに入っている開発ツール」という前提が誤りで、実際は未使用だった。これにより後続イシューが 1 件不要になる
- [ ] ブランチ名 `feature/I151-django-52-lts-upgrade`（作成・push・Draft PR #269 まで実施済み）
- [ ] **再ビルド対象を `backend` だけでなく `celery` / `celery-beat` にも広げる**（同一 Dockerfile を参照するため。イシューは backend のみ記載）
- [ ] コミットメッセージの文言（`fix(I151): ...` / `chore(I151): ...`）

### S. セキュリティ・業務ロジック確認
- [ ] **S-1 認可の判定経路は変更しない**。guardian は `AUTHENTICATION_BACKENDS` に未登録のため、除去しても最小権限の設計に影響しない。django-extensions は認可に一切関与しない
- [ ] **S-2 マルチテナントの閲覧・操作範囲は変更しない**。組織スコープの絞り込みは自前実装であり guardian に依存していない。無退行は §7 の認可・テナント境界モジュール群で確認する
- [ ] **S-3 依存の既知脆弱性はゼロ**であることを計画時点で実測済み（本体・開発とも exit 0）
- [ ] **S-4 実装後に `/security-review` を実施する**（認可ライブラリの依存除去を含むため）
- [ ] **S-5 bandit は MEDIUM 以上を修正対象・LOW は `# nosec`／npm audit は high・critical を修正対象**という基準で運用する

### T. テスト計画確認
- [ ] **新規テストは追加しない**（イシュー決定 6）。依存更新の影響は既存 94 件＋認可モジュール群の結果一致で測る
- [ ] 否定系 TC（TC-AUTO-05 / 06 / 07）は失敗条件を注入して非ゼロ終了することを確認してから採用する
- [ ] **テストの skip・削除・条件緩和による緑化は行わない**

### P. 条件付きセクションの適用
- [ ] P3（データ整合性設計）: **記載あり**（§10）
- [ ] P5（運用設計）: **記載あり**（§11）
- [ ] P8（コスト・保守見積もり）: **影響なし**（§12）
- [ ] P6（性能・UX 設計）: **影響なし**（§13）
- [ ] P9（プライバシー・コンプライアンス）: **影響なし**（§15）

## レビュー結果
- [20260823_1344 判定: ✅ 完了](../../reviews/I151_plan_review_20260823_1344.md)
- [20260822_1809 判定: ✅ 完了](../../reviews/I151_plan_review_20260822_1809.md)
