<!--
## 手動テスト品質基準
- 期待結果は「正常に〜できる」ではなく具体的な画面表示・動作で記載すること
- 実施者: docs/runbooks/plan-writing-rules.md「実施者の区別」で決める（原則 Claude。Human の行は備考に「試した手段: …」が必須。scripts/claude/check-manual-test-executor.sh が確かめる）
-->

# I212 手動テスト: 差分のレビューの起点を「見終えた最新の記録」にする

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M-01 | このブランチで、新しい版の関数を読み込んで本物の `/security-review` を動かし、判定を出す: `REVIEW_LIB_SOURCE_ONLY=1 bash -c '. scripts/claude/code-review.sh; out=$(run_official_review "/security-review" "$SECURITY_FINDINGS_PROMPT"); printf "%s\n" "$out" \| tail -3; official_security_verdict YES "$out"'` | 出力の最後の空でない行が `SECURITY_FINDINGS: <数>`（半角数字）で、最後に `OK` と出る。`(実行できず` は出ない | Claude | | 本物の Claude を 1 回動かす（数分）。読み取りだけの鍵・plan モード（`run_official_review` の起動の形のまま） |
| M-02 | この I212 の review-gate の基本レビュー（`bash scripts/claude/code-review.sh I212`）の記録を開く | 記録に `REVIEW_COMPLETE: YES` か `NO` の行が 1 行あり、注入された証跡に `- 見終えたか（次の差分のレビューの起点にできるか・I212）:` の行がある。2 周目以降があれば、出力の「差分のレビュー（台帳の n 周目・起点 …）」の起点が、`REVIEW_COMPLETE: YES` の最新の記録の `REVIEWED_COMMIT` と同じ | Claude | | review-gate の実走の記録で確かめる（別に動かさない） |

結論:
