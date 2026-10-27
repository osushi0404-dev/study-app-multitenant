#!/usr/bin/env bash
# I205（plan_I205.md §4・auto_test TC-01）: レビューで止める基準を変更の種類で分け、差分の中かどうかを行で決める。
#   H: delta_hunks（行の塊） L: 行で決める範囲 K: 変更の種類 B: 止める基準 W: 本体の通し（gh・claude はスタブ） D: 指示ファイル
#   FG: 判定の要を一時コピーで壊すと、対応する項目が不合格になること
# 実行: bash scripts/claude/tests/test_i205_stop_criteria.sh
# shellcheck disable=SC2016  # 単一引用符内の $ は文字どおりの照合用
# shellcheck disable=SC1090,SC1091  # code-review.sh（と壊した写し）は関数だけを読み込む
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@example.invalid GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@example.invalid

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
rc() { "$@" >/dev/null 2>&1; echo $?; }
CR="$REPO_ROOT/scripts/claude/code-review.sh"

# lib <code-review.sh の写し> <関数と引数…>: 関数だけを読み込んで 1 つ呼ぶ（cwd はそのまま）
lib() { local src="$1"; shift; REVIEW_LIB_SOURCE_ONLY=1 bash -c '. "$1"; shift; "$@"' _ "$src" "$@"; }
# 壊した写し: <置き換え前> <置き換え後>（置き換え前が無ければ印を残して最後に不合格）
broken() { local f="$TMP/cr_$RANDOM$RANDOM.sh"
  python3 -I -c 'import sys
s = open(sys.argv[1], encoding="utf-8").read()
if sys.argv[3] not in s: sys.exit(1)
open(sys.argv[2], "w", encoding="utf-8").write(s.replace(sys.argv[3], sys.argv[4]))' "$CR" "$f" "$1" "$2" || : > "$TMP/broken_failed"
  echo "$f"; }

# ---------------- 一時のリポジトリ ----------------
R="$TMP/repo"; mkdir -p "$R/backend" "$R/scripts/claude" "$R/Docs" "$R/.claude"
git -C "$R" init -q -b develop
seq 1 20 | sed 's/^/x/' > "$R/backend/x.py"
seq 1 20 | sed 's/^/a/' > "$R/scripts/claude/a.sh"
seq 1 10 | sed 's/^/o/' > "$R/old.txt"
seq 1 10 | sed 's/^/u/' > "$R/Docs/up.md"
printf '{}\n' > "$R/.claude/settings.json"
printf 'A\0B\n' > "$R/img.bin"
git -C "$R" add -A; git -C "$R" commit -qm base
git -C "$R" checkout -q -b feature/I900-x
sed -i '10s/.*/x10-changed/' "$R/backend/x.py"
sed -i '15a x15-added-1\nx15-added-2' "$R/backend/x.py"
sed -i '5d' "$R/old.txt"
printf 'n1\nn2\nn3\n' > "$R/new.txt"
printf 'A\0C\n' > "$R/img.bin"
git -C "$R" add -A; git -C "$R" commit -qm "branch 1"
inR() { (cd "$R" && "$@"); }

# ---------------- H delta_hunks ----------------
inR lib "$CR" delta_hunks develop "" > "$TMP/h_full1" 2>/dev/null
hk() { grep -qxF "$1" "$2" && echo yes || echo no; }
ck "H1 変えた 10 行目 → backend/x.py 10〜10" yes "$(hk "$(printf 'backend/x.py\t10\t10')" "$TMP/h_full1")"
ck "H1 15 行目の後に足した 2 行 → backend/x.py 16〜17" yes "$(hk "$(printf 'backend/x.py\t16\t17')" "$TMP/h_full1")"
ck "H2 消しただけ → 消した位置の 1 行（old.txt 4〜4）" yes "$(hk "$(printf 'old.txt\t4\t4')" "$TMP/h_full1")"
ck "H3 新しいファイル → new.txt 1〜3" yes "$(hk "$(printf 'new.txt\t1\t3')" "$TMP/h_full1")"
ck "H4 バイナリ → ファイル全体" yes "$(hk "$(printf 'img.bin\t1\t999999999')" "$TMP/h_full1")"
SINCE=$(git -C "$R" rev-parse HEAD)
# 起点の後: ブランチが 3 行目を変え、develop の 20 行目の変更を取り込む
sed -i '3s/.*/x3-changed/' "$R/backend/x.py"; git -C "$R" add -A; git -C "$R" commit -qm "branch 2"
git -C "$R" checkout -q develop; sed -i '20s/.*/x20-develop/' "$R/backend/x.py"; git -C "$R" add -A; git -C "$R" commit -qm develop
git -C "$R" checkout -q feature/I900-x; git -C "$R" merge -q --no-edit develop
ck "H5 差分のレビュー: 起点の後にブランチが変えた行（3 行目）だけ・取り込んだ develop の行は入らない" "$(printf 'backend/x.py\t3\t3')" \
  "$(inR lib "$CR" delta_hunks develop "$SINCE" 2>/dev/null | paste -sd'|' -)"
