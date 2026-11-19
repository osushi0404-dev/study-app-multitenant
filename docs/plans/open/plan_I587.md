# I587 計画書: 問題・解説の画像を DB に保存し、組織の境界を確かめる API から返す

## 基本情報
- **計画書ID**: plan_I587
- **関連イシュー**: #587
- **Draft PR**: #588
- **作成根拠資料**: docs/issues/open/I587.md（起点イシュー・GitHub #587 の本文の写し）
- **実装後評価**: docs/reviews/open/I587_review.md
- **作成日**: 2026-11-19

## 1. 背景/目的
- 問題・解説の画像は、中身をファイル（`MEDIA_ROOT`＝`backend/media`）に、メタデータを DB（`MediaAsset`）に分けて持っている。配信は `/media/<storage_key>` の静的な配信で、ログイン・組織の確かめを通らない
- 目的: 画像の中身を PostgreSQL に保存し、ログインと組織の境界を確かめる API から返す。DB に置くための最適化を検討して要るものを入れる。今あるファイルは DB に移し、使わない見本のファイル・古い画像の列は承認を得て外す（イシューの設計確認メモ）

### 調査結果
**原因の概要**: 画像の「中身」と「どの問題の画像か」が別の場所にあるので、片方だけ残ったり、DB の控えから画像が戻らなかったりする。さらに、画像の配信がログインの確かめを通らないので、URL を知っていれば他の組織の画像も取れる。

**詳細**:
1. 保存の分離（`backend/problems/services/problem_service.py:118-198`）: `_save_image_as_asset` がファイルを `open(full_path, 'wb')` で書き、その後に `MediaAsset` を作る。ファイルの書き込みはトランザクションの外なので、DB が巻き戻ってもファイルは残る。消すとき（`_reconcile_images`・`delete_problem`）は `StorageService.delete_file` が失敗しても記録だけで続ける（`:400-415`・`:454-461`）
2. 実際の食い違い（2026-11-19・app-1 の開発の DB とディスク。`docker compose exec -T backend python manage.py shell` で数えた）: `MediaAsset` 4 件（組織「E2E Org A」・科目「I472確認用」）は 4 件ともファイルが無い。ディスクの `backend/media` には git に入った見本の PNG 6 枚と `.gitkeep` 12 個だけがあり、どの行からも使われていない。`organization`・`subject` が null の行 0 件・古い `question_image`・`explanation_image` に値のある問題 0 件・問題文と解説に `/media/` を含む問題 0 件。画像の合計 250,288 バイト・最大 62,572 バイト・DB 全体 11MB
3. 配信が認可を通らない: 開発は `backend/core/urls.py:40-44` の `static()`、本番の想定は `nginx/default.conf:16-20` の `alias` で、どちらも Django の認証・組織の確かめを通らない。`MediaAsset.get_url`（`backend/problems/models.py:416-418`）と古い形の `Problem.get_question_image_url`・`get_explanation_image_url`（`:167-179`）が `/media/...` を返す
4. ファイルに書く所は 4 か所: (a) `ProblemService._save_image_as_asset`（作成・更新）(b) `ProblemViewSet.upload_image`（`backend/problems/views.py:612-737`・`StorageService.save_file`。画面からは使われていない〔`frontend/src` に `images/upload` の呼び出しが無い〕）(c) `SubjectViewSet.perform_create`（`views.py:129-140`・科目ごとのフォルダと `.gitkeep` を作る）(d) 消す側の `StorageService.delete_file`（`problem_service.py`・`views.py:785`）
5. 画面の認証: 通信は `Authorization: Bearer`（`frontend/src/services/api.ts:24-31`）。`<img src>` は見出しを付けられないので、API に移すと今の `<img src="/media/...">` のままでは画像が取れない。画像を表示する所は `ProblemImageList`（問題のプレビュー・クイズの問題と解説）・`ImageModal`（拡大）・`ImageUploadArea`（編集のダイアログの保存済みの画像）の 3 つ
6. MIME の出どころ: `_save_image_as_asset` は `mime_type=image_file.content_type`（利用者が送った値）を保存している。検査（`validate_image_file`）は中身から MIME を判定するが、その値を保存していない。配信で保存した MIME を Content-Type に使うと、送り手が決めた型（例: `text/html`）で返ってしまう
7. 開発の起動（`docker-compose.yml:68-71`）は `migrate` を流してから `runserver` する。`./backend` はバインドマウントなので、マイグレーションのファイルを書いた時点で、コンテナを起こし直すと開発の DB に流れる。I492 では review-gate の `adversarial-review.sh` がコンテナを起こし、承認の前に破壊的なマイグレーションが流れた（`docs/reviews/closed/I492_review.md:49`。仕組みの直しは #579・未完了）
8. pytest は `--no-migrations`（`backend/pytest.ini:7`）。テストの DB はモデルから作られ、マイグレーションの `RunSQL`・`RunPython` は流れない。マイグレーションを確かめるテストは、I492 の TC-07 と同じく `MigrationLoader` で本物のマイグレーションを読んで `apply`／`unapply` する
9. 開発の DB は PostgreSQL 15.19。見張り（`pretooluse_guard.py`）は開発の DB への `ALTER TABLE` を危険操作として止めるので、保存方式の設定の確かめは開発の DB でなくテストの DB で行う（TC-03）
10. 問題一覧の応答は Redis に 1 時間キャッシュされる（`backend/core/cache_service.py:108-120`・`settings.py:352`）。URL の形を変えると、古い `/media/...` を含む応答が最長 1 時間残る

## 2. 受け入れ条件
イシューの受け入れ条件に番号を付けた（範囲を足さない）。AC2 の「404 か 403」は、他の組織を 404 にする（規約 §5）と決めて書いた。未ログインの 401 は認証の既定の応答で、イシューの「返らない」を具体にしたもの。
- [ ] AC1: 問題・解説の画像を登録・更新すると、中身が DB に入り、ディスクにファイルが作られない
- [ ] AC2: 画像は API から返り、ログインしていない利用者には 401、他の組織の利用者には 404 で返らない（テストで固定）
- [ ] AC3: 画面（問題のプレビュー・クイズの問題と解説・拡大表示）で画像が表示される
- [ ] AC4: 問題の一覧・クイズの問題の取得で、画像の中身を DB から読まない（クエリのテストで固定）
- [ ] AC5: 画像の応答に ETag と Cache-Control が付き、同じ画像の 2 回目（`If-None-Match`）は 304 になる
- [ ] AC6: DB まわりの最適化の検討の結論（置き方・保存方式・上限・控えの大きさ）と理由が計画書にある（この計画書の 10）
- [ ] AC7: 移行は `migrate` で動き、ファイルのある行は中身が DB に入って `checksum_sha256` と大きさが一致する。ファイルの無い行は行と問題との紐づけが消え、消した件数が出力される。やり直しても二重に入らない（どれもテストで固定）
- [ ] AC8: app-1 で移行を流した結果（移した件数・消した件数。2026-11-19 の見込みは移す 0 件・消す 4 件）が記録にある
- [ ] AC9: リポジトリの `backend/media/` の見本の画像と空の目印ファイルを、承認を得て消した記録がある
- [ ] AC10: 古い `question_image`・`explanation_image` の列と API の古い項目が無くなり、列を消すマイグレーションを承認を得て流した記録がある
- [ ] AC11: `organization` か `subject` が null の `MediaAsset` の行の扱いが決まり、テストで固定されている（扱い: 中身は移すが配信しない〔404〕。9 を参照）
- [ ] AC12: `/media/` から画像が配信されなくなり（`backend/core/urls.py`・`nginx/default.conf`）、`docker-compose.yml` から `backend_media` の定義が無くなる
- [ ] AC13: 画像の応答の Cache-Control が `private` で、Content-Type が保存した MIME・`X-Content-Type-Options: nosniff` が付く
- [ ] AC14: `scripts/db_backup.sh` で取った控えを別の DB に戻し、画像のある問題を画面で開いて画像が表示される。控えの大きさの増え方を記録する（確かめ方は M7・9）

## 3. 影響範囲
- Backend: `problems`（モデル・マイグレーション 3 本・サービス・ビュー・URL・シリアライザ・検査の関数・管理コマンド・テスト）・`core`（`storage_service.py` を消す・`urls.py`・`settings.py`）
- Frontend: 画像の受け取り（新しいフック・部品・API の関数）・画像を表示する 3 つの部品・型・`pickImageUrls`・`url.ts` の `getMediaUrl` を消す・`api.ts` にエラーの通知を出さない指定・`setupProxy.js`
- DB: 新しい表 `media_asset_contents`（`MediaAsset` と 1 対 1・中身の `bytea`）・その列の保存方式・データの移行（ファイル → DB、ファイルの無い行と紐づけの削除）・`problems_problem` の 2 列の削除
- Config/Infra: `nginx/default.conf` の `/media/`・`docker-compose.yml` の `backend_media`（nginx の `production` プロファイルだけ）・`.gitignore` の `!backend/media/`・`backend/media/` のファイルの削除
- 依存のファイル（`requirements*.txt`・`package*.json`）: 変えない（Dockerfile・ビルドへの波及なし）
- OpenAPI の契約（`backend/core/openapi.py` の `CONTRACT_PATHS`）: 問題・クイズ・画像の API は入っていないので、`backend/openapi.yaml`・`frontend/src/types/api/schema.d.ts` は作り直さない

## 4. 変更点一覧（具体）

### 修正アプローチ
画像の中身を、`MediaAsset` と 1 対 1 の別の表（`MediaAssetContent`）の `bytea` の列に入れる。保存は行の作成と同じトランザクションの中で行い、ファイルに書く所・消す所をすべて DB の操作に置き換える。配信は新しい API（`GET /api/media/<asset_id>/`）にし、ログインと「利用者の組織の、消されていない画像か」を確かめてから中身を返す。画面は `<img src>` に API の URL を直接渡せない（Bearer の見出しを付けられない）ので、axios で中身を取り（`responseType: 'blob'`）、`URL.createObjectURL` で表示する小さな部品にまとめる。今あるファイルはデータのマイグレーションで DB に移し、ファイルの無い行は消す。古い画像の列は値が無いことを確かめて外す。`/media/` の配信・ファイルの置き場の設定・見本のファイルを外す。

### 4-1. 中身の表（モデル・マイグレーション 0024）
**修正方針**: 中身を別の表に分けて、問題・画像の一覧（`select_related('asset')`）が中身を読まない形を作りで保証する。
- `backend/problems/models.py`: 新しいモデル
  ```python
  class MediaAssetContent(models.Model):
      """画像の中身（MediaAsset と 1 対 1・I587）。一覧で中身を読まないよう別の表に分ける"""
      # 画像の行が消えたら中身も要らない（CASCADE）。主キーを共有して 1 対 1 を DB で保証する
      asset = models.OneToOneField(
          MediaAsset, on_delete=models.CASCADE, primary_key=True, related_name='content')
      data = models.BinaryField()  # bytea・NOT NULL

      class Meta:
          db_table = 'media_asset_contents'
  ```
- `MediaAsset.storage_key` の `help_text` を「識別用のキー（I587 からファイルの置き場ではない）」に直す。列・一意の制約（`organization`・`storage_key`）は変えない（新しい画像も今と同じ形のキーを作る。列を外すのは別の破壊的変更になり、得るものが無い）
- `MediaAsset.get_url()` を `reverse('media-asset-content', kwargs={'asset_id': self.id})`（`/api/media/<id>/`）に変える
- `backend/problems/migrations/0024_mediaassetcontent.py`: `CreateModel(MediaAssetContent)` と `RunSQL("ALTER TABLE media_asset_contents ALTER COLUMN data SET STORAGE EXTERNAL", reverse_sql="ALTER TABLE media_asset_contents ALTER COLUMN data SET STORAGE EXTENDED")`

### 4-2. 保存（作成・更新）
**修正方針**: 検査で判定した MIME を保存し、中身を同じトランザクションで DB に入れる。ファイル・フォルダに触らない。
- `backend/problems/utils.py`:
  - 新しい関数 `detect_image_mime(file) -> Optional[str]`（先頭 2048 バイトを `magic.from_buffer` で判定し、`ALLOWED_IMAGE_FORMATS` に入る MIME だけを返す。読んだ後に `seek(0)`）。`validate_image_file` の 3 はこの関数を使う（判定の書き方を 1 か所にする）
  - `check_directory_exists` を消す（使う所が無くなる）
- `backend/problems/services/problem_service.py` の `_save_image_as_asset`:
  - 4（フォルダの確かめ）と 5 のファイルの書き込み（`os.makedirs`・`open`）を消す
  - `mime_type=detect_image_mime(image_file)`（送り手の `content_type` を使わない）
  - `data = image_file.read()`（`seek(0)` の後）で中身を読み、`MediaAsset` を作った後に `MediaAssetContent.objects.create(asset=asset, data=data)`。`file_size_bytes=len(data)`・`checksum_sha256=hashlib.sha256(data).hexdigest()`（読んだ中身から出す）
  - `import os`・`settings` の import を外す（使う所が無くなる）
- 作成（`create_problem_with_images`）・更新（`update_problem_with_images`）はどちらも `@transaction.atomic` で、中身の作成もその中に入る（失敗すると行も中身も残らない）

### 4-3. 消す（論理削除）
**修正方針**: 「画像を論理削除するときは中身を消す」を 1 か所にまとめ、ファイルの削除を置き換える。
- `ProblemService` に `_discard_asset(asset: MediaAsset) -> None` を足す: `asset.is_deleted = True`・`save(update_fields=['is_deleted'])`・`MediaAssetContent.objects.filter(asset=asset).delete()`。ファイルの削除と違って同じトランザクションの中で取り消せるので、「物理削除は最後」の順の注意（`_reconcile_images` の docstring）を外す
- `_reconcile_images` の 6・`delete_problem` の 3〜4 を `_discard_asset` に置き換える（`StorageService` の import と `try/except` のログを外す）
- `backend/core/storage_service.py` を消す（使う所が無くなる。`imghdr` は Python 3.13 で外されたので、#554 の前に無くなるのは都合がよい）

### 4-4. 画面から使われていない 2 つの action
**修正方針**: ファイルに書く経路を残さない。共通の保存の流れ（4-2）を使い、規約 §6・§7 のエラーの形にそろえる。
- `ProblemViewSet.upload_image`（`views.py:612-737`）: `StorageService` を使わず `ProblemService._save_image_as_asset(image_file=file_data, usage_kind=usage_kind, organization=problem.subject.organization, subject=problem.subject)` を呼び、紐づけを作る（`transaction.atomic`）。`except Exception` で `str(e)` を返す 500 を消し、検査の誤りは DRF の `ValidationError`（400・`custom_exception_handler` の形）にする。受け付ける形式は共通の検査（PNG・JPEG・WebP・5MB）になり、今の GIF・10MB は受け付けなくなる（画面から使われていない経路で、作成・更新と同じ決まりにそろえる）
- `ProblemViewSet.delete_image`（`views.py:739-805`）: `StorageService.delete_file` と `media_asset.is_deleted = True` を `ProblemService._discard_asset(media_asset)` に置き換え、`except Exception` の 500 を消す
- 2 つの `problem.organization_id != request.user.organization_id` の 403 は変えない（`get_object()` の絞り込みが先に 404 を返すので届かないが、範囲の外）

