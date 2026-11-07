# I212 計画書: 差分のレビューの起点を「見終えた最新の記録」にする（失敗した回の後にセキュリティレビューを飛ばさない）

## 基本情報
- **計画書ID**: plan_I212
- **関連イシュー**: #419（旧 #358）
- **Draft PR**: #421
- **作成根拠資料**: docs/issues/open/I212.md（起点イシュー・同梱 1〜6）
- **実装後評価**: docs/reviews/open/I212_review.md
- **作成日**: 2026-11-08

## 1. 背景/目的
- 高リスクの変更で組み込みの `/security-review` が動かなかった回（`OFFICIAL_SECURITY: FAILED`・HIGH）の後に 1 回だけやり直すと、`code-review.sh` は失敗した回の `REVIEWED_COMMIT` を差分の起点にする。起点の後に記録の場所の外が変わっていなければ「範囲 0 本」でレビュー役も `/security-review` も呼ばずに OK を出す（I211・I213・I200 で計 3 回）
- 目的: やり直しで、失敗した回が見るはずだった差分を必ず見直す。セキュリティレビューを一度も通らない変更が test-gate に進む道を無くす
- 同梱（§9 で採否を決めた）: 2・4（`/security-review` の「指摘なし」の読み違い）・6（G10 の `\b` の後退）

### 調査結果
- **原因の概要**: 差分のレビューの起点を「最後にレビューした場所」で選んでいて、「最後に最後まで見終えた場所」で選んでいない。見終えていない回も「見た」ことになる
- **詳細**:
  - `review_mode()`（`scripts/claude/code-review.sh:497-508`）は、`LEDGER_ROUND:` のある最新の記録（`latest_ledger_record`）の `REVIEWED_COMMIT` が HEAD の祖先なら、その SHA を起点にする。記録の判定の欄は見ていない
  - `/security-review` が動かなかった回も、レビュー役（code-reviewer）が正常に終われば `LEDGER_ROUND:` と `REVIEWED_COMMIT:` が書かれるので起点になる（I211 の `docs/reviews/closed/I211_code_review_20261029_0155.md`: `VERDICT: HIGH`・`LEDGER_ROUND: 2`）
  - やり直しでは `changed_outside_records "$SINCE" HEAD`（`code-review.sh:988-993`）が「変わっていない」を返し、`NO_DELTA=1` → レビュー役も組み込みのレビューも呼ばず `VERDICT: OK`（`..._0204.md`）
- **記録から「見終えたか」を読めるか**: 記録に残る機械の行は `VERDICT:`（合成した最終の判定）・`RISK:`・`REVIEWED_COMMIT:`・`LEDGER_ROUND:`。`OFFICIAL_SECURITY: FAILED` は標準出力だけで、記録には証跡の文（`- ⛔ 高リスク（パス判定 YES）で組み込みの /security-review が動かなかった…`）しか残らない。`VERDICT: HIGH` は「台帳に止める指摘が残った（見終えている）」でも付くので、`VERDICT` だけでは見終えたかを区別できない → 記録に `REVIEW_COMPLETE: YES|NO` の行を足す（§4-1）
- **同梱 2・4 の原因**: `official_security_verdict()`（`code-review.sh:176-182`）は、`run_official_review()` が付ける「読めていない」の注意（`official_output_readable()` の正規表現に当たらない）で HIGH にする。`/security-review` は日本語の文（「報告する脆弱性はありません。」）で書くことがあり、正規表現に当たらない（I200 の `I200_code_review_20261029_2240.md:129-132` で実例）。主題を直しても、この読み違いが残るとやり直しでも同じ FAILED になり止まる
- **スパイク（2026-11-08・成立）**: このブランチで `GH_APP_READONLY=1 timeout 900 claude -p --permission-mode plan --permission-prompts none --strict-mcp-config --append-system-prompt "このレビューの出力の最後の行には、報告する脆弱性の件数を SECURITY_FINDINGS: <件数> の形（半角数字・0 件なら SECURITY_FINDINGS: 0）で必ず 1 行だけ出す。" "/security-review"` を流すと、本文の最後が `報告する脆弱性はありません。` の後に `SECURITY_FINDINGS: 0` の 1 行で終わった（exit 0）。今の `official_output_readable()` は同じ本文を読めない（「報告する脆弱性はありません」は正規表現に当たらない）。→ 公式の CLI のフラグ（`--append-system-prompt`）で判定の 1 行を出させ、判定はその行（行全体が `SECURITY_FINDINGS: <数>` の行）だけで行う
- **同梱 6**: `scripts/claude/tests/test_i223_gh_app.sh:139` の `re.finditer(r"gh auth (status|token)\b", text)`。Python の `\b` は和文の文字も語の文字に数えるので、`gh auth tokenを打つ` で当たらず G10 が合格になる（I226 の台帳 F1）
- **環境前提**: `bash`・`python3`・`git`・`claude`（スパイクで動作確認）があることを確かめた。ツールの追加なし
- **既存テストのベースライン（2026-11-08・このブランチ）**: `test_i197_review_ledger.sh` pass=64 fail=0・`test_i193_official_flow.sh` pass=174 fail=0・`test_i202_ledger_cleanup.sh` pass=157 fail=0・`test_i223_gh_app.sh` pass=37 fail=0。全体は CI（Harness Tests）が正
- **消費箇所の grep（概念「差分の起点」の変更）**: `review_mode` の利用は `code-review.sh:967`（本体）とテスト（`test_i197_review_ledger.sh` R1・R9・FG-R1）。`latest_ledger_record` は `review_mode`・`--route`（`code-review.sh:908`）。説明の文は `.claude/skills/review-gate/SKILL.md:14`・`:36`、`docs/runbooks/review-rules.md:59`。`gate-check.sh` は最新の記録の `VERDICT` と `REVIEWED_COMMIT` だけを読み、起点は読まない（§4-4）

