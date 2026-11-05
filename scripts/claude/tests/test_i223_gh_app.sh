#!/usr/bin/env bash
# I223: GitHub App の鍵の仕組み（scripts/claude/gh-app/）と、テスト用のセッションを読み取りだけの鍵で起こすことを決定論検証する。
# 実行: bash scripts/claude/tests/test_i223_gh_app.sh
# ケースは docs/tests/open/I223_auto_test.md の TC-02（G1〜G5）と対応する。
# curl・openssl・本物の gh・claude は一時フォルダの偽物に差し替える（秘密の鍵ファイルと本物の GitHub は使わない）。
# FG: 各スクリプトの写しを sed で壊し、該当の G が不合格になることをこの中で確かめる。
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
pass=0; fail=0
ck() {  # ck <名前> <期待> <実際>
  if [ "$2" = "$3" ]; then echo "PASS $1"; pass=$((pass + 1))
  else echo "FAIL $1（期待: $2 / 実際: $3）"; fail=$((fail + 1)); fi
}

# ---- 偽物 ----
STUB="$T/stub"; mkdir -p "$STUB"
cat > "$STUB/curl" <<'EOF'
#!/usr/bin/env bash
# 偽の curl: -d の本文を $FAKE_LOG に書き、$FAKE_RESP のファイルの中身を返す
prev=""
for a in "$@"; do
  [ "$prev" = "-d" ] && printf '%s' "$a" > "$FAKE_LOG"
  prev="$a"
done
cat "$FAKE_RESP"
EOF
cat > "$STUB/openssl" <<'EOF'
#!/usr/bin/env bash
# 偽の openssl: base64 は入力をそのまま、dgst は固定の文字列を返す（鍵ファイルは読まない）
case "$1" in
  base64) cat ;;
  dgst) cat > /dev/null; printf 'sig' ;;
esac
EOF
cat > "$STUB/real-gh" <<'EOF'
#!/usr/bin/env bash
echo "GH_TOKEN=${GH_TOKEN:-<none>}"
EOF
cat > "$STUB/claude" <<'EOF'
#!/usr/bin/env bash
echo "GH_APP_READONLY=${GH_APP_READONLY:-<none>}" >> "$FAKE_CLAUDE_OUT"
EOF
chmod +x "$STUB"/*
: > "$T/dummy.pem"
RO_PERMS='{"actions":"read","checks":"read","contents":"read","issues":"read","metadata":"read","pull_requests":"read","statuses":"read"}'
printf '{"token":"ro-token","permissions":%s}' "$RO_PERMS" > "$T/resp_ro.json"
printf '{"token":"rw-token","permissions":{"contents":"write","issues":"write"}}' > "$T/resp_rw.json"
printf '{"token":"bad-token","permissions":{"contents":"read","issues":"write"}}' > "$T/resp_bad.json"

# G6: claude -p の呼び出しと、tmux で claude を起こす行（tui-capture.sh・fix-loop で追加）の論理行
#     （行末の \ でつなぐ・コメントは除く）がすべて GH_APP_READONLY=1 を持つ
#     （export GH_APP_READONLY=1 するファイルは除く）。起動の所が増えても付け忘れを止める（計画変更記録 3）
g6() {
  python3 -I - "$@" <<'PY'
import re, sys
bad = []
for path in sys.argv[1:]:
    text = open(path, encoding="utf-8").read()
    if re.search(r"^export GH_APP_READONLY=1$", text, re.M):
        continue
    logical, cur = [], ""
    for line in text.split("\n"):
        if line.rstrip().endswith("\\"):
            cur += line.rstrip()[:-1] + " "
            continue
        logical.append(cur + line); cur = ""
    for l in logical:
        if l.lstrip().startswith("#"):
            continue
        launch = re.search(r'claude(\}")? -p\s+(--|"\$)', l) or re.search(r'tmux new-session\b.*\bclaude\b', l)
        if launch and "GH_APP_READONLY=1 " not in l:
            bad.append(f"{path}: {l.strip()[:120]}")
for b in bad:
    print(b)
sys.exit(1 if bad else 0)
PY
}

# ---- 1 組の写しに対して G1〜G6 を流し、各 G の合否（OK/NG）を出す ----
# run_cases <写しのフォルダ> [<G>]（G を渡せばそれだけを流す。中に gh-app/・scripts/claude/*.sh の写し）
run_cases() {
  local S="$1" only="${2:-}" W="$T/work.$RANDOM" out body r
  mkdir -p "$W"
  tok() { PATH="$STUB:$PATH" GH_APP_KEY="$T/dummy.pem" FAKE_LOG="$W/body" "$@"; }
  want() { [ -z "$only" ] || [ "$only" = "$1" ]; }

  if want G1; then
  # G1: 読み取りだけの本文と控えの分け方／指定なしでは permissions を送らない
  r=OK
  out=$(tok env GH_APP_READONLY=1 GH_APP_CACHE_DIR="$W/c1" FAKE_RESP="$T/resp_ro.json" bash "$S/gh-app/gh-app-token" 2>/dev/null) || r=NG
  [ "$out" = ro-token ] || r=NG
  body=$(cat "$W/body" 2>/dev/null)
  python3 -I -c 'import json,sys; d=json.loads(sys.argv[1]); p=d.get("permissions");
sys.exit(0 if p == json.loads(sys.argv[2]) and d.get("repositories") == ["study-app-multitenant"] else 1)' "$body" "$RO_PERMS" 2>/dev/null || r=NG
  [ -f "$W/c1/token-readonly" ] && [ ! -e "$W/c1/token" ] || r=NG
  out=$(tok env -u GH_APP_READONLY GH_APP_CACHE_DIR="$W/c1b" FAKE_RESP="$T/resp_rw.json" bash "$S/gh-app/gh-app-token" 2>/dev/null) || r=NG
  [ "$out" = rw-token ] || r=NG
  python3 -I -c 'import json,sys; sys.exit(0 if "permissions" not in json.loads(sys.argv[1]) else 1)' "$(cat "$W/body" 2>/dev/null)" 2>/dev/null || r=NG
  [ -f "$W/c1b/token" ] || r=NG
  echo "G1 $r"
  fi

  if want G2; then
  # G2: 書き込みの鍵の控えがあっても、読み取りだけの指定では返さない
  r=OK
  mkdir -p "$W/c2"; chmod 700 "$W/c2"
  printf '%s %s\n' "$(( $(date +%s) + 3600 ))" "rw-cached" > "$W/c2/token"
  out=$(tok env GH_APP_READONLY=1 GH_APP_CACHE_DIR="$W/c2" FAKE_RESP="$T/resp_ro.json" bash "$S/gh-app/gh-app-token" 2>/dev/null) || r=NG
  [ "$out" = ro-token ] || r=NG
  echo "G2 $r"
  fi

  if want G3; then
  # G3: 読み取りだけの指定で write が返ったら鍵を出さず、控えも作らない
  r=OK
  [ -f "$S/gh-app/gh-app-token" ] || r=NG   # スクリプトが無いと「失敗した」で素通りしないように
  if out=$(tok env GH_APP_READONLY=1 GH_APP_CACHE_DIR="$W/c3" FAKE_RESP="$T/resp_bad.json" bash "$S/gh-app/gh-app-token" 2>/dev/null); then r=NG; fi
  [ -z "$out" ] || r=NG
  [ ! -e "$W/c3/token-readonly" ] || r=NG
  echo "G3 $r"
  fi

  if want G4; then
  # G4: gh の入口は、読み取りだけの指定を GH_APP_DISABLE で外さない／DISABLE だけなら鍵を渡さない
  r=OK
  out=$(tok env -u GH_TOKEN GH_APP_READONLY=1 GH_APP_DISABLE=1 GH_APP_CACHE_DIR="$W/c4" GH_APP_REAL_GH="$STUB/real-gh" \
        FAKE_RESP="$T/resp_ro.json" bash "$S/gh-app/gh" 2>/dev/null) || r=NG
  [ "$out" = "GH_TOKEN=ro-token" ] || r=NG
  out=$(tok env -u GH_TOKEN -u GH_APP_READONLY GH_APP_DISABLE=1 GH_APP_CACHE_DIR="$W/c4b" GH_APP_REAL_GH="$STUB/real-gh" \
        FAKE_RESP="$T/resp_rw.json" bash "$S/gh-app/gh" 2>/dev/null) || r=NG
  [ "$out" = "GH_TOKEN=<none>" ] || r=NG
  echo "G4 $r"
  fi

  if want G5; then
  # G5: テスト用のセッションを起こす 3 か所が、実際に起こした claude に GH_APP_READONLY=1 を渡す
  local o="$W/claude_out"
  : > "$o"; : > "$W/in"
  ( unset GH_APP_READONLY
    export FAKE_CLAUDE_OUT="$o" CLAUDE_BIN="$STUB/claude"
    bash "$S/test-session.sh" x >/dev/null 2>&1
    (cd "$REPO_ROOT" && bash "$S/check-permission-prompt.sh" bash 'true' >/dev/null 2>&1)
    # 写しのフォルダのライブラリ（場所は実行時に決まる）
    # shellcheck source=/dev/null
    . "$S/review-process-lib.sh" && run_claude_logged 10 "$W/log" "$W/in" --permission-prompts none >/dev/null 2>&1 )
  [ "$(paste -sd' ' "$o")" = "GH_APP_READONLY=1 GH_APP_READONLY=1 GH_APP_READONLY=1" ] && echo "G5 OK" || echo "G5 NG"
  fi

  if want G6; then
  g6 "$S"/*.sh > /dev/null && echo "G6 OK" || echo "G6 NG"
  fi
}

copy_scripts() {  # copy_scripts <先>（scripts/claude/*.sh と gh-app/ の写し）
  mkdir -p "$1/gh-app"
  cp "$REPO_ROOT/scripts/claude/gh-app/gh-app-token" "$REPO_ROOT/scripts/claude/gh-app/gh" "$1/gh-app/" 2>/dev/null
  cp "$REPO_ROOT"/scripts/claude/*.sh "$1/" 2>/dev/null
  # git は実行権を記録しない（core.filemode=false の端末から入る）ので、CI と同じく実行権なしの写しで確かめる（I223 fix-loop）
  chmod 644 "$1"/gh-app/* "$1"/*.sh 2>/dev/null
}

# ---- 本物（リポジトリの版）----
copy_scripts "$T/real"
res=$(run_cases "$T/real")
for g in G1 G2 G3 G4 G5 G6; do
  ck "$g リポジトリの版で合格" "$g OK" "$(grep "^$g " <<< "$res")"
done

# ---- FG: 壊した写しでは該当の G が不合格になる ----
fg() {  # fg <G> <説明> <sed のファイル（写しのフォルダからの相対）> <sed の式>…
  local g="$1" what="$2" d="$T/fg.$1.$RANDOM"
  shift 2
  copy_scripts "$d"
  while [ $# -ge 2 ]; do
    [ -f "$d/$1" ] || { ck "FG $g $what の対象がある" "exists" "missing: $1"; return; }
    cp "$d/$1" "$d/$1.orig"
    sed -i "$2" "$d/$1" 2>/dev/null
    if cmp -s "$d/$1" "$d/$1.orig"; then   # 式が当たらない（壊せていない）なら FG そのものを不合格にする
      ck "FG $g $what の書き換えが当たる" "changed" "unchanged"; return
    fi
    shift 2
  done
  ck "FG $g $what で不合格になる" "$g NG" "$(run_cases "$d" "$g" | grep "^$g ")"
}
fg G1 "本文から permissions を消す" gh-app/gh-app-token 's/^  PERMS=",.*/  PERMS=""/'
fg G2 "控えのファイル名を同じにする" gh-app/gh-app-token 's#/token-readonly"#/token"#'
fg G3 "権限の確かめを消す" gh-app/gh-app-token 's/if os.environ.get("GH_APP_READONLY"):/if False:/'
# sed の式なので $ をそのまま渡す
# shellcheck disable=SC2016
fg G4 "GH_APP_READONLY の条件を消す" gh-app/gh 's/\[ -n "\${GH_APP_READONLY:-}" \] || //'
# 入口が gh-app-token を直接実行すると、実行権の無い写し（CI と同じ）で鍵を受け取れない（I223 fix-loop の再発防止）
# shellcheck disable=SC2016
fg G4 "入口が gh-app-token を bash に渡さない" gh-app/gh 's#"$(bash "$dir/gh-app-token")"#"$("$dir/gh-app-token")"#'
fg G5 "test-session.sh の指定を消す" test-session.sh 's/^export GH_APP_READONLY=1$/:/'
fg G5 "check-permission-prompt.sh の指定を消す" check-permission-prompt.sh 's/GH_APP_READONLY=1 //'
fg G5 "review-process-lib.sh の指定を消す" review-process-lib.sh 's/GH_APP_READONLY=1 //'
fg G6 "plan-issue-review.sh の指定を消す" plan-issue-review.sh 's/GH_APP_READONLY=1 //'
fg G6 "複数行の呼び出し（fix-review-lib.sh）の指定を消す" fix-review-lib.sh 's/GH_APP_READONLY=1 //'
fg G6 "code-review.sh の指定を消す" code-review.sh 's/GH_APP_READONLY=1 //'
fg G6 "tmux で起こす tui-capture.sh の指定を消す" tui-capture.sh 's/-e GH_APP_READONLY=1 //'

echo "---"
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
