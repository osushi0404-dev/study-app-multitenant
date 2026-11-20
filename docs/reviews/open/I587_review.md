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

## 振り返り

### かんたんなまとめ

**良かった点**
- イシューの前提の間違い（画像の置き場の volume が実は作られていない・画像の行 4 件はファイルが無い）を、grill-me の前に開発の DB とディスクを数えて見つけ、質問と受け入れ条件を実態に合わせられた（理由: 机の上の想定のまま計画すると、移行の件数や捨てる対象を取り違えていた）
- 危ない操作（行の削除・列の削除・見本の削除）の承認を、DB の更新のファイルを書く前にもらった（理由: I492 では、検証の途中でコンテナが起こし直され、承認の前に DB の更新が流れた。今回は同じ穴〔#579 は未修正〕が残っていても、承認済みの操作になる順にした）
- 守りを一時的に外すとテストが落ちることを、10 か所以上で実際に確かめた（理由: 見かけだけ通るテストを残さない。「置き場の外のキー」のテストは、外しても別の理由で通ってしまう穴をここで見つけて直せた）

**今回の問題への直接の対処**
- レビューの残りの軽い指摘 5 件（画面から使われていない画像の登録・削除の作りと応答の形、移行が今のコードに頼る点、テストの比べ方）。どれも止めるほどではないが、放っておくと同じ所を触る人がつまずく。→ 1 件の後続イシューにまとめて起票する。読む所が無くなった `Subject.image_directory` の列もそこに入れる
- 科目を作ると `backend/media` にフォルダができる件（#549）は、今回フォルダ作りを外したので解消した。→ #549 にコメントし、I587 のマージで閉じられるようにする

**同じ問題を次回から防ぐ改善**
- 危ない操作を承認つきで流す正規の形（コマンドの前に `DANGER_OK=1` を付ける）が、Docker を使う操作ではサンドボックスの中で動いてしまい、Docker に届かなかった（DB の更新と、控えの流し込みの 2 回）。控えのスクリプト（`scripts/db_backup.sh`）も、サンドボックスの中から `.env` を読めずに止まった。→ 同じ原因（前置き・振り向けがあるとサンドボックスの外に出られない）を扱う #538 に同梱する
- 見本の画像を同じ PR で消すと、ほかのワークツリーでは「ファイルが消える → DB の移行が流れる」の順になり、行が消えうることを、計画で Claude が「開発のデータなので受け入れる」と書いていた。ユーザーには確かめていなかった（レビューで見つかり、fix-loop で確かめ直した）。→ 計画で「受け入れ」にするリスクのうち、ユーザーのデータを失うものは、grill-me の回答に根拠があるかを計画レビュー役が確かめる観点として #547 に同梱する

### 詳細

#### 良かった点
- grill-me の前に実データを数えた（`MediaAsset` 4 件・ファイル 0・volume なし・古い列 0）ことで、質問が実態に合った
- Danger Ops の承認をマイグレーションのファイルを書く前に取った（#579 の穴を順番で避けた）
- 失敗の注入: TC-02・03・04・07・08・11・13・14・15・ゲート 3 行。TC-14 の outside は注入で false-green を見つけて直した
- /simplify の 4 観点で、改行の形（CRLF）の書き換え・死んだコード・テストの差し替えの深さを直せた

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | ベストプラクティス | 画面から使われていない `upload_image`・`delete_image` を「消さずに共通の保存・削除に寄せる」だけにしたので、ビューがトランザクションを持ち、サービスの非公開の関数を呼び、独自のエラーの形が残った（台帳 F4・F5・F7）。移行 0025 が今のコードに頼る（F3）。テストの部分文字列の比べ（F6）。`Subject.image_directory` は読む所が無くなった | 後続イシュー I590（#590）「I587 のレビューの残り」に F3〜F7 と `image_directory` をまとめて起票した |
| C2 | 成果 | #549（科目の作成が `backend/media` にフォルダを作り、作業ツリーの確かめを止める）は I587 で科目のフォルダ作りを外したので解消した | #549 にコメント（I587 で解消・マージで閉じる） |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | スキル・規約 | 危ない操作の承認の正規の形（コマンドの前の `DANGER_OK=1`）と、サンドボックスの外に出す設定（`excludedCommands` の前方一致）がかみ合わず、Docker を使う危ない操作は承認つきで流せない。スクリプトの中の `docker compose` も `.env` を読めない | #538 に同梱: 危ない操作を承認つきで流す形を、サンドボックスの外に出る形で用意する（例: 前置きでなく見張りが読める別の合図にする・スクリプトの入口を `scripts/claude/` に置く）。決定論で止める | `docs/runbooks/danger-ops.md`・`.claude/settings.json`（安全装置・ユーザーの判断）・`scripts/db_backup.sh` |
| P2 | プロセス | 計画の「Risk & 回避策」で、ほかの環境のデータを失うリスクを、ユーザーに確かめずに「受け入れ」にできた（grill-me の回答の根拠が無いまま） | #547 に同梱: 計画レビュー役の観点に「処遇が受け入れのリスクのうち、ユーザーのデータを失うもの・ほかの環境に及ぶものは、grill-me の回答（設計確認メモ）に根拠があるか。無ければユーザーに確かめる（止める条件 1）」を足す | `.claude/agents/plan-reviewer.md`・`docs/runbooks/plan-writing-rules.md` |

#### 見送り（4 問の判定）
- 見張りが `migrate <アプリ> <番号>` を前進でも巻き戻しの形として止めた件 — 実害なし（試しのコマンドを直して避けた）。見張りは事故に倒す設計で、番号を指定した前進はまれ。見張り（安全装置）を緩める変更は足さない
- サンドボックスの起動が別のセッションの git の書き込み（`config.lock`）と重なって一時的に失敗した件（3 回）・長いヒアドキュメントがワークツリーの確かめで止められた件 — 実害なし（流し直し・書き方の変更でその場で済んだ）。環境の側の事象
- 敵対的レビューの `Low`（304 の経路で中身の有無を見ない）— 組織の境界は先に確かめている。直す価値が低い
- /simplify で見送った 7 件（計画変更記録）— 理由はそこに書いた。`image_directory` だけ C1 に入れた

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
- [retro] 台帳の残り: F3・F4・F5・F6・F7（どれもアプリ本体の Low・再現なし）→ #590（I590・I587 のレビューの残り）。F1・F2 は resolved。判定の仕組み・SECURITY=yes の行は無い。一覧（`docs/reviews/backlog/`）に回す行は 0 件
- [retro] 改善案の振り分け: C1 → 起票 I590（#590）／C2 → #549 にコメント（I587 で解消）／P1 → #538 に同梱（`DANGER_OK=1` の前置きと Docker・`db_backup.sh`）／P2 → #547 に同梱（受け入れのリスクの根拠の確かめを計画レビュー役の観点に）／見張りの `migrate <アプリ> <番号>` の誤検知・サンドボックスの一時的な失敗・ヒアドキュメントの拒否・敵対的レビューの Low・/simplify の見送り 7 件 → 見送り（理由は「## 振り返り」）
- [close] develop（I583 の記録とハーネスのテスト 1 本）を取り込んだ。I587 のファイルには触れておらず、gate-check は OK のまま
- [close] PR の説明に `Closes #549` を足した（科目のフォルダ作りを外したので解消）。Danger Ops のラベル `danger-approved` はマージ依頼でお願いする
- [close] マージ依頼の後、ユーザーに BP・UI/UX の評価を聞かれ、新しいコードの規約・UX の決まりからの外れ 4 点を挙げた。ユーザーの指示「BP,UI/UX の観点でベストなやり方で進めて」（2026-11-20）を受け、後回しにせずこの PR で直す。PR を下書きに戻し、記録を open に戻して、計画を直して計画レビューからやり直す（方式が変わるため）— #590 のうち今回書き換えたコードの分（F4〜F7）も一緒に直し、F3 と `image_directory` は #590 に残す
- [plan-review] 計画レビュー（20261120_0903）は高リスク判定 Yes・Blocker なし。Warning 3 件（9 のエッジケースの古い記述・/simplify の見送りを覆した旨・`DANGER_OK=1` の実行コマンド）を直した。TC の再実施の Warning はステップ 9 の手順で行う — 方式は計画どおりで再レビューは不要
- [design-security-review] 追加の直しの分を確かめた。Blocker 0・Medium 1（`remove_image` の紐づけの絞り込みに画像の組織〔科目の組織〕を入れる）を必須防御条件として 4-4 と TC-10 に足した。Low 2 件（弱い比較・412）は受け入れ — 組織の絞り込みの後の判定なので境界は越えない
- [implement] 追加の直しを実装した（サービスの `add_image`・`remove_image`・`ImageUploadSerializer`・`GenericAPIView`・`get_conditional_response`・枠の高さ・44px のボタン）。画面は Playwright MCP で、成功・失敗・再読み込みを確かめた（失敗はブラウザのページの中で `/api/media/` の通信だけを 404 にして作った・`browser_run_code_unsafe`）。失敗の枠は表示のときと同じ高さで、下の選択肢の位置が変わらない
- [implement] /simplify（4 観点）の指摘のうち 3 件を直し、3 件を見送った（計画変更記録）
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
STAGE_DONE: close NEXT: merge
STAGE_DONE: close NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