## 2. 受け入れ条件
- [ ] 最新の記録が「見終えていない回」（組み込みの `/security-review` が動かなかった・レビュー役の出力が壊れていた）のとき、やり直しの差分のレビューは、その前の見終えた記録（無ければブランチの分岐点＝ブランチ全体）を起点にする → TC-02（U1〜U3）
- [ ] その結果、失敗した回の後に記録の場所の外の変更が無くても、レビュー役と（高リスクなら）組み込みの `/security-review` が呼ばれる → TC-02（E1）
- [ ] 上の 2 点を失敗注入つきの決定論のテストで固定している（起点の選び方を前の形に戻すとテストが落ちる）→ TC-02（FG）
- [ ] 見終えていない回が 2 つ以上続いても、遡って最後の見終えた記録を起点にする → TC-02（U2）
- [ ] `gate-check.sh` は直さない（理由は §4-4）。失敗した回の記録・そのやり直しの記録での `gate-check.sh` の結果をテストで固定している → TC-02（E1）
- [ ] 台帳（指摘の番号・状態）と台帳の周の数は、起点にした記録ではなく台帳のある最新の記録から引き継ぐ → TC-02（U1・E1）
- [ ] 見終えたかの判定に使う欄（`REVIEW_COMPLETE:`）と、欄が無い古い記録の扱い（見終えていない扱い）を §4-1 に書いている
- [ ] 見終えた記録の後のやり直し（指摘が残って HIGH になった回の後を含む）は、今までどおりその記録から差分を取る → TC-02（U4）・TC-01（既存のテスト）
- [ ] 高リスクの変更で `/security-review` が「指摘なし」を日本語の文で書いても FAILED にならない（判定は `SECURITY_FINDINGS:` の行だけ）→ TC-03・M-01
- [ ] G10 が `gh auth tokenを打つ`（和文がすぐ続く形）を不合格にする → TC-04
- [ ] 既存のハーネステスト・CI がすべて pass する → TC-01・CI

（受け入れ条件 1 の「失敗した回」は、ユーザーの判断（2026-11-08「ループエンジニアリング、ハーネスエンジニアリングのベストプラクティスと開発をサクサク進めるという観点で問題ないやり方を選択して」）を受けて「見終えていない回」に定めた。指摘が残って HIGH になった回は見終えているので起点にしてよい（§9）。イシュー本文の受け入れ条件も同じ意味に合わせて直す）

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra（ハーネス）: `scripts/claude/code-review.sh`・`scripts/claude/tests/test_i212_review_base.sh`（新規）・`scripts/claude/tests/test_i197_review_ledger.sh`・`scripts/claude/tests/test_i193_official_flow.sh`・`scripts/claude/tests/test_i223_gh_app.sh`・`.claude/skills/review-gate/SKILL.md`・`docs/runbooks/review-rules.md`・`docs/issues/open/I212.md`（受け入れ条件の文言）
- `scripts/claude/gate-check.sh`・`scripts/claude/adversarial-review.sh`: 変更なし
- サービスの再起動: 不要

## 4. 変更点一覧（具体）

### 修正アプローチ
1. 記録ごとに「レビュー役と（高リスクなら）組み込みの `/security-review` が範囲を見終えたか」を `REVIEW_COMPLETE: YES|NO` の 1 行で残す
2. 差分のレビューの起点は、台帳のある記録のうち `REVIEW_COMPLETE: YES` で `REVIEWED_COMMIT` が HEAD の祖先の最新のもの。無ければブランチの分岐点（比べる相手との merge-base）を起点にして、ブランチ全体を差分のレビューとして見直す。台帳と周の数は今までどおり台帳のある最新の記録から引き継ぐ
3. `/security-review` には公式のフラグ `--append-system-prompt` で最後の行に `SECURITY_FINDINGS: <件数>` を出させ、動いたかの判定は行全体がその形の行があるかだけで行う
4. G10 の `\b` を英数字だけの先読みに替える

