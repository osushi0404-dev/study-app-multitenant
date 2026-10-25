# 実装レビュー [I193]
## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 回帰・副作用 | `is_record_path` と `changed_outside_records` は `code-review.sh` の 416 行目（`REVIEW_LIB_SOURCE_ONLY` の return）より前で定義されています。そのため `gate-check.sh` が source しても使えます。 | code-review.sh 84〜102 行 |
| Info | 回帰・副作用 | 判定（RISK・VERDICT）を組み込み出力の追記前に行う順序になっています。追記する出力は `neutralize_machine_lines` で機械可読行を無効化済みです。そのため `REVIEWED_COMMIT` などの行の偽造や、表の `\| High \|` の誤検出は起きません。 | code-review.sh 567〜586 行 |
| Info | 方針一致 | 診断メモ3の方針（H1・H2・M1〜M6・L1・L2）に沿った実装です。判定行が無いときの 1 回だけのやり直し、未報告の観点を合格に数えない扱い、blob 比較への変更、粗く止まる側に倒す G19、テスト追加のいずれも確認できました。L2 は採らず、注記だけを足しています。 | 全体 |
| Info | 回帰・副作用 | `develop 側も変えていた` の規則は、ブランチと develop が同じファイルを触ると review-gate をやり直す側に倒れます。これは意図どおりの fail-closed です。 | gate-check.sh の `diff_outside_records` |
| Info | スコープ | 未追跡のイシューファイル（I186・I188・I189・I191・I192）とそのレビュー記録は、`docs/` 配下の記録の場所にあります。実装の範囲に影響しません。 | docs/issues, docs/reviews |

VERDICT: OK
