#!/usr/bin/env bash
# I468: lint-frontend.sh（pre-commit の ESLint のフック）の分岐と終了コードの返し方を決定論で確かめる。
# 実行: bash scripts/claude/tests/test_i468_lint_frontend.sh
# 一時の git リポジトリの中から本物のラッパーを呼ぶ。docker・npm は偽物（引数と作業フォルダを記録し、決めた終了コードで終わる）を PATH の先頭に置く。
# 本物の Docker は使わない。ケースは docs/tests/open/I468_auto_test.md の TC-01〜TC-04 と FG-01〜FG-04 に対応する。
# 失敗の注入は本物の写しを壊して同じケースを当てる（本物は書き換えない）。
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
REAL="$REPO_ROOT/scripts/claude/lint-frontend.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0
ok() { pass=$((pass + 1)); echo "  ✅ $1"; }
ng() { fail=$((fail + 1)); echo "  ❌ $1"; }

# 偽の docker・npm（引数を 1 行で $STUB_LOG に書く。lint を流す呼び出しは STUB_RC で終わる）
STUB="$TMP/stub"
mkdir -p "$STUB"
cat > "$STUB/docker" <<'S'
#!/usr/bin/env bash
echo "docker $* @ $(pwd -P)" >> "$STUB_LOG"
case "$1 ${2:-}" in
  "version "*) exit "${STUB_DAEMON_RC:-0}";;
  "compose ps") printf '%s' "${STUB_PS_OUT:-}"; exit 0;;
esac
exit "${STUB_RC:-0}"
S
cat > "$STUB/npm" <<'S'
#!/usr/bin/env bash
echo "npm $* @ $(pwd -P)" >> "$STUB_LOG"
exit "${STUB_RC:-0}"
S
chmod +x "$STUB/docker" "$STUB/npm"

# docker の無い PATH（要るコマンドだけを入れる）
NODOCKER="$TMP/nodocker"
mkdir -p "$NODOCKER"
for c in bash git grep env; do
  p="$(command -v "$c")" && ln -s "$p" "$NODOCKER/$c"
done
ln -s "$STUB/npm" "$NODOCKER/npm"

# 一時のリポジトリ（$1=ホストの eslint を置くか yes/no）
n=0
make_repo() {
  n=$((n + 1))
  local d="$TMP/repo-$n"
  mkdir -p "$d/frontend/src"
  git -C "$d" init -q
  if [ "$1" = yes ]; then
    mkdir -p "$d/frontend/node_modules/.bin"
    printf '#!/bin/sh\nexit 0\n' > "$d/frontend/node_modules/.bin/eslint"
    chmod +x "$d/frontend/node_modules/.bin/eslint"
  fi
  REPO="$d"
}

# $1=ラッパー $2=PATH の種類（stub か nodocker）。リポジトリは $REPO。RC・LOG・ERR を設定する
run_case() {
  local w="$1" path
  if [ "$2" = nodocker ]; then path="$NODOCKER"; else path="$STUB:$PATH"; fi
  n=$((n + 1))
  LOG="$TMP/log-$n"; ERR="$LOG.err"; : > "$LOG"
  (cd "$REPO" && STUB_LOG="$LOG" PATH="$path" "$BASH" "$w" >/dev/null 2>"$ERR")
  RC=$?
}
# lint を流した呼び出し（docker compose exec|run・npm）だけを、作業フォルダつきで並べる
lint_calls() { grep -E '^docker compose (exec|run) |^npm ' "$LOG"; }

EXEC_LINE="docker compose exec -T frontend npm run lint"
RUN_LINE="docker compose run --rm --no-deps -T --build --entrypoint npm frontend run lint"

