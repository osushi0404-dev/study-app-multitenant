#!/usr/bin/env bash
# I080: pretooluse_guard.py の push ポリシーを決定論検証する。
# 実行: bash scripts/claude/tests/test_pretooluse_push_guard.sh
#
# temp git repo（develop / feature/x ブランチ）を立て、フックへ stdin JSON を投入して
# exit code を検証する（実 push はしない＝フックの判定のみを見る）。
# 検証範囲: protected 宛先 push（danger-op）・--all/--mirror・--repo evasion・DANGER_OK escape・
#           FP 解消・安全 push 素通し・false-green 注入（判定行ごと）。
# shellcheck disable=SC2016
# 本テストは動的 push 形（$(...)/$VAR/${...}/バッククォート）を**展開させず**リテラルで
# フックへ渡すのが目的。単一引用符内の非展開は意図的なので SC2016 を全体抑制する。
set -uo pipefail
# 見張りの「信頼する場所」の起点（I174 0-16）。外から渡された値で一時リポジトリが信頼されなくならないよう消す
unset CLAUDE_PROJECT_DIR
REPO_ROOT="$(git rev-parse --show-toplevel)"
GUARD="$REPO_ROOT/scripts/claude/hooks/pretooluse_guard.py"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cd "$TMP" || exit 1
git init -q -b feature/x
git config user.email t@example.com
git config user.name tester
printf 'x\n' > a.txt
git add a.txt
git commit -qm init
git branch develop

# JSON は python で組み立てる（コマンドに " や ` が含まれても安全にエスケープする・I083）。
json() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$1"; }
run()  { json "$1" | python3 "$GUARD" >/dev/null 2>&1; echo $?; }
rung() { json "$2" | python3 "$1" >/dev/null 2>&1; echo $?; }   # $1=guard, $2=command
# ask 判別版（I083）: exit 0 ＋ stdout に permissionDecision=ask を含めば ASK、それ以外は exit code。
# out=$(...) 直後の code=$? がパイプ末尾(python)の exit を捕捉する（pipefail 不要）。
runj()  { local out code; out=$(json "$1" | python3 "$GUARD" 2>/dev/null); code=$?;
          if [ "$code" = "0" ] && printf '%s' "$out" | grep -q '"permissionDecision":[[:space:]]*"ask"'; \
          then echo "ASK"; else echo "$code"; fi; }
rungj() { local out code; out=$(json "$2" | python3 "$1" 2>/dev/null); code=$?;
          if [ "$code" = "0" ] && printf '%s' "$out" | grep -q '"permissionDecision":[[:space:]]*"ask"'; \
          then echo "ASK"; else echo "$code"; fi; }   # $1=guard, $2=command

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }

# ===== develop ブランチ context =====
git checkout -q develop
ck "P1 bare push (develop)"            2 "$(run 'git push')"
ck "P2 push origin (develop)"          2 "$(run 'git push origin')"
ck "P3 push -u origin (develop)"       2 "$(run 'git push -u origin')"
ck "P4 push origin develop"            2 "$(run 'git push origin develop')"
ck "P5 push origin feature (safe dst)" 0 "$(run 'git push origin feature')"
ck "P6 DANGER_OK push origin develop"  ASK "$(runj 'DANGER_OK=1 git push origin develop')"
ck "P7 DANGER_OK bare push"            ASK "$(runj 'DANGER_OK=1 git push')"

# ===== feature/x ブランチ context =====
git checkout -q feature/x
ck "P8 bare push (feature)"            0 "$(run 'git push')"
ck "P9 push origin (feature)"          0 "$(run 'git push origin')"
ck "P10 push -u origin feature"        0 "$(run 'git push -u origin feature')"
ck "P11 push origin develop"           2 "$(run 'git push origin develop')"
ck "P12 push origin main"              2 "$(run 'git push origin main')"
ck "P13 refspec feat:main"             2 "$(run 'git push origin feat:main')"
ck "P14 refspec HEAD:develop"          2 "$(run 'git push origin HEAD:develop')"
ck "P15 force-shorthand +develop"      2 "$(run 'git push origin +develop')"
ck "P16 refs/heads/develop"            2 "$(run 'git push origin refs/heads/develop')"
ck "P17 HEAD:refs/heads/main"          2 "$(run 'git push origin HEAD:refs/heads/main')"
ck "P18 FP develop-fix (safe)"         0 "$(run 'git push origin develop-fix')"
ck "P19 FP main-backup (safe)"         0 "$(run 'git push origin main-backup')"
ck "P20 refspec feat:feat (safe)"      0 "$(run 'git push origin feat:feat')"
ck "P21 --all"                         2 "$(run 'git push --all')"
ck "P22 --mirror"                      2 "$(run 'git push --mirror')"
ck "P23 DANGER_OK origin develop"      ASK "$(runj 'DANGER_OK=1 git push origin develop')"
ck "P24 DANGER_OK --all"               ASK "$(runj 'DANGER_OK=1 git push --all')"
ck "P25 --force origin feature"        2 "$(run 'git push --force origin feature')"
ck "P26 DANGER_OK --force feature"     ASK "$(runj 'DANGER_OK=1 git push --force origin feature')"
ck "P27 git -C push origin develop"    2 "$(run 'git -C /tmp push origin develop')"
ck "P28 --repo= develop:main"          2 "$(run 'git push --repo=origin develop:main')"
ck "P29 --repo= +develop"              2 "$(run 'git push --repo=origin +develop')"
ck "P30 --repo (space) develop:main"   2 "$(run 'git push --repo origin develop:main')"
ck "P31 DANGER_OK --repo= develop:main" ASK "$(runj 'DANGER_OK=1 git push --repo=origin develop:main')"
ck "P32 --repo= feature (flag-block)"  2 "$(run 'git push --repo=origin feature')"
ck "P33 dst-side + (feat:+refs/heads/main)" 2 "$(run 'git push origin feat:+refs/heads/main')"

# ===== 回帰（既存ハードブロック維持） =====
ck "Pregr1 force push exit2"           2 "$(run 'git push --force origin x')"

# ===== false-green 注入（判定行ごと独立に裏取り） =====
# protected 判定行を無効化（dest を常に None 化）
BROKEN_PROT="$TMP/guard_noprot.py"
sed -e 's/dest = _push_protected_target(cmd, amb)/dest = None/' -e 's/dest = _push_protected_target(seg, amb)/dest = None/' "$GUARD" > "$BROKEN_PROT"
ck "FG-A noprot passes develop"        0 "$(rung "$BROKEN_PROT" 'git push origin develop')"
ck "FG-B real blocks develop"          2 "$(run 'git push origin develop')"
# --all/--mirror 判定行を無効化（regex を非マッチ化）
BROKEN_ALL="$TMP/guard_noall.py"
sed 's/(--all|--mirror)/(--xxall|--xxmirror)/' "$GUARD" > "$BROKEN_ALL"
ck "FG-C noall passes --all"           0 "$(rung "$BROKEN_ALL" 'git push --all')"
ck "FG-D real blocks --all"            2 "$(run 'git push --all')"
# --repo 判定行を無効化（regex を非マッチ化）
BROKEN_REPO="$TMP/guard_norepo.py"
sed 's/--repo(/--xxrepo(/' "$GUARD" > "$BROKEN_REPO"
ck "FG-E norepo passes --repo="        0 "$(rung "$BROKEN_REPO" 'git push --repo=origin develop:main')"
ck "FG-F real blocks --repo="          2 "$(run 'git push --repo=origin develop:main')"

# ===================== I083: 動的宛先 ask / force 取りこぼし =====================
# ----- develop context: 動的・不透明な宛先 → ask（exit0＋ask JSON） -----
git checkout -q develop
ck "D1 cmdsubst \$(echo develop)"      ASK "$(runj 'git push origin $(echo develop)')"
ck "D2 cmdsubst rev-parse"             ASK "$(runj 'git push origin $(git rev-parse --abbrev-ref HEAD)')"
ck "D3 var expansion \$D"              ASK "$(runj 'D=develop; git push origin $D')"
ck "D4 alias indirection"              ASK "$(runj 'git -c alias.p="push origin develop" p')"
# I174 0-13: eval / sh -c の中の push は中身を読んで単純コマンドごとに判定するので、直接書いたときと同じく停止（以前は「宛先を確定できない」として確認）
ck "D5 eval wrapper"                   2 "$(runj 'eval "git push origin develop"')"
ck "D6 sh -c wrapper"                  2 "$(runj 'sh -c "git push origin develop"')"
ck "D8 brace \${BR}"                   ASK "$(runj 'git push origin ${BR}')"
ck "D10 backtick substitution"         ASK "$(runj 'git push origin x`whoami`y')"
ck "DOK1 DANGER_OK dynamic escape"     ASK "$(runj 'DANGER_OK=1 git push origin $(echo develop)')"

