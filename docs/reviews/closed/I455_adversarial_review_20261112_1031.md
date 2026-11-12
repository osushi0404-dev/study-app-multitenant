# 敵対的レビュー [I455]（別プロセス・2026-11-12 10:31）

- 見た範囲: 0dbd5878c9becb65c96765e9bd316c84e1efe41b...2e052070432baea659bdc6cd219f8181c8b8e6ce
- 所要時間: 134 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- 一覧: docs/plans/open/plan_I455.md の「## 必ず確かめる項目」（6 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 実験必須 | 実験で確認 | P1-E1=ran P1-E2=ran  | 確認済み（実験） |
| V2 | 1 | 実験必須 | 実験で確認 | P1-E1=ran  | 確認済み（実験） |
| V3 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 3 | 実験必須 | 実験で確認 | P3-E1=ran  | 確認済み（実験） |
| V6 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 102 秒 | 1 | 0 | $0.4503 | ― | ― | ― |
| 2 | 報告あり | 26 秒 | 0 | 0 | $0.2293 | ― | ― | ― |
| 3 | 報告あり | 120 秒 | 1 | 0 | $0.4593 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 実行した
~~~
bash -c 'timeout 150 docker compose exec -T backend python -m pytest -p no:cacheprovider studylogs/tests/test_I455_org_scoped_querysets.py studylogs/tests/test_I431_studylogs_tenant_isolation.py problems/tests/test_I166_quiz_tenant_isolation.py core/tests/test_I446_cross_api_tenant_isolation.py -q 2>&1 | tail -8'
~~~
出力の先頭:
~~~
is_error=false
core/tests/test_I446_cross_api_tenant_isolation.py::test_list_check[GET api/subjects/]
core/tests/test_I446_cross_api_tenant_isolation.py::test_list_check[GET api/organizations/subjects/]
  /usr/local/lib/python3.11/site-packages/rest_framework/pagination.py:198: UnorderedObjectListWarning: Pagination may yield inconsistent results with an unordered object_list: <class 'problems.models.Subject'> QuerySet.
    paginator = self.django_paginator_class(queryset, page_size)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
183 passed, 9 xfailed, 3 warnings in 37.30s
~~~

#### P1-E2: 実行した
~~~
bash -c 'timeout 90 docker compose exec -T backend python -m pytest -p no:cacheprovider studylogs/tests/test_I455_org_scoped_querysets.py -q -k "catches_unmarked or reason_comment or both_paths or noorg or for_user" 2>&1 | tail -8'
~~~
出力の先頭:
~~~
is_error=false
...................                                                      [100%]
19 passed, 2 deselected in 8.21s
~~~

### 観点 3

#### P3-E1: 実行した
~~~
bash -c 'timeout 120 docker compose exec -T backend python -m pytest -p no:cacheprovider studylogs/tests/test_I455_org_scoped_querysets.py -q -k "reason" 2>&1 | tail -8'
~~~
出力の先頭:
~~~
is_error=false
..                                                                       [100%]
2 passed, 19 deselected in 0.76s
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I455] ── 観点: 1. ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | 1 | 同じ行に呼び出しが 2 つあると、その行の理由コメント 1 つを両方が共有する。既知の F9 と同系で、普通の書き方の事故にはなりにくい。 | test_I455_org_scoped_querysets.py `has_reason` | 静的読解 |

Critical/High になる欠陥は見つからなかった。反証失敗（新規の Critical/High なし）。

- **V1・V2の実測:** P1-E1 で I455・I431・I166・I446 の 4 ファイルを実行し、183 passed・9 xfailed だった（失敗 0）。守りのテストはファイルを変えずに通っている。新しいテストの `for_user` の TC-01〜TC-03 も同じ実行に含まれ、通った。
- **V5の実測:** P1-E2 で `catches_unmarked`・`reason_comment`・`both_paths`・`noorg`・`for_user` を実行し、19 passed だった。検出器の合成テストが、付け忘れの行だけを返す。
- **実測できなかったもの（V1・V5 の一部）:** 失敗の注入（FG）は、作業ツリーを書き換えるため実験案にできず、実行していない。具体的には、TC-09 の LearningSuggestion の経路を 1 つ減らして RED になるか、TC-07 でコメントを消して落ちるかの 2 つ。
  - TC-09 は、テストの読解で補った。TC-03 は、提案の科目だけが他組織の組と、パターンの科目だけが他組織の組を別々に作っている。片方の経路を落とせば、その組が残って落ちる。
  - TC-07 の `test_reason_check_catches_unmarked_reads` は、検出器そのものを合成コードで毎回確かめる。通ることは P1-E2 で実測した。

探索した仮説:
- 検出器が前の行の行末コメントを共有する穴は、`tokenize` と「コメントだけの行」の条件で塞がれている。
- 括弧で包んだ代入で、理由を 1 行上に書くと窓から外れる。これは落ちる側（安全側）に倒れるので、Low とした。
- `get_or_create` が読み出し扱いにならない件と、`tokenize` の行番号のずれは、既知の F8・F10 と同じ。

