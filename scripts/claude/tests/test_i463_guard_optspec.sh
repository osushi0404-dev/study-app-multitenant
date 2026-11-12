#!/usr/bin/env bash
# I463: 見張りのまとめ書きのオプションの読み方（値を取る文字の表 _OPTSPEC・_getopt）を決定論で確かめる。
# python はスクリプト名で読み終える（F15）・psql の値の中の c を -c と読まない（F14・F16）・まとめ書きの途中の値を読む（F17）・
# psql -d の値の f（F2）・sed の in-place（F4）・pytest の読む指定（F6）・cp／mv の書き先と移動元（敵対的レビューの Medium・
# F18・I444 F7）・シェルを包むコマンドの -c。
# 実行: bash scripts/claude/tests/test_i463_guard_optspec.sh
#
# 見張りに JSON を渡して判定だけを見る（コマンドは実行しない）。期待値: 2＝停止・ASK＝確認・0＝通す。
# ケースは docs/tests/open/I463_auto_test.md の TC-01〜TC-08 と 1 対 1。0=全 PASS / 1=FAIL あり。
set -uo pipefail
unset CLAUDE_PROJECT_DIR
REPO_ROOT="$(git rev-parse --show-toplevel)"
GUARD="$REPO_ROOT/scripts/claude/hooks/pretooluse_guard.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 一時リポジトリ（＝今のワークツリーの代役）に別ワークツリー W を作る（test_i454_guard_env_writes.sh と同じ）。
# 見張りはこの一時リポジトリの中から呼ぶ
MAIN="$TMP/main"
mkdir -p "$MAIN"
git -C "$MAIN" init -q
git -C "$MAIN" -c user.email=t@example.com -c user.name=tester commit -q --allow-empty -m init
git -C "$MAIN" branch -q other
W="$TMP/other-wt"
git -C "$MAIN" worktree add -q "$W" other
# アプリを import して全件を消すスクリプト（ホストの python でも危険操作を判定する形）
printf 'import django\nfrom apps.users.models import User\nUser.objects.all().delete()\n' > "$TMP/evil.py"
E="$TMP/evil.py"

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
b() {  # b <コマンド> [見張り]
  local out code
  out=$(python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$1" \
        | (cd "$MAIN" && python3 "${2:-$GUARD}" 2>/dev/null)); code=$?
  if [ "$code" = "0" ] && printf '%s' "$out" | grep -q '"permissionDecision":[[:space:]]*"ask"'; then echo ASK; else echo "$code"; fi; }
# 失敗の注入: 元のファイルの old（ちょうど 1 回だけあること）を new に置き換えた写しを作る。無ければ FAIL にする
patch() {  # patch <元> <出力> <old> <new>
  python3 - "$@" <<'PY'
import sys
src, dst, old, new = sys.argv[1:]
s = open(src, encoding="utf-8").read()
if s.count(old) != 1:
    sys.exit(3)
open(dst, "w", encoding="utf-8").write(s.replace(old, new))
PY
}
fg() {  # fg <ID> <期待> <old> <new> <コマンド>
  if patch "$GUARD" "$TMP/g_$1.py" "$3" "$4"; then ck "$1" "$2" "$(b "$5" "$TMP/g_$1.py")"; else ck "$1 置き換え" ok NOPATCH; fi; }
D='docker compose exec -T backend'

# ---- TC-01 python はスクリプト名でオプションを読み終える（F15） ----
ck 01a 2   "$(b "python3 $E -xcfoo")"
ck 01b 2   "$(b "python3 $E -vc 1")"
ck 01c 2   "$(b "python3 $E")"
ck 01d 2   "$(b "python3 -Xdev $E")"
ck 01e 0   "$(b "python3 -c 'print(1)' $E")"
ck 01f 2   "$(b "$D python manage.py shell -c 'from apps.users.models import User; User.objects.all().delete()'")"
fg FG-01 0 '_OPTSPEC_STOP = {"python": "cm"}' '_OPTSPEC_STOP = {}' "python3 $E -xcfoo"

# ---- TC-02 psql の値の中の文字を -c と読まない（F14・F16） ----
ck 02a 0   "$(b 'psql -Umarc drop-test')"
ck 02b 0   "$(b "psql -hlocalhost -Ucelery -c 'select 1'")"
ck 02c 2   "$(b "psql -Umarc mydb -c 'DELETE FROM users'")"
ck 02d 2   "$(b $'psql -hlocal$(hostname) -U postgres <<EOF\nDELETE FROM users;\nEOF')"
fg FG-02 2 '"psql": ("cdfFhLopPRTUv",' '"psql": ("cdfFhLopPRTv",' 'psql -Umarc drop-test'

# ---- TC-03 まとめ書きの途中の値を読む（F17） ----
ck 03a 2   "$(b 'psql -Xf/tmp/dump.sql')"
ck 03b 2   "$(b "$D psql -Xf/tmp/dump.sql")"
ck 03c ASK "$(b 'grep -ie. .env')"
ck 03d ASK "$(b 'grep -f .env x')"
ck 03e ASK "$(b 'grep -m1 x .env')"
ck 03f 0   "$(b 'grep -ie. README.md')"
fg FG-03 0 '("-f", "--file"), cmd="psql")' '("-f", "--file"))' 'psql -Xf/tmp/dump.sql'

# ---- TC-04 psql の -d の値の f を -f と読まない（F2） ----
ck 04a 0   "$(b 'psql -dprofile_db -c "select 1"')"
ck 04b 0   "$(b "$D psql -dprofile_db -c \"select 1\"")"

