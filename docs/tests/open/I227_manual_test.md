<!--
## 手動テスト品質基準
- 期待結果は「正常に〜できる」ではなく具体的な画面表示・動作で記載すること
- 実施者: docs/runbooks/plan-writing-rules.md「実施者の区別」で決める（原則 Claude。Human の行は備考に「試した手段: …」が必須。scripts/claude/check-manual-test-executor.sh が確かめる）
-->

# I227 手動テスト: レビューの判定を機械が読む形・変数に置き換える

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M-01 | このブランチで、新しい版の関数を読み込んで本物の `/code-review` を動かす（一時のスクリプトに書いて流す）: `REVIEW_LIB_SOURCE_ONLY=1` で `scripts/claude/code-review.sh` を読み込み、`out=$(run_official_review "/code-review medium origin/develop...HEAD" code)` を実行し、`$out` の先頭 3 行と、`official_output_readable code "$out"` の終了コードを出す | `$out` に `(注意: 出力に決まった形の結果` で始まる行が無く、`official_output_readable code` の終了コードが 0。`(実行できず` は出ない | Claude | | 本物の Claude を 1 回動かす（数分〜15 分）。読み取りだけの鍵・plan モード（`run_official_review` の起動の形のまま） |
| M-02 | 同じく `out=$(run_official_review "/security-review" security)` を実行し、`$out` の最後の 3 行と、`official_security_verdict YES 0 "$out"` の出力を出す | 最後の空でない行が `SECURITY_FINDINGS: <数>`（半角数字）で、判定が `OK`。`$out` に `(注意: 出力に決まった形の結果` で始まる行が無い | Claude | | I212 の M-01 の回帰の確認（`run_official_review` の第 2 引数を種類に替えたため） |
| M-03 | この I227 の review-gate の基本レビュー（`bash scripts/claude/code-review.sh I227`）の記録を開き、組み込みの `/code-review` の出力の節を見る | `/code-review` の出力の節に `(注意: 出力に決まった形の結果` の行が無い（JSON の配列が出ていれば）。出ていない場合は、出力に ```` ```json ```` の囲みの配列が無いことを確かめ、食い違いが無いこと（注意と実際が一致）を記録する | Claude | | review-gate の実走の記録で確かめる（別に動かさない） |

結論:
