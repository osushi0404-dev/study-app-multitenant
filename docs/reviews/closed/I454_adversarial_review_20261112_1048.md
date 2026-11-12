# 敵対的レビュー [I454]（別プロセス・2026-11-12 10:48）

- 見た範囲: origin/develop...15aa499f838275e92c58a38e375cf28606ef579e
- 所要時間: 105 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 1 件は下の表）
- 一覧: docs/plans/open/plan_I454.md の「## 必ず確かめる項目」（5 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 実験で確認 | P1-E1=ran P1-E3=ran  | 確認済み（実験） |
| V2 | 1 | 読んで可 | 実験で確認 | P1-E3=ran  | 確認済み（実験） |
| V3 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 101 秒 | 2 | 0 | $0.9604 | ― | ― | ― |
| 2 | 報告あり | 89 秒 | 1 | 1 | $0.7740 | ― | ― | ― |
| 3 | 報告あり | 21 秒 | 0 | 0 | $0.2599 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; for c in "ps -A e" "ps -ef e" "ps -o pid e" "ps -u root e" "ps -eo pid,comm e" "ps -p 1 e" "ps -C node" "ps o etime" "ps --sort etime" "ps -au e" "ps -ax e" "ps aux e" "ps e" "declare +x" "declare -x FOO=1" "declare -p" "export" "ps -eww e" "env" "docker compose exec -T backend ps -A e" "docker compose exec -T backend ps -ef e" "docker compose exec -T backend pytest --junitxml=/app/r.xml -k x" "docker compose exec -T backend pytest -k delete" "docker compose exec -T backend pytest --basetemp /app/x -k x" "docker compose exec -T backend cp -vt/app/x /tmp/y" "docker compose exec -T backend sed -i -es/a/b/ /app/x" "docker compose exec -T backend install -m644 a /app/x" "docker compose exec -T backend install -d /app/newdir" "docker compose exec -T backend sh -c \"pytest -k x > /app/o.txt\"" "docker compose exec -T backend sh -c \"pytest -k x > /tmp/o.txt\"" "docker compose exec backend grep -rn foo /app/apps > /tmp/out.txt" "docker compose exec -T backend tee /app/x" "docker compose exec -T backend dd of=/app/x if=/dev/zero" "docker compose exec -T backend pytest --cov-report=xml:/app/c.xml -k x" "docker compose exec -T backend python -c \"open(\\\"/app/x\\\",\\\"w\\\").write(\\\"a\\\")\""; do j=$(python3 -c "import json,sys;print(json.dumps({\"tool_name\":\"Bash\",\"tool_input\":{\"command\":sys.argv[1]}}))" "$c"); out=$(printf "%s" "$j" | timeout 60 python3 scripts/claude/hooks/pretooluse_guard.py 2>&1); echo "rc=$? :: $c :: $(printf "%s" "$out" | head -c 90 | tr "\n" " ")"; done'
~~~
出力の先頭:
~~~
is_error=false
rc=0 :: ps -A e :: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permi
rc=0 :: ps -ef e :: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permi
rc=0 :: ps -o pid e :: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permi
rc=0 :: ps -u root e :: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permi
rc=0 :: ps -eo pid,comm e :: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permi
rc=0 :: ps -p 1 e :: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permi
rc=0 :: ps -C node ::
rc=0 :: ps o etime ::
rc=0 :: ps --sort etime ::
rc=0 :: ps -au e ::
rc=0 :: ps -ax e :: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permi
rc=0 :: ps aux e :: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permi
rc=0 :: ps e :: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permi
rc=0 :: declare +x :: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permi
rc=0 :: declare -x FOO=1 ::
rc=0 :: declare -p :: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permi
rc=0 :: export :: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permi
rc=0 :: ps -eww e :: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permi
rc=0 :: env :: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permi
rc=0 :: docker compose exec -T backend ps -A e :: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permi
rc=0 :: docker compose exec -T backend ps -ef e :: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permi
rc=0 :: docker compose exec -
~~~

#### P1-E2: 実行した
~~~
bash -c 'ulimit -v 2097152; W=$(git rev-parse --show-toplevel); D=$(dirname "$W"); for c in "install -m644 /tmp/a $D/app-1/x" "ln -s /tmp/a $D/app-1/x" "rsync -a /tmp/a $D/app-1/x" "cp --target-directory=$D/app-1/x /tmp/y" "cp -vt$D/app-1/x /tmp/y" "mv $D/app-1/x /tmp/y" "rsync --remove-source-files $D/app-1/x /tmp/y" "cp $D/app-1/x /tmp/y" "install -d $D/app-1/newdir" "sed -n p $D/app-1/x" "sed -i -nes/a/b/ $D/app-1/x" "sed -i s/a/b/ $D/app-1/x" "tee $D/app-1/x" "echo a > $D/app-1/x"; do j=$(python3 -c "import json,sys;print(json.dumps({\"tool_name\":\"Bash\",\"tool_input\":{\"command\":sys.argv[1]}}))" "$c"); out=$(printf "%s" "$j" | timeout 60 python3 scripts/claude/hooks/pretooluse_guard.py 2>&1); echo "rc=$? :: $c :: $(printf "%s" "$out" | head -c 90 | tr "\n" " ")"; done'
~~~
出力の先頭:
~~~
is_error=false
rc=2 :: install -m644 /tmp/a /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/x :: [guard] 別 worktree（/mnt/c/app/study-app-multitenant/.claude/worktrees/app-1）へのBa
rc=2 :: ln -s /tmp/a /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/x :: [guard] 別 worktree（/mnt/c/app/study-app-multitenant/.claude/worktrees/app-1）へのBa
rc=2 :: rsync -a /tmp/a /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/x :: [guard] 別 worktree（/mnt/c/app/study-app-multitenant/.claude/worktrees/app-1）へのBa
rc=2 :: cp --target-directory=/mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/x /tmp/y :: [guard] 別 worktree（/mnt/c/app/study-app-multitenant/.claude/worktrees/app-1）へのBa
rc=2 :: cp -vt/mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/x /tmp/y :: [guard] 別 worktree（/mnt/c/app/study-app-multitenant/.claude/worktrees/app-1）へのBa
rc=2 :: mv /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/x /tmp/y :: [guard] 別 worktree（/mnt/c/app/study-app-multitenant/.claude/worktrees/app-1）へのBa
rc=0 :: rsync --remove-source-files /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/x /tmp/y ::
rc=0 :: cp /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/x /tmp/y ::
rc=0 :: install -d /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/newdir ::
rc=0 :: sed -n p /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/x ::
rc=2 :: sed -i -nes/a/b/ /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/x :: [guard] 別 worktree（/mnt/c/app/study-app-multitenant/.claude/worktrees/app-1）へのBa
rc=2 :: sed -i s/a/b/ /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/x :: [guard] 別 worktree（/mnt/c/app/study-app-multitenant/.claude/worktrees/app-1）へのBa
rc=2 :: tee /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/x :: [guard] 別 worktree（/mnt/c/app/study-app-multitenant/.claude/worktrees/app-1）へのBa
rc=2 :: echo a > /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/x :: [guard] 別 worktree（/mnt/c/app/study-app-multitenant/.claude/worktrees/a
~~~

#### P1-E3: 実行した
~~~
bash -c 'ulimit -v 2097152; for c in "docker compose exec -T backend ps -A e" "docker compose exec -T backend pytest --junitxml=/app/r.xml -k x" "docker compose exec -T backend pytest -k delete" "docker compose exec -T backend cp -vt/app/x /tmp/y" "docker compose exec -T backend sed -i -es/a/b/ /app/x" "docker compose exec -T backend install -m644 a /app/x" "docker compose exec -T backend install -d /app/newdir" "docker compose exec -T backend sh -c \"pytest -k x > /app/o.txt\"" "docker compose exec -T backend sh -c \"pytest -k x > /tmp/o.txt\"" "docker compose exec backend grep -rn foo /app/apps > /tmp/out.txt" "docker compose exec -T backend pytest --basetemp /app/x -k x" "docker compose exec -T backend pytest --cov-report=xml:/app/c.xml -k x"; do j=$(python3 -c "import json,sys;print(json.dumps({\"tool_name\":\"Bash\",\"tool_input\":{\"command\":sys.argv[1]}}))" "$c"); out=$(printf "%s" "$j" | timeout 60 python3 scripts/claude/hooks/pretooluse_guard.py 2>&1); d=pass; case "$out" in *\"ask\"*) d=ASK;; esac; echo "$d :: $c"; done'
~~~
出力の先頭:
~~~
is_error=false
ASK :: docker compose exec -T backend ps -A e
ASK :: docker compose exec -T backend pytest --junitxml=/app/r.xml -k x
pass :: docker compose exec -T backend pytest -k delete
ASK :: docker compose exec -T backend cp -vt/app/x /tmp/y
ASK :: docker compose exec -T backend sed -i -es/a/b/ /app/x
ASK :: docker compose exec -T backend install -m644 a /app/x
pass :: docker compose exec -T backend install -d /app/newdir
ASK :: docker compose exec -T backend sh -c "pytest -k x > /app/o.txt"
pass :: docker compose exec -T backend sh -c "pytest -k x > /tmp/o.txt"
pass :: docker compose exec backend grep -rn foo /app/apps > /tmp/out.txt
pass :: docker compose exec -T backend pytest --basetemp /app/x -k x
pass :: docker compose exec -T backend pytest --cov-report=xml:/app/c.xml -k x
~~~

