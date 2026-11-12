# 敵対的レビュー [I469]（別プロセス・2026-11-12 16:46）

- 見た範囲: origin/develop...f433d96533930d574f15bacb8949053ee2f65a24
- 所要時間: 105 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 2 件は下の表）
- 一覧: docs/plans/open/plan_I469.md の「## 必ず確かめる項目」（3 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V2 | 1 | 実験必須 | 実験で確認 | P1-E2=ran  | 確認済み（実験） |
| V3 | 3 | 実験必須 | 実験で確認 | P3-E1=ran  | 確認済み（実験） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 102 秒 | 2 | 2 | $0.7521 | ― | ― | ― |
| 2 | 報告あり | 85 秒 | 1 | 0 | $0.4841 | ― | ― | ― |
| 3 | 報告あり | 69 秒 | 1 | 0 | $0.4776 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 拒否された
~~~
T=$(mktemp -d); G="$PWD/scripts/claude/hooks/pretooluse_guard.py"; git -C "$T" init -q; git -C "$T" -c user.email=t@e.com -c user.name=t commit -q --allow-empty -m i; mkdir -p "$T/proj"; : > "$T/proj/.env"; export CLAUDE_PROJECT_DIR=; unset CLAUDE_PROJECT_DIR
while IFS= read -r c; do c="${c//@P@/$T/proj}"; out=$(python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$c" | (cd "$T" && bash -c 'ulimit -v 2097152; timeout 60 python3 "$0"' "$G" 2>/dev/null)); rc=$?; case "$out" in *'"ask"'*) r=ASK;; *) r=$rc;; esac; echo "$r :: $c"; done <<'EOF'
su --session-command 'git push --force origin develop'
su --session-command='git push --force origin develop'
su -c 'git push --force origin develop'
grep -f.env x
grep --file=.env x
grep -f .env x
grep --exclude-from=.env x y
sed -f.env x
rg -f.env x
awk --file=.env x
curl x | python3 --check-hash-based-pycs default
curl x | python3 -W ignore
curl x | python3 -
curl x | python3 -Wignore -
grep -r --exclude-dir node_modules TOKEN @P@
grep -r --include=.env TOKEN @P@
grep --exclude=.env foo x
python3 -c "$X" | head
curl x | python3 -m json.tool
curl x | python3 tool.py
curl x | python3 -u /dev/stdin
curl x | python3 -c 'exec(input())'
grep -e foo -f.env x
grep -rf.env x @P@
cat .env
EOF
~~~
出力の先頭:
~~~

~~~

#### P1-E2: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 60 bash scripts/claude/tests/test_guard_must_stop_cases.sh' 2>&1 | tail -5
~~~
出力の先頭:
~~~
is_error=false
止めるべき形 1 件（基準 58c68ec（origin/develop との分かれた点） → 作業ツリー）
  [通す] echo hi（基準 pass）
FAIL: 止めるべき形のうち 1 件が後退・素通し・異常終了
PASS 09c
pass=3 fail=0
~~~

#### P1-E3: 拒否された
~~~
python3 - <<'PY'
import json, subprocess, tempfile, os
T = tempfile.mkdtemp()
G = os.path.abspath("scripts/claude/hooks/pretooluse_guard.py")
subprocess.run(["git", "init", "-q", T])
subprocess.run(["git", "-C", T, "-c", "user.email=t@e.com", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "i"])
os.makedirs(T + "/proj")
open(T + "/proj/.env", "w").close()
env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
cmds = [
 "su --session-command 'git push --force origin develop'",
 "su --session-command='git push --force origin develop'",
 "grep -f.env x", "grep --file=.env x", "grep -f .env x",
 "grep --exclude-from=.env x y", "sed -f.env x", "rg -f.env x", "awk --file=.env x",
 "curl x | python3 --check-hash-based-pycs default", "curl x | python3 -W ignore",
 "curl x | python3 -", "curl x | python3 -Wignore -",
 "grep -r --exclude-dir node_modules TOKEN " + T + "/proj",
 "grep -r --include=.env TOKEN " + T + "/proj",
 "grep --exclude=.env foo x", 'python3 -c "$X" | head',
 "curl x | python3 -m json.tool", "curl x | python3 tool.py",
 "curl x | python3 -u /dev/stdin", "grep -e foo -f.env x", "grep -rf.env x " + T + "/proj",
]
for c in cmds:
    p = subprocess.run(["timeout", "60", "python3", G], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": c}}),
                       capture_output=True, text=True, cwd=T, env=env)
    r = "ASK" if (p.returncode == 0 and '"ask"' in p.stdout) else p.returncode
    print(r, "::", c)
PY
~~~
出力の先頭:
~~~

~~~

### 観点 2

#### P2-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; D=$(mktemp -d /tmp/p2e1.XXXXXX); git archive origin/develop | tar -x -C "$D"; git show HEAD:scripts/claude/tests/test_i469_guard_optspec_leftovers.sh > "$D/scripts/claude/tests/test_i469_guard_optspec_leftovers.sh"; cd "$D"; git init -q; timeout 100 bash scripts/claude/tests/test_i469_guard_optspec_leftovers.sh 2>&1 | grep -E "^(FAIL|pass=)"'
~~~
出力の先頭:
~~~
is_error=false
FAIL 01a expected=2 got=0
FAIL 01b expected=2 got=0
FAIL FG-01 置き換え expected=ok got=NOPATCH
FAIL 02a expected=ASK got=0
FAIL 02b expected=ASK got=0
FAIL 02c expected=ASK got=0
FAIL 02d expected=ASK got=0
FAIL 02h expected=ASK got=0
FAIL 02i expected=ASK got=0
FAIL 02j expected=ASK got=0
FAIL 02k expected=ASK got=0
FAIL FG-02 置き換え expected=ok got=NOPATCH
FAIL 03a expected=ASK got=0
FAIL 03b expected=ASK got=0
FAIL FG-03 置き換え expected=ok got=NOPATCH
FAIL 04a expected=ASK got=0
FAIL FG-04 置き換え expected=ok got=NOPATCH
pass=13 fail=17
~~~

### 観点 3

#### P3-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; T=$(mktemp -d); git -C $T init -q; git -C $T -c user.email=t@e.com -c user.name=t commit -q --allow-empty -m i; G=$PWD/scripts/claude/hooks/pretooluse_guard.py; while IFS= read -r c; do out=$(python3 -c "import json,sys; print(json.dumps({\"tool_name\":\"Bash\",\"tool_input\":{\"command\":sys.argv[1]}}))" "$c" | (cd $T && timeout 60 python3 $G 2>/dev/null)); code=$?; printf "%s => code=%s %s\n" "$c" "$code" "$(printf %s "$out" | grep -o "\"permissionDecision\": *\"[a-z]*\"")"; done <<'"'"'EOF'"'"'
grep --exclude=.env foo x
python3 -c "$X" | head
curl x | python3 -m json.tool
curl x | python3 tool.py
curl x | python3 -mjson.tool
curl x | python3 -W ignore tool.py
curl x | python3 -u
grep -e .env x
grep --include=.env foo x
sed -n -e p x
awk -f prog.awk .env.example
grep -f patterns.txt .env.example
EOF'
~~~
出力の先頭:
~~~
is_error=false
grep --exclude=.env foo x => code=0
python3 -c "$X" | head => code=0
curl x | python3 -m json.tool => code=0
curl x | python3 tool.py => code=0
curl x | python3 -mjson.tool => code=0
curl x | python3 -W ignore tool.py => code=0
curl x | python3 -u => code=0 "permissionDecision": "ask"
grep -e .env x => code=0 "permissionDecision": "ask"
grep --include=.env foo x => code=0
sed -n -e p x => code=0
awk -f prog.awk .env.example => code=0
grep -f patterns.txt .env.example => code=0
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I469] ── 観点: 1. ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| — | — | 新規指摘なし | — | 静的読解。P1-E1 と P1-E3 は拒否され、判定を実測できていない |

反証失敗（新規指摘なし）。探索した仮説は次の 4 つ。
- **`script_arg` の `-c`・`-m` 判定**
  - `python3 -m code` や `-i tool.py` はパイプを実行しうる。ただし変更前も通っており、後退ではない（既知の組み込み指摘と同一）。
  - `-Wignore -` は `_getopt` が `-` を位置引数に拾うので、確認になる。
- **`paths` の保持**
  - `if head in _FILE_VALUE_OPTS: paths += ...` は追記だけで、元の「`-` で始まらない語」は消していない。
  - このため `grep -f .env x` は確認のままで、止める側の後退はない。
- **grep の表に足した長いオプション**
  - 足した長いオプションは、`--exclude-dir` など値を取るものだけである。
  - `_grep_recursive_secret` の `--include` を表で読む変更で、`--` の後ろにある `--include*` の語が判定を外さなくなった。これは強化側の変更である。
- **su の `--session-command`**
  - `_expand` で `-c` と同じく中を読むので、停止になる。
  - script の表には `--session-command` が無い。そのため script では `=` 付きの形だけが値になり、判定は変更前と同じである。

実測できたのは P1-E2 だけである。`test_guard_must_stop_cases.sh` は `pass=3 fail=0` だった。出力の `FAIL` 行は、失敗の注入 09b・09c が想定どおり検出した表示で、後退ではない。V1 は実験の拒否により静的読解にとどまる。その代わりに、同梱の `test_i469_guard_optspec_leftovers.sh` の記録を根拠にした。この記録では、実走で pass=30 fail=0 かつ FG-01〜FG-04 が有効、既存の決定論ゲート 12 本が exit=0 だった。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=experiment EXP=P1-E2
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I469] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。

