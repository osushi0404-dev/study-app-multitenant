# I228 手動テスト: 敵対的レビューの確認済みの引き継ぎ・空振りした実験の扱い

| No | 手順 | 期待結果 | 実施者 | 実施環境 | 実結果 | 備考 |
|---:|------|----------|--------|----------|--------|------|
| 1 | `bash scripts/claude/check-permission-prompt.sh bash 'docker compose exec -T backend python -m pytest --version'` を実行する（通常モード・このブランチの `.claude/settings.json` だけを読ませた新しいセッション。実験役は auto モードで、通常モードで承認なしなら auto でも承認なし） | 終了コード 0（承認画面が出ずに実行された）。出力の先頭が見張りのブロックの形（`PreToolUse:`）でない。コンテナが止まっていてコマンド自体が失敗しても、承認の判定には関係しない | Claude | claude -p の判定 |  | AC2。2 が出たらもう 1 回流す |
| 2 | `docs/runbooks/plan-writing-rules.md`・`.claude/agents/plan-reviewer.md`・`docs/runbooks/review-rules.md`・`.claude/skills/review-gate/SKILL.md`・`.claude/agents/adversarial-reviewer.md` を Read で読み、追加した文を確かめる。文の中のファイルのパスを `test -f` で確かめる | plan-writing-rules に節「高リスクの計画の「必ず確かめる項目」（I228）」があり、失敗注入・表と外部の正の突き合わせを実験必須にしない決まりが書かれている。plan-reviewer の P4 に、実験必須の項目に決定論で覆える性質が無いかの行がある。review-rules・review-gate に引き継ぎの 1 文、review-gate §3-1 にコンテナを起こす手順、adversarial-reviewer に `docker compose exec -T backend` の案内がある。参照先のパスはすべて実在する | Claude | ― |  | AC3・AC2 |

結論: OK / NG
