# 敵対的レビュー [I452]（別プロセス・2026-11-12 13:18）

- 見た範囲: 16eb7234df751ee1a9c3c445adc40223df1d0ce4...a5f1fcd800432f4cbf9c92e86bcb7fc6d75726fd
- 所要時間: 23 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- 一覧: docs/plans/open/plan_I452.md の「## 必ず確かめる項目」（6 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 17 秒 | 0 | 0 | $0.1286 | ― | ― | ― |
| 2 | 報告あり | 11 秒 | 0 | 0 | $0.1056 | ― | ― | ― |
| 3 | 報告あり | 11 秒 | 0 | 0 | $0.1084 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I452] ── 観点: ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | キャッシュ | `get_due_cards` は `timezone.now()` を基準に絞った結果を 5 分キャッシュする。期限が来る直前の結果は最大 5 分古くなる。組織が漏れる経路ではなく、既知 F4 と同種。 | services.py:44-59 | 静的読解 |

反証失敗（新規指摘なし）。ただし、このレビューで実験は実行していない。差分はドキュメントだけなので、実コードの `services.py` と `quiz_service.py` を読んで確かめた。

探索した仮説:
- **V1: 組織・削除・別の利用者のカードが混ざる穴**
  - 件数、次の日付、出題はすべて `_reviewable_cards` を通る。
  - `_reviewable_cards` は `for_user(self.user)` と `problem__in=available_problems(user, subject)` を重ねている。
  - 別の利用者のカード、他組織の問題、削除済みの問題が入る経路は見つからなかった。
  - `review_summary` は 1 回の集計で `Count` と `Min` を出している。`filter` の条件は `due_count` と `upcoming` で排他的になっている。
- **V3: 出題の範囲と終了**
  - `_next_review_problem` は `due_cards_queryset(session.subject)` から、この回で答えた問題を除いて 1 件を出す。
  - 対象が無ければ `None` を返す。
  - `session.subject` が `None` なら `_reviewable_cards(None)` になり、全科目が対象になる。
  - 答えた問題は次の復習日が翌日 0 時以降になる。同じ回で再出題される経路は見つからなかった。
- **V6: キャッシュのキー**
  - `get_due_cards` のキーは `due_cards_{limit}_org{organization_id}`。
  - 習熟度のキーは `cache_service.py:243` で `org{organization_id}` を含めている。
  - 組織を移った直後は別のキーになるので、前の組織の結果は返らない。
  - 組織なし（`None`）のときは `org None` の文字列になり、他のキーとは衝突しない。

> ITEM: V1 RESULT=read
> ITEM: V3 RESULT=read
> ITEM: V6 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I452] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。探索した仮説:
- V2: `test_schedule_*` と `test_schedule_day_boundary` は、`now` に具体的な日時（23:59 と 0:00:30 など）を渡している。期待値も具体的な日付で比べていて、実装の式を写してはいない。同じ日の 2 回目も、9 時と 21 時の別の入力で確かめている。
- V4: `test_difficulty_mapping_matches_choices` と `test_difficulty_proficiency_counts` は、件数を具体的な数で比べている。#446 の `ListCheck` を外しても、既知 findings の Low にある「データが空でも通りうる」点を超える新しい穴は見つからなかった。
- V5: 行ロックと同じトランザクションの扱いは、読んで確かめた。同時実行のテストが無い点は既知 findings と同じで、新規には数えない。

実験は返していない。前の周で実験環境に `python` が無かったので、追加しても結果が届かないと判断した。

> ITEM: V2 RESULT=read
> ITEM: V4 RESULT=read
> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I452] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗(新規指摘なし)。探索した仮説:
- **組織の境界**: `_reviewable_cards` は `for_user(self.user)` に `problem__in=available_problems(user, subject)` を重ねている。他組織・削除済み・別の利用者のカードが混ざる経路は見つからなかった。
- **同じ日の 2 回目の判定**: `record_quiz_answer` は行をロックしてから `localdate` で比べる。0 時をまたいだ回答は別の日として更新する。コード上は破れない。
- **件数と次の日付**: `review_summary` は 1 回の集計で `due_count` と `upcoming` を出す。復習のクイズの出題は `due_cards_queryset` を通り、件数と同じ条件になっている。
- **前回の報告との重複**: 先の敵対的レビュー(20261112_1305)の観点 3 と同じ仮説は再報告しない。コード側の Low(F1〜F7)も既知の台帳として扱う。

実験は返さなかった。前回の実験役の環境に `python` が無く、実行できなかったため。今回の指摘はすべて静的読解に基づく。V1〜V4・V6 のうち、CI で毎回流れる TC の失敗注入(FG)による裏取りは、計画書とテスト記録の記載に頼っている。

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
UNVERIFIED: 0
REVIEWED_COMMIT: a5f1fcd800432f4cbf9c92e86bcb7fc6d75726fd
ROUNDS: 1
VERDICT: OK
