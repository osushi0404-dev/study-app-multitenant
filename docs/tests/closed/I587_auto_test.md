<!--
## 自動テスト品質基準
各テストケースが以下を満たすことを確認してください:
- アサーションに具体的な期待値（status_code の数値・body の具体フィールド等）があるか
- 「正常レスポンスを確認」のような曖昧な記述になっていないか
- 他テナントデータへのアクセス拒否テストが含まれているか（認可変更がある場合）
- テストが実装詳細をトレースするだけでなく、仕様を検証する形になっているか
-->

# I587 自動テスト: 問題・解説の画像を DB に保存し、組織の境界を確かめる API から返す

実行コマンド（例）: `docker compose exec -T backend pytest problems/tests/test_I587_media_in_db.py problems/tests/test_I587_media_migration.py problems/tests/test_I073_image_update.py problems/tests/test_I472_quiz_answer_explanation_image.py problems/tests/test_I006_subject_org_admin.py -q` / `docker compose exec -T frontend npm test -- --watchAll=false src/components src/hooks src/pages/__tests__/QuizSession.test.tsx src/utils`（pytest・Jest・E2E は CI が PR ごとに流すので、test-gate では流し直さない）

結果:
- backend: 手元（2026-11-19・コンテナ）で全件 797 passed（/simplify の前と後の両方）。`makemigrations --check` は変更なし・ruff は合格。CI の結果は review-gate で記入
- frontend: 手元で Jest 全件 150 passed（/simplify の前と後の両方）・`tsc --noEmit` 合格・ESLint（`--max-warnings=0`）合格・`npm run build` 合格（警告は `Register.tsx` の既存の 2 件だけ）

## 共通の準備（pytest）
- 組織 A・B（`Organization`）、A の科目 `subj_a`・B の科目 `subj_b`、A の管理者 `admin_a`（`role='admin'`）・A の一般の利用者 `learner_a`・B の管理者 `admin_b`
- 画像: Pillow で作った 8×8 の PNG のバイト列 `PNG_BYTES`（`SimpleUploadedFile('a.png', PNG_BYTES, content_type=...)`）
- 書き込みの見張り: `builtins.open` を包み、書き込みのモード（`w`・`a`・`x`・`+`）で開かれたら `AssertionError` にする fixture `no_file_writes`（`os.makedirs` も同じく落とす）

## テストケース

