# 手動テスト: I108 Pillow 12.3.0 へのセキュリティアップデート（pip-audit CI ブロッカー解消）

## テスト方針

本イシューは UI 変更・画面挙動の変更を含まないため、ブラウザ目視の確認項目はない。
すべての確認はファイル内容・コマンド出力・CI 結果の確認であり、Claude が実施可能。
（画像機能の実機回帰は CI の Backend Tests / E2E Tests に委譲する — `I108_auto_test.md` TC-03）

## テスト項目

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `backend/requirements.txt` を Read し、Pillow の行を確認する | 9行目が `Pillow==12.3.0` であり、他の行（Pillow 以外の依存 19 行）に変更がない（`git diff` の変更行が `-Pillow==12.2.0` / `+Pillow==12.3.0` の1組のみ） | Claude | | |
| 2 | `gh pr checks 204` で Draft PR #204 の CI 結果を確認する | Backend Lint & Security（pip-audit 含む）/ Backend Tests / E2E Tests / Frontend 系の全チェックが `pass` と表示される | Claude | | TC-03 と同一コマンド。ここでは個別ジョブ名の pass 表示を目視相当で確認 |
| 3 | Backend Lint & Security ジョブのログで pip-audit ステップを確認する（`gh run view <run-id> --log` の該当ステップ） | pip-audit ステップに脆弱性検出の表（`PYSEC-...`）が**出力されていない**こと（`No known vulnerabilities found` またはステップ成功） | Claude | | 修正前は同ステップに PYSEC-2026-2253〜2257 の5件が表形式で出力されていた |
| 4 | （develop マージ後）PR #202（I107）で develop を取り込み、CI を再実行して結果を確認する | PR #202 の Backend Lint & Security が pass に転じる（pip-audit ブロック解消。AC-4 の充足確認） | Claude | | マージ後の後続確認。実施タイミングは I108 マージ直後 |

## 補足

- No.4 は受け入れ条件「develop へマージ後、後続 PR が CI グリーンになれる状態」の実地確認であり、I108 の close 前（マージ後）に実施する。
- Human 実施が必要な項目: なし（ブラウザ操作・外部ツール操作・感覚的確認を含まないため）。
