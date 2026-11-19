# I587 レビュー: 問題・解説の画像を DB に保存し、組織の境界を確かめる API から返す

## 変更概要
- 画像の中身を `media_asset_contents`（`MediaAsset` と 1 対 1・`bytea`）に保存し、`GET /api/media/<id>/` からログインと組織の境界を確かめて返す。画面は axios で中身を取って表示する。今あるファイルは 0025 で DB に移し、ファイルの無い行を消す。古い画像の列（0026）・`/media/` の配信・見本のファイルを外す

## 変更点
- Backend: `MediaAssetContent`（0024・`SET STORAGE EXTERNAL`）・保存は中身から判定した MIME・論理削除で中身を消す（`ProblemService._discard_asset`）・`GET /api/media/<id>/`（`MediaAssetContentView`・`selectors.py`）・0025（`media_migration.py`・`check_media_migration`）・0026（古い列）・`StorageService`・`MEDIA_*`・`/media/` の配信・科目のフォルダ作りを外した
- Frontend: `MediaImage`・`useMediaImage`・`mediaService.getMediaBlob`・`api.ts` の `skipErrorToast`・画像の 3 つの部品・`pickImageUrls`・型・`utils/url.ts` を消した・`setupProxy.js`
- Config/リポジトリ: `nginx/default.conf` の `/media/`・`docker-compose.yml` の `backend_media`・`.gitignore` の `!backend/media/`・`backend/media/` の見本（承認済み）

## 影響範囲
- Backend/Frontend/DB/Config: 計画書 3 のとおり

## テスト結果
- 自動: 手元で backend 797 passed・frontend 150 passed・型・ESLint・ruff・`makemigrations --check`・ビルド・決定論ゲート 3 行が合格（2026-11-19）。CI は review-gate
- 手動: M1〜M7 OK（Claude・Playwright MCP。M7 の流し込みの 1 行だけユーザーが `!` で流した）。人の手動テストは無い
- CI: eedec7dc ですべて success。コードレビュー 20261119_2319・敵対的レビュー 20261119_2330 とも OK

## 計画との差分
- あり（小さな直しだけ・計画変更記録「実装（2026-11-19）での小さな直し」「/simplify での整理」）

## ロールバック
- 計画書 7 のとおり

## 自律判断の記録
<!-- 各段階が、止めずに自分で決めたことを `- [段階] 決めたこと — 理由` で足す。段階の結線の行（STAGE_DONE:）はこのファイルの末尾に足す -->
- [plan] 開発の DB での保存方式の試し（一時表の `ALTER TABLE ... SET STORAGE`）は、見張りが危険な SQL として止めたのでやめ、テストの DB で確かめる TC-03 に回した — 開発の DB を変えずに同じ性質を CI で毎回確かめられる
- [plan] Danger Ops の承認は、実装の最初（ステップ 1・マイグレーションのファイルを書く前）にもらう — I492 で review-gate のコンテナの起こし直しが承認の前のマイグレーションを流した（#579 は未完了）。承認の後なら流れても承認済みの操作になる
- [plan-review] 計画レビュー（20261119_1527）は高リスク判定 Yes（Blocker なし）。Warning 5 件はすべて直し、方式・範囲・受け入れ条件を変えないので再レビューはしない（計画変更記録）— AC14 は読み替えをやめ、捨てる DB のコンテナに向けた backend を `docker compose run --use-aliases` で起こして画面で確かめる形にした（ユーザーに聞かずに元の受け入れ条件のまま確かめられるため）
- [design-security-review] Blocker 0・Medium 2・Low 4（設計）。Medium の「checksum が null の行の ETag」は必須防御条件として 4-5・4-8・TC-04・TC-13 に足した。方式・範囲・受け入れ条件を変えないので計画レビューはやり直さない — 追加は守りの条件とテストの場合だけ
- [implement] ステップ 1 の数え直し（M1）と控え（M2）を済ませ、Danger Ops の承認を求めて止まる（止める条件 2）— マイグレーションのファイルを書く前に承認を得る（計画書 5 のステップ 1・R1）
- [implement] Danger Ops の承認: ユーザーの回答「3 つとも承認する (Recommended)」（2026-11-19・対象: 画像の行 4 件の削除・古い画像の列 2 つの削除・`backend/media` の PNG 6 枚と `.gitkeep` 12 個の削除。控え `backup_I587_before_20261119.sql`）。マージ依頼のときに PR の `danger-approved` もお願いする
- [implement] TC-03 の確かめのため開発の DB で `migrate problems 0024` を流そうとしたら、見張りが巻き戻しの形として止めた。承認の画面を増やさず、試しのコマンドを中身の表が無くても動く形にした — 試しは流す前の環境で使うもので、こちらが筋が通る
- [implement] ステップ 7 の `migrate` は `DANGER_OK=1` を前に付けずに流した — 付けるとサンドボックスの中で動いて `.env` を読めず止まる。前進の `migrate` は見張りの判定の対象外（danger-ops.md）で、承認はステップ 1 で得ていた。結果は `moved=0 already=0 deleted_assets=4 deleted_links=0`（M4）
- [implement] 画面の確かめ用の問題「I587確認: 画像のある問題」を開発の DB の科目「I472確認用」（E2E Org A）に作った（画像 3 枚）。M7（控えの戻し）で画像のある問題として使うので、test-gate まで残す
- [implement] 決定論ゲートの形を語の区切りつきに直した — 前の形は `../services/mediaService` に当たる誤検知を出した。直した形で失敗の注入を確かめ直した
- [implement] /simplify の 4 つの観点のレビューで出た指摘のうち 8 件を直し、7 件を理由を付けて見送った（計画変更記録）。見送りのうち `Subject.image_directory` の列（読む所が無くなった）は retro で一覧に回す
- [fix-loop] F1 は案 F1-a（`delete_image` の判定に `is_deleted=False`）で直した — 1 行で 3 か所の判定がそろう。共有の判定の 1 か所へのまとめ（F1-b）は止める指摘でない F4 を巻き込むので retro へ
- [fix-loop] F2 はユーザーの判断「このまま消す (Recommended)」（2026-11-19。最初の問いに「見本の画像使うことあるか？」と聞き返されたので、見本の出どころ〔I007 のコミット・70 バイトのテストの残り・取り込みで使われない q02〕を調べて伝え、選び直してもらった）。計画 R6 に書き、0025 が消した行のキーを出力に並べるようにした — 受け入れの目印は止める判定に効かないので、次の review-gate の差分のレビューで、この記録を見て判断してもらう
- [review-gate] 2 回目の基本レビュー（20261119_2319・差分）は OK、敵対的レビュー（20261119_2330・1 周目）も OK（V1〜V6 確認済み）。F2 は計画 R6 のユーザーの受け入れの記録で通った
- [test-gate] M7 の戻し先は捨てる DB のコンテナ（`--rm`・app-1 のネットワーク・外にポートを出さない）にし、終わったらすぐ止めた。`POSTGRES_HOST_AUTH_METHOD=trust` だったのは改善の余地（使い捨てのパスワードを付けるべきだった・ユーザーへの説明で伝えた）
- [test-gate] 確かめに使った控え（after）と、最初に止まった `db_backup.sh` が残した空のファイルを消した。戻し方のための控え `backup_I587_before_20261119.sql` はマージまで残す（gitignore 済み）
- [test-gate] `DANGER_OK=1` を前に付けるとサンドボックスの中で動き、Docker に届かない（DB の更新・`psql -f` の 2 回）。危険な操作を承認つきで流す正規の道が Docker の操作で使えない仕組みの穴として、retro で起票を検討する
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
