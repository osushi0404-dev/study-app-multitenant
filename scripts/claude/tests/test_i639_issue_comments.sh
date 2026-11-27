#!/usr/bin/env bash
# shellcheck disable=SC2317,SC2016  # 場面の関数は "$s" "$SRC"・fg から間接に呼ぶ／sed の式・本文の $・バッククォートは文字そのもの
# I639: scripts/claude/issue-source.sh がイシューのコメントを本文の後ろに付ける・立場で絞る・raw-body が本文だけを出すことを
# 決定論で確かめる（docs/tests/open/I639_auto_test.md の TC-01〜TC-03）。
# gh は PATH の先頭に置いた仮のコマンド（呼ばれた引数を記録し、決めた JSON と終了コードを返す）。
# 守るもの（気づきにくく被害が大きい）: 外の人・隠されたコメントの中身が計画の入力に入る／コメントの見出しが写しの節に混ざる／
# grill-me の書き戻しにコメント・写しの見出しが入る／コメントが無いときの出力が変わる。
# 実行: bash scripts/claude/tests/test_i639_issue_comments.sh（0=全 PASS / 1=FAIL あり）
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SRC="$REPO_ROOT/scripts/claude/issue-source.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fail=0
ok()  { printf 'PASS %s\n' "$1"; }
ng()  { printf 'FAIL %s\n' "$1" >&2; fail=1; }
res() { if [ "$2" -eq 0 ]; then ok "$1"; else ng "$1"; fi; }

# --- 仮の gh ---
mkdir -p "$TMP/bin"
cat > "$TMP/bin/gh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$GH_CALLS"
[ "${GH_RC:-0}" -eq 0 ] || exit "$GH_RC"
cat "$GH_JSON"
EOF
chmod +x "$TMP/bin/gh"
export PATH="$TMP/bin:$PATH"
export GH_CALLS="$TMP/calls" GH_JSON="$TMP/gh.json"
calls() { if [ -f "$GH_CALLS" ]; then wc -l < "$GH_CALLS" | tr -d ' '; else echo 0; fi; }

# gh_json <url> <title> <body のファイル> <comments の JSON（文字列。"-" なら項目なし）>
gh_json() {
  python3 -I -c 'import json, sys
d = {"url": sys.argv[1], "title": sys.argv[2], "body": open(sys.argv[3], encoding="utf-8", newline="").read()}
if sys.argv[4] != "-":
    d["comments"] = json.loads(sys.argv[4])
json.dump(d, sys.stdout, ensure_ascii=False)' "$1" "$2" "$3" "$4" > "$GH_JSON"
}
new_repo() { rm -rf "$1"; mkdir -p "$1"; git -C "$1" init -q; }
rc2() { (cd "$1" && bash "${@:2}" >/dev/null 2>&1); [ $? -eq 2 ]; }

printf '## 関連資料\n- $(echo pwned) と `uname`\n\n## 影響範囲（想定）\n- なし' > "$TMP/body.md"
C2='[{"author":{"login":"alice"},"authorAssociation":"OWNER","body":"1 行目\n\n3 行目","createdAt":"2026-11-01T00:00:00Z","isMinimized":false,"minimizedReason":""},
     {"author":{"login":"bob"},"authorAssociation":"CONTRIBUTOR","body":"x","createdAt":"2026-11-02T00:00:00Z","isMinimized":false,"minimizedReason":""}]'
# S1 の期待（読んだ時点の日時は @NOW@ に置き換えて比べる）
{
  cat "$TMP/body.md"
  printf '\n\n## GitHub のコメント（2 件・読んだ時点 @NOW@・同期しない）\n\n'
  printf '### 2026-11-01T00:00:00Z @alice（OWNER）\n\n> 1 行目\n>\n> 3 行目\n\n'
  printf '### 2026-11-02T00:00:00Z @bob（CONTRIBUTOR）\n\n> x\n'
} > "$TMP/s1_expect"
now_mask() { sed -E 's/読んだ時点 [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2} UTC/読んだ時点 @NOW@/'; }

