# 敵対的レビュー [I452]（別プロセス・2026-11-12 13:05）

- 見た範囲: origin/develop...16eb7234df751ee1a9c3c445adc40223df1d0ce4
- 所要時間: 66 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- 一覧: docs/plans/open/plan_I452.md の「## 必ず確かめる項目」（6 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V2 | 2 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V3 | 1 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V4 | 2 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V5 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 1 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 40 秒 | 1 | 0 | $0.5534 | ― | ― | ― |
| 2 | 報告あり | 53 秒 | 1 | 0 | $0.5452 | ― | ― | ― |
| 3 | 報告あり | 61 秒 | 1 | 0 | $0.5163 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; cd backend && timeout 60 python -m pytest studylogs/tests/test_I452_quiz_review.py -q -x -k "tenant or cache or review_session or interrupted" 2>&1 | tail -15'
~~~
出力の先頭:
~~~
is_error=false
timeout: failed to run command ‘python’: No such file or directory
~~~

### 観点 2

#### P2-E1: 実行した
~~~
bash -c 'cd backend && ulimit -v 2097152; timeout 60 python -m pytest studylogs/tests/test_I452_quiz_review.py -k "schedule or same_day or day_boundary" -q -x 2>&1 | tail -15'
~~~
出力の先頭:
~~~
is_error=false
timeout: failed to run command ‘python’: No such file or directory
~~~

#### P2-E2: 実行した
~~~
bash -c 'cd backend && ulimit -v 2097152; timeout 60 python -m pytest core/tests/test_I446_cross_api_tenant_isolation.py -k "learning_insights or update_analytics or analyze or refresh_analysis or adaptive or select_problems or review_summary" -q 2>&1 | tail -15'
~~~
出力の先頭:
~~~
is_error=false
timeout: failed to run command ‘python’: No such file or directory
~~~

### 観点 3

#### P3-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; cd backend && timeout 60 python -m pytest -p no:cacheprovider -q studylogs/tests/test_I452_quiz_review.py 2>&1 | tail -15'
~~~
出力の先頭:
~~~
is_error=false
timeout: failed to run command ‘python’: No such file or directory
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I452] ── 観点: ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| - | - | 新規の指摘なし | - | 静的読解のみ。P1-E1 は実験環境に `python` が無く（`failed to run command 'python'`）、テストは実行できなかった |

反証失敗（新規指摘なし）。ただし実験で確かめていない。

探索した仮説:
- **V1: 組織の境界**
  - 復習の件数・次の日付・出題は、すべて `_reviewable_cards` を通る。そこで `SpacedRepetitionCard.objects.for_user(user)`（本人かつ自組織の科目）と `problem__in=available_problems(user, subject)`（自組織で解ける問題。削除済みは除く）を重ねている。他組織・削除済み・別の利用者のカードが混ざる穴は見つからなかった。
  - `subject_id` は `OrgSubjectField` で検証し、失敗は一律 400 にしている。他組織・全体共有・存在しない科目の違いは見せていない。
- **V3: 復習の出題範囲**
  - `_next_review_problem` は `due_cards_queryset(session.subject)` から、この回で答えた問題を除いて出す。対象が無くなると `review_complete` を返す。
  - 答えた問題の次の復習日は、必ず翌日 0 時以降になる。そのため、同じ回で再出題されたり終わらなかったりする経路は見つからなかった。
  - 通常モードは `mode` の分岐より後ろの処理が今までどおり動く。
- **V6: キャッシュのキー**
  - 習熟度は `proficiency_..._org{id}_...` の形に、`get_due_cards` は `due_cards_{limit}_org{id}` の形にしている。組織を移った直後は別のキーになるので、前の組織のカードや習熟度は返らない。
  - 無効化のパターン `spaced_repetition_{uid}_*` が新しいキーの形にも当たるかは、パターンと実際のキーの形式の読み合わせだけで、実機では確認できていない。ただし、当たらなくても有効期限は 5 分で、漏れにはならない。

> ITEM: V1 RESULT=read
> ITEM: V3 RESULT=read
> ITEM: V6 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I452] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | false-green | `test_same_day_second_answer_api` と `test_submit_answer_updates_card` は実時刻（`timezone.now()`）で動く。0 時をまたいで実行されると、同じ日の 2 回目が別の日の回答になり、不安定に落ちうる。 | backend/studylogs/tests/test_I452_quiz_review.py（`test_same_day_second_answer_api` ほか） | 静的読解。実行時刻の問題で、論理の欠陥ではない。 |
| Low | 証拠の弱さ | V5 の「同時の回答でカードを 2 回更新しない」は、`select_for_update` の読みだけが根拠。同時実行のテストは無い。`transaction.on_commit` によるキャッシュ無効化も、pytest の db fixture ではコミットが起きないので、テストで確かめられていない。 | services.py `record_quiz_answer`・`review_card` | 静的読解。 |
| Low | 証拠の弱さ | I446 の xfail を外した後の `ListCheck` は、`status==200` と `_leaks==[]` だけを見る。`world` に難易度や復習のデータが入っていないと、500 を起こしていた経路を通らず、200 は空の結果でも通る。 | test_I446…:595-600 | 静的読解。`world` の中身は未確認。 |

- **実験の結果**: P2-E1・P2-E2 は、実験環境の PATH に `python` が無く（`timeout: failed to run command 'python'`）、テストが実行できなかった。実測の裏取りは取れていない。
- **読解の範囲**: V2 の次の復習日の決まり（0 時＋間隔、正解 4／不正解 2、23:59 と 0:00 の境目）は、テストが `now` を渡して具体的な日時で比べている。実装の式を写しただけのテストにはなっていない。ここまでは読解で確かめた。
- **結論**: Critical／High に当たる新規の欠陥は、読解の範囲では見つからなかった。反証失敗（新規指摘なし）。ただし実験での裏取りはできていない。

> ITEM: V2 RESULT=read
> ITEM: V4 RESULT=read
> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I452] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。探索した仮説:
- 回答の問題が自組織で絞られているか。`submit_answer` は `QuizService.available_problems(session.user, session.subject).get(...)` で取っている。他組織の問題でカードが作られる経路は見つからなかった。
- 同じ日の 2 回目の判定が、日付の境目や並行回答で破れないか。`record_quiz_answer` は行ロックの後に `localdate` で比べる。0 時をまたいだ回答は別の日として更新する。コード上は破れなかった。
- 復習の回で、答えた問題が再び出題されないか。`_next_review_problem` は `session.answers` を除外する。答えた問題は `next_review_date` が明日以降になるので、二重に外れる。
- 組織なしのユーザー、冪等キーで `mode` が違う再送、他組織・全体共有の科目の指定。`mode` の比較、`OrgSubjectField`、`available_problems` で処理されている。コード上は塞がっている。
- キャッシュのキーに組織が入っているか。`due_cards` と習熟度の両方に入っている。
- ロールバック時のキャッシュ破棄。`on_commit` に変えてあり、問題は見つからなかった。

実験 P3-E1 は、実験環境に `python` コマンドが無く実行できなかった（`timeout: failed to run command 'python'`）。これはテストの合否ではなく環境側の失敗なので、証跡には使わない。指摘はいずれも静的読解に基づき、実機の実測はしていない。実験は追加しない。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> ITEM: V3 RESULT=read
> ITEM: V4 RESULT=read
> ITEM: V5 RESULT=read
> ITEM: V6 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 5
REVIEWED_COMMIT: 16eb7234df751ee1a9c3c445adc40223df1d0ce4
ROUNDS: 1
VERDICT: HIGH
