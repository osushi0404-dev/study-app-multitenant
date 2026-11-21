# I605 計画書: ほかのワークツリーの画像の移行と片付け

## 基本情報
- **計画書ID**: plan_I605
- **関連イシュー**: #605
- **Draft PR**: #608
- **作成根拠資料**: docs/issues/open/I605.md（起点イシュー・GitHub #605 の本文の写し）
- **実装後評価**: docs/reviews/open/I605_review.md
- **作成日**: 2026-11-20

## 1. 背景/目的
- I587〜I602 で、問題・解説の画像をファイル（`backend/media`）から DB（`media_asset_contents`）に移した。片付けたのは app-1 だけで、ほかのワークツリー（primary・harness-1・harness-2・study）には、移行の前の DB と画像ファイルが残っている
- 目的: primary は画像を安全に DB へ移して画面に出る状態にし、harness-1・harness-2 は DB を捨てて作り直せる状態にし、harness-2・study の画像ファイルを消す（決め方はイシューの設計確認メモ）

### 調査結果
**原因の概要**: 画像の置き場所を変えたとき、片付けを app-1 の中だけで済ませた。DB と画像ファイルはワークツリーごとに別にあり、git のマージでは変わらないので、ほかのワークツリーには古いものが残った。

**詳細**:
1. 2026-11-20 に app-1 から読むだけで確かめた（イシューの「現状の問題」の表）。追加で確かめたこと:
   - コンテナ: `docker ps -a` で、harness-1 の DB のコンテナ `harness-1-db-1`（2026-11-20 に止まった）・harness-2 の `harness-2-db-1`（10 日前に止まった）が、それぞれの保存領域（`harness-1_postgres_data`・`harness-2_postgres_data`）を使っている。止まっていてもコンテナが残っていると `docker volume rm` は「使用中」で失敗するので、先にコンテナを消す
   - primary のコンテナは `study-app-multitenant-*`（すべて止まっている）
2. backend の起動のコマンド（`docker-compose.yml:68-71`）は `collectstatic && migrate && runserver` で、再起動の設定（`restart:`）が無い。移行が 0026・0027 で止まると backend のコンテナは終わり、`docker compose exec backend …` は使えない。今の手順書（`docs/runbooks/backend-check.md:46-56`）は止まった後に `docker compose exec -T backend … dbshell`・`migrate` を使うので、起動の途中で止まった場合には動かない
3. 代わりのやり方を app-1 で試した（読むだけ・2026-11-20）:
   - `docker compose exec -T db psql -U postgres -d learning_app -c "SELECT …"` は DB のコンテナだけで SQL が流れる（成立）
   - `docker compose run --rm --no-deps -T backend python manage.py showmigrations problems` は、起動のコマンド（migrate）を通らずに 1 つのコマンドだけを流す（成立。0001〜0027 の一覧が出た）
4. 移行の中身（`backend/problems/migrations/`）:
   - 0025: `media_assets` のうち `is_deleted` でない行ごとに、`backend/media/<storage_key>` があれば中身を `media_asset_contents` に入れ、無ければ行と紐づけ（`problem_media_assets`）を消す。出力に `I587 media: …` と、消した行ごとに `I587 media: deleted id=… key=…` を書く
   - 0026: `problems_problem` の `question_image`・`explanation_image`（NULL 可）に NULL でも空でもない値が 1 件でもあれば止まる
   - 0027: `problems_subject` の `image_directory`（NULL 不可）に空でない値が 1 件でもあれば止まる
   - 試しのコマンド `manage.py check_media_migration` は今のモデル（0024 で増えた `media_asset_contents`）を使うので、0024 の前の DB では使えない。数えるのは SQL で行う
5. 危険操作の流し方（`docs/runbooks/danger-ops.md:46-56`・I587 の実績 `docs/plans/closed/plan_I587.md:178`）: `DANGER_OK=1` を前に付けるとサンドボックスの中で動き、docker に届かない。そのため docker を使う危険操作は、Claude が前置きなしで流す（見張りが止めない前進の `migrate` など）か、人が `!` を付けて自分で流す
6. 軽い指摘の一覧（`docs/reviews/backlog/I602.md` の F2）: 手順書の 0026 の節に SELECT・UPDATE の例が無い。今回 primary で 0026 に当たりうるので同梱する（9 を参照）

