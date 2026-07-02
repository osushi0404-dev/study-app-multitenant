# I095 手動テスト: 別 worktree 配下への編集ハードブロック

ハーネスの**フック（hook）ロード／権限モード**に依存する挙動（実セッションで exit 2 が実際に Edit/Bash をブロックするか・マッチャ拡張後に MultiEdit/NotebookEdit で発火するか）は稼働中セッションの Claude 実行では検証にならないため、「実施環境」列を追加し `プレーン default 新規セッション` で目視確認する。

| No | 手順 | 期待結果 | 実施環境 | 実施者 | 実結果 | 備考 |
|---:|------|----------|----------|--------|--------|------|
| 1 | `wt-harness` のプレーン default 新規セッションで、`Edit` を別 worktree の絶対パス（例 `/mnt/c/app/study-app-multitenant/README.md`）に対して実行する | フックが `[guard]` メッセージ付きで操作をブロックし、ファイルは変更されない（`study-app-multitenant/README.md` の mtime・内容が不変） | プレーン default 新規セッション | Human | | TC-M1 |
| 2 | 同セッションで `MultiEdit` と `NotebookEdit`（notebook_path=別worktree）、および `Bash` の `echo x > /mnt/c/app/study-app-multitenant/tmp_probe.txt` を別 worktree 宛に実行する | いずれもブロックされ、別 worktree にファイルが作成・変更されない（`ls` で不在確認） | プレーン default 新規セッション | Human | | TC-M2（マッチャ拡張＝R4／エスケープ無し確認） |
| 3 | 逆方向: `study-app-multitenant`（primary）のプレーン新規セッションから `wt-harness` 配下（例 `/mnt/c/app/wt-harness/README.md`）を `Edit`／`echo x > /mnt/c/app/wt-harness/tmp_probe.txt` で書込する | いずれも `[guard]` メッセージ付きでブロックされ、`wt-harness/README.md` の内容・mtime が不変、`wt-harness/tmp_probe.txt` が作成されない（`ls` で不在確認）＝双方向に効く | プレーン default 新規セッション | Human | | TC-M3 |
| 4 | 同セッションで別 worktree 配下を `Read`/`cat`/`grep` で読み取る | 読み取りは成功する（横断書込のみ禁止・§9 の趣旨） | プレーン default 新規セッション | Human | | TC-M4 |
| 5 | 現 worktree 配下の通常の Edit/Write（例 現 worktree の一時ファイル）と `echo x > ./tmp_probe.txt` を行う | ブロックされずに成功し、対象ファイルが実際に作成・更新される（`cat`/`ls` で内容・mtime 変化を確認）＝誤ブロック無し | プレーン default 新規セッション | Human | | TC-M5 |
| 6 | `docs/runbooks/worktree.md` §9 に技術強制済みの追記があることを確認する | §9 に `pretooluse_guard.py` による技術強制（exit 2・読み取り許可・fail-safe・エスケープ無し）の記述がある | 稼働中セッション | Claude | | ファイル確認で可 |

結論: OK / NG
