# 診断レビュー [I193]
## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 対応方針 | H1 の案A（base 追従を先、gate-check を後）は、`gate-check.sh` の実装と整合している。`diff_outside_records` は、レビュー時点と今の両方で「merge-base からのブランチ自身の変更ファイル」を blob で比べる。merge-base が動いたときは、develop 側の進み分がブランチの変更ファイルに触れていれば G19 で止める。develop だけの変更は数えない。よって取り込み後の HEAD に対して使えば、診断メモの意図どおりに働く。 | `scripts/claude/gate-check.sh` 63〜88 行、`close/SKILL.md` 14〜39 行 |
| Info | 対応方針 | 並べ替えの際は、次の 3 点を手順書に明記するとよい。(1) gate-check の FAIL REASON=`base` / `dirty` の扱い（step 0 で fetch 済みなので base は解消する）。(2) step 0 で exit 1 になり、競合を解決してコミットした後も gate-check を通ること。(3) 「gate-check で review-gate に戻すのが 2 回続くときは止める」という数え方が、新しい順序でも保たれること。いずれも実装時の注意で、方針の欠陥ではない。 | `close/SKILL.md` 18・39 行 |
| Info | 根本原因 | M1 は、上限の数え始めに `STAGE_DONE: implement` を加える案で妥当。案Bの plan-review より implement のほうが「実装のやり直し」を直接表す、という選択理由も示されている。ただし fix-loop の ⇄ review-gate の途中でも `implement` 行が書かれる運用でないか、実装前に `review-gate/SKILL.md` 35 行付近と STAGE_DONE の書式を確認するとよい。fix-loop が `implement` を書くなら、上限が働かなくなる。 | `review-gate/SKILL.md` 35 行 |
| Info | 影響調査 | `pr-base-sync.sh` の他の呼び出し箇所、たとえば古い流れの `/close` 相当や `workflow.md` 以外の参照が、並べ替えの影響を受けないかは未記載。ただし案A はスクリプトを変えないため、実害の可能性は低い。 | 影響調査「呼び出し箇所」 |

## 影響調査の網羅性評価
- 同型バグ: gate-check の後に HEAD を動かす段階を探している。test-gate（記録の場所のみ）、close の step 5.5 `final`（確認のみ）、step 3（記録の移動のみ）を確認済みで、十分。
- 呼び出し箇所: `close/SKILL.md` と `workflow.md` のフロー 5 の両方を直す対象に含めている。
- テスト: S22（順序）と S19（区切りの文）の追加を挙げている。
- 根本原因は「確かめる場所が HEAD を変える操作より前にある」と具体的で、コードで裏付けられる。代替案 B・C を、却下理由つきで検討している。

VERDICT: OK
