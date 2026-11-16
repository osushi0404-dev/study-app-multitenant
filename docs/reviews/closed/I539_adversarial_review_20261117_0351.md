# 敵対的レビュー [I539]（別プロセス・2026-11-17 03:51）

- 見た範囲: 280b0d8ab659465cceb3c4e9131bda59cf3455df...a8d258965e42966de9da9ef7277b072a8c63563f
- 所要時間: 21 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: backend を起こして確かめた（17 秒・締め切りの外）
- 一覧: docs/plans/open/plan_I539.md の「## 必ず確かめる項目」（8 項目）
- 引き継ぎ: 引き継がない（I539_adversarial_review_20261116_2152.md の REVIEWED_COMMIT 280b0d8ab659465cceb3c4e9131bda59cf3455df から HEAD までに記録の場所の外が変わった: backend/api/views/user_subjects.py backend/core/subject_service.py backend/openapi.yaml backend/problems/serializers.py backend/problems/tests/test_I494_user_subjects.py backend/problems/tests/test_I539_user_subjects_problem_count.py backend/studylogs/tests/test_I431_studylogs_tenant_isolation.py e2e/tests/auth.spec.ts e2e/tests/quiz-session.spec.ts frontend/src/components/dashboard/StartQuizCard.tsx frontend/src/hooks/useUserSubjects.ts frontend/src/pages/__tests__/Dashboard.test.tsx frontend/src/services/subjectService.ts frontend/src/types/api/schema.d.ts）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V8 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V7 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 16 秒 | 0 | 0 | $0.2450 | ― | ― | ― |
| 2 | 報告あり | 14 秒 | 0 | 0 | $0.2553 | ― | ― | ― |
| 3 | 報告あり | 17 秒 | 0 | 0 | $0.2641 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I539] ── 観点: ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| なし | - | 反証失敗（新規指摘なし） | - | 静的読解のみ。実験は流していない |

反証失敗（新規指摘なし）。探索した仮説は次の 3 本です。

1. **今回の差分（AC13）が V1・V2・V5・V8 の担当範囲に触れていないか。**
   - 差分の本体は `subject_service._problem_count`、`UserSubjectSerializer` の `problem_count`、`UserSubjectsView` の `annotate_count=True` です。
   - 登録（`UserRegistrationSerializer`）・`invitable()`・マイグレーション 0023 の変更は、差分に含まれません。
   - 前周（`docs/reviews/closed/I539_adversarial_review_20261116_2152.md`）で確認した TC-06・TC-07・TC-07b・TC-14〜16・TC-23 の根拠は変わりません。
   - 招待の組織の判定は、今回の変更で壊れていません。
2. **`_problem_count` の分岐の抜け。**
   - `Count('problems', filter=Q(problems__is_deleted=False))` を、キャッシュ経路・DB 経路・`get_user_subjects` の 3 か所で共通の関数にしています。
   - 条件は出題の対象 `available_problems`（`is_deleted=False`）と一致します。
   - 選択肢の結合による重複計上は、TC-24 の選択肢 4 つの問題で防いでいます。
3. **キャッシュが問題数の古さや他組織の科目を持ち込まないか。**
   - キャッシュに入るのは科目の番号だけです。
   - 問題数は毎回 DB で数え直します。
   - 組織は `get_user_selected_subjects` が今の組織に絞るので、他組織の科目 Z は入りません（TC-24）。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> ITEM: V5 RESULT=read
> ITEM: V8 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I539] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。探索した仮説は 3 つです。

- **TC-03・TC-04 が組織の数の前後を比べているか。**
  - 比べています。`test_failed_registration_leaves_no_org` は、`Organization.objects.count()` を `orgs_before` に取り、失敗の後に等しいことを見ています（`test_I539_personal_org_signup.py` の 148-158 行）。
  - 空でない `subject_ids` の場合も、同じ形で前後を比べています（233・241 行）。
- **TC-33 が失敗の応答を作り、ボタンが無効で `register` が呼ばれないことを見ているか。**
  - 見ています。`mockGetSubjects.mockRejectedValueOnce(new Error('500'))` で失敗の応答を作っています（`Register.test.tsx` の 141 行）。
  - そのうえで `toBeDisabled()`（147 行）と `mockRegister` が `not.toHaveBeenCalled()`（151 行）を確かめています。
- **今回の差分（AC13 の追加分）が V4・V7 を壊していないか。**
  - 差分は `problem_count` の数え方とテストの期待値の変更だけです。登録・登録画面には触れていません。

前の周から既知の Low（TC-04 は検証が先に弾くので、`atomic` の効きまでは見ない。TC-33 の Enter 送信は無効なボタンでは暗黙の送信が起きないので、守りを外しても落ちないおそれがある）は、そのまま残っています。新規ではありません。

> ITEM: V4 RESULT=read
> ITEM: V7 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I539] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。探索した仮説は次の 3 本。

- **V6（科目作成で学ぶ科目が増える範囲）**
  - `backend/problems/views.py:124` は、作った科目の組織が `is_individual` のときだけ `UserSubjectAccess` を作る。
  - `is_individual` を True にするのは `backend/accounts/services.py:46` と、マイグレーション 0023 の個人用の組織の作成だけだった。
  - 学校の組織と、種類が既定の `personal` の招待用の組織は `is_individual=False` のままなので、学ぶ科目は増えない。
  - 科目の作成と学ぶ科目の追加は同じ `transaction.atomic` の中にあり、片方だけ残る経路は見つからなかった。
- **V3（個人用の組織の管理者が他組織を横断して見る）**
  - 科目の作成は `request.user.organization_id` に固定されていて、本文から組織を指定する経路は無い。
  - 一覧と番号指定は既存の組織での絞り込みに乗っている。
  - 今回の差分で新しい読み取りの経路は増えていない。増えた `problem_count` は `get_user_selected_subjects` が絞った自組織の科目だけを数える（TC-24 の科目 Z が確認）。
  - 登録を `invitable()` で止めているので、個人用の組織に他人が入ってくる経路も無い。
- **差分で入った AC13 の追加分（数と出題の食い違い）**
  - `_problem_count()` は `is_deleted=False` で数えていて、出題の条件と合っている。
  - キャッシュ経路・DB 経路・`get_user_subjects` の 3 か所がそろっている。
  - 既知の指摘（F1 など）と重なるものは数えていない。

実験は不要と判断した（読解のみ）。

> ITEM: V3 RESULT=read
> ITEM: V6 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: a8d258965e42966de9da9ef7277b072a8c63563f
ROUNDS: 1
VERDICT: OK
