# 敵対的レビュー [I444]（別プロセス・2026-11-11 20:51）

- 見た範囲: origin/develop...0a97a1d8aef00143603af6665df5ef15da112582
- 所要時間: 98 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- 一覧: docs/plans/open/plan_I444.md の「## 必ず確かめる項目」（5 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 3 | 読んで可 | 実験で確認 | P3-E2=ran  | 確認済み（実験） |
| V5 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 37 秒 | 0 | 0 | $0.2803 | ― | ― | ― |
| 2 | 報告あり | 32 秒 | 0 | 0 | $0.3010 | ― | ― | ― |
| 3 | 報告あり | 94 秒 | 1 | 0 | $0.7428 | ― | ― | ― |

## 実験

### 観点 3

#### P3-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; cd "$(git rev-parse --show-toplevel)"; G=scripts/claude/hooks/pretooluse_guard.py; for c in "ps -p 1 -o etime" "ps -C node" "ps -eo etimes,args" "ps aux" "docker compose exec -T backend ps -p 1 -o etime" "env --version" "declare -x FOO=1" "docker compose exec -T backend declare -p FOO"; do out=$(python3 -c "import json,sys;print(json.dumps({\"tool_name\":\"Bash\",\"tool_input\":{\"command\":sys.argv[1]}}))" "$c" | timeout 60 python3 $G 2>/dev/null); rc=$?; if [ $rc = 0 ] && printf %s "$out" | grep -q "\"ask\""; then echo "ASK  $c"; else echo "$rc  $c"; fi; done'
~~~
出力の先頭:
~~~
is_error=false
ASK  ps -p 1 -o etime
ASK  ps -C node
0  ps -eo etimes,args
0  ps aux
ASK  docker compose exec -T backend ps -p 1 -o etime
ASK  env --version
ASK  declare -x FOO=1
ASK  docker compose exec -T backend declare -p FOO
~~~

#### P3-E2: 実行した
~~~
bash -c 'ulimit -v 2097152; cd "$(git rev-parse --show-toplevel)"; G=scripts/claude/hooks/pretooluse_guard.py; D="docker compose exec -T backend"; for c in "$D cp -rt /app/x /tmp/y" "$D cp -vt/app/x /tmp/y" "$D install -d /app/newdir" "$D ln -s /tmp/a /app/b" "$D rsync -avt /tmp/a /app/b" "$D mv /tmp/a /tmp/b" "$D cp /tmp/a /tmp/b" "$D sh -c \"cp -t /app/x /tmp/y\"" "$D sh -c \"export\"" "$D truncate -s0 /app/x" "$D dd if=/dev/null of=/app/x" "$D pytest -k delete" "$D pytest -k delete | tail -20" "$D grep -rn token /app/apps"; do out=$(python3 -c "import json,sys;print(json.dumps({\"tool_name\":\"Bash\",\"tool_input\":{\"command\":sys.argv[1]}}))" "$c" | timeout 60 python3 $G 2>/dev/null); rc=$?; if [ $rc = 0 ] && printf %s "$out" | grep -q "\"ask\""; then echo "ASK  $c"; else echo "$rc  $c"; fi; done'
~~~
出力の先頭:
~~~
is_error=false
ASK  docker compose exec -T backend cp -rt /app/x /tmp/y
0  docker compose exec -T backend cp -vt/app/x /tmp/y
0  docker compose exec -T backend install -d /app/newdir
ASK  docker compose exec -T backend ln -s /tmp/a /app/b
ASK  docker compose exec -T backend rsync -avt /tmp/a /app/b
0  docker compose exec -T backend mv /tmp/a /tmp/b
0  docker compose exec -T backend cp /tmp/a /tmp/b
ASK  docker compose exec -T backend sh -c "cp -t /app/x /tmp/y"
ASK  docker compose exec -T backend sh -c "export"
ASK  docker compose exec -T backend truncate -s0 /app/x
2  docker compose exec -T backend dd if=/dev/null of=/app/x
0  docker compose exec -T backend pytest -k delete
0  docker compose exec -T backend pytest -k delete | tail -20
ASK  docker compose exec -T backend grep -rn token /app/apps
~~~

#### P3-E3: 実行した
~~~
bash -c 'ulimit -v 2097152; cd "$(git rev-parse --show-toplevel)"; G=scripts/claude/hooks/pretooluse_guard.py; W="$(git rev-parse --show-toplevel)/../other-wt"; for c in "cp -t $W/x /tmp/y" "cp /tmp/y $W/x" "mv /tmp/y $W/x" "psql -h localhost -U app -c \"UPDATE users SET is_active=false\"" "docker compose exec -T db psql -U app -c \"UPDATE users SET is_active=false\"" "docker compose exec -T db psql -U app -c \"UPDATE users SET is_active=false WHERE id=1\""; do out=$(python3 -c "import json,sys;print(json.dumps({\"tool_name\":\"Bash\",\"tool_input\":{\"command\":sys.argv[1]}}))" "$c" | timeout 60 python3 $G 2>/dev/null); rc=$?; if [ $rc = 0 ] && printf %s "$out" | grep -q "\"ask\""; then echo "ASK  $c"; else echo "$rc  $c"; fi; done'
~~~
出力の先頭:
~~~
is_error=false
2  cp -t /mnt/c/app/study-app-multitenant/.claude/worktrees/harness-1/../other-wt/x /tmp/y
2  cp /tmp/y /mnt/c/app/study-app-multitenant/.claude/worktrees/harness-1/../other-wt/x
2  mv /tmp/y /mnt/c/app/study-app-multitenant/.claude/worktrees/harness-1/../other-wt/x
2  psql -h localhost -U app -c "UPDATE users SET is_active=false"
2  docker compose exec -T db psql -U app -c "UPDATE users SET is_active=false"
0  docker compose exec -T db psql -U app -c "UPDATE users SET is_active=false WHERE id=1"
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I444] ── 観点: ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | V1 | `ps` の BSD 形式 e の判定は、`-o etime`・`-u deploy`・`-C node` のようなオプションの値にも当たる。ホストの `ps -o etime` が確認になる。`ps -eo etimes,args` は値にカンマがあるので通る。`ps -eo etimes`（カンマなし）は確認になる。(C) の取りこぼしではなく誤検出で、既知の台帳 F3 と同じ。新規には数えない。 | pretooluse_guard.py:2253 | 静的読解（`re.fullmatch` の式を追った） |
| Low | V2 | `-t` の値をくっつけた形（`cp -t/app/x` や `-vt/app/x`）は `_opt_values` が読めず、通る。`install -d /app/d` も位置引数が 1 つなので通る。粗い判定の範囲内で、既知の台帳 F5 と同じ。新規には数えない。 | pretooluse_guard.py:1875-1879, 2413 | 静的読解 |

V1 と V2 の確認項目は、読んだ範囲では計画どおりに動く。

- **V1: 確認になる形**
  - `printenv`、先頭に残った `env`（`env -u X`・`env -0`・引数なし）、引数なしの `set` が確認になる。
  - 引数なし、または `-` で始まる引数だけの `export`・`declare`・`typeset` が確認になる。
  - `-p`・`-x` を含む形も確認になる。
  - `ps e`・`ps auxe`・`ps aux e` も確認になる。
- **V1: 通る形**
  - `set -euo pipefail` は `len(toks)==1` を満たさないので通る。
  - `export FOO=1` は `-` で始まらない引数があり、`-p`・`-x` も無いので通る。
  - `env FOO=1 cmd` は読み解きで `env` が外れるので通る。
  - `ps aux` は英字だけの引数に `e` が無いので通る。
  - `ps -eo etimes,args` は上のとおり通る。
- **V2: 確認になる形**
  - `cp --target-directory=/app/x /tmp/y` は確認になる。
  - `cp -t /app/x /tmp/y` は確認になる。
  - `cp -rt /app/x /tmp/y` は確認になる。
  - `mv /app/x /tmp/y` は移動元の `/app/x` が書き先に入るので確認になる。
- **V2: 通る形**
  - `mv /tmp/a /tmp/b` と `cp -t /tmp/x /tmp/y` は、書き先がすべて `/tmp/` 内なので通る。
  - `rsync -avt` は `-t` を書き先として読まない（コード上でそう分けてある）。
- **回避の確認**
  - `export FOO=1; export` のような連結は、コマンドが分けて判定されるので抜けない。
  - 普通の書き方で、環境変数の表示や `/app/` への書き込みが確認なしで通る穴は見つからなかった。

探索した仮説:
- `env`・`set`・`export`・`declare`・`typeset` の境界（引数なし、値つき、`-` だけの引数）
- `ps` の正規表現の誤検出と見落とし
- `-t` の各表記（`-t X`・`-rt X`・`--target-directory=X`・`--target-directory X`・値をくっつけた形）
- `mv` の移動元の扱い
- `rsync` の `-t`

実験案は出さない。上の判定は読んで確かめた。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I444] ── 観点: テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | false-green | 許可リストを縮めたあとも停止（2）が通る側に変わらないことを、直接確かめるテストはない。TC-03 は psql の UPDATE の 2 件だけを停止として固定している。停止の不変は構造で保たれるので、害はない。 | `scripts/claude/tests/test_i444_guard_gaps.sh:80-85` | 静的読解 |

