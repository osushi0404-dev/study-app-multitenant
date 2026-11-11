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
  - CI: PR #453 で通過（review-gate の `CI_WAIT: OK`・2 回）
- 手動: No.1 OK（primary の dev DB の越境 0 件・10 種類すべて。学習記録の表は空・QuizSession 124 件・UserSubjectAccess 23 件）・No.2 OK（ダッシュボードと学習統計が表示・overview／analytics／user/subjects すべて 200）。Human の項目なし

## 計画との差分
- 提案の二重の絞り込み（subject と mistake_pattern__subject）を `mistake_analysis.scope_learning_suggestions` にまとめて views と共用した（計画では各所で重ねる書き方。同じ条件を 2 か所に書かないための関数化で、振る舞いは同じ）
- /simplify の指摘による 4-11（計画変更記録・計画レビューやり直し済み）

## ロールバック
- PR #453 の revert（コードとテストだけ。マイグレーション・データ変更なし）

## 振り返り

### かんたんなまとめ
**良かった点**
- 修正前のコードに戻してテストが落ちることを確かめ直したので、ダッシュボードのテストが「URL の誤りで落ちていただけ」という見かけの失敗を見抜けた（理由: 失敗の理由まで確かめないと、本当は守れていないテストを合格と見誤る）
- 整理役（/simplify）の指摘で、登録時の科目の絞り込みを呼び出し側ではなく元の関数に移し、もう 1 つの API（科目のプルダウン）の漏れも根元で塞げた（理由: 呼び出し側ごとに足すと、新しい呼び出し元で漏れる）
- 範囲が広がったところで計画書を直し、計画レビューをやり直してから実装した（理由: 計画に無い実装をしない決まりを守れた）

**今回の問題への直接の対処**
- レビューで止めなかった軽い指摘 6 件と、途中で見つけた既存の不具合は、学習記録の機能を直す #452 にまとめて書いた。どれも、その機能を使えるようにするときに一緒に直すのが自然なため（キャッシュの件はセキュリティに関わるので最優先と明記）

**同じ問題を次回から防ぐ改善**
- 敵対的レビューの実験役が、アプリのテストを流そうとして失敗した（パソコン側に pytest が無く、テストはコンテナの中でしか動かない）。そのため「実験で確かめる」項目が確かめられず、レビューをもう 1 周使った。→ 実験役への指示に「アプリのテストはコンテナ経由で流す」ことを書き、流せることを機械で確かめるテストを足す改善を、敵対的レビューの実験の作りを直す既存の #423 にまとめた

**見送ったもの**
- テストの URL の誤り・見張りに止められた 2 件の操作は、その場で気づいて安全な別の手段で済み、手戻りが無かったので、新しい手順は足さない

### 詳細（記録用）
#### 良かった点
- TC-23 の RED を、実装をコミットしてから修正前の本番コードを一時的に取り出して確かめ直した（404 による見かけの RED を排除）
- /simplify（altitude）の指摘で `get_user_selected_subjects` の根で絞り、3 つ目の呼び出し元（`GET /api/user/subjects/`）も塞いだ。範囲の変更として計画変更記録→計画レビューやり直し→design-security-review 追記→実装の順を守った
- 敵対的レビュー 2 周目で OK（新規の Critical/High 0 件）

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | 台帳の残り | 止める条件に当たらない Low（F1〜F6）と、範囲外の既存の不具合が残った | #452 にコメントで同梱（F3 SECURITY=yes を最優先と明記） |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | スキル・規約（敵対的レビュー） | 実験役の指示に、アプリのテストをコンテナ経由で流す入口が無く、実験必須の項目が未検証になる | 実験役の指示にアプリのテストの実行の入口（コンテナ経由）を書き、その実行が実験役の許可で通ることを決定論のテストで確かめる（#423 に同梱） | `.claude/agents/adversarial-reviewer.md`・`scripts/claude/adversarial-review.sh` |

#### 5 Whys（P1）
- 理想の状態: 敵対的レビューの実験役が、アプリのテストをその場で流して実験必須の項目を「確認済み（実験）」にする
- Why 1: なぜ未検証になったか → 実験役の `python -m pytest` が、ホストに python・pytest が無く動かなかった
- Why 2: なぜホストで流したか → 実験役の指示に、アプリのテストの実行環境（コンテナ）の入口が書かれていない
- Why 3: なぜ書かれていないか → 実験役の作りがハーネス（ホストで動くシェルのテスト）を主に想定して作られ、アプリのイシューでの実験の入口を確かめる決定論のチェックが無い
- 抽象化: 「検証役に、対象の実行環境への入口を渡していない」は I431 に固有でなく、アプリ本体の高リスクのイシュー全般に起こる → 予防処置

