# 敵対的レビュー [I468]（別プロセス・2026-11-15 11:12）

- 見た範囲: origin/develop...b825ab0eaf8f55ee3018e1ea3ba3f8811dc3196c
- 所要時間: 46 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 1 件は下の表）
- コンテナ: 確かめていない（ブランチに backend/ の変更なし）
- 一覧: docs/plans/open/plan_I468.md の「## 必ず確かめる項目」（4 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 1 | 実験必須 | 未実施 | ― | 未検証（未実施） |
| V4 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 44 秒 | 1 | 1 | $0.5009 | ― | ― | ― |
| 2 | 報告あり | 20 秒 | 0 | 0 | $0.2592 | ― | ― | ― |
| 3 | 報告あり | 13 秒 | 0 | 0 | $0.2404 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 拒否された
~~~
bash -c 'set -u; D=$(mktemp -d); git clone -q --local "$PWD" "$D/wt" && cd "$D/wt" && git checkout -q HEAD && printf "const i468Unused = 1;\n" > frontend/src/i468Probe.ts && ls frontend/node_modules 2>&1 | head -2; docker compose ps --status running --services 2>&1 | head -5; echo "--- wrapper (stopped container) ---"; ulimit -v 2097152; timeout 280 bash scripts/claude/lint-frontend.sh 2>&1 | tail -15; echo "exit=${PIPESTATUS[0]}"; docker compose down -v >/dev/null 2>&1; echo "dir=$D"'
~~~
出力の先頭:
~~~

~~~

#### P1-E2: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 60 bash scripts/claude/tests/test_i468_lint_frontend.sh 2>&1 | tail -8; echo "exit=${PIPESTATUS[0]}"'
~~~
出力の先頭:
~~~
is_error=false
  ✅ TC-04 absent → exit 1・理由と対処・lint を呼ばない
== 失敗の注入（写しを壊すと不合格になる）
  ✅ FG-01: 壊した写しは不合格
  ✅ FG-02a: 壊した写しは不合格
  ✅ FG-02b: 壊した写しは不合格
  ✅ FG-03: 壊した写しは不合格
  ✅ FG-04: 壊した写しは不合格
pass=17 fail=0
exit=0
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I468] ── 観点: ロジック回避・実機 repro

## findings
反証できていません（新規指摘なし）。V3 は実機で確かめられていません。

- P1-E2 では、17 件がすべて合格しました。TC-01〜TC-04 と、失敗の注入 FG-01〜FG-04 が通っています。つまり、終了コードを捨てる写しや `grep` を部分一致にした写し、`exit 0` にした写しで、テストが不合格になることを確かめました。
- P1-E1 は拒否されました。そのため、本物の Docker・pre-commit・git を使った V3 は未確認です。
- 読んで確かめたこと:
  - 各分岐は `exec` で lint の終了コードをそのまま返し、最後は `exit 1` です。
  - `docker compose ps` の失敗を `|| true` で握りつぶしても、後続の `compose run` が非 0 で終わるので、黙って通る経路はありません。
- 探した仮説:
  - 終了コードの握りつぶし
  - サービス名の部分一致
  - Docker のデーモンが止まっているときの分岐
  - `docker` が無い PATH
  - `pipefail` と `grep -q` の SIGPIPE

> ITEM: V1 RESULT=read
> ITEM: V3 RESULT=not_done
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I468] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。探索した仮説:
- **終了コードを捨てる写しで落ちるか**
  - `expect_lint` は、偽の lint の終了コードが 0 のときと 1 のときの両方を当てる。ラッパーの終了コードが偽の lint と一致し、lint を流す呼び出しが 1 回だけであることを見る（`test_i468_lint_frontend.sh:83-92`）。
  - FG-01 は `|| true; exit 0` を足した写しを、FG-02b は使い捨ての行に同じ細工をした写しを、FG-03 はホストの行に同じ細工をした写しを当てる。どれも `STUB_RC=1` のときに 0 が返るので不合格になる。
  - `exec` を外して呼び出しが続けて 2 回になる写しも、呼び出しの完全一致の比較で落ちる。
- **部分一致の写しで落ちるか**
  - TC-02 の (c) は、`frontend` を含む別の名前 `frontend-old` を出す。
  - FG-02a は `grep -qx` を `grep -q` にした写しを当てる。その写しは `compose exec` を選ぶので、期待する使い捨ての呼び出しと一致せず不合格になる。
- **tautology（実装の再確認だけになっていないか）**
  - 期待値は、ラッパーの本体を参照せず、テスト内の固定の文字列と作業フォルダで持つ。ラッパーと同じ式を使った写しにはなっていない。
  - 失敗の注入の写しを作るとき、置き換え前の文字列が本体に無ければ ng にする（`:124`）。置き換えが空振りして、壊れていない写しが「不合格になった」と誤って数えられることは無い。
- **環境変数が渡らず、すべて同じ経路になってしまわないか**
  - `STUB_PS_OUT=... expect_lint` のように関数呼び出しの前に付けた変数は、関数の中の `run_case` のサブシェルまで渡る。
  - TC-03 と TC-04 の経路は、偽の docker が `STUB_DAEMON_RC` で終了コードを変えることで実際に分かれる。
- **TC-04 の (b)（docker が無い PATH）**
  - `nodocker` の PATH に入れるのは `bash`・`git`・`grep`・`env`・`npm` だけにしている。docker が無い状態は実際に作れている。

軽微な点（件数に数えない）: auto_test の表に `STUB_DOCKER_INFO_RC` と書かれているが、実際の変数名は `STUB_DAEMON_RC`。既知の台帳 F6 と同じ内容。

> ITEM: V2 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I468] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。探索した仮説:
- CI の ESLint の段と `SKIP: eslint` が変わったか。変更ファイルの一覧に `.github/` は無い。`ci.yml:29` の `SKIP: eslint` と `ci.yml:125` の `npm run lint -- -f github-actions` も残っている。CI の pre-commit の段はラッパーを呼ばず、CI の ESLint は別の段で流れる。そのため、手元で止まらなくても最後は CI が止める。
- CI がラッパーを誤って呼ぶ経路があるか。ESLint のフックは `SKIP` で飛ばされ、`entry` の変更は CI の動きに影響しない。
- 脅威モデル（普通の書き方の事故）に対する穴があるか。「流せないのに通る」穴は無かった。ラッパーは各分岐で `exec` するか `exit 1` で終わる。意図的な回避（`SKIP=eslint`・`DOCKER_HOST` の細工）は対象外で、Low 扱い。

> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 1
REVIEWED_COMMIT: b825ab0eaf8f55ee3018e1ea3ba3f8811dc3196c
ROUNDS: 1
VERDICT: HIGH
