#!/usr/bin/env bash
# I211: ハーネスのテストの道具の版を正のファイル（.python-version・uv.lock・pyproject.toml の required-version）で
# ぴったり確かめること・run-all.sh が uv の環境で流し直すこと・実物の版の正の形を確かめる。
# 項目は docs/tests/open/I211_auto_test.md の TC-01 の表（V・X・K）。否定の項目には写しで失敗注入（FG）を付ける。
# 実行: bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i211_version_pin.sh
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)" || exit 1
cd "$REPO_ROOT" || exit 1
CHECK="scripts/claude/tests/check-tools.sh"
PROJ="scripts/claude/tests"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=[%s] got=[%s]\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
has() { if grep -qF -- "$2" <<< "$1"; then echo yes; else echo no; fi; }
# 写しのフォルダ（$1=名前）に一覧（残りの引数=行）を作り、一覧のパスを返す
mkdir_list() { local d="$TMP/$1"; shift; mkdir -p "$d"; printf '%s\n' "$@" > "$d/required-tools.txt"; echo "$d/required-tools.txt"; }

# ---------- V: lock の行のぴったりの確かめ ----------
PY="$(python3 --version 2>&1)"; PY="${PY#Python }"
L="$(mkdir_list v1 'python3 | python3 --version | lock | 入れ方の例')"
printf '%s\n' "$PY" > "$TMP/v1/.python-version"
OUT="$(bash "$CHECK" "$L" 2>&1)"; rc=$?
ck "V1 python3 が .python-version と一致すれば OK" "0 yes" "$rc $(has "$OUT" "OK: python3 $PY")"

printf '0.0.1\n' > "$TMP/v1/.python-version"
OUT="$(bash "$CHECK" "$L" 2>&1)"; rc=$?
ck "FG-V2 正より新しい python3 は exit 1" "1 yes yes" "$rc $(has "$OUT" '⛔ 版が違う道具: python3') $(has "$OUT" '入れ方: 入れ方の例')"

printf '99.0.0\n' > "$TMP/v1/.python-version"
OUT="$(bash "$CHECK" "$L" 2>&1)"; rc=$?
ck "FG-V3 正より古い python3 は exit 1" "1 yes" "$rc $(has "$OUT" '⛔ 版が違う道具: python3')"

rm -f "$TMP/v1/.python-version"
OUT="$(bash "$CHECK" "$L" 2>&1)"; rc=$?
ck "FG-V7 .python-version が無ければ exit 2" "2 yes" "$rc $(has "$OUT" '⛔ 版の正が読めません')"

L="$(mkdir_list v4 'fake-tool | echo fake-tool 1.2.3 | lock | x')"
mklock() { printf '%s\n' 'version = 1' '' '[[package]]' 'name = "other"' 'version = "1.2.3"' '' \
  '[[package]]' "name = \"$1\"" "version = \"$2\"" '' '[[package]]' 'name = "zzz"' 'version = "9.9.9"' > "$TMP/v4/uv.lock"; }
mklock fake-tool 1.2.3
OUT="$(bash "$CHECK" "$L" 2>&1)"; rc=$?
ck "V4 道具が uv.lock の版と一致すれば OK" "0 yes" "$rc $(has "$OUT" 'OK: fake-tool 1.2.3')"

mklock fake-tool 1.2.4
OUT="$(bash "$CHECK" "$L" 2>&1)"; rc=$?
ck "FG-V5 uv.lock の版と違えば exit 1（ほかの package の版に当てない）" "1 yes" "$rc $(has "$OUT" '⛔ 版が違う道具: fake-tool')"

mklock another 1.2.3
OUT="$(bash "$CHECK" "$L" 2>&1)"; rc=$?
ck "FG-V6 uv.lock に名前が無ければ exit 2" "2 yes" "$rc $(has "$OUT" '⛔ 版の正が読めません')"

L="$(mkdir_list v8 'python3 | python3 --version | 3.11 | x')"
OUT="$(bash "$CHECK" "$L" 2>&1)"; rc=$?
ck "FG-V8 版の列が下限の形（3.11）なら exit 2" "2 yes" "$rc $(has "$OUT" '⛔ 一覧の行の形が違います')"

