# 自動テスト: I108 Pillow 12.3.0 へのセキュリティアップデート（pip-audit CI ブロッカー解消）

## テスト方針

本イシューはコード無改変の依存1行更新のため、新規ユニットテストは追加しない。
検証は (1) requirements 内容の決定論判定、(2) pip-audit ゲートの exit 0、(3) CI 全ジョブ（既存テストスイートによる回帰検証を含む）の3層で行う。

## テストケース

### TC-01: requirements.txt のピンが 12.3.0 になっている（決定論判定）

```bash
grep -E '^Pillow==12\.3\.0$' backend/requirements.txt
```

- **期待値**: exit 0（`Pillow==12.3.0` の行が完全一致で出力される）
- **false-green 検証（2026-07-15 実施済み）**: 失敗条件＝修正前（`Pillow==12.2.0`）の requirements.txt に対して実行し、**exit 1（NG・出力なし）** を確認済み。アンカー付き完全一致（`^...$`）のため `Pillow==12.3.0.post1` 等の部分一致誤判定もしない。

### TC-02: pip-audit が exit 0（CI 同条件・依存解決込み）

```bash
pipx run pip-audit -r backend/requirements.txt
```

- **期待値**: exit 0、出力に `No known vulnerabilities found`
- **注記**: CI（`.github/workflows/ci.yml:27`）は `pip-audit -r requirements.txt`（working-directory: backend / pip-audit==2.10.0）で同等。ローカルは pipx の 2.10.1 を使用するが、同一の脆弱性 DB（PyPI Advisory / OSV）照会のため判定は等価。最終判定は CI（TC-03）を正とする。
- **false-green 検証（2026-07-15 実施済み）**: 失敗条件＝修正前ピン（12.2.0）に対して実行し、**exit 1（pillow 12.2.0 に PYSEC-2026-2253〜2257 の5件検出・NG）** を確認済み。
- **計画時スパイク（2026-07-15 実施済み）**: `Pillow==12.3.0` に置換した requirements で本コマンド（依存解決込み）を実行し、**exit 0 / `No known vulnerabilities found`** を確認済み。実装時にも再実行する（スパイク後に新規 CVE が公開される可能性への対応）。

### TC-03: CI 全ジョブ pass（回帰検証を含む）

```bash
gh pr checks 204
```

- **期待値**: PR #204 の全チェック（Backend Lint & Security / Backend Tests / E2E Tests / Frontend 系）が `pass`。exit 0
- **注記**: Backend Tests には Pillow 使用箇所（`backend/problems/utils.py`）の既存回帰テスト `backend/problems/tests/test_I073_image_update.py` が含まれる。E2E Tests は画像アップロードを含む主要フローを検証する。
- **false-green にならない根拠**: 本 TC の失敗条件は「CI ジョブの fail」であり、まさに現在 develop 上の全 PR で Backend Lint & Security が **fail している実績**（PR #202・2026-07-14）がある＝ゲートが失敗を検出できることは実環境で実証済み。

## 実行記録

| TC | 実施日 | 結果 | 備考 |
|----|--------|------|------|
| TC-01 | 2026-07-15 | **PASS**（exit 0・`Pillow==12.3.0` が完全一致で出力） | false-green 検証は計画時に実施済み（12.2.0 状態で NG を確認） |
| TC-02 | 2026-07-15 | **PASS**（exit 0・`No known vulnerabilities found`・依存解決込み） | pipx pip-audit 2.10.1。計画時スパイク以降の新規 CVE 追加公開なし |
| TC-03 | 2026-07-15 | **PASS**（exit 0・全6チェック pass: Backend Lint & Security 49s / Backend Tests 1m9s / E2E Tests (Playwright) 2m57s / Frontend Lint & Security / Frontend Tests / Frontend Type Check） | `gh pr checks 204 --watch` で完了まで監視。run: 29378446350 / 29378446344 |