### 4-5. 配信の API
**修正方針**: 利用者の組織の、消されていない画像だけを返す。中身を読む前にメタデータで 304 を判定し、ブラウザのキャッシュは本人の分だけにする。
- URL: `GET /api/media/<uuid:asset_id>/`（`backend/problems/urls.py` に `path('media/<uuid:asset_id>/', MediaAssetContentView.as_view(), name='media-asset-content')`）
- `backend/problems/views.py` に `MediaAssetContentView(APIView)`:
  - `permission_classes = [permissions.IsAuthenticated]`（認証は既定の `JWTAuthentication`。組織の管理者に限らない: クイズを解く一般の利用者も画像を見る）
  - 取り出し（`backend/problems/selectors.py` を新しく作り `visible_media_asset(*, user, asset_id) -> MediaAsset | None`）: `user.organization_id` が無ければ `None`。`MediaAsset.objects.filter(id=asset_id, is_deleted=False, organization_id=user.organization_id, subject__organization_id=user.organization_id).only('id', 'mime_type', 'checksum_sha256').first()`（組織は `request.user` から決める・規約 §5。`organization` か `subject` が null の行は条件に当たらず返らない）
  - 無ければ `NotFound()`（404。他の組織の画像があることを知らせない。本文は `custom_exception_handler` の形）
  - `checksum_sha256` が空なら ETag を付けず、304 の判定もしない（違う画像が同じ ETag にならないように・セキュリティレビューの必須防御条件）。値があれば `etag = f'"{asset.checksum_sha256}"'`。`request.headers.get('If-None-Match')` を `,` で分けて空白を除いた値のどれかが `etag` か `*` なら、中身を読まずに `HttpResponseNotModified()`（304・本文なし）に ETag・Cache-Control を付けて返す
  - 中身: `MediaAssetContent.objects.filter(asset_id=asset.id).values_list('data', flat=True).first()`。無ければ `NotFound()`
  - 応答: `HttpResponse(bytes(data), content_type=mime)`。`mime` は `asset.mime_type` が `ALLOWED_IMAGE_FORMATS` に入るときだけそれを使い、それ以外は `application/octet-stream`。見出し: `ETag`・`Cache-Control: private, max-age=3600`・`X-Content-Type-Options: nosniff`・`Content-Security-Policy: default-src 'none'; sandbox`・`Content-Disposition: inline`
  - 回数の制限は既定のまま（`AppUserRateThrottle`・300/分）
- `backend/problems/serializers.py`: `MediaAssetSerializer.url` は `get_url()` のまま（新しい URL になる）

### 4-6. 画面
**修正方針**: API の URL から中身を取って表示する部品を 1 つ作り、画像を出す 3 か所で使う。表示の 4 つの状態（規約 §7・UX §1・§2）を出し分ける。
- `frontend/src/services/api.ts`: axios の型を広げて `skipErrorToast?: boolean` を設定に足し（`declare module 'axios' { interface AxiosRequestConfig { skipErrorToast?: boolean } }`）、`handleApiError` の最初で `error.config?.skipErrorToast` なら通知を出さずに戻る（401 のトークンの更新は今のまま効く）
- 新しい `frontend/src/services/mediaService.ts`: `getMediaBlob(url: string): Promise<Blob>`（`apiClient.get<Blob>(url, { responseType: 'blob', skipErrorToast: true })` の `data`）
- 新しい `frontend/src/hooks/useMediaImage.ts`: `useQuery({ queryKey: ['media', url], queryFn: () => getMediaBlob(url), enabled: !!url, staleTime: Infinity })`（同じ画像の中身は変わらない: 画像を替えると新しい ID になる）。取れた `Blob` から `URL.createObjectURL` で表示用の URL を作り、`useEffect` の後片付けで `URL.revokeObjectURL` する。戻り値は `{ state: LoadState（toLoadState）, objectUrl: string | null, retry: () => void }`
- 新しい `frontend/src/components/MediaImage.tsx`（関数の部品・`React.FC` を使わない）: props は `src`（API の URL）・`alt`・`sx`・`onClick`・`onKeyDown`・`role`・`tabIndex`・`aria-label`・`loading`
  - 読み込み中: MUI の `Skeleton`（`variant="rectangular"`・高さは `sx` の高さか 150px）
  - 失敗: 枠の中に「画像を読み込めませんでした」と「再読み込み」のボタン（`retry` を呼ぶ。UX §1「同じ画面に『読み込めませんでした』と再読み込みのボタンを出す」をそのまま当てはめる）
  - 取れた: `Box component="img"` に `objectUrl` を渡し、受け取った props を付ける
- `frontend/src/components/ProblemImageList.tsx`: `getMediaUrl` をやめ、`MediaImage` に API の URL を渡す。`onImageClick` には API の URL を渡す。`key` は URL にする（同じ問題の中で同じ画像は 2 度出ない）
- `frontend/src/components/ImageModal.tsx`: `imageUrl`（API の URL）を `MediaImage` で表示する（同じクエリのキーなのでキャッシュから出る）
- `frontend/src/components/ImageUploadArea.tsx`: 保存済み（`kind: 'existing'`）の画像は `MediaImage` で表示し、新しく選んだ画像は今のまま `URL.createObjectURL(file)` の `img`
- `frontend/src/utils/url.ts` を消す（`getMediaUrl` は `ProblemImageList` だけが使っていた。axios が `baseURL` を付ける）
- `frontend/src/setupProxy.js`: 中継の対象から `'/media'` を外す（`['/api']` にする）

### 4-7. 古い画像の列（マイグレーション 0026）
**修正方針**: 値が無いことを確かめてから列を外す。値がある環境では黙って消さずに止める。
- `backend/problems/models.py`: `Problem.question_image`・`explanation_image`・`get_question_image_url`・`get_explanation_image_url` を消す。`Subject.get_question_image_directory`・`get_explanation_image_directory`・`get_image_base_directory`（古い URL を作るためだけのもの）も、ほかに使う所が無ければ消す（`grep` で確かめてから。`image_directory` の列は範囲の外で残す）
- `backend/problems/serializers.py`: `ProblemSerializer`・`ProblemDisplaySerializer` の `question_image`・`explanation_image`（と `get_*` のメソッド）、`AnswerExplanationSerializer` の `explanation_image` を消す
- `backend/problems/migrations/0026_remove_problem_legacy_images.py`: 1 つ目の操作 `RunPython(refuse_if_legacy_images_exist, reverse_code=RunPython.noop)`（どちらかの列に空でない値がある問題が 1 件でもあれば、件数を書いた `RuntimeError` で止める）、続けて `RemoveField('problem', 'question_image')`・`RemoveField('problem', 'explanation_image')`
- 画面: `frontend/src/utils/problemImages.ts` の `pickImageUrls(assets)` は引数を 1 つにし、`assets` の `url` を並べるだけにする。`ProblemPreview.tsx`・`QuizSession.tsx` の呼び出しを合わせる。`frontend/src/types/quiz.ts`・`frontend/src/services/types.ts` の `question_image`・`explanation_image` を消す

### 4-8. 今あるファイルの移行（マイグレーション 0025・管理コマンド）
**修正方針**: 移行の中身を 1 つの関数にし、マイグレーション（実際に移す）と管理コマンド（試し・読むだけ）の両方から呼ぶ。食い違い（中身の不一致・画像でない・置き場の外を指すキー）は黙って直さずに止める。
- 新しい `backend/problems/media_migration.py`:
  - `LEGACY_MEDIA_ROOT = Path(settings.BASE_DIR) / 'media'`（設定から `MEDIA_ROOT` を外すので、移行が読む場所はここに置く）
  - `move_media_files_to_db(*, asset_model, link_model, content_model, media_root: Path, dry_run: bool) -> MediaMigrationResult`（モデルは引数で受ける: マイグレーションの中では過去のモデル、コマンドでは今のモデル）
  - 対象: `is_deleted=False` の `MediaAsset`（論理削除の行は今もファイルが消されていて配信もしないので触らない）
  - 1 行ごと: すでに中身があれば `already`（やり直しで二重に入らない）。`(media_root / storage_key).resolve()` が `media_root.resolve()` の下でなければ止める。ファイルが無ければ「消す」に入れる。あれば読み、`sha256` と大きさが `checksum_sha256`・`file_size_bytes`（値があるときだけ）と違えば止める。値が null なら読んだ中身から埋める（ETag に使うため・セキュリティレビューの必須防御条件）。`detect_image_mime` 相当の判定（`magic.from_buffer`）が `ALLOWED_IMAGE_FORMATS` に入らなければ止める。合えば中身を作り、`mime_type` を判定した値に直す
  - 「消す」の行: `link_model.objects.filter(asset_id__in=ids).delete()`（紐づけは `RESTRICT` なので先に消す）→ `asset_model.objects.filter(id__in=ids).delete()`
  - `dry_run=True` は何も書かず、行ごとの判定（移す・済み・消す）と件数だけを返す
  - 結果: `MediaMigrationResult(moved, already, deleted_assets, deleted_links, deleted_keys)`。止めるときは `MediaMigrationError`（キーと理由を入れる。中身は入れない）
- `backend/problems/migrations/0025_move_media_files_to_db.py`: `RunPython(forward, reverse_code=backward)`
  - `forward`: 上の関数を `dry_run=False` で呼び、`sys.stdout.write` で `I587 media: moved=… already=… deleted_assets=… deleted_links=…` を 1 行出す（`migrate` の出力に残す。規約の `print` を使わない）。最後に `cache_service.invalidate_problems_cache()` を呼び、古い URL を含む一覧のキャッシュを捨てる。`cache_service` の import は関数の中に置き、どの例外でも `logger.warning` に残して続ける（`migrate` を止めない。捨てられなくてもキャッシュは最長 1 時間で切れる）
  - `backward`: 中身のある画像を `LEGACY_MEDIA_ROOT / storage_key` に書き戻す（戻し方。消した行は戻らない: 戻すのは控え〔7〕）
- 新しい管理コマンド `backend/problems/management/commands/check_media_migration.py`: 読むだけ。上の関数を `dry_run=True` で呼び、行ごとの判定と件数を出す（承認を求めるときに見せる試し）。古い画像の列に値のある問題は 0026 が数えて止める（/simplify で外した・計画変更記録）

### 4-9. 置き場の設定と見本のファイルの片付け
- `backend/core/urls.py`: `static(settings.MEDIA_URL, ...)` と `static`・`settings` の import を消す
- `backend/core/settings.py`: `MEDIA_URL`・`MEDIA_ROOT` を消す
- `backend/problems/views.py` の `SubjectViewSet.perform_create`: 科目のフォルダと `.gitkeep` を作る部分と `os`・`settings` の import を消す
- `nginx/default.conf`: `location /media/ { ... }` を消す
- `docker-compose.yml`: nginx の `- backend_media:/var/www/media` と `volumes:` の `backend_media:` を消す
- `.gitignore`: `!backend/media/` を消す（`media/` の無視は残す: 移行の前の環境のファイルを誤ってコミットしない）
- `backend/media/`: `git rm -r backend/media`（PNG 6 枚・`.gitkeep` 12 個。Danger Ops・承認の後）
- テスト: `settings.MEDIA_ROOT = str(tmp_path)` だけの行（`test_I006_subject_org_admin.py`・`test_I078_is_correct_exposure.py`・`test_I102_problem_authz.py`・`test_I103_cross_org_create.py`・`test_I104_subject_authz.py`・`accounts/tests/test_I539_personal_org_signup.py`）を消す。`test_I006` の TC-AUTO-009（フォルダが作られる）・TC-AUTO-010（フォルダ作りの失敗で巻き戻る）は振る舞いが無くなるので消し、代わりに TC-08（科目を作ってもフォルダが作られない）を足す。`test_I073_image_update.py` はファイルの有無を中身の有無の確かめに、`test_I472_quiz_answer_explanation_image.py` は `/media/` の URL を `/api/media/<id>/` に直す

## 5. 実装手順（ステップ）
1. **Danger Ops の準備と承認**（コードを変える前。ステップ 2 以降の前提・ゲート）
   - 開発の DB の今の件数（`MediaAsset` の全体・ファイルの無い行・null の行・古い列に値のある問題）と、`backend/media` のファイルの一覧を読むだけで数え、レビュー文書の「## 自律判断の記録」に書く → 手動 M1
   - `bash scripts/db_backup.sh` で開発の DB の控えを取る（`backup_*.sql` は `.gitignore` 済み）。大きさを記録する → 手動 M2
   - **ここで止めてユーザーに承認を求める**（止める条件 2）。見せるもの: 消す行（4 件・キー）・消すファイル（PNG 6 枚と `.gitkeep` 12 個）・古い列の削除（値のある問題 0 件）・控えの場所・戻し方（7）。承認の言葉と日付をレビュー文書に書く。承認が無ければ先へ進まない（マイグレーションのファイルを書くとコンテナの起こし直しで流れるため・1 の詳細 7）
2. **中身の保存と配信の縦の 1 本**（ステップ 1 の承認の後）: 4-1・4-2・4-5・4-6
   - TC を先に書く（TC-01・TC-02・TC-04・TC-05・TC-06・TC-07・TC-11・TC-16〜TC-18）。今のコードで落ちることを確かめてから実装する
   - `makemigrations problems --name mediaassetcontent` で `0024` を作り、`RunSQL` を足す → TC-03
3. **消す経路と使われていない action**（ステップ 2 の後）: 4-3・4-4・4-9 の科目のフォルダ → TC-08・TC-09・TC-10
4. **今あるファイルの移行**（ステップ 3 の後）: 4-8 → TC-12〜TC-14。`check_media_migration` を app-1 で流し、ステップ 1 の数と合うことを確かめる → 手動 M3
5. **古い画像の列**（ステップ 4 の後）: 4-7 → TC-15・TC-19
6. **置き場の設定と見本のファイルの片付け**（ステップ 5 の後）: 4-9 の残り（`git rm -r backend/media` を含む）→ TC-20〜TC-22（決定論ゲート）・TC-23
7. **app-1 で移行を流す**（ステップ 6 の後）: `DANGER_OK=1 docker compose exec -T backend python manage.py migrate problems`（ユーザーが承認画面で許可する）。出力の `I587 media:` の行を記録する → 手動 M4
8. **画面で確かめる**（ステップ 7 の後）: Playwright MCP で、画像付きの問題を作ってプレビュー・クイズ・拡大・編集で表示し、通信と見出しを確かめる → 手動 M5・M6。控えを別の DB に戻して確かめる → 手動 M7
- サービスの再起動: ステップ 7 の後、`docker compose restart backend`（設定の `MEDIA_*` を外したので読み直す。起動の `migrate` は流し済みで何もしない）。画面は開発サーバーが読み直す（`setupProxy.js` を変えたので `docker compose restart frontend` も要る）
- 垂直スライス: ステップ 2 で DB → API → 画面を 1 本通す。未知のリスク（画面の blob の受け取りと Jest での `URL.createObjectURL`）もステップ 2 に置く

## 6. テスト計画
### 自動（詳細は `docs/tests/open/I587_auto_test.md`）
- テストの段の選び方: 保存・配信・認可・クエリ・移行は pytest の結合テスト（DB と API のクライアント）。マイグレーションは `MigrationLoader` で本物を読む結合テスト。画面の部品とフックは Jest＋Testing Library（API は今の axios-mock-adapter で差し替え・規約 §16 の #511 まで）。置き場の不在は決定論ゲートの `grep`。E2E は足さない（画像の流れは E2E の既存のシナリオに無く、画面の確かめは M5・M6 で行い、表示の部品は Jest で固定する）
- 認可・組織の境界: 未ログイン 401・他の組織 404・論理削除 404・null の行 404・同じ組織の一般の利用者 200（TC-05・TC-06・TC-07）
- 再発防止: 送り手の `content_type` を保存しない（TC-02）。ファイル・フォルダを作らない（TC-01・TC-08）
### 手動（詳細は `docs/tests/open/I587_manual_test.md`）
- M1〜M7 はすべて Claude（Playwright MCP・コマンド）。人の手動テストは無い

