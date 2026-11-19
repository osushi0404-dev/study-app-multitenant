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
- backend: 実装前のため未実行
- frontend: 実装前のため未実行

## 共通の準備（pytest）
- 組織 A・B（`Organization`）、A の科目 `subj_a`・B の科目 `subj_b`、A の管理者 `admin_a`（`role='admin'`）・A の一般の利用者 `learner_a`・B の管理者 `admin_b`
- 画像: Pillow で作った 8×8 の PNG のバイト列 `PNG_BYTES`（`SimpleUploadedFile('a.png', PNG_BYTES, content_type=...)`）
- 書き込みの見張り: `builtins.open` を包み、書き込みのモード（`w`・`a`・`x`・`+`）で開かれたら `AssertionError` にする fixture `no_file_writes`（`os.makedirs` も同じく落とす）

## テストケース

| TC | 受け入れ条件 | 種別 | 内容 | 期待値 | 結果 |
|---|---|---|---|---|---|
| TC-01 | AC1 | pytest | `test_I587_media_in_db.py::test_create_and_update_store_content_without_files`。`no_file_writes` の下で、`admin_a` が `POST /api/problems/`（multipart・`question_image_1`＝PNG・`explanation_image_1`＝PNG）→ 続けて `PATCH /api/problems/<id>/`（`question_order=[{"new": "question_image_9"}]`・`question_image_9`＝別の PNG） | 作成は 201、更新は 200。`MediaAssetContent` が作成の後 2 件・更新の後 2 件（古い問題画像は論理削除で中身が消え、新しい 1 件が入る）。各中身の `bytes(data)` が送った PNG と同じ、`checksum_sha256 == sha256(PNG).hexdigest()`、`file_size_bytes == len(PNG)`。ファイルの書き込みが 1 回も無い（`no_file_writes` が落ちない） | 実装前のため未実行 |
| TC-02 | AC13・R2 | pytest | `test_create_stores_detected_mime_not_client_content_type`。PNG のバイト列を `content_type='text/html'` で送って問題を作り、その画像を `GET /api/media/<id>/` | `MediaAsset.mime_type == 'image/png'`。配信の `Content-Type` が `image/png` | 実装前のため未実行。失敗の注入: 保存を `image_file.content_type` に戻すと `'text/html' != 'image/png'` で落ちることを確かめる |
| TC-03 | AC6 | pytest | `test_I587_media_migration.py::test_0024_sets_external_storage`。`settings.MIGRATION_MODULES = {}` で `MigrationLoader` から `problems.0024_mediaassetcontent` を取り、0023 の状態で `unapply` → `apply`。`pg_attribute` で `media_asset_contents.data` の `attstorage` を読む | `attstorage == 'e'`（EXTERNAL）。`unapply` の後は表が無い | 実装前のため未実行。失敗の注入: `RunSQL` を一時的に外した写しで `'x' != 'e'` で落ちることを確かめる |
| TC-04 | AC5 | pytest | `test_media_etag_304_without_reading_content`。`admin_a` の画像を 1 回目 `GET`（ETag を取る）→ 2 回目 `If-None-Match: <ETag>`。2 回目は `CaptureQueriesContext` で SQL を集める。別に `If-None-Match: W/<ETag>`・`If-None-Match: "x", <ETag>`・`If-None-Match: *` も送る。`checksum_sha256=None` に `update()` で書き換えた行も取る | 1 回目 200・`ETag == '"<sha256>"'`。2 回目 304・本文が空・`ETag`・`Cache-Control: private, max-age=3600` が付く・集めた SQL に `media_asset_contents` が無い。`W/` 付きは 200。複数の値に一致があれば 304。`*` は 304。`checksum_sha256` が null の行は ETag の見出しが無く、`If-None-Match: "None"` でも 200 | 実装前のため未実行。失敗の注入: 304 の判定を中身の取得の後に動かすと SQL の確かめで落ちることを確かめる |
| TC-05 | AC2・AC13 | pytest | `test_media_response_headers`（`learner_a` で `GET /api/media/<id>/`）と `test_media_unknown_mime_is_octet_stream`（`mime_type='text/html'` に `update()` で書き換えた行を取る） | 200。本文が PNG のバイト列。`Content-Type: image/png`・`Cache-Control: private, max-age=3600`・`X-Content-Type-Options: nosniff`・`Content-Security-Policy: default-src 'none'; sandbox`・`Content-Disposition: inline`。書き換えた行は `Content-Type: application/octet-stream` | 実装前のため未実行 |
| TC-06 | AC2 | pytest | `test_media_requires_login`。認証なしの `APIClient` で `GET /api/media/<id>/` | 401。本文が `{"error": {...}}` の形（`main_message` を持つ） | 実装前のため未実行 |
| TC-07 | AC2・AC11 | pytest | `test_media_tenant_boundary`（`parametrize`）: (a) `admin_b`（他の組織）(b) 論理削除した画像（`is_deleted=True`）(c) `organization=None` の行 (d) `subject=None` の行 (e) 中身の無い行（`MediaAssetContent` を消した行）(f) 無い UUID (g) 組織に属さない利用者。対に (h) `learner_a`（同じ組織の一般の利用者）| (a)〜(g) は 404・本文が `{"error": {...}}`。(h) は 200 | 実装前のため未実行。失敗の注入: 取り出しから `organization_id`・`subject__organization_id` の条件を外すと (a) が 200 で落ちることを確かめる |
| TC-08 | AC1 | pytest | `test_I006_subject_org_admin.py` の TC-AUTO-009・010 を消し、`test_create_subject_makes_no_folders` を足す。`no_file_writes` の下で `admin_a` が `POST /api/subjects/ {"name": "新科目"}` | 201。ファイル・フォルダを作らない（`no_file_writes` が落ちない） | 実装前のため未実行。実装前のコードではフォルダ作り（`os.makedirs`）で落ちることを確かめる |
| TC-09 | AC1 | pytest | `test_upload_image_action_stores_content`。`admin_a` が `POST /api/problems/<id>/images/upload/`（`file`＝PNG・`usage_kind=problem`）。もう 1 回、GIF のバイト列で送る | PNG は 201・`MediaAssetContent` が 1 件・中身が PNG と同じ・`no_file_writes` が落ちない。GIF は 400・本文が `{"error": {...}}`・行が増えない | 実装前のため未実行 |
| TC-10 | AC1 | pytest | `test_discard_removes_content`。(a) `DELETE /api/problems/<id>/images/delete/<asset_id>/`（他の問題に紐づかない画像）(b) `PATCH` で `question_order=[]`（全部外す）(c) `DELETE /api/problems/<id>/`（問題の削除）。(d) 2 つの問題が同じ画像を共有しているときに片方を (c) | (a)〜(c): 画像の `is_deleted=True`・`MediaAssetContent` が 0 件・`no_file_writes` が落ちない。(d): 共有している画像の中身は残り、`is_deleted=False` | 実装前のため未実行 |
| TC-11 | AC4 | pytest | `test_list_and_quiz_do_not_read_content`。画像 2 枚（問題・解説）付きの問題で、`CaptureQueriesContext` の下で (a) `admin_a` の `GET /api/problems/`（キャッシュを捨ててから）(b) `learner_a` のクイズの開始と問題の取得 (c) 回答の送信（解説の画像が応答に入る）| どの応答も 200／201 で、画像の `url` が `/api/media/<id>/`。集めた SQL のどれにも `media_asset_contents` が無い | 実装前のため未実行。失敗の注入: `get_media_assets` に `select_related('asset__content')` を一時的に足すと落ちることを確かめる |
| TC-12 | AC7 | pytest | `test_I587_media_migration.py::test_0025_moves_files_and_reverts`。`MigrationLoader` で `problems.0025_move_media_files_to_db` を取る。`problems.media_migration.LEGACY_MEDIA_ROOT` を `tmp_path` に差し替え、`tmp_path` に PNG を置いた画像の行と、ファイルの無い画像の行（紐づけ 1 件つき）を作って `apply`。次に `unapply` | `apply` の後: ファイルのある行は中身が入り `sha256` と大きさが一致。ファイルの無い行と紐づけは消える。標準出力に `I587 media: moved=1 already=0 deleted_assets=1 deleted_links=1`。`unapply` の後: 中身のある画像が `tmp_path / storage_key` に同じバイト列で書き戻される | 実装前のため未実行 |
| TC-13 | AC7 | pytest | `test_move_media_files_cases`（関数を直接・今のモデルを渡す）: (a) 2 回続けて呼ぶ (b) 論理削除の行（ファイルなし）(c) `dry_run=True` (d) `checksum_sha256`・`file_size_bytes` が null の行（ファイルあり） | (a) 1 回目 `moved=1`、2 回目 `moved=0 already=1`・`MediaAssetContent` は 1 件のまま。(b) 触らない（行が残り、中身も作らない）。(c) 判定と件数だけを返し、DB が変わらない。(d) 中身が入り、`checksum_sha256`・`file_size_bytes` が読んだ中身の値で埋まる | 実装前のため未実行 |
| TC-14 | AC7・R7 | pytest | `test_move_media_files_refuses_anomalies`（`parametrize`）: (a) ファイルの中身が `checksum_sha256` と違う (b) 中身が画像でない（テキスト）(c) `storage_key='../../etc/passwd'`。別に `test_check_media_migration_command`（`call_command('check_media_migration')` の出力） | (a)〜(c) は `MediaMigrationError`（文にキーと理由が入る）で、DB が変わらない（中身 0 件・行が残る）。コマンドは行ごとの判定・件数・古い列に値のある問題の件数を出し、DB を変えない | 実装前のため未実行 |
| TC-15 | AC10 | pytest | `test_0026_refuses_legacy_values_then_removes_columns`。`MigrationLoader` で 0026 を取り、0025 の状態で `unapply` → (a) 過去のモデルで `question_image='x.png'` の問題を作って `apply` (b) その値を空にしてから `apply` | (a) `RuntimeError`（文に件数 1）で止まり、列が残る。(b) `problems_problem` に `question_image`・`explanation_image` の列が無い | 実装前のため未実行 |
| TC-16 | AC3 | Jest | `frontend/src/components/__tests__/MediaImage.test.tsx`。axios-mock-adapter で `/api/media/a/` を (a) 遅らせる (b) 404 (c) PNG の `Blob` で返す。`URL.createObjectURL` を `jest.fn(() => 'blob:a')`・`revokeObjectURL` を `jest.fn()` に差し替える | (a) `Skeleton` が出る（`getByTestId` を使わず、`role` の無い枠を `aria-busy="true"` で探す）(b) 「画像を読み込めませんでした」と「再読み込み」のボタン。押すともう 1 回取りにいく (c) `img` の `src` が `blob:a`・`alt` が渡した値。外すと `revokeObjectURL('blob:a')` が呼ばれる | 実装前のため未実行 |
| TC-17 | R8 | Jest | `frontend/src/services/__tests__/api.skipErrorToast.test.ts`。`ApiClient` を差し替えた axios で作り、404 を返す設定で (a) `skipErrorToast: true` (b) 指定なし | (a) `toast.error` が呼ばれない (b) `toast.error('要求されたリソースが見つかりません')` が 1 回 | 実装前のため未実行 |
| TC-18 | AC3 | Jest | 既存の `ProblemImageList.test.tsx`・`ProblemPreview.test.tsx`・`QuizSession.test.tsx`（画像の節）を、`getMediaUrl` の代わりに `/api/media/<id>/` の差し替えと `blob:` の `src` で確かめる形に直す。`ImageUploadArea` の保存済みの画像に `ImageUploadArea.test.tsx` を足す | 問題画像・解説画像の `img` が順に `blob:` の `src` で出る。押すと拡大のダイアログに同じ画像が出る。編集のダイアログの保存済みの画像も `blob:` で出て、新しく選んだ画像は `URL.createObjectURL(file)` の値で出る | 実装前のため未実行 |
| TC-19 | AC10 | pytest・Jest | pytest `test_problem_payloads_have_no_legacy_image_fields`: 管理の一覧・クイズの問題・回答の応答のキーに `question_image`・`explanation_image` が無く、`question_images`・`explanation_images` はある。Jest `problemImages.test.ts`: `pickImageUrls([a, b])` が `[a.url, b.url]`、`undefined` で `[]` | 期待値のとおり | 実装前のため未実行 |
| TC-20 | AC12 | 決定論ゲート | `frontend/src`（`__tests__` を除く）に古い置き場の `/media`（`/api/media` を除く。`setupProxy.js` の `'/media'` にも当たる）が無い | exit 0 | 実装前: exit 1（2026-11-19・`utils/url.ts` などに残っている） |
| TC-21 | AC12 | 決定論ゲート | `backend` の `.py`（`tests`・`migrations` を除く）に古い置き場の `/media`（`/api/media` を除く）が無い | exit 0 | 実装前: exit 1（2026-11-19・`models.py:172`・`:179`・`:418`） |
| TC-22 | AC12 | 決定論ゲート | `nginx/default.conf` に古い置き場の `/media` が無い | exit 0 | 実装前: exit 1（2026-11-19・`:16`） |
| TC-23 | AC12 | pytest | `test_media_static_route_is_gone`。`settings.DEBUG=True` で URL の設定を読み直し（`importlib.reload(core.urls)`・`clear_url_caches()`）、`resolve('/media/org/x/a.png')` | `Resolver404` | 実装前のため未実行 |
| TC-24 | 全体 | CI | backend（pytest 全件・ruff・bandit・`makemigrations --check`）・frontend（Jest・型・ESLint）・E2E | すべて success | 実装前のため未実行 |

