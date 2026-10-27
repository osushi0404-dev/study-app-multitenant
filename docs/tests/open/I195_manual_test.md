# I195 手動テスト: Claude で確かめられる手動テストを人に振らない仕組みを固める

本物の tmux と claude で、`tui-capture.sh` が対話画面を読めること・承認画面なしで通ること・止める入力を止めること・セッションを残さないことを確かめる。中の claude には Enter を送らない（何も実行させない・費用をかけない）。

| No | 手順 | 期待結果 | 実施環境 | 実施者 | 実結果 | 備考 |
|---:|------|----------|----------|--------|--------|------|
| 1 | `bash scripts/claude/tui-capture.sh '/plan-'` と `bash scripts/claude/tui-capture.sh '/imp'` を流す | どちらも exit 0。`/plan-` の画面に `/plan-issue` と `/issue-bootstrap` の候補の行があり、下の行に `manual mode on` がある。`/imp` の画面に `/implement` の候補の行が無い（I193 の No.5 と同じ確かめ方） | 対話画面の判定 | Claude |  | AC1。I193 の No.5 をこのスクリプトで再現する |
| 2 | `bash scripts/claude/check-permission-prompt.sh bash "bash scripts/claude/tui-capture.sh '/plan-'"` | exit 0（承認画面なし） | claude -p の判定 | Claude |  | AC1。`.claude/settings.json` を変えずに通る（承認なしで通ると実際に実行されるが、画面を読んで閉じるだけで困らない） |
| 3 | `bash scripts/claude/tui-capture.sh '!ls'` を流し、続けて No.1 の後と合わせて `tmux ls` を流す | `!ls` は exit 2 で、何も起動しない。`tmux ls` の出力に `tui-capture-` で始まるセッションが無い（サーバーが無い旨の表示でもよい） | このセッション | Claude |  | AC1。止める入力・後始末。`tmux ls` は読むだけのコマンドだが、許可（allow）に無いので承認画面が出うる（広い許可は足さない方針。出たら「許可」を選ぶ。後始末は自動テスト TC-01 の T1・T6 で決定論に固定済みで、ここは本物での念押し） |
| 4 | `bash scripts/claude/check-manual-test-executor.sh I195` | exit 0（このイシューの手動テストに Human の行が無い） | このセッション | Claude |  | AC4。新しい判定がこの文書を通す |

結論: OK / NG