inR lib "$CR" delta_hunks develop "" > "$TMP/h_full2" 2>/dev/null
ck "H6 全体のレビュー: ブランチが変えた行（3・10・16〜17）があり、develop の行（22 行目）は無い" "yes yes yes no" \
  "$(hk "$(printf 'backend/x.py\t3\t3')" "$TMP/h_full2") $(hk "$(printf 'backend/x.py\t10\t10')" "$TMP/h_full2") $(hk "$(printf 'backend/x.py\t16\t17')" "$TMP/h_full2") $(grep -q "$(printf '\t22\t22')" "$TMP/h_full2" && echo yes || echo no)"
# H7（計画 4.11・F1）: git の接頭辞の設定を変えても塊が同じ
git -C "$R" config diff.noprefix true; git -C "$R" config diff.mnemonicPrefix true
ck "H7 diff.noprefix・diff.mnemonicPrefix を設定しても backend/x.py 10〜10" yes \
  "$(inR lib "$CR" delta_hunks develop "" 2>/dev/null | grep -qxF "$(printf 'backend/x.py\t10\t10')" && echo yes || echo no)"
# H8（4.11・F6）: 追加した行の中身が「++ b/…」（diff では「+++ b/…」）でも、見出しと取り違えず後ろの塊が残る
sed -i '1s/.*/++ b\/zz.txt/; 8s/.*/o8-changed/' "$R/old.txt"; git -C "$R" add -A; git -C "$R" commit -qm "F6"
inR lib "$CR" delta_hunks develop "" > "$TMP/h_f6" 2>/dev/null
ck "H8 中身が「++ b/zz.txt」の行の後ろの塊（old.txt 8〜8）が残る" yes "$(hk "$(printf 'old.txt\t8\t8')" "$TMP/h_f6")"
# H9（4.11・F2）: 対象のファイルなのに diff に出てこないものはファイル全体
printf 'a.txt\nb.txt\n' > "$TMP/h9_list"
printf 'diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -2 +2 @@\n-x\n+y\n' > "$TMP/h9_a"
printf 'diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -5 +5 @@\n-x\n+y\n' > "$TMP/h9_b"
ck "H9 diff に出てこない b.txt はファイル全体・a.txt は 2〜2" "a.txt	2	2|b.txt	1	999999999" "$(lib "$CR" hunks_from_diff "$TMP/h9_list" "$TMP/h9_a" | paste -sd'|' -)"
ck "H9 差分のレビューで両方に出て重ならない a.txt は塊なし" "b.txt	1	999999999" "$(lib "$CR" hunks_from_diff "$TMP/h9_list" "$TMP/h9_a" "$TMP/h9_b" | paste -sd'|' -)"
# H10（F11）: 空白を含むパスでも、3 列の塊が 1 行だけ出て、台帳が作れる
printf 's1\ns2\ns3\n' > "$R/sp ace.md"; git -C "$R" add -A; git -C "$R" commit -qm "sp base"
sed -i '3s/.*/S3/' "$R/sp ace.md"; git -C "$R" commit -qam "sp change"
inR lib "$CR" delta_hunks develop "" > "$TMP/h_sp" 2>/dev/null
ck "H10 空白を含むパス: 塊は 3 列で、sp ace.md の行は 1〜3（新しいファイル）の 1 行だけ" "sp ace.md	1	3" "$(grep '^sp ace.md' "$TMP/h_sp")"
printf 'FINDING: F1 SEV=Low STATUS=open FILE=backend/x.py LINE=1 SECURITY=no STOP=- | s\n' > "$TMP/h10.md"
printf 'sp ace.md\t\t3\t3\n' > "$TMP/h10_hunks"
ck "H10 4 列の塊の行（パスにタブ）があっても台帳の作成が落ちない" 0 "$(rc inR lib "$CR" ledger_update full "" "$TMP/h10.md" "$TMP/h10_hunks")"

# ---------------- L 行で決める範囲 ----------------
printf 'backend/x.py\t10\t10\nscripts/claude/a.sh\t10\t10\ndocs/up.md\t5\t5\n.claude/settings.json\t1\t1\n' > "$TMP/hunks"
printf 'backend/x.py\nscripts/claude/a.sh\n' > "$TMP/bfiles"
# ledger <写し> <full|delta> <前の台帳|""> <FINDING 行…>: 台帳を $TMP/led に作る（形の崩れは PARSE_ERROR）
ledger() { local src="$1" kind="$2" prev="$3"; shift 3; printf '%s\n' "$@" > "$TMP/cur.md"
  (cd "$R" && lib "$src" ledger_update "$kind" "$prev" "$TMP/cur.md" "${HUNKS:-$TMP/hunks}" "${BFILES:-$TMP/bfiles}") > "$TMP/led" 2>/dev/null || { : > "$TMP/led"; echo PARSE_ERROR; }; }
# scope <FINDING 行>: その指摘の SCOPE
scope() { local src="${2:-$CR}"; ledger "$src" full "" "$1" >/dev/null; grep -oE 'SCOPE=(delta|outside)' "$TMP/led" | head -1 | cut -d= -f2; }
fx() { printf 'FINDING: F1 SEV=High STATUS=open FILE=%s LINE=%s SECURITY=no STOP=%s | s | 再現: r' "$1" "$2" "${3:--}"; }
ck "L1 塊の中の行 → delta" delta "$(scope "$(fx backend/x.py 10)")"
ck "L2 塊の後ろ 3 行（13）→ delta" delta "$(scope "$(fx backend/x.py 13)")"
ck "L2 塊の後ろ 4 行（14）→ outside" outside "$(scope "$(fx backend/x.py 14)")"
ck "L3 範囲 1-9（塊の前 3 行と重なる）→ delta" delta "$(scope "$(fx backend/x.py 1-9)")"
ck "L3 範囲 1-6（重ならない）→ outside" outside "$(scope "$(fx backend/x.py 1-6)")"
ck "L4 LINE=- → delta" delta "$(scope "$(fx backend/x.py -)")"
ck "L4 LINE=abc（読めない）→ delta" delta "$(scope "$(fx backend/x.py abc)")"
ck "L5 FILE=- → delta" delta "$(scope "$(fx - 1)")"
ck "L6 触っていない行でも STOP=ac:2 → delta" delta "$(scope "$(fx backend/x.py 1 ac:2)")"
ck "L7 範囲の外の実在のファイル（old.txt）→ outside" outside "$(scope "$(fx old.txt 1)")"
ck "L7 リポジトリに無いパス → delta" delta "$(scope "$(fx no/such.py 1)")"
ck "L7 リポジトリの外の実在のファイル → delta" delta "$(scope "$(fx "$REPO_ROOT/CLAUDE.md" 1)")"
ck "L8 casefold: 範囲 docs/up.md・実在 Docs/up.md の 5 行目 → delta" delta "$(scope "$(fx Docs/up.md 5)")"
ck "L9 全体のレビュー（delta_hunks の実物）でも、ブランチが変えたファイルの触っていない行（old.txt 9 行目）→ outside" outside "$(HUNKS="$TMP/h_full2" scope "$(fx old.txt 9)")"

