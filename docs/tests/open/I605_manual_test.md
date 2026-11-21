# I605 手動テスト: ほかのワークツリーの画像の移行と片付け

片付けそのもの（計画書 4-2 の P1〜P10・4-3 の A1〜A3）は implement の段階で済ませる。この表は、test-gate で app-1 の Claude が、終わった後の状態を読むだけで確かめる項目。
`<W>` は `/mnt/c/app/study-app-multitenant/.claude/worktrees`、`<P>` は primary の `/mnt/c/app/study-app-multitenant`。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M1 | `docker volume inspect --format '{{.Name}}' harness-1_postgres_data`・同じく `harness-2_postgres_data`・同じく `app-1_postgres_data` を 1 つずつ単体で流す（つなぐ・振り向けるとサンドボックスの中で動き docker に届かない）（AC3） | harness-1・harness-2 の 2 つは exit 1（`no such volume`）。app-1 は exit 0（docker に届いていることの確かめ） | Claude |  | 判定の確かめ（2026-11-20）: 消す前の `harness-1_postgres_data` は exit 0・無い名前 `i605_no_such_volume` は exit 1 |
| M2 | `test ! -e <P>/backend/media`・`test ! -e <W>/harness-1/backend/media`・`test ! -e <W>/harness-2/backend/media`・`test ! -e <W>/study/backend/media` を 1 つずつ流す（AC4） | 4 つとも exit 0 | Claude |  |  |
| M3 | 5 つのフォルダ（`<P>`・`<W>/app-1`・`<W>/harness-1`・`<W>/harness-2`・`<W>/study`）それぞれで、`test -d <フォルダ>` を流してから `! compgen -G '<フォルダ>/backup_I605_*'` を流す（AC5） | 10 個とも exit 0 | Claude |  | `test -d` でパスの誤りを先に落とす。失敗の注入: スクラッチパッドに `backup_I605_x.sql` を置いたフォルダでは `! compgen -G` が exit 1 になることを test-gate で確かめる |
| M4 | `docker exec study-app-multitenant-db-1 psql -U postgres -d learning_app -tAc "SELECT name FROM django_migrations WHERE app = 'problems' AND name >= '0024' ORDER BY name"` を流す（primary の DB が止まっていれば、#605 の primary のコメントの P7 を読む）（AC1） | `0024_mediaassetcontent`・`0025_move_media_files_to_db`・`0026_remove_problem_legacy_images`・`0027_remove_subject_image_directory` の 4 行が出る（コメントで見たときは P7 の出力の 4 行が `[X]`） | Claude |  |  |
| M5 | 下の「片付けの記録」の primary の行と `.evidence/I605/primary_image.png`（Read で見る）を読む（AC2） | `I587 media:` の行（`moved=`・`deleted_assets=`・`deleted_links=` の数）があり、消した行の id が P3-b の「ファイルが無い」行と同じ。`moved` が P3-b の「ファイルがある」件数と同じ。画像に問題の画面と、その問題の画像が写っている（画像を使う問題が無いときは、その旨の記録がある） | Claude |  |  |
| M6 | `docs/reviews/open/I605_review.md` の「承認の記録」を読む（AC6） | P4（消える行・空にする値）・P9（primary のファイルと控え）・A2（harness の DB のコンテナと保存領域・harness-2 と study のファイル）のそれぞれに、人の言葉と日付がある（P5 で空にした値が無ければ、その旨） | Claude |  |  |
| M7 | 下の「片付けの記録」の A1 の行を読む（AC4） | harness-2・study の `backend/media` の消す前のファイルの一覧（それぞれの件数とパス）と、primary の P3-b の一覧がある | Claude |  |  |
| M8 | `docs/runbooks/backend-check.md` §4 と `backend/problems/tests/test_I590_review_leftovers.py` の `CLEAR_IMAGE_DIRECTORY_SQL` を Read で並べて読む（AC7） | 空にする SQL の文が同じ（`UPDATE problems_subject SET image_directory = '' WHERE image_directory <> ''`）。§4 の SQL は `docker compose exec -T db psql -U postgres -d learning_app -c` で流す形、移行の流し直しは `docker compose run --rm --no-deps -T backend python manage.py migrate problems`。§4 に「流す前に数える」の SQL（0025・0026・0027 の対象）と、0026 の SELECT・UPDATE がある | Claude |  |  |

## 片付けの記録
<!-- implement の段階で、A1（app-1 で読んだ一覧）・A3（#605 の primary のコメントの写し）を書く -->
| ワークツリー | 記録 |
|---|---|
| primary（P1〜P10） | 2026-11-20 に primary のセッションが実施（#605 のコメント https://github.com/osushi0404-dev/study-app-multitenant/issues/605#issuecomment-7041444387 の写し）。P2 控え `backup_I605_before_primary_20261120_224053.sql`（330791 バイト）。P3-a 移行の前は problems 0021 まで [X]（0022〜0027 は未適用）。`migrate --plan` は accounts.0022・0023・problems.0022〜0027・studylogs.0002。P3-b `media_assets` 8 行（生きている行 1 行）: ファイルあり 0・ファイル無し 1（id=e534f87d-d735-4659-b715-d82fd2a672de key=org/personal/subjects/aws-saa/problem/q02_problem.png・問題 186 に紐づけ 1）。`backend/media` は 7 個（org/personal/subjects/i073-manual/ の problem 4・explanation 3）で、どの行からも使われていない。P3-c 0026 の対象 1 件（問題 186）。P3-d 0027 の対象 2 件（科目 20・21）。P5 UPDATE 1（問題）・UPDATE 2（科目）。P6 `I587 media: moved=0 already=0 deleted_assets=1 deleted_links=1`・`deleted id=e534f87d-… key=org/personal/subjects/aws-saa/problem/q02_problem.png`（P3-b のファイル無しの 1 件と一致）。キャッシュの削除は redis を起こしていないため失敗（最長 1 時間で切れる）。P7 problems 0001〜0027 [X]・`migrate --plan` は「No planned migration operations.」。P8 画像を使う問題が無い（moved=0・使われている行 0）ため画面の画像の確かめは無し。全コンテナ healthy。途中で backend・celery・celery-beat のイメージを作り直した（`drf_spectacular` が無く起動できなかった）。P9 `backend/media`（7 個）と控えを消し、無いことを確かめた |
| harness-1（A1・A2） | A1（2026-11-21）: `backend/media` は無い。DB のコンテナ `harness-1-db-1` は止まっている（Exited 24 時間前）。保存領域 `harness-1_postgres_data` はある。A2（2026-11-21）: 人がコンテナと保存領域を消した |
| harness-2（A1・A2） | A1（2026-11-21）: `backend/media` は 18 個（PNG 6 個: `bk/problems/aws-saa/questions/q02_problem.png`・`org/company_osushi_is_funny/subjects/{business-english,data-science,financial-planning}/problem/013f643f-6b67-45a5-bef3-ef5ce8713bc9.png`・`org/cute_school/subjects/high-school-english/problem/013f643f-….png`・`org/personal/subjects/aws-saa/problem/q02_problem.png`、空の目印ファイル `.gitkeep` 12 個: `org/personal/subjects/{2,3,4,5,s-517bc0f8,s-658a6484}/{problem,explanation}/.gitkeep`）。DB のコンテナ `harness-2-db-1` は止まっている（Exited 10 日前）。保存領域 `harness-2_postgres_data` はある。A2（2026-11-21）: 人がコンテナ・保存領域・`backend/media` を消した |
| study（A1・A2） | A1（2026-11-21）: study のワークツリーはフォルダごと無い（`git worktree list` に無く、`.claude/worktrees/` にも無い。親のフォルダの更新は 2026-11-20 22:35）。I605 の外でワークツリーごと撤去されたため、`backend/media` も無い。消す前の一覧はイシューの「現状の問題」（18 個・2026-11-20 に数えた）と A1 の調べ（2026-11-20・`org/personal/subjects/aws-saa/…`・`bk/…`・`org/company_osushi_is_funny/…`・`org/cute_school/…`）。DB の保存領域は元から無い |

## 画面確認
<!-- frontend/src を変えない。primary の画像の確かめ（P8）は primary のセッションが行い、上の M5 で見る -->
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
|  |  | 理由: frontend/src を変えない（primary の画像の確かめは M5） |  |  |  |  |

結論:
