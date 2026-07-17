# I117 手動テスト: auto_test テンプレートの実行コマンド例示を決定論ゲートセクションへ一本化

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `docs/tests/templates/auto_test_template.md` を Read で開き、冒頭部を確認する | 「実行コマンド（例）:」が `docker compose exec backend python manage.py test` / `docker compose exec frontend npm test` のインラインコード表記になっており、fenced の bash ブロックが冒頭に存在しない。直前に誘導注記（HTML コメント）があり「ゲート系コマンドは『## 決定論ゲート（自動実走）』セクションに書く・セクション外に書くと omission-lint が HIGH」の旨が読める | Claude | OK | 2026-07-18 実施。l.12-18 誘導注記・l.19 インライン表記を確認。冒頭に fenced なし |
| 2 | 同ファイルの「## 決定論ゲート（自動実走）」セクションを確認する | セクション内コメントの allowlist 列挙が omission-lint の検知対象と一致する表記（`bash scripts/claude/tests/*.sh`・`grep -q`（存在）・`grep -L`（不在ファイル一覧）・`! grep -q`（不在）・`python3 -m json.tool`・`bash -n`・`python3 -m py_compile`）になっており、冒頭側に同列挙の複製が無い | Claude | OK | 2026-07-18 実施。l.29-30 に `grep -L 文言 dir/*`（不在ファイル一覧）を含む全列挙を確認。冒頭側の複製なし |
| 3 | 変更後テンプレの冒頭注記を通読する | 注記の文言が平易で、「どこに何を書けばよいか」がテンプレ利用者の視点で誤解なく読める（表現の分かりにくさがあれば NG として指摘） | Human | OK | 2026-07-18 ユーザー確認済み |

結論: OK