## 2. 受け入れ条件
- [ ] AC1: primary の DB で、`problems` の移行 0024〜0027 が適用済み（`showmigrations problems` で `[X]`）
- [ ] AC2: primary の移行の出力（`I587 media:` の行＝移した件数・消した件数と消した行）と、画像のある問題を画面で開いて画像が出たことが記録にある（画像のある問題が無ければその旨）
- [ ] AC3: harness-1・harness-2 の DB の保存領域（`harness-1_postgres_data`・`harness-2_postgres_data`）が無い
- [ ] AC4: primary・harness-1・harness-2・study に `backend/media` が無い（消す前の harness-2・study・primary のファイルの一覧が記録にある）
- [ ] AC5: このイシューで作った控え（`backup_I605_*.sql`）がどのワークツリーにも残っていない
- [ ] AC6: 消える行・値を空にした操作（あれば）・保存領域の削除・ファイルの削除のそれぞれについて、人の承認の言葉と日付が記録にある
- [ ] AC7: 手順書 `docs/runbooks/backend-check.md` §4 のコマンドが、backend が起動の途中で止まった後でも動く形になっている（DB のコンテナで SQL を流す・`run --no-deps` で移行を流し直す）。0026 の SELECT・UPDATE の例がある

## 3. 影響範囲
- Backend: なし（コードは変えない）
- Frontend: なし
- DB: primary の開発の DB（移行 0024〜0027・ファイルの無い画像の行の削除・列の削除・必要なら値を空にする）。harness-1・harness-2 の開発の DB（保存領域ごと削除）
- Config/Infra: primary・harness-2・study の `backend/media`（git の外）の削除。harness-1・harness-2 の DB のコンテナの削除（次の起動で作り直される）
- 手順書: `docs/runbooks/backend-check.md` §4

## 4. 変更点一覧（具体）

### 修正アプローチ
- 片付けそのものはコードを変えない運用の作業。app-1 から別のワークツリーには書き込めない（`docs/runbooks/worktree.md` §9）ので、次のように分ける:
  - **primary**: primary で起動した Claude のセッションが、下の「primary の手順（P1〜P10）」をこの計画書を読んで進める（この計画書はマージ前は app-1 の中にあるので、絶対パス `/mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/docs/plans/open/plan_I605.md` で読む）。結果は GitHub #605 にコメントで残し、app-1 の流れが記録に写す
  - **harness-1・harness-2・study**: 消すだけ（捨てると決めた試しのデータ）なので、app-1 の Claude が消す対象の一覧を記録し、人が app-1 の画面で `!` を付けたコマンドを流す（下の「app-1 の手順（A1〜A3）」）
- 手順書 `backend-check.md` §4 を、backend が起動の途中で止まった後でも動くコマンドに直し、0026 の例を足す（今回の primary で役に立ち、`#579` が直るまで起動のたびに同じことが起こりうるため）

### 4-1. `docs/runbooks/backend-check.md` §4（AC7）
達成すること: 起動の途中で 0026・0027 が止まっても、手順書のコマンドがそのまま動く。止まる前に数えることもできる。
- §4 の冒頭に「止まった後は backend のコンテナが終わっている（起動のコマンドが `migrate && runserver` で、再起動しない）。SQL は DB のコンテナで、移行の流し直しは `docker compose run --rm --no-deps -T backend python manage.py migrate problems` で行う」と書く
- 「流す前に数える（backend を起こさない）」の小節を足す: `docker compose up -d --wait db` の後、DB のコンテナで次の SQL を流す
  - 0026 の対象: `SELECT id, question_image, explanation_image FROM problems_problem WHERE coalesce(question_image, '') <> '' OR coalesce(explanation_image, '') <> ''`
  - 0027 の対象: `SELECT id, name, image_directory FROM problems_subject WHERE image_directory <> ''`
  - 0025 で消える行の候補: `SELECT id, storage_key FROM media_assets WHERE NOT is_deleted ORDER BY created_at, id` の `storage_key` と `backend/media` の中のファイルを突き合わせ、ファイルの無いもの
