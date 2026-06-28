#!/usr/bin/env bash
# I080: pretooluse_guard.py の push ポリシーを決定論検証する。
# 実行: bash scripts/claude/tests/test_pretooluse_push_guard.sh
#
# temp git repo（develop / feature/x ブランチ）を立て、フックへ stdin JSON を投入して
# exit code を検証する（実 push はしない＝フックの判定のみを見る）。
# 検証範囲: protected 宛先 push（danger-op）・--all/--mirror・--repo evasion・DANGER_OK escape・
#           FP 解消・安全 push 素通し・false-green 注入（判定行ごと）。
set -uo pipefail
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

json() { printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$1"; }
run()  { json "$1" | python3 "$GUARD" >/dev/null 2>&1; echo $?; }
rung() { json "$2" | python3 "$1" >/dev/null 2>&1; echo $?; }   # $1=guard, $2=command

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
ck "P6 DANGER_OK push origin develop"  0 "$(run 'DANGER_OK=1 git push origin develop')"
ck "P7 DANGER_OK bare push"            0 "$(run 'DANGER_OK=1 git push')"

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
ck "P23 DANGER_OK origin develop"      0 "$(run 'DANGER_OK=1 git push origin develop')"
ck "P24 DANGER_OK --all"               0 "$(run 'DANGER_OK=1 git push --all')"
ck "P25 --force origin feature"        2 "$(run 'git push --force origin feature')"
ck "P26 DANGER_OK --force feature"     0 "$(run 'DANGER_OK=1 git push --force origin feature')"
ck "P27 git -C push origin develop"    2 "$(run 'git -C /tmp push origin develop')"
ck "P28 --repo= develop:main"          2 "$(run 'git push --repo=origin develop:main')"
ck "P29 --repo= +develop"              2 "$(run 'git push --repo=origin +develop')"
ck "P30 --repo (space) develop:main"   2 "$(run 'git push --repo origin develop:main')"
ck "P31 DANGER_OK --repo= develop:main" 0 "$(run 'DANGER_OK=1 git push --repo=origin develop:main')"
ck "P32 --repo= feature (flag-block)"  2 "$(run 'git push --repo=origin feature')"

# ===== 回帰（既存ハードブロック維持） =====
ck "Pregr1 force push exit2"           2 "$(run 'git push --force origin x')"

# ===== false-green 注入（判定行ごと独立に裏取り） =====
# protected 判定行を無効化（dest を常に None 化）
BROKEN_PROT="$TMP/guard_noprot.py"
sed 's/dest = _push_protected_target(cmd)/dest = None/' "$GUARD" > "$BROKEN_PROT"
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

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
