#!/usr/bin/env bash
# I498（plan_I498.md §4-5・auto_test TC-01）: CI 待ちの上限の既定が code-review.sh と pr-base-sync.sh で同じか。
#   既定の正は code-review.sh の CI_WAIT_TIMEOUT_DEFAULT の 1 か所。pr-base-sync.sh は code-review.sh を関数だけ読み込んで同じ値を使う。
#   書かれた数字ではなく、動かしたときに待ちの行に出る上限（`0s / <N>s`）を比べる（別の形で数字を戻しても捕まえる）。
#   T1: code-review.sh の wait_ci の既定 T2: pr-base-sync.sh final の既定と上限超えの扱い T3: T1 と T2 が同じ
#   T4: 上限の環境変数の数字の既定が無い T5: PBS_CI_TIMEOUT の上書きが効く T6: code-review.sh を読めないと待ち始めずに止まる
#   FG: 写し（一時のフォルダ）を壊すと、対応する項目が不合格になること（本物のファイルは書き換えない）
# gh・sleep はスタブ（実 GitHub に依存しない）。対象のフォルダは I498_SCRIPTS_DIR（既定 scripts/claude）
# 実行: bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i498_ci_wait_timeout.sh（PyYAML が要る）
# shellcheck disable=SC2016  # 単一引用符内の $ は、別の bash に渡す文字どおりのコード・sed の照合用
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
SCRIPTS_DIR="${I498_SCRIPTS_DIR:-scripts/claude}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
yn() { if "$@" >/dev/null 2>&1; then echo yes; else echo no; fi; }

# ---------------- スタブ ----------------
STUB="$TMP/bin"; mkdir -p "$STUB"
cat > "$STUB/gh" <<'EOF'
#!/usr/bin/env bash
case "$*" in
  *isCrossRepository*) echo false ;;
  *baseRefName*)       echo develop ;;
  *mergeStateStatus*)  echo BLOCKED ;;
  *headRefOid*)        echo "$GH_HEAD" ;;
  "pr checks"*--json*) printf 'pending\tA\n' ;;
  "pr checks"*)        printf 'A\tpending\t0\t\n' ;;
  *) exit 0 ;;
esac
EOF
printf '#!/usr/bin/env bash\nexit 0\n' > "$STUB/sleep"
chmod +x "$STUB/gh" "$STUB/sleep"
WF="$TMP/wf.yml"; printf 'jobs:\n  A:\n    runs-on: x\n' > "$WF"
HEAD_SHA="$(git rev-parse HEAD)"

# 待ちの行の上限 <N> を取り出す（`0s / <N>s` の行。無ければ空）
limit_of() { sed -n 's#.* 0s / \([0-9][0-9]*\)s$#\1#p' "$1" | head -1; }

# cr_run <フォルダ> <出力>: code-review.sh を関数だけ読み込み、CI_WAIT_TIMEOUT なしで wait_ci を 1 回呼ぶ
cr_run() {
  timeout 30 env -u CI_WAIT_TIMEOUT PATH="$STUB:$PATH" GH_HEAD="$HEAD_SHA" CI_WORKFLOWS="$WF" CI_POLL_INTERVAL=100000 \
    REVIEW_LIB_SOURCE_ONLY=1 bash -c '. "$1/code-review.sh"; set +e; wait_ci 1; echo "RC=$?"' _ "$1" > "$2" 2>&1
}
# pbs_run <フォルダ> <出力> [<環境変数の代入>…]: pr-base-sync.sh final 219（PBS_CI_TIMEOUT は渡したときだけ）
pbs_run() {
  local d="$1" out="$2"; shift 2
  timeout 30 env -u PBS_CI_TIMEOUT PATH="$STUB:$PATH" PBS_CI_INTERVAL=100000 PBS_RETRY_INTERVAL=0 "$@" \
    bash "$d/pr-base-sync.sh" final 219 > "$out" 2>&1
  echo "RC=$?" >> "$out"
}

# t1 <フォルダ>: wait_ci が時間切れ（戻り値 3・CI_WAIT: TIMEOUT）で、上限が正の整数
t1() { local o="$TMP/t1.$RANDOM"; cr_run "$1" "$o"; grep -qx 'RC=3' "$o" && grep -qx 'CI_WAIT: TIMEOUT' "$o" && [[ "$(limit_of "$o")" =~ ^[1-9][0-9]*$ ]]; }
# t2 <フォルダ>: final が exit 1・待ちの行と同じ上限の「⚠️ CI タイムアウト（<N>秒）」
t2() { local o="$TMP/t2.$RANDOM" n; pbs_run "$1" "$o"; n=$(limit_of "$o")
       grep -qx 'RC=1' "$o" && [[ "$n" =~ ^[1-9][0-9]*$ ]] && grep -qF "⚠️ CI タイムアウト（${n}秒）" "$o"; }
