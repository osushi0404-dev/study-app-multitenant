# I180 自動テスト: Pillow を 13.0.0 に更新（既知脆弱性 8 件の解消）

- 関連: docs/issues/open/I180.md / docs/plans/open/plan_I180.md / GitHub #301 / Draft PR #303
- 実行環境: **wt-harness の Docker（このワークツリーのディレクトリで `docker compose ...`）**。主作業側（`study-app-multitenant`）のコンテナは使わない
- テストレベル: 静的検証（決定論ゲート）／ツール実行／ユニット（新規 9 件）／テスト品質の検証（ミューテーション・プローブ）／既存の単体・結合（全件）／CI
- 合否判定インターフェース: **すべて exit code で判定する**。合格とする exit code は下の「TC 一覧」の『合格条件』列だけで定める（唯一の正）。既定は「exit 0 = 合格・非ゼロ = 不合格」。TC-AUTO-05 判定 2 だけは「exit 1 = 合格・それ以外 = 不合格」（理由は TC 本文）
- **コマンドは複合化しない**。複数条件がある TC は「判定 1・判定 2 …」に分け、すべての判定が『合格条件』列の exit code を返したら合格とする
- heavy なコマンド（docker / gh）は各 TC 本文にインラインコードで書く（コピーして単体で実行する）。リポジトリ内のファイルだけを見る静的判定は「決定論ゲート（自動実走）」に書き、`/code-review` が毎回実走する

## ベースライン（実装前・2026-10-21 実測）

| 項目 | 値 |
|---|---|
| backend テスト | 94 passed |
| `pip-audit -r requirements.txt` | 8 件検出・exit 1 |
| インストール済み Pillow | 12.3.0 |

---

## TC 一覧

| TC | 検証内容 | 対応 AC | 実行タイミング | 合格条件（唯一の正） |
|---|---|---|---|---|
| TC-AUTO-00 | 実行環境の前提（backend / celery / celery-beat の再ビルドと起動） | AC-3 | ステップ 0・1 | exit 0 |
| TC-AUTO-01 | `requirements.txt` の宣言が `Pillow==13.0.0` で、12 系の行が無い | AC-1 | ステップ 1 | exit 0（決定論ゲート） |
| TC-AUTO-02 | 本体依存の脆弱性が 0 件 | AC-2 | ステップ 1 | exit 0 |
| TC-AUTO-03 | 3 サービスのコンテナの Pillow が 13.0.0 | AC-3 | ステップ 1 | exit 0 |
| TC-AUTO-04 | 新規テスト 9 件が通る（件数・失敗・エラー・スキップを判定） | AC-5 | ステップ 2 | exit 0 |
| TC-AUTO-05 | 新規テストが false-green でない（プローブ合格）／プローブ自体が中身のないテストを不合格にする | AC-5 | ステップ 2 | 判定 1: exit 0・**判定 2: exit 1**（例外） |
| TC-AUTO-06 | backend 全テストが通る（ステップ 1 で 94 件・ステップ 2 以降 103 件） | AC-4 | ステップ 1・2 | exit 0 |
| TC-AUTO-07 | CI の全 6 チェックが SUCCESS | AC-6 | ステップ 3 | exit 0 |

---

