#!/usr/bin/env bash
# shellcheck disable=SC2317,SC2016,SC2181  # 場面の関数は "$s" "$SRC"・fg から間接に呼ぶ／本文・下書き・sed の式の $・バッククォートは文字そのもの／終了コード 2 などを見分けるため $? を読む
# I221: scripts/claude/issue-source.sh（イシュー本文の置き場所の判断）と
# check-memo-body-paths.sh --file を決定論で確かめる（docs/tests/open/I221_auto_test.md の TC-01）。
# gh は PATH の先頭に置いた仮のコマンド（呼ばれた引数を記録し、決めた JSON と終了コードを返す）。
# 守るもの（気づきにくく被害が大きい）: 既存番号で GitHub の別のイシューを読む・PR の番号を写す・
# 今までの流れのイシューを新しい形で写す・本文が写しで壊れる・失敗で半端な写しが残る・基準のフォルダ。
# 実行: bash scripts/claude/tests/test_i221_issue_source.sh（0=全 PASS / 1=FAIL あり）
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SRC="$REPO_ROOT/scripts/claude/issue-source.sh"
MEMO="$REPO_ROOT/scripts/claude/check-memo-body-paths.sh"
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

# gh_returns <url> <title> <body のファイル>
gh_returns() {
  python3 -I -c 'import json, sys
json.dump({"url": sys.argv[1], "title": sys.argv[2], "body": open(sys.argv[3], encoding="utf-8").read()}, sys.stdout, ensure_ascii=False)' "$1" "$2" "$3" > "$GH_JSON"
}
calls() { if [ -f "$GH_CALLS" ]; then wc -l < "$GH_CALLS" | tr -d ' '; else echo 0; fi; }

# new_repo <dir>: 空の git リポジトリ
new_repo() { mkdir -p "$1"; git -C "$1" init -q; }
# rc2 <dir> <スクリプト> <引数...>: <dir> をカレントにして流し、終了コードが 2 なら合格（0）
rc2() { (cd "$1" && bash "${@:2}" >/dev/null 2>&1); [ $? -eq 2 ]; }

# 本文（シェルに通すと壊れる文字・末尾の改行なし）
printf '## 関連資料\n- $(echo pwned) と `uname` と "引用"\n\n**背景**: x\n**目的**: y' > "$TMP/body.md"

# ---- 各場面: $1 = 使うスクリプト（FG では壊した写し）。合格なら 0 ----
s1() {
  local r="$TMP/s1"; rm -rf "$r" "$GH_CALLS"; new_repo "$r"; mkdir -p "$r/docs/issues/open"
  printf '# I123: x\nbody\n' > "$r/docs/issues/open/I123.md"
  local a b c
  a="$(cd "$r" && bash "$1" snapshot I123)" || return 1
  b="$(cd "$r" && bash "$1" path I123)" || return 1
  c="$(cd "$r" && bash "$1" body I123)" || return 1
  [ "$a" = "docs/issues/open/I123.md" ] && [ "$b" = "$a" ] && [ "$c" = "$(cat "$r/docs/issues/open/I123.md")" ] && [ "$(calls)" -eq 0 ]
}
s1b() {
  local r="$TMP/s1b"; rm -rf "$r"; new_repo "$r"; mkdir -p "$r/docs/issues/closed"
  printf 'x\n' > "$r/docs/issues/closed/I124.md"
  [ "$(cd "$r" && bash "$1" path I124)" = "docs/issues/closed/I124.md" ]
}
s2() {
  local r="$TMP/s2"; rm -rf "$r" "$GH_CALLS"; new_repo "$r"
  gh_returns "https://github.com/o/r/issues/123" "古い別のイシュー" "$TMP/body.md"
  local sub
  for sub in body snapshot gh-number; do
    rc2 "$r" "$1" "$sub" I123 || return 1
  done
  [ "$(calls)" -eq 0 ] && [ ! -e "$r/docs/issues/open/I123.md" ]
}
s3() {
  local r="$TMP/s3"; rm -rf "$r" "$GH_CALLS"; new_repo "$r"
  gh_returns "https://github.com/o/r/issues/427" '題 "x"' "$TMP/body.md"
  local out f
  out="$(cd "$r" && bash "$1" snapshot I427)" || return 1
  f="$r/docs/issues/open/I427.md"
  [ "$out" = "docs/issues/open/I427.md" ] || return 1
  [ "$(head -n 1 "$f")" = '# I427: 題 "x"' ] || return 1
  grep -qxF '> - GitHub Issue: #427' "$f" || return 1
  # 写しの本文 = 5 行目以降（題名・空行・2 行の注記・空行の後）
  tail -n +6 "$f" > "$TMP/s3_body"
  cmp -s "$TMP/s3_body" "$TMP/body.md" || return 1
  [ "$(calls)" -eq 1 ]
}
s4() {
  local r="$TMP/s4"; rm -rf "$r" "$GH_CALLS"; new_repo "$r"
  gh_returns "https://github.com/o/r/pull/428" "feat: I221 なにか" "$TMP/body.md"
  rc2 "$r" "$1" snapshot I428 || return 1
  [ ! -e "$r/docs/issues/open/I428.md" ]
}
s5() {
  local r="$TMP/s3" before
  s3 "$1" || return 1   # s3 の状態を自分で作る（実行順に頼らない）
  before="$(cat "$r/docs/issues/open/I427.md")"
  rm -f "$GH_CALLS"
  printf 'ちがう本文' > "$TMP/body2.md"; gh_returns "https://github.com/o/r/issues/427" "別" "$TMP/body2.md"
  [ "$(cd "$r" && bash "$1" snapshot I427)" = "docs/issues/open/I427.md" ] || return 1
  [ "$(cat "$r/docs/issues/open/I427.md")" = "$before" ] && [ "$(calls)" -eq 0 ]
}
s6() {
  local r="$TMP/s6"; rm -rf "$r" "$GH_CALLS"; new_repo "$r"; mkdir -p "$r/docs/issues/open"
  printf '## 関連資料\n- GitHub Issue: #402\n- 別: GitHub Issue: #999\n' > "$r/docs/issues/open/I222.md"
  printf '## 関連資料\n- なし\n' > "$r/docs/issues/open/I125.md"
  [ "$(cd "$r" && bash "$1" gh-number I222)" = "402" ] || return 1
  [ "$(cd "$r" && bash "$1" gh-number I430)" = "430" ] || return 1
  rc2 "$r" "$1" gh-number I125 || return 1
  [ "$(calls)" -eq 0 ]
}
s7() {
  local r="$TMP/s7" a; rm -rf "$r"; new_repo "$r"
  for a in I12 I427x ../I427 "" X427; do
    rc2 "$r" "$1" snapshot "$a" || return 1
  done
  [ ! -d "$r/docs" ]
}
s8() {
  local r="$TMP/s8"; rm -rf "$r"; new_repo "$r"; mkdir -p "$r/docs/issues/open"
  gh_returns "https://github.com/o/r/issues/431" "x" "$TMP/body.md"
  GH_RC=1 rc2 "$r" "$1" snapshot I431 || return 1
  [ -z "$(ls -A "$r/docs/issues/open")" ]
}
s10() {
  local a="$TMP/s10a" b="$TMP/s10b"; rm -rf "$a" "$b"; new_repo "$a"; new_repo "$b"
  mkdir -p "$a/scripts/claude"; cp "$1" "$a/scripts/claude/issue-source.sh"
  gh_returns "https://github.com/o/r/issues/432" "x" "$TMP/body.md"
  (cd "$b" && bash "$a/scripts/claude/issue-source.sh" snapshot I432 >/dev/null) || return 1
  [ -f "$b/docs/issues/open/I432.md" ] && [ ! -e "$a/docs/issues/open/I432.md" ]
}
s11() {
  local r="$TMP/s11"; rm -rf "$r"; new_repo "$r"
  gh_returns "https://github.com/o/r/issues/433" "I229: 今の流れで起票したイシュー" "$TMP/body.md"
  local sub
  for sub in snapshot body; do
    rc2 "$r" "$1" "$sub" I433 || return 1
  done
  [ ! -e "$r/docs/issues/open/I433.md" ]
}

for s in s1 s1b s2 s3 s4 s5 s6 s7 s8 s10 s11; do
  "$s" "$SRC"; res "TC-01 ${s^^}" $?
done

# S9: check-memo-body-paths.sh --file
mk_draft() { printf '## 関連資料\n- x\n\n## 設計確認メモ（/grill-me）\n- Q: a → A: `scripts/claude/foo.sh` を直す\n\n## 実装対象（既知のもの）\n| ファイル | 変更内容 |\n|---|---|\n| %s | x |\n\n## 影響範囲（想定）\n- なし\n' "$2" > "$1"; }
mk_draft "$TMP/d_ng.md" '`scripts/claude/bar.sh`'
mk_draft "$TMP/d_ok.md" '`scripts/claude/foo.sh`'
s9rc=0
(cd "$REPO_ROOT" && bash "$MEMO" --file "$TMP/d_ng.md" >/dev/null 2>&1); [ $? -eq 1 ] || s9rc=1
(cd "$REPO_ROOT" && bash "$MEMO" --file "$TMP/d_ok.md" >/dev/null 2>&1); [ $? -eq 0 ] || s9rc=1
(cd "$REPO_ROOT" && bash "$MEMO" --file "$TMP/none.md" >/dev/null 2>&1); [ $? -eq 2 ] || s9rc=1
# I### のときは issue-source.sh path で探す（手元にある I221 は見つかる＝2 以外）
(cd "$REPO_ROOT" && bash "$MEMO" I221 >/dev/null 2>&1); [ $? -ne 2 ] || s9rc=1
res "TC-01 S9 check-memo-body-paths --file" "$s9rc"

# ---- 失敗の注入: 壊した写しでは、その場面が NG になること ----
fg() { # $1=名前 $2=場面 $3=sed 式
  local broken="$TMP/fg_$1.sh"
  sed -e "$3" "$SRC" > "$broken"
  if cmp -s "$broken" "$SRC"; then ng "FG-$1（sed が当たらない）"; return; fi
  if "$2" "$broken" >/dev/null 2>&1; then ng "FG-$1（壊しても合格した）"; else ok "FG-$1"; fi
}
fg S2  s2  's/^NEW_ISSUE_MIN=427$/NEW_ISSUE_MIN=0/'
fg S4  s4  's|^  \[\[ "\$url" =~ .*$|  true|'
fg S3  s3  's/^      field body$/      echo "$(field body)"/'
fg S11 s11 's/^  \[\[ "\$TITLE" =~ .*$/  false \\/'

exit "$fail"
