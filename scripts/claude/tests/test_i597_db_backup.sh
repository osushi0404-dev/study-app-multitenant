#!/usr/bin/env bash
# I597（plan_I597.md §4-5・auto_test TC-01・TC-03）: DB の控えの入口 scripts/claude/db-backup.sh と、人の包み scripts/db_backup.sh。
#   本物の docker は使わない。一時のフォルダに写しのリポジトリを作り、PATH の先頭に偽の docker を置く（外の命令だけを差し替える。
#   入口に差し替えの口は作らない・plan 9）。本物のリポジトリには何も書かない。
#   S: 成功・失敗の 4 通り（非 0・空・完了の行なし・\unrestrict の欠け）・古い形・名前の誤り・人の包み
#   FG: 写しの入口・包みを壊すと、対応する S が不合格になること
# 実行: bash scripts/claude/tests/test_i597_db_backup.sh
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
yn() { if "$@" >/dev/null 2>&1; then echo yes; else echo no; fi; }

# 偽の pg_dump の出力（15.14 以降の形: \restrict <鍵> … 完了の行 … \unrestrict <鍵>）
GOOD="$TMP/good.sql"
cat > "$GOOD" <<'EOF'
--
-- PostgreSQL database dump
--

\restrict KEY123

CREATE TABLE t (id integer);

--
-- PostgreSQL database dump complete
--

\unrestrict KEY123

EOF
OLD="$TMP/old.sql"; grep -v 'restrict KEY123' "$GOOD" > "$OLD"

# 偽の docker: 引数を記録し、FAKE_MODE に応じた出力と終了コードを返す
FAKE_BIN="$TMP/bin"; mkdir -p "$FAKE_BIN"
cat > "$FAKE_BIN/docker" <<EOF
#!/usr/bin/env bash
echo "\$*" >> "\$FAKE_LOG"
case "\$FAKE_MODE" in
  ok) cat "$GOOD" ;;
  old) cat "$OLD" ;;
  fail) head -n 4 "$GOOD"; echo "pg_dump: error: boom" >&2; exit 1 ;;
  empty) : ;;
  trunc) head -n 7 "$GOOD" ;;
  oldtrunc) head -n 6 "$OLD" ;;
  nounrestrict) grep -v '^\\\\unrestrict' "$GOOD" ;;
  wrongkey) sed 's/^\\\\unrestrict KEY123/\\\\unrestrict OTHER/' "$GOOD" ;;
esac
EOF
chmod +x "$FAKE_BIN/docker"

# make_repo <名前>: 入口と包みの写しを持つリポジトリを作り、その根を出す
make_repo() {
  local r="$TMP/$1"
  mkdir -p "$r/scripts/claude"
  cp "$REPO_ROOT/scripts/claude/db-backup.sh" "$r/scripts/claude/db-backup.sh"
  cp "$REPO_ROOT/scripts/db_backup.sh" "$r/scripts/db_backup.sh"
  git -C "$r" init -q
  echo "$r"
}
# run <根> <モード> <スクリプト> [引数...]: 偽の docker で流す。終了コードを RC、出力を $r/out に置く
run() {
  local r="$1" mode="$2" script="$3"; shift 3
  : > "$r/docker.log"
  (cd "$r" && PATH="$FAKE_BIN:$PATH" FAKE_MODE="$mode" FAKE_LOG="$r/docker.log" bash "$script" "$@") > "$r/out" 2>&1
  RC=$?
}
count() { find "$1" -maxdepth 1 -name 'backup_*.sql' | wc -l | tr -d ' '; }

