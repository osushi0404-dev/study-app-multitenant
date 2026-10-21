#!/usr/bin/env bash
# I146: pretooluse_guard.py の cross-repo（fork）PR ポリシーを決定論検証する。
# 実行: bash scripts/claude/tests/test_pretooluse_gh_pr_guard.sh
#
# gh スタブを PATH 先頭に挿し、CROSS_VALUE / GH_FAIL_CROSS で fork 判定値を注入する
# （実 GitHub 非依存）。判定は exit code と ask JSON で行う（test_pretooluse_push_guard.sh と同型）。
# 検証範囲: gh pr の block/ask/素通し・MCP 経路・照会失敗時の ask 降格・自前 PR の無改変・
#           対象外コマンドで gh を呼ばないこと・false-green 注入（判定関数ごと）。
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
GUARD="$REPO_ROOT/scripts/claude/hooks/pretooluse_guard.py"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
STUB="$TMP/bin"
mkdir -p "$STUB"

# gh スタブ: isCrossRepository 照会に JSON を返す。全呼び出しを GH_LOG に記録する
# （対象外コマンドで照会が走らないことをアサートするため）。
cat > "$STUB/gh" <<'EOF'
#!/bin/bash
echo "$*" >> "${GH_LOG:-/dev/null}"
case "$*" in
  *isCrossRepository*)
    [ "${GH_FAIL_CROSS:-0}" = "1" ] && exit 1
    # SELF_IDENTS に含まれる識別子は自前 PR として答える（「別の PR を照会して素通し」を検出するため）
    # 識別子なし照会（＝カレントブランチの PR）も実環境どおり自前 PR として答える
    # （「識別子を gh に渡し忘れて自前 PR を検査し素通し」を検出するため・G11 のみ識別子なしが正）
    #  CURRENT_FORK=1 のときだけカレントブランチを fork PR 扱いにする（G11: fork を checkout 済みの状況）
    if [ "$1 $2" = "pr view" ] && { { [[ "$3" == -* ]] && [ "${CURRENT_FORK:-0}" != "1" ]; } || { [ -n "${SELF_IDENTS:-}" ] && [[ " $SELF_IDENTS " == *" $3 "* ]]; }; }; then
      printf '{"isCrossRepository":false,"headRepositoryOwner":{"login":"osushi0404-dev"},"headRepository":{"name":"study-app-multitenant"}}\n'
      exit 0
    fi
    case "${CROSS_VALUE-false}" in
      true|false)
        printf '{"isCrossRepository":%s,"headRepositoryOwner":{"login":"Dodothereal"},"headRepository":{"name":"study-app-multitenant"}}\n' "${CROSS_VALUE-false}" ;;
      "") printf '' ;;                                              # 空応答
      *)  printf '{"isCrossRepository":"%s"}\n' "${CROSS_VALUE-false}" ;;  # 想定外値
    esac
    ;;
  *) exit 0 ;;
esac
EOF
chmod +x "$STUB/gh"

# stdin JSON の組み立て（" や ` を含んでも安全にエスケープする）
json()  { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$1"; }
mjson() { python3 -c 'import json,sys; print(json.dumps({"tool_name":sys.argv[1],"tool_input":json.loads(sys.argv[2])}))' "$1" "$2"; }

# ASK 判別: exit 0 かつ stdout に permissionDecision=ask を含めば ASK、それ以外は exit code。
_decide() {
  local out="$1" code="$2"
  if [ "$code" = "0" ] && printf '%s' "$out" | grep -q '"permissionDecision":[[:space:]]*"ask"'; then
    echo "ASK"
  else
    echo "$code"
  fi
}

# env は明示的に渡す（呼び出し側の一時代入がエクスポートされるかに依存しない）。
# $1=command / $2=guard（省略時は実体）
runj() {
  local out code
  out=$(json "$1" | env PATH="$STUB:$PATH" \
        CROSS_VALUE="${CROSS_VALUE-false}" GH_FAIL_CROSS="${GH_FAIL_CROSS:-0}" \
        SELF_IDENTS="${SELF_IDENTS:-}" CURRENT_FORK="${CURRENT_FORK:-0}" \
        GH_LOG="${GH_LOG:-/dev/null}" python3 "${2:-$GUARD}" 2>/dev/null)
  code=$?
  _decide "$out" "$code"
}
# $1=tool_name / $2=tool_input JSON / $3=guard（省略時は実体）
runm() {
  local out code
  out=$(mjson "$1" "$2" | env PATH="$STUB:$PATH" \
        CROSS_VALUE="${CROSS_VALUE-false}" GH_FAIL_CROSS="${GH_FAIL_CROSS:-0}" \
        SELF_IDENTS="${SELF_IDENTS:-}" CURRENT_FORK="${CURRENT_FORK:-0}" \
        GH_LOG="${GH_LOG:-/dev/null}" python3 "${3:-$GUARD}" 2>/dev/null)
  code=$?
  _decide "$out" "$code"
}

pass=0; fail=0
ck() {
  if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1))
  else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi
}

# MCP の tool_input（キー名は対象 3 ツールの JSON Schema 実測値＝スネークケース）
MCP_PR='{"owner":"osushi0404-dev","repo":"study-app-multitenant","pull_number":257}'
MCP_APPROVE='{"owner":"osushi0404-dev","repo":"study-app-multitenant","pull_number":257,"body":"x","event":"APPROVE"}'
MCP_COMMENT='{"owner":"osushi0404-dev","repo":"study-app-multitenant","pull_number":257,"body":"x","event":"COMMENT"}'
MCP_NONUM='{"owner":"osushi0404-dev","repo":"study-app-multitenant"}'

# ===== gh pr（fork 由来 PR） =====
ck "G1 gh pr merge (fork)"            2   "$(CROSS_VALUE=true runj 'gh pr merge 257 --squash')"
ck "G2 gh pr merge (自前)"             0   "$(CROSS_VALUE=false runj 'gh pr merge 257')"
ck "G3 gh pr ready (fork)"            ASK "$(CROSS_VALUE=true runj 'gh pr ready 257')"
ck "G4 gh pr edit (fork)"             ASK "$(CROSS_VALUE=true runj 'gh pr edit 257 --base develop')"
ck "G5 gh pr review --approve (fork)" ASK "$(CROSS_VALUE=true runj 'gh pr review 257 --approve')"
ck "G6 gh pr review --comment (fork)" 0   "$(CROSS_VALUE=true runj 'gh pr review 257 --comment --body x')"
ck "G7 gh pr close (fork)"            0   "$(CROSS_VALUE=true runj 'gh pr close 257')"
ck "G8 gh pr comment (fork)"          0   "$(CROSS_VALUE=true runj 'gh pr comment 257 --body x')"
ck "G9 gh pr view (fork)"             0   "$(CROSS_VALUE=true runj 'gh pr view 257 --json state')"
ck "G10 gh pr checks (fork)"          0   "$(CROSS_VALUE=true runj 'gh pr checks 257')"
ck "G11 gh pr merge 識別子なし"        2   "$(CROSS_VALUE=true CURRENT_FORK=1 runj 'gh pr merge')"
ck "G12 gh pr merge URL 形式"          2   "$(CROSS_VALUE=true runj 'gh pr merge https://github.com/o/r/pull/257')"

