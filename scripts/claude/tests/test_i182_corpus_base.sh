#!/usr/bin/env bash
# I182（plan_I182.md 4-1）: guard_corpus_diff.py の比べる相手（base_rev）を、一時 git リポジトリで決定論検証する。
# develop を取り込んだマージコミットが見張りの最終変更でも、取り込んだ側の変更と比べない（誤不合格の再発防止）。
# 実行: bash scripts/claude/tests/test_i182_corpus_base.sh
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
DIFF_PY="$REPO_ROOT/scripts/claude/tests/guard_corpus_diff.py"
TMP="$(mktemp -d)"
trap 'rm -r "$TMP"' EXIT
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@example.invalid GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@example.invalid
G="scripts/claude/hooks/pretooluse_guard.py"

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
# base_rev() の rev を、指定のリポジトリを作業ディレクトリにして求め、コミット ID に直す
base_of() {
  (cd "$1" && python3 - "$DIFF_PY" <<'PY'
import importlib.util, subprocess, sys
spec = importlib.util.spec_from_file_location("gcd", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
git = lambda *a: subprocess.run(["git", *a], capture_output=True, text=True)
rev, _ = m.base_rev(git)
print(git("rev-parse", rev).stdout.strip() if rev else "NONE")
PY
  )
}
commit_line() { echo "$2" >> "$1/$G"; git -C "$1" add "$G"; git -C "$1" commit -qm "$3"; git -C "$1" rev-parse HEAD; }

R="$TMP/r"
mkdir -p "$R/$(dirname "$G")"
git -C "$R" init -q -b develop
echo "v0" > "$R/$G"; git -C "$R" add "$G"; git -C "$R" commit -qm c0
C0="$(git -C "$R" rev-parse HEAD)"
git -C "$R" checkout -q -b feature
C1="$(commit_line "$R" v1-feature c1)"
git -C "$R" checkout -q develop
# develop 側は先頭に足す（feature の末尾の追加と衝突させない）
sed -i '1i v2-develop' "$R/$G"; git -C "$R" commit -qam c2
C2="$(git -C "$R" rev-parse HEAD)"
git -C "$R" update-ref refs/remotes/origin/develop "$C2"

git -C "$R" checkout -q feature
ck "B2 develop を取り込む前の feature は分かれた点（c0）" "$C0" "$(base_of "$R")"
git -C "$R" merge -q --no-edit develop >/dev/null
ck "B1 develop を取り込んだ feature（見張りの最終変更がマージ）は c2（再発防止）" "$C2" "$(base_of "$R")"
OLD="$(git -C "$R" rev-parse "$(git -C "$R" log -1 --format=%H -- "$G")^")"
ck "FG-B1 旧ロジック（最終変更の直前）はこの状態で c1 を選ぶ＝誤不合格を再現している" "$C1" "$OLD"

# B3: develop に feature をマージした M2（HEAD = origin/develop）は、その PR の取り込み前（M2^1）
git -C "$R" checkout -q develop
git -C "$R" merge -q --no-ff --no-edit feature
M2="$(git -C "$R" rev-parse HEAD)"
git -C "$R" update-ref refs/remotes/origin/develop "$M2"
ck "B3 develop の上（HEAD = origin/develop）は M2^1" "$(git -C "$R" rev-parse "$M2^1")" "$(base_of "$R")"

# B4: origin/develop が無いリポジトリでは、今までどおり見張りを最後に変えたコミットの直前
R4="$TMP/r4"
mkdir -p "$R4/$(dirname "$G")"
git -C "$R4" init -q -b feature
echo "v0" > "$R4/$G"; git -C "$R4" add "$G"; git -C "$R4" commit -qm c0
C41="$(commit_line "$R4" v1 c1)"
ck "B4 origin/develop が無ければ c1^1" "$(git -C "$R4" rev-parse "$C41^1")" "$(base_of "$R4")"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