# 1 本のラッパーに TC-01〜TC-04 を当てる（$1=ラッパー $2=結果を表示するか yes/no）。不合格が 1 つでもあれば 1
check_wrapper() {
  local w="$1" show="$2" bad=0 rc out ps mode root
  say() {
    if [ "$1" = ok ]; then [ "$show" = yes ] && ok "$2"; else bad=1; [ "$show" = yes ] && ng "$2"; fi
    return 0
  }

  # $1=ラベル $2=ホストの eslint yes/no $3=期待する lint の呼び出し（「@ <リポジトリからの相対>」の前まで）$4=作業フォルダ（相対）
  # 残りの環境変数（STUB_*）は呼び出し元で付ける。偽の lint の終了コード 0・1 のどちらでも、呼び出しが 1 回だけで終了コードが同じこと
  expect_lint() {
    local label="$1" eslint="$2" want="$3" sub="$4" rc root
    for rc in 0 1; do
      make_repo "$eslint"; root="$(cd "$REPO" && pwd -P)"
      STUB_RC=$rc run_case "$w" stub
      out="$(lint_calls)"
      if [ "$RC" -eq "$rc" ] && [ "$out" = "$want @ $root$sub" ]; then say ok "$label STUB_RC=$rc → exit $RC"
      else say ng "$label STUB_RC=$rc: exit=$RC calls=[$out]"; fi
    done
  }

  # TC-01: 起動中
  STUB_PS_OUT=$'backend\nfrontend\n' expect_lint "TC-01 起動中 → exec" no "$EXEC_LINE" ""
  # TC-02: 起動していない（(a) backend だけ (b) 空 (c) frontend を含む別の名前）
  for ps in $'backend\n' '' $'frontend-old\n'; do
    STUB_PS_OUT="$ps" expect_lint "TC-02 ps=[${ps%$'\n'}] → 使い捨て" no "$RUN_LINE" ""
  done
  # TC-03: Docker が止まっている・ホストの eslint あり
  STUB_DAEMON_RC=1 expect_lint "TC-03 ホスト" yes "npm run lint" "/frontend"

  # TC-04: どこでも流せない（(a) Docker が止まっている (b) docker が無い）。どちらもホストの eslint なし
  for mode in stopped absent; do
    make_repo no
    if [ "$mode" = stopped ]; then STUB_DAEMON_RC=1 run_case "$w" stub
    else run_case "$w" nodocker; fi
    out="$(lint_calls)"
    if [ "$RC" -eq 1 ] && [ -z "$out" ] && grep -q 'ESLint を流せません' "$ERR" && grep -q 'Docker' "$ERR" \
       && grep -qF 'frontend/node_modules/.bin/eslint' "$ERR"; then say ok "TC-04 $mode → exit 1・理由と対処・lint を呼ばない"
    else say ng "TC-04 $mode: exit=$RC calls=[$out] err=[$(tr '\n' ' ' < "$ERR")]"; fi
  done
  return "$bad"
}

echo "== 本物のラッパー"
check_wrapper "$REAL" yes

# 失敗の注入: 本物の写しを壊して当て、不合格が出ることを確かめる
echo "== 失敗の注入（写しを壊すと不合格になる）"
fg() {  # $1=名前 $2=置き換え前 $3=置き換え後
  local copy="$TMP/fg-$1.sh" src
  src="$(<"$REAL")"
  if [[ "$src" != *"$2"* ]]; then ng "$1: 置き換え前の文字列が本体に無い（写しを作れない）"; return; fi
  printf '%s\n' "${src/"$2"/"$3"}" > "$copy"
  if check_wrapper "$copy" no; then ng "$1: 壊した写しでも全部合格した（false-green）"; else ok "$1: 壊した写しは不合格"; fi
}
fg FG-01 "exec $EXEC_LINE" "$EXEC_LINE || true; exit 0"
fg FG-02a "grep -qx frontend" "grep -q frontend"
fg FG-02b "exec $RUN_LINE" "$RUN_LINE || true; exit 0"
fg FG-03 "cd frontend && exec npm run lint" "cd frontend && npm run lint || true; exit 0"
fg FG-04 "exit 1  # 流せない" "exit 0  # 流せない"