# t3 <フォルダ>: 2 つの上限が同じ（どちらも取り出せる）
t3() { local a="$TMP/t3a.$RANDOM" b="$TMP/t3b.$RANDOM" na nb; cr_run "$1" "$a"; pbs_run "$1" "$b"
       na=$(limit_of "$a"); nb=$(limit_of "$b"); [ -n "$na" ] && [ "$na" = "$nb" ]; }
# t4 <フォルダ>: 上限の環境変数に数字の既定が書かれていない
t4() { ! grep -qE '(PBS_CI_TIMEOUT|CI_WAIT_TIMEOUT):-[0-9]' "$1/code-review.sh" "$1/pr-base-sync.sh"; }
# t5 <フォルダ>: PBS_CI_TIMEOUT=7 が効く
t5() { local o="$TMP/t5.$RANDOM"; pbs_run "$1" "$o" PBS_CI_TIMEOUT=7
       grep -qx 'RC=1' "$o" && [ "$(limit_of "$o")" = 7 ] && grep -qF '⚠️ CI タイムアウト（7秒）' "$o"; }
# t6 <フォルダ>: そのフォルダの pr-base-sync.sh だけを code-review.sh の無い所に写して流すと、待ち始めずに exit 1
t6() { local d="$TMP/t6.$RANDOM" o; mkdir -p "$d"; cp "$1/pr-base-sync.sh" "$d/"; o="$d/out"; pbs_run "$d" "$o"
       grep -qx 'RC=1' "$o" && grep -qF 'CI 待ちの上限の既定を code-review.sh から読めません' "$o" && ! grep -qF 'pending...' "$o"; }

ck "T1 code-review.sh の wait_ci の既定で時間切れになり、上限が出る" yes "$(yn t1 "$SCRIPTS_DIR")"
ck "T2 pr-base-sync.sh final の上限超えは exit 1・⚠️ CI タイムアウト（<N>秒）" yes "$(yn t2 "$SCRIPTS_DIR")"
ck "T3 2 つのスクリプトの既定の上限が同じ" yes "$(yn t3 "$SCRIPTS_DIR")"
ck "T4 上限の環境変数に数字の既定が無い" yes "$(yn t4 "$SCRIPTS_DIR")"
ck "T5 PBS_CI_TIMEOUT の上書きが効く" yes "$(yn t5 "$SCRIPTS_DIR")"
ck "T6 code-review.sh を読めないと待ち始めずに止まる" yes "$(yn t6 "$SCRIPTS_DIR")"

# ---------------- FG: 写しを壊すと落ちる ----------------
# copy_dir <名前>: 2 つのスクリプトの写しのフォルダを作って出す
copy_dir() { local d="$TMP/$1"; mkdir -p "$d"; cp "$SCRIPTS_DIR/code-review.sh" "$SCRIPTS_DIR/pr-base-sync.sh" "$d/"; echo "$d"; }
# broke <ファイル> <sed の式>: 書き換え、変わっていなければ失敗（壊し方が効いていない FG を合格にしない）
broke() { cp "$1" "$1.orig"; sed -i "$2" "$1"; ! cmp -s "$1" "$1.orig"; }

D=$(copy_dir fg1)
ck "FG1 の壊し方が効く（pr-base-sync.sh に :-600 を戻す）" yes "$(yn broke "$D/pr-base-sync.sh" 's/^CI_TIMEOUT="\${PBS_CI_TIMEOUT:-}"$/CI_TIMEOUT="${PBS_CI_TIMEOUT:-600}"/')"
ck "FG1 T3 が不合格" no "$(yn t3 "$D")"
ck "FG1 T4 が不合格" no "$(yn t4 "$D")"

D=$(copy_dir fg2)
ck "FG2 の壊し方が効く（wait_ci に :-1200 を戻す）" yes "$(yn broke "$D/code-review.sh" 's/timeout_s="\${CI_WAIT_TIMEOUT:-\$CI_WAIT_TIMEOUT_DEFAULT}"/timeout_s="${CI_WAIT_TIMEOUT:-1200}"/')"
ck "FG2 T3 が不合格" no "$(yn t3 "$D")"
ck "FG2 T4 が不合格" no "$(yn t4 "$D")"

D=$(copy_dir fg3)
ck "FG3 の壊し方が効く（読んだ値の確かめを消す）" yes "$(yn broke "$D/pr-base-sync.sh" '/\[\[ "\$CI_TIMEOUT" =~/,+1d')"
ck "FG3 T6 が不合格" no "$(yn t6 "$D")"

echo "---"
if [ "$fail" -ne 0 ]; then echo "RESULT: NG (fail ${fail} / pass ${pass})"; exit 1; fi
echo "RESULT: OK (pass ${pass})"
