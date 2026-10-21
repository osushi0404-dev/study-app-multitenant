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
ck "G21 bash -c cd sub && restore dirty"   ASK "$(runj "bash -c 'cd sub && git restore s.txt'")"
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
ck "G27 restore --pathspec-from-file"      ASK "$(runj 'git restore --pathspec-from-file=list.txt')"
ck "G28 git rm -rf dirty"                  2 "$(run 'git rm -rf sub')"
ck "G29 git rm --cached は通す"            0 "$(run 'git rm --cached -r sub')"
ck "G30 git.exe checkout -- dirty"         2 "$(run 'git.exe checkout -- sub/s.txt')"
ck "G31 bash -c GIT_WORK_TREE=. checkout"  2 "$(run "bash -c 'GIT_WORK_TREE=. git checkout -- sub/s.txt'")"
# 対象をコマンド・変数・xargs で渡す形（どれを戻すか読めない）は、その場所に変更があれば止める（code-review 20261021_0905 第 1 周）
ck "G32 git diff --name-only | xargs git checkout --" ASK "$(runj 'git diff --name-only | xargs git checkout --')"
# shellcheck disable=SC2016  # $(…)・$f・$S を展開せず、そのまま guard に渡すのが目的
ck "G33 git restore \$(git diff --name-only)"      ASK "$(runj 'git restore $(git diff --name-only)')"
# shellcheck disable=SC2016  # $(…)・$f・$S を展開せず、そのまま guard に渡すのが目的
ck "G34 for f in \$(…); do git checkout -- \$f"    ASK "$(runj 'for f in $(git diff --name-only); do git checkout -- $f; done')"
# ( ) の中の cd は抜けると戻る。どちらの場所でも当たれば止める
mkdir -p other
ck "G35 bash -c (cd other && ls) && checkout"      ASK "$(runj "bash -c '(cd other && ls) && git checkout -- sub/s.txt'")"
ck "G36 bash -c pushd; popd; checkout"            ASK "$(runj "bash -c 'pushd other; popd; git checkout -- sub/s.txt'")"
# -- なしのコミットから戻す形もステージ済みの変更を数える
ck "G37 checkout HEAD <staged>（-- なし）"         2 "$(run 'git checkout HEAD st.txt')"
ck "G38 checkout HEAD .（-- なし）"                2 "$(run 'git checkout HEAD .')"
ck "G39 ブランチの切り替えは通す"                  0 "$(run 'git checkout develop')"
ck "G40 bash -c (cd other && ls) && status は通す" 0 "$(run "bash -c '(cd other && ls) && git status'")"
# まとめて書いた -SW / -WS（-s なし）もステージ済みを戻す形（code-review 20261021_0905 第 1 周・テスト観点）
ck "G41 restore -SW <staged>（-s なし）"          2 "$(run 'git restore -SW st.txt')"
ck "G42 restore -WS <staged>（-s なし）"          2 "$(run 'git restore -WS st.txt')"
# 見張りの作業ディレクトリとは別のリポジトリを GIT_DIR / GIT_WORK_TREE で指す形（G31 は同じ場所を指すので測れない）。
# 信頼しない場所（このリポジトリと worktree の外）なので git を実行せず確認（security-review の Blocker）
T2="$(mktemp -d)"
trap 'rm -rf "$TMP" "$T2"' EXIT
git -C "$T2" init -q
git -C "$T2" config user.email t@example.com
git -C "$T2" config user.name tester
printf 'orig\n' > "$T2/s2.txt"
git -C "$T2" add s2.txt
git -C "$T2" commit -qm i
printf 'x\n' >> "$T2/s2.txt"
ck "G43 GIT_DIR=<別> GIT_WORK_TREE=<別> checkout" ASK "$(runj "GIT_DIR=$T2/.git GIT_WORK_TREE=$T2 git checkout -- s2.txt")"
ck "G44 env GIT_DIR=<別> … checkout"             ASK "$(runj "env GIT_DIR=$T2/.git GIT_WORK_TREE=$T2 git checkout -- s2.txt")"
ck "G45 bash -c 'env GIT_DIR=<別> … checkout'"   ASK "$(runj "bash -c 'env GIT_DIR=$T2/.git GIT_WORK_TREE=$T2 git checkout -- s2.txt'")"
# 作業記録の再判定で見つかった余計な停止: まとめ書きの -qb（ブランチ作成）・場所が変数の cd の後
ck "G46 checkout -qb <新ブランチ> は通す"         0 "$(run 'git checkout -qb feat2')"
# shellcheck disable=SC2016  # $(…)・$f・$S を展開せず、そのまま guard に渡すのが目的
ck "G47 cd \$S; git checkout -qb は通す"          0 "$(run 'cd $S; git checkout -qb feat3')"
# 止めすぎの解消（code-review 20261021_0905 第 2 周）: 変数で渡す切り替え先・( ) の無い cd の後の別リポジトリ
# shellcheck disable=SC2016  # $BR 等を展開せず、そのまま guard に渡すのが目的
ck "G48 git checkout \$BR（切り替え）は通す"      0 "$(run 'git checkout $BR')"
# shellcheck disable=SC2016  # 同上
ck "G49 git checkout --detach \$SHA は通す"       0 "$(run 'git checkout --detach $SHA')"
# shellcheck disable=SC2016  # 同上
ck "G50 git checkout \$(git diff --name-only)"    ASK "$(runj 'git checkout $(git diff --name-only)')"
C2="$T2"   # 変更のある sub/s.txt を持たない別のリポジトリ（s2.txt だけ）
mkdir -p "$C2/sub"
printf 'orig\n' > "$C2/sub/s.txt"
git -C "$C2" add sub/s.txt
git -C "$C2" commit -qm c2
ck "G51 cd <別> && checkout -- sub/s.txt は通す"  0 "$(run "cd $C2 && git checkout -- sub/s.txt")"
ck "G52 (cd <別> && ls) && checkout -- は止める"  ASK "$(runj "(cd $C2 && ls) && git checkout -- sub/s.txt")"
# 未コミットの変更を消す別のコマンド（第 2 周 Low）
ck "G53 git checkout-index -f <dirty>"           2 "$(run 'git checkout-index -f sub/s.txt')"
ck "G54 git read-tree -u --reset HEAD"           2 "$(run 'git read-tree -u --reset HEAD')"
ck "G55 git mv -f <x> <dirty>"                   2 "$(run 'git mv -f tracked.txt sub/s.txt')"
ck "G56 git checkout-index -a（-f なし）は通す"   0 "$(run 'git checkout-index -a')"
# find -exec で渡す形・中かっこで並べたファイル名（第 2 周）
ck "G57 find -exec git checkout -- {} +"         ASK "$(runj 'find sub -name s.txt -exec git checkout -- {} +')"
ck "G58 git checkout -- sub/{s,t}.txt"           ASK "$(runj 'git checkout -- sub/{s,t}.txt')"
ck "G59 find -exec git log -- {} + は通す"       0 "$(run 'find sub -name s.txt -exec git log -1 -- {} +')"
# 読めないが今の場所を指す cd は元の場所も見る／別の場所へ移る cd は移った先だけ
# shellcheck disable=SC2016  # $( ) を展開せず、そのまま guard に渡すのが目的
ck "G60 cd \$(git rev-parse --show-toplevel) && checkout" ASK "$(runj "sh -c 'cd \$(git rev-parse --show-toplevel) && git checkout -- sub/s.txt'")"
# shellcheck disable=SC2016  # 同上
ck "G61 cd \$(mktemp -d) && … checkout -- . は通す" 0 "$(run 'cd $(mktemp -d) && git init -q && git checkout -- .')"
# 新しいブランチ名が変数のまとめ書き（-qb）は作成で、変更のある作業場所でも止めない（第 2 周 テスト観点）
# shellcheck disable=SC2016  # $BR を展開せず、そのまま guard に渡すのが目的
ck "G62 git checkout -qb \$BR は通す"             0 "$(run 'git checkout -qb $BR')"
# 場所が 1 つに決まらない（元へ戻る cd・失敗する cd・読めない cd の先・パイプの中の cd）は確認（I174 0-15・第 3 周 H1・H3）
# shellcheck disable=SC2016  # $OLDPWD・$X・$( ) を展開せず、そのまま guard に渡すのが目的
ck "G63 cd sub; cd - ; checkout -- dirty"          ASK "$(runj 'cd sub; ls; cd -; git checkout -- sub/s.txt')"
# shellcheck disable=SC2016  # 同上
ck "G64 cd sub; cd \$OLDPWD; restore dirty"       ASK "$(runj 'cd sub; cd $OLDPWD; git restore sub/s.txt')"
ck "G65 cd sub; cd ~-; checkout -- dirty"          ASK "$(runj 'cd sub; cd ~-; git checkout -- sub/s.txt')"
ck "G66 cd <無い場所>; checkout -- dirty"          ASK "$(runj 'cd nosuchdir; git checkout -- sub/s.txt')"
# shellcheck disable=SC2016  # 同上
ck "G67 cd \$X && checkout -- dirty"               ASK "$(runj 'cd $X && git checkout -- sub/s.txt')"
# shellcheck disable=SC2016  # 同上
ck "G68 cd \$(git rev-parse …)/sub && checkout"    ASK "$(runj 'cd $(git rev-parse --show-toplevel)/sub && git checkout -- s.txt')"
ck "G69 cd sub | true; checkout -- dirty"          ASK "$(runj 'cd sub | true; git checkout -- sub/s.txt')"
# 対象が読めない checkout（-- なしでも）は変更があれば確認（第 3 周 H2）
# shellcheck disable=SC2016  # 同上
ck "G70 git checkout \$(git rev-parse --show-toplevel)" ASK "$(runj 'git checkout $(git rev-parse --show-toplevel)')"
# shellcheck disable=SC2016  # 同上
ck "G71 git checkout \$(git grep -l x)"            ASK "$(runj 'git checkout $(git grep -l x)')"
# 一意な場所・読める対象は今までどおり精密に（第 3 周 H4・L6・L7）
ck "G72 git checkout-index -f -a"                  2 "$(run 'git checkout-index -f -a')"
ck "G73 git checkout-index -fa"                    2 "$(run 'git checkout-index -fa')"
ck "G74 git read-tree -u -m HEAD は通す"           0 "$(run 'git read-tree -u -m HEAD')"
printf 'o\n' > other/o.txt
git add other/o.txt
git commit -qm o
ck "G75 git mv -f <x> <関係ない変更のあるディレクトリ>/ は通す" 0 "$(run 'git mv -f other/o.txt sub/')"
# 安全網だけが拾う書き方（function の本体・coproc・<( ) の中）でも、対象が読めない取り消しは確認（実装レビューの指摘）
# shellcheck disable=SC2016  # $1・$F を展開せず、そのまま guard に渡すのが目的
ck "G76 function の本体の checkout -- \"\$1\""   ASK "$(runj 'function f { git checkout -- $1; }; f sub/s.txt')"
# shellcheck disable=SC2016  # 同上
ck "G77 coproc の中の restore -- \$F"           ASK "$(runj 'coproc { git restore -- $F; }')"
# shellcheck disable=SC2016  # 同上
ck "G78 <( ) の中の checkout -- \$F"            ASK "$(runj 'cat <(git checkout -- $F)')"
# 場所が読めない -C・--work-tree も確認（cd ではない書き方）
# shellcheck disable=SC2016  # 同上
ck "G79 git -C \$X restore <file>"              ASK "$(runj 'git -C $X restore sub/s.txt')"
# shellcheck disable=SC2016  # 同上
ck "G80 git --work-tree=\$X checkout -- <file>" ASK "$(runj 'git --work-tree=$X checkout -- sub/s.txt')"
# 見張りが判定のために実行する git で、コマンドや外部リポジトリの設定によるコマンド実行が起きない（security-review の Blocker）
PW="$TMP/PWNED"
# 仕込みは 2 種類: core.fsmonitor（見張りの打ち消しで防げる）と clean フィルタ（同じ大きさの変更で status が中身を
# 読むときに動く。打ち消しでは防げず、信頼する場所に限ることで防ぐ）
mkevil() { mkdir -p "$1"; git -C "$1" init -q; printf 'x\n' > "$1/g"
           git -C "$1" add g; git -C "$1" -c user.email=t@e -c user.name=t commit -qm i
           git -C "$1" config core.fsmonitor "touch $PW"
           printf '* filter=pw\n' > "$1/.git/info/attributes"
           git -C "$1" config filter.pw.clean "sh -c 'touch $PW; cat'"
           printf 'z\n' > "$1/g"; touch -d '2001-01-01' "$1/g"; }
