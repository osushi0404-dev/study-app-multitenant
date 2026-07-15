#!/usr/bin/env bash
# I109 決定論ゲート: scheduled 依存監査の不変条件検証
# - dependency-audit.yml: YAML 構文・cron・ref: develop・最小権限・workflow_dispatch・simulate 分岐
# - 監査コマンドの CI 同一性: ci.yml とのペア検証（ci.yml 側だけ変更されても fail し乖離を検知）
# - dependency-audit-issue.sh: 重複防止分岐を gh スタブ（PATH 差し替え）で検証
# false-green 注入検証（TC-02）用に、検証対象を I109_TEST_WF / I109_TEST_SCRIPT で
# 一時コピーへ差し替え可能（既定は実ファイル。実ファイルは改変しない）。
set -u

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
WF="${I109_TEST_WF:-$REPO_ROOT/.github/workflows/dependency-audit.yml}"
SCRIPT="${I109_TEST_SCRIPT:-$REPO_ROOT/scripts/claude/dependency-audit-issue.sh}"
CI_WF="$REPO_ROOT/.github/workflows/ci.yml"

FAIL=0
ok() { echo "OK: $1"; }
ng() { echo "NG: $1"; FAIL=1; }
# check <説明> <コマンド...>: コマンド成功なら OK・失敗なら NG（stderr は抑止）
check() {
  local desc="$1"
  shift
  if "$@" 2>/dev/null; then
    ok "$desc"
  else
    ng "$desc"
  fi
}

# ---- TC-01: 静的不変条件 ----
if python3 -c "import sys, yaml; yaml.safe_load(open(sys.argv[1]))" "$WF" 2>/dev/null; then
  ok "workflow YAML 構文"
else
  ng "workflow YAML 構文"
fi

check "cron 値（UTC22:00=JST7:00 毎日）" grep -qF "cron: '0 22 * * *'" "$WF"
check "checkout ref: develop（監査対象の固定）" grep -qF "ref: develop" "$WF"
check "permissions: issues: write" grep -qF "issues: write" "$WF"
check "permissions: contents: read（最小権限）" grep -qF "contents: read" "$WF"
check "手動トリガー（workflow_dispatch）" grep -qF "workflow_dispatch" "$WF"
check "テスト用 simulate 分岐の存在" grep -qF "inputs.simulate_failure" "$WF"

# CI 同一性（ペア検証）: 監査コマンドが scheduled 側と PR ゲート側の両方に存在すること
if grep -qF "pip-audit -r requirements.txt" "$WF" 2>/dev/null && grep -qF "pip-audit -r requirements.txt" "$CI_WF" 2>/dev/null; then
  ok "backend 監査コマンドの CI 同一性（ペア検証）"
else
  ng "backend 監査コマンドの CI 同一性（ペア検証）"
fi
if grep -qF -- "--audit-level=critical --omit=dev" "$WF" 2>/dev/null && grep -qF -- "--audit-level=critical --omit=dev" "$CI_WF" 2>/dev/null; then
  ok "frontend 監査コマンドの CI 同一性（ペア検証）"
else
  ng "frontend 監査コマンドの CI 同一性（ペア検証）"
fi

check "起票スクリプト bash 構文" bash -n "$SCRIPT"

# ---- TC-04: runbook / CLAUDE.md 整合 ----
check "runbook 実在" test -f "$REPO_ROOT/docs/runbooks/dependency-audit.md"
check "CLAUDE.md 参照行" grep -qF "docs/runbooks/dependency-audit.md" "$REPO_ROOT/CLAUDE.md"
check "起票 body の runbook 参照（実在パス）" grep -qF "docs/runbooks/dependency-audit.md" "$SCRIPT"

# ---- TC-03: 重複防止ロジック（gh スタブ） ----
STUB_DIR="$(mktemp -d)"
trap 'rm -rf "$STUB_DIR"' EXIT
cat > "$STUB_DIR/gh" <<'STUB'
#!/usr/bin/env bash
echo "$*" >> "$GH_STUB_LOG"
if [ "$1" = "issue" ] && [ "$2" = "list" ]; then
  cat "$GH_STUB_LIST_RESULT"
fi
exit 0
STUB
chmod +x "$STUB_DIR/gh"
echo "dummy audit output" > "$STUB_DIR/audit.txt"

# ケースA: 既存 open イシューなし → create のみ
export GH_STUB_LOG="$STUB_DIR/log_a"
: > "$GH_STUB_LOG"
printf '' > "$STUB_DIR/list_a"
export GH_STUB_LIST_RESULT="$STUB_DIR/list_a"
PATH="$STUB_DIR:$PATH" bash "$SCRIPT" backend "$STUB_DIR/audit.txt" >/dev/null 2>&1
rc_a=$?
if [ "$rc_a" -eq 0 ] && grep -q "^issue create" "$GH_STUB_LOG" && ! grep -q "^issue comment" "$GH_STUB_LOG"; then
  ok "重複防止A: 既存なし → create 1回・comment 0回"
else
  ng "重複防止A: 既存なし → create 1回・comment 0回"
fi

# ケースB: 既存 open イシュー #42 あり → comment のみ
export GH_STUB_LOG="$STUB_DIR/log_b"
: > "$GH_STUB_LOG"
echo "42" > "$STUB_DIR/list_b"
export GH_STUB_LIST_RESULT="$STUB_DIR/list_b"
PATH="$STUB_DIR:$PATH" bash "$SCRIPT" backend "$STUB_DIR/audit.txt" >/dev/null 2>&1
rc_b=$?
if [ "$rc_b" -eq 0 ] && grep -q "^issue comment 42" "$GH_STUB_LOG" && ! grep -q "^issue create" "$GH_STUB_LOG"; then
  ok "重複防止B: 既存あり → comment 1回・create 0回"
else
  ng "重複防止B: 既存あり → comment 1回・create 0回"
fi

# ケースC: KIND 不正 → exit 2（許可リスト検証）
export GH_STUB_LOG="$STUB_DIR/log_c"
: > "$GH_STUB_LOG"
PATH="$STUB_DIR:$PATH" bash "$SCRIPT" badkind "$STUB_DIR/audit.txt" >/dev/null 2>&1
rc_c=$?
if [ "$rc_c" -eq 2 ]; then
  ok "KIND 許可リスト: badkind → exit 2"
else
  ng "KIND 許可リスト: badkind → exit 2（実際: exit $rc_c）"
fi

echo ""
if [ "$FAIL" -ne 0 ]; then
  echo "RESULT: NG"
  exit 1
fi
echo "RESULT: OK"
exit 0
