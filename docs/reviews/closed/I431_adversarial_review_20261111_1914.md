# 敵対的レビュー [I431]（別プロセス・2026-11-11 19:14）

- 見た範囲: origin/develop...c4df27e45290911d36d5a942d78bd35c54541a5e
- 所要時間: 97 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- 一覧: docs/plans/open/plan_I431.md の「## 必ず確かめる項目」（8 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V2 | 1 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V3 | 1 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V4 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 1 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V7 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V8 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 82 秒 | 2 | 0 | $0.7276 | ― | ― | ― |
| 2 | 報告あり | 47 秒 | 0 | 0 | $0.2928 | ― | ― | ― |
| 3 | 報告あり | 62 秒 | 0 | 0 | $0.3219 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 実行した
~~~
bash -c 'cd backend && ulimit -v 2097152; timeout 60 python -m pytest -p no:cacheprovider -q -x studylogs/tests/test_I431_studylogs_tenant_isolation.py -k "create_card or study_log_create or study_log_update or existing_other_org_cards or existing_other_org_reviews or submit_review or adaptive_problem_pool or subject_proficiency" 2>&1 | tail -30'
~~~
出力の先頭:
~~~
is_error=false
timeout: failed to run command ‘python’: No such file or directory
~~~

#### P1-E2: 実行した
~~~
bash -c 'cd backend && ulimit -v 2097152; timeout 60 python3 -m pytest -p no:cacheprovider -q -x studylogs/tests/test_I431_studylogs_tenant_isolation.py -k "create_card or study_log_create or study_log_update or existing_other_org_cards or existing_other_org_reviews or submit_review or adaptive_problem_pool or subject_proficiency" 2>&1 | tail -30'
~~~
出力の先頭:
~~~
is_error=false
/usr/bin/python3: No module named pytest
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I431] ── 観点: ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| - | - | 反証失敗（新規指摘なし）。ただし実機での裏取りはできていない。 | - | P1-E1 は `python` が無く、P1-E2 は `python3` に pytest が入っておらず、どちらも実行できなかった。静的読解のみ。 |

反証失敗（新規指摘なし）。探索した仮説は次のとおり。

- **V1（カード作成）:** `create_card` は `available_problems(request.user).get(id=...)` で問題を引く。他組織・存在しない・削除済み・全体共有科目の問題は、どれも同じ `DoesNotExist` になる。組織に属さない利用者は `none()` になる。差分の範囲では抜け道は見つからなかった。ただし 404 の本文が存在しない ID と完全に一致するかは、`except` 節の全文を読めていない（差分が切れていた）。実機では確かめていない。
- **V2（学習記録の POST と PATCH）:** `OrgSubjectField` は `available_subjects` を queryset にする。他組織の科目と存在しない科目は、同じ `does_not_exist` の 400 になる。`StudyLogSerializer` と `StudyLogCreateSerializer` の両方に付いているので、PUT と PATCH も塞がれる。context に request が無いと `none()` になる fail-closed 側の作りになっている。
- **V3（既存の他組織カード・復習の読み出し）:** `sr-cards`、`sr-reviews`、`get_due_cards`、`submit_review` はすべて `scope_to_user_org(..., 'problem__subject')` を通る。`get_due_cards` のキャッシュは、キャッシュに入る前の絞り込み済みの結果なので、キャッシュ経由で漏れることはない。ただし `get_due_cards` のキャッシュキーが組織変更後も残る可能性は、読んだだけでは判断できなかった。これは Low 相当の懸念で、件数には数えない。
- **V6（適応的な問題選択）:** `_get_problem_pool` は `available_problems(self.user, subject)` に置き換わっている。`_calculate_subject_proficiency` は `available_subjects(self.user)` に置き換わっている。他組織が混ざる経路は見つからなかった。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> ITEM: V3 RESULT=read
> ITEM: V6 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I431] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | tautology | TC-10 の「科目の指定なし」部分は、応答がエラー(difficulty の型の不具合)になる。エラー本文に他組織の文字列が入らないのは自明なので、`_no_other(no_subject)` は事実上どんな実装でも通る。レビュー記録でも、修正前に通った 3 件に TC-10 が入っている。実際の保証は TC-08・TC-09 の直接テストが担っているので、害は小さい。 | test_I431_studylogs_tenant_isolation.py(TC-10 の末尾) | 静的読解(`select_problems` は `except Exception` で 500 を返す。views.py:944-947) |
| Low | 副作用 | autouse の `_clear_caches` が、`settings.CACHES` の全 alias を `clear()` する。テストが開発用の Redis に向いていると、開発中の cache も消える。テストの正しさには影響しない。 | 同ファイル `_clear_caches` | 静的読解 |

探索した攻め筋は次の 3 本で、いずれも反証できなかった。
- **空を返すだけの実装で通るか。** TC-03・TC-13・TC-15〜TC-19 は、すべて同じテストの中で自組織の記録が出ることを明示的に assert している。TC-03 の `by_subject == []` だけは不在確認のみだが、同じテスト内の自組織の assert で補えている。空を返す実装では落ちる。
- **TC-09 などが修正前でも通るか。** 他組織の科目にも試行を作ってあるので、修正前なら科目 ID の集合が一致せず RED になる。
- **TC-04b の同一性。** 修正前なら `study_session` が他組織の科目の進行中ログに紐づくので RED になる。修正後は、400 が返っても、先に作られた review を `get` で取れることを確認している。
- **V8(RED の記録・順序依存)。**
  - review 記録に「修正前 20 failed・3 passed」とある。通った 3 件(TC-02・TC-10・TC-22)は、無退行または既に安全な経路で、計画に書いた期待どおりである。TC-22 は tenant_scope のファイルが残った状態で流したため通っただけで、本物の RED ではない。これも記録に明記されている。
  - TC-15b は後から足し、単独で FAIL を確認したと記録にある。
  - cache を消す autouse fixture があり、`_missing_id` も各テスト内で作った行を前提にしているので、順序に依存しない。

> ITEM: V5 RESULT=read
> ITEM: V8 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I431] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | 脅威モデル（キャッシュ） | `get_due_cards` は、組織で絞る前に `cache_service.get_spaced_repetition_cache(user.id, "due_cards_{limit}")` を返す。キーは利用者 ID だけで、組織を含まない。修正のデプロイ前（または組織を移る前）に作られた最大 5 分間のキャッシュには、他組織のカード（問題文入りのモデルのリスト）が残りうる。最大 5 分で自然に消え、一時的で上限がある。ただし「境界の判定のためキャッシュは使わない」という、`tenant_scope` と `get_user_selected_subjects` の方針とはそろっていない。 | `backend/studylogs/services.py:37-41` | 静的読解。実験はしていない。TTL は `settings.CACHE_TIMEOUTS['spaced_repetition']`（5 分）。 |
| Low | エッジケース | `StudyLogViewSet.create` は、先に `is_active=True` の既存ログをすべて終了させてから `is_valid` を呼ぶ。他組織の科目が 400 で断られるようになったので、400 の応答なのに進行中のログが終了する副作用が出る。越境の問題ではなく、既存の順序の問題。 | `backend/studylogs/views.py:49-57` | 静的読解。 |
| Low | エッジケース | `scope_to_user_org` は `is_deleted` を見ない。自組織の削除済みの問題を指す既存のカード・復習記録は、一覧に残る。他組織への漏れではない。 | `backend/problems/services/tenant_scope.py` | 静的読解。 |

V4 は、`studylogs/` と `dashboard/` の変更後のコードを grep して確かめた。
- `Problem.objects` と `Subject.objects` の直接の使用は、本番コードには残っていない。
- 科目・問題を指すモデルの読み出しは、調査表の「塞ぐ」か、数だけを返す「変えない」に当たる。表から漏れている箇所は見つからなかった。
- `StudyLogViewSet.create` の一括 `update`（views.py:51）と `_update_daily_summary` は、中身を返さない書き込みなので、漏れではない。

V7 は読んで確かめた。
- 組織に属さない利用者は、`available_*` が空を返し、`scope_to_user_org` が `none()` になる。
- 全体共有科目は、`organization_id` の等価比較で外れる。
- 削除済みの問題は、`is_deleted=False` で外れる。
- TC-01 は、他組織・存在しない・削除済み・共有の 4 通りを同じ 404 で見ている。TC-21・TC-22 は、組織に属さない利用者と単体の関数を見ている。
- 境界が開く経路は見つからなかった。

反証失敗（新規の Critical/High なし）。探索した仮説は 3 つ。
1. 調査表にない科目・問題の読み出しがある。
2. 組織に属さない利用者・全体共有科目・削除済みの問題で境界が開く。
3. 組織で絞る前に返すキャッシュ経路がある。

> ITEM: V4 RESULT=read
> ITEM: V7 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 4
REVIEWED_COMMIT: c4df27e45290911d36d5a942d78bd35c54541a5e
ROUNDS: 1
VERDICT: HIGH
