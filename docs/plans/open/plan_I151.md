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
| **django-redis 7.0.0（メジャー 2 段更新）** | **稼働中の Redis に対して実際に読み書きして検証済み**（2026-08-23）。`settings.py` の `CACHES` が使う API がすべて 7.0.0 に存在し、4 つのキャッシュ（`default` / `sessions` / `problems` / `analytics`）すべてで set → get → delete が成功した。確認した API: `django_redis.cache.RedisCache` / `django_redis.client.DefaultClient` / `django_redis.compressors.zlib.ZlibCompressor`、および `CONNECTION_POOL_KWARGS`（`max_connections=50` / `retry_on_timeout=True`）と `IGNORE_EXCEPTIONS=True` の受理 |
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
- **celery の `core.tasks` が未登録（2026-10-16・`/test` で判明。I004＝2026-03-20 からの既存不具合）**: `core/celery.py:52` の beat が 30 分ごとに `core.tasks.cache_maintenance_task` を送るが、`core` が `INSTALLED_APPS` に無いため worker が登録しておらず、届くたびに `Received unregistered task` の ERROR と Traceback を出して捨てている。試しに直接実行すると、中で呼ぶ `cache_service.get_cache_stats()` は `_cache` 不在で失敗し、処理は空振りする。I151 の差分（`settings.py` の 2 行削除）とは無関係で、celery の版も据え置き。**本イシューでは直さず、別イシューで根治する**（登録方式と、空振りしているタスクを残すか消すかの設計判断を伴うため。診断は `docs/reviews/I151_fix_diagnosis_20261016_1740.md`）。TC-AUTO-10 ではこの 1 種だけを暫定で除外する（§11 の celery 検証方針を参照）。AC-15（イシュー決定 7-B「成功まで確かめる」）は、beat スケジュール 5 件のうち、この既知の 1 件を除く 4 件の成功で判定する（2026-10-16 の解釈。I151 では直さない既存不具合のため）。
  - **更新前と同じであることの実測（2026-10-16）**: `origin/develop` の `backend/` と更新前の requirements（Django 4.2.30）で使い捨てイメージを作り、worker と同じ手順でタスクを読み込んで、更新後（Django 5.2.17）と比べた。登録済みタスクの一覧は完全に一致し、スケジュールにあって未登録なのは、どちらも `core.tasks.cache_maintenance_task` の 1 件だけだった。この 1 件は、依存更新で生じたものではないことが実測で確かめられた。
  - **「条件緩和しない」の例外としての承認（2026-10-16）**: TC-AUTO-10 の判定 2a・2b で、この 1 件だけを除外するのは、旧判定 2 より合否基準を緩める変更である。fix-loop で案 A を承認いただいた時点では、私（Claude）が「判定は厳しくなる」と誤って説明していた。そのため、敵対的レビューの指摘を受けて、改めて判断を仰いだ。ユーザーの回答は「理想的・最適なものを基準として問題ないなら OK」（条件付きの承認）。理想の基準で見ると、除外の根拠がコードを読んだだけで実測ではない点と、確認スクリプトが実メールを送りうる点が不十分だった。そこで、更新前の実測（上記）と、確認スクリプトが足す 1 回分のメール送信の停止を加えた。条件を満たしたかの判定は Claude が行い、その後の敵対的レビュー（`I151_adversarial_review_20261016_1100.md` とその後の再レビュー）で検証したうえで、例外として適用した。除外は根治イシューのマージまでの暫定である（TC-AUTO-10 本文）
  - **確認スクリプトの副作用（Danger Ops の扱い）**: `docs/tests/open/I151_celery_probe.py` は、beat が定期実行するのと同じ 4 タスクを 1 回ずつ余分に実行する（期限切れ提案の無効化など）。外部送信を伴う `send_study_reminders_task` は、スクリプトが足す 1 回分だけ、メールを locmem に溜める設定で実行し、実際には送らない。開発環境（手元の compose）専用で、CI・本番相当の環境では実行しない（`settings.DEBUG` が False なら実行せずに終わる）
  - **開発環境の常設設定による実メールの危険（2026-10-16・敵対的レビュー第 3 周で判明。I151 の範囲外の既存の問題）**: beat は `send_study_reminders_task` を 60 秒ごとに worker へ送り、worker の `EMAIL_BACKEND` は SMTP（SendGrid のキーあり）で固定されている。復習カードがある状態で celery が動いていると、24 時間学習していない有効ユーザー（実在とみられる gmail.com のアドレスを含む）に、1 分ごとにメールが送られうる。いま送信されないのは、復習カードが 0 件で、さらに下の既存不具合で送信処理が必ず失敗するためである。TC-AUTO-10 と手動テストでは、復習カードを作る操作の直後に celery を動かさない。根治（開発環境では明示しない限り送信しない設定）は、I151 の完了後に起票するイシューで行う
  - **`send_study_reminders_task` の送信処理が必ず失敗する（同・既存不具合）**: 送信処理が呼ぶ `User.get_full_name` が、カスタムの `User(AbstractBaseUser, PermissionsMixin)` に存在しないので、復習カードを持つユーザーごとに AttributeError になり、`send_mail` まで届かない（Django 2.0 以降ずっと同じで、I151 による退行ではない）。tasks を参照するテストは 0 件で、この経路を確かめるテストは無い。I151 の完了後に起票するイシューの候補とする

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
| AC-15 | celery worker のログでタスクの**成功**が確認できる（2026-10-16 の解釈: beat スケジュール 5 件のうち、更新前から未登録の既知 1 件を除く 4 件の成功を、ログと実際の実行結果で確認する。§2-8） | TC-AUTO-10 |
| AC-16 | 再ビルド後の `pip freeze` を `docs/tests/open/I151_pip_freeze.txt` に記録している | TC-AUTO-15 |
| AC-17 | コミットが 2 段に分かれている（2026-10-14 追補: R6 発動による openai 再固定は、変更の出どころを追えるよう 3 つ目の `fix(I151)` コミットに分ける。2026-10-15 訂正: このコミットだけを取り消すと openai 1.3.0（`anyio<4`）に戻り、anyio の CVE 2 件で必須チェック `pip-audit` が必ず落ちる。したがって**単独では取り消せない**。問題が出たときは §8 の前方修正で直す） | TC-AUTO-16 |
| AC-18 | 認可・テナント境界テストのモジュール名を列挙し、前後の件数を記録している | 手動 No.6 |
| AC-19 | 後続 3 件を起票している。2026-10-16 追補: 4 件目（celery `core.tasks` 未登録の根治）は、I151 の完了後に起票する（ユーザー指示）。I151 の完了までに満たすのは「4 件目のタイトル・受け入れ条件・実施順の制約が確定し、記録されている」こと（ステップ 4・手動テストの後続イシュー欄・I150 / I157 への注記） | 手動 No.8 |
| AC-20 | develop マージ後に #262 をクローズしている | `/close` 工程（本 PR の範囲外） |
| AC-21 | レート制限のカウンタ保存が再ビルド後の実コンテナで機能する（security-review 由来） | TC-AUTO-17 |
| AC-22 | psycopg2-binary の 5.2 環境での動作がテスト実走で確定している（イシュー受け入れ条件・2026-10-14 追補） | TC-AUTO-03（94 件が Docker の postgres:15 へ実接続して pass） |
| AC-23 | テスト記録に「マイグレーション検証は (a) ローカルの使い捨て DB と (b) CI の E2E ジョブの 2 経路で担保」と明記している（イシュー受け入れ条件・2026-10-14 追補） | `I151_manual_test.md`「マイグレーション検証の担保経路」欄 |

