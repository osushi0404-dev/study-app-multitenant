# I498 計画書: マージ前の最終確認の CI 待ちの上限を code-review.sh と 1 か所にまとめる

## 基本情報
- **計画書ID**: plan_I498
- **関連イシュー**: #498
- **Draft PR**: #528
- **作成根拠資料**: docs/issues/open/I498.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I498_review.md
- **作成日**: 2026-11-16

## 1. 背景/目的
- 背景: close 段階の手順 5.5 は、マージ依頼の直前に `bash scripts/claude/pr-base-sync.sh final` を流して「BEHIND・DIRTY でない」かつ「CI が全部合格」を確かめる。PR #495（I480）では、ハーネスのテストのジョブ（Harness Tests）が 10 分 56 秒かかり、スクリプトの待ちの上限 600 秒を超えて「⚠️ CI タイムアウト（600秒）」・exit 1 になった。CI は全部合格していた
- 目的: CI が正常に終わる PR で、最終確認が待ち時間の不足で落ちないようにする。あわせて、同じ意味の値が 2 か所で別々に持たれて食い違う形をなくす

### 調査結果
- **原因の概要**: マージ前の最終確認の CI 待ちの上限（600 秒）が、ハーネスのテストのジョブの所要時間（6〜11 分）より短い。もとは「code-review.sh と同じ値」として置かれたが、code-review.sh だけが 1200 秒に延び、こちらは取り残された
- **詳細な原因分析**:
  1. `scripts/claude/pr-base-sync.sh:20` は `CI_TIMEOUT="${PBS_CI_TIMEOUT:-600}"`（コメントは「code-review.sh と同値」）。`ci_wait`（`:76-86`）は上限を過ぎると `⚠️ CI タイムアウト（${CI_TIMEOUT}秒）`・exit 1（`:82`）
  2. `scripts/claude/code-review.sh:240` の `wait_ci` は `CI_WAIT_TIMEOUT` の既定 1200 秒（I193 で延びた）。時間切れのメッセージ（`:1204`）にも `1200` がもう一度書いてある。同じ意味の値が 3 か所に数字で書かれている
  3. ハーネスのテストのジョブの実測: PR #495 で 10 分 56 秒、develop の直近（run 43789388782・2026-11-16）で 8 分 16 秒、PR #527 で 6 分 27 秒。ほかのジョブは 4 分以内（E2E を含む）
  4. CI のジョブの時間の上限は、`.github/workflows/ci.yml:187` の Harness Tests の `timeout-minutes: 30` と、`.github/workflows/e2e.yml:30` の 1 ステップの 5 分だけ。ほかのジョブは GitHub の既定（360 分）
  5. close 段階は push の直後に `final` を流すので、ハーネスのテストのジョブが動く PR では、待ちが 600 秒を超えうる。前面の実行（Bash ツールの上限 10 分）でも打ち切られうる（I480 では背景に移して流した）
- **環境変数での上書きの使用箇所**（`grep -rn` で全件）: `PBS_CI_TIMEOUT` は `scripts/claude/tests/test_pr_base_sync.sh:76`（`=0`）だけ。`CI_WAIT_TIMEOUT` は `test_i193_official_flow.sh:311・320・385`・`test_i197_review_ledger.sh:257`・`test_i202_ledger_cleanup.sh:182`・`test_i205_stop_criteria.sh:242`・`test_i212_review_base.sh:158`（どれも 2 か 5）。手順書（`.claude/skills/`・`docs/runbooks/`）からの使用は無い。→ 両方の環境変数を残す
- **code-review.sh を写して動かすテスト**: `test_i197_adversarial_process.sh:148`・`test_i202_ledger_cleanup.sh:172`・`test_i205_stop_criteria.sh:234`・`test_i212_review_base.sh:148` は code-review.sh と review-process-lib.sh だけを一時のリポジトリに写す。`test_i197_review_ledger.sh`・`test_i202`・`test_i205`・`test_i212`・`test_i512` の `lib` は壊した写しを一時のフォルダから読み込む。→ code-review.sh が新しい別のファイルを読み込む形にすると、これらの写しがすべて壊れる（§9 の判断の根拠）
- **スパイク（2026-11-16・このセッション）**: `REVIEW_LIB_SOURCE_ONLY=1 bash -c '. scripts/claude/code-review.sh; declare -F wait_ci'` → `wait_ci`・rc=0・何も出力せず 0.006 秒 → **成立**（ガードより前の最上位の文は代入と関数の定義だけで、関数だけを読み込む形に副作用が無い。`pr-base-sync.sh` から既定を読むのに使える）

