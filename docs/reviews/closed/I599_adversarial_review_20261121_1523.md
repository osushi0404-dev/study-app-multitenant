# 敵対的レビュー [I599]（別プロセス・2026-11-21 15:23）

- 見た範囲: origin/develop...4bcf6423ecdff4620844227561c595f7750b7722
- 所要時間: 235 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: 確かめていない（ブランチに backend/ の変更なし）
- 一覧: docs/plans/open/plan_I599.md の「## 必ず確かめる項目」（6 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 2 | 読んで可 | 実験で確認 | P2-E1=ran  | 確認済み（実験） |
| V5 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 1 | 実験必須 | 未実施 | ― | 未検証（未実施） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 217 秒 | 1 | 0 | $0.5215 | ― | ― | ― |
| 2 | 報告あり | 234 秒 | 1 | 0 | $0.7529 | ― | ― | ― |
| 3 | 報告あり | 35 秒 | 0 | 0 | $0.2989 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 実行した
~~~
bash scripts/claude/test-session.sh "Bash ツールで次のコマンドを単体で 1 回だけ実行し、終了コードと出力を一字も変えずに報告して: bash scripts/claude/issue-source.sh gh-number I599" --model haiku --permission-mode auto --permission-prompts none --setting-sources user --settings .claude/settings.json
~~~
出力の先頭:
~~~
is_error=false
Permission allow rule "Read(*)" adds nothing to Read's default, which already runs without asking in the working directories. "Read" alone allows every path. Older versions of Claude Code treat "Read(*)" as "Read", and this version will too if Anthropic turns this change off.
Permission allow rule "Grep(*)" adds nothing to Grep's default, which already runs without asking in the working directories. "Grep" alone allows every path. Older versions of Claude Code treat "Grep(*)" as "Grep", and this version will too if Anthropic turns this change off.
Permission allow rule "Glob(*)" adds nothing to Glob's default, which already runs without asking in the working directories. "Glob" alone allows every path. Older versions of Claude Code treat "Glob(*)" as "Glob", and this version will too if Anthropic turns this change off.
<sandbox_violations>
deny network-outbound api.anthropic.com:443 (host is not on the allow list)
deny network-outbound api.anthropic.com:443 (host is not on the allow list)
deny network-outbound api.anthropic.com:443 (host is not on the allow list)
deny network-outbound api.anthropic.com:443 (host is not on the allow list)
deny network-outbound api.anthropic.com:443 (host is not on the allow list)
deny network-outbound api.github.com:443 (host is not on the allow list)
deny network-outbound api.anthropic.com:443 (host is not on the allow list)
deny network-outbound api.anthropic.com:443 (host is not on the allow list)
deny network-outbound api.anthropic.com:443 (host is not on the allow list)
deny network-outbound api.anthropic.com:443 (host is not on the allow list)
deny network-outbound api.anthropic.com:443 (host is not on the allow list)
deny network-outbound api.anthropic.com:443 (host is not on the allow list)
deny network-outbound api.anthropic.com:443 (host is not on the allow list)
deny network-outbound api.anthropic.com:443 (host is not on the allow list)
deny network-outbound api.anthropic.com:443 (host is not on the allow list)
deny networ
~~~

### 観点 2

#### P2-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 280 bash scripts/claude/tests/test_i599_unreviewed_scripts.sh 2>&1 | tail -n 15'
~~~
出力の先頭:
~~~
is_error=false
PASS FG TC-05: test-session の表を「何でも可」にすると不合格
PASS FG TC-17: cwd の確かめを外すと不合格
PASS FG TC-07: 起動役が常に止めると不合格
PASS FG TC-08: 差を見ない写し（①）・無視されるファイルを数えない写し（③）で不合格
PASS FG TC-09: 基準の失敗を「なし」に倒すと不合格
PASS FG TC-10: 名前の確かめを外すと一覧に無い other.sh が動く
PASS FG TC-16: 中の確かめを外すと不合格
PASS FG TC-11: gate_reviewed を常に真にすると、レビュー前の中身があってもテストが流れる
PASS FG TC-14: フックの起動役の -c を 1 つ消すと不合格
PASS FG TC-12: 常に写しにすると、作業ツリーの印にならない
PASS FG TC-12: 差を見ないと、変更があっても作業ツリーで動いて不合格
PASS FG TC-18: スキルに包んだ形の呼び出しを足すと不合格
PASS FG TC-05b・TC-02: ワイルドカードを単体でない文字から外すと付け替わる
---
pass=34 fail=0
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I599] ── 観点: ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| - | - | 反証失敗（新規指摘なし）。ただし V6 は実測できなかった。 | - | P1-E1 の出力が判定に使えない（下記） |

**探索した仮説**
- **外に出す型の回避（V1）**: `bash scripts/claude/*` を一覧から外したので、どの形の `bash scripts/claude/…` も外に出る型に当たらない。型は二重スペースや `-u` 付きの起動役にも当たらない。静的読解では穴を確認できなかった。
- **起動役の形の迂回（V3）**: つなぎ・置き換え・前置きの代入・最上位でない cwd・git／gh／docker の後ろに置いた起動役は、`LAUNCH_FORM_RE`・`LAUNCH_AT_BOUNDARY_RE`・`_same_dir` により止まる。単体の形を起動役に付け替えるときは、`NOT_SIMPLE_RE` が展開文字を除外し、引数の文字列をそのまま渡す。静的読解では回避を確認できなかった。
- **レビュー前の中身の判定（V2）**: 差・追跡していない新規・無視されるファイルを数える。一覧にない名前・`/`・「..」は `run` が終了コード 2 で拒む。静的読解では回避を確認できなかった。

**V6 が未確認である理由**
- P1-E1 の出力は途中で切れている。
- 出力の先頭には `api.anthropic.com:443`（および 1 件の `api.github.com:443`）への接続拒否が並ぶ。子のセッションがサンドボックスの中で動き、API につながらなかったと読める。
- そのため、起動役の形が外に出たか（終了コード 3 のメッセージ）、中で動いたか（終了コード 4 のメッセージ）を示す行は得られなかった。
- 実験役の環境ではこの実験の再実行も同じになる見込みなので、追加の実験案は出さない。
- 手動 No.1（ステップ 3.5 の関所）での実測が必要。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> ITEM: V3 RESULT=read
> ITEM: V6 RESULT=not_done EXP=P1-E1
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I599] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。探索した仮説:
- **仮説 1: テストが本物のリポジトリの状態に左右される。**
  - TC-11 の `gate_reviewed` は一時リポジトリを見ます。
  - 起動役・見張り・TC-06 の壊れた判定は、一時リポジトリの写しを読みます。
  - 本物の作業ツリーの差分には依存しません。
- **仮説 2: FG が実装の再確認になっているだけ。**
  - `broken_judge` は置き換え元の存在を assert します。
  - 判定・起動役・見張り・フックの起動役の主要な部分を壊す FG が揃っています。
  - 実験 P2-E1 では、13 本の FG がすべて PASS でした。全体は pass=34 fail=0 です。
  - 壊す側の判定が期待どおり不合格になることを、実測で確認できました。
- **仮説 3: 期待値が緩く、真偽どちらでも通る。**
  - `routed` は、`updatedInput.command`・`timeout` の保持・`permissionDecision` なしを同時に要求します。
  - `blocked` は終了コード 2 を要求します。
  - `untouched` は出力が空であることを要求します。
  - いずれも緩くありません。

軽微な弱点（Low。重大度の件数には数えません）:
- **FG TC-12 `always_snap`:** 写しが無くて `exec` が失敗し、標準出力が空になります。`not startswith(V1…)` はその理由でも真になるため、落ちる理由が少し弱いです。
- **TC-05 の FG:** 変異は `--mcp-config` だけです。`--permission-mode` の値の検証と、起動役の形の側の分岐（`args[0]==TEST_SESSION`）は、専用の FG がありません。
- **TC-14 `same_defs`:** 文字列の一致を見るだけで、挙動は見ていません。

> ITEM: V4 RESULT=experiment EXP=P2-E1
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I599] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Medium | 要件の網羅漏れ（V5・R7 の主張の不正確） | 計画の「引数のファイルを動かすもの・外の任意のものを動かすものが `test-session.sh` だけ」は正確でない。`check-permission-prompt.sh bash '<コマンド>'` は、任意のコマンドを子の `claude -p` に流させる。`tui-capture.sh` は、任意の文字列を対話の子 claude に送れる。この 2 本は一覧にあり、レビュー前の中身が無いときに起動役が外で動かす。どちらも `AC5` の確かめ（表に無い引数での承認）の対象外で、見張りは引数を見ない。子はリポジトリの `.claude/settings.json`（`check-permission-prompt.sh` は `--settings .claude/settings.json` で渡す。`tui-capture.sh` は cwd のプロジェクト設定を読む）を読み、その設定のフックは外で動く。`unreviewed.py` の `dirty` が見るのは `scripts/claude/` の中身だけである。`.claude/settings.json` やフックの設定・ユーザー側の設定の書き換えは、見ていない。`scripts/claude/` が無傷でも、設定の書き換えが外で動く道が残る。この書き換えには承認が要る見込みなので、実害は限られ Medium とした。ただし R7・調査結果 6・V5 に、この残りの入口を書いていない。 | `scripts/claude/check-permission-prompt.sh:28-30,74-83`、`scripts/claude/tui-capture.sh:47,57-66`、`.claude/hooks/unreviewed.py` の `OUTSIDE_SCRIPTS`・`_test_session_ask`、`docs/plans/open/plan_I599.md` R7・R10 | 静的読解のみ。実験案は返していない。承認が要るかは `.claude/settings.json` の ask・deny の欄を確かめていない。 |

反証できたのは、V5 の「引数のファイルを動かすもの」に限る。`issue-source.sh`・`lint-frontend.sh`・`db-backup.sh`・`wt-*.sh`・`pr-base-sync.sh`・`post-review-comment.sh` を、`eval`・`source`・引数展開・`bash -c` の有無で grep した。引数を命令として動かすものは見つからなかった。`pr-base-sync.sh:84` の `bash -c` は固定の文字列である。

探索した仮説:
- 16 本のうち `test-session.sh` 以外に、引数のファイルを動かすもの
- 16 本のうち、外の任意のものを動かすもの。これが `check-permission-prompt.sh` と `tui-capture.sh` で見つかった。
- レビュー前の中身の確かめが `scripts/claude/` だけを見ていて、設定やフックのファイルを見ていないこと

> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 1
REVIEWED_COMMIT: 4bcf6423ecdff4620844227561c595f7750b7722
ROUNDS: 1
VERDICT: HIGH