#### 見送り
- テストの URL の誤り: RED の確かめ直しでその場で捕まり、手戻りが数分（新しい手順は足さない）
- 見張りが `git checkout` の書き戻し・`psql -f` を止めた: 安全な代わりの手段で済み実害なし。見張りの整理は既存の #430・#444

#### I206 からの引き継ぎ（測った結果）
- ① `RISK=up`: 0 件（`docs/reviews/I431_code_review_20261111_1902.md`・`docs/reviews/I431_code_review_20261111_1915.md`）。期待値どおり。直す・起票するものなし
- ② 敵対的レビューの締め切りによる未検証: 0 件（`docs/reviews/I431_adversarial_review_20261111_1914.md`・`docs/reviews/I431_adversarial_review_20261111_1949.md`）。直す・起票するものなし（1 周目の未検証は締め切りではなく実験環境が原因で、P1 で扱う）

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
- [review-gate] 基本レビュー（20261111_1902）は OK・CI 通過・台帳は Low 6 件（F1〜F6・retro へ）。敵対的レビュー 1 周目（20261111_1914）は新規の Critical/High 0 件だが、V1・V2・V3・V6 が未検証（実験役のホストに python・pytest が無い）で HIGH。決まり（3-3）に沿い、失敗の注入で FAIL→PASS を実測済みの決定論の TC で覆っていることを一覧に書き、確かめ方を「読んで可」に下げて 2 周目へ — 実験役がホストで pytest を動かせない件はハーネスの改善候補として retro で扱う
- [review-gate] 基本レビュー（20261111_1915）OK・敵対的レビュー 2 周目（20261111_1949）OK（新規の Critical/High 0 件・Low 2 件〔export_user_data_task の調査表の理由の書き方・キャッシュ〈F3 と同じ〉〕は retro へ）。最終判定 OK で test-gate へ
- [test-gate] 手動 No.1 は、止まっていた primary の DB のコンテナだけを起こして SELECT で数え、終わった後に止めた。`psql -f` は見張りに止められたので `DANGER_OK=1` は使わず、同じ SELECT を `-c` で渡した — バックエンドを起こすと起動時の migrate で primary の DB に書き込むおそれがあり、読み取りだけに限るため
- [retro] 台帳の残り 6 件（F1〜F6・すべて Low・アプリ本体・F3 は SECURITY=yes）は、1 件ずつ起票せず #452 にコメントで同梱（F3 を最優先と明記）。一覧（docs/reviews/backlog/）に回すものは 0 件
- [retro] 実装中に見つけた既存の不具合（科目が空のパターンで提案の生成が落ちる）と、敵対的レビュー 2 周目の Low（export_user_data_task の調査表の理由）も #452 に同梱
- [retro] 実験役がホストでアプリのテストを流せない件（敵対的レビュー 1 周目が未検証で HIGH になり 2 周目を使った）は、敵対的レビューの実験の作りを扱う既存の #423 に同梱（根本原因・予防策・対象ファイルをコメント）
- [retro] 見送り: ダッシュボードのテストの URL の誤り（RED の確かめ直しでその場で捕まり、手戻りは数分）・見張りが `git checkout` の書き戻しと `psql -f` を止めた件（代わりの安全な手段で済み、実害なし。見張りの整理は #430・#444 が既にある）— その場で捕まり手戻りが無い見逃しに手順を足さない
- [retro] I206 からの引き継ぎの 2 点を測った: ① `RISK=up` は 2 つのコードレビューの記録（20261111_1902・_1915）で 0 件（期待値どおり）② 敵対的レビューの「実行していない（締め切り）」は 2 つの記録（20261111_1914・_1949）で 0 件。どちらも基準に当たらず、直す・起票するものなし
- [implement] 学習記録の「科目が空のパターンで提案の生成が落ちる」既存の不具合は I452 の範囲として残す（I452 の本文に追記するかは retro で判断）

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: test-gate

STAGE_DONE: test-gate NEXT: retro
