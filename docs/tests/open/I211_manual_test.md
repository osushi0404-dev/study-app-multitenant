# I211 手動テスト: ハーネスのテストの python・PyYAML・pre-commit の版を CI と手元でぴったり揃える

CI の runner での実際の版（AC3）・手元の流し直し（AC1）・uv の環境の外での止まり方（AC4）・版を上げる手順（AC6）を、test-gate で Claude が確かめる。どれも `gh` とコマンドの実行・出力の確認だけで、画面・Claude Code の承認画面は関係しない（入口のコマンド `bash scripts/claude/tests/run-all.sh` は今の許可ルールのまま変わらない）。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | PR #357 の最新の CI の Harness Tests のログを `gh run view <run の番号> --log --job <Harness Tests のジョブの番号>` で読む | ジョブが success。setup-uv の step に `uv 0.13.6`（`required-version` の版）。「Run harness tests」に `OK: python3 3.11.18（正 …/.python-version）`・`OK: PyYAML <uv.lock の版>`・`OK: pre-commit <uv.lock の版>`・`OK: uv`・`OK: git`・`OK: docker compose`・`OK: shellcheck` の 7 行と `run-all: pass=… fail=0`。`actions/setup-python`・`pip install` の step が無い | Claude | | AC1・AC3・V1 |
| 2 | 手元で、スクラッチパッドに印のファイルを書くだけの `test_mark.sh` を置いたフォルダを作り、`TEST_DIR=<そのフォルダ>` で `bash scripts/claude/tests/run-all.sh` を流す（uv の環境の外から） | exit 0。`OK: python3 3.11.18`・`OK: PyYAML`・`OK: pre-commit` の版が No.1 の CI のログの版と同じ文字列。印のファイルがある。`run-all: pass=1 fail=0` | Claude | | AC1・AC3・V2（全体は流し直さない） |
| 3 | 手元で、uv の環境の外（OS の python 3.12.3）から `bash scripts/claude/tests/check-tools.sh` を直に流す | exit 1。`⛔ 版が違う道具: python3 3.12.3（正 3.11.18・…/.python-version）。入れ方: bash scripts/claude/tests/run-all.sh で流す…`。PyYAML（apt の 6.0.1）・pre-commit（pipx の 4.5.1）も `⛔ 版が違う道具` | Claude | | AC4 |
| 4 | `docs/runbooks/onboarding.md` の版を上げる手順に沿って、スクラッチパッドに写した `scripts/claude/tests/`（`pyproject.toml`・`uv.lock`・`.python-version`・`required-tools.txt`・`check-tools.sh`）で pre-commit の版を 1 つ前に下げる（`uv lock --project <写し> --upgrade-package pre-commit==<1 つ前の版>`）→ `uv run --locked --project <写し> bash <写し>/check-tools.sh` | `uv.lock` の pre-commit の版だけが変わり、`OK: pre-commit <1 つ前の版>`（uv が入れ直して正と一致）。`uv.lock` を戻さずに元の環境（実物の `.venv`）の pre-commit で写しの一覧を確かめると `⛔ 版が違う道具: pre-commit` | Claude | | AC6・V5（片方だけ上げたら止まる） |

結論:
