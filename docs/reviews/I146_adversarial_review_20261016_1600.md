# 敵対的レビュー記録 [I146] ── 2026-10-16

起点: `/code-review I146`（`docs/reviews/I146_code_review_20261016_1532.md`・FINAL_VERDICT OK・RISK YES）→ 敵対的レビューステージ自動起動。

## 第 1 周（エージェント 4）

| # | 観点 | NEW_CRITICAL | NEW_HIGH |
|---|---|---|---|
| 1 | ロジック回避・実機 repro | 0 | 1 |
| 2 | テストの false-green・tautology | 0 | 1 |
| 3 | 要件・脅威モデルの網羅漏れ | 0 | 0 |
| 4 | 権限・設定面と hook の実行時挙動（動的観点） | 0 | 1（#1 と同一） |

### findings（重複統合後）

| ID | 重大度 | 指摘 | 再実証（オーケストレーター） | 対応 |
|---|---|---|---|---|
| A1 | **High** | 複数行・空白なし `;`・`&`・サブシェル・コマンド置換の中の `gh pr merge`（fork）が素通し。`main()` が `_norm` で改行を空白に潰し、`_segments` は空白で囲まれた演算子しか区切らないため（観点 1・4 が独立に検出） | gh スタブで `$'git status\ngh pr merge 257 --squash'` → rc=0、`true;gh pr merge 257` → rc=0（単一行は rc=2、同形の push は rc=2） | **修正**: gh pr 判定専用の `_gh_segments`（shlex `punctuation_chars=";&|()\`\n"`・クォート内は分割しない）を追加し、生コマンドを渡す。既存 `_segments` は無改変 |
| A2 | **High** | gh スタブが識別子・`--repo` を見ずに同じ値を返す tautology。ガードが識別子を渡し忘れても全件 PASS する（観点 2） | 指摘の注入結果（M1〜M4 で `pass=34 fail=0`）と、スタブのコード読解で確認 | **修正**: スタブは識別子なし照会と `SELF_IDENTS` に自前（false）を返す。G53/G54 で照会引数を GH_LOG で検証。`test_pr_base_sync.sh` のスタブも対象 PR 219 以外は false を返す（照会先を PR 1 にした注入版で `RESULT: NG (5 件)` を確認） |
| A3 | Medium | `GH_REPO=` 前置・`env`/`command`/`timeout`/絶対パス `/usr/bin/gh` で素通し | スタブで `GH_REPO=x/y gh pr merge 257` → rc=0 | **修正**: `_gh_invocation` で `VAR=val`・ラッパー・`timeout <dur>` を読み飛ばし、`basename == "gh"` で判定 |
| A4 | Medium | `-R/--repo`（`gh -R o/r pr …` のグローバル位置を含む）・`GH_REPO` が照会に渡らず、別リポジトリの PR を検査する | 静的読解（`_guard_cross_repo(t[0], t[1], None, raw)`） | **修正**: グローバル・サブコマンド両位置の `-R/--repo/--repo=/-Rx` と `GH_REPO=` を照会の `--repo` に渡す（G38〜G40b） |
| A5 | Medium | 値付きフラグ（`--subject`/`-t`/`--title`/`-b` 等）の値を PR 識別子と誤認し、自前 PR を検査して素通し | 指摘の引数判定スタブで `gh pr merge -t 12 257` → 0 | **修正**: 値付きフラグ一覧で値を読み飛ばし、`--x=v` は値を消費しない。位置引数が複数なら ask 降格（G41〜G45・G52） |
| A6 | Medium | G22 が順序を検証できていない（merge は cross ガード自身も exit 2） | 指摘の M10 注入結果 | **修正**: G22 を `gh pr ready 257 && rm -rf x`（ask 種別）に変更 |
| A7 | Medium | `gh pr checkout <fork PR>` が対象外。checkout で `.claude/settings.json` と hook 本体が攻撃者版に置き換わり、次のツール呼び出しで実行される | 静的読解（`_GH_PR_*_VERBS` に checkout なし） | **ユーザー判断待ち**（計画の範囲拡大。下記） |
| A8 | Low | Bash の `gh pr update-branch` が対象外（MCP 版は ask） | 静的読解 | **ユーザー判断待ち**（A7 と同じ判断） |
| A9 | Low | `-ab`（approve 結合）・`--approve=true` が素通し | 指摘の実測 | **修正**: 短縮フラグ結合を 1 文字ずつ解釈・`--approve=` は false/0 以外を approve 扱い（G46〜G48） |
| A10 | Low | PR テンプレートの相対リンク `../CONTRIBUTING.md` が PR 本文で 404 になり得る | 未実測（ネットワーク不可）。GitHub は PR 本文の相対リンクを blob パスに解決しない | **修正**: 絶対 URL（`…/blob/develop/CONTRIBUTING.md`）に変更 |
| A11 | Low | CONTRIBUTING の英日差（「Please do not take it personally.」が日本語に無い・「We read them」と「必ず読みます」の強さの差） | 目視 | **修正**: 日本語に一文追加・「内容には目を通します」に変更 |
| A12 | Low | `-a` 短縮形・MCP `pullNumber` の分岐が未検証 | 指摘の M5/M8 | **修正**: G55/G56 を追加 |
| A13 | Low | 決定論ゲートの grep が緩い（`"Issue"` 等は文意を問わない・MCP 3 件は matcher 登録を保証しない） | 目視 | 見送り（MCP matcher 登録は G13〜G16 の実挙動＋手動 No.11 で担保。文言 grep は存在確認の位置づけ） |
| A14 | Low | 手動テスト No.4 の判定根拠（hook 出力なし）が「ready が判定対象から外れる回帰」と区別できない | 記録読解 | 見送り（観点は自動テスト G3/G18 で担保。記録に限界を明記済み） |

