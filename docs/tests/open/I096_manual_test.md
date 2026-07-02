# I096 手動テスト: worktree lifecycle スクリプト（作成・撤去）

本イシューは通常の bash スクリプト追加であり、ハーネスの権限モード/フックの新規挙動には依存しない。したがって全 TC が**稼働中セッションの Claude で実施可能**（ファイル存在・構文チェック・runbook 追記内容の確認）。「実施環境」列は不要。
実際の作成・撤去の振る舞い（`git worktree add` / `docker compose up -d,down -v`）は自動テスト（`test_wt_lifecycle.sh`・temp repo + docker スタブ）で決定論検証するため、ここでは本番リポジトリに副作用を出す実操作は行わない。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `scripts/claude/wt-new.sh` と `scripts/claude/wt-remove.sh` が存在し実行可能ビットが立っていることを確認する | 両ファイルが存在し `-rwxr-xr-x` 等の実行権限を持つ | Claude | | |
| 2 | `bash -n scripts/claude/wt-new.sh` / `bash -n scripts/claude/wt-remove.sh` を実行する | いずれも構文エラーなし（exit 0） | Claude | | |
| 3 | `bash scripts/claude/tests/test_wt_lifecycle.sh` を実行する | 全 TC PASS（`fail=0`・exit 0） | Claude | | |
| 4 | `wt-new.sh` を引数なしで実行する | Usage を表示し exit 2（誤用で止まる） | Claude | | |
| 5 | `docs/runbooks/worktree.md` §3/§5 を確認する | `wt-new.sh` / `wt-remove.sh` の利用手順（推奨）と、手動手順が fallback として保持されていることを確認できる（`DANGER_OK=1` 前置の撤去例を含む） | Claude | | |
| 6 | `wt-remove.sh` 内に `DANGER_OK` ゲートと `git branch -r --contains HEAD`（未 push 検出）が実装されていることを Read で確認する | `docker compose down -v` が `DANGER_OK=1` 分岐配下にあり、未設定時は exit 2 する記述がある | Claude | | |

結論: （実施後に記入）
