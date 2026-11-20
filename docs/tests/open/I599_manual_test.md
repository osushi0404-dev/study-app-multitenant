# I599 手動テスト: サンドボックスの中から scripts/claude/ に書いたスクリプトをレビュー前に外で流せる穴を塞ぐ

このセッションは起動時の設定（フックが作業ツリーの見張りを直接動かす）のまま動くので、実装の後は新しい見張りで動く。子のセッションは `bash scripts/claude/test-session.sh` で起こし、このブランチの `.claude/settings.json`（起動役を通るフック）を読む。

| No | 手順 | 期待結果 | 実施者 | 実施環境 | 実結果 | 備考 |
|---:|------|----------|--------|----------|--------|------|
| 1 | 追跡していない `scripts/claude/tmp_i599_probe.sh`（`~/.cache/i599-probe.txt` に書いて消し、書けたら `WRITE_OK`・拒否されたら `WRITE_DENIED` と出す）を置き、このセッションで `bash scripts/claude/tmp_i599_probe.sh` を単体で流す。終わったらファイルを消す | 出力の 1 行目が `[I599] レビュー前の中身があるので、サンドボックスの中で動かします（届いた変更: scripts/claude/tmp_i599_probe.sh …` で、次の行が `WRITE_DENIED` | Claude | このセッション |  | V1・AC1。手順の書き換えが本物の Claude Code で中に回ることの確かめ（R1） |
| 2 | このセッションで `bash scripts/claude/issue-source.sh body I599` を単体で流す | `[I599]` の行が出ず、イシューの本文（`## 関連資料` で始まる）が出る（gh は外でしか動かないので、外で動いた証拠） | Claude | このセッション |  | AC4。`issue-source.sh` から届くファイルにこのブランチの変更が無いこと |
| 3 | `bash scripts/claude/test-session.sh "Bash で ls docs だけを流し、出力の 1 行目を答えて" --permission-mode default --max-turns 3` を流し、その後 `ls ~/.cache/claude-reviewed-hooks/` と、`git merge-base HEAD origin/develop` の値の下の `.complete` を見る | 子が `ls` の結果を答える（フックが起動役を通って動いた）。`~/.cache/claude-reviewed-hooks/<BASE>/.complete` がある | Claude | claude -p の判定 |  | V6・AC6 |
| 5 | `.claude/hooks/` を作った後、このセッションの Bash で `touch .claude/hooks/i599-probe` を単体で流す | 書き込みが拒否される（`Read-only file system` などのエラー・ファイルができない） | Claude | このセッション | OK（2026-11-20 implement: `touch: cannot touch '.claude/hooks/i599-probe': Read-only file system`。Python からの書き込みも `OSError: [Errno 30] Read-only file system`） | 計画レビュー Warning 1。書けたら計画をやり直す |
| 4 | このセッションで、見張りを JSON で直接流して時間を測る: ① `scripts/claude/` を含まないコマンド ② `bash scripts/claude/b.sh` 相当（このブランチの変更あり） ③ 起動役（変更あり・写しが既にある） | ①は今の見張りとの差が 0.1 秒未満。②③は 1 回 2 秒以下 | Claude | このセッション |  | R5 |
