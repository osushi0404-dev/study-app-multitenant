# plan_I073: 問題編集時の画像更新（追加・差し替え・削除・並び替え）

## 基本情報
- **計画書ID**: plan_I073
- **関連イシュー**: #150
- **Draft PR**: #151
- **作成根拠資料**: docs/issues/open/I073.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I073_review.md
- **作成日**: 2026-06-23

---

## 1. 背景/目的

問題は画像付き（問題画像・解説画像 各最大5枚）で**作成**できるが、作成後に画像を**編集**できない。
編集フロー（PUT `/api/problems/{id}/`）に画像差分処理が接続されておらず、`ProblemService.update_problem_with_images()` は `# TODO: 画像の追加・削除・並び替え機能` のコメントのみで画像をサーバ側で無視している。フロント編集ダイアログも JSON PUT で画像を送らず、既存画像を表示すらしない。

本イシューでは、編集を作成と対等な **PUT の一括差分更新（multipart）** で完結させ、画像の追加・差し替え・削除・並び替えを `@transaction.atomic` 下で一貫処理する。

### 調査結果

#### 現状コードの根拠（実在確認済み）
- `backend/problems/services/problem_service.py:212-259` `update_problem_with_images()` … 基本情報・選択肢のみ更新、画像は `# TODO`（256-257行）で未実装。
- `backend/problems/services/problem_service.py:114-210` `_process_images()` … 作成フローの画像保存パイプライン（バリデーション→サニタイズ→重複チェック→ディレクトリ確認→UUID保存→`MediaAsset`作成→`ProblemMediaAsset`作成、position は `enumerate(images, start=1)`）。**本実装で共有ヘルパへ抽出して再利用する**。
- `backend/problems/views.py:276-279` `ProblemViewSet.perform_update()` … `serializer.save()` のみでキャッシュ無効化。画像・order の取り出しなし。
- `backend/problems/views.py:231-274` `perform_create()` … 画像取り出しの参照実装（`request.FILES['question_image_{i}']` を 1..5 でループ → `ProblemService.create_problem_with_images()`）。
- `backend/problems/serializers.py:82-225` `ProblemSerializer` … `question_images`/`explanation_images` は `SerializerMethodField`（読み取り専用、`get_media_assets()` 経由）。`to_internal_value` で `choices` JSON をパース。画像入力フィールドは持たない（multipart の追加フィールドは ModelSerializer が無視）。
- `backend/common/mixins.py` `MultipartFormDataMixin` … QueryDict→dict 変換は serializer 用。`perform_update` は `self.request.FILES` / `self.request.data` を直接参照するため影響なし。
- `frontend/src/pages/QuizManagement.tsx`
  - `handleCreateProblem`（225-269行付近）… FormData に `question_image_{i}`/`explanation_image_{i}` を積んで `apiClient.post` 直呼び。
  - `handleUpdateProblem`（284-289行付近）… `apiClient.put(.../, data)` の **JSON 直呼び（画像無視）**。
  - `openEditDialog`（311-325行付近）… 既存画像（`problem.question_images`）を state に読み込まない。
  - 画像 state は `questionImages: File[]` / `explanationImages: File[]`（react-hook-form 外）。
- `frontend/src/components/ImageUploadArea.tsx` … props は `images: File[]` のみ。既存画像（URL＋asset id）・並び替えは未対応。
- `frontend/src/services/quiz.service.ts:42-48` `updateProblem(id, problemData)` … **呼び出し元ゼロ**（`grep -rn updateProblem frontend/src` で定義1件のみ）。QuizManagement は `apiClient` 直呼び。→ 本実装で multipart 送信用に転用し、`handleUpdateProblem` から利用する（サービス層経由化・テスト容易性の改善）。
- `frontend/src/services/types.ts` … `Problem.question_images?: MediaAsset[]` / `MediaAsset { id, url, usage_kind, original_filename, mime_type, file_size_bytes, created_at }`。

#### DB モデル制約（`backend/problems/models.py`、実在確認済み）
- `ProblemMediaAsset` `unique_together = [['problem','asset','usage_kind'], ['problem','usage_kind','position']]`、`ordering = ['problem','usage_kind','position']`、`asset` は `on_delete=models.RESTRICT`、`problem` は `related_name='media_links'`。
  - **重要**: `(problem, usage_kind, position)` の UNIQUE 制約は `is_deleted` を条件に含まない。よって**位置のインプレース更新（入れ替え）は一時的な重複で制約違反を起こし得る**。論理削除（`is_deleted=True`）後の再作成も同じ position 値が残り衝突する。→ 並び替えは「対象 usage_kind の link 行を物理削除→順序通りに再作成」する（後述「実装手順 ステップ2」）。
- `MediaAsset` `unique_together = [['organization','storage_key']]`、`is_deleted`（論理削除フラグ）、`usage_kind ∈ {problem, explanation}`。
- `Problem.organization`、`Subject.organization`、`MediaAsset.organization` 各 FK。

#### 環境前提確認
- バックエンドのテスト/実行は Docker 経由（`docs/runbooks/common-commands.md`: `docker compose exec backend python manage.py test`）。`backend/pytest.ini` あり（`DJANGO_SETTINGS_MODULE=core.settings`、`--no-migrations`、pytest スタイル）。
- **WSL 再起動直後で Docker Desktop の WSL 連携が無効のため、本計画作成時点でバックエンドテストスイートは未実行**（`backend/.venv` はフック用の bandit/flake8 のみで Django/pytest 非導入）。ベースラインは実装フェーズ（Docker 起動後）に取得する。既存 `problems/tests/` は3ファイル（`test_views.py`/`test_serializers.py`/`test_I006_subject_org_admin.py`）で、**画像系テストは未整備**（本イシューで新規追加）。
- 既存テストは pytest スタイル（`@pytest.mark.django_db`、`settings.MEDIA_ROOT = str(tmp_path)`、`APIClient().force_authenticate(...)`、URL はハードコード `/api/problems/`）。本イシューのテストもこれに合わせる。

---

## 2. 受け入れ条件（イシュー AC を踏襲）
- [ ] 既存問題に画像を追加でき、保存後の再取得で反映される
- [ ] 既存画像を削除でき、共有されていない場合はストレージ実体も削除される（共有時は紐づけのみ解除）
- [ ] 既存画像を差し替えでき（削除＋追加）、結果が正しく反映される
- [ ] 画像の並び順を変更でき、`position` が再採番されて表示順に反映される
- [ ] 問題画像・解説画像それぞれで上記が機能する
- [ ] 枚数上限（各5枚）を編集時も超過できない（超過時はバリデーションエラー＝HTTP 400）
- [ ] 編集処理はトランザクションで、途中失敗時に部分更新が残らない
- [ ] 他組織ユーザーは対象問題を編集できない（queryset スコープにより 404）
- [ ] 上記を検証する決定論テストが追加され全て PASS する（追加・削除・差し替え・並び替え・枚数上限・共有画像・他組織不可の各ケース）

---

## 3. 影響範囲
- **Backend**: `problems/services/problem_service.py`（差分処理本体）、`problems/views.py`（`perform_update` で order/files 取り出し）、`problems/serializers.py`（multipart 追加フィールドの無害な受理確認のみ。原則コード変更なし）。
- **Frontend**: `pages/QuizManagement.tsx`（編集ダイアログの既存画像ロード・multipart 送信）、`components/ImageUploadArea.tsx`（既存/新規混在・並び替え対応）、`services/quiz.service.ts`（`updateProblem` を multipart 転用）、`services/types.ts`（編集用画像アイテム型の追加）。
- **DB**: スキーマ変更なし（既存 `MediaAsset`/`ProblemMediaAsset` を使用）。→ セクション10（データ整合性設計）は**マイグレーションなし**だがトランザクション境界の設計を記載。
- **Config/Infra**: なし。依存ライブラリ追加なし（DnD ライブラリ不採用＝上下ボタン）。→ Dockerfile / docker-compose / requirements / package.json への波及なし（**P3/P5/P8 影響なし**）。

---

## 4. 変更点一覧

### Backend
| ファイル | 関数/箇所 | 変更内容 |
|---------|----------|---------|
| `problems/services/problem_service.py` | `_save_image_as_asset()`（**新規・staticmethod**） | `_process_images` のステップ1〜6（バリデーション→サニタイズ→重複チェック→ディレクトリ確認→UUID保存→`MediaAsset.create`）を抽出。`MediaAsset` を返す。`ProblemMediaAsset` 作成・position 採番は呼び出し側が担当。 |
| 〃 | `_process_images()` | 上記ヘルパを呼ぶよう内部リファクタ（作成フローと更新フローでロジック共有・C7）。外部挙動は不変（回帰テストで担保）。 |
| 〃 | `update_problem_with_images()` | シグネチャを `(problem, validated_data, question_files=None, explanation_files=None, question_order=None, explanation_order=None)` に変更。基本情報・選択肢更新は現状維持。usage_kind ごとに `_reconcile_images()` を呼ぶ。 |
| 〃 | `_reconcile_images()`（**新規・staticmethod**） | order 配列に基づく差分削除・追加・並び替え（後述ロジック）。`order is None` の usage_kind は無変更。 |
| `problems/views.py` | `ProblemViewSet.perform_update()` | `request.FILES` から `question_image_*`/`explanation_image_*` を収集、`request.data` から `question_images_order`/`explanation_images_order`（JSON）をパース。`ProblemService.update_problem_with_images()` を呼び、キャッシュ無効化、`serializer.instance` 設定（`serializer.save()` は**呼ばない**＝作成フローと同方式）。 |

