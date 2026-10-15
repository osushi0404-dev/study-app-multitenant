# I151 自動テスト（Django 5.2 LTS 更新・未使用の django-guardian / django-extensions の除去）

- 関連: docs/issues/open/I151.md / docs/plans/open/plan_I151.md / GitHub #267 / Draft PR #269
- 実行環境: **Docker（`docker compose exec`）**。ホスト venv の結果は合否根拠にしない（イシュー決定 5）
- テストレベル: 静的検証（決定論 TC）／ツール実行／既存の単体・API 結合／コンポーネント／E2E
- **新規テストコードは追加しない**（イシュー決定 6）。既存 94 件が同じ結果を返すことで依存更新の影響を測る
- 合否判定インターフェース: **すべて exit code で判定する**。**合格とする exit code は下の「TC 一覧」の『合格条件』列だけで定める（唯一の正）**。既定は「exit 0 = 合格・非ゼロ = 不合格」。TC-AUTO-06 / 07 だけは「exit 1 = 合格・それ以外 = 不合格」（理由は TC-AUTO-06 本文）。TC 本文・実施記録・手動テスト・計画書で合否に触れる箇所は、この列に従う
- **コマンドは複合化しない**（`&&` / パイプで束ねない）。複数条件がある TC は「準備」と「判定 1・判定 2 …」に分け、**判定コマンドすべてが『合格条件』列の exit code を返したら合格**とする。複合コマンドは Claude Code の bash allowlist に一致せず承諾プロンプトを誘発し、自動テスト工程が止まるため

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

| TC | 検証内容 | 対応 AC | 実行タイミング | 合格条件（唯一の正） |
|---|---|---|---|---|
| TC-AUTO-00 | 実行環境の前提（6 サービス healthy） | — | ステップ 0 | exit 0 |
| TC-AUTO-01 | 本体依存の脆弱性が 0 件 | AC-08 | ステップ 1 | exit 0 |
| TC-AUTO-02 | 開発依存の脆弱性が 0 件 | AC-09 | ステップ 2 | exit 0 |
| TC-AUTO-03 | backend テストが 94 件 pass（postgres 実接続＝psycopg2 の動作確認を内包） | AC-11・AC-22 | ステップ 1・2 | exit 0 |
| TC-AUTO-04 | `manage.py check` が警告 0 | AC-05 | ステップ 1 | exit 0 |
| TC-AUTO-05 | guardian / django-extensions が requirements / requirements-dev / settings に無い | AC-02 | ステップ 1 | exit 0 |
| TC-AUTO-06 | guardian / django_extensions が Python コード全体に無い | AC-03 | ステップ 1 | **exit 1**（例外） |
| TC-AUTO-07 | guardian 専用設定が無い | AC-04 | ステップ 1 | **exit 1**（例外） |
| TC-AUTO-08 | マイグレーション drift が無い | AC-07 | ステップ 1 | exit 0 |
| TC-AUTO-09 | まっさらな DB で `migrate` が通る | AC-06 | ステップ 1 | exit 0 |
| TC-AUTO-10 | celery worker のタスクが成功する | AC-15 | ステップ 1 | exit 0 |
| TC-AUTO-11A | 本体依存＋pytest-django の固定値が一致する | AC-01・AC-10 | ステップ 1 | exit 0 |
| TC-AUTO-11B | pytest の固定値が一致する | AC-10 | ステップ 2 | exit 0 |
| TC-AUTO-12 | frontend テストが 10 件 pass | AC-12 | ステップ 1・2 | exit 0 |
| TC-AUTO-13 | E2E が全件 pass | AC-13 | ステップ 3 | exit 0 |
| TC-AUTO-14 | CI の全 6 チェックが SUCCESS | AC-14 | ステップ 3 | exit 0 |
| TC-AUTO-15 | 再ビルド後の `pip freeze` を記録 | AC-16 | ステップ 3 | exit 0 |
| TC-AUTO-16 | コミットが 2 段に分かれている | AC-17 | ステップ 3 | exit 0 |
| TC-AUTO-17 | レート制限のカウンタ保存が実コンテナで機能する | AC-21（security-review 由来） | ステップ 1 | exit 0 |

> **判定コマンドの表記ルール（2026-10-07・fix-loop で是正）**: リポジトリ内ファイルだけを見る静的判定は下の「決定論ゲート（自動実走）」欄に宣言し、`/code-review` が毎回実走する。実行時の一時ファイル（`/tmp/i151_*`）や `git grep` を見る判定は code-review で実走できない（前者は heavy 実行の産物・後者は gate allowlist 外）ため、各 TC 本文に **inline code** で記載する（コピーして単体実行する）。2026-10-07 の表記変更の時点では、判定式・合否基準は変えていない。
>
> **判定式の厳格化（2026-10-14・敵対的レビュー第 1・2 周）**: 判定式そのものに見逃しが見つかったため、TC-AUTO-03 / 05 / 06 / 07 / 12 / 14 / 15 / 16 の判定式を改めた。条件を足して**合否基準を厳しくした**もの（例: TC-AUTO-14 にチェック件数の判定を追加）を含む。「何を確かめる TC か」という意図は変えていない。各 TC 本文に、変更理由と false-green 検証を記載している。
>
> **判定式の追加・改訂（2026-10-15・敵対的レビュー第 1・2 周）**: TC-AUTO-13 に判定 0・0b・0c を追加した（根拠にする CI の job を現コードに結び付ける。ログとコミットは同じ job_id から取る）。TC-AUTO-15 に判定 3（全 8 固定値）と判定 4（推移的依存 anyio / kombu）を追加した。TC-AUTO-16 は判定 8・10 の件数判定を `--numstat` に替え、判定 11（`requirements-dev.txt` を触ったコミットの数）を追加した。いずれも合否基準を厳しくする方向の変更である。
>
> **合格条件の定義場所（2026-10-14・fix-loop で是正）**: 合格とする exit code は「TC 一覧」の『合格条件』列だけで定める。第 2 周で TC-AUTO-06 / 07 を「exit 1 のときだけ合格」に変えた際、合否の書き方が文書中に散らばっていたため、書き換え漏れ（同じ TC 本文の旧 exit code 記述など）が残った。その再発を防ぐため、定義を 1 か所にまとめた。

---

