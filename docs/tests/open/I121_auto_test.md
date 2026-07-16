# I121 自動テスト: frontend 依存監査の緊急是正（npm audit fix 非破壊）

対象: frontend/package-lock.json（`npm audit fix` 適用後）
実行ディレクトリ: リポジトリルート（コマンドは `--prefix frontend` / `cd frontend` を明記）

結果:
- **全 TC PASS（実装時 2026-07-17 実測）**
  - 事前確認: fix 適用直前の再監査で 25 件（critical 1）＝計画時と同一・advisory DB ドリフトなし
  - TC-01: `TC01_gate_exit=0`（CI ゲート同一条件で exit 0・critical 0 件）
  - TC-02: grep -c 出力 **0**（3 GHSA とも監査結果から消失。修正前は 3）
  - TC-03: #1 変更ファイルは `frontend/package-lock.json` の 1 行のみ / #2 package.json 差分ゼロ / #3 `"react-scripts": "5.0.1"` ヒット / #4 lockfile の react-scripts version 5.0.1 ヒット（websocket-driver 0.7.5・ws 7.5.12 への更新も確認）
  - TC-04: **exit 0・2 suites / 7 tests 全 PASS**（46.8s・ベースライン 2026-07-16 と同数）
  - TC-05: **exit 0**（`The build folder is ready to be deployed.`）
  - TC-06: `18 vulnerabilities (9 low, 4 moderate, 5 high)`・**critical 0**（計画時の模擬適用実測と完全一致）
- Red 状態（修正前）の実測は計画時 2026-07-16 に記録済み（各 TC の false-green 検証欄参照）

## テストケース

### TC-01: CI ゲート同一条件の監査（AC1）
| 項目 | 内容 |
|------|------|
| コマンド | `npm audit --audit-level=critical --omit=dev --prefix frontend` |
| 期待値 | **exit 0**（critical 0 件） |
| false-green 検証 | 修正前の現状（websocket-driver critical あり）で **exit 1** を実測済み（2026-07-16・計画時）。壊れた状態を確実に不合格にする |

### TC-02: 対象 3 advisory の消失（AC2）
| 項目 | 内容 |
|------|------|
| コマンド | `npm audit --omit=dev --json --prefix frontend 2>/dev/null \| grep -c "GHSA-mp7j-qc5w-4988\\\|GHSA-xv26-6w52-cph6\\\|GHSA-96hv-2xvq-fx4p"` |
| 期待値 | **0**（3 GHSA とも監査結果に不在。grep -c が 0 を返す） |
| false-green 検証 | 修正前の現状で **3** を実測済み（2026-07-16・計画時）。模擬適用後のロックファイルでは **0** を実測済み（不在検知と消失の両方向を確認） |

### TC-03: 非破壊性（AC3）
| # | 検証項目 | コマンド | 期待値 |
|---|---------|---------|--------|
| 1 | 変更ファイルが lockfile と docs のみ | `git status --porcelain -- frontend/` | `frontend/package-lock.json` の 1 行のみ（M 表示） |
| 2 | package.json 無変更 | `git diff --stat origin/develop -- frontend/package.json` | 出力なし（差分ゼロ） |
| 3 | react-scripts 宣言バージョン不変 | `grep -F '"react-scripts": "5.0.1"' frontend/package.json` | ヒット（exit 0） |
| 4 | lockfile に破壊的 react-scripts なし | `grep -F '"node_modules/react-scripts"' -A1 frontend/package-lock.json \| grep -F '"version": "5.0.1"'` | ヒット（exit 0・0.0.0 化していない） |

false-green 検証: #3/#4 は肯定一致（文字列が消えれば非ゼロ終了で NG になる）。#3 を空入力に対して実行すると exit 1 になることは grep の仕様どおり（2026-07-16 に `grep -F '"react-scripts": "5.0.1"' /dev/null` → exit 1 を確認）。

### TC-04: frontend Jest 回帰（非破壊の実証）
| 項目 | 内容 |
|------|------|
| コマンド | `npm test --prefix frontend -- --watchAll=false --passWithNoTests` |
| 期待値 | **exit 0・2 suites / 7 tests 全 PASS**（計画時ベースライン 2026-07-16 と同数） |
| ベースライン | 修正前 2026-07-16 実測: 2 suites / 7 tests PASS（49.9s）。act() 警告は pre-existing |

### TC-05: frontend 本番ビルド回帰（非破壊の実証）
| 項目 | 内容 |
|------|------|
| コマンド | `npm run build --prefix frontend` |
| 期待値 | **exit 0**（`Compiled successfully` または警告付き成功。エラーで fail しない） |

### TC-06: 残存件数の実測記録（AC6・記録のみ・合否は critical 0 で判定）
| 項目 | 内容 |
|------|------|
| コマンド | `npm audit --omit=dev --prefix frontend 2>&1 \| grep "vulnerabilities"` |
| 期待値 | **critical 0**（計画時の模擬適用実測: `18 vulnerabilities (9 low, 4 moderate, 5 high)`。advisory DB ドリフトで件数が前後した場合は実測値を記録し、critical 0 のみを合否条件とする） |

## 実行順序・前提
- TC-01〜TC-06 はすべて実装ステップ1（`npm audit fix`）完了後に実行する。
- TC-04/TC-05 は node_modules 同期が前提（`npm audit fix` が install を伴うため通常は追加操作不要。乖離時のみ `npm ci`）。