# ---------------- K 変更の種類 ----------------
cat > "$TMP/kpaths" <<'EOF'
backend/x.py
frontend/src/a.tsx
e2e/a.spec.ts
docker-compose.yml
README.md
scripts/db_backup.sh
nginx/a.conf
.claude/skills/x/SKILL.md
.claude/agents/x.md
scripts/claude/x.sh
docs/runbooks/x.md
rules/x.md
CLAUDE.md
.mcp.json
.worktreeinclude
.github/workflows/ci.yml
.github/CODEOWNERS
.pre-commit-config.yaml
.secrets.baseline
scripts/claude/hooks/pretooluse_guard.py
.claude/settings.json
.claude/settings.local.json
EOF
EXPECT_K="app app app app app app app harness harness harness harness harness harness harness harness guard guard guard guard guard guard guard"
ck "K1 パスごとの種類" "$EXPECT_K" "$(lib "$CR" ledger_kinds "$TMP/kpaths" | cut -f1 | paste -sd' ' -)"
# 1 回だけ読み込み、パスごとに path_risk_trigger と種類を突き合わせる
k2() { REVIEW_LIB_SOURCE_ONLY=1 bash -c '. "$1"; while IFS=$'"'"'\t'"'"' read -r k p; do
         t=$(path_risk_trigger "$p"); { [ "$k" = guard ] && [ "$t" = YES ]; } || { [ "$k" != guard ] && [ "$t" = NO ]; } || exit 1
       done < <(ledger_kinds "$2")' _ "$1" "$TMP/kpaths"; }
ck "K2 guard の集合と path_risk_trigger() が一致" 0 "$(rc k2 "$CR")"
kind_dash() { printf '%s\n' "$@" > "$TMP/bf_k3"; BFILES="$TMP/bf_k3" ledger "$CR" full "" "$(fx - 1)" >/dev/null; grep -oE 'KIND=[a-z]+' "$TMP/led" | cut -d= -f2; }
ck "K3 FILE=- の種類: guard を含む → guard" guard "$(kind_dash backend/a.py .github/workflows/ci.yml)"
ck "K3 FILE=- の種類: app を含む → app" app "$(kind_dash docs/x.md backend/a.py)"
ck "K3 FILE=- の種類: ハーネスだけ → harness" harness "$(kind_dash docs/x.md scripts/claude/y.sh)"

# ---------------- B 止める基準 ----------------
# v <写し> <FINDING 行…>: 全体のレビューとして台帳を作り、合否を出す
v() { local src="$1"; shift; [ "$(ledger "$src" full "" "$@")" = PARSE_ERROR ] && { echo PARSE_ERROR; return; }; lib "$src" ledger_verdict "$TMP/led"; }
fl() { # fl <SEV> <FILE> <LINE> <SECURITY> <STOP> <再現 yes|no>
  printf 'FINDING: F1 SEV=%s STATUS=open FILE=%s LINE=%s SECURITY=%s STOP=%s | 要約' "$1" "$2" "$3" "$4" "$5"; [ "$6" = yes ] && printf ' | 再現: この手順で壊れる'; printf '\n'; }
ck "B1 app・High・delta・再現あり → HIGH" HIGH "$(v "$CR" "$(fl High backend/x.py 10 no - yes)")"
ck "B2 app・Medium・delta・再現あり → HIGH" HIGH "$(v "$CR" "$(fl Medium backend/x.py 10 no - yes)")"
ck "B3 app・Low・delta・再現あり → OK" OK "$(v "$CR" "$(fl Low backend/x.py 10 no - yes)")"
ck "B4 app・Medium・outside・再現あり → OK" OK "$(v "$CR" "$(fl Medium backend/x.py 1 no - yes)")"
ck "B4 台帳に STATUS=open SCOPE=outside で残る" yes "$(grep -q '^LEDGER: F1 SEV=Medium STATUS=open SCOPE=outside KIND=app' "$TMP/led" && echo yes || echo no)"
ck "B5 app・High・delta・再現なし → OK" OK "$(v "$CR" "$(fl High backend/x.py 10 no - no)")"
ck "B5 台帳に REPRO=no で残る" yes "$(grep -q 'REPRO=no' "$TMP/led" && echo yes || echo no)"
ck "B5b app・Low・STOP=ac:1・触っていない行・再現あり → HIGH" HIGH "$(v "$CR" "$(fl Low backend/x.py 1 no ac:1 yes)")"
ck "B6 app・Blocker・SECURITY=yes・outside・再現あり → BLOCKER" BLOCKER "$(v "$CR" "$(fl Blocker backend/x.py 1 yes - yes)")"
ck "B7 app・Blocker・SECURITY=yes・outside・再現なし → OK" OK "$(v "$CR" "$(fl Blocker backend/x.py 1 yes - no)")"
ck "B7 台帳に STATUS=open・SECURITY=yes で残る（retro 4-0 が拾い最優先にする）" yes "$(grep -q '^LEDGER: F1 SEV=Blocker STATUS=open .*SECURITY=yes' "$TMP/led" && echo yes || echo no)"
ck "B8 harness・Low・STOP=flow・delta・再現あり → HIGH（重大度を見ない）" HIGH "$(v "$CR" "$(fl Low scripts/claude/a.sh 10 no flow yes)")"
ck "B9 harness・High・STOP=-・delta・再現あり → OK" OK "$(v "$CR" "$(fl High scripts/claude/a.sh 10 no - yes)")"
ck "B9 台帳に KIND=harness STOP=- で残る" yes "$(grep -q 'STATUS=open SCOPE=delta KIND=harness STOP=- REPRO=yes' "$TMP/led" && echo yes || echo no)"
ck "B10 harness・STOP=flow・delta・再現なし → OK" OK "$(v "$CR" "$(fl High scripts/claude/a.sh 10 no flow no)")"
ck "B11 harness・STOP=ac（番号なし）→ OK" OK "$(v "$CR" "$(fl High scripts/claude/a.sh 10 no ac yes)")"
ck "B11 harness・STOP=other → OK" OK "$(v "$CR" "$(fl High scripts/claude/a.sh 10 no other yes)")"
ck "B12 harness・STOP=ac:3・触っていない行・再現あり → HIGH" HIGH "$(v "$CR" "$(fl Low scripts/claude/a.sh 1 no ac:3 yes)")"
ck "B12 harness・STOP=leak・delta → HIGH" HIGH "$(v "$CR" "$(fl Medium scripts/claude/a.sh 10 no leak yes)")"
ck "B12 harness・STOP=github・delta → HIGH" HIGH "$(v "$CR" "$(fl Medium scripts/claude/a.sh 10 no github yes)")"
ck "B13 harness・Blocker・SECURITY=yes・STOP=-・outside・再現あり → BLOCKER" BLOCKER "$(v "$CR" "$(fl Blocker scripts/claude/a.sh 1 yes - yes)")"
ck "B14 guard・High・delta・再現なし → HIGH" HIGH "$(v "$CR" "$(fl High .claude/settings.json 1 no - no)")"
ck "B14 guard・Medium・delta → OK" OK "$(v "$CR" "$(fl Medium .claude/settings.json 1 no - yes)")"
printf 'LEDGER: F1 SEV=High STATUS=open SCOPE=delta KIND=harness STOP=flow REPRO=yes SECURITY=no | x\n' > "$TMP/b15_prev"
ledger "$CR" delta "$TMP/b15_prev" "$(fl High scripts/claude/a.sh 10 no - no)" >/dev/null
ck "B15 書き直しで STOP=-・再現なしにしても、止める指摘のまま（HIGH）" "HIGH yes" \
  "$(lib "$CR" ledger_verdict "$TMP/led") $(grep -q 'STOP=flow REPRO=yes' "$TMP/led" && echo yes || echo no)"
printf 'LEDGER: F1 SEV=Medium STATUS=open SCOPE=delta SECURITY=no | m\n' > "$TMP/b16"
ck "B16 前の形の台帳の行は止める側の既定値（app・STOP=-・REPRO=yes）で読む → HIGH" HIGH "$(lib "$CR" ledger_verdict "$TMP/b16")"
cat > "$TMP/b17" <<'EOF'
LEDGER: F1 SEV=High STATUS=open SCOPE=delta KIND=app STOP=- REPRO=yes SECURITY=no | a
LEDGER: F2 SEV=High STATUS=open SCOPE=delta KIND=harness STOP=- REPRO=yes SECURITY=no | b
LEDGER: F3 SEV=Low STATUS=open SCOPE=delta KIND=harness STOP=flow REPRO=yes SECURITY=no | c
LEDGER: F4 SEV=Medium STATUS=open SCOPE=outside KIND=app STOP=- REPRO=yes SECURITY=no | d
LEDGER: F5 SEV=Blocker STATUS=open SCOPE=outside KIND=harness STOP=- REPRO=yes SECURITY=yes | e
LEDGER: F6 SEV=High STATUS=resolved SCOPE=delta KIND=app STOP=- REPRO=yes SECURITY=no | f
LEDGER: F7 SEV=Medium STATUS=open SCOPE=delta KIND=guard STOP=- REPRO=no SECURITY=no | g
EOF
ck "B17 ledger_blocking は止める指摘（F1・F3・F5）だけを出し、合否は BLOCKER" "F1,F3,F5 BLOCKER" \
  "$(lib "$CR" ledger_blocking "$TMP/b17" | awk '{print $2}' | paste -sd, -) $(lib "$CR" ledger_verdict "$TMP/b17")"
ck "B 形: 新しい欄（LINE・STOP）の無い FINDING 行は形の崩れ" PARSE_ERROR "$(v "$CR" 'FINDING: F1 SEV=High STATUS=open FILE=backend/x.py SECURITY=no | 古い形')"

# ---------------- W 本体の通し ----------------
ES="$TMP/e2e_stub"; mkdir -p "$ES"
printf 'jobs:\n  j:\n    name: J\n' > "$ES/wf.yml"
cat > "$ES/gh" <<'SH'
#!/usr/bin/env bash
case "$*" in
  "pr list"*) echo 7 ;;
  *headRefOid*) git rev-parse HEAD ;;
  "pr checks"*"--json"*) printf 'pass\tJ\n' ;;
  *) exit 0 ;;