### 観点 2

#### P2-E1: 拒否された
~~~
bash -c 'ulimit -v 2097152; timeout 60 bash -c '"'"'
set -u
unset CLAUDE_PROJECT_DIR
REPO_ROOT="$(git rev-parse --show-toplevel)"
GUARD="$REPO_ROOT/scripts/claude/hooks/pretooluse_guard.py"
TMP="$(mktemp -d /tmp/p2e1.XXXXXX)"
MAIN="$TMP/main"; mkdir -p "$MAIN"
git -C "$MAIN" init -q
git -C "$MAIN" -c user.email=t@e.com -c user.name=t commit -q --allow-empty -m init
git -C "$MAIN" branch -q other
W="$TMP/other-wt"
git -C "$MAIN" worktree add -q "$W" other
b() {
  out=$(python3 -c "import json,sys; print(json.dumps({\"tool_name\":\"Bash\",\"tool_input\":{\"command\":sys.argv[1]}}))" "$1" | (cd "$MAIN" && python3 "$GUARD" 2>/dev/null)); code=$?
  if [ "$code" = "0" ] && printf "%s" "$out" | grep -q "\"ask\""; then echo ASK; else echo "$code"; fi
}
for c in \
  "sed -e\"s/print/log/\" $W/x" \
  "sed -n -es/print/log/ $W/x" \
  "cp -vt/tmp/d $W/a $W/b" \
  "cp -t /tmp/d $W/a $W/b" \
  "cp -vt/tmp/d $W/a" \
  "mv -vt/tmp/d $W/a" \
  "rsync --remove-source-files $W/x /tmp/y" \
  "sed -i -le $W/x" \
  "cp -rt /tmp/d $W/a $W/b" ; do
  printf "%s => %s\n" "$c" "$(b "$c")"
done
rm -rf "$TMP"
'"'"''
~~~
出力の先頭:
~~~

~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I454] ── 観点: ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | ロジック回避 | `rsync --remove-source-files <別ワークツリー>/x /tmp/y` は移動元が消えるのに、`mv` と違って停止しない。設計確認メモの範囲（`mv` の移動元だけ）との差で、意図的な回避ではなく普通の書き方で起きる取りこぼし。ただし影響は小さい | pretooluse_guard.py:`_write_targets` | P1-E2: rc=0 |
| Low | ロジック回避 | 通す形の離した形（`pytest --basetemp /app/x`）と接頭辞つきの値（`--cov-report=xml:/app/c.xml`）は、/tmp/ 以外へ書くのに通る。計画の 5-4 で「粗い判定・分岐ごとの除外を残す」と明記済みの既知の範囲。`--basetemp` は指定先を消すが、I444 より前からの挙動で後退ではない | pretooluse_guard.py:`_OPT_PATH_RE`・`_container_risky` | P1-E3: pass |

V1 と V2 では Critical／High の欠陥は見つからなかった。

**V1（環境変数の表示）**
- ホスト（P1-E1）の結果:
  - 確認になった形: `ps -A e`・`ps -ef e`・`ps -o pid e`・`ps -u root e`・`ps -eo pid,comm e`・`ps -p 1 e`・`ps -ax e`・`ps aux e`・`ps e`・`ps -eww e`・`declare +x`・`declare -p`・`export`・`env`。
  - 通った形: `ps -C node`・`ps o etime`・`ps --sort etime`・`declare -x FOO=1`。
- コンテナ（P1-E3）の結果: `ps -A e` は確認になった。
- `ps -au e` が通るのは、procps の読みでは `-u e` が値なので正しい。

**V2（コンテナの /tmp/ 以外への書き込み）**（P1-E3）
- 確認になった形: `pytest --junitxml=/app/r.xml`・`cp -vt/app/x`・`sed -i -es/a/b/ /app/x`・`install -m644 a /app/x`・`sh -c "… > /app/o.txt"`。
- 通った形: `pytest -k delete`・`install -d /app/newdir`・`sh -c "… > /tmp/o.txt"`・ホスト側の `> /tmp/out.txt`。

## 探索した仮説
- `_PS_VALUE_OPT_RE` に、値を取らないフラグの後ろの e を値とみなす穴がないか。
- `_opt_values` のまとめ書き読みで、別ワークツリーの停止やコンテナの書き込みが抜けないか。
- 通す形に書き込みの理由が効いているか。