# ---- TC-05 sed の in-place の判定（F4） ----
ck 05a 0   "$(b "sed -e's/print/log/' $W/x")"
ck 05b 2   "$(b "sed -ie s/a/b/ $W/x")"
ck 05c 2   "$(b "sed -i.bak s/a/b/ $W/x")"
ck 05d 2   "$(b "sed --in-place=.bak -e s/a/b/ $W/x")"
ck 05e 0   "$(b "sed -n -f $W/x /tmp/y")"
fg FG-05 2 '        if not names & {"-i", "--in-place"}:' '        if not _has_short(args, "i", "--in-place"):' "sed -e's/print/log/' $W/x"

# ---- TC-06 読む指定を書き込みと見なさない（F6） ----
ck 06a 0   "$(b "$D pytest --cov=/app/apps")"
ck 06b 0   "$(b "$D pytest --ignore=/app/apps/x")"
ck 06c 0   "$(b "$D pytest --cov-config=/app/.coveragerc")"
ck 06d 0   "$(b "$D pytest --deselect=/app/apps/t.py::test_a")"
ck 06e ASK "$(b "$D pytest --basetemp=/app/tmp")"
ck 06f ASK "$(b "$D pytest --junitxml=/app/r.xml -k x")"
fg FG-06 ASK '"confcutdir", "cov", ' '"confcutdir", ' "$D pytest --cov=/app/apps"

# ---- TC-07 cp／mv の書き先と移動元（敵対的レビューの Medium・F18・I444 F7） ----
ck 07a 0   "$(b "cp -vt/tmp/d $W/a $W/b")"
ck 07b 0   "$(b "cp -t /tmp/d $W/a $W/b")"
ck 07c 2   "$(b "cp -vt$W/d /tmp/a /tmp/b")"
ck 07d 2   "$(b "mv -vt/tmp/d $W/a")"
ck 07e 2   "$(b "install -m644 /tmp/a $W/b")"
ck 07f 0   "$(b "mv -S $W/sfx /tmp/a /tmp/b")"
fg FG-07 2 '    return tdir or (pos[-1:] if len(pos) >= 2 else [])' '    return tdir + pos[-1:]' "cp -vt/tmp/d $W/a $W/b"

# ---- TC-08 シェルを包むコマンドの -c（su・flock・script） ----
ck 08a 2   "$(b "su -lc'git push --force origin develop'")"
ck 08b 2   "$(b "su -s/bin/bash -c 'git push --force origin develop'")"
ck 08c 2   "$(b "flock -w3 /tmp/l -c 'git push --force origin develop'")"
ck 08d 2   "$(b "script -qc 'git push --force origin develop' /dev/null")"

printf 'pass=%d fail=%d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
