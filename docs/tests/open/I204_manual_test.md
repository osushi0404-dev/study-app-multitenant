# I204 手動テスト: ハーネスのテストが頼る道具を CI と手元で同期する

CI の runner での実際の動き（AC5・AC7）と、手元の実物の一覧での止まり方（AC2）を、test-gate で Claude が確かめる。どれも `gh` とコマンドの実行・出力の確認だけで、画面・承認画面は関係しない。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | PR #354 の最新の CI の Harness Tests のログを `gh run view <run の番号> --log --job <Harness Tests のジョブの番号>` で読む | ジョブが success。「Install test dependencies」に `PyYAML` と `pre-commit` を入れた行（`Successfully installed` に両方の名前）。「Run harness tests」に `OK: python3 3.11.`・`OK: PyYAML`・`OK: git`・`OK: docker compose`・`OK: pre-commit`・`OK: shellcheck` の 6 行と `run-all: pass=… fail=0` | Claude |  | AC5・AC7。ステップ 1 の未知リスク（runner で pre-commit が shellcheck を入れられるか） |
| 2 | スクラッチパッドに、`exit 1` だけをする実行できる `docker` を置いたフォルダを作り、そのフォルダを PATH の先頭にして `bash scripts/claude/tests/run-all.sh` を流す | 数秒で終わり exit 1。出力に `⛔ 足りない道具: docker compose（`docker compose version` が通らない）。入れ方: Docker Desktop の WSL 連携を有効にする…` と `テストは流していません`。`FAIL scripts/claude/tests/test_` の行も `run-all: pass=` の行も出ない | Claude |  | AC2 を実物の一覧で |
| 3 | `bash scripts/claude/tests/check-tools.sh` を流す | exit 0。`OK: python3 3.12.3`・`OK: PyYAML 6.0.1`・`OK: git`・`OK: docker compose`・`OK: pre-commit 4.5.1`・`OK: shellcheck` の 6 行 | Claude |  | AC1・AC4（手元が下限を満たす） |

結論:
