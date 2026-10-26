# 敵対的レビュー [I197]（別プロセス・2026-10-27 01:53）

- 見た範囲: origin/develop...20af2ae2e809f6acca15704fc2be00ed6cedd592
- 所要時間: 188 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- 一覧: docs/plans/open/plan_I197.md の「## 必ず確かめる項目」（11 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 実験必須 | 実験で確認 | P1-E1=ran  | 確認済み（実験） |
| V2 | 1 | 実験必須 | 実験で確認 | P1-E1=ran  | 確認済み（実験） |
| V3 | 1 | 実験必須 | 実験で確認 | P1-E1=ran  | 確認済み（実験） |
| V4 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 2 | 実験必須 | 実験で確認 | P2-E1=ran  | 確認済み（実験） |
| V6 | 2 | 読んで可 | 実験で確認 | P2-E2=ran  | 確認済み（実験） |
| V7 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V8 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V9 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V10 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V11 | 2 | 実験必須 | 実験で確認 | P2-E1=ran P2-E3=ran  | 確認済み（実験） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり（） | 151 秒 | 1 | 0 | $0.9119 | ― | ― | ― |
| 2 | 報告あり（） | 183 秒 | 1 | 0 | $1.1722 | ― | ― | ― |
| 3 | 報告あり（） | 64 秒 | 0 | 0 | $0.4489 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 280 bash scripts/claude/tests/test_i197_adversarial_process.sh 2>&1 | grep -E "^(PASS|FAIL) (A3|A4|A5|A8|FG-A5|FG-A8)|pass=|fail="'
~~~
出力の先頭:
~~~
is_error=false
PASS A3 実験が拒否 → HIGH
PASS A3 V1 は未検証
PASS A3 記録に「拒否された」とコマンド
PASS A4 違うコマンドを実行 → V1 未検証・HIGH
PASS A4 呼ばない → V1 未検証・HIGH
PASS A5 時間切れ → exit 3
PASS A5 ROUNDS: 0・VERDICT: HIGH
PASS A5 観点 3 の行に時間切れ・最後の Read・その結果・経過の秒
PASS A5 V3 は未検証（報告なし）
PASS A5 締め切り＋10 秒以内に終わる
PASS A8 実験役が作業ツリーを変える → HIGH
PASS A8 記録に scripts/x.txt・ファイルは残る
PASS FG-A5 報告なしで exit 3 にしないと A5 が不合格
PASS FG-A8 作業ツリーの比較を消すと A8 が不合格（OK が出る）
pass=115 fail=0
~~~

#### P1-E2: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 60 bash -c '"'"'
T=$(mktemp -d)
printf "false" > $T/cmd
printf "1\t%s\n" "{\"type\":\"assistant\",\"message\":{\"content\":[{\"type\":\"tool_use\",\"id\":\"t1\",\"name\":\"Bash\",\"input\":{\"command\":\"false\"}}]}}" > $T/log
printf "2\t%s\n" "{\"type\":\"user\",\"message\":{\"content\":[{\"type\":\"tool_result\",\"tool_use_id\":\"t1\",\"content\":\"bash: nosuchcmd: command not found\",\"is_error\":true}]}}" >> $T/log
printf "3\t%s\n" "{\"type\":\"result\",\"subtype\":\"success\",\"result\":\"DONE\",\"permission_denials\":[]}" >> $T/log
. scripts/claude/review-process-lib.sh
claude_log_ran $T/log $T/cmd; echo "rc=$?"
'"'"''
~~~
出力の先頭:
~~~
is_error=false
is_error=true
bash: nosuchcmd: command not foundrc=0
~~~

### 観点 2

#### P2-E1: 実行した
~~~
ulimit -v 2097152
echo "== TC-09"
timeout 200 bash scripts/claude/tests/test_i197_review_ledger.sh 2>&1 | grep -E '^(FAIL|---|pass=)'
echo "== TC-01"
timeout 250 bash scripts/claude/tests/test_i197_adversarial_process.sh 2>&1 | grep -E '^(FAIL|---|pass=)'
~~~
出力の先頭:
~~~
is_error=false
== TC-09
---
pass=64 fail=0
== TC-01
---
pass=115 fail=0
~~~

