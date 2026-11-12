# 敵対的レビュー [I463]（別プロセス・2026-11-12 13:57）

- 見た範囲: e377602efa82755260c378db93b1fe6617b28cfd...8cc7153bf47fd97dd16b5fb6ce51debd91b96567
- 所要時間: 185 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- 一覧: docs/plans/open/plan_I463.md の「## 必ず確かめる項目」（4 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 2 | 実験必須 | 実験で確認 | P2-E3=ran  | 確認済み（実験） |
| V3 | 1 | 実験必須 | 実験で確認 | P1-E1=ran  | 確認済み（実験） |
| V4 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 172 秒 | 1 | 0 | $0.3726 | ― | ― | ― |
| 2 | 報告あり | 182 秒 | 1 | 0 | $0.3774 | ― | ― | ― |
| 3 | 報告あり | 11 秒 | 0 | 0 | $0.1680 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; for t in test_guard_must_stop_cases test_i463_guard_optspec test_i454_guard_env_writes test_i444_guard_gaps test_i200_guard_narrowing test_pretooluse_guard_matrix test_guard_bash_oracle; do echo "== $t"; timeout 60 bash scripts/claude/tests/$t.sh 2>&1 | tail -4; echo "exit=${PIPESTATUS[0]}"; done'
~~~
出力の先頭:
~~~
is_error=false
== test_guard_must_stop_cases
  [通す] echo hi（基準 pass）
FAIL: 止めるべき形のうち 1 件が後退・素通し・異常終了
PASS 09c
pass=3 fail=0
exit=0
== test_i463_guard_optspec
PASS 08b
PASS 08c
PASS 08d
pass=46 fail=0
exit=0
== test_i454_guard_env_writes
PASS FG-07c
PASS FG-07d
PASS FG-07b
pass=59 fail=0
exit=0
== test_i444_guard_gaps
PASS 05a
PASS 05b
PASS FG-05
pass=64 fail=0
exit=0
== test_i200_guard_narrowing
PASS 05f
PASS 05g
PASS 05h
pass=75 fail=0
exit=0
== test_pretooluse_guard_matrix
---
pass=391 fail=0（13 操作 × (29 書き方 + 行の継続 1) + 偽合格の防止 1）
exit=0
== test_guard_bash_oracle
Command did not complete within its 120s timeout and was moved to the background (ID: btic6hmbh). Output is being written to: /tmp/claude-1000/-mnt-c-app-study-app-multitenant--claude-worktrees-harness-1/8951b303-d24e-4634-96ce-e4b0cbedd107/tasks/btic6hmbh.output. You will be notified when it completes. If it is still running after 10m in the background, it will be stopped and you will be notified. It is running now: do not start a second copy while it runs. If it is no longer needed, stop it with TaskStop. To check interim output, use Read on that file path.
~~~

### 観点 2

#### P2-E3: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 60 python3 -c "
import importlib.util as u
s=u.spec_from_file_location(\"g\",\"scripts/claude/hooks/pretooluse_guard.py\");m=u.module_from_spec(s);s.loader.exec_module(m)
g=m._getopt
for cmd,a in [(\"python\",[\"/tmp/e.py\",\"-xcfoo\"]),(\"python\",[\"-m\",\"pytest\",\"-xcfoo\"]),(\"python\",[\"-\",\"-c\",\"x\"]),(\"python\",[\"--\",\"e.py\",\"-c\",\"x\"]),(\"python\",[\"--check-hash-based-pycs\",\"default\",\"-c\",\"x\"]),(\"python\",[\"-Wignore\",\"/tmp/e.py\",\"-c\",\"x\"]),(\"psql\",[\"mydb\",\"-c\",\"DELETE\"]),(\"psql\",[\"--\",\"mydb\",\"-c\",\"D\"]),(\"psql\",[\"-\",\"-c\",\"D\"]),(\"sed\",[\"s/a/b/\",\"x\",\"-i\"])]:
    print(cmd,a,g(cmd,a))
"'
~~~
出力の先頭:
~~~
is_error=false
python ['/tmp/e.py', '-xcfoo'] ([], ['/tmp/e.py', '-xcfoo'])
python ['-m', 'pytest', '-xcfoo'] ([('-m', 'pytest')], ['-xcfoo'])
python ['-', '-c', 'x'] ([], ['-', '-c', 'x'])
python ['--', 'e.py', '-c', 'x'] ([], ['e.py', '-c', 'x'])
python ['--check-hash-based-pycs', 'default', '-c', 'x'] ([('--check-hash-based-pycs', 'default'), ('-c', 'x')], [])
python ['-Wignore', '/tmp/e.py', '-c', 'x'] ([('-W', 'ignore')], ['/tmp/e.py', '-c', 'x'])
psql ['mydb', '-c', 'DELETE'] ([('-c', 'DELETE')], ['mydb'])
psql ['--', 'mydb', '-c', 'D'] ([], ['mydb', '-c', 'D'])
psql ['-', '-c', 'D'] ([('-c', 'D')], ['-'])
sed ['s/a/b/', 'x', '-i'] ([('-i', None)], ['s/a/b/', 'x'])
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I463] ── 観点: 1. ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | V1 | 差分の範囲で表に足したのは 2 点。`python` の `--check-hash-based-pycs`（値を取る長いオプション）と、`script` の `-t`（`-t[<file>]`、くっつけたときだけ値を取る）。どちらも `--help` や Python の文書と矛盾しない。値を取らない文字を値ありに足した箇所は見つからなかった。 | pretooluse_guard.py:1864, 1876 | 静的読解 |
| Low | V1 | TC-13 は短いオプションの文字だけを突き合わせる。長いオプション、psql、python は対象外。コードレビューの F8 と同じ指摘なので新規には数えない。 | test_i463_optspec_help.sh | 既知 F8 |
| Info | V3 | 止めるべき形の一覧（TC-09）、I454、I444、I200、見張りの組み合わせ表は、実測でいずれも fail=0・exit 0 だった。`must_stop_cases` の出力に出る FAIL は、失敗の注入（09b・09c）が意図どおり検知した表示で、本体の判定は pass=3 fail=0。`test_guard_bash_oracle` は 120 秒で背景に回り、結果が届いていない。 | P1-E1 | P1-E1（oracle のみ未確認） |

反証失敗（新規指摘なし）。探索した仮説:
- 表の文字の誤りで、後ろの文字を読まなくなる。
- `script -t` の optional が次の語を食う。
- 止めるべき形の後退。
- 既存の見張りのテストの後退。
- `paths` を位置引数に絞る変更。差分に無い。

`test_guard_bash_oracle` は時間切れで未確認。TC-10 のうちこの 1 本だけが実験で確かめられていない。ほかの 4 本は実験で exit 0。

> ITEM: V1 RESULT=read
> ITEM: V3 RESULT=experiment EXP=P1-E1
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I463] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| — | — | 新規指摘なし。V2 の読み方はすべて期待どおり。 | pretooluse_guard.py:1887-1918 | P2-E3 |

反証失敗（新規指摘なし）。探索した仮説と P2-E3 で `_getopt` の戻り値を確かめた結果は次のとおり。

- **python の読み終わり**
  - `/tmp/e.py -xcfoo` は、スクリプト名で読み終え、`-xcfoo` を位置引数にした。
  - `-m pytest -xcfoo` は、`-m` の値で読み終え、`-xcfoo` を位置引数にした。
  - `-Wignore /tmp/e.py -c x` は、スクリプト名より後ろの `-c` を位置引数にした。
  - `- -c x` は、`-` を位置引数にして読み終えた。
  - `-- e.py -c x` は、`--` より後ろを位置引数にした。
- **値を取る長いオプション**
  - `--check-hash-based-pycs default -c x` は、`default` を値として取り、後ろの `-c x` を読んだ。コードレビュー F1 の後退は直っている。
  - 01g は、この表の行を外すと `-c` を読まなくなって ASK でなく通す(0)になる。実装をなぞっただけのテストではなく、実際に落ちる。
- **psql など python 以外のコマンド**
  - `psql mydb -c DELETE` は、位置引数より後ろの `-c` を読んだ（`-c` の値は `DELETE`、位置引数は `mydb`）。
  - `psql -- mydb -c D` は、`--` より後ろを位置引数にした。
  - `psql - -c D` は、`-` 単体を位置引数にし、後ろの `-c` は読んだ。
  - `sed s/a/b/ x -i` は、位置引数より後ろの `-i` を読んだ。
- 既知の F9（FG-13 が exit 1 だけを見る）は再報告しない。

> ITEM: V2 RESULT=experiment EXP=P2-E3
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I463] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| — | — | 反証失敗（新規指摘なし） | — | 静的読解 |

反証失敗（新規指摘なし）。探索した仮説:
- **V4 の通る側**: 今回の差分は、`_OPTSPEC` の python に `--check-hash-based-pycs` を足し、script に `-t` を任意値として足しただけだ。読む指定（`--cov=` など）、読むだけの sed、cp の形が通る方向は変わっていない。
- **TC-11（作業記録での判定比較）**: 差分内の記録（`docs/tests/open/I463_auto_test.md`）では、変更前の実装の時点で新しく確認・停止が 0 件、異常終了が 0 件だった。今回の差分は表への追加 2 件だけで、新しく確認が増える向きの変更ではない。`--check-hash-based-pycs` を足したことで、確認だった形が通る側に動く場合がある。TC-11 は今回の差分の後では再実行されていない。ただし変更が小さく、「新しく確認・停止」は増えない向きだ。
- **既知 findings との重複**: 台帳の F7（`_cmd_external` の `first`）、F8（TC-13 が長いオプションを対象にしない）、F9（FG-13 が exit 1 だけを見る）は再報告しない。
- **新しいテスト TC-13 の誤停止リスク**: TC-13 は `--help` と突き合わせるだけで、見張り本体の判定には影響しない。`script -t` を任意値に足したことで、`script -t` に続く語を値として読まなくなる方向に変わるが、止める側の判定が減る形ではない。

V4 は、通常の操作が通ること、新しい誤停止が増えないことを、差分と記録から読んで確かめた。実験では確かめていない。

> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 8cc7153bf47fd97dd16b5fb6ce51debd91b96567
ROUNDS: 1
VERDICT: OK
