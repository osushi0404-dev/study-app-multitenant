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
| TC-AUTO-03 | backend テストが 94 件 pass | AC-11 | ステップ 1・2 |
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

## TC-AUTO-03: backend テストが 94 件 pass（AC-11）

exit 0 と件数の両方を判定する（件数を見ないと skip 化による緑化を検出できない）。

準備:
```bash
docker compose exec -T backend python -m pytest -q > /tmp/i151_pytest.log 2>&1
```

判定 1（件数が 94 ちょうど）:
```bash
grep -qE '^94 passed' /tmp/i151_pytest.log
```

判定 2（skip / xfail / deselect が 0 件）:
```bash
! grep -qE 'skipped|xfailed|deselected' /tmp/i151_pytest.log
```

- **合格**: exit 0（全件 pass・**94 件ちょうど**・skip / xfail / deselect が 0 件）
- **不合格**: 非ゼロ（失敗があるか、件数が 94 でないか、skip 等が混入した）
- **skip 判定を足した理由**: 件数だけを見ると `94 passed, 2 skipped` のように「テストを追加しつつ別のテストを skip 化する」緑化を検出できない。skip・xfail・deselect の不在を独立に判定する
- **ベースライン**: 94 passed（実装前・実測済み。skip / xfail / deselect は 0 件で、強化後の判定式が実装前のログに対して exit 0 を返すことを確認済み）

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

判定 1（guardian）:
```bash
! grep -qi guardian backend/requirements.txt backend/core/settings.py
```

判定 2（django-extensions）:
```bash
! grep -qiE 'django[-_]extensions' backend/requirements.txt backend/core/settings.py
```

- **合格**: 判定 1・2 の**両方が exit 0**（どちらのファイルにも記述が無い）
- **不合格**: 非ゼロ
- **実装前の状態（false-green 検証）**: 判定 1 は **exit 1** を実測済み（`requirements.txt:14` と `settings.py:41` に存在）。判定 2 も `requirements.txt:7` と `settings.py:38` に存在するため **exit 1** になる

---

## TC-AUTO-06: guardian / django_extensions が Python コード全体に無い（AC-03）

判定 1（guardian）:
```bash
! grep -rqi guardian --include=*.py backend/
```

判定 2（django_extensions）:
```bash
! grep -rqi django_extensions --include=*.py backend/
```

- **合格**: 判定 1・2 の**両方が exit 0**
- **不合格**: 非ゼロ
- **実装前の状態（false-green 検証）**: 判定 1 は **exit 1** を実測済み（`backend/core/settings.py:41`）。判定 2 も `backend/core/settings.py:38` に存在するため **exit 1** になる

---

## TC-AUTO-07: guardian 専用設定が無い（AC-04）

```bash
! grep -rq ANONYMOUS_USER_NAME backend/
```

- **合格**: exit 0
- **不合格**: 非ゼロ
- **false-green 検証**: 実装前も 0 件のため現状では合格してしまう。判定式が実際に不合格を返せることを、`ANONYMOUS_USER_NAME = 'AnonymousUser'` を含むダミーファイルを作った一時ディレクトリに対して実行し **exit 1** になることで確認済み（2026-08-22）

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

判定 1（タスクが成功で完了している）:
```bash
grep -qE 'Task studylogs\.tasks\.[a-z_]+\[[^]]+\] succeeded' /tmp/i151_celery.log
```

判定 2（エラーが出ていない）:
```bash
! grep -qE 'ERROR|Traceback' /tmp/i151_celery.log
```

> ログを一時ファイルに落としてから 2 つの判定を行う。`docker compose logs` を 2 回実行すると、成功判定とエラー判定が**別々のスナップショット**を見ることになり、その間に書き込まれたエラーを取りこぼす。

