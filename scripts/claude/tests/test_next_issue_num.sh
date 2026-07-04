#!/usr/bin/env bash
# I098: next-issue-num.sh（全 worktree 横断採番）を決定論検証する（docker/pytest 非依存）。
# 実行: bash scripts/claude/tests/test_next_issue_num.sh
#
# 隔離方針: temp の bare origin + primary clone + linked worktree を作り、docs/issues を作り込んで
# next-issue-num.sh の出力を検証する（read-only スクリプトなので実 worktree を汚さない）。
# TC-N1..N7 はスクリプト挙動、TC-DOC1..4 は実リポジトリの記述整合。0=全 PASS / 1=FAIL あり。
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SCRIPT="$REPO_ROOT/scripts/claude/next-issue-num.sh"
ISSUE_FLOW="$REPO_ROOT/docs/runbooks/issue-flow.md"
SKILL="$REPO_ROOT/.claude/skills/issue-bootstrap/SKILL.md"
WORKTREE_MD="$REPO_ROOT/docs/runbooks/worktree.md"

ALL_TMP=()
cleanup() { local d; for d in "${ALL_TMP[@]:-}"; do [ -n "$d" ] && rm -rf "$d"; done; }
trap cleanup EXIT

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
ckt() { local name="$1"; shift
        if "$@"; then printf 'PASS %s\n' "$name"; pass=$((pass+1));
        else printf 'FAIL %s\n' "$name"; fail=$((fail+1)); fi; }