# --- S の判定（根を受けて合否を返す。FG で壊した写しにも同じ判定を使う） ---
s1() {  # 成功: 1 個・名前の形・中身が同じ・権限 600・一時のファイルなし・✅ の行・docker の引数
  local r="$1" f
  run "$r" ok scripts/claude/db-backup.sh t1
  [ "$RC" = 0 ] && [ "$(count "$r")" = 1 ] || return 1
  f=$(find "$r" -maxdepth 1 -name 'backup_*.sql')
  [[ "$(basename "$f")" =~ ^backup_t1_[0-9]{8}_[0-9]{6}\.sql$ ]] || return 1
  cmp -s "$f" "$GOOD" || return 1
  [ "$(stat -c %a "$f")" = 600 ] || return 1
  grep -q '✅ 控えを取りました: backup_t1_' "$r/out" || return 1
  grep -qx 'compose exec -T db pg_dump -U postgres learning_app' "$r/docker.log"
}
fails_clean() {  # <根> <モード>: 入口が 1 で終わり、backup_*.sql（一時のファイルを含む）が 0 個
  run "$1" "$2" scripts/claude/db-backup.sh t
  [ "$RC" = 1 ] && [ "$(count "$1")" = 0 ]
}
s2() { fails_clean "$1" fail; }
s3() { fails_clean "$1" empty; }
s4() { fails_clean "$1" trunc && fails_clean "$1" oldtrunc; }  # oldtrunc は完了の行の確かめだけが止める
s5() { fails_clean "$1" nounrestrict && fails_clean "$1" wrongkey; }
s6() {  # 古い形（\restrict なし）: 成功・名前なしの形
  local f
  run "$1" old scripts/claude/db-backup.sh
  [ "$RC" = 0 ] && [ "$(count "$1")" = 1 ] || return 1
  f=$(find "$1" -maxdepth 1 -name 'backup_*.sql')
  [[ "$(basename "$f")" =~ ^backup_[0-9]{8}_[0-9]{6}\.sql$ ]]
}
bad_name() {  # <根> <引数...>: 2 で終わり、ファイルなし、docker を呼ばない
  local r="$1"; shift
  run "$r" ok scripts/claude/db-backup.sh "$@"
  [ "$RC" = 2 ] && [ "$(count "$r")" = 0 ] && [ ! -s "$r/docker.log" ]
}
s7() { bad_name "$1" ../x && bad_name "$1" 'a b' && bad_name "$1" '' && bad_name "$1" a b &&
       bad_name "$1" "$(printf 'a%.0s' {1..65})"; }
s8() {  # 人の包み: 失敗で非 0・0 個、成功で 0・1 個・案内の行
  local r="$1"
  run "$r" fail scripts/db_backup.sh
  [ "$RC" != 0 ] && [ "$(count "$r")" = 0 ] || return 1
  run "$r" ok scripts/db_backup.sh
  [ "$RC" = 0 ] && [ "$(count "$r")" = 1 ] && grep -q 'Google Drive' "$r/out"
}
s9() { run "$1" fail scripts/claude/db-backup.sh t; grep -qF 'bash scripts/claude/db-backup.sh <名前>' "$1/out"; }

# 判定ごとに新しい写しを使う（前の判定のファイルが数に混ざらないように）
for s in s1 s2 s3 s4 s5 s6 s7 s8 s9; do
  ck "$s" yes "$(yn "$s" "$(make_repo "$s")")"
done

# ---------------- FG: 写しを壊すと落ちる ----------------
R=$(make_repo fg1); sed -i '/^trap /d' "$R/scripts/claude/db-backup.sh"
ck "FG1 入口から trap を消すと S2（失敗で残さない）が不合格" no "$(yn s2 "$R")"
R=$(make_repo fg2); sed -i 's/-- PostgreSQL database dump complete/--/' "$R/scripts/claude/db-backup.sh"
ck "FG2 完了の行の確かめを外すと S4（途中で切れた）が不合格" no "$(yn s4 "$R")"
R=$(make_repo fg3); cat > "$R/scripts/db_backup.sh" <<'EOF'
#!/bin/bash
set -e
OUTPUT="backup_$(date +%Y%m%d_%H%M%S).sql"
docker compose exec -T db pg_dump -U postgres learning_app > "$OUTPUT"
echo "このファイルをGoogle Drive等に保存して他のPCと共有してください。"
EOF
ck "FG3 人の包みを今の形に戻すと S8 が不合格" no "$(yn s8 "$R")"

printf '\n%d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