esac
SH
cat > "$ES/claude" <<'PY'
#!/usr/bin/env python3
# code-reviewer（--agent）には $E2E_REVIEW を stream-json で返し、入力を $E2E_IN に書く。組み込みのレビューには「指摘なし」
import json, os, sys
args = sys.argv[1:]
if "--agent" in args:
    open(os.environ["E2E_IN"], "w").write(sys.stdin.read())
    body = open(os.environ["E2E_REVIEW"]).read()
    print(json.dumps({"type": "system", "subtype": "init", "session_id": "s"}))
    print(json.dumps({"type": "result", "subtype": "success", "result": body, "permission_denials": []}))
else:
    print("指摘なし")
PY
chmod +x "$ES/gh" "$ES/claude"
# e2e <名前> <写し> <変えるファイル> <レビュー役の本文>: 一時のリポジトリで本体を丸ごと動かす（変えるファイルの 2 行目を足す）
e2e() { local n="$1" src="$2" f="$3" E="$TMP/e2e_$1" O="$TMP/e2e_$1.git"
  mkdir -p "$E/scripts/claude" "$E/docs/issues/open" "$E/docs/reviews" "$(dirname "$E/$f")"
  cp "$src" "$E/scripts/claude/code-review.sh"; cp "$REPO_ROOT/scripts/claude/review-process-lib.sh" "$E/scripts/claude/"
  printf '# I900\n' > "$E/docs/issues/open/I900.md"; printf 'l1\n' > "$E/$f"
  printf '# 計画レビュー\n\n## 高リスク判定\n判定: No\n' > "$E/docs/reviews/I900_plan_review_20260101_0000.md"
  git init -q --bare "$O"; git -C "$E" init -q -b develop; git -C "$E" add -A; git -C "$E" commit -qm base
  git -C "$E" remote add origin "$O"; git -C "$E" push -q origin develop 2>/dev/null
  git -C "$E" checkout -q -b feature/I900-x; printf 'l2\n' >> "$E/$f"; git -C "$E" add -A; git -C "$E" commit -qm change
  printf '%b' "$4" > "$TMP/review_$n.txt"
  (cd "$E" && PATH="$ES:$PATH" CLAUDE_BIN="$ES/claude" E2E_IN="$TMP/in_$n.txt" E2E_REVIEW="$TMP/review_$n.txt" CI_WORKFLOWS="$ES/wf.yml" \
     CI_WAIT_TIMEOUT=5 CI_POLL_INTERVAL=1 bash scripts/claude/code-review.sh I900 > "$TMP/out_$n.txt" 2>&1)
  find "$E/docs/reviews" -name 'I900_code_review_*.md' | LC_ALL=C sort | tail -1; }