## 決定論ゲート（自動実走）
<!--
  code-review.sh が下の ```bash ブロックを 1 行 1 コマンドで実走し、実 exit code を VERDICT に注入する。
  対象はリポジトリ内ファイルだけを見る静的判定のみ（TC-AUTO-05 / 11A 判定 A-1 / 11B 判定 B-1 / 15）。
  TC-AUTO-15 判定 2 は正規表現の `|` が gate のチェーン文字ガード（UNSAFE）に掛かるため、パッケージごとに 2 行へ分割した。
  TC-AUTO-15 は 2026-10-14（敵対的レビュー第 1 周の指摘）で厳格化: 判定 1 に -x（行全体一致）、判定 2 を大文字小文字無視＋ハイフン/アンダースコア両対応に変更。
  第 2 周で判定 2 の行頭アンカーを外した（editable install のコメント行・-e 行も検出するため）。TC-AUTO-05 は requirements-dev.txt も対象に追加（Dockerfile でイメージに入るため）。
  2026-10-15 に TC-AUTO-15 判定 3（全 8 固定値・7 行）と判定 4（推移的依存 anyio / kombu・2 行）を追加。
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
grep -qx 'openai==3.31.0' backend/requirements.txt
grep -qx 'pytest-django==4.14.0' backend/requirements-dev.txt
# TC-AUTO-11B 判定 B-1（宣言側の固定値）
grep -qx 'pytest==9.0.3' backend/requirements-dev.txt
# TC-AUTO-15 判定 1・2（pip freeze 記録の中身）
grep -qx 'Django==5.2.17' docs/tests/open/I151_pip_freeze.txt
! grep -qiE 'django[-_]guardian' docs/tests/open/I151_pip_freeze.txt
! grep -qiE 'django[-_]extensions' docs/tests/open/I151_pip_freeze.txt
# TC-AUTO-15 判定 3（記録が宣言側の全固定値と一致する＝R6 などの再固定後に記録を更新し忘れていない）
grep -qx 'djangorestframework==3.18.0' docs/tests/open/I151_pip_freeze.txt
grep -qx 'django-cors-headers==4.9.0' docs/tests/open/I151_pip_freeze.txt
grep -qx 'django-filter==26.1' docs/tests/open/I151_pip_freeze.txt
grep -qx 'django-redis==7.0.0' docs/tests/open/I151_pip_freeze.txt
grep -qx 'openai==3.31.0' docs/tests/open/I151_pip_freeze.txt
grep -qx 'pytest-django==4.14.0' docs/tests/open/I151_pip_freeze.txt
grep -qx 'pytest==9.0.3' docs/tests/open/I151_pip_freeze.txt
# TC-AUTO-15 判定 4（宣言ファイルには無い推移的依存が記録されている＝requirements の写しではなく実コンテナの freeze である。anyio は R6 の対象）
grep -qx 'anyio==4.15.1' docs/tests/open/I151_pip_freeze.txt
grep -qx 'kombu==5.6.2' docs/tests/open/I151_pip_freeze.txt
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
- **`:(top)` を付ける理由（2026-10-14・敵対的レビュー第 1 周で是正）**: `git grep` の pathspec は実行ディレクトリ基準で解釈されるため、旧判定を `backend/` から実行すると `backend/backend/...` を探して何もヒットせず、`!` で**痕跡があっても合格**になっていた。`:(top)` はリポジトリルート基準を強制する。お試し用の一時リポジトリで、ルート・`backend/` のどちらから実行しても追跡済みの痕跡を検出できることを確認済み（検出したときの exit code は、第 1 周の `!` 付き旧形式では exit 1、第 2 周以降の現判定式では exit 0。どちらも「不合格」）
- **`grep -r` ではなく `git grep` を使う理由（2026-08-23・実装中に是正）**: 当初は `! grep -rqi guardian --include=*.py backend/` としていたが、これは **gitignore 対象の `backend/.venv/` まで走査する**。実際に実装後の検証で、`backend/.venv/lib/python3.12/site-packages/pygments/lexers/_scheme_builtins.py` が Scheme の組み込み関数名 `make-guardian` を含むために **false-red（実装は正しいのに不合格）** になった。`git grep` は追跡ファイルのみを対象とするため、リポジトリの実体（＝ CI が見るもの）と一致する
- **実装前の状態（false-green 検証）**: 差し替え後の判定式が失敗条件を捕捉できることを確認済み。`origin/develop` の `backend/core/settings.py`（guardian / django_extensions を含む）に対して不合格を返す（`!` 付きの旧形式では exit 1。第 2 周の「exit 1 のみ合格」形式では、痕跡を検出して exit 0＝不合格）

---

## TC-AUTO-07: guardian 専用設定が無い（AC-04）

判定: `git grep -q ANONYMOUS_USER_NAME -- ':(top)backend/'`

- **合格**: **exit 1**（痕跡が見つからなかった）
- **不合格**: exit 0（痕跡がある）・2 以上（実行エラー）
- **前提・`:(top)` の理由・「exit 1 のみ合格」の理由**: TC-AUTO-06 と同じ
- **false-green 検証（2026-10-14 再実施）**: 実装前も 0 件のため現状では合格してしまう。2026-08-22 の検証は差し替え前の `grep -r` に対するもので、`git grep` は**未追跡ファイルを見ない**ため現判定式の検証にはならなかった。そこでお試し用の一時リポジトリで `backend/core/dirty.py` に `ANONYMOUS_USER_NAME = 'AnonymousUser'` を書き、**`git add` した状態**で判定式を実行し、ルート・`backend/` の双方から不合格になることを確認した（第 1 周の `!` 付き旧形式では exit 1、現判定式では **exit 0**。どちらも「不合格」）。未追跡のままでは検出しない（現判定式では exit 1＝合格扱い）が、これは「リポジトリの実体＝CI が見るもの」を対象にする設計どおり。2026-10-14（fix-loop）に現判定式で再実測し、`git add` 後はルート・`backend/` とも exit 0、`git rm --cached` で未追跡に戻すと exit 1 を確認
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

判定 2a（ERROR の行は、既知の既存不具合 1 種だけ）: `test "$(grep -c 'ERROR' /tmp/i151_celery.log)" -eq "$(grep -c "unregistered task of type 'core.tasks.cache_maintenance_task'" /tmp/i151_celery.log)"`

判定 2b（Traceback は、既知の既存不具合 1 種だけ）: `test "$(grep -c 'Traceback' /tmp/i151_celery.log)" -eq "$(grep -c "KeyError: 'core.tasks.cache_maintenance_task'" /tmp/i151_celery.log)"`

> ログを一時ファイルに落としてから判定を行う。`docker compose logs` を 2 回実行すると、成功判定とエラー判定が**別々のスナップショット**を見ることになり、その間に書き込まれたエラーを取りこぼす。

準備 2（worker が登録しているタスクの一覧）:
```bash
docker compose exec -T celery celery -A core inspect registered > /tmp/i151_celery_registered.txt 2>&1
```

判定 3（beat スケジュールの `studylogs` 4 タスクがすべて登録されている）: 次の 4 行
- `grep -qE '^[[:space:]]+\* studylogs\.tasks\.update_daily_analytics_task$' /tmp/i151_celery_registered.txt`
- `grep -qE '^[[:space:]]+\* studylogs\.tasks\.send_study_reminders_task$' /tmp/i151_celery_registered.txt`
- `grep -qE '^[[:space:]]+\* studylogs\.tasks\.analyze_mistake_patterns_task$' /tmp/i151_celery_registered.txt`
- `grep -qE '^[[:space:]]+\* studylogs\.tasks\.cleanup_expired_suggestions_task$' /tmp/i151_celery_registered.txt`

- **合格**: 判定 1・2a・2b・3 のすべてが exit 0（直近 3 分に成功ログがある。ERROR / Traceback は既知の 1 種以外に無い。スケジュールされた studylogs のタスクがすべて登録されている）
- **不合格**: 非ゼロ
- **判定 2 を 2a・2b に改め、判定 3 を足した理由（2026-10-16・fix-loop）**: `/test` で旧判定 2（`! grep -qE 'ERROR|Traceback'`）が不合格になった。原因は I151 以前（2026-03-20 の I004）からある既存の不具合である。beat が 30 分ごとに `core.tasks.cache_maintenance_task` を送るが、`core` が `INSTALLED_APPS` に無いので worker が登録しておらず、届くたびに ERROR と Traceback を出して捨てている（`docs/reviews/I151_fix_diagnosis_20261016_1740.md`）。I151 の差分は `settings.py` の 2 行削除だけで、`celery.py` / `tasks.py` / celery の版は変わっていない。これまで合格していたのは、30 分周期のエラーが判定窓の 3 分に入らなかったからで、旧判定は**タイミング次第でしか既存エラーを検出できなかった**。新判定は、タスク名まで完全に指定した既知の 1 種だけを件数一致で除き、ほかの ERROR / Traceback が 1 行でもあれば件数がずれて不合格になる。既知の 1 種が窓に入らなくても 0 = 0 で同じ結果になり、タイミングに左右されない。判定 3 は、依存更新で登録そのものが壊れる退行を、タイミングに関係なく検出する
- **除外は暫定**: 既知の 1 種の除外は、別イシュー（起票予定:「celery の core.tasks が未登録で cache_maintenance_task が 30 分ごとに破棄される問題を修正」）のマージまでとする。そのイシューの受け入れ条件に「TC-AUTO-10 から除外を外しても合格すること」を入れる
- **false-green 検証（2026-10-16 実施）**: 下の「現行判定式・2026-10-16」の表を参照
- **ベースライン**: 実装前に成功ログを実測済み（`Task studylogs.tasks.update_daily_analytics_task[...] succeeded in 0.0103s`）。したがって前半の判定式が実際に成功ログを捕捉できることは確認済み

---

## TC-AUTO-11A: 本体依存＋pytest-django の固定値が一致する（AC-01・AC-10）

**実行タイミング: ステップ 1 完了後。** 宣言（requirements）と実インストール（pip freeze）の両方を判定する。宣言だけを見ると、再ビルド漏れで古いイメージのまま合格してしまう。

> **pytest の判定を含めない理由**: ステップ 1 時点の `pytest` は 8.3.4 のままが正しい。pytest の固定値判定を本 TC に混ぜると、ステップ 1 の「全 TC 合格」条件が原理的に満たせなくなる。pytest は TC-AUTO-11B としてステップ 2 で独立に判定する。

判定 A-1（宣言側・7 パッケージを 1 コマンドずつ確認。2026-10-14 の R6 で openai を追加し 6→7）: 「決定論ゲート（自動実走）」欄に宣言（`/code-review` が毎回実走）。
- `grep -qx 'Django==5.2.17' backend/requirements.txt`
- `grep -qx 'djangorestframework==3.18.0' backend/requirements.txt`
- `grep -qx 'django-cors-headers==4.9.0' backend/requirements.txt`
- `grep -qx 'django-filter==26.1' backend/requirements.txt`
- `grep -qx 'django-redis==7.0.0' backend/requirements.txt`
- `grep -qx 'openai==3.31.0' backend/requirements.txt`（2026-10-14 追加・R6 発動）
- `grep -qx 'pytest-django==4.14.0' backend/requirements-dev.txt`

準備（実インストール側のスナップショット）:
```bash
docker compose exec -T backend pip freeze > /tmp/i151_freeze.txt
```

判定 A-2（実インストール側・**宣言側と同じ 7 パッケージを全件**確認）:
- `grep -qx 'Django==5.2.17' /tmp/i151_freeze.txt`
- `grep -qx 'djangorestframework==3.18.0' /tmp/i151_freeze.txt`
- `grep -qx 'django-cors-headers==4.9.0' /tmp/i151_freeze.txt`
- `grep -qx 'django-filter==26.1' /tmp/i151_freeze.txt`
- `grep -qx 'django-redis==7.0.0' /tmp/i151_freeze.txt`
- `grep -qx 'openai==3.31.0' /tmp/i151_freeze.txt`（2026-10-14 追加・R6 発動）
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

E2E はログイン〜主要画面の通しを担保する。**「まっさらな DB への `migrate`」を同時に担保するのは CI 実行に限る**（CI は毎回新しいランナーで DB ボリュームが空）。ローカルの `e2e-init` は開発用 DB（`learning_app`）へ `migrate` と `seed_e2e` を流すため、まっさらな DB の検証にはならない。ローカルでのまっさらな DB の検証は TC-AUTO-09 が担う。

**合否は CI 記録で判定する（AC-13 の正式な判定）**:

**使う ID は `<job_id>` の 1 つだけ**（`gh pr checks 269 --json name,link` の E2E Tests (Playwright) 行の link 末尾）。ログもコミットも、この同じ job から取る。

準備 1（CI の E2E ジョブログを保存）:
```bash
gh run view --log --job <job_id> > /tmp/i151_e2e_ci.log
```

準備 0（同じ job がテストしたコミットを取得）:
```bash
gh api repos/osushi0404-dev/study-app-multitenant/actions/jobs/<job_id> -q .head_sha > /tmp/i151_e2e_run_sha.txt
```

判定 0（その job の後に、`docs/` 以外の変更が 1 つも無い）: `git diff --quiet "$(cat /tmp/i151_e2e_run_sha.txt)" HEAD -- ':(top)' ':(top,exclude)docs'`

判定 0b（手元に、`docs/` 以外の未コミットの変更が無い）: `git diff --quiet HEAD -- ':(top)' ':(top,exclude)docs'`

判定 0c（手元の HEAD が push 済みで、PR の head と同じ。記録用の docs コミットを push した後に判定する）: `test "$(git rev-parse HEAD)" = "$(gh pr view 269 --json headRefOid -q .headRefOid)"`

判定 1（Playwright の合格サマリ行がある）: `grep -qE ' [0-9]+ passed \(' /tmp/i151_e2e_ci.log`

判定 2（flaky・failed・skipped・did not run・interrupted の行が無い）: `! grep -qE ' [0-9]+ (flaky|failed|skipped|did not run|interrupted)$' /tmp/i151_e2e_ci.log`

- **合格**: 判定 0・0b・0c・1・2 とも exit 0
- **不合格**: 非ゼロ
- **ID を job の 1 つに絞った理由（2026-10-15・敵対的レビュー第 2 周）**: 第 1 周の版は、コミットを `<run_id>` から、ログを `--job <job_id>` から取っていた。`gh run view` は `--job` を渡すと位置引数の run_id を無視し、その job のログを返す。そのため、新しい run_id と旧 job_id（本文の false-green 検証欄にある 97222730997）を組み合わせると、旧 run（ac7a1dd・openai 1.3.0）のログで判定 0・1・2 がすべて合格した（メインセッションで再現。`gh run view 38711268663 --log --job 97222730997` の出力に `openai==1.3.0` と `7 passed (15.4s)` が含まれる）。ログとコミットを同じ job_id から取れば、組み合わせの誤りは起こらない
- **判定 0b・0c を足した理由（同上）**: 判定 0 は「job のコミット」と「手元の HEAD」を比べる。手元にコード変更が未コミットで残っている場合や、手元の HEAD が PR の head とずれている場合（push 忘れ、remote 側だけにある merge コミット）は、判定 0 だけでは見逃す。なお pull_request の CI がテストするのは develop との合成（`refs/pull/269/merge`）で、job の後に develop が進んだ場合は判定 0 では検出しない。I151 のマージ前に develop が進んだら、CI を再実行してから判定する
- **判定 0 を足した理由（2026-10-15・敵対的レビュー第 1 周）**: 旧手順は run を選ぶ条件が無かった。そのため、2026-10-14 の再実施記録は 2026-08-23 の run 32651105381（head ac7a1dd・openai 1.3.0・I159 の lockfile 取り込み前）を根拠にしていた。その後の R6 再固定や I159 取り込みの後で E2E が通ることは示していなかった。判定 0 で、根拠にする run を「その後にコード・依存・設定の変更が無い」コミットに結び付ける。記録用の docs コミットは許す（「job の SHA が PR の head と一致」にすると、結果を記録するコミット自体が head を進めるため、永遠に合格できない）。判定 0c が比べるのは job の SHA ではなく「手元の HEAD と PR の head」で、記録コミットを push した後なら一致するので、この問題は起きない。run の後に `docs/` 以外が 1 行でも変わっていれば exit 1、run の SHA が手元に無ければ exit 128 で、どちらも不合格
- **判定 2 を足した理由（2026-10-14・fix-loop）**: `e2e/playwright.config.ts` は `retries: 2` を条件なしで設定している。1 回失敗して再試行で通ったテスト（flaky）でも、Playwright は exit 0 を返す。Django 5.2 化で生じた間欠的な不具合を見逃さないよう、flaky が 0 件であることを判定する（CI 設定 `e2e.yml` と `playwright.config.ts` は I151 の範囲外のため変更しない）
- **判定 2 の `!` がファイル不在で合格に反転しない理由**: ログが保存されていなければ判定 1 が exit 2 で不合格になるため、TC 全体として不合格になる
- **false-green 検証（2026-10-14 実施）**: 実際の CI ログ（run 32651105381・job 97222730997）で判定 1・2 とも exit 0（`7 passed (15.4s)`・flaky 等の行なし）。`1 flaky` 行・`1 failed` 行を含むダミーログでは、判定 2 の grep が一致して不合格になることを確認

**ローカルで実行する場合（補助・合否には使わない）**:

準備 L1（`backend` と `e2e-init` のイメージを作り直す。`run` は依存サービスのイメージを自動では作り直さないため）:
```bash
docker compose --profile e2e build backend e2e-init
```

準備 L1b（作り直した `backend` で起動し直す）:
```bash
docker compose up -d --wait backend
```

準備 L1c（E2E が実際に叩く `backend` コンテナの中身を記録）:
```bash
docker compose exec -T backend pip freeze > /tmp/i151_backend_freeze.txt
```

判定 L0b（`backend` コンテナが更新後の Django である）: `grep -qx 'Django==5.2.17' /tmp/i151_backend_freeze.txt`

準備 L2（`e2e-init` イメージの中身を記録）:
```bash
docker compose --profile e2e run --rm --no-deps --entrypoint pip e2e-init freeze > /tmp/i151_e2einit_freeze.txt
```

判定 L0（`e2e-init` イメージが更新後の Django である）: `grep -qx 'Django==5.2.17' /tmp/i151_e2einit_freeze.txt`

実行（flaky も不合格にする）:
```bash
docker compose rm -f e2e-init
docker compose --profile e2e run --rm e2e npx playwright test --fail-on-flaky-tests
```

- **備考**: `docker compose rm -f e2e-init` は `common-commands.md` に記載の必須手順（`run --rm` は対象サービスのみ削除するため）。ローカル実行には、`common-commands.md` の手順に従ってレート制限を無効にした backend が必要
- **準備 L1・判定 L0 を足した理由（2026-10-14・fix-loop）**: 旧手順は `e2e-init` を作り直さなかった。`e2e-init` は `./backend` をマウントするのでコードは最新になるが、ライブラリはイメージ作成時のまま残る。2026-10-14 時点の手元イメージは 5 か月前のもので（Django 4.2.7・django-guardian 2.4.0）、旧手順のままだと Django 4.2 のまま合格していた。2026-10-14 に準備 L1 で作り直し、判定 L0 が exit 0 になることを確認
- **`backend` も対象に足した理由（2026-10-15・敵対的レビュー第 1 周）**: E2E が実際に叩くのは `backend` コンテナで、`e2e-init` は migrate と seed を流すだけである。2026-10-15 時点の手元の `backend` は、別ブランチ（develop）のイメージ（Django 4.2.30）で動いていた。そのため、`e2e-init` だけを作り直す旧手順では判定 L0 が exit 0 のまま、E2E が Django 4.2 の API に対して流れていた

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
- 判定 2（除去した 2 パッケージが記録に現れない＝再ビルド後の実体である）: `! grep -qiE 'django[-_]guardian' docs/tests/open/I151_pip_freeze.txt` と `! grep -qiE 'django[-_]extensions' docs/tests/open/I151_pip_freeze.txt` の 2 行
- **判定式の変遷**: 2026-10-07 に `! grep -qE 'django-(guardian|extensions)=='` を 2 行に分割（正規表現の `|` が gate のチェーン文字ガードに掛かるため）。2026-10-14（敵対的レビュー第 1 周）で厳格化した。旧判定 1 は `-x` が無く `Django==5.2.170` やコメント行に部分一致していた。旧判定 2 は `django-guardian==` 固定で、`django_guardian==`（pip freeze はアンダースコア表記も出す）・大文字表記・`@ file://` 形式を見逃していた
- **第 2 周での変更（2026-10-14）**: 第 1 周で付けた行頭アンカー `^` を外した。アンカー付きだと、pip freeze の editable install の形（`# Editable install with no version control (django-guardian==2.4.0)` / `-e /src/django-guardian` / `-e git+...#egg=django_extensions`）を見逃すため。追加で検証し、これら 3 形と第 1 周の不合格形がすべて不合格（exit 1）、実記録が合格（exit 0）になることを確認した
- **false-green 検証（2026-10-14 実施）**: 実記録で判定 1・判定 2（2 行）がすべて exit 0。不合格にすべき 5 形（`Django==5.2.170` → 判定 1 が exit 1／コメント行のみ → 判定 1 が exit 1／アンダースコア表記の旧 freeze → 判定 2 の両行が exit 1／`Django-Guardian==` → guardian 行が exit 1／`django-extensions @ file://` → extensions 行が exit 1）と、ファイル不在（判定 1 が exit 2）をすべて確認

