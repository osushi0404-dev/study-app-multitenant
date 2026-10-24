#!/usr/bin/env bash
# I193（plan_I193.md §5・auto_test TC-01）: 公式の道具を土台にした流れの決定論テスト。
#   R: 名前と置き場所（組み込みを隠さない・段階のスキル・レビュー役の読み取り専用・timeout）
#   F: flow-stage.sh の挙動（一時フォルダの記録で実行）
#   G: gate-check.sh の挙動（一時の git リポジトリで実行）
#   C: code-review.sh の関数の挙動（CI 待ち・REVIEWED_COMMIT・組み込みの出力の扱い）
#   S: スキルの中身（守りの文が消えたら落ちる）
#   D: 文書
# 否定・不在の判定には FG（一時コピーを壊すと不合格になること）を付ける。
# 実行: bash scripts/claude/tests/test_i193_official_flow.sh
# shellcheck disable=SC2016  # 単一引用符内の $・バッククォートは文書・正規表現の文字どおりの照合用（展開させない意図）
# shellcheck disable=SC1091  # code-review.sh は関数だけを読み込む（REVIEW_LIB_SOURCE_ONLY=1）。実行時に存在を確かめている
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
rc() { "$@" >/dev/null 2>&1; echo $?; }   # コマンドの終了コードだけを返す

STAGE_SKILLS=(plan-review design-security-review implement review-gate test-gate fix-loop retro close)
AGENTS=(issue-reviewer plan-reviewer code-reviewer adversarial-reviewer fix-diagnosis-reviewer fix-implementation-reviewer fix-test-reviewer)

# frontmatter の値（無ければ空）: fm <file> <key>
fm() {
  python3 - "$1" "$2" <<'PY'
import sys
path, key = sys.argv[1:3]
lines = open(path, encoding="utf-8").read().split("\n")
if not lines or lines[0] != "---":
    sys.exit(0)
for l in lines[1:]:
    if l == "---":
        break
    if l.startswith(key + ":"):
        print(l[len(key) + 1:].strip())
        break
PY
}

# ---------------- R: 名前と置き場所 ----------------
r1() { local d="$1" n; for n in code-review security-review verify simplify review test; do [ ! -e "$d/$n" ] || return 1; done; }
r2() { local d="$1" s; for s in "${STAGE_SKILLS[@]}"; do
         [ -f "$d/$s/SKILL.md" ] || return 1
         [ "$(fm "$d/$s/SKILL.md" user-invocable)" = "false" ] || return 1
         [ "$(fm "$d/$s/SKILL.md" disable-model-invocation)" != "true" ] || return 1
         [ "$(fm "$d/$s/SKILL.md" name)" = "$s" ] || return 1
       done; }
r3() { local d="$1"
       [ "$(fm "$d/plan-issue/SKILL.md" disable-model-invocation)" = "true" ] || return 1
       [ "$(fm "$d/grill-me/SKILL.md" disable-model-invocation)" = "true" ] || return 1
       [ -z "$(fm "$d/proceed/SKILL.md" disable-model-invocation)" ] || return 1
       [ -z "$(fm "$d/issue-bootstrap/SKILL.md" disable-model-invocation)" ] || return 1
       [ "$(fm "$d/proceed/SKILL.md" user-invocable)" != "false" ] || return 1; }
r4() { local d="$1" old="$2" a want; [ ! -e "$old" ] || return 1
       for a in "${AGENTS[@]}"; do
         [ -f "$d/$a.md" ] || return 1
         [ "$(fm "$d/$a.md" name)" = "$a" ] || return 1
         want="Read, Grep, Glob"; [ "$a" = "adversarial-reviewer" ] && want="Read, Grep, Glob, Bash"
         [ "$(fm "$d/$a.md" tools)" = "$want" ] || return 1
       done; }
