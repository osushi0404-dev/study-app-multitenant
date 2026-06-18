#!/usr/bin/env bash
# I062 回帰テスト: レビュー判定の堅牢化（VERDICT 一次 + 装飾許容/プレーン grep 保険）と
#                  find_plan_file の連番数値順選択、既存 find_file の非退行を検証する。
#
# 実行（必ずスクリプトとして bash 実行すること。対話シェルへ貼らない）:
#   bash scripts/claude/tests/test_review_verdict.sh
#
# 理由: Claude Code の対話シェルでは grep が同梱 ugrep ラッパーに上書きされ -E/-o パイプが
#       誤動作する。bash サブプロセスでは実 GNU grep が使われるため決定論的に PASS する。
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1

CODE_REVIEW="scripts/claude/code-review.sh"
PLAN_REVIEW="scripts/claude/plan-issue-review.sh"
CODE_AGENT=".claude/review-agents/code-reviewer.md"
PLAN_AGENT=".claude/review-agents/plan-reviewer.md"
RUNBOOK="docs/runbooks/common-commands.md"

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
ck_false() { # name cmd... : expect non-zero
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then printf 'FAIL %s (expected non-zero)\n' "$name"; fail=$((fail+1))
  else printf 'PASS %s\n' "$name"; pass=$((pass+1)); fi
}

# ---- 対象スクリプトから helper 関数のみを source（ガードで本体は実行されない） ----
# shellcheck source=/dev/null
REVIEW_LIB_SOURCE_ONLY=1 source "$CODE_REVIEW"   # find_file / find_plan_file / detect_code_verdict
# shellcheck source=/dev/null
REVIEW_LIB_SOURCE_ONLY=1 source "$PLAN_REVIEW"   # （find_* 再定義）+ detect_plan_verdict
set +e +o pipefail   # source が有効化した errexit/pipefail をテストハーネス用に解除

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "== TC-19: source ガードで関数のみ定義（本体未実行） =="
ck_true TC-19-fn-find_plan_file   declare -F find_plan_file
ck_true TC-19-fn-detect_code      declare -F detect_code_verdict
ck_true TC-19-fn-detect_plan      declare -F detect_plan_verdict
ck_true TC-19-fn-find_file        declare -F find_file

echo "== TC-01〜TC-05f: find_plan_file（連番数値順・最大選択） =="
mkdir -p "$TMP/docs/plans/open" "$TMP/docs/plans/closed"
touch "$TMP/docs/plans/open/plan_I999.md"
ck TC-01 "docs/plans/open/plan_I999.md"    "$(cd "$TMP" && find_plan_file I999)"
touch "$TMP/docs/plans/open/plan_I999_2.md"
ck TC-02 "docs/plans/open/plan_I999_2.md"  "$(cd "$TMP" && find_plan_file I999)"
touch "$TMP/docs/plans/open/plan_I999_9.md" "$TMP/docs/plans/open/plan_I999_10.md"
ck TC-03 "docs/plans/open/plan_I999_10.md" "$(cd "$TMP" && find_plan_file I999)"
touch "$TMP/docs/plans/closed/plan_I888.md" "$TMP/docs/plans/open/plan_I888_3.md"
ck TC-04 "docs/plans/open/plan_I888_3.md"  "$(cd "$TMP" && find_plan_file I888)"
ck TC-05f ""                               "$(cd "$TMP" && find_plan_file I777)"

echo "== TC-06: 既存 find_file 非退行（issues/tests ルックアップ） =="
mkdir -p "$TMP/docs/issues/open" "$TMP/docs/issues/closed"
touch "$TMP/docs/issues/open/Itest.md"
ck TC-06  "docs/issues/open/Itest.md"     "$(cd "$TMP" && find_file issues Itest.md)"
touch "$TMP/docs/issues/closed/Iclosed.md"
ck TC-06b "docs/issues/closed/Iclosed.md" "$(cd "$TMP" && find_file issues Iclosed.md)"
ck TC-06c ""                              "$(cd "$TMP" && find_file issues Inone.md)"

echo "== TC-01c〜TC-12: detect_code_verdict（一次=VERDICT / 保険=装飾許容） =="
printf 'x\nVERDICT: BLOCKER\n'              > "$TMP/c1"; ck TC-01c BLOCKER "$(detect_code_verdict "$TMP/c1")"
printf 'x\nVERDICT: HIGH\n'                 > "$TMP/c2"; ck TC-02c HIGH    "$(detect_code_verdict "$TMP/c2")"
printf 'x\nVERDICT: OK\n'                   > "$TMP/c3"; ck TC-03c OK      "$(detect_code_verdict "$TMP/c3")"
printf '| **Blocker** | x |\nVERDICT: OK\n' > "$TMP/c4"; ck TC-04c OK      "$(detect_code_verdict "$TMP/c4")"
# TC-05: 太字 Blocker・VERDICT 行なし → 保険経路で BLOCKER（合成 hermetic fixture・実ファイル依存撤去）
printf '| **Blocker** | 説明 |\n指摘あり\n'  > "$TMP/c5"; ck TC-05 BLOCKER "$(detect_code_verdict "$TMP/c5")"
printf '| Blocker | x |\n'                  > "$TMP/c7"; ck TC-07 BLOCKER "$(detect_code_verdict "$TMP/c7")"
printf '| High | x |\n'                     > "$TMP/c8"; ck TC-08 HIGH    "$(detect_code_verdict "$TMP/c8")"
printf '| **High** | x |\n'                 > "$TMP/c9"; ck TC-09 HIGH    "$(detect_code_verdict "$TMP/c9")"
printf '# clean review\n指摘なし\n'         > "$TMP/c10"; ck TC-10 OK     "$(detect_code_verdict "$TMP/c10")"
# TC-12: 旧プレーン grep が太字 Blocker に非マッチ（バグの存在＝修正の前提を固定化）
ck_false TC-12-old-grep-nonmatch grep -qE '^\| Blocker \|' "$TMP/c5"

echo "== TC-13〜TC-17: detect_plan_verdict（一次=VERDICT / 保険=プレーン判定） =="
printf '## 判定: 差し戻し\nVERDICT: BLOCKER\n' > "$TMP/p1"; ck TC-13 BLOCKER  "$(detect_plan_verdict "$TMP/p1")"
printf 'VERDICT: HIGHRISK\n'                  > "$TMP/p2"; ck TC-14 HIGHRISK "$(detect_plan_verdict "$TMP/p2")"
printf 'VERDICT: OK\n'                        > "$TMP/p3"; ck TC-15 OK       "$(detect_plan_verdict "$TMP/p3")"
printf '## 判定: 差し戻し（Blocker 2件）\n'   > "$TMP/p4"; ck TC-16 BLOCKER  "$(detect_plan_verdict "$TMP/p4")"
printf '## 判定: ✅ 完了\n指摘なし\n'         > "$TMP/p5"; ck TC-17 OK       "$(detect_plan_verdict "$TMP/p5")"

echo "== TC-11/TC-15w: スクリプトが detect_* を一次判定に配線していること =="
# shellcheck disable=SC2016  # 単一引用符はリテラル文字列を grep する意図（展開不要）
ck_true TC-11-code-wired grep -q 'case "$(detect_code_verdict' "$CODE_REVIEW"
# shellcheck disable=SC2016
ck_true TC-15-plan-wired grep -q 'case "$(detect_plan_verdict' "$PLAN_REVIEW"

echo "== TC-18: エージェント定義の VERDICT 契約・P1 gate 観点 =="
ck_true TC-18a-code-blocker  grep -q 'VERDICT: BLOCKER'  "$CODE_AGENT"
ck_true TC-18a-code-high     grep -q 'VERDICT: HIGH'     "$CODE_AGENT"
ck_true TC-18a-code-ok       grep -q 'VERDICT: OK'       "$CODE_AGENT"
ck_true TC-18b-plan-blocker  grep -q 'VERDICT: BLOCKER'  "$PLAN_AGENT"
ck_true TC-18b-plan-highrisk grep -q 'VERDICT: HIGHRISK' "$PLAN_AGENT"
ck_true TC-18b-plan-ok       grep -q 'VERDICT: OK'       "$PLAN_AGENT"
ck_true TC-18c-code-p1gate   grep -q '消費箇所' "$CODE_AGENT"
ck_true TC-18c-plan-p1gate   grep -q '消費箇所' "$PLAN_AGENT"

