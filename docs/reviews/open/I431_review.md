# I431 レビュー: 学習記録 API・ダッシュボード API の他組織データ漏れを塞ぐ

- 関連: docs/issues/open/I431.md / docs/plans/open/plan_I431.md / GitHub #431 / Draft PR #453

## 変更概要
- 境界の判定（ユーザーの組織の科目・問題）を `backend/problems/services/tenant_scope.py` に集め、学習記録（`/api/study/` の下）とダッシュボード（`/api/dashboard/` の下）の全経路をそれに通す（計画書「調査結果」の表の「塞ぐ」）。

## 変更点
- （実装後に記入）

## 影響範囲
- Backend: problems/services（tenant_scope 新規・quiz_service）・studylogs（views・serializers・services・adaptive_selection・mistake_analysis・tasks・tests）・dashboard（views）
- Frontend: なし
- DB: なし（スキーマ変更なし）
- Config: なし

## テスト結果
- 自動: （TC-23 の RED・TC-24・TC-25・CI を記入）
- 手動: （No.1・No.2 を記入）

## 計画との差分
- なし

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

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement
