# 敵対的レビュー [I446]（別プロセス・2026-11-12 02:26）

- 見た範囲: origin/develop...cc77b27ae901d741ab7521f4181a5150a502c79f
- 所要時間: 83 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- 一覧: docs/plans/open/plan_I446.md の「## 必ず確かめる項目」（9 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 実験必須 | 実験で確認 | P1-E1=ran P1-E2=ran  | 確認済み（実験） |
| V2 | 1 | 実験必須 | 実験で確認 | P1-E1=ran P1-E2=ran  | 確認済み（実験） |
| V3 | 2 | 実験必須 | 実験で確認 | P2-E1=ran  | 確認済み（実験） |
| V4 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 3 | 実験必須 | 未実施 | ― | 未検証（未実施） |
| V7 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V8 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V9 | 1 | 実験必須 | 実験で確認 | P1-E1=ran  | 確認済み（実験） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 63 秒 | 1 | 0 | $0.5037 | ― | ― | ― |
| 2 | 報告あり | 40 秒 | 1 | 0 | $0.5269 | ― | ― | ― |
| 3 | 報告あり | 77 秒 | 1 | 0 | $0.5447 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 実行した
~~~
docker compose exec -T backend bash -c 'ulimit -v 2097152; timeout 60 python -m pytest -p no:cacheprovider -q -x core/tests/test_I446_cross_api_tenant_isolation.py -k "problems or quiz or noorg"'
~~~
出力の先頭:
~~~
is_error=false
......................x...                                               [100%]
=============================== warnings summary ===============================
core/tests/test_I446_cross_api_tenant_isolation.py::test_id_check[GET api/problems/ subject]
  /app/core/storage_service.py:2: DeprecationWarning: 'imghdr' is deprecated and slated for removal in Python 3.13
    import imghdr

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
25 passed, 103 deselected, 1 xfailed, 1 warning in 2.74s
~~~

#### P1-E2: 実行した
~~~
docker compose exec -T backend bash -c 'ulimit -v 2097152; timeout 60 python -m pytest -p no:cacheprovider -q problems/tests/test_I103_cross_org_create.py problems/tests/test_I166_quiz_tenant_isolation.py'
~~~
出力の先頭:
~~~
is_error=false
....................                                                     [100%]
=============================== warnings summary ===============================
problems/tests/test_I103_cross_org_create.py::test_cross_org_create_rejected
  /app/core/storage_service.py:2: DeprecationWarning: 'imghdr' is deprecated and slated for removal in Python 3.13
    import imghdr

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
20 passed, 1 warning in 6.89s
~~~

### 観点 2

#### P2-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 60 docker compose exec -T backend pytest problems/tests/test_I166_quiz_tenant_isolation.py -q -x -p no:cacheprovider 2>&1 | tail -15'
~~~
出力の先頭:
~~~
is_error=false
..............                                                           [100%]
=============================== warnings summary ===============================
problems/tests/test_I166_quiz_tenant_isolation.py::test_start_with_other_org_subject_is_rejected_like_missing
  /app/core/storage_service.py:2: DeprecationWarning: 'imghdr' is deprecated and slated for removal in Python 3.13
    import imghdr

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
14 passed, 1 warning in 5.27s
~~~

### 観点 3

#### P3-E1: 実行した
~~~
bash -c 'set -e; d=$(mktemp -d); cp -r backend "$d/backend"; cd "$d/backend"; sed -i "s/subject__organization=self.request.user.organization/subject__organization__isnull=False/" problems/views.py; ulimit -v 2097152; timeout 60 python -m pytest core/tests/test_I446_cross_api_tenant_isolation.py -x -q -k "problems" 2>&1 | tail -15'
~~~
出力の先頭:
~~~
is_error=false
timeout: failed to run command ‘python’: No such file or directory
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I446] ── 観点: 1. ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| （なし） | — | 反証失敗（新規指摘なし）。 | — | P1-E1 は 25 passed・1 xfailed、P1-E2 は 20 passed |

探索した仮説は次のとおり。
- 問題の作成（POST）・付け替え（PUT・PATCH）・AI 生成の 2 経路で、他組織・全体共有の科目が存在しない科目と同じ応答にならない抜け道がないか。`-k "problems or quiz or noorg"` で選んだ IdCheck が通り、既存の I103 のテストも新しい期待値で通った。
- クイズの回の古いデータ（他組織の科目の回・科目なしの回の中の他組織の問題への回答）が、詳細・終了の応答に出ないか。OwnCheck と I166 の TC-09 が通った。
- 組織が空の組織管理者が、問題の一覧・詳細で全体共有の問題を見られないか。`test_noorg_org_admin_sees_no_problems` が通った。
- xfail の 1 件は表に書いた #452 由来で、想定どおり。

実験の制約が 2 つある。
- 修正前の FAIL（TC-20）は、作業ツリーに書かずにソースを戻す手段がなく、実測していない。V1・V2・V9 の「修正前の FAIL」の半分は未実測。
- `-k` の選択は部分一致なので、選ばれなかった経路の確認が部分的になる。

> ITEM: V1 RESULT=experiment EXP=P1-E1,P1-E2
> ITEM: V2 RESULT=experiment EXP=P1-E1,P1-E2
> ITEM: V8 RESULT=read
> ITEM: V9 RESULT=experiment EXP=P1-E1
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I446] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。探索した仮説:
- 4-4 の先読みの絞り込みが、`submit_answer` の「回答済みか」、`QuizService` の未回答の判定、終了の応答の回答の数を変えるか。
  - `session.answers` を使う箇所は `.filter()` / `.values_list()` / `session.answers...` で、どれも新しい問い合わせになる。先読み（prefetch）の結果は使わない。
  - 先読みは `retrieve` と `end` の応答だけに掛かる。
  - 実験 P2-E1 で `test_I166_quiz_tenant_isolation.py` の 14 件がすべて通った（TC-02〜TC-08・TC-12 を含む）。
- `ProblemSerializer`・`ProblemAdminSerializer` を、request の無い文脈で書き込みに使う箇所があるか。
  - `ProblemSerializer(...)` の呼び出しはすべて出力だけで使っている。`read_only=True` の入れ子か、`.data` の読み出しである。
  - `ProblemAdminSerializer` は継承の定義だけで、直接呼ぶ箇所は無い。

> ITEM: V3 RESULT=experiment EXP=P2-E1
> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I446] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| — | — | 新規指摘なし。 | — | — |

反証失敗（新規指摘なし）。探索した仮説:
- `api/auth/me/` の PUT・PATCH で組織・役割が書き換えられるか。
  - `UserSerializer.fields` に `organization` が無く、`role`・`is_staff`・`is_superuser` は `read_only_fields` にある（accounts/serializers.py:187-203）。書き換えられない。
  - 書き換えられるのは `email` と、`is_email_verified`（read_only_fields に無い）で、組織の境界とは関係しない。
  - これは静的読解で確かめた。
- 表と経路の突き合わせ（V5）が、新しい経路・古い行の両方で落ちるか。
  - `test_route_table_matches_urlconf` は `routes - table` と `table - routes` の両方向を検査している。
  - 両方に載る行（`ROUTE_TABLE` と `OUT_OF_SCOPE` の両方に載るキー）、`OUT_OF_SCOPE` の空の理由、空の確かめ方の並びも `assert` で落ちる。
  - 読んだ範囲では漏れはない。FG1 の実測は、この観点では行っていない。
- 「対象外」の各行の理由（V7）が、ビューのコードと合っているか。
  - 読んだのは `api/auth/me/`、`api/settings/`（本人固定）、`POST api/subjects/`・`POST api/study/goals/`（組織と持ち主を固定）の行だけ。
  - 他の行の理由は、計画書と grill-me の記録を信じており、ビューのコードとは突き合わせていない。
- 組織の絞り込みを外す失敗注入（V6）。
  - 実験 P3-E1 は、実行環境に `python` が無く（`timeout: failed to run command 'python'`）、テストが一度も走っていない。
  - そのため V6 は実測できていない。
  - 静的読解では、正の対照（`own_status=200`）と `OwnCheck`・I166・I431 のテストが組み合わさっているが、これは実測の代わりにならない。

> ITEM: V5 RESULT=read
> ITEM: V6 RESULT=not_done
> ITEM: V7 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 1
REVIEWED_COMMIT: cc77b27ae901d741ab7521f4181a5150a502c79f
ROUNDS: 1
VERDICT: HIGH
