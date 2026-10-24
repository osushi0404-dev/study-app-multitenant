#!/usr/bin/env bash
# I187: check-frontend-evidence.sh（frontend/src を変えたイシューで画面確認の記録と画像の実在を確かめる判定）を決定論検証する。
# 実行: bash scripts/claude/tests/test_check_frontend_evidence.sh
# 一時リポジトリに基準コミット（ブランチ base）と変更コミットを作り、BASE_REF=base で判定させる。
# ケースは docs/tests/open/I187_auto_test.md の TC-07（E1〜E12）と対応する。
# 別のスクリプトに当てるとき（false-green の確認）: CHECK=<スクリプト> bash scripts/claude/tests/test_check_frontend_evidence.sh
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
CHECK="${CHECK:-$REPO_ROOT/scripts/claude/check-frontend-evidence.sh}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

HDR='| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |'
SEP='|---|---|---|---|---|---|---|'
row() { printf '| 2026-10-24 21:00 | abc1234 | 問題管理を開く | e2e_user_a | 一覧が出る | 一覧が出た | %s |\n' "$1"; }

# $1=ケース名 $2=変更するファイル（frontend/src/App.tsx か backend/x.py）$3=記録の置き場所（open/closed/none）
# $4=記録の本文（## 画面確認 以下。空なら見出しなし）$5=作る画像（空白区切り）
setup() {
  local d="$TMP/$1" f
  mkdir -p "$d"
  git -C "$d" init -q
  git -C "$d" checkout -q -b base
  mkdir -p "$d/frontend/src" "$d/backend"
  echo "base" > "$d/frontend/src/App.tsx"
  echo "base" > "$d/backend/x.py"
  git -C "$d" add -A
  git -C "$d" -c user.email=t@example.com -c user.name=t commit -qm base
  git -C "$d" checkout -q -b feature
  echo "change" >> "$d/$2"
  if [ "$3" != "none" ]; then
    mkdir -p "$d/docs/tests/$3"
    printf '# I999 手動テスト\n\n%s\n' "$4" > "$d/docs/tests/$3/I999_manual_test.md"
  fi
  git -C "$d" add -A
  git -C "$d" -c user.email=t@example.com -c user.name=t commit -qm change
  mkdir -p "$d/.evidence/I999"
  for f in $5; do echo png > "$d/.evidence/I999/$f"; done
  echo "$d"
}
run() { (cd "$1" && BASE_REF=base bash "$CHECK" "${2:-I999}" >/dev/null 2>&1); echo $?; }

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }

SEC="## 画面確認"
ck "E1 frontend/src を変えていない"   0 "$(run "$(setup e1 backend/x.py none '' '')")"
ck "E2 画面確認の見出しが無い"        1 "$(run "$(setup e2 frontend/src/App.tsx open '| No | 手順 |' '')")"
ck "E3 画像が実在する"                0 "$(run "$(setup e3 frontend/src/App.tsx open "$SEC
$HDR
$SEP
$(row login-a-1.png)" 'login-a-1.png')")"
ck "E4 画像が実在しない"              1 "$(run "$(setup e4 frontend/src/App.tsx open "$SEC
$HDR
$SEP
$(row login-a-1.png)" '')")"
ck "E5 理由つき"                      0 "$(run "$(setup e5 frontend/src/App.tsx open "$SEC
$HDR
$SEP
$(row '理由: バックエンドだけの不具合でエラー画面を出せないため')" '')")"
ck "E6 理由が空"                      1 "$(run "$(setup e6 frontend/src/App.tsx open "$SEC
$HDR
$SEP
$(row '理由:')" '')")"
ck "E7 .. を含む名前"                 1 "$(run "$(setup e7 frontend/src/App.tsx open "$SEC
$HDR
$SEP
$(row '../secret.png')" '')")"
ck "E8 テンプレートの空行だけ"        1 "$(run "$(setup e8 frontend/src/App.tsx open "$SEC
$HDR
$SEP
|  |  |  |  |  |  |  |" '')")"
ck "E9 合格と不合格が 1 行ずつ"       1 "$(run "$(setup e9 frontend/src/App.tsx open "$SEC
$HDR
$SEP
$(row a.png)
$(row missing.png)" 'a.png')")"
ck "E10 画像 2 つがどちらも実在"      0 "$(run "$(setup e10 frontend/src/App.tsx open "$SEC
$HDR
$SEP
$(row 'a.png, b.png')" 'a.png b.png')")"
ck "E11 記録が closed にだけある"     0 "$(run "$(setup e11 frontend/src/App.tsx closed "$SEC
$HDR
$SEP
$(row a.png)" 'a.png')")"
E12D="$(setup e12 backend/x.py none '' '')"
ck "E12a 引数なし"                    2 "$( (cd "$E12D" && BASE_REF=base bash "$CHECK" >/dev/null 2>&1); echo $?)"
ck "E12b I99 の形"                    2 "$(run "$E12D" I99)"
# 追加: 記録が無い（frontend/src を変えた）・基準が無い（git diff が失敗）は不合格
ck "E13 記録が無い"                   1 "$(run "$(setup e13 frontend/src/App.tsx none '' '')")"
E14D="$(setup e14 frontend/src/App.tsx none '' '')"
ck "E14 基準のブランチが無い"         2 "$( (cd "$E14D" && BASE_REF=no-such-ref bash "$CHECK" I999 >/dev/null 2>&1); echo $?)"
# 見出しの後ろの別の節の表は数えない
ck "E15 別の節の表は数えない"         1 "$(run "$(setup e15 frontend/src/App.tsx open "$SEC
$HDR
$SEP

## 別の節
$HDR
$SEP
$(row a.png)" 'a.png')")"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
