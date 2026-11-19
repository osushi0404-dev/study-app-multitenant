#!/usr/bin/env bash
# I569: イシューの番号（I＋GitHub の番号）が 3 桁以上でも流れが動き、不正な値は今までどおり断ることを決定論検証する。
# あわせて、番号を受け付ける判定に 3 桁固定の書き方が残っていない・書き戻されていないことを走査する（TC-09・再発防止）。
# 実行: bash scripts/claude/tests/test_i569_issue_number_digits.sh
# ケースは docs/tests/{open,closed}/I569_auto_test.md の TC-01〜TC-09・FG-01〜FG-04 と、
# docs/tests/{open,closed}/I583_auto_test.md の TC-10・FG-05〜FG-07（TC-02・TC-03・TC-05 の組み直し）と対応する。
# 走査（TC-09）の例外の決まり: 番号でない 3 桁（例: HTTP の状態コード）の判定が要るときは、そのファイルを SCAN_EXCLUDE に足す（理由をコメントに書く）。
# shellcheck disable=SC2016  # 単一引用符の $ISSUE などは、走査・注入の材料として文字どおりに書く
set -uo pipefail
unset CLAUDE_PROJECT_DIR
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
SCAN_EXCLUDE=("scripts/claude/tests/test_i569_issue_number_digits.sh")   # このファイル自身は走査の形と失敗の注入の材料を書くので除く
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
# コマンドが成功なら YES・失敗なら NO
yn() { if "$@"; then echo YES; else echo NO; fi; }
# $1=出力 $2=含むべき文字 → 含めば YES
has() { yn grep -qF -- "$2" <<<"$1"; }
# $1・$2 の中身が違えば成功（失敗の注入の写しに置換が入ったかを見る）
differs() { ! cmp -s "$1" "$2"; }
# 不正な番号を断ること。$1=名前 $2=期待する exit code $3=出力に含むべき文字 $4..=コマンド（末尾に値を付けて呼ぶ）
rejects() {
  local label=$1 code=$2 mark=$3 n out rc; shift 3
  for n in I12 I1a I1000x ''; do
    out="$("$@" "$n" 2>&1)"; rc=$?
    ck "$label '$n' は exit $code" "$code" "$rc"
    ck "$label '$n' は $mark" YES "$(has "$out" "$mark")"
  done
}

# ---- TC-01 flow-stage.sh ----
RD="$TMP/reviews"; mkdir -p "$RD/open"
for n in I1000 I12345 I999; do
  printf 'x\nSTAGE_DONE: plan NEXT: plan-review\n' > "$RD/open/${n}_review.md"
  out="$(REVIEW_DIR="$RD" bash scripts/claude/flow-stage.sh "$n" 2>&1)"; rc=$?
  ck "TC-01 flow-stage $n は exit 0" 0 "$rc"
  ck "TC-01 flow-stage $n は次の段階を返す" YES "$(has "$out" "NEXT_STAGE: plan-review")"
done
rejects "TC-01 flow-stage" 2 "使い方" env REVIEW_DIR="$RD" bash scripts/claude/flow-stage.sh

# ---- TC-02・TC-03・TC-05 の土台（I583）----
# 番号の確かめを通った後の止まり方は、本物のリポジトリではなく一時の git リポジトリの中から本物のスクリプトを起動して見る
# （3 本とも起動した場所の git の根から記録を読むので、本物の I1000 の記録ができても結果が変わらない）。
# 起動のたびに、呼ばれたら印を作る差し替えの claude を PATH の先頭と CLAUDE_BIN に置く（本物のレビュー役を起こさない・起動を検出する）
GATE="$REPO_ROOT/scripts/claude/gate-check.sh"
ADV="$REPO_ROOT/scripts/claude/adversarial-review.sh"
MTE="$REPO_ROOT/scripts/claude/check-manual-test-executor.sh"
LIB="$REPO_ROOT/scripts/claude/code-review.sh"   # gate-check.sh の既定の部品は git の根からの相対パスなので、本物を明示する
STUB_DIR="$TMP/stub"; MARK="$TMP/claude_called"; mkdir -p "$STUB_DIR"
printf '#!/bin/sh\ntouch "%s"\nexit 1\n' "$MARK" > "$STUB_DIR/claude"; chmod +x "$STUB_DIR/claude"
command -v flock >/dev/null 2>&1 || echo "    flock がありません（TC-03・FG-06 は確かめられない）"
# $1=一時のリポジトリ $2..=git の引数 → 作者を付けて git を流す（CI の git に作者が無くても動く）
tgit() { git -C "$1" -c user.name=t -c user.email=t@t "${@:2}"; }
# $1=フォルダ → git init と空のコミットだけの一時のリポジトリを作る
iso_repo() { git init -q "$1" && tgit "$1" commit -q --allow-empty -m init; }
# $1=起動する場所 $2=期待する exit code $3=照合の仕方（line=行全体・text=含む） $4=期待する文字 $5..=コマンド
# → 終了コードが一致し、かつ出力が期待を含めば YES。TC と FG（失敗の注入）が同じこの判定を呼ぶ。
# git の場所を指す環境変数を外し、git の探索を $TMP で止める（外から流しても本物のリポジトリに届かない）
stops() {
  local dir=$1 code=$2 how=$3 want=$4 out rc; shift 4
  out="$(cd "$dir" && env -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE "GIT_CEILING_DIRECTORIES=$TMP" \
    "PATH=$STUB_DIR:$PATH" "CLAUDE_BIN=$STUB_DIR/claude" "$@" 2>&1)"; rc=$?
  if [ "$rc" != "$code" ]; then echo NO; return; fi
  if [ "$how" = line ]; then yn grep -qxF -- "$want" <<<"$out"; else has "$out" "$want"; fi
}
ISO="$TMP/iso"; iso_repo "$ISO"

# ---- TC-02 gate-check.sh ----
ck "TC-02 gate-check I1000 は番号の確かめを通り、記録が無くて止まる" YES \
  "$(stops "$ISO" 1 line 'GATE_CHECK: FAIL REASON=missing' env GATE_BASE=HEAD "GATE_CHECK_LIB=$LIB" bash "$GATE" I1000)"
rejects "TC-02 gate-check" 1 "使い方" bash "$GATE"

# ---- TC-03 adversarial-review.sh（I1000 はファイルが無いので、レビュー役を起こす前に止まる）----
ck "TC-03 adversarial I1000 は番号の確かめを通り、ファイルが無くて止まる" YES \
  "$(stops "$ISO" 2 line 'ADVERSARIAL_ERROR: FILES' bash "$ADV" I1000)"
rejects "TC-03 adversarial" 2 "ADVERSARIAL_ERROR: USAGE" bash "$ADV"

# ---- TC-04 check-frontend-evidence.sh ----
BASE_REF=HEAD bash scripts/claude/check-frontend-evidence.sh I1000 >/dev/null 2>&1
ck "TC-04 frontend-evidence I1000 は対象外で合格" 0 "$?"
rejects "TC-04 frontend-evidence" 2 "使い方" env BASE_REF=HEAD bash scripts/claude/check-frontend-evidence.sh

# ---- TC-05 check-manual-test-executor.sh ----
ck "TC-05 manual-test-executor I1000 は番号の確かめを通り、文書が無くて止まる" YES \
  "$(stops "$ISO" 2 text '判定できない: I1000_manual_test.md がありません' bash "$MTE" I1000)"
rejects "TC-05 manual-test-executor" 2 "使い方" bash "$MTE"

# ---- TC-10 TC-02〜TC-05 は別プロセスの claude を起動しない（I583）----
ck "TC-10 差し替えの claude が呼ばれていない" NO "$(yn [ -e "$MARK" ])"

# ---- TC-06 close のスキルの番号の確かめ ----
# $1=SKILL.md → 番号の確かめの正規表現（`=~ ` と ` ]]` の間）
close_re() { sed -n 's/.*"\$ISSUE_NUM" =~ \(.*\) \]\].*/\1/p' "$1" | head -1; }
# $1=正規表現 $2=値 → 一致なら YES
re_match() { if [[ "$2" =~ $1 ]]; then echo YES; else echo NO; fi; }
CLOSE=".claude/skills/close/SKILL.md"
RE="$(close_re "$CLOSE")"
ck "TC-06 close の正規表現を取り出せる" YES "$(yn [ -n "$RE" ])"
for v in 1000 12345 569; do ck "TC-06 close '$v' は一致" YES "$(re_match "$RE" "$v")"; done
for v in 12 1a 1000x ''; do ck "TC-06 close '$v' は不一致" NO "$(re_match "$RE" "$v")"; done

# ---- TC-07 見張りの画面確認の保存先 ----
GUARD="scripts/claude/hooks/pretooluse_guard.py"
# $1=見張り $2=filename → 見張りの exit code
shot() {
  python3 -c '
import json, sys
print(json.dumps({"tool_name": "mcp__playwright__browser_take_screenshot", "tool_input": {"filename": sys.argv[1]}}))' "$2" \
    | python3 "$1" >/dev/null 2>&1
  echo $?
}
for f in .evidence/I1000/a.png .evidence/I569/a.png; do ck "TC-07 見張り $f は通す" 0 "$(shot "$GUARD" "$f")"; done
for f in .evidence/I12/a.png .evidence/I1a/a.png .evidence/I1000/../../backend/.env .evidence/I1000/sub/x.txt /tmp/x.png; do
  ck "TC-07 見張り $f は止める" 2 "$(shot "$GUARD" "$f")"
done

# ---- TC-08 開始時の文脈（題の自由文は出さず、I＋数字だけを取る）----
SS_OUT="$(python3 - "scripts/claude/hooks/sessionstart_context.py" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("ssc", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
d = "2026-11-18T00:00:00Z"
prs = [{"number": 1, "title": "feat: I1000 x", "mergedAt": d}, {"number": 2, "title": "I12: x", "mergedAt": d},
       {"number": 3, "title": "fix: I1000x y", "mergedAt": d}, {"number": 4, "title": "I569: x", "mergedAt": d}]
print(m.format_context("feature/x", 0, prs, None))
PY
)"
for w in "#1 I1000 2026-11-18" "#2 - 2026-11-18" "#3 - 2026-11-18" "#4 I569 2026-11-18"; do
  ck "TC-08 開始時の文脈に「$w」" YES "$(has "$SS_OUT" "$w")"
done

# ---- TC-09 3 桁固定の書き方の走査（追跡しているファイルだけ）----
SCAN_PAT='I\[0-9\]\{3\}([^,]|$)|\^\[0-9\]\{3\}\$|I\[0-9\]\[0-9\]\[0-9\]|I\\d\{3\}([^,]|$)'
# $1=git のフォルダ → 当たりを「ファイル:行:中身」で出す
scan() {
  local ex args=()
  for ex in "${SCAN_EXCLUDE[@]}"; do args+=(":(exclude)$ex"); done
  git -C "$1" grep -nE "$SCAN_PAT" -- scripts .claude .github .pre-commit-config.yaml "${args[@]}"
}
hits="$(scan "$REPO_ROOT")"
[ -n "$hits" ] && printf '%s\n' "$hits" | sed 's/^/    3 桁固定: /'
ck "TC-09 3 桁固定の書き方が残っていない" 0 "$(printf '%s' "$hits" | grep -c .)"

# ---- FG-01 走査が書き戻りを捕まえる（本物の scan を一時の git フォルダに流す）----
F1="$TMP/fg1"; mkdir -p "$F1/scripts" "$F1/.claude/skills/b"
git -C "$F1" init -q
printf '%s\n' '[[ "$X" =~ ^I[0-9]{3}$ ]]' > "$F1/scripts/a.sh"
printf '%s\n' 'if ! [[ "$N" =~ ^[0-9]{3}$ ]]; then' > "$F1/.claude/skills/b/SKILL.md"
printf '%s\n' 'R = re.compile(r"I[0-9]{3}/")' > "$F1/scripts/c.py"
printf '%s\n' 'grep "I[0-9][0-9][0-9]"' > "$F1/scripts/d.sh"
git -C "$F1" add -A
ck "FG-01 4 形を置くと 4 件とも当たる" 4 "$(scan "$F1" | grep -c .)"
F2="$TMP/fg2"; mkdir -p "$F2/scripts"
git -C "$F2" init -q
printf '%s\n' '[[ "$X" =~ ^I[0-9]{3,}$ ]]' > "$F2/scripts/a.sh"
git -C "$F2" add -A
ck "FG-01 {3,} だけなら当たらない" 0 "$(scan "$F2" | grep -c .)"