- 0027 の手順の 2・4・5 のコマンドを `docker compose exec -T db psql -U postgres -d learning_app -c "…"`・`docker compose run --rm --no-deps -T backend python manage.py migrate problems` に置き換える。空にする SQL の文（`UPDATE problems_subject SET image_directory = '' WHERE image_directory <> ''`）は変えない（`backend/problems/tests/test_I590_review_leftovers.py` の `CLEAR_IMAGE_DIRECTORY_SQL` と同じ文のまま）
- 0026 の段落に、値を見る SQL（上の SELECT）と空にする SQL `UPDATE problems_problem SET question_image = NULL, explanation_image = NULL WHERE coalesce(question_image, '') <> '' OR coalesce(explanation_image, '') <> ''` を足す。空にする前に、その画像が `media_assets` に移っているかを確かめること（移っていなければ値の使い道を人に聞く）も書く

### 4-2. primary の手順（P1〜P10・primary で起動した Claude のセッションが行う）
達成すること: 控えを取ってから、消える行と止まる値を人に見せて承認を得て移し、画像が画面に出ることを確かめてから、ファイルと控えを消す。どこで止まっても、控えと元のファイルが残っている。
前提: primary のフォルダ（`/mnt/c/app/study-app-multitenant`）で `claude` を起動する。primary は develop にいて、0024〜0027 がコードにある。コマンドはすべて primary のフォルダで、1 回の呼び出しに 1 つずつ流す（`docs/runbooks/danger-ops.md`「外に出すコマンドの書き方」）。
- P1 DB だけを起こす: `docker compose up -d --wait db`（backend は起こさない。起こすと控えの前に移行が流れる）
- P2 控え: `bash scripts/claude/db-backup.sh I605_before_primary`（出力: primary の直下の `backup_I605_before_primary_<日時>.sql`）
- P3 今の状態を数える（読むだけ。SQL は 4-1 と同じ）:
  - a. 適用済みの移行と、P6 で流れる移行の全部: `docker compose run --rm --no-deps -T backend python manage.py showmigrations problems` と `docker compose run --rm --no-deps -T backend python manage.py migrate --plan`（`problems` 以外のアプリの未適用の移行も P6 で流れるので、`--plan` の一覧を P4 で一緒に見せる。`problems` の 0024〜0027 以外に、行や列を消す移行があれば、その中身も見せて承認を得る）
  - b. 画像の行: `media_assets` の `id`・`storage_key` の一覧と、`find backend/media -type f` の一覧を突き合わせ、「ファイルがある（0025 で移す）」「ファイルが無い（0025 で行と紐づけを消す）」に分ける。紐づけの数は `SELECT asset_id, count(*) FROM problem_media_assets GROUP BY asset_id`
  - c. 0026 の対象（4-1 の SELECT）
  - d. 0027 の対象（4-1 の SELECT）
- P4 承認を得る（止めて聞く）: P3 の結果（消える行の id と storage_key・紐づけの数・空にする値・ファイルの一覧）を見せ、「0025 で消える行を消してよいか」「0027 の値を空にしてよいか（あれば）」を聞く。0026 の対象があるときは、その値の画像が `media_assets` に移っているかも見せ、空にするかどうかを人に決めてもらう（移っていない画像を空にすると、その画像が問題から外れる）。承認の言葉と日付を P10 のコメントに書く
- P5 値を空にする（P4 で承認を得たものだけ）: 4-1 の UPDATE を `docker compose exec -T db psql -U postgres -d learning_app -c "…"` で流す（前置きは付けない。見張りが止めたら、同じコマンドを人に `!` を付けて流してもらう）
- P6 移す: `docker compose run --rm --no-deps -T backend python manage.py migrate`。出力の `I587 media:` の行（件数と消した行）をそのまま P10 のコメントに写す。途中で止まったら、そこで止めて出力を人に見せる（承認していない値を空にしない）
- P7 適用の確かめ: P3-a のコマンドで `problems` の 0024〜0027 が `[X]` であることを見る
- P8 画面で確かめる: `docker compose up -d --wait` でアプリを起こし、`docs/runbooks/frontend-verify.md` の手順で Playwright MCP を使い、P3-b で「ファイルがある」画像を使う問題を 1 つ開いて画像が出ることを確かめ、画面の画像を primary の `.evidence/I605/primary_image.png` に保存する。移した件数（`I587 media:` の `moved`）が P3-b の「ファイルがある」件数と同じことも見る。画像を使う問題が無ければ、その旨を書く（引数なしの `up` は `dashboard-verify-seed` も動かし、primary の DB に確かめ用の組織と科目を作り直す。いつもの起動と同じ動きで、移行の確かめには影響しない）
- P9 消す（止めて聞く）: P8 が済んだら、`backend/media` のファイルの一覧（P3-b）と控えのファイル名を見せ、「消すと、画像の中身は DB にしか無くなり、移行の前の DB にも戻せなくなる」ことを伝えて承認を得る。承認の後に `DANGER_OK=1 rm -rf backend/media`（見張りが承認画面を出す）と `rm backup_I605_before_primary_<日時>.sql` を流す
- P10 記録: 下の形のコメントを `gh issue comment 605 --body-file <一時ファイル>` で残す（一時ファイルはスクラッチパッドに置き、送った後に消す。**リポジトリは公開なので、メールアドレス・ユーザー名・問題文や解説の中身・控えの中身を書かない**。書くのは件数・id・`storage_key`・移行の名前・`I587 media:` の行だけ。詳しくは末尾の「セキュリティレビュー結果」）
  ```
  ## I605 primary の結果（YYYY-MM-DD）
  - P2 控え: <ファイル名>（<バイト数>）
  - P3-a 移行の前: 0023 まで [X]／0024〜0027 [ ]（実際の出力）
  - P3-b 画像の行: ファイルあり <n> 件・ファイル無し <m> 件（無い行の id と storage_key）・紐づけ <k> 件
  - P3-c 0026 の対象: <件数>（あれば id と値）
  - P3-d 0027 の対象: <件数>（あれば id・name・値）
  - P4 承認: 「<人の言葉>」（日付）
  - P5 空にした値: <SQL と UPDATE の件数> または なし
  - P6 移行の出力: <I587 media: の行をそのまま>
  - P7 移行の後: 0024〜0027 [X]（実際の出力）
  - P8 画面: <問題の id・画面の URL・画像が出たか>・画像 .evidence/I605/primary_image.png
  - P9 承認: 「<人の言葉>」（日付）・消したもの: backend/media（<n> 個）・<控えのファイル名>
  ```

### 4-3. app-1 の手順（A1〜A3・app-1 の Claude と人が行う。primary の後）
達成すること: 捨てると決めた harness-1・harness-2 の DB と、harness-2・study の画像ファイルを、一覧を残してから消す。
- A1 一覧を記録する（読むだけ）: `find <harness-2>/backend/media -type f`・`find <study>/backend/media -type f`・`test ! -e <harness-1>/backend/media`・`docker ps -a --filter volume=harness-1_postgres_data --filter volume=harness-2_postgres_data`・`docker volume ls` の結果を `docs/tests/open/I605_manual_test.md` の記録に書く
- A2 承認を得て人が消す（止めて聞く）: A1 の一覧を見せ、次の 3 つのコマンドを、人が app-1 の画面で `!` を付けて 1 つずつ流す（流すことと返信を承認として、言葉と日付を記録する）
  - `docker rm harness-1-db-1 harness-2-db-1`（DB のコンテナ。次の起動で作り直される。保存領域を使うのは DB のコンテナだけなので、backend などほかの止まったコンテナは消さずに残す。それらは次の起動でそのまま使われ、空の DB につながる）
  - `docker volume rm harness-1_postgres_data harness-2_postgres_data`
  - `rm -rf /mnt/c/app/study-app-multitenant/.claude/worktrees/harness-2/backend/media /mnt/c/app/study-app-multitenant/.claude/worktrees/study/backend/media`
- A3 primary の結果を写す: GitHub #605 の primary のコメントを `gh issue view 605 --comments` で読み、`docs/tests/open/I605_manual_test.md` と `docs/reviews/open/I605_review.md` に写す。primary の画面の画像を `.evidence/I605/` に写す（primary の `.evidence/I605/primary_image.png` を読んで app-1 に置く）

## 5. 実装手順（ステップ）
1. 手順書を直す（4-1）→ TC-01・手動 M8。commit する
2. 止めて人に頼む（止める条件 2・`STAGE_DONE` は書かない）: 「primary で `claude` を起動し、計画書（絶対パス）の 4-2 の P1〜P10 を進めるように頼む」「primary が済んだら `/proceed I605` を打つ」を伝える（ステップ 1 の後。ステップ 3 は人の返事の後）
3. `/proceed I605` で戻ったら、A3（primary の結果を写す）→ A1 → A2（止めて人に頼む。人が流して返信した後に続ける）
4. A2 の後に、記録（手動テスト文書・レビュー文書の承認の言葉）を commit し、`STAGE_DONE: implement NEXT: review-gate` を書く
- ステップ 2 と 3 は順に行う（primary → harness-1 → harness-2 → study の順。イシューの設計確認メモ）
- 実装の後に再起動の要るサービスは無い（primary は P8 で起こしたまま。止めるかは人が決める）

