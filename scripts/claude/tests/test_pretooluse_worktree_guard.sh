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

# --- 未カバー経路の no-silent-caps 警告（TC-A22）。固定パスの cd は I179 で判定対象になった（X20）ため、変数越しの cd で見る ---
# shellcheck disable=SC2016  # $WT はガードに渡すコマンド文字列の一部（展開させない）
A22_CODE=$(printf '{"tool_name":"Bash","tool_input":{"command":"cd $WT && echo x > f"}}' \
             | ( cd "$MAIN" && python3 "$GUARD" >/dev/null 2>&1 ); echo $?)
ck "A22 cd経由 未カバー exit0" 0 "$A22_CODE"
# shellcheck disable=SC2016  # 同上
A22_ERR=$(printf '{"tool_name":"Bash","tool_input":{"command":"cd $WT && echo x > f"}}' \
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
# コマンド文字列を JSON に安全に埋め込んで叩く（クォート・改行を含むケース用）
bash_j() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$1" \
             | ( cd "$MAIN" && python3 "${2:-$GUARD}" >/dev/null 2>&1 ); echo $?; }
# --- 敵対的レビュー第2周: docker 本体のオプション・クォート・短縮結合・ラッパー・区切り（DV10〜DV21） ---
ck "DV10 docker --context x compose down -v→block" 2 "$(bash_j 'docker --context x compose down -v')"
ck "DV11 docker -H unix:///s compose down -v→block" 2 "$(bash_j 'docker -H unix:///s compose down -v')"
ck "DV12 クォートした down/-v→block"               2 "$(bash_j 'docker compose "down" "-v"')"
ck "DV13 短縮結合 -vt 5→block"                     2 "$(bash_j 'docker compose down -vt 5')"
ck "DV14 docker --log-level error volume rm→block" 2 "$(bash_j 'docker --log-level error volume rm foo')"
ck "DV15 docker volume remove→block"               2 "$(bash_j 'docker volume remove foo')"
ck "DV16 docker system prune --volumes→block"      2 "$(bash_j 'docker --context x system prune --volumes -f')"
ck "DV17 bash -c の中→block"                       2 "$(bash_j 'bash -c "docker compose -p x down -v"')"
ck "DV18 改行の後→block"                           2 "$(bash_j "$(printf 'echo hi\ndocker compose down -v')")"
ck "DV19 サブシェル・& の後→block"                 2 "$(bash_j 'sleep 1 & ( docker compose down -v )')"
# 文字列の中の記述も止める（develop から続く既知の誤ブロック。安全装置が後退しないことを優先する・DANGER_OK=1 前置か言い換えで解ける）
ck "DV20 コミットメッセージ中の文字列→block（既知の誤ブロック）" 2 "$(bash_j 'git commit -m "docs: docker volume rm の手順"')"
ck "DV21 pytest -k down -v（down はサブコマンドでない）→allow" 0 "$(bash_j 'docker compose exec backend pytest -k down -v')"
ck "DV21b pytest -k \"count down\" -v→allow"                0 "$(bash_j 'docker compose exec backend pytest -k "count down" -v')"
ck "DV22 system prune（--volumes なし）→allow"     0 "$(bash_j 'docker system prune -f')"
ck "DV23 down --volumes=false→block（安全側）"     2 "$(bash_j 'docker compose down --volumes=false')"

# --- fix-loop（敵対的レビュー第3周の後退・ヒアドキュメントの穴）: シェルの書き方に関係なく止まる（DV24〜DV45） ---
while IFS= read -r c; do
  [ -n "$c" ] || continue
  ck "DV-sh ${c}→block" 2 "$(bash_j "$(printf '%b' "$c")")"
done <<'CASES'
true;docker compose down -v
cd /tmp&&docker compose down -v
echo a|docker compose down -v
echo $(docker compose down -v)
echo `docker volume rm v1`
bash -lc 'docker compose down -v'
sh -ec 'docker volume prune -f'
timeout 60 docker compose down -v
nice -n 5 docker compose down -v
sudo -E docker compose down -v
env -i docker compose down -v
env -u X docker compose down -v
stdbuf -oL docker compose down -v
if true; then docker compose down -v; fi
for p in a b; do docker compose -p $p down -v; done
f(){ docker compose down -v; }; f
eval docker compose down -v
sudo docker volume rm v1
sleep 1 & docker compose down -v
docker volume ls -q -f dangling=true | xargs -r docker volume rm
find . -name x -exec docker volume rm {} \;
docker.exe compose down -v
docker compose down -vt5
cat <<EOF && docker compose down -v\nx\nEOF
echo "<<EOF"\ndocker volume rm v1
cat <<<x; docker compose -p x down -v
true <<x && docker volume rm wt-app_postgres_data
cat <<'EOF'\ndocker compose down -v\nEOF
bash -c "$(cat <<'EOF'\ndocker compose down -v\nEOF\n)"
docker compose down \\\n  -v
timeout 120 docker compose down \\\n  --volumes --remove-orphans
true;docker compose down \\\n -v
bash -lc 'docker compose down \\\n  -v'
sudo -E docker compose down \\\n  -v
echo $(docker compose down \\\n -v)
timeout 60 docker \\\n volume rm wt-app_postgres_data
timeout 5 docker system prune -af \\\n --volumes
CASES

# --- トークン層でしか捕まらない形（docker 本体のオプション付き）を、前置コマンド・eval・& の後でも止める ---
#     （正規表現の層はこれらを捕まえないので、トークン層の前置き読み飛ばし・eval の再帰・& の区切りが停止要因になる）
ck "DV-tok sudo の後→block"  2 "$(bash_j 'sudo docker --context x compose down -v')"
ck "DV-tok env X=1 の後→block" 2 "$(bash_j 'env X=1 docker --context x compose down -v')"
ck "DV-tok eval の中→block"  2 "$(bash_j 'eval docker --context x compose down -v')"
ck "DV-tok & の後→block"     2 "$(bash_j 'sleep 1 & docker --context x compose down -v')"
ck "DV-tok ( の後→block"     2 "$(bash_j '( docker --context x compose down -v )')"

# --- develop のガードとの比較（後退しないこと）: develop で止まっていた入力は、今のガードでも止まる ---
OLD_GUARD="$TMP/guard_develop.py"
if git -C "$REPO_ROOT" show origin/develop:scripts/claude/hooks/pretooluse_guard.py > "$OLD_GUARD" 2>/dev/null; then
  while IFS= read -r c; do
    [ -n "$c" ] || continue
    cmd="$(printf '%b' "$c")"
    old_rc="$(bash_j "$cmd" "$OLD_GUARD")"
    if [ "$old_rc" = "2" ]; then
      ck "NOREG ${c}（develop=2）" 2 "$(bash_j "$cmd")"
    fi
  done <<'CASES'
docker compose down -v
docker compose down --volumes
true;docker compose down -v
timeout 60 docker compose down -v
if true; then docker compose down -v; fi
cat <<EOF && docker compose down -v\nx\nEOF
echo "<<EOF"\ndocker compose down -v
bash -lc 'docker compose down -v'
docker compose down -v; echo ok
x=1 docker compose down -v
timeout 120 docker compose down \\\n  -v
true;docker compose down \\\n -v
env -i docker compose down \\\n -v
CASES
else
  echo "SKIP NOREG（origin/develop を取得できない環境）"
fi
# FG-DV1: 判定関数を常に None にした複製では DV2・DV10 が素通りする（ブロックの停止要因が判定関数である証明）
BROKEN_DV="$TMP/guard_nowipe.py"
sed 's/^def _docker_volume_wipe(cmd: str):/def _docker_volume_wipe(cmd: str):\n    return None  # FG-DV1/' \
  "$GUARD" > "$BROKEN_DV"
if grep -q 'return None  # FG-DV1' "$BROKEN_DV"; then
  ck "FG-DV1 判定除去複製でDV2=allow"  0 "$(bash_j 'docker compose -p wt-harness down -v' "$BROKEN_DV")"
  ck "FG-DV1 判定除去複製でDV10=allow" 0 "$(bash_j 'docker --context x compose down -v' "$BROKEN_DV")"
else
  ck "FG-DV1 注入できた" 0 1
fi
# FG-DV2: (1) 正規表現の層を外した複製では、トークン判定だけでは捕まらない DV-sh の形（true;docker）が素通りする
#        （和集合の (1) が停止要因である証明＝置き換えると後退することの再現）
BROKEN_RX="$TMP/guard_norx.py"
sed 's/^    for rx, reason in _DOCKER_WIPE_RES:$/    for rx, reason in ():/' "$GUARD" > "$BROKEN_RX"
if grep -q '^    for rx, reason in ():$' "$BROKEN_RX"; then
  ck "FG-DV2 正規表現の層の除去複製で true;docker=allow" 0 "$(bash_j 'true;docker compose down -v' "$BROKEN_RX")"
else
  ck "FG-DV2 注入できた" 0 1
fi
# FG-DV3: (2) トークン判定の層を外した複製では、DV10（docker --context x compose）が素通りする（(2) が停止要因である証明）
BROKEN_TK="$TMP/guard_notok.py"
sed 's/^    return _docker_volume_wipe_tokens(cmd)$/    return None  # FG-DV3/' "$GUARD" > "$BROKEN_TK"
if grep -q 'return None  # FG-DV3' "$BROKEN_TK"; then
  ck "FG-DV3 トークン層の除去複製で DV10=allow" 0 "$(bash_j 'docker --context x compose down -v' "$BROKEN_TK")"
else
  ck "FG-DV3 注入できた" 0 1
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

# --- 別ワークツリーの削除・破棄と相対パス書込（I179 計画変更記録 5・TC-X1〜X38・FG-X1/X2・DO1/DO2） ---
printf '.claude/worktrees/\n' > "$MAIN/.gitignore"
SCR="$TMP/scratch-outside"; mkdir -p "$SCR"
# cwd を指定し、JSON を正しくエスケープしてフックに渡す
bj_in() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$2" \
            | ( cd "$1" && python3 "${3:-$GUARD}" >/dev/null 2>&1 ); echo $?; }
R="r""m"   # このテストを Claude の Bash で組み立て直して試すときに、試す側のコマンドが rm 規則に当たらないように
while IFS='|' read -r tc where c; do
  [ -n "$tc" ] || continue
  case "$where" in main) d="$MAIN" ;; nest) d="$NEST" ;; esac
  c="${c//@R@/$R}"; c="${c//@MAIN@/$MAIN}"; c="${c//@OTHER@/$OTHER}"
  ck "$tc ${c}→block" 2 "$(bj_in "$d" "$c")"
done <<'CASES'
X1|main|@R@ -r .claude/worktrees/nest
X2|main|@R@ -fr @MAIN@/.claude/worktrees/nest/x.py
X3|main|@R@ -r -f .claude/worktrees/nest
X4|main|cd .claude/worktrees/nest && @R@ x.py
X5|main|@R@ -r .claude
X5b|main|@R@ -r .claude/worktrees/*
X6|nest|@R@ -r @OTHER@/src
X7|nest|@R@ -r ../nest2
X8|main|find .claude/worktrees/nest -name '*.py' -delete
X9|main|find .claude/worktrees/nest -name x -exec @R@ {} +
X10|main|git -C .claude/worktrees/nest checkout -- .
X11|main|git -C .claude/worktrees/nest reset --hard
X12|main|git -C @MAIN@/.claude/worktrees/nest clean -fd
X13|main|git -C .claude/worktrees/nest stash -u
X14|main|git --work-tree=.claude/worktrees/nest restore .
X15|main|git clean -ffdx
X16|main|git clean -f -f -d
X17|main|git worktree remove --force .claude/worktrees/nest
X18|main|git worktree remove -f @OTHER@
X19|main|echo x > .claude/worktrees/nest/f
X20|main|cd .claude/worktrees/nest && echo x > f
X22|main|DANGER_OK=1 @R@ -r .claude/worktrees/nest
X23|main|true;@R@ -r .claude/worktrees/nest
X24|main|sudo -E @R@ -r .claude/worktrees/nest
X25|main|timeout 60 git -C .claude/worktrees/nest reset --hard
X26|main|mv .claude/worktrees/nest /tmp/x
X27|main|cd .claude/worktrees && git -C nest reset --hard
X36|main|git worktree remove .claude/worktrees/nest
X42|main|echo a#b; @R@ -r .claude/worktrees/nest
X43|main|git log --format=%h#x; git -C .claude/worktrees/nest checkout -- .
X44|main|echo $'\''; @R@ -r .claude/worktrees/nest
X45|main|git worktree remove -ff .claude/worktrees/nest
X46|main|pushd .claude/worktrees/nest && git checkout -- .
X47|main|env -C .claude/worktrees/nest git checkout -- .
X48|main|GIT_WORK_TREE=.claude/worktrees/nest git checkout -- .
X49|main|@R@ -r .claude/worktrees/*
X50|main|@R@ -r .*
X52|main|tee .claude/worktrees/nest/f < /dev/null
X53|main|cp a.txt .claude/worktrees/nest/a.txt
X54|main|cp -t .claude/worktrees/nest a.txt
X55|main|sed -i s/a/b/ .claude/worktrees/nest/f
X56|main|git clean --force --force -d
X57|main|git clean -f --force
X60|main|@R@ -r tmp_*
X61|main|mv *.md docs/
X70|main|DANGER_OK=1 @R@ -rf .[^.]*
X71|main|@R@ -r .claude/worktrees/[^.]*
X72|main|@R@ -r .claude/worktrees/[[:alpha:]]*
X73|main|@R@ -r .claude/worktree[^z]
X74|main|@R@ -r .claude/worktrees/{nest,zz}
X75|main|@R@ -r {.claude,zz}
X76|main|@R@ -r .claude/worktree{s,}
X77|main|mv .claude/{worktrees,old}
X78|main|@R@ .claude/worktrees/{nest,zz}/f.txt
X79|main|shopt -s dotglob; @R@ -r *
X80|main|GLOBIGNORE=x; @R@ -r *
X81|main|@R@ -r ~+/.claude
X82|main|(cd /tmp && ls) && git -C .claude/worktrees/nest reset --hard
X83|main|(cd /tmp) ; @R@ -r .claude/worktrees/nest
X84|main|timeout -s KILL 60 @R@ -r .claude/worktrees/nest
X85|main|timeout --signal KILL 5 @R@ -r .claude/worktrees/nest
X86|main|exec -a foo @R@ -r .claude/worktrees/nest
X87|main|sudo -D .claude/worktrees @R@ -r nest
X88|main|env -C.claude/worktrees @R@ -r nest
X89|main|sudo -u git @R@ -r .claude/worktrees/nest
X90|main|pushd .claude/worktrees/nest && pushd /tmp && popd && git checkout -- .
X91|main|cd .claude/worktrees/nest && cd /tmp && cd - && git checkout -- .
X92|main|GIT_DIR=.claude/worktrees/nest/.git git checkout -- .
X94|main|{ cd .claude/worktrees/nest; @R@ -r src; }
X95|main|if true; then cd .claude/worktrees/nest; @R@ -r src; fi
X96|main|X=1 cd .claude/worktrees/nest; @R@ -r src
X97|main|command cd .claude/worktrees/nest; @R@ -r src
X98|main|time cd .claude/worktrees/nest; @R@ -r src
X99|main|cp f .claude/worktrees/n*
X100|main|cp -t .claude/worktrees/n* f
X101|main|env -u cd -C .claude/worktrees @R@ -r nest
X102|main|cd .claude/worktrees && cd /tmp && @R@ -r ~-/nest
X103|main|env cd /tmp; @R@ -r .claude/worktrees/nest
X104|main|sudo cd /tmp && @R@ -r .claude/worktrees/nest
X105|main|sudo mv .claude/worktrees/nest /tmp/x
X106|main|timeout 60 find .claude/worktrees/nest -delete
X107|main|sudo sed -i s/a/b/ .claude/worktrees/nest/f
X108|main|sudo tee .claude/worktrees/nest/f < /dev/null
X109|main|sudo cp a .claude/worktrees/nest/f
X110|main|@R@ -r .claude/worktree?
X111|main|env --chdir=.claude/worktrees @R@ -r nest
X112|main|sed -i -e 's/a/b/' .claude/worktrees/nest/f
X116|main|sed -i -es/a/b/ .claude/worktrees/nest/f
X117|main|sed -i -e's/.*//' .claude/worktrees/nest/f
X118|main|sed -i -f/tmp/s.sed .claude/worktrees/nest/f
X119|main|sed -i --expression=s/a/b/ .claude/worktrees/nest/f
X120|main|cd /tmp & @R@ -r .claude/worktrees/nest
X121|main|mv -t /tmp/x .claude/worktrees/nest
X122|main|mv --target-directory=/tmp/x .claude/worktrees/nest
X123|main|builtin cd .claude/worktrees/nest; @R@ -r src
X124|main|time -p cd .claude/worktrees/nest; @R@ -r src
X125|main|nohup @R@ -r .claude/worktrees/nest
X126|main|nice -n 5 @R@ -r .claude/worktrees/nest
X127|main|stdbuf -oL @R@ -r .claude/worktrees/nest
X128|main|ionice -c3 git -C .claude/worktrees/nest reset --hard
X129|main|doas @R@ -r .claude/worktrees/nest
X130|main|cd .claude/worktrees/nest && cd /tmp && (cd /var) ; cd - && @R@ -r src
X131|main|GIT_WORK_TREE=.claude/worktrees/nest nice git checkout -- .
X132|main|time xargs @R@ -r .claude/worktrees/nest
X133|main|cp f .claude/worktrees/nes?
X134|main|cp -t .claude/worktrees/nes[t] f
X135|main|cp f .claude/worktrees/{zz,nest}
X137|main|git --work-tree .claude/worktrees/nest checkout -- .
X138|main|f(){ cd worktrees/nest && git checkout -- .; }; cd .claude && f
X139|main|cd ~+/.claude/worktrees/nest; @R@ -r src
X140|main|git -C ~+/.claude/worktrees/nest checkout -- .
X141|main|cp --target-directory .claude/worktrees/nest/src f
X142|main|cp -t.claude/worktrees/nest/src f
X143|main|cp -vt .claude/worktrees/nest/src f
X144|main|cp --target=.claude/worktrees/nest/src f
X145|main|mv --target .claude/worktrees/nest f
X69|main|(cd .claude/worktrees/nest && git status) ; git commit -m x
X113|main|sed -i '2{s/foo/bar/}' f
X114|main|sed -i -e '1,3{s/a/b/;s/c/d/}' backend/x.py
X66|main|cd .claude/worktrees/nest && cd - && git checkout -- .
X146|nest|cd backend && cd .. && git add -A
X147|nest|cd backend && cd ../frontend && @R@ -r build
X148|nest|cd docs && cd .. && echo a > x.txt
X149|nest|cd backend && pytest; cd -; cd ../nest2 && git checkout -- .
X150|nest|pushd backend && pytest && popd && cd ../nest2 && git checkout -- .
X151|nest|git -C backend log -1 && cd ../nest2 && @R@ -r src
X152|main|git -C backend status && cd ../other-wt && git checkout -- .
X153|main|cd frontend && npm run build && cd ~- && cd ../other-wt && git checkout -- .
X154|main|cd /tmp && cd /var && @R@ -r .claude/worktrees/nest
CASES
# ヒアドキュメント本文にアポストロフィ（閉じていないクォート）があっても、後ろのコマンドを見落とさない
ck "X51 本文に don't のヒアドキュメントの後→block" 2 \
  "$(bj_in "$MAIN" "$(printf "cat > /tmp/x <<'X'\ndon't\nX\n%s -r .claude/worktrees/nest" "$R")")"
