# I593 手動テスト: 判定の仕組みを変える PR を変更前の版で審査する

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | この PR の review-gate で `bash scripts/claude/code-review.sh I593` を流したときの起動役の出力を読む | 写しに `reviewer-agents-lib.sh` が無い（BASE はこのイシューのマージ前）ため、終了コード 75 と「`! bash scripts/claude/code-review.sh I593` で流してもらう」案内が出る（審査の入口でも、古い写しでは自動で流さない） | Claude | OK（2026-11-26・27）: `bash scripts/claude/code-review.sh I593`・`fix-diagnosis-review.sh`・`adversarial-review.sh` のすべてで終了コード 75 と「`! bash scripts/claude/<名前> …` で流してもらう」案内が出た（例: 「この入口か部品（.claude/agents/code-reviewer.md, scripts/claude/code-review.sh）をブランチで変えているので、レビュー済みの版では流しません」） | review-gate のコマンドの出力で確かめる |
| 2 | No.1 の後に人が `!` で流したコードレビューの記録（`docs/reviews/I593_code_review_*.md`）の証跡の節を読む | 「審査の版: 作業ツリー（写しで動かせなかった → 高リスク）」の行と、「高リスク判定: YES」の行がある。「### テストを弱めうる差分」に当たる `TEST_WEAKENING:` の行が証跡にある | Claude | OK: `docs/reviews/I593_code_review_20261126_1509.md`・`_1848.md` の 10 行目に「審査の版: 作業ツリー（写しで動かせなかった → 高リスク）」、20 行目に「高リスク判定: YES（計画レビュー=NO / path=YES / 審査の版=YES / 台帳の目印=NO）」、11 行目以降に `TEST_WEAKENING:` の行（新しいテストの中の目印の文字列）がある | 記録のファイルを Read で確かめる |

## 画面確認
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
| - | - | 理由: frontend/src を変えない | - | - | - | - |

結論: OK
