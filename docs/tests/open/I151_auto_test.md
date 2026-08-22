# I151 自動テスト（Django 5.2 LTS 更新・未使用 django-guardian の除去）

- 関連: docs/issues/open/I151.md / docs/plans/open/plan_I151.md / GitHub #267 / Draft PR #269
- 実行環境: **Docker（`docker compose exec`）**。ホスト venv の結果は合否根拠にしない（イシュー決定 5）
- テストレベル: 静的検証（決定論 TC）／ツール実行／既存の単体・API 結合／コンポーネント／E2E
- **新規テストコードは追加しない**（イシュー決定 6）。既存 94 件が同じ結果を返すことで依存更新の影響を測る
- 合否判定インターフェース: **すべて exit code に統一**（合格 = exit 0・不合格 = 非ゼロ）

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
| TC-AUTO-05 | guardian が requirements / settings に無い | AC-02 | ステップ 1 |
| TC-AUTO-06 | guardian が Python コード全体に無い | AC-03 | ステップ 1 |
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

```bash
docker compose exec -T backend python -m pytest -q > /tmp/i151_pytest.log 2>&1 \
  && grep -qE '^94 passed' /tmp/i151_pytest.log \
  && ! grep -qE 'skipped|xfailed|deselected' /tmp/i151_pytest.log
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

## TC-AUTO-05: guardian が requirements / settings に無い（AC-02）

```bash
! grep -qi guardian backend/requirements.txt backend/core/settings.py
```

- **合格**: exit 0（どちらのファイルにも guardian の記述が無い）
- **不合格**: 非ゼロ
- **実装前の状態（false-green 検証）**: **exit 1** を実測済み（`requirements.txt:14` と `settings.py:41` に存在）

---

## TC-AUTO-06: guardian が Python コード全体に無い（AC-03）

```bash
! grep -rqi guardian --include=*.py backend/
```

- **合格**: exit 0
- **不合格**: 非ゼロ
- **実装前の状態（false-green 検証）**: **exit 1** を実測済み（`backend/core/settings.py:41`）

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
- **事前実測**: guardian 除去済み＋確定セットの組み合わせで `No changes detected` を確認済み

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

beat が投げたことではなく、worker が**成功で完了した**ことまで判定する（イシュー決定 7-B）。`update_daily_analytics_task` は 30 秒間隔のため、再作成から 1 分以上経過してから実行する。

```bash
docker compose logs celery --since 3m > /tmp/i151_celery.log 2>&1 \
  && grep -qE 'Task studylogs\.tasks\.[a-z_]+\[[^]]+\] succeeded' /tmp/i151_celery.log \
  && ! grep -qE 'ERROR|Traceback' /tmp/i151_celery.log
```

> ログを一時ファイルに落としてから 2 つの判定を行う。`docker compose logs` を 2 回実行すると、成功判定とエラー判定が**別々のスナップショット**を見ることになり、その間に書き込まれたエラーを取りこぼす。

- **合格**: exit 0（直近 3 分に成功ログがあり、かつ ERROR / Traceback が無い）
- **不合格**: 非ゼロ
- **ベースライン**: 実装前に成功ログを実測済み（`Task studylogs.tasks.update_daily_analytics_task[...] succeeded in 0.0103s`）。したがって前半の判定式が実際に成功ログを捕捉できることは確認済み

---

## TC-AUTO-11A: 本体依存＋pytest-django の固定値が一致する（AC-01・AC-10）

**実行タイミング: ステップ 1 完了後。** 宣言（requirements）と実インストール（pip freeze）の両方を判定する。宣言だけを見ると、再ビルド漏れで古いイメージのまま合格してしまう。

> **pytest の判定を含めない理由**: ステップ 1 時点の `pytest` は 8.3.4 のままが正しい。pytest の固定値判定を本 TC に混ぜると、ステップ 1 の「全 TC 合格」条件が原理的に満たせなくなる。pytest は TC-AUTO-11B としてステップ 2 で独立に判定する。

宣言側:
```bash
grep -qx 'Django==5.2.17' backend/requirements.txt \
  && grep -qx 'djangorestframework==3.18.0' backend/requirements.txt \
  && grep -qx 'django-cors-headers==4.9.0' backend/requirements.txt \
  && grep -qx 'django-extensions==4.1' backend/requirements.txt \
  && grep -qx 'django-filter==26.1' backend/requirements.txt \
  && grep -qx 'django-redis==7.0.0' backend/requirements.txt \
  && grep -qx 'pytest-django==4.14.0' backend/requirements-dev.txt
```

実インストール側（`pip freeze` の表記は PyPI の正規化名で固定されるため、宣言側と同じ `-qx` の完全一致で判定する）:
```bash
docker compose exec -T backend pip freeze > /tmp/i151_freeze.txt \
  && grep -qx 'Django==5.2.17' /tmp/i151_freeze.txt \
  && grep -qx 'djangorestframework==3.18.0' /tmp/i151_freeze.txt \
  && grep -qx 'django-filter==26.1' /tmp/i151_freeze.txt \
  && grep -qx 'django-redis==7.0.0' /tmp/i151_freeze.txt \
  && grep -qx 'pytest-django==4.14.0' /tmp/i151_freeze.txt
```

- **合格**: 両方が exit 0
- **不合格**: 非ゼロ
- **実装前の状態（false-green 検証）**: 宣言側の 1 行目 `grep -qx 'Django==5.2.17'` が **exit 1** になることを実測済み

---

## TC-AUTO-11B: pytest の固定値が一致する（AC-10）

**実行タイミング: ステップ 2 完了後。**

```bash
grep -qx 'pytest==9.0.3' backend/requirements-dev.txt \
  && docker compose exec -T backend pip freeze | grep -qx 'pytest==9.0.3'
```

- **合格**: exit 0（宣言と実インストールの両方が 9.0.3）
- **不合格**: 非ゼロ
- **ステップ 1 時点の状態**: `pytest==8.3.4` のため **exit 1**。これはこの時点では正常であり、本 TC はステップ 2 完了後にのみ評価する

---

## TC-AUTO-12: frontend テストが 10 件 pass（AC-12）

```bash
docker compose exec -T frontend npm test -- --watchAll=false > /tmp/i151_jest.log 2>&1 \
  && grep -qE 'Tests:[[:space:]]+10 passed, 10 total' /tmp/i151_jest.log
```

- **合格**: exit 0
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
[ "$(gh pr checks 269 --json state -q '[.[]|select(.state!="SUCCESS")]|length')" -eq 0 ]
```

- **合格**: exit 0（SUCCESS 以外のチェックが 0 件）
- **不合格**: 非ゼロ
- **対象 6 チェック**: Backend Lint & Security / Backend Tests / Frontend Lint & Security / Frontend Tests / Frontend Type Check / E2E Tests (Playwright)
- **機構の事前検証**: 同じ判定式を PR #256 に対して実行し `0` が返ることを確認済み（2026-08-22）

---

## TC-AUTO-15: 再ビルド後の `pip freeze` を記録（AC-16）

推移的依存（kombu 等）が再ビルドで変動した場合に、後から切り分けられるようにする（イシュー決定 7-C）。

```bash
docker compose exec -T backend pip freeze
```

- **合格**: 出力を本文書の「実施記録」へ貼り付けてあること
- **判定**: 記録の有無（人手判定・機械判定なし）
- **ベースライン（実装前・2026-08-22）**: `Django==4.2.30` / `celery==5.3.4` / `kombu==5.6.2` / `amqp==5.3.1` / `billiard==4.2.4` / `vine==5.1.0` / `redis==5.0.1` / `djangorestframework==3.15.2` / `django-guardian==2.4.0` / `pytest==8.3.4` / `pytest-django==4.9.0`

---

## TC-AUTO-16: コミットが 2 段に分かれている（AC-17）

```bash
git log origin/develop..HEAD --oneline | grep -qE 'fix\(I151\)' \
  && git log origin/develop..HEAD --oneline | grep -qE 'chore\(I151\)' \
  && [ "$(git log origin/develop..HEAD --oneline -- backend/requirements.txt | wc -l)" -eq 1 ]
```

- **合格**: exit 0（1 段目と 2 段目のコミットが存在し、`requirements.txt` を触ったコミットが 1 つだけ＝本体依存の変更が 1 段目に集約されている）
- **不合格**: 非ゼロ
- **実装前の状態（false-green 検証）**: `fix(I151)` コミットが存在しないため **exit 1**

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

### false-green 検証の記録（計画時点・2026-08-22 実施済み）

否定・回帰系 TC が実際に不合格を返せることを、実装前の状態またはダミー注入で確認した。

| TC | 判定式 | 検証方法 | 結果 |
|---|---|---|---|
| TC-AUTO-04 | `manage.py check --fail-level WARNING` | 実装前の状態（guardian.W001 あり） | **exit 1**（正しく不合格） |
| TC-AUTO-05 | `! grep -qi guardian ...` | 実装前の状態（guardian 記述あり） | **exit 1**（正しく不合格） |
| TC-AUTO-06 | `! grep -rqi guardian --include=*.py backend/` | 実装前の状態 | **exit 1**（正しく不合格） |
| TC-AUTO-07 | `! grep -rq ANONYMOUS_USER_NAME ...` | ダミー注入（`ANONYMOUS_USER_NAME = 'AnonymousUser'` を含むファイルを一時ディレクトリに作成） | **exit 1**（正しく不合格） |
| TC-AUTO-11A | `grep -qx 'Django==5.2.17' ...` | 実装前の状態（4.2.30） | **exit 1**（正しく不合格） |
| TC-AUTO-16 | `git log ... grep -qE 'fix\(I151\)'` | 実装前の状態（コミット未作成） | **exit 1**（正しく不合格） |

### 機構の事前検証（計画時点・2026-08-22 実施済み）

| 対象 | 検証内容 | 結果 |
|---|---|---|
| TC-AUTO-09 | `docker compose exec -e DB_NAME=migrate_check` が Django 設定に届くか | `settings.DATABASES['default']['NAME'] = migrate_check` を確認 |
| TC-AUTO-10 | 成功ログの grep パターンが実際のログに一致するか | 実装前のログで `Task studylogs.tasks.update_daily_analytics_task[...] succeeded` に一致 |
| TC-AUTO-14 | `gh pr checks --json` の判定式が動くか | PR #256 に対して `0` を確認 |
