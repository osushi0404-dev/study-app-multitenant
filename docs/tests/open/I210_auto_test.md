# I210 自動テスト: ハーネスのテスト N10（敵対的レビューの締め切り）が実時間に依存して揺れるのを直す

実行コマンド（例）: アプリのコード変更が無いため `docker compose exec backend python -m pytest`・`docker compose exec frontend npm test`・E2E は非該当（CI では今までどおり動く）

結果:
- backend: 非該当
- frontend: 非該当

## テストケース

合否はすべて終了コード（合格=exit 0・不合格=非ゼロ）。否定の判定（「呼ばない」「当たらない」「変わらない」）には失敗注入（FG: 本体の一時コピーの判定の要を壊す／規則の写しに前の形を足すと、対応する項目が不合格になることを確かめる）を付ける。実際の claude は使わない（偽物の `CLAUDE_BIN`）。前の形の見逃し（SIGPIPE）を合格の条件にする FG は作らない（パイプの容量に左右される・一覧 I195 F11。代わりに手動 No.2）。

| TC | 内容 | 期待値 | 結果 |
|---|---|---|---|
| TC-01 | `bash scripts/claude/tests/test_i202_ledger_cleanup.sh`（A1・FG-A1・A1b・N10・FG-N10 の書き換え・`d3_bl` の書き換え・「I210」の節 N15〜N19 を足す）。既存の R・L・W・A・G・D・N・P・Q も | exit 0・`fail=0`（ベースライン pass=148） | implement で実行（2026-10-28）: pass=157 fail=0（ステップ 1 の後に負荷をかけて 5 回: `STRESS: 5/5`） |
| TC-01b | `bash scripts/claude/tests/test_pipefail_negated_grep.sh`（新規。項目は下の表） | exit 0・`fail=0`。実装前（4.4〜4.7 の前）は G1 が 4 か所に当たって不合格 | implement で実行（2026-10-28）: 実装前（Red）pass=9 fail=1（G1 が計画どおりの 4 か所に当たった）→ 実装後 pass=10 fail=0 |
| TC-01c | `bash scripts/claude/tests/test_stress_repeat.sh`（新規。`stress-repeat.sh` の失敗注入。項目は下の表） | exit 0・`fail=0` | implement で実行（2026-10-28）: pass=5 fail=0。S5 の効き目は、`stop_load` を空にした写しで負荷のプロセスが残る（pgrep が当たる）ことで 1 回確かめた |
| TC-02 | `bash scripts/claude/tests/test_check_frontend_evidence.sh`（E16〜E18 を足す） | exit 0・`fail=0`（ベースライン pass=16） | implement で実行（2026-10-28）: pass=19 fail=0 |
| TC-03 | 影響を受けうるテスト: `test_posttooluse_check.sh`（32 行の書き換え）・`test_i193_official_flow.sh`（527・528 行を消す）・`test_i197_adversarial_process.sh`（`adversarial-review.sh` の時計の差し替え・実時間の既定の動き） | どれも exit 0（ベースライン pass=6・175・115） | implement で実行（2026-10-28）: pass=6・174（FG-S21 の前の形の 1 項目を消した）・115（fail=0） |
| TC-04 | `bash scripts/claude/tests/run-all.sh`（CI の Harness Tests ジョブで確かめる。手元では流し直さない） | CI の Harness Tests が pass | 実装前のため未実行 |

### TC-01 の項目（書き換え・I210 の節）
一時の git リポジトリ（既存の `amk`）と偽物の claude（`$AS`）で `adversarial-review.sh` を流す。偽の時計は `ADV_CLOCK_FILE="$TMP/a_<名前>/sd/clock"`（中身 `1000000` から）。偽物の実験役は、偽の時計のときは「実験する 2 観点の `exec_in1.txt` がそろう」のを待って（上限 `exec_wait` 秒）時計を `exec_advance` だけ進め、印 `barrier` に `ok`／`timeout` を書く。実時間のときは「ほかの実験役が始まる」のを待つ（上限 `exec_wait` 秒）。

