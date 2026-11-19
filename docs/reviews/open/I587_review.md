# I587 レビュー: 問題・解説の画像を DB に保存し、組織の境界を確かめる API から返す

## 変更概要
- （実装前）画像の中身を `media_asset_contents`（`MediaAsset` と 1 対 1・`bytea`）に保存し、`GET /api/media/<id>/` からログインと組織の境界を確かめて返す。画面は axios で中身を取って表示する。今あるファイルは 0025 で DB に移し、ファイルの無い行を消す。古い画像の列（0026）・`/media/` の配信・見本のファイルを外す

## 変更点
- （実装前）計画書 4 のとおり

## 影響範囲
- Backend/Frontend/DB/Config: 計画書 3 のとおり

## テスト結果
- 自動: 実装前のため未実行
- 手動: 実装前のため未実行

## 計画との差分
- なし（実装前）

## ロールバック
- 計画書 7 のとおり

## 自律判断の記録
<!-- 各段階が、止めずに自分で決めたことを `- [段階] 決めたこと — 理由` で足す。段階の結線の行（STAGE_DONE:）はこのファイルの末尾に足す -->
- [plan] 開発の DB での保存方式の試し（一時表の `ALTER TABLE ... SET STORAGE`）は、見張りが危険な SQL として止めたのでやめ、テストの DB で確かめる TC-03 に回した — 開発の DB を変えずに同じ性質を CI で毎回確かめられる
- [plan] Danger Ops の承認は、実装の最初（ステップ 1・マイグレーションのファイルを書く前）にもらう — I492 で review-gate のコンテナの起こし直しが承認の前のマイグレーションを流した（#579 は未完了）。承認の後なら流れても承認済みの操作になる
- [plan-review] 計画レビュー（20261119_1527）は高リスク判定 Yes（Blocker なし）。Warning 5 件はすべて直し、方式・範囲・受け入れ条件を変えないので再レビューはしない（計画変更記録）— AC14 は読み替えをやめ、捨てる DB のコンテナに向けた backend を `docker compose run --use-aliases` で起こして画面で確かめる形にした（ユーザーに聞かずに元の受け入れ条件のまま確かめられるため）
- [design-security-review] Blocker 0・Medium 2・Low 4（設計）。Medium の「checksum が null の行の ETag」は必須防御条件として 4-5・4-8・TC-04・TC-13 に足した。方式・範囲・受け入れ条件を変えないので計画レビューはやり直さない — 追加は守りの条件とテストの場合だけ
- [implement] ステップ 1 の数え直し（M1）と控え（M2）を済ませ、Danger Ops の承認を求めて止まる（止める条件 2）— マイグレーションのファイルを書く前に承認を得る（計画書 5 のステップ 1・R1）
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
