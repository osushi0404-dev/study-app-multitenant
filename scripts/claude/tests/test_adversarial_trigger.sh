#!/usr/bin/env bash
# I086 回帰テスト: 高リスク判定の機械可読化（detect_risk_flag の fail-closed／
#                  path_risk_trigger のパス決定論トリガ）と敵対ステージ結線行の存在を検証する。
# I181: path_risk_trigger の対象を「GitHub から復旧できない例外」に絞った（P1〜P7・FG-P1・FG-P2）。
#
# 実行（必ずスクリプトとして bash 実行すること。対話シェルへ貼らない）:
#   bash scripts/claude/tests/test_adversarial_trigger.sh
#
# 理由: Claude Code の対話シェルでは grep が同梱 ugrep ラッパーに上書きされ -E/-o パイプが
#       誤動作する。bash サブプロセスでは実 GNU grep が使われるため決定論的に PASS する。
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1

CODE_REVIEW="scripts/claude/code-review.sh"

pass=0; fail=0
ck() { # name expected actual
  if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1))
  else printf 'FAIL %s  expected[%s] got[%s]\n' "$1" "$2" "$3"; fail=$((fail+1)); fi
}
ck_true() { # name cmd... : expect exit 0
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then printf 'PASS %s\n' "$name"; pass=$((pass+1))
  else printf 'FAIL %s (expected success)\n' "$name"; fail=$((fail+1)); fi
}

# ---- 対象スクリプトから helper 関数のみを source（ガードで本体は実行されない） ----
# shellcheck source=/dev/null
REVIEW_LIB_SOURCE_ONLY=1 source "$CODE_REVIEW"   # detect_risk_flag / path_risk_trigger
set +e +o pipefail   # source が有効化した errexit/pipefail をテストハーネス用に解除

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# ---- detect_risk_flag: RISK 行の anchored 解析・fail-closed ----
printf 'RISK: YES\nVERDICT: OK\n' > "$TMP/r_yes.md"
ck "risk: RISK YES" "YES" "$(detect_risk_flag "$TMP/r_yes.md")"

printf 'RISK: NO\nVERDICT: OK\n' > "$TMP/r_no.md"
ck "risk: RISK NO" "NO" "$(detect_risk_flag "$TMP/r_no.md")"

printf 'VERDICT: OK\n' > "$TMP/r_none.md"
ck "risk: 行欠落は fail-closed YES" "YES" "$(detect_risk_flag "$TMP/r_none.md")"

printf '**RISK: NO**\nVERDICT: OK\n' > "$TMP/r_deco.md"
ck "risk: 装飾付き行は不一致=fail-closed YES" "YES" "$(detect_risk_flag "$TMP/r_deco.md")"

# VERDICT 行直前の RISK 行を採用（正規出力）。複数の RISK/VERDICT では最終 VERDICT 直前を採る。
printf 'RISK: NO\n中間テキスト\nRISK: YES\nVERDICT: OK\n' > "$TMP/r_multi.md"
ck "risk: VERDICT 直前の RISK 行を採用" "YES" "$(detect_risk_flag "$TMP/r_multi.md")"

# H2 対応: 本文（fenced block・引用）に紛れた RISK 行は、直後が VERDICT 行でないため拾わない。
# RISK 行の正規出力が欠落していれば fail-closed YES（引用の NO で fail-open しない）。
# shellcheck disable=SC2016  # printf のフォーマット文字列はリテラル（展開させない）
printf '# レビュー\n```\nRISK: NO\n```\n本文\nVERDICT: OK\n' > "$TMP/r_quoted.md"
ck "risk: 引用内 RISK NO は無視し fail-closed YES" "YES" "$(detect_risk_flag "$TMP/r_quoted.md")"

# H2 対応: 引用の NO があっても、正規の VERDICT 直前 RISK 行が優先される。
# shellcheck disable=SC2016
printf '```\nRISK: NO\n```\nRISK: YES\nVERDICT: OK\n' > "$TMP/r_quoted_yes.md"
ck "risk: 引用 NO より正規 VERDICT 直前 YES を優先" "YES" "$(detect_risk_flag "$TMP/r_quoted_yes.md")"

# 正規の NO（VERDICT 直前）は NO を返す。
printf 'RISK: NO\nVERDICT: OK\n' > "$TMP/r_regnO.md"
ck "risk: VERDICT 直前の正規 NO は NO" "NO" "$(detect_risk_flag "$TMP/r_regnO.md")"

