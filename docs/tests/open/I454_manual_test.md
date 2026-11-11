# I454 手動テスト: 見張りの環境変数の表示の後退（ps -A e）と書き先の取りこぼしを直す

承認画面が出るかは、`bash scripts/claude/check-permission-prompt.sh bash '<コマンド>'`（通常モード・承認は誰も答えない・このブランチの `.claude/settings.json` を読む）で確かめる。exit 0＝承認なしで実行された・10＝承認画面が出る・2＝判定できない（もう 1 回流す）。承認なしで通る操作は実際に実行されるので、コンテナの中の操作は存在しないサービス名 `i454-no-such` で流す（見張りの判定はサービス名によらない。docker は「サービスが無い」で失敗し、何も実行されない）。

| No | 手順 | 期待結果 | 実施者 | 実施環境 | 実結果 | 備考 |
|---:|------|----------|--------|----------|--------|------|
| M-01 | 普通の操作 2 つを `check-permission-prompt.sh` で流す: `docker compose exec -T i454-no-such pytest -k delete`／`docker compose exec -T i454-no-such sh -c "pytest -k delete > /tmp/out.txt"` | 2 つとも exit 0（承認画面が出ない） | Claude | claude -p の判定 | | サービスが無いので何も実行されない |
| M-02 | 確認になるはずの形 3 つを `check-permission-prompt.sh` で流す: `docker compose exec -T i454-no-such ps -A e`／`docker compose exec -T i454-no-such cp -vt/app/x /tmp/y`／`docker compose exec -T i454-no-such pytest --junitxml=/app/r.xml -k x` | 3 つとも exit 10（承認画面が出る） | Claude | claude -p の判定 | | M-01 と同じ `docker compose exec` の許可（settings.json の allow）で M-01 が通るので、exit 10 は見張りの確認による。承認画面が出る操作は自動で拒否され、実行されない |
| M-03 | 見張りの行数の増減を見る（パイプなしの 1 コマンド）: `git diff --numstat origin/develop...HEAD -- scripts/claude/hooks/pretooluse_guard.py`（レビュー済みの HEAD で） | 実結果に出力の 2 つの数値をそのまま書き、1 列目（足した行）が 2 列目（消した行）以下なら OK（計画時の見込み: `60 83`・差し引き −23 前後） | Claude | — | | 増えた場合は、増えた行数と理由を計画書に書き、計画レビューで認められれば満たしたことにする（受け入れ条件） |
| M-04 | `docs/runbooks/danger-ops.md`「見張りの扱い」の 4. と `docs/runbooks/worktree.md` §9 の「技術強制済み（I095）」を、見張りの `_write_targets`・`_container_risky`・`_container_safe`・`_bash_write_targets` と突き合わせて読む | 4. の書き込みの正の関数名が `_write_targets` で、「通す形でも /tmp/ 以外への書き込みは確認」が書かれている。§9 の Bash の書き込みの代表に `mv` の移動元と `install`・`ln`・`rsync` の書き先が入り、正の関数が実物と一致する。実物より広い約束・狭い約束が無い | Claude | — | | |
