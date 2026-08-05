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
        GH_LOG="${GH_LOG:-/dev/null}" python3 "${2:-$GUARD}" 2>/dev/null)
  code=$?
  _decide "$out" "$code"
}
# $1=tool_name / $2=tool_input JSON / $3=guard（省略時は実体）
runm() {
  local out code
  out=$(mjson "$1" "$2" | env PATH="$STUB:$PATH" \
        CROSS_VALUE="${CROSS_VALUE-false}" GH_FAIL_CROSS="${GH_FAIL_CROSS:-0}" \
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
ck "G11 gh pr merge 識別子なし"        2   "$(CROSS_VALUE=true runj 'gh pr merge')"
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
ck "G21 DANGER_OK エスケープ"          0   "$(CROSS_VALUE=true runj 'DANGER_OK=1 gh pr merge 257')"
ck "G22 rm -rf 同居は hard-block 優先"  2   "$(CROSS_VALUE=true runj 'gh pr merge 257 && rm -rf x')"
ck "G23 mcp pull_number なし=ask"      ASK "$(CROSS_VALUE=true runm mcp__github__merge_pull_request "$MCP_NONUM")"

# ===== 想定外値・空応答は ask 降格 =====
ck "G25 空応答=ask 降格"               ASK "$(CROSS_VALUE='' runj 'gh pr merge 257')"
ck "G26 想定外値=ask 降格"             ASK "$(CROSS_VALUE=hoge runj 'gh pr merge 257')"

# ===== ask 文言に head リポジトリ名が含まれる =====
ASK_OUT=$(json 'gh pr ready 257' | env PATH="$STUB:$PATH" CROSS_VALUE=true \
          python3 "$GUARD" 2>/dev/null)
printf '%s' "$ASK_OUT" | grep -q "Dodothereal/study-app-multitenant"
ck "G27 ask 文言に head リポジトリ名"  0 "$?"

# ===== false-green 注入（判定関数ごとに独立に裏取り） =====
BROKEN_GH="$TMP/guard_nogh.py"
sed 's/^def _gh_pr_target(cmd: str):$/&\n    return None/' "$GUARD" > "$BROKEN_GH"
ck "FG-A 判定無効化で素通し"           0   "$(CROSS_VALUE=true runj 'gh pr merge 257' "$BROKEN_GH")"
ck "FG-B 実体は block"                 2   "$(CROSS_VALUE=true runj 'gh pr merge 257')"

BROKEN_CROSS="$TMP/guard_nocross.py"
sed 's/^def _pr_is_cross_repo(ident, repo=None):$/&\n    return False, None/' "$GUARD" > "$BROKEN_CROSS"
ck "FG-C 常に自前扱いで素通し"          0   "$(CROSS_VALUE=true runj 'gh pr merge 257' "$BROKEN_CROSS")"

BROKEN_MCP="$TMP/guard_nomcp.py"
sed 's/^def _mcp_pr_target(tool_name: str, tool_input: dict):$/&\n    return None/' "$GUARD" > "$BROKEN_MCP"
ck "FG-D MCP 判定無効化で素通し"        0   "$(CROSS_VALUE=true runm mcp__github__merge_pull_request "$MCP_PR" "$BROKEN_MCP")"
ck "FG-E 実体は block（MCP）"           2   "$(CROSS_VALUE=true runm mcp__github__merge_pull_request "$MCP_PR")"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
