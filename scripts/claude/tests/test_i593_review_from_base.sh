#!/usr/bin/env bash
# shellcheck disable=SC2016,SC1091  # 単一引用符の \$ は、置き換え元・照合の文字どおりの文字列（展開させない）
# I593: 判定の仕組みを変える PR を変更前の版で審査する（plan_I593.md・docs/tests/open/I593_auto_test.md の TC）。
#   TC-01 高リスクの集合（review_mechanism_trigger）／TC-02 集合の説明の一致／TC-03 定義の変換（reviewer-agents-lib.sh）／
#   TC-04 審査の入口の呼び方／TC-06 写しで動かなかったときの高リスク／TC-07・TC-08 テストを弱める差分／TC-09 STOP=test／
#   TC-10 gate-check は BASE の判定の関数を使う／TC-11 写しの中身と壊れたフォルダ／TC-12 python3 -I
#   （TC-05 の起動役は scripts/claude/tests/i599_cases.py の TC-I593-05*）
# 一時の git リポジトリ・写しのダミーを使い、本物のファイルを書き換えない。各 TC に失敗の注入（FG）を付ける。
# 実行: bash scripts/claude/tests/test_i593_review_from_base.sh
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
CR=scripts/claude/code-review.sh
RAL=scripts/claude/reviewer-agents-lib.sh
GC=scripts/claude/gate-check.sh
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ck() { # name expected actual
  if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1))
  else printf 'FAIL %s  expected[%s] got[%s]\n' "$1" "$2" "$3"; fail=$((fail+1)); fi
}
rc() { "$@" >/dev/null 2>&1; echo $?; }
# broken <元のファイル> <置き換え元> <置き換え先>: 1 か所だけ置き換えた写しのパスを出す（置き換え元が無ければ印を残す）
broken() { local out; out="$TMP/broken_$RANDOM$RANDOM"
  python3 -I -c 'import sys
s=open(sys.argv[1],encoding="utf-8").read()
if sys.argv[2] not in s: open(sys.argv[4]+".missing","w").close()
open(sys.argv[4],"w",encoding="utf-8").write(s.replace(sys.argv[2],sys.argv[3],1))' "$1" "$2" "$3" "$out"
  [ -e "$out.missing" ] && touch "$TMP/broken_failed"; printf '%s\n' "$out"; }
# lib <code-review.sh の写し> <関数> [引数…]: 関数だけを読み込んで呼ぶ
lib() { local f="$1"; shift; REVIEW_LIB_SOURCE_ONLY=1 bash -c '. "$1"; shift; "$@"' _ "$f" "$@"; }
G() { git -c user.name=t -c user.email=t@example.invalid "$@"; }

# ---------------- TC-01: 高リスクの集合 ----------------
YES_PATHS=(.claude/hooks/unreviewed.py .claude/hooks/reviewed-hook.sh .claude/skills/review-gate/SKILL.md .claude/skills/test-gate/SKILL.md
           .claude/skills/fix-loop/SKILL.md .claude/skills/plan-review/SKILL.md scripts/claude/gate-check.sh .github/workflows/ci.yml)
NO_PATHS=(.claude/skills/retro/SKILL.md .claude/skills/review-gate-x/SKILL.md scripts/claude/code-review.sh .claude/agents/code-reviewer.md
          docs/runbooks/review-rules.md scripts/claude/gate-check.sh.bak backend/a.py)
tc01() { local f="$1" p
  for p in "${YES_PATHS[@]}"; do [ "$(lib "$f" path_risk_trigger "$p")" = YES ] || return 1; done
  for p in "${NO_PATHS[@]}"; do [ "$(lib "$f" path_risk_trigger "$p")" = NO ] || return 1; done
  [ "$(lib "$f" path_risk_trigger "$(printf 'backend/a.py\n.claude/skills/test-gate/SKILL.md')")" = YES ]; }
ck "TC-01 審査の部品のパスで YES・ほかのスキル・似た名前・審査の入口と定義で NO" 0 "$(rc tc01 "$CR")"
for pat in '.claude/hooks/\*|' '.claude/skills/review-gate/\*|' '.claude/skills/test-gate/\*|' '.claude/skills/fix-loop/\*|' '.claude/skills/plan-review/\*|' '|scripts/claude/gate-check.sh)'; do
  plain="${pat//\\/}"; repl="${plain//|/}"; [ "${plain: -1}" = ")" ] && repl=")"
  ck "FG-TC-01 集合から ${plain} を外すと不合格" 1 "$(rc tc01 "$(broken "$CR" "$plain" "$repl")")"
done
ck "FG-TC-01 path_risk_trigger を guard だけにすると不合格" 1 \
  "$(rc tc01 "$(broken "$CR" ' || [ "$(review_mechanism_trigger "$1")" = YES ]' '')")"

# ---------------- TC-02: 集合の説明の一致（guard は TC-K2・S12・i181 が見る。ここは審査の部品の集合） ----------------
tc02() { python3 -I - "$@" <<'PY'
import re, sys
crs, md = sys.argv[1:3]
case = [l for l in open(crs, encoding="utf-8").read().split("\n") if re.match(r"^\s+\.claude/hooks/\*\|", l)]
if len(case) != 1:
    sys.exit(1)
want = set(case[0].strip().split(")")[0].split("|"))
rows = [l for l in open(md, encoding="utf-8").read().split("\n") if "変更前の版で動かせない判定の部品" in l and "`.claude/hooks/*`" in l]
if len(rows) != 1:
    sys.exit(1)
head = rows[0].split("変更前の版で動かせない判定の部品の変更", 1)[1].split("正は")[0]
if set(re.findall(r"`([^`]+)`", head)) != want:
    sys.exit(1)
PY
}
# 定義に path_risk_trigger の集合（例外のファイル・判定の部品）のパスが 1 つも無い（写しが戻っていない）: <code-review.sh> <定義> → 無ければ 0
tc02b() { python3 -I - "$@" <<'PY'
import re, sys
crs, md = sys.argv[1:3]
src = open(crs, encoding="utf-8").read().split("\n")
paths = set()
for pat in (r"^\s+\.github/\*\|", r"^\s+\.claude/hooks/\*\|"):
    case = [l for l in src if re.match(pat, l)]
    if len(case) != 1:
        sys.exit(2)
    paths |= set(case[0].strip().split(")")[0].split("|"))
body = open(md, encoding="utf-8").read()
sys.exit(1 if any("`" + x + "`" in body for x in paths) else 0)
PY
}
# I547: 一覧の正は review-rules.md の 1 か所（2 つのレビュー役は「高リスク判定の条件」の節を参照する）。定義に写しが戻らないことも見る
RRM=docs/runbooks/review-rules.md
ck "TC-02 審査の部品の集合が review-rules.md の行と一致" 0 "$(rc tc02 "$CR" "$RRM")"
ck "FG-TC-02 review-rules.md から scripts/claude/gate-check.sh を消すと不合格" 1 "$(rc tc02 "$CR" "$(broken "$RRM" '・`scripts/claude/gate-check.sh`' '')")"
for m in .claude/agents/code-reviewer.md .claude/agents/plan-reviewer.md; do
  ck "TC-02b ${m} に高リスクのパスの一覧の写しが無い" 0 "$(rc tc02b "$CR" "$m")"
done
ck "FG-TC-02b 定義に .github/* を書くと不合格" 1 "$(rc tc02b "$CR" "$(broken .claude/agents/code-reviewer.md '## 高リスク判定の参照' '## 高リスク判定の参照 `.github/*`')")"

# ---------------- TC-03: 定義の変換 ----------------
SNAP="$TMP/snap"; mkdir -p "$SNAP/scripts/claude" "$SNAP/.claude/agents" "$SNAP/docs/runbooks"
cp "$RAL" "$SNAP/scripts/claude/"; touch "$SNAP/.complete"; printf '# 決まり\n' > "$SNAP/docs/runbooks/review-rules.md"
printf -- '---\nname: code-reviewer\ndescription: d: 説明\ntools: Read, Grep, Glob\nmodel: sonnet\n---\n\nSNAPSHOT_BODY 決まりは `docs/runbooks/review-rules.md`\n' > "$SNAP/.claude/agents/code-reviewer.md"
tc03() { local s="$1" out="$TMP/tc03_$RANDOM"
  ( . "$s/scripts/claude/reviewer-agents-lib.sh" && reviewer_agent_args code-reviewer "$out" && printf '%s\n' "${REVIEWER_ARGS[@]}" > "$out/args" ) || return 1
  python3 -I - "$out/agents.json" "$s" <<'PY' || return 1
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))["code-reviewer"]
s = sys.argv[2]
ok = (d["tools"] == ["Read", "Grep", "Glob"] and d["model"] == "sonnet" and d["description"] == "d: 説明"
      and "SNAPSHOT_BODY" in d["prompt"] and f"`{s}/docs/runbooks/review-rules.md`" in d["prompt"])