#### P2-E2: 実行した
~~~
ulimit -v 2097152
D=$(mktemp -d)
cp -r scripts "$D/"
sed -n '/^s1() {/,/^}/p' scripts/claude/tests/test_i197_adversarial_process.sh > "$D/s1fn.sh"
. "$D/s1fn.sh"
s1 "$D"/scripts/claude/*.sh >/dev/null 2>&1; echo "base=$?"
for spec in adversarial-review.sh:160 adversarial-review.sh:168 code-review.sh:148 code-review.sh:806 issue-review.sh:40 check-permission-prompt.sh:49 fix-review-lib.sh:82; do
  f=${spec%%:*}; n=${spec##*:}
  M=$(mktemp -d); cp "$D"/scripts/claude/*.sh "$M/"
  sed -i "${n}s/ --permission-prompts none//" "$M/$f"
  cmp -s "$M/$f" "$D/scripts/claude/$f" && echo "NOCHANGE $spec"
  s1 "$M"/*.sh >/dev/null 2>&1; echo "$spec rc=$?"
done
~~~
出力の先頭:
~~~
is_error=false
base=0
adversarial-review.sh:160 rc=1
adversarial-review.sh:168 rc=1
code-review.sh:148 rc=1
code-review.sh:806 rc=1
issue-review.sh:40 rc=1
check-permission-prompt.sh:49 rc=1
fix-review-lib.sh:82 rc=1
~~~

#### P2-E3: 実行した
~~~
ulimit -v 2097152
D=$(mktemp -d)
cp -r scripts .claude "$D/"
mut() {
  M=$(mktemp -d); cp -r "$D/scripts" "$D/.claude" "$M/"
  python3 -I - "$M/scripts/claude/code-review.sh" "$2" "$3" <<'PY'
import sys
p, old, new = sys.argv[1:4]
s = open(p, encoding="utf-8").read()
if old not in s:
    sys.exit("NOT FOUND: " + old)
open(p, "w", encoding="utf-8").write(s.replace(old, new))
PY
  echo "== $1"
  ( cd "$M" && git init -q && timeout 100 bash scripts/claude/tests/test_i197_review_ledger.sh 2>&1 | grep -E '^(FAIL|pass=)' | head -8 )
}
mut M6_scope_recompute 'st, old[2], "yes"' 'st, scope_of(path), "yes"'
mut M7_sec_drop '"yes" if "yes" in (sec, old[3]) else "no"' 'sec'
mut M1_medium_blocks 'RANK[sev] >= 2 and' 'RANK[sev] >= 1 and'
~~~
出力の先頭:
~~~
is_error=false
== M6_scope_recompute
FAIL FG-R15 振り直しを消すと R15 が不合格（F2 に合流して止まらない） expected=OK got=HIGH
pass=63 fail=1
== M7_sec_drop
pass=64 fail=0
== M1_medium_blocks
FAIL R13 ledger_blocking は止める指摘（F1・F3）だけを出す expected=F1,F3 got=F1,F3,F4
pass=63 fail=1
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I197] ── 観点: 1. ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Medium | 判定の抜け道 | 実験が失敗しただけ（`is_error=true`・command not found）でも、`claude_log_ran` は exit 0 を返して `ran` になる。`is_error` は出力に載せるだけで、判定には使わない。レビュー役が `RESULT=experiment EXP=...` と書けば、中身のない実行でも実験必須の項目が「確認済み（実験）」になる。拒否・未呼び出し・コマンドの書き換えは捕まえている。失敗した実行だけが抜ける。Critical/High にしない理由は、レビュー役が結果を読んで ITEM 行を書くこと、結果は記録に残ること、人が監査できることの 3 点。判定の自動化としては穴が残る。 | `review-process-lib.sh:139-141`、`adversarial-review.sh:276,322` | P1-E2: `rc=0`・`is_error=true` と `command not found` の出力。失敗したコマンドでも「実行した」扱いになる |
| Low | 検出範囲 | `check_worktree` は `git status` に見える変更だけを比べる。gitignore 対象のファイルへの書き込みは検出しない。 | `adversarial-review.sh:120-141` | 静的読解 |
| Low | 文言のずれ | SKILL 3-0 の説明は「最新の記録の `REVIEWED_COMMIT` から」。実装は `ROUNDS: 0` の記録を起点から外す。周回の数え方（ROUNDS の合計・行の無い記録は 1）は SKILL と一致している。 | `adversarial-review.sh:88-107` | 静的読解 |

探索した仮説: 実験の「ran」判定の偽陽性（失敗した実行）／作業ツリー比較の抜け（gitignore）／報告なし・時間切れの扱い／周回数と起点の決め方。

V1・V2・V3 は P1-E1 で確かめた。スタブ claude で実行して、A3（拒否）・A4（違うコマンド・呼ばない）は未検証になり HIGH、A5（時間切れ）は exit 3・`ROUNDS: 0`・HIGH で、最後のツール呼び出し・結果・経過が記録に出た。A8（作業ツリーの変更）は HIGH になり、ファイルは残った。FG の壊した写しでは A5・A8 が落ちた。全体は pass=115 fail=0。

> ITEM: V1 RESULT=experiment EXP=P1-E1
> ITEM: V2 RESULT=experiment EXP=P1-E1
> ITEM: V3 RESULT=experiment EXP=P1-E1
> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I197] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Medium | FG 抜け | `ledger_update` の「既存の指摘の SECURITY は yes を持ち越す」の部分（`"yes" if "yes" in (sec, old[3]) else "no"`）を `sec` だけに変えても、TC-09 は 64 件すべて合格する。範囲の外で SECURITY=yes の Blocker が台帳にあるとき、次の周で `SECURITY=no` と書き直されるだけで止まらなくなる。この持ち越しを守るテストが無い。実際に起きるのは、セキュリティ指摘を書き直した周に限られる。止める条件は「普通の書き方の事故」の範囲なので Medium とする | scripts/claude/code-review.sh:562 | P2-E3 の M7_sec_drop: `pass=64 fail=0`（落ちなかった） |
| Low | FG の守り方 | SCOPE を前のまま持ち越す行（`st, old[2],`）を `scope_of(path)` に戻すと、落ちたのは FG-R15 の 1 件だけだった。R5 や R6 の本体は落ちなかった。持ち越しを直接守るテストは無く、FG-R15 が副次的に守っている。いまは落ちるので false-green ではない。ただし FG-R15 を直すと穴になる | scripts/claude/code-review.sh:562 | P2-E3 の M6_scope_recompute: `FG-R15 … expected=OK got=HIGH`・`pass=63 fail=1` |

探索した仮説:
- TC-01・TC-09 の現状の合否: 現状は全合格（TC-09 は pass=64、TC-01 は pass=115。P2-E1）。
- TC-01 の判定の要を壊す FG（FG-A2・A3・A5・A8・A9・A10・A14）: 構造を読み、実行すると全部合格する。壊した写しで A が落ちる作りになっている。
- S1（`--permission-prompts none` の有無）: 7 か所を 1 つずつ外した写しで、すべて rc=1 で落ちた（P2-E2）。FG-S1 に無い adversarial-review.sh の `run_step` 行や `check-permission-prompt.sh` でも落ちる。
- 台帳の変異: Medium を止める側に倒す変異（M1）は R13 が落とす。

> ITEM: V5 RESULT=experiment EXP=P2-E1
> ITEM: V6 RESULT=experiment EXP=P2-E2
> ITEM: V11 RESULT=experiment EXP=P2-E1,P2-E3
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I197] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Medium | V7 AC の対応漏れ | AC2（方式の比較の記録）と AC9（公式の道具を土台にする根拠）に、対応する TC も手動テストの行もない。auto_test の TC-01〜09 と S1〜S6 は、どちらも文書の中身を見ていない。S4 が見るのは review-rules.md の節の見出しなど（AC1）だけ。manual No.3 は SKILL の §3 と計画の §4.5 を突き合わせるだけで、§4.2 の比較表と §9 の根拠は見ない。AC は「§4.2・§9」と書くだけで済ませている。 | docs/tests/open/I197_auto_test.md:15-23,67-73、I197_manual_test.md:9、plan_I197.md §2 の AC2・AC9 | 静的読解。両ファイルを Grep と Read で確認した |
| Medium | V9 実験役の範囲 | 実験役は `--settings .claude/settings.json` を読み込み、`--permission-mode auto` で動く。その settings.json の allow には `Bash(git push)`、`Bash(git push *)`、`Bash(git branch *)`、`Bash(git checkout *)` がある。deny が止めるのは develop・main 宛てと `--force` だけ。レビュー役が `git push origin <feature>` や `git branch -D` を実験案に書いても、スクリプトは実験のコマンドを何もふるいにかけない。拒否されず、リモートの feature ブランチが更新される。作業ツリーの比較（`worktree_state`）は `git status` ベースなので、push、ブランチの削除、gitignore されたファイルの変更や削除は検出できない（HEAD とブランチ名の変化だけ見る）。禁止はレビュー役への文言のみ。実機の確認はしていない。 | adversarial-review.sh:120-141,165-172、.claude/settings.json:33-43,114-130 | 静的読解。実験で確かめる前にこの観点の持ち時間を使い切った |
| Low | V8 すり替え | 無害化は行頭（空白のみ可）の語に限る。判定を読む側は行頭に固定した `grep -E` と最後の行だけを使うので、本文経由のすり替えは見つからなかった。ただし `ITEM:` を読む `item_line` は、持ち主の観点のレビュー役の本文を信じる。差分に埋め込まれた文章でレビュー役が誘導されると、`RESULT=read` を書かせることはできる。実験必須の項目は read だと未検証になる。読んで可の項目だけが影響を受ける。 | adversarial-review.sh:204-208、code-review.sh:163-166 | 静的読解 |

V10 は問題なし。入力に変更ファイルの一覧、差分、100KB で切った注記が入り（adversarial-review.sh:228-229,386-395）、TC-01 の A12 が固定している。

反証失敗の範囲: V8 と V10 では新規の Critical/High を見つけられなかった。V7 と V9 は Medium までにとどまる。探索した仮説は、AC と TC の対応表、本文からのすり替え（無害化とアンカー）、実験役の権限と作業ツリー比較の穴、差分の入力の 4 つ。

> ITEM: V7 RESULT=read
> ITEM: V8 RESULT=read
> ITEM: V9 RESULT=read
> ITEM: V10 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 20af2ae2e809f6acca15704fc2be00ed6cedd592
ROUNDS: 1
VERDICT: OK