L="$(mkdir_list v9 'quiet | false | - | x')"
OUT="$(bash "$CHECK" "$L" 2>&1)"; rc=$?
BLANK=no; grep -qE '^    $' <<< "$OUT" && BLANK=yes
ck "V9 出力が空で通らない道具は字下げの空行を出さない" "1 yes no" "$rc $(has "$OUT" '⛔ 足りない道具: quiet') $BLANK"

L="$(mkdir_list v10 'loud | echo boom; false | - | x')"
OUT="$(bash "$CHECK" "$L" 2>&1)"; rc=$?
BOOM=no; grep -qxF '    boom' <<< "$OUT" && BOOM=yes
ck "FG-V10 出力がある通らない道具は字下げで出す" "1 yes" "$rc $BOOM"

# ---------- X: run-all.sh の流し直しと引数 ----------
R="$TMP/repo"
mkdir -p "$R/$PROJ" "$R/t" "$TMP/fakeuv"
git -C "$R" init -q
cp "$PROJ/run-all.sh" "$CHECK" "$R/$PROJ/"   # pyproject.toml は置かない（無くても流し直す＝版の正を迂回しない）
printf '%s\n' 'bash | bash --version | - | -' > "$R/$PROJ/required-tools.txt"
printf '#!/usr/bin/env bash\ntouch "%s"\n' "$TMP/mark" > "$R/t/test_mark.sh"
printf '#!/usr/bin/env bash\nprintf "%%s\\n" "$*" > "%s"\nexit 0\n' "$TMP/uvargs" > "$TMP/fakeuv/uv"
chmod +x "$TMP/fakeuv/uv"
RROOT="$(cd "$R" && pwd -P)"
# 一時のリポジトリで run-all.sh を流して終了コードを返す（$@=env に渡す変数・XARGS=run-all.sh の引数）
run_x() { rm -f "$TMP/mark" "$TMP/uvargs"
  # shellcheck disable=SC2086  # XARGS は空か 1 語（空のとき引数を渡さない）
  ( cd "$R" && env -u VIRTUAL_ENV -u HARNESS_UV_REEXEC "$@" bash "$PROJ/run-all.sh" ${XARGS:-} ) > "$TMP/xout" 2>&1; echo $?; }
rc="$(run_x PATH="$TMP/fakeuv:$PATH" TEST_DIR=t)"
MARK=no; [ -e "$TMP/mark" ] && MARK=yes
ck "X1 uv の環境の外なら uv run --locked で流し直す（外側では流さない）" \
   "0 no run --locked --project $PROJ bash $PROJ/run-all.sh" "$rc $MARK $(cat "$TMP/uvargs" 2>/dev/null)"

XARGS=t/test_mark.sh run_x PATH="$TMP/fakeuv:$PATH" >/dev/null
ck "X2 引数をそのまま uv run に渡す" "run --locked --project $PROJ bash $PROJ/run-all.sh t/test_mark.sh" "$(cat "$TMP/uvargs" 2>/dev/null)"

# PATH から uv のあるフォルダを除く
NOUV=""; IFS=: read -ra DIRS <<< "$PATH"
for d in "${DIRS[@]}"; do [ -x "$d/uv" ] || NOUV="${NOUV:+$NOUV:}$d"; done
rc="$(run_x PATH="$NOUV" TEST_DIR=t)"
MARK=no; [ -e "$TMP/mark" ] && MARK=yes
ck "FG-X3 uv が無ければテストを流さず exit 1" "1 no yes yes" \
   "$rc $MARK $(has "$(cat "$TMP/xout")" '⛔ uv がありません') $(has "$(cat "$TMP/xout")" 'テストは流していません')"

rc="$(run_x PATH="$TMP/fakeuv:$PATH" TEST_DIR=t HARNESS_UV_REEXEC=1)"
CALLED=no; [ -e "$TMP/uvargs" ] && CALLED=yes
ck "FG-X4 流し直した後も uv の環境に入れなければ exit 1（もう流し直さない）" "1 no yes" \
   "$rc $CALLED $(has "$(cat "$TMP/xout")" '⛔ uv で流し直しても uv の環境に入れませんでした')"