反証失敗（V3 は成り立つ）。探索した仮説:
- **停止の判定が許可リストを通るか**: 通らない。`_analyze`（`pretooluse_guard.py:2620`）は `d, e = _cmd_danger(c), _cmd_external(c)` を先に計算する。`_container_safe` を呼ぶのは `not d and not e` のときだけ（2628 行）。
- **許可リストの結果がどこに入るか**: 追加先は `res["container"]`（確認）だけで、`res["hard"]` や停止の経路には入らない。許可リストを縮めると、確認になる形が増えることはあっても、停止が通る側に変わることはない。
- **SQL の停止判定が許可リストに依存していないか**: 依存していない。`_sql_is_destructive` の呼び出しは 1165・2156・2160 行で、どれも `_cmd_danger` 側にある。`_container_safe` 内の psql の判定は読み取りの SQL（`_sql_is_safe_read`）だけを通す。
- **削った定数が停止の経路で使われていないか**: 使われていない。`_SAFE_READ_CMDS` と `_SAFE_REDIS` は、grep で定義も参照も残っていない。
- **テストの失敗の注入が空振りしないか**: 空振りしない。`patch` は `old` がちょうど 1 回なければ exit 3 になり、`fg` が `NOPATCH` として FAIL に倒す。FG-03 は `if False:` へ置き換えて、停止（2）が通る（0）に変わることを確かめている。
- **TC-03 が実装の再確認になっていないか**: なっていない。期待値は人が決めた 2（停止）と、WHERE ありの 0。1 件ごとに独立に判定している。
- **実験は不要と判断した**: 上の構造で十分に言えるため。

> ITEM: V3 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I444] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Medium | 要件の抜け（B） | `install -d /app/newdir` と `cp -vt/app/x`（値をくっつけた形）は、コンテナの `/app/`（手元に bind mount）への書き込みなのに確認にならない。これは `install -d`（位置引数が 1 つ）が書き先として見られないことと、`_opt_values` が `-vt/app/x` の形を読めないことによる。受け入れ条件の `cp -t` 系は確認になるが、同じ意味の別の書き方が漏れる。計画の「粗い判定」の範囲内の取りこぼしで、意図的な回避ではなく普通の書き方で起きる。コードレビューの F5 と実質同一なので、新規としては数えない。 | `pretooluse_guard.py:2408-2413` | P3-E2: `install -d /app/newdir` は 0、`cp -vt/app/x /tmp/y` は 0 |
| Low | 誤検出 | `ps -p 1 -o etime`・`ps -C node`・`env --version`・`declare -x FOO=1`・`declare -p FOO` が新しく確認になる。止める側の漏れではなく、普通の作業の確認が増える。コードレビューの F3・F4 と同じなので、新規としては数えない。 | `pretooluse_guard.py:2252-2255` | P3-E1 の結果のとおり |
| Low | 手順書 | `danger-ops.md` 3. は代表を `printenv`・`env`・`export` に絞って書いている。`set`・`ps` の e・`declare -p` の書き込みは代表に入っていないが、「代表」と明記しているので食い違いではない。 | `danger-ops.md:28` | 静的読解 |

観点 3 の主な確認結果:
- 受け入れ条件の 3 点は、実測で成り立っている。
  - `cp -rt /app/x /tmp/y`・`rsync -avt /tmp/a /app/b`・`ln -s /tmp/a /app/b` は確認になる。
  - `mv /tmp/a /tmp/b` と `cp /tmp/a /tmp/b` は通る。
  - psql の WHERE なしの UPDATE は、ホストでもコンテナ内でも停止（2）になる。WHERE ありは通る。
  - 別ワークツリーへの書き込みは、`cp`・`mv`・`cp -t` のどれも停止（2）になる。
- 普通の操作は通る。`pytest -k delete` と `pytest -k delete | tail -20` は 0。`ps aux` と `ps -eo etimes,args` も 0。
- `sh -c "cp -t …"`・`sh -c "export"` のように `sh -c` で包んだ形も確認になる。
- 手順書は実物と合っている。
  - `danger-ops.md` 4. の「形の正」の指定先と、`mv` の移動元・`-t` の記述は実物と一致する。
  - `worktree.md:244` の打ち切りの説明は、`sessionstart_context.py` の `_run` と一致する。

新規の Critical/High は見つからなかった。

> ITEM: V4 RESULT=experiment EXP=P3-E2
> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 0a97a1d8aef00143603af6665df5ef15da112582
ROUNDS: 1
VERDICT: OK
