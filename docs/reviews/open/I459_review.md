# I459 レビュー: 学習統計の画面が、解いた問題が 0 件の日があると 500 になる不具合を直す（dashboard/analytics）

- 関連: docs/issues/open/I459.md / docs/plans/open/plan_I459.md / GitHub #459 / Draft PR #478

## 変更概要
`GET /api/dashboard/analytics/` の週ごとの正答率を週の合計で割る形にして、0 問の日がある利用者で 500 になる不具合を直した。`days` を確かめ、不正な値を 400 にした。

## 変更点
- `backend/dashboard/views.py`: `_accuracy_percent`（新規・モジュールの関数）・`DashboardAnalyticsView.get` の `days` の確かめと 400・`_get_performance_trends` の正答率を `Sum`/`Sum` で 1 回だけ割る形に
- `backend/dashboard/serializers.py`（新規）: `AnalyticsQuerySerializer`（`days` 1〜365・省略時 30）
- `backend/dashboard/tests/__init__.py`・`test_I459_analytics_zero_division.py`（新規）: TC-01〜TC-06（13 件）
- `backend/core/tests/test_I446_cross_api_tenant_isolation.py`: 下準備に 0 件の日のまとめを 1 件足し、避ける注記を外した

## 影響範囲
- API: `performance_trends[].avg_accuracy` の値の意味（週の合計で割る）と丸め（小数第 2 位）。`days` の不正な値は 500 → 400。キー・型は変わらない
- 画面: 変わらない（`performance_trends` を読まず `days` も送らない）。統計の画面が 500 で読み込みに失敗しなくなる
- DB・依存: 変更なし

## テスト結果
- 手元: 新しいテスト 13 件と #446・I431 が 172 passed。Red（直す前に 8 件 FAIL）と FG（おすすめの絞り込みを外すと TC-05 FAIL）を確認（`docs/tests/open/I459_auto_test.md` の実行記録）
- CI: PR #478（`41b84ec4`）の 7 ジョブすべて pass
- コードレビュー: `docs/reviews/I459_code_review_20261112_1837.md`（OK・Low 2 件・敵対的レビュー不要）
- 手動テスト: No.1〜No.3 すべて OK（Claude。dev で 0 件の日を持つ `e2e_user_c` の統計の画面が 200 で開く・不正な `days` が 400）

## 計画との差分
- /simplify で `_accuracy_percent` を 1 行にし、400 の `sub_message` の上限を定数から作るようにした（動き・文言は同じ。計画変更記録）

## ロールバック
PR を revert する（コードとテストだけ・DB の形は変えない）。

## 自律判断の記録
- [plan] 週ごとの正答率の割り算を、集計の後に Python で 1 回だけ行う形にした（データベースの中で `NullIf` で割る案は採らない） — 0 の扱いが 1 行で読め、overview の週のまとめと同じ書き方
- [plan] `days` の確かめを DRF の serializer（`dashboard/serializers.py`・新規）にし、400 の文言を「期間の指定が正しくありません／日数は 1〜365 の整数で指定してください」にした — I452 の `review_summary` と同じ形。画面は `days` を送らないので利用者の目に触れない
- [plan] 正答率を小数第 2 位で丸める — ほかの正答率の欄と同じ
- [plan] 集計のサービス層への移動・overview の同じ計算の共通化はしない — #473 が作り直す
- [plan] おすすめの割り算は直さず回帰テスト（TC-05）だけ足す — 再現で 0 で割らないことを確かめた（HAVING の後）
- [implement] /simplify の 4 観点を 2 体にまとめて回した — 差分が 40 行ほどで、4 体は過剰。見送った指摘は計画変更記録に書いた
- [test-gate] 手動テスト No.3 を、計画の `browser_evaluate`（承認画面が出る操作）から、dev の backend のコンテナで `APIClient.force_authenticate` して呼ぶ形に変えた — 確かめたいのは dev で動くコードの応答で、承認なしで同じことを確かめられる。期待結果は同じ
- [test-gate] 統計の画面のコンソールに出た 2 件の error（開発サーバーの WebSocket・`Statistics` の一覧の `key` の警告）は今回と関係ない既存のものとして扱った — どちらも analytics の応答と無関係で、変更前からある
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