| TC | 受け入れ条件 | 種別 | 内容 | 期待値 | 結果 |
|---|---|---|---|---|---|
| TC-01 | AC1 | pytest | `test_I587_media_in_db.py::test_create_and_update_store_content_without_files`。`no_file_writes` の下で、`admin_a` が `POST /api/problems/`（multipart・`question_image_1`＝PNG・`explanation_image_1`＝PNG）→ 続けて `PATCH /api/problems/<id>/`（`question_images_order=[{"new": "question_image_9"}]`・`question_image_9`＝別の PNG） | 作成は 201、更新は 200。`MediaAssetContent` が作成の後 2 件・更新の後 2 件（古い問題画像は論理削除で中身が消え、新しい 1 件が入る）。各中身の `bytes(data)` が送った PNG と同じ、`checksum_sha256 == sha256(PNG).hexdigest()`、`file_size_bytes == len(PNG)`。ファイルの書き込みが 1 回も無い（`no_file_writes` が落ちない） | OK（2026-11-19） |
| TC-02 | AC13・R2 | pytest | `test_create_stores_detected_mime_not_client_content_type`。PNG のバイト列を `content_type='text/html'` で送って問題を作り、その画像を `GET /api/media/<id>/` | `MediaAsset.mime_type == 'image/png'`。配信の `Content-Type` が `image/png` | OK（2026-11-19）。失敗の注入（計画時の注記）: 保存を `image_file.content_type` に戻すと `'text/html' != 'image/png'` で落ちることを確かめる |
| TC-03 | AC6 | pytest | `test_I587_media_migration.py::test_0024_sets_external_storage`。`settings.MIGRATION_MODULES = {}` で `MigrationLoader` から `problems.0024_mediaassetcontent` を取り、0023 の状態で `unapply` → `apply`。`pg_attribute` で `media_asset_contents.data` の `attstorage` を読む | `attstorage == 'e'`（EXTERNAL）。`unapply` の後は表が無い | OK（2026-11-19）。失敗の注入（計画時の注記）: `RunSQL` を一時的に外した写しで `'x' != 'e'` で落ちることを確かめる |
| TC-04 | AC5 | pytest | `test_media_etag_304_without_reading_content`。`admin_a` の画像を 1 回目 `GET`（ETag を取る）→ 2 回目 `If-None-Match: <ETag>`。2 回目は `CaptureQueriesContext` で SQL を集める。別に `If-None-Match: W/<ETag>`・`If-None-Match: "x", <ETag>`・`If-None-Match: *`・`If-None-Match: "x"` も送る。`checksum_sha256=None` に `update()` で書き換えた行も取る | 1 回目 200・`ETag == '"<sha256>"'`。2 回目 304・本文が空・`ETag`・`Cache-Control: private, max-age=3600` が付く・集めた SQL に `media_asset_contents` が無い。`W/` 付き・複数の値に一致・`*` は 304（RFC 9110 の弱い比較・2026-11-20 に変更）。一致しない `"x"` は 200。`checksum_sha256` が null の行は ETag の見出しが無く、`If-None-Match: "None"` でも 200 | OK（2026-11-20）。追加の直しの前のコード（自前の強い一致）では `W/` 付きが 200 で落ちた |
| TC-05 | AC2・AC13 | pytest | `test_media_response_headers`（`learner_a` で `GET /api/media/<id>/`）と `test_media_unknown_mime_is_octet_stream`（`mime_type='text/html'` に `update()` で書き換えた行を取る）と `test_media_ignores_list_query_params`（`?ordering=id`・`?search=x`・`?page=2` を付ける・fix-loop F8） | 200。本文が PNG のバイト列。`Content-Type: image/png`・`Cache-Control: private, max-age=3600`・`X-Content-Type-Options: nosniff`・`Content-Security-Policy: default-src 'none'; sandbox`・`Content-Disposition: inline`。書き換えた行は `Content-Type: application/octet-stream`。一覧の値を付けても 200 と画像 | OK（2026-11-19） |
| TC-06 | AC2 | pytest | `test_media_requires_login`。認証なしの `APIClient` で `GET /api/media/<id>/` | 401。本文が `{"error": {...}}` の形（`main_message` を持つ） | OK（2026-11-19） |
| TC-07 | AC2・AC11 | pytest | `test_media_tenant_boundary`（`parametrize`）: (a) `admin_b`（他の組織）(b) 論理削除した画像（`is_deleted=True`）(c) `organization=None` の行 (d) `subject=None` の行 (e) 中身の無い行（`MediaAssetContent` を消した行）(f) 無い UUID (g) 組織に属さない利用者。対に (h) `learner_a`（同じ組織の一般の利用者）| (a)〜(g) は 404・本文が `{"error": {...}}`。(h) は 200 | OK（2026-11-19）。失敗の注入（計画時の注記）: 取り出しから `organization_id`・`subject__organization_id` の条件を外すと (a) が 200 で落ちることを確かめる |
| TC-08 | AC1 | pytest | `test_I006_subject_org_admin.py` の TC-AUTO-009・010 を消し、`test_I587_media_in_db.py::test_create_subject_makes_no_folders` を足す。`no_file_writes` の下で `admin_a` が `POST /api/subjects/ {"name": "新科目"}` | 201。ファイル・フォルダを作らない（`no_file_writes` が落ちない） | OK（2026-11-19）。科目の作成でフォルダを作る形に一時的に戻すと落ちた（失敗の注入の節） |
| TC-09 | AC1 | pytest | `test_upload_image_action_stores_content`。`admin_a` が `POST /api/problems/<id>/images/upload/`（`file`＝PNG・`usage_kind=problem`）。もう 1 回、GIF のバイト列で送る。別に `test_upload_image_action_rejects_bad_input`（`file` なし・`usage_kind="x"`）| PNG は 201・`MediaAssetContent` が 1 件・中身が PNG と同じ・`position` が 1・`no_file_writes` が落ちない。GIF・`file` なし・`usage_kind` の誤りは 400・本文が `{"error": {...}}`（`main_message` を持つ）・行が増えない | OK（2026-11-20）。追加の直しの前のコードでは `file` なし・`usage_kind` の誤りが独自の形 `{"error": "..."}` で落ちた |
| TC-10 | AC1 | pytest | `test_discard_removes_content`（(a) `DELETE /api/problems/<id>/images/delete/<asset_id>/`（他の問題に紐づかない画像）(b) `PATCH` で `question_images_order=[]` (c) `DELETE /api/problems/<id>/`）・`test_delete_problem_keeps_shared_content`・`test_delete_image_ignores_deleted_links_of_other_problems`（fix-loop F1）・`test_delete_image_rejects_missing_or_deleted_own_link`（自分の紐づけが無い・論理削除済み〔F7〕・他の組織の画像の ID〔セキュリティレビュー〔追加の直し〕〕）| (a)〜(c): 画像の `is_deleted=True`・`MediaAssetContent` が 0 件・`no_file_writes` が落ちない。共有している画像の中身は残る。共有の相手が論理削除済みなら外した画像は中身ごと消えて 404。自分の紐づけが無い・論理削除済みは 404・本文が `{"error": {...}}`・紐づけと画像が変わらない | OK（2026-11-20）。追加の直しの前のコードでは 3 つの場合（紐づけ無し・論理削除済み・他の組織の画像）がどれも独自の形の本文か 200 で落ちた。形の違う ID（`not-a-uuid`）は経路で 404（`test_delete_image_route_accepts_only_uuid`） |
| TC-11 | AC4 | pytest | `test_list_and_quiz_do_not_read_content`。画像 2 枚（問題・解説）付きの問題で、`CaptureQueriesContext` の下で (a) `admin_a` の `GET /api/problems/`（キャッシュを捨ててから）(b) `learner_a` のクイズの開始と問題の取得 (c) 回答の送信（解説の画像が応答に入る）| どの応答も 200／201 で、画像の `url` が `/api/media/<id>/`。集めた SQL のどれにも `media_asset_contents` が無い | OK（2026-11-19）。失敗の注入（計画時の注記）: `get_media_assets` に `select_related('asset__content')` を一時的に足すと落ちることを確かめる |
| TC-12 | AC7 | pytest | `test_I587_media_migration.py::test_0025_moves_files_and_reverts`。`MigrationLoader` で `problems.0025_move_media_files_to_db` を取る。`problems.media_migration.LEGACY_MEDIA_ROOT` を `tmp_path` に差し替え、`tmp_path` に PNG を置いた画像の行と、ファイルの無い画像の行（紐づけ 1 件つき）を作って `apply`。次に `unapply` | `apply` の後: ファイルのある行は中身が入り `sha256` と大きさが一致。ファイルの無い行と紐づけは消える。標準出力に `I587 media: moved=1 already=0 deleted_assets=1 deleted_links=1` と、消した行の `I587 media: deleted id=<id> key=<key>`（移した行は出ない・fix-loop F2。出力は行ごとに分け、消した行の行が期待の 1 行と完全に一致することで比べる〔F6・2026-11-20〕）。`unapply` の後: 中身のある画像が `tmp_path / storage_key` に同じバイト列で書き戻される | OK（2026-11-19） |
| TC-13 | AC7 | pytest | `test_move_media_files_cases`（関数を直接・今のモデルを渡す）: (a) 2 回続けて呼ぶ (b) 論理削除の行（ファイルなし）(c) `dry_run=True` (d) `checksum_sha256`・`file_size_bytes` が null の行（ファイルあり） | (a) 1 回目 `moved=1`、2 回目 `moved=0 already=1`・`MediaAssetContent` は 1 件のまま。(b) 触らない（行が残り、中身も作らない）。(c) 判定と件数だけを返し、DB が変わらない。(d) 中身が入り、`checksum_sha256`・`file_size_bytes` が読んだ中身の値で埋まる | OK（2026-11-19） |
| TC-14 | AC7・R7 | pytest | `test_move_media_files_refuses_anomalies`（`parametrize`）: (a) ファイルの中身が `checksum_sha256` と違う (b) 中身が画像でない（テキスト）(c) `storage_key='../../etc/passwd'`。別に `test_check_media_migration_command`（`call_command('check_media_migration')` の出力） | (a)〜(c) は `MediaMigrationError`（文にキーと理由が入る）で、DB が変わらない（中身 0 件・行が残る）。コマンドは行ごとの判定と件数を出し、DB を変えない（古い列の値は 0026 が数えて止める〔TC-15〕。/simplify でコマンドから外した） | OK（2026-11-19） |
| TC-15 | AC10 | pytest | `test_0026_refuses_legacy_values_then_removes_columns`。`MigrationLoader` で 0026 を取り、0025 の状態で `unapply` → (a) 過去のモデルで `question_image='x.png'` の問題を作って `apply` (b) その値を空にしてから `apply` | (a) `RuntimeError`（文に件数 1）で止まり、列が残る。(b) `problems_problem` に `question_image`・`explanation_image` の列が無い | OK（2026-11-19） |
| TC-16 | AC3 | Jest | `frontend/src/components/__tests__/MediaImage.test.tsx`。`services/mediaService` の `getMediaBlob` を差し替えて (a) 終わらない (b) 失敗 (c) PNG の `Blob` を返す。`height={300}` を渡す場合も見る | (a) `Skeleton` が出る（ラベル「問題画像 1を読み込み中」・`aria-busy="true"`・高さ 300px）(b) 高さ 300px の枠に「画像を読み込めませんでした」と「再読み込み」のボタン（`min-height: 44px`・`min-width: 44px`）。押すともう 1 回取りにいく (c) `img` の `src` が `blob:a`・`alt` が渡した値。外すと `revokeObjectURL('blob:a')` が呼ばれる | OK（2026-11-20）。追加の直しの前のコードでは枠の高さ（150px）・ボタンの大きさ（指定なし）で落ちた |
| TC-17 | R8 | Jest | `frontend/src/services/__tests__/api.test.ts` の I587 TC-17。`ApiClient` を差し替えた axios で作り、404 を返す設定で (a) `skipErrorToast: true` (b) 指定なし | (a) `toast.error` が呼ばれない (b) `toast.error('要求されたリソースが見つかりません')` が 1 回 | OK（2026-11-19） |
| TC-18 | AC3 | Jest | 既存の `ProblemImageList.test.tsx`・`ProblemPreview.test.tsx`・`QuizSession.test.tsx`（画像の節）と新しい `ImageUploadArea.test.tsx` で、`useMediaImage` を手動のモック（`hooks/__mocks__/useMediaImage.ts`・渡された API の URL を取れた画像の URL として返す）に差し替え、本物の `MediaImage` を描いて確かめる（取得と 4 つの状態は TC-16） | 問題画像・解説画像の `img` が順に（`ProblemImageList` の画像は高さ 300px・`object-fit: contain`〔2026-11-20〕） `/api/media/<id>/` の `src` で出る。押すと拡大のダイアログに同じ画像の URL が出る。編集のダイアログの保存済みの画像は API の URL、新しく選んだ画像は `URL.createObjectURL(file)` の値で出る | OK（2026-11-19） |
| TC-19 | AC10 | pytest・Jest | pytest `test_problem_payloads_have_no_legacy_image_fields`: 管理の一覧・クイズの問題・回答の応答のキーに `question_image`・`explanation_image` が無く、`question_images`・`explanation_images` はある。Jest `problemImages.test.ts`: `pickImageUrls([a, b])` が `[a.url, b.url]`、`undefined` で `[]` | 期待値のとおり | OK（2026-11-19） |
| TC-20 | AC12 | 決定論ゲート | `frontend/src`（`__tests__` を除く）に古い置き場の `/media`（語の区切りつき。`/api/media`・`mediaService` には当たらない。`setupProxy.js` の `'/media'` には当たる）が無い | exit 0 | 実装前: exit 1（2026-11-19・`utils/url.ts` などに残っている）。実装後: exit 0（2026-11-19） |
| TC-21 | AC12 | 決定論ゲート | `backend` の `.py`（`tests`・`migrations` を除く）に古い置き場の `/media`（`/api/media` を除く）が無い | exit 0 | 実装前: exit 1（2026-11-19・`models.py:172`・`:179`・`:418`）。実装後: exit 0（2026-11-19） |
| TC-22 | AC12 | 決定論ゲート | `nginx/default.conf` に古い置き場の `/media` が無い | exit 0 | 実装前: exit 1（2026-11-19・`:16`）。実装後: exit 0（2026-11-19） |
| TC-23 | AC12 | pytest | `test_media_static_route_is_gone`。`settings.DEBUG=True` で URL の設定を読み直し（`importlib.reload(core.urls)`・`clear_url_caches()`）、`resolve('/media/org/x/a.png')` | `Resolver404` | OK（2026-11-19） |
| TC-24 | 全体 | CI | backend（pytest 全件・ruff・bandit・`makemigrations --check`）・frontend（Jest・型・ESLint）・E2E | すべて success | OK（2026-11-19・eedec7dc） |

