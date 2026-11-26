# 敵対的レビュー [I593]（別プロセス・2026-11-27 01:55）

- 見た範囲: origin/develop...5e3e3917791d84bf24c86a332517864e042b22e4
- 所要時間: 65 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: 確かめていない（ブランチに backend/ の変更なし）
- 一覧: docs/plans/open/plan_I593.md の「## 必ず確かめる項目」（6 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 2 | 読んで可 | 実験で確認 | P2-E1=ran  | 確認済み（実験） |
| V4 | 2 | 読んで可 | 実験で確認 | P2-E1=ran  | 確認済み（実験） |
| V5 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 23 秒 | 0 | 0 | $0.2855 | ― | ― | ― |
| 2 | 報告あり | 64 秒 | 1 | 0 | $0.7192 | ― | ― | ― |
| 3 | 報告あり | 25 秒 | 0 | 0 | $0.2690 | ― | ― | ― |

## 実験

### 観点 2

#### P2-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 120 bash scripts/claude/tests/test_i593_review_from_base.sh 2>&1 | grep -E "FG-TC-07|TC-07|FAIL|^PASS.*TC-0[1-2]" | head -40'
~~~
出力の先頭:
~~~
is_error=false
PASS TC-01 審査の部品のパスで YES・ほかのスキル・似た名前・審査の入口と定義で NO
PASS FG-TC-01 集合から .claude/hooks/*| を外すと不合格
PASS FG-TC-01 集合から .claude/skills/review-gate/*| を外すと不合格
PASS FG-TC-01 集合から .claude/skills/test-gate/*| を外すと不合格
PASS FG-TC-01 集合から .claude/skills/fix-loop/*| を外すと不合格
PASS FG-TC-01 集合から .claude/skills/plan-review/*| を外すと不合格
PASS FG-TC-01 集合から |scripts/claude/gate-check.sh) を外すと不合格
PASS FG-TC-01 path_risk_trigger を guard だけにすると不合格
PASS TC-02 審査の部品の集合が code-reviewer.md・plan-reviewer.md・review-rules.md の行と一致
PASS FG-TC-02 .claude/agents/code-reviewer.md から scripts/claude/gate-check.sh を消すと不合格
PASS FG-TC-02 .claude/agents/plan-reviewer.md から scripts/claude/gate-check.sh を消すと不合格
PASS FG-TC-02 docs/runbooks/review-rules.md から scripts/claude/gate-check.sh を消すと不合格
PASS TC-07 消した・数の減った・スキップを足したテストを拾い、テストでないファイルと並べ替えは拾わない
PASS TC-07 何も無いときは なし
PASS FG-TC-07 .only の目印を外すと不合格
PASS FG-TC-07 消したファイルを見ないと不合格
PASS FG-TC-07 テストのファイルの判定を全部にすると views.py が出て不合格
PASS FG-TC-07 確かめの数を見ないと不合格
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I593] ── 観点: 1. ロジック回避・実機 repro

## findings
反証失敗（新規指摘なし）。

探索した仮説:
- **V1: 写しに新しい仕組みがあるのに、ブランチの定義が使われる。**
  - `unreviewed.py` の `run()`（:323〜326）は、`name in REVIEW_ENTRIES` かつ写しに `reviewer-agents-lib.sh` があるときだけ `hit` を空にします。
  - 入口は写しの `entry` で動くので、`reviewer-agents-lib.sh` も写しの版で読まれます。
  - `reviewer_agent_args` は定義を `$src/.claude/agents/<名前>.md`（`src` は写しの最上位）から読み、`--agents` の JSON で渡します。作業ツリーの定義は読みません。
  - 決まりの参照も `review-rules.md` から写しの版に置き換え、`--add-dir "$src"` を付けます。
  - 名前は `[a-z0-9-]` だけを通すので、パスをたどる入力はできません。
- **V1: 変換が定義ファイルの前書きを受け付けない。**
  - 現行の 6 本の定義の前書きは `name`・`description`・`tools`・`model` の 4 つだけです。確かめたのは `adversarial-reviewer`・`code-reviewer`・`fix-diagnosis-reviewer`・`issue-reviewer` で、残りの 2 本の前書きは未確認です。
  - 変換は fail-closed なので、定義の変換に失敗しても作業ツリーの定義に戻ることはありません。
- **V2: 75 の条件が広すぎる、または狭すぎる。**
  - 75 になるのは、写しを作れない・入口が写しに無い・部品の差を確かめられない・写しに `reviewer-agents-lib.sh` が無いときです。
  - 作業ツリーから動いたときは `reviewer_from_snapshot` が偽になり、高リスクが YES になります。
  - 写しから動くときは `.complete` があり、かつ最上位が `git rev-parse --show-toplevel` と違います。偽の `.complete` を作る行為は意図的な回避なので、Low 以下として扱います。
  - 判断の根拠はすべて静的読解で、実験は流していません。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I593] ── 観点: テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。探索した仮説:
- V3: 集合を 1 つ外したときの TC-01 と TC-02 の FG（失敗の注入）が、実際に落ちるかを確かめました。P2-E1 では、TC-01 の 6 件と TC-02 の 3 件の FG がすべて PASS でした。YES と NO のパスの両側が検証されています。
- V4: 疑いが 1 件ありましたが、実験で外れました。js の SKIP 正規表現には第 3 の枝 `.only(` があり、`FG-TC-07 .only` が空振りで赤になると疑いました。P2-E1 では PASS でした。FG は期待どおり落ちています。
  - 落ちる理由が「`.only` を外したから」なのか、別の副作用なのかは確かめていません。ただし FG は落ちているので、false-green ではありません。
- V4: TC-07 の FG は、4 種類の拾う対象を 1 つずつ外した形になっています。外す対象は、skip の目印、deleted、テストのファイルの判定、fewer-checks です。テストでないファイル `views.py` の `skip` と、テストの並べ替え `test_r.py` が拾われないことも、同じ TC-07 の中で確かめています。結果は PASS でした。
- TC-09 の FG は、読んだだけで、実験では確かめていません。今回の実験の出力は先頭 18 行だけで、TC-09 は含まれていません。TC-09 は担当の項目に入っていません。

> ITEM: V3 RESULT=experiment EXP=P2-E1
> ITEM: V4 RESULT=experiment EXP=P2-E1
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I593] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。実験はしていません。担当の V5・V6 はどちらも「読んで可」の項目で、読んで確かめました。

探索した仮説:
- **V5（gate-check.sh の判定の関数）**
  - `gate-check.sh:29-41` は、`GATE_CHECK_LIB` が無いとき `git merge-base GATE_BASE HEAD` で BASE を求め、`git show BASE:scripts/claude/code-review.sh` を一時ファイルに書き出して `source` します。
  - 取れなければ `fail base` で止まります。
  - したがって、ブランチの `code-review.sh` で高リスク判定を NO に書き換えても、gate-check には効きません。
  - gate-check.sh と `.claude/hooks/*` 自体は `review_mechanism_trigger` の集合に入っています。そのためブランチで gate-check を書き換えた PR も高リスクになります。
  - 懸念として、新しい gate-check が BASE の古い `code-review.sh` に無い関数を呼ぶと止まります。ただし止まる側に倒れるので Critical/High ではありません。計画書 R1 の「2 段で変える」で扱われています。
- **V6（定義の変換）**
  - `reviewer-agents-lib.sh:30-63` は、次のとき `sys.exit` で非 0 になります。
    - 前書きが無い、または閉じていない。
    - `name`・`description`・`tools`・`model` 以外の鍵、重複した鍵、インデントされた行、`:` の無い行がある。
    - `name` がファイル名と違う。
    - `description` が無い。
  - 定義ファイルが無いときは `reviewer_agent_args` が return 2 になり、古い写しの案内も出ます。
  - 写しから動くときは、本文の `docs/runbooks/review-rules.md` を写しの版のパスへ置き換えます。写しにその決まりが無ければ止まります（fail-closed）。
  - 名前は `[a-z0-9-]` だけを受け付けるので、パスをたどる入力はできません。
  - Python は `-I` で起動します。
  - 複数行の YAML リストなどの `tools` は崩れた形として止まります。止まる側に倒れるので問題ではありません。
- **脅威モデルの穴（普通の書き方の事故）**
  - 写しに新しい仕組みが無い古い BASE では、`unreviewed.py` が 75 に倒れます。
  - `reviewer_from_snapshot` が偽なら、`reviewer_source_risk` で高リスクが YES になります。
  - 新しい穴は見つかりませんでした。

> ITEM: V5 RESULT=read
> ITEM: V6 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 5e3e3917791d84bf24c86a332517864e042b22e4
ROUNDS: 1
VERDICT: OK