fv() { sed -n 's/^FINAL_VERDICT: //p' "$TMP/out_$1.txt"; }
W1_REC=$(e2e w1 "$CR" a.py '# r\n\n## 台帳\nFINDING: F1 SEV=Medium STATUS=open FILE=a.py LINE=2 SECURITY=no STOP=- | m | 再現: x\n\nVERDICT: OK\n')
ck "W1 アプリ本体の全体のレビュー: code-reviewer が VERDICT: OK でも、変えた行の Medium（再現あり）で HIGH" HIGH "$(fv w1)"
ck "W3 記録に「止める指摘（スクリプトが決めた」の節と F1・台帳に KIND=app" "yes yes yes" \
  "$(grep -qF '## 止める指摘（スクリプトが決めた' "$W1_REC" && echo yes || echo no) $(grep -q '^- F1 SEV=Medium' "$W1_REC" && echo yes || echo no) $(grep -q '^LEDGER: F1 .*KIND=app' "$W1_REC" && echo yes || echo no)"
ck "W4 code-reviewer への入力に「変更の種類」の節と app・a.py の行" "yes yes" \
  "$(grep -qF '### 変更の種類' "$TMP/in_w1.txt" && echo yes || echo no) $(grep -qxF "$(printf 'app\ta.py')" "$TMP/in_w1.txt" && echo yes || echo no)"
