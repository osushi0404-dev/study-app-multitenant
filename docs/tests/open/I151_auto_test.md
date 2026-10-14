# I151 自動テスト（Django 5.2 LTS 更新・未使用の django-guardian / django-extensions の除去）

- 関連: docs/issues/open/I151.md / docs/plans/open/plan_I151.md / GitHub #267 / Draft PR #269
- 実行環境: **Docker（`docker compose exec`）**。ホスト venv の結果は合否根拠にしない（イシュー決定 5）
- テストレベル: 静的検証（決定論 TC）／ツール実行／既存の単体・API 結合／コンポーネント／E2E
- **新規テストコードは追加しない**（イシュー決定 6）。既存 94 件が同じ結果を返すことで依存更新の影響を測る
- 合否判定インターフェース: **すべて exit code に統一**（合格 = exit 0・不合格 = 非ゼロ）
- **コマンドは複合化しない**（`&&` / パイプで束ねない）。複数条件がある TC は「準備」と「判定 1・判定 2 …」に分け、**判定コマンドすべてが exit 0 なら合格**とする。複合コマンドは Claude Code の bash allowlist に一致せず承諾プロンプトを誘発し、自動テスト工程が止まるため

## ベースライン（実装前・2026-08-22 実測）

| 項目 | 値 |
|---|---|
| backend テスト | 94 passed |
| frontend テスト | 10 passed / 3 suites |
| `pip-audit -r requirements.txt` | 7 件検出・exit 1 |
| インストール済み Django | 4.2.30 |
| celery worker | タスク成功（kombu 5.6.2 環境） |

---

## TC 一覧

| TC | 検証内容 | 対応 AC | 実行タイミング |
|---|---|---|---|
| TC-AUTO-00 | 実行環境の前提（6 サービス healthy） | — | ステップ 0 |
| TC-AUTO-01 | 本体依存の脆弱性が 0 件 | AC-08 | ステップ 1 |
| TC-AUTO-02 | 開発依存の脆弱性が 0 件 | AC-09 | ステップ 2 |
| TC-AUTO-03 | backend テストが 94 件 pass（postgres 実接続＝psycopg2 の動作確認を内包） | AC-11・AC-22 | ステップ 1・2 |
| TC-AUTO-04 | `manage.py check` が警告 0 | AC-05 | ステップ 1 |
| TC-AUTO-05 | guardian / django-extensions が requirements / settings に無い | AC-02 | ステップ 1 |
| TC-AUTO-06 | guardian / django_extensions が Python コード全体に無い | AC-03 | ステップ 1 |
| TC-AUTO-07 | guardian 専用設定が無い | AC-04 | ステップ 1 |
| TC-AUTO-08 | マイグレーション drift が無い | AC-07 | ステップ 1 |
| TC-AUTO-09 | まっさらな DB で `migrate` が通る | AC-06 | ステップ 1 |
| TC-AUTO-10 | celery worker のタスクが成功する | AC-15 | ステップ 1 |
| TC-AUTO-11A | 本体依存＋pytest-django の固定値が一致する | AC-01・AC-10 | ステップ 1 |
| TC-AUTO-11B | pytest の固定値が一致する | AC-10 | ステップ 2 |
| TC-AUTO-12 | frontend テストが 10 件 pass | AC-12 | ステップ 1・2 |
| TC-AUTO-13 | E2E が全件 pass | AC-13 | ステップ 3 |
| TC-AUTO-14 | CI の全 6 チェックが SUCCESS | AC-14 | ステップ 3 |
| TC-AUTO-15 | 再ビルド後の `pip freeze` を記録 | AC-16 | ステップ 3 |
| TC-AUTO-16 | コミットが 2 段に分かれている | AC-17 | ステップ 3 |
| TC-AUTO-17 | レート制限のカウンタ保存が実コンテナで機能する | AC-21（security-review 由来） | ステップ 1 |

> **判定コマンドの表記ルール（2026-10-07・fix-loop で是正）**: リポジトリ内ファイルだけを見る静的判定は下の「決定論ゲート（自動実走）」欄に宣言し、`/code-review` が毎回実走する。実行時の一時ファイル（`/tmp/i151_*`）や `git grep` を見る判定は code-review で実走できない（前者は heavy 実行の産物・後者は gate allowlist 外）ため、各 TC 本文に **inline code** で記載する（コピーして単体実行する）。2026-10-07 の表記変更の時点では、判定式・合否基準は変えていない。
>
> **判定式の厳格化（2026-10-14・敵対的レビュー第 1・2 周）**: 判定式そのものに見逃しが見つかったため、TC-AUTO-03 / 05 / 06 / 07 / 12 / 14 / 15 / 16 の判定式を改めた。条件を足して**合否基準を厳しくした**もの（例: TC-AUTO-14 にチェック件数の判定を追加）を含む。「何を確かめる TC か」という意図は変えていない。各 TC 本文に、変更理由と false-green 検証を記載している。
>
> **例外（TC-AUTO-06 / 07）**: この 2 つだけは「**exit 1 のときだけ合格**」とする（理由は TC-AUTO-06 本文）。

---

## 決定論ゲート（自動実走）
<!--
  code-review.sh が下の ```bash ブロックを 1 行 1 コマンドで実走し、実 exit code を VERDICT に注入する。
  対象はリポジトリ内ファイルだけを見る静的判定のみ（TC-AUTO-05 / 11A 判定 A-1 / 11B 判定 B-1 / 15）。
  TC-AUTO-15 判定 2 は正規表現の `|` が gate のチェーン文字ガード（UNSAFE）に掛かるため、パッケージごとに 2 行へ分割した。
  TC-AUTO-15 は 2026-10-14（敵対的レビュー第 1 周の指摘）で厳格化: 判定 1 に -x（行全体一致）、判定 2 を大文字小文字無視＋ハイフン/アンダースコア両対応に変更。
  第 2 周で判定 2 の行頭アンカーを外した（editable install のコメント行・-e 行も検出するため）。TC-AUTO-05 は requirements-dev.txt も対象に追加（Dockerfile でイメージに入るため）。
-->
```bash
# TC-AUTO-05 判定 1・2（guardian / django-extensions が requirements / requirements-dev / settings に無い）
! grep -qi guardian backend/requirements.txt backend/requirements-dev.txt backend/core/settings.py
! grep -qiE 'django[-_]extensions' backend/requirements.txt backend/requirements-dev.txt backend/core/settings.py
# TC-AUTO-11A 判定 A-1（宣言側の固定値）
grep -qx 'Django==5.2.17' backend/requirements.txt
grep -qx 'djangorestframework==3.18.0' backend/requirements.txt
grep -qx 'django-cors-headers==4.9.0' backend/requirements.txt
grep -qx 'django-filter==26.1' backend/requirements.txt
grep -qx 'django-redis==7.0.0' backend/requirements.txt
grep -qx 'pytest-django==4.14.0' backend/requirements-dev.txt
# TC-AUTO-11B 判定 B-1（宣言側の固定値）
grep -qx 'pytest==9.0.3' backend/requirements-dev.txt
# TC-AUTO-15 判定 1・2（pip freeze 記録の中身）
grep -qx 'Django==5.2.17' docs/tests/open/I151_pip_freeze.txt
! grep -qiE 'django[-_]guardian' docs/tests/open/I151_pip_freeze.txt
! grep -qiE 'django[-_]extensions' docs/tests/open/I151_pip_freeze.txt
```

---

## TC-AUTO-00: 実行環境の前提

6 サービスすべてが healthy であること（`celery` / `celery-beat` は healthcheck 定義に従う）。

```bash
docker compose up -d --wait
```

- **合格**: exit 0
- **不合格**: 非ゼロ（いずれかのサービスが unhealthy）

> 備考: 2026-08-22 の起動時、frontend イメージが古く（curl 未同梱）healthcheck が通らなかった。`docker compose build frontend` で解消済み。

---

## TC-AUTO-01: 本体依存の脆弱性が 0 件（AC-08）

```bash
docker compose exec -T backend pip-audit -r requirements.txt
```

- **合格**: exit 0（`No known vulnerabilities found`）
- **不合格**: 非ゼロ
- **実装前の状態（false-green 検証）**: **exit 1**（7 件検出）を実測済み。この TC は現状で確実に不合格になる

---

## TC-AUTO-02: 開発依存の脆弱性が 0 件（AC-09）

```bash
docker compose exec -T backend pip-audit -r requirements-dev.txt
```

- **合格**: exit 0
- **不合格**: 非ゼロ
- **注意**: この TC は**手元実行の記録のためのもの**であり、`.github/workflows/ci.yml` の常設ゲートには追加しない（イシュー決定 4）
- **実装前の状態**: pytest 8.3.4 の `PYSEC-2026-1845` が検出され exit 1

---

## TC-AUTO-03: backend テストが 94 件 pass（AC-11・AC-22）

> AC-22（psycopg2-binary の 5.2 環境での動作確定）: テストは Docker の postgres:15 へ psycopg2 で実接続して実行される（sqlite への差し替えなし）ため、本 TC の合格が psycopg2 の動作確認を兼ねる。

pytest の最終サマリ行が「94 passed（＋警告件数と所要時間のみ）」と**行全体で一致**することを判定する。失敗・エラー・skip・xfail・xpass・deselect が 1 件でも混ざるとサマリ行に追記されて一致しなくなるため、pytest の exit code が非ゼロになるケースをすべて不合格にできる。

準備:
```bash
docker compose exec -T backend python -m pytest -q > /tmp/i151_pytest.log 2>&1
```

判定（サマリ行の完全一致）: `grep -qxE '94 passed(, [0-9]+ warnings?)? in [0-9.]+s( \([0-9:]+\))?' /tmp/i151_pytest.log`

- **合格**: exit 0（全件 pass・**94 件ちょうど**・それ以外の結果種別が 0 件）
- **不合格**: 非ゼロ（失敗・エラーがあるか、件数が 94 でないか、skip / xfail / xpass / deselect が混入した）
- **判定を 1 本の完全一致にした理由（2026-10-14・敵対的レビュー第 1 周で是正）**: 旧判定（`grep -qE '^94 passed'` と `! grep -qE 'skipped|xfailed|deselected'` の 2 本）は、`94 passed, 1 xpassed, 1 error` のような**テスト後片付け（teardown）のエラーや xpass が混ざったログでも両方合格**していた（pytest 自体は exit 1）。禁止語を列挙する方式は列挙漏れが原理的に残るため、許可する形（passed と warnings と所要時間のみ）を行全体で指定する方式に改めた
- **false-green 検証（2026-10-14 実施）**: 合格すべき 3 形（`94 passed in 20.01s` / `94 passed, 5 warnings in 22.69s` / `94 passed, 1 warning in 70.00s (0:01:10)`）で exit 0、不合格にすべき 9 形（error 混入 2 種・failed・skipped・xfailed・deselected・93 件・940 件・行頭に余計な文字）ですべて exit 1 を確認
- **ベースライン**: 94 passed（実装前・実測済み）

---

## TC-AUTO-04: `manage.py check` が警告 0（AC-05）

`--fail-level WARNING` により、警告が 1 件でもあれば非ゼロ終了する。

```bash
docker compose exec -T backend python manage.py check --fail-level WARNING
```

- **合格**: exit 0
- **不合格**: 非ゼロ
- **実装前の状態（false-green 検証）**: **exit 1** を実測済み（`guardian.W001: Guardian authentication backend is not hooked.` が出るため）。guardian を除去すると警告が消えて exit 0 になる

---

## TC-AUTO-05: guardian / django-extensions が requirements / settings に無い（AC-02）

判定 1（guardian）・判定 2（django-extensions）: 「決定論ゲート（自動実走）」欄に宣言（`/code-review` が毎回実走）。
- 判定 1: `! grep -qi guardian backend/requirements.txt backend/requirements-dev.txt backend/core/settings.py`
- 判定 2: `! grep -qiE 'django[-_]extensions' backend/requirements.txt backend/requirements-dev.txt backend/core/settings.py`
- **`requirements-dev.txt` を対象に加えた理由（2026-10-14・敵対的レビュー第 2 周）**: `Dockerfile` が開発イメージに `requirements-dev.txt` もインストールするため。django-extensions のような開発用ツールは requirements-dev 側へ戻されやすく、旧判定ではそれを検出できなかった。2026-10-14 に実リポジトリで判定 1・2 とも exit 0 を確認

- **合格**: 判定 1・2 の**両方が exit 0**（どちらのファイルにも記述が無い）
- **不合格**: 非ゼロ
- **実装前の状態（false-green 検証）**: 判定 1 は **exit 1** を実測済み（`requirements.txt:14` と `settings.py:40` に存在。計画書 §5-3 の訂正に合わせて 41→40 に修正）。判定 2 も `requirements.txt:7` と `settings.py:38` に存在するため **exit 1** になる

---

## TC-AUTO-06: guardian / django_extensions が Python コード全体に無い（AC-03）

判定 1（guardian）: `git grep -qi guardian -- ':(top)backend/*.py' ':(top)backend/**/*.py'`

判定 2（django_extensions）: `git grep -qi django_extensions -- ':(top)backend/*.py' ':(top)backend/**/*.py'`

- **合格**: 判定 1・2 の**両方が exit 1**（痕跡が見つからなかった）
- **不合格**: exit 0（痕跡がある）・exit 128 など 2 以上（リポジトリ外での実行・index 破損などの実行エラー）
- **前提**: リポジトリ内（任意のサブディレクトリ可）で実行する
- **`!` で反転させず「exit 1 のみ合格」にした理由（2026-10-14・敵対的レビュー第 2 周）**: `! git grep ...` は実行エラー（exit 128）まで exit 0＝合格に反転させる。お試し用の一時リポジトリで、痕跡がある状態でも、リポジトリ外での実行・壊れた index ではそれぞれ合格になることを実測した。「exit 1 のみ合格」は、`code-review.sh` の決定論ゲートが `! grep` を扱う方式（exit 1 のみ合格・2 以上は不合格）と同じ。お試し用リポジトリで、痕跡なし→exit 1、痕跡あり→exit 0、リポジトリ外→exit 128、壊れた index→exit 128 を確認済み
- **`:(top)` を付ける理由（2026-10-14・敵対的レビュー第 1 周で是正）**: `git grep` の pathspec は実行ディレクトリ基準で解釈されるため、旧判定を `backend/` から実行すると `backend/backend/...` を探して何もヒットせず、`!` で**痕跡があっても合格**になっていた。`:(top)` はリポジトリルート基準を強制する。お試し用の一時リポジトリで、ルート・`backend/` のどちらから実行しても追跡済みの痕跡を検出（exit 1）できることを確認済み
- **`grep -r` ではなく `git grep` を使う理由（2026-08-23・実装中に是正）**: 当初は `! grep -rqi guardian --include=*.py backend/` としていたが、これは **gitignore 対象の `backend/.venv/` まで走査する**。実際に実装後の検証で、`backend/.venv/lib/python3.12/site-packages/pygments/lexers/_scheme_builtins.py` が Scheme の組み込み関数名 `make-guardian` を含むために **false-red（実装は正しいのに不合格）** になった。`git grep` は追跡ファイルのみを対象とするため、リポジトリの実体（＝ CI が見るもの）と一致する
- **実装前の状態（false-green 検証）**: 差し替え後の判定式が失敗条件を捕捉できることを確認済み。`origin/develop` の `backend/core/settings.py`（guardian / django_extensions を含む）に対して不合格を返す（`!` 付きの旧形式では exit 1。第 2 周の「exit 1 のみ合格」形式では、痕跡を検出して exit 0＝不合格）

---

## TC-AUTO-07: guardian 専用設定が無い（AC-04）

判定: `git grep -q ANONYMOUS_USER_NAME -- ':(top)backend/'`

- **合格**: **exit 1**（痕跡が見つからなかった）
- **不合格**: exit 0（痕跡がある）・2 以上（実行エラー）
- **前提・`:(top)` の理由・「exit 1 のみ合格」の理由**: TC-AUTO-06 と同じ
- **false-green 検証（2026-10-14 再実施）**: 実装前も 0 件のため現状では合格してしまう。2026-08-22 の検証は差し替え前の `grep -r` に対するもので、`git grep` は**未追跡ファイルを見ない**ため現判定式の検証にはならなかった。そこでお試し用の一時リポジトリで `backend/core/dirty.py` に `ANONYMOUS_USER_NAME = 'AnonymousUser'` を書き、**`git add` した状態**で現判定式を実行し、ルート・`backend/` の双方から **exit 1**（正しく不合格）を確認した。未追跡のままでは検出しない（exit 0）が、これは「リポジトリの実体＝CI が見るもの」を対象にする設計どおり
- **`git grep` を使う理由**: TC-AUTO-06 と同じ（`grep -r` は gitignore 対象の `backend/.venv/` を巻き込む）

---

## TC-AUTO-08: マイグレーション drift が無い（AC-07）

CI の `Backend Lint & Security` の「Check migration drift」ステップと同じ判定。

```bash
docker compose exec -T backend python manage.py makemigrations --check --dry-run
```

- **合格**: exit 0（`No changes detected`）
- **不合格**: 非ゼロ（モデルとマイグレーションに乖離がある）
- **事前実測**: guardian / django-extensions 除去済み＋確定セットの組み合わせで `No changes detected` を確認済み
- **false-green 検証（2026-08-23 実施）**: マイグレーション未作成のモデルを持つダミーアプリを `INSTALLED_APPS` に注入したところ **exit 1**（`+ Create model DriftProbe`）を返した。判定式が実際に drift を捕捉できることを確認済み
- **検出の盲点（実測で判明）**: `migrations/` パッケージを持たないアプリは Django が drift 検出の対象外として**黙って読み飛ばす**（同じダミーアプリでも `migrations/__init__.py` を置く前は `No changes detected` が返った）。本イシューの変更範囲では既存アプリがすべて `migrations/` を持つため影響しないが、将来 `migrations/` の無いアプリにモデルを足した場合、この TC と CI の drift チェックの双方が素通りする

---

## TC-AUTO-09: まっさらな DB で `migrate` が通る（AC-06）

開発 DB を壊さないよう、**検証専用の使い捨て DB** を作って `migrate` を流す（イシュー決定 7-A）。

セットアップ（前回の後片付けが済んでいない場合に備え、作成前に取り除く）:
```bash
docker compose exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS migrate_check;"
docker compose exec -T db psql -U postgres -c "CREATE DATABASE migrate_check;"
```

判定（この行の exit code が合否）:
```bash
docker compose exec -T -e DB_NAME=migrate_check backend python manage.py migrate --noinput
```

後片付け:
```bash
docker compose exec -T db psql -U postgres -c "DROP DATABASE migrate_check;"
```

- **合格**: `migrate` が exit 0
- **不合格**: 非ゼロ
- **機構の事前検証**: `docker compose exec -T -e DB_NAME=migrate_check backend` で `settings.DATABASES['default']['NAME']` が `migrate_check` になることを実測済み（2026-08-22）。`settings.py` が `os.getenv('DB_NAME', 'learning_app')` で読むため上書きが効く
- **注意**: 後片付けの `DROP DATABASE` は破壊的操作として PreToolUse フックが承認を求める場合がある。対象は**アプリデータを含まない検証専用 DB** であり、承認して実行してよい。承認しない場合は DB を残置しても害はないが、TC の再実行時に `CREATE DATABASE` が失敗する

---

## TC-AUTO-10: celery worker のタスクが成功する（AC-15）

beat が投げたことではなく、worker が**成功で完了した**ことまで判定する（イシュー決定 7-B）。**起算点は `docker compose up -d --wait` が完了し、`celery` / `celery-beat` コンテナが healthy になった時点**であり、そこから **1 分以上**待ってから実行する。`update_daily_analytics_task` が 30 秒間隔のため、1 分待てば 2 回分の実行ログが出る。待たずに実行すると、worker が 1 度も実行していない状態で判定 1 が exit 1 になる（false-red）。

準備（1 スナップショットを取る）:
```bash
docker compose logs celery --since 3m > /tmp/i151_celery.log 2>&1
```

判定 1（タスクが成功で完了している）: `grep -qE 'Task studylogs\.tasks\.[a-z_]+\[[^]]+\] succeeded' /tmp/i151_celery.log`

判定 2（エラーが出ていない）: `! grep -qE 'ERROR|Traceback' /tmp/i151_celery.log`

> ログを一時ファイルに落としてから 2 つの判定を行う。`docker compose logs` を 2 回実行すると、成功判定とエラー判定が**別々のスナップショット**を見ることになり、その間に書き込まれたエラーを取りこぼす。

- **合格**: exit 0（直近 3 分に成功ログがあり、かつ ERROR / Traceback が無い）
- **不合格**: 非ゼロ
- **ベースライン**: 実装前に成功ログを実測済み（`Task studylogs.tasks.update_daily_analytics_task[...] succeeded in 0.0103s`）。したがって前半の判定式が実際に成功ログを捕捉できることは確認済み

---

## TC-AUTO-11A: 本体依存＋pytest-django の固定値が一致する（AC-01・AC-10）

**実行タイミング: ステップ 1 完了後。** 宣言（requirements）と実インストール（pip freeze）の両方を判定する。宣言だけを見ると、再ビルド漏れで古いイメージのまま合格してしまう。

> **pytest の判定を含めない理由**: ステップ 1 時点の `pytest` は 8.3.4 のままが正しい。pytest の固定値判定を本 TC に混ぜると、ステップ 1 の「全 TC 合格」条件が原理的に満たせなくなる。pytest は TC-AUTO-11B としてステップ 2 で独立に判定する。

判定 A-1（宣言側・6 パッケージを 1 コマンドずつ確認）: 「決定論ゲート（自動実走）」欄に宣言（`/code-review` が毎回実走）。
- `grep -qx 'Django==5.2.17' backend/requirements.txt`
- `grep -qx 'djangorestframework==3.18.0' backend/requirements.txt`
- `grep -qx 'django-cors-headers==4.9.0' backend/requirements.txt`
- `grep -qx 'django-filter==26.1' backend/requirements.txt`
- `grep -qx 'django-redis==7.0.0' backend/requirements.txt`
- `grep -qx 'pytest-django==4.14.0' backend/requirements-dev.txt`

準備（実インストール側のスナップショット）:
```bash
docker compose exec -T backend pip freeze > /tmp/i151_freeze.txt
```

判定 A-2（実インストール側・**宣言側と同じ 6 パッケージを全件**確認）:
- `grep -qx 'Django==5.2.17' /tmp/i151_freeze.txt`
- `grep -qx 'djangorestframework==3.18.0' /tmp/i151_freeze.txt`
- `grep -qx 'django-cors-headers==4.9.0' /tmp/i151_freeze.txt`
- `grep -qx 'django-filter==26.1' /tmp/i151_freeze.txt`
- `grep -qx 'django-redis==7.0.0' /tmp/i151_freeze.txt`
- `grep -qx 'pytest-django==4.14.0' /tmp/i151_freeze.txt`

- **合格**: 判定 A-1 / A-2 の**全コマンドが exit 0**
- **宣言側と実インストール側で対象を揃える理由**: 片方だけ確認すると、再ビルド漏れ（宣言は新しいがイメージは古い）を検出できない。初版では実インストール側から `django-cors-headers` が漏れていたため両側を揃えた。`django-extensions` は削除対象になったため本 TC の対象から外し、不在確認（TC-AUTO-05 / 06）へ移した
- **表記の事前確認**: `pip freeze` が `django-cors-headers==4.3.1` の形（ハイフン・小文字）で出力することを実測済み（2026-08-22）。`-qx` の完全一致で判定できる
- **不合格**: 非ゼロ
- **実装前の状態（false-green 検証）**: 宣言側の 1 行目 `grep -qx 'Django==5.2.17'` が **exit 1** になることを実測済み

---

## TC-AUTO-11B: pytest の固定値が一致する（AC-10）

**実行タイミング: ステップ 2 完了後。**

判定 B-1（宣言側）: 「決定論ゲート（自動実走）」欄に宣言（`/code-review` が毎回実走）。`grep -qx 'pytest==9.0.3' backend/requirements-dev.txt`

準備（実インストール側のスナップショット）:
```bash
docker compose exec -T backend pip freeze > /tmp/i151_freeze2.txt
```

判定 B-2（実インストール側）: `grep -qx 'pytest==9.0.3' /tmp/i151_freeze2.txt`

- **合格**: 判定 B-1 / B-2 の**両方が exit 0**
- **不合格**: 非ゼロ
- **ステップ 1 時点の状態**: `pytest==8.3.4` のため **exit 1**。これはこの時点では正常であり、本 TC はステップ 2 完了後にのみ評価する

---

## TC-AUTO-12: frontend テストが 10 件 pass（AC-12）

準備:
```bash
docker compose exec -T frontend npm test -- --watchAll=false > /tmp/i151_jest.log 2>&1
```

判定 1（テストファイル単位の集計が 3 件すべて成功）: `grep -qxE 'Test Suites:[[:space:]]+3 passed, 3 total' /tmp/i151_jest.log`

判定 2（テスト単位の集計が 10 件すべて成功）: `grep -qxE 'Tests:[[:space:]]+10 passed, 10 total' /tmp/i151_jest.log`

- **合格**: 準備・判定 1・2 とも exit 0
- **不合格**: 非ゼロ
- **判定 1 を足し、行全体一致にした理由（2026-10-14・敵対的レビュー第 2 周）**: 旧判定は Tests 行しか見ず、部分一致だった。そのため、テストファイルの読み込み失敗（`Test Suites: 1 failed, 3 passed, 4 total`。そのファイルのテストは数に入らない）や afterAll の失敗でも合格していた。`-x` を付けたので、`1 failed, ` などの前置きが付いた行には一致しない
- **false-green 検証（2026-10-14 実施）**: 実ログでは判定 1・2 とも exit 0。suite の読み込み失敗・afterAll の失敗では判定 1 が exit 1、テストの失敗・skip では判定 2 が exit 1
- **ベースライン**: 10 passed / 3 suites（実装前・実測済み）

---

## TC-AUTO-13: E2E が全件 pass（AC-13）

E2E はまっさらな DB への `migrate` とログイン〜主要画面の通しを同時に担保する。

```bash
docker compose rm -f e2e-init
docker compose --profile e2e run --rm e2e
```

- **合格**: exit 0
- **不合格**: 非ゼロ
- **備考**: `docker compose rm -f e2e-init` は `common-commands.md` に記載の必須手順（`run --rm` は対象サービスのみ削除するため）

---

## TC-AUTO-14: CI の全 6 チェックが SUCCESS（AC-14）

判定 1（SUCCESS 以外が 0 件）:
```bash
test "$(gh pr checks 269 --json state -q '[.[]|select(.state!="SUCCESS")]|length')" -eq 0
```

判定 2（チェックが 6 件そろっている）:
```bash
test "$(gh pr checks 269 --json name -q length)" -eq 6
```

- **合格**: 判定 1・2 の**両方が exit 0**
- **不合格**: 非ゼロ
- **判定 2 を足した理由（2026-10-14・敵対的レビュー第 1 周で是正）**: 判定 1 だけでは、ワークフローが起動しなかった（チェック 0 件）場合も「SUCCESS 以外が 0 件」で合格してしまう。2026-10-14 に PR #269 で `6` を確認済み
- **対象 6 チェック**: Backend Lint & Security / Backend Tests / Frontend Lint & Security / Frontend Tests / Frontend Type Check / E2E Tests (Playwright)
- **機構の事前検証**: 同じ判定式を PR #256 に対して実行し `0` が返ることを確認済み（2026-08-22）

---

## TC-AUTO-15: 再ビルド後の `pip freeze` を記録（AC-16）

推移的依存（kombu 等）が再ビルドで変動した場合に、後から切り分けられるようにする（イシュー決定 7-C）。

記録先は**専用ファイル**とする。本文書を grep 対象にすると、説明文中に書かれた文字列にも反応してしまい判定が壊れる（初版はこの誤りを含んでいた）。

準備（出力を記録ファイルへ保存し、リポジトリにコミットする）:
```bash
docker compose exec -T backend pip freeze > docs/tests/open/I151_pip_freeze.txt
```

判定 1・2: 「決定論ゲート（自動実走）」欄に宣言（`/code-review` が毎回実走）。

- 判定 1（更新後の Django が記録されている）: `grep -qx 'Django==5.2.17' docs/tests/open/I151_pip_freeze.txt`
- 判定 2（除去した 2 パッケージが記録に現れない＝再ビルド後の実体である）: `! grep -qiE 'django[-_]guardian' docs/tests/open/I151_pip_freeze.txt` と `! grep -qiE 'django[-_]extensions' docs/tests/open/I151_pip_freeze.txt` の 2 行（ゲート欄では 3 行で宣言しているため、記録欄では「判定 1〜3」と書いている箇所がある。判定 1 ＋ 判定 2 の 2 行のことを指す）
- **判定式の変遷**: 2026-10-07 に `! grep -qE 'django-(guardian|extensions)=='` を 2 行に分割（正規表現の `|` が gate のチェーン文字ガードに掛かるため）。2026-10-14（敵対的レビュー第 1 周）で厳格化した。旧判定 1 は `-x` が無く `Django==5.2.170` やコメント行に部分一致していた。旧判定 2 は `django-guardian==` 固定で、`django_guardian==`（pip freeze はアンダースコア表記も出す）・大文字表記・`@ file://` 形式を見逃していた
- **第 2 周での変更（2026-10-14）**: 第 1 周で付けた行頭アンカー `^` を外した。アンカー付きだと、pip freeze の editable install の形（`# Editable install with no version control (django-guardian==2.4.0)` / `-e /src/django-guardian` / `-e git+...#egg=django_extensions`）を見逃すため。追加で検証し、これら 3 形と第 1 周の不合格形がすべて不合格（exit 1）、実記録が合格（exit 0）になることを確認した
- **false-green 検証（2026-10-14 実施）**: 実記録で判定 1・判定 2（2 行）がすべて exit 0。不合格にすべき 5 形（`Django==5.2.170` → 判定 1 が exit 1／コメント行のみ → 判定 1 が exit 1／アンダースコア表記の旧 freeze → 判定 2 の両行が exit 1／`Django-Guardian==` → guardian 行が exit 1／`django-extensions @ file://` → extensions 行が exit 1）と、ファイル不在（判定 1 が exit 2）をすべて確認

