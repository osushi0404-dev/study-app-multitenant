# I183 手動テスト: djangorestframework 3.18.0 → 3.18.2（pip-audit 失敗の解消）

対象: PR #310（feature/I183-drf-3-18-2-cve-fix → develop）

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M1 | push 後、`gh pr checks 310 --watch` で PR の全チェックの完了を待つ | Backend Lint & Security / Backend Tests / Frontend Type Check / Frontend Lint & Security / Frontend Tests / E2E Tests (Playwright) を含む全チェックが **pass** と表示される | Claude | OK | 2026-10-24 実施（head 41bbb06）。全 6 チェック pass: Backend Lint & Security 1m8s / Backend Tests 1m16s / E2E Tests (Playwright) 9m59s / Frontend Lint & Security 1m41s / Frontend Tests 1m46s / Frontend Type Check 1m47s。AC2・AC3・AC4 |
| M2 | `gh run view <run-id> --log` で「Backend Lint & Security」ジョブの pip-audit ステップのログを確認する | `No known vulnerabilities found` と出ており、ステップが成功している（CVE-2026-114136/114137/114138 の記載が無い） | Claude | OK | 2026-10-24 実施（run 39865644887・job 120127040735）。`Run pip-audit -r requirements.txt` の出力は `No known vulnerabilities found`、CVE-2026-114136/114137/114138 の記載なし。ローカル TC-03 と一致。AC2 |
| M3 | （参考・マージ後・I182 側の作業）I182 の担当（wt-harness のセッション）が PR #308 に develop を取り込み、`gh pr checks 308` を確認する | PR #308 の Backend Lint & Security が pass になる | Claude（I182 側） | 対象外 | AC4 の後半。本イシューの合否には含めない（I182 の記録に残す） |