# TC-05: 本物の pre-commit と git で、フックの設定（.pre-commit-config.yaml の eslint のフック）→ ラッパー → 終了コードがつながり、
# lint の失敗でコミットが止まる・成功でコミットされる（docker だけ偽物。本物の Docker での確かめは manual_test No.1・No.2）
echo "== TC-05 本物の pre-commit と git"
# $1=フックの設定の取り出し方（real か broken）。一時のリポジトリを作り、pre-commit のフックを入れる
make_hook_repo() {
  n=$((n + 1))
  REPO="$TMP/hook-$n"
  mkdir -p "$REPO/frontend/src" "$REPO/scripts/claude"
  git -C "$REPO" init -q
  cp "$REAL" "$REPO/scripts/claude/lint-frontend.sh"
  python3 - "$REPO_ROOT/.pre-commit-config.yaml" "$REPO/.pre-commit-config.yaml" "$1" <<'P'
import sys, yaml
src, dst, mode = sys.argv[1:]
cfg = yaml.safe_load(open(src))
hooks = [h for r in cfg["repos"] if r["repo"] == "local" for h in r["hooks"] if h["id"] == "eslint"]
assert len(hooks) == 1, "eslint のフックが 1 つではない"
if mode == "broken":
    hooks[0]["entry"] = "true"
yaml.safe_dump({"repos": [{"repo": "local", "hooks": hooks}]}, open(dst, "w"), allow_unicode=True)
P
  git -C "$REPO" add -A
  git -C "$REPO" -c user.email=t@example.com -c user.name=t commit -qm base --no-verify
  (cd "$REPO" && PRE_COMMIT_HOME="$TMP/pc" pre-commit install >/dev/null) || ng "TC-05: pre-commit install に失敗"
}
# lint の終了コード $1 で frontend/src のファイルをコミットする。RC=コミットの終了コード・MOVED=yes/no（HEAD が進んだか）
commit_with_lint_rc() {
  local before
  before="$(git -C "$REPO" rev-parse HEAD)"
  mkdir -p "$REPO/frontend/src"   # 前の reset --hard で空のフォルダが消えるため
  echo "export const x$n = 1;" > "$REPO/frontend/src/probe$n.ts"
  git -C "$REPO" add -A
  n=$((n + 1)); LOG="$TMP/log-$n"; : > "$LOG"
  (cd "$REPO" && STUB_LOG="$LOG" STUB_RC="$1" STUB_PS_OUT="" PRE_COMMIT_HOME="$TMP/pc" PATH="$STUB:$PATH" \
     git -c user.email=t@example.com -c user.name=t commit -qm probe >/dev/null 2>&1)
  RC=$?
  if [ "$(git -C "$REPO" rev-parse HEAD)" = "$before" ]; then MOVED=no; else MOVED=yes; fi
  git -C "$REPO" reset -q --hard "$before"
}
# $1=設定の取り出し方。lint の失敗でコミットが止まり、成功でコミットされ、どちらも使い捨てのコンテナの呼び出しが 1 回あるか
check_hook() {
  local bad=0 calls
  make_hook_repo "$1"
  commit_with_lint_rc 1; calls="$(lint_calls)"
  [ "$RC" -ne 0 ] && [ "$MOVED" = no ] && [ "$calls" = "$RUN_LINE @ $(cd "$REPO" && pwd -P)" ] || bad=1
  [ "$2" = yes ] && { if [ "$bad" -eq 0 ]; then ok "TC-05 lint 失敗 → コミットが止まる"; else ng "TC-05 lint 失敗: rc=$RC moved=$MOVED calls=[$calls]"; fi; }
  local b2=0
  commit_with_lint_rc 0; calls="$(lint_calls)"
  [ "$RC" -eq 0 ] && [ "$MOVED" = yes ] && [ "$calls" = "$RUN_LINE @ $(cd "$REPO" && pwd -P)" ] || b2=1
  [ "$2" = yes ] && { if [ "$b2" -eq 0 ]; then ok "TC-05 lint 成功 → コミットされる"; else ng "TC-05 lint 成功: rc=$RC moved=$MOVED calls=[$calls]"; fi; }
  [ "$bad" -eq 0 ] && [ "$b2" -eq 0 ]
}
check_hook real yes
# FG-05: フックの entry をラッパーでないもの（true）にした設定では、lint の失敗でもコミットされ不合格になる
if check_hook broken no; then ng "FG-05: entry を true にした設定でも合格した（false-green）"; else ok "FG-05: entry を true にした設定は不合格"; fi

echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