### Frontend
| ファイル | 箇所 | 変更内容 |
|---------|------|---------|
| `services/types.ts` | 新規型 | `EditableImage = { kind:'existing'; assetId:string; url:string; filename:string } \| { kind:'new'; file:File }` を追加。 |
| `components/ImageUploadArea.tsx` | props/描画 | props を `images:File[]` → `items: EditableImage[]` に変更。`onImagesAdd(files)` / `onRemove(index)` / `onMoveUp(index)` / `onMoveDown(index)` を受ける。プレビューは existing=`item.url`、new=`URL.createObjectURL(item.file)`。各サムネに ↑/↓ ボタン（先頭で↑無効・末尾で↓無効）と削除ボタン。枚数バリデーションは `items.length` 基準。 |
| `pages/QuizManagement.tsx` | state | `questionImages/explanationImages: File[]` → `questionImageItems/explanationImageItems: EditableImage[]`。 |
| 〃 | `openEditDialog` | `problem.question_images?.map(a => ({kind:'existing', assetId:a.id, url:a.url, filename:a.original_filename}))` で初期化。解説画像も同様。新規作成時は空配列。 |
| 〃 | `handleCreateProblem` | items（全て new）から `question_image_{i}` を組み立て（挙動不変、order は送らない＝作成フローは従来通り）。 |
| 〃 | `handleUpdateProblem` | FormData にテキスト・choices＋ usage_kind ごとに order 配列（`{existing:assetId}`/`{new:key}`）と新規ファイルを積み、`quizService.updateProblem(id, formData)` を呼ぶ。 |
| `services/quiz.service.ts` | `updateProblem` | シグネチャを `(id:string, formData:FormData)` に変更し `multipart/form-data` で PUT 送信（`importProblems` と同方式）。 |

---

## 5. 実装手順（垂直スライス）

> 検証手順は各ステップ本文に書かず、`docs/tests/open/I073_auto_test.md` の TC として記述する（→ TC 参照）。

### ステップ1: バックエンド差分処理の中核（追加・削除・並び替え＋トランザクション）
**未知リスク先行**: position UNIQUE 制約・共有画像・トランザクション原子性が本イシュー最大の技術リスクのため最初に実装する。

1. `_save_image_as_asset()` を新規抽出し `_process_images()` をそれ経由に変更（C7 再利用）。
2. `update_problem_with_images()` のシグネチャ変更＋`_reconcile_images()` 実装。
3. `perform_update()` で order/files を取り出して service を呼ぶ。

**`_reconcile_images(problem, usage_kind, order, files, organization, subject)` のロジック**（`order is None` なら即 return＝当該種別は無変更）。

**重要な順序原則（Blocker 是正・物理削除は最後）**: 物理ファイル削除は**非可逆**でトランザクションのロールバック対象外のため、**新規ファイルの保存（バリデーション含む）と link 再構築がすべて成功した後に、最後にまとめて実行する**。これにより「途中失敗時に**残すべき**ファイルが消える」事故を構造的に排除する（C1）。

```
1. 枚数上限: len(order) > MAX_IMAGES_PER_KIND → ValidationError("…は最大5枚までです")
     # MAX_IMAGES_PER_KIND = 5 を problem_service.py のモジュール定数として新設し、
     # create_problem_with_images / _process_images の既存リテラル「5」もこの定数に寄せる（マジックナンバー排除・C7）。
2. 現在の有効 link を取得:
     current = ProblemMediaAsset.objects.filter(
         problem=problem, usage_kind=usage_kind, is_deleted=False
     ).select_related('asset')
   current_assets = {str(link.asset_id): link for link in current}
3. order を検証しながら「残すアセット」を決定:
     keep_asset_ids = set(); seen_new_keys = set()
     for entry in order:
       # existing と new の同時指定は不正（孤児アセット生成・あいまいさ防止）→ 400【code-review対応】
       if 'existing' in entry and 'new' in entry:
          raise ValidationError("order 要素は existing と new を同時に指定できません")
       if 'existing' in entry:
         aid = str(entry['existing'])
         if aid not in current_assets:            # 他問題/他種別のアセット混入を拒否（認可・整合）
            raise ValidationError("指定された既存画像は本問題に紐づいていません")
         if aid in keep_asset_ids:                # 同一既存の重複指定（unique違反=500）を事前に弾く→400【code-review対応】
            raise ValidationError("同じ既存画像を重複して指定できません")
         keep_asset_ids.add(aid)
       elif 'new' in entry:
         if entry['new'] not in files:            # 参照する新規ファイルが未送信
            raise ValidationError(f"新規画像ファイル {entry['new']} が見つかりません")
         if entry['new'] in seen_new_keys:        # 同一新規キーの重複指定（unique違反=500）を弾く→400
            raise ValidationError("同じ新規画像を重複して指定できません")
         seen_new_keys.add(entry['new'])
       else:
         raise ValidationError("order 要素は existing / new のいずれかを指定してください")
4. 【新規ファイルを先に保存】（物理削除の前に実施＝失敗時に削除を一切行わせない）:
     new_assets = {}                              # field_key -> MediaAsset
     for entry in order:
       if 'new' in entry:
         # _save_image_as_asset 内で validate_image_file / 重複・ディレクトリ確認 → 失敗時 ValidationError
         # 失敗すれば物理削除（手順6）に到達せず rollback。新規 UUID 保存のため既存ファイルを上書きしない。
         new_assets[entry['new']] = ProblemService._save_image_as_asset(
             files[entry['new']], usage_kind, organization, subject)
5. 【link 再構築】position UNIQUE 衝突回避のため delete→recreate:
     current.delete()        # 当該 (problem, usage_kind) の link 行を物理削除（asset 実体・ファイルは未削除）
     for position, entry in enumerate(order, start=1):
       asset = (current_assets[str(entry['existing'])].asset
                if 'existing' in entry else new_assets[entry['new']])
       ProblemMediaAsset.objects.create(
           organization=organization, problem=problem, asset=asset,
           usage_kind=usage_kind, position=position)
6. 【最後に】削除対象アセットの論理削除＋物理削除（ここまで全成功時のみ到達）:
     for aid, link in current_assets.items():
       if aid not in keep_asset_ids:
         asset = link.asset
         shared = ProblemMediaAsset.objects.filter(
             asset=asset, is_deleted=False
         ).exclude(problem=problem).exists()      # 手順5で自問題 link は削除済み（多重防御）
         if not shared:
            asset.is_deleted = True
            asset.save(update_fields=['is_deleted'])
            try: StorageService.delete_file(asset.storage_key)
            except Exception as e:
               logger.warning(                    # 物理削除失敗はログのみで続行（DB整合優先・delete_problem 踏襲）
                 "media physical delete failed",
                 extra={"problem_id": problem.id, "organization_id": organization.id,
                        "asset_id": str(asset.id), "storage_key": asset.storage_key,
                        "error": str(e)})
```