# ---- path_risk_trigger: 監視パスの決定論トリガ（I181: GitHub から復旧できない例外だけ） ----
# P1: 例外の各パスは YES（I182 の danger-ops.md「GitHub から復旧できる範囲」が出典）
EXCEPTION_PATHS=(
  ".github/workflows/ci.yml"
  ".github/workflows/e2e.yml"
  ".github/CODEOWNERS"
  ".pre-commit-config.yaml"
  ".secrets.baseline"
  "scripts/claude/hooks/pretooluse_guard.py"
  ".claude/settings.json"
  ".claude/settings.local.json"
)
for p in "${EXCEPTION_PATHS[@]}"; do
  ck "path P1: 例外 $p は YES" "YES" "$(path_risk_trigger "$p")"
done

# P2: 例外に当たらないハーネスは NO（GitHub が最後の守り。旧判定では YES だったもの）
for p in scripts/git-hooks/pre-push scripts/claude/code-review.sh scripts/claude/tests/test_review_gates.sh \
         scripts/claude/hooks/posttooluse_check.py .claude/skills/code-review/SKILL.md \
         .claude/review-agents/code-reviewer.md .claude/agents/reviewer.md CLAUDE.md \
         docs/runbooks/workflow.md docs/runbooks/review-rules.md; do
  ck "path P2: 例外外のハーネス $p は NO" "NO" "$(path_risk_trigger "$p")"
done

# P3: I180 と同じ形（関所ではないスキルの変更＋テストの新規追加）は NO（再発防止）
I180_SHAPE="$(printf '.claude/skills/retro/SKILL.md\nscripts/claude/tests/test_i180_retro_triage.sh')"
ck "path P3: I180 と同じ形は NO" "NO" "$(path_risk_trigger "$I180_SHAPE")"

# P4: 似た名前は NO（先頭一致・完全一致）
for p in docs/.github/x.md backend/.pre-commit-config.yaml .secrets.baseline.bak \
         scripts/claude/hooks/pretooluse_guard.py.orig .claude/settings.json.bak backend/app/views.py; do
  ck "path P4: 似た名前 $p は NO" "NO" "$(path_risk_trigger "$p")"
done
ck "path P4: 空入力は NO" "NO" "$(path_risk_trigger "")"

# P6: 通常＋例外の混在は YES
MIXED="$(printf 'backend/app/views.py\nfrontend/src/App.tsx\n.github/workflows/ci.yml')"
ck "path P6: 通常＋例外の混在は YES" "YES" "$(path_risk_trigger "$MIXED")"

# P5 / FG-P2: 名前変更で元の場所が落ちない（code-review.sh の GIT_FILES と同じ git コマンド）
RREPO="$TMP/rename_repo"
mkdir -p "$RREPO/.github/workflows"
(
  cd "$RREPO" || exit 1
  git init -q -b develop
  echo a > .github/workflows/ci.yml
  git add -A
  git -c user.email=t@t -c user.name=t commit -qm c0
  git checkout -qb feat
  git mv .github/workflows/ci.yml off.yml
  git -c user.email=t@t -c user.name=t commit -qm c1
)
RENAMED_NO_RENAMES="$(git -C "$RREPO" -c core.quotePath=false diff develop...HEAD --name-only --no-renames)"
RENAMED_DEFAULT="$(git -C "$RREPO" -c core.quotePath=false diff develop...HEAD --name-only)"
ck "path P5: 名前変更（--no-renames）で元の場所が残り YES" "YES" "$(path_risk_trigger "$RENAMED_NO_RENAMES")"
ck "path FG-P2: --no-renames なしは元の場所が落ちて NO（P5 の前提の証明）" "NO" "$(path_risk_trigger "$RENAMED_DEFAULT")"

# FG-P1: case 行から例外のパターンを 1 つずつ外した複製では、そのパスが NO になる
#        （P1 が一覧の欠落を捕まえることの証明。外せなければその FG 自体を不合格にする）
CASE_LINE="$(grep -nE '^[[:space:]]+\.github/\*\|' "$CODE_REVIEW" | head -1)"
CASE_NO="${CASE_LINE%%:*}"
for pat in '.github/*' '.pre-commit-config.yaml' '.secrets.baseline' \
           'scripts/claude/hooks/pretooluse_guard.py' '.claude/settings.json' '.claude/settings.local.json'; do
  case "$pat" in
    '.github/*') probe=".github/workflows/ci.yml" ;;
    *) probe="$pat" ;;
  esac
  copy="$TMP/cr_fg.sh"
  if [ -z "$CASE_NO" ]; then
    ck "path FG-P1: $pat を外した複製を作れる" "ok" "ng"
    continue
  fi
  if ! python3 - "$CODE_REVIEW" "$copy" "$CASE_NO" "$pat" <<'PY'
import sys
src, dst, line_no, pat = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
lines = open(src, encoding="utf-8").read().split("\n")
head, sep, tail = lines[line_no - 1].partition(")")
alts = head.strip().split("|")
if pat not in alts:
    sys.exit(3)
