# 敵対的レビュー [I463]（別プロセス・2026-11-12 13:19）

- 見た範囲: origin/develop...e377602efa82755260c378db93b1fe6617b28cfd
- 所要時間: 115 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 2 件は下の表）
- 一覧: docs/plans/open/plan_I463.md の「## 必ず確かめる項目」（4 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V2 | 2 | 実験必須 | 実験で確認 | P2-E2=ran  | 確認済み（実験） |
| V3 | 1 | 実験必須 | 実験で確認 | P1-E3=ran  | 確認済み（実験） |
| V4 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 72 秒 | 1 | 1 | $0.5791 | ― | ― | ― |
| 2 | 報告あり | 112 秒 | 2 | 1 | $1.0778 | ― | ― | ― |
| 3 | 報告あり | 14 秒 | 0 | 0 | $0.2304 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 60 bash -c "for c in sed grep cp mv ln install su flock script; do echo \"== \$c\"; \$c --help 2>&1 | grep -E \"^ +-[A-Za-z0-9]|^ +-[A-Za-z], --\" | grep -E \"[A-Z=\[<]\" | head -40; done; python3 --help 2>&1 | grep -E \"^-[cmWX]|^-[A-Za-z] \" | head -30"'
~~~
出力の先頭:
~~~
is_error=false
== sed
  -e script, --expression=script
  -f script-file, --file=script-file
  -i[SUFFIX], --in-place[=SUFFIX]
  -l N, --line-length=N
  -E, -r, --regexp-extended
== grep
  -E, --extended-regexp     PATTERNS are extended regular expressions
  -F, --fixed-strings       PATTERNS are strings
  -G, --basic-regexp        PATTERNS are basic regular expressions
  -P, --perl-regexp         PATTERNS are Perl regular expressions
  -e, --regexp=PATTERNS     use PATTERNS for matching
  -f, --file=FILE           take PATTERNS from FILE
  -V, --version             display version information and exit
  -m, --max-count=NUM       stop after NUM selected lines
  -H, --with-filename       print file name with output lines
  -a, --text                equivalent to --binary-files=text
  -I                        equivalent to --binary-files=without-match
  -d, --directories=ACTION  how to handle directories;
  -D, --devices=ACTION      how to handle devices, FIFOs and sockets;
  -r, --recursive           like --directories=recurse
  -R, --dereference-recursive  likewise, but follow all symlinks
  -L, --files-without-match  print only names of FILEs with no selected lines
  -l, --files-with-matches  print only names of FILEs with selected lines
  -c, --count               print only a count of selected lines per FILE
  -T, --initial-tab         make tabs line up (if needed)
  -Z, --null                print 0 byte after FILE name
  -B, --before-context=NUM  print NUM lines of leading context
  -A, --after-context=NUM   print NUM lines of trailing context
  -C, --context=NUM         print NUM lines of output context
  -NUM                      same as --context=NUM
  -U, --binary              do not strip CR characters at EOL (MSDOS/Windows)
== cp
  -a, --archive                same as -dR --preserve=all
  -d                           same as --no-dereference --preserve=links
  -H                           follow command-line symbolic links in SOURCE
  -L, --dereference            always
~~~

#### P1-E2: 拒否された
~~~
bash -c 'ulimit -v 2097152; cd "$(git rev-parse --show-toplevel)"; mkdir -p /tmp/p1e2; git show origin/develop:scripts/claude/hooks/pretooluse_guard.py > /tmp/p1e2/base_guard.py; cat > /tmp/p1e2/run.sh <<"EOS"
#!/bin/bash
# usage: run.sh guardfile command
python3 - "$1" "$2" <<"PY"
import json,subprocess,sys
g,c=sys.argv[1],sys.argv[2]
p=subprocess.run(["python3",g],input=json.dumps({"tool_name":"Bash","tool_input":{"command":c},"cwd":"/tmp"}),capture_output=True,text=True,timeout=40)
print(p.returncode, (p.stdout+p.stderr)[:60].replace("\n"," "))
PY
EOS
chmod +x /tmp/p1e2/run.sh
while IFS= read -r c; do
 b=$(timeout 60 /tmp/p1e2/run.sh /tmp/p1e2/base_guard.py "$c"); n=$(timeout 60 /tmp/p1e2/run.sh scripts/claude/hooks/pretooluse_guard.py "$c")
 echo "CMD: $c"; echo "  BASE: $b"; echo "  NEW : $n"
done <<"CASES"
grep -f .env x
grep -f.env x
grep -ie. .env
grep -i x .env
grep -m1 x .env
grep -A3 -f .env x
psql -Xf/tmp/dump.sql
psql mydb -c "DELETE FROM users"
psql -tAc "DELETE FROM users"
psql -Xc "DELETE FROM users"
psql -1c "DELETE FROM users"
psql -U postgres -d db -c "DROP TABLE users"
psql --command="DROP TABLE users"
psql --command "DROP TABLE users"
psql -- -c "DROP TABLE x"
sed -i s/a/b/ /app/.env
sed -ni s/a/b/ .env
sed -n -i.bak s/a/b/ .env
sed --in-place s/a/b/ .env
sed -i -e s/a/b/ .env
python3 -c "import os; os.system(\"rm -rf /\")"
python3 -W ignore -c "open(\".env\").read()"
python3 -X dev -c "open(\".env\").read()"
python3 -Wignore -c "open(\".env\").read()"
python3 -m django flush --noinput
python3 manage.py flush --noinput
python3 manage.py shell -c "User.objects.all().delete()"
python3 manage.py shell -i python -c "User.objects.all().delete()"
python3 manage.py shell -v 2 -c "User.objects.all().delete()"
su -c "git push --force origin develop"
su -lc "git push --force origin develop"
su -s /bin/bash -c "git push --force origin develop"
su postgres -c "git push --force origin develop"
flock /tmp/l -c "git push --force origin develop"
flock -w 3 /tmp/l git push --force origin develop
flock -n /tmp/l git push --force origin develop
flock -E 5 /tmp/l -c "git push --force origin develop"
script -qc "git push --force origin develop" /dev/null
script -q -c "git push --force origin develop" /dev/null
script -O out -c "git push --force origin develop"
cp -t /tmp/d /app/.env
cp -S .bak a /app/.env
mv -S .bak a /app/.env
install -m 644 a /app/.env
install -d /app/x
ln -sf a /app/.env
CASES
'
~~~
出力の先頭:
~~~

~~~

#### P1-E3: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 60 bash scripts/claude/tests/test_guard_must_stop_cases.sh 2>&1 | tail -15'
~~~
出力の先頭:
~~~
is_error=false
OK: 47 件すべて作業ツリーで確認か停止・変更前より弱い判定 0 件
PASS 09a
止めるべき形 5 件（基準 HEAD → 作業ツリー）
  [通す] psql -hlocalhost -U postgres <<EOF⏎DELETE FROM users;⏎EOF（基準 block）
  [通す] psql -Ucelery -dcourse_db <<EOF⏎DELETE FROM users;⏎EOF（基準 block）
  [通す] psql -tAc'DELETE FROM users'（基準 block）
  [通す] psql -Umarc mydb -c 'DELETE FROM users'（基準 block）
  [通す] psql -hlocal$(hostname) -U postgres <<EOF⏎DELETE FROM users;⏎EOF（基準 block）
FAIL: 止めるべき形のうち 5 件が後退・素通し・異常終了
PASS 09b
止めるべき形 1 件（基準 72ffe57（origin/develop との分かれた点） → 作業ツリー）
  [通す] echo hi（基準 pass）
FAIL: 止めるべき形のうち 1 件が後退・素通し・異常終了
PASS 09c
pass=3 fail=0
~~~

### 観点 2