- **合格**: 判定 1・2 の**両方が exit 0**
- **この形にした理由**: 「記録した」という主張を人手判定に委ねると、貼り忘れても合格になる。専用ファイルを grep 対象にすることで、記録の有無と中身の正しさを exit code で判定できる（文書冒頭の「合否判定はすべて exit code」を満たす）
- **実装前の状態（false-green 検証）**: 記録ファイルが存在しないため判定 1 が **exit 2**（grep のファイル不在エラー・非ゼロ）になる。ベースラインの `pip freeze` をそのまま保存した場合は、除去前の 2 パッケージが含まれるため判定 2 が **exit 1** になる
- **ベースライン（実装前・2026-08-22）**: Django 4.2.30 / celery 5.3.4 / kombu 5.6.2 / amqp 5.3.1 / billiard 4.2.4 / vine 5.1.0 / redis 5.0.1 / djangorestframework 3.15.2 / django-guardian 2.4.0 / django-extensions 3.2.3 / pytest 8.3.4 / pytest-django 4.9.0

---

## TC-AUTO-16: コミットが 2 段に分かれている（AC-17）

準備 1:
```bash
git log origin/develop..HEAD --oneline > /tmp/i151_commits.txt
```

準備 2:
```bash
git log origin/develop..HEAD --oneline -- backend/requirements.txt > /tmp/i151_req_commits.txt
```