# ----- feature/x context -----
git checkout -q feature/x
ck "D7 dynamic feature (not exit2)"    ASK "$(runj 'git push origin $(git rev-parse --abbrev-ref HEAD)')"
ck "D9 dynamic + rm-rf (block wins)"   2   "$(run 'git push origin $VAR && rm -rf x')"
# I174（0-13 後の敵対的レビュー）: xargs / parallel で包んだ push は宛先が後から足される（feature 上でも main に push しうる）ので確認
ck "XP5 + を付けた宛先の force push"   2   "$(runj 'git push origin +feature/x')"
ck "XP6 +HEAD:x の force push"         2   "$(runj 'git push origin +HEAD:feature/x')"
ck "XP7 + の無い普通の push は通す"     0   "$(runj 'git push origin feature/x')"
ck "XP1 xargs で宛先を足す push"       ASK "$(runj "git branch --format='%(refname:short)' | xargs -n1 git push origin")"
ck "XP2 echo main | xargs git push"    ASK "$(runj 'echo main | xargs git push origin')"
ck "XP3 parallel の push（宛先が見える）" 2 "$(runj 'parallel git push origin ::: main develop')"
ck "XP4 parallel の push（宛先が見えない）" ASK "$(runj 'git branch | parallel git push origin')"
# 敵対的レビュー（20261020_2001 の後の第 2 周）: xargs の包み方・別の場所のブランチ・git の呼び方・宛先の書き方
ck "XP8 xargs -I{} sh -c の push"        ASK "$(runj "git branch | xargs -I{} sh -c 'git push origin {}'")"
ck "XP9 timeout で包んだ xargs の push"  ASK "$(runj 'git branch | timeout 60 xargs -n1 git push origin')"
git worktree add -q "$TMP/devwt" develop
W="$TMP/devwt"
ck "XP10 git -C <develop の場所> push"    2   "$(runj "git -C $W push")"
ck "XP11 git -C <develop の場所> push -u origin HEAD" 2 "$(runj "git -C $W push -u origin HEAD")"
ck "XP12 cd <develop の場所> && git push" 2   "$(runj "cd $W && git push")"
ck "XP13 bash -c 'cd <develop の場所> && git push'" 2   "$(runj "bash -c 'cd $W && git push'")"
ck "XP14 -o の値を remote と読み違えない" 2   "$(runj "cd $W && git push -o ci.skip origin")"
ck "XP15 @ は今のブランチ"               2   "$(runj "cd $W && git push origin @")"
ck "XP16 git -C の先が読めない push"      ASK "$(runj 'git -C "$WT" push')"
# ( ) が無ければ cd は順に効くので、最後の場所（feature/x）で判定する。( ) があるときは通った場所すべて（XP60）
ck "XP17 cd で戻った先の push は通す"     0   "$(runj "cd $W && cd .. && git push")"
ck "XP18 git -C <develop の場所> status は通す" 0 "$(runj "git -C $W status")"
ck "XP19 絶対パスの git で main へ push"   2   "$(runj '/usr/bin/git push origin main')"
ck "XP20 git.exe の force push"          2   "$(runj 'git.exe push --force origin feature/x')"
ck "XP21 glob の refspec（refs/heads/*）" 2   "$(runj "git push origin 'refs/heads/*:refs/heads/*'")"
ck "XP22 tag の glob は通す"             0   "$(runj "git push origin 'refs/tags/*'")"
ck "XP23 -o 付きの普通の push は通す"     0   "$(runj 'git push -o ci.skip origin feature/x')"
ck "XP24 parallel '…push origin {}' ::: main" ASK "$(runj "parallel 'git push origin {}' ::: main develop")"
ck "XP25 xargs sh -c '…push origin \"\$@\"'"  ASK "$(runj "xargs sh -c 'git push origin \"\$@\"' _ < b")"
ck "XP26 push.default=matching"            2   "$(runj 'git -c push.default=matching push')"
ck "XP27 --prune と glob の refspec"        2   "$(runj "git push --prune origin 'refs/heads/*:refs/heads/*'")"
# 第 3 周: 入れ子の中の宛先の読めない push（H2）・場所の書き方（M4）・push の設定（M8）・誤確認（M6）
ck "XP28 bash -lc の \$() 宛先 push"        ASK "$(runj "bash -lc 'git push -u origin \$(git branch --show-current)'")"
ck "XP29 timeout bash -lc の \$() 宛先"     ASK "$(runj "timeout 60 bash -lc 'git push origin \$(git branch --show-current)'")"
ck "XP30 ヒアドキュメントの \$() 宛先"      ASK "$(runj "$(printf "bash <<'EOF'\nset -e\ngit push -u origin \"\$(git branch --show-current)\"\nEOF")")"
ck "XP31 cd -- <develop> && git push"     2   "$(runj "cd -- $W && git push origin")"
ck "XP32 cd -P <develop> && git push"     2     "$(runj "cd -P $W && git push origin")"
ck "XP33 --git-dir/--work-tree <develop>" 2   "$(runj "git --git-dir=$W/.git --work-tree=$W push origin")"
ck "XP34 GIT_DIR=<develop の worktree>"   2   "$(runj 'GIT_DIR=.git/worktrees/devwt git push origin')"
ck "XP35 pushd <develop> && git push"     2     "$(runj "pushd $W && git push")"
ck "XP36 -c remote.origin.push=HEAD:main" 2   "$(runj 'git -c remote.origin.push=HEAD:main push origin')"
ck "XP37 git config remote.origin.push"   2   "$(runj 'git config remote.origin.push HEAD:main')"
ck "XP38 git config push.default matching" 2  "$(runj 'git config push.default matching')"
ck "XP39 git config user.name は通す"      0   "$(runj 'git config user.name x')"
ck "XP40 xargs grep \"git push\" は通す"   0   "$(runj 'git diff --name-only | xargs grep -n "git push"')"
ck "XP41 bash -c grep \"git push\" は通す" 0   "$(runj "bash -c 'grep -rn \"git push\" docs'")"
ck "XP42 bash -c の普通の push は通す"     0   "$(runj "bash -c 'git push -u origin feature/x'")"
ck "XP43 cd ~（HOME が develop）&& git push" 2   "$(HOME="$W" runj 'cd ~ && git push')"
ck "XP44 cd（引数なし＝HOME）&& git push"    2   "$(HOME="$W" runj 'cd && git push')"
# 入れ子の中の前置き GIT_DIR=・実行場所が変数の push（fix-loop テストレビューの指摘）
ck "XP45 bash -c 'GIT_DIR=<develop> git push'" 2  "$(runj "bash -c 'GIT_DIR=.git/worktrees/devwt git push origin'")"
ck "XP46 env GIT_DIR=<develop> git push"      2   "$(runj 'env GIT_DIR=.git/worktrees/devwt git push origin')"
ck "XP47 GIT_DIR=<develop> bash -c 'git push'" 2  "$(runj "GIT_DIR=.git/worktrees/devwt bash -c 'git push origin'")"
ck "XP48 GIT_DIR=\$X git push（場所が変数）"  ASK "$(runj 'GIT_DIR=$X git push origin')"
ck "XP49 bash -c 'GIT_DIR=\$X git push'"      ASK "$(runj "bash -c 'GIT_DIR=\$X git push origin'")"
ck "XP50 bash -c 'cd \"\$D\" && git push'"    ASK "$(runj "bash -c 'cd \"\$D\" && git push'")"
ck "XP51 bash -c 'git -C \"\$D\" push'"       ASK "$(runj "bash -c 'git -C \"\$D\" push'")"
# 余計な確認・停止の回帰を防ぐ（普段の読み取り）
ck "XP52 git config --get push.default は通す" 0  "$(runj 'git config --get push.default')"
ck "XP53 git branch | xargs -n1 echo は通す"  0   "$(runj 'git branch | xargs -n1 echo')"
ck "XP54 cd <develop> && git status は通す"   0   "$(runj "cd $W && git status")"
# 強制 push になる設定・安全な push の設定（code-review 20261021_0905 第 1 周）
ck "XP55 -c remote.origin.mirror=true push"   2   "$(runj 'git -c remote.origin.mirror=true push origin')"
ck "XP56 git config remote.origin.mirror true" 2  "$(runj 'git config remote.origin.mirror true')"
ck "XP57 git config push.default simple は通す" 0 "$(runj 'git config push.default simple')"
ck "XP58 remote.origin.push を feature に は通す" 0 "$(runj 'git config remote.origin.push refs/heads/feature/x:refs/heads/feature/x')"
ck "XP59 -c push.default=simple push は通す"  0   "$(runj 'git -c push.default=simple push -u origin feature/x')"
ck "XP60 bash -c (cd <develop> && ls) && git push" 2   "$(runj "bash -c '(cd $W && ls) && git push origin'")"
# code-review 20261021_0905 第 2 周: 上流へ push する設定・: の push・値を省いた設定・git config -f
ck "XP61 -c push.default=upstream push"     2   "$(runj 'git -c push.default=upstream push')"
ck "XP62 git config push.default upstream"  2   "$(runj 'git config push.default upstream')"
ck "XP63 -c push.default=tracking push"     2   "$(runj 'git -c push.default=tracking push origin')"
ck "XP64 git push origin :（同名すべて）"    2   "$(runj 'git push origin :')"
ck "XP65 -c remote.origin.push=: push"      2   "$(runj 'git -c remote.origin.push=: push origin')"
ck "XP66 -c remote.origin.mirror（値なし）"  2   "$(runj 'git -c remote.origin.mirror push origin')"
ck "XP67 git config -f … remote.origin.push HEAD:develop" 2 "$(runj 'git config -f .git/config remote.origin.push HEAD:develop')"
ck "XP68 git config -f … user.name は通す"   0   "$(runj 'git config -f .git/config user.name x')"
ck "XP69 git config remote.origin.push +<feature>（強制）" 2 "$(runj 'git config remote.origin.push +refs/heads/feature/x:refs/heads/feature/x')"
ck "XP70 -c remote.origin.push=+HEAD:feature/x push"  2 "$(runj 'git -c remote.origin.push=+HEAD:feature/x push origin')"
ck "XP71 git config remote.origin.mirror yes"        2 "$(runj 'git config remote.origin.mirror yes')"
# 場所が 1 つに決まらない、今のブランチで宛先が決まる push は確認（I174 0-15・第 3 周 H1）
ck "XP72 cd <develop> && cd - && git push"     ASK "$(runj "cd $W && git status && cd - && git push origin HEAD")"
ck "XP73 cd <無い場所>; git push origin HEAD"   ASK "$(runj 'cd nosuch; git push origin HEAD')"
ck "XP74 一意な cd <develop> && git push は停止" 2 "$(runj "cd $W && git push origin")"
ck "XP75 cd - の後でも宛先を書いた push は通す" 0   "$(runj "cd $W && cd - && git push origin feature/x")"
ck "XP76 [ -d … ] || cd <develop>; git push"    2   "$(runj "[ -d nosuch ] || cd $W; git push origin HEAD")"
ck "XP77 false && cd <develop>; git push"      2   "$(runj "false && cd $W; git push")"
# 場所が 1 つに決まらなくても、書かれたとおりの場所で保護ブランチなら止める（停止を確認に格下げしない・
# code-review 20261021_1559 第 1 周）。XP13・XP32・XP35・XP43・XP44・XP60・XP76・XP77 は 2
ck "XP83 cd <develop>⏎git push（改行の cd・ありそうな場所で当たる）" 2 "$(runj "$(printf 'cd %s\ngit push' "$W")")"
ck "XP84 cd <develop> && git push origin HEAD || true" 2 "$(runj "cd $W && git push origin HEAD || true")"
ck "XP85 cd <feature> && git push 2>&1 | tail -5 は通す" 0 "$(runj "cd $TMP && git push 2>&1 | tail -5")"
ck "XP87 sudo -D <develop> git push（-D の値を読み違えない）" ASK "$(runj "sudo -D $W git push")"
ck "XP88 env -C <develop> git push"            ASK "$(runj "env -C $W git push -u origin HEAD")"
ck "XP89 export GIT_DIR=<develop>; git push"   ASK "$(runj 'export GIT_DIR=.git/worktrees/devwt; git push')"
ck "XP90 sudo -D <develop> git push origin main は停止" 2 "$(runj "sudo -D $W git push origin main")"
ck "XP86 cd && commit -m \"\$(cat <<'EOF' …)\" && push は通す" 0 "$(runj "$(printf 'cd %s && git commit -m "$(cat <<%sEOF%s\nfix: x\n\nbody\nEOF\n)" && git push -u origin feature/x' "$TMP" "'" "'")")"
# push の宛先（今のブランチ）は git-dir の HEAD で決まり、作業ディレクトリに依らない（主の .git は feature/x）
ck "XP78 cd <develop の worktree> && git --git-dir=<主の .git> push は通す" 0 "$(runj "cd $W && git --git-dir=$TMP/.git push")"
# 引用符の中（コミットメッセージ）の ( や eval は場所の範囲に関係しない（第 2 周 要件観点）
ck "XP79 cd && commit -m \"fix(I1): eval\" && push は通す" 0 "$(runj "cd $TMP && git commit -m \"fix(I1): eval の説明\" && git push -u origin feature/x")"
ck "XP80 cd && commit -m \"fix(I1): eval\" && 宛先なし push は通す" 0 "$(runj "cd $TMP && git commit -m \"fix(I1): eval の説明\" && git push")"
ck "XP81 cd && commit -m '…' && 宛先なし push は通す（安全網の組み立て直し）" 0 "$(runj "cd $TMP && git commit -m 'fix x' && git push")"
ck "XP82 cd <feature の場所>; git push（cd が失敗しうる・当たらない）は確認" ASK "$(runj "cd $TMP; git push")"
# 偽合格の防止: 実行場所が変数かの判定（_git_loc_dynamic）を外すと、変数の場所の push が素通しになる
BROKEN_LOC="$TMP/guard_noloc.py"
# 信頼する場所の判定（_git_loc_trusted・security-review の Blocker）も同じ形を確認にするので、両方を外す
sed -e 's/^def _git_loc_dynamic(loc) -> bool:$/&\n    return False/' \
    -e 's/^def _git_loc_trusted(loc, need_worktree: bool = True) -> bool:$/&\n    return True/' "$GUARD" > "$BROKEN_LOC"