> **追補の経緯（2026-10-14・敵対的レビュー第 1 周）**: イシュー本文の受け入れ条件のうち AC-22 / AC-23 の 2 件が、本表に割り当てられていなかった（作業自体は完了済み）。あわせて、過去のコードレビュー記録は本表と異なる番号体系を使っているため、対応を下表に示す。**正となる番号は本表**とする。
>
> | 本表 | `I151_code_review_20260824_0126.md` | `I151_code_review_20261007_1356.md` | `I151_code_review_20261014_1548.md` |
> |---|---|---|---|
> | AC-01〜AC-11 | 同番号 | 同番号 | 同番号 |
> | AC-12（frontend テスト） | 行なし（未照合） | AC-12 | AC-12 |
> | AC-13（E2E） | AC-12 | AC-13 | AC-13 |
> | AC-14（CI 6 チェック） | AC-13 | AC-14 | AC-14 |
> | AC-15（celery 成功） | AC-14 | AC-15 | AC-15 |
> | AC-16（pip freeze） | AC-16 | AC-17 | AC-16 |
> | AC-17（2 段コミット） | AC-19 | AC-20-commit | AC-17 |
> | AC-18（認可モジュール記録） | AC-20 | AC-21 | AC-18 |
> | AC-19（後続 3 件起票） | AC-21 | AC-22 | AC-19 |
> | AC-20（#262 クローズ） | AC-22 | AC-23 | AC-20 |
> | AC-21（レート制限） | AC-23 | AC-24 | AC-21 |
> | AC-22（psycopg2） | AC-15 | AC-16 | 行なし（未照合） |
> | AC-23（マイグレーション 2 経路の明記） | AC-17 | AC-18 | 行なし（未照合） |
> | （本表に無し・AC-07 と同内容） | AC-18（マイグレーション新規生成の有無） | AC-19（同） | — |
> | （本表に無し・手動 No.7） | — | AC-25（ブラウザ UI 確認） | — |

---

## 4. 影響範囲

| 区分 | 対象 | 内容 |
|---|---|---|
| Backend（変更） | `backend/requirements.txt` | 6 パッケージのバージョン更新（2026-10-14 の R6 で openai を追加し 5→6）＋`django-guardian` / `django-extensions` の 2 行削除 |
| Backend（変更） | `backend/requirements-dev.txt` | `pytest-django` 4.9.0→4.14.0（1 段目）／`pytest` 8.3.4→9.0.3（2 段目） |
| 記録（新規） | `docs/tests/open/I151_pip_freeze.txt` | 再ビルド後の `pip freeze` の出力。推移的依存が変動した際の切り分け材料（TC-AUTO-15 の判定対象） |
| Backend（変更） | `backend/core/settings.py` | `THIRD_PARTY_APPS` から `'django_extensions',`（38 行目）と `'guardian',`（40 行目）の**2 行**を削除 |
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
| 17（develop 版の行番号。2026-10-14 追補・R6 発動。2026-10-15 に 15→17 へ訂正） | `openai==1.3.0` | `openai==3.31.0` | 推移的依存 `anyio 3.7.1` に新規 CVE 2 件（`PYSEC-2026-4024` / `PYSEC-2026-4025`・修正版 4.14.2）が公開された。`openai 1.3.0` は `anyio<4` を要求するため、anyio だけを上げることはできない。openai 3.31.0 は `anyio>=4.10,<5` を要求する（§5-1 追補） |

据え置き: `djangorestframework-simplejwt==5.5.1` / `psycopg2-binary==2.9.9` / `python-dotenv==1.2.2` / `Pillow==12.3.0` / `celery==5.3.4` / `redis==5.0.1` / `django-ratelimit==4.1.0` / `sendgrid==6.10.0` / `pydantic==2.5.0` / `gunicorn==22.0.0` / `psutil==5.9.6` / `python-magic==0.4.27`（`openai` は 2026-10-14 に据え置きから外した）

### 5-1 追補（2026-10-14）: 実装後に公開された新規 CVE（R6 発動）

fix-loop の手順 6 で `pip-audit -r requirements.txt` を再実行したところ、exit 1 になった（`anyio 3.7.1` に `PYSEC-2026-4024` / `PYSEC-2026-4025`、修正版 4.14.2）。develop の定期監査も 2026-10-10 以降、毎日失敗している。

| 確認項目 | 結果（2026-10-14・Docker 実測） |
|---|---|
| anyio を要求しているもの | `openai==1.3.0`（`anyio<4,>=3.5.0`）と `httpx 0.28.1`。直接固定している依存は無い |
| 解消方法 | openai を anyio 4 系を許す版へ上げる。`openai==3.31.0`（最新・`anyio<5,>=4.10.0`・`pydantic>=1.10.13,<3` で 2.5.0 と両立・Python 3.10 以上）。anyio は推移的依存として 4 系の最新が解決される |
| 候補セットの監査 | `requirements.txt` の openai 行だけを 3.31.0 に変えた候補で `pip-audit -r` → **`No known vulnerabilities found`** |
| アプリへの影響 | openai を使うのは `problems/ai_generator.py` だけ。同ファイルは openai 0.x 時代の `openai.ChatCompletion.create` を呼んでおり、**現行の 1.3.0 でも既に動いていない**（呼び出し時に例外が出て `except` で代替問題に切り替わる）。3.31.0 でも同じく例外→代替問題になるので、挙動は変わらない（退行なし）。テストからの参照は無い。v1 以降の API への書き換えは別イシューで行う |

R6 の想定（「新しい CVE が実装中に公開され、`pip-audit` が再び落ちる」→「Fix Versions を確認して再固定する」）が発動したものとして、I151 の範囲で対応する（ユーザー承認 2026-10-14）。

### 5-2. `backend/requirements-dev.txt`

| 行 | 現在 | 変更後 | コミット |
|---|---|---|---|
| 5 | `pytest-django==4.9.0` | `pytest-django==4.14.0` | **1 段目**（Django 5.2 対応に必須） |
| 4 | `pytest==8.3.4` | `pytest==9.0.3` | **2 段目**（PYSEC-2026-1845 の解消・唯一の任意変更） |

据え置き: `ruff==0.15.12` / `bandit==1.7.9` / `pip-audit==2.10.0`

### 5-3. `backend/core/settings.py`

```python
# 変更前（34-41 行目）
THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_extensions',     # <- 削除（未使用・§2-4b・38 行目）
    'django_filters',
    'guardian',              # <- 削除（未使用・§2-4・40 行目）
]

# 変更後
THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
]
```

> **【実装時の訂正・2026-08-24】** 初版のスニペットは `'rest_framework_simplejwt.token_blacklist',` を含んでいたが、これは `feature/I142-*` ブランチの状態であり、`develop` 起点の本ブランチには存在しない。削除対象の 2 行は同じで実装内容に影響はないが、guardian の行番号が 41 → 40 にずれる。上記は実態に合わせた内容。

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
5. 検証 → TC-AUTO-01 / 03 / 04 / 05 / 06 / 07 / 08 / 09 / 10 / 11A / 12 / 17 参照。**TC-AUTO-11B（pytest の固定値）はこの時点では対象外**（pytest は 8.3.4 のままが正しいため）。
6. すべて合格したら実装コミットとして記録する。
   - コミットメッセージ: `fix(I151): Django 5.2.17 へ更新し依存を対応版へ一括更新・未使用の django-guardian / django-extensions を削除`
   - 対象: `backend/requirements.txt` / `backend/requirements-dev.txt` / `backend/core/settings.py`

> **このステップが失敗した場合**: 計画をやり直す。テストの skip・削除・条件緩和による緑化は行わない（イシュー Danger Ops の承認条件）。**唯一の例外（条件付きのユーザー承認（2026-10-16「理想的・最適なものを基準として問題ないなら OK」。条件の充足は Claude が判定し、敵対的レビューで検証））**: TC-AUTO-10 の判定 2a・2b で、更新前から存在することを実測した既知の既存不具合 1 種だけを除外する（§2-8）。

### ステップ 2: pytest 9 への更新（コミット 2）
1. `backend/requirements-dev.txt` の `pytest` を `9.0.3` に更新する。
2. backend イメージを再ビルドし、`backend` を作り直す。
3. 検証 → TC-AUTO-02 / 03 / 11B / 12 参照。
4. 合格したらコミットする。
   - コミットメッセージ: `chore(I151): pytest 9.0.3 へ更新（PYSEC-2026-1845 の解消）`
   - 対象: `backend/requirements-dev.txt`

> **このステップが失敗した場合**: **2 段目の変更のみを取り消す**（手順は §8 を参照。Edit ツールで書き戻し、再ビルドまで行う）。ステップ 1 の成果は保持される。その場合は pytest の脆弱性解消を別イシューへ送り、受け入れ条件 AC-09 / AC-10 を「pytest は据え置き」に読み替える旨をレビュー記録に明記する。

### ステップ 3: CI での検証
1. Draft PR #269 に 2 コミットを push する。
2. CI の全 6 チェックの結果を確認する → TC-AUTO-13 / TC-AUTO-14 参照。
3. `pip freeze` の出力を `docs/tests/open/I151_pip_freeze.txt` へ保存しコミットする → TC-AUTO-15 参照。
4. コミットが 2 段に分かれていることを確認する → TC-AUTO-16 参照。

### ステップ 4: 後続イシューの起票
イシュー決定 2 / 7-C / 7-D に基づき 3 件を起票する（タイトル案はイシュー本文に記載済み）→ 手動テスト No.8 参照。**django-extensions の依存移動イシューは決定 7 の変更により不要になった**。**2026-10-16 追加（fix-loop）**: §2-8 の celery `core.tasks` 未登録の既存不具合を、別イシューとして起票する（タイトル案:「celery の core.tasks が未登録で cache_maintenance_task が 30 分ごとに破棄される問題を修正（キャッシュ統計も取得できていない）」）。受け入れ条件に「TC-AUTO-10 から既知 1 種の除外（2a・2b のパターンと `I151_celery_probe.py` の `KNOWN_UNREGISTERED`）を外しても合格すること」を入れる。**起票は I151 の完了後に行う**（2026-10-16 ユーザー指示）。これで後続イシューは計 4 件になる（AC-19）。**実施順の制約（2026-10-16・敵対的レビュー第 1 周で追加）**: ① 未着手の I150（失効トークンの定期削除）は `core/tasks.py` にタスクを足して beat に載せる計画である。この根治イシューより先に I150 を実装すると、単体テストは通るのに worker がタスクを未登録として捨て続け、トークン表が増え続ける。そのため**根治イシューを I150 より先に実施する**（I150 の計画時に前提として確認する）。② 起票済みの I157（beat スケジュールの環境別切り替え・#274）は、AC で cache-maintenance を含む 5 件すべての crontab 化を求めている。これは根治イシューで決める「このタスクを残すか消すか」を、先に「残す」と決める形になる。根治イシューの起票時に、cache-maintenance の扱いをどちらが持つかを決め、I157 の AC を調整する

### ステップ 5: 記録の完成
`docs/tests/open/I151_auto_test.md` / `I151_manual_test.md` に結果を記入し、認可・テナント境界テストのモジュール名と前後の件数を記録する → 手動テスト No.6 参照。

**I151 の完了後に起票するイシューの引き継ぎ（2026-10-16 追加）**: AC-19 は「4 件目の記録の確定」までを I151 の完了条件にしたので、完了後の起票は、どの AC も追わない。その抜けを防ぐため、`/close` で PR #269 の本文に「後続タスク（I151 の完了後に起票）」の節を作り、次を必ず列挙する。
1. celery の `core.tasks` が未登録で cache_maintenance_task が 30 分ごとに破棄される問題の根治（ステップ 4。I150 より先・I157 と調整。TC-AUTO-10 の除外の撤去）
2. 開発環境の実メール対策（beat が 60 秒ごとに SMTP 設定の worker へリマインダーを送る）と、`send_study_reminders_task` の `User.get_full_name` 不在（§2-8）
3. fix-loop の後に、計画書・コードの変更が再レビューされずに `/test` へ進む問題の是正
4. ユーザー確認の要否を「理想・最適の基準で決められるか」で判定する運用への統一（どのスキル・フェーズに入れるかはイシューの中で検討）

手動テスト No.8 で、この節が PR 本文にあることを確認する。

---

## 7. テスト計画

### テストレベルの選択
| レベル | 対象 | 理由 |
|---|---|---|
| 静的検証（決定論 TC） | 依存の固定値・guardian 残存・設定 | 「存在しない」ことの検証は grep の exit code でしか決定論的に判定できない |
| ツール実行 | `pip-audit` / `manage.py check` / `makemigrations --check` / `migrate` | 受け入れ条件がツールの exit code で定義されている |
| 単体・API 結合 | 既存 backend テスト 94 件 | **新規テストは追加しない**（イシュー決定 6）。依存更新の影響は「既存テストが同じ結果を返すか」で測る |
| コンポーネント | 既存 frontend Jest 10 件 | 無退行の確認 |
| E2E | 既存 Playwright 一式 | ログイン〜主要画面の通しを担保する。まっさらな DB への `migrate` を同時に担保するのは **CI 実行に限る**（ローカルの `e2e-init` は開発用 DB へ migrate する。2026-10-14 明記） |

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
- `backend/problems/tests/test_I102_problem_authz.py`（ロール別の認可。2026-10-14 追加）
- `backend/problems/tests/test_I115_public_unauth.py`（公開エンドポイントが**未認証でも 200** を返し、テナント範囲と露出フィールドが固定されていること。認証クラス更新で公開経路が誤って 401 化する退行の検出。2026-10-14 追加）