- **残留オーソン（軽微）**: 手順4で正常保存した新規ファイルの後、手順5/6 で予期せぬ例外が起きると DB はロールバックされるが手順4で書き込んだ物理ファイルは残る（=「余分なファイル」。**消えてはいけないファイルが消える」事故とは逆方向**で実害小）。発生は稀（UNIQUE 違反等）で、storage_key は MediaAsset 行に残らないため将来の孤児ファイル GC イシューで回収する。本イシューでは許容（R2）。
- `update_problem_with_images` 全体は既存の `@transaction.atomic` を維持。`_reconcile_images` 内の例外（バリデーション・保存失敗）は全体ロールバックされ部分更新が残らない（C1）。→ TC-AUTO-07/08。
- **【セキュリティ／テナント境界・必須防御 SEC-1】画像保存に使う `organization`/`subject` は更新対象 `problem` の**永続化済み**（編集前の）`problem.subject` とその `organization` を権威とする。投稿された `validated_data['subject']` をそのまま信頼して org を導出しない。さらに `perform_update` で、`validated_data` に subject 変更が含まれる場合は `new_subject.organization_id == request.user.organization_id` を検証し、不一致なら `ValidationError`（400）。これにより「自組織の問題を他組織 subject に付け替える」越境データ注入と、新規画像を他組織ストレージ配下に書き込む越境ファイル書き込みを防ぐ（`ProblemSerializer.subject` は queryset 未スコープのため本ガードで補う）。→ TC-AUTO-12。
  - 注: `subject` フィールド queryset 自体の org スコープ化は作成フロー（`create_problem_with_images` も投稿 subject の org を信頼）にも及ぶ**既存の系統的ギャップ**のため、本イシューでは更新経路を上記ガードで塞ぎ、シリアライザ全体のスコープ化はフォローアップ・セキュリティイシューに切り出す（/retro で処遇決定）。
- 依存: ステップ2（フロント）はステップ1完了が前提。ステップ1単独でバックエンド TC（TC-AUTO-00〜12、ただし手動UI依存を除く）が完結する。

### ステップ2: フロント編集ダイアログ（既存画像表示・並び替え・multipart 送信）
1. `services/types.ts` に `EditableImage` を追加。
2. `ImageUploadArea.tsx` を `items` ベースに改修（↑/↓・削除・既存/新規プレビュー）。
3. `QuizManagement.tsx`: state を items 化、`openEditDialog` で既存画像ロード、`handleCreateProblem`/`handleUpdateProblem` を items から組み立て。
4. `quiz.service.ts` `updateProblem` を FormData multipart 送信に転用。
- 依存: ステップ1完了後（API 契約確定後）に実施。手動 TC（TC-MAN-01〜06）はステップ2完了後。

### ステップ3: テスト整備
- バックエンド: `backend/problems/tests/test_I073_image_update.py`（新規）に **TC-AUTO-00〜12（13件）** を pytest スタイルで実装（→ I073_auto_test.md）。回帰（00）・解説画像（10）・差し替え（11）・越境subject拒否（12, SEC-1）を見落とさないこと。
- フロント手動: I073_manual_test.md の TC-MAN-01〜06。

---

## 6. テスト計画（自動/手動）

### テストレベルの選択
- **結合（API）テスト**（pytest + APIClient）: 差分処理は service＋view＋DB＋ストレージの結合動作が本質のため、ユニットでなく `/api/problems/{id}/` への multipart PUT を起点とする結合テストを主軸にする。
- **手動（E2E/UX）**: ブラウザ上のダイアログ操作・並び替えボタン・プレビュー表示は Human 手動。
- **認可・テナント境界**: 他組織 404（TC-AUTO-06）、他問題アセット混入拒否（TC-AUTO-09）を明示的に含める。
- **回帰防止**: 作成フロー（`_process_images` リファクタ）の既存挙動回帰（TC-AUTO-00 として作成フローの画像作成が従来通り動くこと）。

詳細は `docs/tests/open/I073_auto_test.md` / `docs/tests/open/I073_manual_test.md`。

---

## 7. ロールバック
- 単一 PR・スキーマ変更なしのため、PR revert で完全に元に戻せる。
- 物理ファイル削除を伴うが、削除対象は「当該問題に紐づき他で共有されていないアセット」に限定。万一の誤削除に対しては DB の `MediaAsset`（論理削除＝レコードは残存）から storage_key を辿って復旧判断が可能。
- フロント/バックは独立 revert 可能だが、API 契約が連動するため**同一 PR 内で整合を保ってマージ／revert する**。