r5() { ! grep -qE 'ultra|claude-code-action' "$@"; }
R6_RE='/(implement|code-review|test|fix-loop|retro|close|security-review) (I[0-9#]|\$ARGUMENTS|\[I)|/plan-issue-review([^.]|$)|review-agents'
r6() { local root="$1"; ! ( cd "$root" && grep -rqE "$R6_RE" CLAUDE.md docs/runbooks/*.md .claude/skills .claude/agents scripts/claude/*.sh \
         scripts/migration_verify docs/plans/templates docs/tests/templates docs/issues/templates docs/claude-code-structure.md ); }
# 実際に claude -p を呼ぶ行（`claude -p --…` か、行末の `claude -p \`）は timeout を伴い、旧い呼び方が無い
r7() { local f bad=0
       for f in "$@"; do
         while IFS= read -r l; do
           case "$l" in *timeout*) ;; *) bad=1 ;; esac
         done < <(grep -E 'claude -p( --|[[:space:]]*\\$)' "$f" | grep -vE '^[[:space:]]*#')
         grep -qE -- '--system-prompt|claude-sonnet-4-6' "$f" && bad=1
       done
       [ "$bad" -eq 0 ]; }

SCRIPTS=(scripts/claude/code-review.sh scripts/claude/plan-issue-review.sh scripts/claude/issue-review.sh scripts/claude/fix-review-lib.sh)
ck "R1 組み込みと同じ名前のスキルが無い" 0 "$(rc r1 .claude/skills)"
ck "R2 段階のスキルは user-invocable: false・名前一致・disable-model-invocation なし" 0 "$(rc r2 .claude/skills)"
ck "R3 ユーザーが打つスキルの呼び出し設定" 0 "$(rc r3 .claude/skills)"
ck "R4 レビュー役 7 本が .claude/agents にあり tools が許可リスト" 0 "$(rc r4 .claude/agents .claude/review-agents)"
ck "R5 有料の道具（ultra・claude-code-action）が無い" 0 "$(rc r5 scripts/claude/*.sh .github/workflows/*.yml)"
ck "R6 古い流れの参照が無い" 0 "$(rc r6 "$REPO_ROOT")"
ck "R7 claude -p は timeout つき・旧い呼び方が無い" 0 "$(rc r7 "${SCRIPTS[@]}")"

cp -r .claude/skills "$TMP/skills1"; mkdir "$TMP/skills1/code-review"
ck "FG-R1 code-review フォルダを足すと R1 不合格" 1 "$(rc r1 "$TMP/skills1")"
cp -r .claude/skills "$TMP/skills2"; sed -i 's/^user-invocable: false$/disable-model-invocation: true/' "$TMP/skills2/review-gate/SKILL.md"
ck "FG-R2 review-gate を disable-model-invocation にすると R2 不合格" 1 "$(rc r2 "$TMP/skills2")"
cp -r .claude/skills "$TMP/skills3"; sed -i '0,/^argument-hint/s//disable-model-invocation: true\nargument-hint/' "$TMP/skills3/proceed/SKILL.md"
ck "FG-R3 proceed を disable-model-invocation にすると R3 不合格" 1 "$(rc r3 "$TMP/skills3")"
cp -r .claude/agents "$TMP/agents4"; sed -i 's/^tools: Read, Grep, Glob$/tools: Read, Grep, Glob, Write/' "$TMP/agents4/code-reviewer.md"
ck "FG-R4 code-reviewer に Write を足すと R4 不合格" 1 "$(rc r4 "$TMP/agents4" "$TMP/no-such-dir")"
mkdir -p "$TMP/old-review-agents"
ck "FG-R4 .claude/review-agents が残っていると R4 不合格" 1 "$(rc r4 .claude/agents "$TMP/old-review-agents")"
printf 'claude -p "/code-review ultra"\n' > "$TMP/r5.sh"
ck "FG-R5 ultra を足すと R5 不合格" 1 "$(rc r5 "$TMP/r5.sh")"
R6TMP="$TMP/r6root"; mkdir -p "$R6TMP"
( cd "$REPO_ROOT" && tar cf - CLAUDE.md docs/runbooks .claude/skills .claude/agents scripts/claude/*.sh scripts/migration_verify \
    docs/plans/templates docs/tests/templates docs/issues/templates docs/claude-code-structure.md ) | ( cd "$R6TMP" && tar xf - )
cp -r "$R6TMP" "$TMP/r6a"; printf '\n/test I123 を打つ\n' >> "$TMP/r6a/docs/runbooks/workflow.md"
ck "FG-R6 workflow.md に /test I123 を足すと R6 不合格" 1 "$(rc r6 "$TMP/r6a")"
cp -r "$R6TMP" "$TMP/r6b"; printf '\n.claude/review-agents/code-reviewer.md\n' >> "$TMP/r6b/.claude/skills/close/SKILL.md"
ck "FG-R6 close に review-agents を足すと R6 不合格" 1 "$(rc r6 "$TMP/r6b")"
ck "FG-R6 写しの元のままなら合格（写し方の確認）" 0 "$(rc r6 "$R6TMP")"
sed 's/timeout "${REVIEW_TIMEOUT:-900}" claude -p --agent/claude -p --agent/' scripts/claude/plan-issue-review.sh > "$TMP/r7.sh"
ck "FG-R7 plan-issue-review.sh の timeout を外すと R7 不合格" 1 "$(rc r7 "$TMP/r7.sh")"

# ---------------- F: flow-stage.sh ----------------
FS="$REPO_ROOT/scripts/claude/flow-stage.sh"
fs_dir() { mkdir -p "$TMP/$1/open" "$TMP/$1/closed"; printf '%b' "$2" > "$TMP/$1/open/I999_review.md"; }
fs_out() { REVIEW_DIR="$TMP/$1" bash "$FS" I999 2>/dev/null; }
fs_rc() { REVIEW_DIR="$TMP/$1" bash "$FS" I999 >/dev/null 2>&1; echo $?; }
fs_dir f1 '# x\n\nSTAGE_DONE: plan NEXT: plan-review\n'
ck "F1 最後の STAGE_DONE の NEXT を返す" "NEXT_STAGE: plan-review" "$(fs_out f1 | head -1)"
ck "F1 exit 0" 0 "$(fs_rc f1)"
fs_dir f2 'STAGE_DONE: plan NEXT: plan-review\nSTAGE_DONE: plan-review NEXT: implement\nSTAGE_DONE: implement NEXT: review-gate\n'
ck "F2 3 行あるとき最後の行を使う" "NEXT_STAGE: review-gate" "$(fs_out f2 | head -1)"
ck "F2 LAST_LINE はその行番号" "LAST_LINE: 3" "$(fs_out f2 | sed -n 2p)"
ck "F2 STAGE_COUNT は STAGE_DONE 行の数" "STAGE_COUNT: 3" "$(fs_out f2 | sed -n 3p)"
# F11: STAGE_DONE より上の節に行を足しても STAGE_COUNT は変わらない（proceed の見分けに使う・I193 H1）
fs_dir f11 '## 自律判断の記録\n- a\n\nSTAGE_DONE: plan NEXT: plan-review\n'
C_BEFORE=$(fs_out f11 | sed -n 3p)
printf '%b' '## 自律判断の記録\n- a\n- b（止める前に足した行）\n\nSTAGE_DONE: plan NEXT: plan-review\n' > "$TMP/f11/open/I999_review.md"
ck "F11 自律判断の記録に行を足しても STAGE_COUNT は同じ" "$C_BEFORE" "$(fs_out f11 | sed -n 3p)"
ck "S14 review-gate は判定行が無いとき 1 回だけやり直す" 0 "$(rc grep -qF '出力に `FINAL_VERDICT:` 行が無い（途中で止まった・背景の実行が打ち切られた）' .claude/skills/review-gate/SKILL.md)"
ck "S15 review-gate は報告の無い観点を合格に数えない" 0 "$(rc grep -qF '**報告の無い観点を合格に数えない**' .claude/skills/review-gate/SKILL.md)"
ck "S16 plan-review は背景で実行し、判定行が無いときやり直す" 0 "$(rc grep -qF '出力に `PLAN_VERDICT:` 行が無い（途中で止まった）' .claude/skills/plan-review/SKILL.md)"
ck "FG-S15 「時間切れの体は新規 Critical/High 0 として数える」を戻すと S15 不合格" 1 "$(sed 's#\*\*報告の無い観点を合格に数えない\*\*#時間切れの体は新規 Critical/High 0 として数える#' .claude/skills/review-gate/SKILL.md > "$TMP/s15.md"; rc grep -qF '**報告の無い観点を合格に数えない**' "$TMP/s15.md")"
ck "S13 proceed は STAGE_COUNT で見分ける（LAST_LINE を見分けに使わない）" 0 "$(rc grep -qF '`STAGE_COUNT:`（`STAGE_DONE:` 行の数）が増えていなければ' .claude/skills/proceed/SKILL.md)"
fs_dir f3 '# x\n\n本文だけ\n'
ck "F3 STAGE_DONE 行が無いと exit 2" 2 "$(fs_rc f3)"
mkdir -p "$TMP/f4/open"
ck "F4 記録ファイルが無いと exit 2" 2 "$(fs_rc f4)"
fs_dir f5 'STAGE_DONE: plan NEXT: deploy\n'
ck "F5 一覧に無い NEXT は exit 2" 2 "$(fs_rc f5)"
fs_dir f6 'STAGE_DONE: plan NEXT: plan-review\n> 引用: STAGE_DONE: close NEXT: merge\n'
ck "F6 行頭でない STAGE_DONE は数えない" "NEXT_STAGE: plan-review" "$(fs_out f6 | head -1)"
mkdir -p "$TMP/f7/closed"; printf 'STAGE_DONE: close NEXT: merge\n' > "$TMP/f7/closed/I999_review.md"
ck "F7 close の後は closed の記録を読む" "NEXT_STAGE: merge" "$(fs_out f7 | head -1)"
ck "F8 I### でない引数は exit 2" 2 "$(rc bash "$FS" 'I99;rm')"
ck "F10 サブディレクトリから実行してもリポジトリのルートの記録を読む" 0 "$( (cd "$REPO_ROOT/scripts" && bash ../scripts/claude/flow-stage.sh I193 >/dev/null 2>&1); echo $?)"
mkdir -p "$TMP/f9"; printf '#!/usr/bin/env bash\nexit 0\n' > "$TMP/f9/test_ok.sh"; printf '#!/usr/bin/env bash\nexit 1\n' > "$TMP/f9/test_ng.sh"
ck "F9 run-all.sh は失敗するテストが 1 本あれば非ゼロ" 1 "$(TEST_DIR="$TMP/f9" rc bash scripts/claude/tests/run-all.sh)"
rm "$TMP/f9/test_ng.sh"
ck "F9 run-all.sh は全部合格なら 0" 0 "$(TEST_DIR="$TMP/f9" rc bash scripts/claude/tests/run-all.sh)"
mkdir -p "$TMP/f9b"
ck "F9 run-all.sh はテストが 1 本も無いと非ゼロ" 1 "$(TEST_DIR="$TMP/f9b" rc bash scripts/claude/tests/run-all.sh)"

# ---------------- G: gate-check.sh ----------------
GC="$REPO_ROOT/scripts/claude/gate-check.sh"; LIB="$REPO_ROOT/scripts/claude/code-review.sh"
g_init() {   # g_init <dir>: main（比べる相手）から切った feature ブランチ。scripts/a.sh と docs/ を持つ
  local d="$TMP/$1"; mkdir -p "$d/scripts" "$d/docs/reviews"
  git -C "$d" init -q -b main
  printf 'echo a\n' > "$d/scripts/a.sh"; printf '# r\n' > "$d/docs/reviews/keep.md"
  git -C "$d" add -A; git -C "$d" -c user.name=t -c user.email=t@example.invalid commit -q -m base
  git -C "$d" checkout -q -b feature
  printf 'echo f\n' > "$d/scripts/f.sh"
  git -C "$d" add -A; git -C "$d" -c user.name=t -c user.email=t@example.invalid commit -q -m "feature change"
}
g_commit() { git -C "$TMP/$1" add -A; git -C "$TMP/$1" -c user.name=t -c user.email=t@example.invalid commit -q -m "$2"; }
g_record() {   # g_record <dir> <kind> <ts> <verdict> <risk|-> : HEAD を REVIEWED_COMMIT にした記録を書いてコミット
  local d="$TMP/$1" sha; sha=$(git -C "$d" rev-parse HEAD)
  { printf '# %s\n\n' "$2"; [ "$5" != "-" ] || true
    printf 'REVIEWED_COMMIT: %s\n' "$sha"; [ "$5" = "-" ] || printf 'RISK: %s\n' "$5"; printf 'VERDICT: %s\n' "$4"; } > "$d/docs/reviews/I999_$2_$3.md"
  g_commit "$1" "record $2"
}
g_rc() { ( cd "$TMP/$1" && GATE_BASE="${GBASE:-main}" GATE_CHECK_LIB="$LIB" bash "$GC" I999 >/dev/null 2>&1 ); echo $?; }
g_out() { ( cd "$TMP/$1" && GATE_BASE="${GBASE:-main}" GATE_CHECK_LIB="$LIB" bash "$GC" I999 2>&1 ) | grep '^GATE_CHECK:'; }

g_init g1; g_record g1 code_review 20260101_0000 OK NO
ck "G1 最新のレビューが OK で HEAD を見ている → 0" 0 "$(g_rc g1)"
printf 'more\n' >> "$TMP/g1/docs/reviews/keep.md"; g_commit g1 "docs only"
ck "G2 レビューの後に docs/reviews だけ変えた → 0" 0 "$(g_rc g1)"
printf 'echo b\n' >> "$TMP/g1/scripts/a.sh"; g_commit g1 "code"
ck "G3 レビューの後に scripts を変えた → 1" 1 "$(g_rc g1)"
g_init g4; g_record g4 code_review 20260101_0000 OK NO; g_record g4 code_review 20260101_0100 HIGH NO
ck "G4 最新の記録が HIGH（古い記録は OK）→ 1" 1 "$(g_rc g4)"
g_init g5; printf '# x\nRISK: NO\nVERDICT: OK\n' > "$TMP/g5/docs/reviews/I999_code_review_20260101_0000.md"; g_commit g5 rec
ck "G5 REVIEWED_COMMIT 行が無い → 1" 1 "$(g_rc g5)"
g_init g6; g_record g6 code_review 20260101_0000 OK YES
ck "G6 RISK YES で敵対的レビュー記録が無い → 1" 1 "$(g_rc g6)"
g_record g6 adversarial_review 20260101_0010 HIGH -
ck "G6 RISK YES で敵対的レビューの最新が HIGH → 1" 1 "$(g_rc g6)"
g_record g6 adversarial_review 20260101_0020 OK -
ck "G6 RISK YES で敵対的レビューの最新が OK → 0" 0 "$(g_rc g6)"
g_init g7
ck "G7 コードレビュー記録が 1 本も無い → 1" 1 "$(g_rc g7)"
g_init g8; g_record g8 adversarial_review 20260101_0000 OK -
printf 'echo c\n' >> "$TMP/g8/scripts/a.sh"; g_commit g8 "code after adversarial OK"
g_record g8 code_review 20260101_0100 OK YES
ck "G8 敵対的レビューの OK の後に scripts を変えた → 1" 1 "$(g_rc g8)"
g_init g9; g_record g9 code_review 20260101_0000 OK NO
printf 'echo d\n' >> "$TMP/g9/scripts/a.sh"
ck "G9 scripts にコミットしていない変更がある → 1" 1 "$(g_rc g9)"
git -C "$TMP/g9" checkout -q -- scripts/a.sh; printf 'x\n' > "$TMP/g9/scripts/new.sh"
ck "G9 scripts に未追跡のファイルがある → 1" 1 "$(g_rc g9)"
rm "$TMP/g9/scripts/new.sh"; printf 'x\n' > "$TMP/g9/docs/reviews/I998_issue_review_x.md"
ck "G9 docs/reviews の未追跡ファイルだけなら → 0" 0 "$(g_rc g9)"
g_init g10; g_record g10 code_review 20260101_0000 OK NO
printf 'x\n' > "$TMP/g10/scripts/日本語.sh"; g_commit g10 "jp"
ck "G10 日本語のファイル名のスクリプトを足した → 1" 1 "$(g_rc g10)"
# G11: レビュー役が RISK: NO でも、ブランチが安全装置（.github/）を変えていればパス判定で敵対的レビューを求める（I193 F1）
g_init g11; mkdir -p "$TMP/g11/.github/workflows"
printf 'name: x\n' > "$TMP/g11/.github/workflows/x.yml"; g_commit g11 "ci change"
g_record g11 code_review 20260101_0000 OK NO
ck "G11 .github を変えたブランチで RISK: NO・敵対的レビュー無し → 1" 1 "$(g_rc g11)"
g_record g11 adversarial_review 20260101_0010 OK -
ck "G11 同じで敵対的レビューの最新が OK → 0" 0 "$(g_rc g11)"
ck "G12 比べる相手が無い → 1（REASON=base）" "GATE_CHECK: FAIL REASON=base" "$(GBASE=no-such-branch g_out g6)"
ck "G13 未コミットの変更は REASON=dirty" "GATE_CHECK: FAIL REASON=dirty" "$(printf 'z\n' >> "$TMP/g9/scripts/a.sh"; g_out g9)"
ck "G13 レビュー後の変更は REASON=unreviewed" "GATE_CHECK: FAIL REASON=unreviewed" "$(g_out g1)"
# G14: レビューの後に比べる相手（develop 役の main）が進み、それを取り込んでも、ブランチ自身の変更が同じなら通す（I193 H2）
g_init g14; g_record g14 code_review 20260101_0000 OK NO
git -C "$TMP/g14" checkout -q main; printf 'echo dev\n' > "$TMP/g14/scripts/dev.sh"; g_commit g14 "develop moves"
git -C "$TMP/g14" checkout -q feature; git -C "$TMP/g14" -c user.name=t -c user.email=t@example.invalid merge -q --no-edit main
ck "G14 develop を取り込んだだけ → 0" 0 "$(g_rc g14)"
printf 'echo f2\n' >> "$TMP/g14/scripts/f.sh"; g_commit g14 "branch code after merge"
ck "G14 取り込みの後にブランチ自身のコードを変えた → 1" 1 "$(g_rc g14)"
# G15: auto_test.md の決定論ゲートの節をレビューの後に変えたら通さない。実行記録だけなら通す（I193 M2）
g_init g15; mkdir -p "$TMP/g15/docs/tests/open"
printf '# t\n\n## 決定論ゲート（自動実走）\n```bash\nbash scripts/claude/tests/test_a.sh\n```\n\n## 実行記録\n- なし\n' > "$TMP/g15/docs/tests/open/I999_auto_test.md"
g_commit g15 "auto test"; g_record g15 code_review 20260101_0000 OK NO
sed -i 's/^- なし$/- 2026-10-25 実行 OK/' "$TMP/g15/docs/tests/open/I999_auto_test.md"; g_commit g15 "record run"
ck "G15 auto_test.md の実行記録だけ変えた → 0" 0 "$(g_rc g15)"
sed -i 's#^bash scripts/claude/tests/test_a.sh$#bash scripts/claude/tests/test_b.sh#' "$TMP/g15/docs/tests/open/I999_auto_test.md"; g_commit g15 "gate change"
ck "G15 auto_test.md の決定論ゲートの節を変えた → 1" 1 "$(g_rc g15)"
# G16: テンプレート（docs/tests/templates）は記録の場所ではない
g_init g16; g_record g16 code_review 20260101_0000 OK NO
mkdir -p "$TMP/g16/docs/tests/templates"; printf 'x\n' > "$TMP/g16/docs/tests/templates/t.md"; g_commit g16 "template"
ck "G16 レビューの後にテンプレートを変えた → 1" 1 "$(g_rc g16)"
# G17: 空白を含む名前の未追跡ファイルでも、記録の場所の中なら汚れにしない（I193 M3）
g_init g17; g_record g17 code_review 20260101_0000 OK NO
printf 'x\n' > "$TMP/g17/docs/reviews/I998 issue review.md"
ck "G17 記録の場所の空白を含む名前の未追跡ファイル → 0" 0 "$(g_rc g17)"
# G18: レビューの後にバイナリのファイルの中身を差し替えたら数える（中身〔blob〕で比べる。I193 3 回目 M3）
g_init g18; printf '\x00\x01\x02' > "$TMP/g18/scripts/b.bin"; g_commit g18 "binary"; g_record g18 code_review 20260101_0000 OK NO
printf '\x00\x09\x02' > "$TMP/g18/scripts/b.bin"; g_commit g18 "binary changed"
ck "G18 レビューの後にバイナリの中身を差し替えた → 1" 1 "$(g_rc g18)"
# G19: develop がブランチと同じファイルを変えて取り込んだときは、止まる側（review-gate を通り直す）
g_init g19; g_record g19 code_review 20260101_0000 OK NO
git -C "$TMP/g19" checkout -q main; printf 'echo f\n' > "$TMP/g19/scripts/f.sh"; printf 'echo a2\n' > "$TMP/g19/scripts/a.sh"; g_commit g19 "develop touches a.sh"
git -C "$TMP/g19" checkout -q feature; printf 'echo a-feature\n' > "$TMP/g19/scripts/a.sh"; g_commit g19 "feature touches a.sh"
g_record g19 code_review 20260101_0100 OK NO
git -C "$TMP/g19" -c user.name=t -c user.email=t@example.invalid merge -q --no-edit -X ours main
ck "G19 develop も同じファイルを変えていて取り込んだ → 1（止まる側）" 1 "$(g_rc g19)"
# G20: docs/issues/templates・docs/reviews/templates は記録の場所ではない（I193 3 回目 M4）
g_init g20; g_record g20 code_review 20260101_0000 OK NO
mkdir -p "$TMP/g20/docs/issues/templates"; printf 'x\n' > "$TMP/g20/docs/issues/templates/issue_template.md"; g_commit g20 "issue template"
ck "G20 レビューの後に docs/issues/templates を変えた → 1" 1 "$(g_rc g20)"

# ---------------- C: code-review.sh の関数 ----------------
# shellcheck source=scripts/claude/code-review.sh
REVIEW_LIB_SOURCE_ONLY=1 . scripts/claude/code-review.sh
set +e   # code-review.sh の set -e を、このテストの中では使わない
STUB="$TMP/stubbin"; mkdir -p "$STUB"
cat > "$STUB/gh" <<'SH'
#!/usr/bin/env bash
# テスト用の gh:
#   gh pr view <n> --json headRefOid ... → GH_HEAD
#   gh pr checks <n> --json name,bucket ... → GH_CHECKS（「bucket<TAB>name」の行。\t・\n を解釈）
case "$*" in
  *headRefOid*) printf '%s\n' "${GH_HEAD:-}" ;;
  *--json*) printf '%b' "${GH_CHECKS:-}" ;;
  *) printf 'stub\n' ;;
esac
SH
chmod +x "$STUB/gh"
printf 'jobs:\n  a:\n    name: A\n  b:\n    name: B\n' > "$TMP/wf.yml"
MYHEAD=$(git rev-parse HEAD)
wc_rc() { PATH="$STUB:$PATH" GH_HEAD="${2:-$MYHEAD}" GH_CHECKS="$1" CI_WORKFLOWS="$TMP/wf.yml" CI_WAIT_TIMEOUT=2 CI_POLL_INTERVAL=1 wait_ci 1 >/dev/null 2>&1; echo $?; }
ck "C1 CI がずっと pending → 3（時間切れ）" 3 "$(wc_rc 'pass\tA\npending\tB\n')"
ck "C2 fail がある → 1" 1 "$(wc_rc 'pass\tA\nfail\tB\n')"
ck "C3 cancel がある → 1" 1 "$(wc_rc 'pass\tA\ncancel\tB\n')"
ck "C4 チェックがまだ 1 つも無い → 成功にしない（3）" 3 "$(wc_rc '')"
ck "C4b ジョブが一部しか登録されていない（B が無い）→ 成功にしない（3）" 3 "$(wc_rc 'pass\tA\n')"
ck "C5 全部 pass か skipping → 0" 0 "$(wc_rc 'pass\tA\nskipping\tB\n')"
ck "C10 PR の最新のコミットが手元の HEAD と違う → 1" 1 "$(wc_rc 'pass\tA\npass\tB\n' deadbeef)"
ck "C10 そのとき CI_WAIT: NOT_PUSHED を出す" "CI_WAIT: NOT_PUSHED" "$(PATH="$STUB:$PATH" GH_HEAD=deadbeef CI_WORKFLOWS="$TMP/wf.yml" wait_ci 1 2>/dev/null | tail -1)"
ck "C10b ワークフローのジョブ名を読めない → 理由を出して 1（待ち続けない）" 1 "$(PATH="$STUB:$PATH" GH_HEAD="$MYHEAD" GH_CHECKS='pass\tA\n' CI_WORKFLOWS="$TMP/no-such.yml" CI_WAIT_TIMEOUT=2 CI_POLL_INTERVAL=1 wait_ci 1 >/dev/null 2>&1; echo $?)"
bash -c 'sleep 300 & wait' & KT=$!
sleep 1; KT_CHILD=$(ps -o pid= --ppid "$KT" | head -1 | tr -d ' ')
kill_tree "$KT"; sleep 1
ck "C11 kill_tree は子のプロセスまで止める" 1 "$(rc kill -0 "$KT_CHILD")"
printf '# r\n\nRISK: NO\nVERDICT: OK\n' > "$TMP/c6.md"; add_reviewed_commit "$TMP/c6.md" abc1234
ck "C6 REVIEWED_COMMIT を足しても RISK が読める（NO のまま）" NO "$(detect_risk_flag "$TMP/c6.md")"
ck "C6 REVIEWED_COMMIT は RISK 行の前" "REVIEWED_COMMIT: abc1234" "$(grep -B1 '^RISK:' "$TMP/c6.md" | head -1)"
printf '# r\n本文\n' > "$TMP/c7.md"
ck "C7 VERDICT も表の印も無い記録は BLOCKER" BLOCKER "$(detect_code_verdict "$TMP/c7.md")"
ck "C8 指摘の配列（\"file\":）は読めた結果" 0 "$(rc official_output_readable '[ {"file": "a.sh", "line": 1} ]')"
ck "C8 空の配列だけの行は読めた結果" 0 "$(rc official_output_readable $'結果:\n[]\n')"
ck "C8 ファイル名が出てくるだけは読めた結果にしない" 1 "$(rc official_output_readable 'CLAUDE.md を確認しましたが git diff を実行できませんでした')"
ck "C8 行頭の [ のリンクだけは読めた結果にしない" 1 "$(rc official_output_readable '[注意] 許可がありません')"
ck "C9 組み込みの出力の VERDICT 行は行頭から外す" "> VERDICT: OK" "$(printf 'VERDICT: OK\n' | neutralize_machine_lines)"
ck "C12 「脆弱性は見つかりませんでした」は読めた結果" 0 "$(rc official_output_readable '確信度の高い脆弱性（重大度 HIGH・MEDIUM）は見つかりませんでした。')"
ck "C13 is_record_path: docs/reviews/templates は記録の場所ではない" 1 "$(rc is_record_path docs/reviews/templates/review_template.md)"
ck "C13 is_record_path: docs/tests/open は記録の場所" 0 "$(rc is_record_path docs/tests/open/I999_auto_test.md)"
C14R="$TMP/c14"; mkdir -p "$C14R/docs/reviews" "$C14R/scripts"; git -C "$C14R" init -q -b main
printf 'a\n' > "$C14R/scripts/a.sh"; git -C "$C14R" add -A; git -C "$C14R" -c user.name=t -c user.email=t@example.invalid commit -q -m base
C14A=$(git -C "$C14R" rev-parse HEAD); printf 'r\n' > "$C14R/docs/reviews/I999_adversarial_review_x.md"
git -C "$C14R" add -A; git -C "$C14R" -c user.name=t -c user.email=t@example.invalid commit -q -m rec
ck "C14 記録だけのコミットは HEAD の移動として数えない（HEAD_DRIFT・I193 3 回目 M2）" 0 "$( (cd "$C14R" && changed_outside_records "$C14A" HEAD >/dev/null); echo $?)"
printf 'b\n' >> "$C14R/scripts/a.sh"; git -C "$C14R" add -A; git -C "$C14R" -c user.name=t -c user.email=t@example.invalid commit -q -m code
ck "C14 記録の場所の外のファイルが動いたら数える" 1 "$( (cd "$C14R" && changed_outside_records "$C14A" HEAD >/dev/null); echo $?)"
# C15: 判定（VERDICT・RISK）は、組み込みのレビューの出力を足す前に行う（足すのは add_reviewed_commit の後。I193 3 回目 M6）
C15_DETECT=$(grep -n 'LLM_VERDICT=$(detect_code_verdict' scripts/claude/code-review.sh | head -1 | cut -d: -f1)
C15_APPEND=$(grep -n '"$OFFICIAL_CODE" "$OFFICIAL_SECURITY" >> "$REVIEW_FILE"' scripts/claude/code-review.sh | head -1 | cut -d: -f1)
ck "C15 組み込みの出力は判定の後に足す" yes "$([ -n "$C15_DETECT" ] && [ -n "$C15_APPEND" ] && [ "$C15_DETECT" -lt "$C15_APPEND" ] && echo yes || echo no)"
ck "C12 claude の設定の警告行は除く" "本文" "$(printf 'Permission allow rule (../x.json): Write(a) is not matched\n本文\n' | drop_cli_warnings)"

# ---------------- S: スキルの中身 ----------------
s_has() { grep -qF -- "$2" "$1"; }
s_not() { ! grep -qF -- "$2" "$1"; }
s1() { s_not "$1" "承認ポイントを提示して停止" && s_has "$1" 'Skill ツールで `proceed` を呼ぶ'; }
s2() { s_not "$1" "/implement を実行して初めて" && s_has "$1" 'Skill ツールで `simplify` を呼ぶ'; }
s3() { s_has "$1" 'bash scripts/claude/gate-check.sh' && s_has "$1" 'NEXT: review-gate'; }
s4() { s_has "$1" 'STAGE_DONE: fix-loop NEXT: review-gate' && s_not "$1" '/test に戻る' && s_not "$1" '承認待ちで停止'; }
s5() { s_has "$1" 'bash scripts/claude/code-review.sh' && s_has "$1" 'run_in_background: true' && s_has "$1" '1 回だけ実行し直す' && s_has "$1" 'OK の周の後に差分を足さない'; }
s6() { s_has "$1" 'Skill ツールで `issue-bootstrap` を呼ぶ' && s_not "$1" 'ユーザーの判断を待つ:'; }
s7() { local f; for f in "$@"; do s_has "$f" '「止めて聞く条件」' || return 1; done; }
s8() { grep -qE 'claude -p --permission-mode plan' "$1" && s_has "$1" '"/code-review medium origin/develop...HEAD"' && s_has "$1" '"/security-review"' && s_has "$1" 'git fetch -q origin develop'; }
s11() { local f; for f in "$@"; do s_has "$f" 'コマンドの出力・ログ・環境変数・記録' || return 1; done; }
# 止める条件 2 の安全装置の集合が path_risk_trigger の case 行と一致する
s12() {
  python3 - "$1" "$2" <<'PY'
import re, sys
crs, wf = sys.argv[1:3]
case = [l for l in open(crs, encoding="utf-8").read().split("\n") if re.match(r"^\s+\.github/\*\|", l)]
if len(case) != 1: sys.exit(1)
want = set(case[0].strip().split(")")[0].split("|"))
rows = [l for l in open(wf, encoding="utf-8").read().split("\n") if l.startswith("2. **取り消せない操作・安全装置そのものを変える操作**")]
if len(rows) != 1: sys.exit(1)
got = set(re.findall(r"`([^`]+)`", rows[0].split("と同じ:")[1].split("（安全装置は")[0])) if "と同じ:" in rows[0] else set()
sys.exit(0 if got == want else 1)
PY
}
SK=.claude/skills
ck "S1 plan-issue は止まらずに proceed を呼ぶ" 0 "$(rc s1 $SK/plan-issue/SKILL.md)"
ck "S2 implement は明示コマンド待ちが無く /simplify を呼ぶ" 0 "$(rc s2 $SK/implement/SKILL.md)"
ck "S3 test-gate は最初に gate-check" 0 "$(rc s3 $SK/test-gate/SKILL.md)"
ck "S3 close は最初に gate-check" 0 "$(rc s3 $SK/close/SKILL.md)"
ck "S4 fix-loop の戻り先は review-gate だけ・承認待ちが無い" 0 "$(rc s4 $SK/fix-loop/SKILL.md)"
ck "S5 review-gate は背景実行・やり直し 1 回・OK の周の後に差分を足さない" 0 "$(rc s5 $SK/review-gate/SKILL.md)"
ck "S6 retro は issue-bootstrap を呼び、ユーザーの判断を待たない" 0 "$(rc s6 $SK/retro/SKILL.md)"
STOP_REF_SKILLS=()
for s in "${STAGE_SKILLS[@]}" plan-issue proceed; do STOP_REF_SKILLS+=("$SK/$s/SKILL.md"); done
ck "S7 段階とユーザー用のスキルが止める条件を workflow.md で参照" 0 "$(rc s7 "${STOP_REF_SKILLS[@]}")"
ck "S8 code-review.sh は fetch し、組み込み 2 本を plan モードで呼ぶ" 0 "$(rc s8 scripts/claude/code-review.sh)"
ck "S11 retro・issue-bootstrap に自動起票の本文の決まり" 0 "$(rc s11 $SK/retro/SKILL.md $SK/issue-bootstrap/SKILL.md)"
ck "S12 止める条件 2 の集合が path_risk_trigger と一致" 0 "$(rc s12 scripts/claude/code-review.sh docs/runbooks/workflow.md)"

sed 's#bash scripts/claude/gate-check.sh#bash scripts/claude/no-check.sh#' $SK/test-gate/SKILL.md > "$TMP/s3.md"
ck "FG-S3 test-gate から gate-check を消すと S3 不合格" 1 "$(rc s3 "$TMP/s3.md")"
{ cat $SK/fix-loop/SKILL.md; printf '\nfix-loop 完了後は /test に戻る\n'; } > "$TMP/s4.md"
ck "FG-S4 fix-loop に「/test に戻る」を足すと S4 不合格" 1 "$(rc s4 "$TMP/s4.md")"
sed 's#claude -p --permission-mode plan#claude -p#' scripts/claude/code-review.sh > "$TMP/s8.sh"
ck "FG-S8 plan モードを外すと S8 不合格" 1 "$(rc s8 "$TMP/s8.sh")"
sed 's#`.secrets.baseline`・`scripts/claude/hooks/pretooluse_guard.py`#`scripts/claude/hooks/pretooluse_guard.py`#' docs/runbooks/workflow.md > "$TMP/s12.md"
ck "FG-S12 止める条件 2 から .secrets.baseline を消すと S12 不合格" 1 "$(rc s12 scripts/claude/code-review.sh "$TMP/s12.md")"
sed 's#^止めてユーザーに聞くのは `docs/runbooks/workflow.md`「止めて聞く条件」#止めてユーザーに聞くのは次のとき#' $SK/review-gate/SKILL.md > "$TMP/s7.md"
ck "FG-S7 review-gate から止める条件の参照を消すと S7 不合格" 1 "$(rc s7 "$TMP/s7.md")"

# ---------------- D: 文書 ----------------
DS=docs/proposals/I193_official_base_flow.md; WF=docs/runbooks/workflow.md
d1() { local h; for h in "## 2." "## 3." "## 4." "## 5." "## 6." "## 7."; do grep -q "^$h" "$1" || return 1; done
       s_has "$1" "https://code.claude.com/docs/en/best-practices"; }
d2() { local i; for i in $(seq 1 14); do grep -qE "^\| L${i} \|" "$1" || return 1; done; }
d3() { local t; for t in '/code-review' '/security-review' '/simplify' '/verify'; do
         grep -E "^\| \`${t}\`" "$1" | grep -qE '\*\*(入れる|入れない)\*\*' || return 1; done; }
d4() { s_has "$1" "## 止めて聞く条件" && s_has "$1" "要件・基本設計・UI/UX" && s_has "$1" "取り消せない操作" && s_has "$1" "安全側の選択肢" && s_has "$1" "## 自律判断の記録"; }
d5() { s_not "$1" "ユーザー承認なしにコード変更" && s_has "$1" "「止めて聞く条件」"; }
d6() { s_has "$1" "古い流れのまま最後まで進める" && s_has "$1" "スキルは各ワークツリーで checkout しているブランチから読み込まれる"; }
d7() { local c; for c in '/issue-bootstrap' '/grill-me' '/plan-issue' '/proceed'; do s_has "$1" "- ${c}" || return 1; done
       s_has "$1" "ユーザーは打たない"; }
ck "D1 設計書に §2〜§7 と出典" 0 "$(rc d1 $DS)"
ck "D2 設計書 §3 に L1〜L14" 0 "$(rc d2 $DS)"
ck "D3 設計書 §4 に 4 つの道具の採否" 0 "$(rc d3 $DS)"
ck "D4 workflow.md に止める 3 条件と自律判断の記録" 0 "$(rc d4 $WF)"
ck "D5 CLAUDE.md に旧承認ルールが無く止める条件を参照" 0 "$(rc d5 CLAUDE.md)"
ck "D6 workflow.md に着手済みイシューの扱い" 0 "$(rc d6 $WF)"
ck "D7 workflow.md の使うスキルは 4 つで段階は打たない" 0 "$(rc d7 $WF)"
sed 's#^| L13 |#| X13 |#' $DS > "$TMP/d2.md"
ck "FG-D2 L13 を消すと D2 不合格" 1 "$(rc d2 "$TMP/d2.md")"
sed 's#安全側の選択肢#選択肢#g' $WF > "$TMP/d4.md"
ck "FG-D4 安全側の選択肢を消すと D4 不合格" 1 "$(rc d4 "$TMP/d4.md")"
{ cat CLAUDE.md; printf '\n2) ユーザー承認なしにコード変更を開始しない\n'; } > "$TMP/d5.md"
ck "FG-D5 旧承認ルールを戻すと D5 不合格" 1 "$(rc d5 "$TMP/d5.md")"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
