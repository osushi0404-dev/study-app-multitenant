# 敵対的レビュー [I615]（別プロセス・2026-11-24 02:43）

- 見た範囲: origin/develop...4a76cfea378895f5280c06a68d721af786e78eed
- 所要時間: 121 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: 確かめていない（ブランチに backend/ の変更なし）
- 一覧: docs/plans/open/plan_I615.md の「## 必ず確かめる項目」（6 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 実験で確認 | P1-E2=ran  | 確認済み（実験） |
| V2 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 119 秒 | 1 | 0 | $0.9763 | ― | ― | ― |
| 2 | 報告あり | 43 秒 | 0 | 0 | $0.3720 | ― | ― | ― |
| 3 | 報告あり | 23 秒 | 0 | 0 | $0.2743 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; for c in "git merge --ff-only origin/develop 2>&1 | tail -2" "git switch x" "git checkout main && git pull" "git status | head" "git pull --ff-only && ls" "git -C . merge x | tail" "time git merge x | tail" "(git merge x)" "git merge x; echo done" "git stash push -m \"<wip>\"" "DANGER_OK=1 git checkout x | tail" "git pull origin develop 2>/dev/null"; do printf "%s => " "$c"; python3 -c "import json,sys;print(json.dumps({\"tool_name\":\"Bash\",\"tool_input\":{\"command\":sys.argv[1]}}))" "$c" | timeout 60 python3 -I scripts/claude/hooks/pretooluse_guard.py >/dev/null 2>&1; echo "exit=$?"; done'
~~~
出力の先頭:
~~~
is_error=false
git merge --ff-only origin/develop 2>&1 | tail -2 => exit=2
git switch x => exit=0
git checkout main && git pull => exit=0
git status | head => exit=0
git pull --ff-only && ls => exit=2
git -C . merge x | tail => exit=2
time git merge x | tail => exit=2
(git merge x) => exit=2
git merge x; echo done => exit=2
git stash push -m "<wip>" => exit=2
DANGER_OK=1 git checkout x | tail => exit=0
git pull origin develop 2>/dev/null => exit=2
~~~

#### P1-E2: 実行した
~~~
bash -c 'ulimit -v 2097152; set -e; T=$(mktemp -d); export HOME=$T/home; mkdir -p $HOME $T/r; cd $T/r; git init -q -b develop; git config user.email a@b; git config user.name a; mkdir -p scripts/claude/tests .claude/hooks .claude/agents; printf "#!/bin/bash\n. \"\$(dirname \"\${BASH_SOURCE[0]}\")/review-process-lib.sh\"\necho ran-entry\n" > scripts/claude/code-review.sh; seq 1 40 | sed "s/^/# line /" > scripts/claude/review-process-lib.sh; echo "echo lib" >> scripts/claude/review-process-lib.sh; cp "'"$PWD"'"/.claude/hooks/unreviewed.py "'"$PWD"'"/.claude/hooks/reviewed-hook.sh .claude/hooks/; git add -A; git commit -qm base; git update-ref refs/remotes/origin/develop HEAD; git checkout -qb feat; git mv scripts/claude/review-process-lib.sh scripts/claude/tests/lib.sh; echo "# changed" >> scripts/claude/tests/lib.sh; git add -A; git commit -qm mv; env -u SANDBOX_RUNTIME timeout 60 python3 -I .claude/hooks/unreviewed.py run code-review.sh; echo "exit=$?"'
~~~
出力の先頭:
~~~
is_error=false
lib
ran-entry
exit=0
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I615] ── 観点: ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Medium | V1 | 部品を別の場所へ移した（リネーム）ブランチでも、入口の起動役は 75 で止まらず BASE の旧版を外で動かす。`git diff --name-only` はリネーム検出が効くと新名だけを出す。部品の判定は旧名で照合するので重ならず、AC2「部品を変えたら新しい版を `!` で流す」を取りこぼす。外で動くのは BASE の写しの中身なので、守りの穴ではない。直したレビューの道具が新しい版で流れないまま周が進むだけ | `.claude/hooks/unreviewed.py:114`（`_unreviewed_files` の diff）。修正案は `--no-renames` を付けること | P1-E2: `review-process-lib.sh` を `tests/lib.sh` に移して内容も変えたコミットで、`code-review.sh` が 75 にならず `lib`・`ran-entry` を出して exit=0 になった |
| Low | V5 | 単独の `git stash push -m "<wip>"` が exit=2 で止まる。引数の `<` を `_REDIRECT_RE.match(t)` が振り向けと取り違える。安全側の誤停止で、AC6「単独の形は通す」に反する。ただし計画で「引用符の中の `$(`・バッククォートは安全側」と決めた方針の延長にあたる | `pretooluse_guard.py:799` | P1-E1: `git stash push -m "<wip>" => exit=2` |
| Low | V1 | `git archive` は `.git/info/attributes` の `export-ignore` を読む。このファイルはサンドボックスから書けるので、写しから部品を落とせる。わざと回避する形なので脅威モデル外 | `reviewed-hook.sh` の `_reviewed_snapshot_make` | 静的読解のみ |

