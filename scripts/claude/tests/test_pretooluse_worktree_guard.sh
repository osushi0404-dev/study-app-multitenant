#!/usr/bin/env bash
# I095: pretooluse_guard.py の worktree 横断書込ブロックを決定論検証する。
# 実行: bash scripts/claude/tests/test_pretooluse_worktree_guard.sh
#
# temp repo（＝現worktreeの代役）に linked worktree を生やし、フックへ stdin JSON を
# 投入して exit code を検証する（実書込はしない＝判定のみ）。0=素通し / 2=ブロック。
set -uo pipefail
# 見張りの「信頼する場所」の起点（I174 0-16）。外から渡された値で一時リポジトリが信頼されなくならないよう消す
unset CLAUDE_PROJECT_DIR
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
# I174 敵対的レビュー再実施 第 2 周: >| を > とパイプに割らない
ck "A11c >| redirect→block"        2 "$(bash_c "echo x >| $OTHER/f")"
ck "A11d 埋め込み>|→block"         2 "$(bash_c "echo x >|$OTHER/f")"
ck "A11e 2>&1 の後の >|→block"     2 "$(bash_c "echo x 2>&1 >| $OTHER/f")"
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
# 文字列・ヒアドキュメント本文の中の記述は実行されないので止めない（I174 の見張りはコマンドを読み解いて判定する・計画変更記録 7）
ck "DV20 コミットメッセージ中の文字列→allow" 0 "$(bash_j 'git commit -m "docs: docker volume rm の手順"')"
ck "DV20b cat のヒアドキュメント本文→allow"  0 "$(bash_j "$(printf "cat <<'EOF'\ndocker compose down -v\nEOF")")"
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
docker compose down -vt5
cat <<EOF && docker compose down -v\nx\nEOF
echo "<<EOF"\ndocker volume rm v1
cat <<<x; docker compose -p x down -v
true <<x && docker volume rm wt-app_postgres_data
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
# FG-DV1〜DV3 は、I179 の Docker 判定（_docker_volume_wipe）を I174 の見張りの判定に一本化したため削除した（計画変更記録 7）
# FG-DV4: I174 の判定から remove（rm の別名）を外した複製では DV15 が素通りする（計画変更記録 7 で足した 1 語が停止要因である証明）
BROKEN_RM="$TMP/guard_noremove.py"
sed 's/args\[0\] in ("rm", "remove", "prune")/args[0] in ("rm", "prune")/' "$GUARD" > "$BROKEN_RM"
if grep -q 'args\[0\] in ("rm", "prune")' "$BROKEN_RM"; then
  ck "FG-DV4 remove 除去複製で DV15=allow" 0 "$(bash_j 'docker volume remove foo' "$BROKEN_RM")"
else
  ck "FG-DV4 注入できた" 0 1
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

# --- git clean -f の承認制（I179 計画変更記録 6・7。別ワークツリーを消す操作の判定は廃止し、GitHub の保護・こまめな commit/push・wt-remove.sh に任せる。
#     入れ子ごと消える git clean -ff を含め、I174 の見張りが git clean -f を f の数によらず止める） ---
printf '.claude/worktrees/\n' > "$MAIN/.gitignore"
# cwd を指定し、JSON を正しくエスケープしてフックに渡す
bj_in() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$2" \
            | ( cd "$1" && python3 "${3:-$GUARD}" >/dev/null 2>&1 ); echo $?; }
ck "GC1 git clean -ffdx→block"               2 "$(bj_in "$MAIN" 'git clean -ffdx')"
ck "GC2 git clean -f -f -d→block"            2 "$(bj_in "$MAIN" 'git clean -f -f -d')"
ck "GC3 git clean --force -f→block"          2 "$(bj_in "$MAIN" 'git clean --force -f')"
ck "GC4 cd /tmp && git clean -ffd→block"     2 "$(bj_in "$MAIN" 'cd /tmp && git clean -ffd')"
ck "GC5 git clean -fdx（f 1 つ）→block"       2 "$(bj_in "$MAIN" 'git clean -fdx')"
ck "GC6 DANGER_OK=1 git clean -ffdx→確認（exit 0）" 0 "$(bj_in "$MAIN" 'DANGER_OK=1 git clean -ffdx')"
ck "GC7 git clean -n -d（試すだけ）→allow"     0 "$(bj_in "$MAIN" 'git clean -n -d')"
# X21: /mnt/<ドライブ>/ 配下（drvfs）では大文字小文字だけ違うパスも別ワークツリーと判定する（実リポジトリの登録で判定のみ）
REAL_ROOTS="$(git -C "$REPO_ROOT" worktree list --porcelain | sed -n 's/^worktree //p')"
REAL_OTHER="$(printf '%s\n' "$REAL_ROOTS" | grep -vxF "$REPO_ROOT" | grep -m1 '^/mnt/[a-z]/' || true)"
if [ -n "$REAL_OTHER" ]; then
  UP="$(printf '%s' "$REAL_OTHER" | tr '[:lower:]' '[:upper:]' | sed 's#^/MNT/\(.\)/#/mnt/\L\1/#')"
  ck "X21 大文字小文字違いの別wt edit→block" 2 \
    "$(printf '{"tool_name":"Edit","tool_input":{"file_path":"%s/zz_probe.txt"}}' "$UP" \
       | ( cd "$REPO_ROOT" && python3 "$GUARD" >/dev/null 2>&1 ); echo $?)"
else
  echo "SKIP X21（/mnt/<ドライブ>/ 配下の別ワークツリーが無い環境）"
fi
# DO1/DO2: 区切りの後ろの DANGER_OK=1 では解除しない
ck "DO1 echo DANGER_OK=1; docker compose down -v→block" 2 "$(bj_in "$MAIN" 'echo DANGER_OK=1; docker compose down -v')"
ck "DO2 echo hi && DANGER_OK=1 git reset --hard→block"   2 "$(bj_in "$MAIN" 'echo hi && DANGER_OK=1 git reset --hard')"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