> ITEM: V1 RESULT=experiment EXP=P1-E1,P1-E2
> ITEM: V2 RESULT=experiment EXP=P1-E1
> ITEM: V5 RESULT=experiment EXP=P1-E2
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I455] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | 2 | 同じ行に呼び出しが 2 つあると、1 つの理由を両方が共有する。理由の判定が行単位なので、2 つ目が理由なしでも通る。普通の書き方ではまれで、すでに既知の F9 に近い。 | `_missing_reasons` の `has_reason(node.lineno)` | 静的読解 |

それ以外は反証失敗（Critical/High の新規指摘なし）。

試した攻め筋:
- **TC-07 の合成コード**:
  - 期待値 `[3,4,5,8,9,13,15]` を、tokenize と判定の流れで 1 行ずつ追った。
  - 3 行目は直前が理由のない 2 行目なので、離れたコメントを共有せず「付け忘れ」と判定される。
  - 13 行目は、直前の 12 行目の理由が行末コメントなので、`lstrip().startswith("#")` が偽になる。共有されず落ちる。
  - 15 行目は、直前の 14 行目の印が文字列リテラルなので、COMMENT トークンに入らない。理由に数えられず落ちる。
  - 4 行目は `models.X` の形で、`_model_name` が `Attribute.attr` を返して検出される。
  - 5 行目は複数行の呼び出しで、基準の行は先頭になる。
  - 8 行目と 9 行目は、`filter(**kw)` と `.all()` が `NOT_READS` に入っていないので検出される。
  - 10 行目と 11 行目は、`for_user` と `create` を除外している。
  - 12 行目は同じ行のコメントが効くので通る。
  - 検出器の判定を壊すと落ちる作りだった。
  - 弱点は 1 つ。4 行目の `ProblemAttempt` など、期待値の一部が `SCOPED_MODELS` の登録に暗黙に頼っている（既知 F9）。
- **tautology**:
  - TC-01 から TC-03 の期待集合は `SPECS` と作成関数から独立に組み立てている。`for_user` の実装の写しにはなっていない。
  - 診断書に FG 実測（行末コメントの判定条件を外すと RED）が記録されている。
- **V3**: `mistake_analysis.py:249` で `subjects = available_subjects(self.user)` を確認した。これは組織で絞った科目なので、(B) に分けた 267・273 行目の根拠は成り立つ。
- **V4**: (C) の例（`mistake_analysis.py:92` と `99`、`151` と `157`、`192` の `.filter(` は件数・時間の集計）は、他組織の名前・本文・ID を応答に出さない。
- **V6**:
  - Manager を `objects` 名で差し替え、`use_in_migrations` を付けていないので、migration は出ない。
  - `problems/querysets.py` はモデルを import しないので、循環 import は起きない。
  - CI の `makemigrations --check` が毎回確かめる。
  - 敵対的レビュー 1 周目の P1-E7 でも `No changes detected` だった。
  - 実験役の環境に python が無く、今回は実測していない。

> ITEM: V3 RESULT=read
> ITEM: V4 RESULT=read
> ITEM: V6 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I455] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | 3 | 検出器は、理由の中身が空の `# 組織で絞らない:` でも理由ありと数える。同じ行に読み出しが 2 つあると、1 つの理由を共有する。`get_object_or_404(StudyLog, …)` や `_default_manager` 経由は検出外。いずれも既知の F8 と同系統で、割り切り済み(R5)なので新規扱いにしない。 | `test_I455_org_scoped_querysets.py:228-250` | 静的読解 |

反証失敗(新規の Critical/High なし)。探索した攻め筋は次の 3 本。

- **前の行の行末コメントの共有**: `has_reason` は、その行のコメントに印があるか、直前の行に印がありかつその行が `#` 始まりのときだけ理由と認める。合成ケースの 13 行目と 15 行目は missing になる。
- **文字列の中の印**: `tokenize` で COMMENT トークンだけを見るので、文字列の中の印は理由に数えない。
- **検出の形**: `models.X` は `_model_name` が Attribute を扱うので拾える。複数行の呼び出しは `Attribute.lineno` が先頭行を指すので拾える。`filter(**kw)` と `.all()` は `NOT_READS` に無いので拾える。

実験 P3-E1 で、`-k reason` の 2 件が実走して通った(2 passed)。`test_reason_check_catches_unmarked_reads` が `[3,4,5,8,9,13,15]` と一致し、本番コードの TC-06 も通っている。

V5 の「理由なしで足すと落ちる」「コメントを消すと落ちる」の FG は、実験役の環境で実測できなかった。これは実験案を出せていない私の側の抜けで、本番コードを使った FG は未実測。代わりに合成コードで同じ形を毎回確かめるテストが通ったことを根拠にする。

> ITEM: V5 RESULT=experiment EXP=P3-E1
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 2e052070432baea659bdc6cd219f8181c8b8e6ce
ROUNDS: 1
VERDICT: OK