## 7. ロールバック
- **マージ前**: PR を閉じる。開発の DB に流した 0024〜0026 は、ステップ 1 の控え（`backup_*.sql`）から戻す（下の 3）
- **マージ後**: 次の順（どれも Danger Ops。ユーザーの承認の後に `DANGER_OK=1` を付けて行う）
  1. I587 のコードのまま `docker compose exec -T backend python manage.py migrate problems 0023`（0026 の戻しで 2 列が空で戻る・0025 の戻しで中身のある画像がファイルに書き戻される・0024 の戻しで中身の表が消える）
  2. I587 の PR を戻す（revert の PR。`backend/media/` の見本のファイルも git から戻る）
  3. 消した 4 行と紐づけを戻すときは、控え（`backup_*.sql`）を別の DB に戻し、`media_assets`・`problem_media_assets` の該当の行を写す（4 行ともファイルは元から無いので、画像は戻らない）

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: マイグレーションのファイルを書いた後に backend のコンテナが起こし直され（review-gate の `adversarial-review.sh` など）、承認の前に 0025・0026 が開発の DB に流れる | ステップ 1 で控えを取り、承認を得てからマイグレーションを書く（承認の後なら流れても承認済みの操作）。仕組みの直しは #579 | 回避 |
| R2: 送り手が決めた `content_type`（`text/html` など）で画像を返し、API の出どころで HTML・スクリプトとして解釈される | 判定した MIME を保存し（4-2）、配信は許可した 3 つの MIME 以外を `application/octet-stream` にする。`nosniff`・`Content-Security-Policy: default-src 'none'; sandbox` を付ける（TC-02・TC-05） | 回避 |
| R3: 一覧・クイズの取得が画像の中身まで読み、遅くなる・メモリを使う | 中身を別の表にし（10）、取得のクエリに中身の表が出ないことをテストで固定する（TC-11） | 回避 |
| R4: 共有のキャッシュ（中継の機器）が画像を持ち、他の利用者に返す | `Cache-Control: private`（TC-05）。ETag は中身の SHA-256 で、組織を表す値を含まない | 回避 |
| R11: 本人のブラウザのキャッシュ（`max-age=3600`）に、ログアウト・権限の変更・画像の論理削除の後も最長 1 時間、画像が残る（共有の端末では次の人が同じブラウザで見られる） | 画像は問題・解説の図で、本番は無い。期限を 1 時間に抑える | 受け入れ |
| R5: 解説の画像の ID を、答える前に知っていれば取れる | 画像の ID（UUID）は答えた後の応答にだけ入る（I476 の決まり・`AnswerExplanationSerializer`）。推測できない。組織の境界は掛ける | 受け入れ |
| R6: ほかのワークツリーで develop を取り込むと、git が `backend/media/` の見本のファイルを先に消し、それを指す行があれば「ファイルの無い行」として消える | 開発のデータで、ユーザーが受け入れた（2026-11-19・fix-loop で確かめた。回答「このまま消す (Recommended)」。調べた事実: 見本の 70 バイトの PNG 4 枚は I007 で入ったテストの残りと見られ、持ち主の組織は app-1 に無い。`q02_problem.png` は問題の取り込みで使われない。ほかのワークツリーの DB は未確認）。0025 は消した行の ID とキーを `migrate` の出力に並べる（TC-12）。各ワークツリーで登録した画像のファイルは git に入っていないので消えない | 受け入れ |
| R7: ほかの環境で中身の不一致・画像でないファイル・置き場の外を指すキー、古い列に値のある問題があると、`migrate` が止まり backend が起動しない | 黙って消さないための止め方（C7）。止まったときの理由とキー・件数をエラーの文に出す。本番は無い | 受け入れ |
| R8: 画面で画像の取得に失敗したとき、axios の共通の通知（トースト）と画像の枠のエラーが二重に出る | `skipErrorToast` で画像の取得だけ通知を止め、枠の中に出す（4-6・TC-17） | 回避 |
| R9: 控え（`pg_dump` の平文）で `bytea` が 16 進の文字になり、控えが画像の約 2 倍の大きさになる | 今の画像は合計 250KB 程度。増え方を M7 で記録する。大きくなったら控えの形（`-Fc`）を別に決める | 受け入れ |
| R10: 移行の後も最長 1 時間、Redis の一覧のキャッシュに古い `/media/` の URL が残る | 0025 の最後に一覧のキャッシュを捨てる（4-8） | 回避 |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 画像の中身を PostgreSQL に保存し、ログイン・組織の境界を確かめる API から返す。`/media/` の配信をやめる
- 見本の画像と空の目印ファイル（`backend/media/`）は移さずに消す（承認を得てから）
- ファイルの無い画像の行は、行と紐づけを消して件数を記録する（ほかの環境でも同じ）
- 古い画像の列と API の古い項目を外し、画面の後戻り（`pickImageUrls` の 2 つ目の引数）も外す（列の削除は承認を得てから）
- 移行は `migrate` で動く形にし、確かめるのは app-1 だけ。ほかのワークツリーの DB は起動しない・触らない
- 外部のオブジェクトストレージ・過去問の画像の登録・画像以外のファイルは範囲の外

Claude が決めた（技術的な選択と理由）:
- 置き方は別の表（`MediaAssetContent`・1 対 1・主キーの共有）— `get_media_assets` の `select_related('asset')` など、画像の行を読む所が中身を読まない形を作りで保証できる（列を足して `defer` にすると、付け忘れた所で黙って読む）
- 型は `bytea`（`BinaryField`）。Large Object にしない — 行と一緒にトランザクション・`CASCADE`・`pg_dump` に入る。Large Object は消し忘れ（`lo_unlink`）の手当てが要る。今の上限 5MB は `bytea` の上限（1GB）に十分収まる
- 保存方式は `SET STORAGE EXTERNAL`（TOAST の圧縮をしない）— PNG・JPEG・WebP はもう圧縮されていて、圧縮を試す CPU が無駄になる
- 大きさの上限は今のまま（5MB・4096px・`backend/problems/utils.py`）。縮小・再圧縮はしない — 画面の見え方が変わる（イシュー: 変わる判断はユーザーに確認）。今の画像は最大 62KB で、上限を変える理由が無い
- 配信の URL は `GET /api/media/<asset_id>/`（問題の下に置かない）— 同じ画像を複数の問題が共有できる作り（`ProblemMediaAsset`）なので、画像の ID で引く
- 境界は `organization_id` と `subject__organization_id` の両方が利用者の組織であること。null の行は返さない（AC11）。中身は移す（移さないと、後で持ち主を埋めたときに画像が無い）— 持ち主の分からない画像を誰にも見せない（fail-closed）。app-1 では 0 件
- 権限は `IsAuthenticated` だけ（管理者に限らない）— クイズを解く一般の利用者も画像を見る。問題の取得（`available_problems`）と同じく組織の単位で見せる
- 304 の判定は中身を読む前にメタデータだけで行う — 2 回目の表示で中身を DB から読まない（AC5 の目的）。`max-age=3600` — 中身は ID ごとに変わらないが、権限が変わったときに長く残さない
- 画面は axios で `blob` を取り、`URL.createObjectURL` で表示する。短い期限の署名付きの URL にしない — 署名付きの URL は取得のときにログインを確かめない（AC2 の「ログインしていない利用者には返らない」に合わない）・URL がログや Referer に残る
- 画像の取得の失敗は、共通の通知を出さず画像の枠に出す（`skipErrorToast`）— 1 ページに画像が複数あると通知が重なる。枠の文言と再読み込みのボタンは UX §1 の決まり（「読み込めませんでした」と再読み込みのボタン）をそのまま当てはめたもので、新しい価値判断ではない
- 移行は `RunPython` のデータのマイグレーション（0025）にし、試しは別の管理コマンド（読むだけ）にする — ほかの環境は `migrate` で自動で移る（設計確認メモ）。承認の前に見せる試しは書き込みの無いコマンドで出す
- 移行の食い違い（中身の不一致・画像でない・置き場の外のキー）と古い列の値は、黙って直さずに止める — C7。止まっても開発の DB だけで、理由がエラーの文に出る
- 論理削除の行（`is_deleted=True`）は移行で触らない — 今もファイルが消されていて、配信もしない
- 古い列のマイグレーション（0026）は、移行（0025）と分ける — 規約 §4（データの書き換えとスキーマの変更を分ける）
- `upload_image`・`delete_image` は消さずに共通の保存・削除にそろえる — 画面から使われていないが、消すと API の範囲が変わる。ファイルに書く経路を残さないことが目的。受け付ける形式が GIF・10MB から PNG・JPEG・WebP・5MB に変わるが、呼ぶ所が無い: `frontend/src`・`e2e` に `images/upload` が無い（2026-11-19 の `grep`）・本番が無く外の利用者がいない（2026-11-17 時点）
- `storage_key` の列は残す — 外すと別の破壊的な変更になり、一意の制約の作り直しが要る。識別用のキーとして今の形で作り続ける
- 応答の `Content-Disposition: inline`・`Content-Security-Policy: default-src 'none'; sandbox` — 画像を別のタブで開いたときもスクリプトを動かさない（多層の守り）
- AC14 の「別の DB」は、捨てる DB のコンテナ（`docker run --rm`・app-1 のネットワーク）にする。backend を止め、`docker compose run -d --rm --use-aliases --service-ports -e DB_HOST=i587-restore backend` で戻した DB に向けた backend を `backend` の名前で起こし、画面（`BACKEND_URL=http://backend:8000` の中継）で画像のある問題を開く。確かめた後にその backend とコンテナを止め、`docker compose start backend` で元に戻す（M7）— 開発の DB を戻し先にすると、片付け（`DROP DATABASE`）が危険操作になり、開発の DB の中身も変わる。捨てるコンテナなら消すのは止めるだけ
- テストで `settings.MEDIA_ROOT` を差し替えるだけの行を消す — 設定が無くなり、残すと「科目の作成が画像の置き場所を作る」という誤った説明が残る
- 一覧 `docs/reviews/backlog/I223.md` B1〜B4・`docs/reviews/backlog/I224.md` F9（`FILE=-`）: 残す — どれもハーネスの事柄で、本イシューの変更点と関係が無い。実装対象のファイルに当たる行は無い

