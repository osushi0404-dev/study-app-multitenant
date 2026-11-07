# I227 計画書: レビューの判定が文の形・表示の文字列に頼っている残りを、機械が読む形・変数に置き換える

## 基本情報
- **計画書ID**: plan_I227
- **関連イシュー**: #422
- **Draft PR**: #424
- **作成根拠資料**: docs/issues/open/I227.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I227_review.md
- **作成日**: 2026-11-08

## 1. 背景/目的
- I212 で、組み込みの `/security-review` の「動いた」の判定を、`--append-system-prompt` で出させた `SECURITY_FINDINGS: <数>` の行だけにした。同じ「判定を文の形・表示の文字列に頼る」作りが 2 か所残っている
  1. `official_security_verdict()` が、出力のどこかに `(実行していない: 差分なし)` の文字列があれば OK にする（I212 の台帳 F1・Medium・再現あり。止める側に倒れない向き）
  2. `official_output_readable()` が、`/code-review` の「読めたか」を和文・英文の「指摘なし」の正規表現で決める（記録の注意と実際が食い違う）
- 目的: レビューの合否・「読めたか」の判定が、組み込みのレビューの文章や、表示用の文字列に左右されない状態にする

### 調査結果
- **原因の概要**: 「差分が無くて動かしていない」という事実を、スクリプト自身が表示用に書いた文字列で受け渡している。`/code-review` の「読めたか」も、文の言い回しで当てている
- **詳細**:
  - `code-review.sh:1058-1060`: `NO_DELTA=1` のとき、`(実行していない: 差分なし)` を `$OFFICIAL_DIR/code`・`security` に書く。`:1115-1120` で `security_note` と連結した `OFFICIAL_SECURITY` を `official_security_verdict "$RISK_PATH" "$OFFICIAL_SECURITY"` に渡す
  - `code-review.sh:186`: `[[ "$2" == *"(実行していない: 差分なし)"* ]] && { echo OK; return; }`。部分一致なので、`/security-review` が本文でこの文字列を引用しただけで（判定の行が無くても）OK になる。変数 `NO_DELTA`（`:1014`）は判定より前にいつも決まっている
  - `code-review.sh:89-98` `official_output_readable()`: `"file":` の行・`[]` だけの行・`SECURITY_FINDINGS:` の行・和文／英文の「指摘なし」の正規表現のどれかで「読めた」とする。`run_official_review()`（`:163`）が `/code-review`・`/security-review` の両方の出力に使う
  - `SECURITY_FINDINGS` の正規表現が `:95` と `:188` に重複（I212 の台帳 F7）