indent = head[: len(head) - len(head.lstrip())]
lines[line_no - 1] = indent + "|".join(a for a in alts if a != pat) + sep + tail
open(dst, "w", encoding="utf-8").write("\n".join(lines))
PY
  then
    ck "path FG-P1: $pat を外した複製を作れる" "ok" "ng"
    continue
  fi
  got="$(REVIEW_LIB_SOURCE_ONLY=1 bash -c 'source "$1" >/dev/null 2>&1; path_risk_trigger "$2"' _ "$copy" "$probe")"
  ck "path FG-P1: $pat を外すと $probe が NO" "NO" "$got"
done

# ---- H5 対応: 配線ロジックの挙動（OR 合成・ステージ要否）を関数として固定化 ----
# 本体フローに直書きすると OR→AND 変異や REQUIRED/NOT_REQUIRED 反転を文字列 grep が検出できず
# false-green になるため、関数の真理値表をここで固定する。
ck "combine: YES/YES → YES" "YES" "$(combine_risk YES YES)"
ck "combine: YES/NO → YES"  "YES" "$(combine_risk YES NO)"
ck "combine: NO/YES → YES"  "YES" "$(combine_risk NO YES)"
ck "combine: NO/NO → NO"    "NO"  "$(combine_risk NO NO)"
ck "decision: YES → REQUIRED"     "REQUIRED"     "$(adversarial_stage_decision YES)"
ck "decision: NO → NOT_REQUIRED"  "NOT_REQUIRED" "$(adversarial_stage_decision NO)"

# ---- H6 対応: emit_decision_lines の入出力対応を担保（引数 risk_final が RISK 行と
#      ADVERSARIAL_STAGE 行の両方を一貫して決めることを固定。emit 内での別変数参照＝
#      誤配線を構造的に排除し、前方一致 grep では捕捉できない false-green を潰す） ----
OUT_YES=$(emit_decision_lines "rev.md" YES OK)
ck_true "emit: risk_final=YES → RISK: YES 行"          grep -qx 'RISK: YES' <<< "$OUT_YES"
ck_true "emit: risk_final=YES → ADVERSARIAL_STAGE: REQUIRED" grep -qx 'ADVERSARIAL_STAGE: REQUIRED' <<< "$OUT_YES"
ck_true "emit: review_file を REVIEW_FILE 行へ"        grep -qx 'REVIEW_FILE: rev.md' <<< "$OUT_YES"
ck_true "emit: final_verdict を FINAL_VERDICT 行へ"    grep -qx 'FINAL_VERDICT: OK' <<< "$OUT_YES"
OUT_NO=$(emit_decision_lines "rev.md" NO BLOCKER)
ck_true "emit: risk_final=NO → RISK: NO 行"            grep -qx 'RISK: NO' <<< "$OUT_NO"
ck_true "emit: risk_final=NO → ADVERSARIAL_STAGE: NOT_REQUIRED" grep -qx 'ADVERSARIAL_STAGE: NOT_REQUIRED' <<< "$OUT_NO"

# ---- 本体の配線行を厳密文字列で固定（引数レベルの誤配線＝path→GIT_LOG 取り違え等を捕捉） ----
# shellcheck disable=SC2016  # スクリプト内リテラルの配線行を検索（展開させない）
ck_true "wire: 本体の高リスクの計画レビューの判定（I197: code-reviewer の RISK 行は使わない）" grep -qF 'RISK_PLAN=$(plan_risk "$ISSUE")' "$CODE_REVIEW"
# shellcheck disable=SC2016
ck_true "wire: 本体 RISK_PATH の取得元（GIT_FILES 固定）" grep -qF 'RISK_PATH=$(path_risk_trigger "$GIT_FILES")' "$CODE_REVIEW"
# P7（I181）: GIT_FILES は --no-renames で名前変更の元の場所も出す
# shellcheck disable=SC2016
ck_true "wire P7: GIT_FILES に --no-renames" grep -qF 'GIT_FILES=$(git -c core.quotePath=false diff origin/develop...HEAD --name-only --no-renames)' "$CODE_REVIEW"
# shellcheck disable=SC2016
ck_true "wire: 本体 RISK_FINAL の合成（I197: 計画レビューの判定 OR パス。code-reviewer の RISK は使わない）" grep -qF 'RISK_FINAL=$(combine_risk "$RISK_PLAN" "$RISK_PATH")' "$CODE_REVIEW"
# shellcheck disable=SC2016
ck_true "wire: 本体 emit の引数配線" grep -qF 'emit_decision_lines "$REVIEW_FILE" "$RISK_FINAL" "$FINAL_VERDICT"' "$CODE_REVIEW"

echo "----"
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ] || exit 1
exit 0
