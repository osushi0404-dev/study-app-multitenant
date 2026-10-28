#!/usr/bin/env bash
# I187: check-manual-test-executor.sh（手動テスト文書の Human の行を確かめる判定）を決定論検証する。
# 実行: bash scripts/claude/tests/test_check_manual_test_executor.sh
# 一時リポジトリに docs/tests/open/I999_manual_test.md を作って判定させる。
# ケースは docs/tests/closed/I187_auto_test.md の TC-28（X1〜X8）と docs/tests/open/I195_auto_test.md の TC-02 と対応する。
# I195: Human の行の備考は「試した手段: …」（前の「Claude で確かめられない理由: …」だけの行は不合格）。
# 終わったイシューの記録は判定にかけない（作った例だけで確かめる）。
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
$(row 2 Human '試した手段: Playwright MCP・tui-capture.sh。どちらも実機の操作感は分からない')")")"
ck "X2 Human・理由なし"          1 "$(run "$(setup x2 "$HDR
$SEP
$(row 1 Human '')")")"
ck "X3 Human・承認画面"          1 "$(run "$(setup x3 "$HDR
$SEP
| 1 | コマンドを流す | 承認画面が出る | Human |  | 試した手段: 画面が見えない |")")"
ck "X4 Claude だけ"              0 "$(run "$(setup x4 "$HDR
$SEP
$(row 1 Claude '')
$(row 2 Claude '')")")"
ck "X5 理由の後ろが空"           1 "$(run "$(setup x5 "$HDR
$SEP
$(row 1 Human '試した手段: ')")")"
ck "X6 実施環境の列があっても見つける" 1 "$(run "$(setup x6 "| No | 手順 | 期待結果 | 実施環境 | 実施者 | 実結果 | 備考 |
|---:|---|---|---|---|---|---|
| 1 | 画面を開く | 一覧が出る | 新規セッション | Human |  |  |")")"
ck "X7 文書が無い"               2 "$(run "$(setup x7 '')")"
ck "X8a 引数なし"                2 "$(run "$(setup x8a "$HDR")" '')"
ck "X8b 形が違う"                2 "$(run "$(setup x8b "$HDR")" I99)"
# 以下は敵対的レビュー 3 周目で足したケース
ck "X10 手順に \\| があっても列がずれない" 1 "$(run "$(setup x10 "$HDR
$SEP
| 1 | \`git log \\| head\` を流す | 1 行出る | Human |  |  |")")"
ck "X11 理由の中に \\| があっても理由を読める" 0 "$(run "$(setup x11 "$HDR
$SEP
| 1 | 画面を開く | 一覧が出る | Human |  | 試した手段: 実機の操作感（a \\| b）のため |")")"
for w in 承認なし 確認プロンプト 確認が出 確認画面 確認なし ダイアログ; do
  ck "X12 Human・言い換え（${w}）" 1 "$(run "$(setup "x12-${w}" "$HDR
$SEP
| 1 | コマンドを流す | ${w}で通る | Human |  | 試した手段: 新しいセッションでないと見えない |")")"
done
# 言葉が当たっても、check-permission-prompt.sh では確かめられない理由まで書いてあれば通す（BP 周の High: 正当な Human の行が止まる）
ck "X16 PR の Approve（理由にスクリプトで確かめられないわけ）" 0 "$(run "$(setup x16 "$HDR
$SEP
| 1 | PR を Approve する | 承認される | Human |  | 試した手段: check-permission-prompt.sh は Claude Code の承認画面だけを見るので使えない。bot は自分の PR を承認できない |")")"
ck "X17 言葉が当たり、理由にスクリプトの名前が無い" 1 "$(run "$(setup x17 "$HDR
$SEP
| 1 | PR を Approve する | 承認される | Human |  | 試した手段: bot は自分の PR を承認できない |")")"
ck "X13 実施者の列がある表が無い"  2 "$(run "$(setup x13 "| No | 手順 | 期待結果 |
|---|---|---|
| 1 | 画面を開く | 一覧が出る |")")"
ck "X14 太字の **Human**"         1 "$(run "$(setup x14 "$HDR
$SEP
$(row 1 '**Human**' '')")")"
ck "X15 実施者がユーザー"         1 "$(run "$(setup x15 "$HDR
$SEP
$(row 1 'ユーザー' '')")")"
# I195: 前の書き方（Claude で確かめられない理由）だけの行は不合格。例は I193 の No.5 の当初の書き方
# （X9〔I187 の終わった記録の判定〕は消した）
X19_DOC="$HDR
$SEP
| 5 | \`claude\` を起動し \`/\` を入力して候補を見る | 候補に \`/plan-issue\` が出る | Human |  | Claude で確かめられない理由: claude -p は一覧を出さない |"
ck "X19 I193 の No.5 の当初の書き方" 1 "$(run "$(setup x19 "$X19_DOC")")"
ck "X20 全角のコロン"             0 "$(run "$(setup x20 "$HDR
$SEP
$(row 1 Human '試した手段：Playwright MCP。Figma は開けない')")")"
# FG-X19: 空の判定を消した写しでは X19 が通ってしまう（＝規則が効いている）
FG_CHECK="$TMP/fg_check.sh"
python3 - "$CHECK" "$FG_CHECK" <<'PY'
import sys
src, dst = sys.argv[1:3]
s = open(src, encoding="utf-8").read()
a = 'if [ -z "$tried" ]; then'
if a not in s: sys.exit(1)
open(dst, "w", encoding="utf-8").write(s.replace(a, "if false; then"))
PY
ck "FG の写しが作れた"            0 "$?"
fg_run() { (cd "$1" && bash "$FG_CHECK" I999 >/dev/null 2>&1); echo $?; }
ck "FG-X19 空の判定を消すと通る"  0 "$(fg_run "$(setup fg19 "$X19_DOC")")"

echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