> 未認証の**拒否（401）**は `test_I102_problem_authz.py` の `test_anonymous_gets_401` が担保する。以上 **9 モジュール**（当初 7・2026-10-14 に 2 追加）。

### false-green 防止
否定・不在を判定する TC（TC-AUTO-05 / 06 / 07）は、失敗条件を注入して実際に**不合格**を返すことを確認してから採用する（手順は auto_test 文書に記載）。合格とする exit code は auto_test の TC 一覧『合格条件』列だけで定める（既定 exit 0・TC-AUTO-06 / 07 は exit 1。2026-10-14 に一本化）。

---

## 8. ロールバック

| 段階 | 手順 |
|---|---|
| ステップ 2 で失敗 | 2 段目の変更のみを取り消す。**手順を明示する**: コミット前なら `backend/requirements-dev.txt` の `pytest==9.0.3` の行を **Edit ツールで `pytest==8.3.4` に書き戻す**（`git restore` は同一ファイル内の他の未コミット変更まで巻き戻すため使わない）。コミット後なら当該コミットを `git revert` する。**取り消し後は必ず再ビルドする**（ファイルを戻してもイメージには pytest 9 が残り、宣言と実インストールが食い違うため）。再ビルド後に TC-AUTO-11B が exit 1（= pytest が 9.0.3 でない）になることで、戻し漏れを検出できる |
| R6 の openai 再固定（055aa11）で問題 | **このコミットだけを取り消すことはできない**（2026-10-15 追記）。取り消すと openai 1.3.0（`anyio<4`）に戻り、anyio 3.7.1 の CVE 2 件（`PYSEC-2026-4024` / `PYSEC-2026-4025`）で `pip-audit` が必ず落ちる。下の「develop マージ後に判明」と同じく前方修正（openai を anyio 4 系を許す別の版へ再固定するか、アプリ側を直す）で対応する |
| ステップ 1 で失敗 | 3 ファイル（`backend/requirements.txt` / `backend/requirements-dev.txt` / `backend/core/settings.py`）を **Edit ツールで更新前の内容へ書き戻す**（変更箇所は §5-1 / §5-2 / §5-3 に列挙済みなので機械的に戻せる。`git restore` は使わない）。その後 backend / celery / celery-beat を再ビルドし、TC-AUTO-01 が exit 1（= 脆弱性が再検出される）に戻ることで巻き戻しの完了を確認する |
| develop マージ後に判明 | **前方修正（5.2 系のまま直す）を正式手順とする**。不具合の原因となった依存だけを 5.2 対応の別パッチ版へ再固定するか、アプリ側を修正する PR を出す。**revert PR は使えない**（2026-10-14・敵対的レビュー第 1 周で訂正）: ① revert すると Django 4.2.30 に戻り、CI の必須チェック `Backend Lint & Security`（`pip-audit -r requirements.txt`）が必ず失敗する（Django の 7 件。R6 の後は openai 1.3.0 / anyio 3.7.1 にも戻るので anyio の 2 件が加わり、少なくとも 9 件。2026-10-15 追記）。branch protection は管理者も迂回不可の設定で、bot には admin 権限もない。② DRF 3.18・django-filter 26.1・django-redis 7.0.0 はいずれも `Django>=5.2` を要求するため、Django だけを戻す部分ロールバックもできない。どうしても 4.2 系へ戻す必要が生じた場合は、ユーザーが GitHub の UI で branch protection を一時解除する判断が必要（Danger Ops）。**前方修正にも同じ行き止まりがある**（2026-10-14・敵対的レビュー第 2 周で追記）: 前方修正 PR も同じ `pip-audit` 必須チェックを通る必要があるため、5.2 系に修正版の無い CVE が公開されている間は前方修正 PR を含む全 PR が止まる（I151 の発端と同じ構造）。この構造の解消は **I152（#268・PR ゲートを許可リスト＋失効日方式へ）** に依存する。I152 マージ前にこの状況が起きた場合も、branch protection の一時解除はユーザー判断（Danger Ops）となる。**一時解除の手順（2026-10-14・fix-loop で追記）**:
① **範囲**は最小にする。外すのは develop の必須チェックのうち、止めている `Backend Lint & Security` の必須指定だけ。管理者への適用（`enforcement_level: everyone`）とほかの 4 チェックは外さない。
② **期限**は、対象の修正 PR がマージされた直後。ユーザーが GitHub の画面で元に戻す（bot には設定変更の権限が無い）。
③ **元に戻ったことの確認**は Claude が機械的に行う。`gh api repos/osushi0404-dev/study-app-multitenant/branches/develop --jq '.protection.required_status_checks.contexts|length'` が `5`、`--jq '.protection.required_status_checks.enforcement_level'` が `everyone` であることを確かめる（この読み取り API は bot でも使えることを 2026-10-14 に確認済み）。
④ 解除・復元の日時と確認結果を、対象 PR の記録に残す。

danger-ops.md の対象例（DB・Git・Docker・Files）にリポジトリ設定の変更は無く、同ファイルの実行条件（`DANGER_OK=1` 等）は画面操作には当てはまらない。そのため本手順を、この操作の承認・実施・確認の正とする。なお `guardian_*` テーブルは残置しているため、guardian を再導入する場合も `INSTALLED_APPS` と依存の復元のみで足りる（データ復旧は不要） |
| DB | マイグレーションを新規生成しないため、DB のロールバックは不要。検証用の使い捨て DB（`migrate_check`）は検証後に破棄する |

---

## 9. Risk & 回避策

