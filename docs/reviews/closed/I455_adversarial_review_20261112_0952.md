# 敵対的レビュー [I455]（別プロセス・2026-11-12 09:52）

- 見た範囲: origin/develop...0dbd5878c9becb65c96765e9bd316c84e1efe41b
- 所要時間: 130 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- 一覧: docs/plans/open/plan_I455.md の「## 必ず確かめる項目」（6 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 実験必須 | 実験で確認 | P1-E6=ran  | 確認済み（実験） |
| V2 | 1 | 実験必須 | 実験で確認 | P1-E6=ran  | 確認済み（実験） |
| V3 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 3 | 実験必須 | 実験で確認 | P3-E1=ran  | 確認済み（実験） |
| V6 | 2 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 125 秒 | 2 | 0 | $0.7748 | ― | ― | ― |
| 2 | 報告あり | 80 秒 | 1 | 0 | $0.5160 | ― | ― | ― |
| 3 | 報告あり | 72 秒 | 1 | 0 | $0.5107 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; cd backend && timeout 60 python -m pytest studylogs/tests/test_I455_org_scoped_querysets.py -q -x 2>&1 | tail -15'
~~~
出力の先頭:
~~~
is_error=false
timeout: failed to run command ‘python’: No such file or directory
~~~

#### P1-E2: 実行した
~~~
bash -c 'ulimit -v 2097152; cd backend && timeout 60 python -m pytest studylogs/tests/test_I431_studylogs_tenant_isolation.py problems/tests/test_I166_quiz_tenant_isolation.py core/tests/test_I446_cross_api_tenant_isolation.py -q 2>&1 | tail -15'
~~~
出力の先頭:
~~~
is_error=false
timeout: failed to run command ‘python’: No such file or directory
~~~

#### P1-E3: 実行した
~~~
bash -c 'ulimit -v 2097152; cd backend && timeout 60 python manage.py makemigrations --check --dry-run 2>&1 | tail -10'
~~~
出力の先頭:
~~~
is_error=false
timeout: failed to run command ‘python’: No such file or directory
~~~

#### P1-E4: 実行した
~~~
bash -c 'set -e; d=$(mktemp -d); cp -r backend $d/b; cd $d/b; sed -i "s/subject_paths = (.subject., .mistake_pattern__subject.)/subject_paths = (\"subject\",)/" studylogs/models.py; ulimit -v 2097152; timeout 60 python -m pytest studylogs/tests/test_I455_org_scoped_querysets.py -q -k both_paths 2>&1 | tail -8'
~~~
出力の先頭:
~~~
is_error=false
timeout: failed to run command ‘python’: No such file or directory
~~~

#### P1-E5: 実行した
~~~
bash -c 'd=$(mktemp -d); cp -r backend $d/b; cd $d/b; printf "\nfrom studylogs.models import StudyLog\ndef _x(u):\n    return StudyLog.objects.filter(\n        user=u)\n" >> dashboard/views.py; ulimit -v 2097152; timeout 60 python -m pytest studylogs/tests/test_I455_org_scoped_querysets.py -q -k reason_comment 2>&1 | tail -8'
~~~
出力の先頭:
~~~
is_error=false
timeout: failed to run command ‘python’: No such file or directory
~~~

#### P1-E6: 実行した
~~~
bash -c 'timeout 120 docker compose exec -T backend python -m pytest -p no:cacheprovider studylogs/tests/test_I455_org_scoped_querysets.py studylogs/tests/test_I431_studylogs_tenant_isolation.py problems/tests/test_I166_quiz_tenant_isolation.py core/tests/test_I446_cross_api_tenant_isolation.py -q 2>&1 | tail -15'
~~~
出力の先頭:
~~~
is_error=false
........................................................................ [ 37%]
...........................................................xx..xx....xxx [ 75%]
xx.............................................                          [100%]
=============================== warnings summary ===============================
studylogs/tests/test_I431_studylogs_tenant_isolation.py::test_create_card_rejects_other_org_like_missing
  /app/core/storage_service.py:2: DeprecationWarning: 'imghdr' is deprecated and slated for removal in Python 3.13
    import imghdr

core/tests/test_I446_cross_api_tenant_isolation.py::test_list_check[GET api/subjects/]
core/tests/test_I446_cross_api_tenant_isolation.py::test_list_check[GET api/organizations/subjects/]
  /usr/local/lib/python3.11/site-packages/rest_framework/pagination.py:198: UnorderedObjectListWarning: Pagination may yield inconsistent results with an unordered object_list: <class 'problems.models.Subject'> QuerySet.
    paginator = self.django_paginator_class(queryset, page_size)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
182 passed, 9 xfailed, 3 warnings in 27.04s
~~~

#### P1-E7: 実行した
~~~
bash -c 'timeout 90 docker compose exec -T backend python manage.py makemigrations --check --dry-run 2>&1 | tail -10'
~~~
出力の先頭:
~~~
is_error=false
No changes detected
~~~

### 観点 2

#### P2-E1: 実行した
~~~
bash -c 'cd backend && ulimit -v 2097152; timeout 60 python manage.py makemigrations --check --dry-run 2>&1 | tail -5'
~~~
出力の先頭:
~~~
is_error=false
timeout: failed to run command ‘python’: No such file or directory
~~~

#### P2-E2: 実行した
~~~
bash -c 'cd backend && ulimit -v 2097152; timeout 60 python -m pytest studylogs/tests/test_I455_org_scoped_querysets.py -q -x -k "specs_cover or unscoped_reads or base_without" 2>&1 | tail -15'
~~~
出力の先頭:
~~~
is_error=false
timeout: failed to run command ‘python’: No such file or directory
~~~

### 観点 3

#### P3-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 60 python3 - <<"EOF"
import ast
SCOPED={"StudyLog"}
NOT={"for_user","create","get_or_create","update_or_create","bulk_create"}
src="""# 組織で絞らない: x
a = StudyLog.objects.filter(user=u).count()
b = StudyLog.objects.filter(user=u2).count()


c = models.StudyLog.objects.filter(user=u)
d = StudyLog.objects.filter(**kw)
e = StudyLog.objects.all()
f = (StudyLog.objects
     .filter(user=u))
"""
lines=src.splitlines()
for n in ast.walk(ast.parse(src)):
    if (isinstance(n,ast.Attribute) and isinstance(n.value,ast.Attribute) and n.value.attr=="objects" and isinstance(n.value.value,ast.Name) and n.value.value.id in SCOPED and n.attr not in NOT):
        w=lines[max(0,n.lineno-4):n.lineno]
        print(n.lineno, "OK" if any("組織で絞らない" in l for l in w) else "MISSING")
EOF'
~~~
出力の先頭:
~~~
is_error=false
7 MISSING
8 MISSING
9 MISSING
2 OK
3 OK
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I455] ── 観点: ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| なし | - | 反証失敗（新規指摘なし）。新テスト、I431・I166・I446 の既存テストは全部通った。migration も増えず、循環 import も無い。 | - | P1-E6: 182 passed, 9 xfailed（I455・I431・I166・I446 の 4 ファイルをまとめて実行）。P1-E7: No changes detected。 |

探索した仮説: ①LearningSuggestion の 2 経路の二重絞り込みと、組織なし利用者・LEFT JOIN での取りこぼし。②(B) に分けた箇所で、`for_user` にすると結果が変わるか。③静的テストのすり抜け。

実測できなかったもの:
- TC-09 の FG（LearningSuggestion の経路を 1 つに減らして RED を確認）は、実験役が実行できていない。往復 1 の E4 はホストに python が無く、往復 2 では組み込めなかった。
- TC-07 の FG（理由コメントなしの読み出しを足して落ちることの確認）も、同じ理由で実行できていない。
- この 2 件の RED は、読んで確かめただけ。

> ITEM: V1 RESULT=experiment EXP=P1-E6
> ITEM: V2 RESULT=experiment EXP=P1-E6
> ITEM: V5 RESULT=read
> ITEM: V6 RESULT=experiment EXP=P1-E6,P1-E7
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I455] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| なし | - | 差分の読解では Critical/High になる欠陥は見つからなかった。V6 は、実験環境に `python` が無く実測できなかった | - | P2-E1・P2-E2 は `python: No such file or directory` で実行できなかった（静的読解のみ） |

読んで確かめたこと（前回の報告と同じ）:
- **TC-01・TC-02 の期待値**: 期待集合を `for_user` の実装から導いていない。`SPECS` の `allow_null` と作成関数から独立に組み立てているので、実装の写しにはなっていない。他組織の科目・全体共有の科目・同じ組織の別の利用者を除外する失敗条件も入っていて、実装が崩れれば落ちる。
- **TC-03**: 提案の科目とパターンの科目が食い違う 2 通りを別々に作っている。どちらか片方の経路を落とすと落ちる。
- **TC-04**: 例外が `filter` の前に出るので、絞り込みが空になるだけの偽の通過にはならない。
- **`test_specs_cover_all_scoped_models`**: `SCOPED_MODELS` は `apps.get_models()` から集めている。`SPECS` に足し忘れたモデルも検出できる。
- **TC-06 の対象行**: 複数行の呼び出しでも、`Attribute.lineno` の先頭行から直前 3 行を窓にしてコメントを探せる。
- **TC-06 の限界（Low、割り切り済み）**: `models.X.objects` の形、変数に入れたモデル、関連の取り出しは見ない。コメントの有無だけを見るので、コメントの内容の正しさは検証されない。
- **V3（(B) の箇所）**: 渡す科目・問題はすでに組織で絞られているか、組織の候補から除く ID を集めるだけだった。`for_user` にしても結果は変わらない。`mistake_analysis.py:267・273` の `subjects` の出所は、差分が途切れていて確認できなかった。計画書の記述（`available_subjects`）を信じた。
- **V4（(C) の箇所）**: 件数・時間・正答率・印付け・利用者を持たない一括処理だった。重複の確かめは `exists()` で応答に出ない。
- **V6**: Manager は `objects` という名前で `use_in_migrations` を持たないので、migration は出ない見込み。循環 import は、`problems/querysets.py` がモデルを import しないので起きない。どちらも実測はできていない。

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
| Medium | 3 | TC-06 は「直前 3 行以内にコメントがある」で判定するため、近くにあるコメントを別の呼び出しが共有できる。コメント付きの呼び出しから 3 行以内に、理由なしで絞らずに読む呼び出しを足しても落ちない。 | `test_I455_org_scoped_querysets.py` の `window = lines[max(0, node.lineno - 4):node.lineno]` | P3-E1: 2 行目と 3 行目が OK。3 行目はコメントのない 2 つ目の呼び出しで、すり抜けている。 |
| Medium | 3 | 検出するのは `Name.objects.<メソッド>` の形だけ。`models.StudyLog.objects.filter(...)` は出力に現れず、検出されない。`from . import models` は普通の書き方なので Medium とした。 | 同上の `isinstance(node.value.value, ast.Name)` | P3-E1: 6 行目の `models.StudyLog` は出力に現れない。 |
| Medium | 3 | 走査範囲が `studylogs/`・`dashboard/` だけ。QuizSession を `problems/` で絞らずに読んでも止まらない。AC3 の範囲は計画どおりだが、QuizSession の付け忘れは作りで防げていない。 | `for app in ("studylogs", "dashboard")` | 静的読解 |

確認できたこともある。複数行の呼び出し（9 行目）、`filter(**kwargs)`（7 行目）、`.all()`（8 行目）は、コメントがなければ MISSING になる。検出の穴は、コメントを近くに置いた場合の共有と、`models.X` の形である。

> ITEM: V5 RESULT=experiment EXP=P3-E1
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 1
REVIEWED_COMMIT: 0dbd5878c9becb65c96765e9bd316c84e1efe41b
ROUNDS: 1
VERDICT: HIGH
