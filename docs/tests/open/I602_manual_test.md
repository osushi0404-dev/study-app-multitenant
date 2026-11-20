# I602 手動テスト: I590 のレビューの残り（テストの守りの抜け・0027 の戻し方・補助の集約）

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | PR #603 の最新の CI（backend の pytest）のログを `gh run view --log` で読み、3 つのテストのファイルの結果を見る | `test_I590_review_leftovers.py`・`test_I587_media_migration.py`・`test_I492_remove_legacy_study_logs.py` の行がすべて PASSED で、FAILED・ERROR が 0 | Claude |  |  |
| 2 | `docs/runbooks/backend-check.md` の新しい節の空にする SQL と、`test_I590_review_leftovers.py` の `CLEAR_IMAGE_DIRECTORY_SQL` を Read で並べて読む | 2 つの SQL の文が同じ（`UPDATE problems_subject SET image_directory = '' WHERE image_directory <> ''`）。節に「控え（`db-backup.sh`）→ 値の確かめ → 空にする（人の承認）→ `migrate problems`」の順が書いてある | Claude |  |  |

## 画面確認
<!-- frontend/src を変えないので画面確認は無い -->
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
|  |  | 理由: frontend/src を変えない |  |  |  |  |

結論: OK / NG