## 決定論ゲート（自動実走）
```bash
! grep -rq -e "^/media" -e "[^i]/media" --exclude-dir=__tests__ frontend/src
! grep -rq -e "^/media" -e "[^i]/media" --include=*.py --exclude-dir=tests --exclude-dir=migrations backend
! grep -q -e "^/media" -e "[^i]/media" nginx/default.conf
```

## 失敗の注入（false-green の確かめ）
- TC-20〜TC-22（ゲート）: 実装の前の今のコードで 3 行とも exit 1 になることを確かめた（2026-11-19）。`/api/media/1/` だけを書いた一時ファイルでは exit 0（新しい URL に当たらない）、`['/api', '/media']` を書いた一時ファイルでは exit 1（`setupProxy.js` の形に当たる）ことも確かめた（2026-11-19・計画レビューの Warning への対応）
- TC-02・TC-03・TC-04・TC-07・TC-08・TC-11: 各行の「失敗の注入」を、実装のステップでテストを先に書くとき（または一時的に守りを外した写し）に確かめ、結果をこの表の結果の欄に書く
- TC-13〜TC-15: 止める・飛ばす場合ごとに、守りの行（`already` の判定・`resolve()` の確かめ・`sha256` の比べ・古い列の数え）を一時的に外すと落ちることを確かめる
