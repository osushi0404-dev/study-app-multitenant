#!/usr/bin/env bash
# I095: pretooluse_guard.py の worktree 横断書込ブロックを決定論検証する。
# 実行: bash scripts/claude/tests/test_pretooluse_worktree_guard.sh
#
# temp repo（＝現worktreeの代役）に linked worktree を生やし、フックへ stdin JSON を
# 投入して exit code を検証する（実書込はしない＝判定のみ）。0=素通し / 2=ブロック。
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
GUARD="$REPO_ROOT/scripts/claude/hooks/pretooluse_guard.py"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

MAIN="$TMP/main"
mkdir -p "$MAIN"
cd "$MAIN" || exit 1
git init -q
git config user.email t@example.com
git config user.name tester
printf 'x\n' > f.txt
git add f.txt
git commit -qm init
git branch -q other
OTHER="$TMP/other-wt"
git worktree add -q "$OTHER" other

# 兄弟名 decoy: OTHER と接頭辞が同じだが worktree ではない別ディレクトリ
SIBLING="${OTHER}-foo"
mkdir -p "$SIBLING"
# symlink decoy: 現worktree内から別worktreeへ張ったリンク（realpath で解決されるべき）
ln -s "$OTHER" "$MAIN/link_to_other"

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }

# 現worktree(=$MAIN)を cwd にしてフックを叩き exit code を返す
edit()   { printf '{"tool_name":"%s","tool_input":{"file_path":"%s"}}' "$1" "$2" \
             | ( cd "$MAIN" && python3 "$GUARD" >/dev/null 2>&1 ); echo $?; }
nbedit() { printf '{"tool_name":"NotebookEdit","tool_input":{"notebook_path":"%s"}}' "$1" \
             | ( cd "$MAIN" && python3 "$GUARD" >/dev/null 2>&1 ); echo $?; }