#### P2-E1: 拒否された
~~~
bash -c 'ulimit -v 2097152; set -u
R="$(git rev-parse --show-toplevel)"
T="$(mktemp -d)"
git show origin/develop:scripts/claude/hooks/pretooluse_guard.py > "$T/base.py"
M="$T/main"; mkdir -p "$M"; git -C "$M" init -q
git -C "$M" -c user.email=t@e.com -c user.name=t commit -q --allow-empty -m i
git -C "$M" branch -q other
W="$T/wt"; git -C "$M" worktree add -q "$W" other
E="$T/evil.py"
printf "import django\nfrom apps.users.models import User\nUser.objects.all().delete()\n" > "$E"
printf "print(1)\n" > "$T/ok.py"
b() { local out code
  out=$(python3 -c "import json,sys; print(json.dumps({\"tool_name\":\"Bash\",\"tool_input\":{\"command\":sys.argv[1]}}))" "$1" | (cd "$M" && timeout 60 python3 "$2" 2>/dev/null)); code=$?
  if [ "$code" = 0 ] && printf "%s" "$out" | grep -q "\"ask\""; then echo ASK; else echo "$code"; fi; }
while IFS= read -r line; do
  [ -z "$line" ] && continue
  line="${line//@E@/$E}"; line="${line//@O@/$T/ok.py}"; line="${line//@W@/$W}"
  printf "%-6s %-6s %s\n" "$(b "$line" "$T/base.py")" "$(b "$line" "$R/scripts/claude/hooks/pretooluse_guard.py")" "$line"
done <<EOF
psql mydb -c "DELETE FROM users"
psql mydb -f /tmp/x.sql
psql -- mydb -c "DELETE FROM users"
psql - -c "DELETE FROM users"
psql -Umarc mydb -c "DELETE FROM users"
psql -1c "DELETE FROM users"
psql -tAc "DELETE FROM users"
psql --command "DELETE FROM users"
psql --command="DELETE FROM users"
psql mydb --command="DELETE FROM users"
python3 @E@ -xcfoo
python3 @E@ -m foo
python3 -- @E@
python3 -u @E@
python3 -W ignore @E@
python3 -Wignore @E@ -c x
python3 -c "print(1)" @E@
python3 -m pytest -xcfoo
python3 @O@ -xcfoo
python3 - -c x
python3 -c "import os; os.system(\"rm -rf /\")" @O@
python3 -Ic "from apps.users.models import User; User.objects.all().delete()"
python3 -Xdev -c "from apps.users.models import User; User.objects.all().delete()"
python3 -B -- -c "from apps.users.models import User; User.objects.all().delete()"
python3 --check-hash-based-pycs default -c "print(open(\".env\").read())"
python3 -q @E@
python3 -E @E@
cp -- @W@/a /tmp/b
cp /tmp/a @W@/b -v
cp /tmp/a -t @W@/d
cp /tmp/a -- @W@/b
sed s/a/b/ @W@/x -i
sed -- s/a/b/ @W@/x -i
sed -n -- -i @W@/x
sed -i -- s/a/b/ @W@/x
EOF
rm -rf "$T"'
~~~
出力の先頭:
~~~

~~~