### 4-1. `scripts/claude/code-review.sh`: 見終えたかの行（`REVIEW_COMPLETE`）
修正方針: 判定を合成した後に、見終えたかを決定論で決め、記録に 1 行書く。組み込みのレビュー・レビュー役の本文の中の同じ形の行は無効にする（偽の行で起点を動かさない）。
- 決め方（本体・`REVIEWER_VERDICT` を決めた直後）:
  ```bash
  # I212: レビュー役と（高リスクなら）組み込みの /security-review が範囲を見終えたか。YES の記録だけが次の差分のレビューの起点になる
  # （台帳に止める指摘が残った HIGH は見終えているので YES。/security-review が動かなかった・レビュー役の出力が壊れた・台帳を作れなかったは NO）
  REVIEW_COMPLETE=NO
  if [ "$REVIEW_OK" = "1" ] && [ "$REVIEWER_VERDICT" = "OK" ] && [ "$SECURITY_VERDICT" = "OK" ]; then REVIEW_COMPLETE=YES; fi
  GATE_EVIDENCE+="- 見終えたか（次の差分のレビューの起点にできるか・I212）: ${REVIEW_COMPLETE}"$'\n'
  ```
  - 組み込みの `/code-review` の失敗（`OFFICIAL_CODE` が「実行できず」など）は条件に入れない（計画レビュー Warning 1）。`/code-review` の結果は合否に使わず、参考としてレビュー役に渡すだけなので、動かなくても範囲を見る役（レビュー役・高リスクなら `/security-review`）は見終えている
  - `NO_DELTA=1`（起点の後に記録の場所の外が変わっていない）の回は、レビュー役の代わりの本文で `REVIEW_OK=1`・`REVIEWER_VERDICT=OK`・`SECURITY_VERDICT=OK`（下の 4-3 の「差分なし」）になり YES。起点が見終えた記録なので、引き継いで見終えた扱いでよい
- 書く場所: `add_reviewed_commit` の直後、組み込みのレビューの出力を足す前に `printf 'REVIEW_COMPLETE: %s\n' "$REVIEW_COMPLETE" >> "$REVIEW_FILE"`
- 偽の行を無効にする: `neutralize_machine_lines()` の語の一覧に `REVIEW_COMPLETE` を足す（組み込みのレビューの出力）。`REVIEW_CLEAN` の sed（`code-review.sh:1193`）の `(LEDGER|LEDGER_ROUND)` を `(LEDGER|LEDGER_ROUND|REVIEW_COMPLETE)` にする（レビュー役の本文）
- 読む関数（新規・`record_reviewed_commit` の隣）:
  ```bash
  # I212: 記録が「見終えた」か（REVIEW_COMPLETE: YES の行があれば exit 0）。行が無い古い記録は見終えていない扱い
  # （起点にしない側＝見直す範囲が広がる側に倒す）
  record_complete() { grep -qE '^REVIEW_COMPLETE:[[:space:]]*YES[[:space:]]*$' "$1" 2>/dev/null; }
  ```
- 欄が無い古い記録: 見終えていない扱い。今このブランチより前に作った記録で進行中のイシューは無い（I212 自身の記録は新しい版で作る）ので、影響は「起点がさかのぼり、見直す範囲が広がる」だけ

### 4-2. `scripts/claude/code-review.sh`: 起点の選び方（`review_mode`）
修正方針: 全体か差分かの決め方（最新の台帳のある記録の `REVIEWED_COMMIT` が祖先でなければ全体＝rebase の後）と、台帳・周の数の引き継ぎは変えない。起点だけを「見終えた最新の記録」に替える。
```bash
# 全体か差分か: "full<TAB>1<TAB><TAB>" か "delta<TAB><n><TAB><起点の SHA><TAB><前の記録>"。
# 差分にするのは、台帳のある最新の記録の REVIEWED_COMMIT が今の HEAD の祖先のときだけ（rebase などで祖先でなければ全体）。
# I212: 起点は、台帳のある記録のうち見終えた（record_complete）最新の記録の REVIEWED_COMMIT（HEAD の祖先のものだけ）。
# 無ければブランチの分岐点（比べる相手との merge-base）＝ブランチ全体を差分のレビューとして見直す。
# 台帳と周の数（<n>・<前の記録>）は、起点に関係なく台帳のある最新の記録から引き継ぐ（I206 の番号の合流を壊さない）
review_mode() {   # $1=I### [$2=比べる相手（既定 origin/develop）]
  local last n sha rec base=""
  last=$(latest_ledger_record "$1")
  if [ -n "$last" ]; then
    n=$(grep -oE '^LEDGER_ROUND:[[:space:]]*[0-9]+[[:space:]]*$' "$last" | tail -1 | grep -oE '[0-9]+' || true)
    sha=$(record_reviewed_commit "$last")
    if [ -n "$n" ] && [ -n "$sha" ] && git merge-base --is-ancestor "$sha" HEAD 2>/dev/null; then
      while IFS= read -r rec; do
        sha=$(record_reviewed_commit "$rec")
        if record_complete "$rec" && [ -n "$sha" ] && git merge-base --is-ancestor "$sha" HEAD 2>/dev/null; then base="$sha"; fi
      done < <(ledger_records "$1")
      [ -n "$base" ] || base=$(git merge-base "${2:-origin/develop}" HEAD 2>/dev/null) || base=""
      if [ -n "$base" ]; then printf 'delta\t%s\t%s\t%s\n' "$(( n + 1 ))" "$base" "$last"; return 0; fi
    fi
  fi
  printf 'full\t1\t\t\n'
}
```
- 本体の呼び出し（`code-review.sh:967`）: `review_mode "$ISSUE" origin/develop`
- 本体の表示（`code-review.sh:975` の後）: 起点が前の記録の `REVIEWED_COMMIT` と違うときに 1 行出す: `（前の記録 <パス> は見終えていない〔REVIEW_COMPLETE: NO〕ため、見終えた最新の記録〔無ければブランチの分岐点〕から見直します）`
- 分岐点を起点にした差分のレビューは、`delta_files`・`delta_hunks`・見せるファイル・`changed_outside_records` がすべてブランチ全体と同じ範囲になる（起点＝merge-base）。レビュー役の入力は「差分のレビュー」の形のまま（前の周の止める指摘・台帳の残りも渡る）
- 先頭のコメント（`code-review.sh:495-496`）と `latest_ledger_record` のコメント（492 行目）を合わせて直す

