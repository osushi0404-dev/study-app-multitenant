# 敵対的レビュー [I587]（別プロセス・2026-11-20 09:36）

- 見た範囲: d57c7718b4f027692cb2ade8fe8511d9d8470211...3db8b78adca5b5639c6f1fa5ea11ce5c412d2b3a
- 所要時間: 20 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: backend を起こして確かめた（12 秒・締め切りの外）
- 一覧: docs/plans/open/plan_I587.md の「## 必ず確かめる項目」（6 項目）
- 引き継ぎ: 引き継がない（I587_adversarial_review_20261119_2330.md の REVIEWED_COMMIT d57c7718b4f027692cb2ade8fe8511d9d8470211 から HEAD までに記録の場所の外が変わった: backend/problems/selectors.py backend/problems/serializers.py backend/problems/services/problem_service.py backend/problems/tests/test_I587_media_in_db.py backend/problems/tests/test_I587_media_migration.py backend/problems/views.py frontend/src/components/ImageUploadArea.tsx frontend/src/components/MediaImage.tsx frontend/src/components/ProblemImageList.tsx frontend/src/components/__tests__/MediaImage.test.tsx frontend/src/components/__tests__/ProblemImageList.test.tsx scripts/claude/tests/test_i569_issue_number_digits.sh）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 12 秒 | 0 | 0 | $0.2553 | ― | ― | ― |
| 2 | 報告あり | 11 秒 | 0 | 0 | $0.2400 | ― | ― | ― |
| 3 | 報告あり | 17 秒 | 0 | 0 | $0.2363 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I587] ── 観点: 1. ロジック回避・実機 repro

## findings
反証失敗（新規指摘なし）。探索した仮説:
- V1: TC-05〜TC-07 は本物の API クライアント（`client_for`）で配信を呼んでいる。確かめている境界は次のとおり。
  - 未ログインは 401。
  - 他の組織、論理削除、organization が null、subject が null、中身なし、存在しない UUID、組織なしの利用者は、すべて 404。
  - 同じ組織の一般の利用者は 200。
  - 組織の絞り込みを外すと `other_org` のケースが 200 になって落ちる。TC-07 の失敗の注入は、テストファイルのコメントではなく、既存のレビュー記録と自動テスト文書に書かれている。そちらを読んで確認した。
- V2: TC-02 は `content_type=text/html` の PNG を送り、保存された `mime_type` が `image/png` であること、配信の Content-Type が `image/png` であることを確かめている。TC-05 の `test_media_unknown_mime_is_octet_stream` は、`mime_type` を `text/html` に書き換えた行が `application/octet-stream` で返ることを確かめている。
- 実験は行っていない。読んで確かめただけである。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I587] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。探索した仮説:

- **V3（TC-11）**:
  - `content_sqls` は `CaptureQueriesContext` が取った SQL に `media_asset_contents` が含まれるかを見る。一覧・クイズの取得・回答の 3 つの with ブロックが、どれも `== []` で確かめている。
  - `select_related('asset__content')` を足すと JOIN の句にこの表名が出る。`prefetch_related` でも別の SELECT に出る。どちらも落ちる。
  - 注入の実機確認はしていない（読んだだけ）。
- **V6（TC-04）**:
  - 2 回目のリクエストだけを `CaptureQueriesContext` で囲み、`content_sqls(context) == []` を確かめている（`test_I587_media_in_db.py:204`）。
  - `W/` 付きは 304、一致しない `"x"` は 200、複数の値の中に一致があれば 304、`*` は 304 で、RFC 9110 の弱い比較どおり。
  - 実装は `get_conditional_response(request, etag=etag)` を `media_asset_data` より前に呼んでいる。差分で確認した（`views.py`）。メタデータだけの `.only(...)` で判定し、304 の枝では中身を読まない。
  - 中身を先に読む実装に変えると `content_sqls` の assert が落ちる。
- 補足（Low・指摘にしない）: 304 の経路は、`checksum_sha256` が空の行では ETag を付けず 200 になる。TC-04 の後半が確かめている。

> ITEM: V3 RESULT=read
> ITEM: V6 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I587] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。

探索した仮説:
- **削除の境界（`remove_image`）**
  - 絞り込みは `problem`・`asset_id`・`is_deleted=False`・`asset__organization_id=problem.subject.organization_id` の 4 条件。
  - 他の組織の画像・論理削除済みの自分の紐づけ・紐づけなしは、すべて 404 になる。
  - 追加テスト `test_delete_image_rejects_missing_or_deleted_own_link` がこの 3 つを見ている。
  - 同じ問題の別の用途に共有された画像は、`_discard_asset_if_unused` が全部の有効な紐づけを数えるので、誤って消えない。
- **追加の入力（`add_image`・`ImageUploadSerializer`）**
  - `file` なしと `usage_kind` の誤りは 400 になる。
  - `test_upload_image_action_rejects_bad_input` が、400 であること、`custom_exception_handler` の形であること、行が増えないことを見ている。
  - 表示順は、論理削除の紐づけも含めた最大値に 1 を足す。一意の制約に当たらない。
- **削除の経路の形**
  - 経路の正規表現は UUID の形だけを受ける。`uuid.UUID(asset_id)` で変換するので、形の違う値で 500 にはならない（`test_delete_image_route_accepts_only_uuid`）。
  - 経路は大文字小文字の 16 進を受け、`uuid.UUID` も受ける。
- **配信の `If-None-Match`・一覧の仕組み**
  - 弱い比較は ETag が中身の SHA-256 なので、違う画像を 304 にしない。判定は組織の絞り込み（`get_object()`）の後にある。
  - `get_conditional_response` は `If-Match` などを見て 412 を返しうる。組織の絞り込みの後なので、他の組織の画像の有無は漏れない。Low で、計画に受け入れ済み。
  - `filter_backends = []`・`pagination_class = None` で、`?ordering=` などは効かない（`test_media_ignores_list_query_params`）。
- **V4**
  - 今回の差分の変更は、出力の行を比べる形への直しだけ。ファイルのある行・無い行（TC-12）と、5 つの場合の網羅（既知 findings で確認済み）は変わらない。
  - 消す順は、紐づけを先、画像の行を後（既知 findings で確認済み）。
- **V5**
  - `upload_image` は `add_image` から `_save_image_as_asset` を通る。
  - `delete_image` は `remove_image` から `_discard_asset` を通る。
  - ビューから `StorageService`・`MEDIA_ROOT`・`/media/` を使うコードが消えた。
  - `views.py` に残る `MediaAsset` の import も外れている。
- 実験は行わなかった。
- 差分で見えなかった範囲: 304 の応答に ETag と Cache-Control が付くか（`views.py` の後半が差分に出ていない）。

> ITEM: V4 RESULT=read
> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 3db8b78adca5b5639c6f1fa5ea11ce5c412d2b3a
ROUNDS: 1
VERDICT: OK
