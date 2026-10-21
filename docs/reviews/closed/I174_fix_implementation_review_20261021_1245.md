# 実装レビュー [I174]（代替サブエージェント）

`scripts/claude/fix-implementation-review.sh` の `claude -p` が失敗（`docs/reviews/I174_fix_implementation_review_20261021_1238.md`・FIX_GATE: SKIP）したため、同じ指示書 `.claude/review-agents/fix-implementation-reviewer.md` で独立サブエージェントが実施した結果を保存する。対象は 4 回目の fix-loop（計画 0-15・診断 `I174_fix_diagnosis_20261021_1226.md` の案 A）の作業ツリー差分。

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| BLOCKER | 回帰・副作用 | **(a) 実行の不備。** 対象が読めない取り消しを「停止」から `_analyze` の `git_unsure`（確認）に移したが、`_safety_net` は `_sn_judge` の結果のうち hard/danger/external/container しか集めず、main も `net["git_unsure"]` を見ない。精密判定が読み落として安全網だけが拾う書き方で、HEAD では 2 だった形が 0 に後退: `function f { git checkout -- "$1"; }; f f.txt`・`coproc { git restore -- "$F"; }`・`function f { git checkout -- sub/{s,t}.txt; }; f`・`coproc { git restore --pathspec-from-file=l.txt; }`・`cat <(git checkout -- $F)`（1 つ目は実行で変更が消えた）。直し方: `_safety_net` で `git_unsure` も集め、main で確認にする。外したら落ちるテストを追加 | `_safety_net`・`_sn_judge`・main の安全網の節 |
| HIGH | 方針一致 | **(a) 実行の不備。** 場所が読めない `-C`・`--work-tree`（`git -C "$(git rev-parse --show-toplevel)" checkout -- f.txt`・`git -C "$X" restore f.txt`・`git -C "$X" rm -f f.txt`・`git --work-tree="$X" checkout -- f.txt`）が推測で 0。`_loc_ambiguous` は cd しか見ず、`_git_run` の失敗を「変更なし」と扱う。push 側の `_git_loc_dynamic` とそろえて確認にする | `_git_revert_check`・`_loc_ambiguous` |
| Info | 回帰・副作用 | 場所が一意かをコマンド全体で 1 回だけ決めるので、git の後ろの `cd -` だけで手前の精密判定も確認になる（`cd sub && git checkout -- s.txt; cd - && git status` が 2→ASK）。素通しにはならず方針の文言どおり | `_loc_ambiguous`・`_analyze` |
| Info | 方針一致 | `coproc { cd "$X"; git checkout -- f.txt; }` は確認ではなく停止（安全側） | `_danger_reasons` |
| Info | 方針一致・スコープ | それ以外は方針どおり。第 3 周 H1〜H3・L5 は ASK、H4（checkout-index -f -a）は 2、L6・L7 は 0、`read-tree -u --reset` は 2、danger-ops.md 更新済み。一意な場所の精密判定・場所に依存しない停止は後退なし。checkout 81・push 164 合格 | 差分全体 |

VERDICT: BLOCKER