| 項目 | 入力 | 期待値 | FG（失敗注入） |
|---|---|---|---|
| A1（AC2） | 実時間・`exec_wait` 10・既定の `arun`（締め切り 60・最小 1） | 区間 2 つ・重ならない・判定 OK（`2 yes OK`） | FG-A1: `flock 9` を `:` にした写しで区間が重なる（`no`） |
| A1b（AC2） | 偽の時計・`ADV_DEADLINE=100 ADV_MIN_STEP=40`・`exec_advance` 70・`exec_wait` 15 | 実験役 1 回・記録に「実行していない（締め切り）」・判定 HIGH（`1 yes HIGH`） | （N10 の FG で固定） |
| N10（AC1・AC3） | 偽の時計・`ADV_DEADLINE=100 ADV_MIN_STEP=30`・`exec_advance` 45・`exec_wait` 15 | 実験役 1 回・記録に「実行していない（締め切り）」・`barrier` は `ok` だけ（`1 yes yes`） | FG-N10: 273 行を `-lt "${ADV_MIN_STEP}"` にした写しで、締め切りにならない（`no`）。同じ偽の時計・同じ数 |
| N15（AC4・止める側） | `ADV_CLOCK_FILE` の中身 `abc` で `arun` | exit 2・出力に `ADVERSARIAL_ERROR: CLOCK` の行（`2 yes`） | FG-N15: 起動時の `\|\| { …CLOCK…; exit 2; }` を外した写しで exit 2 にならない |
| N16（止める側） | 関数だけを読み込み `ADV_START=100 ADV_DEADLINE=50`。時計のファイルが `x`／`120`／無い | `remaining` が `0`／`30`／`0`（`0 30 0`） | FG-N16: `\|\| { echo 0; return; }` を外した写しで、`x` のとき `0` にならない |
| N17（AC4） | `ADV_CLOCK_FILE` なしで関数だけを読み込み `adv_now` | `date +%s` との差が 1 以下 | —（既定の値の確認。不在の判定ではない） |
| N18（AC4） | `scripts/claude/adversarial-review.sh` | 既定値の 2 行（`: "${ADV_DEADLINE:=600}" "${ADV_STEP_TIMEOUT:=300}" "${ADV_MIN_STEP:=60}" "${ADV_EXPERIMENT_ROUNDS:=2}" \` と `  "${ADV_ROUND_LIMIT:=2}" "${ADV_REVIEW_BUDGET:=2}" "${ADV_EXEC_BUDGET:=0.5}" "${ADV_BASE:=origin/develop}"`）が行全体で一致 | FG-N18: `ADV_MIN_STEP:=60` を `30` にした写しで不合格 |
| N19（AC4・根本原因） | `scripts/claude/adversarial-review.sh` | `date +%s` の行がちょうど 1 つで、それが `adv_now` の中 | FG-N19: `remaining()` を前の形（`$(date +%s)`）に戻した写しで不合格 |
| D3（AC5・書き換え） | `d3_bl` を python 1 回の形に（4.5） | 期待値は前と同じ（実物の一覧のどの行も決まった形・形の崩れた行を足した写しは不合格・行を全部消した写しは合格） | 既存の FG-D3・D3b |

### TC-01b の項目（`test_pipefail_negated_grep.sh`）
規則は計画書 4.8。写しは一時のフォルダに作る（`!` の代わりに `NOT` と書いて置き換える）。

| 項目 | 入力 | 期待値 |
|---|---|---|
| G1（AC7） | 実物: `find scripts/claude -type f -name '*.sh'` の全部 | 当たりなし（exit 0） |
| G2 | 同上 | 見た pipefail のスクリプトが 20 本以上（対象が空のまま合格しない） |
| FG-G3a | `set -uo pipefail` と `if ! printf '%s\n' "$X" \| grep -q '^a/'; then` の写し（前の `check-frontend-evidence.sh` の形） | 当たる（exit 1） |
| FG-G3b | `set -uo pipefail` と `f() { ! grep -hE 'a\|b' "$@" \| grep -qvF 'c'; }`（引用符の中の `\|`・前の `test_i193` の形） | 当たる |
| FG-G3c | `set -uo pipefail` と `! cat x \| grep -E '^- F' \| grep -qvE "$Y"`（前の `d3_bl` の形） | 当たる |
| FG-G3d | `set -uo pipefail` と `if [ -n "$3" ] && ! printf '%s' "$E" \| grep -q "$3"; then`（前の `test_posttooluse_check.sh` の形） | 当たる |
| FG-G3e | `set -o pipefail` と `! a \| grep --quiet b`／`set -euo pipefail` と `! a \| grep -E -q b` | どちらも当たる |
| G4 | pipefail の無いスクリプトに FG-G3a の行 | 当たらない（反転しない） |
| G5 | pipefail のスクリプトに、コメントの行 `# ! a \| grep -q b`・直した形（`[[ $'\n'"$X" != *$'\n'a/* ]]`・`awk '…' f`・`! grep -q a f`〔パイプなし〕） | 当たらない |

### TC-01c の項目（`test_stress_repeat.sh`）
一時のフォルダに小さなテストのスクリプトを作り、`stress-repeat.sh <回数> <スクリプト> 1`（負荷 1 本）で流す。

| 項目 | 入力 | 期待値 |
|---|---|---|
| S1 | 必ず exit 0 のスクリプトを 2 回 | exit 0・`STRESS: 2/2`・`RUN 1: PASS`・`RUN 2: PASS` |
| FG-S2 | 必ず exit 1 のスクリプトを 2 回 | exit 1・`STRESS: 0/2` |
| FG-S3 | 2 回目だけ exit 1 のスクリプト（回数をファイルに数える）を 2 回 | exit 1・`STRESS: 1/2`・`RUN 2: FAIL` |
| S4 | 引数の誤り（回数が `x`・回数が `0`・スクリプトが無い・引数なし） | どれも exit 2 |
| S5 | S1 の後 | 負荷のループ（`stress-repeat.sh` が起こした子のプロセス）が残っていない |

### TC-02 の項目（`test_check_frontend_evidence.sh`）
| 項目 | 入力 | 期待値 |
|---|---|---|
| E16（AC6） | `frontend/src/App.tsx` と `zz/` の下に名前の長い（約 90 バイト）ファイル 1000 個（一覧 約 9 万バイト）を変えたブランチ・テストの記録なし | exit 1（対象。記録が無いので不合格） |
| E17 | `zz/` の下の 1000 個だけを変えた（`frontend/src/` を変えない）・記録なし | exit 0（対象外） |
| E18 | `docs/frontend/src/a.md` だけを変えた・記録なし | exit 0（対象外。行の先頭の `frontend/src/` だけを見る） |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i202_ledger_cleanup.sh
bash scripts/claude/tests/test_pipefail_negated_grep.sh
bash scripts/claude/tests/test_stress_repeat.sh
bash scripts/claude/tests/test_check_frontend_evidence.sh
bash scripts/claude/tests/test_posttooluse_check.sh
bash scripts/claude/tests/test_i193_official_flow.sh
bash scripts/claude/tests/test_i197_adversarial_process.sh
```

## 実行記録
