# I228 手動テスト: 敵対的レビューの確認済みの引き継ぎ・空振りした実験の扱い

| No | 手順 | 期待結果 | 実施者 | 実施環境 | 実結果 | 備考 |
|---:|------|----------|--------|----------|--------|------|
| 1 | `bash scripts/claude/check-permission-prompt.sh bash 'docker compose exec -T backend python -m pytest --version'` を実行する（通常モード・このブランチの `.claude/settings.json` だけを読ませた新しいセッション。実験役は auto モードで、通常モードで承認なしなら auto でも承認なし） | 終了コード 0（承認画面が出ずに実行された）。出力の先頭が見張りのブロックの形（`PreToolUse:`）でない。コンテナが止まっていてコマンド自体が失敗しても、承認の判定には関係しない | Claude | claude -p の判定 | OK | AC2。2026-11-13 実施: exit 0「承認なしで実行された」（出力の先頭: Exit code 1 service "backend" is not running。コンテナは止まっていたが承認の判定には関係しない） |
| 2 | `docs/runbooks/plan-writing-rules.md`・`.claude/agents/plan-reviewer.md`・`docs/runbooks/review-rules.md`・`.claude/skills/review-gate/SKILL.md`・`.claude/agents/adversarial-reviewer.md` を Read で読み、追加した文を確かめる。文の中のファイルのパスを `test -f` で確かめる | plan-writing-rules に節「高リスクの計画の「必ず確かめる項目」（I228）」があり、失敗注入・表と外部の正の突き合わせを実験必須にしない決まりが書かれている。plan-reviewer の P4 に、実験必須の項目に決定論で覆える性質が無いかの行がある。review-rules・review-gate に引き継ぎの 1 文、review-gate §3-1 にコンテナを起こす手順、adversarial-reviewer に `docker compose exec -T backend` の案内がある。参照先のパスはすべて実在する | Claude | ― | OK | AC3・AC2。2026-11-13 実施: 追加した文をすべて確認・参照先 5 件は test -f で実在 |
| 3 | `bash scripts/claude/check-permission-prompt.sh bash 'docker compose up --help'`（review-gate §3-1 の `docker compose up -d backend` と同じ allow の規則 `Bash(docker compose up *)` に当たり、副作用の無い代わりの操作。本物を流すとハーネスのワークツリーでコンテナが立ち上がるため） | 終了コード 0（承認なしで実行される） | Claude | claude -p の判定 | OK | 2026-11-13 1 回目: §3-1 が `docker compose ps --status running --services` だったときは exit 10（承認画面が出る・NG）→ fix-loop で `up -d backend` だけにした。2 回目: exit 0「承認なしで実行された」 |

結論: OK（No.3 は fix-loop の後に OK）
