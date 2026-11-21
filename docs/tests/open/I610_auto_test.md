# I610 自動テスト: フックの起動役の無視されるファイル・gate-check のリンクの見逃し・run-all の中のキャッシュ

実行コマンド: 下の「決定論ゲート」。pytest・Jest・E2E は対象のコードが無いので対象外（CI の `scripts/claude/tests/run-all.sh` も同じテストを流す）

結果:
- 計画時のベースライン（2026-11-21・変更前）: `UV_CACHE_DIR="$TMPDIR/uv-cache" bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i599_unreviewed_scripts.sh scripts/claude/tests/test_i193_official_flow.sh` → pass=2 fail=0
- 実装前のため TC-01〜TC-04 は未実行

共通の準備: TC-01・TC-02 は `scripts/claude/tests/i599_cases.py` の `make_repo`（一時のリポジトリに本物の `.claude/hooks/reviewed-hook.sh`・`.claude/hooks/unreviewed.py` を写す・`.gitignore` に `*.tmp`）を使う。TC-03 は `test_i193_official_flow.sh` の `g_init` の一時のリポジトリ。失敗の注入は写しを壊して流す（本物は書き換えない）。置き換え元の文字列が本体に無いときは、テストが失敗する（`assert old in …`）

| TC | AC | 内容 | 期待（合格=exit 0） | 失敗の注入 |
|---|---|---|---|---|
| TC-01 | AC1 | TC-12b: `make_repo` のリポジトリ（変更なし）に `scripts/claude/hooks/x.tmp`（無視される）を置いてフックを起こす | 出力が `V1 <HOME>/.cache/claude-reviewed-hooks/<BASE>/scripts/claude/hooks/h.py` で始まる（写しの道）。終了コード 0 | FG-01: 4-1 (1) の条件を元の `git diff --quiet …` と `ls-files --others --exclude-standard` の 2 つに戻した写しで、出力が作業ツリーのパスになり不合格 |
| TC-02 | AC2 | TC-12c: BASE に `scripts/claude/hooks/json.py`（`print("EVIL")`）と、`import json` してから `V1` を出す `h.py` をコミットした一時のリポジトリ（変更なし＝作業ツリーの道）でフックを起こす | 標準出力に `EVIL` が無く、`V1` がある。終了コード 0 | FG-02: 作業ツリーの道の `exec python3 -I "$root/$rel"` から `-I` を外した写しで `EVIL` が出て不合格 |
| TC-03 | AC3 | G9b: `g_init` のリポジトリに未追跡の `ln -s /dev/null .bashrc`（最上位）、別に `scripts/x/.bashrc`（深い場所）を置いて `gate-check.sh` / G9c: `&& ! -L "$p"` を外した写し（リンクを印と見なす＝本物の文字デバイスの道）で最上位のリンクだけ | G9b: どちらも exit 1（汚れ）／G9c: exit 0（印は数えない道が残る） | FG-G9b: `&& ! -L "$p"` を外した写しで G9b（最上位）が 0 になり不合格／FG-G9c: 印を数えない行を消した写しで G9c が 1 になり不合格 |
| TC-04 | （R1） | `bash -n .claude/hooks/reviewed-hook.sh` | exit 0（文法の誤りが無い） | —（文法の確かめそのもの） |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i599_unreviewed_scripts.sh
bash scripts/claude/tests/test_i193_official_flow.sh
bash -n .claude/hooks/reviewed-hook.sh
```