- 判定 3（2026-10-15 追加）: 記録が、宣言側（TC-AUTO-11A / 11B の判定 A-1・B-1）の全 8 固定値と行全体で一致する。決定論ゲート欄に 7 行で宣言（Django は判定 1 と同じ）
- **判定 3 を足した理由（2026-10-15・敵対的レビュー第 1 周）**: 判定 1・2 は Django の 1 行と、除去した 2 パッケージが無いことしか見ていなかった。そのため、R6 の再ビルド前の古い記録（openai 1.3.0・脆弱な anyio 3.7.1。`git show bca4503:docs/tests/open/I151_pip_freeze.txt`）でも、`Django==5.2.17` の 1 行だけのファイルでも全判定が合格した。R6 の後に記録の更新を忘れても、`/code-review` の決定論ゲートは OK のままだった。判定 3 で、記録を宣言側の固定値に縛る
- **false-green 検証（2026-10-15 実施）**: 現在の記録で判定 3 の 7 行すべて exit 0。R6 前の記録（bca4503 版）では `openai==3.31.0` の行が exit 1。`Django==5.2.17` だけのファイルでは 7 行すべて exit 1
- 判定 4（2026-10-15・敵対的レビュー第 2 周で追加）: 宣言ファイル（requirements / requirements-dev）には書かれていない推移的依存 `anyio==4.15.1`（R6 で CVE を解消した対象）と `kombu==5.6.2`（イシュー決定 7-C で据え置きを確認する対象）が記録にある。判定 3 だけでは、コンテナを作り直さずに `backend/requirements*.txt` を連結しただけのファイルでも判定 1〜3 がすべて合格した（判定 3 は宣言の固定値をもう一度書いたものなので、宣言そのものと一致するだけ）。判定 4 は、記録が「実際のコンテナから取った freeze」であることを判定する。再ビルドで anyio / kombu が変わった場合は、記録の更新と同時にこの 2 行も更新する
- **判定 4 の false-green 検証（2026-10-15 実施）**: 現在の記録で 2 行とも exit 0。requirements 2 ファイルを連結したファイルでは 2 行とも exit 1。R6 前の記録（bca4503 版・anyio 3.7.1）では anyio の行が exit 1
- **合格**: 判定 1・2・3・4 の**すべてが exit 0**
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

