# I530 計画書: マージ前の最終確認の CI 待ちをレビュー段階の wait_ci に一本化する

## 基本情報
- **計画書ID**: plan_I530
- **関連イシュー**: #530
- **Draft PR**: #531
- **作成根拠資料**: docs/issues/open/I530.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I530_review.md
- **作成日**: 2026-11-16

## 1. 背景/目的
- 背景: close 段階の手順 5.5 は、マージ依頼の直前に `bash scripts/claude/pr-base-sync.sh final` を流して「BEHIND・DIRTY でない」かつ「CI が全部合格」を確かめる。この CI 待ち（`ci_wait`）は、レビュー段階の `code-review.sh` の `wait_ci` とは別に書かれた古い判定のままで、CI のチェックがまだ登録されていない・一部だけ登録済みのときに、待たずに合格と言う
- 目的: 最終確認が、CI のジョブが全部そろって合格するまで待ってから合格と言うようにする。CI を待つ判定を `wait_ci` の 1 か所だけにする

### 調査結果
- **原因の概要**: 最終確認は「CI の一覧に『失敗』も『実行中』も無ければ合格」と見ている。push の直後は一覧がまだ空、または一部しか載っていないので、そのまま合格になる
- **詳細な原因分析**:
  1. `scripts/claude/pr-base-sync.sh` の `ci_wait`（I498 の後の `:84-94`）は `gh pr checks` の文字の出力に `fail` があれば失敗、`pending` が無ければ `return 0`（合格）
  2. チェックが 1 つも無いとき（push の直後）・一部のワークフローだけ登録されたときは、どちらの語も無いか、登録済みの分が終われば `pending` が消えるので、合格になる
  3. 呼ぶ所は `BEHIND` の追従の後（`:118`）と `BLOCKED|UNSTABLE`（`:122`）。`CLEAN|HAS_HOOKS`（`:123`）は CI を待たずに合格にする（承認の後でないと CLEAN にならない設定〔develop は Code Owners の承認が必須〕なので今は起きにくいが、同じ形の穴）
  4. `code-review.sh` の `wait_ci`（`:243-283`）は I193 で強くなった: 手元の HEAD と PR の最新のコミット（`headRefOid`）が同じか（違えば `CI_WAIT: NOT_PUSHED`・戻り値 1）／`fail`・`cancel` があれば失敗（戻り値 1）／PR で動くワークフローのジョブ（`expected_ci_jobs`）が全部 `pass` か `skipping` でそろったときだけ成功（戻り値 0）／時間切れは戻り値 3／ジョブ名を読めないと `CI_WAIT: NO_JOBS`・戻り値 1
  5. 根本原因: 同じ「CI を待つ」処理が 2 か所に書かれ、片方だけが直された（I498 の上限の食い違いと同じ形）
