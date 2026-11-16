# I498 自動テスト: マージ前の最終確認の CI 待ちの上限を code-review.sh と 1 か所にまとめる

実行コマンド（例）: `bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i498_ci_wait_timeout.sh scripts/claude/tests/test_pr_base_sync.sh scripts/claude/tests/test_i193_official_flow.sh scripts/claude/tests/test_i525_skill_sandbox_form.sh`

結果:
- backend: 対象外（変更なし）
- frontend: 対象外（変更なし）
- harness: 2026-11-16 implement で上の 4 本を `run-all.sh` で実行 → `run-all: pass=4 fail=0`

## TC-01: 2 つのスクリプトの CI 待ちの既定の上限（新規 `scripts/claude/tests/test_i498_ci_wait_timeout.sh`）
- 前提: `gh`・`sleep` のスタブを `PATH` の先頭に置く（実 GitHub に依存しない）。`gh` は、`pr view <N> --json isCrossRepository` に `false`、`baseRefName` に `develop`、`mergeStateStatus` に `BLOCKED`、`headRefOid` に手元の HEAD、`pr checks <N>`（表）に `A	pending`、`pr checks <N> --json name,bucket`（`--jq` の結果）に `pending	A` を返す。`sleep` は何もせず 0。`CI_WORKFLOWS` はジョブ `A` だけの一時の yml。各起動は `timeout 30` で包む（待ちが終わらない壊れ方でもテストが止まる）
- 対象のフォルダ: `I498_SCRIPTS_DIR`（既定 `scripts/claude`）。失敗の注入は、一時のフォルダに `code-review.sh`・`pr-base-sync.sh` を写して壊す（本物のファイルは書き換えない）
- 上限の取り出し方: 待ちの間隔を大きくして（`CI_POLL_INTERVAL=100000`・`PBS_CI_INTERVAL=100000`）1 回だけ待ちの行を出させ、行末の `0s / <N>s` の `<N>` を取る

| No | 内容 | 期待（合格＝exit 0 の判定） |
|---|---|---|
| T1 | `code-review.sh` を関数だけ読み込み（`REVIEW_LIB_SOURCE_ONLY=1`・`CI_WAIT_TIMEOUT` は未設定）、`wait_ci 1` を呼ぶ | 戻り値 3・最後の行が `CI_WAIT: TIMEOUT`・待ちの行の上限 `<N_cr>` が正の整数 |
| T2 | `pr-base-sync.sh final 219` を流す（`PBS_CI_TIMEOUT` は未設定） | exit 1・`pending... 0s / <N_pbs>s` の行が出る・`⚠️ CI タイムアウト（<N_pbs>秒）` が出る（AC4）・`<N_pbs>` が正の整数 |
| T3 | T1 と T2 の上限を比べる | `<N_cr>` と `<N_pbs>` が同じ（AC1） |
| T4 | 2 つのスクリプトに、上限の環境変数の数字の既定（`PBS_CI_TIMEOUT:-<数字>`・`CI_WAIT_TIMEOUT:-<数字>`）が無い | `grep -qE '(PBS_CI_TIMEOUT|CI_WAIT_TIMEOUT):-[0-9]'` がどちらにも当たらない（AC1 の「定義が 1 か所」の補い） |
| T5 | `PBS_CI_TIMEOUT=7` で `pr-base-sync.sh final 219` を流す | exit 1・`pending... 0s / 7s`・`⚠️ CI タイムアウト（7秒）`（上書きが今までどおり効く） |
| T6 | `code-review.sh` の無いフォルダに `pr-base-sync.sh` だけを写して `final 219` を流す（`PBS_CI_TIMEOUT` は未設定） | exit 1・`CI 待ちの上限の既定を code-review.sh から読めません` が出る・`pending...` の行が出ない（待ち始めない） |
| FG1 | 写しの `pr-base-sync.sh` の `CI_TIMEOUT="${PBS_CI_TIMEOUT:-}"` を `CI_TIMEOUT="${PBS_CI_TIMEOUT:-600}"` に戻す | T3 と T4 が不合格になる |
| FG2 | 写しの `code-review.sh` の `wait_ci` の `${CI_WAIT_TIMEOUT:-$CI_WAIT_TIMEOUT_DEFAULT}` を `${CI_WAIT_TIMEOUT:-1200}` に戻す | T3 と T4 が不合格になる |
| FG3 | 写しの `pr-base-sync.sh` から、読んだ値の確かめ（`[[ "$CI_TIMEOUT" =~ ^[1-9][0-9]*$ ]]` の 2 行）を消す | T6 が不合格になる（空の上限で待ち始める・`timeout` で切られる） |

- テストの終わりに `RESULT: OK` で exit 0、1 件でも不合格なら `RESULT: NG` で exit 1
- 実装の手順 1 で、今の develop の形のスクリプトに対して T3 が不合格（600 と 1200）になることも確かめる（テストの先書き）
- 結果（2026-11-16 implement）:
  - 先書き（直す前のスクリプト）: T1・T2・T5 合格、T3（同じ値）・T4（数字の既定）・T6（読めないと止まる）不合格、FG1〜FG3 は壊し方が当たらず不合格 → `RESULT: NG (fail 6 / pass 8)`（期待どおりの赤）
  - 直した後: T1〜T6・FG1〜FG3 の 14 項目すべて合格（`run-all: pass=1 fail=0`）

## TC-02: close・proceed の手順書が最終確認を背景の実行で流すと書いている（AC3）
下の決定論ゲートの `grep -q`（2 行）で確かめる。手順書の文言は意図的な変更でしか消えないので、テストのファイルにはしない（`docs/runbooks/plan-writing-rules.md`「決定論テストの対象の選び方」）。
- 失敗の注入: 写し（`$TMPDIR`）から `run_in_background: true` を消した手順書に同じ `grep -q` を掛け、exit 1 になることを実装の後に確かめて結果に書く
- 結果（2026-11-16 implement）: 本物の close・proceed は `rc=0`、記述を消した写しは close・proceed とも `rc=1`（失敗の注入が効く）

## TC-03: 既存のテストが通る（AC4・上書きの後方互換）
- `test_pr_base_sync.sh`（21 件・`PBS_CI_TIMEOUT=0` の上書き）・`test_i193_official_flow.sh`（`wait_ci` の C 群・`CI_WAIT_TIMEOUT=2` の上書き）・`test_i525_skill_sandbox_form.sh`（手順書に環境変数の前置きの起動が無い）が合格
- 結果（2026-11-16 implement）: 3 本とも合格（TC-01 と合わせて `run-all: pass=4 fail=0`）

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i498_ci_wait_timeout.sh
bash scripts/claude/tests/test_pr_base_sync.sh
bash scripts/claude/tests/test_i193_official_flow.sh
bash scripts/claude/tests/test_i525_skill_sandbox_form.sh
grep -q 'run_in_background: true' .claude/skills/close/SKILL.md
grep -q 'run_in_background: true' .claude/skills/proceed/SKILL.md
bash -n scripts/claude/pr-base-sync.sh
bash -n scripts/claude/code-review.sh
```

## 実行記録
- 2026-11-16 review-gate（code-review.sh・HEAD e778d4a3）: 決定論ゲート 8 行すべて exit=0（docs/reviews/I498_code_review_20261116_1139.md）。CI 全ジョブ合格（CI_WAIT: OK）
- 2026-11-16 test-gate: gate-check.sh I498 → GATE_CHECK: OK。test-gate に回された重いテストは無し（pytest・Jest・E2E は CI）