## 2. 受け入れ条件
- [ ] AC1: `pr-base-sync.sh final` の CI 待ちの既定の上限が `code-review.sh` の CI 待ちの既定と同じで、値の定義が 1 か所（`code-review.sh` の `CI_WAIT_TIMEOUT_DEFAULT`）にある（→ TC-01 の T1〜T3・T5）
- [ ] AC2: 2 つの上限の既定が食い違うと落ちる決定論のテスト（失敗の注入つき）がある（→ TC-01 の FG1〜FG3）
- [ ] AC3: close 手順 5.5 と proceed の `merge` が、最終確認を背景の実行（`run_in_background: true`）で流すと書いている（→ TC-02）
- [ ] AC4: 上限を超えたときの扱い（exit 1・`⚠️ CI タイムアウト（<秒>秒）`）は変わらない（→ TC-01 の T2。既存の `test_pr_base_sync.sh` も通る）

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: ハーネスのスクリプト（`pr-base-sync.sh`・`code-review.sh`）と手順書（close・proceed）。review-gate の CI 待ちの既定も 1200 秒から 1980 秒に延びる（§9）。`.github/`・`.claude/settings.json` は変えない

## 4. 変更点一覧（具体）
| ファイル | 変更内容 |
|---|---|
| `scripts/claude/code-review.sh` | (1) `wait_ci` の前（`:233` のコメントの位置）に `CI_WAIT_TIMEOUT_DEFAULT=1980` を置き、理由をコメントに書く (2) `:240` の `${CI_WAIT_TIMEOUT:-1200}` と `:1204` の `${CI_WAIT_TIMEOUT:-1200}` を `${CI_WAIT_TIMEOUT:-$CI_WAIT_TIMEOUT_DEFAULT}` にする |
| `scripts/claude/pr-base-sync.sh` | `:20` の `600` をやめ、`PBS_CI_TIMEOUT` が無いときは同じフォルダの `code-review.sh` を関数だけ読み込む形で `CI_WAIT_TIMEOUT_DEFAULT` を読む。読めない・正の整数でないときは STOP（exit 1） |
| `.claude/skills/close/SKILL.md` | 手順 5.5 を `run_in_background: true` で流し、完了の通知で終了コードを受け取ると書く |
| `.claude/skills/proceed/SKILL.md` | `merge` の行を同じく背景の実行にすると書く |
| `scripts/claude/tests/test_i498_ci_wait_timeout.sh`（新規） | 2 つのスクリプトの「実際に効く既定の上限」を動かして取り出し、同じであること・数字の既定が書き戻されていないこと・上限超えの扱い（失敗の注入つき）。auto_test の TC-01 |

### 修正アプローチ
CI 待ちの上限の既定を `code-review.sh` の 1 つの変数 `CI_WAIT_TIMEOUT_DEFAULT` だけに置く。`code-review.sh` の中の 2 か所はそれを使い、`pr-base-sync.sh` は `code-review.sh` を関数だけ読み込む形（テストが使っている既存の `REVIEW_LIB_SOURCE_ONLY=1`）で同じ値を読む。既定は、CI で時間の上限を持つ一番長いジョブ（Harness Tests の 30 分）より長い 1980 秒（33 分）にし、CI が自分の上限で止まる前に待ちをやめないようにする。待ちが前面の上限 10 分を超えるので、close・proceed では背景の実行で流す。

### 4-1. `code-review.sh`（修正方針: 既定の値を 1 つの変数に置き、数字の書き写しをなくす）
`:233` のコメントを次の形にし、変数を足す（`REVIEW_LIB_SOURCE_ONLY` のガード〔`:1027`〕より前＝関数だけを読み込む形でも定義される位置）:

```bash
# I193・I498: CI 待ち。CI_WAIT_TIMEOUT 秒（既定 CI_WAIT_TIMEOUT_DEFAULT）まで CI_POLL_INTERVAL 秒（既定 15）ごとに見る。
# 既定の正はこの 1 か所（pr-base-sync.sh の final も、関数だけを読み込む形でこの値を読む・I498）。
# 1980 秒＝CI で時間の上限を持つ一番長いジョブ（.github/workflows/ci.yml の Harness Tests・timeout-minutes: 30）が
# 自分の上限で止まるより先に待ちをやめないよう、30 分＋3 分（登録・順番待ちの分）。実測は 6〜11 分（PR #495 で 10 分 56 秒）
CI_WAIT_TIMEOUT_DEFAULT=1980
```
- `:240`: `timeout_s="${CI_WAIT_TIMEOUT:-$CI_WAIT_TIMEOUT_DEFAULT}"`
- `:1204`: `echo "⛔ CI が ${CI_WAIT_TIMEOUT:-$CI_WAIT_TIMEOUT_DEFAULT} 秒で終わりませんでした。"`
- `:234-238` の判定のコメントは変えない