## 6. テスト計画
### 自動
- コードを変えないので、新しい自動テストは無い。手順書の SQL とテストの SQL の一致は手動 M8 で見る（`plan-writing-rules.md`「決定論テストの対象の選び方」: 手順書の文言は意図的な変更でしか変わらず、レビューで見る）
- CI（backend・frontend のテスト）がそのまま通ること → TC-01
### 手動
- test-gate で app-1 の Claude が、終わった状態を読むだけで確かめる（M1〜M8・`docs/tests/open/I605_manual_test.md`）。人に頼む確かめは無い（人が行うのは承認と `!` のコマンドで、ステップ 2・3 の中で済む）

## 7. ロールバック
- 手順書: このブランチの差分を戻す
- primary: P6 の前なら P2 の控えを `psql` で流し込む（それ自体が危険操作・人の承認の後）。P6 の後・P9 の前なら `docker compose run --rm --no-deps -T backend python manage.py migrate problems 0024`（0025 の戻しが `media_asset_contents` の中身を `backend/media` に書き戻す。0026・0027 を戻すと列は空の値で戻る。危険操作・人の承認の後）。P9 の後は戻さない（画像の中身は DB にある）
- harness-1・harness-2・study: 戻さない（試しのデータを捨てるとユーザーが決めた・2026-11-20 の設計確認メモ）

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 控えを取る前に primary で backend が起き、承認の前に 0025 が流れて行が消える | P1 で DB だけを起こす。P3-a・P6 は `run --no-deps` で起動のコマンドを通らない。P1〜P5 の間に `docker compose up`（引数なし）を流さない | 回避 |
| R2: 0026・0027 で止まり、backend が起動しない | P3 で先に数え、P4 で承認を得て P5 で空にしてから P6 を流す。それでも止まったら P6 で止めて出力を見せる。流し直しは 4-1 の手順 | 回避 |
| R3: 0026 の値を空にすると、`media_assets` に移っていない画像が問題から外れる | P4 で値と `media_assets` の対応を見せ、空にするかを人が決める | 回避 |
| R4: 画像の行の一覧と `find` の突き合わせを誤り、消えないはずの行が消える | 突き合わせはあくまで見せる材料で、実際に消す行は 0025 自身が判定する。P6 の出力の `deleted id=…` と P3-b を P10 で並べ、違えば P9 に進まずに止める（P9 の前なら 7 のとおり戻せる） | 回避 |
| R5: harness-1 で I599 の作業のセッションが DB を使っている最中に消す | A1 で `docker ps -a` を見て、`harness-1-db-1` が動いていたら A2 に進まず、人に止めてよいかを聞く | 回避 |
| R6: 消した後の harness-1・harness-2 を起動すると、空の DB から始まり、試しのアカウント・データが無い | 捨てるとユーザーが決めた（2026-11-20）。E2E の試しのデータは E2E の起動のたびに作られ、ダッシュボードの確かめのデータは起動のたびに作り直される（`docker-compose.yml` の `dashboard-verify-seed`）。それ以外の手作りの試しのデータは戻らない | 受け入れ |
| R7: primary の画面の確かめで、Playwright MCP が primary のセッションで使えない | `docs/runbooks/frontend-verify.md` §12 のとおり再接続を頼む。それでも使えなければ P9 に進まずに止める（画像が出ることを確かめないままファイルを消さない。P9 の前なら 7 のとおり戻せる） | 回避 |
| R8: 他のワークツリーのセッションが GitHub に書き込むのと、app-1 の書き込みが重なる（`docs/runbooks/workflow.md`「同時に複数のセッションで GitHub に書き込まない」） | primary が書き込むのは P10 のコメント 1 回だけで、app-1 はその間（ステップ 2 で止まっている間）に GitHub へ書き込まない | 回避 |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- primary は丁寧に移す（控え → 件数の確かめ → 承認 → 移行 → 画面で確かめ → ファイルを消す → 控えを消す）
- harness-1・harness-2 は捨てて作り直す（保存領域を消す・移行と画面の確かめはしない・develop の取り込みは待たない）
- study は画像ファイル 18 個の一覧を記録に残して、確かめを増やさずに消す
- I605 1 本で、primary → harness-1 → harness-2 → study の順に回る。結果は I605 の記録にまとめる
- 消す操作はどれも人の承認の後
Claude が決めた（技術的な選択と理由）:
- harness-1・harness-2・study の削除は、各ワークツリーで Claude を起動せず、app-1 で人が `!` を付けて流す（4-3 A2）— 理由: そこで行うのは消すことだけで、どれも人の承認が要る。Claude のセッションが `DANGER_OK=1 docker volume rm` を流すと前置きでサンドボックスの中に入り docker に届かない（調査結果 5）ので、結局は人の `!` になる。セッションを 3 つ起こす手間を省く。消す対象の一覧は app-1 から読める（`worktree.md` §9 は読み取りを認めている）。設計確認メモの「各ワークツリーで claude を起動して行う」は、Claude が別のワークツリーに書けないことから来た進め方で、作業を人が行う形はイシューの制約の欄（「各ワークツリーで claude を起動して進めるか、人が行う」）の範囲
- primary の結果は GitHub #605 のコメントで受け渡す（4-2 P10）— 理由: primary のセッションは app-1 のファイルに書けない（`worktree.md` §9）。チャットでの受け渡しは禁止（同 §9）。コメントは GitHub に残り、app-1 から `gh issue view --comments` で読める。本文の書き換え（`gh issue edit`）は grill-me の 1 回だけの決まりなので使わない
- primary で件数を数えるのも移行を流すのも、backend の起動のコマンドを通さない（DB のコンテナの `psql` と `docker compose run --rm --no-deps`）— 理由: 起動のたびに `migrate` が流れる（#579）ので、backend を起こすと承認の前に流れる。2 つのやり方は app-1 で成立を確かめた（調査結果 3）
- 0025 で消える行の候補は SQL と `find` の突き合わせで出す — 理由: `check_media_migration` は 0024 の後の DB でしか動かない（調査結果 4）
- 手順書 §4 を直す（4-1）— 理由: 起動の途中で止まった後に今のコマンドが動かない（調査結果 2）。イシューのスコープの「必要なら backend を起こさずに数える手順を足す」に当たる。#579 が直るまで、どのワークツリーでも起こりうる
- 手順書の変更に自動のテストを作らない — 理由: `plan-writing-rules.md`「決定論テストの対象の選び方」。空にする SQL と `CLEAR_IMAGE_DIRECTORY_SQL` の一致は I602 と同じく手動 M8 で見る
- 実装の段階で止まり（ステップ 2・3 の A2）、`/proceed` で戻る — 理由: 危険操作は人の承認が要る（止める条件 2）。test-gate で終わった状態を Claude が確かめられるように、片付けは test-gate より前（implement）に済ませる
- 一覧 docs/reviews/backlog/I602.md F2: 同梱 — 手順書 §4 を直す今回の変更（4-1）と同じ節で、primary で 0026 に当たりうる
- 一覧 docs/reviews/backlog/I224.md F9・I223.md B1〜B4（`FILE=-`）: 残す — どれもハーネスの別の話（測定・bot の停止中の片付け）で、今回の範囲と関係が無い
Danger Ops（有）:
- 影響範囲: primary の開発の DB（0025 の行と紐づけの削除・0026／0027 の列の削除・必要なら値を空にする UPDATE）・primary の `backend/media`（7 個）と控え。harness-1・harness-2 の DB のコンテナと保存領域。harness-2・study の `backend/media`（18 個ずつ）
- 代替案: harness の DB も primary と同じく移す（ユーザーが捨てると決めた）／`#579` を先に直す（範囲外・イシューの含まないもの）
- ロールバック: 7 のとおり（primary の控えのファイル名は `backup_I605_before_primary_<日時>.sql`）
- 実行コマンド: 4-2 の P5（`docker compose exec -T db psql … -c "UPDATE …"`）・P6（`docker compose run --rm --no-deps -T backend python manage.py migrate`。前進の移行は見張りの判定の対象外・承認は P4）・P9（`DANGER_OK=1 rm -rf backend/media`・控えの `rm`）。4-3 の A2 の 3 つ（人が `!` で流す）
- 承認の記録: primary は #605 のコメント（P10）、app-1 の分は `docs/reviews/closed/I605_review.md` の「## 自律判断の記録」の下の「承認の記録」
- PR のラベル `danger-approved`: 付けない — この PR の差分は手順書だけで、破壊的なマイグレーションのコードを含まない（危険操作は手元の開発の DB への運用で、PR には入らない）
要件適合性・業務ロジック: 受け入れ条件の外の仕様の追加は無い。マルチテナント・状態の遷移の変更は無い（コードを変えない）
セキュリティ影響なし（コードを変えない。控えは DB の中身の写しなので P9 で消す・C2）
P3/P5/P8 影響なし（DB のスキーマのコードは変えない。運用で既存の移行を流すだけ。外部 API・非同期処理・新しいインフラは無い）
P6 影響なし（画面・データ量の変更は無い）
P9 影響なし（個人情報の新しい扱いは無い。控えは用が済んだら消す）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 3 | 読んで可 | 4-2 の P1〜P6 の間に、backend の起動のコマンド（`migrate` を含む）が流れる手順が無い（`docker compose up` の引数なし・`up backend` が P8 より前に無い） |
| V2 | 3 | 読んで可 | 4-2 で、消す操作（P5・P6・P9）のどれもが、その前の止めて聞く手順（P4・P9）の承認の後にしか来ない |
| V3 | 1 | 読んで可 | 4-1 の空にする SQL の文が `backend/problems/tests/test_I590_review_leftovers.py` の `CLEAR_IMAGE_DIRECTORY_SQL` と同じ（手動 M8） |

