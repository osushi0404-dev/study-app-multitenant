# I498 手動テスト: マージ前の最終確認の CI 待ちの上限を code-review.sh と 1 か所にまとめる

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | review-gate 段階の `bash scripts/claude/code-review.sh I498`（背景の実行）の出力を読む（この PR は `scripts/claude/` を変えるので Harness Tests が動く） | CI 待ちの行が `待ち（未完了: …）... <経過>s / 1980s` の形で出て、最後に `CI_WAIT: OK` が出る（上限が 1980 秒で効き、待ちの途中で打ち切られない） | Claude | OK（2026-11-16 test-gate）: review-gate の実行（e778d4a3）の出力で、待ちの行が `0s / 1980s` から `495s / 1980s` まで 15 秒ごとに 34 行出て（最後まで残ったのは Harness Tests）、続けて `CI_WAIT: OK`・`FINAL_VERDICT: OK`。前面の上限 10 分の近くまで待っても打ち切られなかった | review-gate の実際の実行の記録を読む。CI が 1 回目の照会で終わっていて待ちの行が出ないときは、`REVIEW_LIB_SOURCE_ONLY=1` で読み込んだ `wait_ci` の時間切れの出力（TC-01 の T1）を根拠にし、その旨を書く |

- 実際の `pr-base-sync.sh final` の背景での実行は、この PR の close の手順 5.5 そのもの（test-gate の時点では PR が Draft なので `final` は DRAFT で止まり確かめにならない・計画書 §6）。結果は close のマージ依頼の報告に書く

結論: OK
