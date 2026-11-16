# 敵対的レビュー [I494]（別プロセス・2026-11-16 12:24）

- 見た範囲: origin/develop...65d03b13b7960908b78e5f9b4146e642f56ff5c6
- 所要時間: 28 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: backend を起こして確かめた（18 秒・締め切りの外）
- 一覧: docs/plans/open/plan_I494.md の「## 必ず確かめる項目」（5 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 13 秒 | 0 | 0 | $0.2451 | ― | ― | ― |
| 2 | 報告あり | 25 秒 | 0 | 0 | $0.2730 | ― | ― | ― |
| 3 | 報告あり | 16 秒 | 0 | 0 | $0.2382 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I494] ── 観点: ロジック回避・実機 repro

## findings
反証失敗（新規指摘なし）。探索した仮説:
- 本文の組織を使った越境（V1）: `UserSubjectSelectionSerializer.validate_subject_ids` は `self.context['request'].user` から `available_subjects(user)` を引く。`organization_id` は本文から取らない。`available_subjects` は `filter(organization_id=user.organization_id)` だけで絞る。他組織・全体共有・存在しない番号は、どれも「件数が合わない」ことで同じ文言になる。TC-03 は 3 つの本文が一致することを確かめ、`_selected` が不変であることも確かめている。
- 組織なしの利用者と全体共有の科目（V5）: `available_subjects` は `organization_id is None` なら `Subject.objects.none()` を返す。シリアライザ・サービス・`AvailableSubjectsView` の 3 か所は、いずれもこの関数を使う。組織なしの利用者は、全体共有を選べず、`available` にも出ない。組織のある利用者も `organization_id` の完全一致でしか選べないので、全体共有（`organization=None`）は選べない。TC-09 と TC-03 がこれを固定している。
- サービスの単独呼び出し（V2）: `replace_user_subjects` は `available_subjects(user).filter(id__in=…)` で `wanted` を作る。他組織・全体共有の番号は `wanted` に入らず、書かれない。TC-10b がこれを確かめている。
- 範囲外の Low: 既知の台帳 F2・F3 と同じ種類の指摘（別組織の旧行の削除、検証後の削除競合）は再報告しない。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I494] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | false-green | TC-05 の最後の `not any(_cached)` は、保存の途中の「今すぐ消す」だけでも通る。確定の後の消去（`on_commit`）を単独では検証していない。`PUT` の応答に使う `get_user_selected_subjects(use_cache=False)` はキャッシュに書き戻さないので、間に入る読み取りが無く、`on_commit` を外しても落ちない。計画書は、足すだけの保存に変えると、外す操作のシグナルによる消去を抜いた場合に落ちることを確かめたと書いている。ただ、on_commit の消去を抜いた場合に落ちる実験は見当たらない。Critical/High ではなく、キャッシュが古くなる経路そのものは塞がれている。 | backend/problems/tests/test_I494_user_subjects.py:TC-05、backend/problems/signals.py:`invalidate_user_subjects_cache_now_and_on_commit` | 静的読解。`subject_service.py:141-162` を読み、`use_cache=False` では書き戻さないことを確かめた。実験は行っていない。 |

V3 は読んで確かめた。TC-05 が本当にキャッシュを通っている根拠は次のとおり。
- `LOCMEM` は `settings.CACHES` の全 alias を LocMem に差し替え、`override_settings` で適用している。`cache_service.default_cache` は呼ぶたびに `caches['default']` を引く（`cache_service.py:30-31`）ので、差し替えが効く。
- 保存の前に `GET` と `annotate_count=True` の呼び出しを行い、`user_subjects_cache_key` で作った 2 つのキーの両方に値が入っていることを、`cache_service.get_subjects_cache` で確かめている（正の対照）。このキーは読む側と同じ関数で作る。`_generate_key` も書く側と読む側で同じなので、キーの食い違いによる空振りは起きない。
- 保存は `[数学, 物理]` の足すだけ。`bulk_create` は `post_save` を送らないので、サービスが明示的に呼ぶ消去が効かないとキャッシュが残り、テストは落ちる。
- 保存の後の `GET` は、キャッシュに残った古い `[数学]` が返れば失敗する。新しい一覧を要求しているので、同語反復ではない。
- `django_capture_on_commit_callbacks(execute=True)` で `on_commit` を実行しているので、`db` フィクスチャのトランザクションの中でも確定後の消去が動く。

> ITEM: V3 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I494] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | トランザクション | `replace_user_subjects` は `@transaction.atomic` の中で、先に `delete()`、次に `bulk_create` を行う。`bulk_create` が途中で失敗すると例外が atomic を抜け、削除もロールバックされる。`on_commit` の再消去はロールバックで捨てられる。TC-11 は `bulk_create` を例外にし、`math` の削除が先に走る形（`removed={math}`）にしてある。そのため「外した行が戻る」ことを本当に検証している。pytest の `db` フィクスチャの中では atomic がセーブポイントになるが、それでもロールバックは効く。削除のシグナルが失敗の前にキャッシュを消す（`now` 側）が、DB は元のままなので害はない。 | `backend/problems/services/user_subject_service.py:21-45`、`backend/problems/tests/test_I494_user_subjects.py` の `test_rollback_on_failure` | 静的読解。`mock.patch.object(UserSubjectAccess.objects, ...)` は同じマネージャのインスタンスに効く。実験は不要と判断した。 |

反証失敗（新規の Critical/High なし）。探索した仮説:
- 途中で失敗したときに、削除だけが確定して 0 件になる。
- テストが空振りしている（削除が先に走らず、ロールバックを見ていない）。
- 失敗時に確定後の消去が残り、古いキャッシュが入る。

> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 65d03b13b7960908b78e5f9b4146e642f56ff5c6
ROUNDS: 1
VERDICT: OK