ck "X136 パイプの cd の後→block" 2 "$(bj_in "$MAIN" "cd /tmp | :; $R -r .claude/worktrees/nest")"
# 改行で区切った後のコマンドも止まる
ck "X28 改行の後→block" 2 "$(bj_in "$MAIN" "$(printf 'echo a\n%s -r .claude/worktrees/nest' "$R")")"
# X21: /mnt/<ドライブ>/ 配下（drvfs）では大文字小文字だけ違うパスも別ワークツリーと判定する（実リポジトリの登録で判定のみ）
REAL_ROOTS="$(git -C "$REPO_ROOT" worktree list --porcelain | sed -n 's/^worktree //p')"
REAL_OTHER="$(printf '%s\n' "$REAL_ROOTS" | grep -vxF "$REPO_ROOT" | grep -m1 '^/mnt/[a-z]/' || true)"
if [ -n "$REAL_OTHER" ]; then
  UP="$(printf '%s' "$REAL_OTHER" | tr '[:lower:]' '[:upper:]' | sed 's#^/MNT/\(.\)/#/mnt/\L\1/#')"
  ck "X21 大文字小文字違いの別wt edit→block" 2 \
    "$(printf '{"tool_name":"Edit","tool_input":{"file_path":"%s/zz_probe.txt"}}' "$UP" \
       | ( cd "$REPO_ROOT" && python3 "$GUARD" >/dev/null 2>&1 ); echo $?)"
  # 削除の判定でも大文字小文字をそろえる（中に別ワークツリーを含む親フォルダの大文字表記。判定のみで実行はしない）
  ck "X21b 大文字小文字違いの親フォルダの削除→block" 2 "$(bj_in "$REPO_ROOT" "$R -r $(dirname "$UP")")"