- **スパイク（2026-11-08・判定の行は不成立 → 設計をやり直した）**: `GH_APP_READONLY=1 timeout 900 claude -p --permission-mode plan --permission-prompts none --strict-mcp-config --append-system-prompt "このレビューの出力の最後の行には、報告する指摘の件数を CODE_FINDINGS: <件数> の形（半角数字・0 件なら CODE_FINDINGS: 0）で必ず 1 行だけ出す。" "/code-review medium <範囲>"` を 2 つの範囲で流した（スクリプトは scratchpad の `spike_code_review.sh`）
  - 範囲 `origin/develop...HEAD`（文書だけ）: exit 0。出力は ```` ```json ```` の囲みの中の指摘の配列（要素は `"file"`・`"line"`・`"summary"`・`"failure_scenario"` を持つオブジェクト）で終わり、`CODE_FINDINGS:` の行は無かった
  - 範囲 `1c6ebdd9...f3ff5c1f`（I212 のマージ。コードの差分）: exit 0。同じく ```` ```json ```` の囲みの配列で終わり、`CODE_FINDINGS:` の行は無かった
  - 過去の記録（`docs/reviews/closed/I212_code_review_20261108_0100.md:74`・`I226_code_review_20261106_2139.md:66`・`I224_code_review_20261107_2228.md:66`）の `/code-review` の出力も、すべて ```` ```json ```` の囲みの配列だった。「読めていない」の注意が付いた過去の記録 6 件はすべて `/security-review` の和文の出力（I212 で直した側）
  - → `/code-review` は公式の手順が出力の形（指摘の JSON 配列）を決めていて、足した指示に従わない。**`/code-review` の「読めたか」は、判定の行ではなく、公式の決まった出力の形（JSON として読める指摘の配列）で決める**（§4-3）。`--append-system-prompt` は `/code-review` には付けない（効かず、雑音になるだけ）
- **環境前提**: `bash`・`python3`・`git`・`claude` があることを確かめた（スパイクで動作確認）。ツールの追加なし
- **既存テストのベースライン（2026-11-08・このブランチ・直す前）**: `test_i212_review_base.sh` pass=31 fail=0・`test_i193_official_flow.sh` pass=174 fail=0・`test_i197_review_ledger.sh` pass=64 fail=0。全体は CI（Harness Tests）が正
- **消費箇所の grep（概念「差分なし」「読めたか」の判定の変更）**:
  - `official_security_verdict` の呼び出し: `code-review.sh:1120`（本体）・`test_i212_review_base.sh:68`（`osv`）・`test_i193_official_flow.sh:351-354`（C23）
  - `official_output_readable` の呼び出し: `code-review.sh:163`（`run_official_review` の中）・`test_i193_official_flow.sh:330-335`（テストの番号 C8・C12）・`test_i212_review_base.sh:78`
  - `run_official_review` の呼び出し: `code-review.sh:1063`・`:1071`。テストの文字列照合: `test_i197_review_ledger.sh:185`（`run_official_review "/code-review medium ${REVIEW_RANGE}"` の部分一致）・`test_i193_official_flow.sh:425`（s8: `"/code-review medium ${REVIEW_RANGE}"`・`"/security-review"` の部分一致）。第 2 引数を後ろに足す形なら、どちらも部分一致のまま通る
  - `(実行していない: 差分なし)` の文字列: `code-review.sh:186`（判定・消す）・`:1059-1060`（表示・残す）・`test_i212_review_base.sh:75`
  - 説明の文: `.claude/skills/review-gate/SKILL.md:36`（`SECURITY_FINDINGS` の判定）。`docs/runbooks/review-rules.md` には読み取りの判定の説明が無い（grep で「読めていない」「指摘の配列」の該当なし）→ 変えない
- **ついでに見つけたもの（範囲の外）**: スパイクの出力の先頭に、`drop_cli_warnings()`（`code-review.sh:102`）が除かない新しい形の警告（`Permission allow rule "Read(*)" adds nothing …`）が出ている。記録に雑音が入るだけで、§4-3 の判定（```` ```json ```` の囲みを探す）には影響しない。retro で一覧に回す

## 2. 受け入れ条件
- [ ] `/security-review` の出力に `(実行していない: 差分なし)` の文字列が含まれていても、判定の行が無く、実際に差分なしで動かしていない回（`NO_DELTA=1`）でなければ HIGH になる。実際に差分なしで動かしていない回は、出力の中身に関係なく OK のまま → TC-02（U9・FG-U9）・TC-04（E2・FG-E2）
- [ ] `/code-review` の「読めたか」が、公式の決まった出力の形（JSON として読める指摘の配列）だけで決まり、和文・英文の「指摘なし」の文の形に左右されない → TC-03（U10・FG-U10）・M-01
- [ ] 判定の行（`<名前>: <数>`）の正規表現が 1 か所（`findings_line_present`）にまとまっている → TC-05
- [ ] 既存のハーネステスト・CI がすべて pass する → TC-01・CI

（受け入れ条件 2 の「決まった形の判定の行」は、スパイクで `/code-review` が足した指示に従わず、公式の決まった形の JSON 配列だけを出すと分かったので、「公式の決まった出力の形（JSON 配列）」に置き換えた。条件の狙い〔文の形に左右されない〕は変えない・§9。イシュー本文も合わせて直す）

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra（ハーネス）: `scripts/claude/code-review.sh`・`scripts/claude/tests/test_i212_review_base.sh`・`scripts/claude/tests/test_i193_official_flow.sh`・`.claude/skills/review-gate/SKILL.md`・`docs/issues/open/I227.md`（受け入れ条件 2 の文言・古いパス）・`docs/reviews/backlog/I212.md`（同梱した F5・F7 の行を消す）
- `scripts/claude/gate-check.sh`・`adversarial-review.sh`・`docs/runbooks/review-rules.md`・`test_i197_review_ledger.sh`: 変更なし
- サービスの再起動: 不要

## 4. 変更点一覧（具体）

### 修正アプローチ
1. 「差分が無くて動かしていない」は、表示の文字列ではなく変数 `NO_DELTA` を `official_security_verdict()` の引数で渡して決める。表示の文字列は表示のためだけに残す
2. 判定の行（`<名前>: <数>`）を読む正規表現を関数 `findings_line_present()` の 1 か所にまとめる（I212 の台帳 F7）
3. 「読めたか」は、レビューの種類（`code`／`security`）ごとに決まった形だけで決める。`security` は判定の行 `SECURITY_FINDINGS`、`code` は公式の決まった出力の形（JSON として読める指摘の配列）。和文・英文の「指摘なし」の正規表現・`"file":` の行・`[]` の行の当て方は消す