### 4-3. `scripts/claude/code-review.sh`: `/security-review` の判定の 1 行（同梱 2・4）
修正方針: 組み込みのレビューの文の形に頼らず、公式の CLI のフラグで出させた 1 行だけで「動いた」を判定する。
- `run_official_review()` に省略できる第 2 引数（足す指示）を付け、あれば `--append-system-prompt "$2"` を付けて起動する（無ければ今と同じ起動）
  ```bash
  run_official_review() {   # $1=プロンプト $2=足す指示（省略可。--append-system-prompt で渡す）
    local prompt="$1" out rc=0 extra=()
    [ -n "${2:-}" ] && extra=(--append-system-prompt "$2")
    out=$(GH_APP_READONLY=1 timeout "${OFFICIAL_REVIEW_TIMEOUT:-900}" claude -p --permission-mode plan --permission-prompts none --strict-mcp-config ${extra[@]+"${extra[@]}"} "$prompt" 2>&1 < /dev/null) || rc=$?
    ...（以下は今のまま）
  ```
- 指示の文は定数にする（関数だけを読み込む側でも見えるよう、関数の定義の並びに置く）:
  ```bash
  # I212: /security-review に出させる判定の 1 行（official_security_verdict がこの行だけで「動いた」を決める）
  SECURITY_FINDINGS_PROMPT='このレビューの出力の最後の行には、報告する脆弱性の件数を SECURITY_FINDINGS: <件数> の形（半角数字・0 件なら SECURITY_FINDINGS: 0）で必ず 1 行だけ出す。'
  ```
- 呼び出し（`code-review.sh:1045`）: `run_official_review "/security-review" "$SECURITY_FINDINGS_PROMPT"`
- `official_security_verdict()`:
  ```bash
  # I212: 高リスク（パス判定 YES）では、組み込みの /security-review の出力に、行全体が
  # `SECURITY_FINDINGS: <数>` の行があるときだけ「動いた」（OK）。差分が無くて動かしていない回は OK。それ以外（実行できず・判定の行が無い）は HIGH
  official_security_verdict() {   # $1=RISK_PATH（YES/NO） $2=組み込みの /security-review の出力
    [ "$1" = "YES" ] || { echo OK; return; }
    [[ "$2" == *"(実行していない: 差分なし)"* ]] && { echo OK; return; }
    # here-string で渡す（pipefail の下で grep -q が先に終わって 141 になる誤判定を避ける。official_output_readable と同じ・I193 L1）
    if grep -qE '^SECURITY_FINDINGS:[[:space:]]*[0-9]+[[:space:]]*$' <<< "$2"; then echo OK; else echo HIGH; fi
  }
  ```
  - 「最後の行だけ」に限らない（計画レビュー Warning 3）: モデルが判定の行の後に締めの文を付けても FAILED にしない。行全体が固定の形の行だけを読むので、文の中に出てくる語（「SECURITY_FINDINGS: 0 と書く」など）では当たらない
  - 指摘の件数は判定に使わない（指摘の中身はレビュー役と台帳が扱う。今までどおり）
  - `SECURITY_FINDINGS` は `neutralize_machine_lines` の対象にしない（判定はこの行を読むため。記録の中のこの行を読む処理は無い）
- 本体の `⛔ … /security-review が動きませんでした（実行できず・読めていない）` の文を「（実行できず・判定の行 SECURITY_FINDINGS が無い）」に直す

### 4-4. `scripts/claude/gate-check.sh`: 変更しない（理由）
- `gate-check.sh` は「最新の記録の `VERDICT` が OK で、その `REVIEWED_COMMIT` の後に記録の場所の外が変わっていない」を確かめる。直した後の `code-review.sh` では:
  - 見終えていない回（`/security-review` が動かない・レビュー役の出力が壊れた）は必ず `VERDICT` が HIGH／BLOCKER になる（`SECURITY_VERDICT`・`REVIEWER_VERDICT` が `FINAL_VERDICT` に合成される）ので、その記録では通らない
  - そのやり直しの記録は、起点を見終えた記録（無ければ分岐点）にするので、失敗した回が見るはずだった差分をレビュー役と `/security-review` が見る。「範囲 0 本・OK」の記録は、見終えた記録の後に記録の場所の外が変わっていないときにしかできない
- よって gate-check に起点をたどる検査を足しても、`code-review.sh` が作る記録では結果が変わらない。足すと記録の形への依存が 2 か所になる。テスト（TC-02 E1）で、失敗した回の記録では `GATE_CHECK: FAIL REASON=verdict`、やり直しの記録では `GATE_CHECK: OK` で、そのやり直しでレビュー役と `/security-review` が呼ばれたことを固定する

### 4-5. `scripts/claude/tests/test_i212_review_base.sh`（新規）
- U（関数・一時のリポジトリ。`test_i197_review_ledger.sh` の `rec`・`lib` と同じ作り）:
  - U1: 記録 A（`LEDGER_ROUND: 1`・`REVIEW_COMPLETE: YES`・`REVIEWED_COMMIT: <c1>`）→ 記録 B（`LEDGER_ROUND: 2`・`REVIEW_COMPLETE: NO`・`<c2>`）→ `review_mode I900 develop` が `delta|3|<c1>|<B のパス>`（起点は A・周と前の記録は B）
  - U2: さらに記録 C（`LEDGER_ROUND: 3`・`NO`・`<c2>`）→ `delta|4|<c1>|<C>`（2 つ続いても A まで遡る）
  - U3: 見終えた記録が 1 つも無い（A を `NO` にする）→ `delta|4|<develop との merge-base>|<C>`
  - U4: 最新が `VERDICT: HIGH`・`REVIEW_COMPLETE: YES`（台帳に止める指摘が残った回）→ その記録の `REVIEWED_COMMIT` が起点（今までどおり）
  - U5: `REVIEW_COMPLETE` の行が無い記録は見終えていない扱い（起点にしない）
  - U6: 見終えた記録の `REVIEWED_COMMIT` が HEAD の祖先でない（rebase の前の枝）なら、その記録は起点にしない
  - U7: `official_security_verdict`: YES＋最後の行 `SECURITY_FINDINGS: 0` → OK／YES＋`SECURITY_FINDINGS: 2` → OK／YES＋日本語の「報告する脆弱性はありません。」だけ → HIGH／YES＋`SECURITY_FINDINGS: 0` の後に締めの文 → OK／YES＋文の中に `SECURITY_FINDINGS: 0` の語がある行だけ（行全体ではない）→ HIGH／YES＋`(実行できず: exit=124…)` → HIGH／YES＋`(実行していない: 差分なし)` → OK／NO → OK
  - U8: `neutralize_machine_lines` が `REVIEW_COMPLETE: YES` を `> REVIEW_COMPLETE: YES` にする
- E（本体の通し。`test_i202_ledger_cleanup.sh` の偽の `gh`・`claude` と同じ作り。偽の `claude` は、プロンプトが `/security-review` なら `$E2E_SEC` の中身〔既定は `SECURITY_FINDINGS: 0` で終わる文〕を返し、呼ばれた種類〔agent／code／security〕を書く）:
  - E1: `.github/` の下のファイルを変えたブランチ（パス判定 YES）で、1 周目は `/security-review` が判定の行を出さない（`E2E_SEC` に日本語の「報告する脆弱性はありません。」だけ）→ `FINAL_VERDICT: HIGH`・記録に `REVIEW_COMPLETE: NO`・gate-check は `REASON=verdict`。記録だけのコミットの後（記録の場所の外は変えない）に 2 周目（`E2E_SEC` は既定）→ 出力に `範囲のファイル 0 本` も `呼ばずに台帳を引き継ぎます` も無い・偽の `claude` の呼び出しに agent と security がある・`FINAL_VERDICT: OK`・記録に `REVIEW_COMPLETE: YES`・`LEDGER_ROUND: 2`・gate-check は `GATE_CHECK: OK`
  - E2: E1 の 2 周目の記録の後に、記録の場所だけを変えて 3 周目 → 今までどおり範囲 0 本でレビュー役を呼ばない・`REVIEW_COMPLETE: YES`（見終えた記録の後は I202 の動きのまま）
- FG（`broken`: 写しの文字列を置き換えて壊す）:
  - FG-U1: `if record_complete "$rec" &&` を `if :  &&` にする（見終えたかを見ない）→ U1 が `<c2>` になり不合格
  - FG-E1: 本体の写しの `review_mode` を前の形（最新の記録の SHA を起点）に戻す → E1 の 2 周目が `範囲のファイル 0 本` になり不合格
  - FG-U7: `official_security_verdict` の行頭の固定（`'^SECURITY_FINDINGS:`）を外して `'SECURITY_FINDINGS:` にする → U7 の「文の中に語がある行だけ → HIGH」が OK になり不合格
  - 直す前の版（develop の `official_security_verdict`）で U7 を流し、期待と違う行（例: 「報告する脆弱性はありません。」だけ → 前の版は注意が付かない入力なので OK）が出ることをステップ 1 の記録に残す
  - FG-U8: `neutralize_machine_lines` の一覧から `REVIEW_COMPLETE` を外す → U8 が不合格

### 4-6. 既存テストの直し（意図した振る舞いの変更に合わせる）
- `test_i197_review_ledger.sh`:
  - R1「LEDGER_ROUND: 2・祖先の REVIEWED_COMMIT → delta・3・起点」の記録に `REVIEW_COMPLETE: YES` を足す（見終えた記録が起点、という新しい決まりの例にする）
  - FG-R1 の `broken` の置き換え前の文字列を新しい `printf 'delta\t%s\t%s\t%s\n' "$(( n + 1 ))" "$base" "$last"; return 0` に合わせる
- `test_i193_official_flow.sh`:
  - C23「YES で読めた結果 → OK」の出力を `確信度の高い脆弱性は見つかりませんでした。` から、その後に `SECURITY_FINDINGS: 0` の行を足した形にする（判定の行が要る、という新しい決まり）
  - s8 は `"/security-review"` の文字列を探すだけなので、呼び出しに第 2 引数を足しても変えない（実装で確かめる）
  - R1 の他のケース（記録が無い・`LEDGER_ROUND` の無い記録だけ・祖先でない）は、第 2 引数を省いて既定の `origin/develop` が一時のリポジトリに無くても、起点を探す前に `full` で終わるので変わらない（計画レビュー Warning 2）。ステップ 1 で R1 が全部合格することを確かめ、変わるケースがあれば、そのケースに第 2 引数 `develop` を渡す。新しい `test_i212_review_base.sh` は常に `develop` を渡す
- `test_i202_ledger_cleanup.sh`: 偽の `claude` は `/security-review` を呼ばない作り（パス判定 NO）なので変えない。見終えた記録の後の通し（m・n）はそのまま合格するはず（TC-01 で確かめる）

### 4-7. `scripts/claude/tests/test_i223_gh_app.sh`（同梱 6）
- 139 行目: `r"gh auth (status|token)\b"` → `r"gh auth (status|token)(?![A-Za-z0-9_-])"`
- FG を 1 つ足す: `g10_fg "和文がすぐ続く auth token は不合格" 1 'gh auth tokenを打つ'`
- 冒頭の G10 の説明（111 行目付近）に「語の境目は英数字だけで見る（和文が続いても当たる・I212）」を足す

### 4-8. 説明の文
- `.claude/skills/review-gate/SKILL.md:14`: 「前の記録の `REVIEWED_COMMIT` からの直した差分」→「見終えた最新の記録（`REVIEW_COMPLETE: YES`）の `REVIEWED_COMMIT` からの差分（見終えていない回の後は、その前の見終えた記録〔無ければブランチ全体〕から見直す・I212）」。括弧の中の「台帳のある最新の記録の `REVIEWED_COMMIT` が HEAD の祖先なら差分のレビュー」は残す（全体か差分かの決め方は変えない）
- `.claude/skills/review-gate/SKILL.md:36`: `OFFICIAL_SECURITY: FAILED` の行に「やり直しは、見終えた記録から差分を取り直すので、動かなかった回が見るはずだった差分を `/security-review` が見る（I212）。判定は `/security-review` の出力の、行全体が `SECURITY_FINDINGS: <数>` の行だけで行う」を足す
- `docs/runbooks/review-rules.md:59`: 「前の記録の `REVIEWED_COMMIT` からの直した差分」→「見終えた最新の記録の `REVIEWED_COMMIT` からの差分（組み込みの `/security-review` が動かなかった回などは起点にしない・I212）」

### 4-9. `docs/issues/open/I212.md`
- 受け入れ条件 1・2 の「HIGH・BLOCKER・`OFFICIAL_SECURITY: FAILED`」を、§2 の注記のとおり「見終えていない回（組み込みの `/security-review` が動かなかった・レビュー役の出力が壊れていた）」に合わせる。受け入れ条件 7 の欄の名前を `REVIEW_COMPLETE` に合わせる。同梱 3・5 は別イシューに切り出したと書く（§9）

## 5. 実装手順（ステップ）
1. テストを先に書く: 4-5 の `test_i212_review_base.sh` と 4-6・4-7 のテストの直しを書き、直す前の本体で U1〜U3・U5・U7・U8・E1・G10 の新しい FG が落ちることを記録する → TC-02・TC-03・TC-04 参照
2. 4-1・4-2（見終えたかの行と起点の選び方）→ TC-02 参照（ステップ 1 が前提）
3. 4-3（`/security-review` の判定の 1 行）→ TC-03 参照（ステップ 2 と並行可）
4. 4-7（G10）→ TC-04 参照（並行可）
5. 4-8・4-9（説明の文）（ステップ 2・3 の後）。文言の有無の決定論テストは作らない（消すのが意図的な変更でしか起きない・`plan-writing-rules.md`「決定論テストの対象の選び方」）。中身はレビューで見る。構文は TC-05
- サービスの再起動は要らない（次の review-gate から新しい版が動く）