#### P2-E2: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 60 python3 -c "
import importlib.util as u
s=u.spec_from_file_location(\"g\",\"scripts/claude/hooks/pretooluse_guard.py\");m=u.module_from_spec(s);s.loader.exec_module(m)
g=m._getopt
for cmd,a in [(\"python\",[\"/tmp/e.py\",\"-xcfoo\"]),(\"python\",[\"-Wignore\",\"/tmp/e.py\",\"-c\",\"x\"]),(\"python\",[\"-\",\"-c\",\"x\"]),(\"python\",[\"-m\",\"pytest\",\"-xcfoo\"]),(\"python\",[\"--\",\"e.py\",\"-c\",\"x\"]),(\"python\",[\"-B\",\"--\",\"-c\",\"x\"]),(\"psql\",[\"mydb\",\"-c\",\"DELETE\"]),(\"psql\",[\"--\",\"mydb\",\"-c\",\"D\"]),(\"psql\",[\"-\",\"-c\",\"D\"]),(\"psql\",[\"-1c\",\"D\"]),(\"sed\",[\"s/a/b/\",\"x\",\"-i\"]),(\"sed\",[\"-i\",\"--\",\"s/a/b/\",\"x\"]),(\"cp\",[\"/tmp/a\",\"x\",\"-v\"])]:
    print(cmd,a,g(cmd,a))
"'
~~~
出力の先頭:
~~~
is_error=false
python ['/tmp/e.py', '-xcfoo'] ([], ['/tmp/e.py', '-xcfoo'])
python ['-Wignore', '/tmp/e.py', '-c', 'x'] ([('-W', 'ignore')], ['/tmp/e.py', '-c', 'x'])
python ['-', '-c', 'x'] ([], ['-', '-c', 'x'])
python ['-m', 'pytest', '-xcfoo'] ([('-m', 'pytest')], ['-xcfoo'])
python ['--', 'e.py', '-c', 'x'] ([], ['e.py', '-c', 'x'])
python ['-B', '--', '-c', 'x'] ([('-B', None)], ['-c', 'x'])
psql ['mydb', '-c', 'DELETE'] ([('-c', 'DELETE')], ['mydb'])
psql ['--', 'mydb', '-c', 'D'] ([], ['mydb', '-c', 'D'])
psql ['-', '-c', 'D'] ([('-c', 'D')], ['-'])
psql ['-1c', 'D'] ([('-1', None), ('-c', 'D')], [])
sed ['s/a/b/', 'x', '-i'] ([('-i', None)], ['s/a/b/', 'x'])
sed ['-i', '--', 's/a/b/', 'x'] ([('-i', None)], ['s/a/b/', 'x'])
cp ['/tmp/a', 'x', '-v'] ([('-v', None)], ['/tmp/a', 'x'])
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I463] ── 観点: 1. ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | V1 | `_OPTSPEC` の sed・grep・cp・mv・ln・install・su・flock・script・python は、静的読解では `--help` と矛盾しない。grep の値を取る文字 `ABCDdefm`、sed の `-e -f -l` と `-i[SUFFIX]` は E1 の出力と一致した。E1 の出力は `head -40` と grep の絞り込みで途中までなので、cp 以降は実機で突き合わせられていない。値を取らない文字を値ありとした箇所は見つからなかった。psql は手元に無く、文書に拠るため実機で突き合わせていない。 | pretooluse_guard.py:1860-1875 | E1（grep・sed のみ実機で確認）。ほかは静的読解 |
| Low | V1 | 値を取る長いオプションが表に無い。例は grep の `--exclude-dir`、python の `--check-hash-based-pycs`、su の `-C`。python の例は変更前の確認から通すに後退する。脅威モデルは「普通の書き方の事故」で、これは意図的なすり抜けにあたる。台帳 F1〜F5 と同じ指摘なので新規には数えない。 | :1864-1872 | 台帳 F1〜F5。静的読解 |
| Low（実験の不備） | V3 | E3 の 09b・09c では、失敗の注入が意図どおり「FAIL」を出した。09b は DELETE 行の見張りを外すと 5 件が通るようになる。09c は `echo hi` を足すと FAIL になる。この後退検知は動いている。ただし E3 の出力の本体は `OK: 47 件…` で、HEAD の見張りが変更前より弱い判定を出した形は 0 件だった。 | test_guard_must_stop_cases.sh | E3 |
| Info | V3 | `paths` は `-` で始まらない語すべてのままで、位置引数に絞っていない。静的読解で確認した。`grep -f .env x` は確認のままのはず。ただし E2 は実験役に拒否され、変更前との判定比較が取れていない。 | pretooluse_guard.py:~2304 | E2 は denied。静的読解 |

反証失敗（新規指摘なし）。探索した仮説:
- 表の文字の誤り。値を取らない文字を値ありとして、後ろの文字を読まなくなる。
- `_getopt` の `--` の扱い、`-` 単体、まとめ書き。
- python の読み終わりが他のコマンドに広がっていないか。
- 秘密のファイルを探す `paths` を位置引数に絞っていないか。
- 止めるべき形の一覧（47 件）で、変更前より弱い判定が出る形があるか。E3 は 0 件。

E2 は拒否されたため、個別のコマンドで変更前と作業ツリーの判定を並べて比べる実験はできていない。V3 のうち、TC-10（既存テスト全件）は E3 の対象外で、実験では確かめていない。

> ITEM: V1 RESULT=read
> ITEM: V3 RESULT=experiment EXP=P1-E3
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I463] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| — | — | 新規指摘なし。V2 の読み方はすべて期待どおり。 | pretooluse_guard.py:1887-1918 | P2-E2 |

反証失敗（新規指摘なし）。

P2-E2 で `_getopt` の戻り値を直接確かめた結果は次のとおり。
- **python の読み終わり**:
  - `python /tmp/e.py -xcfoo` は、スクリプト名で読み終え、後ろの `-xcfoo` を位置引数にした。TC-01 の想定どおり。
  - `-m pytest -xcfoo` は、`-m` の値で読み終え、`-xcfoo` を位置引数にした。
  - `-Wignore /tmp/e.py -c x` は、スクリプト名の後ろの `-c` を位置引数にした。
  - `python - -c x` は、`-` を位置引数にして読み終えた。
  - `python -- e.py -c x` と `python -B -- -c x` は、`--` の後ろを位置引数にした。
- **psql などの位置引数の後ろ**:
  - `psql mydb -c DELETE` は、位置引数の後ろの `-c` を読んだ（`-c` の値は `DELETE`、位置引数は `mydb`）。
  - `psql -- mydb -c D` は、`--` の後ろを位置引数にした。
  - `psql - -c D` は、`-` 単体を位置引数にし、後ろの `-c` は読んだ。
  - `psql -1c D` は、`-1` を値なしで読み、`-c` に値 `D` を付けた。
  - `sed s/a/b/ x -i` と `cp /tmp/a x -v` は、位置引数の後ろのオプションを読んだ。

探索した仮説:
- 停止条件 `opts[-1][0][1:] in "cm"` が部分文字列として誤判定しないか（長いオプションの名前は `-` で始まり、`cm` の部分文字列にならないため該当しない）。
- `--` と `-` 単体の扱い。
- 失敗の注入（FG）が、置き換え元の出現回数を 1 回に固定しているため、置き換えそこねて見かけ上合格する形になっていないか。

> ITEM: V2 RESULT=experiment EXP=P2-E2
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I463] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| — | — | 反証失敗（新規指摘なし） | — | 静的読解 |