判定 3（`requirements.txt` を触ったコミットが 2 つ＝1 段目と、R6 発動による openai 再固定の 2 つだけ）:
```bash
test "$(wc -l < /tmp/i151_req_commits.txt)" -eq 2
```

> `wc -l < file` はリダイレクトであってパイプではないため、本文書冒頭の「コマンドを複合化しない」原則を満たす。

判定 4（`requirements.txt` を触ったコミットがどちらも `fix(I151)`＝2 段目の chore には本体依存が入っていない）: `test "$(grep -c 'fix(I151)' /tmp/i151_req_commits.txt)" -eq 2`

- **判定 3・4 の改訂（2026-10-14・R6 発動）**: anyio の新規 CVE 解消のため、openai の再固定を **3 つ目の `fix(I151)` コミット（055aa11）** として足した（計画書 AC-17 追補）。独立したコミットにしたのは、変更の出どころを追えるようにするため（2026-10-15 訂正: 当初は「この再固定だけを取り消せるように」と書いていたが、取り消すと openai 1.3.0（`anyio<4`）に戻り、anyio の CVE で必須チェック `pip-audit` が必ず落ちるため、単独では取り消せない。問題が出たときは計画書 §8 の前方修正で直す）。旧判定（requirements.txt を触ったコミットが 1 つ）は、この追補で 2 になる

準備 5（R6 コミットの変更ファイル一覧）:
```bash
git log origin/develop..HEAD --grep='^fix(I151): openai' --name-only --format= > /tmp/i151_r6_files.txt
```

準備 6（R6 コミットの差分）:
```bash
git log origin/develop..HEAD --grep='^fix(I151): openai' -p --format= > /tmp/i151_r6_diff.txt
```

判定 9（R6 コミットが変えたのは `requirements.txt` だけ）: `grep -qx 'backend/requirements.txt' /tmp/i151_r6_files.txt` と `test "$(grep -c . /tmp/i151_r6_files.txt)" -eq 1` の 2 行

準備 7（R6 コミットの追加・削除行数。git 自身が全行を数える）:
```bash
git log origin/develop..HEAD --grep='^fix(I151): openai' --numstat --format= > /tmp/i151_r6_numstat.txt
```

判定 10（R6 コミットの変更行は openai の 1 行の置き換えだけ）: `grep -qx -- '-openai==1.3.0' /tmp/i151_r6_diff.txt` と `grep -qx -- '+openai==3.31.0' /tmp/i151_r6_diff.txt` と `grep -qxP '1\t1\tbackend/requirements.txt' /tmp/i151_r6_numstat.txt` の 3 行

準備 3（2 段目のコミットの変更ファイル一覧）:
```bash
git log origin/develop..HEAD --grep='^chore(I151)' --name-only --format= > /tmp/i151_chore_files.txt
```

準備 4（2 段目のコミットの差分）:
```bash
git log origin/develop..HEAD --grep='^chore(I151)' -p --format= > /tmp/i151_chore_diff.txt
```

判定 5（2 段目のコミットがちょうど 1 つ）: `test "$(grep -c 'chore(I151)' /tmp/i151_commits.txt)" -eq 1`

判定 6（2 段目が `requirements-dev.txt` を変えている）: `grep -qx 'backend/requirements-dev.txt' /tmp/i151_chore_files.txt`

判定 7（2 段目が変えたファイルはそれ 1 つだけ）: `test "$(grep -c . /tmp/i151_chore_files.txt)" -eq 1`

準備 8（2 段目のコミットの追加・削除行数）:
```bash
git log origin/develop..HEAD --grep='^chore(I151)' --numstat --format= > /tmp/i151_chore_numstat.txt
```

判定 8（2 段目の変更行は pytest の 1 行の置き換えだけ）: `grep -qx -- '-pytest==8.3.4' /tmp/i151_chore_diff.txt` と `grep -qx -- '+pytest==9.0.3' /tmp/i151_chore_diff.txt` と `grep -qxP '1\t1\tbackend/requirements-dev.txt' /tmp/i151_chore_numstat.txt` の 3 行

- **件数判定を `--numstat` に替えた理由（2026-10-15・敵対的レビュー第 1 周）**: 旧判定 `grep -cE '^[-+][^-+]'` は、差分行のうち「+/- の直後が +/- の行」と空行を数えなかった。そのため `+--extra-index-url ...`（取得元の追加）・`+-e git+...`（editable install）・`+-r other.txt`・空行の追加を 2 段目や R6 コミットに混ぜても件数が 2 のままで、判定 6〜10 がすべて合格していた。`--numstat` は git 自身が追加・削除行を全行数えるため、行の中身による数え漏れが無い。差分ヘッダ（`---` / `+++`）と区別する必要も無くなる
- **false-green 検証（2026-10-15 実施）**: 一時リポジトリで、正しい分け方（pytest 行だけ）→ exit 0。`--extra-index-url` の追加・`-e git+...` の追加・空行の追加・`-r other.txt` の追加 → いずれも `2	1	...` となり exit 1。空コミット → 出力なしで exit 1。実リポジトリでは 2 段目（3a6e0e8）・R6（055aa11）とも `1	1	...` で exit 0

準備 9（`requirements-dev.txt` を触ったコミットの一覧）:
```bash
git log origin/develop..HEAD --oneline -- backend/requirements-dev.txt > /tmp/i151_dev_commits.txt
```

判定 11（`requirements-dev.txt` を触ったコミットはちょうど 2 つで、`fix(I151)` 1 つ（pytest-django）と `chore(I151)` 1 つ（pytest））: `test "$(wc -l < /tmp/i151_dev_commits.txt)" -eq 2` と `test "$(grep -c 'fix(I151)' /tmp/i151_dev_commits.txt)" -eq 1` と `test "$(grep -c 'chore(I151)' /tmp/i151_dev_commits.txt)" -eq 1` の 3 行

- **判定 11 を足した理由（2026-10-15・敵対的レビュー第 2 周）**: 判定 3・4 はコミット数を `requirements.txt` についてしか数えていなかった。`requirements-dev.txt` は 2 段目の中身だけを照合していた。そのため、pytest 9 を前提にするプラグインを足す 3 つ目のコミット（例: `test(I151): ...`）が混ざっても判定 1〜10 はすべて合格し、「2 段目を落とせば pytest 9 を取り消せる」（計画書 §8）が成り立たなくなっていた
- **判定 11 の false-green 検証（2026-10-16 実施）**: 一時リポジトリで、fix・chore の 2 コミットでは 3 行とも exit 0。3 つ目の `test(I151): add plugin`（`requirements-dev.txt` に 1 行追加）を足すと、件数の行が exit 1
- **合格**: 判定 1〜11 の**すべてが exit 0**
- **判定 5〜8 を足した理由（2026-10-14・fix-loop）**: 判定 2 は件名に `chore(I151)` を含むコミットがあることしか見ていなかった。そのため、pytest を 1 段目にまとめて 2 段目を空のコミットにするような誤った分け方でも、判定 1〜4 がすべて合格していた。それでは「2 段目のコミットを落とすだけで pytest 9 を取り消せる」という退避手順（計画書 §8）が成り立たない
- **false-green 検証（2026-10-14 実施）**: 実リポジトリで判定 5〜8 がすべて exit 0（2 段目＝3a6e0e8 は `requirements-dev.txt` の pytest 行だけを変更）。一時リポジトリでの結果は次のとおり。2 段目が空コミット → 判定 6・7・8 がすべて不合格。2 段目に pytest 以外の行が混入 → 判定 8 の件数判定が不合格。正しい分け方 → 全判定が合格
- **判定 4 を足した理由（2026-10-14・敵対的レビュー第 2 周）**: 判定 1〜3 だけでは、「requirements.txt を触ったコミットが 1 つある」ことしか分からず、それが 1 段目かどうかは確かめていなかった。依存更新を全部 2 段目（chore）に入れるような誤った分け方でも合格してしまう。2026-10-14 に実リポジトリで exit 0（該当コミット 4877e18 は `fix(I151)`）、chore だけのダミー記録で exit 1 を確認
- **不合格**: 非ゼロ
- **実装前の状態（false-green 検証）**: `fix(I151)` コミットが存在しないため **exit 1**

---

## TC-AUTO-17: レート制限のカウンタ保存が実コンテナで機能する（AC-21・security-review 由来）

**なぜ必要か**: `@ratelimit`（ログイン 5/5m・登録 10/5m・パスワードリセット 3/15m 等のブルートフォース防御）は、カウンタを **`default` キャッシュ**に保存する（`settings.py` の `RATELIMIT_USE_CACHE = 'default'`）。その `default` は本 PR で **django-redis 5.4.0 → 7.0.0（メジャー 2 段）** に更新され、しかも `IGNORE_EXCEPTIONS: True` が設定されているため**失敗しても例外が出ずに握り潰される**。

> **訂正（2026-10-15・敵対的レビュー第 1・2 周）**: 当初は、握り潰された結果「レート制限がフェイルオープンする（総当たり防御が消える）」と書いていた。実際は逆である。django-ratelimit は、カウンタを取得できないとき（`count is None`）、既定の `RATELIMIT_FAIL_OPEN=False` により**遮断**する（`django_ratelimit/core.py:249-252`。新イメージで確認）。つまりカウンタ操作が壊れると、正しいパスワードのログインを含め、`@ratelimit` 付きの全経路が 403 になる（**フェイルクローズ＝可用性の喪失**）。この TC が検出するのは「django-redis 7 でカウンタ操作が壊れて、全利用者がログインできなくなる」退行である。Redis 障害時の扱いは計画書の残余リスク申し送りを参照

**既存テストでは検出できない**: `backend/core/tests/test_I127_throttling.py` は 4 つのキャッシュをすべて `LocMemCache` に差し替えるため、django-redis は一度も実行されない。つまり 94 件が全部 pass しても、実環境でカウンタ操作が壊れている可能性が残る（2026-10-15 訂正: 当初は「レート制限が黙って無効化される」と書いていた。実際の症状は上の訂正注記のとおり、全経路が 403 になる側である）。

django-ratelimit が使うキャッシュ操作は `cache.add` と `cache.incr` の 2 つ（`django_ratelimit.core` を実測）。これを**再ビルド後の実コンテナ**で確認する。

準備:
```bash
docker compose exec -T backend python manage.py shell -c "from django.core.cache import cache; cache.delete('i151_rl_probe'); print('add_new', cache.add('i151_rl_probe', 0, 60)); print('add_dup', cache.add('i151_rl_probe', 0, 60)); print('incr1', cache.incr('i151_rl_probe')); print('incr2', cache.incr('i151_rl_probe')); cache.delete('i151_rl_probe')" > /tmp/i151_rl.txt 2>&1
```

判定 1（新規キーの追加が成功する）: `grep -q 'add_new True' /tmp/i151_rl.txt`

判定 2（既存キーの重複追加が拒否される）: `grep -q 'add_dup False' /tmp/i151_rl.txt`

判定 3（カウンタが加算される）: `grep -q 'incr2 2' /tmp/i151_rl.txt`

- **合格**: 判定 1〜3 の**すべてが exit 0**
- **不合格**: 非ゼロ（＝カウンタが機能していない。django-ratelimit はこのとき遮断側に倒れるため、`@ratelimit` 付きの全経路が 403 になる。2026-10-15 訂正）
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
| TC-AUTO-06 | ✅ 合格 | 2026-08-24 | 判定 1・2 とも exit 0（**当時の `!` 付き旧形式での値**。旧形式では exit 0 が合格。現行の合格条件は exit 1 で、2026-10-14 の再実施を参照）。**当初の `grep -r` は `backend/.venv` の pygments に反応して false-red となったため `git grep` へ是正** |
| TC-AUTO-07 | ✅ 合格 | 2026-08-24 | exit 0（**当時の `!` 付き旧形式での値**。現行の合格条件は exit 1 で、2026-10-14 の再実施を参照） |
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
| TC-AUTO-16 | ✅ 合格 | 2026-10-14 | 第 2 周：判定 4（requirements.txt を触ったコミットが `fix(I151)`）が exit 0。fix-loop：判定 5〜8（2 段目＝pytest 単独）もすべて exit 0 |
| TC-AUTO-00 | ✅ 合格 | 2026-10-14 | R6 発動：openai 3.31.0 で 4 イメージ（backend / celery / celery-beat / e2e-init）を作り直した後、`docker compose up -d --wait` が exit 0（6 サービス healthy） |
| TC-AUTO-01 | ✅ 合格 | 2026-10-14 | R6 発動：再固定**前**は exit 1（`anyio 3.7.1` に `PYSEC-2026-4024` / `PYSEC-2026-4025`）。再固定後は `No known vulnerabilities found`・exit 0 |
| TC-AUTO-02 | ✅ 合格 | 2026-10-14 | R6 発動：再固定後に `No known vulnerabilities found`・exit 0 |
| TC-AUTO-03 | ✅ 合格 | 2026-10-14 | R6 発動：再固定後に `94 passed, 5 warnings in 21.00s`。判定（サマリ行の完全一致）exit 0 |
| TC-AUTO-04 | ✅ 合格 | 2026-10-14 | R6 発動：`System check identified no issues (0 silenced).` |
| TC-AUTO-08 | ✅ 合格 | 2026-10-14 | R6 発動：`No changes detected` |
| TC-AUTO-09 | ✅ 合格 | 2026-10-14 | R6 発動：使い捨て DB `migrate_check` に 58 マイグレーションを適用して exit 0。検証後に破棄 |
| TC-AUTO-10 | ✅ 合格 | 2026-10-14 | R6 発動：コンテナ作り直しの後、直近 3 分に成功ログ 9 件・`ERROR` / `Traceback` 0 件 |
| TC-AUTO-11A | ✅ 合格 | 2026-10-14 | R6 発動：宣言側（決定論ゲート・`openai==3.31.0` を追加）・実インストール側とも全件 exit 0 |
| TC-AUTO-15 | ✅ 合格 | 2026-10-14 | R6 発動：作り直し後の `pip freeze` で `I151_pip_freeze.txt` を更新（openai 3.31.0・anyio 4.15.1。作り直しで推移的依存の amqp 5.4.1 / billiard 4.3.1 なども更新された。kombu は 5.6.2 のまま）。判定 1・2 とも exit 0 |
| TC-AUTO-16 | ✅ 合格 | 2026-10-14 | R6 発動：判定 3・4 を「requirements.txt を触ったコミットが 2 つ、どちらも `fix(I151)`」に改め、判定 9・10（R6 コミット 055aa11 は openai の 1 行だけ）を追加。すべて exit 0 |
| TC-AUTO-17 | ✅ 合格 | 2026-10-14 | R6 発動：`add_new True` / `add_dup False` / `incr1 1` / `incr2 2` |
| （参考） | — | 2026-10-14 | R6 発動：`problems/ai_generator.py` を実際に呼び、更新前と同じく `openai.ChatCompletion` の例外 → 代替問題が返ることを確認（挙動不変。v1 以降の API への書き換えは別イシュー） |
| TC-AUTO-13 | ✅ 合格 | 2026-10-14 | fix-loop：CI 記録（run 32651105381）で判定 1・2 とも exit 0（`7 passed (15.4s)`・flaky / failed / skipped の行なし）。ローカル補助手順の判定 L0 も、`e2e-init` の作り直し後に exit 0（Django==5.2.17） |

### R6・I159 取り込み後の CI 系の再実施（2026-10-15・敵対的レビュー第 1 周の是正）

2026-10-14 の再実施表のうち、TC-AUTO-12 / 13 / 14 は R6（055aa11 / 9a6f809）と I159 の取り込み（729dfbd / 5c31947）**より前**の状態を根拠にしていた。TC-AUTO-13 の CI run 32651105381 は 2026-08-23 の ac7a1dd（openai 1.3.0）。TC-AUTO-12 / 14 は R6 前の第 1・2 周の実行。そのため、最新のコードで取り直した。

**記録していなかった CI 失敗**: R6 を push した 9a6f809 の CI run 38564774555 は **FAILURE** だった（失敗は `Frontend Lint & Security` の npm audit だけ。Backend Lint & Security・Backend Tests・Frontend Type Check・Frontend Tests の 4 つは success。同じ SHA の E2E run 38564774645 も success）。原因は frontend の推移的依存 proxy-addr / shell-quote の critical で、I151 の変更（backend のみ）が原因ではない。I159（#276）で是正し、I151 へ取り込んだ（5c31947）。取り込み後の run 38711268649（CI）/ 38711268663（E2E）は全 6 チェックが success。

| TC | 結果 | 実施日 | 備考 |
|---|---|---|---|
| TC-AUTO-12 | ✅ 合格 | 2026-10-15 | I159 の lockfile 取り込み後の作業ツリーで、frontend コンテナから実行。判定 1（`Test Suites: 3 passed, 3 total`）・判定 2（`Tests: 10 passed, 10 total`）とも exit 0。CI の Frontend Tests（run 38711268649・head 5c31947・lockfile から `npm ci`）でも同じ 2 行 |
| TC-AUTO-13 | ✅ 合格 | 2026-10-15 | run 38711268663・job 116342939620（head 5c31947＝R6 と I159 取り込みの後）。判定 0（run 後の `docs/` 以外の差分なし）exit 0・判定 1 exit 0（`7 passed (14.9s)`）・判定 2 exit 0（flaky / failed / skipped 等の行なし）。判定 0 の false-green 検証: 旧根拠の run 32651105381（ac7a1dd）では exit 1、存在しない SHA では exit 128 で、どちらも不合格 |
| TC-AUTO-14 | ✅ 合格 | 2026-10-15 | PR head 5c31947 で判定 1（SUCCESS 以外 0 件）・判定 2（チェック 6 件）とも exit 0 |
| TC-AUTO-16 | ✅ 合格 | 2026-10-15 | 判定 8・10 を `--numstat` 版へ替えて再実行。2 段目 `1	1	backend/requirements-dev.txt`・R6 `1	1	backend/requirements.txt` で exit 0 |
| TC-AUTO-13 | ✅ 合格 | 2026-10-16 | 第 2 周の手順（ID は job の 1 つ）で再実施。job 116375327027（run 38721027473・head 94271e4＝第 2 周の是正を push した head）。判定 0（job 後の `docs/` 以外の差分なし）・0b（未コミットの非 docs 変更なし）・0c（手元 HEAD 94271e4 = PR head）・1（`7 passed (15.6s)`）・2（flaky 等の行なし）がすべて exit 0。false-green 検証: 旧 job 97222730997 から取った SHA（ac7a1dd）では判定 0 が exit 1。新 run_id と旧 job_id を組み合わせる誤りは、ID を 1 つにしたので起こらない |
| TC-AUTO-14 | ✅ 合格 | 2026-10-16 | PR head 94271e4 で全 6 チェック SUCCESS（判定 1・2 とも exit 0） |
| TC-AUTO-15 | ✅ 合格 | 2026-10-15 | 判定 3（全 8 固定値・7 行）・判定 4（`anyio==4.15.1` / `kombu==5.6.2`）とも、現在の記録で exit 0。false-green 検証は TC 本文のとおり（R6 前の記録・requirements の連結・Django 1 行だけのファイルで不合格）。決定論ゲートでの実走は、次回の `/code-review` で行われる |
| TC-AUTO-16 | ✅ 合格 | 2026-10-16 | 判定 11: 実リポジトリで `requirements-dev.txt` を触ったコミットは 2 件（4877e18 fix / 3a6e0e8 chore）で、3 行とも exit 0。false-green 検証: 一時リポジトリで 3 つ目のコミット（`test(I151): add plugin`）を足すと、件数の行が exit 1 |
| TC-AUTO-10 | ❌→✅ | 2026-10-16 | `/test` で旧判定 2 が不合格（既存不具合 `core.tasks.cache_maintenance_task` の未登録エラーが窓に入った）。fix-loop で判定 2a・2b・3 へ改め、再実行で判定 1（succeeded 10 件）・2a・2b・3（4 行）すべて exit 0。不合格時の実ログでも新判定 2a・2b は exit 0（下の再発防止記録） |
| （環境復旧） | ✅ | 2026-10-16 | ユーザー指示で `docker compose build backend celery celery-beat` → `docker compose up -d --wait`（6 サービス healthy）。作り直し後、TC-AUTO-11A 判定 A-2 相当（全 8 固定値＋anyio 4.15.1）が backend・celery の両コンテナで exit 0。backend の `pip freeze` は `I151_pip_freeze.txt` と完全に一致。TC-AUTO-03 `94 passed, 5 warnings in 21.20s`（判定 exit 0）・TC-AUTO-01 `No known vulnerabilities found`・TC-AUTO-17 `add_new True` / `add_dup False` / `incr1 1` / `incr2 2` |