else
  echo "SKIP X21（/mnt/<ドライブ>/ 配下の別ワークツリーが無い環境）"
fi
# 通す側
while IFS='|' read -r tc where c; do
  [ -n "$tc" ] || continue
  case "$where" in main) d="$MAIN" ;; nest) d="$NEST" ;; esac
  c="${c//@R@/$R}"; c="${c//@NEST@/$NEST}"; c="${c//@SCR@/$SCR}"
  ck "$tc ${c}→allow" 0 "$(bj_in "$d" "$c")"
done <<'CASES'
X30|nest|@R@ -r build
X31|nest|@R@ @NEST@/tmp.txt
X32|main|@R@ -r @SCR@/x
X33|main|git -C .claude/worktrees/nest status
X33b|main|git -C .claude/worktrees/nest log -1
X33c|main|git -C .claude/worktrees/nest diff
X33d|main|git -C .claude/worktrees/nest stash list
X34|main|git clean -fdx
X35|nest|git clean -ffdx
X37|main|find .claude/worktrees/nest -name '*.py'
X38|main|echo x > ok.txt
X39|main|git commit -m "docs: @R@ -r .claude/worktrees/nest の手順"
X40|main|git checkout -b feature/x
X41|main|echo x 2>&1 >/dev/null
X62|main|@R@ -f tmp_*.log
X67|main|@R@ *.log
X68|main|(cd /tmp && ls) && git status
X93|nest|@R@ -r tmp_*
X155|nest|cd backend && cd .. && pytest
X156|nest|cd backend && @R@ -r build
X157|main|cd a && cd b && @R@ -r @SCR@/x
X115|main|{ cd /tmp; @R@ -r x; }
X63|main|# @R@ -r .claude/worktrees/nest
X64|main|git worktree add ../wt-extra -b feature/y
X65|main|git worktree prune
CASES
# FG-X1: 新しい判定を常に空にした複製では、止める側の代表が素通りする（停止要因の証明）
BROKEN_X="$TMP/guard_nodestroy.py"
sed 's/^def _bash_destroy_targets(cmd: str) -> list:/def _bash_destroy_targets(cmd: str) -> list:\n    return []  # FG-X1/' \
  "$GUARD" > "$BROKEN_X"
if grep -q 'return \[\]  # FG-X1' "$BROKEN_X"; then
  for c in "$R -r .claude/worktrees/nest" "find .claude/worktrees/nest -delete" \
           "git -C .claude/worktrees/nest checkout -- ." "git clean -ffdx" \
           "git worktree remove --force .claude/worktrees/nest"; do
    ck "FG-X1 判定除去複製で ${c}=allow" 0 "$(bj_in "$MAIN" "$c" "$BROKEN_X")"
  done
else
  ck "FG-X1 注入できた" 0 1
fi
# FG-X2: 相対パスの絶対化を外した複製では、相対パスの削除・書込が素通りする
BROKEN_REL="$TMP/guard_norel.py"
sed 's/^def _abs_in(cwd, p):/def _abs_in(cwd, p):\n    if p and not p.startswith("\/"): return None  # FG-X2/' "$GUARD" > "$BROKEN_REL"
if grep -q '# FG-X2' "$BROKEN_REL"; then
  ck "FG-X2 絶対化除去複製で X1=allow"  0 "$(bj_in "$MAIN" "$R -r .claude/worktrees/nest" "$BROKEN_REL")"
  ck "FG-X2 絶対化除去複製で X19=allow" 0 "$(bj_in "$MAIN" "echo x > .claude/worktrees/nest/f" "$BROKEN_REL")"
