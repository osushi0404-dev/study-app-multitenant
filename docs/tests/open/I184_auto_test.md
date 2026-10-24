# I184 自動テスト: I179 のワークツリー運用を既存の環境に適用する

実行場所: primary（`/mnt/c/app/study-app-multitenant`）のセッション。各 TC のコマンドを Bash で 1 つずつ実行する。

- アプリ（backend / frontend）のコード変更は無いため pytest・Jest・E2E は対象外。
- すべて環境・文書の状態を見る決定論 TC。**合否は exit code**（合格=exit 0・不合格=非ゼロ）。
- 否定・不在の TC は、計画時点（移行前）の環境そのものが失敗条件なので、計画時に実行して不合格になることを確かめた（下の「計画時（移行前）」）。存在を見る TC は、欠けた対象を与える失敗注入（FG）で不合格になることを確かめた。
- `H1`・`H2` は `/mnt/c/app/study-app-multitenant/.claude/worktrees/harness-1`・`…/harness-2` の略。

結果:
- backend: 対象外（コード変更なし）
- frontend: 対象外（コード変更なし）
- 計画時（移行前・2026-10-24）: 下記「計画時の実行記録」
- 実装時（2026-10-24・/implement）: TC-0・TC-1・TC-2a・TC-2b・TC-3・TC-4b・TC-5・TC-6・TC-7・TC-9 すべて exit 0。TC-4a は撤去前（ステップ 3 の後・2026-10-24）に exit 0（撤去後は計画どおり実行しない＝実行すると exit 1）。TC-8 は廃止（D4）。FG-2b・FG-3・FG-4b は引き続き exit 1（不合格を返す）。FG-7 は §7 に補足を入れた後なので exit 0（＝TC-7 の合格側の確認）
- 実装後（/test）: 未実施

## テストケース

| TC | 内容 | コマンド | 期待 |
|----|------|---------|------|
| TC-0 | §2 確認 2（primary のブランチが I179 以降） | `test -f .worktreeinclude && grep -qx '.claude/worktrees/' .gitignore && grep -q '_owning_root' scripts/claude/hooks/pretooluse_guard.py` | exit 0 |
| TC-1 | `origin/HEAD` が develop | `[ "$(git symbolic-ref refs/remotes/origin/HEAD)" = refs/remotes/origin/develop ]` | exit 0 |
| TC-2a | wt-harness が登録に無い | `! git worktree list --porcelain \| grep -qx 'worktree /mnt/c/app/wt-harness'` | exit 0 |
| TC-2b | harness-1・harness-2 が登録にある（注: harness-2 は手動 No.4 で自動片付け済み。/test 時点では作り直さない限り exit 1 になるので、合否は実装時〔2026-10-24〕の exit 0 の記録で判断する。TC-3 も同じ） | `git worktree list --porcelain \| grep -qx 'worktree /mnt/c/app/study-app-multitenant/.claude/worktrees/harness-1' && git worktree list --porcelain \| grep -qx 'worktree /mnt/c/app/study-app-multitenant/.claude/worktrees/harness-2'` | exit 0 |
| TC-3 | 2 つそれぞれに CLAUDE.md・`.claude/settings.json`・`backend/.env`・`.worktreeinclude` があり、HEAD が develop の履歴上にある（`.worktreeinclude` の有無で main 基点の空ワークツリーを弾く。`backend/.env` は `test -f` だけで中身は読まない） | `for w in H1 H2; do test -f "$w/CLAUDE.md" && test -f "$w/.claude/settings.json" && test -f "$w/backend/.env" && test -f "$w/.worktreeinclude" && git -C "$w" merge-base --is-ancestor HEAD origin/develop \|\| exit 1; done`（`H1`・`H2` は実パスに置き換える） | exit 0 |
| TC-4a | **撤去前だけ実行する**（計画書ステップ 3 の後・ステップ 5 の前。wt-harness 撤去後は `git -C` が失敗して必ず不合格になるので、ステップ 7・/test の全件実行には含めず、ステップ 3 での結果を記録として使う）: wt-harness の `??` がすべて「primary に同じ中身がある」か「develop に同じ番号の closed イシューがあるイシューファイル」のどちらか | 下の「TC-4a のスクリプト」 | exit 0 |
| TC-4b | 撤去後: `I184_review.md` の一覧（`<!-- copied-begin -->`〜`<!-- copied-end -->`）の 37 件がすべて primary にある | `L=$(sed -n '/<!-- copied-begin -->/,/<!-- copied-end -->/{/^docs\//p}' docs/reviews/open/I184_review.md); [ "$(printf '%s\n' "$L" \| grep -c .)" -eq 37 ] && printf '%s\n' "$L" \| while read -r f; do test -f "$f" \|\| exit 1; done` | exit 0 |
| TC-5 | ラベル説明文にワークツリー名が無い（取得に失敗したら不合格） | `out=$(gh label list --search track) && [ -n "$out" ] && ! printf '%s\n' "$out" \| grep -qE 'wt-harness\|study-app-multitenant'` | exit 0 |
| TC-6 | wt-harness の Compose プロジェクト・コンテナ・volume が無い | `! docker compose ls -a \| grep -q '^wt-harness ' && [ -z "$(docker ps -aq --filter label=com.docker.compose.project=wt-harness)" ] && [ -z "$(docker volume ls -q --filter label=com.docker.compose.project=wt-harness)" ]` | exit 0 |
| TC-7 | `worktree.md` §7 に反映のタイミングの補足（見出し語・取り込みコマンド・例外の参照）がある | `S=$(awk '/^## 7\./{f=1;next} /^## /{f=0} f' docs/runbooks/worktree.md); for k in 'ワークツリー間の反映のタイミング' 'git fetch origin' 'git merge origin/develop' '~/.claude' '.worktreeinclude' 'primary が今チェックアウトしているブランチ'; do printf '%s\n' "$S" \| grep -qF -- "$k" \|\| exit 1; done` | exit 0 |
| TC-9 | PR #313 に `danger-approved` ラベルが付いている（取得に失敗したら不合格） | `l=$(gh pr view 313 --json labels -q '.labels[].name') && printf '%s\n' "$l" \| grep -qx danger-approved` | exit 0 |
| TC-8 | 廃止（バックアップを取らない＝計画 D4。2026-10-24 計画承認時のユーザー判断） | — | — |

### TC-4a のスクリプト
撤去前に 1 回だけ実行する TC（wt-harness 撤去後は `git -C` が失敗して必ず不合格になる）なので、下の「決定論ゲート（自動実走）」には載せない。実行と結果はステップ 3 の記録（2026-10-24・exit 0）。再実行用ではない記録として、インデントのコードブロックで残す（fix-loop 2026-10-24 の診断 `docs/reviews/I184_fix_diagnosis_20261024_1326.md`）。

    P=/mnt/c/app/study-app-multitenant; W=/mnt/c/app/wt-harness
    closed=$(git -C "$P" ls-tree -r --name-only origin/develop docs/issues/closed/) || exit 1
    list=$(git -C "$W" status --porcelain --untracked-files=all) || exit 1
    printf '%s\n' "$list" | sed -n 's/^?? //p' | while read -r f; do
      case "$f" in
        docs/issues/open/I[0-9][0-9][0-9].md)
          n=$(basename "$f")
          printf '%s\n' "$closed" | grep -qx "docs/issues/closed/$n" && continue ;;
      esac
      cmp -s "$W/$f" "$P/$f" || { echo "NG: $f"; exit 1; }
    done

（`??` 以外の未コミット変更〔` M` 等〕があれば `wt-remove.sh` が止めるので、ここでは見ない）

## 決定論ゲート（自動実走）
`/code-review` が毎回実走する、副作用の無い再実行可能な確認（本イシューで PR に入る `worktree.md` の追記 3 つが残っていること＝TC-7 の要点と 4-10）。環境の状態を見る TC（TC-1〜TC-6・TC-9）は環境に依存するためここには載せない。

```bash
grep -qF 'ワークツリー間の反映のタイミング' docs/runbooks/worktree.md
grep -qF 'git merge origin/develop' docs/runbooks/worktree.md
grep -qF '作った直後のワークツリーは変更が無いので' docs/runbooks/worktree.md
```

## 失敗注入（FG）
| FG | 対象 TC | 注入 | 期待 |
|----|--------|------|------|
| FG-2b | TC-2b | パスを存在しない `…/harness-9` に変えて実行 | 非ゼロ |
| FG-3 | TC-3 | `H1`・`H2` を、CLAUDE.md 等の無い空の一時ディレクトリ（scratchpad）に置き換えて実行 | 非ゼロ |
| FG-3m | TC-3 | `.worktreeinclude` の確認を外し、HEAD を `origin/main` に置き換えた形（`git merge-base --is-ancestor origin/main origin/develop`）が合格してしまうことを確かめる（＝`.worktreeinclude` の確認が要る理由） | exit 0（この形だけでは main 基点を弾けない） |
| FG-4b | TC-4b | 一覧に存在しないパス `docs/issues/open/I999.md` を 1 行足した複製（scratchpad）に対して実行 | 非ゼロ |
| FG-7 | TC-7 | （移行前の `worktree.md` §7 がそのまま失敗条件） | 非ゼロ |

## 計画時の実行記録（移行前・2026-10-24）
各 TC を `bash -c` で 1 つずつ実行（TC-3 の `H1`・`H2` は実パス）。

| TC / FG | exit | 解釈 |
|--------|-----:|------|
| TC-0 | 0 | 本ブランチ（develop 3ca7375 から作成）は I179 以降を含む |
| TC-1 | 1 | `origin/HEAD` が `origin/main`（移行前の失敗条件） |
| TC-2a | 1 | wt-harness が登録されている（移行前の失敗条件） |
| TC-2b | 1 | harness-1/2 が無い |
| TC-3 | 1 | harness-1/2 が無い |
| TC-4a | 1 | まだコピーしていない（最初の NG: `docs/issues/open/I093.md`） |
| TC-4b | 1 | `I184_review.md` の一覧がまだ無い |
| TC-5 | 1 | 説明文に `wt-harness`・`study-app-multitenant` がある（移行前の失敗条件） |
| TC-6 | 1 | wt-harness の volume 4 つが残っている（移行前の失敗条件。`docker compose ls -a` だけなら合格していた） |
| TC-7 | 1 | §7 に補足が無い（＝FG-7） |
| TC-8 | 2 | （後に廃止＝D4）バックアップファイルが無い（`ls` が失敗） |
| TC-9 | 1 | PR #313 にラベルが無い（移行前の失敗条件。D8 決定後に追加して実行） |
| FG-9 | 1 | ラベル一覧を `track:harness`・`danger-approved-x` に差し替えると不合格（似た名前に当たらない完全一致） |
| FG-2b | 1 | 存在しないパスで不合格 |
| FG-3 | 1 | 空のディレクトリで不合格 |
| FG-3m | 0 | `origin/main` は develop の祖先なので、`merge-base` だけでは main 基点を弾けない → TC-3 の `.worktreeinclude` 確認が必要 |
| FG-4b | 1 | 存在しないパスを含む一覧で不合格 |
| FG-4b（対照） | 0 | 実在する 37 行の一覧なら合格（判定の書き方自体は通る） |
| FG-7 | 1 | 補足の無い §7 で不合格 |
| FG-8 | 1 | （後に廃止＝D4）空のバックアップで不合格 |

TC-7 の合格側（補足を入れた後に exit 0 になること）と TC-4a の合格側は、実装時に確かめる。

## 再発防止記録（fix-loop・2026-10-24）
- **なぜ失敗したか**: `/code-review` の omission-lint（`scripts/claude/code-review.sh` の `omission_lint()`）は、「## 決定論ゲート（自動実走）」節の外の fenced コードブロックに `grep -q` 等があると HIGH にする。TC-4a のスクリプトを fenced ```bash で書き（中に `grep -qx`）、ゲート節も無かったため、`/code-review` が 2 回とも FINAL VERDICT: HIGH になった（LLM のレビューは原因を「/test 未実施」と取り違えていた）
- **何を変えたか**: TC-4a のスクリプトを、ゲートに載せない理由（撤去前に 1 回だけ・撤去後は必ず失敗）を明記したうえでインデントのコードブロックにした。`## 決定論ゲート（自動実走）` 節を作り、PR に入る `worktree.md` の追記 3 つを `grep -qF` で毎回実走する。TC-2b・TC-3 に harness-2 の自動片付け後の扱いを注記。詳細は `docs/reviews/I184_fix_diagnosis_20261024_1326.md`・`docs/reviews/I184_fix_test_result_20261024_1326.md`
- **セキュリティ上の考慮点**: なし（テスト文書だけの変更。ゲートのコマンドは読み取りだけの `grep -qF` で `classify_gate` の ALLOW）
- **次回どう防ぐか**: auto_test.md で検証コマンドを fenced に書くときは、ゲート節に宣言して実走させるか、一回限りの記録ならゲートに載せない理由を書いて fenced 以外で残す。/retro の材料: (1) fix-loop の実装・テストレビューのスクリプトが未追跡ファイルの中身を全部入力に足すため、未コミットのイシューファイルが多い primary では `claude -p` が失敗して SKIP になる（本 fix-loop では独立サブエージェントで代替）。(2) 計画時に omission-lint を通していれば `/code-review` 1 回目で捕まえずに済んだ