ck "FG-M 複製に置換が入った"                 YES "$( (! cmp -s "$GUARD" "$BROKEN_LOC") && echo YES || echo NO)"
ck "FG-M noloc passes GIT_DIR=\$X push"      0   "$(rungj "$BROKEN_LOC" 'GIT_DIR=$X git push origin')"
# force 取りこぼし → block
ck "F1 -f short"                       2   "$(run 'git push -f origin x')"
ck "F2 -uf combined"                   2   "$(run 'git push -uf origin x')"
ck "F3 --force-with-lease"             2   "$(run 'git push --force-with-lease origin x')"
ck "F4 --force-if-includes"            2   "$(run 'git push --force-if-includes origin x')"
ck "F5 compound && --force"            2   "$(run 'cd foo && git push --force origin x')"
ck "F6 compound ; --force"             2   "$(run 'true; git push --force origin x')"
# force 誤 block 回帰 → pass（runj=0・ask でも block でもない）
ck "FP1 push;echo --force"             0   "$(runj 'git push origin feature; echo "use --force later"')"
ck "FP2 push&&echo --force"            0   "$(runj 'git push origin feature && echo "--force"')"
ck "FP3 --push-option=force"           0   "$(runj 'git push --push-option=force origin x')"
ck "FP4 rm -f && push"                 0   "$(runj 'rm -f x && git push origin feature')"
# ラッパー隠蔽 force → ask（block しない・Q7）
ck "F7 eval hidden force"              2 "$(runj 'eval "git push --force origin x"')"
# ラッパー誤 ask 回帰（構造的検出・branch/remote 名の偶然一致で発火しない・Q8）→ pass
ck "W1 branch bash-feature"            0   "$(runj 'git push origin bash-feature')"
ck "W2 branch sh-fix"                  0   "$(runj 'git push origin sh-fix')"
ck "W3 remote eval-remote"             0   "$(runj 'git push eval-remote feature')"
ck "W4 non-alias -c config"            0   "$(runj 'git -c user.name=x push origin feature')"
# DANGER_OK escape（force / eval-force）
ck "DOK2 DANGER_OK -f"                 ASK "$(runj 'DANGER_OK=1 git push -f origin x')"
ck "DOK3 DANGER_OK eval force"         ASK "$(runj 'DANGER_OK=1 eval "git push --force origin x"')"
# 静的安全 push 無確認通過（runj=0・ask 無し）
ck "S1 bare push feature"              0   "$(runj 'git push')"
ck "S2 -u origin feature"              0   "$(runj 'git push -u origin feature')"
ck "S3 develop-fix safe"              0   "$(runj 'git push origin develop-fix')"