> **手元環境の注意（2026-10-15 確認・2026-10-16 復旧済み）**: 手元の `backend` コンテナは、このブランチのコードをマウントしたまま、別ブランチ（develop）で作ったイメージ（Django 4.2.30）で動いていた（同じ compose プロジェクトを複数のブランチで共有しているため）。backend 系 TC を手元で再実行するときは、先に `docker compose build backend celery celery-beat` で作り直し、TC-AUTO-11A 判定 A-2 が exit 0 になることを確かめてから実行する。上の CI 系 3 TC は CI（毎回ビルド）と frontend コンテナだけを使うので、この状態の影響を受けない。

### false-green 検証の記録（計画時点・2026-08-22 実施済み）

否定・回帰系 TC が実際に不合格を返せることを、実装前の状態またはダミー注入で確認した。**この表の exit code は、2026-08-22 時点の判定式（TC-AUTO-06 / 07 は `!` 付きの旧形式）での値**であり、当時の合格条件は exit 0 だったので、exit 1＝不合格である。現行の判定式での検証は、下の「現行判定式・2026-10-14」の表を参照（合格条件は TC 一覧の『合格条件』列）。

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
| TC-AUTO-16 | 判定 5〜8（2 段目＝pytest 単独） | 一時リポジトリで「2 段目が空コミット」「2 段目に余計な行」「正しい分け方」を作成 | 空コミットは判定 6〜8 が不合格・余計な行は判定 8 の件数判定が不合格・正しい分け方は全合格 |
| TC-AUTO-13 | 判定 2（flaky 等の行なし） | `1 flaky` / `1 failed` の行を含むダミーログ | grep が一致して判定 2 が不合格 |
| TC-AUTO-07 | `git grep -q ANONYMOUS_USER_NAME -- ':(top)backend/'`（合格条件 exit 1） | 一時リポジトリで痕跡を `git add`、その後 `git rm --cached` | 追跡中はルート・`backend/` とも exit 0（不合格）、未追跡に戻すと exit 1 |

### false-green 検証の記録（現行判定式・2026-10-16 実施・fix-loop）

| TC | 判定式 | 検証方法 | 結果 |
|---|---|---|---|
| TC-AUTO-10 | 判定 2a（ERROR の数＝既知 1 種の数）・2b（Traceback の数＝既知の KeyError の数） | 一時ディレクトリにログを 6 種作成: 成功のみ／既知の 1 種のみ／既知＋別の ERROR／既知＋別の Traceback／別のエラーのみ／2026-10-16 の実ログ | 成功のみ・既知のみ・実ログは 2a・2b とも exit 0。別の ERROR を足すと 2a が exit 1、別の Traceback を足すと 2b が exit 1、別のエラーのみは 2a・2b とも exit 1 |
| TC-AUTO-10 | 判定 3（studylogs 4 タスクの登録） | 実際の `inspect registered` の出力／そこから `send_study_reminders_task` を除いた出力／空ファイル | 実出力は 4 行とも exit 0。1 件欠けると該当行が exit 1。空ファイルは 4 行とも exit 1 |

### 機構の事前検証（計画時点・2026-08-22 実施済み）

| 対象 | 検証内容 | 結果 |
|---|---|---|
| TC-AUTO-09 | `docker compose exec -e DB_NAME=migrate_check` が Django 設定に届くか | `settings.DATABASES['default']['NAME'] = migrate_check` を確認 |
| TC-AUTO-10 | 成功ログの grep パターンが実際のログに一致するか | 実装前のログで `Task studylogs.tasks.update_daily_analytics_task[...] succeeded` に一致 |
| TC-AUTO-14 | `gh pr checks --json` の判定式が動くか | PR #256 に対して `0` を確認 |

---

## 再発防止記録（2026-10-16・fix-loop: TC-AUTO-10 判定 2 の不合格）

- **なぜ失敗したか**: `/test` で TC-AUTO-10 の旧判定 2（`! grep -qE 'ERROR|Traceback'`）が不合格になった。原因は I151 以前（2026-03-20 の I004）からある既存の不具合である。beat が 30 分ごとに `core.tasks.cache_maintenance_task` を送るが、`core` が `INSTALLED_APPS` に無いため worker が登録しておらず、届くたびに ERROR と Traceback を出して捨てている。I151 の差分（`settings.py` の 2 行削除）は関係しない。これまでの実施（2026-08-24 / 2026-10-14）が合格していたのは、30 分周期のエラーが判定窓の 3 分に入らなかったからである。2026-10-16 はコンテナを作り直している間に溜まったメッセージが起動時に一斉に届いたので、窓に入った。**判定がタイミング次第でしか既存エラーを検出できない設計だった**ことが、本当の弱点である
- **何を変えたか**（docs のみ・コードは変えていない。計画外の実装を I151 に混ぜないため）:
  - 判定 2 を 2a・2b に改めた。タスク名まで完全に指定した既知の 1 種だけを件数一致で除き、それ以外の ERROR / Traceback が 1 行でもあれば不合格になる。既知の 1 種が窓に入るかどうかに関係なく、同じ結果になる
  - 判定 3 を追加した。`inspect registered` で、beat スケジュールの studylogs 4 タスクがすべて登録されていることを、タイミングに関係なく確かめる（依存更新で登録が壊れる退行を検出する）
  - 手動 No.3 の期待結果を同じ書きぶりへ揃えた
  - 失敗注入で検証した（上の「false-green 検証の記録（現行判定式・2026-10-16 実施・fix-loop）」）
- **セキュリティ上の考慮点**: 該当なし。捨てられているのは引数なしのキャッシュ統計タスクで、認証・認可・入力・機密データのいずれにも関わらない。除外は ERROR と Traceback それぞれの件数一致で、タスク名まで完全に指定しており、別のエラーを隠さない（別の ERROR / Traceback を 1 つ足したログで不合格になることを確認）
- **次回どう防ぐか**:
  - 根治は別イシューで行う（起票予定:「celery の core.tasks が未登録で cache_maintenance_task が 30 分ごとに破棄される問題を修正（キャッシュ統計も取得できていない）」）。登録方式と、何もしていないタスクを残すか消すかは、そちらで決める。そのイシューの受け入れ条件に「TC-AUTO-10 から既知 1 種の除外を外しても合格すること」を入れ、暫定の除外が残り続けないようにする
  - ログの時間窓だけで「エラーが無い」を判定する TC は、周期の長いエラーを見逃す。今後は、窓に頼らない状態の確認（登録一覧・設定の照合など）を組み合わせる。この観点は /retro で、テストテンプレートとレビュー観点への反映を判断する