- **再現（スパイク・2026-11-16・このセッション）**: `gh`・`sleep` のスタブ（`mergeStateStatus`=BLOCKED、`gh pr checks` が空）で今の `pr-base-sync.sh final 219` を流す → `✅ CI 全グリーン（BLOCKED＝Approve 待ち等）`・exit 0。`gh pr checks` が `A	pass` だけ（ワークフローには A・B）でも exit 0 → **再現した**
- **スパイク（新しい呼び方・2026-11-16・このセッション）**: `REVIEW_LIB_SOURCE_ONLY=1 bash -c '. "$1" || exit 4; wait_ci "$2" || exit $?' _ scripts/claude/code-review.sh 219 | tee <log>` を同じスタブで流し、`${PIPESTATUS[0]}` と最後の `CI_WAIT:` 行を読む → チェック無し: rc=3・`CI_WAIT: TIMEOUT`／A だけ: rc=3／fail あり: rc=1・`CI_WAIT: FAIL`／全部 pass・skipping: rc=0・`CI_WAIT: OK`／HEAD 違い: rc=1・`CI_WAIT: NOT_PUSHED`／code-review.sh が無い: rc=4／`CI_WAIT_TIMEOUT=abc`: rc=3（`[` の整数のエラーでループを抜けて時間切れ＝止まる側）→ **成立**（別の bash で呼んで、戻り値と結果の行が取れる）
- **I498 との関係**: I498（PR #528）はマージ依頼中で develop に未マージ。このイシューは I498 の `CI_WAIT_TIMEOUT_DEFAULT`・`test_i498_ci_wait_timeout.sh` の上に乗るので、ブランチに `origin/feature/I498-ci-wait-timeout-unify` を取り込んだ（§9）
- **環境変数の使用箇所**（`grep -rn "PBS_CI_"`）: `PBS_CI_TIMEOUT`・`PBS_CI_INTERVAL` は `pr-base-sync.sh` と 2 本のテスト（`test_pr_base_sync.sh:76`・`test_i498_ci_wait_timeout.sh`）だけ。手順書（`.claude/skills/`・`docs/runbooks/`）からの使用は無い
- **`pr-base-sync.sh` を読む他のテスト**: `test_i193_official_flow.sh:147・152` は close の手順書の中の `pr-base-sync.sh sync` の行の位置を見るだけで、スクリプトは動かさない（影響なし）
- **環境**: `python3` と PyYAML はハーネスのテストの uv の環境（`run-all.sh` が `uv run --locked` で入る）にある。`test_pr_base_sync.sh` は今後 `wait_ci` 経由で PyYAML を使う（無いと `CI_WAIT: NO_JOBS` で合格のケースが落ちるので、気づかずに素通りはしない）

## 2. 受け入れ条件
- [ ] AC1: `pr-base-sync.sh final` は、CI のチェックがまだ登録されていない・一部のワークフローだけ登録済みのときに合格にならず、全部そろって合格するまで待つ（→ TC-01 の T22・T23・T24）
- [ ] AC2: CI を待つ判定の処理が `code-review.sh` の `wait_ci` の 1 か所だけにある（`pr-base-sync.sh` に `gh pr checks` を呼ぶ行と `ci_wait` 関数が無い）（→ TC-03）
- [ ] AC3: 上限を超えたとき・CI が失敗したときの `pr-base-sync.sh` の終わり方（exit 1・今のメッセージ `⚠️ CI タイムアウト（<秒>秒）`・`⛔ CI 失敗`）は変わらない。手元の HEAD が PR の最新のコミットと違うときは exit 1 で止まり、`NOT_PUSHED` と分かる（→ TC-01 の T9・T22・T25、TC-02 の T2・T5）
- [ ] AC4: 決定論のテスト（失敗の注入つき）で、チェック未登録のとき・一部のジョブだけ登録済みのときのどちらも `final` が合格（exit 0）にならないことを確かめる（→ TC-01 の T22〜T24 と FG1・FG2）

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: ハーネスのスクリプト（`pr-base-sync.sh`・`code-review.sh` のコメントだけ）とそのテスト 2 本。close の手順 5.5・proceed の `merge` の最終確認の判定が強くなる（待つ時間が延びうる・手順書の文言は変えない）。`.github/`・`.claude/settings.json`・`.claude/skills/` は変えない

## 4. 変更点一覧（具体）
| ファイル | 変更内容 |
|---|---|
| `scripts/claude/pr-base-sync.sh` | (1) `ci_wait` を消し、`code-review.sh` の `wait_ci` を別の bash で呼ぶ `run_wait_ci` に置き換える (2) I498 の上限の既定の読み込み（`:21-29`）と `PBS_CI_INTERVAL`（`:19`）を消す（上限・間隔は `wait_ci` と同じ `CI_WAIT_TIMEOUT`・`CI_POLL_INTERVAL`） (3) `CLEAN|HAS_HOOKS` でも `run_wait_ci` を通す (4) 冒頭の説明を直す |
| `scripts/claude/code-review.sh` | `wait_ci` の前のコメントだけ: `CI_WAIT_TIMEOUT_DEFAULT=1980` を説明の箇条の前に移す（一覧 I498 F1）・「pr-base-sync.sh の final も…この値を読む」を「final も wait_ci そのものを呼ぶ」に直す。コードの動きは変えない |
| `scripts/claude/tests/test_pr_base_sync.sh` | `gh`・`git` のスタブを `wait_ci` が呼ぶ形（`pr checks --json`・`headRefOid`・`rev-parse HEAD`）に合わせ、ワークフローの yml を一時に置く。新しいケース T22〜T26 と出力の確かめ、失敗の注入 FG1・FG2 を足す |
| `scripts/claude/tests/test_i498_ci_wait_timeout.sh` | `pbs_run` の環境変数（`PBS_CI_*` → `CI_WAIT_TIMEOUT`・`CI_POLL_INTERVAL`・`GH_HEAD`・`CI_WORKFLOWS`）、T5・T6 の中身、FG1・FG3 の壊し方を新しい形に合わせる |
| `docs/reviews/backlog/I498.md` | 同梱して直した F1・F2・F3・R1 の行を消す（F4 は残す） |
| `docs/reviews/backlog/I224.md` | 同梱して直した F1 の行を消す |

### 修正アプローチ
`pr-base-sync.sh` は CI の判定を自分で持たず、同じフォルダの `code-review.sh` を関数だけ読み込む形（`REVIEW_LIB_SOURCE_ONLY=1`）で別の bash に読ませ、その中で `wait_ci` を呼ぶ。`wait_ci` の戻り値と最後の `CI_WAIT:` 行を、今のメッセージと exit 1 に対応させる。上限・間隔は `wait_ci` が読む環境変数（`CI_WAIT_TIMEOUT`・`CI_POLL_INTERVAL`）をそのまま子に渡すので、既定も上書きも review-gate と同じになる。final の合格（exit 0）の道はすべて `run_wait_ci` を通る。

### 4-1. `pr-base-sync.sh`（修正方針: 判定を持たず wait_ci を呼び、終わり方だけを今のまま保つ）
冒頭（`:5-7`）の説明を次の意味に直す: final の合格条件は「BEHIND/DIRTY でない ＋ CI のジョブが全部そろって合格（判定は code-review.sh の wait_ci）」。終了コードの意味は変えない。

`:17-29` の並びを次にする（`PBS_CI_INTERVAL`・`CI_TIMEOUT` とその読み込みを消す）:
```bash
RETRY_INTERVAL="${PBS_RETRY_INTERVAL:-5}"   # UNKNOWN/DRAFT 再取得間隔（秒）＝イシュー確定値
RETRY_MAX="${PBS_RETRY_MAX:-6}"             # 再取得回数（計30秒）＝イシュー確定値
LOOP_MAX="${PBS_LOOP_MAX:-3}"               # final の BEHIND 追従再チェック上限
# CI 待ちの判定・上限・間隔は code-review.sh の wait_ci（CI_WAIT_TIMEOUT・CI_POLL_INTERVAL）の 1 か所（I498・I530）
CR_SCRIPT="$(dirname "${BASH_SOURCE[0]}")/code-review.sh"
```

