# 実装レビュー [I193]

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 方針一致 | H1〜H2、M1〜M3、繰り返しの上限は、診断メモ(4)の方針どおりに実装されている。効率の Medium と Low は対象外とされ、変更に混ざっていない。 | 全体 |
| Info | 回帰・副作用 | `code-review.sh` は、PR を取れないときと PR が無いときに `CI_WAIT: NO_PR` を出して exit 1 で止まる。以前の CI 待ちを丸ごと飛ばす動きはなくなった。`if ! PR_NUM=$(...)` の形は `set -e` の下でも安全。`--jq '.[0].number // empty'` は PR が無ければ空になる。 | code-review.sh |
| Info | 回帰・副作用 | `post-review-comment.sh` は失敗しても exit 0 で終わる。「失敗しても止めない」という元の方針を保っている。コメントが 60000 バイトを超えるときは先頭 58000 バイトで切る。`head -c` は日本語の文字の途中で切れる恐れがあるが、表示が崩れるだけ。 | post-review-comment.sh |
| Info | 回帰・副作用 | `review-timer.sh` は引数を検証している（数字のみ、1〜3600）。`Bash(bash scripts/claude/*)` の許可に当たるので、承認画面は出ない。`sleep` を直接書いた手順は S17 のテストで検出される。 | review-timer.sh、S17 |
| Info | 回帰・副作用 | `gate-check.sh` の here-string 化は、pipefail 下で `grep -q` が早く終わったときの SIGPIPE(141) を避ける。意味は変わらない。 | gate-check.sh |
| Info | 回帰・副作用 | F10 は一時リポジトリを使うようになった。`$FS` は絶対パスで、`flow-stage.sh` は `git rev-parse --show-toplevel` を使う。そのため本物の I193 の記録に依存せず、M2 は解消している。 | test_i193_official_flow.sh |
| Info | テスト | 既存の FG-D1 は `review-timer.sh 900` に追従して更新されている。S17〜S19 と FG-S17 が追加され、失敗条件を注入して落ちることを確かめている。`S18` の `NO_PR` 検査は文字列の存在確認なので実行時の挙動までは見ないが、軽微。 | test_i181、test_i193 |
| Info | スコープ | 未追跡の `docs/issues/open/I186・I188・I189・I191・I192` と、それぞれの issue_review は I193 の差分と無関係。ほかのイシューの起票ファイルが作業ツリーに載っているだけで、コミット時に混ぜないよう注意が要る。I193 のコードへの影響はない。 | docs/issues/open、docs/reviews |
| Info | 方針一致 | test-gate の `dirty` の扱いは、「この段階は記録の場所の外をコミットしない」「実装の一部なら `NEXT: fix-loop`」に整理された。上限の記述（4 回目以上は High 以上だけを直し、5 回目で止める）も、診断メモの「3 回続けて HIGH なら 4 回目から」と整合している。 | SKILL.md ×2 |

VERDICT: OK
