# I530 自動テスト: マージ前の最終確認の CI 待ちをレビュー段階の wait_ci に一本化する

実行コマンド（例）: `bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_pr_base_sync.sh scripts/claude/tests/test_i498_ci_wait_timeout.sh scripts/claude/tests/test_i193_official_flow.sh`

結果:
- backend: 対象外（変更なし）
- frontend: 対象外（変更なし）
- harness: 2026-11-16 implement で `run-all.sh` に 3 本（test_pr_base_sync・test_i498_ci_wait_timeout・test_i193_official_flow）→ `run-all: pass=3 fail=0`

## TC-01: final の分岐と CI 待ち（`scripts/claude/tests/test_pr_base_sync.sh`）
- 前提: `gh`・`git`・`sleep` のスタブを `PATH` の先頭に置く（実 GitHub・実 git に依存しない）。`git rev-parse HEAD` は `FAKE_HEAD`（固定の値）。`gh` は `headRefOid` に `${PR_HEAD-$FAKE_HEAD}`、`pr checks`（`--json` の有無とも）に `CHECKS_FILE` の中身（`<bucket>\t<name>` の行）を返す。`CI_WORKFLOWS` はジョブ `build`・`test` の一時の yml。`CI_WAIT_TIMEOUT=1 CI_POLL_INTERVAL=1`
- チェックの形: GREEN=`pass build`・`pass test`／FAIL=`fail build`／PARTIAL=`pass build` だけ／NONE=空
- 既存の T1〜T21（sync・final の分岐・fork のガード・照会失敗）と副作用の確かめは、スタブの形を変えたうえでそのまま合格すること

| No | 内容 | 期待（合格＝exit 0 の判定） |
|---|---|---|
| T9 追加 | final UNSTABLE＋FAIL の出力 | exit 1（既存）・出力に `⛔ CI 失敗` がある（AC3） |
| T22 | final BLOCKED＋NONE（チェックがまだ無い） | exit 1・出力に `⚠️ CI タイムアウト（1秒）` がある（AC1・AC3） |
| T23 | final BLOCKED＋PARTIAL（一部のジョブだけ登録・合格） | exit 1（AC1） |
| T24 | final CLEAN＋NONE | exit 1（AC1・合格の道すべてが待つ） |
| T25 | final BLOCKED＋GREEN・`PR_HEAD=deadbeef`（PR の最新のコミットが手元と違う） | exit 1・出力に `NOT_PUSHED` がある（AC3） |
| T26 | sync CLEAN を、同じフォルダに `code-review.sh` の無い写しの `pr-base-sync.sh` で流す | exit 0（sync は code-review.sh を読まない・一覧 I498 F3） |
| FG1 | 一時のフォルダに `pr-base-sync.sh`・`code-review.sh` を写し、`run_wait_ci` の中身を古い判定（`gh pr checks` に `fail` が無ければ `return 0`）に置き換え、その写しに T22・T23 と同じ入力を与える（`CASE_SCRIPT`） | 壊し方が効いている（写しが元と違う）・写しは exit 0（穴が開く＝本物の T22・T23 がこの壊し方を捕まえる） |
| FG2 | 同じく `CLEAN|HAS_HOOKS` の行から `run_wait_ci` を消した写しに T24 と同じ入力を与える | 壊し方が効いている・写しは exit 0（本物の T24 が捕まえる） |

- テストの終わりに `RESULT: OK` で exit 0、1 件でも NG なら `RESULT: NG` で exit 1
- 実装の手順 1 で、直す前の `pr-base-sync.sh` に対して T22〜T25 が NG になることを確かめる（テストの先書き）
- 結果（2026-11-16 implement）:
  - 先書き（直す前のスクリプト）: T1〜T21 合格、T22〜T26 が NG、FG1・FG2 は壊す対象が無く NG → `RESULT: NG (9 件 / pass 31)`（期待どおりの赤）
  - 直した後: 26 ケース・41 項目すべて合格（FG1 の写しは T22・T23 の入力で exit 0、FG2 の写しは T24 の入力で exit 0）

## TC-02: CI 待ちの上限の既定と上書き（`scripts/claude/tests/test_i498_ci_wait_timeout.sh`）
- I498 の TC-01 を新しい形に合わせたもの。`pbs_run` は `env -u CI_WAIT_TIMEOUT … CI_POLL_INTERVAL=100000 GH_HEAD=<HEAD> CI_WORKFLOWS=<yml>`