rc="$(run_x PATH="$TMP/fakeuv:$PATH" TEST_DIR=t VIRTUAL_ENV="$RROOT/$PROJ/.venv")"
CALLED=no; [ -e "$TMP/uvargs" ] && CALLED=yes
MARK=no; [ -e "$TMP/mark" ] && MARK=yes
ck "X5 uv の環境の中では流し直さずに流す" "0 no yes" "$rc $CALLED $MARK"

INVENV="VIRTUAL_ENV=$RROOT/$PROJ/.venv"
printf '#!/usr/bin/env bash\ntouch "%s"\n' "$TMP/mark_a" > "$R/t/test_a.sh"
printf '#!/usr/bin/env bash\ntouch "%s"\n' "$TMP/mark_b" > "$R/t/test_b.sh"
rc="$(XARGS=t/test_a.sh run_x TEST_DIR=t "$INVENV")"
A=no; B=no; [ -e "$TMP/mark_a" ] && A=yes; [ -e "$TMP/mark_b" ] && B=yes
ck "X6 引数のテストだけを流す" "0 yes no yes" "$rc $A $B $(has "$(cat "$TMP/xout")" 'run-all: pass=1 fail=0')"

rc="$(XARGS=t/test_nothing.sh run_x TEST_DIR=t "$INVENV")"
ck "FG-X7 引数のテストが無ければ exit 1" "1 yes" "$rc $(has "$(cat "$TMP/xout")" '⛔')"

# ---------- K: 実物の版の正 ----------
RV="$(grep -E '^required-version = ' "$PROJ/pyproject.toml")"
RP="$(grep -E '^requires-python = ' "$PROJ/pyproject.toml")"
PV="$(cat "$PROJ/.python-version")"
K1=no
# python のマイナー版は .python-version と requires-python で同じ（版を上げるときに片方だけ変えると止まる）
if [[ "$RV" =~ ^required-version\ =\ \"==[0-9]+\.[0-9]+\.[0-9]+\"$ ]] && [[ "$PV" =~ ^([0-9]+\.[0-9]+)\.[0-9]+$ ]] \
   && [ "$RP" = "requires-python = \"==${BASH_REMATCH[1]}.*\"" ]; then K1=yes; fi
ck "K1 uv の版・python の版がぴったりの形で、python のマイナー版が揃っている" yes "$K1"

# --offline: lock の食い違いは手元のキャッシュで分かる（ネットワークに頼らない）
OUT="$(uv lock --check --offline --project "$PROJ" 2>&1)"; rc=$?
ck "K2 pyproject.toml と uv.lock が合っている" 0 "$rc"
[ "$rc" -eq 0 ] || printf '%s\n' "$OUT"

mkdir -p "$TMP/k2"
cp "$PROJ/pyproject.toml" "$PROJ/uv.lock" "$PROJ/.python-version" "$TMP/k2/"
sed -i 's/"PyYAML>=6.0", //' "$TMP/k2/pyproject.toml"
OUT="$(uv lock --check --offline --project "$TMP/k2" 2>&1)"; rc=$?
ck "FG-K2 pyproject.toml と uv.lock がずれれば不合格" "yes yes" \
   "$([ "$rc" -ne 0 ] && echo yes || echo no) $(has "$OUT" 'update')"

K3=yes
for f in uv.lock pyproject.toml .python-version; do git ls-files --error-unmatch "$PROJ/$f" >/dev/null 2>&1 || K3="no($f)"; done
git check-ignore -q "$PROJ/.venv" || K3="no(.venv)"
ck "K3 版の正は git で追跡・.venv は除外" yes "$K3"

LOCKROWS="$(awk -F' [|] ' '$3=="lock"{print $1}' "$PROJ/required-tools.txt" | tr '\n' ' ')"
UVROW=no; grep -qE '^uv [|] ' "$PROJ/required-tools.txt" && UVROW=yes
ck "K4 実物の一覧で python3・PyYAML・pre-commit が lock・uv の行がある" "python3 PyYAML pre-commit  yes" "$LOCKROWS $UVROW"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