## 決定論ゲート（自動実走）
<!--
  code-review.sh が下の ```bash ブロックを 1 行 1 コマンドで実走し、実 exit code を VERDICT に注入する。
  許可（実走）: `bash scripts/claude/tests/*.sh` / `grep -q 文言 file`（存在）/ `grep -L 文言 dir/*`（不在ファイル一覧）/
    `! grep -q 文言 file`（不在）/ `python3 -m json.tool file` / `bash -n file` / `python3 -m py_compile file`
  1 行 1 コマンド・チェーン（; && || | ` $( > 等）不可。heavy（docker/gh/pytest）はここに書かない。
  TC-AUTO-01 判定 1・2 と TC-AUTO-04 判定 0 をここで実走する。
-->
```bash
# TC-AUTO-01 判定 1（宣言が 13.0.0 の行全体一致）
grep -qx 'Pillow==13.0.0' backend/requirements.txt
# TC-AUTO-01 判定 2（12 系の行が残っていない・大文字小文字無視）
! grep -qi 'pillow==12' backend/requirements.txt
# TC-AUTO-04 判定 0（新規テスト・プローブ・反証用フィクスチャが存在し、構文が正しい）
python3 -m py_compile backend/problems/tests/test_I180_image_validation.py
python3 -m py_compile docs/tests/open/I180_mutation_probe.py
python3 -m py_compile docs/tests/open/I180_probe_vacuous_fixture.py
```

---

## TC-AUTO-00: 実行環境の前提（AC-3）

backend / celery / celery-beat を、現在の `requirements.txt` で再ビルドして起動する。backend はヘルスチェック（`/health/`）が通るまで待つ。

- 判定 1: `docker compose up -d --build --wait backend celery celery-beat`
- **合格**: exit 0
- **不合格**: 非ゼロ（ビルド失敗・いずれかのサービスが起動しない・backend が unhealthy）

---

## TC-AUTO-01: 宣言が `Pillow==13.0.0`（AC-1）

決定論ゲートの「TC-AUTO-01 判定 1・2」。

- 判定 1: `Pillow==13.0.0` の行が完全一致で存在する
- 判定 2: `pillow==12` を含む行が無い（大文字小文字無視。旧版の行の消し忘れ・重複固定を検知）
- **合格**: 判定 1・2 とも exit 0
- **false-green 検証（実装前に実施済み）**: 実装前の `requirements.txt`（`Pillow==12.3.0`）に対して、判定 1 は exit 1・判定 2 は exit 1（実施記録を参照）

---

## TC-AUTO-02: 本体依存の脆弱性が 0 件（AC-2）

- 判定 1: `docker compose exec -T backend pip-audit -r requirements.txt`
- **合格**: exit 0（`No known vulnerabilities found`）
- **不合格**: 非ゼロ。Pillow 以外の検出が出た場合は、イシューのスコープ外として記録し、別イシューを提案する
- **false-green 検証（実装前に実施済み）**: 実装前のコンテナ（12.3.0）で exit 1・8 件（実施記録を参照）

---

## TC-AUTO-03: 3 サービスの Pillow が 13.0.0（AC-3）

再ビルド漏れ（celery 系だけ古いイメージのまま等）を検知する。

- 判定 1: `docker compose exec -T backend python -c "import sys, PIL; sys.exit(PIL.__version__ != '13.0.0')"`
- 判定 2: `docker compose exec -T celery python -c "import sys, PIL; sys.exit(PIL.__version__ != '13.0.0')"`
- 判定 3: `docker compose exec -T celery-beat python -c "import sys, PIL; sys.exit(PIL.__version__ != '13.0.0')"`
- **合格**: 判定 1〜3 とも exit 0
- **false-green 検証（実装前に実施済み）**: 実装前の backend（12.3.0）で判定 1 が exit 1（実施記録を参照）

---

## TC-AUTO-04: 新規テスト 9 件が通る（AC-5）

`backend/problems/tests/test_I180_image_validation.py`（計画書 §5-2）。件数を JUnit XML から判定し、「収集されずに 0 件で緑」「スキップで緑」を防ぐ。

- 判定 0: 決定論ゲートの「TC-AUTO-04 判定 0」（3 ファイルの存在と構文）
- 判定 1: `docker compose exec -T backend python -m pytest problems/tests/test_I180_image_validation.py -q -p no:cacheprovider --junitxml=/tmp/i180_new.xml`
- 判定 2: `docker compose exec -T backend python -c "import sys, xml.etree.ElementTree as E; s = E.parse('/tmp/i180_new.xml').getroot().find('testsuite'); sys.exit(not (s.get('tests') == '9' and s.get('failures') == '0' and s.get('errors') == '0' and s.get('skipped') == '0'))"`
- **合格**: 判定 0〜2 とも exit 0
- **期待するテスト（9 件）**:

| テスト | 期待値 |
|---|---|
| `test_allowed_formats_pass[a.png-PNG-image/png]` | `(True, None)` |
| `test_allowed_formats_pass[a.jpg-JPEG-image/jpeg]` | `(True, None)` |
| `test_allowed_formats_pass[a.jpeg-JPEG-image/jpeg]` | `(True, None)` |
| `test_allowed_formats_pass[a.webp-WEBP-image/webp]` | `(True, None)` |
| `test_max_dimension_boundary_passes[size0]`（4096x1） | `(True, None)` |
| `test_max_dimension_boundary_passes[size1]`（1x4096） | `(True, None)` |
| `test_over_max_dimension_rejected[size0]`（4097x1） | `(False, "画像サイズが大きすぎます（4097x1）。最大4096x4096ピクセルまでです。")` |
| `test_over_max_dimension_rejected[size1]`（1x4097） | `(False, "画像サイズが大きすぎます（1x4097）。最大4096x4096ピクセルまでです。")` |
| `test_truncated_png_rejected_by_pillow` | `is_valid is False`・`error_msg` が `"画像ファイルの読み込みに失敗しました: "` で始まる |

- **false-green 検証（実装前に実施済み）**: 判定 1 はファイル未作成で exit 4。判定 2 の件数判定を 94 件の XML に当てると exit 1（件数違いで不合格になる）。テストの中身の検証力は TC-AUTO-05 で確かめる

---

## TC-AUTO-05: 新規テストが false-green でない（AC-5）

`docs/tests/open/I180_mutation_probe.py`（計画書 §5-3）。`problems.utils` を実行時にだけ 4 通りに壊し、そのたびに新規テストが失敗する（pytest exit 1）ことを確かめる。リポジトリのファイルは変更しない。

- 判定 1: `docker compose exec -T backend python docs/tests/open/I180_mutation_probe.py`
  - **合格**: exit 0（無改変で pytest exit 0、`max_dimension_plus_1` / `max_dimension_minus_1` / `drop_webp` / `skip_pillow_open` の 4 種すべてで pytest exit 1）
- 判定 2（プローブ自体の反証）: `docker compose exec -T backend python docs/tests/open/I180_mutation_probe.py docs/tests/open/I180_probe_vacuous_fixture.py`
  - **合格**: **exit 1**（中身のないテストでは 4 種すべて「見逃し」になる＝プローブが常に合格を返す壊れ方をしていない）
  - exit 1 を合格にする理由: この判定は「プローブが不合格を出せること」を確かめる反証であり、正しく動くプローブは中身のないテストに対して exit 1 を返すため
- **合格**: 判定 1 が exit 0、かつ判定 2 が exit 1
- **スパイク実績（計画時・2026-10-21・scratchpad の同一コード）**: 12.3.0 / 13.0.0 とも判定 1 相当が exit 0、判定 2 相当が exit 1（計画書 §2-5）

---

## TC-AUTO-06: backend 全テストが通る（AC-4）

画像アップロードの結合テスト（`test_I073_image_update.py`・multipart → 検証 → 保存）を含む全件。

- 判定 1: `docker compose exec -T backend python -m pytest --tb=short -q -p no:cacheprovider --junitxml=/tmp/i180_all.xml`
- 判定 2（ステップ 1・新規テスト追加前）: `docker compose exec -T backend python -c "import sys, xml.etree.ElementTree as E; s = E.parse('/tmp/i180_all.xml').getroot().find('testsuite'); sys.exit(not (s.get('tests') == '94' and s.get('failures') == '0' and s.get('errors') == '0' and s.get('skipped') == '0'))"`
- 判定 2（ステップ 2 以降・94 + 新規 9）: `docker compose exec -T backend python -c "import sys, xml.etree.ElementTree as E; s = E.parse('/tmp/i180_all.xml').getroot().find('testsuite'); sys.exit(not (s.get('tests') == '103' and s.get('failures') == '0' and s.get('errors') == '0' and s.get('skipped') == '0'))"`
- **合格**: 判定 1・2 とも exit 0
- 件数を固定する理由: skip・削除による緑化と、収集漏れを機械的に検知するため

---

## TC-AUTO-07: CI の全 6 チェックが SUCCESS（AC-6）

対象: Backend Lint & Security / Backend Tests / Frontend Type Check / Frontend Lint & Security / Frontend Tests / E2E Tests (Playwright)。

- 判定 1: `gh pr checks 303 --watch`
- 判定 2: `gh pr checks 303 --json name,state --jq 'if ([.[] | select(.state == "SUCCESS")] | length) == 6 then "ok" else error("not all 6 SUCCESS") end'`
- **合格**: 判定 1・2 とも exit 0
- 判定 2 の理由: 判定 1 だけでは、チェックが一部しか登録されていない状態でも全成功に見えうるため、SUCCESS の数を 6 で固定する
- **false-green 検証（計画時に実施済み）**: Backend Lint & Security が FAILURE の PR #300 に判定 2 を実行して exit 1。条件を `== 5` にすると exit 0（判定式が真偽の両方を返すこと）

---

## 実施記録

### 実装前（2026-10-21・plan-issue 時点）

| TC | 実行 | 結果 | 備考 |
|---|---|---|---|
| TC-AUTO-00 | `docker compose up -d --build --wait backend` | exit 0 | backend / db / redis が healthy（celery 系は未起動。ステップ 0 で起動する） |
| TC-AUTO-01 判定 1 | `grep -qx 'Pillow==13.0.0' backend/requirements.txt` | exit 1 | 実装前なので不合格（false-green でない） |
| TC-AUTO-01 判定 2 | `! grep -qi 'pillow==12' backend/requirements.txt` | exit 1 | 同上 |
| TC-AUTO-02 | `docker compose exec -T backend pip-audit -r requirements.txt` | exit 1 | 8 件（イシュー記載と同じ ID） |
| TC-AUTO-03 判定 1 | backend の `PIL.__version__ != '13.0.0'` | exit 1 | 12.3.0 |
| TC-AUTO-04 判定 0 | `python3 -m py_compile backend/problems/tests/test_I180_image_validation.py` | exit 1 | ファイル未作成 |
| TC-AUTO-04 判定 1 | 新規テストの pytest | exit 4 | ファイル未作成（収集対象なし） |
| TC-AUTO-05 | プローブ | — | ファイル未作成。scratchpad の同一コードでのスパイク結果は計画書 §2-5 |
| TC-AUTO-04 判定 2（反証） | 件数判定を 94 件の XML（`/tmp/i180_all.xml`）に当てる | exit 1 | 件数が 9 でなければ不合格になる |
| TC-AUTO-06 | 全件 pytest＋件数 94 | exit 0 / exit 0 | 94 passed |
| TC-AUTO-06 判定 2（反証） | 同じ XML に `'103'` 版を当てる | exit 1 | 新規テスト追加前は不合格になる |
| TC-AUTO-07 判定 2 | PR #300 に対して実行（反証） | exit 1 | PR #303 はコード未 push のため未実施 |

### 実装後

| TC | 結果 | 備考 |
|---|---|---|
| TC-AUTO-00 | ✅ exit 0 | 2026-10-21・ステップ 1。backend / celery / celery-beat を再ビルド（`RUN pip install -r requirements.txt` 層を再実行）し、全サービス Healthy |
| TC-AUTO-01 | ✅ 判定 1・2 とも exit 0 | ステップ 1 |
| TC-AUTO-02 | ✅ exit 0 | `No known vulnerabilities found` |
| TC-AUTO-03 | ✅ 判定 1〜3 とも exit 0 | backend / celery / celery-beat すべて 13.0.0 |
| TC-AUTO-04 | ✅ 判定 0〜2 とも exit 0 | `9 passed in 0.21s`。JUnit XML: tests=9・failures=0・errors=0・skipped=0。コードは計画書 §5-2 と diff 0 |
| TC-AUTO-05 | ✅ 判定 1 exit 0・判定 2 exit 1 | 判定 1: baseline exit 0・4 種すべて exit 1（検知）。判定 2: 中身のないテストで 4 種すべて「見逃し」・exit 1。プローブは計画書 §5-3 と diff 0 |
| TC-AUTO-06 | ✅ 判定 1・2 とも exit 0 | ステップ 1: `94 passed`（件数 94 判定 exit 0）。ステップ 2: `103 passed`（件数 103 判定 exit 0）。プローブ・フィクスチャは通常収集に混ざっていない |
| TC-AUTO-07 | ✅ 判定 1・2 とも exit 0 | head `db5d205`・CI run 39525530289 / E2E run 39525530302。6 チェックすべて SUCCESS（Backend Lint & Security 37s・Backend Tests 1m56s・E2E 4m2s ほか）。判定 2 は `ok` |