# ===== MCP 経路 =====
ck "G13 mcp merge (fork)"             2   "$(CROSS_VALUE=true runm mcp__github__merge_pull_request "$MCP_PR")"
ck "G14 mcp update branch (fork)"     ASK "$(CROSS_VALUE=true runm mcp__github__update_pull_request_branch "$MCP_PR")"
ck "G15 mcp review APPROVE (fork)"    ASK "$(CROSS_VALUE=true runm mcp__github__create_pull_request_review "$MCP_APPROVE")"
ck "G16 mcp review COMMENT (fork)"    0   "$(CROSS_VALUE=true runm mcp__github__create_pull_request_review "$MCP_COMMENT")"

# ===== 失敗時の降格・自前 PR の無改変 =====
ck "G17 照会失敗=ask 降格"             ASK "$(CROSS_VALUE=true GH_FAIL_CROSS=1 runj 'gh pr merge 257')"
ck "G18 gh pr ready (自前)"            0   "$(CROSS_VALUE=false runj 'gh pr ready 257')"
ck "G19 mcp merge (自前)"              0   "$(CROSS_VALUE=false runm mcp__github__merge_pull_request "$MCP_PR")"

# ===== 対象外は gh を呼ばない =====
GH_LOG="$TMP/ghlog.g20" ; : > "$GH_LOG"
ck "G20 無関係コマンド"                0   "$(CROSS_VALUE=true GH_LOG="$GH_LOG" runj 'ls -la')"
ck "G20b 無関係コマンドで gh 未呼出"   0   "$(wc -l < "$GH_LOG" | tr -d ' ')"
GH_LOG="$TMP/ghlog.g24" ; : > "$GH_LOG"
ck "G24 対象外 MCP ツール"             0   "$(CROSS_VALUE=true GH_LOG="$GH_LOG" runm mcp__github__get_pull_request "$MCP_PR")"
ck "G24b 対象外 MCP で gh 未呼出"      0   "$(wc -l < "$GH_LOG" | tr -d ' ')"
unset GH_LOG

# ===== エスケープ・既存ガードとの順序 =====
ck "G21 DANGER_OK は人の承認（I174）"  ASK "$(CROSS_VALUE=true runj 'DANGER_OK=1 gh pr merge 257')"
ck "G21b DANGER_OK でも checkout は承認" ASK "$(CROSS_VALUE=true runj 'DANGER_OK=1 gh pr checkout 257')"
ck "G21c DANGER_OK・自前 PR は素通し"   0   "$(CROSS_VALUE=false runj 'DANGER_OK=1 gh pr merge 257')"
ck "G22 rm -rf 同居は hard-block 優先"  2   "$(CROSS_VALUE=true runj 'gh pr ready 257 && rm -rf x')"  # ask 種別の動詞で順序を検証（merge だと cross ガード自身も exit 2 で順序が見えない）
ck "G23 mcp pull_number なし=ask"      ASK "$(CROSS_VALUE=true runm mcp__github__merge_pull_request "$MCP_NONUM")"

# ===== 想定外値・空応答は ask 降格 =====
ck "G25 空応答=ask 降格"               ASK "$(CROSS_VALUE='' runj 'gh pr merge 257')"
ck "G26 想定外値=ask 降格"             ASK "$(CROSS_VALUE=hoge runj 'gh pr merge 257')"

# ===== ask 文言に head リポジトリ名が含まれる =====
ASK_OUT=$(json 'gh pr ready 257' | env PATH="$STUB:$PATH" CROSS_VALUE=true \
          python3 "$GUARD" 2>/dev/null)
printf '%s' "$ASK_OUT" | grep -q "Dodothereal/study-app-multitenant"
ck "G27 ask 文言に head リポジトリ名"  0 "$?"

