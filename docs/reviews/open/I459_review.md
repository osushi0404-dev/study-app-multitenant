# I459 レビュー: 学習統計の画面が、解いた問題が 0 件の日があると 500 になる不具合を直す（dashboard/analytics）

- 関連: docs/issues/open/I459.md / docs/plans/open/plan_I459.md / GitHub #459 / Draft PR #478

## 変更概要
（実装後に記入）`GET /api/dashboard/analytics/` の週ごとの正答率を週の合計で割る形にして、0 問の日がある利用者で 500 になる不具合を直す。`days` を確かめ、不正な値を 400 にする。

## 変更点
（実装後に記入）

## 影響範囲
（実装後に記入）

## テスト結果
（実装後に記入）

## 計画との差分
（実装後に記入）

## ロールバック
PR を revert する（コードとテストだけ・DB の形は変えない）。

## 自律判断の記録
- [plan] 週ごとの正答率の割り算を、集計の後に Python で 1 回だけ行う形にした（データベースの中で `NullIf` で割る案は採らない） — 0 の扱いが 1 行で読め、overview の週のまとめと同じ書き方
- [plan] `days` の確かめを DRF の serializer（`dashboard/serializers.py`・新規）にし、400 の文言を「期間の指定が正しくありません／日数は 1〜365 の整数で指定してください」にした — I452 の `review_summary` と同じ形。画面は `days` を送らないので利用者の目に触れない
- [plan] 正答率を小数第 2 位で丸める — ほかの正答率の欄と同じ
- [plan] 集計のサービス層への移動・overview の同じ計算の共通化はしない — #473 が作り直す
- [plan] おすすめの割り算は直さず回帰テスト（TC-05）だけ足す — 再現で 0 で割らないことを確かめた（HAVING の後）
STAGE_DONE: plan NEXT: plan-review
