# 敵対的レビュー [I587]（別プロセス・2026-11-19 23:30）

- 見た範囲: origin/develop...d57c7718b4f027692cb2ade8fe8511d9d8470211
- 所要時間: 27 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: backend を起こして確かめた（20 秒・締め切りの外）
- 一覧: docs/plans/open/plan_I587.md の「## 必ず確かめる項目」（6 項目）

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
| 1 | 報告あり | 13 秒 | 0 | 0 | $0.2482 | ― | ― | ― |
| 2 | 報告あり | 23 秒 | 0 | 0 | $0.2591 | ― | ― | ― |
| 3 | 報告あり | 25 秒 | 0 | 0 | $0.3284 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I587] ── 観点: 1. ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| なし | - | 反証失敗（新規指摘なし） | - | 静的読解 |

反証失敗（新規指摘なし）。探索した仮説:
- V1: TC-05〜TC-07 が `APIClient` で次の境界を確かめているかを調べた。未ログイン 401、他の組織・論理削除・null の組織・null の科目・中身なし・無い UUID・組織なしの利用者はすべて 404、同じ組織の一般の利用者は 200 である。
- V1: TC-07 の失敗の注入は、自動テスト文書の TC-07 の行に「取り出しから `organization_id`・`subject__organization_id` を外すと落ちる」と書かれている。62 行目には、一時的に壊して実際に落ちたことが記録されている。
- V2: TC-02 は `content_type=text/html` で PNG を送り、保存された `mime_type` が `image/png` で、配信の Content-Type も `image/png` であることを確かめている。
- V2: TC-05 の `test_media_unknown_mime_is_octet_stream` は、`mime_type` を `text/html` に書き換えた行の配信が `application/octet-stream` になることを確かめている。
- 配信ビューの実装は、差分が 100KB で切れていたため未確認。TC の記述とテスト本体だけで判定した。
- 実験は行わなかった。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I587] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。

探索した仮説:
- 仮説 1: TC-11 は中身の表を読んでいても落ちない。
  - 結論: 落ちる。`content_sqls` は `CaptureQueriesContext` が取った SQL に `media_asset_contents` が含まれるかを見る。`select_related('asset__content')` を足すと JOIN の句にこの表名が出る。`prefetch_related` でも別の SELECT に出る。どちらも `== []` で落ちる。
  - 一覧の前に `invalidate_problems_cache()` を呼んでいるので、キャッシュ命中で SQL が出ない形の見かけの合格にはならない。
  - クイズの開始・取得・回答は 1 つの `with` に入っているので、3 つの経路が同じ検査を受ける。
  - 確認の限界: 注入の実機確認はしていない。`Problem` の一覧のキャッシュ作りの実装も読んでいないので、キャッシュ無効化が全科目を対象にするかは未確認。
- 仮説 2: TC-04 の 304 が、中身を読んだうえで返っている。
  - 結論: 返せない。`views.py:775-776` は `visible_media_asset` が `.only('id','mime_type','checksum_sha256')` で取ったメタデータだけで判定する。`media_asset_data` は 304 の枝では呼ばれない。
  - テストは 2 回目のリクエストだけを `CaptureQueriesContext` で囲み、`content_sqls == []` を確かめている。304 の前に中身を読む実装にすると落ちる。
- 仮説 3: 弱い ETag（`W/`）が一致になる。
  - 結論: ならない。`_if_none_match_hits` は文字列の完全一致（`etag in candidates`）で、`W/"…"` は不一致になる。
  - TC-04 は `W/` 付きで 200 になること、複数の値の中の強い一致と `*` で 304 になること、`checksum` が null のとき ETag を付けずに 200 になることまで確かめている。
  - 弱い一致を許す実装に変えると `W/` の assert が落ちる。

> ITEM: V3 RESULT=read
> ITEM: V6 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I587] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。探索した仮説は次の 3 つ。

1. **TC-12〜TC-14 の網羅と共通関数**
   - TC-12 は `MigrationLoader` で本物の 0025 を apply／unapply している。
   - 0025 の `forward` と TC-13・TC-14 の `run_move` は、どちらも同じ `move_media_files_to_db` を通る。
   - TC-12 でファイルのある行と無い行を、TC-13 で済みの行を、TC-14 で checksum 不一致・画像でない・置き場の外のキーを見ている。5 つの場合が揃っている。
   - 消す順は `links.delete()` の後に `asset.delete()` で、`RESTRICT` の紐づけを先に消している。
   - 置き場の外のキーは、`is_file` の判定より前に `_resolve_inside` が止める。
   - `MediaAsset` を指す外部キーは `ProblemMediaAsset` と `MediaAssetContent` だけだった（grep で確認）。消し漏れは無い。
2. **ファイル・`/media/` の残り**
   - `MEDIA_ROOT`・`MEDIA_URL`・`/media/`・`StorageService` を backend の `.py` で grep した。残りは移行用の `LEGACY_MEDIA_ROOT`、コメント、テストだけだった。
   - 旧の `question_image` 系・`get_*_image_url`・`image_directory` は、migrations とテストの外に無い。
   - `upload_image` は `_save_image_as_asset` を `transaction.atomic()` の中で通る。
   - `delete_image` は `_discard_asset` を通る。共有の判定は `is_deleted=False` の紐づけだけで行っている。
3. **配信の境界のエッジケース**
   - 304 は中身を読む前に返り、弱い ETag は一致にしない。`checksum` が空なら ETag を付けない。
   - 304 の経路では中身の行の有無を確かめないが、組織の境界は先に確かめている。Low 以下で、指摘にはしない。

> ITEM: V4 RESULT=read
> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: d57c7718b4f027692cb2ade8fe8511d9d8470211
ROUNDS: 1
VERDICT: OK
