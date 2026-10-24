#!/usr/bin/env bash
# I187: check-manual-test-executor.sh（手動テスト文書の Human の行を確かめる判定）を決定論検証する。
# 実行: bash scripts/claude/tests/test_check_manual_test_executor.sh
# 一時リポジトリに docs/tests/open/I999_manual_test.md を作って判定させる。
# ケースは docs/tests/open/I187_auto_test.md の TC-28（X1〜X8）と対応する。
# 別のスクリプトに当てるとき（false-green の確認）: CHECK=<スクリプト> bash scripts/claude/tests/test_check_manual_test_executor.sh
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
CHECK="${CHECK:-$REPO_ROOT/scripts/claude/check-manual-test-executor.sh}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

HDR='| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |'
SEP='|---:|------|----------|--------|--------|------|'
row() { printf '| %s | 画面を開く | 一覧が出る | %s |  | %s |\n' "$1" "$2" "$3"; }

# $1=ケース名・$2=表の本文（空なら文書を作らない）
setup() {
  local d="$TMP/$1"
  mkdir -p "$d"
  git -C "$d" init -q
  if [ -n "$2" ]; then
    mkdir -p "$d/docs/tests/open"
    printf '# I999 手動テスト\n\n%s\n\n結論: OK / NG\n' "$2" > "$d/docs/tests/open/I999_manual_test.md"
  fi
  echo "$d"
}
run() { (cd "$1" && bash "$CHECK" "${2-I999}" >/dev/null 2>&1); echo $?; }

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }

ck "X1 Human・理由あり"          0 "$(run "$(setup x1 "$HDR
$SEP
$(row 1 Claude '')
$(row 2 Human 'Claude で確かめられない理由: 実機の操作感のため')")")"
ck "X2 Human・理由なし"          1 "$(run "$(setup x2 "$HDR
$SEP
$(row 1 Human '')")")"
ck "X3 Human・承認画面"          1 "$(run "$(setup x3 "$HDR
$SEP
| 1 | コマンドを流す | 承認画面が出る | Human |  | Claude で確かめられない理由: 画面が見えない |")")"
ck "X4 Claude だけ"              0 "$(run "$(setup x4 "$HDR
$SEP
$(row 1 Claude '')
$(row 2 Claude '')")")"
ck "X5 理由の後ろが空"           1 "$(run "$(setup x5 "$HDR
$SEP
$(row 1 Human 'Claude で確かめられない理由: ')")")"
ck "X6 実施環境の列があっても見つける" 1 "$(run "$(setup x6 "| No | 手順 | 期待結果 | 実施環境 | 実施者 | 実結果 | 備考 |
|---:|---|---|---|---|---|---|
| 1 | 画面を開く | 一覧が出る | 新規セッション | Human |  |  |")")"
ck "X7 文書が無い"               2 "$(run "$(setup x7 '')")"
ck "X8a 引数なし"                2 "$(run "$(setup x8a "$HDR")" '')"
ck "X8b 形が違う"                2 "$(run "$(setup x8b "$HDR")" I99)"
# TC-30: 本イシュー自身の手動テストに、理由の無い Human の行・承認画面を Human に振った行が無い
ck "X9 I187 の手動テスト"        0 "$(run "$REPO_ROOT" I187)"

echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
