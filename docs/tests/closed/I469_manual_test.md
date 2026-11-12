# I469 手動テスト: 見張りの値を取る文字の表の読み残しを直す

承認画面が出るかは、`bash scripts/claude/check-permission-prompt.sh bash '<コマンド>'`（通常モード・承認は誰も答えない・このブランチの `.claude/settings.json` を読む）で確かめる。exit 0＝承認なしで実行された・10＝承認画面が出る・2＝判定できない（もう 1 回流す）。承認画面が出る操作は自動で拒否され、実行されない。`grep *` は `.claude/settings.json` の allow にあるので、作業フォルダの中のファイルを読む grep の exit 10 は見張りの確認による（M-00 で確かめる）。流す形は、もし承認なしで通っても秘密が出ない形にする（README.md を検索するので、パターンを `.env` から読んでも表示されるのは README.md の行だけ）。

test-gate での手順の訂正（2026-11-12）: 計画時は検索先を `/dev/null` にしていたが、`grep x /dev/null`（.env を含まない形）でも exit 10 になった。作業フォルダの外のファイルを読む操作には Claude Code 自体が承認を求めるためで、見張りの判定と見分けられない。検索先を作業フォルダの中の README.md に替え、基準の M-00 を足した（確かめる中身・期待は同じ）。

| No | 手順 | 期待結果 | 実施者 | 実施環境 | 実結果 | 備考 |
|---:|------|----------|--------|----------|--------|------|
| M-00 | 基準: `.env` を含まない形を `check-permission-prompt.sh` で流す: `grep i469-no-such-word README.md` | exit 0（承認なしで実行された） | Claude | claude -p の判定 | OK（2026-11-12・HEAD 4c45d443 以降の記録だけのコミット）: exit 0「承認なしで実行された」 | 作業フォルダの中の grep に承認画面が出ないことの確かめ |
| M-01 | くっつけた形の秘密のファイルの読み出し 2 つを `check-permission-prompt.sh` で流す: `grep -f.env README.md`／`grep --file=.env README.md` | 2 つとも exit 10（承認画面が出る。直す前は見張りが通していた） | Claude | claude -p の判定 | OK（2026-11-12・同上）: 2 つとも exit 10「承認画面が出る」。見張り単体でも `permissionDecision: ask`（理由「秘密情報ファイルの読み出し」） | 承認画面が出る操作は自動で拒否され、実行されない |
| M-02 | 止める対象を増やさない形を `check-permission-prompt.sh` で流す: `grep --exclude=.env i469-no-such-word README.md` | exit 0（承認なしで実行された。grep 自体は一致が無く終わる） | Claude | claude -p の判定 | OK（2026-11-12・同上）: exit 0「承認なしで実行された」・出力なし | 何も表示しない |