| No | 内容 | 期待（合格＝exit 0 の判定） |
|---|---|---|
| T1 | `code-review.sh` の `wait_ci` の既定で時間切れ | 戻り値 3・`CI_WAIT: TIMEOUT`・待ちの行の上限が正の整数（変更なし） |
| T2 | `pr-base-sync.sh final 219`（`CI_WAIT_TIMEOUT` 未設定） | exit 1・待ちの行の `0s / <N>s` と同じ `<N>` の `⚠️ CI タイムアウト（<N>秒）`（AC3） |
| T3 | T1 と T2 の上限が同じ | 同じ |
| T4 | 2 つのスクリプトに上限の環境変数の数字の既定が無い | `grep -qE 'CI_WAIT_TIMEOUT:-[0-9]'` が当たらない（`PBS_CI_TIMEOUT` はもう無い名前なので見ない） |
| T5 | `CI_WAIT_TIMEOUT=7` で `final 219` | exit 1・上限 7・`⚠️ CI タイムアウト（7秒）`（review-gate と同じ上書きが final に効く・一覧 I498 F2） |
| T6 | `code-review.sh` の無いフォルダに `pr-base-sync.sh` だけを写して `final 219` | exit 1・`CI 待ちの処理（` と `を読み込めません` が出る・`待ち` の行が出ない |
| FG1 | 写しの `pr-base-sync.sh` の `set -u` の次に `export CI_WAIT_TIMEOUT="${CI_WAIT_TIMEOUT:-600}"` を足す | T3・T4 が不合格 |
| FG2 | 写しの `code-review.sh` の `wait_ci` の既定を `:-1200` に戻す | T4 が不合格（T3 は見ない。final が `wait_ci` そのものを呼ぶので、既定を変えても 2 つの上限は食い違わない・計画変更記録） |
| FG3 | 写しの `pr-base-sync.sh` の ` || exit 4` を消す | T6 が不合格 |

- 結果（2026-11-16 implement）: 13 項目すべて合格

## TC-03: CI を待つ判定が pr-base-sync.sh に無い（AC2・決定論ゲート 1 回）
- 判定: 下の決定論ゲートの 5 行目（`pr-base-sync.sh` に `gh pr checks` も `ci_wait()` の定義も無ければ exit 0）
- 意図的に戻さない限り起きないのでテストのファイルにはしない（`docs/runbooks/plan-writing-rules.md`「決定論テストの対象の選び方」）。戻したときの害は TC-01 の T22〜T24 が止める
- 失敗の注入: 直す前の `pr-base-sync.sh`（`git show HEAD:scripts/claude/pr-base-sync.sh` を `$TMPDIR` に書き出したもの）に同じ判定を掛けると exit 1
- 結果（2026-11-16 plan-issue）: 失敗の注入（直す前のファイル）で exit 1 を確認済み。本物のファイル（実装の後）は exit 0（2026-11-16 implement）

## TC-04: 関係する既存のテストと静的な確かめ
- `test_i193_official_flow.sh`（`wait_ci` の C 群・`wait_ci` を変えないので通る）
- `pre-commit run shellcheck --files …`（変えたスクリプト 2 本とテスト 2 本。手元に shellcheck 単体が無いので pre-commit 経由）
- 結果（2026-11-16 implement）: `test_i193_official_flow.sh` 合格・shellcheck `Passed`（最初の実行で出た SC2097/SC2098〔環境変数の渡し方〕・SC2016 をテストで直した）

## TC-05: 一覧の行（決定論ゲート 1 回）
- 判定: 下の決定論ゲートの 6 行目（I498 の F1・F2・F3・R1 と I224 の F1 の行が無く、I498 の F4 の行が残っていれば exit 0）
- 失敗の注入: 直す前の一覧（今のファイル）では exit 1
- 結果: 失敗の注入（直す前の一覧）で exit 1 を確認済み（2026-11-16 plan-issue）。行を消した後は exit 0（2026-11-16 implement）

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_pr_base_sync.sh
bash scripts/claude/tests/test_i498_ci_wait_timeout.sh
bash scripts/claude/tests/test_i193_official_flow.sh
pre-commit run shellcheck --files scripts/claude/pr-base-sync.sh scripts/claude/code-review.sh scripts/claude/tests/test_pr_base_sync.sh scripts/claude/tests/test_i498_ci_wait_timeout.sh
bash -c "! grep -qF 'gh pr checks' scripts/claude/pr-base-sync.sh && ! grep -qE '^ci_wait\(\)' scripts/claude/pr-base-sync.sh"
bash -c "! grep -qE '^- (F1|F2|F3|R1) ' docs/reviews/backlog/I498.md && grep -qE '^- F4 ' docs/reviews/backlog/I498.md && ! grep -qE '^- F1 ' docs/reviews/backlog/I224.md"
```

## 実行記録