---

## 8. Risk & 回避策
| Risk | 内容 | 回避策 |
|------|------|--------|
| R1 | position UNIQUE 制約による並び替え時の制約違反 | link 行を delete→recreate で再採番（インプレース更新しない）。TC-AUTO-04 で検証。 |
| R2 | 途中失敗による**残すべきファイルの消失**／孤児アセット（部分更新） | **物理削除を全工程の最後に遅延**（新規保存＋link再構築の成功後にのみ削除実行）＋`@transaction.atomic`。失敗注入テスト（TC-AUTO-07/08）で「物理・DB ともに元のまま」を確認。逆方向の軽微な残留オーソン（成功保存後の予期せぬ例外で書込済みファイルが残る）は実害小として許容。 |
| R3 | 他問題/他組織アセットの混入による不正紐づけ | order の `existing` UUID を現在の link 集合に対して検証（混入は 400）。TC-AUTO-09。他組織は queryset スコープで 404（TC-AUTO-06）。 |
| R4 | 共有アセットの誤物理削除 | 削除前に `is_deleted=False` の他問題 link 有無を確認、共有時は紐づけ解除のみ（既存 `delete_problem` 踏襲）。TC-AUTO-05。 |
| R5 | `order` 未送信時に画像が意図せず全削除される | `order is None`（フィールド非送信）は当該種別を無変更、`[]`（空配列送信）のみ全削除という二値仕様を厳守。TC-AUTO-03（空配列で全削除）＋テキストのみ編集で画像保持（TC-AUTO-02 の派生）。 |
| R6 | 作成フローのリファクタ回帰 | `_process_images` の外部挙動を変えず、TC-AUTO-00 で作成時画像が従来通り作られることを担保。 |
| R7 | 物理ファイル削除失敗時の挙動 | `delete_file` 失敗はログ警告のみで処理続行（DB 整合優先・既存踏襲）。ログは構造化（`extra` に `problem_id`/`organization_id`(=tenant)/`asset_id`/`storage_key`/`error`）して障害追跡性を確保。`request_id` 単位の追跡はリクエストID付与ミドルウェアが整備された時点で `extra` に追加（本イシューでは `organization_id` で tenant 追跡可能なため任意・将来対応）。 |
| R8 | 並行リクエストによる同一非共有アセットの二重物理削除（競合） | 同一問題の同時編集は想定外・スコープ外（§10）。`delete_file` は冪等（存在しなければ no-op）のため二重削除でも致命的破壊はなし。将来 `select_for_update` 等の排他制御は別イシューで検討。 |

---

## 10. データ整合性設計（DB スキーマ変更なし／トランザクション境界）
- **マイグレーション**: なし（既存テーブル使用）。
- **トランザクション境界**: `update_problem_with_images()` 全体を `@transaction.atomic`。問題基本情報・選択肢・問題画像・解説画像の更新を単一トランザクションに含め、いずれかの失敗で全ロールバック。
- **冪等性**: order 配列は「最終状態」を表す宣言的指定のため、同一 order の再送は同一結果（新規ファイルキーが無ければ existing のみで収束）。ただし `new` を含む再送は新規アセットを再作成するため非冪等（クライアントは成功後に order を existing 化する想定）。
- **同時更新**: `MediaAsset.version`（楽観ロック用フィールド）は本イシューでは未使用（同一問題の同時編集は想定外・スコープ外）。並行リクエストでの二重物理削除競合は `delete_file` の冪等性で致命傷化せず、排他制御（`select_for_update`）は将来イシューで検討（R8）。
- **物理削除の安全性（Blocker 是正の核）**: 物理ファイル削除は非可逆でロールバック対象外のため、**「新規ファイル保存（バリデーション含む）→ link 再構築 → ★最後に物理削除」の順序を厳守**する（`_reconcile_images` 手順4→5→6）。これにより、新規ファイルのバリデーション失敗や link 制約違反など**途中失敗時には物理削除に到達せず**、残すべきファイルが消える事故が構造的に発生しない。共有チェック（他問題の有効 link 有無）→ 非共有時のみ物理削除＋論理削除。逆方向の残留（成功保存後の予期せぬ例外による書込済みファイルの残置）は実害小として許容し、storage_key が DB に残らないため将来の孤児ファイル GC で回収（R2）。

---

## 13. 性能・UX設計
- **パフォーマンス**: 1問題あたり画像は最大5枚×2種別。`current` 取得は `select_related('asset')`。link の delete→recreate は最大10行で N+1 懸念なし。共有チェックは usage_kind ごとの削除候補数だけ（最大5回）。キャッシュは `cache_service.invalidate_problems_cache(subject_id)` で無効化（作成・削除と同方式）。
- **ローディング/エラー表示**: 編集保存中はダイアログの保存ボタンを無効化（既存パターン踏襲）。API 400 はトーストでメッセージ表示（枚数上限・不正order）。
- **空状態**: 既存画像 0 枚・新規 0 枚の編集はテキストのみ更新（order 非送信）。
- **破壊的操作（画像削除）の確認導線**: 各サムネの削除はトグル（ダイアログを保存するまでサーバ反映されない）ため、保存前に取り消し可能。明示の確認ダイアログは過剰のため設けない（保存時に最終状態が確定する設計を承認ポイントで確認）。
- **並び替え UI**: 各サムネに ↑/↓ ボタン（先頭は↑、末尾は↓を `disabled`）。DnD ライブラリは追加しない（イシュー確定事項）。
- **アクセシビリティ**: ↑/↓・削除ボタンに `aria-label`（「上に移動」「下に移動」「削除」）を付与。