### 4-1. `official_security_verdict()`: 「差分なし」を引数で受ける
修正方針: 判定を、出力の中身ではなく、本体が決めた事実（`NO_DELTA`）で行う。
```bash
# I193 7 回目 H2・I212・I227: 高リスク（パス判定 YES）で組み込みの /security-review が動かなかったら HIGH。
# 「動いた」は、出力に判定の行（findings_line_present SECURITY_FINDINGS）があるときだけ。差分が無くて動かしていない回
# （本体の NO_DELTA=1）は OK。表示の文字列「(実行していない: 差分なし)」では決めない（出力がそれを引用しても OK にしない・I227）
official_security_verdict() {   # $1=RISK_PATH（YES/NO） $2=NO_DELTA（1=差分なしで動かしていない） $3=組み込みの /security-review の出力
  [ "$1" = "YES" ] || { echo OK; return; }
  [ "$2" = "1" ] && { echo OK; return; }
  if findings_line_present SECURITY_FINDINGS "$3"; then echo OK; else echo HIGH; fi
}
```
- 本体の呼び出し（`:1120`）: `SECURITY_VERDICT=$(official_security_verdict "$RISK_PATH" "$NO_DELTA" "$OFFICIAL_SECURITY")`
- `:1059-1060` の表示の文字列はそのまま（記録とレビュー役への入力の表示）
- `NO_DELTA` が `1` 以外（`0`・空・他の値）はすべて「動かした回」として判定の行を求める（止める側に倒れる向き）

### 4-2. `findings_line_present()`（新規）: 判定の行の正規表現を 1 か所に
```bash
# I212・I227: 組み込みのレビューに出させた判定の 1 行（行全体が `<名前>: <数>`）があるか（exit 0＝ある）。
# 判定の行の正規表現はここだけ（I212 F7: 2 か所にあると、片方だけ変えて判定と記録の注意が食い違う）。
# 行全体の固定の形だけを読む（文の中の語では当たらない）。出力のどこにあってもよい（締めの文が後に付いても読む・I212 W3）。
# here-string で渡す（pipefail の下で grep -q が先に終わって 141 になる誤判定を避ける・I193 L1）
findings_line_present() {   # $1=行の名前（コードの中の定数だけを渡す） $2=出力
  grep -qE "^${1}:[[:space:]]*[0-9]+[[:space:]]*\$" <<< "$2"
}
```
- 置き場所: `official_output_readable()` の前