### 4-2. `pr-base-sync.sh`（修正方針: 既定を自分で持たず code-review.sh から読み、読めなければ止まる）
`:20` を次に置き換える（`:17-21` の並びの中。`PBS_CI_TIMEOUT` の上書きは今までどおり、値の確かめをしない）:

```bash
# CI 待機上限（秒）。既定は code-review.sh の CI_WAIT_TIMEOUT_DEFAULT（正は 1 か所・I498）。
# 関数だけを読み込む形（REVIEW_LIB_SOURCE_ONLY=1）で読む。別の bash で読むので、この スクリプトの set の設定は変わらない
CI_TIMEOUT="${PBS_CI_TIMEOUT:-}"
if [ -z "$CI_TIMEOUT" ]; then
  CI_TIMEOUT=$(REVIEW_LIB_SOURCE_ONLY=1 bash -c '. "$1" && printf "%s\n" "$CI_WAIT_TIMEOUT_DEFAULT"' _ \
    "$(dirname "${BASH_SOURCE[0]}")/code-review.sh" 2>/dev/null) || CI_TIMEOUT=""
  [[ "$CI_TIMEOUT" =~ ^[1-9][0-9]*$ ]] \
    || { echo "⛔ CI 待ちの上限の既定を code-review.sh から読めません（'${CI_TIMEOUT}'）。STOP してユーザーに報告"; exit 1; }
fi
```
- `ci_wait` の中身（`:76-86`。上限超えの `⚠️ CI タイムアウト（${CI_TIMEOUT}秒）`・exit 1 を含む）は変えない（AC4）
- 読むのは `MODE` の確かめの後・`gh` を呼ぶ前（`:21` の後）。sync でも読む（止まるのは code-review.sh が無い・壊れているときだけで、そのときは close の他の段階も動かない）
- `:76` のコメント「code-review.sh L214-237 と同型」は行番号がずれているので「code-review.sh の wait_ci と同じ上限の既定」に直す

### 4-3. `close/SKILL.md` 手順 5.5（修正方針: 前面の上限 10 分で打ち切られないよう背景で流す）
コードブロックの直前に次の 1 文を足す（review-gate の 3-1 と同じ書き方）:
> Bash ツールの `run_in_background: true` で実行し、完了の通知で終了コードを受け取る（CI 待ちは既定で最長 1980 秒〔`code-review.sh` の `CI_WAIT_TIMEOUT_DEFAULT`〕で、前面の実行の上限 10 分を超えうるため・I498）。通知に終了コードが無いときは exit 1 と同じに扱う。

### 4-4. `proceed/SKILL.md` の `merge` の行（修正方針: close と同じ扱いにする）
`:35` の「`bash scripts/claude/pr-base-sync.sh final` を流し、」を「`bash scripts/claude/pr-base-sync.sh final` を Bash ツールの `run_in_background: true` で流し（close の手順 5.5 と同じ・前面の上限 10 分を超えうる）、」にする。

### 4-5. `test_i498_ci_wait_timeout.sh`（新規。修正方針: 書かれた数字ではなく、動かしたときに効く値を比べる）
→ auto_test の TC-01。対象のスクリプトのフォルダを `I498_SCRIPTS_DIR`（既定 `scripts/claude`）で差し替えられる形にし、失敗の注入は一時のフォルダの写しに対して行う（本物のファイルは書き換えない）。

## 5. 実装手順（ステップ）
1. `test_i498_ci_wait_timeout.sh` を書き、今の develop の形で T3（同じ値）が不合格になる（600 と 1200）ことを確かめる（→ TC-01。テストの先書き）
2. `code-review.sh` を 4-1 のとおり直す（ステップ 1 の後）
3. `pr-base-sync.sh` を 4-2 のとおり直す（ステップ 2 の後。読む変数がステップ 2 で生まれる）→ TC-01 が合格
4. close・proceed の手順書を 4-3・4-4 のとおり直す（ステップ 1〜3 と並行してよい）→ TC-02
5. 関係するテスト（`test_pr_base_sync.sh`・`test_i193_official_flow.sh`・`test_i525_skill_sandbox_form.sh` と TC-01）を流す（→ TC-03。全体は CI）