---

## 要件適合性・セキュリティ・設計判断（承認ポイント用サマリ）

### 要件適合性・業務ロジック
- 仕様追加・逸脱なし。イシュー「設計確認メモ」で確定した multipart 契約（`*_image_i` / `*_images_order` の `{existing}|{new}`、暗黙削除、上限5枚、上下ボタン）をそのまま計画に反映。
- マルチテナント/組織スコープ: `ProblemViewSet.get_queryset` の `subject__organization == request.user.organization` で他組織 404。加えて order の `existing` UUID を本問題の link 集合に限定（横断混入拒否）。**計画に明示済み**。
- 更新可否条件: `permission_classes=[IsAuthenticated]`（`IsOrgAdmin` は Subject 作成のみ）。問題編集は組織所属ユーザーなら可（既存挙動踏襲、変更なし）。

### セキュリティ・ベストプラクティス
- 入力バリデーション: 新規ファイルは既存 `validate_image_file`（サイズ/MIME/マジックナンバー/ピクセル/ファイル名安全性）を `_save_image_as_asset` 経由で再利用。order は JSON パース失敗・型不正・上限超過・不正UUID を 400 で拒否。
- 認可: 最小権限。他組織 404・他問題アセット混入 400。新規の権限緩和なし。
- 機密データ: 扱わない（画像のみ。個人情報・トークンなし）。
- OWASP: パストラバーサルは `sanitize_filename`/`storage_key` 既存対策を踏襲。IDOR は queryset スコープ＋existing UUID 検証で防止。CSRF は既存 DRF 認証設定踏襲（変更なし）。XSS はファイル名表示時に React の既定エスケープ。
- 依存ライブラリ追加なし → pip-audit / npm audit 新規対象なし。
- スキャン基準: bandit MEDIUM 以上を修正対象（LOW は `# nosec`）、npm audit high/critical を修正対象（プロジェクト既定）。新規導入コードに対し実装時に `flake8`/`bandit` を実行。

### テスト計画チェック
- バグ修正（編集で画像が無視される）に対する再発防止: TC-AUTO-01（追加）〜09 を新規追加。
- テストレベル選択を明記（結合主軸・手動はUX）。
- 認可・テナント境界テスト: TC-AUTO-06（他組織404）・TC-AUTO-09（他問題アセット混入400）を含む。

### データ整合性・運用性・コスト
- DB 変更なし（マイグレーションなし）→ セクション10にトランザクション境界・物理削除順序を記載。
- 外部API・非同期・バッチなし → **P5（運用設計）影響なし**。
- 新規インフラ・外部サービスなし → **P8（コスト見積もり）影響なし**。
- 依存ファイル変更なし → Dockerfile/compose 波及なし。

### 性能・UX
- フロント変更あり → セクション13 を記載（ローディング・エラー・並び替えUI・a11y・破壊的操作の確認導線）。
- パフォーマンス: 最大10行操作で N+1 なし。

### プライバシー・コンプライアンス
- 個人情報・未成年データ・テナント越境利用なし（画像コンテンツのみ、組織内に閉じる）→ **P9 影響なし**。高リスク判定（I043）非該当・`/security-review`（I044）対象外。

### 設計品質
- アンチパターン回避: ビジネスロジックは `ProblemService`（Fat View 回避）、Raw SQL 不使用、ORM のみ。フロントは `ImageUploadArea` を再利用（巨大コンポーネント化回避）、props で受け渡し（過度な props drilling なし）。
- null/空値方針: `order is None`=無変更 / `[]`=全削除 の二値を統一。
- 例外処理: バリデーションは DRF `ValidationError`→400。物理削除失敗はログ警告のみ（DB 整合優先）。
- ハードコード回避: 上限5枚は新設モジュール定数 `MAX_IMAGES_PER_KIND = 5`（`problem_service.py`）に集約し、`_reconcile_images`・`create_problem_with_images`・`_process_images` で共用（新規マジックナンバーを作らない）。storage_key 規約は既存ユーティリティ再利用。

### 設計判断の明示（イシュー記載 / 仮定 の区別）
| 設計判断 | 区分 | 補足 |
|---------|------|------|
| multipart 契約（`*_image_i`/`*_images_order` の `{existing}\|{new}`、暗黙削除、上限5） | **イシュー明記** | 設計確認メモで確定 |
| 並び替え UI = 上下ボタン・DnD不採用 | **イシュー明記** | 設計確認メモで確定 |
| 編集権限 = IsAuthenticated＋組織スコープ（IsOrgAdmin不要） | **イシュー明記** | 設計確認メモ Q（自己解決） |
| `order is None`=無変更 / `[]`=全削除 の二値仕様 | **仮定（要確認）** | イシューは「暗黙削除」を定義するが「種別フィールド非送信＝無変更」は本計画での補完。テキストのみ編集で画像を保持するため必要。 |
| 並び替えを link 行 delete→recreate で実現（インプレース更新しない） | **仮定（実装方式）** | position UNIQUE 制約回避のための実装判断。外部契約には影響なし。 |
| `quizService.updateProblem` を multipart 転用（未使用のため安全） | **仮定（実装方式）** | 呼び出し元ゼロを確認済み |
| 物理削除失敗時はログ警告のみで続行 | **仮定（既存踏襲）** | `delete_problem` の挙動に合わせる |

> 「仮定」のうち **R5 の二値仕様**（order 非送信＝無変更）はユーザー価値判断に関わるため、承認ポイントで明示確認する。

---

## 9. 承認ポイント（チェックリスト）
以下に同意いただければ実装に着手します。

1. **API 契約**: PUT `/api/problems/{id}/`（multipart）で、`question_images_order`/`explanation_images_order`（JSON 配列、要素 `{"existing":"<UUID>"}` または `{"new":"<field key>"}`）＋ 新規ファイル `question_image_1..N`/`explanation_image_1..N` を受ける。**order フィールド非送信の種別は画像無変更／空配列 `[]` 送信で当該種別を全削除**（R5 の二値仕様）。この挙動で良いか。
2. **並び替え実装方式**: position UNIQUE 制約回避のため、対象種別の紐づけ行を delete→順序通り recreate（外部挙動は position 再採番として観測）。
3. **削除の物理/論理**: order に現れない既存アセットは紐づけ解除。**非共有なら物理削除＋`MediaAsset` 論理削除**、共有なら紐づけ解除のみ。
4. **UI（編集ダイアログ）**: 既存＋新規を1リスト表示。各サムネに「↑」「↓」「削除」ボタン（先頭↑・末尾↓は無効化、`aria-label` 付与）。削除は保存まで未確定（取り消し可）。新規 DnD ライブラリは追加しない。配置は既存「問題用画像」「解説用画像」欄を踏襲。
5. **サービス層**: 未使用の `quizService.updateProblem` を multipart 送信に転用し、`handleUpdateProblem` から利用。
6. **スコープ外の確認**: `upload_image`/`delete_image` 旧個別 API の刷新・二重実装統一は本イシュー対象外（フォローアップ）。
7. **テスト**: バックエンド結合テスト TC-AUTO-00〜12（作成回帰・追加・テキストのみ無変更・空配列全削除・並び替え・共有画像・他組織404・atomic 失敗注入×2・他問題アセット混入400・解説画像・差し替え・越境subject拒否SEC-1）＋手動 TC-MAN-01〜09 を追加。
8. **セキュリティ防御 SEC-1**: 画像保存の org/subject は問題の永続化済み subject を権威とし、subject の他組織付け替えを 400 で拒否（テナント越境の注入・ファイル書き込み防止）。

承認後の次のステップ: `/plan-issue-review I073` で計画書・テスト文書をレビュー。
</content>
</invoke>

## レビュー結果
- [20260623_0730 判定: ✅ 完了](../../reviews/I073_plan_review_20260623_0730.md)
- [20260623_0652 判定: 差し戻し（Blocker 1件）](../../reviews/I073_plan_review_20260623_0652.md)

---

## セキュリティレビュー結果

**実施日**: 2026-06-23

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| High | マルチテナント | `ProblemSerializer.subject` の queryset が組織スコープされておらず（全 Subject）、org を投稿 subject の `subject.organization` から導出している。編集 PUT で自組織の問題を**他組織の subject に付け替え**でき、越境データ注入＋新規画像を他組織ストレージ配下に書き込む越境ファイル書き込みが起こり得る。 | **SEC-1（必須・本計画に組込済）**: 画像保存の `organization`/`subject` は更新対象 `problem` の永続化済み subject を権威とする。`perform_update` で投稿 subject の org ≠ request.user.organization なら 400。→ TC-AUTO-12。残るシリアライザ全体のスコープ化（作成フローにも及ぶ既存ギャップ）は**フォローアップ・セキュリティイシュー**へ（/retro で処遇）。 |
| Low | ファイル操作 | 画像デコード時の decompression bomb（小サイズ高圧縮）による DoS 余地。 | 既存 `validate_image_file` の 4096×4096 ピクセル上限＋5MB サイズ上限で実質緩和済み。追加対処不要（許容）。 |
| Low | 入力検証 | `*_images_order` の JSON 構造・要素型・`existing` UUID の正当性。 | `_reconcile_images` で JSON パース失敗・型不正・上限超過・非自問題 UUID を 400 拒否（TC-AUTO-08/09）。対処済み。 |