セキュリティ・BP の確認:
- 入力の検証: 画像は今の `validate_image_file`（大きさ・拡張子・中身の MIME・寸法・ファイル名）を、作成・更新・`upload_image` の全部で使う（4-4 で `upload_image` も共通の検査に入る）。URL の `asset_id` は `uuid` の変換器で受ける（形の違う値は 404）
- 認証・認可: 新しい API は `IsAuthenticated`・組織の絞り込み（`request.user` から）。他の組織・論理削除・null の行は 404（最小の権限）。`get_permissions()` の上書きは無い
- 機密データ: ログに中身・ファイル名を出さない。移行のエラーの文に入れるのは画像の ID とキーだけ
- OWASP: XSS（Content-Type の固定・`nosniff`・CSP の `sandbox`）・IDOR（組織の境界・UUID）・パストラバーサル（移行で `storage_key` が置き場の外を指せば止める）・CSRF（JWT の見出しで、Cookie を使わない GET）。生 SQL は保存方式の `RunSQL` 1 行だけ（値を埋め込まない）
- フレームワークの推奨: ビューは薄く、取り出しは `selectors.py`・書き込みは `services/`。エラーは `custom_exception_handler` の形（`except Exception` で `str(e)` を返す 2 か所を消す）。画面は `dangerouslySetInnerHTML` を使わない・トークンは今の通信の土台のまま
- 依存ライブラリ: 足さない・上げない（pip-audit・npm audit の対象の変化なし）
- 静的検査の基準: bandit は MEDIUM 以上を直す（LOW は `# nosec` で抑える）。npm audit は high/critical を直す

要件適合・業務ロジック:
- 受け入れ条件の外の仕様の追加は無い（`upload_image` の受け付ける形式がそろうのは、画面から使われていない経路の内部のそろえ）
- マルチテナント: 画像の閲覧は利用者の組織の分だけ（`organization_id` と `subject__organization_id`）。操作（登録・更新・削除）は今のまま組織の管理者だけ（`ProblemViewSet` の `IsOrgAdmin`）
- エッジケース: 中身の無い画像（論理削除の後・移行の前）は 404。`If-None-Match` が複数の値・`*`・弱い ETag の形（`W/"…"`）でも、強い一致だけを 304 にする（`W/` 付きは一致としない）。0 枚の問題は画像の枠を出さない（今のまま）

Danger Ops（有無/手順/ロールバック）:
- 有: (1) `git rm -r backend/media`（PNG 6 枚・`.gitkeep` 12 個）(2) 0026（`problems_problem` の 2 列の削除）(3) 0025 でのファイルの無い `MediaAsset` の行と紐づけの削除（app-1 では 4 件）
- 影響範囲: 開発の DB（app-1 の `app-1-db-1`）とリポジトリのファイル。本番は無い。ほかのワークツリーは develop を取り込んで `migrate` したときに同じ決まりで流れる（設計確認メモ）
- 代替案: ファイルの無い行を残す（画面に壊れた画像の枠が出続ける）・古い列を残す（画像の出どころが 2 つ残る）は、grill-me でユーザーが選ばなかった
- 承認: ステップ 1 で、件数・消すもの・控え・戻し方を見せてユーザーに承認を求める（承認の言葉と日付をレビュー文書に残す）。マージ依頼のときに PR に `danger-approved` を付けてもらう
- 実行コマンド: `git rm -r backend/media`（ステップ 6）・`DANGER_OK=1 docker compose exec -T backend python manage.py migrate problems`（ステップ 7・見張りの承認画面が出るのでユーザーが許可する）
- ロールバック: 7

P3/P5/P8: P3（データ整合性）は 10、P5（運用）は 11。P8（コスト）は影響なし（新しい資源・外部サービスは無い。DB が画像の分だけ増える〔今は 250KB〕）
P6: 13 に書いた
P9: 15 に書いた（個人情報の新しい扱いは無い・テナントの境界は強くなる）

## 10. データ整合性設計
- 置き方の結論（AC6）: 別の表 `media_asset_contents`（`asset_id` が主キーで `media_assets.id` への外部キー・`ON DELETE CASCADE`・`data bytea NOT NULL`）。理由は 9
- 保存方式の結論（AC6）: `data` の列を `SET STORAGE EXTERNAL`（TOAST の外の表に置き、圧縮しない）。PostgreSQL は 2KB を超える値を自動で TOAST に出すので、本の表の行は小さいまま
- 上限の結論（AC6）: 1 枚 5MB・4096px・1 問の種類ごとに 5 枚（今のまま）。1 回の配信で読むのは 1 枚（最大 5MB）だけ
- 控えの大きさの結論（AC6）: 今の画像の合計 250KB では控え（平文の `pg_dump`）が 0.5MB 程度増えるだけ。増え方を M7 で測って記録する（R9）
- 接続ごとのメモリ・時間（AC6）: 1 回の配信で中身を 1 回だけ読み、応答に渡す（最大 5MB）。304 のときは中身を読まない。タイムアウトの設定は変えない（gunicorn・DB の既定のまま）
- トランザクション境界: 画像の行・紐づけ・中身の作成と削除はどれも `ProblemService` の `@transaction.atomic` の中（作成・更新・問題の削除）と、`upload_image`・`delete_image` の `transaction.atomic` の中
- 冪等性: 移行は「中身がすでにある行は飛ばす」（TC-13）。消す行は 2 回目には無い
- 同時更新: 画像の中身は作った後に書き換えない（替えるときは新しい画像の行）。`OneToOneField` の主キーで 1 つの画像に中身は 1 つ
- マイグレーションの安全性: 0024（表の追加）は後方互換。0025・0026 は Danger Ops（9）。0026 は値のある問題が 1 件でもあれば止まる。戻し方は 7（0025 の戻しはファイルに書き戻す。TC-12）

