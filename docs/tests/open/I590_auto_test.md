# I590 自動テスト: I587 のレビューの残り（移行 0025 の依存・配信の 412 の見出し・`Subject.image_directory` の削除）

実行コマンド（例）: `docker compose exec -T backend pytest problems/tests/test_I590_review_leftovers.py problems/tests/test_I587_media_migration.py problems/tests/test_I587_media_in_db.py`（全体は CI が PR ごとに流す）

テストのファイル: `backend/problems/tests/test_I590_review_leftovers.py`（新規）

| TC | 内容 | 期待値 | 失敗の注入（先に落ちることの確かめ） | 結果 |
|---|---|---|---|---|
| TC-01 | `problems/media_migration.py` の読み込み（`import`・`from ... import`）を AST で集め、`problems` か `problems.` で始まるものを数える | 0 件。あわせて、同じ数え方の関数に `from problems.utils import detect_mime` を含む文字列を渡すと 1 件（数え方が効くことの確かめ） | 今のコード（`from problems.utils import ...` がある）で 1 件になり落ちる | 実装前のため未実行 |
| TC-02 | (a) `monkeypatch.setitem(problems.utils.ALLOWED_IMAGE_FORMATS, 'text/plain', ['.txt'])` の下で、文字の中身（`b"just text, not an image"`）のファイルを持つ画像の行に `move_media_files_to_db(dry_run=False)` を流す。(b) `monkeypatch.setattr(problems.utils, 'detect_mime', lambda data: 'image/png')` の下でも同じに流す | (a)(b) とも `MediaMigrationError` が出て、文に `画像ではありません` と画像の ID を含む。`MediaAssetContent` は 0 件のまま | 今のコードでは (a) は同じ辞書を読むので止まらずに通り、落ちる。(b) は今のコードでは読み込み時に束縛した関数を使うので止まる（(b) は将来 `problems.utils.detect_mime` を属性で読む形に変えたときの守り） | 実装前のため未実行 |
| TC-03 | 自分の組織の画像に対し、配信の API（`GET /api/media/<id>/`）を (a) 見出しなし (b) `If-None-Match: <最初の応答の ETag>` (c) `If-Match: "x"` で呼ぶ | 状態コードが (a) 200 (b) 304 (c) 412。3 つとも `X-Content-Type-Options == "nosniff"`・`Content-Security-Policy == "default-src 'none'; sandbox"`・`Cache-Control == "private, max-age=3600"` | 今のコードでは (b)・(c) に `X-Content-Type-Options` が無く落ちる | 実装前のため未実行 |
| TC-04 | 0027 を `MigrationExecutor` で戻して流し直す（I587 の TC-15〔`test_0026_refuses_legacy_values_then_removes_columns`〕と同じ形）。(a) 戻した後に 1 件の科目の `image_directory` を `'problems/x'` にして流す (b) `' '`（空白だけ）にして流す (c) 空に戻して流す | (a)(b) `RuntimeError`（文に `1 件` を含む）で止まり、`problems_subject` に `image_directory` の列が残る (c) 列が無くなる。戻したときは列があり、全行の値が `''` | 判定の `RunPython` を外した写しでは (a) が止まらずに列が消え、落ちる（テストの中で `operations` から判定を除いた `Migration` を作って確かめる） | 実装前のため未実行 |

既存のテスト（変えずに通ること・CI）:
- `backend/problems/tests/test_I587_media_migration.py`（0025 の移行・戻し・食い違いで止まる・管理コマンド・0026）
- `backend/problems/tests/test_I587_media_in_db.py`（配信・2 つの action のエラーの形・論理削除の紐づけ）

結果:
- backend: 実装前のため未実行
- frontend: 変更なし
- 決定論ゲート（2026-11-20・計画の時点）: `media_migration.py`・`views.py` の py_compile は exit 0。`test_I590_review_leftovers.py` は実装前のため未実行

## 決定論ゲート（自動実走）
```bash
python3 -m py_compile backend/problems/media_migration.py
python3 -m py_compile backend/problems/views.py
python3 -m py_compile backend/problems/tests/test_I590_review_leftovers.py
```