## 計画変更記録
- 2026-11-20 plan-review: 計画書の記載: [P3-a は `showmigrations problems` だけ・M1/M3 は出力を目で見る・A2 にほかのコンテナの扱いが無い・P8 に `dashboard-verify-seed` の副作用の記述が無い] → 採った方法: P3-a に `migrate --plan` を足して P4 で見せる・M1/M3 を合格で exit 0 の形にする・A2 と P8 に注記 — 理由: 計画レビュー 20261120_2000 の Warning 3 件・Info 1 件への対応。計画レビューのやり直し: 不要（findings への対応の追記だけ。方式・範囲・受け入れ条件は変えない）

## レビュー結果
- [20261120_2000 判定: ✅ 完了](../../reviews/closed/I605_plan_review_20261120_2000.md)

## セキュリティレビュー結果

**実施日**: 2026-11-20

コード変更なし（差分は `docs/runbooks/backend-check.md` だけ）。バックエンドの認証・認可・シリアライザ・URL は読む対象が無いので省いた。見たのは、運用の手順（4-2・4-3）が情報を外に出さないか・消す操作が承認の外で起きないか。

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Medium | 機密情報 | リポジトリは公開（`gh repo view` の `visibility` が `PUBLIC`・2026-11-20）。P10 のコメントと app-1 の記録（push される）は誰でも読める。primary の開発の DB には、ログインに使うアカウント（メールアドレス）や、人が作った問題の中身が入りうる | **禁止**: P10 のコメント・`docs/` の記録に、メールアドレス・ユーザー名・パスワード・問題文や解説の中身・控え（`backup_*.sql`）の中身を書かない。**書いてよいもの**: 件数・行の id（UUID）・`storage_key`・移行の名前・`I587 media:` の行・科目の id。`name`・`image_directory` の値は試しのデータの名前のときだけ書き、迷えば件数と id だけにする。画面の画像（`.evidence/`）は git から外れていて push されないが、コメントに貼らない |
| Low | 機密情報 | 控え（P2）は DB の中身の写しで、`/mnt/c` の上では `umask 077` が効かず、誰でも読める権限で置かれる（`docs/plans/closed/plan_I597.md` R6） | P9 で消す（AC5・M3）。P2〜P9 の間に控えを別の場所へ写さない |
| Low | セキュリティ設定ミス | A2 の `!` のコマンドは見張りとサンドボックスを通らないので、パスの打ち間違いがそのまま消す操作になる | A2 は計画書のとおりの絶対パスで 1 つずつ流す。Claude は A1 で一覧を見せるときに、流すコマンドの文字列も同じ形で示す |
| なし | 認証・認可・マルチテナント・入力検証・ファイル操作（アップロード）・外部通信・依存ライブラリ | コードと依存を変えない | なし |

### 攻撃シナリオレビュー
攻撃シナリオなし（コード変更なし。新しい・変わる入口は無い）

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 0件 | 0件 |
| Medium  | 1件 | 0件 |
| Low     | 2件 | 0件 |

### 残余リスク処遇
（retro 段階で決定する）