## 6. テスト計画
### 自動
- テストレベル: シェルの単体（関数を読み込む）と本体の通し（一時のリポジトリ・偽の `gh`・`claude`）。本物の GitHub・Claude は使わない
- 再発防止テスト: E1（I211・I213・I200 の再現）・U2（続けて失敗）・U7（I200 の日本語の文）・G10 の FG。どれも FG で不合格になることを確かめる
- 認可・テナント境界: 該当なし（アプリのコードを変えない）
- 詳細は `docs/tests/open/I212_auto_test.md`
### 手動
- `docs/tests/open/I212_manual_test.md`（すべて Claude。本物の `/security-review` を新しい版の `run_official_review` で動かし、判定が OK になるか）

## 7. ロールバック
- PR を revert する（設定・データの変更なし）。記録に足した `REVIEW_COMPLETE:` の行は、古い版では読まれないだけで害は無い

## 8. Risk & 回避策
- **見終えた記録が無いと、ブランチ全体を見直す（1 周目が `/security-review` の失敗だった I213 の形）**: 見直す範囲は 1 周目と同じで、台帳は引き継ぐので、止める指摘の番号は崩れない。新しい指摘が出うるが、それは 1 周目で見るはずだったもの
- **`/security-review` が判定の行を出し忘れる**: HIGH（FAILED）になり、review-gate の手順どおり 1 回だけやり直す（やり直しは見終えた記録から差分を取り直すので、同じ範囲を見る）。2 回続けば止める（止める条件 3）。スパイクでは出た
- **`--append-system-prompt` が組み込みのレビューの中身を変える**: 足すのは最後の行の形だけで、指摘の基準には触れない。スパイクの本文は今までと同じ形だった
- **偽の `REVIEW_COMPLETE: YES` の行で起点を動かす**: 組み込みのレビュー・レビュー役の本文の中の行は無効にする（4-1）。わざと記録を書き換えるのは対象外（「普通の書き方の事故」まで・I179 の決まり）
- **古い記録（欄が無い）が起点にならない**: 進行中のイシューは無い。あっても見直す範囲が広がる側

## 9. 確定事項と自律判断
イシューに明記されている:
- 差分の起点を、失敗した回ではなく前の合格した記録（無ければ全体）にする。台帳は最新の台帳のある記録から引き継ぐ。決定論のテストと失敗の注入で固定する。`gate-check.sh` は必要なら直し、直さないならその理由を書く
- 同梱 1〜6 の採否は計画で決める

ユーザーの判断（2026-11-08）:
- 「失敗した回」の範囲: ユーザーは「ループエンジニアリング、ハーネスエンジニアリングのベストプラクティスと開発をサクサク進めるという観点で問題ないやり方を選択して」と答えた → **見終えていない回（`/security-review` が動かなかった・レビュー役の出力が壊れた）だけを起点にしない**。台帳に止める指摘が残って HIGH になった回は見終えているので起点にする。理由: 指摘が残った回まで起点から外すと、fix-loop のたびにブランチ全体を見直すことになり、I197 の「差分だけを見て周を収束させる」設計が崩れる（I179・I193・I197 で、全体の見直しは新しい指摘が毎回出て減らないことを実測済み）。今回の穴の原因は「見ていない回を起点にした」ことだけで、ここを塞げば足りる

Claude が決めた（技術的な選択と理由）:
- **見終えたかを記録の新しい行 `REVIEW_COMPLETE` で残す**（仮定・技術的）: `VERDICT` は「指摘が残った HIGH」と「見ていない HIGH」を区別できない。証跡の文を読む形は文の形に頼る（同梱 2 と同じ穴）
- **見終えた記録が無いときは、全体のレビューではなく「分岐点を起点にした差分のレビュー」にする**（仮定・技術的）: 範囲はブランチ全体で同じだが、台帳（番号・止める指摘）と周の数を引き継げる。全体のレビューにすると台帳を作り直し、I206 の番号の合流の守りが外れる
- **`gate-check.sh` は直さない**（§4-4）
- **同梱 2・4 を入れる**: 主題を直しても、日本語の「指摘なし」で FAILED になる限り、やり直しでも同じ FAILED になって止まる（I200 の実例）。判定の 1 行は公式のフラグで出せることをスパイクで確かめた
- **同梱 6 を入れる**: 1 行の直しと FG 1 つで、ハーネスの最優先の印（I226 の retro）
- **同梱 3・5（敵対的レビューの「確認済み」の引き継ぎ・締め切りで実験が走らない）は別イシューに切り出す**: 対象が `adversarial-review.sh`・`adversarial-reviewer.md` で、差分のレビューの起点（このイシューの本題）とは仕組みが別。どちらも設計の検討（引き継ぐ条件・時間の配分）が要り、同じ PR に入れると高リスクの変更が大きくなる。retro で起票する（`issue-bootstrap`）
- **`--append-system-prompt` は `/security-review` だけに付ける**: `/code-review` の結果は合否に使わない（参考としてレビュー役に渡すだけ）ので、判定の行は要らない
- 要件・基本設計・UI/UX の仮定: なし（受け入れ条件の意味はユーザーの判断で確定）