sys.exit(0 if ok else 1)
PY
  [ "$(paste -sd' ' "$out/args")" = "--agents $out/agents.json --agent code-reviewer --add-dir $s" ]; }
ck "TC-03 写しの定義が JSON になり、決まりの参照が写しの版に置き換わり、--add-dir に写し" 0 "$(rc tc03 "$SNAP")"
bad_def() { local s="$TMP/bad_$1"; rm -rf "$s"; cp -R "$SNAP" "$s"; printf '%b' "$2" > "$s/.claude/agents/code-reviewer.md"; tc03 "$s"; }
ck "FG-TC-03 前書きに未知の鍵（permissionMode）があると非 0" 1 "$(rc bad_def k '---\nname: code-reviewer\ndescription: d\npermissionMode: bypassPermissions\n---\nx\n')"
ck "FG-TC-03 前書きが閉じていないと非 0" 1 "$(rc bad_def c '---\nname: code-reviewer\ndescription: d\nx\n')"
ck "FG-TC-03 name が違うと非 0" 1 "$(rc bad_def n '---\nname: other\ndescription: d\n---\nx\n')"
ck "FG-TC-03 定義が無いと非 0（2）" 2 "$(rc bash -c 's="$1"; rm -f "$s/.claude/agents/code-reviewer.md"; . "$s/scripts/claude/reviewer-agents-lib.sh"; reviewer_agent_args code-reviewer "$2"' _ "$(cp -R "$SNAP" "$TMP/nodef" && echo "$TMP/nodef")" "$TMP/nodef_out")"
ck "FG-TC-03 写しに決まりが無いと非 0（2）" 2 "$(rc bash -c 's="$1"; rm -f "$s/docs/runbooks/review-rules.md"; . "$s/scripts/claude/reviewer-agents-lib.sh"; reviewer_agent_args code-reviewer "$2"' _ "$(cp -R "$SNAP" "$TMP/norules" && echo "$TMP/norules")" "$TMP/norules_out")"
# 下の FG で使う tc03 の定義を書き出しておく（bash -c の中から呼ぶため）
declare -f tc03 > "$TMP/tc03_fn.sh"
ck "FG-TC-03 決まりの置き換えを外すと不合格" 1 \
  "$(rc bash -c 's="$1"; cp "$2" "$s/scripts/claude/reviewer-agents-lib.sh"; . "$3"; tc03 "$s"' _ "$(cp -R "$SNAP" "$TMP/norepl2" && echo "$TMP/norepl2")" \
     "$(broken "$RAL" 'body = body.replace("docs/runbooks/review-rules.md", rules)' 'pass')" "$TMP/tc03_fn.sh")"
ck "TC-03 実物の 5 つの定義がすべて変換できる" 0 "$(rc bash -c '. "$1"; for a in code-reviewer plan-reviewer adversarial-reviewer issue-reviewer fix-diagnosis-reviewer; do reviewer_agent_args "$a" "$2/$a" || exit 1; done' _ "$RAL" "$TMP/real")"

# ---------------- TC-04: 審査の入口はレビュー役を REVIEWER_ARGS だけで起こす ----------------
ENTRIES=(scripts/claude/code-review.sh scripts/claude/adversarial-review.sh scripts/claude/plan-issue-review.sh scripts/claude/issue-review.sh scripts/claude/fix-review-lib.sh)
tc04() { local f
  for f in "$@"; do
    grep -vE '^[[:space:]]*#' "$f" | grep -qE -- '--agent[[:space:]]+("|[a-z])' && return 1
    grep -qE 'reviewer_agent_args[[:space:]]+"?\$?[A-Za-z_-]' "$f" || return 1
    grep -qF '"${REVIEWER_ARGS[@]}"' "$f" || return 1
  done; }
ck "TC-04 審査の入口 5 本に --agent の直書きが無く、reviewer_agent_args と REVIEWER_ARGS を使う" 0 "$(rc tc04 "${ENTRIES[@]}")"
ck "FG-TC-04 code-review.sh に --agent \"\$REVIEWER_AGENT\" を戻すと不合格" 1 \
  "$(rc tc04 "$(broken "$CR" '    "${REVIEWER_ARGS[@]}" --tools' '    --agent "$REVIEWER_AGENT" --tools')")"
ck "FG-TC-04 adversarial-review.sh に --agent adversarial-reviewer を戻すと不合格" 1 \
  "$(rc tc04 "$(broken scripts/claude/adversarial-review.sh '    "${REVIEWER_ARGS[@]}" --tools' '    --agent adversarial-reviewer --tools')")"
# fix-review-lib.sh を差し替えの claude で流し、受け取った引数に写しの agents.json がある
FS="$TMP/fsnap"; mkdir -p "$FS/scripts/claude" "$FS/.claude/agents" "$FS/docs/runbooks" "$TMP/fbin"
cp scripts/claude/fix-review-lib.sh "$RAL" "$FS/scripts/claude/"; cp .claude/agents/fix-diagnosis-reviewer.md "$FS/.claude/agents/"
printf 'x\n' > "$FS/docs/runbooks/review-rules.md"; touch "$FS/.complete"
printf '#!/usr/bin/env bash\nprintf "%%s\\n" "$@" > "$ARGS_OUT"; for a in "$@"; do case "$a" in *agents.json) cp "$a" "$ARGS_OUT.json";; esac; done; printf "VERDICT: OK\\n"\n' > "$TMP/fbin/claude"
chmod +x "$TMP/fbin/claude"
tc04run() { local d="$TMP/frepo_$RANDOM"; mkdir -p "$d"; G -C "$d" init -q -b main; G -C "$d" commit -q --allow-empty -m b
  ( cd "$d" && export CLAUDE_BIN="$TMP/fbin/claude" ARGS_OUT="$d/args" PATH="$TMP/nogh:$PATH"
    REVIEW_LIB_SOURCE_ONLY=1 . "$1/scripts/claude/fix-review-lib.sh" && run_fix_review I900 diagnosis .claude/agents/fix-diagnosis-reviewer.md ctx x >/dev/null 2>&1 )
  grep -qx -- '--agents' "$d/args" && grep -qx -- '--add-dir' "$d/args" && grep -qx -- "$1" "$d/args" \
    && python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if "fix-diagnosis-reviewer" in d else 1)' "$d/args.json"; }
mkdir -p "$TMP/nogh"; printf '#!/bin/sh\nexit 1\n' > "$TMP/nogh/gh"; chmod +x "$TMP/nogh/gh"
ck "TC-04 fix-review-lib.sh は写しの定義を --agents・写しを --add-dir で渡して claude を起こす" 0 "$(rc tc04run "$FS")"

# ---------------- TC-06: 写しで動かなかったときの高リスク ----------------
tc06() { local s="$1" w="$2"
  [ "$(cd "$w" && REVIEW_LIB_SOURCE_ONLY=1 bash -c '. "$1/scripts/claude/reviewer-agents-lib.sh"; . "$2"; reviewer_source_risk' _ "$s" "$3")" = NO ] || return 1
  [ "$(cd "$w" && REVIEW_LIB_SOURCE_ONLY=1 bash -c '. "$1/scripts/claude/reviewer-agents-lib.sh"; . "$2"; reviewer_source_risk' _ "$w" "$3")" = YES ] || return 1
  [ "$(cd "$w" && REVIEW_LIB_SOURCE_ONLY=1 bash -c '. "$1"; reviewer_source_risk' _ "$3")" = YES ]; }
WREPO="$TMP/wrepo"; mkdir -p "$WREPO/scripts/claude"; cp "$RAL" "$WREPO/scripts/claude/"; G -C "$WREPO" init -q -b main
ck "TC-06 写しから NO・作業ツリーから YES・判定の部品が無ければ YES（fail-closed）" 0 "$(rc tc06 "$SNAP" "$WREPO" "$REPO_ROOT/$CR")"
ck "FG-TC-06 判定を常に NO にすると不合格" 1 "$(rc tc06 "$SNAP" "$WREPO" "$(broken "$CR" '  if declare -F reviewer_from_snapshot >/dev/null && reviewer_from_snapshot; then echo NO; else echo YES; fi' '  echo NO')")"
cp -R "$WREPO" "$TMP/wrepo_c"; touch "$TMP/wrepo_c/.complete"
ck "FG-TC-06 作業ツリーに .complete を置いても写しにならない（最上位が同じ）" 0 "$(rc tc06 "$SNAP" "$TMP/wrepo_c" "$REPO_ROOT/$CR")"
# plan-issue-review.sh: 作業ツリーの版で流れた記録は高リスク Yes・VERDICT HIGHRISK
PIR=scripts/claude/plan-issue-review.sh
tc06p() { local f="$TMP/pr_$RANDOM.md"
  printf '# r\n## 判定: ✅ 完了\n\n## 高リスク判定\n判定: No\n理由\n\nVERDICT: OK\n' > "$f"
  lib "$1" force_plan_highrisk "$f" || return 1
  [ "$(lib "$1" detect_plan_verdict "$f")" = HIGHRISK ] \
    && awk '/^## 高リスク判定/ { s=1; next } s && /^## / { s=0 } s && /^判定:/ { print; exit }' "$f" | grep -qx '判定: Yes'; }