else
  ck "FG-X2 注入できた" 0 1
fi
# FG-X3: 中かっこを展開文字から外した複製では、中かっこの削除が素通りする（展開を含むパスの粗い判定が停止要因である証明）
BROKEN_BR="$TMP/guard_nobrace.py"
sed 's/m = re.search(r"\[\*?\\\[{\]", p)/m = re.search(r"[*?\\[]", p)  # FG-X3/' "$GUARD" > "$BROKEN_BR"
if grep -q '# FG-X3' "$BROKEN_BR"; then
  ck "FG-X3 中かっこ除去複製で X74=allow" 0 "$(bj_in "$MAIN" "$R -r .claude/worktrees/{nest,zz}" "$BROKEN_BR")"
else
  ck "FG-X3 注入できた" 0 1
fi
# FG-X5: 「判定不能」の検出を外した（常に連鎖なしとして判定する）複製では、移動の連鎖で別ワークツリーへ入る X27・X138 が素通りする
BROKEN_MV="$TMP/guard_noundecidable.py"
sed 's/^    bases = {cwd0} if cwd0 else set()$/    undecidable = False  # FG-X5\n&/' "$GUARD" > "$BROKEN_MV"
if grep -q '# FG-X5' "$BROKEN_MV"; then
  ck "FG-X5 判定不能の検出除去複製で X27=allow" 0 "$(bj_in "$MAIN" "cd .claude/worktrees && git -C nest reset --hard" "$BROKEN_MV")"
  ck "FG-X5 判定不能の検出除去複製で X138=allow" 0 \
    "$(bj_in "$MAIN" "f(){ cd worktrees/nest && git checkout -- .; }; cd .claude && f" "$BROKEN_MV")"
else
  ck "FG-X5 注入できた" 0 1
fi
# X158/X159: 移動先が多くても処理量は線形（第 10 周 C1: 候補の爆発でメモリを使い切った）。10 秒・メモリ 1GB で打ち切る
MANY=""; for i in $(seq 1 12); do MANY="${MANY}cd d$i; "; done
bj_lim() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$1" \
             | ( cd "$MAIN" && ulimit -v 1048576 && timeout 10 python3 "$GUARD" >/dev/null 2>&1 ); echo $?; }
ck "X158 cd 12 個＋相対の削除→block（10 秒以内）" 2 "$(bj_lim "${MANY}$R -r x")"
ck "X159 cd 12 個＋読み取りだけ→allow（10 秒以内）" 0 "$(bj_lim "${MANY}ls")"
# X160: 判定中の例外は止める側に倒す（exit 2 以外の異常終了はフックが止めず、後ろの危険操作の検査まで素通りになる）
BROKEN_EX="$TMP/guard_raise.py"
sed 's/^def _bash_destroy_targets(cmd: str) -> list:/&\n    raise MemoryError  # X160/' "$GUARD" > "$BROKEN_EX"
if grep -q '# X160' "$BROKEN_EX"; then
  ck "X160 判定中の例外→block" 2 "$(bj_in "$MAIN" "ls" "$BROKEN_EX")"
else
  ck "X160 注入できた" 0 1
fi
# X161: 判定不能で止めたときは、分けて実行する案内を出す
X161_ERR=$(python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' \
             "cd backend && cd .. && git add -A" | ( cd "$NEST" && python3 "$GUARD" 2>&1 >/dev/null ) || true)
if printf '%s' "$X161_ERR" | grep -q "Bash 呼び出しを分ける"; then
  ck "X161 判定不能の案内" 0 0; else ck "X161 判定不能の案内" 0 1; fi
# DO1/DO2: 区切りの後ろの DANGER_OK=1 では解除しない
ck "DO1 echo DANGER_OK=1; docker compose down -v→block" 2 "$(bj_in "$MAIN" 'echo DANGER_OK=1; docker compose down -v')"
ck "DO2 echo hi && DANGER_OK=1 git reset --hard→block"   2 "$(bj_in "$MAIN" 'echo hi && DANGER_OK=1 git reset --hard')"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