判定 1（1 段目のコミットが存在する）: `grep -qE 'fix\(I151\)' /tmp/i151_commits.txt`

判定 2（2 段目のコミットが存在する）: `grep -qE 'chore\(I151\)' /tmp/i151_commits.txt`

判定 3（`requirements.txt` を触ったコミットが 1 つだけ＝本体依存が 1 段目に集約されている）:
```bash
test "$(wc -l < /tmp/i151_req_commits.txt)" -eq 1
```

> `wc -l < file` はリダイレクトであってパイプではないため、本文書冒頭の「コマンドを複合化しない」原則を満たす。

判定 4（`requirements.txt` を触った唯一のコミットが 1 段目＝`fix(I151)` である）: `grep -qE 'fix\(I151\)' /tmp/i151_req_commits.txt`

- **合格**: 判定 1〜4 の**すべてが exit 0**
- **判定 4 を足した理由（2026-10-14・敵対的レビュー第 2 周）**: 判定 1〜3 だけでは、「requirements.txt を触ったコミットが 1 つある」ことしか分からず、それが 1 段目かどうかは確かめていなかった。依存更新を全部 2 段目（chore）に入れるような誤った分け方でも合格してしまう。2026-10-14 に実リポジトリで exit 0（該当コミット 4877e18 は `fix(I151)`）、chore だけのダミー記録で exit 1 を確認
- **不合格**: 非ゼロ
- **実装前の状態（false-green 検証）**: `fix(I151)` コミットが存在しないため **exit 1**