ck "TC-06 計画レビューの記録を作業ツリーの版で書いたら 判定: Yes・VERDICT HIGHRISK" 0 "$(rc tc06p "$PIR")"
ck "FG-TC-06 判定の行を Yes にしないと不合格" 1 "$(rc tc06p "$(broken "$PIR" '    s && !done && /^判定:/ { print "判定: Yes"; done=1; next }' '')")"
ck "FG-TC-06 計画レビューで写しの確かめを外すと（呼び出しが消えると）不合格" 1 \
  "$(rc grep -qF 'reviewer_from_snapshot || force_plan_highrisk "$REVIEW_FILE"' "$(broken "$PIR" 'reviewer_from_snapshot || force_plan_highrisk "$REVIEW_FILE"' '')")"
ck "TC-06 code-review.sh の本体が RISK_SOURCE を高リスクに入れる" 0 "$(rc grep -qF 'RISK_FINAL=$(combine_risk "$RISK_FINAL" "$RISK_SOURCE")' "$CR")"

# ---------------- TC-07: テストを弱める差分 ----------------
TW="$TMP/tw"; mkdir -p "$TW/backend/x/tests" "$TW/frontend/src/__tests__" "$TW/scripts/claude/tests" "$TW/e2e"
cat > "$TW/backend/x/tests/test_a.py" <<'PY'
def test_one():
    assert 1 == 1
    assert 2 == 2

def test_two():
    assert True
PY
printf 'it("a", () => { expect(1).toBe(1); });\ntest("b", () => { expect(2).toBe(2); });\n' > "$TW/frontend/src/__tests__/a.test.tsx"
printf 'ck a 1 1\nck b 2 2\nck_true c true\n' > "$TW/scripts/claude/tests/test_s.sh"
printf 'def test_gone():\n    assert 1\n' > "$TW/backend/x/tests/test_gone.py"
printf 'def f():\n    return 1\n' > "$TW/backend/x/views.py"
printf 'def test_r1():\n    assert 1\n\ndef test_r2():\n    assert 2\n' > "$TW/backend/x/tests/test_r.py"
G -C "$TW" init -q -b main; G -C "$TW" add -A; G -C "$TW" commit -q -m base; TWB=$(git -C "$TW" rev-parse HEAD)
cat > "$TW/backend/x/tests/test_a.py" <<'PY'
import pytest

@pytest.mark.skip(reason="x")
def test_one():
    assert 1 == 1

def test_two():
    pytest.xfail("y")
PY
printf 'it.only("a", () => { expect(1).toBe(1); });\ntest.todo("b");\ntest.fixme("c", () => {});\n' > "$TW/frontend/src/__tests__/a.test.tsx"
printf 'ck a 1 1\nck_true c true\n' > "$TW/scripts/claude/tests/test_s.sh"
rm "$TW/backend/x/tests/test_gone.py"
printf 'def f():\n    skip = 1\n    return skip\n' > "$TW/backend/x/views.py"
printf 'def test_r2():\n    assert 2\n\ndef test_r1():\n    assert 1\n' > "$TW/backend/x/tests/test_r.py"
G -C "$TW" add -A; G -C "$TW" commit -q -m change
tw() { (cd "$TW" && lib "$REPO_ROOT/$1" test_weakening_report "$TWB" HEAD); }
tc07() { local out; out=$(tw "$1") || return 1
  printf '%s\n' "$out" > "$TMP/tw_out"
  grep -qx 'TEST_WEAKENING: deleted backend/x/tests/test_gone.py' "$TMP/tw_out" || return 1
  grep -qx 'TEST_WEAKENING: fewer-checks backend/x/tests/test_a.py 3->1' "$TMP/tw_out" || return 1
  grep -qx 'TEST_WEAKENING: fewer-tests frontend/src/__tests__/a.test.tsx 2->0' "$TMP/tw_out" || return 1
  grep -qx 'TEST_WEAKENING: fewer-checks scripts/claude/tests/test_s.sh 3->2' "$TMP/tw_out" || return 1
  grep -qE '^TEST_WEAKENING: skip backend/x/tests/test_a.py:3 @pytest\.mark\.skip' "$TMP/tw_out" || return 1
  grep -qE '^TEST_WEAKENING: skip backend/x/tests/test_a.py:[0-9]+ pytest\.xfail' "$TMP/tw_out" || return 1
  grep -qE '^TEST_WEAKENING: skip frontend/src/__tests__/a.test.tsx:1 it\.only' "$TMP/tw_out" || return 1
  grep -qE '^TEST_WEAKENING: skip frontend/src/__tests__/a.test.tsx:2 test\.todo' "$TMP/tw_out" || return 1
  grep -qE '^TEST_WEAKENING: skip frontend/src/__tests__/a.test.tsx:3 test\.fixme' "$TMP/tw_out" || return 1
  ! grep -q 'views.py' "$TMP/tw_out" || return 1
  ! grep -q 'test_r.py' "$TMP/tw_out"; }
ck "TC-07 消した・数の減った・スキップを足したテストを拾い、テストでないファイルと並べ替えは拾わない" 0 "$(rc tc07 "$CR")"
ck "TC-07 何も無いときは なし" "TEST_WEAKENING: なし" "$(cd "$TW" && lib "$REPO_ROOT/$CR" test_weakening_report HEAD HEAD)"
ck "FG-TC-07 .only の目印を外すと不合格" 1 "$(rc tc07 "$(broken "$CR" '|only|todo|fixme)\b|' '|todo|fixme)\b|')")"
ck "FG-TC-07 消したファイルを見ないと不合格" 1 "$(rc tc07 "$(broken "$CR" '        out.append(f"deleted {p}")' '        pass')")"
ck "FG-TC-07 テストのファイルの判定を全部にすると views.py が出て不合格" 1 "$(rc tc07 "$(broken "$CR" '    if p.startswith("scripts/claude/tests/") or p.startswith("e2e/"):' '    if True:')")"
ck "FG-TC-07 確かめの数を見ないと不合格" 1 "$(rc tc07 "$(broken "$CR" '        for kind, table in (("fewer-tests", TESTS), ("fewer-checks", CHECKS)):' '        for kind, table in (("fewer-tests", TESTS),):')")"

# ---------------- TC-08: 入力と記録に載る ----------------
tc08() { local f="$1" out
  out=$(cd "$TW" && G remote add origin "$TW" 2>/dev/null; G -C "$TW" update-ref refs/remotes/origin/develop "$TWB"; lib "$REPO_ROOT/$f" weakening_section origin/develop) || return 1
  printf '%s\n' "$out" | grep -q '^TEST_WEAKENING: deleted backend/x/tests/test_gone.py$' || return 1
  grep -qF 'WEAKENING=$(weakening_section origin/develop)' "$f" || return 1
  grep -qF '### テストを弱めうる差分（決定論・I593' "$f" || return 1
  grep -qF '${WEAKENING}' "$f" || return 1
  grep -qF 'GATE_EVIDENCE+="- テストを弱めうる差分（ブランチ全体・I593）:"' "$f"; }
ck "TC-08 ブランチ全体の差分を数え、本体がレビュー役の入力と証跡（記録）に入れる" 0 "$(rc tc08 "$CR")"
ck "FG-TC-08 証跡への追加を消すと不合格" 1 "$(rc tc08 "$(broken "$CR" 'GATE_EVIDENCE+="- テストを弱めうる差分（ブランチ全体・I593）:"' 'X="')")"
ck "FG-TC-08 入力の節を消すと不合格" 1 "$(rc tc08 "$(broken "$CR" '### テストを弱めうる差分（決定論・I593' '### x')")"

# ---------------- TC-09: STOP=test は止める ----------------
tc09() { local f="$1" d="$TMP/l9_$RANDOM"; mkdir -p "$d"
  printf 'b.py\t1\t5\nscripts/claude/tests/t.sh\t1\t5\n' > "$d/hunks"; printf 'backend/x/tests/test_a.py\nscripts/claude/tests/t.sh\n' > "$d/own"
  printf 'backend/x/tests/test_a.py\t1\t5\n' >> "$d/hunks"
  # F3: 実在するファイルで、行が変更の塊（1〜2 行目＋前後 3 行）から離れている（review-gate 1 周目 F1）
  printf 'scripts/claude/tests/run-all.sh\t1\t2\n' >> "$d/hunks"; printf 'scripts/claude/tests/run-all.sh\n' >> "$d/own"
  printf '# r\n\n## 台帳\nFINDING: F1 SEV=Low STATUS=open FILE=backend/x/tests/test_a.py LINE=3 SECURITY=no STOP=test | 理由の無いスキップ | 再現: TEST_WEAKENING: skip …・計画書に理由なし\nFINDING: F2 SEV=Low STATUS=open FILE=scripts/claude/tests/t.sh LINE=2 SECURITY=no STOP=test | 理由の無い削除 | 再現: TEST_WEAKENING: fewer-checks …\nFINDING: F3 SEV=Low STATUS=open FILE=scripts/claude/tests/run-all.sh LINE=40 SECURITY=no STOP=test | 理由の無いテストの削除（消えた行の位置） | 再現: TEST_WEAKENING: fewer-tests …\n\nVERDICT: OK\n' > "$d/rev.md"
  lib "$f" ledger_update full "" "$d/rev.md" "$d/hunks" "$d/own" > "$d/led" || return 1
  [ "$(lib "$f" ledger_blocking "$d/led" | grep -c '^LEDGER: ')" -eq 3 ]; }
ck "TC-09 STOP=test はアプリ本体（Low）でもハーネスでも、行が変更の塊から離れていても止める指摘になる" 0 "$(rc tc09 "$CR")"
ck "FG-TC-09 塊から離れた行の STOP=test を差分の外にすると不合格（review-gate 1 周目 F1）" 1 \
  "$(rc tc09 "$(broken "$CR" 'if stop.startswith("ac:") or stop == "test" or path == "-":' 'if stop.startswith("ac:") or path == "-":')")"
ck "FG-TC-09 STOP_RE から test を外すと不合格" 1 "$(rc tc09 "$(broken "$CR" 'STOP_RE = re.compile(r"flow|leak|github|test|ac:[0-9]+")' 'STOP_RE = re.compile(r"flow|leak|github|ac:[0-9]+")')")"
ck "FG-TC-09 アプリ本体で test を止めないと不合格" 1 "$(rc tc09 "$(broken "$CR" ' or stop.startswith("ac:") or stop == "test"' ' or stop.startswith("ac:")')")"

