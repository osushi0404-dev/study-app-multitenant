#!/usr/bin/env bash
# I097: docker compose config で publish ホストポートの変数化・同時 up 非衝突を検証する。
# 実行: bash scripts/claude/tests/test_compose_ports.sh
#
# docker compose config は Docker デーモン不要（パース/展開のみ）。docker 未使用環境では SKIP（exit 0）。
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
COMPOSE="$REPO_ROOT/docker-compose.yml"

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "SKIP: docker compose 未使用環境のためスキップ（決定論ロジックは test_wt_port_offset.sh が担保）"
  exit 0
fi

ALL_TMP=()
cleanup() { local f; for f in "${ALL_TMP[@]:-}"; do [ -n "$f" ] && rm -f "$f"; done; }
trap cleanup EXIT

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
ckline()   { if printf '%s\n' "$2" | grep -qx "$3"; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
             else printf 'FAIL %s (missing line: %s)\n' "$1" "$3"; fail=$((fail+1)); fi; }
cknoline() { if printf '%s\n' "$2" | grep -qx "$3"; then printf 'FAIL %s (unexpected line: %s)\n' "$1" "$3"; fail=$((fail+1));
             else printf 'PASS %s\n' "$1"; pass=$((pass+1)); fi; }

mkenv() { local f; f="$(mktemp)"; ALL_TMP+=("$f"); printf '%s' "$1" > "$f"; echo "$f"; }
# publish されるホストポートをレンダリング（--env-file で補間を決定論化）
render_ports() { docker compose -f "$COMPOSE" --env-file "$1" config 2>/dev/null \
                   | sed -n 's/.*published: "\([0-9]\{1,\}\)".*/\1/p' | sort -u; }

EMPTY="$(mkenv '')"
OFF10="$(mkenv 'DB_PORT=5442
REDIS_PORT=6389
BACKEND_PORT=8010
FRONTEND_PORT=3010
')"
OFF20="$(mkenv 'DB_PORT=5452
REDIS_PORT=6399
BACKEND_PORT=8020
FRONTEND_PORT=3020
')"

# --- TC-D1: 変数未設定 → 既定ポート（後方互換・AC1） ---
D1="$(render_ports "$EMPTY")"
ckline "D1 db 5432"       "$D1" 5432
ckline "D1 redis 6379"    "$D1" 6379
ckline "D1 backend 8000"  "$D1" 8000
ckline "D1 frontend 3000" "$D1" 3000

# --- TC-D2: offset=10 → publish がオフセットされる ---
D2="$(render_ports "$OFF10")"
ckline   "D2 backend 8010"    "$D2" 8010
ckline   "D2 frontend 3010"   "$D2" 3010
ckline   "D2 db 5442"         "$D2" 5442
ckline   "D2 redis 6389"      "$D2" 6389
cknoline "D2 旧 8000 不在"    "$D2" 8000

# --- TC-D3: offset=10 と offset=20 の publish が非衝突（AC3・同時 up 可能） ---
D3DUP="$(printf '%s\n%s\n' "$D2" "$(render_ports "$OFF20")" | sort | uniq -d)"
ck "D3 offset10/20 重複なし" "" "$D3DUP"
# 自己検証（false-green 防止）: 同一 offset 同士なら重複が検出される
D3SAME="$(printf '%s\n%s\n' "$D2" "$D2" | sort | uniq -d)"
if [ -n "$D3SAME" ]; then printf 'PASS %s\n' "D3 自己検証(同一offsetは重複検出)"; pass=$((pass+1));
else printf 'FAIL %s\n' "D3 自己検証(同一offsetは重複検出が空)"; fail=$((fail+1)); fi

# --- TC-D4: nginx（80/443）は既定 up の publish に現れない（対象外） ---
cknoline "D4 no 80 published"  "$D1" 80
cknoline "D4 no 443 published" "$D1" 443

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
