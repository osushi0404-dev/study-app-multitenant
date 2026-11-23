# I615 自動テスト: 外で動く入口をレビュー済みの写しで動かし、人に `!` を頼まなくする

実行コマンド（例）: `bash scripts/claude/tests/test_i599_unreviewed_scripts.sh`（本体は `scripts/claude/tests/i599_cases.py`。一時フォルダに小さなリポジトリを作り、本物は書き換えない）

結果:
- backend: 対象外（コードの変更なし）
- frontend: 対象外（コードの変更なし）
- harness: 実装前のため未実行 → 下の「実行記録」

## テストケース
すべて `i599_cases.py` の中の確かめ（`ck`）。合否は入口のスクリプトの終了コード（合格=exit 0）。FG は、本体の写し（起動役・見張り・フック）を一時フォルダで壊し、その TC が不合格になることを確かめる（`assert old in src` で置き換え元が無ければ落ちる）。

| TC | 対応 | 確かめること（期待値） | FG（失敗の注入） |
|---|---|---|---|
| TC-01 | AC1 | 一時のリポジトリで、BASE を作った後に (a) 関係しない `scripts/claude/other.sh` を書き換える (b) 追跡していない `scripts/claude/n.sh` を置く (c) 無視される `scripts/claude/evil.tmp` を置く、のそれぞれで、`launch(r, "code-review.sh", "a", "b c")` が終了コード 0、印（`$MARK`）が `V1 <写し>/scripts/claude/review-process-lib.sh|a|b c|`（写しの部品から書かれ、引数がそのまま届く）、標準エラーに `!` の案内が無い | (1) 写しでなく作業ツリーの入口を動かす写し（`f"{snap}/scripts/claude/{name}"` を作業ツリーの入口に置き換え）で、印の場所が写しでなくなり不合格 (2) 変更があれば止める I599 の判定（`dirty`）を戻した写しで 75 になり不合格 |
| TC-02 | AC2 | (a) 入口 `code-review.sh` を書き換える (b) 部品 `review-process-lib.sh` を書き換える（`MARK` に `EVIL` を書く） (c) レビュー役の定義 `.claude/agents/code-reviewer.md` を書き換える、のそれぞれを、未コミットのままと、コミットした後（BASE との差）の両方で、`launch(r, "code-review.sh", "a")` が 75、印が無い（何も動かない）、標準エラーに `! bash scripts/claude/code-review.sh a` がある。部品でない `other.sh` の書き換えでは止まらない（TC-01） | (1) 部品を見ない写し（`parts` が入口だけを返す）で (b)・(c) が 0 になり不合格 (2) 75 の代わりに作業ツリーの入口を動かす写しで (b) の印に `EVIL` が出て不合格 |
| TC-03 | AC3 | (a) `refs/remotes/origin/develop` を消す（基準なし） (b) `HOME` をファイルにして写しの置き場所を作れなくする、のそれぞれで、`launch` が 75、印が無い、標準エラーに `!` の案内と理由（基準を求められない／写しを作れない） | 写しの失敗を「作業ツリーで動かす」に倒した写しで、印が出て不合格 |
| TC-04 | AC4 | 同じ一時のリポジトリで、フックの起動役（`reviewed-hook.sh scripts/claude/hooks/h.py`）と入口の起動役（`launch(r, "issue-source.sh", "a")`）を流すと、`~/.cache/claude-reviewed-snapshots/` の下にできる写しは BASE の 1 つだけで、フックの出力の `__file__` と入口の印の `$0` がどちらもその写しの中 | フックの起動役の置き場所の名前だけを変えた写しで、写しが 2 つになり不合格 |
| TC-05 | AC5・F1 | 写しの置き場所に、`.complete` のある写しを先に置き、その中に印のファイル `keep` を置く。`reviewed-hook.sh` を読み込み（`.`。関数を定義するだけ）、作成の処理 `_reviewed_snapshot_make` を写しの有無の確かめを飛ばして直接呼ぶと、戻り値 0・`keep` が残る・標準出力がその写しの場所 | `mv -T` の前に `rm -rf "$snap"` を戻した写しで、`keep` が消えて不合格 |
| TC-06 | AC5・F2 | `scripts/claude/hooks/*.py` の、`sys.executable` で始まる起動の引数の並び（`[sys.executable, …]`）がすべて 2 番目に `"-I"` を持つ（ast で読む）。数は 1 以上 | `sessionstart_context.py` の写しから `"-I", ` を外すと不合格 |
| TC-07 | AC6 | 見張り（`guard()`）が止める（exit 2・理由に `I615`）: `git merge --ff-only origin/develop 2>&1 \| tail -2`・`cd scripts && git switch x`・`X=1 git pull`・`git stash pop; ls`・`git switch x > o`・`timeout 5 git switch x`・`echo $(git rev-parse HEAD) && git rebase x`。止めない（exit 0・理由に `I615` が無い）: `git merge --ff-only origin/develop`・`git fetch origin && git merge --ff-only origin/develop`・`git status \| head`・`git log --oneline \| head -3`・`git stash list \| head`・`git commit -m "a \| b; c"`・`git diff > o`・`DANGER_OK=1 git checkout -- x`（I615 の理由では止めない） | `_git_update_inside` が常に None を返す写しで、止める形が通り不合格 |
| TC-08 | R1 | `bash -n .claude/hooks/reviewed-hook.sh`・`python3 -m py_compile .claude/hooks/unreviewed.py`・`python3 -m py_compile scripts/claude/hooks/pretooluse_guard.py` が 0 | （文法の確かめ。壊れた写しは作らない） |

既存の TC の直し（I599・I610）:
- TC-07〜TC-09（I599）: TC-01・TC-03 に置き換える（「レビュー前の中身があれば止める」は「写しで動く」に変わった）
- TC-12・TC-12b〜d（I610）: 写しの置き場所を `claude-reviewed-snapshots` に直す。ほかの期待値は変えない
- TC-11（`code-review.sh` の `gate_reviewed`）・TC-14（基準と `-c` の一致）: 変えない。TC-14 は `reviewed-hook.sh` の基準と `-c` を今までどおり確かめる

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i599_unreviewed_scripts.sh
bash scripts/claude/tests/test_guard_must_stop_cases.sh
bash -n .claude/hooks/reviewed-hook.sh
python3 -m py_compile .claude/hooks/unreviewed.py
python3 -m py_compile scripts/claude/hooks/pretooluse_guard.py
```

## 実行記録
- 2026-11-22〜24 implement（手元・サンドボックスの中）: `bash scripts/claude/tests/test_i599_unreviewed_scripts.sh` → exit 0（pass=56 fail=0。TC-I615-01〜07 と各 FG を含む）／`bash scripts/claude/tests/test_guard_must_stop_cases.sh` → exit 0（pass=3）／`bash scripts/claude/tests/test_pretooluse_checkout_guard.sh` → exit 0（pass=140）／`test_pretooluse_container_guard.sh`・`test_pretooluse_push_guard.sh`・`test_pretooluse_worktree_guard.sh`・`test_i182_guard_failsafe.sh`・`test_i200_guard_narrowing.sh`・`test_i444_guard_gaps.sh`・`test_i454_guard_env_writes.sh`・`test_i463_guard_optspec.sh`・`test_i469_guard_optspec_leftovers.sh`・`test_i187_mcp_filename_guard.sh` → すべて exit 0
- 2026-11-24 review-gate: CI（Harness Tests を含む）OK（`docs/reviews/I615_code_review_20261124_0231.md`・`CI_WAIT: OK`）。決定論ゲートの `bash -n`・`py_compile` は code-review.sh が実走、`test_*.sh` は CI が流した
- 2026-11-24 test-gate: 委譲（heavy）の行は無い。見張りの重いテストは manual No.5
