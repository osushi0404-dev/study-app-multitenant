# I463 手動テスト: 見張りのオプションの値の読み方を、値を取る文字の表で直す

承認画面が出るかは、`bash scripts/claude/check-permission-prompt.sh bash '<コマンド>'`（通常モード・承認は誰も答えない・このブランチの `.claude/settings.json` を読む）で確かめる。exit 0＝承認なしで実行された・10＝承認画面が出る・2＝判定できない（もう 1 回流す）。承認なしで通る操作は実際に実行されるので、コンテナの中の操作は存在しないサービス名 `i463-no-such` で流す（見張りの判定はサービス名によらない。docker は「サービスが無い」で失敗し、何も実行されない）。`docker compose exec *` は settings.json の allow にあるので、exit 10 は見張りの確認による。

| No | 手順 | 期待結果 | 実施者 | 実施環境 | 実結果 | 備考 |
|---:|------|----------|--------|----------|--------|------|
| M-01 | 読む指定の形 2 つを `check-permission-prompt.sh` で流す: `docker compose exec -T i463-no-such pytest --cov=/app/apps`／`docker compose exec -T i463-no-such pytest --ignore=/app/apps/x` | 2 つとも exit 0（承認画面が出ない。直す前は 10） | Claude | claude -p の判定 | OK（2026-11-12・HEAD c2310be4）: 2 つとも exit 0「承認なしで実行された」・出力は `service "i463-no-such" is not running` | サービスが無いので何も実行されない |
| M-02 | 書き出し先の形を `check-permission-prompt.sh` で流す: `docker compose exec -T i463-no-such pytest --junitxml=/app/r.xml -k x` | exit 10（承認画面が出る・今までどおり） | Claude | claude -p の判定 | OK（2026-11-12・HEAD c2310be4）: exit 10「承認画面が出る」 | 承認画面が出る操作は自動で拒否され、実行されない |