---

## TC-AUTO-17: レート制限のカウンタ保存が実コンテナで機能する（AC-21・security-review 由来）

**なぜ必要か**: `@ratelimit`（ログイン 5/5m・登録 10/5m・パスワードリセット 3/15m 等のブルートフォース防御）は、カウンタを **`default` キャッシュ**に保存する（`settings.py` の `RATELIMIT_USE_CACHE = 'default'`）。その `default` は本 PR で **django-redis 5.4.0 → 7.0.0（メジャー 2 段）** に更新され、しかも `IGNORE_EXCEPTIONS: True` が設定されているため**失敗しても例外が出ずに握り潰される（フェイルオープン）**。

**既存テストでは検出できない**: `backend/core/tests/test_I127_throttling.py` は 4 つのキャッシュをすべて `LocMemCache` に差し替えるため、django-redis は一度も実行されない。つまり 94 件が全部 pass しても、実環境でレート制限が黙って無効化されている可能性が残る。

django-ratelimit が使うキャッシュ操作は `cache.add` と `cache.incr` の 2 つ（`django_ratelimit.core` を実測）。これを**再ビルド後の実コンテナ**で確認する。

準備:
```bash
docker compose exec -T backend python manage.py shell -c "from django.core.cache import cache; cache.delete('i151_rl_probe'); print('add_new', cache.add('i151_rl_probe', 0, 60)); print('add_dup', cache.add('i151_rl_probe', 0, 60)); print('incr1', cache.incr('i151_rl_probe')); print('incr2', cache.incr('i151_rl_probe')); cache.delete('i151_rl_probe')" > /tmp/i151_rl.txt 2>&1
```

判定 1（新規キーの追加が成功する）: `grep -q 'add_new True' /tmp/i151_rl.txt`

判定 2（既存キーの重複追加が拒否される）: `grep -q 'add_dup False' /tmp/i151_rl.txt`

判定 3（カウンタが加算される）: `grep -q 'incr2 2' /tmp/i151_rl.txt`

- **合格**: 判定 1〜3 の**すべてが exit 0**
- **不合格**: 非ゼロ（＝カウンタが機能せず、レート制限がフェイルオープンしている）
- **`python -c` ではなく `manage.py shell -c` を使う理由（実装中に是正）**: `python -c` は Django の設定を読み込まないため `ImproperlyConfigured: Requested setting CACHES` で落ちる（実装時に実測）。`manage.py shell -c` は設定済みの状態で実行される
- **設計時点の実測（2026-08-23・ホスト venv）**: django-redis 7.0.0 に対して `add_new True` / `add_dup False` / `incr 1` / `incr 2` を確認済み。ただし**ホスト venv の結果は合否根拠にしない**（イシュー決定 5）ため、再ビルド後の実コンテナで再実行する

---

## 実施記録

| TC | 結果 | 実施日 | 備考 |
|---|---|---|---|
| TC-AUTO-00 | ✅ 合格 | 2026-08-24 | `docker compose up -d --wait` exit 0（6 サービス healthy） |
| TC-AUTO-01 | ✅ 合格 | 2026-08-24 | `No known vulnerabilities found`・exit 0（ベースライン 7 件 → 0 件） |
| TC-AUTO-02 | ✅ 合格 | 2026-08-24 | ステップ 2 完了後に実行。`No known vulnerabilities found`・exit 0 |
| TC-AUTO-03 | ✅ 合格 | 2026-08-24 | ステップ 1・2 とも `94 passed`（ベースラインと同数）・skip / xfail / deselect 0 件 |
| TC-AUTO-04 | ✅ 合格 | 2026-08-24 | `System check identified no issues (0 silenced).`・exit 0（guardian.W001 が消滅） |
| TC-AUTO-05 | ✅ 合格 | 2026-08-24 | 判定 1・2 とも exit 0 |
| TC-AUTO-06 | ✅ 合格 | 2026-08-24 | 判定 1・2 とも exit 0。**当初の `grep -r` は `backend/.venv` の pygments に反応して false-red となったため `git grep` へ是正** |
| TC-AUTO-07 | ✅ 合格 | 2026-08-24 | exit 0 |
| TC-AUTO-08 | ✅ 合格 | 2026-08-24 | `No changes detected`・exit 0 |
| TC-AUTO-09 | ✅ 合格 | 2026-08-24 | 使い捨て DB で 58 マイグレーションを適用し exit 0。guardian のマイグレーションは 0 件。検証後に DB を破棄 |
| TC-AUTO-10 | ✅ 合格 | 2026-08-24 | 直近 3 分に成功ログ 9 件・`ERROR` / `Traceback` 0 件 |
| TC-AUTO-11A | ✅ 合格 | 2026-08-24 | 宣言側 6 件・実インストール側 6 件ともすべて exit 0 |
| TC-AUTO-11B | ✅ 合格 | 2026-08-24 | ステップ 2 完了後。宣言・実インストールとも `pytest==9.0.3` |
| TC-AUTO-12 | ✅ 合格 | 2026-08-24 | ステップ 1・2 とも `Tests: 10 passed, 10 total` |
| TC-AUTO-13 | ✅ 合格 | 2026-08-24 | CI の E2E ジョブで全件 pass（3m10s） |
| TC-AUTO-14 | ✅ 合格 | 2026-08-24 | 全 6 チェック SUCCESS。`gh pr checks 269` の SUCCESS 以外が 0 件 |
| TC-AUTO-15 | ✅ 合格 | 2026-08-24 | `docs/tests/open/I151_pip_freeze.txt`（81 行）に記録。判定 1・2 とも exit 0 |
| TC-AUTO-16 | ✅ 合格 | 2026-08-24 | `fix(I151)` / `chore(I151)` の 2 コミット。`requirements.txt` を触ったコミットは 1 つ |
| TC-AUTO-17 | ✅ 合格 | 2026-08-24 | `add_new True` / `add_dup False` / `incr1 1` / `incr2 2`。**当初の `python -c` は Django 未設定で落ちたため `manage.py shell -c` へ是正** |

### 判定式厳格化後の再実施（2026-10-14・敵対的レビュー第 1 周の是正）

| TC | 結果 | 実施日 | 備考 |
|---|---|---|---|
| TC-AUTO-03 | ✅ 合格 | 2026-10-14 | 新判定式（サマリ行の完全一致）で再実行。pytest exit 0・サマリ行 `94 passed, 5 warnings in 22.69s`。警告 5 件は DRF の `UnorderedObjectListWarning` 等で I151 以前から出ているもの（判定対象外） |
| TC-AUTO-05 | ✅ 合格 | 2026-10-14 | 第 2 周：`requirements-dev.txt` を対象に加えた判定 1・2 とも exit 0（`/code-review` の決定論ゲートでも実走） |
| TC-AUTO-06 | ✅ 合格 | 2026-10-14 | 第 1 周：`:(top)` 付き判定式を、リポジトリルート・`backend/` の双方から実行して合格。`origin/develop` に対しては判定 1・2 とも痕跡を検出（正しく不合格）。第 2 周：「exit 1 のみ合格」形式で実リポジトリの判定 1・2 とも **exit 1**（合格） |
| TC-AUTO-07 | ✅ 合格 | 2026-10-14 | 第 1 周：`:(top)` 付き判定式を、ルート・`backend/` の双方から実行して合格。第 2 周：「exit 1 のみ合格」形式で **exit 1**（合格） |
| TC-AUTO-12 | ✅ 合格 | 2026-10-14 | 第 2 周：frontend テストを再実行。`Test Suites: 3 passed, 3 total` / `Tests: 10 passed, 10 total` で判定 1・2 とも exit 0 |
| TC-AUTO-14 | ✅ 合格 | 2026-10-14 | 判定 1（SUCCESS 以外 0 件）・判定 2（チェック 6 件）とも exit 0 |
| TC-AUTO-15 | ✅ 合格 | 2026-10-14 | 厳格化後の判定 1・判定 2（2 行）とも exit 0（第 2 周で行頭アンカーを外した形でも exit 0。`/code-review` の決定論ゲートでも実走） |
| TC-AUTO-16 | ✅ 合格 | 2026-10-14 | 第 2 周：判定 4（requirements.txt を触ったコミットが `fix(I151)`）が exit 0 |