# ----- I083 false-green 注入（判定行ごと・ask 系は JSON で判別） -----
# FG-G: _push_has_force を常に False（def 直後に return False を注入）
BROKEN_FORCE="$TMP/guard_noforce.py"
sed 's/^def _push_has_force(cmd: str) -> bool:$/&\n    return False/' "$GUARD" > "$BROKEN_FORCE"
ck "FG-G noforce passes -f"            0   "$(rung "$BROKEN_FORCE" 'git push -f origin x')"
ck "FG-G2 real blocks -f"             2   "$(run 'git push -f origin x')"
# FG-H: 短縮クラスタ分岐を無効化（"f" in tok[1:] → False）
BROKEN_SHORT="$TMP/guard_noshort.py"
sed 's/return "f" in tok\[1:\]/return False/' "$GUARD" > "$BROKEN_SHORT"
ck "FG-H noshort passes -uf"          0   "$(rung "$BROKEN_SHORT" 'git push -uf origin x')"
ck "FG-H2 real blocks -uf"            2   "$(run 'git push -uf origin x')"
# FG-I: _push_is_dynamic と単純コマンドごとの判定（_push_dest_dynamic）を常に False
BROKEN_DYN="$TMP/guard_nodyn.py"
sed -e 's/^def _push_is_dynamic(cmd: str) -> bool:$/&\n    return False/' \
    -e 's/^def _push_dest_dynamic(toks) -> bool:$/&\n    return False/' "$GUARD" > "$BROKEN_DYN"