# ---- FG-02 flow-stage の確かめを外すと、TC-01 の不正な値の側が捕まえる ----
B2="$TMP/flow-stage.sh"
sed 's/^if ! \[\[ "\$ISSUE" =~ .*\]\]; then$/if false; then/' scripts/claude/flow-stage.sh > "$B2"
ck "FG-02 写しに置換が入った" YES "$(yn differs scripts/claude/flow-stage.sh "$B2")"
out="$(REVIEW_DIR="$RD" bash "$B2" I1a 2>&1)"
ck "FG-02 確かめを外すと I1a で使い方が出ない" NO "$(has "$out" "使い方")"

# ---- FG-03 見張りの判定を緩めると、TC-07 の止める側が捕まえる ----
# `..` は正規表現とは別の判定でも止めるので、正規表現だけが守る入れ子・絶対パスで確かめる
B3="$TMP/guard.py"
sed 's/^_EVIDENCE_FILE_RE = re.compile(r"[^"]*")/_EVIDENCE_FILE_RE = re.compile(r".*")/' "$GUARD" > "$B3"
ck "FG-03 写しに置換が入った" YES "$(yn differs "$GUARD" "$B3")"
ck "FG-03 緩めると入れ子が素通し" 0 "$(shot "$B3" .evidence/I1000/sub/x.txt)"
ck "FG-03 緩めると絶対パスが素通し" 0 "$(shot "$B3" /tmp/x.png)"

# ---- FG-04 close の正規表現を緩めると、TC-06 の不一致の側が捕まえる ----
B4="$TMP/SKILL.md"
sed 's/\("\$ISSUE_NUM" =~ \)[^ ]*\( \]\]\)/\1.*\2/' "$CLOSE" > "$B4"
ck "FG-04 写しに置換が入った" YES "$(yn differs "$CLOSE" "$B4")"
ck "FG-04 緩めると 1a が一致" YES "$(re_match "$(close_re "$B4")" 1a)"

# ---- FG-05 確かめの後・記録を読む前に別の理由（部品の読み込みの失敗）で終わると、TC-02 の判定が捕まえる（I583）----
ck "FG-05 部品を読めないと TC-02 の判定は NO" NO \
  "$(stops "$ISO" 1 line 'GATE_CHECK: FAIL REASON=missing' env GATE_BASE=HEAD "GATE_CHECK_LIB=$TMP/no-such-lib.sh" bash "$GATE" I1000)"

# ---- FG-06 I1000 の記録ができた状態では、TC-03 の判定が捕まえ、差し替えの claude の起動が印に出る（I583）----
F6="$TMP/fg6"; iso_repo "$F6"; mkdir -p "$F6/docs/issues/open" "$F6/docs/plans/open"
echo x > "$F6/docs/issues/open/I1000.md"
printf '# p\n\n## 必ず確かめる項目\n| 項目 | 観点 | 確かめ方 | 内容 |\n|---|---|---|---|\n| V1 | 1 | 読んで可 | x |\n' > "$F6/docs/plans/open/plan_I1000.md"
tgit "$F6" add -A && tgit "$F6" commit -q -m rec
rm -f "$MARK"   # FG-06 自身の起動だけを印で見る（前のケースの印を持ち越さない）
ck "FG-06 記録があると TC-03 の判定は NO" NO \
  "$(stops "$F6" 2 line 'ADVERSARIAL_ERROR: FILES' env ADV_BASE=HEAD ADV_DEADLINE=30 ADV_STEP_TIMEOUT=10 ADV_MIN_STEP=1 bash "$ADV" I1000)"
ck "FG-06 記録があると差し替えの claude が呼ばれ、印に出る" YES "$(yn [ -e "$MARK" ])"

# ---- FG-07 確かめの後に別の理由（git の外）で終わると、TC-05 の判定が捕まえる（I583）----
mkdir -p "$TMP/nogit"
ck "FG-07 git の外では TC-05 の判定は NO" NO \
  "$(stops "$TMP/nogit" 2 text '判定できない: I1000_manual_test.md がありません' bash "$MTE" I1000)"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