### false-green 検証の記録（計画時点・2026-08-22 実施済み）

否定・回帰系 TC が実際に不合格を返せることを、実装前の状態またはダミー注入で確認した。

| TC | 判定式 | 検証方法 | 結果 |
|---|---|---|---|
| TC-AUTO-04 | `manage.py check --fail-level WARNING` | 実装前の状態（guardian.W001 あり） | **exit 1**（正しく不合格） |
| TC-AUTO-05 | `! grep -qi guardian ...` / `! grep -qiE 'django[-_]extensions' ...` | 実装前の状態（両方の記述あり） | **exit 1**（正しく不合格） |
| TC-AUTO-06 | `! grep -rqi guardian ...` / `! grep -rqi django_extensions ...`（旧判定式。現行の `git grep` 版は下の 2026-10-14 表を参照） | 実装前の状態 | **exit 1**（正しく不合格） |
| TC-AUTO-07 | `! grep -rq ANONYMOUS_USER_NAME ...`（旧判定式。現行の `git grep` 版は下の 2026-10-14 表を参照） | ダミー注入（`ANONYMOUS_USER_NAME = 'AnonymousUser'` を含むファイルを一時ディレクトリに作成） | **exit 1**（正しく不合格） |
| TC-AUTO-08 | `makemigrations --check --dry-run` | マイグレーション未作成のモデルを持つダミーアプリを `INSTALLED_APPS` に注入 | **exit 1**（正しく不合格） |
| TC-AUTO-11A | `grep -qx 'Django==5.2.17' ...` | 実装前の状態（4.2.30） | **exit 1**（正しく不合格） |
| TC-AUTO-16 | `git log ... grep -qE 'fix\(I151\)'` | 実装前の状態（コミット未作成） | **exit 1**（正しく不合格） |

### false-green 検証の記録（現行判定式・2026-10-14 実施）

| TC | 判定式 | 検証方法 | 結果 |
|---|---|---|---|
| TC-AUTO-03 | `grep -qxE '94 passed(, [0-9]+ warnings?)? in [0-9.]+s( \([0-9:]+\))?'` | 合格形 3 種・不合格形 9 種のログを一時ディレクトリに作って実行 | 合格形はすべて exit 0、不合格形はすべて **exit 1** |
| TC-AUTO-06 / 07 | `:(top)` 付き `git grep`（第 1 周は `!` 付き） | 一時リポジトリに痕跡ファイルを `git add` し、ルート・`backend/` の双方から実行 | 双方で正しく不合格。旧判定式は `backend/` から実行すると合格していた |
| TC-AUTO-06 / 07 | `:(top)` 付き `git grep`・exit 1 のみ合格（第 2 周） | 痕跡なし／痕跡あり／リポジトリ外／壊れた index | exit 1（合格）／exit 0・exit 128・exit 128（いずれも不合格）。`!` 付きの旧形式では、後の 2 つが合格に反転していた |
| TC-AUTO-12 | `grep -qxE` で Test Suites 行・Tests 行の両方 | suite 読み込み失敗・afterAll 失敗・テスト失敗・skip のログ | すべていずれかの判定が **exit 1**（正しく不合格） |
| TC-AUTO-15 | `grep -qx 'Django==5.2.17'` / `! grep -qiE 'django[-_]guardian'` / `! grep -qiE 'django[-_]extensions'`（第 2 周で行頭アンカーを外した形） | 壊れた記録 5 形＋editable 形式 3 形とファイル不在 | 該当する判定がすべて非ゼロ（正しく不合格） |
| TC-AUTO-16 | 判定 4 `grep -qE 'fix\(I151\)' /tmp/i151_req_commits.txt` | requirements.txt を触ったコミットが chore だけのダミー記録 | **exit 1**（正しく不合格） |

### 機構の事前検証（計画時点・2026-08-22 実施済み）

| 対象 | 検証内容 | 結果 |
|---|---|---|
| TC-AUTO-09 | `docker compose exec -e DB_NAME=migrate_check` が Django 設定に届くか | `settings.DATABASES['default']['NAME'] = migrate_check` を確認 |
| TC-AUTO-10 | 成功ログの grep パターンが実際のログに一致するか | 実装前のログで `Task studylogs.tasks.update_daily_analytics_task[...] succeeded` に一致 |
| TC-AUTO-14 | `gh pr checks --json` の判定式が動くか | PR #256 に対して `0` を確認 |
