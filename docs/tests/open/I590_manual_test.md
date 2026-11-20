# I590 手動テスト: I587 のレビューの残り（移行 0025 の依存・配信の 412 の見出し・`Subject.image_directory` の削除）

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M1 | 開発の DB（app-1）で、科目の数と `image_directory` に値のある科目の数を読むだけで数える（`docker compose exec -T backend python manage.py shell -c` で `Subject.objects.count()` と `Subject.objects.exclude(image_directory='').count()`） | 2 つの数が出る（2026-11-20 の grill-me の時点では 11 と 0）。数をレビュー文書に書く | Claude | OK（2026-11-20）: 科目 11・値のある科目 0 | 計画 5 のステップ 1 |
| M2 | #597 で作る控えの入口（`scripts/claude/` のスクリプト）で開発の DB の控えを取る | `backup_*.sql` ができ、大きさが 0 より大きい。ファイル名と大きさをレビュー文書に書く | Claude | OK（2026-11-20）: `bash scripts/claude/db-backup.sh I590_before` → `backup_I590_before_20261120_161736.sql`（160768 バイト・入口が完了の行を確かめ済み） | 計画 5 のステップ 1。この後、ユーザーの承認を得るまで 0027 を書かない |
| M3 | `docker compose exec -T backend python manage.py migrate problems` を流し、`showmigrations problems` と列の一覧（`connection.introspection.get_table_description` で `problems_subject`）を見る | `Applying problems.0027_remove_subject_image_directory... OK` が出る。`[X] 0027_remove_subject_image_directory`。`problems_subject` の列に `image_directory` が無い | Claude |  | 計画 5 のステップ 4 |

## 画面確認
画面（`frontend/src`）を変えないので無い。理由: バックエンドだけの変更（配信の見出し・移行・列）で、画面の表示は変わらない。

結論: OK / NG
