#!/usr/bin/env bash
# I223: GitHub App の鍵の仕組み（scripts/claude/gh-app/）と、テスト用のセッションを読み取りだけの鍵で起こすことを決定論検証する。
# I225: 入口の auth status の置き換え（G8）・失効のスクリプト（G9）・鍵を出す書き方の静的な検査（G10）・MCP の抜け道（G7）を足した。
# 実行: bash scripts/claude/tests/test_i223_gh_app.sh
# ケースは docs/tests/closed/I223_auto_test.md の TC-02（G1〜G6）と docs/tests/open/I225_auto_test.md の TC-02（G7〜G10）と対応する。
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
cat > "$STUB/real-gh-auth" <<'EOF'
#!/usr/bin/env bash
# 偽の本物の gh（G8）: 引数を $FAKE_GH_ARGS に書く。--json があれば $FAKE_AUTH_JSON を、無ければ鍵の行を出す
echo "$*" >> "$FAKE_GH_ARGS"
for a in "$@"; do
  if [ "$a" = --json ]; then cat "$FAKE_AUTH_JSON"; exit 0; fi
done
echo "  - Token: SECRET-abc123"
EOF
cat > "$STUB/real-gh-revoke" <<'EOF'
#!/usr/bin/env bash
# 偽の本物の gh（G9）: 「鍵 引数」を $FAKE_GH_ARGS に書く。DELETE は $FAKE_REVOKED に鍵を足す（$FAKE_NO_REVOKE なら足さない）。
# 読みに行くと、失効した鍵なら 401 の文言で 1、$FAKE_NET_DOWN なら通信の失敗で 1、それ以外は 0。
# $FAKE_NET_AFTER_DELETE なら、最初の DELETE の後の読みをすべて通信の失敗にする（I226: DELETE の後の分岐）
echo "${GH_TOKEN:-<none>} $*" >> "$FAKE_GH_ARGS"
if [ "${1:-} ${2:-} ${3:-}" = "api -X DELETE" ]; then
  [ -n "${FAKE_NO_REVOKE:-}" ] || echo "${GH_TOKEN:-}" >> "$FAKE_REVOKED"
  [ -z "${FAKE_NET_AFTER_DELETE:-}" ] || : > "$FAKE_REVOKED.netdown"
  exit 0
fi
if [ -n "${FAKE_NET_DOWN:-}" ] || [ -e "$FAKE_REVOKED.netdown" ]; then echo "gh: dial tcp: lookup api.github.com: no such host" >&2; exit 1; fi
if grep -qxF "${GH_TOKEN:-}" "$FAKE_REVOKED" 2>/dev/null; then echo "gh: Bad credentials (HTTP 401)" >&2; exit 1; fi
exit 0
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

# launch_lines_missing <要る文字列> <export GH_APP_READONLY=1 のファイルを除くか 0|1> <ファイル…>
#   claude -p の呼び出しと、tmux で claude を起こす行の論理行（行末の \ でつなぐ・コメントは除く）のうち、
#   <要る文字列> を持たない行を出し、1 つでもあれば 1
# G6: すべて GH_APP_READONLY=1 を持つ（export GH_APP_READONLY=1 するファイルは除く）。起動の所が増えても付け忘れを止める（I223 計画変更記録 3）
# G7（I225）: すべて --strict-mcp-config を持つ（MCP は --mcp-config で渡したものだけ。export のファイルも除外しない）
g6() { launch_lines_missing "GH_APP_READONLY=1 " 1 "$@"; }
g7() { launch_lines_missing "--strict-mcp-config" 0 "$@"; }
launch_lines_missing() {
  python3 -I - "$@" <<'PY'
import re, sys
need, skip_export, paths = sys.argv[1], sys.argv[2] == "1", sys.argv[3:]
bad = []
for path in paths:
    text = open(path, encoding="utf-8").read()
    if skip_export and re.search(r"^export GH_APP_READONLY=1$", text, re.M):
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
        if launch and need not in l:
            bad.append(f"{path}: {l.strip()[:120]}")
for b in bad:
    print(b)
sys.exit(1 if bad else 0)
PY
}

# G10（I225）: 決まりの置き場（CLAUDE.md・docs/runbooks・.claude/skills・.claude/agents・scripts/claude〔tests を除く〕・
#     docs/*/templates）に、鍵を画面に出す書き方（--json なし、または -t/--show-token 付きの auth status・auth token）が無い。
#     auth status は、出てくるたびに、そのあとから行末か次のバッククォートまでの語を見る（行末の \ で続く行はつなぐ・I226）。auth token は鍵を丸ごと出すので、語を問わず不合格（I226）。語の境目は英数字だけで見る（和文がすぐ続いても当たる・I212）。個々のイシューの記録は対象外（plan_I225.md §9）
g10() {  # g10 <ルート>
  python3 -I - "$1" <<'PY'
import os, re, sys
root = sys.argv[1]
targets = ["CLAUDE.md", "docs/runbooks", ".claude/skills", ".claude/agents", "scripts/claude"]
docs = os.path.join(root, "docs")
if os.path.isdir(docs):
    targets += [os.path.join("docs", d, "templates") for d in sorted(os.listdir(docs))]
skip = os.path.join(root, "scripts", "claude", "tests")
files = []
for t in targets:
    p = os.path.join(root, t)
    if os.path.isfile(p):
        files.append(p)
    for dp, dns, fns in os.walk(p):
        if dp == skip or dp.startswith(skip + os.sep):
            dns[:] = []
            continue
        files += [os.path.join(dp, f) for f in fns]
bad = []
for f in files:
    try:
        text = open(f, encoding="utf-8").read()
    except (UnicodeDecodeError, OSError):
        continue
    for m in re.finditer(r"gh auth (status|token)(?![A-Za-z0-9_])", text):
        # 次のバッククォートか、行末の \ の付かない改行までを見る（\ で続く行はつなぐ）
        rest = re.split(r"`|(?<!\\)\n", text[m.end():], maxsplit=1)[0].replace("\\\n", " ")
        toks = rest.split()
        has_json = any(t.startswith("--json") for t in toks)
        shows = any(t == "--show-token" or re.fullmatch(r"-[A-Za-z]*t[A-Za-z]*", t) for t in toks)
        if m.group(1) == "token" or not has_json or shows:
            line = text.count("\n", 0, m.start()) + 1
            bad.append(f"{os.path.relpath(f, root)}:{line}: {m.group(0)}{rest[:60]}")
for b in bad:
    print(b)
sys.exit(1 if bad else 0)
PY
}

# ---- 1 組の写しに対して G1〜G9 を流し、各 G の合否（OK/NG）を出す ----
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

  if want G7; then
  g7 "$S"/*.sh > /dev/null && echo "G7 OK" || echo "G7 NG"
  fi

  if want G8; then
  # G8: 入口は --json・-t/--show-token なしの auth status を、鍵の行を出さない --json の表示に置き換える
  r=OK
  local A="$W/g8args" J_OK="$W/g8ok.json" J_ERR="$W/g8err.json" rc
  printf '%s' '{"hosts":{"github.com":[{"active":true,"host":"github.com","login":"bot","state":"success","tokenSource":"GH_TOKEN","gitProtocol":"https"},{"active":false,"host":"github.com","login":"old","state":"success","tokenSource":"/x/hosts.yml","gitProtocol":"https"}]}}' > "$J_OK"
  printf '%s' '{"hosts":{"github.com":[{"active":true,"host":"github.com","login":"bot","state":"error","error":"SECRET-in-error","tokenSource":"GH_TOKEN","gitProtocol":"https"}]}}' > "$J_ERR"
  # 鍵を受け取らない形で動かす（GH_APP_DISABLE=1・読み取りだけの指定なし）。$1=JSON・残り=gh の引数。出力は標準出力だけ
  g8() { local j="$1"; shift
         env -u GH_APP_READONLY GH_APP_DISABLE=1 GH_APP_REAL_GH="$STUB/real-gh-auth" FAKE_GH_ARGS="$A" FAKE_AUTH_JSON="$j" \
           bash "$S/gh-app/gh" "$@" 2>/dev/null; }
  : > "$A"
  out=$(g8 "$J_OK" auth status); rc=$?
  [ "$rc" = 0 ] || r=NG
  [ "$out" = "github.com bot GH_TOKEN success (active)
github.com old /x/hosts.yml success" ] || r=NG
  [ "$(cat "$A")" = "auth status --json hosts" ] || r=NG
  : > "$A"
  out=$(g8 "$J_OK" auth status -a -h github.com) || r=NG
  [[ "$out" != *SECRET* ]] || r=NG
  [ "$(cat "$A")" = "auth status -a -h github.com --json hosts" ] || r=NG
  out=$(g8 "$J_ERR" auth status); rc=$?
  [ "$rc" = 1 ] || r=NG                       # state が success でないものがあれば 1
  [[ "$out" != *SECRET* ]] || r=NG            # error の欄は出さない
  [ "$out" = "github.com bot GH_TOKEN error (active)" ] || r=NG
  # ログインなし（hosts が空）は 1。案内の文は本物の gh が標準エラーに出すので、標準出力は空（I226・F2）
  printf '%s' '{"hosts":{}}' > "$W/g8empty.json"
  out=$(g8 "$W/g8empty.json" auth status); rc=$?
  [ "$rc" = 1 ] || r=NG
  [ -z "$out" ] || r=NG
  # わざと鍵を見る書き方・--json・ほかのコマンドは置き換えない
  for args in "auth status -t" "auth status --show-token" "auth status -at" "auth status --json hosts" "pr list"; do
    : > "$A"
    # shellcheck disable=SC2086  # 語に分けて渡す
    g8 "$J_OK" $args > /dev/null
    [ "$(cat "$A")" = "$args" ] || r=NG
  done
  echo "G8 $r"
  fi

  if want G9; then
  # G9: revoke.sh は控えの 2 つの鍵を失効させ、401 で無効を確かめて控えを消す。--stdin は渡された鍵だけを失効させる
  r=OK
  local C="$W/g9c" A="$W/g9args" V="$W/g9rev" out2
  rv() { GH_APP_REAL_GH="$STUB/real-gh-revoke" GH_APP_CACHE_DIR="$C" FAKE_GH_ARGS="$A" FAKE_REVOKED="$V" bash "$S/gh-app/revoke.sh" "$@" 2>&1; }
  mkcache() { rm -rf "$C"; mkdir -p "$C"; : > "$A"; : > "$V"; rm -f "$V.netdown"
              printf '%s %s\n' 9999999999 rw-1 > "$C/token"; printf '%s %s\n' 9999999999 ro-1 > "$C/token-readonly"; }
  [ -f "$S/gh-app/revoke.sh" ] || r=NG
  # a) 2 つとも失効・確認・消す。鍵の値は出さない
  mkcache
  out2=$(rv) || r=NG
  [ "$(sort "$V" | paste -sd' ')" = "ro-1 rw-1" ] || r=NG
  [ ! -e "$C/token" ] && [ ! -e "$C/token-readonly" ] || r=NG
  [[ "$out2" != *rw-1* && "$out2" != *ro-1* ]] || r=NG
  grep -q '^rw-1 api -X DELETE installation/token' "$A" || r=NG
  # b) 控えが無い → 0
  rm -rf "$C"; mkdir -p "$C"
  rv > /dev/null || r=NG
  # c) 失効しない（GitHub が受け付けない）→ 1・控えは残す
  mkcache
  if FAKE_NO_REVOKE=1 rv > /dev/null; then r=NG; fi
  [ -f "$C/token" ] && [ -f "$C/token-readonly" ] || r=NG
  # d) 通信の失敗（401 が出ない）は無効の確認にしない → 1・控えは残す
  mkcache
  if FAKE_NET_DOWN=1 rv > /dev/null; then r=NG; fi
  [ -f "$C/token" ] || r=NG
  # e) --stdin: 渡された鍵だけを失効させ、控えは触らない。値は出さない
  mkcache
  out2=$(printf 'leaked-x\n' | rv --stdin) || r=NG
  [ "$(cat "$V")" = "leaked-x" ] || r=NG
  [ -f "$C/token" ] && [ -f "$C/token-readonly" ] || r=NG
  [[ "$out2" != *leaked-x* ]] || r=NG
  # f) 使い方の誤り → 2
  printf '' | rv --stdin > /dev/null; [ $? = 2 ] || r=NG
  rv --bogus > /dev/null; [ $? = 2 ] || r=NG
  # g) --stdin に最初から無効な鍵（貼り間違い・失効済み）→ 1。「失効を確認」と出さず、DELETE も送らない。値は出さない（I226・F1）
  mkcache
  echo bad-x > "$V"
  if out2=$(printf 'bad-x\n' | rv --stdin); then r=NG; fi
  [[ "$out2" == *最初から無効* && "$out2" != *失効を確認* && "$out2" != *bad-x* ]] || r=NG
  ! grep -q '^bad-x api -X DELETE' "$A" || r=NG
  # h) 控えの token だけ最初から無効（期限切れ）→ 0。2 つとも控えを消し、token は「もともと無効」と出す
  mkcache
  echo rw-1 > "$V"
  out2=$(rv) || r=NG
  [ ! -e "$C/token" ] && [ ! -e "$C/token-readonly" ] || r=NG
  [[ "$out2" == *"token: もともと無効"* ]] || r=NG
  # i) 失効の前の読みは成功し、DELETE の後の読みだけ通信の失敗 → 1・控えは残す
  mkcache
  if FAKE_NO_REVOKE=1 FAKE_NET_AFTER_DELETE=1 rv > /dev/null; then r=NG; fi
  [ -f "$C/token" ] && [ -f "$C/token-readonly" ] || r=NG
  grep -q '^rw-1 api -X DELETE' "$A" || r=NG
  echo "G9 $r"
  fi
}

copy_scripts() {  # copy_scripts <先>（scripts/claude/*.sh と gh-app/ の写し）
  mkdir -p "$1/gh-app"
  cp "$REPO_ROOT/scripts/claude/gh-app/gh-app-token" "$REPO_ROOT/scripts/claude/gh-app/gh" "$REPO_ROOT/scripts/claude/gh-app/revoke.sh" "$1/gh-app/" 2>/dev/null
  cp "$REPO_ROOT"/scripts/claude/*.sh "$1/" 2>/dev/null
  # git は実行権を記録しない（core.filemode=false の端末から入る）ので、CI と同じく実行権なしの写しで確かめる（I223 fix-loop）
  chmod 644 "$1"/gh-app/* "$1"/*.sh 2>/dev/null
}

# ---- 本物（リポジトリの版）----
copy_scripts "$T/real"
res=$(run_cases "$T/real")
for g in G1 G2 G3 G4 G5 G6 G7 G8 G9; do
  ck "$g リポジトリの版で合格" "$g OK" "$(grep "^$g " <<< "$res")"
done
g10_out=$(g10 "$REPO_ROOT"); g10_rc=$?
[ "$g10_rc" = 0 ] || printf '%s\n' "$g10_out"
ck "G10 決まりの置き場に鍵を出す auth status の書き方が無い" 0 "$g10_rc"

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
fg G7 "code-review.sh の --strict-mcp-config を消す" code-review.sh 's/ --strict-mcp-config//'
fg G7 "tmux で起こす tui-capture.sh の --strict-mcp-config を消す" tui-capture.sh 's/ --strict-mcp-config//'
# shellcheck disable=SC2016  # sed の式なので $ をそのまま渡す
fg G8 "入口の置き換えの分岐を消す" gh-app/gh 's/if \[ "\${1:-}" = auth \] && \[ "\${2:-}" = status \]; then/if false; then/'
fg G8 "state の判定を消す（いつも 0）" gh-app/gh 's/sys.exit(0 if ok and n else 1)/sys.exit(0)/'
fg G8 "アカウントの数の確かめを消す（ログインなしで 0）" gh-app/gh 's/sys.exit(0 if ok and n else 1)/sys.exit(0 if ok else 1)/'
fg G9 "控えの名前の一覧から token-readonly を消す" gh-app/revoke.sh 's/for name in token token-readonly; do/for name in token; do/'
# shellcheck disable=SC2016  # sed の式なので $ をそのまま渡す
fg G9 "401 の確かめを消す（失敗なら無効とみなす）" gh-app/revoke.sh 's/\[\[ "\$out" == \*"HTTP 401"\* \]\]/[ -n "$out" ]/'
# shellcheck disable=SC2016  # sed の式なので $ をそのまま渡す
fg G9 "--stdin で読んだ値を使わず控えの鍵を使う" gh-app/revoke.sh 's/revoke_one "\$leaked"; rc=\$?/revoke_one "$(cut -d" " -f2 "$CACHE_DIR\/token")"; rc=$?/'
# shellcheck disable=SC2016  # sed の式なので $ をそのまま渡す
fg G9 "失効の前の確かめを消す（もともと無効でも失効を確認と出す）" gh-app/revoke.sh 's/case \$? in 0) ;; 1) return 3 ;; \*) return 1 ;; esac/:/'

# G10 の FG: 一時フォルダの手順書に鍵を出す書き方を書くと不合格、--json の形だけなら合格
g10_fg() {  # g10_fg <説明> <期待の終了コード> <手順書の 1 行>
  local d="$T/g10.$RANDOM"
  mkdir -p "$d/docs/runbooks"
  printf '%s\n' "$3" > "$d/docs/runbooks/x.md"
  g10 "$d" > /dev/null; ck "FG G10 $1" "$2" "$?"
}
# shellcheck disable=SC2016  # バッククォートは手順書の文字そのもの
g10_fg "--json なしは不合格" 1 '確かめる: `gh auth status`'
# shellcheck disable=SC2016
g10_fg "--json に -t を足すと不合格" 1 '確かめる: `gh auth status --json hosts -t`'
# shellcheck disable=SC2016
g10_fg "本物の gh を直接呼ぶ形も不合格" 1 '確かめる: `/usr/bin/gh auth status -a`'
# shellcheck disable=SC2016
g10_fg "--json の形だけなら合格" 0 '確かめる: `gh auth status --json hosts --jq '"'"'.hosts[][] | .login'"'"'`'
# I226（F6）: 鍵を丸ごと出す auth token は不合格。行末の \ で分けた --json 付きの書き方は合格
# shellcheck disable=SC2016
g10_fg "auth token は不合格" 1 '鍵を見る: `gh auth token`'
g10_fg "行末の \\ で分けた --json は合格" 0 "$(printf 'gh auth status \\\n  --json hosts')"
# I212（I226 の台帳 F1）: Python の \b は和文も語の文字に数えるので、和文がすぐ続く書き方を取りこぼさない
g10_fg "和文がすぐ続く auth token は不合格" 1 'gh auth tokenを打つ'

echo "---"
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
