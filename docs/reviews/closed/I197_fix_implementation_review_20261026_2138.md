# 実装レビュー [I197]
## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 方針一致 | 診断メモの対応方針（1・2・3・4・5・7・8・9 は案 A、6 と 10 は見送り）と実装が一致している。計画書の §4.3 の 2・5、§4.3.1 の文、計画変更記録 4 も同じ内容に直っている。方針外の変更は見当たらない。 | `adversarial-review.sh` 全体、`plan_I197.md` |
| Info | 回帰・副作用 | `review_base()` は `ROUNDS:` の行が無い古い記録を 1 周として数える（`${r:-1}`）。`count_rounds` と同じ規則で、`ROUNDS: 0` の記録だけを飛ばす。スクリプトは `set -e` を使っておらず、`[ -n "$sha" ] && base=...` が偽でもループは止まらない。 | `review_base` |
| Info | 回帰・副作用 | `run_perspective` は最後に成功した呼び出しのログ（`good_log`）で判定する。続きの呼び出しが時間切れになっても、前の報告を消さない。最初の呼び出しが失敗した場合は `good_log` が空で、従来どおり「時間切れ」か「失敗」になる。`body.txt` は事前に空で作ってあり、`set -u` に抵触しない。 | `run_perspective` |
| Info | 回帰・副作用 | `check_worktree` は HEAD・ブランチ・記録の外の変更を周全体のフラグ `$RUN/dirty` に追記する。`REVIEWED_HEAD` と `REVIEWED_BRANCH` は観点の起動より前に設定済みで、並列の追記も安全。全観点の終了後にもう一度呼ぶ。記録のコミットはその後なので、誤検知は起きない。 | `check_worktree`、本体 |
| Info | 回帰・副作用 | `trap cleanup_adv EXIT` に `kill_tree` を使っており、`code-review.sh` を source していて定義済み（136 行目）。`PIDS=()` は `trap` の前に初期化されている。`INT`・`TERM` は `exit 130` で EXIT の trap に流れる。 | 本体の `trap` 部分 |
| Info | 回帰・副作用 | `extract_experiments` は `.cmd` が既にある id を書き直さない。実行したコマンドと記録のコマンドが食い違わなくなる。記録に貼るコマンドも `neutralize_machine_lines` を通す。 | `extract_experiments`、記録の書き出し |
| Info | スコープ | 非ゼロ終了の実験を未検証にしない判断（指摘 6）と、`gate-check.sh` との共有の見送り（指摘 10）は、計画変更記録に理由つきで書かれている。計画の範囲内。 | 計画変更記録 4 |
| Info | 回帰・副作用 | `git diff` の失敗を `ADVERSARIAL_ERROR: DIFF`（exit 2）で止める。以前の「失敗メッセージが差分になる」状態は解消した。ただし `--name-status` と `git diff` を `||` でつないでいるため、一覧の失敗でも同じエラーになる。これは意図どおり。 | 本体の差分取得部分 |
| Info | テスト | A16〜A22 と、それに対応する FG（失敗条件の注入）が追加された。FG-A3・FG-A8 は置き換え前の文字列が新しい形に合わせて直っている。実行結果は差分からは確認できないので、テスト工程で確かめること。 | `test_i197_adversarial_process.sh` |

重大度 BLOCKER・HIGH の指摘はない。前回の BLOCKER（指摘 1: `ROUNDS: 0` の記録が起点になり、空の差分で OK が出うる）は、`review_base` の修正と A16・FG-A16 で解消している。High だった指摘 2（続きの失敗で前の報告が消える）も、往復前の `2 × ADV_MIN_STEP` の確認と `good_log` で解消している。

VERDICT: OK
