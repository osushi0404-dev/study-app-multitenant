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
- 実装時: 未実施
- 実装後（/test）: 未実施

## テストケース

| TC | 内容 | コマンド | 期待 |
|----|------|---------|------|
| TC-0 | §2 確認 2（primary のブランチが I179 以降） | `test -f .worktreeinclude && grep -qx '.claude/worktrees/' .gitignore && grep -q '_owning_root' scripts/claude/hooks/pretooluse_guard.py` | exit 0 |
| TC-1 | `origin/HEAD` が develop | `[ "$(git symbolic-ref refs/remotes/origin/HEAD)" = refs/remotes/origin/develop ]` | exit 0 |
| TC-2a | wt-harness が登録に無い | `! git worktree list --porcelain \| grep -qx 'worktree /mnt/c/app/wt-harness'` | exit 0 |
| TC-2b | harness-1・harness-2 が登録にある | `git worktree list --porcelain \| grep -qx 'worktree /mnt/c/app/study-app-multitenant/.claude/worktrees/harness-1' && git worktree list --porcelain \| grep -qx 'worktree /mnt/c/app/study-app-multitenant/.claude/worktrees/harness-2'` | exit 0 |
| TC-3 | 2 つそれぞれに CLAUDE.md・`.claude/settings.json`・`backend/.env`・`.worktreeinclude` があり、HEAD が develop の履歴上にある（`.worktreeinclude` の有無で main 基点の空ワークツリーを弾く。`backend/.env` は `test -f` だけで中身は読まない） | `for w in H1 H2; do test -f "$w/CLAUDE.md" && test -f "$w/.claude/settings.json" && test -f "$w/backend/.env" && test -f "$w/.worktreeinclude" && git -C "$w" merge-base --is-ancestor HEAD origin/develop \|\| exit 1; done`（`H1`・`H2` は実パスに置き換える） | exit 0 |
| TC-4a | 撤去前: wt-harness の `??` がすべて「primary に同じ中身がある」か「develop に同じ番号の closed イシューがあるイシューファイル」のどちらか | 下の「TC-4a のスクリプト」 | exit 0 |
| TC-4b | 撤去後: `I184_review.md` の一覧（`<!-- copied-begin -->`〜`<!-- copied-end -->`）の 37 件がすべて primary にある | `L=$(sed -n '/<!-- copied-begin -->/,/<!-- copied-end -->/{/^docs\//p}' docs/reviews/open/I184_review.md); [ "$(printf '%s\n' "$L" \| grep -c .)" -eq 37 ] && printf '%s\n' "$L" \| while read -r f; do test -f "$f" \|\| exit 1; done` | exit 0 |
| TC-5 | ラベル説明文にワークツリー名が無い（取得に失敗したら不合格） | `out=$(gh label list --search track) && [ -n "$out" ] && ! printf '%s\n' "$out" \| grep -qE 'wt-harness\|study-app-multitenant'` | exit 0 |
| TC-6 | wt-harness の Compose プロジェクト・コンテナ・volume が無い | `! docker compose ls -a \| grep -q '^wt-harness ' && [ -z "$(docker ps -aq --filter label=com.docker.compose.project=wt-harness)" ] && [ -z "$(docker volume ls -q --filter label=com.docker.compose.project=wt-harness)" ]` | exit 0 |
| TC-7 | `worktree.md` §7 に反映のタイミングの補足（見出し語・取り込みコマンド・例外の参照）がある | `S=$(awk '/^## 7\./{f=1;next} /^## /{f=0} f' docs/runbooks/worktree.md); for k in 'ワークツリー間の反映のタイミング' 'git fetch origin' 'git merge origin/develop' '~/.claude' '.worktreeinclude' 'primary が今チェックアウトしているブランチ'; do printf '%s\n' "$S" \| grep -qF -- "$k" \|\| exit 1; done` | exit 0 |
| TC-9 | PR #313 に `danger-approved` ラベルが付いている（取得に失敗したら不合格） | `l=$(gh pr view 313 --json labels -q '.labels[].name') && printf '%s\n' "$l" \| grep -qx danger-approved` | exit 0 |
| TC-8 | 廃止（バックアップを取らない＝計画 D4。2026-10-24 計画承認時のユーザー判断） | — | — |

### TC-4a のスクリプト
```bash
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
```
（`??` 以外の未コミット変更〔` M` 等〕があれば `wt-remove.sh` が止めるので、ここでは見ない）

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
