# I062 手動テスト

- **関連イシュー**: #128
- **計画書**: docs/plans/open/plan_I062.md

> 大半の検証は自動テスト（`docs/tests/open/I062_auto_test.md` / `bash scripts/claude/tests/test_review_verdict.sh`）でカバーする。本文書は `claude -p` 込みの実レビュー経路（非決定的・実行コスト高）と、生成側エージェントが実際に `VERDICT:` 行を出力することの確認に限定する。

> **実施者の見直し（feedback 反映）**: 本イシューの `/code-review I062`・`/plan-issue-review I062` は `/test` フロー内で実行済みであり、生成された実アーティファクト（レビューファイル）の最終行は Read/tail で機械確認できる。よって No.1〜3 はブラウザ操作不要で **Claude 実施可**に再判定した。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `/code-review I062` を実行し、生成された `docs/reviews/I062_code_review_*.md` の最終行を確認する | 最終行に `VERDICT: BLOCKER` / `HIGH` / `OK` のいずれか1行が出力されている | Claude | ✅ OK | 最新（ステップ5後）`docs/reviews/I062_code_review_20260616_0651.md` の最終行 = `VERDICT: OK`。末尾アンカー版 `detect_code_verdict` でも正常系維持 |
| 2 | 同じ実レビュー結果に対するスクリプトの最終案内表示を確認する | レビュー本文の重大度（太字含む）と一致した案内（⛔ / ❌ / ✅）が表示され、誤 `✅` が出ない | Claude | ✅ OK | レビュー本文は Blocker/High なし → スクリプトは `✅ コードレビュー完了` を出力。`detect_code_verdict` が `VERDICT: OK` を一次判定 |
| 3 | `/plan-issue-review I062` を実行し、生成された `docs/reviews/I062_plan_review_*.md` の最終行を確認する | 最終行に `VERDICT: BLOCKER` / `HIGHRISK` / `OK` のいずれか1行が出力されている | Claude | ✅ OK | 最新（ステップ5後）`docs/reviews/I062_plan_review_20260616_0055.md` の最終行 = `VERDICT: OK`。更新後 `plan-reviewer.md` の新契約が機能 |
| 4 | `plan_I###_2.md` 等の再作成計画書が存在する実イシューで `/code-review` または `/plan-issue-review` を実行する | スクリプトが連番数値順で最新（最大サフィックス）の計画書を読み込む | Claude | ✅ OK（自動TC代替） | I062 には `plan_I062_2.md` が存在しないため、`_N` 連番ロジックは決定論的な自動テスト TC-01〜TC-04（`_10`>`_9`・open/closed 横断含む）で代替確認済み |