## 決定論ゲート（自動実走）
```bash
! grep -rq -e "^/media\b" -e "[^i]/media\b" --exclude-dir=__tests__ frontend/src
! grep -rq -e "^/media\b" -e "[^i]/media\b" --include=*.py --exclude-dir=tests --exclude-dir=migrations backend
! grep -q -e "^/media\b" -e "[^i]/media\b" nginx/default.conf
```

## 失敗の注入（false-green の確かめ）
- TC-20〜TC-22（ゲート）: 実装の前の今のコードで 3 行とも exit 1 になることを確かめた（2026-11-19）。`/api/media/1/` だけを書いた一時ファイルでは exit 0（新しい URL に当たらない）、`['/api', '/media']` を書いた一時ファイルでは exit 1（`setupProxy.js` の形に当たる）ことも確かめた（2026-11-19・計画レビューの Warning への対応）
- 実装の中で語の区切りを付けた形に直した（`[^i]/media` だけでは `../services/mediaService` に当たる誤検知が出た）。直した形で、`['/api', '/media']`（実装前の `setupProxy.js` の行）と `'/media/a.png'`（実装前の `models.py` の形）を書いた一時ファイルは exit 1、`mediaService` の import と `/api/media/1/` だけの一時ファイルは exit 0 になることを確かめた（2026-11-19）
- TC-02・TC-04・TC-07・TC-08・TC-11（2026-11-19）: 元のファイルを写してから 5 か所を一時的に壊した — 保存の MIME を `image_file.content_type` に戻す／配信で 304 の判定の前に中身を読む／取り出しから組織の 2 条件を外す／`get_media_assets` に `select_related('asset__content')` を足す／科目の作成でフォルダを作る。結果: TC-02・TC-04・TC-07（other_org・null_org・null_subject）・TC-08・TC-11 が落ちた。写しから戻した後に全部通った
- TC-13〜TC-15（2026-11-19）: 4 か所を一時的に外した — `already` の判定／`is_relative_to` の確かめ／`checksum_sha256` の比べ／0026 の数えの止め。結果: TC-13・TC-14（checksum・outside）・TC-15 が落ちた。TC-14 の outside は、守りを外すと「画像ではありません」で止まって通ってしまったので、止まった理由の文まで確かめる形に直してから確かめ直した
- TC-03（2026-11-19）: テストの DB で通る（`attstorage == 'e'`）。0024 の `RunSQL` を一時的に外すと `assert 'x' == 'e'` で落ちた。写しから戻した後に通った

## 再発防止記録（fix-loop・2026-11-19）
- なぜ失敗したか: F1 は「ほかの問題が使っているか」の判定が 3 か所に別々にあり、`delete_image` だけが論理削除の紐づけを数えていた（I587 の前からの形。中身が DB に残ると配信され続けるので影響が大きくなった）。F2 は、追跡ファイルの削除と、そのファイルを読む移行を同じ変更に入れたので、ほかの環境では「消える → 読む」の順になる
- 何を変えたか: F1 は `delete_image` の判定に `is_deleted=False` を足した。F2 はユーザーの判断で削除はそのまま（計画 R6）にし、0025 が消した行の `id`・`key` を `migrate` の出力に並べるようにした
- セキュリティ上の考慮点: F1 は、消したつもりの画像が同じ組織の利用者に配信され続けるのを止める（組織の境界は越えていなかった）
- 次回どう防ぐか: 共有の判定を 1 か所にまとめるのは台帳の F4（ビューからサービスの非公開の関数を呼ぶ）と一緒に retro で扱う。追跡ファイルの削除と移行を同じ変更に入れるときは、ほかの環境での順番（git の取り込み → 起動の `migrate`）を計画の段階で確かめる（retro の振り返りに入れる）
- 確かめた結果: 新しいテスト `test_delete_image_ignores_deleted_links_of_other_problems`（TC-10 に追加）は直す前に `assert False is True`（`is_deleted`）で落ち、直した後に通った。TC-12 に「消した行の id・key が出力に出る・移した行は出ない」を足した。関係するテスト 153 passed（`test_I587_media_in_db.py`・`test_I587_media_migration.py`・`test_I073_image_update.py`・`test_I446_cross_api_tenant_isolation.py`）・ruff・bandit 合格（2026-11-19）