- **合格**: exit 0（直近 3 分に成功ログがあり、かつ ERROR / Traceback が無い）
- **不合格**: 非ゼロ
- **ベースライン**: 実装前に成功ログを実測済み（`Task studylogs.tasks.update_daily_analytics_task[...] succeeded in 0.0103s`）。したがって前半の判定式が実際に成功ログを捕捉できることは確認済み

---

## TC-AUTO-11A: 本体依存＋pytest-django の固定値が一致する（AC-01・AC-10）

**実行タイミング: ステップ 1 完了後。** 宣言（requirements）と実インストール（pip freeze）の両方を判定する。宣言だけを見ると、再ビルド漏れで古いイメージのまま合格してしまう。

> **pytest の判定を含めない理由**: ステップ 1 時点の `pytest` は 8.3.4 のままが正しい。pytest の固定値判定を本 TC に混ぜると、ステップ 1 の「全 TC 合格」条件が原理的に満たせなくなる。pytest は TC-AUTO-11B としてステップ 2 で独立に判定する。

判定 A-1（宣言側・6 パッケージを 1 コマンドずつ確認）:
```bash
grep -qx 'Django==5.2.17' backend/requirements.txt
grep -qx 'djangorestframework==3.18.0' backend/requirements.txt
grep -qx 'django-cors-headers==4.9.0' backend/requirements.txt
grep -qx 'django-filter==26.1' backend/requirements.txt
grep -qx 'django-redis==7.0.0' backend/requirements.txt
grep -qx 'pytest-django==4.14.0' backend/requirements-dev.txt
```

準備（実インストール側のスナップショット）:
```bash
docker compose exec -T backend pip freeze > /tmp/i151_freeze.txt
```

判定 A-2（実インストール側・**宣言側と同じ 6 パッケージを全件**確認）:
```bash
grep -qx 'Django==5.2.17' /tmp/i151_freeze.txt
grep -qx 'djangorestframework==3.18.0' /tmp/i151_freeze.txt
grep -qx 'django-cors-headers==4.9.0' /tmp/i151_freeze.txt
grep -qx 'django-filter==26.1' /tmp/i151_freeze.txt
grep -qx 'django-redis==7.0.0' /tmp/i151_freeze.txt
grep -qx 'pytest-django==4.14.0' /tmp/i151_freeze.txt
```

- **合格**: 判定 A-1 / A-2 の**全コマンドが exit 0**
- **宣言側と実インストール側で対象を揃える理由**: 片方だけ確認すると、再ビルド漏れ（宣言は新しいがイメージは古い）を検出できない。初版では実インストール側から `django-cors-headers` が漏れていたため両側を揃えた。`django-extensions` は削除対象になったため本 TC の対象から外し、不在確認（TC-AUTO-05 / 06）へ移した
- **表記の事前確認**: `pip freeze` が `django-cors-headers==4.3.1` の形（ハイフン・小文字）で出力することを実測済み（2026-08-22）。`-qx` の完全一致で判定できる
- **不合格**: 非ゼロ
- **実装前の状態（false-green 検証）**: 宣言側の 1 行目 `grep -qx 'Django==5.2.17'` が **exit 1** になることを実測済み

---

## TC-AUTO-11B: pytest の固定値が一致する（AC-10）

**実行タイミング: ステップ 2 完了後。**

判定 B-1（宣言側）:
```bash
grep -qx 'pytest==9.0.3' backend/requirements-dev.txt
```

準備（実インストール側のスナップショット）:
```bash
docker compose exec -T backend pip freeze > /tmp/i151_freeze2.txt
```

判定 B-2（実インストール側）:
```bash
grep -qx 'pytest==9.0.3' /tmp/i151_freeze2.txt
```

- **合格**: 判定 B-1 / B-2 の**両方が exit 0**
- **不合格**: 非ゼロ
- **ステップ 1 時点の状態**: `pytest==8.3.4` のため **exit 1**。これはこの時点では正常であり、本 TC はステップ 2 完了後にのみ評価する

---

## TC-AUTO-12: frontend テストが 10 件 pass（AC-12）

準備:
```bash
docker compose exec -T frontend npm test -- --watchAll=false > /tmp/i151_jest.log 2>&1
```

判定:
```bash
grep -qE 'Tests:[[:space:]]+10 passed, 10 total' /tmp/i151_jest.log
```

- **合格**: 準備・判定とも exit 0
- **不合格**: 非ゼロ
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

```bash
test "$(gh pr checks 269 --json state -q '[.[]|select(.state!="SUCCESS")]|length')" -eq 0
```

- **合格**: exit 0（SUCCESS 以外のチェックが 0 件）
- **不合格**: 非ゼロ
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

判定 1（更新後の Django が記録されている）:
```bash
grep -q 'Django==5.2.17' docs/tests/open/I151_pip_freeze.txt
```

判定 2（除去した 2 パッケージが記録に現れない＝再ビルド後の実体である）:
```bash
! grep -qE 'django-(guardian|extensions)==' docs/tests/open/I151_pip_freeze.txt
```

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

判定 1（1 段目のコミットが存在する）:
```bash
grep -qE 'fix\(I151\)' /tmp/i151_commits.txt
```

判定 2（2 段目のコミットが存在する）:
```bash
grep -qE 'chore\(I151\)' /tmp/i151_commits.txt
```

判定 3（`requirements.txt` を触ったコミットが 1 つだけ＝本体依存が 1 段目に集約されている）:
```bash
test "$(wc -l < /tmp/i151_req_commits.txt)" -eq 1
```

> `wc -l < file` はリダイレクトであってパイプではないため、本文書冒頭の「コマンドを複合化しない」原則を満たす。

- **合格**: 判定 1〜3 の**すべてが exit 0**
- **不合格**: 非ゼロ
- **実装前の状態（false-green 検証）**: `fix(I151)` コミットが存在しないため **exit 1**

---

## TC-AUTO-17: レート制限のカウンタ保存が実コンテナで機能する（AC-21・security-review 由来）

**なぜ必要か**: `@ratelimit`（ログイン 5/5m・登録 10/5m・パスワードリセット 3/15m 等のブルートフォース防御）は、カウンタを **`default` キャッシュ**に保存する（`settings.py` の `RATELIMIT_USE_CACHE = 'default'`）。その `default` は本 PR で **django-redis 5.4.0 → 7.0.0（メジャー 2 段）** に更新され、しかも `IGNORE_EXCEPTIONS: True` が設定されているため**失敗しても例外が出ずに握り潰される（フェイルオープン）**。

**既存テストでは検出できない**: `backend/core/tests/test_I127_throttling.py` は 4 つのキャッシュをすべて `LocMemCache` に差し替えるため、django-redis は一度も実行されない。つまり 94 件が全部 pass しても、実環境でレート制限が黙って無効化されている可能性が残る。

django-ratelimit が使うキャッシュ操作は `cache.add` と `cache.incr` の 2 つ（`django_ratelimit.core` を実測）。これを**再ビルド後の実コンテナ**で確認する。

準備:
```bash
docker compose exec -T backend python -c "from django.core.cache import cache; cache.delete('i151_rl_probe'); print('add_new', cache.add('i151_rl_probe', 0, 60)); print('add_dup', cache.add('i151_rl_probe', 0, 60)); print('incr1', cache.incr('i151_rl_probe')); print('incr2', cache.incr('i151_rl_probe')); cache.delete('i151_rl_probe')" > /tmp/i151_rl.txt 2>&1
```

判定 1（新規キーの追加が成功する）:
```bash
grep -q 'add_new True' /tmp/i151_rl.txt
```

判定 2（既存キーの重複追加が拒否される）:
```bash
grep -q 'add_dup False' /tmp/i151_rl.txt
```

判定 3（カウンタが加算される）:
```bash
grep -q 'incr2 2' /tmp/i151_rl.txt
```

