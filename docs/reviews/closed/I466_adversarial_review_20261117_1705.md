# 敵対的レビュー [I466]（別プロセス・2026-11-17 17:05）

- 見た範囲: origin/develop...95af75d2ac00bdb6fe38320f4fbc5fb9b1f6961f
- 所要時間: 24 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: backend を起こして確かめた（14 秒・締め切りの外）
- 一覧: docs/plans/open/plan_I466.md の「## 必ず確かめる項目」（3 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 21 秒 | 0 | 0 | $0.2544 | ― | ― | ― |
| 2 | 報告あり | 17 秒 | 0 | 0 | $0.2337 | ― | ― | ― |
| 3 | 報告あり | 20 秒 | 0 | 0 | $0.2624 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I466] ── 観点: 1. ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | テストの確かめ力（V1） | TC-16 ①の `rushed_mistakes(...) is None` の確かめは、他組織の答えが入っても通る。他組織の 25 問はどれも 5 秒で、平均も 5 秒になる。急いだ間違いは 2.5 秒未満なので 0 件になり、None が返る。そのため、この確かめだけでは他組織の答えが混ざったことを検出できない。`weak_difficulties` の確かめは、難易度「上級」が 25 問で 0% の苦手になるはずなので、混ざれば落ちる。TC-17 は並びの確かめで、`for_user` が組織で絞ることも確認できる。 | backend/problems/tests/test_I466_weakness.py（test_other_org_and_other_people_are_not_counted ①） | 静的読解。5 秒の答えだけなら、組織で絞らない場合も、`rushed` は `time_taken < 5*0.5` を満たす行が 0 件になる。 |

実装そのものに穴は見つからなかった。`user_answers` は `QuizAnswer.objects.for_user(user)` を使う。`for_user` は本人の記録に絞ったうえで、`scope_to_user_org` で自組織の科目に絞る。苦手を優先の並び・難易度別の苦手・急いだ間違いは、どれも `user_answers` を通る。並びの `last` の副問い合わせも `answers` から作るので、他組織の答えは入らない。

探索した仮説:
- 苦手な難易度の判定に他組織の答えが混ざる経路
- 苦手を優先の並びが 5 問未満かどうかを数えるとき、他組織の答えが入る経路
- 急いだ間違いに他組織の答えが入る経路。これは上の Low のとおり、確かめが弱いだけだった。

> ITEM: V1 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I466] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。探索した仮説:
- **TC-15 が候補ごとの問い合わせに戻したときに落ちるか**: 落ちると判断した。理由は次の3点。
  - `test_query_count_does_not_grow_with_candidates` は、候補 3 問と 40 問の回で、`QuizService.get_next_problem` が流すクエリ数を `CaptureQueriesContext` で数え、`counts[0] == counts[1]` を確かめる。
  - どちらの回も、本人の答えが 10 件ある（5 問以上）。このため `order_weak_first` はフォールバックに入らず、並べ替えの経路を通る。
  - 回の中の答えは 0 件なので、未回答の分岐（`.exclude(...).first()`）に入る。もし `order_weak_first` が候補ごとに最後の答えを引く形（`last_answered_at` / `last_correct` のサブクエリを外して Python で回す形）に戻ると、クエリ数は候補数に比例して増える（3 対 40）。そのときこの等式は破れる。
- **同じ数のクエリを二重に数えるだけで、何も確かめない形になっていないか**: 実装の式を写していない。数えるのは実際に流れたクエリの本数だけだ。
- **データが苦手の判定に届かず、並べ替えの経路が走らない形になっていないか**: 難易度は易しいと難しいが交互、正解は `i % 3 == 0`（正答率 約 40%）で、苦手な難易度が実際に出る。`Case` の枝も通る。
- **残る弱点（Low）**: 絶対値の固定がない。候補数に依らず一定のまま多い本数（定数の N+1）なら見逃す。ただし TC-15 の目的である候補数への比例は検出できるので、重大度は付けない。また、既出の問題を出す経路（`is_review_mode`）はクエリ数の確認に入っていない。

> ITEM: V2 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I466] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| なし | - | 反証失敗（新規指摘なし） | - | 静的読解（Grep） |

反証失敗（新規指摘なし）。探索した仮説は次の 3 つ。

1. **消した経路の呼び出し元が残っているか。**
   - `docs/` を除く全体を、`mistake-analysis`、`adaptive-learning`、`select_problems`、`proficiency_analysis`、`learning_path`、`refresh_analysis` などで検索した。
   - 一致したのは `test_I466_removed_routes.py`（404 を確かめるテスト）と、コメント、celery のテストの「消したタスク名」だけだった。
   - frontend、e2e、backend の本体コードに呼び出し元は残っていない。
   - `studylogs/urls.py` には `logs`、`statistics`、`goals`、`spaced-repetition`、`sr-cards`、`sr-reviews` の登録だけがある。そのため、消した経路の下はすべて 404 になる。
2. **消したモジュール・キャッシュ関数・タスクの参照が残っているか。**
   - `adaptive_selection`、`mistake_analysis`、`cache_service` の旧関数、`analyze_mistake_patterns_task` の参照は、本体コードに残っていない。
   - `MistakePattern`、`LearningSuggestion`、`LearningWeakness` のモデルは残っている。これは `test_I455` が使うためで、経路の削除とは別の話。
3. **celery beat の予定が消したタスクを指していないか。**
   - 予定から消したタスクは外してある。残りの予定は実在するタスクを指している。`test_I466_celery_schedule.py` がこれを確かめている。

> ITEM: V3 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 95af75d2ac00bdb6fe38320f4fbc5fb9b1f6961f
ROUNDS: 1
VERDICT: OK