## 実行記録（test-gate・2026-11-20）
- `bash scripts/claude/gate-check.sh I587` → exit 0（コードレビュー 20261119_2319 と敵対的レビュー 20261119_2330 が OK・その後は記録の場所だけ）
- 決定論ゲート 3 行は review-gate（`code-review.sh`）が実走して 3 行とも exit 0。test-gate に回された重いもの（docker・npm・pytest）は無い
- pytest・Jest・E2E は CI が PR ごとに流し、review-gate が完了と成功を確かめた（`CI_WAIT: OK`・コミット eedec7dc）。手元では流し直していない
- TC-24（CI）: OK（2026-11-19・eedec7dc の CI がすべて success）

## 追加の直しの記録（implement・2026-11-20）
- テストを先に直し、追加の直しの前のコードで 6 件（pytest）と 3 件（Jest）が狙いどおりに落ちることを確かめてから実装した（上の各行の結果）
- 実装の後: pytest（`problems`・`core/tests/test_I446_cross_api_tenant_isolation.py`・`studylogs/tests/test_I452_quiz_review.py`）324 passed → /simplify の後 301 passed（`problems`・I446 のみ）・Jest 全件 150 passed・型・ESLint・ruff 合格
- /simplify の後に足したテスト: `test_delete_image_route_accepts_only_uuid`（画像の削除の経路は UUID の形だけを受ける）

