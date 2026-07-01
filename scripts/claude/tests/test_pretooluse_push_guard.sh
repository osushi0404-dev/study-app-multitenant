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
ck "P33 dst-side + (feat:+refs/heads/main)" 2 "$(run 'git push origin feat:+refs/heads/main')"

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

# ===================== I083: 動的宛先 ask / force 取りこぼし =====================
# ----- develop context: 動的・不透明な宛先 → ask（exit0＋ask JSON） -----
git checkout -q develop
ck "D1 cmdsubst \$(echo develop)"      ASK "$(runj 'git push origin $(echo develop)')"
ck "D2 cmdsubst rev-parse"             ASK "$(runj 'git push origin $(git rev-parse --abbrev-ref HEAD)')"
ck "D3 var expansion \$D"              ASK "$(runj 'D=develop; git push origin $D')"
ck "D4 alias indirection"              ASK "$(runj 'git -c alias.p="push origin develop" p')"
ck "D5 eval wrapper"                   ASK "$(runj 'eval "git push origin develop"')"
ck "D6 sh -c wrapper"                  ASK "$(runj 'sh -c "git push origin develop"')"
ck "D8 brace \${BR}"                   ASK "$(runj 'git push origin ${BR}')"
ck "D10 backtick substitution"         ASK "$(runj 'git push origin x`whoami`y')"
ck "DOK1 DANGER_OK dynamic escape"     0   "$(runj 'DANGER_OK=1 git push origin $(echo develop)')"

# ----- feature/x context -----
git checkout -q feature/x
ck "D7 dynamic feature (not exit2)"    ASK "$(runj 'git push origin $(git rev-parse --abbrev-ref HEAD)')"
ck "D9 dynamic + rm-rf (block wins)"   2   "$(run 'git push origin $VAR && rm -rf x')"
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
ck "F7 eval hidden force"              ASK "$(runj 'eval "git push --force origin x"')"
# ラッパー誤 ask 回帰（構造的検出・branch/remote 名の偶然一致で発火しない・Q8）→ pass
ck "W1 branch bash-feature"            0   "$(runj 'git push origin bash-feature')"
ck "W2 branch sh-fix"                  0   "$(runj 'git push origin sh-fix')"
ck "W3 remote eval-remote"             0   "$(runj 'git push eval-remote feature')"
ck "W4 non-alias -c config"            0   "$(runj 'git -c user.name=x push origin feature')"
# DANGER_OK escape（force / eval-force）
ck "DOK2 DANGER_OK -f"                 0   "$(runj 'DANGER_OK=1 git push -f origin x')"
ck "DOK3 DANGER_OK eval force"         0   "$(runj 'DANGER_OK=1 eval "git push --force origin x"')"
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
# FG-I: _push_is_dynamic を常に False
BROKEN_DYN="$TMP/guard_nodyn.py"
sed 's/^def _push_is_dynamic(cmd: str) -> bool:$/&\n    return False/' "$GUARD" > "$BROKEN_DYN"
ck "FG-I nodyn passes cmdsubst"       0   "$(rungj "$BROKEN_DYN" 'git push origin $(echo develop)')"
ck "FG-I2 real asks cmdsubst"         ASK "$(runj 'git push origin $(echo develop)')"
# FG-J: eval ラッパー分岐を無効化
BROKEN_EVAL="$TMP/guard_noeval.py"
sed 's/if head == "eval" and any("push" in t for t in toks\[1:\]):/if False:/' "$GUARD" > "$BROKEN_EVAL"
ck "FG-J noeval passes eval"          0   "$(rungj "$BROKEN_EVAL" 'eval "git push origin develop"')"
ck "FG-J2 real asks eval"             ASK "$(runj 'eval "git push origin develop"')"
# FG-K: alias サブ分岐を無効化
BROKEN_ALIAS="$TMP/guard_noalias.py"
sed 's/if t == "-c" and toks\[i + 1\].startswith("alias.") and "push" in toks\[i + 1\]:/if False:/' "$GUARD" > "$BROKEN_ALIAS"
ck "FG-K noalias passes alias"        0   "$(rungj "$BROKEN_ALIAS" 'git -c alias.p="push origin develop" p')"
ck "FG-K2 real asks alias"            ASK "$(runj 'git -c alias.p="push origin develop" p')"
# FG-L: eval 分岐削除 + force 入力（force-in-eval が block でなく ask に degrade する裏取り）
ck "FG-L noeval passes eval-force"    0   "$(rungj "$BROKEN_EVAL" 'eval "git push --force origin x"')"
ck "FG-L2 real asks eval-force"       ASK "$(runj 'eval "git push --force origin x"')"

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