bash_c() { printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$1" \
             | ( cd "$MAIN" && python3 "$GUARD" >/dev/null 2>&1 ); echo $?; }

# --- 判定コア（TC-A1〜A5） ---
ck "A1 edit 別wt→block"        2 "$(edit Edit "$OTHER/x.py")"
ck "A2 edit 現wt→allow"        0 "$(edit Edit "$MAIN/x.py")"
ck "A3 edit リポジトリ外→allow" 0 "$(edit Edit "$TMP/outside.txt")"
ck "A4 edit 兄弟名decoy→allow"  0 "$(edit Edit "$SIBLING/x.py")"
ck "A5 edit 相対(現wt)→allow"   0 "$(edit Edit "relative.py")"

# --- 書込ツール網羅（TC-A6〜A10） ---
ck "A6 write 別wt→block"        2 "$(edit Write "$OTHER/x.py")"
ck "A7 multiedit 別wt→block"    2 "$(edit MultiEdit "$OTHER/x.py")"
ck "A8 notebookedit 別wt→block" 2 "$(nbedit "$OTHER/nb.ipynb")"
ck "A9 write 現wt→allow"        0 "$(edit Write "$MAIN/x.py")"
ck "A10 edit symlink→block"     2 "$(edit Edit "$MAIN/link_to_other/x.py")"

# --- Bash 書込経路（TC-A11〜A15・A11b） ---
ck "A11 redirect 別wt→block"       2 "$(bash_c "echo x > $OTHER/f")"
ck "A11b 埋め込みredirect→block"   2 "$(bash_c "echo x>$OTHER/f")"
ck "A12 tee 別wt→block"            2 "$(bash_c "tee $OTHER/f")"
ck "A13 cp dest別wt→block"         2 "$(bash_c "cp a.txt $OTHER/")"
ck "A14 mv dest別wt→block"         2 "$(bash_c "mv a.txt $OTHER/b.txt")"
ck "A15 sed -i 別wt→block"         2 "$(bash_c "sed -i s/x/y/ $OTHER/f")"

# --- 読み取り許可・非書込（TC-A16〜A17） ---
ck "A16 cp src別wt→allow"  0 "$(bash_c "cp $OTHER/src.txt ./dest.txt")"
ck "A17 cat 別wt→allow"    0 "$(bash_c "cat $OTHER/f")"

# --- fail-safe（TC-A18・git不在 cwd → 境界確定不能 → block） ---
NOGIT="$TMP/nogit"; mkdir -p "$NOGIT"
ck "A18 fail-safe(git不在)→block" 2 \
  "$(printf '{"tool_name":"Edit","tool_input":{"file_path":"%s"}}' "$NOGIT/x.py" \
     | ( cd "$NOGIT" && python3 "$GUARD" >/dev/null 2>&1 ); echo $?)"

# --- エスケープ無し（TC-A19・DANGER_OK でも解除されない） ---
ck "A19 DANGER_OK 別wt bash→block" 2 "$(bash_c "DANGER_OK=1 echo x > $OTHER/f")"

# --- 回帰（TC-A20・現wt書込 allow / force push block 維持） ---
ck "A20a 現wt redirect→allow" 0 "$(bash_c "echo x > $MAIN/ok.txt")"
ck "A20b force push→block"    2 "$(bash_c "git push --force origin x")"

# --- 未カバー経路の no-silent-caps 警告（TC-A22） ---
A22_CODE=$(printf '{"tool_name":"Bash","tool_input":{"command":"cd %s && echo x > f"}}' "$OTHER" \
             | ( cd "$MAIN" && python3 "$GUARD" >/dev/null 2>&1 ); echo $?)
ck "A22 cd経由 未カバー exit0" 0 "$A22_CODE"
A22_ERR=$(printf '{"tool_name":"Bash","tool_input":{"command":"cd %s && echo x > f"}}' "$OTHER" \
             | ( cd "$MAIN" && python3 "$GUARD" 2>&1 >/dev/null ) || true)
if printf '%s' "$A22_ERR" | grep -q "絶対パス宛先のみ検査"; then
  ck "A22 未カバー警告出力" 0 0; else ck "A22 未カバー警告出力" 0 1; fi

# --- 未カバー警告の誤発火防止（TC-A23・cp read は cd/変数なし → 警告なし・Medium 対応） ---
A23_ERR=$(printf '{"tool_name":"Bash","tool_input":{"command":"cp %s/src.txt ./dest.txt"}}' "$OTHER" \
             | ( cd "$MAIN" && python3 "$GUARD" 2>&1 >/dev/null ) || true)
if printf '%s' "$A23_ERR" | grep -q "絶対パス宛先のみ検査"; then
  ck "A23 read-cp 警告誤発火なし" 0 1; else ck "A23 read-cp 警告誤発火なし" 0 0; fi

# --- FALSEGREEN 注入（TC-A21・_cross_worktree を常に False 化） ---
BROKEN="$TMP/guard_broken.py"
sed 's/^def _cross_worktree(path):/def _cross_worktree(path):\n    return False  # FALSEGREEN/' \
  "$GUARD" > "$BROKEN"
ck "A21 falsegreen複製=allow" 0 \
  "$(printf '{"tool_name":"Edit","tool_input":{"file_path":"%s"}}' "$OTHER/x.py" \
     | ( cd "$MAIN" && python3 "$BROKEN" >/dev/null 2>&1 ); echo $?)"
ck "A21 falsegreen実体=block" 2 "$(edit Edit "$OTHER/x.py")"

# --- Docker のデータ削除（I179 TC-DV1〜DV8・worktree.md §4 の取り残しの片付け手順の二重ガード） ---
ck "DV1 compose down -v→block"                    2 "$(bash_c "docker compose down -v")"
ck "DV2 compose -p <名前> down -v→block"          2 "$(bash_c "docker compose -p wt-harness down -v")"
ck "DV3 --project-name down --volumes→block"     2 "$(bash_c "docker compose --project-name wt-harness down --volumes")"
ck "DV4 docker-compose -f x.yml down -v→block"    2 "$(bash_c "docker-compose -f x.yml down -v")"
ck "DV5 docker volume rm→block"                  2 "$(bash_c "docker volume rm wt-harness_postgres_data")"
ck "DV6 docker volume prune→block"               2 "$(bash_c "docker volume prune -f")"
ck "DV7 compose -p <名前> down（-v なし）→allow"   0 "$(bash_c "docker compose -p wt-harness down")"
ck "DV8 DANGER_OK=1 compose -p down -v→allow"    0 "$(bash_c "DANGER_OK=1 docker compose -p wt-harness down -v")"
ck "DV9 docker volume ls→allow"                  0 "$(bash_c "docker volume ls -f dangling=true")"
# FG-DV1: 旧パターン（compose の直後に down が必要）に戻した複製では DV2 が素通りする
BROKEN_DV="$TMP/guard_olddown.py"
python3 - "$GUARD" "$BROKEN_DV" <<'PY'
import sys
src = open(sys.argv[1], encoding="utf-8").read()
new = r"\bdocker(\s+compose|\-compose)\b[^;&|\n]*\sdown\b"
old = r"\bdocker(\s+compose|\-compose)\s+down\b"
open(sys.argv[2], "w", encoding="utf-8").write(src.replace(new, old))
PY
if ! cmp -s "$GUARD" "$BROKEN_DV"; then
  ck "FG-DV1 旧パターン複製でDV2=allow" 0 \
    "$(printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "docker compose -p wt-harness down -v" \
       | ( cd "$MAIN" && python3 "$BROKEN_DV" >/dev/null 2>&1 ); echo $?)"
else
  ck "FG-DV1 注入できた" 0 1
fi

# --- 入れ子ワークツリー（I179 TC-G1〜G7・FG-G1） ---
# 公式 `claude --worktree` の配置（<primary>/.claude/worktrees/<name>）を再現する。
# 入れ子のパスは親 root の配下でもあるため、最も内側の root（最長一致）で所有者を決める必要がある。
cd "$MAIN" || exit 1
git branch -q nest-b
git branch -q nest2-b
NEST="$MAIN/.claude/worktrees/nest"
NEST2="$MAIN/.claude/worktrees/nest2"
git worktree add -q "$NEST" nest-b
git worktree add -q "$NEST2" nest2-b

# cwd を指定してフックを叩き exit code を返す
edit_in() { printf '{"tool_name":"%s","tool_input":{"file_path":"%s"}}' "$2" "$3" \
              | ( cd "$1" && python3 "${4:-$GUARD}" >/dev/null 2>&1 ); echo $?; }
bash_in() { printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$2" \
              | ( cd "$1" && python3 "$GUARD" >/dev/null 2>&1 ); echo $?; }

ck "G1 入れ子→自分 edit→allow"     0 "$(edit_in "$NEST" Edit "$NEST/x.py")"
ck "G2 入れ子→自分 redirect→allow" 0 "$(bash_in "$NEST" "echo x > $NEST/ok.txt")"
ck "G3 入れ子→親 edit→block"       2 "$(edit_in "$NEST" Edit "$MAIN/x.py")"
ck "G4 親→入れ子 edit→block"       2 "$(edit_in "$MAIN" Edit "$NEST/x.py")"
ck "G5 入れ子→兄弟wt edit→block"   2 "$(edit_in "$NEST" Edit "$OTHER/x.py")"
ck "G6 入れ子→別の入れ子 write→block" 2 "$(edit_in "$NEST" Write "$NEST2/x.py")"
G7_ERR=$(printf '{"tool_name":"Write","tool_input":{"file_path":"%s"}}' "$NEST2/x.py" \
           | ( cd "$NEST" && python3 "$GUARD" 2>&1 >/dev/null ) || true)
if printf '%s' "$G7_ERR" | grep -qF "（$(cd "$NEST2" && pwd -P)）"; then
  ck "G7 所有者=入れ子rootを表示" 0 0; else ck "G7 所有者=入れ子rootを表示" 0 1; fi

# FG-G1: _owning_root を「最初に一致した root」（旧ロジック相当）に戻した複製では G1 がブロックされる
BROKEN_G="$TMP/guard_firstmatch.py"
sed 's/^def _owning_root(ap, roots):/def _owning_root(ap, roots):\n    return next((r for r in roots if ap == r or ap.startswith(r + os.sep)), None)  # FIRSTMATCH/' \
  "$GUARD" > "$BROKEN_G"
if grep -q FIRSTMATCH "$BROKEN_G"; then
  ck "FG-G1 旧ロジック複製でG1=block" 2 "$(edit_in "$NEST" Edit "$NEST/x.py" "$BROKEN_G")"
else
  ck "FG-G1 注入できた" 0 1
fi

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