W2_BODY='# r\n\n## 台帳\nFINDING: F1 SEV=Low STATUS=open FILE=a.py LINE=2 SECURITY=no STOP=- | l | 再現: x\n\nVERDICT: HIGH\n'
e2e w2 "$CR" a.py "$W2_BODY" >/dev/null
ck "W2 全体のレビュー: code-reviewer が VERDICT: HIGH でも、Low だけなら OK" OK "$(fv w2)"
e2e w5 "$CR" a.py '# r\n\n| High | 表の中にだけ書いた指摘 |\n\nVERDICT: HIGH\n' >/dev/null
ck "W5 全体のレビュー: VERDICT: HIGH なのに読める FINDING 行が無い → BLOCKER" BLOCKER "$(fv w5)"
W6_REC=$(e2e w6 "$CR" scripts/claude/h.sh '# r\n\n## 台帳\nFINDING: F1 SEV=High STATUS=open FILE=scripts/claude/h.sh LINE=2 SECURITY=no STOP=- | h | 再現: x\n\nVERDICT: HIGH\n')
ck "W6 ハーネスの全体のレビュー: STOP=- の High だけなら OK・台帳に KIND=harness で残る" "OK yes" \
  "$(fv w6) $(grep -q '^LEDGER: F1 SEV=High STATUS=open SCOPE=delta KIND=harness STOP=-' "$W6_REC" && echo yes || echo no)"

# ---------------- D 指示ファイル ----------------
CRV=.claude/agents/code-reviewer.md; RG=.claude/skills/review-gate/SKILL.md; FL=.claude/skills/fix-loop/SKILL.md
RT=.claude/skills/retro/SKILL.md; RR=docs/runbooks/review-rules.md
d1() { grep -qF 'LINE=' "$1" && grep -qF 'STOP=' "$1" && grep -qF '| 再現:' "$1" && grep -qF 'flow' "$1" && grep -qF 'leak' "$1" \
       && grep -qF 'github' "$1" && grep -qF 'ac:' "$1" && ! grep -qF '## コード品質・セキュリティ指摘' "$1"; }
d2() { grep -qF '最後の安全網' "$1" && grep -qF '止める指摘（スクリプトが決めた' "$1" && grep -qF 'イシューに関係する Medium' "$1"; }
d3() { grep -qF '止める指摘（スクリプトが決めた' "$1" && ! grep -qF '止める指摘（Blocker・High）' "$1"; }
d4() { grep -qF "grep -h '^LEDGER: .*STATUS=open'" "$1" && grep -qF '最優先' "$1"; }
d5() { grep -qF '関所の穴' "$1" && grep -qF '最後の安全網' "$1" && ! grep -qF '止めるのは High 以上だけ' "$1"; }
ck "D1 code-reviewer に新しい FINDING 行の欄と止める条件があり、指摘の表が無い" 0 "$(rc d1 "$CRV")"
ck "D2 review-gate に最後の安全網・止める指摘の節・アプリ本体の Medium の扱い" 0 "$(rc d2 "$RG")"
ck "D3 fix-loop は止める指摘の節だけを直す" 0 "$(rc d3 "$FL")"
ck "D4 retro に台帳の残りを拾うコマンドと最優先" 0 "$(rc d4 "$RT")"
ck "D5 review-rules に関所の穴・最後の安全網があり、古い基準の文が無い" 0 "$(rc d5 "$RR")"
# without <ファイル> <消す語>: 写しから語を含む行を消す
without() { local o="$TMP/w_$RANDOM$RANDOM"; grep -vF -- "$2" "$1" > "$o"; echo "$o"; }
ck "FG-D1 code-reviewer から LINE= を消すと不合格" 1 "$(rc d1 "$(without "$CRV" 'LINE=')")"
ck "FG-D2 review-gate から最後の安全網を消すと不合格" 1 "$(rc d2 "$(without "$RG" '最後の安全網')")"
ck "FG-D3 fix-loop から止める指摘の節を消すと不合格" 1 "$(rc d3 "$(without "$FL" '止める指摘（スクリプトが決めた')")"
ck "FG-D4 retro からコマンドを消すと不合格" 1 "$(rc d4 "$(without "$RT" "grep -h '^LEDGER: .*STATUS=open'")")"
ck "FG-D5 review-rules から関所の穴を消すと不合格" 1 "$(rc d5 "$(without "$RR" '関所の穴')")"