| # | リスク | 影響 | 回避策 |
|---|---|---|---|
| R1 | DRF 3.15 → 3.18 でシリアライザ・権限の挙動が変わる | 認可・エラー応答の退行 | 事前スパイクで `core/exceptions.py` と全ビューの import 互換を確認済み。実測は既存 94 件＋認可モジュール群（§7）で担保 |
| R2 | guardian を外すと `migrate` が失敗する | 全テストが落ちる／E2E が落ちる | 使い捨て DB での `migrate`（TC-AUTO-09）＋ drift チェック（TC-AUTO-08）＋ CI の E2E（TC-AUTO-13）の 3 経路で確認 |
| R3 | pytest 9 のメジャー更新でテスト基盤が壊れる | テストが落ちる | 2 段目のコミットに隔離。取り消せば 1 段目の成果は残る |
| R4 | 再ビルドで推移的依存（kombu 等）が変動し celery が壊れる | 非同期タスクの失敗 | worker ログでタスクの**成功**まで確認（TC-AUTO-10）。`pip freeze` を記録して誤帰属を防ぐ（TC-AUTO-15）。現況では kombu 5.6.2 で既に正常動作（§2-7）。2026-10-16 追記: TC-AUTO-10 に、スケジュールの全タスクの登録と実行結果の判定（`I151_celery_probe.py`）を足し、ログの時間窓に頼らずに登録と実行の退行を検出する |
| R5 | 再ビルド対象の取りこぼし（celery / celery-beat が旧イメージのまま） | 本番相当構成での検証にならない | ビルド対象に `celery` `celery-beat` を明示（ステップ 1-4）。**`e2e-init` は E2E 実行時に自動では再ビルドされない**（2026-10-14 訂正。旧記述「E2E 実行時に再ビルドされる」は誤りで、手元の `e2e-init` イメージは Django 4.2.7 のまま残っていた）。ローカル E2E では TC-AUTO-13 の準備 L1 で明示的に作り直し、判定 L0 でイメージの Django 版を確かめる。AC-13 の正式な判定は、毎回ビルドする CI 実行の記録で行う |
| R6 | 新しい CVE が実装中に公開され `pip-audit` が再び落ちる | CI が赤のまま | 計画時点で 7 件へ増えた実績あり（§2-2）。発生時は Fix Versions を確認し 5.2 系の最新パッチへ再固定する（系列変更を伴わないため影響は局所）。ただし、推移的依存の CVE で、それを縛っている直接依存のメジャー更新が必要になる場合は、系列変更を伴う（2026-10-15 追記: 実際の 2026-10-14 の発動はこちらだった。openai 1.x → 3.x。影響範囲は §5-1 追補で確認した）。**2026-10-14 に実装後の発動を確認**（anyio の新規 CVE。openai を 3.31.0 へ再固定。§5-1 追補）。**マージ後の運用時**も同じ手順だが、修正版が未公開の間は全 PR が止まる（§8 参照）。この構造の解消は I152（#268）に依存する |
| R7 | ホスト venv の実測を合否根拠にしてしまう | 本番構成と異なる結論 | すべての TC を `docker compose exec` 経由で実行する。ホスト venv の結果は「下見」としてのみ記載 |
| R8 | Django 5.2 でパスワードハッシュ（PBKDF2）の反復回数が 600,000 → 1,000,000 に増える（2026-10-14 追記） | 既存ユーザーは次回ログイン時にハッシュが作り直され、ログイン経路で `password` 列への書き込みが起きる。1 回あたりの計算時間が増える（2026-10-14 にコンテナ内で実測し、1 回約 0.1 秒） | 影響は小さく、許容する。旧ハッシュは検証でき（`verify=True`）、ログイン時に自動で作り直される（`must_update=True`）。ログインのロック処理とは別のインスタンスで保存されるので衝突しない（敵対的レビュー第 2 周で確認）。4.2 系は反復回数の多いハッシュも検証できるため、仮に戻しても検証は失敗しない |

---

## 10. データ整合性設計（DB 変更があるため記載）

- **DB 制約の変更**: なし。モデル定義に変更がないため、NOT NULL / UNIQUE / FK / CHECK のいずれも変わらない。
- **マイグレーション**: 新規生成なし（事前実測で `No changes detected`・実装時に TC-AUTO-08 で再確認）。
- **`INSTALLED_APPS` からのアプリ除去の扱い**: guardian を外しても Django は既存テーブルに触れない。`django_migrations` テーブルに残る guardian の適用履歴も削除されないが、参照されなくなるだけで整合性に影響しない。
- **孤立テーブル**: `guardian_userobjectpermission` / `guardian_groupobjectpermission` の 2 テーブルが未参照のまま残る。**本イシューでは意図的に残置**し、除去は別イシュー（バックアップ取得のうえ実施）とする。
- **孤立データ（2026-10-14・敵対的レビュー第 2 周で判明）**: テーブルのほかに、guardian が既存 DB に自動作成したデータも残る。① `AnonymousUser` ユーザー行 1 件（`email='AnonymousUser'`・`is_active=True`・組織 3「個人利用」所属。パスワードは使用不可（`!` 始まり）のためログイン不可）② contenttype 2 行（`guardian.groupobjectpermission` / `guardian.userobjectpermission`）③ それに紐づく `auth_permission` 8 行。I151 以降に作られる新しい DB にはこれらは作られないため、**既存 DB と新規 DB で中身が食い違う**。開発 DB で実測済み（読み取りのみ）。なお、ユーザー行を削除すると `UserSettings` 1 行・`StudyStreak` 1 行が CASCADE で連鎖削除される（`Collector` による読み取り専用の試算で確認）。除去は、連鎖削除分を含めたバックアップ・確認手順とあわせて I155（#272）の範囲に追加した。
- **トランザクション境界・冪等性・同時更新**: 本変更はスキーマにもデータにも触れないため該当なし。
- **後方互換性**: guardian を戻す場合も `INSTALLED_APPS` と依存の復元のみで足り、テーブルが残っているためデータ復旧は不要。

---

## 11. 運用設計（非同期処理があるため記載）

- **構造化ログ方針**: 変更なし。`core/enhanced_logging.py` / `core/middleware.py` のログ出力に手を入れない。`custom_exception_handler`（`core/exceptions.py`）も変更しない。（2026-10-15 訂正: 当初は「I142 で整備したエラーハンドリング規約（ログ＋統一 JSON 500）」と書いていた。しかし I142（PR #256）は未マージで、本ブランチの `core/exceptions.py` は I142 前の版である。ロガーも無く、DRF 以外の例外は Django 標準の HTML 500 になる。I151 で確認できるのは「この I142 前のハンドラの挙動が、依存更新の前後で変わらない」ことまでで、「ログ＋統一 JSON 500」は担保していない）
- **celery の検証方針**: worker と beat を再ビルド後に起動し、beat がスケジュールしたタスクが**成功**するまでをログで確認する（TC-AUTO-10）。`update_daily_analytics_task` は 30 秒間隔のため 1 分以内に判定できる。**2026-10-16 改訂（fix-loop）**: エラーの判定は、§2-8 の既知の既存不具合 1 種（`core.tasks.cache_maintenance_task` の未登録）だけを、ERROR と Traceback それぞれの件数一致で除外する形にした（それ以外のエラーが 1 行でもあれば不合格）。この 1 種については合否基準を緩める変更である。除外は、別イシューのマージまでの暫定とする。**2026-10-16 再改訂（fix-loop 後の敵対的レビュー第 1 周）**: ログの 3 分窓だけでは、周期の長いタスク（1 時間ごとの `cleanup_expired_suggestions_task` など）の実行時の失敗を 95% 前後の窓で見逃す。studylogs のタスクは例外を捕まえて `{'error': ...}` を返し、celery 上は succeeded になる点も、ログの成功判定では見抜けない。そこで `docs/tests/open/I151_celery_probe.py` で、`beat_schedule` から導いた全対象タスクについて、worker ごとの登録（応答 worker は 1 つ）と、実際の実行結果を確かめる判定を加えた。**第 2 周の改訂**: 実行結果は、戻り値の `'error'` キーに加えて `error_count` も見る。送信タスク（`send_study_reminders_task`）は実メールを送らないよう、スクリプトのプロセス内で locmem にして実行し、そのエラーログの件数も見る。手順は「スクリプト → ログ」の順にし、スクリプトが worker で動かしたタスクのエラーが必ずログ判定の窓に入るようにした。**第 3 周の改訂**: beat の送信（判定 1b）だけでなく、beat のログの ERROR / Traceback が 0 件であること（2c・2d）と、beat が送ったタスクが worker に届いて成功したこと（1c）を確かめる。限界として、開発 DB には復習カードが 0 件で直近の学習記録もほとんど無いので、ユーザーごとのループの中の処理はほぼ通らない。この経路を確かめるテストは無い（tasks を参照するテストは 0 件。2026-10-16 訂正）
- **タイムアウト・リトライ**: 変更なし（`studylogs/tasks.py` の `max_retries=3` 等はそのまま）。
- **Feature Flag・段階リリース**: 不要。依存更新は全体一括で適用され、部分的に有効化する意味がない。マージ前の切り戻しは §8 のとおりコミット単位で行い、develop マージ後は §8 のとおり前方修正で直す（revert PR は CI の必須チェックで必ず落ちるため使えない。2026-10-14 訂正）。
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

