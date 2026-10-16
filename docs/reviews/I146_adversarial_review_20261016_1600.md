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

VERDICT: HIGH
