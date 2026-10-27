# 診断レビュー [I197]

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 影響調査 | `counted_records` に統一すると、ユーザー受け入れ記録（`ROUNDS: 0`・`VERDICT: OK`）の「受け入れた指摘の一覧」も `PREV_RECORDS` から外れる。受け入れ後の周で、受け入れ済みの指摘が再報告される可能性がある。受け入れは上限到達後の稀な場面なので許容範囲。ただし意図した挙動として、A27 かコメントに 1 行書いておくとよい。 | `review-gate/SKILL.md` L75、`adversarial-review.sh` L373 |
| Info | 根本原因 | H2 は「今の claude では `permission_denials` に入る」と実測済みで、現行コードの欠陥ではなく形が変わったときの備えである。診断メモもそう明記している。二重の守りとして `PreToolUse:` で始まり `hook error` を含む本文を拒否とみなす案 A は、案 B を退けた理由（反証実験が通らなくなる）と整合しており妥当。 | `review-process-lib.sh` L170（`claude_log_ran`） |
| Info | 対応方針 | H1 の根本原因は「`ROUNDS: 0` の扱いを `PREV_RECORDS` に入れ忘れた」で、症状の言い換えではない。コードでも確認できた。`review_base`（L92-93）は `ROUNDS: 0` を飛ばすが、`PREV_RECORDS`（L373）は `adversarial_records` をそのまま全部使っている。案 A は規則を 1 か所にまとめられ、案 B より適切。 | `adversarial-review.sh` L74-98、L373 |

## 影響調査の網羅性評価
- 同型の調査は十分。`ROUNDS:` を読む箇所を count_rounds・review_base・PREV_RECORDS の 3 か所と特定している。Grep でも、読み取り側はこの 3 か所以外に見当たらない。`gate-check.sh` は `ROUNDS` を読まないとの記載にも矛盾はない。
- `claude_log_ran` の呼び出しは `adversarial-review.sh` L263 の 1 か所。`check-permission-prompt.sh` は別の判定なので、変更対象外とする判断も妥当。
- テストは A27（`ROUNDS: 0` は渡さず `ROUNDS: 1` は渡す）・L6 と、それぞれの失敗注入 FG-A27・FG-L6 を足す計画で、失敗注入つき。
- 欠けているのは上の Info 1 件（受け入れ記録の扱い）のみ。着手を止める重大な欠落はない。

VERDICT: OK