## 再発防止記録（fix-loop・2026-11-20・F8）
- なぜ失敗したか: 配信のビューを `APIView` から `GenericAPIView` に変えたので、`get_object()` が `filter_queryset()` を通り、全体の設定の `OrderingFilter` が効くようになった。`serializer_class` も `ordering_fields` も無いビューで `?ordering=` を受けると、DRF が設定の誤りとして例外を投げ 500 になる
- 何を変えたか: `MediaAssetContentView` に `filter_backends = []`・`pagination_class = None` を書いた
- セキュリティ上の考慮点: 500 の本文に内部の情報は出ていなかった。組織の境界（`get_queryset()`）は変わらない
- 次回どう防ぐか: 一覧を返さない `GenericAPIView` を足すときは、全体の設定の絞り込み・ページ分けが効くことを前提に、使わないなら空にする（retro で規約 §6 への追記を検討）
- 確かめた結果: `test_media_ignores_list_query_params[?ordering=id]` が直す前に `ImproperlyConfigured` で落ち、直した後に 3 つとも通った。`test_I587_media_in_db.py`・`test_I446_cross_api_tenant_isolation.py` 134 passed・ruff 合格（2026-11-20）

## 実行記録（test-gate・追加の直しの後・2026-11-20）
- `bash scripts/claude/gate-check.sh I587` → exit 0（コードレビュー 20261120_0925・敵対的レビュー 20261120_0936 が OK・その後は記録の場所だけ）
- 決定論ゲート 3 行は review-gate が実走して exit 0。test-gate に回された重いものは無い
- pytest・Jest・E2E は CI（a7e24950）がすべて success（`CI_WAIT: OK`）。手元では流し直していない