## 6. テスト計画
### 自動
- TC-01（新規 `test_i498_ci_wait_timeout.sh`）: 2 つのスクリプトの実際に効く既定の上限を、`gh`・`sleep` のスタブで動かして出力から取り出して比べる。数字の既定の書き戻しが無いこと。上限超えの扱い（exit 1・メッセージ）。上書きの環境変数が効くこと。code-review.sh が読めないときに止まること。失敗の注入 3 つ
- TC-02: close・proceed の手順書に背景の実行が書いてあること（`grep -q`）。手順書の文言は意図的な変更でしか消えないので、決定論テストのファイルにはせず、決定論ゲートの `grep` で 1 回確かめる（`plan-writing-rules.md`「決定論テストの対象の選び方」）
- TC-03: 既存の `test_pr_base_sync.sh`（21 件）・`test_i193_official_flow.sh`（wait_ci の C 群）・`test_i525_skill_sandbox_form.sh`（手順書に前置きの起動が無い）が通る
- テストのレベル: すべてシェルの決定論テスト（スタブで `gh`・`sleep` を差し替え。実 GitHub に依存しない）。バグの直しの再発防止は TC-01 の T3 と FG1・FG2
### 手動
- No.1（Claude）: review-gate の `code-review.sh` の実際の実行（この PR はハーネスのテストのジョブが動く）の出力で、待ちの行の上限が `1980s` で、`CI_WAIT: OK` になる
- 実際の `pr-base-sync.sh final` の背景での実行は、この PR の close の手順 5.5 そのもの（test-gate の時点では PR が Draft なので `final` は DRAFT で止まり、確かめにならない）。結果は close のマージ依頼の報告に書く

## 7. ロールバック
- この PR のコミットを revert する（スクリプト 2 本・手順書 2 本・テスト 1 本。データ・設定の変更なし）

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: code-review.sh を写して動かす既存のテストが、新しいファイルの読み込みで壊れる | 新しいファイルを作らず、値を code-review.sh の中に置く（code-review.sh 側の読み込みは増えない） | 回避 |
| R2: pr-base-sync.sh が code-review.sh を読めないと、既定が空のまま待ち始める（fail-open）／0 秒で時間切れ | 読めない・正の整数でないときは exit 1 で止める（TC-01 の T6） | 回避 |
| R3: 待ちが 1980 秒に延び、CI が本当に止まっているときに review-gate・close の待ちが長くなる | 失敗・取り消しは見つけ次第すぐ止まる（`fail`・`cancel`）。延びるのは CI が終わらないときだけで、Harness Tests は 30 分で GitHub が取り消す。背景の実行なので会話は止まらない | 受け入れ |
| R4: 背景の実行が 10 分を超えて打ち切られる | 2026-10-25 に 700 秒で止まらないことを実測済み（review-gate の 3-1）。終了コードが無いときは exit 1 と同じに扱う（4-3） | 回避 |
| R5: CI のジョブの `timeout-minutes` を延ばすと、待ちの上限がまた短くなる | code-review.sh のコメントに理由（30 分＋3 分）と ci.yml の場所を書き、変えるときに目に入るようにする。決定論テストにはしない（設定の写しになる・`plan-writing-rules.md`） | 受け入れ |

## 9. 確定事項と自律判断
イシューに明記されている:
- 値を 1 か所にまとめ、2 つのスクリプトが同じ値を使う（既定 1200 秒以上）
- close 手順 5.5・proceed の `merge` を `run_in_background: true` で流すと書く
- 上限超えの扱い（exit 1・メッセージ）は変えない。`PBS_CI_TIMEOUT`・`CI_WAIT_TIMEOUT` の上書きは、使っている箇所があれば保つ
- 含まない: ハーネスのテストのジョブを速くすること・`timeout-minutes` の変更

