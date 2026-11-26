# I593 自動テスト: 判定の仕組みを変える PR を変更前の版で審査する

実行コマンド（例）: `bash scripts/claude/tests/test_i593_review_from_base.sh`（ハーネスのテストは CI の Harness Tests〔`scripts/claude/tests/run-all.sh`〕が流す。アプリのテストは変えない）

結果:
- backend: 変更なし（CI）
- frontend: 変更なし（CI）
- harness: 実装前のため未実行

## テストケース
すべて `scripts/claude/tests/test_i593_review_from_base.sh` の中（一時の git リポジトリ・写しのダミー・`CLAUDE_BIN` の差し替えを使い、本物のファイルを書き換えない）。合否は終了コード（合格=0）。各 TC の FG は、判定を外した写し・壊した入力で流し、その TC が不合格になることを確かめる。

| TC | AC | 内容 | 期待値 | FG（失敗の注入） |
|---|---|---|---|---|
| TC-01 | AC3 | `path_risk_trigger` に `.claude/hooks/unreviewed.py`・`.claude/skills/review-gate/SKILL.md`・`.claude/skills/test-gate/SKILL.md`・`.claude/skills/fix-loop/SKILL.md`・`.claude/skills/plan-review/SKILL.md`・`scripts/claude/gate-check.sh` を 1 つずつ渡す／`.claude/skills/retro/SKILL.md`・`.claude/skills/review-gate-x/SKILL.md`・`scripts/claude/code-review.sh`・`.claude/agents/code-reviewer.md` を渡す | 前者はすべて `YES`、後者はすべて `NO` | `review_mechanism_trigger` の case から 1 パターンずつ消した写しで、そのパスが `NO` になり TC が落ちる |
| TC-02 | AC6 | `guard_path_trigger` の集合が今の集合（`.github/*`・`.pre-commit-config.yaml`・`.secrets.baseline`・`scripts/claude/hooks/pretooluse_guard.py`・`.claude/settings.json`・`.claude/settings.local.json`）のまま、変更の種類 `guard`・`docs/runbooks/workflow.md` の止めて聞く条件 2 と一致する。`review_mechanism_trigger` の集合が `.claude/agents/code-reviewer.md`・`.claude/agents/plan-reviewer.md`・`docs/runbooks/review-rules.md` の高リスクの集合の行と一致する（既存の `test_i181_review_slim.sh`・`test_i193_official_flow.sh` S12・`test_i205_stop_criteria.sh` K2 を新しい関数に合わせて直す） | すべて一致で exit 0 | 説明の 1 つから 1 パスを消した写しで不一致になり落ちる |
| TC-03 | AC1 | `reviewer_agent_args code-reviewer <一時>` を、写しのダミー（`.complete` あり・定義の本文に `docs/runbooks/review-rules.md` を含む）から呼ぶ | `agents.json` が JSON として読め、`code-reviewer.prompt` が写しの本文（作業ツリーの本文と違う目印）で、参照が `<写し>/docs/runbooks/review-rules.md` に置き換わる。`tools` が `["Read","Grep","Glob"]`。`REVIEWER_ARGS` が `--agents <ファイル> --agent code-reviewer --add-dir <写し>` | 前書きに未知の鍵（`permissionMode: x`）・前書きの崩れ・定義なしのそれぞれで非 0 になる（なければ落ちる） |
| TC-04 | AC1 | 審査の入口 5 本（`code-review.sh`・`adversarial-review.sh`・`plan-issue-review.sh`・`issue-review.sh`・`fix-review-lib.sh`）が、レビュー役を `REVIEWER_ARGS` だけで起こす | 5 本のどれにも `--agent "` ・`--agent adversarial-reviewer` などの直書きが無く（`! grep -qE`）、`reviewer_agent_args` を呼んでいる。`fix-review-lib.sh` の `run_fix_review` を `CLAUDE_BIN` の差し替えで流すと、差し替えが受け取った引数に `--agents` と写しの `agents.json` がある | 1 本に `--agent "$REVIEWER_AGENT"` を戻した写しで落ちる |
| TC-05 | AC1・AC2 | 一時リポジトリで `unreviewed.py run`（`execvp` の手前で止める差し替え）: (a) 写しに `reviewer-agents-lib.sh` があり、ブランチで `code-review.sh` と `.claude/agents/code-reviewer.md` を変えた (b) 同じで写しに `reviewer-agents-lib.sh` が無い (c) ブランチで `issue-source.sh` を変えて `issue-source.sh` を流す (d) 写しに入口が無い | (a) 75 にならず写しの入口を動かす（標準エラーに「変更前の版で審査します」）(b) 75 (c) 75 (d) 75 | `REVIEW_ENTRIES` の判定を外した写しで (a) が 75 になり落ちる。lib の有無の確かめを外した写しで (b) が動いて落ちる |
| TC-06 | AC2 | `reviewer_source_risk` を写しのダミーの置き場所と作業ツリーの置き場所から呼ぶ。`plan-issue-review.sh` の RISK の上書きも同じ | 写しから `NO`、作業ツリーから `YES`。`combine_risk` を通した本体の RISK が YES | 置き場所の判定を常に `NO` にした写しで落ちる |
| TC-07 | AC4 | 一時リポジトリに BASE と HEAD を作り `test_weakening_report`: テストのファイルを消す／`def test_` を 1 つ減らす／`assert` を 1 つ減らす／`ck` の行を 1 つ減らす／`@pytest.mark.skip`・`it.only(`・`test.todo(`・`test.fixme(`・`xfail` を足す／`backend/x/views.py` に `skip` を足す／同じファイルの中でテストを並べ替える | 前の 5 種類がそれぞれ `TEST_WEAKENING: deleted|fewer-tests|fewer-checks|skip` の行で出る。`views.py` と並べ替えは出ない。何も無いときは `TEST_WEAKENING: なし` | 目印の正規表現から 1 つ消した写しで、その行が出ず落ちる。テストのファイルの判定を「全部」にした写しで `views.py` が出て落ちる |
| TC-08 | AC4 | `code-review.sh` の本体が、`test_weakening_report` の出力をコンテキストの節と証跡（`GATE_EVIDENCE`）の両方に入れる（差分のレビューの周でも範囲は merge-base から HEAD） | 本体の組み立てを関数 `weakening_section` にし、その出力に節の見出しと `TEST_WEAKENING:` の行がある。本体が `weakening_section` の結果を `CONTEXT` と `GATE_EVIDENCE` に入れている | 本体から証跡への追加を消した写しで落ちる |
| TC-09 | AC4 | 台帳: `FINDING: F1 SEV=Medium STATUS=open FILE=backend/x/tests/test_a.py LINE=3 SECURITY=no STOP=test | … | 再現: …` を harness と app の両方の種類で `ledger_update` → `ledger_blocking` | 止める指摘に出る。`STOP=testx` は形の崩れ | `STOP_RE` から `test` を消した写しで落ちる |
| TC-10 | AC3 | 一時リポジトリで、BASE の `code-review.sh` の `path_risk_trigger` は YES、作業ツリーの `code-review.sh` は常に NO を返す形にして gate-check.sh（`GATE_CHECK_LIB` なし）を流す。敵対的レビューの記録は無い | `GATE_CHECK: FAIL REASON=missing`（敵対的レビューを求める）で exit 1 | gate-check の読み込み先を作業ツリーに戻した写しで exit 0 になり落ちる |
| TC-11 | AC1 | `reviewed-hook.sh` の `_reviewed_snapshot_make` で作った写しに `.claude/agents/code-reviewer.md` と `docs/runbooks/review-rules.md` がある。`.complete` の無いフォルダが先にあっても写しが置かれる（I615 F3） | 両方のファイルがあり、`.complete` がある。先にあった壊れたフォルダは `.stale.` の名前で残る | archive のパスから `.claude/agents` を消した写しで落ちる。壊れたフォルダを移す処理を消した写しで rc=4 になり落ちる |
| TC-12 | 同梱（一覧 I615 F5） | `code-review.sh` で `python3` を `-I` 無しで起こす行が無い（`python3 -`・`python3 -c`・`python3 -B` など、`python3` の直後の引数が `-I` で始まらない行） | テストの中で `grep -nP 'python3(?! +-I)\s+-' scripts/claude/code-review.sh` が 0 件（`! grep -qP …` の形で exit 0） | `-I` を 1 か所外した写しで 1 件になり落ちる |
| TC-13 | AC5 | 既存のハーネスのテスト全部（`scripts/claude/tests/run-all.sh`）と shellcheck・bandit | CI の Harness Tests・pre-commit が成功 | （既存のテストの FG） |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i593_review_from_base.sh
bash scripts/claude/tests/test_adversarial_trigger.sh
bash scripts/claude/tests/test_i181_review_slim.sh
bash scripts/claude/tests/test_i193_official_flow.sh
bash scripts/claude/tests/test_i205_stop_criteria.sh
bash scripts/claude/tests/test_i599_unreviewed_scripts.sh
bash scripts/claude/tests/test_fix_review.sh
```
