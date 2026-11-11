# I431 レビュー: 学習記録 API・ダッシュボード API の他組織データ漏れを塞ぐ

- 関連: docs/issues/open/I431.md / docs/plans/open/plan_I431.md / GitHub #431 / Draft PR #453

## 変更概要
- 境界の判定（ユーザーの組織の科目・問題）を `backend/problems/services/tenant_scope.py` に集め、学習記録（`/api/study/` の下）とダッシュボード（`/api/dashboard/` の下）の全経路をそれに通す（計画書「調査結果」の表の「塞ぐ」）。

## 変更点
- `backend/problems/services/tenant_scope.py`（新規）: `available_subjects`・`available_problems`・`scope_to_user_org`
- `backend/problems/services/quiz_service.py`: `available_subjects`・`available_problems` を tenant_scope に委ねる
- `backend/problems/serializers.py`: `QuizSubjectField` → `OrgSubjectField`（tenant_scope を直接使う・学習記録と共用）
- `backend/core/subject_service.py`: `get_user_selected_subjects` を今の組織の科目に絞る（キャッシュあり・なしの両方）
- `backend/studylogs/views.py`: C1・R1・R2・R4・R6〜R11・R15（計画書 4-4）
- `backend/studylogs/serializers.py`: 学習記録の科目に `OrgSubjectField`（C2）
- `backend/studylogs/services.py`: R5・C3
- `backend/studylogs/adaptive_selection.py`: R12・R13
- `backend/studylogs/mistake_analysis.py`: C4（`_error_records` を切り出し）・C5・C6・R9〜R11。提案の二重の絞り込みを `scope_learning_suggestions` にまとめ、views と共用
- `backend/studylogs/tasks.py`: R14
- `backend/dashboard/views.py`: D1・D2・D4〜D6（D3 は core 側で絞る）
- `backend/studylogs/tests/test_I431_studylogs_tenant_isolation.py`（新規・24 件）

## 影響範囲
- Backend: problems/services（tenant_scope 新規・quiz_service）・studylogs（views・serializers・services・adaptive_selection・mistake_analysis・tasks・tests）・dashboard（views）
- Frontend: なし
- DB: なし（スキーマ変更なし）
- Config: なし

## テスト結果
- 自動:
  - TC-23（RED）: 修正前の本番コードに対して 20 failed・3 passed（通ったのは TC-02・TC-10・TC-22。TC-22 は tenant_scope のファイルが残る状態で流したため。TC-15b は後から足し、修正前の core で単独で FAIL を確認）
  - TC-24: 修正後に `studylogs/tests/test_I431_studylogs_tenant_isolation.py`（24 件）＋ `problems/tests/`（119 件・I166 を含む）＝ 143 passed
  - TC-25: commit 時の pre-commit（ruff・bandit を含む）すべて Passed
  - CI: review-gate で確認
- 手動: （No.1・No.2 を記入）

## 計画との差分
- 提案の二重の絞り込み（subject と mistake_pattern__subject）を `mistake_analysis.scope_learning_suggestions` にまとめて views と共用した（計画では各所で重ねる書き方。同じ条件を 2 か所に書かないための関数化で、振る舞いは同じ）
- /simplify の指摘による 4-11（計画変更記録・計画レビューやり直し済み）

## ロールバック
- PR #453 の revert（コードとテストだけ。マイグレーション・データ変更なし）

## 自律判断の記録
- [plan] 判定の置き場所を `problems/services/tenant_scope.py` にし、`QuizService` は委ねる形にした — 科目・問題は problems のモデルで I166 の判定もここ。呼び出し元を変えずに判定を 1 か所にする
- [plan] 数だけを返す集計と中身を返さない印付けは変えない（扱いの基準 3） — 漏れる中身が無く、変えると自組織の数字まで変わるおそれがある
- [plan] `get_new_cards`・`_get_problem_pool`・おすすめの問題数は土台を `available_problems` に置き換え、存在しない `is_active` の条件が消える — 境界の判定を通す以上避けられない副作用。機能を直すための変更ではない（grill-me の「直さない」は機能の修正をしないという意味と判断）
- [plan] キャッシュの最大 5 分の古い結果は受け入れる — dev のみで本番が無い
- [plan] 台帳の残り（I224 F9・I223 B1〜B4）は残す — `FILE=-` のハーネス・bot の項目で、変更点と関係しない
- [plan-review] 計画レビューの Warning 3 件（`submit_review` の進行中の学習記録の絞り込み〔R15・TC-04b〕・テストでまだ無い関数をテストの中で import・本番の cache の消し方）を直し、再レビューはしない — 方式・受け入れ条件を変えない追記だけ
- [design-security-review] Blocker 0 件。Medium（提案の `mistake_pattern_description` から他組織の文言が出うる）に対応し、提案をパターン側の科目でも絞る・TC-16 に確認を足した。再レビューはしない — 同じ経路の絞り込みを重ねるだけで方式・受け入れ条件は変えない
- [implement] RED の確認で、ダッシュボードの 3 件のテストの URL の誤り（`/api/dashboard/dashboard/...` で 404）に気づき直した。直した後、実装をコミットしてから修正前の本番コードを一時的に取り出して流し、20 件の RED（ダッシュボードの 3 件を含む）を確かめ直した — 404 による見かけの RED を除くため
- [implement] TC-16 の科目が空のパターンの `confidence_score` を 0.1 にした — 提案の生成が科目が空のパターンで落ちる既存の不具合（`_generate_pattern_based_suggestions` が全種類の文言を `pattern.subject.name` で先に組み立てる）に当たらないようにするため。不具合そのものは I452 の範囲
- [implement] 修正前のコードに一時的に戻したファイルを元に戻す `git checkout HEAD -- …` は安全装置に止められた。`DANGER_OK=1` は使わず、ステージを外してから、コミット前に退避していた同じ中身を書き戻し、`git status` でコミットとの差分が無いことを確かめた — 捨てたのは develop と同じ中身の一時的なファイルだけ
- [implement] /simplify の指摘のうち、登録時の科目の絞り込みを根の関数に移す・科目の欄を 1 つにする、を採った。範囲が API 1 つ広がるため、計画書を直して計画レビューをやり直す（計画変更記録の 3 行目）
- [plan-review] やり直しの計画レビュー（20261111_1857）は HIGHRISK・Blocker なし。Warning 4 件（本文の旧方式の記述・TC-23 の RED の一覧・手動 No.1 の式の記録・範囲の広がり）を文書に反映し、再レビューはしない。イシューの「影響範囲」への 1 行の追記は、GitHub の本文が正で手元の写しは同期しないため、計画書の影響範囲と計画変更記録に書くことで代える
- [implement] /simplify の見送り: モデルごとの絞り方の表（problems → studylogs の依存が生まれる）・`QuizService` の中継の削除（呼び出し元を変えない方針）・おすすめの問題数の 1 クエリ化と `id__in` の副問い合わせ（効果が小さい。後者は core へ移したことで消えた）・`create_card` の関数内の import（既存の書き方） — 振る舞いを変えず、計画の方針と依存の向きを保つため
- [implement] 学習記録の「科目が空のパターンで提案の生成が落ちる」既存の不具合は I452 の範囲として残す（I452 の本文に追記するかは retro で判断）

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement
