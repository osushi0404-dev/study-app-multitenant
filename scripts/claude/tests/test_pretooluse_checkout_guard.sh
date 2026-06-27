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
ck "G7 DANGER_OK bypass"       0 "$(run 'DANGER_OK=1 git checkout -- tracked.txt')"

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

# --- FALSEGREEN（自動注入）: 判定呼び出し行を無効化した複製で dirty が素通し /
#     実体で block。両者の差で「block は判定行に依存」を機械裏取り（false-green 排除） ---
BROKEN="$TMP/guard_broken.py"
sed 's/target = _git_revert_target_on_dirty(cmd)/target = None/' "$GUARD" > "$BROKEN"
ck "FALSEGREEN injected passes" 0 "$(json 'git checkout -- g11.txt' | python3 "$BROKEN" >/dev/null 2>&1; echo $?)"
ck "FALSEGREEN real blocks"     2 "$(run 'git checkout -- g11.txt')"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
