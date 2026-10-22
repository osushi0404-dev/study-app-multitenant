# I183 自動テスト: djangorestframework 3.18.0 → 3.18.2（pip-audit 失敗の解消）

対象: `backend/requirements.txt`（DRF の行の更新）と、作り直した backend イメージ
実行ディレクトリ: リポジトリルート（`docker compose exec backend` のコマンドはコンテナの `/app`＝`backend/` で実行される）

注意: 対話シェルの `grep` はラッパー（ugrep）で `-x` が誤動作するため、`grep` は `/usr/bin/grep` をフルパスで使う。

結果:
- **全 TC PASS（実装時 2026-10-23 実測）**
  - TC-01: exit 0（`djangorestframework==3.18.2` の行あり）
  - TC-02: exit 0（backend 配下の差分は `backend/requirements.txt` の 1 行追加・1 行削除のみ）
  - TC-03: exit 0・`No known vulnerabilities found`（advisory DB のドリフトなし＝計画時の模擬適用と一致）
  - イメージの作り直し: `docker compose build backend celery celery-beat e2e-init` 成功（4 イメージ Built・djangorestframework-3.18.2 を取得）→ `docker compose up -d backend celery celery-beat` で再作成
  - TC-04: `3.18.2`・exit 0
  - TC-05: exit 0・**103 passed**, 5 warnings（19.96s・ベースラインと同数）。警告は `imghdr` 非推奨 1 件と DRF pagination の `UnorderedObjectListWarning` 4 件（Subject の並び順未指定・既存）
  - TC-06: exit 0・`No broken requirements found.`
  - TC-07: exit 0・`No changes detected`

## テストケース

### TC-01: requirements.txt の DRF が 3.18.2（AC1）
| 項目 | 内容 |
|------|------|
| コマンド | `/usr/bin/grep -qx "djangorestframework==3.18.2" backend/requirements.txt` |
| 期待値 | **exit 0** |
| false-green 検証 | 変更前（3.18.0）の `backend/requirements.txt` で **exit 1** を確認済み（2026-10-23・計画時）。3.18.2 に変えた写しで exit 0 も確認済み。ラッパーの `grep -qx` は変更前でも exit 0 を返した（誤合格）ため `/usr/bin/grep` に固定 |

### TC-02: backend の変更は requirements.txt の 1 行だけ（AC1・スコープ外の変更なし）
| 項目 | 内容 |
|------|------|
| コマンド | `bash -c '[ "$(git diff --numstat origin/develop -- backend/)" = "$(printf "1\t1\tbackend/requirements.txt")" ]'` |
| 期待値 | **exit 0**（backend 配下の差分が requirements.txt の 1 行追加・1 行削除のみ） |
| false-green 検証 | 変更前（差分なし）で **exit 1** を確認済み（2026-10-23・計画時）。別の行や別ファイルが変わると文字列が一致せず非ゼロ終了になる |

### TC-03: pip-audit が既知の脆弱性 0 件（AC2・CI と同条件）
| 項目 | 内容 |
|------|------|
| コマンド | `docker compose exec backend pip-audit -r requirements.txt` |
| 期待値 | **exit 0**・`No known vulnerabilities found` |
| false-green 検証 | 変更前で **exit 1**・CVE-2026-114136/114137/114138 の 3 件を確認済み（2026-10-23・計画時）。3.18.2 にした写しでは exit 0 を確認済み。pip-audit は CI と同じ 2.10.0（`requirements-dev.txt`） |

### TC-04: コンテナにインストールされた DRF が 3.18.2（イメージの作り直し確認）
| 項目 | 内容 |
|------|------|
| コマンド | `docker compose exec backend python -c "import sys, rest_framework; print(rest_framework.VERSION); sys.exit(rest_framework.VERSION != '3.18.2')"` |
| 期待値 | `3.18.2` を表示して **exit 0** |
| false-green 検証 | 作り直し前のコンテナで `3.18.0`・**exit 1** を確認済み（2026-10-23・計画時） |

### TC-05: backend テストの回帰（AC3）
| 項目 | 内容 |
|------|------|
| コマンド | `docker compose exec backend pytest -q -p no:cacheprovider` |
| 期待値 | **exit 0・103 passed**（計画時ベースラインと同数） |
| ベースライン | 変更前 2026-10-23: 103 passed, 5 warnings（20.93s）。警告は `imghdr` 非推奨（既存・DRF と無関係） |
| 前提 | TC-04 が合格していること（3.18.0 のまま通る誤合格を防ぐ） |
| false-green 検証 | 回帰テストのため変更前（3.18.0）でも合格するのが正しく、変更前に不合格を誘発することはできない。「3.18.0 のまま実行して合格してしまう」誤合格は、TC-05 の前に TC-04（作り直し前は exit 1 を確認済み）でコンテナの版を確かめることで防ぐ |

### TC-06: 依存の整合（simplejwt 5.5.1 との共存）
| 項目 | 内容 |
|------|------|
| コマンド | `docker compose exec backend pip check` |
| 期待値 | **exit 0**・`No broken requirements found.` |
| ベースライン | 変更前 2026-10-23: `No broken requirements found.` |

### TC-07: マイグレーションの差分なし（DB 影響なし）
| 項目 | 内容 |
|------|------|
| コマンド | `docker compose exec backend python manage.py makemigrations --check --dry-run` |
| 期待値 | **exit 0**・`No changes detected` |

## 実行順序・前提
- TC-01・TC-02・TC-03 はステップ1（requirements.txt の更新）の後に実行する（TC-03 はコンテナから bind mount された requirements.txt を読む）。
- TC-04〜TC-07 はステップ2（イメージの作り直しと再起動）の後に、TC-04 → TC-05 の順で実行する。
- E2E は CI（`E2E Tests (Playwright)`）で確認する（手動テスト M1）。