### 修正後の検証

- `test_pretooluse_gh_pr_guard.sh`: 修正前 `pass=45 fail=22`（Red）→ 修正後 `pass=67 fail=0`
- `test_pr_base_sync.sh`: `RESULT: OK (21/21 cases, 30 assertions)`
- 回帰: push guard `pass=87`・worktree guard `pass=27`・checkout guard `pass=14`（fail=0）
- code-review.sh の omission-lint OK・宣言ゲート 22 件 exit 0

### A7/A8 のユーザー判断（2026-10-16）

計画書の対象動詞を広げる設計判断のため SKILL 3-3 に従い確認した。ユーザー回答: **「checkout=止める・update-branch=確認」**。計画書 R9/R10・設計上の限界・runbook（「手元に checkout しない」）を更新し、`_GH_PR_BLOCK_VERBS=("merge","checkout")`・`_GH_PR_ASK_VERBS` に `update-branch`・値付きフラグに `--branch` を追加。G57〜G61 を追加（Red `pass=69 fail=3` → `pass=72 fail=0`）。

第 1 周の新規 High 2 件はいずれも修正済み。修正の妥当性を含めて第 2 周で反証する。

## 第 2 周（エージェント 3・累計 7）

| # | 観点 | NEW_CRITICAL | NEW_HIGH |
|---|---|---|---|
| 1 | ロジック回避・実機 repro（修正の妥当性） | 1 | 2 |
| 2 | テストの false-green・tautology（修正の妥当性） | 0 | 7 |
| 3 | 要件・脅威モデルの網羅漏れと回帰 | 0 | 2（うち 1 件は #1 の Critical と同一） |

### findings（重複統合後）

| ID | 重大度 | 指摘 | 対応 |
|---|---|---|---|
| B1 | **Critical** | 第 1 周の修正で値付き短縮フラグ表を全サブコマンド共通にしたため、merge の `-m`（`--merge`・値なし）を値ありと誤認。`gh pr merge -m 257` で 257 を読み捨て、カレントブランチ（自前）を照会して fork merge が素通し（#1・#3 が独立検出。**第 1 周の修正が持ち込んだ回帰**） | サブコマンドごとのフラグ表 `_GH_PR_SPECS`（gh 2.88 の help 準拠）に作り直し、表にないフラグは推測せず ask（G62〜G64） |
| B2 | High | ヒアドキュメント本文（コミットメッセージ・PR 本文・文書）の `gh pr merge 257` で誤 block。レビュー中に実 hook でも発生 | 本文行を判定前に除外（終端なしは除外しない fail-safe）（G65〜G68） |
| B3 | High | `then`/`do`/`{`/`!`/前置リダイレクトの後ろの gh を検出しない | `gh` をコマンド中の位置に依らず検出（G69〜G74） |
| B4 | High | 値付きラッパー（`nice -n`・`sudo -u`・`env -u`・`timeout -s`）で gh に到達しない・`xargs` | 位置非依存検出で解消。識別子なしで前に別コマンドがある形は ask（G75〜G84） |
| B5 | High | `#` コメントが行末改行ごと読み捨てられ区切りが消える | 改行を `\n;\n` に置換してからトークン化（G89・G90） |
| B6 | High | 最初の block で return・照会 1 件のため、先頭の自前 PR で後続の fork を見逃す | 検出した全 `gh pr` を判定（`_guard_gh_pr_targets`）（G94〜G96） |
| B7 | High | false-green: 区切り `|`・`` ` ``、各ラッパー、複数区切り、ValueError 経路にテストなし | 各経路のテストを追加（G80〜G83・G91〜G93 ほか） |
| B8 | High | gh 既定エイリアス `gh co`（= pr checkout）で checkout block を回避 | `co` を checkout と同一視（G101・G102）。利用者定義エイリアスは設計上の限界に明記 |
| B9 | Medium | `gh pr --repo o/r merge`（pr と verb の間のフラグ）で verb を誤認 | pr 後・verb 前のフラグを処理（G85・G86） |
| B10 | Medium | `2>&1` が位置引数扱いになり自前 PR でも ask・識別子取り違え | fd 番号付きリダイレクトを除去しリダイレクトは演算子＋行き先ごと除外（G87・G88） |
| B11 | Medium | グローバル `--repo=`/`-Rx`/サブコマンド側 `-R`/値連結 `-bLGTM` の分岐にテストなし | G97〜G100 を追加 |
| B12 | Medium | `cd <別 clone> && gh pr merge`（識別子なし）は hook 側のカレントを照会 | 識別子なしで `cd`/`pushd` がある形は ask（G103） |
| B13 | Medium | `git fetch pull/N/head`・`gh pr diff | git apply` 等の別経路で fork コードを持ち込めるのに「block される」と過大記述 | 計画書「設計上の限界」と runbook に対象外として明記し、do 層の手順で補う |
| B14 | Low | checkout block 文言に代替手段がない | 文言に `gh pr diff` / `gh pr view` と checkout の危険を追記 |
| B15 | Low | `export GH_REPO=…;`・cwd の変更を追跡しない | 設計上の限界に明記 |
| B16 | Low | 安全側の等価変異（ask が増える方向） | 見送り（実害なし） |

### 修正後の検証

- 新テスト（G62〜G106）を直前コミット 670d184 のガードに当てると `pass=90 fail=27`（Red）→ 作り直し後 `pass=117 fail=0`
- 回帰: push guard 87・worktree guard 27・checkout guard 14・pr-base-sync 21/21（fail=0）
- 自前 PR の正規手順（/close の識別子なし merge/ready・`edit --body "$(cat <<'EOF' …)"`）は不変（G104〜G106）

第 2 周の新規 Critical/High はすべて修正済み。修正の妥当性を第 3 周（上限）で反証する。

## 第 3 周（エージェント 4・累計 11）— 上限到達・未収束

| # | 観点 | NEW_CRITICAL | NEW_HIGH |
|---|---|---|---|
| 1 | ロジック回避・実機 repro | 0 | 2 |
| 2 | テストの false-green・tautology（変異 130 個） | 0 | 8 |
| 3 | 要件・脅威モデルの網羅漏れ | 0 | 2（1 件は #1 と同一原因） |
| 4 | 過剰検出・日常運用への副作用（動的観点） | 0 | 1 |

### findings（重複統合後）

| ID | 重大度 | 指摘 |
|---|---|---|
| C1 | High | 行継続 `\<改行>` で 1 コマンドが分断され、`gh pr \⏎ merge 257` 等が素通し・`review 257 \⏎ --approve` の ask が消える・自前 PR の折り返しで毎回 ask（#1・#3・#4） |
| C2 | High | shlex 既定の `commenters='#'` が語中の `#`（`a#b`・`${#x}`・URL）をコメント扱いし、同じ行の後ろの `gh pr merge` が消える（#1） |
| C3 | High | ヒアドキュメント除外がクォート/コメント/算術式内の `<<WORD` も開始とみなし、後続の実コマンドを本文として隠す（B2 修正の回帰。#2・#3） |
| C4 | High | ヒアドキュメント終端語の正規表現が狭く（`END-OF-MSG`・`EOF.`・`\EOF`・CRLF）、本文が除外されず正当なコミット/文書作成を誤 block（#4） |
| C5 | High | false-green: 値なしフラグを値ありに変える変異（merge の -r/-s/-d/--squash 等・checkout の -f/--force 等）が生存。fork が先・自前が後の順、here-string、`<<-`、`--`、識別子より前のリダイレクト、ValueError fallback（`$'..'`）にテストなし（#2） |
| C6 | Medium | プロセス置換 `<(…)`・クォートなし `$(…)` が値の位置にあると識別子を失い自前照会で素通し（#1） |
| C7 | Medium | ask 種別フラグ表（ready --undo・update-branch --rebase）・pushd・未知短縮フラグ・review の ambiguous の変異が生存（#2） |
| C8 | Low | runbook 末尾のまとめが MCP merge=block・update-branch=ask を反映していない／計画書 R8〜R10 の関数名が旧実装のまま（#3） |
| C9 | Low | 照会の重複排除・件数上限なし（hook タイムアウトで fail-safe が空洞化し得る）・変数指定の PR は毎回 ask・クォートなし引数中の文字列でも照会（#4） |
| C10 | Low | `gh.exe`（WSL から Windows 版）を検出しない（#1） |

補足: #2 のエージェントは probe の 1 つで誤ってリポジトリの cwd で `git commit -m …` を実行したと申告（ステージ無しで「nothing added to commit」・変更なし）。#4 は並行エージェントにスクラッチパッドのスタブを上書きされ、自前の mktemp で測り直したと申告。

### 判定

SKILL 3-2 の上限（最大 3 周）に到達し、新規 High が残るため**自動 OK にせず打ち切り**、ユーザーへエスカレーションする（上限到達・未収束）。所見: 周回ごとにシェル構文の別の穴が見つかっており、「シェルを正確に解釈して漏れなく検出する」方式は収束しにくい。

### ユーザー判断（2026-10-16）と第 3 周対応

ユーザー回答: **「二重の構えに変更＋もう 1 周」**（上限を 1 周超えての再検証を承認）。

- 精密判定の前処理 `_shell_code` を bash の規則（クォート状態・行継続・語頭 `#`・クォート外の `<<WORD` と終端語全体・CRLF・here-string・算術式）で書き直し（C1〜C4）
- 値の位置のプロセス置換・クォートなしコマンド置換は ask（C6）、review の approve 判定を ambiguous 判定の後へ（C1 の派生）、`gh.exe` 検出（C10）、同一 PR の照会を 1 回に（C9 の一部）
- **安全網** `_GH_COARSE_RE`: 粗い検出の件数 > 精密判定の件数なら ask（block しない）。精密判定の穴は素通しではなく確認になる
- テスト G107〜G157・FG-F/G を追加（C5・C7 の false-green を含む）。直前版で `fail=21`（Red）→ `pass=170 fail=0`
- runbook のまとめ・計画書 R8〜R10 の記述を実装に合わせて更新（C8）
- 見送り: C9 の hook タイムアウト設定・変数指定 PR の ask 文言（Low）

VERDICT: HIGH
