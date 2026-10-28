# I204 自動テスト: ハーネスのテストが頼る道具を CI と手元で同期する

実行コマンド（例）: アプリのコード変更が無いため `docker compose exec backend python -m pytest`・`docker compose exec frontend npm test`・E2E は非該当（CI では今までどおり動く）

結果:
- backend: 非該当
- frontend: 非該当

## テストケース

合否はすべて終了コード（合格=exit 0・不合格=非ゼロ）。否定の判定（「流さない」「当たらない」「通さない」）には失敗注入（FG: 写しの一覧・写しの `ci.yml`・偽物の `pre-commit`・前の形の写しで、対応する項目が不合格になることを確かめる）を付ける。

| TC | 内容 | 期待値 | 結果 |
|---|---|---|---|
| TC-01 | `bash scripts/claude/tests/test_i204_tool_sync.sh`（新規。項目は下の表） | exit 0・`fail=0`。ステップ 3 の前（4.5・4.6 の前）は S1 が `test_compose_ports.sh`・`guard_bash_oracle.py` に当たって不合格 | 実装前のため未実行 |
| TC-02 | `bash scripts/claude/tests/test_review_commit_lifecycle.sh`（TC-C1 の書き換え） | exit 0・`FAIL=0`・出力に `SKIP` の行が無く `PASS TC-C1-shellcheck` がある（ベースライン PASS=30 SKIP=1 → PASS=31） | 実装前のため未実行 |
| TC-03 | `bash scripts/claude/tests/test_compose_ports.sh`（SKIP の分岐を消す） | exit 0・`pass=13 fail=0`（ベースラインと同じ） | 実装前のため未実行 |
| TC-04 | `bash scripts/claude/tests/test_guard_bash_oracle.sh`（`guard_bash_oracle.py` の SKIP を消す） | exit 0・`見逃し=0 余計な停止=0`（ベースラインと同じ） | 実装前のため未実行 |
| TC-05 | `bash scripts/claude/tests/test_i193_official_flow.sh`（F9 が `TEST_DIR` で `run-all.sh` を流す。冒頭の確認が入っても期待値が変わらない） | exit 0・`fail=0` | 実装前のため未実行 |
| TC-06 | `bash scripts/claude/tests/run-all.sh`（CI の Harness Tests ジョブで確かめる。手元では流し直さない） | CI の Harness Tests が pass | 実装前のため未実行 |

### TC-01 の項目（`test_i204_tool_sync.sh`）
写しの一覧・写しの `ci.yml` は一時のフォルダに作る。規則の文字列と写しは分けた文字列をつないで作る（テストの行が規則に当たらないように。除外の印は作らない）。

| 項目 | 入力 | 期待値 |
|---|---|---|
| L1（AC1） | 実物の `scripts/claude/tests/required-tools.txt` | 形が正しい（`check-tools.sh --pip-specs` が exit 0）・名前の列に `python3`・`PyYAML`・`git`・`docker compose`・`pre-commit`・`shellcheck` の 6 つがちょうどある |
| L2（AC2） | 実物の一覧で `check-tools.sh` | exit 0・`OK:` の行が 6 つ |
| FG-L3（AC2） | 写しの一覧に `no-such-tool-i204 \| no-such-tool-i204 --version \| - \| - \| 入れ方の例` を足す | exit 1・出力に `⛔ 足りない道具: no-such-tool-i204` と `入れ方: 入れ方の例`。ほかの行の `OK:` も出る（全部確かめてから返す） |
| FG-L4（AC4） | 写しの一覧の python3 の下限を `99.0` にする | exit 1・出力に `⛔ 版が古い道具: python3` |
| FG-L5 | 写しの一覧に、下限 `1.0` で数字を出さないコマンド（`echo none`）の行 | exit 1・出力に `⛔ 版を読めない道具` |
| FG-L6a | 写しの一覧に列が 4 つの行／下限が `abc` の行 | どちらも exit 2・出力に `⛔ 一覧の行の形が違います` |
| FG-L6b | 写しの一覧の pip の列を `--extra-index-url=http://example.invalid`／`PyYAML @ https://example.invalid/x.whl`／`-e git+https://example.invalid/x` にする | どれも `check-tools.sh --pip-specs` が exit 2・stdout が空 |
| L7（AC6） | 実物の一覧で `check-tools.sh --pip-specs` | exit 0・stdout がちょうど `PyYAML>=6.0` と `pre-commit>=4.0` の 2 行（この順） |
| FG-R1（AC2） | 一時の git リポジトリに `run-all.sh`・`check-tools.sh`（実物の写し）と、FG-L3 の行だけの一覧を置き、`TEST_DIR` に印のファイルを書くだけの `test_mark.sh` を置いて `run-all.sh` を流す | exit 1・印のファイルが無い（テストを流していない）・出力に `⛔ 足りない道具: no-such-tool-i204` と `テストは流していません` |
| R2 | 同じリポジトリで、一覧を `bash \| bash --version \| - \| - \| -` の 1 行にする | exit 0・印のファイルがある |
| FG-P1（AC2・AC3） | PATH の先頭に偽物の `pre-commit`（exit 127）を置いて `test_review_commit_lifecycle.sh` | exit 0 以外・出力に `FAIL TC-C1-shellcheck`・`SKIP` の行が無い |
| FG-P2（AC5） | 偽物の `pre-commit` が `shellcheck...(no files to check)Skipped` を出して exit 0 | exit 0 以外・出力に `FAIL TC-C1-shellcheck` |
| C1（AC6） | 実物の `.github/workflows/ci.yml` と一覧 | Harness Tests（`harness-tests`）の `python-version` が一覧の python3 の下限（`3.11`）と同じ・一覧を読む step がある・ほかの install と `uses:`（`actions/checkout`・`actions/setup-python` 以外）が無い・最後の step が `bash scripts/claude/tests/run-all.sh` → exit 0 |
| FG-C2 | 写しの `ci.yml` の `python-version` を `'3.12'` にする | 不合格（exit 1） |
| FG-C3 | 写しの `ci.yml` の Harness Tests に `run: pip install foo` の step を足す | 不合格 |
| FG-C4 | 写しの `ci.yml` の Harness Tests に `uses: some/setup-tool@v1` の step を足す | 不合格 |
| FG-C5 | 写しの `ci.yml` の一覧を読む step を前の `run: pip install pyyaml` に戻す | 不合格 |
| S1（AC3） | 実物: `scripts/claude/tests/` の `*.sh`・`*.py` | 当たり無し（exit 0）・見たファイルが 40 本以上 |
| FG-S2 | 写し: 前の TC-C1 の形（`if command -v shellcheck …; then … else printf 'SKIP …'`）・前の `test_compose_ports.sh` の形（`if ! command -v docker …; then echo "SKIP: …"; exit 0`）・前の `guard_bash_oracle.py` の形（`if not shutil.which("bash"): print("SKIP: …")`） | 3 つとも当たる（exit 1） |
| S3 | 写し: `BASH_BIN="$(command -v bash)"` の行の 10 行後に `SKIP`・`echo "SKIP NOREG（origin/develop を取得できない環境）"`（道具を探す行が無い） | 当たらない（exit 0） |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i204_tool_sync.sh
bash scripts/claude/tests/test_review_commit_lifecycle.sh
bash scripts/claude/tests/test_compose_ports.sh
bash scripts/claude/tests/test_guard_bash_oracle.sh
bash scripts/claude/tests/test_i193_official_flow.sh
```

## 実行記録