EV="$(mktemp -d)"
trap 'rm -rf "$TMP" "$T2" "$EV"' EXIT
mkevil "$EV/evil"
mkevil "$TMP/nested"
mkdir -p "$TMP/fakegit"
cp -r "$TMP/.git/." "$TMP/fakegit/"
git --git-dir="$TMP/fakegit" config core.fsmonitor "touch $PW"
pw() { rm -f "$PW"; local r; r="$(runj "$1")"; [ -e "$PW" ] && echo "PWNED:$r" || echo "$r"; }
ck "G81 -c core.fsmonitor=… checkout（実行しない）"  2   "$(pw "git -c core.fsmonitor='touch $PW' checkout -- sub/s.txt")"
ck "G82 cd <外のリポジトリ> && checkout（実行しない）" ASK "$(pw "cd $EV/evil && git checkout -- g")"
ck "G83 git -C <外のリポジトリ> checkout"            ASK "$(pw "git -C $EV/evil checkout -- g")"
ck "G84 cd <入れ子のリポジトリ> && checkout"         ASK "$(pw 'cd nested && git checkout -- g')"
ck "G85 --git-dir=<中に作った偽の git-dir>"          ASK "$(pw 'git --git-dir=fakegit --work-tree=. checkout -- sub/s.txt')"
ck "G86 GIT_DIR=<中に作った偽の git-dir>"            ASK "$(pw 'GIT_DIR=fakegit git checkout -- sub/s.txt')"
ck "G87 cd <外のリポジトリ> && git push"             ASK "$(pw "cd $EV/evil && git push")"
# 条件付きの cd（実行されないまま後ろが動きうる）は場所が 1 つに決まらない → 確認（code-review 20261021_1509 第 1 周）
ck "G88 false && cd other; checkout -- dirty"      ASK "$(runj 'false && cd other; git checkout -- sub/s.txt')"
ck "G89 true || cd other; checkout -- dirty"       ASK "$(runj 'true || cd other; git checkout -- sub/s.txt')"
ck "G90 cd other || true; checkout -- dirty"       ASK "$(runj 'cd other || true; git checkout -- ../sub/s.txt')"
ck "G91 cd sub || exit 1; checkout は精密（停止）"  2 "$(run 'cd sub || exit 1; git checkout -- s.txt')"
ck "G92 git status && cd sub && checkout は精密"   2 "$(run 'git status && cd sub && git checkout -- s.txt')"
ck "G94 cd sub && git --git-dir=<.git> checkout"  ASK "$(runj "cd sub && git --git-dir=$TMP/.git checkout -- s.txt")"
ck "G95 git --git-dir=<.git> checkout（最上位）"  2 "$(run "git --git-dir=$TMP/.git checkout -- sub/s.txt")"
# --work-tree だけが食い違う形（別の場所の変更は読めないので確認）
ck "G96 --work-tree=<別の場所> checkout"         ASK "$(runj "git --work-tree=$T2 checkout -- s2.txt")"
# `-` という名前のディレクトリがあっても cd - は元の場所へ戻る（名前の有無ではなく cd - を見分ける）
mkdir -p "sub/-"
ck "G97 cd sub; cd -（sub/- がある）; checkout" ASK "$(runj 'cd sub; cd -; git checkout -- sub/s.txt')"
rmdir "sub/-"
# 見張りの無害化（信頼するリポジトリの設定の core.fsmonitor）と、見張りの環境の GIT_ 変数を使わないこと（テスト観点）
git config core.fsmonitor "touch $PW"
rm -f "$PW"
ck "G98 信頼するリポジトリの core.fsmonitor も打ち消す" "2:no" "$(run 'git checkout -- sub/s.txt'):$([ -e "$PW" ] && echo PWNED || echo no)"
git config --unset core.fsmonitor
ck "G99 見張りの環境の GIT_INDEX_FILE を使わない"  2 "$(json 'git checkout -- sub/s.txt' | GIT_INDEX_FILE="$TMP/noidx" python3 "$GUARD" >/dev/null 2>&1; echo $?)"
# 信頼する場所の起点はプロジェクト（CLAUDE_PROJECT_DIR）。Bash の作業ディレクトリが入れ子のリポジトリでも信頼しない
rm -f "$PW"
r="$(cd "$TMP/nested" && json 'git checkout -- g' | CLAUDE_PROJECT_DIR="$TMP" python3 "$GUARD" 2>/dev/null; echo "rc=$?")"
ck "G93 作業ディレクトリが入れ子のリポジトリ（実行しない）" "ask:no" "$(printf '%s' "$r" | grep -q '"ask"' && echo ask || echo noask):$([ -e "$PW" ] && echo PWNED || echo no)"
# 偽合格の防止: 信頼する場所の判定を外すと、外のリポジトリの設定で判定中にコマンドが実行される
BROKEN_TRUST="$TMP/guard_notrust.py"
sed 's/^    for root, rgd in _trusted_repos():$/    return (cur, cur, gd or os.path.join(cur, ".git"))\n&/' "$GUARD" > "$BROKEN_TRUST"
ck "FG-TRUST 複製に置換が入った" YES "$( (! cmp -s "$GUARD" "$BROKEN_TRUST") && echo YES || echo NO)"
rm -f "$PW"
json "cd $EV/evil && git checkout -- g" | python3 "$BROKEN_TRUST" >/dev/null 2>&1
ck "FG-TRUST notrust は判定中に実行してしまう" YES "$([ -e "$PW" ] && echo YES || echo NO)"
# 偽合格の防止: 場所が一意かの判定（_loc_ambiguous）を外すと、cd - の後の checkout が素通しになる
BROKEN_AMB="$TMP/guard_noamb.py"
sed 's/^def _loc_ambiguous(text: str, cmds=None) -> bool:$/&\n    return False/' "$GUARD" > "$BROKEN_AMB"
ck "FG-AMB 複製に置換が入った" YES "$( (! cmp -s "$GUARD" "$BROKEN_AMB") && echo YES || echo NO)"
ck "FG-AMB noamb passes cd - checkout" 0 "$(json 'cd sub; ls; cd -; git checkout -- sub/s.txt' | python3 "$BROKEN_AMB" >/dev/null 2>&1; echo $?)"

# --- FALSEGREEN（自動注入）: 判定呼び出し行を無効化した複製で dirty が素通し /
#     実体で block。両者の差で「block は判定行に依存」を機械裏取り（false-green 排除） ---
BROKEN="$TMP/guard_broken.py"
# 判定の関数そのものを無効化する（最上位と単純コマンドごとの 2 か所から呼ばれるため・I174）。
# 場所・対象が 1 つに決まらない形は確認（ASK）にする（I174 0-15。G21 ほか ASK の行）
sed 's/^def _git_revert_check(cmd: str, opaque: bool = False, ambiguous: bool = False):$/&\n    return None/' "$GUARD" > "$BROKEN"
ck "FALSEGREEN 複製に置換が入った" YES "$( (! cmp -s "$GUARD" "$BROKEN") && echo YES || echo NO)"
ck "FALSEGREEN injected passes" 0 "$(json 'git checkout -- g11.txt' | python3 "$BROKEN" >/dev/null 2>&1; echo $?)"
ck "FALSEGREEN real blocks"     2 "$(run 'git checkout -- g11.txt')"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
