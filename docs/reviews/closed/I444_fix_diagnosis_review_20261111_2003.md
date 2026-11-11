# 診断レビュー [I444]
## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 根本原因 | 直接原因は妥当。`NO_DELTA=1` が前の周のまま引き継がれたことは、診断メモが引く `code-review.sh` の記述から読み取れる。コメント修正は F1 の再発防止の根を断つが、F1 の台帳の FILE は `guard_corpus_diff.py` になっている。レビュー役を呼べても、決定論ゲートから外した事実（`I444_auto_test.md`、fix-loop 1）と手で流した記録を見て resolved にできるかは、レビュー役の判断に依る。 | `scripts/claude/tests/test_guard_corpus_diff.sh:2`、`docs/reviews/I444_code_review_20261111_1949.md` の LEDGER F1 |
| Info | 対応方針 | 案 A（コメントのみの修正）は妥当。案 B は共有の仕組みの変更で範囲外のため、retro に回す判断も適切。`danger-ops.md` 34 行目にも「数分かかる」と一言足すと、より確実に誤解を防げる。計画の見落としの元は、コメントと手順書の両方だったため。必須ではない。 | `docs/runbooks/danger-ops.md:34` |
| Info | 影響調査 | `test_guard_corpus_diff.sh` を auto_test の決定論ゲートに置く open の文書が I444 だけである点は、Grep で再確認した。参照は `plan_I444.md`、`I444_auto_test.md`、`danger-ops.md` と過去の文書のみ。`test_guard_bash_oracle.sh` を直さない判断は、診断メモの「ゲートで exit 0・数秒」を根拠とする。私は oracle の所要時間までは確認していない。 | `scripts/claude/tests/` |

## 影響調査の網羅性評価
- 同型の写し: コメントの同型表現は oracle と corpus_diff の 2 箇所と特定されている。oracle は速いので対象外とした判断に、大きな問題は見当たらない。
- 他のイシューの決定論ゲート: `docs/tests/open/` で corpus_diff を置くのは I444 のみ。これは私の Grep でも確認できた。
- 呼び出し箇所: `run-all.sh` と `danger-ops.md` を確認している。コードの動きは変えないので、波及の恐れは小さい。
- 仕組みの穴（記録の場所だけの直しでは止める指摘が閉じない）は、このイシューでは直さず retro に回す。範囲の線引きとして妥当。

VERDICT: OK
