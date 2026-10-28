#!/usr/bin/env bash
# I210（plan_I210.md 4.8・auto_test TC-01c）: stress-repeat.sh（負荷をかけてテストを繰り返す道具）が、
# 失敗を合格にしないこと（1 回でも落ちれば exit 1）・引数の誤りで exit 2・終わった後に負荷のプロセスを残さないことを確かめる。
# 実行: bash scripts/claude/tests/test_stress_repeat.sh
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
SR="$REPO_ROOT/scripts/claude/tests/stress-repeat.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
yn() { if "$@" >/dev/null 2>&1; then echo yes; else echo no; fi; }

printf 'exit 0\n' > "$TMP/ok.sh"
printf 'exit 1\n' > "$TMP/ng.sh"
# 2 回目だけ落ちる（回数をファイルに数える）
# shellcheck disable=SC2016  # 書き出すスクリプトの中身（ここでは展開しない）
printf 'n=$(( $(cat "%s" 2>/dev/null || echo 0) + 1 )); echo "$n" > "%s"; [ "$n" -ne 2 ]\n' "$TMP/cnt" "$TMP/cnt" > "$TMP/second.sh"
# sr <名前> <引数…>: 出力を $TMP/<名前>.out に、終了コードを出す
sr() { local n="$1"; shift; bash "$SR" "$@" > "$TMP/$n.out" 2>&1; echo $?; }
has() { grep -qxF -- "$2" "$TMP/$1.out"; }

ck "S1 必ず合格するスクリプト 2 回 → exit 0・STRESS: 2/2・RUN 1/2: PASS" "0 yes yes yes" \
  "$(sr s1 2 "$TMP/ok.sh" 1) $(yn has s1 'STRESS: 2/2') $(yn has s1 'RUN 1: PASS') $(yn has s1 'RUN 2: PASS')"
# S5: S1 の後に負荷のループ（stress-repeat.sh の子のサブシェル）が残っていない
ck "S5 終わった後に負荷のプロセスが残らない" no "$(yn pgrep -f "bash $SR 2 $TMP/ok.sh 1")"
ck "FG-S2 必ず落ちるスクリプト 2 回 → exit 1・STRESS: 0/2" "1 yes" "$(sr s2 2 "$TMP/ng.sh" 1) $(yn has s2 'STRESS: 0/2')"
ck "FG-S3 2 回目だけ落ちる → exit 1・STRESS: 1/2・RUN 2: FAIL" "1 yes yes" \
  "$(sr s3 2 "$TMP/second.sh" 1) $(yn has s3 'STRESS: 1/2') $(yn has s3 'RUN 2: FAIL')"
ck "S4 引数の誤り（回数 x・回数 0・スクリプトが無い・引数なし）→ どれも exit 2" "2 2 2 2" \
  "$(sr s4a x "$TMP/ok.sh" 1) $(sr s4b 0 "$TMP/ok.sh" 1) $(sr s4c 1 "$TMP/none.sh" 1) $(sr s4d)"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