反証失敗（新規指摘なし）。探索した仮説:
- **読む指定（F6）**: `_OPT_READ_PATH` は読む指定の 7 語（rootdir・confcutdir・cov・cov-config・ignore・ignore-glob・deselect）だけを除く。先読みの `=` で終わるため、`--cov-report=/x` は除かれず、書き出し先の確認は残る。
- **sed と cp の普通の形**: コードレビュー台帳 F1〜F6 と、同梱の差分の記述（`sed -e's/print/log/'`、`cp -vt`、`mv -S`）を読んだ。普通の書き方で新しく誤停止する形は、読んだ範囲では見つからなかった。
- **TC-11**: 作業記録での判定比較は、コードレビュー記録に「新しく確認・停止 0 件・異常終了 0 件」と書かれている。ただし、これは記録上の値だ。私は再実行できていない。
- **台帳 F1（python の長いオプション）**: この変更で、確認だった形が通る後退になる。ただし、わざと書く形で、脅威モデルの範囲外（Low 扱い）だ。V4 の判定には関係しない。

V4 は、読む指定・読むだけの sed・cp の形が通る方向にしか変わっておらず、TC-11 の記録も 1% 以内だった。読んで確かめた範囲では問題を見つけていない。

> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 1
REVIEWED_COMMIT: e377602efa82755260c378db93b1fe6617b28cfd
ROUNDS: 1
VERDICT: HIGH