# ---------------- FG（判定の要） ----------------
ck "FG-B5 再現の検査を消すと B5 が不合格（HIGH）" HIGH "$(v "$(broken '    if repro != "yes":' '    if False:')" "$(fl High backend/x.py 10 no - no)")"
ck "FG-B6 差分の外のセキュリティの Blocker の扱いを消すと B6 が不合格（OK）" OK "$(v "$(broken '    if sec_blocker:' '    if False:')" "$(fl Blocker backend/x.py 1 yes - yes)")"
ck "FG-B8 ハーネスを重大度で決めると B8 が不合格（OK）" OK "$(v "$(broken '    return bool(STOP_RE.fullmatch(stop))' '    return RANK[sev] >= 2')" "$(fl Low scripts/claude/a.sh 10 no flow yes)")"
ck "FG-B11 STOP を何でも当たるにすると B11 が不合格（HIGH）" HIGH "$(v "$(broken 'STOP_RE = re.compile(r"flow|leak|github|ac:[0-9]+")' 'STOP_RE = re.compile(r".*")')" "$(fl High scripts/claude/a.sh 10 no other yes)")"
ck "FG-L2 前後の行数を 0 にすると L2 が不合格（outside）" outside "$(scope "$(fx backend/x.py 13)" "$(broken 'HUNK_MARGIN = 3' 'HUNK_MARGIN = 0')")"
ck "FG-L8 casefold を外すと L8 が不合格（outside）" outside "$(scope "$(fx Docs/up.md 5)" "$(broken 'hunks.get(norm.casefold(), [])' 'hunks.get(norm, [])')")"
ck "FG-L9 全部を delta にすると L9 が不合格（delta）" delta "$(HUNKS="$TMP/h_full2" scope "$(fx old.txt 9)" "$(broken '        if stop.startswith("ac:") or path == "-":' '        if True:')")"
ck "FG-K1 harness の場所から .claude/ を外すと K1 が不合格（app）" app \
  "$(lib "$(broken 'HARNESS_PREFIX = (".claude/", ' 'HARNESS_PREFIX = (')" ledger_kinds "$TMP/kpaths" | sed -n 8p | cut -f1)"
BW2=$(broken "grep -qE '^VERDICT:[[:space:]]*(BLOCKER|HIGH|OK)[[:space:]]*\$' \"\$REVIEW_FILE\" && REVIEWER_VERDICT=OK || REVIEWER_VERDICT=BLOCKER" 'REVIEWER_VERDICT="$LLM_VERDICT"')
e2e fgw2 "$BW2" a.py "$W2_BODY" >/dev/null
ck "FG-W2 LLM の VERDICT を合否に使うと W2 が不合格（HIGH）" HIGH "$(fv fgw2)"
BH7=$(broken '--src-prefix=a/ --dst-prefix=b/ "$mb" HEAD' '"$mb" HEAD')
ck "FG-H7 接頭辞の固定を外すと H7 が不合格（10〜10 が出ない）" no \
  "$(inR lib "$BH7" delta_hunks develop "" 2>/dev/null | grep -qxF "$(printf 'backend/x.py\t10\t10')" && echo yes || echo no)"
ck "FG-H8 見出しを最初の @@ までに限る判定を外すと H8 が不合格" no \
  "$(inR lib "$(broken '        elif head and line.startswith("+++ "):' '        elif line.startswith("+++ "):')" delta_hunks develop "" 2>/dev/null | grep -qxF "$(printf 'old.txt\t8\t8')" && echo yes || echo no)"
ck "FG-H9 読めなかったファイルをファイル全体にする処理を外すと H9 が不合格" no \
  "$(lib "$(broken '        a[p] = b[p] = WHOLE' '        pass')" hunks_from_diff "$TMP/h9_list" "$TMP/h9_a" | grep -q '^b.txt' && echo yes || echo no)"
BH10=$(broken '[len("+++ b/"):].rstrip("\t")' '[len("+++ b/"):]')
ck "FG-H10 行末のタブを取り除く処理を外すと H10 が不合格（3 列の 1 行にならない）" no \
  "$([ "$(inR lib "$BH10" delta_hunks develop "" 2>/dev/null | grep '^sp ace.md')" = "$(printf 'sp ace.md\t1\t3')" ] && echo yes || echo no)"
ck "FG-H10b 列を後ろから読む処理を外すと H10 が不合格（台帳の作成が落ちる）" 1 \
  "$(rc inR lib "$(broken 'p, s, e = l.rsplit("\t", 2)' 'p, s, e = l.split("\t")')" ledger_update full "" "$TMP/h10.md" "$TMP/h10_hunks")"
ck "FG の写しがすべて作れた（置き換え前の文字列が本体にある）" no "$([ -e "$TMP/broken_failed" ] && echo yes || echo no)"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