ck "FG-I nodyn passes cmdsubst"       0   "$(rungj "$BROKEN_DYN" 'git push origin $(echo develop)')"
ck "FG-I2 real asks cmdsubst"         ASK "$(runj 'git push origin $(echo develop)')"
# FG-J: eval ラッパー分岐を無効化
BROKEN_EVAL="$TMP/guard_noeval.py"
sed -e 's/if head == "eval" and any("push" in t for t in toks\[1:\]):/if False:/' -e 's/        if sub == "push":/        if False:/' "$GUARD" > "$BROKEN_EVAL"
ck "FG-J noeval passes eval"          0   "$(rungj "$BROKEN_EVAL" 'eval "git push origin develop"')"
ck "FG-J2 real blocks eval"           2   "$(runj 'eval "git push origin develop"')"
# FG-K: alias サブ分岐を無効化
BROKEN_ALIAS="$TMP/guard_noalias.py"
sed 's/if t == "-c" and toks\[i + 1\].startswith("alias.") and "push" in toks\[i + 1\]:/if False:/' "$GUARD" > "$BROKEN_ALIAS"
ck "FG-K noalias passes alias"        0   "$(rungj "$BROKEN_ALIAS" 'git -c alias.p="push origin develop" p')"
ck "FG-K2 real asks alias"            ASK "$(runj 'git -c alias.p="push origin develop" p')"
# FG-L: eval 分岐削除 + force 入力（force-in-eval が block でなく ask に degrade する裏取り）
ck "FG-L noeval passes eval-force"    0   "$(rungj "$BROKEN_EVAL" 'eval "git push --force origin x"')"
ck "FG-L2 real blocks eval-force"     2   "$(runj 'eval "git push --force origin x"')"

# ----- TC-DOC1: 限界注記更新の決定論 grep（手動テスト No.4 の機械版・grep 0=hit/1=miss） -----
DOC="$REPO_ROOT/docs/claude-code-structure.md"
grep -q "後続イシューで根治予定" "$DOC"; ck "DOC1a old note removed"      1 "$?"
grep -q "I083 で対応済み" "$DOC";        ck "DOC1b updated note present"  0 "$?"
grep -qE "完全に隠蔽|脅威モデル外" "$DOC"; ck "DOC1c residual limit noted"  0 "$?"
# false-green 裏取り: grep パターン自体が旧注記に一致することを確認（DOC1a の「不在」判定が意味を持つ）
printf '後続イシューで根治予定\n' > "$TMP/olddoc.md"
grep -q "後続イシューで根治予定" "$TMP/olddoc.md"; ck "DOC1a-fg pattern matches old note" 0 "$?"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