# ---- 各場面: $1 = 使うスクリプト。合格なら 0 ----
s1() {
  local r="$TMP/r1"; new_repo "$r"; rm -f "$GH_CALLS"
  gh_json "https://github.com/o/r/issues/500" "x" "$TMP/body.md" "$C2"
  (cd "$r" && bash "$1" body I500) | now_mask > "$TMP/s1_out" || return 1
  cmp -s "$TMP/s1_out" "$TMP/s1_expect"
}
s2() {
  local r="$TMP/r2" c
  for c in '[]' '-'; do
    new_repo "$r"
    gh_json "https://github.com/o/r/issues/501" "x" "$TMP/body.md" "$c"
    (cd "$r" && bash "$1" body I501) > "$TMP/s2_out" || return 1
    cmp -s "$TMP/s2_out" "$TMP/body.md" || return 1
    (cd "$r" && bash "$1" snapshot I501 >/dev/null) || return 1
    tail -n +6 "$r/docs/issues/open/I501.md" > "$TMP/s2_snap"
    cmp -s "$TMP/s2_snap" "$TMP/body.md" || return 1
  done
}
s3() {
  local r="$TMP/r3" f; new_repo "$r"
  gh_json "https://github.com/o/r/issues/502" "題" "$TMP/body.md" "$C2"
  (cd "$r" && bash "$1" snapshot I502 >/dev/null) || return 1
  f="$r/docs/issues/open/I502.md"
  [ "$(head -n 1 "$f")" = '# I502: 題' ] || return 1
  sed -n 3p "$f" | grep -q '^> GitHub #502 の本文の写し（' || return 1
  grep -qxF '> - GitHub Issue: #502' "$f" || return 1
  tail -n +6 "$f" | now_mask > "$TMP/s3_out"
  cmp -s "$TMP/s3_out" "$TMP/s1_expect"
}
s4() {
  local r="$TMP/r4" f; new_repo "$r"
  # 本文の設計確認メモにあるパスを、本文の節には書かず、コメントの中の「## 影響範囲（想定）」にだけ書く
  printf '## 設計確認メモ（/grill-me）\n- Q: a → A: `scripts/claude/x.sh` を直す\n\n## 実装対象（既知のもの）\n- なし\n\n## 影響範囲（想定）\n- なし' > "$TMP/s4_body.md"
  gh_json "https://github.com/o/r/issues/503" "x" "$TMP/s4_body.md" \
    '[{"author":{"login":"alice"},"authorAssociation":"OWNER","body":"## 受け入れ条件\n- [ ] 偽\n## 影響範囲（想定）\n- `scripts/claude/x.sh`","createdAt":"2026-11-01T00:00:00Z","isMinimized":false}]'
  (cd "$r" && bash "$1" snapshot I503 >/dev/null) || return 1
  f="$r/docs/issues/open/I503.md"
  [ "$(grep -c '^## 受け入れ条件' "$f")" -eq 0 ] || return 1
  # 本物の節の切り出し: コメントのパスが本文の節に数えられなければ「メモにあって本文に無い」で exit 1
  (cd "$REPO_ROOT" && bash scripts/claude/check-memo-body-paths.sh --file "$f" >/dev/null 2>&1)
  [ $? -eq 1 ]
}
s5() {
  local r="$TMP/r5"; new_repo "$r"
  printf '## 関連資料\r\n- a\r\n' > "$TMP/crlf.md"
  gh_json "https://github.com/o/r/issues/504" "x" "$TMP/crlf.md" \
    '[{"author":{"login":"alice"},"authorAssociation":"OWNER","body":"a\r\nb","createdAt":"t","isMinimized":false}]'
  (cd "$r" && bash "$1" body I504) > "$TMP/s5_out" || return 1
  grep -qF '> b' "$TMP/s5_out" && ! grep -q $'\r' "$TMP/s5_out"
}
s6() {
  local r="$TMP/r6"; new_repo "$r"; rm -f "$GH_CALLS"; mkdir -p "$r/docs/issues/open"
  printf '# I123: x\nbody\n' > "$r/docs/issues/open/I123.md"
  [ "$(cd "$r" && bash "$1" body I123)" = "$(cat "$r/docs/issues/open/I123.md")" ] && [ "$(calls)" -eq 0 ]
}
s7() {
  local r="$TMP/r7" out; new_repo "$r"
  gh_json "https://github.com/o/r/issues/505" "x" "$TMP/body.md" \
    '[{"author":{"login":"eve"},"authorAssociation":"NONE","body":"SECRET-NONE","createdAt":"t1","isMinimized":false},
      {"author":{"login":"fay"},"authorAssociation":"FIRST_TIME_CONTRIBUTOR","body":"SECRET-FTC","createdAt":"t2","isMinimized":false},
      {"author":{"login":"alice"},"authorAssociation":"OWNER","body":"SECRET-MIN","createdAt":"t3","isMinimized":true,"minimizedReason":"SPAM"}]'
  (cd "$r" && bash "$1" snapshot I505 >/dev/null) || return 1
  (cd "$r" && bash "$1" body I505) > "$TMP/s7_body" || return 1
  for out in "$TMP/s7_body" "$r/docs/issues/open/I505.md"; do
    ! grep -q 'SECRET-' "$out" || return 1
    grep -qxF '### t1 @eve（NONE）' "$out" || return 1
    grep -qxF '### t2 @fay（FIRST_TIME_CONTRIBUTOR）' "$out" || return 1
    grep -qxF '> （中身は出さない: 立場が NONE の人のコメント。要るならユーザーに確かめる）' "$out" || return 1
    grep -qxF '> （中身は出さない: 隠されたコメント（SPAM））' "$out" || return 1
  done
}
s8() {
  local r="$TMP/r8"; new_repo "$r"
  gh_json "https://github.com/o/r/issues/506" "x" "$TMP/body.md" \
    '[{"author":null,"authorAssociation":"OWNER","body":"y","createdAt":"t","isMinimized":false}]'
  (cd "$r" && bash "$1" body I506) | grep -qxF '### t @ghost（OWNER）'
}
s9() {
  local r="$TMP/r9"; new_repo "$r"
  gh_json "https://github.com/o/r/issues/507" "x" "$TMP/body.md" "$C2"
  (cd "$r" && bash "$1" raw-body I507) > "$TMP/s9_out" || return 1
  cmp -s "$TMP/s9_out" "$TMP/body.md"
}
s10() {
  local r="$TMP/r10"; new_repo "$r"
  gh_json "https://github.com/o/r/issues/508" "x" "$TMP/body.md" "$C2"
  (cd "$r" && bash "$1" snapshot I508 >/dev/null) || return 1
  rm -f "$GH_CALLS"
  (cd "$r" && bash "$1" raw-body I508) > "$TMP/s10_out" || return 1
  cmp -s "$TMP/s10_out" "$TMP/body.md" && [ "$(calls)" -eq 1 ]
}
s10b() {
  local r="$TMP/r10b" f; new_repo "$r"
  gh_json "https://github.com/o/r/issues/509" "x" "$TMP/body.md" "$C2"
  (cd "$r" && bash "$1" snapshot I509 >/dev/null) || return 1
  f="$r/docs/issues/open/I509.md"
  sed -i '3s/.*/> 人が直した注記/' "$f"
  rm -f "$GH_CALLS"
  [ "$(cd "$r" && bash "$1" raw-body I509)" = "$(cat "$f")" ] && [ "$(calls)" -eq 0 ]
}
s11() {
  local r="$TMP/r11"; new_repo "$r"; rm -f "$GH_CALLS"; mkdir -p "$r/docs/issues/open"
  printf '# I123: x\nbody\n' > "$r/docs/issues/open/I123.md"
  [ "$(cd "$r" && bash "$1" raw-body I123)" = "$(cat "$r/docs/issues/open/I123.md")" ] && [ "$(calls)" -eq 0 ]
}
s12() {
  local r="$TMP/r12"; new_repo "$r"
  gh_json "https://github.com/o/r/pull/510" "x" "$TMP/body.md" "$C2"
  rc2 "$r" "$1" raw-body I510 || return 1
  gh_json "https://github.com/o/r/issues/511" "I229: 今の流れ" "$TMP/body.md" "$C2"
  rc2 "$r" "$1" raw-body I511 || return 1
  rc2 "$r" "$1" raw-body I123
}

for s in s1 s2 s3 s4 s5 s6 s7 s8 s9 s10 s10b s11 s12; do
  "$s" "$SRC"; res "TC-0x ${s^^}" $?
done

# ---- 失敗の注入: 壊した写しでは、その場面が NG になること ----
fg() { # $1=名前 $2=場面 $3=sed 式
  local broken="$TMP/fg_$1.sh"
  sed -e "$3" "$SRC" > "$broken"
  if cmp -s "$broken" "$SRC"; then ng "FG-$1（sed が当たらない）"; return; fi
  if "$2" "$broken" >/dev/null 2>&1; then ng "FG-$1（壊しても合格した）"; else ok "FG-$1"; fi
}
fg S4   s4   's/("> " + line) if line else ">"/line/'
fg S7   s7   's/^        elif assoc not in trusted:$/        elif False:/'
fg S7b  s7   's/^        if c.get("isMinimized"):$/        if False:/'
fg S2   s2   's/^if mode == "body" and comments:$/if mode == "body":/'
fg S10  s10  's/^is_snapshot() {.*/is_snapshot() { return 1; }/'
fg S5   s5   's/^def lf(s):.*/def lf(s): return s/'

exit "$fail"
