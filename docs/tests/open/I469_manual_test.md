# I469 手動テスト: 見張りの値を取る文字の表の読み残しを直す

承認画面が出るかは、`bash scripts/claude/check-permission-prompt.sh bash '<コマンド>'`（通常モード・承認は誰も答えない・このブランチの `.claude/settings.json` を読む）で確かめる。exit 0＝承認なしで実行された・10＝承認画面が出る・2＝判定できない（もう 1 回流す）。承認画面が出る操作は自動で拒否され、実行されない。`grep *` は `.claude/settings.json` の allow にあるので、exit 10 は見張りの確認による。流す形は、もし承認なしで通っても秘密が出ない形にする（`/dev/null` を検索するので、パターンを `.env` から読んでも何も表示しない）。

| No | 手順 | 期待結果 | 実施者 | 実施環境 | 実結果 | 備考 |
|---:|------|----------|--------|----------|--------|------|
| M-01 | くっつけた形の秘密のファイルの読み出し 2 つを `check-permission-prompt.sh` で流す: `grep -f.env /dev/null`／`grep --file=.env /dev/null` | 2 つとも exit 10（承認画面が出る。直す前は 0） | Claude | claude -p の判定 | | 承認画面が出る操作は自動で拒否され、実行されない |
| M-02 | 止める対象を増やさない形を `check-permission-prompt.sh` で流す: `grep --exclude=.env x /dev/null` | exit 0（承認なしで実行された。grep 自体は一致が無く終わる） | Claude | claude -p の判定 | | 何も表示しない |
