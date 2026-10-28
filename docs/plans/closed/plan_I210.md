# I210 計画書: ハーネスのテスト N10（敵対的レビューの締め切り）が実時間に依存して揺れるのを直す

## 基本情報
- **計画書ID**: plan_I210
- **関連イシュー**: #352
- **Draft PR**: #353
- **作成根拠資料**: docs/issues/open/I210.md（起点イシュー。#352 のコメント〔I195 の retro の同梱〕を本文に反映済み）
- **実装後評価**: docs/reviews/open/I210_review.md
- **作成日**: 2026-10-28

## 1. 背景/目的
- 背景: I206 で足した N10（敵対的レビューの実験役は、鍵を取った後も 2 回分の時間が無ければ呼ばない）は実時間で動き、境目までの余裕が約 1 秒しかない。I195 の implement 中、負荷の高いときに 3 回中 1 回落ちた。あわせて I195 の retro が、同じ「実行の条件で結果が変わる」種類の穴として、pipefail の下の `! A | grep -q …` が大きな入力で結果を反転させる形を同梱した
- 目的: ①締め切りの判定に使う時刻を外から渡せる形にし、N10・FG-N10（と同じ問題のあるテスト）が実時間を待たずに毎回同じ結果になる ②`! A | grep -q` の反転を直し、その形を止める決定論のテストを足す

### 調査結果
#### A. N10 の揺れ
- 原因の概要: 締め切りの判定が `date +%s`（実際の時計）を読み、テストは偽物の実験役が本当に 9 秒眠ることで境目を作っている。判定は「残り 12 秒未満か」で、2 本目の観点が鍵を取ったときの残りは通常 11 秒。余裕が約 1 秒で、時計の読みが少しずれると結果が入れ替わる
- 詳細な流れ（`scripts/claude/adversarial-review.sh`。N10 は `ADV_DEADLINE=20`・`ADV_MIN_STEP=6`・偽物の実験役は 9 秒眠る）:
  1. 観点 1・2 のレビュー役（偽物・すぐ返る）が実験案を返す。256 行で残り（`remaining()`・141 行）が `2 × 6 = 12` 以上なので往復を始める
  2. 先に鍵（`flock 9`・272 行）を取った観点が、273 行でも残り 20 秒前後を読んで実験役を呼ぶ（9 秒）
  3. もう一方は鍵を待ち、取った後に 273 行で残りを読む。正しくは 11 秒（< 12）で「締め切り」になり、実験役は 1 回だけになる
- スパイク（2026-10-28・このセッション。`/tmp/claude-1000/-mnt-c-app-study-app-multitenant/d4ef9c12-197e-4261-8873-b59489ed1bf1/scratchpad/n10_repro.sh`）: N10 だけを 2 回流すと、どちらも実験役は 1 回・締め切りあり。1 回目の実験役は開始から 0.16 秒〜9.16 秒。鍵の後の残りは 11 秒（整数の秒で切り捨てても、時計が進む限り 11 以下）
- 鍵の直列化はスパイクで確かめた（`{ flock 9; …; } 9>file` を背景で 2 本 → 1 本目が終わってから 2 本目が鍵を取る）。そのため「実験役が 2 回動いた」には、2 本目が鍵を取ったときの `date +%s` が開始から 8 秒以内だった（＝時計が実験の 9 秒ぶん進まなかった）ことが要る。負荷の高いときに何が起きたか（WSL2 の時計の補正による巻き戻しなど）は記録が残っておらず特定できない（未特定）。どの原因でも、テストが実際の時計を読まなければ起きない。直した後は負荷をかけて 20 回流して確かめる（手動 No.1）
- 根本原因（コード）: 141 行 `remaining() { echo $(( ADV_START + ADV_DEADLINE - $(date +%s) )); }`・361 行 `ADV_START=$(date +%s)`。時刻の読み先が固定で、テストが境目の前後を作るには本当に待つしかない
#### B. 同じく実時間で境目を作っているテスト（AC2・全件）
`grep -rnE 'sleep|ADV_DEADLINE=|STEP_TIMEOUT=|exec_sleep|time\.sleep|date \+%s' scripts/claude/tests/` の全件を分類した。

| テスト | 境目 | 余裕 | 扱い |
|---|---|---|---|
| `test_i202_ledger_cleanup.sh` N10・FG-N10 | 鍵の後の残り 11 秒 vs 12 秒 | 約 1 秒 | 直す（偽の時計） |
| 同 A1b | 締め切り 10・最小 4（判定 8）。最初の判定（256 行）を通るには開始から 2 秒以内 | 約 2 秒（開始の遅れで実験役が 0 回になる向き） | 直す（偽の時計） |
| 同 A1・FG-A1 | 実験役 1 秒の区間が重なるか。FG-A1（鍵なし）は 2 本目の実験役が 1 本目の 1 秒の間に始まることが要る | 約 1 秒（FG-A1 が不合格に倒れる向き） | 直す（偽物の実験役が相手の開始を待つ） |
| `test_i197_adversarial_process.sh` A5・FG-A5 | `ADV_STEP_TIMEOUT=3` で 30 秒眠る呼び出しを切る・全体が 20 秒以内 | 10 秒以上 | 直さない（本物の `timeout` で切ることを確かめる項目。時計の差し替えの対象外） |
| 同 A13・A17a | 最小の間隔の 2 倍が締め切りより大きい（いつでも締め切り） | 境目なし | 直さない |
| 同 A17b・A23・FG-A17・FG-A23 | `ADV_STEP_TIMEOUT=3` vs 30 秒 | 27 秒 | 直さない（本物の `timeout`） |
| 同 ほかの項目（`ADV_DEADLINE=60`・`ADV_MIN_STEP=1`） | 開始から 58 秒以内 | 58 秒 | 直さない |
| `test_pretooluse_gh_pr_guard.sh` G182・G188・G189・G203、`test_sessionstart_context.sh` TC-11c、`test_review_gates.sh` TC-RUN9 | 性能の上限・タイムアウト（時間を測ること自体が目的） | 1〜15 秒 | 別種（締め切りの判定ではない）。このイシューの対象外 |

#### C. `! A | grep -q` の反転
- 原因の概要: `set -o pipefail` の下では、パイプ全体の終了コードが「0 以外で終わった最後のコマンド」になる。`grep -q` が見つけてすぐ終わると、前のコマンドが書けずに SIGPIPE（141）で終わり、パイプが 0 以外になる。`!` がそれを「見つからなかった」に反転させる
- 規則の案を実際に流した（2026-10-28。`find scripts/claude -name '*.sh'` のうち pipefail を含むもの。`/tmp/claude-1000/-mnt-c-app-study-app-multitenant/d4ef9c12-197e-4261-8873-b59489ed1bf1/scratchpad/rule_spike.sh`）。当たったのは 4 か所（grill-me の時点の grep は、引用符の中の `|` で 2 か所を見落としていた）:

| 場所 | 向き | 扱い |
|---|---|---|
| `scripts/claude/check-frontend-evidence.sh:27` | 見逃し（`frontend/src/` を変えたのに「対象外」で合格） | 直す（4.4） |
| `scripts/claude/tests/test_i202_ledger_cleanup.sh:595`（`d3_bl`） | 見逃し（一覧の形の崩れた行を見逃す） | 直す（4.5） |
| `scripts/claude/tests/test_i193_official_flow.sh:527`（`s21_rules_prompt_old`） | 意図した前の形（FG-S21 が見逃すことを合格の条件にしている） | 消す（4.6・一覧 I195 F11 の同梱） |
| `scripts/claude/tests/test_posttooluse_check.sh:32` | 偽赤（stderr が大きいと「文言が無い」で不合格） | 書き換える（4.7） |

- `scripts/claude/tests/test_auto_test_template_lint.sh:70` の同じ形は pipefail が無いので当たらない（反転しない）
- 再現（スパイク・`/tmp/claude-1000/-mnt-c-app-study-app-multitenant/d4ef9c12-197e-4261-8873-b59489ed1bf1/scratchpad/fe_big.sh`）: `check-frontend-evidence.sh` に、`frontend/src/App.tsx` と 1000 個のファイル（一覧 91914 バイト）を変えたブランチを当てると、テストの記録が無いのに 20 回中 20 回 exit 0（対象外）。変更 2 個（201 バイト）では 10 回中 10 回 exit 1（正しい）
#### 環境の前提・ベースライン
- `bash`・`python3`・`git`・`flock`・`timeout`・`nproc` はハーネスとテストで既に使っている（新しい道具は無い）。`/proc/self/fd` は Linux（WSL2・CI の ubuntu）で使える（スパイク: `timeout` の子の python が fd 9 から鍵のファイルの場所を読めた・`fd9_spike.sh`）
- `/proc/locks` は `flock 9` の鍵を表示しない（鍵を取った flock のプロセスが終わるため。スパイク `locks_spike3.sh`）。待ちの検出には使えない（4.2 で別の印を使う理由）
- ベースライン（2026-10-28・develop 506f3ee）: `test_i202_ledger_cleanup.sh` pass=148 fail=0（58 秒）・`test_check_frontend_evidence.sh` pass=16・`test_posttooluse_check.sh` pass=6・`test_i193_official_flow.sh` pass=175・`test_i197_adversarial_process.sh` pass=115（すべて fail=0）

## 2. 受け入れ条件
イシューの AC と同じ（番号を振る）。
- AC1: N10・FG-N10 が実時間の経過を待たずに締め切りの判定を確かめ、マシンの負荷によらず同じ結果になる（CPU に負荷をかけた状態で 20 回続けて流し、20 回とも pass。負荷のかけ方は 4.8）
- AC2: 同じく実時間で境目を作っているテストを調べた結果が計画書にあり（調査結果 B）、同じ問題があるもの（A1b・A1/FG-A1）は同じ形で直っている
- AC3: 締め切りの判定を壊した写し（FG-N10 と同じ形）では N10 が不合格になる（失敗注入が効いたまま）
- AC4: `adversarial-review.sh` の本番の動き（既定の締め切り・間隔）は変わらない
- AC5: `docs/reviews/backlog/I206.md` から F5 の行が消えている
- AC6: `check-frontend-evidence.sh` が、変更ファイルの一覧が 64KB を超え先頭近くに `frontend/src/` があるときも「対象」と判定する（回帰テストあり）
- AC7: pipefail を含む `scripts/claude/` のシェルスクリプトに `! <コマンド> | grep -q` の形が無いことを確かめるテストがあり、その形を足した写しでは不合格になる（失敗注入が効く）
- AC8: `bash scripts/claude/tests/run-all.sh`（CI の Harness Tests）が pass する

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra（ハーネス）: `scripts/claude/adversarial-review.sh`・`scripts/claude/check-frontend-evidence.sh`・`scripts/claude/tests/test_i202_ledger_cleanup.sh`・`scripts/claude/tests/test_check_frontend_evidence.sh`・`scripts/claude/tests/test_posttooluse_check.sh`・`scripts/claude/tests/test_i193_official_flow.sh`・新規 `scripts/claude/tests/test_pipefail_negated_grep.sh`・新規 `scripts/claude/tests/stress-repeat.sh`・新規 `scripts/claude/tests/test_stress_repeat.sh`・`docs/reviews/backlog/I206.md`・`docs/reviews/backlog/I195.md`
- `path_risk_trigger()` の集合（`.github/`・`.pre-commit-config.yaml`・`.secrets.baseline`・見張り・settings）には触れない

## 4. 変更点一覧（具体）

### 4.1 時刻の読み先を 1 か所にし、外から渡せるようにする（AC1・AC4）
修正方針: 締め切りの計算に使う「今の時刻」を関数 `adv_now` 1 つに集める。環境変数 `ADV_CLOCK_FILE` があれば、そのファイルの中身（整数の秒）を今の時刻として読む。無ければ今までどおり `date +%s`。テストは時刻のファイルを書き換えて、待たずに境目の前後を作る。時刻を読めないときは「残り 0」として締め切りの側に倒す。

`scripts/claude/adversarial-review.sh`:
```bash
# 今の時刻（秒）。締め切りの計算はすべてこれを通す（I210）。ADV_CLOCK_FILE があれば中身（整数の秒）を読む
# （テストが実時間を待たずに締め切りの前後を作るため。既定は date +%s で、本番の動きは変わらない）。読めなければ 1
adv_now() {
  if [ -z "${ADV_CLOCK_FILE:-}" ]; then date +%s; return; fi
  local n=""
  { read -r n < "$ADV_CLOCK_FILE"; } 2>/dev/null
  [[ "$n" =~ ^[0-9]+$ ]] || return 1
  echo "$n"
}
# 時刻を読めなければ残り 0（締め切りの側に倒す。実験役を呼ばず、呼び出しも始めない）
remaining() { local n; n=$(adv_now) || { echo 0; return; }; echo $(( ADV_START + ADV_DEADLINE - n )); }
```
- 141 行の `remaining()` を上の 2 つに置き換える
- 361 行: `ADV_START=$(adv_now) || { echo "⛔ 今の時刻を読めません（ADV_CLOCK_FILE=${ADV_CLOCK_FILE}）"; echo "ADVERSARIAL_ERROR: CLOCK"; exit 2; }`
- 214 行 `t0=$(date +%s)`・309 行 `$(( $(date +%s) - t0 ))`・421 行 `ELAPSED=$(( $(date +%s) - ADV_START ))` も `adv_now` にする（記録の「所要」「所要時間（上限）」を締め切りと同じ時計で数える）。表示だけに使う値なので、時刻を読めなければ経過は 0 とする: `elapsed_since() { local n; n=$(adv_now) || { echo 0; return; }; echo $(( n - $1 )); }` を足し、309 行は `$(elapsed_since "$t0")`・421 行は `ELAPSED=$(elapsed_since "$ADV_START")`、214 行は `t0=$(adv_now) || t0=$ADV_START`（判定は `remaining()` が止める側に倒す）。記録のファイル名・見出しの日時（455・459 行の `date +%Y%m%d_%H%M` など）は実際の日時のまま
- 先頭の「環境変数」の説明（13〜15 行）に `ADV_CLOCK_FILE（テスト用。今の時刻〔整数の秒〕を読むファイル。既定は date +%s）` を足す
- 既定値の行（28〜29 行）・判定の式（256・273 行の `2 * ADV_MIN_STEP`）は変えない

### 4.2 テストの偽物の実験役を、時間を待たずに順番を作る形にする（AC1・AC2・AC3）
修正方針: 偽物の実験役は、眠って時間を進める代わりに、①順番の印を待ち ②偽の時計（`ADV_CLOCK_FILE`）を進める。順番の印は、本体が往復を始めると決めた後（256 行を通った後）・鍵の前に書くファイル `$RUN/p<n>/exec_in1.txt`。偽物の実験役は鍵のファイル（fd 9）の場所から `$RUN` を知る。

`scripts/claude/tests/test_i202_ledger_cleanup.sh` の偽物（298〜332 行）の実験役の分岐:
```python
if val("--tools") == "Bash":
    t0 = time.time()
    open(os.path.join(sd, f"start_{os.getpid()}"), "w").close()   # 実験役が始まった印
    def num(name, d):
        p = os.path.join(sd, name)
        return float(open(p).read()) if os.path.exists(p) else d
    wait_until = time.time() + num("exec_wait", 0)
    clock = os.environ.get("ADV_CLOCK_FILE")
    if clock:
        # 偽の時計: 実験する 2 観点がどちらも往復を始めると決めた（鍵の手前の exec_in1.txt を書いた）のを待ってから時計を進める。
        # こうすると、もう一方は必ず「鍵を取った後」に進んだ時計を読む（実時間の速さに左右されない）
        run = os.path.dirname(os.readlink("/proc/self/fd/9"))
        while len(glob.glob(os.path.join(run, "p*", "exec_in1.txt"))) < 2 and time.time() < wait_until:
            time.sleep(0.05)
        ok = len(glob.glob(os.path.join(run, "p*", "exec_in1.txt"))) >= 2
        open(os.path.join(sd, "barrier"), "a").write("ok\n" if ok else "timeout\n")
        now = int(open(clock).read()) + int(num("exec_advance", 0))
        tmp = clock + ".tmp"; open(tmp, "w").write(f"{now}\n"); os.replace(tmp, clock)
    else:
        # 実時間: ほかの実験役が始まるのを待つ（鍵があれば始まらないので exec_wait 秒で終わる。鍵が無ければ必ず重なる）
        while len(glob.glob(os.path.join(sd, "start_*"))) < 2 and time.time() < wait_until:
            time.sleep(0.05)
    open(os.path.join(sd, "spans"), "a").write(f"{t0} {time.time()}\n")
    …（以下は今のまま: init・tool_use・tool_result・result）
```
- `exec_sleep` は使わなくなる（既定 0.5 秒の眠りも無くす。ほかの A の項目は待たずに終わる）
- 書き換える項目（`arun` の引数で `ADV_CLOCK_FILE="$TMP/a_<名前>/sd/clock"` を渡し、時計は `1000000` から始める）:

| 項目 | 前 | 後 | 期待値（変えない） |
|---|---|---|---|
| A1 | `exec_sleep` 1 | `exec_wait` 10（実時間） | `2 yes OK` |
| FG-A1 | `exec_sleep` 1（鍵を外した写し） | `exec_wait` 10（実時間） | 区間が重なる（`no`） |
| A1b | 実時間・`ADV_DEADLINE=10 ADV_MIN_STEP=4`・7 秒眠る | 偽の時計・`ADV_DEADLINE=100 ADV_MIN_STEP=40`・時計を 70 進める・`exec_wait` 15 | `1 yes HIGH`（鍵の後の残り 30 は ADV_MIN_STEP 未満） |
| N10 | 実時間・`ADV_DEADLINE=20 ADV_MIN_STEP=6`・9 秒眠る | 偽の時計・`ADV_DEADLINE=100 ADV_MIN_STEP=30`・時計を 45 進める・`exec_wait` 15 | `1 yes` に加えて、順番の印が `ok` だけ（`barrier` に `timeout` が無い） |
| FG-N10 | 同上（鍵の後を 1 回分で比べる写し） | 同上 | 締め切りにならない（`no`） |

- 数の理由（N10）: 鍵の後の残りは 100 − 45 = 55。正しい判定（2 × 30 = 60）では締め切り、壊した写し（30）では実験役を呼ぶ。どちらも 5 以上の差があり、偽の時計なので実時間の速さで変わらない。本物の `timeout` に渡る秒（`step_timeout` = min(20, 残り)）は 10 秒以上になる（偽物はすぐ返る）
- N10 に「順番の印が `ok`」を足す理由: 本体の `exec_in1.txt` の名前・置き場所が将来変わると、順番の待ちが時間切れ（15 秒）になり、FG-N10 が揺れる側に戻る。その変化を「印が timeout」で毎回はっきり落とす（黙って揺れに戻らない）

### 4.3 時計の扱いのテスト（AC4・止める側の守り）
`scripts/claude/tests/test_i202_ledger_cleanup.sh` の I206 の節の後に「I210」の節を足す（項目は auto_test の TC-01 の表）:
- N15: `ADV_CLOCK_FILE` の中身が `abc` → exit 2・`ADVERSARIAL_ERROR: CLOCK`（FG: 起動時の確かめを外した写しでは exit 2 にならない）
- N16: `remaining()` は時刻を読めないとき 0、読めるとき `ADV_START + ADV_DEADLINE − 今`（関数だけを読み込んで確かめる。FG: 読めないときの 0 を外した写しでは 0 にならない）
- N17: `ADV_CLOCK_FILE` が無いとき `adv_now` は `date +%s` と同じ秒（前後 1 秒）
- N18: 既定値の 2 行（28〜29 行）が前と 1 字も違わない（FG: 既定値を変えた写しは不合格）
- N19: `date +%s` は `adv_now` の中の 1 か所だけ（締め切りの計算が実際の時計を直に読まない。FG: `remaining()` を前の形に戻した写しは不合格）

### 4.4 `check-frontend-evidence.sh` の反転を直す（AC6）
修正方針: パイプと `!` を使わず、bash の文字列の照合で「行の先頭が `frontend/src/` の行があるか」を決める（`grep -q '^frontend/src/'` と同じ意味）。
```bash
# パイプと ! を使わない（pipefail の下で grep -q が先に終わると前の printf が SIGPIPE で終わり、「対象外」に反転する・I210）
if [[ $'\n'"$CHANGED" != *$'\n'frontend/src/* ]]; then
```
- 27 行だけを置き換える（28〜30 行の「対象外」の出力・exit 0 は変えない）

`scripts/claude/tests/test_check_frontend_evidence.sh` に足す:
- `setup_big <名前> <frontend/src を変えるか yes|no> <余分のファイルの数>`: `zz/` の下に名前の長い（約 90 バイト）空のファイルを足したコミットを作る（記録は置かない）
- E16: `frontend/src/App.tsx` と余分 3000 個（一覧 約 27 万バイト）・記録なし → exit 1（対象。記録が無いので不合格）
- E17: 余分 3000 個だけ（`frontend/src/` を変えない）→ exit 0（対象外）
- E18: `docs/frontend/src/a.md` だけを変えた（行の途中の `frontend/src/`）→ exit 0（行の先頭だけを見る意味が変わらない）

### 4.5 `test_i202_ledger_cleanup.sh` の `d3_bl` を直す（調査結果 C）
修正方針: 一覧の行の形の確認を python 1 回にする（パイプと `!` を使わない。`BL_FORM` の `\S` を同じ意味で読める）。
```bash
d3_bl() { [ -d "$1" ] || return 0
  python3 -I -c 'import glob, re, sys
form = re.compile(sys.argv[2])
bad = [l for p in sorted(glob.glob(sys.argv[1] + "/*.md")) for l in open(p, encoding="utf-8").read().split("\n") if l.startswith("- F") and not form.search(l)]
sys.exit(1 if bad else 0)' "$1" "$BL_FORM"; }
```
- 期待値（D3・FG-D3・D3b）は変えない。読めないファイルは python が例外で 0 以外（止める側）

### 4.6 `test_i193_official_flow.sh` の前の形の写しを消す（一覧 I195 F11）
- 527・528 行（`s21_rules_prompt_old` と「FG-S21 前の形（パイプと !）では大きな入力の違反を見逃す」）を消す。525 行の「大きな入力でも違反を見逃さない」が回帰を捕まえる（F11 の指摘どおり）。前の形の見逃しはパイプの容量や grep の版に左右されるので、合格の条件にしない
- 522 行のコメントの「（前の形〔! grep | grep -qvF〕は 200 回とも見逃した）」は経緯として残す（コメントの行なので 4.7 の規則に当たらない）

### 4.7 `test_posttooluse_check.sh` の同じ形を書き換える
- 32 行: `if [ -n "$3" ] && [[ "$ERR" != *"$3"* ]]; then`（文字列として含むか。呼び出しの値 `syntax error` は正規表現の記号を含まないので意味は同じ）

### 4.8 規則のテストと、負荷をかけて繰り返す道具（AC1・AC7）
新規 `scripts/claude/tests/test_pipefail_negated_grep.sh`:
- 規則（python 1 回）: 渡されたシェルスクリプトのうち `set … -…o pipefail` を含むものについて、コメントでない行に「`!` と空白の後に、`|` に続く `grep` で `-q` を含む短いオプション・`--quiet`・`--silent` がある」形があれば、その行を出して 1。無ければ 0
  ```python
  PF = re.compile(r"^\s*set\s+(?:[^#\n]*\s)?-[A-Za-z]*o\s+pipefail\b", re.M)
  BAD = re.compile(r"(?:^|[\s;&({])!\s.*[^|]\|\s*grep\s(?:[^|]*\s)?(?:-[A-Za-z]*q[A-Za-z]*|--quiet|--silent)(?:\s|$)")
  ```
  - 粗い文字列の規則で、普通の書き方の事故を止める。行をまたぐ書き方（`\` の改行）・`head` など `grep -q` 以外の先に終わるコマンドは対象外（意図した回避も対象外）
- 項目（auto_test TC-01b）: G1 実物（`find scripts/claude -type f -name '*.sh'`）に当たりが無い／G2 見た pipefail のスクリプトが 20 本以上（対象が空で合格しない）／FG は写しで: 前の 4 か所の形・引用符の中に `|` がある形・`--quiet`・`set -o pipefail` と `set -euo pipefail` の両方で当たる／pipefail の無いスクリプト・コメントの行・直した形（`[[ … ]]`・awk 1 回・python 1 回）は当たらない
- 写しの作り方: テストの行そのものが規則に当たらないよう、`!` の代わりに `NOT` と書いた行を一時ファイルに書き、`NOT` を `!` に置き換える（印で除外する仕組みは作らない＝規則に抜け道を作らない）

新規 `scripts/claude/tests/stress-repeat.sh`（`test_` で始まらないので `run-all.sh` は流さない）:
- 使い方: `bash scripts/claude/tests/stress-repeat.sh <回数> <テストのスクリプト> [<負荷のプロセスの数（既定 nproc）>]`
- CPU を使い切るループ（`while :; do :; done`）を負荷の数だけ背景で動かし、テストを回数だけ順に流す。毎回 `RUN <n>: PASS|FAIL` を出し、最後に `STRESS: <合格>/<回数>`。全部合格で exit 0、1 回でも失敗で 1、使い方の誤りで 2。終わったとき・止められたとき（trap）に負荷のプロセスを止める
- 道具そのもののテスト: 新規 `scripts/claude/tests/test_stress_repeat.sh`（項目は auto_test の TC-01c。必ず合格するスクリプト・必ず落ちるスクリプト・2 回目だけ落ちるスクリプト・引数の誤りを当て、終了コードと `STRESS:` の行を確かめる。終わった後に負荷のプロセスが残らない）。AC1 の合否を決める道具が「いつも合格」にならないことを固定する（計画レビュー 20261028_1213 の Warning）
- 負荷のかけ方の理由: I195 で落ちたのは、裏でサブエージェント 4 つが動いて CPU が埋まっていたとき。CPU の数だけ回り続けるループで同じ状態（どのプロセスもすぐには走れない）を作る。新しい道具を入れずに CI と手元で同じ形にできる

### 4.9 一覧の行の削除（AC5・一覧 I195 F11）
- `docs/reviews/backlog/I206.md` から F5 の行を消す（F3・F4・F6 は残る）
- `docs/reviews/backlog/I195.md` から F11 の行を消す

## 5. 実装手順（ステップ）
1. 未知リスクを先に確かめる（偽の時計と順番の印で N10・FG-N10 が決まった結果になるか）: 4.1・4.2 → TC-01 の A1・FG-A1・A1b・N10・FG-N10、手動 No.1 の短い形（5 回）。ここで揺れるなら 4.2 の順番の作り方をやり直す（計画変更記録に書く）
2. 4.3（時計の扱いのテスト）を先に書いて落ちることを確かめる → 4.1 の残り（起動時の確かめ・`ELAPSED` など）→ TC-01 の N15〜N19
3. 4.8 の規則のテストを先に書き、今の 4 か所に当たって不合格になることを確かめる（Red）→ 4.4〜4.7 → TC-01b・TC-02・TC-03・TC-04
4. 4.9（一覧の行を消す）→ TC-01 の D3
5. 手動 No.1（負荷 20 回）・No.2（前の `check-frontend-evidence.sh` で E16 が落ちる）は test-gate で行う
- 依存: 2 は 1 の後（同じ関数）。3 は 1・2 と並行できる（別のファイル）が、`test_i202` の `d3_bl` は 1 の後に同じファイルで直す。4 は 1〜3 の後

## 6. テスト計画
### 自動（docs/tests/open/I210_auto_test.md）
- テストのレベル: ハーネスの単体（`remaining`・`adv_now` を `REVIEW_LIB_SOURCE_ONLY=1` で読み込む）・本体の通し（一時のリポジトリで偽物の claude を使って `adversarial-review.sh` を流す）・判定スクリプトの通し（一時のリポジトリで `check-frontend-evidence.sh`）・規則の文字列の確認。アプリのテスト（pytest・Jest・E2E）は非該当
- 再発防止: N10 の揺れは偽の時計の N10・FG-N10 と手動 No.1、`frontend/src/` の反転は E16、`! | grep -q` の形は規則のテスト（G1）で固定する
- 否定・不在の項目にはすべて失敗注入（FG）を付ける。前の形の見逃し（SIGPIPE）を合格の条件にする FG は作らない（パイプの容量に左右される・一覧 I195 F11）。E16 の効き目は手動 No.2 で 1 回確かめる
### 手動（docs/tests/open/I210_manual_test.md）
- No.1: 負荷をかけて `test_i202_ledger_cleanup.sh` を 20 回（AC1）
- No.2: 前の `check-frontend-evidence.sh`（develop 506f3ee）に E16 を当てると不合格になる（AC6 の失敗注入）

## 7. ロールバック
- PR を revert する（ハーネスのスクリプト・テスト・一覧ファイルだけ。データ・設定の変更は無い）。`ADV_CLOCK_FILE` は既定で使われないので、revert しても本番の動きは変わらない

## 8. Risk & 回避策
- 時計の差し替えが本番で効いてしまう → `ADV_CLOCK_FILE` が空のときは `date +%s` だけ（N17）。review-gate は `ADV_CLOCK_FILE` を渡さない。渡されても効くのは締め切りの計算だけで、`ADV_DEADLINE` を渡せるのと同じ信頼の範囲
- 時計を読めないまま進む（判定が締め切りを過ぎても実験役を呼ぶ向き） → 起動時に exit 2（N15）、途中で読めなければ残り 0（N16）
- 締め切りの計算が将来また `date +%s` を直に読む → N19 で 1 か所だけに固定
- 順番の印（`exec_in1.txt`・fd 9）の名前が変わり、FG-N10 が揺れる側に戻る → N10 で印の時間切れを毎回落とす（4.2）
- A1 が鍵ありでいつも 10 秒待つ（テストが遅くなる） → N10・A1b・FG-N10 の実時間の眠り（9＋9＋7 秒）が無くなるので全体は速くなる。FG-A1 は鍵なしで 2 本目の実験役が 10 秒以内に始まれば必ず重なる（前は 1 秒）
- `check-frontend-evidence.sh` の新しい照合が意味を変える → E1〜E15 の既存の期待値と E17・E18（行の途中の `frontend/src/`・対象外）で固定
- 規則が正しい書き方に当たる（誤検知） → 実物で当たるのは直す 4 か所だけ（調査結果 C）。当たったら書き方を直す（印で除外しない）

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ・解決方針・スコープ）:
- 時刻を外から渡せる設計にする（解決方針 1）。締め切りの決まり（`2 * ADV_MIN_STEP`）は変えない
- 同じく実時間で境目を作っているテストを調べ、同じ問題があれば同じ形で直す
- #352 の同梱: `check-frontend-evidence.sh` の反転の修正と回帰テスト・`! <コマンド> | grep -q` を止める規則のテスト（粗い文字列の規則でよい）・`test_posttooluse_check.sh` の書き換え
- 一覧 I206 の F5 を消す。F3・F4・F6 は扱わない

Claude が決めた（技術的な選択と理由。要件・基本設計・UI/UX の仮定は無い）:
- 時刻の注入点は `adv_now` 1 つ（`ADV_CLOCK_FILE` のファイルを読む）（仮定で決めた）。理由: 判定の 2 か所（256・273 行）と `step_timeout` がすべて `remaining()` を通るので、そこから読む時計を差し替えれば足りる。コマンドを渡す形（`ADV_NOW_CMD`）は任意のコマンドを実行させることになるので、読むだけのファイルにした
- 偽物の実験役の眠りは偽の時計を進める形にし、鍵の待ちの順番は本体が鍵の前に書く `exec_in1.txt` で作る（仮定で決めた）。理由: 偽の時計だけでは、もう一方の観点が「鍵の前の判定（256 行）」より前に時計が進むと 256 行で締め切りになり、FG-N10 が揺れる。`/proc/locks` は `flock 9` の鍵を表示しない（スパイク）ので、鍵の待ちは直接見られない
- 判定を関数に切り出して単体で確かめる案は採らない（仮定で決めた）。理由: N10 が固定したいのは「鍵を待った後に読み直す」通しの動きで、関数の単体では鍵の後かどうかを確かめられない
- A1・FG-A1 は実時間のまま、相手の開始を待つ形にする（仮定で決めた）。理由: 区間が重ならないこと（鍵の効き目）は実際の時刻でしか測れない。待ちの上限 10 秒は、鍵ありで毎回かかる時間と、FG-A1 の余裕（2 本目が始まるまで）の釣り合い
- 時刻を読めないときは残り 0（仮定で決めた）。理由: 締め切りの側（実験しない・未検証で合格にしない）に倒す
- `ELAPSED`・観点ごとの所要も `adv_now` で数える（仮定で決めた）。理由: 記録の「所要時間（上限 …）」を締め切りと同じ時計で比べられるようにする。本番では同じ `date +%s`
- 規則のテストは新しいファイル、規則は python で書く（仮定で決めた）。理由: どのイシューのテストにも属さない常設の規則。CI の awk（ubuntu の既定は mawk）の違いに左右されない
- 規則に除外の印を作らない（仮定で決めた）。理由: 印は規則の抜け道になる。意図した前の形（`test_i193` の 527 行）は消し、写しは `NOT` を置き換えて作る
- 負荷は CPU の数だけのループ・20 回の繰り返しは `stress-repeat.sh`（仮定で決めた）。理由: 4.8。単体のコマンドで流せる（複合のコマンドにしない）
- 手動 No.2 の失敗注入は、前の形の見逃しを合格の条件にする FG をテストに入れない代わりに、test-gate で 1 回確かめる（仮定で決めた）。理由: 一覧 I195 F11（パイプの容量に左右される）
- 一覧 docs/reviews/backlog/I206.md F5: 同梱 — このイシューそのもの（4.2）
- 一覧 docs/reviews/backlog/I206.md F3: 残す — イシューのスコープ外（`flock 9` の戻り値。締め切りの判定と別）
- 一覧 docs/reviews/backlog/I206.md F6: 残す — イシューのスコープ外（`check_worktree` の位置）
- 一覧 docs/reviews/backlog/I195.md F11: 同梱 — 4.6。規則のテスト（4.8）を足すと 527 行が当たるので、同じ変更で片付く
- 一覧 docs/reviews/backlog/I195.md F10: 残す — `s21_rules_prompt` のディレクトリ・引数 0 個の扱いで、時間・パイプの反転と関係しない（Low・再現なし）
- 一覧 docs/reviews/backlog/I208.md F4: 残す — `test_i202` の FG-Q4 の確かめ方で、このイシューの項目と関係しない
- 一覧 docs/reviews/backlog/I208.md F6: 残す — `test_i202` の `d1_208` の照合で、このイシューの項目と関係しない
- 高リスク判定: `adversarial-review.sh` は判定の仕組み（敵対的レビュー）で、締め切りの計算の時計を差し替えられるようにする。既定の時計・判定の式・既定値は変えず（N17〜N19）、読めないときは止める側に倒す（N15・N16）。`path_risk_trigger()` の集合には触れず、アプリの高リスクの条件（認証・認可・テナント境界・個人情報・決済など）にも当たらない → No の見立て（判定は plan-review）

要件適合性: 受け入れ条件の範囲を超えた仕様の追加は無い（`d3_bl`・`test_i193` 527 行は、AC7 の規則を実物で流して当たった同じ形の直し）。マルチテナント・ステータス遷移は非該当

セキュリティ・ベストプラクティス:
- セキュリティ影響なし（アプリのコード・認証認可・個人情報・依存ライブラリを変えない。bandit・npm audit の対象の変更なし）
- 入力の扱い: `ADV_CLOCK_FILE` の中身は整数の秒（`^[0-9]+$`）だけを受け付け、ほかは読めない扱い（実行しない・展開しない）
- `check-frontend-evidence.sh` は、判定が「対象外（合格）」へ反転する見逃しを無くす（止める側への修正）

P3/P5/P8 影響なし（DB・外部 API・非同期処理・インフラの追加なし。依存関係ファイルの変更なし）。P6 影響なし（UI・データ量の懸念なし）。P9 影響なし（個人情報・未成年データ・テナントデータを扱わない）

設計品質: 時刻の読み先は `adv_now` の 1 か所（N19）。設定値の追加は `ADV_CLOCK_FILE`（テスト用・既定なし）だけ。数の境目（N10・A1b）はテストの引数で、本体の既定値は変えない

Danger Ops（有無/手順/ロールバック）:
- 無（データ削除・破壊的変更・強制 push は無い。一覧の行の削除は記録の場所の通常の手順）

## 必ず確かめる項目
（高リスク判定が Yes になったときに敵対的レビューが使う。No なら使わない）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | `ADV_CLOCK_FILE` が空のとき、締め切りの判定（256・273 行）と `step_timeout` は `date +%s` で計算され、前と同じ値になる |
| V2 | 1 | 実験必須 | `ADV_CLOCK_FILE` の中身が整数でない・ファイルが無いとき、起動時は exit 2、途中では残り 0（実験役を呼ばない） |
| V3 | 2 | 実験必須 | 鍵の後の判定を 1 回分にした写し（FG-N10）では、偽の時計の N10 が毎回不合格になる（順番の印が ok） |
| V4 | 2 | 実験必須 | 規則のテストは、`! printf … \| grep -q …` を足した pipefail のスクリプトの写しで不合格になる |
| V5 | 3 | 読んで可 | `check-frontend-evidence.sh` の新しい照合は、行の先頭の `frontend/src/` だけを対象にし、一覧の大きさで結果が変わらない |

## 計画変更記録
（実装中に計画と違うことをするときに書く）
- 1（計画レビュー 20261028_1213 の Warning 対応・2026-10-28）: Warning 1 は 4.8 に `stress-repeat.sh` の失敗注入つきテスト（`test_stress_repeat.sh`・TC-01c）を足した。Warning 2 は 4.1 に、表示だけの経過の秒は時刻を読めなければ 0 とする `elapsed_since()` を書いた。Warning 3（規則の誤検知）は許容（イシューに「粗い規則でよい」・除外の印を作らない方針）。Info 2 件は対応不要。方式・範囲・受け入れ条件は変えないので再レビューはしない
- 2（implement の /simplify・2026-10-28）: 計画書の記載「4.4 `[[ $'\n'"$CHANGED" != *$'\n'frontend/src/* ]]`」「4.5 `d3_bl` を python 1 回に」「4.7 `[[ "$ERR" != *"$3"* ]]`」「E16・E17 は余分 3000 個」。採った方法: 4.4・4.7 はリポジトリに既にある書き方（`code-review.sh:91` のヒアストリング `grep -q … <<< "$X"`・I193）にそろえた（パイプが無いので SIGPIPE で反転しない。4.7 は正規表現の意味もそのまま）。4.5 は `[ -z "$(cat … | grep -E '^- F' | grep -vE "$BL_FORM")" ]`（`-q` を使わず全部読むので反転しない・grep の正規表現のまま）。E16・E17 は 1000 個（一覧 約 9 万バイト。64KB を超え、前のスクリプトで E16 が落ちることを確かめた）。あわせて規則のテストの走査を 1 回に、N17 は `lib` を使う形に、FG-N16 の写しは専用の場所に置いた。理由: 書き方を 1 つにそろえる・読みやすさ・テストの時間。判定と期待値は同じ（TC-01・TC-01b・TC-02・TC-03 と手動 No.2 を流し直して確かめた）。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件は変えない）

## レビュー結果
- [20261028_1213 判定: ✅ 完了](../../reviews/closed/I210_plan_review_20261028_1213.md)