読みと実験で確かめて、問題がなかった点は次のとおり。
- V5: `git merge … 2>&1 | tail -2`・つなぎ・`-C`・`time`・かっこ・`;` は exit=2 で止まった。単独の `git switch x`・git どうしのつなぎ・`git status | head`・`DANGER_OK=1` の前置きは exit=0 で通った（P1-E1）。
- V1: 入口 16 本と部品は、作業ツリーの `scripts/claude/` を動かす箇所を `fix-diagnosis-review.sh` の 1 か所しか持たない。この 1 か所は今回の差分で直っている。
- V2: 基準が無い場合と写しを作れない場合は、`reviewed_snapshot` が 3 か 4 を返す。起動役はこれを 75 にし、作業ツリーへは倒れない。
- V3: `_reviewed_snapshot_make` から `rm -rf "$snap"` は消えている。

> ITEM: V1 RESULT=experiment EXP=P1-E2
> ITEM: V2 RESULT=read
> ITEM: V3 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I615] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | false-green | FG `fg_no_parts` は、ファイル名のたどりとレビュー役のたどりを 1 つの FG でまとめて外している。片方だけが壊れたときの検出は、FG ではなく TC-02 の 3 つの PART_SETUPS（入口・部品ライブラリ・レビュー役 md）に頼っている。TC-02 本体が各部品を個別に書き換えるので実害は小さい。 | scripts/claude/tests/i599_cases.py:594-597 | 静的読解 |
| Low | 設計 | `all(part_cases(...))` と `all(unrelated_cases(...))` は、最初の失敗で止まるとジェネレータの後片付け（`reset --hard`・`undo`）が走らない。本物の `r` では TC-02 が合格する限り起きない。失敗時だけ後続の検査に影響する。FG 用の使い捨てリポジトリでは問題ない。 | i599_cases.py:298-309, 311-314 | 静的読解 |

V4 の確認結果（実験なし。読んで確かめた）:
- **印の出どころ**: TC-01 の印は `review-process-lib.sh` の `mark_it` が `"V1 ${BASH_SOURCE[0]}"` で書く（60 行目）。期待値 `lib_mark` は `snapdir(root)/scripts/claude/review-process-lib.sh` の完全一致（243-244 行目）。作業ツリーの部品や入口が動くと、印のパスが写しのパスと違うので落ちる。`FG TC-I615-01`（`SCRIPTS + name` で作業ツリーを動かす版）がこの区別を確かめている。TC-02 は `printf EVIL` の印の有無（`got_ is None`）と終了コード 75 で見ており、書き換えた入口・部品が外で動けば落ちる。
- **「置き換えに失敗して合格」の防止**: `broken_judge` は `assert o in src`（78 行目）、`launcher_variant` は `assert old in lsrc`（417 行目）、`sessionstart` 用は 611 行目の `assert` で置き換え元の存在を確かめる。置き換え元が消えると FG は黙って合格せず、落ちる。
- **assert の無い置き換え**: `all_dash_i`・`same_defs` の FG は、置き換え元が無いと元の本体と同じ結果になる。その結果は `not <真>` で FG が不合格になる側に倒れる。false-green にはならない。

反証失敗（新規指摘なし）。探索した仮説: 印が作業ツリーの部品から書かれても通る tautology・FG の置き換え元の文字列が変わって無変更で合格する穴・TC-02 のジェネレータの状態漏れ・TC-04 と TC-05 の FG の有効性。

> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I615] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。探索した仮説:
- **見張りの判定の穴（V5）**: `pretooluse_guard.py` の 767〜804 行を読んで確かめた。
  - 止める条件は2つある。作業ツリーを書き換える git の命令があること（`_GIT_UPDATE_SUBS`。`stash list`・`stash show` は除く）。かつ、呼び出しが中で動く形であること。
  - 中で動く形とは、`$(`・バッククォート、`|`・`&`・`|&`、`>`・`<`・`&>` の振り向け、`git`・`gh`・`docker` 以外で始まる命令（`cd`・`timeout`・前置きの代入）のどれかである。
  - I586 の形 `git merge … 2>&1 | tail -2` は、`|` と `2>&1` の両方に当たるので止まる。
  - 単独の形と、`git` どうしの `&&`・`;` のつなぎは、`inside` が偽なので通る。
  - 読み取りだけの git は `subs` が空なので通る。
  - `DANGER_OK=1 ` で始まるコマンドは、判定の先頭で除外している。
  - 引用符の中の `$(`・バッククォートまで止まる点は、既知の F4（Low）で、計画で決めた安全側の仕様。
- **`-I` の抜け（V6）**: `scripts/claude/hooks/` 配下で `sys.executable` を使うのは `sessionstart_context.py:200` の 1 か所だけで、`-I` が付いている。ほかに python を起こす箇所は、grep で見つからなかった。`reviewed-hook.sh` の `exec python3 -I` は 3 か所とも `-I` 付き。
- **脅威モデル**: 変数・`eval` で組み立てた git による回避は、方針どおり Low で、件数に数えない。

> ITEM: V5 RESULT=read
> ITEM: V6 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 4a76cfea378895f5280c06a68d721af786e78eed
ROUNDS: 1
VERDICT: OK
