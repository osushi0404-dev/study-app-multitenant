# 敵対的レビュー [I494]（別プロセス・2026-11-16 13:12）

- 見た範囲: 65d03b13b7960908b78e5f9b4146e642f56ff5c6...9dac41914de1d5f3b3d28778d8f6685e734cc889
- 所要時間: 19 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: backend を起こして確かめた（4 秒・締め切りの外）
- 一覧: docs/plans/open/plan_I494.md の「## 必ず確かめる項目」（5 項目）
- 引き継ぎ: 引き継がない（I494_adversarial_review_20261116_1224.md の REVIEWED_COMMIT 65d03b13b7960908b78e5f9b4146e642f56ff5c6 から HEAD までに記録の場所の外が変わった: frontend/src/components/dashboard/StartQuizCard.tsx frontend/src/components/settings/LearningSubjectsCard.tsx frontend/src/components/settings/__tests__/LearningSubjectsCard.test.tsx frontend/src/constants/routes.ts）

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
| 1 | 報告あり | 13 秒 | 0 | 0 | $0.1899 | ― | ― | ― |
| 2 | 報告あり | 12 秒 | 0 | 0 | $0.1746 | ― | ― | ― |
| 3 | 報告あり | 12 秒 | 0 | 0 | $0.1741 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I494] ── 観点: 1. ロジック回避・実機 repro

## findings
反証失敗（新規指摘なし）。探索した仮説:
- 本文の組織を使った越境（V1）: `validate_subject_ids` は `self.context['request'].user` から `available_subjects(user)` を引く（`serializers.py:51-53`）。本文から組織を取らない。`available_subjects` は `organization_id=user.organization_id` の完全一致だけで絞る（`tenant_scope.py:18-22`）。他組織・全体共有・存在しない番号は、どれも「件数が合わない」ことで同じ文言の 400 になる。検証は書き込みの前なので、400 のときは割り当てが変わらない。
- サービスの単独呼び出し（V2）: `replace_user_subjects` は `available_subjects(user).filter(id__in=…)` で `wanted` を作る（`user_subject_service.py:26`）。他組織・全体共有の番号は `wanted` に入らず、`added` にならない。シリアライザを通らなくても書かれない。
- 組織なしの利用者（V5）: `available_subjects` は `organization_id is None` なら `Subject.objects.none()` を返す（`tenant_scope.py:20-21`）。シリアライザとサービスはどちらもこの関数を使うので、組織なしの利用者は科目を選べず、全体共有（`organization=None`）にも当たらない。組織のある利用者も完全一致でしか選べないので、全体共有は選べない。`AvailableSubjectsView` の読み込みは差分の範囲外で、今回は読んでいない。ただし、観点 1 の既存報告では同じ関数を使うとされている。
- 範囲外の Low: 既知の台帳 F2・F3 と同じ種類の指摘（前の組織の割り当て行の削除、検証後の削除競合）は再報告しない。

> 補足: `AvailableSubjectsView` は実ファイルを開いて確かめていない。V5 の「3 か所」のうち 2 か所は読んで確かめ、View の 1 か所は既知の報告に依拠している。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I494] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。探索した仮説:
- TC-05 がキャッシュを素通りしている可能性: 全 alias を LocMem に差し替え（`override_settings`）、`caches["default"].clear()` の後に保存前の `GET` でキーに値が入ることを確かめている。読む側のキーと同じ関数でキーを作るので、キーの食い違いで空振りすることはない。
- 保存が「足すだけ」の `bulk_create` なので、`post_save` に頼る消去では通らない。サービスが明示的にキャッシュを消さないと、保存後にキーが残って落ちる。
- `django_capture_on_commit_callbacks(execute=True)` で確定後の消去も実行される。
- 今回の差分はフロントと記録だけで、バックエンドのテストは変わっていない。既知の指摘（TC-05 が確定後の消去を単独では確かめていない）の再報告は避けた。

> ITEM: V3 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I494] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。探索した仮説:
- 途中で失敗したときに、外した行が戻らない。`replace_user_subjects` は `@transaction.atomic` で、`delete()` も `bulk_create` も同じトランザクションの中にある。`bulk_create` が失敗すると例外が atomic を抜け、削除もロールバックされる。
- 失敗時に古いキャッシュが残る。確定後の消去（`on_commit`）はロールバックで捨てられる。失敗の前に「今すぐ消す」側が動いても、DB は元のままなので害はない。
- 外すだけの保存で `added` が空になり、`bulk_create` もキャッシュの消去も呼ばれない。外す操作は `delete()` のシグナルで消えるので、実害はない（既知の Low 指摘と同じ範囲）。
- 今回の差分は、フロントのアクセシビリティ属性の追加と定数の移動だけ。書き換えのサービスと API は変わっていないので、V4 の前提は崩れていない。

実験は行っていない。読んで確かめた。

> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 9dac41914de1d5f3b3d28778d8f6685e734cc889
ROUNDS: 1
VERDICT: OK