echo "== TC-21〜23: retro C1（末尾アンカー）・P1（do/gate） =="
# C1: 隣接値の部分一致誤読を末尾アンカーで排除
printf 'x\nVERDICT: HIGHRISK\n' > "$TMP/r1"; ck TC-21a OK "$(detect_code_verdict "$TMP/r1")"   # code側に HIGHRISK 混入 → HIGH 誤読しない
printf 'x\nVERDICT: HIGH\n'     > "$TMP/r2"; ck TC-21b OK "$(detect_plan_verdict "$TMP/r2")"   # plan側に HIGH 混入 → HIGHRISK 部分一致しない
printf 'x\nVERDICT: OK\n'       > "$TMP/r3"; ck TC-21c OK "$(detect_code_verdict "$TMP/r3")"   # 正常系がアンカー後も壊れない
# P1 gate: code-reviewer.md にシェルテスト決定論性観点
ck_true TC-22-gate grep -q 'シェルスクリプト検証の決定論性' "$CODE_AGENT"
# P1 do: runbook にシェル検証の実行コンテキスト注意
ck_true TC-23-do   grep -q 'シェルスクリプトのロジック検証' "$RUNBOOK"

echo "== TC-24〜27: detect_plan_verdict 高リスク保険の多行対応（VERDICT 行なし・I066 #1） =="
# 実出力書式: 「## 高リスク判定」見出し + 次行「判定: Yes/No」（別行）。VERDICT 行を持たない旧形式を想定。
printf '## 高リスク判定\n判定: Yes\n該当条件: 認可変更\n' > "$TMP/hr1"; ck TC-24 HIGHRISK "$(detect_plan_verdict "$TMP/hr1")"
printf '## 高リスク判定\n判定: No\n該当条件: なし\n'      > "$TMP/hr2"; ck TC-25 OK       "$(detect_plan_verdict "$TMP/hr2")"
# アンカリング: 高リスク判定ブロックは No、別セクションに 判定: Yes → 誤検出しない
printf '## 高リスク判定\n判定: No\n## その他\n判定: Yes\n' > "$TMP/hr3"; ck TC-26 OK       "$(detect_plan_verdict "$TMP/hr3")"
# TC-27: 旧行単位 grep が多行 Yes に非マッチ（バグの存在＝修正の前提を固定化）
ck_false TC-27-old-grep-nonmatch grep -qiE "高リスク判定.*Yes" "$TMP/hr1"
# TC-27b: 大文字小文字を無視（旧 grep -i パリティ）— 小文字 yes も HIGHRISK
printf '## 高リスク判定\n判定: yes\n' > "$TMP/hr4"; ck TC-27b HIGHRISK "$(detect_plan_verdict "$TMP/hr4")"

echo "== TC-28〜31: append_review_link 冪等追記（I066 #3） =="
ck_true TC-28-fn-append declare -F append_review_link
# TC-29/30:「## レビュー結果」を含まない plan に 2 回追記 → 見出し1個・リンク2行（履歴保持）
printf '# plan\n本文\n' > "$TMP/pl1"
append_review_link "$TMP/pl1" "20260618_0900" "判定: 完了" "I066_plan_review_a.md"
append_review_link "$TMP/pl1" "20260618_1000" "判定: 完了" "I066_plan_review_b.md"
ck TC-29 1 "$(grep -c '^## レビュー結果$' "$TMP/pl1")"
# リンク行はレビューリンク形式で厳密にカウント（本文の箇条書き混入による偽陽性を排除）
ck TC-30 2 "$(grep -cF '](../../reviews/' "$TMP/pl1")"
# TC-31: 見出しなし plan への初回（1回）追記 → 見出し+リンク 1組（TC-29 との差分は呼び出し回数のみ）
printf '# plan\n本文\n' > "$TMP/pl2"
append_review_link "$TMP/pl2" "20260618_1100" "判定: 完了" "I066_plan_review_c.md"
ck TC-31a 1 "$(grep -c '^## レビュー結果$' "$TMP/pl2")"
ck TC-31b 1 "$(grep -cF '](../../reviews/' "$TMP/pl2")"

echo "== TC-20: bash -n 構文チェック =="
ck_true TC-20-syntax-code bash -n "$CODE_REVIEW"
ck_true TC-20-syntax-plan bash -n "$PLAN_REVIEW"
ck_true TC-20-syntax-self bash -n "scripts/claude/tests/test_review_verdict.sh"

printf '\n==== I062 review-verdict tests: PASS=%d FAIL=%d ====\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