cklt() { if [ "$2" -lt "$3" ]; then printf 'PASS %s (%s < %s)\n' "$1" "$2" "$3"; pass=$((pass+1));
         else printf 'FAIL %s (%s !< %s)\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
cknt() { local name="$1"; shift   # 与コマンドが「失敗（非0）」なら PASS（不在・否定の検証用）
         if "$@"; then printf 'FAIL %s (unexpected success)\n' "$name"; fail=$((fail+1));
         else printf 'PASS %s\n' "$name"; pass=$((pass+1)); fi; }
is3() { printf '%s' "$1" | grep -qE '^[0-9]{3}$'; }   # 3 桁のみの 1 行か

# 隔離環境（globals: TMP PRIMARY）。linked worktree は必要な TC 内で足す。
new_env() {
  local SRC ORIGIN
  TMP="$(mktemp -d)"; ALL_TMP+=("$TMP")
  SRC="$TMP/src"
  git init -q -b main "$SRC"
  git -C "$SRC" config user.email t@example.com
  git -C "$SRC" config user.name tester
  mkdir -p "$SRC/docs/issues/open" "$SRC/docs/issues/closed" "$SRC/docs/issues/templates"
  printf 'template\n' > "$SRC/docs/issues/templates/issue_template.md"
  git -C "$SRC" add -A; git -C "$SRC" commit -qm init
  git -C "$SRC" checkout -q -b develop
  ORIGIN="$TMP/origin.git"; git clone -q --bare "$SRC" "$ORIGIN"
  PRIMARY="$TMP/primary"; git clone -q "$ORIGIN" "$PRIMARY"
  git -C "$PRIMARY" config user.email t@example.com
  git -C "$PRIMARY" config user.name tester
  git -C "$PRIMARY" checkout -q develop
}
add_wt() { git -C "$PRIMARY" worktree add -q "$TMP/$1" -b "$2" develop >/dev/null 2>&1; }
run() { ( cd "$1" && bash "$SCRIPT" ); }                 # $1=実行dir → stdout に番号
mkissue() { mkdir -p "$(dirname "$1")"; printf '%s\n' "${2:-x}" > "$1"; }  # $1=path $2=content

# ===================== TC-N1: 再現ケース（横断で他 worktree の高番号 untracked を拾う） =====================
new_env; add_wt wt-b feature/b
mkissue "$PRIMARY/docs/issues/open/I050.md"          # primary 側 untracked（高）
mkissue "$TMP/wt-b/docs/issues/open/I030.md"         # linked 側 untracked（低）
ck "N1 primaryから=051"  051 "$(run "$PRIMARY")"
ck "N1 linkedから=051"   051 "$(run "$TMP/wt-b")"

# ===================== TC-N2: git 履歴最大（削除済みも使用済み扱い） =====================
new_env
mkissue "$PRIMARY/docs/issues/open/I060.md"; git -C "$PRIMARY" add -A; git -C "$PRIMARY" commit -qm addI060
git -C "$PRIMARY" rm -q docs/issues/open/I060.md; git -C "$PRIMARY" commit -qm delI060
mkissue "$PRIMARY/docs/issues/open/I040.md"          # FS 最大は 040、履歴最大は 060
ck "N2 削除済み履歴=061"  061 "$(run "$PRIMARY")"

# ===================== TC-N3: I094 decoy（部分一致）を誤カウントしない =====================
new_env
mkissue "$PRIMARY/docs/issues/open/I040.md"
mkissue "$PRIMARY/docs/issues/open/draft-I200.md"
mkissue "$PRIMARY/docs/issues/open/I055-backup.md"
mkissue "$PRIMARY/docs/issues/open/plan_I010_2.md"   # + templates/issue_template.md（new_env で作成済）
ck "N3 decoy無視=041"  041 "$(run "$PRIMARY")"

# ===================== TC-N4: subject 誤マッチを拾わない（file-path 抽出） =====================
new_env
mkissue "$PRIMARY/docs/issues/open/I040.md"
printf 'note\n' > "$PRIMARY/docs/note.txt"           # docs/issues 外のファイル
git -C "$PRIMARY" add -A; git -C "$PRIMARY" commit -qm "work refs I900 in message"
ck "N4 subject無視=041"  041 "$(run "$PRIMARY")"

# ===================== TC-N5: 出力契約（3 桁 1 行のみ・rc0） =====================
new_env; mkissue "$PRIMARY/docs/issues/open/I040.md"
OUT="$(run "$PRIMARY")"; RC=$?
ck  "N5 rc0"          0 "$RC"
ckt "N5 3桁1行のみ"   is3 "$OUT"

# ===================== TC-N6: CWD 非依存（回帰）＋ 相対 pathspec 反証 =====================
new_env
mkissue "$PRIMARY/docs/issues/open/I060.md"; git -C "$PRIMARY" add -A; git -C "$PRIMARY" commit -qm addI060
git -C "$PRIMARY" rm -q docs/issues/open/I060.md; git -C "$PRIMARY" commit -qm delI060
mkissue "$PRIMARY/docs/issues/open/I040.md"          # FS=040, 履歴=060 → 061
ck "N6 rootから=061"    061 "$(run "$PRIMARY")"
ck "N6 subdirから=061"  061 "$(run "$PRIMARY/docs")"   # :/ 固定なら subdir でも履歴を落とさない
# 反証: pathspec を相対に差し替えた複製を subdir 実行 → 履歴脱落で低い値（041）＝:/ が停止要因
REL="$TMP/next-rel.sh"; sed "s#:/docs/issues#docs/issues#" "$SCRIPT" > "$REL"
ck "N6反証 相対はsubdirで履歴脱落=041" 041 "$( cd "$PRIMARY/docs" && bash "$REL" )"

# ===================== TC-N7: 横断スキャンの false-green 反証 =====================
new_env; add_wt wt-b feature/b
mkissue "$PRIMARY/docs/issues/open/I020.md"; git -C "$PRIMARY" add -A; git -C "$PRIMARY" commit -qm addI020
mkissue "$TMP/wt-b/docs/issues/open/I080.md"         # linked 側 untracked（高・履歴に無い）
ck "N7 本体=081"  081 "$(run "$PRIMARY")"
# FS 走査を無効化した複製 → 横断 untracked を無視して低い値（履歴 020 → 021）
BROKEN="$TMP/next-nofs.sh"
# shellcheck disable=SC2016  # 単一引用は意図的（$wt を展開せず sed パターンに渡す）
sed 's#find "$wt/docs/issues"#find /nonexistent-xyz#' "$SCRIPT" > "$BROKEN"
BR="$( cd "$PRIMARY" && bash "$BROKEN" )"
cklt "N7反証 FS無効化は横断を落とす" "$BR" 081

# ===================== TC-DOC: 実リポジトリの記述整合（steps 3-5 後に PASS） =====================
# 旧採番 bash の検出は変数宣言 `FS_MAX=` / `GIT_MAX=` を指標にする（consumer 3ファイルに実行 bash が
# 残っていないこと。plan/test の説明的言及は対象外）。next-issue-num.sh への一元化を確認する。
ckt  "DOC1a issue-flow に next-issue-num 3箇所以上" test "$(grep -c 'next-issue-num.sh' "$ISSUE_FLOW")" -ge 3
cknt "DOC1b issue-flow 旧採番bash(FS_MAX=) 0件"  grep -q 'FS_MAX=' "$ISSUE_FLOW"
ckt  "DOC2a SKILL に next-issue-num 出現"        grep -q 'next-issue-num.sh' "$SKILL"
cknt "DOC2b SKILL 旧採番bash(FS_MAX=) 0件"       grep -q 'FS_MAX=' "$SKILL"
ckt  "DOC3a worktree §8 に next-issue-num"       grep -q 'next-issue-num.sh' "$WORKTREE_MD"
ckt  "DOC3b worktree §8 に「権威」"               grep -q '権威' "$WORKTREE_MD"
cknt "DOC3c worktree §8 旧人手規律（develop へ取り込む）除去" grep -q 'すみやかに develop へ取り込' "$WORKTREE_MD"
cknt "DOC4 consumer に旧 FS_MAX bash 0件"        grep -q 'FS_MAX=' "$ISSUE_FLOW" "$SKILL" "$WORKTREE_MD"
cknt "DOC4b consumer に旧 GIT_MAX bash 0件"      grep -q 'GIT_MAX=' "$ISSUE_FLOW" "$SKILL" "$WORKTREE_MD"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