# ---------------- TC-10: gate-check は BASE の判定の関数を使う ----------------
GR="$TMP/gr"; mkdir -p "$GR/scripts/claude" "$GR/docs/reviews" "$GR/docs/issues/open"
cp "$CR" "$GR/scripts/claude/code-review.sh"; printf '# I900\n' > "$GR/docs/issues/open/I900.md"; printf 'a\n' > "$GR/a.txt"
G -C "$GR" init -q -b develop; G -C "$GR" add -A; G -C "$GR" commit -q -m base
G -C "$GR" checkout -q -b feature/I900-x
mkdir -p "$GR/.claude/hooks"; printf 'x\n' > "$GR/.claude/hooks/h.sh"   # BASE の判定では高リスク
# ブランチの code-review.sh は、高リスクを常に NO にする
python3 -I -c 'import sys,re
p=sys.argv[1]; s=open(p,encoding="utf-8").read()
s=s.replace("path_risk_trigger() {\n", "path_risk_trigger() { echo NO; return; \n",1)
open(p,"w",encoding="utf-8").write(s)' "$GR/scripts/claude/code-review.sh"
G -C "$GR" add -A; G -C "$GR" commit -q -m change
printf 'REVIEWED_COMMIT: %s\nRISK: NO\nVERDICT: OK\n' "$(git -C "$GR" rev-parse HEAD)" > "$GR/docs/reviews/I900_code_review_20260101_0000.md"
G -C "$GR" add -A; G -C "$GR" commit -q -m rec
tc10() { local s="$1" out; case "$s" in /*) ;; *) s="$REPO_ROOT/$s" ;; esac
  out=$(cd "$GR" && GATE_BASE=develop bash "$s" I900 2>&1); grep -qx 'GATE_CHECK: FAIL REASON=missing' <<< "$out"; }
ck "TC-10 ブランチの code-review.sh で高リスクを NO にしても、BASE の判定で敵対的レビューを求める" 0 "$(rc tc10 "$GC")"
GCB="$(broken "$GC" '  LIB_FILE="$GC_TMP/code-review.sh"' '  LIB_FILE=scripts/claude/code-review.sh')"
ck "FG-TC-10 読み込み先を作業ツリーに戻すと通ってしまい不合格" 1 "$(rc tc10 "$GCB")"

# ---------------- TC-11: 写しの中身と壊れたフォルダ ----------------
SR="$TMP/sr"; mkdir -p "$SR/scripts/claude" "$SR/.claude/agents" "$SR/docs/runbooks"
printf 'x\n' > "$SR/scripts/claude/a.sh"; printf 'r\n' > "$SR/.claude/agents/code-reviewer.md"; printf 'd\n' > "$SR/docs/runbooks/review-rules.md"
printf 'o\n' > "$SR/docs/runbooks/other.md"
G -C "$SR" init -q -b main; G -C "$SR" add -A; G -C "$SR" commit -q -m base; SRB=$(git -C "$SR" rev-parse HEAD)
tc11() { local hook="$1" cache="$TMP/cache_$RANDOM" snap
  mkdir -p "$cache/$SRB"; printf 'half\n' > "$cache/$SRB/partial"          # .complete の無い作りかけ
  snap=$(bash -c '. "$1" && _reviewed_snapshot_make "$2" "$3" "$4"' _ "$hook" "$SR" "$SRB" "$cache") || return 1
  [ -f "$snap/.complete" ] && [ -f "$snap/scripts/claude/a.sh" ] && [ -f "$snap/.claude/agents/code-reviewer.md" ] \
    && [ -f "$snap/docs/runbooks/review-rules.md" ] && [ ! -e "$snap/docs/runbooks/other.md" ] \
    && ls -d "$cache"/.stale."$SRB".*/old >/dev/null 2>&1; }
HOOK=.claude/hooks/reviewed-hook.sh
ck "TC-11 写しに定義と決まりが入り（ほかの手順書は入らない）、作りかけのフォルダは脇へ移して置く" 0 "$(rc tc11 "$HOOK")"
ck "FG-TC-11 写しに定義を入れないと不合格" 1 "$(rc tc11 "$(broken "$HOOK" 'ls-tree --name-only "$base" -- .claude/agents docs/runbooks/review-rules.md' 'ls-tree --name-only "$base" -- docs/runbooks/review-rules.md')")"
ck "FG-TC-11 作りかけを脇へ移さないと写しを置けず不合格" 1 "$(rc tc11 "$(broken "$HOOK" '        mv -T "$snap" "$stale/old" 2>/dev/null || true' '        true')")"
# 定義が BASE に無いときも写しは作れる（archive 全体を失敗させない）
SR2="$TMP/sr2"; mkdir -p "$SR2/scripts/claude"; printf 'x\n' > "$SR2/scripts/claude/a.sh"
G -C "$SR2" init -q -b main; G -C "$SR2" add -A; G -C "$SR2" commit -q -m base
ck "TC-11 定義の無い BASE でも写しを作れる" 0 "$(rc bash -c '. "$1" && _reviewed_snapshot_make "$2" "$(git -C "$2" rev-parse HEAD)" "$3"' _ "$HOOK" "$SR2" "$TMP/cache2")"

# ---------------- TC-12: code-review.sh の python3 は -I（一覧 I615 F5） ----------------
tc12() { ! grep -nP 'python3(?! +-I)\s+-' "$1"; }
ck "TC-12 code-review.sh に -I の無い python3 の起動が無い" 0 "$(rc tc12 "$CR")"
ck "FG-TC-12 -I を 1 か所外すと不合格" 1 "$(rc tc12 "$(broken "$CR" '  python3 -I - ${CI_WORKFLOWS' '  python3 - ${CI_WORKFLOWS')")"

ck "FG の写しがすべて作れた（置き換え元が本体にある）" no "$([ -e "$TMP/broken_failed" ] && echo yes || echo no)"
printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