台帳の残りの一覧（`grep -rnF` で実装対象のファイルと `FILE=-` に当たった行）:
- 一覧 I206 F4・I207 F6・I207 F7・I208 F1・I208 F2・I208 F3・I208 F5（`scripts/claude/code-review.sh`）: 残す — どれも台帳の合流・振り分け・一時ファイルの Low で、起点の選び方と `/security-review` の判定に関係しない
- 一覧 I226 F3・I223 F6（`scripts/claude/tests/test_i223_gh_app.sh`）: 残す — CRLF のつなぎ・G6 の検出の狭さで、G10 の語の境目とは別
- 一覧 I224 F9・I223 B1〜B4（`FILE=-`）: 残す — push の回数の実測（I224 の retro の後）と bot の停止の後始末で、このイシューと関係しない

要件適合性・業務ロジック:
- 受け入れ条件の範囲を超えた仕様の追加なし（同梱 2・4・6 はイシューの同梱で、計画で採ると決めた）。マルチテナント・ステータス遷移は該当なし
- エッジケース: 見終えた記録が無い（分岐点）・続けて失敗（遡る）・rebase の後（全体のまま）・欄の無い古い記録（見終えていない扱い）・差分なしの回（見終えた扱い）・比べる相手が無い（全体）

セキュリティ・ベストプラクティス:
- 入力: 記録の行は行頭の固定の形だけを読む（`^REVIEW_COMPLETE:[[:space:]]*YES[[:space:]]*$`）。組み込みのレビュー・レビュー役の本文の中の同じ形の行は無効にする
- 起動: `--append-system-prompt` の文は定数（差分の中身を入れない）。起動の形（plan モード・承認なし・読み取りだけの鍵・`--strict-mcp-config`）は変えない
- 機密データ・OWASP・依存ライブラリ: 該当なし（依存の追加なし）
- bandit・npm audit: 対象のコードなし（シェルとテストだけ）
- 「普通の書き方の事故」の範囲: 記録をわざと書き換える・組み込みのレビューにわざと偽の行を出させるのは対象外（I179）

P3/P5/P8 影響なし（DB・外部 API の新規・非同期・インフラの追加なし）。P6 影響なし（UI なし）。P9 影響なし（個人情報・テナントデータを扱わない）。

設計品質:
- 判定の本体は 1 か所（`record_complete`・`official_security_verdict`）。起点の選び方は `review_mode` の中だけ
- 例外処理: 読めない・欄が無い・git の失敗は、起点にしない（見直す範囲が広がる側）に倒す
- 設定値: 指示の文は定数 `SECURITY_FINDINGS_PROMPT`

Danger Ops: 無

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | `/security-review` が動かなかった回の後のやり直しで、記録の場所の外を変えていなくても、レビュー役と `/security-review` が呼ばれ、範囲が 0 本にならない（TC-02 E1） |
| V2 | 1 | 実験必須 | 見終えていない回が 2 つ以上続いても、最後の見終えた記録（無ければ分岐点）が起点になる。台帳と周の数は最新の記録から引き継ぐ（TC-02 U1〜U3） |
| V3 | 2 | 実験必須 | 台帳に止める指摘が残って HIGH になった回の後は、今までどおりその記録が起点（周が収束する動きを壊さない・TC-02 U4・TC-01） |
| V4 | 2 | 実験必須 | 組み込みのレビュー・レビュー役の本文の中の `REVIEW_COMPLETE: YES` の行が記録の判定の行として読まれない（TC-02 U8） |
| V5 | 3 | 実験必須 | `/security-review` が日本語の「指摘なし」で書いても、行全体が `SECURITY_FINDINGS: <数>` の行があれば OK（その後に締めの文があっても OK）、無ければ HIGH（TC-03・M-01）。新しい FG がすべて直す前の版で不合格になる（false-green でない） |

## 計画変更記録
1. 計画レビュー（20261108_0044・OK・高リスク判定 No）の Warning 3 件・Info 1 件への対応: (W1) §4-1 に「`/code-review` の失敗は見終えたかの条件に入れない」と理由を足した (W2) §4-6 に、既存の R1 の他のケースが第 2 引数なしでも変わらない理由と、ステップ 1 で確かめることを足した (W3) `official_security_verdict` を「最後の空でない行だけ」から「行全体が `SECURITY_FINDINGS: <数>` の行があるか」に緩めた（判定の行の後に締めの文が付いても FAILED にしない。行全体の固定の形なので文の中の語では当たらない）。U7・FG-U7・TC-03・V5 を合わせて直した (Info 1) 空の配列の展開を `${extra[@]+"${extra[@]}"}` にした。Info 2（欄の無い古い記録）は §8 のとおりで対応なし。計画レビューのやり直し: 不要（findings への対応で、方式・範囲・受け入れ条件は変えない）

## レビュー結果
- [20261108_0044 判定: ✅ 完了](../../reviews/I212_plan_review_20261108_0044.md)
（plan-review 段階が追記する）
