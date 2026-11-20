# I597 手動テスト: DB の控えの入口を Claude から流せる形で直す

前提: このワークツリー（harness-1）の開発の DB が動いている（`docker compose up -d --wait db`。計画のスパイクで起動済み）。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | Claude の Bash ツールで `bash scripts/claude/db-backup.sh I597_check` を単体で流す。できたファイルを `ls -l`・`grep -cx -- '-- PostgreSQL database dump complete'`・最後の空でない行・`git status --short` で見る | 終了コード 0。`✅ 控えを取りました: backup_I597_check_<日時>.sql（<数> バイト）` が出る。ファイルは 0 バイトでなく（権限は `/mnt/c` の drvfs では `-rwxrwxrwx` になる・計画 R6。600 は TC-01 が Linux のファイルシステムで確かめる）、完了の行が 1 行、最後の空でない行が先頭の `\restrict <鍵>` と同じ鍵の `\unrestrict <鍵>`。`backup_partial_*` は無い。`git status --short` に控えのファイルが出ない。確かめた後、作った控えを消す | Claude |  | 受け入れ条件 1・6（I590 と同じコマンドがワークツリーの DB で動く） |
| 2 | Claude の Bash ツール（サンドボックスの中）で `bash scripts/db_backup.sh` を流す。前後で作業フォルダの `backup_*.sql` の数を比べる | 終了コードが 0 でない。標準エラーに止まった理由と、入口 `bash scripts/claude/db-backup.sh` の案内が出る。`backup_*.sql`・`backup_partial_*` の数が増えない | Claude |  | 受け入れ条件 4（人の道具を Claude から流したとき） |
| 3 | 終わったら `docker compose stop db` で、このワークツリーの DB を止める | `docker compose ps --format "{{.Service}} {{.State}}"` に db が出ない（データのボリュームは消さない） | Claude |  | 後片付け |

## 画面確認
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
|  |  | 理由: 画面の変更なし（frontend/src を変えない） |  |  |  |  |

結論: OK / NG