# ===== 敵対的レビュー（2026-10-16）対応: 区切り・前置・-R・値付きフラグ =====
# 複数行・空白なし区切り・サブシェル・コマンド置換で gh pr merge を隠さない
ck "G28 複数行の 2 行目 merge"           2   "$(CROSS_VALUE=true runj $'git status\ngh pr merge 257 --squash')"
ck "G29 空白なし ; の後の merge"         2   "$(CROSS_VALUE=true runj 'true;gh pr merge 257')"
ck "G30 & の後の merge"                  2   "$(CROSS_VALUE=true runj 'echo ok& gh pr merge 257')"
ck "G31 サブシェル (merge)"              2   "$(CROSS_VALUE=true runj '(gh pr merge 257)')"
# shellcheck disable=SC2016  # $( を展開させず文字列のまま hook に渡す意図
ck "G32 コマンド置換 \$(merge)"          2   "$(CROSS_VALUE=true runj 'echo $(gh pr merge 257)')"
# 前置（環境変数・ラッパー・絶対パス）
ck "G33 GH_REPO= 前置"                   2   "$(CROSS_VALUE=true runj 'GH_REPO=o/r gh pr merge 257')"
ck "G34 env 前置"                        2   "$(CROSS_VALUE=true runj 'env gh pr merge 257')"
ck "G35 command 前置"                    2   "$(CROSS_VALUE=true runj 'command gh pr merge 257')"
ck "G36 絶対パス /usr/bin/gh"            2   "$(CROSS_VALUE=true runj '/usr/bin/gh pr merge 257')"
ck "G37 timeout 前置"                    2   "$(CROSS_VALUE=true runj 'timeout 60 gh pr merge 257')"
# -R / --repo / GH_REPO は照会側へ渡す（別リポジトリの PR を検査しない）
GH_LOG="$TMP/ghlog.adv"
: > "$GH_LOG"
ck "G38 gh -R o/r pr merge（グローバル位置）" 2 "$(CROSS_VALUE=true GH_LOG="$GH_LOG" runj 'gh -R o/r pr merge 257')"
grep -q -- '--repo o/r' "$GH_LOG"
ck "G38b グローバル -R が照会に渡る"    0   "$?"
: > "$GH_LOG"
ck "G39 gh pr merge 257 --repo o/r"      2   "$(CROSS_VALUE=true GH_LOG="$GH_LOG" runj 'gh pr merge 257 --repo o/r')"
grep -q -- '--repo o/r' "$GH_LOG"
ck "G39b --repo が照会に渡る"           0   "$?"
: > "$GH_LOG"
ck "G40 GH_REPO 前置"                    2   "$(CROSS_VALUE=true GH_LOG="$GH_LOG" runj 'GH_REPO=o/r gh pr merge 257')"
grep -q -- '--repo o/r' "$GH_LOG"
ck "G40b GH_REPO が照会に渡る"          0   "$?"
# 値付きフラグの値を PR 識別子と取り違えない（12 は自前 PR として応答するスタブ）
ck "G41 --subject 12 257"                2   "$(CROSS_VALUE=true SELF_IDENTS=12 runj 'gh pr merge --subject 12 257')"
ck "G42 -t 12 257"                       2   "$(CROSS_VALUE=true SELF_IDENTS=12 runj 'gh pr merge -t 12 257')"
ck "G43 --body=12 は値を消費しない"      2   "$(CROSS_VALUE=true SELF_IDENTS=12 runj 'gh pr merge --body=12 257')"
ck "G44 edit --title 12 257"             ASK "$(CROSS_VALUE=true SELF_IDENTS=12 runj 'gh pr edit --title 12 257')"
ck "G45 review -b 12 -a 257"             ASK "$(CROSS_VALUE=true SELF_IDENTS=12 runj 'gh pr review -b 12 -a 257')"
# approve の結合・= 形式
ck "G46 review -ab LGTM"                 ASK "$(CROSS_VALUE=true runj 'gh pr review 257 -ab LGTM')"
ck "G47 review --approve=true"           ASK "$(CROSS_VALUE=true runj 'gh pr review 257 --approve=true')"
ck "G48 review -ba（-b の値が a）"       0   "$(CROSS_VALUE=true runj 'gh pr review 257 -ba')"
# 誤検出しない・自前 PR の挙動は不変（AC-12）
# 引用符の中身はデータ（I174 と同じ方針・2026-10-16 ユーザー指示）: 判定しない
ck "G49 クォート内の改行＋merge 文字列"  0   "$(CROSS_VALUE=true runj $'gh pr comment 1 --body "x\ngh pr merge 257"')"
ck "G50 自前 PR の複数行 merge"          0   "$(CROSS_VALUE=false runj $'git status\ngh pr merge 261')"
: > "$GH_LOG"
ck "G51 複数行の無関係コマンド"          0   "$(CROSS_VALUE=true GH_LOG="$GH_LOG" runj $'git status\nls -la')"
ck "G51b 無関係コマンドで gh 未呼出"     0   "$(wc -l < "$GH_LOG" | tr -d ' ')"
# 識別子を一意に決められない（位置引数が複数）場合は ask に降格する
ck "G52 位置引数が複数=ask 降格"         ASK "$(CROSS_VALUE=false runj 'gh pr merge 261 257')"
# 照会に識別子と repo が実際に渡ること（スタブが引数を見ない tautology の解消）
: > "$GH_LOG"
CROSS_VALUE=true GH_LOG="$GH_LOG" runm mcp__github__merge_pull_request "$MCP_PR" >/dev/null
grep -q -- 'pr view 257 --repo osushi0404-dev/study-app-multitenant' "$GH_LOG"
ck "G53 MCP の pull_number/owner/repo が照会に渡る" 0 "$?"
: > "$GH_LOG"
CROSS_VALUE=true GH_LOG="$GH_LOG" runj 'gh pr merge 257' >/dev/null
grep -q -- 'pr view 257 ' "$GH_LOG"
ck "G54 Bash の識別子が照会に渡る"      0   "$?"
# 個別分岐（削除しても落ちなかった分岐）
ck "G55 review -a（短縮形）"             ASK "$(CROSS_VALUE=true runj 'gh pr review 257 -a')"
# checkout=block（hook 本体の置き換え防止）・update-branch=ask（MCP 版と揃える）（R10・2026-10-16 承認）
ck "G57 checkout (fork)"                 2   "$(CROSS_VALUE=true runj 'gh pr checkout 257')"
ck "G58 checkout (自前)"                 0   "$(CROSS_VALUE=false runj 'gh pr checkout 261')"
ck "G59 checkout -b x 257 (fork)"        2   "$(CROSS_VALUE=true runj 'gh pr checkout -b x 257')"
ck "G60 update-branch (fork)"            ASK "$(CROSS_VALUE=true runj 'gh pr update-branch 257 --rebase')"
ck "G61 update-branch (自前)"            0   "$(CROSS_VALUE=false runj 'gh pr update-branch 261')"
# ===== 敵対的レビュー第 2 周（2026-10-16）対応: サブコマンド別フラグ表・gh の位置非依存検出・全件判定 =====
# merge の -m は値なし（--merge）。値ありと誤認すると 257 を読み捨てて自前を照会する
ck "G62 merge -m 257"                    2   "$(CROSS_VALUE=true runj 'gh pr merge -m 257')"
ck "G63 merge -dm 257"                   2   "$(CROSS_VALUE=true runj 'gh pr merge -dm 257')"
ck "G64 merge 257 未知フラグ=ask"         ASK "$(CROSS_VALUE=false runj 'gh pr merge 261 --foo')"
# ヒアドキュメント本文はデータ（誤 block しない）。終端の後ろの実コマンド・終端なしは検出する
ck "G65 heredoc 本文の merge は無視"     0   "$(CROSS_VALUE=true runj $'git commit -F - <<\'X\'\nfix\ngh pr merge 257\nX')"
ck "G66 heredoc 本文の \`checkout\` 無視" 0  "$(CROSS_VALUE=true runj $'cat > /tmp/n.md <<\'X\'\n手順: don\'t run `gh pr checkout 257`\nX')"
ck "G67 heredoc 終端後の merge"          2   "$(CROSS_VALUE=true runj $'cat <<EOF\nx\nEOF\ngh pr merge 257')"
ck "G68 heredoc 終端なし=除外しない"     2   "$(CROSS_VALUE=true runj $'cat <<EOF\ngh pr merge 257')"
# シェル構文（キーワード・グループ・否定・前置リダイレクト）
ck "G69 if/then 内の merge"              2   "$(CROSS_VALUE=true runj 'if true; then gh pr merge 257; fi')"
ck "G70 for/do 内の merge"               2   "$(CROSS_VALUE=true runj 'for i in 1; do gh pr merge 257; done')"
ck "G71 { } 内の merge"                  2   "$(CROSS_VALUE=true runj '{ gh pr merge 257; }')"
ck "G72 ! merge"                         2   "$(CROSS_VALUE=true runj '! gh pr merge 257')"
ck "G73 前置 >/dev/null"                 2   "$(CROSS_VALUE=true runj '>/dev/null gh pr merge 257')"
ck "G74 前置 &>/dev/null"                2   "$(CROSS_VALUE=true runj '&>/dev/null gh pr merge 257')"
# 値付きフラグを持つラッパー・その他ラッパー
ck "G75 nice -n 5"                       2   "$(CROSS_VALUE=true runj 'nice -n 5 gh pr merge 257')"
ck "G76 sudo -u bob"                     2   "$(CROSS_VALUE=true runj 'sudo -u bob gh pr merge 257')"
ck "G77 env -u X"                        2   "$(CROSS_VALUE=true runj 'env -u X gh pr merge 257')"
ck "G78 timeout -s KILL 60"              2   "$(CROSS_VALUE=true runj 'timeout -s KILL 60 gh pr merge 257')"
ck "G79 timeout --kill-after=5 60"       2   "$(CROSS_VALUE=true runj 'timeout --kill-after=5 60 gh pr merge 257')"
ck "G80 nohup"                           2   "$(CROSS_VALUE=true runj 'nohup gh pr merge 257')"
ck "G81 time"                            2   "$(CROSS_VALUE=true runj 'time gh pr merge 257')"
ck "G82 exec"                            2   "$(CROSS_VALUE=true runj 'exec gh pr merge 257')"
ck "G83 env -i"                          2   "$(CROSS_VALUE=true runj 'env -i gh pr merge 257')"
ck "G84 xargs（識別子が外から）=ask"     ASK "$(CROSS_VALUE=false runj 'echo 257 | xargs gh pr merge')"
# pr と verb の間のフラグ・fd リダイレクト・コメント・パイプ・バッククォート・クォート不整合
ck "G85 gh pr --repo o/r merge"          2   "$(CROSS_VALUE=true runj 'gh pr --repo o/r merge 257')"
ck "G86 gh pr -R o/r merge"              2   "$(CROSS_VALUE=true runj 'gh pr -R o/r merge 257')"
ck "G87 自前 merge 2>&1 は ask しない"   0   "$(CROSS_VALUE=false runj 'gh pr merge 12 2>&1')"
ck "G88 fork merge 2>&1"                 2   "$(CROSS_VALUE=true runj 'gh pr merge 257 2>&1')"
ck "G89 # コメント行の次の merge"        2   "$(CROSS_VALUE=true runj $'true #note\ngh pr merge 257')"
ck "G90 クォート付きコメントの次"        2   "$(CROSS_VALUE=true runj $'true # don\'t\ngh pr merge 257')"
ck "G91 パイプの後の merge"              2   "$(CROSS_VALUE=true runj 'echo y | gh pr merge 257')"
# shellcheck disable=SC2016  # バッククォートを展開させず文字列のまま hook に渡す意図
ck "G92 バッククォート内の merge"        2   "$(CROSS_VALUE=true runj 'echo `gh pr merge 257`')"
ck "G93 クォート不整合でも検出"          2   "$(CROSS_VALUE=true runj 'echo "oops; gh pr merge 257')"
# 複数の gh pr を全件判定（先頭の自前 PR で後続の fork を見逃さない）
ck "G94 自前 merge; fork merge"          2   "$(CROSS_VALUE=true SELF_IDENTS=261 runj 'gh pr merge 261; gh pr merge 257')"
ck "G95 自前 merge && fork checkout"     2   "$(CROSS_VALUE=true SELF_IDENTS=261 runj 'gh pr merge 261 && gh pr checkout 257')"
ck "G96 fork edit; 自前 merge"           ASK "$(CROSS_VALUE=true SELF_IDENTS=261 runj 'gh pr edit 257 --base main; gh pr merge 261')"
# 照会先リポジトリ（各形式）・値の連結
: > "$GH_LOG"; CROSS_VALUE=true GH_LOG="$GH_LOG" runj 'gh --repo=o/r pr merge 257' >/dev/null
grep -q -- '--repo o/r' "$GH_LOG"; ck "G97 グローバル --repo= が照会に渡る" 0 "$?"
: > "$GH_LOG"; CROSS_VALUE=true GH_LOG="$GH_LOG" runj 'gh -Ro/r pr merge 257' >/dev/null
grep -q -- '--repo o/r' "$GH_LOG"; ck "G98 グローバル -Rx が照会に渡る"     0 "$?"
: > "$GH_LOG"; CROSS_VALUE=true GH_LOG="$GH_LOG" runj 'gh pr merge 257 -R o/r' >/dev/null
grep -q -- '--repo o/r' "$GH_LOG"; ck "G99 サブコマンド側 -R が照会に渡る" 0 "$?"
ck "G100 -bLGTM 257（値の連結）"          2   "$(CROSS_VALUE=true runj 'gh pr merge -bLGTM 257')"
# gh 既定エイリアス co・cd 後の識別子なし
ck "G101 gh co 257（fork）"               2   "$(CROSS_VALUE=true runj 'gh co 257')"
ck "G102 gh co 261（自前）"               0   "$(CROSS_VALUE=false runj 'gh co 261')"
ck "G103 cd 後の識別子なし merge=ask"     ASK "$(CROSS_VALUE=false runj 'cd /x && gh pr merge --squash')"
# 自前 PR の正規手順（/close 等）は不変
ck "G104 自前 merge --squash --delete-branch" 0 "$(CROSS_VALUE=false runj 'gh pr merge --squash --delete-branch')"
ck "G105 自前 ready（識別子なし）"        0   "$(CROSS_VALUE=false runj 'gh pr ready')"
ck "G106 自前 edit --body \$(heredoc)"    0   "$(CROSS_VALUE=false runj $'gh pr edit 261 --body "$(cat <<\'EOF\'\n## x (A) `y`\nEOF\n)"')"
# ===== 敵対的レビュー第 3 周（2026-10-16）対応: 行継続・語中 #・heredoc の厳密化・安全網 =====
# 行継続（\<改行>）は bash と同じく 1 コマンドに連結する
ck "G107 gh pr \\⏎ merge 257"            2   "$(CROSS_VALUE=true runj $'gh pr \\\n merge 257')"
ck "G108 gh \\⏎ pr merge 257"            2   "$(CROSS_VALUE=true runj $'gh \\\n pr merge 257')"
ck "G109 merge \\⏎ 257"                  2   "$(CROSS_VALUE=true runj $'gh pr merge \\\n  257 --squash')"
ck "G110 review 257 \\⏎ --approve"       ASK "$(CROSS_VALUE=true runj $'gh pr review 257 \\\n  --approve')"
ck "G111 自前 merge の折り返しは ask しない" 0 "$(CROSS_VALUE=false runj $'gh pr merge 236 \\\n  --squash --delete-branch')"
# 語中の # はコメントではない
ck "G112 echo a#b; merge"                2   "$(CROSS_VALUE=true runj 'echo a#b; gh pr merge 257')"
# shellcheck disable=SC2016  # ${#PATH} を展開させず文字列のまま hook に渡す意図
ck "G113 \${#PATH}; checkout"            2   "$(CROSS_VALUE=true runj 'echo ${#PATH}; gh pr checkout 257')"
# heredoc: クォート/コメント内の << は開始ではない・終端語の各形式・CRLF・here-string・<<-
ck "G114 \"<<X\" の次行 merge"           2   "$(CROSS_VALUE=true runj $'echo "<<X"\ngh pr merge 257\nX')"
ck "G115 コメント内 <<X の次行 merge"    2   "$(CROSS_VALUE=true runj $'true # <<X\ngh pr merge 257\nX')"
ck "G116 <<'END-OF-MSG' 本文は無視"      0   "$(CROSS_VALUE=true runj $'git commit -F - <<\'END-OF-MSG\'\nfix\n    gh pr merge 257 --squash\nEND-OF-MSG')"
ck "G117 <<\\EOF 本文は無視"             0   "$(CROSS_VALUE=true runj $'git commit -F - <<\\EOF\nfix\n    gh pr checkout 257\nEOF')"
ck "G118 <<'EOF.' 本文は無視"            0   "$(CROSS_VALUE=true runj $'git commit -F - <<\'EOF.\'\nfix: gh pr merge 257\nEOF.')"
ck "G119 CRLF の heredoc 本文は無視"     0   "$(CROSS_VALUE=true runj $'cat > /tmp/x.md <<\'EOF\'\r\nx gh pr merge 257\r\nEOF\r\n')"
ck "G120 <<EO\"F\" 終端後の merge"       2   "$(CROSS_VALUE=true runj $'cat <<EO"F"\nb\nEOF\ngh pr merge 257\nEO')"
ck "G121 here-string <<< の次行 merge"   2   "$(CROSS_VALUE=true runj $'cat <<<EOF\ngh pr merge 257\nEOF')"
ck "G122 <<- タブ終端後の merge"         2   "$(CROSS_VALUE=true runj $'cat <<-X\nb\n\tX\ngh pr merge 257\nX')"
# 値の位置のプロセス置換・クォートなしコマンド置換は識別子を確定できない → ask
ck "G123 --body-file <(…) 257"           ASK "$(CROSS_VALUE=false runj 'gh pr merge --body-file <(echo hi) 257')"
# shellcheck disable=SC2016  # $( を展開させず文字列のまま hook に渡す意図
ck "G124 --subject \$(…) 257"            ASK "$(CROSS_VALUE=false runj 'gh pr merge --subject $(echo x) 257')"
# フラグ表: 値なしフラグの後ろの識別子を読み捨てない（fork）
ck "G125 merge -s 257"                   2   "$(CROSS_VALUE=true runj 'gh pr merge -s 257')"
ck "G126 merge -r 257"                   2   "$(CROSS_VALUE=true runj 'gh pr merge -r 257')"
ck "G127 merge -d 257"                   2   "$(CROSS_VALUE=true runj 'gh pr merge -d 257')"
ck "G128 merge --squash 257"             2   "$(CROSS_VALUE=true runj 'gh pr merge --squash 257')"
ck "G129 merge --rebase 257"             2   "$(CROSS_VALUE=true runj 'gh pr merge --rebase 257')"
ck "G130 merge --merge 257"              2   "$(CROSS_VALUE=true runj 'gh pr merge --merge 257')"
ck "G131 merge --delete-branch 257"      2   "$(CROSS_VALUE=true runj 'gh pr merge --delete-branch 257')"
ck "G132 merge --admin 257"              2   "$(CROSS_VALUE=true runj 'gh pr merge --admin 257')"
ck "G133 merge --auto 257"               2   "$(CROSS_VALUE=true runj 'gh pr merge --auto 257')"
ck "G134 merge --disable-auto 257"       2   "$(CROSS_VALUE=true runj 'gh pr merge --disable-auto 257')"
ck "G135 checkout -f 257"                2   "$(CROSS_VALUE=true runj 'gh pr checkout -f 257')"
ck "G136 checkout --force 257"           2   "$(CROSS_VALUE=true runj 'gh pr checkout --force 257')"
ck "G137 checkout --detach 257"          2   "$(CROSS_VALUE=true runj 'gh pr checkout --detach 257')"
ck "G138 checkout --recurse-submodules 257" 2 "$(CROSS_VALUE=true runj 'gh pr checkout --recurse-submodules 257')"
ck "G139 ready --undo 257"               ASK "$(CROSS_VALUE=true runj 'gh pr ready --undo 257')"
ck "G140 update-branch --rebase 257"     ASK "$(CROSS_VALUE=true runj 'gh pr update-branch --rebase 257')"
# 値ありフラグ（各サブコマンド）の値を識別子にしない（12 は自前）
ck "G141 merge -F f 257"                 2   "$(CROSS_VALUE=true SELF_IDENTS=12 runj 'gh pr merge -F 12 257')"
ck "G142 merge --match-head-commit 12 257" 2 "$(CROSS_VALUE=true SELF_IDENTS=12 runj 'gh pr merge --match-head-commit 12 257')"
ck "G143 merge -A 12 257"                2   "$(CROSS_VALUE=true SELF_IDENTS=12 runj 'gh pr merge -A 12 257')"
ck "G144 checkout --branch 12 257"       2   "$(CROSS_VALUE=true SELF_IDENTS=12 runj 'gh pr checkout --branch 12 257')"
# 順序・--・リダイレクトが識別子より前・ValueError fallback・pushd・未知短縮・review の未知フラグ
ck "G145 fork merge; 自前 merge"         2   "$(CROSS_VALUE=true SELF_IDENTS=261 runj 'gh pr merge 257; gh pr merge 261')"
ck "G146 merge -- 257"                   2   "$(CROSS_VALUE=true runj 'gh pr merge -- 257')"
ck "G147 merge >/dev/null 257"           2   "$(CROSS_VALUE=true runj 'gh pr merge >/dev/null 257')"
ck "G148 merge 2>/dev/null 257"          2   "$(CROSS_VALUE=true runj 'gh pr merge 2>/dev/null 257')"
ck "G149 \$'it\\'s';merge（fallback）"   2   "$(CROSS_VALUE=true runj $'echo $\'it\\\'s\';gh pr merge 257')"
ck "G150 pushd 後の識別子なし=ask"       ASK "$(CROSS_VALUE=false runj 'pushd /x && gh pr merge')"
ck "G151 merge 261 -x（未知短縮）=ask"   ASK "$(CROSS_VALUE=false runj 'gh pr merge 261 -x')"
ck "G152 review 257 --foo=ask"           ASK "$(CROSS_VALUE=false runj 'gh pr review 257 --foo')"
ck "G153 gh.exe pr merge"                2   "$(CROSS_VALUE=true runj 'gh.exe pr merge 257')"
# 安全網: 判定しきれない gh pr の取り込み系記述は ask（block しない）・該当しない記述は素通し
ck "G154 クォート内の merge 記述は素通し" 0   "$(CROSS_VALUE=false runj 'git commit -m "note: gh pr merge 257 is blocked"')"
ck "G155 review --comment 記述は素通し"   0   "$(CROSS_VALUE=false runj 'gh pr review 261 --comment --body-file /tmp/r.md')"
ck "G156 view/checks は素通し"            0   "$(CROSS_VALUE=false runj 'gh pr view 261 --json state && gh pr checks 261')"
# 照会の重複排除（同じ PR への複数操作で照会 1 回）
: > "$GH_LOG"; CROSS_VALUE=false GH_LOG="$GH_LOG" runj 'gh pr edit 236 --add-label a && gh pr ready 236' >/dev/null
ck "G157 同一 PR の照会は 1 回"          1   "$(wc -l < "$GH_LOG" | tr -d ' ')"
# ===== 敵対的レビュー第 4 周・I174 引き継ぎ（2026-10-16）対応 =====
# 引き継ぎ 1: リダイレクトを PR 番号と読み違えない・--help だけの呼び出しは ask しない
ck "G158 merge --help 2>&1 | grep"       0   "$(CROSS_VALUE=false runj 'gh pr merge --help 2>&1 | grep -E "squash"; gh pr checkout --help 2>&1 | grep -E "force"')"
ck "G159 merge 12 >out <in 2>/dev/null"  0   "$(CROSS_VALUE=false runj 'gh pr merge 12 >/tmp/o <in 2>/dev/null')"
# 引き継ぎ 2: 引数として渡す文字列・ヒアドキュメント本文には反応しない
ck "G160 run '…gh pr merge…' の列"       0   "$(CROSS_VALUE=true runj "run 'gh pr merge 257' ; run 'gh pr edit 12 --base x' ; run 'gh co 257'")"
ck "G161 python3 -c \"…gh pr merge…\""   0   "$(CROSS_VALUE=true runj 'python3 -c "print(\"gh pr merge 257\")"')"
ck "G162 heredoc でスクリプトを書く"     0   "$(CROSS_VALUE=true runj $'cat > /tmp/t.sh <<\'EOF\'\nrun \'gh pr merge 257\'\nrun $\'cat <<X\\ndon\\\'t\\nX\\ngh pr merge 257\'\nEOF')"
# 第 4 周: 二重引用符内のコマンド置換に引用符があっても状態を取り違えない（後続の実コマンドを検出）
ck "G163 \"\$(printf '\"')\" ' #'; merge"  2  "$(CROSS_VALUE=true runj "echo \"\$(printf '\"')\" ' #' ; gh pr merge 257")"
ck "G164 \"\`printf '\"'\`\" ' #'; co"   2   "$(CROSS_VALUE=true runj "echo \"\`printf '\"'\`\" ' #' ; gh co 257")"
# 第 4 周: \$' と $$' は ANSI-C 引用ではない
ck "G165 \$\$'x\\' ' #'; merge"          2   "$(CROSS_VALUE=true runj "echo \$\$'x\\' ' #' ; gh pr merge 257")"
ck "G166 \\\$'a\\' ' #'; checkout"       2   "$(CROSS_VALUE=true runj "echo \\\$'a\\' ' #'; gh pr checkout 257")"
# 第 4 周: ブレース展開は識別子を確定できない → ask
ck "G167 merge -t {x,257}"               ASK "$(CROSS_VALUE=true runj 'gh pr merge -t {x,257}')"
ck "G168 gh co -b {x,257}"               ASK "$(CROSS_VALUE=true runj 'gh co -b {x,257}')"
ck "G169 review -b {x,-a} 257"           ASK "$(CROSS_VALUE=true runj 'gh pr review -b {x,-a} 257')"
# 第 4 周: 件数相殺（引用符で囲んだ verb は精密判定のみが数える）→ 件数不一致で ask
ck "G170 gh pr \"merge\" 12"             ASK "$(CROSS_VALUE=false runj 'gh pr "merge" 12')"
# 引用符の中のコマンド置換は実行される部分（精密判定が拾えなくても安全網が ask）
# shellcheck disable=SC2016  # $( を展開させず文字列のまま hook に渡す意図
ck "G171 echo \"\$(gh pr merge 257)\""   ASK "$(CROSS_VALUE=true runj 'echo "$(gh pr merge 257)"')"
# 算術式の << はヒアドキュメントではない
ck "G172 \$((1<<X)) の次行 merge"        2   "$(CROSS_VALUE=true runj $'echo $((1<<X))\ngh pr merge 257\nX')"
# 第 4 周 false-green 対応: 引用状態の各分岐（取り違えると後続の実コマンドをコメント/本文として消す）
ck "G173 \$'\\' # x'; merge（ANSI-C）"   2   "$(CROSS_VALUE=true runj "echo \$'\\' # x'; gh pr merge 257")"
ck "G174 \$'a #'; merge（ANSI-C 終端）"  2   "$(CROSS_VALUE=true runj "echo \$'a #'; gh pr merge 257")"
ck "G175 \"a\\\" # \"; merge（dq の \\\"）" 2 "$(CROSS_VALUE=true runj 'echo "a\" # "; gh pr merge 257')"
ck "G176 \\<<EOF はヒアドキュメントでない" 2  "$(CROSS_VALUE=true runj $'echo \\<<EOF\ngh pr merge 257\nEOF')"
ck "G177 ((x=1<<2)) の次行 checkout"     2   "$(CROSS_VALUE=true runj $'((x=1<<2))\ngh pr checkout 257\n2')"
ck "G178 <<-X の後ろの -X 行まで隠さない" 2  "$(CROSS_VALUE=true runj $'cat <<-X\nb\n\tX\ngh pr merge 257\n-X')"
ck "G179 << 'EOF'（空白入り）本文は無視"  0   "$(CROSS_VALUE=true runj $'git commit -F - << \'EOF\'\nfix: gh pr merge 257\nEOF')"
ck "G180 heredoc 2 つの本文は両方無視"    0   "$(CROSS_VALUE=true runj $'cat <<A <<B\na\nA\ngh pr merge 257\nB')"
# 照会キャッシュは repo ごと（同番号でも別リポジトリは別照会）
: > "$GH_LOG"; CROSS_VALUE=false GH_LOG="$GH_LOG" runj 'gh pr ready 257 -R self/r; gh pr ready 257 -R fork/x' >/dev/null
ck "G181 repo 違いの同番号は別照会"       2   "$(wc -l < "$GH_LOG" | tr -d ' ')"
# 第 4 周 D2: 安全網は線形時間（`gh pr` を 900 回並べた 1 行でも 2 秒以内。旧正規表現は 11 秒以上）
PAD=$(python3 -c 'print("echo" + " gh pr" * 900)')
T0=$(date +%s%N); CROSS_VALUE=false runj "$PAD" >/dev/null; T1=$(date +%s%N)
FAST=1; [ $(( (T1 - T0) / 1000000 )) -lt 2000 ] && FAST=0
ck "G182 安全網の走査が線形（900 件 < 2 秒）" 0 "$FAST"
# 第 5 周: ${…}（パラメータ展開）の中の # や << はコメント/ヒアドキュメントではない
# shellcheck disable=SC2016  # ${…} を展開させず文字列のまま hook に渡す意図
ck "G183 \${x:- #}; merge"                2   "$(CROSS_VALUE=true runj 'echo ${x:- #}; gh pr merge 257')"
# shellcheck disable=SC2016
ck "G184 \${x:-\$(echo }) #)}; merge"     2   "$(CROSS_VALUE=true runj 'echo ${x:-$(echo }) #)}; gh pr merge 257')"
# shellcheck disable=SC2016
ck "G185 \${x/<<true } の次行 co"         2   "$(CROSS_VALUE=true runj $'echo ${x/<<true }\ngh co 257\ntrue')"
# 第 5 周: \$( … ) 内の case パターンの ) は閉じ括弧ではない
# shellcheck disable=SC2016
ck "G186 \"\$(case …) …; merge)\""        ASK "$(CROSS_VALUE=true runj 'echo "$(case x in a) echo;; esac; gh pr merge 257)"')"
# 第 5 周: <<\$'EOF' の終端語は EOF（$ は引用の一部）
ck "G187 <<\$'EOF' 終端後の merge"        2   "$(CROSS_VALUE=true runj $'cat <<$\'EOF\'\nhi\nEOF\ngh pr merge 257\n$EOF')"
# 第 5 周: 判定は入力に対して線形（多数の gh 語・終端なし heredoc の多数行でもタイムアウトしない）
BIG=$(python3 -c 'print("echo " + "gh " * 24000 + "; gh pr merge 257")')
T0=$(date +%s%N); R=$(CROSS_VALUE=true runj "$BIG"); T1=$(date +%s%N)
FAST=1; [ $(( (T1 - T0) / 1000000 )) -lt 5000 ] && FAST=0
ck "G188 gh 語 2.4 万個でも 5 秒未満"     0   "$FAST"
ck "G188b その末尾の fork merge は block" 2   "$R"
HD=$(python3 -c 'print("cat <<EOF x\n" * 8000 + "gh pr merge 257")')
T0=$(date +%s%N); R=$(CROSS_VALUE=true runj "$HD"); T1=$(date +%s%N)
FAST=1; [ $(( (T1 - T0) / 1000000 )) -lt 5000 ] && FAST=0
ck "G189 終端なし heredoc 8000 行でも 5 秒未満" 0 "$FAST"
ck "G189b その末尾の fork merge は block" 2   "$R"
# 第 5 周: 引用符の中の {a,b}・"cd" はデータ（自前 PR で ask しない）
ck "G190 --title \"…{x,y}…\"（自前）"     0   "$(CROSS_VALUE=false runj 'gh pr edit 230 --title "feat: support {x,y} tokens"')"
ck "G191 --body '{\"a\": 1, \"b\": 2}'"   0   "$(CROSS_VALUE=false runj "gh pr edit 230 --body '{\"a\": 1, \"b\": 2}'")"
ck "G192 echo \"cd\"; gh pr ready"        0   "$(CROSS_VALUE=false runj 'echo "cd"; gh pr ready')"
# 第 6 周: 前処理の入れ子の取り違え（dq 内の ${・param 内の `・bt 内 dq の `・param 内の $'）でも
# 独立した 2 つ目の安全網（入れ子を含むコマンドは生の文字列で数える）が ask に倒す（黙って通さない）
# shellcheck disable=SC2016
ck "G193 \"\${x:-\" #\"}\" ; merge"        ASK "$(CROSS_VALUE=true runj 'echo "${x:-" #"}" ; gh pr merge 257')"
# shellcheck disable=SC2016
ck "G194 \"\${x:-\" #\"}\" ; co"           ASK "$(CROSS_VALUE=true runj 'echo "${x:-" #"}" ; gh co 257')"
# shellcheck disable=SC2016
ck "G195 \${x:-\`echo } #\`}; merge"       ASK "$(CROSS_VALUE=true runj 'echo ${x:-`echo } #`}; gh pr merge 257')"
# shellcheck disable=SC2016
ck "G196 \"\`echo \"\`  #\" ; merge"       ASK "$(CROSS_VALUE=true runj 'echo "`echo "`  #" ; gh pr merge 257')"
# shellcheck disable=SC2016
ck "G197 \${x:-\$'\\''} ; merge"           ASK "$(CROSS_VALUE=true runj "echo \${x:-\$'\\\\''} ; gh pr merge 257 ; echo \\\\'")"
# 入れ子を含まないコマンドの文字列データには反応しない（I174 方針の維持）
ck "G198 bash t.sh \$'cat <<EOF…merge'"    0   "$(CROSS_VALUE=true runj $'bash t.sh $\'cat <<EOF\\ndon\\\'t\\nEOF\\ngh pr merge 257\'')"
# 第 6 周: case/esac はコマンド位置のときだけ数える（引数の case で置換の閉じを誤らない）
# shellcheck disable=SC2016
ck "G199 X=\"\$(echo case)\"; echo \" # \"; merge" 2 "$(CROSS_VALUE=true runj 'X="$(echo case)"; echo " # "; gh pr merge 257')"
# shellcheck disable=SC2016
ck "G200 X=\"\$(echo test case)\"; 自前 merge" 0  "$(CROSS_VALUE=false runj 'X="$(echo test case)"; gh pr merge 12')"
# shellcheck disable=SC2016
ck "G201 n=\"\$(grep -c case f)\"; 自前 ready" 0  "$(CROSS_VALUE=false runj 'n="$(grep -c case README.md)"; echo "$n"; gh pr ready 12')"
# 第 6 周: 閉じ引用の直後の # はコメントではない（実行される部分の置換で誤認しない）
ck "G202 echo \"a\"#b; 自前 ready"        0   "$(CROSS_VALUE=false runj 'echo "a"#b; gh pr ready 12')"
# 第 6 周: 終端語の違う終端なし heredoc が多数でも線形
HD2=$(python3 -c 'print("".join("cat <<E%d\n" % k for k in range(9000)) + "gh pr merge 257")')
T0=$(date +%s%N); R=$(CROSS_VALUE=true runj "$HD2"); T1=$(date +%s%N)
FAST=1; [ $(( (T1 - T0) / 1000000 )) -lt 5000 ] && FAST=0
ck "G203 異なる終端語の heredoc 9000 個でも 5 秒未満" 0 "$FAST"
ck "G203b その末尾の fork merge は block" 2 "$R"
# 第 7 周: 引用なし終端語の heredoc 本文に行継続があると bash は連結後の行で終端判定する → 除去しない（fail-safe）
ck "G204 本文行継続＋コメント内 <<Z"      2   "$(CROSS_VALUE=true runj $'cat <<true\ntr\\\nue\ntrue # <<Z\ngh pr merge 257\nZ\ntrue\n')"
ck "G205 本文行継続＋混在終端語 <<A\"B\"" 2   "$(CROSS_VALUE=true runj $'cat <<true\ntr\\\nue\ncat <<A"B"\nAB\ngh pr merge 257\nA\ntrue\n')"
ck "G206 本文行継続のみ（block を保つ）"  2   "$(CROSS_VALUE=true runj $'cat <<true\ntr\\\nue\ngh pr merge 257\ntrue\n')"
# 第 8 周: 定番の "$(cat <<'EOF' … EOF\n)" の本文（展開されないデータ）には反応しない（自前 PR）
ck "G207 pr edit --body \"\$(cat <<'EOF' …merge…)\"" 0 "$(CROSS_VALUE=false runj $'gh pr edit 230 --body "$(cat <<\'EOF\'\n## 概要\nfork PR に対する `gh pr merge` を block\nEOF\n)"')"
ck "G208 commit -m \"\$(cat <<'EOF' …)\""   0   "$(CROSS_VALUE=false runj $'git commit -m "$(cat <<\'EOF\'\nfix(I146): gh pr merge の fork 判定を強化\nEOF\n)"')"
ck "G209 issue create --body \"\$(cat <<'EOF'…)\"" 0 "$(CROSS_VALUE=false runj $'gh issue create --title t --body "$(cat <<\'EOF\'\nfork PR を gh pr merge しないよう guard する\nEOF\n)"')"
# 定番形でも本文の後ろの実コマンドは数える（終端の後ろは除かない）
ck "G210 定番形の後ろの fork merge"       2   "$(CROSS_VALUE=true runj $'gh pr edit 230 --body "$(cat <<\'EOF\'\nx\nEOF\n)" ; gh pr merge 257')"
ck "G56 MCP pullNumber（キャメル）"      2   "$(CROSS_VALUE=true runm mcp__github__merge_pull_request '{"owner":"o","repo":"r","pullNumber":257}')"

# ===== false-green 注入（判定関数ごとに独立に裏取り） =====
BROKEN_GH="$TMP/guard_nogh.py"
sed 's/^def _gh_pr_target(cmd: str):$/&\n    return None/' "$GUARD" > "$BROKEN_GH"
# 精密判定を無効化すると block が消え、安全網の ask に落ちる（精密判定が block の担い手であることの裏取り）
ck "FG-A 判定無効化で block が消える"   ASK "$(CROSS_VALUE=true runj 'gh pr merge 257' "$BROKEN_GH")"
ck "FG-B 実体は block"                 2   "$(CROSS_VALUE=true runj 'gh pr merge 257')"

BROKEN_CROSS="$TMP/guard_nocross.py"
sed 's/^def _pr_is_cross_repo(ident, repo=None):$/&\n    return False, None/' "$GUARD" > "$BROKEN_CROSS"
ck "FG-C 常に自前扱いで素通し"          0   "$(CROSS_VALUE=true runj 'gh pr merge 257' "$BROKEN_CROSS")"

BROKEN_MCP="$TMP/guard_nomcp.py"
sed 's/^def _mcp_pr_target(tool_name: str, tool_input: dict):$/&\n    return None/' "$GUARD" > "$BROKEN_MCP"
ck "FG-D MCP 判定無効化で素通し"        0   "$(CROSS_VALUE=true runm mcp__github__merge_pull_request "$MCP_PR" "$BROKEN_MCP")"
ck "FG-E 実体は block（MCP）"           2   "$(CROSS_VALUE=true runm mcp__github__merge_pull_request "$MCP_PR")"

# ===== 第 4 周 false-green 対応: 安全網の各選択肢を、精密判定を無効化したガードで個別に検証 =====
for c in 'gh pr checkout 257' 'gh co 257' 'gh.exe pr merge 257' 'gh -R o/r pr merge 257' \
         'gh pr --repo o/r merge 257' 'gh pr ready 257' 'gh pr edit 257 --base main' \
         'gh pr update-branch 257' 'gh pr review 257 --approve' 'gh pr review 257 -a'; do
  ck "FG-N 安全網が拾う: $c" ASK "$(CROSS_VALUE=true runj "$c" "$BROKEN_GH")"
done
ck "FG-N 安全網は review --comment を拾わない" 0 "$(CROSS_VALUE=true runj 'gh pr review 257 --comment' "$BROKEN_GH")"
# 第 7 周: 2 つ目の安全網はコメント内の << を heredoc 開始とみなさない・混在終端語は除去しない
# （精密判定と 1 つ目の安全網を無効化し、2 つ目の安全網だけで検証）
BROKEN_ONLY2="$TMP/guard_only2.py"
sed 's/_gh_coarse_count(_shell_code(raw, keep_quoted=False)) != n_targets/False/' "$BROKEN_GH" > "$BROKEN_ONLY2"
grep -q '(False$' "$BROKEN_ONLY2"
ck "FG-N1 注入が一致している"           0   "$?"
ck "FG-N2 コメント内 <<Z の次行 merge"   ASK "$(CROSS_VALUE=true runj $'echo x # <<Z\ngh pr merge 257\nZ' "$BROKEN_ONLY2")"
# 第 8 周: 安全網は gh の表記揺れ（g\h・\gh・"gh"・g''h）も数える（精密判定を無効化して検証）
ck "FG-N5 g\\h pr merge"                 ASK "$(CROSS_VALUE=true runj 'g\h pr merge 257' "$BROKEN_GH")"
ck "FG-N6 \\gh co"                        ASK "$(CROSS_VALUE=true runj '\gh co 257' "$BROKEN_GH")"
ck "FG-N7 g''h pr checkout"              ASK "$(CROSS_VALUE=true runj "g''h pr checkout 257" "$BROKEN_GH")"
ck "FG-N3 混在終端語 <<A\"B\" の AB 後"   ASK "$(CROSS_VALUE=true runj $'cat <<A"B"\nAB\ngh pr merge 257\nA' "$BROKEN_ONLY2")"

# 精密判定と安全網の両方を無効化すると素通しになる（FG-A の ASK が安全網によるものであることの裏取り）
BROKEN_BOTH="$TMP/guard_noboth.py"
sed 's/_safety_net_mismatch(raw, len(targets))/False/' "$BROKEN_GH" > "$BROKEN_BOTH"
grep -q 'if False:' "$BROKEN_BOTH"
ck "FG-F 注入が一致している"            0   "$?"
ck "FG-G 両層無効化で素通し"            0   "$(CROSS_VALUE=true runj 'gh pr merge 257' "$BROKEN_BOTH")"

# 2 つ目の安全網（_safety_text）だけを無効化すると、共有前処理を取り違える入力が黙って通る（G193 の ASK の担い手の裏取り）
BROKEN_NET2="$TMP/guard_nonet2.py"
sed 's/or _gh_coarse_count(_safety_text(raw)) > n_targets)/)/' "$GUARD" > "$BROKEN_NET2"
grep -q '_safety_text(raw)) > n_targets' "$BROKEN_NET2"
ck "FG-H 注入が一致している"            1   "$?"
# shellcheck disable=SC2016
ck "FG-I 2 つ目の安全網なしでは素通し"   0   "$(CROSS_VALUE=true runj 'echo "${x:-" #"}" ; gh pr merge 257' "$BROKEN_NET2")"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