### 4-3. `official_output_readable()`・`run_official_review()`: 種類ごとの決まった形だけで「読めたか」を決める
修正方針: 文の言い回しを当てる正規表現をやめ、`security` は判定の行、`code` は公式の決まった出力の形（JSON として読める指摘の配列）で決める。種類を知らない呼び出しは「読めていない」に倒す。
```bash
# I193・I227: 組み込みのレビューの出力が「対象を読めた結果」か（exit 0＝読めた）。文の言い回し（「指摘なし」など）では決めない。
#   security: 判定の行 SECURITY_FINDINGS があるとき（--append-system-prompt で出させる・I212）
#   code: 公式の /code-review の決まった出力の形（JSON として読める指摘の配列）があるとき。/code-review は足した指示に従わず
#         この形だけを出す（I227 のスパイク）。配列の要素はすべて "file" を持つオブジェクト（空の配列は「指摘なし」として読めた結果）
#   それ以外の種類: 読めていない扱い
official_output_readable() {   # $1=種類（code / security） $2=出力
  case "$1" in
    security) findings_line_present SECURITY_FINDINGS "$2" ;;
    code) official_findings_json_present "$2" ;;
    *) return 1 ;;
  esac
}

# I227: 出力に、JSON として読める指摘の配列があるか（exit 0＝ある）。```（言語名は何でもよい）の囲みの中を順に試し、
# 囲みが 1 つも無ければ出力全体を試す。どれかが「要素がすべて "file" を持つオブジェクトの配列」なら読めた結果
official_findings_json_present() {   # $1=出力
  python3 -I -c '
import json, re, sys
text = sys.stdin.read()
blocks = re.findall(r"^```[A-Za-z0-9_+-]*[ \t]*\n(.*?)^```[ \t]*$", text, re.M | re.S) or [text]
def ok(s):
    try:
        v = json.loads(s)
    except ValueError:
        return False
    return isinstance(v, list) and all(isinstance(e, dict) and "file" in e for e in v)
sys.exit(0 if any(ok(b) for b in blocks) else 1)
' <<< "$1"
}
```
- `run_official_review()` の第 2 引数を「足す指示」から「種類」に替える。`security` のときだけ `--append-system-prompt "$SECURITY_FINDINGS_PROMPT"` を付ける:
  ```bash
  run_official_review() {   # $1=プロンプト（例: /code-review medium origin/develop...HEAD） $2=種類（code / security。読めたかの決め方と足す指示を選ぶ）
    local prompt="$1" kind="$2" out rc=0 extra=()
    # I212: /security-review には判定の 1 行を出させる。/code-review は足した指示に従わないので付けない（I227 のスパイク）
    [ "$kind" = "security" ] && extra=(--append-system-prompt "$SECURITY_FINDINGS_PROMPT")
    ...（起動は今のまま）
    if ! official_output_readable "$kind" "$out"; then
      printf '(注意: 出力に決まった形の結果〔/code-review は指摘の JSON 配列・/security-review は SECURITY_FINDINGS の行〕が無く、対象を読めていない可能性がある。この出力は判定の根拠にしない)\n'
    fi
    ...
  ```
  - `[ … ] && extra=(…)` は偽で 1 を返すが、関数の途中の行なので `set -e` でも止まらない（`set -e` は `&&` の左の失敗を無視する）。実装では `if` の形にしてもよい（振る舞いは同じ）
- 呼び出し（`:1063`・`:1071`）: `run_official_review "/code-review medium ${REVIEW_RANGE}" code`・`run_official_review "/security-review" security`
- `SECURITY_FINDINGS_PROMPT` は `run_official_review()` の中で使うので、定数の定義を `run_official_review()` の前（`official_output_readable()` の近く）へ移す（関数だけを読み込む側でも見える並びのまま）
- `SECURITY_FINDINGS` は今までどおり `neutralize_machine_lines` の対象にしない（判定はこの行を読むため）
- 正規表現 `^```(?:json)?…` は囲みを探すだけで、言い回しは当てない。読めたかの決め手は `json.loads` が配列を返すか

### 4-4. 説明の文（`.claude/skills/review-gate/SKILL.md:36`・I212 の台帳 F5 を同梱）
- 今: 「やり直しは見終えた記録から差分を取り直すので、動かなかった回が見るはずだった差分を `/security-review` が見る。」
- 直す: 「やり直しでは、差分が無い（`NO_DELTA`）近道でも `/security-review` を飛ばさないので、動かなかった回の分も `/security-review` が見る（`/security-review` は範囲を受け取らず、毎回ブランチ全体を見る）。」
- 同じ行の末尾に「差分が無くて動かしていない回だけは、本体の変数 `NO_DELTA` で OK にする（出力の文字列では決めない・I227）」を足す

### 4-5. テスト
- `scripts/claude/tests/test_i212_review_base.sh`:
  - `osv` を 3 引数（`<RISK_PATH> <NO_DELTA> <出力>`、4 つ目に写し）にし、U7 の各ケースは `NO_DELTA=0` で呼ぶ。U7 の「差分なしで動かしていない → OK」は `NO_DELTA=1` に替える
  - U9（新規・`official_security_verdict` の「差分なし」）: YES＋`NO_DELTA=0`＋出力 `(実行していない: 差分なし)` だけ → HIGH／YES＋`NO_DELTA=0`＋本文の中に `(実行していない: 差分なし)` を引用した文があり判定の行が無い → HIGH／YES＋`NO_DELTA=1`＋出力が空 → OK／YES＋`NO_DELTA=1`＋判定の行が無い文 → OK／YES＋`NO_DELTA=` 空＋判定の行が無い → HIGH
  - U10（新規・`official_output_readable`）: `code`＋```` ```json ```` の囲みの指摘の配列（`"file"` つき）→ 読めた／`code`＋囲みの中が `[]` → 読めた／`code`＋囲みが無い裸の配列 `[ {"file": "a.sh"} ]` → 読めた／`code`＋```` ```python ```` の囲みの後に ```` ```json ```` の囲みの指摘の配列 → 読めた（囲みの組が食い違わない）／`code`＋和文の「指摘はありません。」だけ → 読めていない／`code`＋英文の `No issues found.` だけ → 読めていない／`code`＋本文に `"file": "a.sh"` の語があるだけ（JSON として読めない）→ 読めていない／`code`＋配列だが要素に `"file"` が無い（`[1, 2]`）→ 読めていない／`code`＋`SECURITY_FINDINGS: 0` の行だけ → 読めていない／`security`＋`SECURITY_FINDINGS: 0` の行 → 読めた／`security`＋指摘の配列だけ（判定の行なし）→ 読めていない／`security`＋和文の「報告する脆弱性はありません。」だけ → 読めていない／種類なし（空）＋指摘の配列 → 読めていない
  - 今の U7 の最後（`official_output_readable` の 1 ケース）は U10 の `security` の行に移す
  - E2（既存）: パス判定 YES のブランチで、見終えた記録の後に記録の場所だけ変えた 3 周目は `NO_DELTA=1` → `REVIEW_COMPLETE: YES`（＝`SECURITY_VERDICT` が OK）。本体の呼び出しが `NO_DELTA` を渡すことを通しで固定する（変えない）
  - FG（`broken` の写し）:
    - FG-U7: 置き換え前を `findings_line_present` の `"^${1}:[[:space:]]*[0-9]+[[:space:]]*\$"` に、置き換え後を `"${1}:[[:space:]]*[0-9]+"` に替える（行全体の固定を外す）→ U7 の「文の中に語があるだけ → HIGH」が OK になり不合格
    - FG-U9: `[ "$2" = "1" ] && { echo OK; return; }` を前の形 `[[ "$3" == *"(実行していない: 差分なし)"* ]] && { echo OK; return; }` に戻す → U9 の「引用だけ → HIGH」が OK になり不合格
    - FG-E2: 本体の写しの呼び出し `official_security_verdict "$RISK_PATH" "$NO_DELTA" "$OFFICIAL_SECURITY"` の `"$NO_DELTA"` を `0` にする → E2 の 3 周目が `REVIEW_COMPLETE: NO` になり不合格（差分なしの回を HIGH にする退行を止める）
    - FG-U10: `code) official_findings_json_present "$2" ;;` を前の形の和文の正規表現 `code) grep -qE '指摘(は)?(なし|ありません|見つかりません)' <<< "$2" ;;` に替える → U10 の「和文の指摘はありません だけ → 読めていない」が読めたになり不合格
    - 直す前の版（develop の本体）で U9・U10 を流し、期待と違う行（U9 の引用 → OK、U10 の和文 → 読めた）が出ることをステップ 1 の記録に残す
- `scripts/claude/tests/test_i193_official_flow.sh`:
  - C8 の 4 ケースを `official_output_readable code …` の形にする。「指摘の配列（`"file":`）は読めた結果」の入力を JSON として読める配列にする（今の入力 `[ {"file": "a.sh", "line": 1} ]` はそのまま読める）。「空の配列だけの行は読めた結果」の入力 `結果:\n[]\n` は囲みが無く全体が JSON でないので、```` ```json\n[]\n``` ```` の囲みに替える
  - C12（335 行目）「脆弱性は見つかりませんでした は読めた結果」→ 期待を 1（読めていない）に替え、名前を「文の言い回しだけでは読めた結果にしない（I227）」にする。種類は `security`
  - C23 の 4 ケースを `official_security_verdict YES 0 …`（NO なら `NO 0 …`）の 3 引数にする。352 行目の入力の注意文を新しい文（`(注意: 出力に決まった形の結果…`）に揃える
- `test_i197_review_ledger.sh:185`・`test_i193_official_flow.sh:425`（s8）: 部分一致のまま通るので変えない（TC-01 で確かめる）

### 4-6. `docs/issues/open/I227.md`（計画の時点で直した。受け入れ条件と本文を計画の確定値に合わせるため）
- 受け入れ条件 2 の文言を §2 のとおり「公式の決まった出力の形（JSON 配列）」に合わせ、`NO_DELTA=1` の回は OK のままを受け入れ条件 1 に足す
- 関連資料の古いパスを直す: `docs/reviews/I212_code_review_20261108_0100.md` → `docs/reviews/closed/…`、`docs/plans/open/plan_I212.md` → `docs/plans/closed/plan_I212.md`
- 実装対象の「C8・C12」を「`test_i193_official_flow.sh` のテストの番号 C8・C12」と書き、品質基準の C8 と取り違えないようにする
- 解決方針 2 の「判定の行」を、スパイクの結果（JSON 配列で決める）に合わせる

### 4-7. `docs/reviews/backlog/I212.md`
- 同梱して直した F5・F7 の行を消す（F2・F3・F4・F6 は残す）

## 5. 実装手順（ステップ）
1. テストを先に書く: 4-5 のテストの直しと新しいケースを書き、直す前の本体で U9・U10 が期待どおり不合格になることを記録する → TC-02・TC-03 参照
2. 4-2・4-1（`findings_line_present` と `official_security_verdict` の引数）→ TC-02・TC-04 参照（ステップ 1 が前提）
3. 4-3（`official_output_readable`・`official_findings_json_present`・`run_official_review` の種類）→ TC-03・TC-05 参照（ステップ 2 が前提。`findings_line_present` を使う）
4. 4-4・4-7（説明の文・一覧）（ステップ 2・3 の後。4-6 のイシュー本文は計画の時点で直した）。文言の有無の決定論テストは作らない（消すのが意図的な変更でしか起きない・`plan-writing-rules.md`「決定論テストの対象の選び方」）。構文は TC-06
- サービスの再起動は要らない（次の review-gate から新しい版が動く）

## 6. テスト計画
### 自動
- テストレベル: シェルの単体（関数を読み込む）と本体の通し（一時のリポジトリ・偽の `gh`・`claude`。既存の E2）。本物の GitHub・Claude は使わない
- 再発防止テスト: U9（F1 の再現: 引用で OK になる）・U10（和文の言い回しで読めたになる）・E2（差分なしの回を HIGH にする退行）。どれも FG で不合格になることを確かめる
- 認可・テナント境界: 該当なし（アプリのコードを変えない）
- 詳細は `docs/tests/open/I227_auto_test.md`
### 手動
- `docs/tests/open/I227_manual_test.md`（すべて Claude。本物の `/code-review` と `/security-review` を新しい版の `run_official_review` で動かし、「読めていない」の注意が付かないこと・判定が OK になること）

## 7. ロールバック
- PR を revert する（設定・データの変更なし）。記録の形は変えない

## 8. Risk & 回避策
- **`/code-review` が JSON の配列を出さない回がある**: 記録に「読めていない」の注意が付くだけで、合否には使わない（今までどおり参考）。過去の記録 3 件とスパイク 2 回はすべて囲みの配列だった
- **`/security-review` が判定の行を飾りつき（`**SECURITY_FINDINGS: 0**`・全角コロン）で出す**: 行全体の固定の形だけを読むので HIGH（FAILED）に倒れる（止める側）。review-gate の手順どおり 1 回だけやり直す。I212 の M-01・review-gate では飾りなしで出た。緩めると文の中の語で当たる道が開くので、このイシューでは緩めない
- **`/security-review` が差分の中の `SECURITY_FINDINGS: 0` だけの行をそのまま引用する**: I212 の台帳 F3 のとおり、出力のどこにあっても受ける作りは意図どおり（締めの文で FAILED にしないため）。差分の行は先頭に `+` が付くので、そのまま引用しても行全体の形に当たらない。わざと偽の行を出させるのは対象外（I179）
- **差分なしの回を HIGH にする退行（呼び出しで `NO_DELTA` を渡し忘れる）**: E2 と FG-E2 で通しで止める
- **`python3` が使えない環境**: 読めたかの判定が「読めていない」に倒れ、注意が付くだけ（合否は変わらない）。`code-review.sh` は既に `python3` を使っている（`expected_ci_jobs` など）

## 9. 確定事項と自律判断
イシューに明記されている:
- 「差分なし」は表示の文字列ではなく変数か引数で渡す（どちらかは計画で決める）
- 判定の行の正規表現を 1 か所にまとめる。行全体の固定の形だけを読む。I212 の `SECURITY_FINDINGS` と同じ形にそろえる
- `/code-review` は合否に使わない参考のまま（止めない）
- 台帳の残りの一覧の同梱は計画で決める
- ガードの守る範囲は「普通の書き方の事故」まで（わざと偽の行を出させるのは対象外・I179）

Claude が決めた（技術的な選択と理由）:
- **「差分なし」は既存の変数 `NO_DELTA` を `official_security_verdict()` の引数で渡す**（仮定・技術的）: `NO_DELTA` は判定の前にいつも決まっている。別の印のファイルや定数の文字列で表すと、また中身の照合が残る。表示の文字列は表示のためだけに残す
- **`/code-review` の「読めたか」は、判定の行ではなく公式の決まった出力の形（JSON として読める指摘の配列）で決める**（スパイクの結果・技術的）: `/code-review` は `--append-system-prompt` の指示に従わず、公式の手順の決まった形（```` ```json ```` の囲みの配列）だけを出した（2 回とも）。この形は文の言い回しではなく機械が読む形なので、受け入れ条件 2 の狙い（和文の「指摘なし」の文の形に左右されない）を満たす。受け入れ条件 2 の文言「判定の行」は、狙いを変えずに「決まった出力の形」に置き換えた（要件の変更ではなく、達成の手段の置き換え）
- **自由文の正規表現は補助にも残さず消す**: 残すと受け入れ条件 2（文の形に左右されない）と矛盾する。`/code-review` は合否に使わないので、読めない回は注意が付くだけ
- **`"file":` の行・`[]` の行の当て方も消し、`json.loads` で配列として読めるかにする**: 行の当て方は、本文に語が出てくるだけで当たる（文の形に頼る作りの一種）
- **種類（`code`／`security`）を `run_official_review()` の第 2 引数にする**: 種類ごとに決まった形と足す指示が違う。同じ引数から両方を決めれば、呼び出しで指示と読み方が食い違わない。種類を知らない呼び出しは「読めていない」に倒す
- **テストは既存の `test_i212_review_base.sh`・`test_i193_official_flow.sh` を直して足す（新しいテストのファイルは作らない）**: どちらも実装対象の関数のテストを持ち、`broken`（写しを壊す FG）と E の通しの土台がある。新しいファイルにすると E の土台の写しが増える（I212 の retro の指摘）
- **受け入れ条件 3 は `grep` のゲート（TC-05）で確かめる**: 判定の行の正規表現を足すのは、普通の書き方で気づかずに起きうる（今回の F7 がその例）。ハーネステストには入れず、このイシューの完了の確認だけにする
- 要件・基本設計・UI/UX の仮定: なし

台帳の残りの一覧（`grep -rnF` で実装対象のファイルと `FILE=-` に当たった行）:
- 一覧 `scripts/claude/code-review.sh` I212 F7: 同梱 — `findings_line_present` にまとめる（受け入れ条件 3 そのもの）
- 一覧 `.claude/skills/review-gate/SKILL.md` I212 F5: 同梱 — 同じ行（SKILL.md:36）を直すので文言の不正確さも一緒に直す（§4-4）
- 一覧 `scripts/claude/code-review.sh` I212 F2: 残す — 件数を判定に使わないのは意図どおりの設計判断（指摘の中身はレビュー役と台帳が扱う）
- 一覧 `scripts/claude/code-review.sh` I212 F3: 残す — 出力のどこにあっても受けるのは意図どおり（§8）
- 一覧 `scripts/claude/code-review.sh` I212 F4・F6: 残す — 差分の起点の選び方の Low で、このイシューの範囲の外（イシューの「含まない」）
- 一覧 `scripts/claude/code-review.sh` I206 F4・I207 F6・I207 F7・I208 F1・I208 F2・I208 F3・I208 F5: 残す — 台帳の合流・振り分け・一時ファイルの Low で、判定の読み取りに関係しない
- 一覧 `scripts/claude/tests/test_i193_official_flow.sh` I204 F6・I195 F10: 残す — F9 の `run-all.sh`・別の検査の `[ -r ]` で、C8・C12・C23 と関係しない
- 一覧 `FILE=-` I224 F9・I223 B1〜B4: 残す — push の回数の実測と bot の停止の後始末で、このイシューと関係しない

要件適合性・業務ロジック:
- 受け入れ条件の範囲を超えた仕様の追加なし（同梱 F5・F7 は一覧の同梱）。マルチテナント・ステータス遷移は該当なし
- エッジケース: `NO_DELTA` が空・`0`・`1`／出力に引用だけ／`/code-review` の配列が空・裸の配列・囲みの中が壊れた JSON・要素に `"file"` が無い／種類が無い

セキュリティ・ベストプラクティス:
- 入力: 組み込みのレビューの出力は信用しない。判定の行は行全体の固定の形だけ、JSON は `json.loads` で読むだけ（評価しない）。`python3 -I` で起動し、出力は標準入力で渡す（引数・コードに埋めない）
- `findings_line_present` の `$1` は正規表現に入るので、コードの中の定数（`SECURITY_FINDINGS`）だけを渡す（コメントに書く）
- 起動: `--append-system-prompt` の文は定数（差分の中身を入れない）。起動の形（plan モード・承認なし・読み取りだけの鍵・`--strict-mcp-config`）は変えない
- 機密データ・OWASP・依存ライブラリ: 該当なし（依存の追加なし）
- bandit・npm audit: 対象のコードなし（シェルとテストだけ）

P3/P5/P8 影響なし（DB・外部 API の新規・非同期・インフラの追加なし）。P6 影響なし（UI なし）。P9 影響なし（個人情報・テナントデータを扱わない）。
コーディング規約: 変更はシェルとハーネスの文書だけで、`rules/ultimate_django_coding_standards.md`・`rules/react-coding-standards-integrated.md` の対象のコードは無い。

設計品質:
- 判定の本体は 1 か所ずつ（判定の行は `findings_line_present`・JSON は `official_findings_json_present`・種類の振り分けは `official_output_readable`）
- 例外処理: 読めない・種類が無い・`NO_DELTA` が想定外の値は、止める側（HIGH・読めていない）に倒す
- 設定値: 指示の文は定数 `SECURITY_FINDINGS_PROMPT`。行の名前は呼び出しの定数

Danger Ops: 無

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | 高リスクで `NO_DELTA=0` のとき、`/security-review` の出力が `(実行していない: 差分なし)` を含んでも（引用でも全文でも）、判定の行が無ければ HIGH（TC-02 U9・FG-U9） |
| V2 | 1 | 実験必須 | 差分なしで動かしていない回（`NO_DELTA=1`）は、本体の通しで OK のまま（`REVIEW_COMPLETE: YES`）。呼び出しで渡し忘れると落ちる（TC-04 E2・FG-E2） |
| V3 | 2 | 実験必須 | `/code-review` の「読めたか」が、和文・英文の「指摘なし」の文や、本文の `"file":` の語では決まらず、JSON として読める指摘の配列だけで決まる（TC-03 U10・FG-U10・M-01） |
| V4 | 2 | 実験必須 | `SECURITY_FINDINGS` の判定の行の読み方が 1 か所で、行全体の固定の形だけを読む（TC-05・TC-02 U7・FG-U7） |

## 計画変更記録
1. 計画レビュー（20261108_0156・OK・高リスク判定 No）の Warning 3 件への対応: (W1) 囲みの開始の正規表現を言語名を問わない形（`^```[A-Za-z0-9_+-]*`）にし、```` ```python ```` の囲みの後に JSON の囲みがあるケースを U10 に足した（組の食い違いで読めていないに倒れるのを防ぐ）。警告行の除去は §1 のとおり retro で一覧に回す (W2) M-01 の備考に、JSON の配列が出なかったときは 1 回だけ実行し直し、2 回とも出なければ出力の末尾を記録して、注意が付いていること（注意と実際が一致）を確かめる、と書いた（`/code-review` は合否に使わない参考のため） (W3) C23 の 352 行目の入力の注意文を新しい文に揃える、と §4-5 に足した。計画レビューのやり直し: 不要（findings への対応で、方式・範囲・受け入れ条件は変えない）
2. /simplify（4 観点）を受けた整理: (a) `official_security_verdict` の判定を `findings_line_present` の直呼びから `official_output_readable security` に替え、security の「読めた」の決まりを 1 か所にした（振る舞いは同じ） (b) `findings_line_present` のコメントの「ここだけ」を、組み込みのレビューの判定の行に限ると直した（台帳の `LEDGER_ROUND` などは別の読み方のまま・範囲の外） (c) `NO_DELTA=1` で書く「差分なし」の文字列に「表示用・判定に使わない」のコメントを足した (d) SKILL.md:36 の文を「やり直しは見終えた記録を起点にするので、`NO_DELTA` の近道に入らず `/security-review` がもう一度動く」に直した (e) テストの `rd` を他のテストと同じ `rc` の上に書いた・C23 の入力の注意文を短い任意の文にした（表示の文字列にテストを結び付けない）。見送り: `findings_line_present` を `SECURITY_FINDINGS` 固定にする案（計画どおり名前を受ける形のまま）・`official_output_readable` の `*) return 1` を消す案（止める側に倒す既定として残す）・種類ごとの指示と読み方を 1 つの case にまとめる案（種類が 2 つだけで軽微）・FG-E2 を grep に替える案（通しで退行を止める方が強いので計画どおり）・関数の読み込みを 1 回にまとめる案（既存の `lib` の書き方に合わせる）・ほかのテストのスタブが「指摘なし」を返す件（差分の外。合否に影響せず、retro で一覧に回す）。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件は変えない）

## レビュー結果
- [20261108_0156 判定: ✅ 完了](../../reviews/I227_plan_review_20261108_0156.md)
（plan-review 段階が追記する）
