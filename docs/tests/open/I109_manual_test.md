# I109 手動テスト: 依存脆弱性ドリフトの定期検知（scheduled 監査＋自動起票）

## Phase A（develop マージ前）

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M1 | ブラウザで https://github.com/osushi0404-dev/study-app-multitenant/settings にオーナー（osushi0404-dev）でアクセスし、General → Default branch を `main` から `develop` に変更する | Default branch の表示が `develop` になる | Human | OK | 実装ステップ1（前提ゲート）。2026-07-15 ユーザー実施（スクリーンショット確認） |
| M2 | `gh api repos/osushi0404-dev/study-app-multitenant --jq .default_branch` を実行 | 出力が `develop` | Claude | OK | 2026-07-15 実行・出力 `develop` を確認 |
| M3 | `gh label list --search dependency-audit` を実行 | `dependency-audit` ラベルが 1 件表示される | Claude | OK | 2026-07-15 実行・`dependency-audit（scheduled 依存監査の自動起票・#D93F0B）` 1 件を確認（実装ステップ2 で作成） |
| M4 | PR #211 の CI 結果を `gh pr checks 211` で確認 | 全チェックが pass（fail 0 件） | Claude | | 既存 CI が新規ファイルで壊れないこと |

## Phase B（develop マージ後・クローズ処理内で GitHub イシュークローズ前に実施）

**順序特例**: workflow_dispatch は workflow が default branch（develop）上に存在して初めて実行可能なため、以下はマージ後に実施する（plan_I109.md Risk 参照）。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M5 | `gh workflow run dependency-audit.yml`（simulate_failure 未指定=none）を実行し、`gh run list --workflow=dependency-audit.yml` で完了を待って結果確認 | run の conclusion が `success`。`gh issue list --label dependency-audit --state open` が **0 件**（グリーン時は起票されない） | Claude | | グリーン経路。現状 pip-audit 0 件・npm audit critical 0 件のため success になる（計画書調査結果） |
| M6 | `gh workflow run dependency-audit.yml -f simulate_failure=backend` を実行し完了を待つ | run の conclusion が `failure`。`gh issue list --label dependency-audit --state open` に **タイトル `[dependency-audit] backend: 依存脆弱性を検知（scheduled audit）` のイシューが 1 件**作成され、body に `SIMULATED FAILURE` と「## 対応手順」（runbook 参照）が含まれる | Claude | | fail 経路＋GITHUB_TOKEN の issues:write の live 検証。403 等で起票失敗時はオーナーが Settings → Actions → General → Workflow permissions を確認（Risk 対応） |
| M7 | M6 と同一コマンドをもう一度実行し完了を待つ | open の `[dependency-audit] backend:` イシューは **1 件のまま増えない**。M6 のイシューに**コメントが 1 件追記**される | Claude | | 重複防止の live 検証 |
| M8 | M6 で作成されたテストイシューを `gh issue close <番号> --comment "I109 の検知動作テスト（simulate_failure）による起票のためクローズ"` でクローズ | イシューが closed になり、open の dependency-audit イシューが 0 件に戻る | Claude | | テスト残骸のクリーンアップ |
| M9 | （任意・翌営業日）Actions タブまたは `gh run list --workflow=dependency-audit.yml` で JST 7:00 台の scheduled 実行を確認 | schedule イベント起因の run が存在し conclusion が `success` | Human | | AC 必須ではない（AC は workflow_dispatch 検証まで）。schedule 発火の最終確認 |

結論: OK / NG （全 TC 完了後に記入）