> ITEM: V1 RESULT=experiment EXP=P1-E1,P1-E3
> ITEM: V2 RESULT=experiment EXP=P1-E3
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I454] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Medium | false-green（対照の不足） | V3 の「読むだけの形は通る」の対照が、`cp $W/x /tmp/y`・`ln -s $W/x /tmp/y`・`install -d`・`sed -n p` に限られています。くっつけた `-t` と複数の読み元を組み合わせた形（`cp -vt/tmp/d $W/a $W/b`）の対照がありません。この形では `guess` が空でないため、`tdir + guess + pos[-1:]` が `$W/b` を書き先に足します。読むだけでも exit 2 になるはずです。離した `cp -t /tmp/d $W/a $W/b` は `tdir` だけを返して通るので、形によって結果が食い違います。DANGER_OK でも外れない誤停止です。 | pretooluse_guard.py:821-827、test_i454_guard_env_writes.sh:97-100 | 静的読解のみ。E1 は拒否されて結果なし |
| Medium | false-green（対照の不足） | `sed -e"s/print/log/" $W/x` のように式に i が入る読むだけの形を、`_has_short(args,"i")` が `-i` と誤認し、`$W/x` を書き先として停止するはずです。04o の `sed -n p` は i を含まないため、固定されていません。TC-07 も停止側（取りこぼし）の期待しか持たないので、この誤停止はテストで検知できません。レビュー記録の F4 と同系統です。 | pretooluse_guard.py:811、test_i454_guard_env_writes.sh:100,103-121 | 静的読解のみ（同上） |
| Low | tautology 寄りの弱さ | FG-04 の失敗の注入は `cp -vt` 1 本だけです。04c〜04f（`install`・`ln`・`rsync`・`mv`）は、直接の期待値（2）で固定されるだけです。ただし書き先に至る経路は `_write_targets` だけなので、実害は小さいです。 | test_i454_guard_env_writes.sh:101 | 静的読解 |

読んで確かめたことは次のとおりです。

- **FG-01〜FG-03・FG-07 の注入**: 置き換え元が 1 回だけあることを `patch` が確かめています。注入後のコードで、対象ケースが期待どおり 0 に変わる作りになっています。注入が空振りしても NOPATCH で FAIL するので、tautology ではありません。
- **`b()` のガード異常終了**: 異常終了は `0`・`2`・`ASK` のどれにもならず FAIL になります。false-green にはなりません。
- **V4**: 非 loose の `_opt_values`（1884-1889 行）は、変更前と同じ 2 形（最後の文字が該当する形と先頭の文字が該当する形）だけを読みます。psql `-f`、grep のパターン、docker inspect の書式は非 loose の呼び出し元です。取りこぼしの後退は見つかりませんでした。loose を使うのは、多く読むほど止める側に倒れる箇所だけです。

> ITEM: V3 RESULT=read
> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I454] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Medium | 普通の操作の誤確認 | `_OPT_PATH_RE` は `--rootdir=`・`--confcutdir=` 以外の `--opt=/絶対パス` をすべて書き込みとみなす。通す形の道具のうち、読むだけの指定（`pytest --cov=/app/apps`・`--cov-config=/app/.coveragerc`・`--ignore=/app/x`・`--deselect=/app/…`、`eslint --config=/app/…`、`curl --output=/dev/null`）が毎回「コンテナの /tmp/ 以外への書き込み」の確認になる。V5 の「`pytest -k delete` などの通す形」は通るが、普通の作業に確認を出さないという目的には届いていない。計画の Risk 表は「件数は TC-06 で 1% 以内」としか書いておらず、今回の除外は 2 語だけ。corpus diff に出た実例は `--rootdir` だけだった。 | pretooluse_guard.py:2377, 2386–2388 | 静的読解。`_container_risky` が `_container_safe` の結果にかかわらず先に `vals` を `_in_scratch` で判定している。コードレビュー 0934 の F6 と同種で、既知 findings 欄は「なし」。実験はしていない。 |

V5 のうち確かめられた範囲（すべて読んで確認）:
- `pytest -k delete` は `-k` で `--opt=/` に当たらず、`_container_safe` が True になる。語の理由は打ち消され、書き込みの理由も空なので通る。
- `sh -c "pytest -k delete > /tmp/out.txt"` は、`write_to` が /tmp/ 配下なら `_in_scratch` が True になる。`_container_safe` から `c["writes"]` を外したので、通す形のまま通る。
- `/tmp/../app/y` は `normpath` で正規化されるので、/tmp/ 内とは扱われない。

他の観点の細部（`_opt_values` の誤読の再発など）は見ていない。

> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 15aa499f838275e92c58a38e375cf28606ef579e
ROUNDS: 1
VERDICT: OK