Claude が決めた（技術的な選択と理由）:
- 値の置き場所は `code-review.sh` の `CI_WAIT_TIMEOUT_DEFAULT`（新しい共有ファイルを作らない）— 新しいファイルにすると、code-review.sh を写して動かすテスト 5 本以上（§1 調査結果）の写しの組み合わせを全部直す必要があり、直し漏れで壊れる。code-review.sh は今も値を持つ側で、関数だけを読み込む形（`REVIEW_LIB_SOURCE_ONLY=1`）が既にあり、副作用が無いことをスパイクで確かめた
- `pr-base-sync.sh` は別の bash で読み込む — 同じシェルで読むと code-review.sh の `set -euo pipefail` と多数の関数が pr-base-sync.sh に入り、今の分岐の動きが変わりうる
- 既定は 1980 秒（1200 秒のままにしない）— ハーネスのテストのジョブは延び続けており（600 秒の取り残しもこれで表に出た）、1200 秒でも項目が増えればまた同じことが起きる。CI で時間の上限を持つ一番長いジョブ（30 分）より長くすれば、待ちが CI より先に諦めることが無くなる。code-review.sh（review-gate）も同じ値に延びるが、背景の実行で、失敗はすぐ止まるので害は待ちが長くなることだけ（R3）
- 上限超えの扱いは 2 つのスクリプトで今のまま別々（pr-base-sync.sh は exit 1、code-review.sh は exit 3）— イシューの AC4。待ちの判定の中身をまとめることはしない
- 決定論テストは新しいファイル `test_i498_ci_wait_timeout.sh` にする（`test_pr_base_sync.sh` に足さない）— code-review.sh も対象で、両方のフォルダの写しを作る失敗の注入が要るため
- 比べるのは「書かれた数字」ではなく「動かしたときに出力に出る上限」— 数字の既定を別の形（`:-600` の書き戻し・別の変数）で入れても捕まえられる。数字の既定の書き戻しの grep（T4）は補い
- 背景の実行の手順書の文言は決定論テストのファイルにしない（TC-02 の grep 1 回）— 意図的な変更でしか消えない（`plan-writing-rules.md`「決定論テストの対象の選び方」）
- 一覧 `.claude/skills/close/SKILL.md` I224 F1: 残す — 衝突を直したコミットを push せずにマージ依頼へ進む話で、待ちの上限とは別の道
- 一覧 `.claude/skills/proceed/SKILL.md` I224 F2: 残す — `merge` で `final` を流すたびに base を取り込んで承認を取り消す話で、待ちの上限とは別。今回は呼び方（背景）だけを変える
- 一覧 `.claude/skills/close/SKILL.md` I224 F3・F4: 残す — close の手順の中断・記録の話で、待ちの上限とは別
- 一覧 `scripts/claude/code-review.sh` I206 F4・I207 F6/F7・I208 F2/F5・I212 F2/F3/F4/F6・I227 F1/F2/F4/F5/R1・I512 F2/F3/F6/F14/F15: 残す — どれも台帳・組み込みのレビュー・一時ファイルの話で、CI 待ちの上限とは別
- 一覧 `FILE=-` I223 B1〜B4・I224 F9: 残す — bot の後片付け・I224 の測定で、このイシューと関係しない
- 調べる途中で見つけた別の穴（このイシューでは直さない）: `pr-base-sync.sh` の `ci_wait` は `gh pr checks` に `pending` が無ければ合格にするので、push の直後でチェックがまだ登録されていないと、CI を待たずに通りうる（code-review.sh の `wait_ci` は期待するジョブがそろうまで待つ）。イシューの目的（待ち時間の不足で落ちない）とは逆向き（待たずに通る）の話で、マージは GitHub の承認が最後に止める。retro で起票するかを決める

セキュリティ・ベストプラクティス:
- セキュリティ影響なし（ハーネスのシェルスクリプトと手順書だけ。認証・認可・機密データ・依存ライブラリの変更なし）。`bash -c` に渡すのは自分のフォルダの code-review.sh のパスだけで、外からの入力を混ぜない（`$1` で渡し、文字列に埋め込まない）
- P3/P5/P8 影響なし（DB・外部 API・非同期・インフラの変更なし）。P6 影響なし（UI・データ量の懸念なし）。P9 影響なし（個人情報を扱わない）

Danger Ops（有無/手順/ロールバック）:
- 無

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 2 | 読んで可 | TC-01 の T3 が、2 つのスクリプトの実際に効く既定（出力に出る上限）を比べていて、片方だけ数字の既定に戻すと不合格になる（FG1・FG2）か |
| V2 | 1 | 読んで可 | `pr-base-sync.sh` が code-review.sh を読めない・壊れているときに、空や 0 の上限で待ち始めずに exit 1 で止まる（TC-01 の T6・FG3）か |
| V3 | 3 | 読んで可 | 上限超えの扱い（exit 1・`⚠️ CI タイムアウト（<秒>秒）`）と `PBS_CI_TIMEOUT` の上書き（`test_pr_base_sync.sh` の `=0` を含む）が変わっていない（TC-01 の T2・T5、TC-03）か |

## 計画変更記録
- （なし）

## レビュー結果
- [20261116_1132 判定: ✅ 完了](../../reviews/I498_plan_review_20261116_1132.md)