`ci_wait` を消し、次の `run_wait_ci` を置く:
```bash
# I530: CI 待ち。code-review.sh を関数だけ読み込む形（REVIEW_LIB_SOURCE_ONLY=1）で別の bash に読ませ、wait_ci を呼ぶ
# （同じシェルで読むと code-review.sh の set -euo pipefail がこのスクリプトに入るため）。
# 合格（戻り値 0 かつ CI_WAIT: OK）なら return 0。それ以外は理由を出して exit 1（止まる側）
run_wait_ci() {
  local log rc result limit
  log=$(mktemp) || { echo "⛔ 一時ファイルを作れません。STOP してユーザーに報告"; exit 1; }
  # shellcheck disable=SC2016  # 単一引用符の中は子の bash が展開する
  REVIEW_LIB_SOURCE_ONLY=1 bash -c '
    . "$1" || exit 4
    rc=0; wait_ci "$2" || rc=$?
    [ "$rc" -ne 3 ] || echo "CI_WAIT_LIMIT: ${CI_WAIT_TIMEOUT:-$CI_WAIT_TIMEOUT_DEFAULT}"
    exit "$rc"' _ "$CR_SCRIPT" "$PR_NUM" 2>&1 | tee "$log"
  rc=${PIPESTATUS[0]}
  result=$(grep '^CI_WAIT: ' "$log" | tail -1)
  limit=$(sed -n 's/^CI_WAIT_LIMIT: //p' "$log" | tail -1)
  rm -f "$log"
  case "${rc}:${result}" in
    "0:CI_WAIT: OK")         return 0 ;;
    3:*)                     echo "⚠️ CI タイムアウト（${limit}秒）"; exit 1 ;;
    "1:CI_WAIT: FAIL")       echo "⛔ CI 失敗（上のチェックの一覧を見る）"; exit 1 ;;
    "1:CI_WAIT: NOT_PUSHED") echo "⛔ 手元のコミットが PR に送られていません（CI_WAIT: NOT_PUSHED）。push してから final をやり直す"; exit 1 ;;
    "1:CI_WAIT: NO_JOBS")    echo "⛔ PR で動くワークフローのジョブ名を読めません（CI_WAIT: NO_JOBS）。STOP してユーザーに報告"; exit 1 ;;
    4:*)                     echo "⛔ CI 待ちの処理（${CR_SCRIPT}）を読み込めません。STOP してユーザーに報告"; exit 1 ;;
    *)                       echo "⛔ CI 待ちが想定外の終わり方をしました（rc=${rc} ${result:-CI_WAIT 行なし}）。STOP してユーザーに報告"; exit 1 ;;
  esac
}
```
- final の分岐: `BEHIND` の `ci_wait` → `run_wait_ci`（`:118`）／`BLOCKED|UNSTABLE` の `ci_wait` → `run_wait_ci`（`:122`）／`CLEAN|HAS_HOOKS` は `run_wait_ci; echo "✅ ${S}（マージ可・CI 通過）。マージ依頼へ進めます"; exit 0`
- sync は CI を待たないので code-review.sh を読まない（一覧 I498 F3 が消える）
- `PBS_CI_TIMEOUT`・`PBS_CI_INTERVAL` は受け付けなくなる（使うのはテストだけ・§1 調査結果）。上限の上書きは `CI_WAIT_TIMEOUT` 1 つになり、review-gate と final で値がずれない（一覧 I498 F2 の後半）。数字でない・0 以下の上書きは `wait_ci` のループに入らず時間切れ（exit 1・止まる側）になる（F2 の前半。スパイクで確かめた）

### 4-2. `code-review.sh`（修正方針: コメントだけを直し、コードの動きは変えない）
`:233-242` を次の並びにする（変数を説明の箇条の前に置く・一覧 I498 F1）:
```bash
# I193・I498: CI 待ちの上限の既定（秒）。既定の正はこの 1 か所（pr-base-sync.sh の final も wait_ci そのものを呼ぶ・I530）。
# 1980 秒＝CI で時間の上限を持つ一番長いジョブ（.github/workflows/ci.yml の Harness Tests・timeout-minutes: 30）が
# 自分の上限で止まるより先に待ちをやめないよう、30 分＋3 分（登録・順番待ちの分）。実測は 6〜11 分（PR #495 で 10 分 56 秒）
CI_WAIT_TIMEOUT_DEFAULT=1980
# CI 待ち。CI_WAIT_TIMEOUT 秒（既定 CI_WAIT_TIMEOUT_DEFAULT）まで CI_POLL_INTERVAL 秒（既定 15）ごとに見る。
# - PR の最新のコミット（headRefOid）が手元の HEAD と違う → …（今の箇条のまま）
# 戻り値: …（今のまま）
wait_ci() {
```

### 4-3. `test_pr_base_sync.sh`（修正方針: スタブを wait_ci の呼び方に合わせ、穴のケースと失敗の注入を足す）
→ auto_test の TC-01。
- `git` のスタブ: `rev-parse HEAD` に `$FAKE_HEAD`（固定の値）を返す。他は今のまま記録する
- `gh` のスタブ: `*headRefOid*` に `${PR_HEAD-$FAKE_HEAD}`、`"pr checks"*` に `CHECKS_FILE` の中身（`<bucket>\t<name>` の形）を返す
- ワークフローの yml（ジョブ `build`・`test`）を一時に置き `CI_WORKFLOWS` で渡す。`sleep` もスタブにする
- 呼ぶ環境変数: `PBS_CI_INTERVAL=0 PBS_CI_TIMEOUT=0` → `CI_WAIT_TIMEOUT=1 CI_POLL_INTERVAL=1`（0 だと `wait_ci` は 1 回も見ずに時間切れになるため）
- `CHECKS_GREEN` = `pass\tbuild` と `pass\ttest`、`CHECKS_FAIL` = `fail\tbuild`、新しく `CHECKS_PARTIAL` = `pass\tbuild` だけ、`CHECKS_NONE` = 空
- `run_case` の出力を `$LAST_OUT` に残し、`out_has <文字列> <名前>` で確かめる
- 新しいケース: T22 final BLOCKED＋チェック無し=STOP（`⚠️ CI タイムアウト（1秒）`）／T23 final BLOCKED＋一部だけ=STOP／T24 final CLEAN＋チェック無し=STOP／T25 final BLOCKED＋CI 緑＋PR の最新のコミットが違う=STOP（`NOT_PUSHED`）／T26 sync は同じフォルダに code-review.sh が無くても CLEAN で exit 0（一覧 I498 F3）／T9 の出力に `⛔ CI 失敗` があること
- 失敗の注入（本物のファイルは書き換えない。一時のフォルダに `pr-base-sync.sh` と `code-review.sh` を写して壊し、`TARGET_SCRIPT` をそこに向けてこのテストを内側で流す。内側では `PBS_FG_INNER=1` で FG を飛ばす）: FG1 `run_wait_ci` の中身を古い判定（`gh pr checks` に `fail` が無ければ合格）に戻す → 内側の T22・T23 が NG／FG2 `CLEAN|HAS_HOOKS` の `run_wait_ci` を消す → 内側の T24 が NG。どちらも壊し方が効いたこと（写しが変わったこと）も確かめる

### 4-4. `test_i498_ci_wait_timeout.sh`（修正方針: I498 の確かめを新しい形の上で保つ）
→ auto_test の TC-02。
- `pbs_run`: `env -u PBS_CI_TIMEOUT … PBS_CI_INTERVAL=100000` → `env -u CI_WAIT_TIMEOUT … CI_POLL_INTERVAL=100000 GH_HEAD="$HEAD_SHA" CI_WORKFLOWS="$WF"`
- T5: `PBS_CI_TIMEOUT=7` → `CI_WAIT_TIMEOUT=7`（final にも review-gate と同じ上書きが効く）
- T6: メッセージを `CI 待ちの処理（` と `を読み込めません` に、待ち始めていない印を `! grep -qF '待ち'` にする
- FG1: 壊し方を「`set -u` の次に `export CI_WAIT_TIMEOUT="${CI_WAIT_TIMEOUT:-600}"` を足す」にする（T3・T4 が不合格）
- FG3: 壊し方を「`|| exit 4` を消す」にする（T6 が不合格）
- 冒頭の説明の T5・T6 の文言を直す

## 5. 実装手順（ステップ）
1. `test_pr_base_sync.sh` を 4-3 のとおり直し、今の `pr-base-sync.sh` で T22〜T25 が NG になることを確かめる（→ TC-01。テストの先書き）
2. `pr-base-sync.sh` を 4-1 のとおり直す（ステップ 1 の後）→ TC-01 が合格
3. `code-review.sh` のコメントを 4-2 のとおり直す（ステップ 1・2 と並行してよい）
4. `test_i498_ci_wait_timeout.sh` を 4-4 のとおり直す（ステップ 2 の後）→ TC-02
5. 一覧（`docs/reviews/backlog/I498.md` の F1・F2・F3・R1、`I224.md` の F1）の行を消す（ステップ 2〜4 の後）→ TC-05
6. 関係するテストを流す（→ TC-01〜TC-05。全体は CI）

## 6. テスト計画
### 自動
- TC-01（`test_pr_base_sync.sh`）: 今の 21 件と副作用の確かめに、T22〜T26・出力の確かめ・FG1・FG2 を足す。スタブで `gh`・`git`・`sleep` を差し替え、実 GitHub に依存しない
- TC-02（`test_i498_ci_wait_timeout.sh`）: 2 つのスクリプトの上限の既定が同じ・上限超えの扱い・`CI_WAIT_TIMEOUT` の上書きが final に効く・code-review.sh が読めないと止まる。失敗の注入 FG1〜FG3
- TC-03（決定論ゲート・1 回）: `pr-base-sync.sh` に `gh pr checks` と `ci_wait()` の定義が無い。意図的に戻さない限り起きないので決定論テストのファイルにはしない（`plan-writing-rules.md`「決定論テストの対象の選び方」）。戻したときの害（穴の再発）は TC-01 の T22〜T24 が止める
- TC-04: `test_i193_official_flow.sh`（`wait_ci` の C 群。`wait_ci` は変えないので通ること）・`shellcheck`（変えたスクリプト 2 本とテスト 2 本）
- TC-05（決定論ゲート・1 回）: 一覧から消した行が無く、残す I498 F4 が残っている
- テストのレベル: すべてシェルの決定論テスト。バグの直しの再発防止は TC-01 の T22〜T24 と FG1・FG2
### 手動
- No.1（Claude・close の手順 5.5 で）: この PR の close の手順 5.5 の `pr-base-sync.sh final` の実際の出力に、`wait_ci` の待ちの行（`待ち（未完了: …）… / 1980s` または即時の `CI_WAIT: OK`）が出て、exit 0 で終わる。test-gate の時点では PR が Draft なので final は DRAFT で止まり確かめにならないため、結果は close のマージ依頼の報告に書く

## 7. ロールバック
- この PR のコミットを revert する（スクリプト 2 本・テスト 2 本・一覧 2 本。データ・設定の変更なし）

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 別の bash の呼び出しが、戻り値か結果の行を取り違えて合格にする（fail-open） | 合格は「戻り値 0」かつ「最後の `CI_WAIT:` 行が `OK`」の両方のときだけ。それ以外は全部 exit 1（`*` の道を含む）。TC-01 の T22〜T25 と FG1 | 回避 |
| R2: push の直後に GitHub の `headRefOid` の反映が遅れ、BEHIND の追従の直後に `NOT_PUSHED` で止まる | 止まる側（exit 1）で、やり直せば通る。review-gate の `wait_ci` も implement の push の直後に同じ確かめをしていて、これまで起きていない | 受け入れ |
| R3: `CLEAN|HAS_HOOKS` でも CI を待つので、承認の後の最終確認が CI の終わりまで待つ | CI が合格していれば 1 回の照会で終わる。待つのは CI がまだ終わっていないときだけで、それは待つべき場面 | 受け入れ |
| R4: `PBS_CI_TIMEOUT`・`PBS_CI_INTERVAL` を使う人の手順が壊れる | 使うのはテスト 2 本だけ（§1 調査結果）で、このイシューで直す | 回避 |
| R5: `test_pr_base_sync.sh` が PyYAML を要るようになり、無い環境で落ちる | ハーネスのテストは `run-all.sh` が uv の環境（PyYAML あり）で流す。無ければ `NO_JOBS` で合格のケースが落ちる（素通りしない） | 受け入れ |
| R6: I498（PR #528）を取り込んだブランチなので、#528 より先にマージすると I498 の変更も一緒に入る | #528 のマージを待ってから、このイシューのマージを依頼する（close で #528 がマージ済みかを確かめ、まだなら報告に書く） | 回避 |

## 9. 確定事項と自律判断
イシューに明記されている:
- `pr-base-sync.sh` の CI 待ちを `code-review.sh` の `wait_ci` を呼ぶ形に置き換える。読み込みは `REVIEW_LIB_SOURCE_ONLY=1`
- 終わり方は今のまま: 時間切れ（戻り値 3）は `⚠️ CI タイムアウト（<秒>秒）`・exit 1、失敗（戻り値 1）は `⛔ CI 失敗`・exit 1
- `NOT_PUSHED` は最終確認でも exit 1 で止め、メッセージで分かるようにする
- 含まない: `wait_ci` の判定そのものの変更・close/proceed の手順の流れの変更・CI の `timeout-minutes` の変更

Claude が決めた（技術的な選択と理由）:
- 別の bash で呼ぶ（同じシェルで読まない）— 同じシェルで読むと `code-review.sh` の `set -euo pipefail` と多数の関数が `pr-base-sync.sh` に入り、今の分岐（`$()` の失敗・`case` の扱い）の動きが変わりうる。I498 と同じ選択。スパイクで戻り値と結果の行が取れることを確かめた
- 合格の条件は「戻り値 0 かつ `CI_WAIT: OK`」の両方 — 片方だけだと、読み込みの途中の失敗などで取り違えたときに合格になりうる（R1）
- 上限・間隔の上書きは `CI_WAIT_TIMEOUT`・`CI_POLL_INTERVAL` に一本化し、`PBS_CI_TIMEOUT`・`PBS_CI_INTERVAL` は消す — 使うのはテストだけで、2 つの名前があると review-gate と final の値がずれる（一覧 I498 F2）。値の確かめは足さない: 数字でない・0 以下の値は `wait_ci` が時間切れ（exit 1）にして止まる側に倒れることをスパイクで確かめた
- 時間切れのメッセージの秒数は、子の bash が `wait_ci` と同じ式（`${CI_WAIT_TIMEOUT:-$CI_WAIT_TIMEOUT_DEFAULT}`）で出す — `code-review.sh` の本体（`:1208`）の時間切れのメッセージと同じ書き方。親は既定を読まない（sync で code-review.sh を読まずに済む）
- 待ちの途中の行は `tee` でそのまま出す（取り込んでから出さない）— close は背景で流すので、途中の様子が出力のファイルで見える
- `CLEAN|HAS_HOOKS` でも `run_wait_ci` を通す — イシューの目的「全部そろって合格するまで待ってから合格と言う」を、final の合格（exit 0）のすべての道に当てる。CI が終わっていれば照会 1 回で済む（R3）。イシューの解決方針は `ci_wait` の置き換えだけを書いているが、受け入れ条件の範囲内の補いで、仕様の追加ではない
- 関数の名前は `run_wait_ci`（`ci_wait` を残さない）— AC2 の「`ci_wait` 関数が無い」をそのまま満たし、判定を持つ関数と取り違えない
- 決定論テストは `test_pr_base_sync.sh` に足す（新しいファイルを作らない）— `final` の分岐のテストの置き場がここで、スタブも揃っている。失敗の注入は、写しに向けて同じテストを内側で流す形（`TARGET_SCRIPT` は I113 からある差し替え口）
- close の手順書（`.claude/skills/close/SKILL.md` 5.5）は変えない — `NOT_PUSHED` のときの直し方は `wait_ci` とこのスクリプトのメッセージ（「push してから final をやり直す」）が出し、手順 5.5 の「exit 1 は原因を見て直す」に当たる（イシューの「手順を変えない」）
- I498 のブランチを取り込んで作る — このイシューの変更点（`CI_WAIT_TIMEOUT_DEFAULT`・`test_i498_ci_wait_timeout.sh`）が I498 の上にしかない。#528 のマージを待ってからマージを依頼する（R6）。ユーザーへの確認は要らない（技術的な順序で、相互依存のイシューは自律で進める運用）
- 一覧 `scripts/claude/pr-base-sync.sh` I498 R1: 同梱 — このイシューそのもの
- 一覧 `scripts/claude/pr-base-sync.sh` I498 F2: 同梱 — 上書きの名前を `CI_WAIT_TIMEOUT` 1 つにして自然に消える（上記）
- 一覧 `scripts/claude/pr-base-sync.sh` I498 F3: 同梱 — sync が code-review.sh を読まなくなって自然に消える（TC-01 の T26）
- 一覧 `scripts/claude/pr-base-sync.sh` I498 F4: 残す — BEHIND の追従の後の待ちを無くすと、push の直後の古い `mergeStateStatus`（まだ BEHIND と出る）で空の取り込みを繰り返し上限に当たるおそれが新しく出る。最悪の合計待ちが長いのは base が進み続けるときだけで、今回の目的（待たずに通る穴）とは逆向き
- 一覧 `scripts/claude/code-review.sh` I498 F1: 同梱 — このイシューで同じコメントを直すので、並びも一緒に直す（4-2）
- 一覧 `.claude/skills/close/SKILL.md` I224 F1: 同梱（行を消す） — 「`final` は手元の HEAD と PR の head を比べない」がこのイシューで比べるようになる（`NOT_PUSHED` で exit 1）。手順 5.5 を流し直せば、push していないコミットで依頼へ進まない。実装対象のファイルの grep には当たらないが、イシューの解決方針に明記がある
- 一覧 `scripts/claude/code-review.sh` I206 F4・I207 F6/F7・I208 F2/F5・I212 F2/F3/F4/F6・I227 F1/F2/F4/F5/R1・I512 F2/F3/F6/F14/F15: 残す — どれも台帳・組み込みのレビュー・一時ファイルの話で、CI 待ちとは別（このイシューで code-review.sh はコメントしか変えない）
- 一覧 `FILE=-` I223 B1〜B4・I224 F9: 残す — bot の後片付け・I224 の測定で、このイシューと関係しない
- 規約の読み込み: `rules/ultimate_django_coding_standards.md`・`rules/react-coding-standards-integrated.md` は、このイシューがアプリのコード（Django・React）を変えないので当てはまる節が無い