## 11. 運用設計
- ログ: 移行は `migrate` の出力に件数の 1 行を出す。止めるときはエラーの文に画像の ID・キー・理由を入れる（中身・元のファイル名は入れない）。キャッシュを捨てられなかったときは `logger.warning`
- タイムアウト・リトライ: 外部の API・非同期の処理は増えない。画面の取得は axios の既定の時間（`REACT_APP_API_TIMEOUT`）と 401 のときのトークンの更新を今のまま使う
- 段階リリース・切り戻し: 本番が無いので Feature Flag は使わない。切り戻しは 7

## 13. 性能・UX設計
- N+1・余計な読み込み: 一覧・クイズの取得は中身の表を読まない（TC-11）。画像の配信は 1 枚 1 回の取得で、2 回目は TanStack Query のキャッシュ（`staleTime: Infinity`）とブラウザの HTTP のキャッシュ（`private, max-age=3600`・ETag）から出る
- 読み込み中: 画像の枠に MUI の `Skeleton`（形だけ先に出す・UX §2）
- 失敗: 画像の枠に「画像を読み込めませんでした」と「再読み込み」のボタン（UX §1）。画面の他の部分はそのまま使える
- 空: 画像が 0 枚の問題は画像の場所を出さない（今のまま）
- 破壊的な操作: 画像の削除は今の編集のダイアログの操作のまま（変えない）
- アクセシビリティ: `img` の `alt`・クリックできる画像の `role="button"`・`tabIndex`・`aria-label`・Enter とスペースでの拡大は今のまま `MediaImage` に渡す。再読み込みのボタンは `button`

## 15. プライバシー・コンプライアンス設計
- 画像は組織が登録した問題・解説の図で、個人情報の新しい扱いは無い
- テナントの境界は強くなる（今はキーを知っていれば誰でも取れる → ログインと組織で絞る）。画面のキャッシュは本人のブラウザだけ（`private`）
- 消した画像の中身は論理削除のときに DB から消える（今のファイルの削除と同じ）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | TC-05〜TC-07 が、配信の API の境界（未ログイン 401・他の組織 404・論理削除 404・null の行 404・中身の無い行 404・同じ組織の一般の利用者 200）を、本物の API のクライアントで確かめているか。TC-07 の失敗の注入（組織の絞り込みを外すと他の組織で 200 になって落ちる）が書かれているか |
| V2 | 1 | 読んで可 | TC-02 が、送り手の `content_type`（`text/html`）で送った PNG の `mime_type` が `image/png` で保存され、配信の Content-Type が `image/png` になることを確かめているか。配信が許可の外の MIME を `application/octet-stream` にすることを TC-05 が確かめているか |
| V3 | 2 | 読んで可 | TC-11 が、一覧・クイズの取得の SQL に `media_asset_contents` が出ないことを確かめていて、`select_related('asset__content')` を足すと落ちる（失敗の注入）か |
| V4 | 3 | 読んで可 | TC-12〜TC-14 が、本物の 0025（`MigrationLoader`）と同じ関数を通り、ファイルのある行・無い行・済みの行・不一致・置き場の外のキーの 5 つの場合を見ているか。消す行の紐づけ（`RESTRICT`）を先に消しているか |
| V5 | 3 | 読んで可 | 画像をファイルに書く・`/media/` を返す・`MEDIA_ROOT` を読むコードが、テストとマイグレーションの外に残っていないか（TC-01・TC-08・TC-20〜TC-23）。`upload_image`・`delete_image` が共通の保存・削除を通るか（TC-09・TC-10） |
| V6 | 2 | 読んで可 | TC-04 の 304 が、中身を読む前に返っている（`django_assert_num_queries` で中身の表を読まない）ことを確かめているか。弱い ETag（`W/`）を一致にしないか |

## 計画変更記録
<!-- 形は docs/runbooks/plan-writing-rules.md「計画変更記録の形」 -->
- 計画レビュー（20261119_1527）の Warning への対応（方式・範囲・受け入れ条件は変えない・計画レビューのやり直し: 不要）: 2 の「そのまま」の言い方と AC14 の文をイシューのとおりに戻し、M7 を画面で確かめる形にした／`upload_image` の呼び出しが無い根拠を 9 に書いた／決定論ゲートを `/api/media/` に当たらない形（`-e "^/media" -e "[^i]/media"`）にした（失敗の注入を確かめ直した）／0025 のキャッシュの捨て方を関数の中の import と警告だけにした／本人のブラウザに残る画像を R11 で受け入れた／M7 に承認画面の予告を足した
- セキュリティ設計レビュー（2026-11-19）の必須防御条件への対応（方式・範囲・受け入れ条件は変えない・計画レビューのやり直し: 不要）: 0025 で null の `checksum_sha256`・`file_size_bytes` を埋める（4-8）／配信は `checksum_sha256` が空なら ETag を付けない（4-5）／TC-04 に null の行の場合を足した
- 実装（2026-11-19）での小さな直し（方式・範囲・受け入れ条件は変えない・計画レビューのやり直し: 不要）:
  - 中身の取り出しも `selectors.py` に置いた（`media_asset_data`）— 4-5 の「取り出しは selectors」にそろえる
  - TC-08 は `test_I006` でなく `test_I587_media_in_db.py` に置いた（`no_file_writes` の準備を共有するため）。`test_I006` の TC-AUTO-009・010 は計画どおり消した
  - `studylogs/tests/test_I452_quiz_review.py` の応答のキーの一覧から `explanation_image` を外した（4-7 で外した項目を前提にしていた既存のテスト）
  - `check_media_migration` は、中身の表がまだ無い（0024 の前）ときも動くようにした — 試しは流す前の環境で使うもの。開発の DB で `migrate problems 0024` を流そうとしたら見張りが巻き戻しの形として止めたので、先に 0024 だけを流す代わりにこちらにした
  - 決定論ゲートの形を語の区切りつき（`-e "^/media\b" -e "[^i]/media\b"`）にした — 前の形は `../services/mediaService` に当たる誤検知を出した
  - 画面のテスト（TC-16〜TC-18）は、axios-mock-adapter でなく `getMediaBlob` の差し替え（TC-16）と `MediaImage` の手動のモック（TC-18）で書いた。TC-17 は既存の `api.test.ts` に足した — ページのテストは今 `jest.mock('../../services/api')` で API を差し替えていて、画像の取得が順番の決まった差し替えを食い違わせるため
  - `utils.py` の `calculate_file_checksum` を消した（4-2 の後に呼ぶ所が無くなった）
  - ステップ 1 の控えは `scripts/db_backup.sh` と同じ `pg_dump` を DB のコンテナの中で流して取り出した（サンドボックスの中のスクリプトは `.env` を読めない）。ステップ 7 の `migrate` は前置きの `DANGER_OK=1` を付けずに流した（付けるとサンドボックスの中で動いて止まる。前進の `migrate` は見張りの判定の対象外〔danger-ops.md〕・承認はステップ 1 で得た）
- /simplify（2026-11-19・4 つの観点のレビュー役）での整理（方式・範囲・受け入れ条件は変えない・計画レビューのやり直し: 不要）:
  - 直した: 3 つの画面のファイルの改行の形を元の CRLF に戻した（差分が全体の書き換えに見えていた）／中身から MIME を判定する所を `utils.detect_mime(data)` の 1 か所にし、保存と移行の両方から使う（保存は読んだ中身から判定・ファイルを読み直さない）／`check_media_migration` の古い列の数えを外した（今のモデルから列が外れていて、いつも「列なし」と出る死んだコードだった。数えて止めるのは 0026）／`problem_service.py` の使われない `logger` を外した／0025 の書き戻しで、偽のモデルの実体を作らず値で場所を作り、中身を `.iterator()` で読む／画面のテストの差し替えを `MediaImage` から `useMediaImage`（`hooks/__mocks__/`）に下げ、本物の部品の属性の受け渡しもテストが通るようにした／blob の URL には効かない `loading="lazy"` を外した／画像の中身のキャッシュの持ち時間（`gcTime`）を 60 秒にした
  - 見送った: `If-None-Match` を Django の `get_conditional_response` で読む（Django は弱い比較で `W/` も一致にする。計画 9・セキュリティレビューで「強い一致だけ」と決めて TC-04 で固定しているので変えない）／`upload_image`・`delete_image` の処理をサービスの公開の関数にまとめる（4-4 で今の作りのまま共通の保存・削除に寄せると決めた。紐づけの共有の判定の条件の違いは今からあるもの）／`MediaMigrationResult` の件数を判定の一覧から数える形にする（読みやすさの差が小さい）／`Subject.image_directory` の列を外す（読む所が無くなったが、外すと別のマイグレーションが要る。retro で一覧に回す）／テストの PNG・画像の行を作る補助を共通にする（範囲の外の既存のテストにまたがる）／失敗の枠を `SubjectsRetryRow` と共通にする（置き方が違う）／`isExisting` を `kind` から出す・`mediaImageKey` の export（軽い）
- fix-loop（2026-11-19・コードレビュー 20261119_1825 の止める指摘 F1・F2）（方式・範囲・受け入れ条件は変えない・計画レビューのやり直し: 不要）: F1 `delete_image` の共有の判定を有効な紐づけだけにした（`_reconcile_images`・`delete_problem` とそろえる）／F2 見本のファイルを同じ PR で消すと、ほかの環境では消えた後に 0025 が流れる件は、ユーザーが「このまま消す」を選んだ（R6）。0025 が消した行の ID とキーを出力に並べるようにした

## レビュー結果
- [20261119_1527 判定: ✅ 完了](../../reviews/I587_plan_review_20261119_1527.md)

## セキュリティレビュー結果

**実施日**: 2026-11-19

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Medium | OWASP（セキュリティ設定ミス） | `checksum_sha256` が null の古い行があると、ETag が `"None"` になり、違う画像どうしが同じ ETag で 304 になりうる | 必須: 0025 で中身を移すとき、`checksum_sha256`・`file_size_bytes` が null なら読んだ中身から埋める（値があれば比べて、違えば止める）。配信は `checksum_sha256` が空なら ETag を付けず、304 の判定もしない（TC-04 に「checksum が null の行は ETag なし・`If-None-Match: "None"` で 200」を足す） |
| Medium | 入力検証（ファイル） | 保存する MIME を送り手の `content_type` から取ると、配信で HTML として解釈される（調査結果 6） | 必須: 保存は中身から判定した MIME（4-2）。配信は許可した 3 つ以外を `application/octet-stream`・`nosniff`・CSP の `sandbox`（4-5・TC-02・TC-05）。禁止: `image/svg+xml` を許可に足すこと |
| Low | マルチテナント | 一般の利用者は、同じ組織のどの画像も ID で取れる（学ぶ科目に入れていない科目の画像・答える前の解説の画像を含む） | 問題の取得（`available_problems`）と同じ組織の単位の境界にそろえる。ID は UUID で、応答に出るのは見てよい場面だけ（R5 で受け入れ） |
| Low | OWASP（資源の消費） | ログインした利用者が大きな画像（最大 5MB）を繰り返し取り、DB の読み込みを増やす | 既定の回数の制限（300/分）・`max-age` と 304 で 2 回目の読み込みを減らす。上限は今の 5MB のまま |
| Low | ファイル操作 | 移行が `storage_key` から読む場所を作るので、`../` やシンボリックリンクで置き場の外を読める | 必須: `resolve()` した場所が `LEGACY_MEDIA_ROOT.resolve()` の下でなければ止める（4-8・TC-14 の (c)。シンボリックリンクも `resolve()` で外に出るので止まる） |
| Low | 機密情報 | 検査のエラーの文に例外の文字列（`str(e)`）が入る（`utils.py` の `validate_image_file` の 3・4。今からある） | 範囲の外で変えない。新しく足すコードでは例外の文字列を応答に入れない（`upload_image`・`delete_image` の 500 の `str(e)` は消す・4-4） |
| なし | 認証・認可 | — | 新しい API は `IsAuthenticated`・組織は `request.user` から（4-5）。書き込みの action は今の `IsOrgAdmin` のまま |
| なし | 外部通信 | — | 外部の API・Webhook は無い |
| なし | 依存ライブラリ | — | 足さない・上げない |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | `GET /api/media/<id>/` | 未認証 | 知っている画像の ID で中身を取る | 401 で中身を返さない | Yes: TC-06 | Yes: M6（未ログインの `fetch`） | なし | High |
| 2 | `GET /api/media/<id>/` | 他の組織の利用者 | 他の組織の画像の ID で取る | 404（あることも知らせない） | Yes: TC-07 (a) | Yes: M6（組織 B） | なし | High |
| 3 | `GET /api/media/<id>/` | 同じ組織の利用者 | 論理削除した画像・持ち主が null の画像を取る | 404 | Yes: TC-07 (b)〜(e) | No | なし | Medium |
| 4 | `POST /api/problems/`・`PATCH`・`images/upload/` | 組織の管理者 | 中身が PNG で `content_type: text/html` の画像、または HTML を埋めた画像を登録し、配信の URL を他の利用者に開かせる | 保存は判定した MIME・配信は `image/png`＋`nosniff`＋CSP の `sandbox` で、スクリプトが動かない | Yes: TC-02・TC-05 | No | 画像として正しいファイルに埋めた文字列は画像として表示されるだけ | High |
| 5 | `GET /api/media/<id>/`（`If-None-Match`） | 同じ組織の利用者 | ETag を合わせて 304 を引き出し、中身があるかを確かめる・別の画像の中身を取り違えさせる | 304 は利用者に見える画像だけ（取り出しの絞り込みの後に判定）。ETag は中身の SHA-256 で、null の行は ETag を付けない | Yes: TC-04（null の行を含む） | No | なし | Medium |
| 6 | `PATCH /api/problems/<id>/`（`question_order` の `existing`） | 組織の管理者 | 他の組織の画像の ID を `existing` に入れて自分の問題に紐づけ、配信で取る | その問題に紐づいた画像だけを受け付ける（`_reconcile_images` の今の確かめ。変えない） | Yes: 既存の `test_I073_image_update.py`（他の問題の画像の指定で 400） | No | なし | High |
| 7 | `migrate`（0025） | 開発の環境の DB に行を書ける人 | `storage_key` に `../../` やシンボリックリンクを入れ、置き場の外のファイルを DB に入れさせる | 置き場の外なら止める | Yes: TC-14 (c) | No | DB に直接書ける人はもともと何でも読める（脅威は事故） | Low |
| 8 | 画面（`MediaImage`） | 同じ組織の利用者 | 画像の取得の失敗を何度も起こし、通知を重ねる | 画像の取得は通知を出さず枠に出す | Yes: TC-16・TC-17 | Yes: M5 のコンソール | なし | Low |

### 必須防御条件（実装で守ること）
- 0025: `checksum_sha256`・`file_size_bytes` が null なら読んだ中身から埋める。値があって違えば止める
- 配信: `checksum_sha256` が空の行は ETag を付けず、304 の判定をしない。304 の判定は、利用者に見える画像の取り出し（組織・論理削除・null の絞り込み）の後に行う
- 許可する MIME に `image/svg+xml` を足さない

## レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 0件 | 4件（どれも設計で守られている・自動テストあり） |
| Medium  | 2件 | 2件 |
| Low     | 4件 | 2件 |

### 残余リスク処遇
（retro 段階で決定する）
