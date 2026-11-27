# I639 手動テスト: イシューのコメントを流れの入力に入れ、計画の「別イシュー」の番号を確かめる

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | ユーザーが `! bash scripts/claude/issue-source.sh body I547` を流す（このブランチでは入口が 75 で止まるため）。出力は Claude が読んで判定する | 本文の後ろに `## GitHub のコメント（12 件・読んだ時点 …・同期しない）` があり、`### <日時> @osushi0404-claude（CONTRIBUTOR）` の見出しが 12 個、中身が `> ` の引用で出る。続けて `! bash scripts/claude/issue-source.sh body I645`（コメントの無いイシュー。test-gate の時点で 0 件かを `gh issue view 645 --json comments` で先に確かめ、あれば 0 件のイシューに替える）の出力に `## GitHub のコメント` が無い | Human |  | 試した手段: Bash ツールからの起動役（このブランチは `issue-source.sh` を変えるので 75 で止まり `!` を案内する・I615）・サンドボックスの中で直接流す（gh が App の鍵を読めない）。実物の GitHub のコメントの形を確かめられるのは `!` で流した出力だけ |
| 2 | Claude が `bash scripts/claude/check-plan-followups.sh I466` を流す | exit 1。出力に `docs/plans/closed/plan_I466.md:165: ` と、表の削除を別イシューにする行がある | Claude |  | 実物の記録での取りこぼしの再現 |

結論: OK / NG