要件適合性・業務ロジック:
- 受け入れ条件の範囲を超える仕様の追加は無い（`CLEAN|HAS_HOOKS` の待ちは AC1 の目的の範囲・上記）。マルチテナント・ステータス遷移・業務ルールの変更なし

セキュリティ・ベストプラクティス:
- セキュリティ影響なし（ハーネスのシェルスクリプトとテストだけ。認証・認可・機密データ・依存ライブラリの変更なし）。`bash -c` に渡すのは自分のフォルダの code-review.sh のパスと PR 番号だけで、`$1`・`$2` で渡し文字列に埋め込まない
- P3/P5/P8 影響なし（DB・外部 API・非同期・インフラの変更なし）。P6 影響なし（UI・データ量の懸念なし）。P9 影響なし（個人情報を扱わない）

設計品質:
- 判定の書き写しをなくす（1 か所）。空・取得失敗・想定外の戻り値はすべて止まる側（exit 1）。設定値は `code-review.sh` の 1 か所で、`pr-base-sync.sh` に数字を書かない

Danger Ops（有無/手順/ロールバック）:
- 無

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | `run_wait_ci` が合格（return 0）にするのは「戻り値 0 かつ最後の `CI_WAIT:` 行が `OK`」のときだけで、読み込みの失敗・想定外の戻り値・行の欠けがすべて exit 1 になるか（TC-01 の T22〜T25・TC-02 の T6） |
| V2 | 2 | 読んで可 | TC-01 の T22〜T24 が、古い判定（`pending` が無ければ合格）に戻した写し・CLEAN の待ちを消した写しで本当に NG になる（FG1・FG2）か。スタブのチェックの形が `wait_ci` の `--json name,bucket --jq` の出力（`<bucket>\t<name>`）と同じか |
| V3 | 3 | 読んで可 | final の exit 0 の道（`BLOCKED|UNSTABLE`・`CLEAN|HAS_HOOKS`）がすべて `run_wait_ci` を通り、BEHIND の追従の後も通るか。上限超え・失敗のメッセージと exit 1 が変わっていないか（TC-01 の T9・T22、TC-02 の T2・T5） |

## 計画変更記録
- 計画書の記載: 4-1「`⛔ CI 失敗（上の gh pr checks の出力を見る）`」／採った方法: 「`⛔ CI 失敗（上のチェックの一覧を見る）`」／理由: 計画レビューの Info（P4）。メッセージに `gh pr checks` の文字があると TC-03 の判定が本物のファイルで落ちる／計画レビューのやり直し: 不要（文言だけで、方式・範囲・受け入れ条件は変えない）

## レビュー結果
- [20261116_1218 判定: ✅ 完了](../../reviews/I530_plan_review_20261116_1218.md)
