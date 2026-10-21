#!/usr/bin/env bash
# I081: pretooluse_guard.py の checkout/restore データ消失防止を決定論検証する。
# 実行: bash scripts/claude/tests/test_pretooluse_checkout_guard.sh
#
# temp git repo を立て、フックへ stdin JSON を投入して exit code を検証する
# （実 checkout は実行しない＝フックの判定のみを見る）。
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
GUARD="$REPO_ROOT/scripts/claude/hooks/pretooluse_guard.py"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cd "$TMP" || exit 1
git init -q
git config user.email t@example.com
git config user.name tester
printf 'orig\n' > tracked.txt
git add tracked.txt
git commit -qm init

json() { printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$1"; }
run()  { json "$1" | python3 "$GUARD" >/dev/null 2>&1; echo $?; }
# ask 判別版（test_pretooluse_push_guard.sh と同じ定義）: exit 0 ＋ stdout に permissionDecision=ask を含めば ASK。
runj() { local out code; out=$(json "$1" | python3 "$GUARD" 2>/dev/null); code=$?;
         if [ "$code" = "0" ] && printf '%s' "$out" | grep -q '"permissionDecision":[[:space:]]*"ask"'; \
         then echo "ASK"; else echo "$code"; fi; }

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }

# --- clean baseline（block しない） ---
ck "G1 clean checkout -- file" 0 "$(run 'git checkout -- tracked.txt')"
ck "G2 branch create -b"       0 "$(run 'git checkout -b newbr')"

# --- worktree を dirty にして block を検証 ---
printf 'changed\n' >> tracked.txt
ck "G3 dirty checkout -- file" 2 "$(run 'git checkout -- tracked.txt')"
ck "G4 dirty restore file"     2 "$(run 'git restore tracked.txt')"
ck "G5 dirty checkout ."       2 "$(run 'git checkout .')"
ck "G6 branch switch name"     0 "$(run 'git checkout develop')"
ck "G7 DANGER_OK → ask (I174)" ASK "$(runj 'DANGER_OK=1 git checkout -- tracked.txt')"

# --- staged のみ（index）変更 → restore --staged は素通し ---
git add tracked.txt
ck "G8a restore --staged"      0 "$(run 'git restore --staged tracked.txt')"

# --- untracked → 素通し ---
printf 'x\n' > untracked.txt
ck "G8b untracked checkout"    0 "$(run 'git checkout -- untracked.txt')"

# --- 危険 bash 回帰（既存ハードブロック維持） ---
ck "G9 force push exit2"       2 "$(run 'git push --force origin x')"

# --- 空白を含むパス（dirty）も shlex で検出 ---
printf 'orig\n' > "my file.txt"
git add "my file.txt"
git commit -qm spacefile
printf 'changed\n' >> "my file.txt"
ck "G10 dirty spaced path"     2 "$(echo '{"tool_name":"Bash","tool_input":{"command":"git checkout -- \"my file.txt\""}}' | python3 "$GUARD" >/dev/null 2>&1; echo $?)"

# --- && 後続の checkout も検出（shlex が && を単一トークン化）。
#     先頭は保護ブランチ以外への push にして既存 push ブロックを誘発しない ---
printf 'orig\n' > g11.txt
git add g11.txt
git commit -qm g11
printf 'x\n' >> g11.txt
ck "G11 && trailing checkout"  2 "$(run 'git push origin tmpbranch && git checkout -- g11.txt')"

# --- 語にくっついた ; で区切る（I174: 区切らないと後ろの git log の -- g11.txt を checkout の対象と誤読する） ---
ck "G12 checkout br; log -- dirty (複数行)" 0 "$(run 'git status\ngit checkout feat; git log --oneline -3 -- g11.txt')"
ck "G13 checkout br; log -- dirty (1 行)"  0 "$(run 'git checkout feat; git log -- g11.txt')"
ck "G14 log; checkout -- dirty も検出"     2 "$(run 'git log -1; git checkout -- g11.txt')"
ck "G15 fetch & checkout -- dirty も検出"  2 "$(run 'git fetch & git checkout -- g11.txt')"

# --- 作業場所を変える形（I174 敵対的レビュー第 3 周 H1）: -C・cd・pushd・--work-tree・入れ子の中も同じに止める ---
mkdir sub
printf 'orig\n' > sub/s.txt
git add sub/s.txt
git commit -qm sub
printf 'x\n' >> sub/s.txt
ck "G16 git -C . checkout -- dirty"        2 "$(run 'git -C . checkout -- sub/s.txt')"
ck "G17 git -C sub restore dirty"          2 "$(run 'git -C sub restore s.txt')"
ck "G18 cd sub && checkout -- dirty"       2 "$(run 'cd sub && git checkout -- s.txt')"
ck "G19 cd -- sub && checkout -- dirty"    2 "$(run 'cd -- sub && git checkout -- s.txt')"
ck "G20 pushd sub && restore dirty"        2 "$(run 'pushd sub && git restore s.txt')"
ck "G21 bash -c cd sub && restore dirty"   2 "$(run "bash -c 'cd sub && git restore s.txt'")"
ck "G22 --work-tree=. checkout -- dirty"   2 "$(run 'git --work-tree=. checkout -- sub/s.txt')"
ck "G23 cd sub && cd .. 後の clean ファイル" 0 "$(run 'cd sub && cd .. && git checkout -- tracked.txt')"
# --- ステージ済みの変更（第 3 周 M7）: コミットから戻す形は消えるので止める・index から戻す形は残るので通す ---
printf 'orig\n' > st.txt
git add st.txt
git commit -qm st
printf 'staged\n' >> st.txt
git add st.txt
ck "G24 checkout HEAD -- staged"           2 "$(run 'git checkout HEAD -- st.txt')"
ck "G25 restore -s HEAD -SW staged"        2 "$(run 'git restore -s HEAD -SW st.txt')"
ck "G26 checkout -- staged（index から）"  0 "$(run 'git checkout -- st.txt')"
# --- 同じ結果になる別の操作（第 3 周 M9）---
printf 'sub/s.txt\n' > list.txt
ck "G27 restore --pathspec-from-file"      2 "$(run 'git restore --pathspec-from-file=list.txt')"
ck "G28 git rm -rf dirty"                  2 "$(run 'git rm -rf sub')"
ck "G29 git rm --cached は通す"            0 "$(run 'git rm --cached -r sub')"
ck "G30 git.exe checkout -- dirty"         2 "$(run 'git.exe checkout -- sub/s.txt')"
ck "G31 bash -c GIT_WORK_TREE=. checkout"  2 "$(run "bash -c 'GIT_WORK_TREE=. git checkout -- sub/s.txt'")"
# 対象をコマンド・変数・xargs で渡す形（どれを戻すか読めない）は、その場所に変更があれば止める（code-review 20261021_0905 第 1 周）
ck "G32 git diff --name-only | xargs git checkout --" 2 "$(run 'git diff --name-only | xargs git checkout --')"
# shellcheck disable=SC2016  # $(…)・$f・$S を展開せず、そのまま guard に渡すのが目的
ck "G33 git restore \$(git diff --name-only)"      2 "$(run 'git restore $(git diff --name-only)')"
# shellcheck disable=SC2016  # $(…)・$f・$S を展開せず、そのまま guard に渡すのが目的
ck "G34 for f in \$(…); do git checkout -- \$f"    2 "$(run 'for f in $(git diff --name-only); do git checkout -- $f; done')"
# ( ) の中の cd は抜けると戻る。どちらの場所でも当たれば止める
mkdir -p other
ck "G35 bash -c (cd other && ls) && checkout"      2 "$(run "bash -c '(cd other && ls) && git checkout -- sub/s.txt'")"
ck "G36 bash -c pushd; popd; checkout"            2 "$(run "bash -c 'pushd other; popd; git checkout -- sub/s.txt'")"
# -- なしのコミットから戻す形もステージ済みの変更を数える
ck "G37 checkout HEAD <staged>（-- なし）"         2 "$(run 'git checkout HEAD st.txt')"
ck "G38 checkout HEAD .（-- なし）"                2 "$(run 'git checkout HEAD .')"
ck "G39 ブランチの切り替えは通す"                  0 "$(run 'git checkout develop')"
ck "G40 bash -c (cd other && ls) && status は通す" 0 "$(run "bash -c '(cd other && ls) && git status'")"
# まとめて書いた -SW / -WS（-s なし）もステージ済みを戻す形（code-review 20261021_0905 第 1 周・テスト観点）
ck "G41 restore -SW <staged>（-s なし）"          2 "$(run 'git restore -SW st.txt')"
ck "G42 restore -WS <staged>（-s なし）"          2 "$(run 'git restore -WS st.txt')"
# 見張りの作業ディレクトリとは別のリポジトリを GIT_DIR / GIT_WORK_TREE で指す形（G31 は同じ場所を指すので測れない）
T2="$(mktemp -d)"
trap 'rm -rf "$TMP" "$T2"' EXIT
git -C "$T2" init -q
git -C "$T2" config user.email t@example.com
git -C "$T2" config user.name tester
printf 'orig\n' > "$T2/s2.txt"
git -C "$T2" add s2.txt
git -C "$T2" commit -qm i
printf 'x\n' >> "$T2/s2.txt"
ck "G43 GIT_DIR=<別> GIT_WORK_TREE=<別> checkout" 2 "$(run "GIT_DIR=$T2/.git GIT_WORK_TREE=$T2 git checkout -- s2.txt")"
ck "G44 env GIT_DIR=<別> … checkout"             2 "$(run "env GIT_DIR=$T2/.git GIT_WORK_TREE=$T2 git checkout -- s2.txt")"
ck "G45 bash -c 'env GIT_DIR=<別> … checkout'"   2 "$(run "bash -c 'env GIT_DIR=$T2/.git GIT_WORK_TREE=$T2 git checkout -- s2.txt'")"
# 作業記録の再判定で見つかった余計な停止: まとめ書きの -qb（ブランチ作成）・場所が変数の cd の後
ck "G46 checkout -qb <新ブランチ> は通す"         0 "$(run 'git checkout -qb feat2')"
# shellcheck disable=SC2016  # $(…)・$f・$S を展開せず、そのまま guard に渡すのが目的
ck "G47 cd \$S; git checkout -qb は通す"          0 "$(run 'cd $S; git checkout -qb feat3')"

# --- FALSEGREEN（自動注入）: 判定呼び出し行を無効化した複製で dirty が素通し /
#     実体で block。両者の差で「block は判定行に依存」を機械裏取り（false-green 排除） ---
BROKEN="$TMP/guard_broken.py"
# 判定の関数そのものを無効化する（最上位と単純コマンドごとの 2 か所から呼ばれるため・I174）
sed 's/^def _git_revert_target_on_dirty(cmd: str, opaque: bool = False, cds=None):$/&\n    return None/' "$GUARD" > "$BROKEN"
ck "FALSEGREEN 複製に置換が入った" YES "$( (! cmp -s "$GUARD" "$BROKEN") && echo YES || echo NO)"
ck "FALSEGREEN injected passes" 0 "$(json 'git checkout -- g11.txt' | python3 "$BROKEN" >/dev/null 2>&1; echo $?)"
ck "FALSEGREEN real blocks"     2 "$(run 'git checkout -- g11.txt')"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