- **合格**: 判定 1〜3 の**すべてが exit 0**
- **不合格**: 非ゼロ（＝カウンタが機能せず、レート制限がフェイルオープンしている）
- **設計時点の実測（2026-08-23・ホスト venv）**: django-redis 7.0.0 に対して `add_new True` / `add_dup False` / `incr 1` / `incr 2` を確認済み。ただし**ホスト venv の結果は合否根拠にしない**（イシュー決定 5）ため、再ビルド後の実コンテナで再実行する

---

## 実施記録

| TC | 結果 | 実施日 | 備考 |
|---|---|---|---|
| TC-AUTO-00 | 未実施 | | |
| TC-AUTO-01 | 未実施 | | |
| TC-AUTO-02 | 未実施 | | |
| TC-AUTO-03 | 未実施 | | |
| TC-AUTO-04 | 未実施 | | |
| TC-AUTO-05 | 未実施 | | |
| TC-AUTO-06 | 未実施 | | |
| TC-AUTO-07 | 未実施 | | |
| TC-AUTO-08 | 未実施 | | |
| TC-AUTO-09 | 未実施 | | |
| TC-AUTO-10 | 未実施 | | |
| TC-AUTO-11A | 未実施 | | |
| TC-AUTO-11B | 未実施 | | |
| TC-AUTO-12 | 未実施 | | |
| TC-AUTO-13 | 未実施 | | |
| TC-AUTO-14 | 未実施 | | |
| TC-AUTO-15 | 未実施 | | |
| TC-AUTO-16 | 未実施 | | |
| TC-AUTO-17 | 未実施 | | |

### false-green 検証の記録（計画時点・2026-08-22 実施済み）

否定・回帰系 TC が実際に不合格を返せることを、実装前の状態またはダミー注入で確認した。

| TC | 判定式 | 検証方法 | 結果 |
|---|---|---|---|
| TC-AUTO-04 | `manage.py check --fail-level WARNING` | 実装前の状態（guardian.W001 あり） | **exit 1**（正しく不合格） |
| TC-AUTO-05 | `! grep -qi guardian ...` / `! grep -qiE 'django[-_]extensions' ...` | 実装前の状態（両方の記述あり） | **exit 1**（正しく不合格） |
| TC-AUTO-06 | `! grep -rqi guardian ...` / `! grep -rqi django_extensions ...` | 実装前の状態 | **exit 1**（正しく不合格） |
| TC-AUTO-07 | `! grep -rq ANONYMOUS_USER_NAME ...` | ダミー注入（`ANONYMOUS_USER_NAME = 'AnonymousUser'` を含むファイルを一時ディレクトリに作成） | **exit 1**（正しく不合格） |
| TC-AUTO-08 | `makemigrations --check --dry-run` | マイグレーション未作成のモデルを持つダミーアプリを `INSTALLED_APPS` に注入 | **exit 1**（正しく不合格） |
| TC-AUTO-11A | `grep -qx 'Django==5.2.17' ...` | 実装前の状態（4.2.30） | **exit 1**（正しく不合格） |
| TC-AUTO-16 | `git log ... grep -qE 'fix\(I151\)'` | 実装前の状態（コミット未作成） | **exit 1**（正しく不合格） |

### 機構の事前検証（計画時点・2026-08-22 実施済み）

| 対象 | 検証内容 | 結果 |
|---|---|---|
| TC-AUTO-09 | `docker compose exec -e DB_NAME=migrate_check` が Django 設定に届くか | `settings.DATABASES['default']['NAME'] = migrate_check` を確認 |
| TC-AUTO-10 | 成功ログの grep パターンが実際のログに一致するか | 実装前のログで `Task studylogs.tasks.update_daily_analytics_task[...] succeeded` に一致 |
| TC-AUTO-14 | `gh pr checks --json` の判定式が動くか | PR #256 に対して `0` を確認 |
