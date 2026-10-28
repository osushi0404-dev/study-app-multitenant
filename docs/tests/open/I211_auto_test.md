# I211 自動テスト: ハーネスのテストの python・PyYAML・pre-commit の版を CI と手元でぴったり揃える

実行コマンド（例）: アプリのコード変更が無いため `docker compose exec backend python -m pytest`・`docker compose exec frontend npm test`・E2E は非該当（CI では今までどおり動く）

結果:
- backend: 非該当
- frontend: 非該当

## テストケース

合否はすべて終了コード（合格=exit 0・不合格=非ゼロ）。否定の判定（「合格にしない」「流さない」「拾う」）には失敗注入（FG: 写しの一覧・写しの `.python-version`／`uv.lock`・写しの `ci.yml`・偽物の `uv`）を付ける。テストは `bash scripts/claude/tests/run-all.sh <テスト>` で uv の環境で流す。

| TC | 内容 | 期待値 | 結果 |
|---|---|---|---|
| TC-01 | `bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i211_version_pin.sh`（新規。項目は下の表） | exit 0・`fail=0`。実装の前（ステップ 2 の Red）は V・X の項目が不合格 | implement（2026-10-29）: Red（直す前の check-tools.sh・run-all.sh）pass=5 fail=17（V・X・K3・K4 が不合格）→ 実装・/simplify の後、commit 18a0fb5 で pass=22 fail=0 |
| TC-02 | `bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i204_tool_sync.sh`（書き換え。項目は下の表） | exit 0・`fail=0`。実装の前（Red）は L・C の新しい項目が不合格 | implement（2026-10-29）: 実装と同時に書き換えたので、書き換えた後の形での Red は流していない（否定の項目は写しの一覧・写しの `ci.yml` を不合格にする FG で確かめている）→ 実装・/simplify の後 exit 0・fail=0 |
| TC-03 | `bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i193_official_flow.sh`（F9 が `TEST_DIR` で `run-all.sh` を流す。流し直しが入っても期待値が変わらない） | exit 0・`fail=0` | implement（2026-10-29）: exit 0・fail=0 |
| TC-04 | `bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_review_commit_lifecycle.sh`（TC-C1 が uv の環境の pre-commit で shellcheck を流す） | exit 0・`FAIL=0`・`PASS TC-C1-shellcheck` | implement（2026-10-29）: exit 0・FAIL=0 |
| TC-05 | ステップ 1 の後に `uv lock --check --project scripts/claude/tests` | exit 0（`pyproject.toml` と `uv.lock` が合っている）。TC-01 の K2 に含めて決定論ゲートで流す | implement（2026-10-29）: exit 0（`Resolved 12 packages`） |
| TC-06 | `bash scripts/claude/tests/run-all.sh`（CI の Harness Tests ジョブで確かめる。手元では全体を流し直さない） | CI の Harness Tests が pass | 実装前のため未実行 |

### TC-01 の項目（`test_i211_version_pin.sh`）
写しの一覧・`.python-version`・`uv.lock` は一時のフォルダに並べて作る（`check-tools.sh` は一覧と同じフォルダの正を読む）。`PY` は `python3 --version` から取った今の版。

| 項目 | 入力 | 期待値 |
|---|---|---|
| V1（AC3） | 一覧 `python3 \| python3 --version \| lock \| 入れ方の例`・`.python-version` = `PY` | exit 0・`OK: python3 <PY>` |
| FG-V2（AC4） | 同じ一覧・`.python-version` = `0.0.1`（今より下） | exit 1・`⛔ 版が違う道具: python3`・`入れ方: 入れ方の例` |
| FG-V3（AC4） | 同じ一覧・`.python-version` = `99.0.0`（今より上） | exit 1・`⛔ 版が違う道具: python3` |
| V4（AC3） | 一覧 `fake-tool \| echo fake-tool 1.2.3 \| lock \| x`・`uv.lock` に `[[package]]` `name = "fake-tool"` `version = "1.2.3"`（前後にほかの package を置く） | exit 0・`OK: fake-tool 1.2.3` |
| FG-V5（AC4） | 同じ一覧・`uv.lock` の版を `1.2.4` に（ほかの package の版が `1.2.3` でも当てない） | exit 1・`⛔ 版が違う道具: fake-tool` |
| FG-V6 | 同じ一覧・`uv.lock` に `fake-tool` が無い | exit 2・`⛔ 版の正が読めません` |
| FG-V7 | V1 の一覧・`.python-version` が無い | exit 2・`⛔ 版の正が読めません` |
| FG-V8 | 版の列が `3.11`（前の下限の形） | exit 2・`⛔ 一覧の行の形が違います` |
| V9（AC8） | 一覧 `quiet \| false \| - \| x`（出力が空で通らない） | exit 1・`⛔ 足りない道具: quiet`・字下げだけの行（`^    $`）が無い |
| FG-V10 | 一覧 `loud \| echo boom; false \| - \| x`（出力があって通らない） | exit 1・`    boom` の行がある（空のときだけ消したことを確かめる） |
| X1（AC1） | 一時の git リポジトリに `run-all.sh`・`check-tools.sh`（実物の写し）（`pyproject.toml` は置かない。無くても流し直すことも見る）・一覧 `bash \| bash --version \| - \| -`・印を書く `test_mark.sh` を置き、引数を記録して exit 0 する偽物の `uv` を PATH の先頭にして、`VIRTUAL_ENV` を消して `run-all.sh` を流す | exit 0・偽物の `uv` の引数がちょうど `run --locked --project scripts/claude/tests bash scripts/claude/tests/run-all.sh`・印のファイルが無い（外側では流さない） |
| X2（AC1） | X1 と同じで、引数 `t/test_mark.sh` を付けて流す | 偽物の `uv` の引数の最後が `t/test_mark.sh`（引数をそのまま渡す） |
| FG-X3（AC1） | X1 と同じで、PATH から `uv` のあるフォルダを除き、偽物も置かない | exit 1・`⛔ uv がありません`・`テストは流していません`・印のファイルが無い |
| FG-X4 | X1 と同じで、`HARNESS_UV_REEXEC=1` を付ける（流し直した後なのに uv の環境に入れていない） | exit 1・`⛔ uv で流し直しても uv の環境に入れませんでした`・偽物の `uv` を呼んでいない |
| X5 | X1 と同じで、`VIRTUAL_ENV=<一時のリポジトリ>/scripts/claude/tests/.venv` | 偽物の `uv` を呼んでいない・印のファイルがある（uv の環境の中では流し直さない） |
| X6（D6） | 一時のリポジトリで、`VIRTUAL_ENV=<一時のリポジトリ>/scripts/claude/tests/.venv`（uv の環境の中）で、`t/test_a.sh`・`t/test_b.sh`（それぞれ印を書く）を置いて引数 `t/test_a.sh` で流す | exit 0・`test_a` の印だけある・`run-all: pass=1 fail=0` |
| FG-X7（D6） | X6 と同じで、引数 `t/test_nothing.sh`（無いファイル） | exit 1・`⛔` |
| K1（AC2） | 実物の `scripts/claude/tests/pyproject.toml`・`.python-version` | `required-version` が `==<数>.<数>.<数>`・`.python-version` が `<数>.<数>.<数>`・`requires-python` が `.python-version` と同じマイナー版の `==<数>.<数>.*` |
| K2（AC2・AC5） | `uv lock --check --offline --project scripts/claude/tests` | exit 0 |
| FG-K2 | 実物の `pyproject.toml`・`uv.lock`・`.python-version` を一時のフォルダに写し、`dependencies` から `PyYAML>=6.0` を消して `uv lock --check --offline --project <写し>` | exit 0 以外・出力に `update` |
| K3（AC2） | 実物 | `scripts/claude/tests/uv.lock`・`pyproject.toml`・`.python-version` が git で追跡されている・`scripts/claude/tests/.venv` が `.gitignore` で除かれる |
| K4（AC2） | 実物の一覧 | `python3`・`PyYAML`・`pre-commit` の版の列が `lock`・`uv` の行がある |

### TC-02 の項目（`test_i204_tool_sync.sh`。I204 からの書き換え）
| 項目 | 入力 | 期待値 |
|---|---|---|
| L1 | 実物の一覧 | `check-tools.sh` の形の確かめが通る・名前の列が `python3`・`PyYAML`・`uv`・`git`・`docker compose`・`pre-commit`・`shellcheck` の 7 つ（この順） |
| FG-L1b（I204 F5） | 写しの一覧に字下げしたコメント行（`  # x`）を足す | `names()` の結果に `# x` が入らない |
| L2（AC3） | 実物の一覧で `check-tools.sh`（uv の環境） | exit 0・`OK:` の行が一覧の行の数（7） |
| FG-L3 | 写しの一覧 `bash \| bash --version \| - \| -` と `no-such-tool-i204 \| no-such-tool-i204 --version \| - \| 入れ方の例` | exit 1・`⛔ 足りない道具: no-such-tool-i204`・`入れ方: 入れ方の例`・bash の `OK:` も出る |
| FG-L5 | 写しの一覧 `nover \| echo none \| lock \| x`・`uv.lock` に `nover` | exit 1・`⛔ 版を読めない道具: nover` |
| FG-L6a | 列が 3 つの行／版の列が `abc`／名前が空の行 | どれも exit 2・`⛔ 一覧の行の形が違います` |
| FG-R1・R2 | （I204 と同じ。写しの一覧を 4 列に・`VIRTUAL_ENV` を一時のリポジトリの `.venv` にして uv の環境の中として流す） | （I204 と同じ） |
| FG-P1・FG-P2 | （I204 と同じ） | （I204 と同じ） |
| C1（AC5） | 実物の `.github/workflows/ci.yml` | uses は `actions/checkout`・`astral-sh/setup-uv` だけ・setup-uv はちょうど 1 つで `with` が `version-file: scripts/claude/tests/pyproject.toml` だけ・install が 0 個・最後の step が `bash scripts/claude/tests/run-all.sh` → exit 0 |
| FG-C（AC5） | 写しの `ci.yml`: setup-uv に `python-version: '3.12'`／`version: 0.9.0`／`version-file` を消す／`actions/setup-python@v5` を足す／`some/setup-tool@v1` を足す | どれも不合格（exit 1） |
| FG-C（AC7） | 写しの `ci.yml` の Harness Tests に `run:` で `pip install foo`／`sudo apt-get -y install foo`／`npm i foo`／`uv pip install foo`／`python -m pip install foo`／`uv sync` | どれも不合格（exit 1） |
| C2（AC7） | `ci_check` の install の検出に `uv run --locked --project scripts/claude/tests bash x.sh`・`echo install` の `run:` を足した写し | 合格（exit 0。uv run・単なる語は install として数えない） |
| S1・FG-S2・S3 | （I204 と同じ） | （I204 と同じ） |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i211_version_pin.sh
bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i204_tool_sync.sh
bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i193_official_flow.sh
bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_review_commit_lifecycle.sh
```

## 実行記録