## 18. 確定事項

本計画に**ユーザーの価値判断を要する未決事項は残っていない**。以下はすべて実測または既存ルールから一意に決まったものであり、承認を求めずに実装へ進む。

### 依存の確定セット（Danger Ops の対象）
- `requirements.txt`: Django 5.2.17 / DRF 3.18.0 / django-cors-headers 4.9.0 / django-filter 26.1 / django-redis 7.0.0。**`django-guardian` と `django-extensions` は行ごと削除**（いずれも未使用）。**2026-10-14 追補（R6 発動・§5-1 追補）**: openai 1.3.0 → 3.31.0（anyio の新規 CVE 解消のため）
- `requirements-dev.txt`: pytest-django 4.14.0（1 段目）／pytest 9.0.3（2 段目）
- 上記以外は据え置き（celery 5.3.4 を含む）
- 根拠: `pip-audit` 本体・開発とも 0 件、`manage.py check` 警告 0、マイグレーション drift なし、Python 3.11 / PostgreSQL 15 で要件充足（すべて §2 で実測）

### 変動する測定値は本文に固定しない（2026-08-22 決定）
- **脆弱性の件数**: 起票時 6 件 → 再実測 7 件と 1 週間で変動。イシューのタイトルからは外し、日付付きの実測値として本文に残す。新規 `PYSEC-2026-3717` の修正版は 5.2.17 で、既に決めていたバージョンで解消できる
- **テスト件数**: イシューの受け入れ条件は「実装直前に計測したベースラインと同数」という不変条件とし、**実測値 94 件は本計画書と TC-AUTO-03 に固定**して決定論を保つ

### 実測から導いた実装上の決定
- **django-extensions は更新ではなく削除**（§2-4b）。マイグレーション・DB テーブルとも持たないため残置物なし
- **再ビルド対象は `backend` / `celery` / `celery-beat`**。`docker-compose.yml` の 3 サービスが同じ Dockerfile を参照するため
- ブランチ名 `feature/I151-django-52-lts-upgrade`（作成・push・Draft PR #269 まで実施済み）
- コミットメッセージ: 1 段目 `fix(I151): ...` / 2 段目 `chore(I151): ...`

### セキュリティ（§16 の要約）
- 認可の判定経路は変更しない。guardian は `AUTHENTICATION_BACKENDS` に未登録で、django-extensions は認可に関与しない
- マルチテナントの閲覧・操作範囲は変更しない。組織スコープは自前実装で両パッケージに依存していない
- 依存の既知脆弱性は本体・開発とも 0 件（計画時点で実測）
- **実装後に `/security-review I151` を実施する**（高リスク判定: 認可ライブラリの依存除去＋主要依存のメジャー更新）
- bandit は MEDIUM 以上を修正対象・LOW は `# nosec`／npm audit は high・critical を修正対象

### テスト
- **新規テストは追加しない**（イシュー決定 6）。依存更新の影響は既存 94 件＋認可・テナント境界の 9 モジュール（§7・当初 7、2026-10-14 に 2 追加）の結果一致で測る
- 否定系 TC（TC-AUTO-04/05/06/07/11A/16）は失敗条件を注入して**不合格**を返すことを確認済み（auto_test の実施記録。合格条件は auto_test の TC 一覧『合格条件』列）
- **テストの skip・削除・条件緩和による緑化は行わない**（唯一の例外は TC-AUTO-10 の既知 1 種の除外。条件付きのユーザー承認（2026-10-16「理想的・最適なものを基準として問題ないなら OK」。条件の充足は Claude が判定し、敵対的レビューで検証）・§2-8）

### 条件付きセクションの適用
- P3（データ整合性設計）: 記載あり（§10）／P5（運用設計）: 記載あり（§11）
- P8（コスト）・P6（性能・UX）・P9（プライバシー）: いずれも影響なし（§12 / §13 / §15）

### ユーザーに残るもの
- `/security-review I151` と `/implement I151` の起動（Claude はプロジェクトスキルを自己起動しない）
- PR のマージ（不可逆・外向きの操作）


## セキュリティレビュー結果

**実施日**: 2026-08-23

### セキュリティ設計レビュー

**対象コード変更**: `backend/requirements.txt` / `backend/requirements-dev.txt` / `backend/core/settings.py`（`INSTALLED_APPS` から未使用アプリ 2 行の削除）のみ。**新規エンドポイント・シリアライザ・モデル・URL・permission_classes の変更なし**。

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Medium | 依存ライブラリ／認証 | **レート制限がフェイルオープンしうる**（2026-10-15 訂正: 実際の失敗時の向きは**フェイルクローズ**で、全利用者のログインが 403 になる＝可用性の喪失。下の「残余リスク処遇」の訂正注記を参照。対処の TC-AUTO-17 は、どちら向きの故障も検出できるので有効なまま）。`@ratelimit`（ログイン 5/5m・登録 10/5m・パスワードリセット 3/15m 等のブルートフォース防御）はカウンタを `default` キャッシュに保存する（`RATELIMIT_USE_CACHE = 'default'`）。その `default` は本 PR で **django-redis 5.4.0 → 7.0.0（メジャー 2 段）** に更新され、かつ `IGNORE_EXCEPTIONS: True` により**キャッシュ操作の失敗が例外にならず握り潰される**。カウンタが機能しなくなってもエラーは出ない（初版はここで「総当たり防御だけが静かに消える」と書いていたが誤り。django-ratelimit はカウンタを取得できないと遮断するので、実際の症状は全利用者の 403。2026-10-15 訂正）。さらに既存テスト `core/tests/test_I127_throttling.py` は 4 キャッシュすべてを `LocMemCache` に差し替えるため、**django-redis は 1 度も検証されない**（94 件が全部 pass しても検出できない） | **TC-AUTO-17 を追加し、再ビルド後の実コンテナで `cache.add` / `cache.incr` の動作を必須確認とする**（django-ratelimit が実際に使う操作を `django_ratelimit.core` の実測で特定）。設計時点でホスト venv 上の django-redis 7.0.0 に対し `add_new True` / `add_dup False` / `incr 1→2` を確認済みだが、ホスト venv は合否根拠にしないため実コンテナで再実行する。**`IGNORE_EXCEPTIONS` を無効化する変更は本 PR では行わない**（キャッシュ障害時にアプリ全体を落とす設計変更になるため。恒久対応は別途判断） |
| Low | 認証・認可 | `REST_FRAMEWORK` の `DEFAULT_PERMISSION_CLASSES` が **空リスト**（既存設計）。`permission_classes` を明示し忘れたビューは無防備になる。本 PR は DRF を 3.15 → 3.18 に上げるため、空リストの解釈が変わらないことの確認が要る | **本 PR では設定を変更しない**（変更すると全ビューの挙動が動き、脆弱性解消という目的から外れる）。DRF 更新後も認可判定が不変であることを、既存の認可・テナント境界 9 モジュール（§7・当初 7、2026-10-14 に 2 追加）と全 94 件で確認する。空リストの是正は本 PR のスコープ外 |
| Low | 機密情報 | 新規に `docs/tests/open/I151_pip_freeze.txt` をコミットする（TC-AUTO-15 の記録） | `pip freeze` の出力は**パッケージ名とバージョンのみ**で認証情報を含まない。コミット前に内容を確認する。pre-commit の detect-secrets も通過させる |
| — | マルチテナント | なし。組織スコープの絞り込みは自前実装であり、除去する guardian / django-extensions のいずれにも依存していない（§2-4 / §2-4b で実測） | 既存の認可・テナント境界テストで無退行を確認 |
| — | 入力検証 | なし。シリアライザ・バリデータに変更なし | — |
| — | OWASP Top 10 | **A06（脆弱で古くなったコンポーネント）を直接是正するのが本 PR の目的**。XSS / SQLi / CSRF / IDOR に関わるコード変更なし。`SECURE_BROWSER_XSS_FILTER` / `SECURE_CONTENT_TYPE_NOSNIFF` / `X_FRAME_OPTIONS='DENY'` / 本番時の HSTS 設定はいずれも変更しない | — |
| — | ファイル操作 | なし。アップロード・ダウンロード経路に変更なし | — |
| — | 外部通信 | なし。外部 API・Webhook の呼び出し経路に変更なし | — |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | `POST /api/auth/login/` | 未認証 | パスワードを変えて連続試行（総当たり） | `@ratelimit(key='ip', rate='5/5m')` が 5 回で遮断する | Yes: TC-AUTO-17（カウンタ保存が機能することを実コンテナで確認） | Yes: 実コンテナで連続リクエストして遮断されることを確認（手動 No.11） | カウンタは機能しても、レート値そのものの妥当性は本 PR の対象外。**2026-10-15 追記**: プロキシの背後ではキーが全利用者共通になる既存の不備がある（残余リスク処遇を参照）。本行が担保するのは「カウンタ機構が更新後も動く」ことまで | Medium |
| 2 | `POST /api/auth/password-reset/` 等 | 未認証 | リセット要求の大量送信 | `@ratelimit(key='ip', rate='3/15m')` が遮断する | Yes: TC-AUTO-17（同一のカウンタ機構） | No（#1 と同じ機構のため代表確認で足りる） | 同上 | Medium |
| 3 | 任意の API | 一般ユーザー | 他組織のリソースを取得・更新（テナント越境） | 組織スコープの絞り込みで 403 / 404 を返す | Yes: `test_I103_cross_org_create` / `test_I104_subject_authz` / `test_I006_subject_org_admin` / `test_I078_is_correct_exposure` | No | DRF 3.18 で権限クラスの評価順が変わる可能性は既存テストで担保（新規テストは追加しない方針） | Low |
| 4 | 任意の API | 未認証 / 認証済み | 大量リクエストで DRF スロットルを突破 | `anon 60/min` / `user 300/min` で 429 を返す | Yes: `test_I127_throttling`（ただし LocMemCache 上での検証） | No | 実バックエンド（django-redis 7.0.0）でのスロットル動作は TC-AUTO-17 のカウンタ確認で間接的に担保。DRF スロットルは `cache.get`/`cache.set` を使うため、実コンテナでの実測で充足（2026-10-16 訂正: 初版は「TC-AUTO-15 の read/write 実測と合わせて充足」と書いていたが、TC-AUTO-15 は pip freeze の記録でキャッシュ操作は測っていない。§2 の設計時実測はホスト venv での文字列の set/get で、イシュー決定 5 により合否の根拠にしない。根拠は次の実測に差し替える: 敵対的レビュー第 3 周で、新依存イメージ（django-redis 7.0.0 / DRF 3.18.0）と使い捨ての redis:7 に対し、`core.throttling.AppAnonRateThrottle.allow_request` を同一 IP で 62 回実行して `allowed 60 / denied 2`、保存値が 60 要素の list（時刻リスト）であることを確認。DRF スロットルは Redis 障害時にフェイルオープンするので、壊れても気付かれにくい点に注意） | Low |
| 5 | `POST /api/auth/logout/` → refresh トークン再利用 | 認証済み | ログアウト後の refresh トークンでアクセストークンを再取得 | （あるべき姿）ログアウトした refresh トークンは 401 で拒否される。**I151 時点の実体は満たしていない**（下の訂正注記） | No（本ブランチに該当テストは無い） | No | **I151 以前からある不備（I151 起因ではない）**。ログアウトした refresh の再利用は I142（PR #256・未マージ）で是正される。ローテーション後の旧 refresh の再利用は I142 でも是正されない（残余リスク処遇の (b)）。I151 は simplejwt を据え置いており、挙動は更新前後で同じ | — （既存・範囲外） |
| 6 | Django admin | 未認証 | `/admin/` への到達 | 認証画面が返り、未認証で内部データに到達できない | No | Yes: 手動 No.5（`/admin/login/` が 200） | admin に登録されているモデルの露出範囲は本 PR で変更しない | Low |

> **訂正（2026-10-15・敵対的レビュー第 1 周）**: 初版の #5 は「`token_blacklist` により 401（I142 の成果）・自動テスト `accounts/tests/test_I142_error_handling.py`」、#6 は「I142 で token_blacklist の admin 登録を除外済み」と記載していた。しかし I142（PR #256）は**未マージ**で、`develop` 起点の本ブランチには `rest_framework_simplejwt.token_blacklist` も当該テストも無い（§5-3 訂正注記と同じ取り違え）。実体は次のとおり（敵対的レビューで実測・メインセッションでコードを確認）: `logout_view`（`backend/accounts/views.py:419-429`）の `token.blacklist()` はアプリ未導入のため例外になり、ログアウトは常に 400 を返す。そのため refresh トークンはログアウト後も使える（ローテーション後の旧 refresh も再利用できる）。この挙動は更新前（Django 4.2.30）の旧イメージでも同じで、I151 による退行ではない。ログアウト経路の是正は I142 のマージで行う。ローテーション後の旧 refresh の再利用は、I142 が `BLACKLIST_AFTER_ROTATION=False` にするため残る（2026-10-15・第 2 周で分割。残余リスク処遇の (a)(b) を参照）。I151 のセキュリティ判定（Blocker / High 0 件）は、この既存の不備を「担保済み」として数えていたので、下のサマリーから #5 を外した。

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0 件 | 0 件 |
| High    | 0 件 | 0 件 |
| Medium  | 1 件 | 2 件 |
| Low     | 2 件 | 3 件 |
| 既存・範囲外 | — | 1 件（#5。ログアウト経路は I142 で是正・ローテーション経路は未起票。2026-10-15 訂正） |

### 残余リスク処遇
（/retro で決定する）

暫定の申し送り:
- `IGNORE_EXCEPTIONS: True` でキャッシュ障害を握り潰す設計は、レート制限という**セキュリティ制御**の振る舞いに直結する。本 PR では変更しない。（2026-10-15 訂正: 当初は「レート制限だけはフェイルクローズさせる設計の要否を判断する」と書いていたが、django-ratelimit はすでにフェイルクローズしている。判断すべきなのは「Redis 障害時に全利用者のログイン・登録・パスワードリセットが 403 になる（可用性の喪失）ことを許容するか」である。下の訂正注記を参照）
- `DEFAULT_PERMISSION_CLASSES: []` は、ビューの書き忘れが即座に無防備につながる設計。是正の要否を別途判断する
- **Redis 障害時の向きの訂正（2026-10-15・敵対的レビュー第 1 周）**: 上の設計レビュー Medium 行は「カウンタ失敗が握り潰されて総当たり防御が消える（フェイルオープン）」を想定していた。実測では逆だった。django-ratelimit は既定の `RATELIMIT_FAIL_OPEN=False` で**フェイルクローズ**する。Redis に接続できないと、正しいパスワードのログインを含め、`@ratelimit` 付きの全経路が 403 になる（可用性の喪失）。DRF スロットルのほうはフェイルオープンする。この挙動は更新前（django-redis 5.4.0）と同じで、I151 による退行ではない。TC-AUTO-17 / 手動 No.11 は Redis が正常な状態だけを担保する。障害時の扱いは、上の「キャッシュ障害時の設計」と合わせて別途判断する
- **logout の不備（攻撃シナリオ #5 の訂正）**: 不備は 2 つあり、受け取り先が違う（2026-10-15・敵対的レビュー第 2 周で分割）。
  - (a) **ログアウトした refresh の再利用**: I142（PR #256）のマージで是正される（`token_blacklist` を導入するため）。I142 マージ後に、ログアウトした refresh トークンが 401 になることを確認する
  - (b) **ローテーション後の旧 refresh の再利用**: **I142 でも是正されない**。I142 は `BLACKLIST_AFTER_ROTATION` を明示的に `False` にしている（`feature/I142-accounts-error-handling` の `settings.py:174-175`「FE の更新処理を是正するまで明示的に False とする」）。そのため、旧 refresh は期限（7 日）まで使える。受け取り先は「FE の refresh 処理の是正と `BLACKLIST_AFTER_ROTATION=True` への復帰」で、まだ起票されていない。/retro で起票を判断する。**是正範囲の補足（2026-10-16・第 3 周）**: FE は存在しない URL `/api/auth/token/refresh/` を呼んでいる（`frontend/src/services/api.ts:134`・`auth.service.ts:56`）。backend の実ルートは `/api/auth/refresh/`（`accounts/urls.py:16`）なので、FE の refresh は毎回 404 になり、FE からはローテーション自体が起きない。是正は「新しい refresh の保存」より手前の、URL の修正から始まる。I142 の「True だと 2 回目の更新で強制ログアウト」という前提も、URL を直してから確かめ直す必要がある。なお攻撃者は `/api/auth/refresh/` を直接呼べるので、旧 refresh を再利用できるリスク自体は変わらない
- **IP 単位のレート制限が、nginx の背後で全利用者共通になる（2026-10-15・敵対的レビュー第 2 周で追加。I151 以前からの不備）**: `@ratelimit(key='ip')` は、`RATELIMIT_IP_META_KEY` が未設定のため `REMOTE_ADDR` を使う。`NUM_PROXIES=1` を設定しているのは DRF スロットルだけである。本番（nginx 1 段）と開発（frontend のプロキシ経由）では、`REMOTE_ADDR` が全員プロキシの IP になる。そのため、誰か 1 人が誤ったパスワードで 5 回送ると、5 分間すべての利用者のログインが 403 になる（ログインへの DoS）。旧イメージ（Django 4.2.30）でも同じ結果で、I151 による退行ではない（敵対的レビューで実測）。攻撃シナリオ #1・#2 の「5 回で遮断する」は IP ごとの防御を担保したものではない。また、手動 No.11 は `APIClient`（`REMOTE_ADDR` が固定）で実行しているため、この不備を原理的に検出できない。/retro で起票を判断する。**補足（2026-10-16・第 3 周）**: ① 開発環境の dev proxy（`frontend/src/setupProxy.js`。`xfwd` 未指定）は X-Forwarded-For を付けないので、DRF の anon スロットル（60/min）も全員共通になる。② 「本番は nginx 1 段」は `settings.py:304-306` の記述に基づくもので、リポジトリの production 構成（compose の nginx は `./nginx/nginx.conf` をマウントするが、`nginx/` には `default.conf` しか無い）からは段数を確かめられない。起票時は、実際の本番構成を確かめてから `NUM_PROXIES` / `RATELIMIT_IP_META_KEY` を決める
- **Redis 障害時の範囲（2026-10-16・第 3 周で追加）**: `IGNORE_EXCEPTIONS` があるのは `default` だけである。`sessions` / `problems` / `analytics` の各キャッシュには無く、`SESSION_ENGINE` もキャッシュを使う（`settings.py:235-262, 319-320`）。障害時は、これらを使う経路（admin ログインなど）が 403 ではなく例外（500）になる見込みである（静的読解・未実測）。「キャッシュ障害時の設計」を判断するときは、この範囲も含める

## レビュー結果
- [20261016_0922 判定: ✅ 完了](../../reviews/I151_plan_review_20261016_0922.md)
- [20260823_1437 判定: ✅ 完了](../../reviews/I151_plan_review_20260823_1437.md)
- [20260823_1428 判定: ✅ 完了](../../reviews/I151_plan_review_20260823_1428.md)
- [20260823_1419 判定: ✅ 完了](../../reviews/I151_plan_review_20260823_1419.md)
- [20260823_1344 判定: ✅ 完了](../../reviews/I151_plan_review_20260823_1344.md)
- [20260822_1809 判定: ✅ 完了](../../reviews/I151_plan_review_20260822_1809.md)