その他分類（認証・認可／機密情報／OWASP Top10／外部通信／依存ライブラリ）: 設計上の新規リスクなし。
- 認証・認可: `permission_classes=[IsAuthenticated]`＋queryset の組織スコープ（他組織は 404）。新規権限緩和なし。
- 機密情報: ログは storage_key / 各種 id のみ（パスワード・トークン・PII 露出なし）。
- OWASP: IDOR は queryset スコープ＋order の existing UUID 自問題限定で防御。XSS はファイル名表示時に React 既定エスケープ。SQLi は ORM のみ。CSRF は既存 DRF 認証設定踏襲（変更なし）。
- 外部通信: なし。依存ライブラリ: 追加なし（DnD 不採用）。

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | PUT /api/problems/{id}/ | 他組織一般 | 他組織の問題を編集 | queryset 組織スコープで 404 | Yes: TC-AUTO-06 | No | なし | Low |
| 2 | PUT（order.existing） | 一般 | 他問題/他組織のアセット UUID を existing 指定し自問題へ紐づけ | 自問題の現在 link 集合に無い UUID は 400 | Yes: TC-AUTO-09 | No | なし | Low |
| 3 | PUT（subject 付け替え） | 一般 | 自問題を他組織 subject に付け替え＋新規画像投入 | 投稿 subject の org=自組織でなければ 400／画像 org は問題の権威 org | Yes: TC-AUTO-12（SEC-1 ガード） | No | シリアライザ全体の未スコープは作成フローに残る（フォローアップ issue） | High→（SEC-1で）Low |
| 4 | PUT（新規ファイル） | 一般 | 非画像/サイズ超過/拡張子偽装/パス含みファイル名をアップロード | `validate_image_file`（MIME マジック・拡張子整合・サイズ・ピクセル・ファイル名安全）で 400 | Yes: TC-AUTO-07（不正ファイル） | Yes: 多形式ポリグロット等の手動探索（TC-MAN系で補完可） | 既知形式以外の polyglot は理論上残るが MIME マジック＋拡張子整合で実用上遮断 | Low |
| 5 | PUT（order 枚数） | 一般 | 6枚以上を投入し上限回避 | `len(order) > MAX_IMAGES_PER_KIND` で 400 | Yes: TC-AUTO-08 | No | なし | Low |
| 6 | PUT（空 order []） | 一般（CSRF 誘発含む） | 既存画像の不正全削除 | 認証＋既存 CSRF/認証設定。order=[] は明示時のみ全削除 | 一部: TC-AUTO-03（挙動） | No | CSRF は既存設定に依存（本変更で悪化なし） | Low |

### 残余リスク処遇
（/retro で決定する）
- 主たる残余: シリアライザ `subject` フィールドの org スコープ未対応（作成フローを含む既存系統ギャップ）。SEC-1 で更新経路は遮断済み。作成経路を含む恒久対処はフォローアップ・セキュリティイシューとして起票候補。

---

## 振り返り候補（retro carry-over）

> /retro 実施時にここを必ず確認すること。本イシュー進行中に表面化した **skill 改善提案**（予防処置）であり、I073 のクローズ時に同梱処理する。

### 提案1: security-review 検出事項の actionable 反映を skill に組み込む

- **背景（観測事実）**: 本イシューの `/security-review` で High 1件（SEC-1: テナント越境 subject 付け替え）を検出。現状スキルは手順5で `## セキュリティレビュー結果` への**記録のみ**を規定しており、必須防御条件を計画書の実装手順・テスト・レビュー観点へ伝播する手順が無い。記録だけだと `/implement`（実装手順しか実装しない）・`/test`（auto_test の TC しか実行しない）に乗らず、「**文書化されたが実装も検証もされない防御**」＝ I072 の false-green と同型の false-safety になり得る。
- **今回の手当て（スキル規定外で手動実施）**: SEC-1 を §5 必須防御・§9 承認項目8・TC-AUTO-12（＋false-green 注入欄）・`I073_review.md` 観点へ伝播済み。この挙動を恒久化したい。
- **予防処置（do + gate の2層）**:
  - **do層** — `.claude/skills/security-review/SKILL.md` に手順 5.5 を追加:
    > 手順2/3 で検出した **Blocker/High かつ本イシュー対象の必須防御条件**（設計表の対処列が非空）は、`## セキュリティレビュー結果` への記録だけで終わらせず、(a) 計画書の実装手順／変更点一覧、(b) `I###_auto_test.md` の検証 TC（認可・否定系は false-green 自己検証欄も）、(c) `I###_review.md` のレビュー観点 へ**同時反映**する。Low/情報・残余リスク・スコープ外は「残余リスク処遇（/retro）」に留める。
  - **gate層** — `plan-reviewer.md` / `code-reviewer.md` のいずれか（または security-review 手順6の自己チェック）に追加:
    > - [ ] `## セキュリティレビュー結果` の各 Blocker/High 必須防御条件に、対応する (a) 実装手順/変更点・(b) 決定論 TC・(c) レビュー観点 が揃っているか（記録のみ＝未実装/未検証の防御が無いか）
- **スコープ判断**: 新規イシューは過剰。security-review スキルの小改修のため I073 の retro 予防処置として同梱する（既存イシュー同梱優先）。
- **波及確認（同梱時）**: 上記 do/gate 文言が I072 の false-green 文言・粒度とパリティを保つこと。`plan-writing-rules.md` の「計画書を変更したら関連ドキュメントも同時更新」原則の security-review 版に当たる点を明記。

### 提案2（フォローアップ・セキュリティイシュー候補）

- `ProblemSerializer.subject` の queryset が組織スコープ未対応で、**作成フロー（`create_problem_with_images`）にも同じテナント越境ギャップ**が残る（I073 は更新経路を SEC-1 で遮断したのみ）。シリアライザ全体の org スコープ化を別イシューで起票するか /retro で処遇決定する。
