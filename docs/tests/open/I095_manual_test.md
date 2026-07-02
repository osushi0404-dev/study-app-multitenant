# I095 手動テスト: 別 worktree 配下への編集ハードブロック

PreToolUse フックは**セッション開始時点で settings.json に登録済み**（push ガード等で既存）かつフック本体は毎回フレッシュに実行されるため、**Bash / Edit / Write については稼働中セッションでも I095 ロジックが有効**であり in-session で確認できる（下記 TC-M2b/M4/M5 は Claude が稼働中セッションで確認済み・実ブロックをライブ観測）。一方、**settings.json のマッチャ拡張（`MultiEdit`/`NotebookEdit` の発火）は新規セッションでの再ロードが必要**なため、その分と**逆方向**は `プレーン default 新規セッション`（Human）で確認する。

| No | 手順 | 期待結果 | 実施環境 | 実施者 | 実結果 | 備考 |
|---:|------|----------|----------|--------|--------|------|
| 1 | `wt-harness` のプレーン default 新規セッションで、`Edit` を別 worktree の絶対パス（例 `/mnt/c/app/study-app-multitenant/README.md`）に対して実行する | フックが `[guard]` メッセージ付きで操作をブロックし、ファイルは変更されない（`study-app-multitenant/README.md` の mtime・内容が不変） | プレーン default 新規セッション | Human | | TC-M1 |
| 2a | 別 worktree 宛に `MultiEdit` と `NotebookEdit`（notebook_path=別worktree）を実行する | いずれもブロックされ、別 worktree にファイルが作成・変更されない（マッチャ拡張＝R4 の発火確認） | プレーン default 新規セッション | Human | | TC-M2a（要新規セッション：マッチャ再ロード） |
| 2b | 別 worktree 宛に `Bash` 書込（`echo x > /mnt/c/app/study-app-multitenant/...`）を実行する | `[guard]` メッセージ付きでブロックされ、書込されない | 稼働中セッションでも可 | Claude | OK | 稼働中セッションでライブ確認：`echo probe > /mnt/c/app/study-app-multitenant/__i095_nonexistent__/x.txt` → `[guard] 別 worktree ... へのBash 書込は禁止` exit 2・書込なし（2026-07-02） |
| 3 | 逆方向: I095 を持つ別 worktree（例 feature/I095 の使い捨て worktree）のプレーン新規セッションから `wt-harness` 配下（例 `echo x > /mnt/c/app/wt-harness/tmp_probe.txt`）を書込する | `[guard]` でブロックされ、`wt-harness/tmp_probe.txt` が作成されない（`ls` で不在）＝双方向に効く | プレーン default 新規セッション | Human | | TC-M3（primary は develop 未マージのため I095 未搭載。I095 を持つ worktree から確認） |
| 4 | 別 worktree 配下を `Read`/`cat`/`grep` で読み取る | 読み取りは成功する（横断書込のみ禁止・§9 の趣旨） | 稼働中セッションでも可 | Claude | OK | 稼働中セッションで `cat /mnt/c/app/study-app-multitenant/README.md` 成功を確認（2026-07-02） |
| 5 | 現 worktree 配下の Edit/Write が誤ブロックされない | ブロックされずに成功し、ファイルが実際に作成・更新される＝誤ブロック無し | 稼働中セッションでも可 | Claude | OK | 本実装セッションで wt-harness 配下の Edit/Write（worktree.md・pretooluse_guard.py・テスト・docs 多数）が全て通過・誤ブロックなし（2026-07-02） |
| 6 | `docs/runbooks/worktree.md` §9 に技術強制済みの追記があることを確認する | §9 に `pretooluse_guard.py` による技術強制（exit 2・読み取り許可・fail-safe・エスケープ無し）の記述がある | 稼働中セッション | Claude | OK | L134 に記述確認済み（Edit/Write/MultiEdit/NotebookEdit・Bash 書込・双方向・fail-safe・エスケープ無し明記） |

結論: OK / NG