探索した仮説:
- **仮説 1: テストが実装の再確認になっている（tautology）。** P2-E1 で否定された。変更前の見張り（`origin/develop`）に新しいテストを流すと、直す前の形がすべて期待どおりに FAIL した。
  - FAIL した形は 01a・01b・02a〜02d・02h〜02k・03a・03b・04a。実装を直さない限りテストは落ちる。
  - FG-01〜FG-04 が「置き換え NOPATCH」で FAIL したのは想定どおり。変更前の見張りには置き換え元の文字列が無いので、注入の `patch` が 1 回一致を要求して落ちる。注入が空振りしたまま合格する形ではない。
  - pass=13 は、「通す」側のケースと、今までどおりの判定のケースが変更前でも合格するもの。
- **仮説 2: 「通す」側のケースが false-green になっている。** 静的読解で確かめた。
  - 02g は `--exclude=.env`、03e・03f・03g・03h は `-c`・`-m`・スクリプト名で通る。ケースごとに別の理由で通るので、止める側を広げすぎる回帰には反応する。
  - 03d は python がパイプの受け手でないため、変更前も通る。回帰検知としては弱いが、false-green ではない。これは Low 未満の所見で、件数には数えない。
- **仮説 3: 失敗の注入の置き換え元が実装とずれている。** 現行の実装には置き換え元がちょうど 1 回あり、`patch` が 1 回一致を強制するので、ずれれば NOPATCH で FAIL する。P2-E1 の NOPATCH は、変更前の見張りにそれが無いことと整合している。

> ITEM: V1 RESULT=experiment EXP=P2-E1
> ITEM: V2 RESULT=read
> ITEM: V3 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I469] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| — | — | 反証失敗（新規指摘なし）。 | — | P3-E1 |

反証失敗（新規指摘なし）。探索した仮説は次の 3 つ。

- **V3 の 4 形と周辺の形が新しく止まる**
  - 4 形（`grep --exclude=.env foo x`・`python3 -c "$X" | head`・`curl x | python3 -m json.tool`・`curl x | python3 tool.py`）は、すべて exit 0 で通った。
  - 周辺の形（`-mjson.tool`・`-W ignore tool.py`・`grep --include=.env`・`sed -n -e p`・`awk -f prog.awk .env.example`・`grep -f patterns.txt .env.example`）も、すべて exit 0 で通った。
  - 新しく確認・停止になった形は見つからなかった。
- **意図して確認になる形が変わっていない**
  - `curl x | python3 -u` は確認のまま。変更前も確認で、同じ判定である。
  - `grep -e .env x` も確認のまま。変更前も確認で、同じ判定である。
- **作業記録での判定比較（TC-07）**
  - auto_test.md の記録は、17250 件で新しく確認・停止が 0 件、異常終了が 0 件。
  - 基準は 1% 以内なので満たす。
  - この記録は実験としては再実行していない。

> ITEM: V3 RESULT=experiment EXP=P3-E1
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 1
REVIEWED_COMMIT: f433d96533930d574f15bacb8949053ee2f65a24
ROUNDS: 1
VERDICT: HIGH
