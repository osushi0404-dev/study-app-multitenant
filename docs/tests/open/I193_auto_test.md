# I193 自動テスト: 開発の流れを公式の道具を土台に組み直す

実行コマンド（例）: アプリのコード変更が無いため `docker compose exec backend python -m pytest`・`docker compose exec frontend npm test`・E2E は非該当（CI では今までどおり動く）

結果:
- backend: 非該当
- frontend: 非該当

## テストケース

合否はすべて終了コード（合格=exit 0・不合格=非ゼロ）。否定・不在の判定には、テストの中に失敗注入（FG: 一時コピーを壊して、その判定が非ゼロになることを確かめる）を付ける。

| TC | 内容 | 期待値 |
|---|---|---|
| TC-01 | `bash scripts/claude/tests/test_i193_official_flow.sh`（新設）。下の R・F・G・S・D の各項目と、その FG を含む | exit 0・`fail=0` |
| TC-02 | `bash scripts/claude/tests/test_review_verdict.sh`（更新）: `detect_code_verdict` は VERDICT 行も表の印も無い入力で `BLOCKER`、`VERDICT: OK` で `OK`。`REVIEWED_COMMIT:` 行を出す関数が HEAD の SHA を出す | exit 0 |
| TC-03 | `bash scripts/claude/tests/test_review_gates.sh`（ゲートの分類と実走。案内の文言の変更に合わせて更新） | exit 0 |
| TC-04 | `bash scripts/claude/tests/test_adversarial_trigger.sh`（RISK とパス判定。参照パスを `review-gate`・`.claude/agents/` に更新） | exit 0 |
| TC-05 | `bash scripts/claude/tests/test_fix_review.sh`（FIX_GATE の純関数。`claude -p --agent` と `timeout` の呼び出しに更新） | exit 0 |
| TC-06 | `bash scripts/claude/tests/test_i181_review_slim.sh`（パスの改名・D8 の修正） | exit 0・`fail=0` |
| TC-07 | `bash scripts/claude/tests/test_i182_docs.sh`（DOC6 の修正） | exit 0・`fail=0` |
| TC-08 | `bash scripts/claude/tests/test_i185_harness_docs.sh`（文言の固定と fixtures を新しい流れに更新） | exit 0・`fail=0` |
| TC-09 | `bash scripts/claude/tests/test_i114_retro_plain_output.sh`・`bash scripts/claude/tests/test_i180_retro_triage.sh`（retro の自律化に合わせて更新） | どちらも exit 0 |
| TC-10 | `bash scripts/claude/tests/test_review_commit_lifecycle.sh` | exit 0 |
| TC-11 | `bash scripts/claude/tests/test_auto_test_template_lint.sh`（テンプレの文言の変更に合わせて更新） | exit 0 |
| TC-12 | `bash scripts/claude/tests/test_settings_permissions.sh`（settings.json は変えないので、そのまま合格すること） | exit 0 |
| TC-13 | `bash scripts/claude/tests/run-all.sh`（全テスト） | exit 0。FG: `TEST_DIR` に「exit 1 だけするテスト」を 1 本置いたフォルダを渡すと非ゼロ（TC-01 F9 で確かめる） |
| TC-14 | PR #327 の CI に `Harness Tests` が出て成功している: `gh pr checks 327` の出力に `Harness Tests` の行があり、`pass` | 手動テスト No.6 で確かめる（CI の結果のため） |

### TC-01 の項目
R: 名前と置き場所
- R1 `.claude/skills/` に `code-review`・`security-review`・`verify`・`simplify`・`review`・`test` のフォルダが無い（組み込みの名前を隠さない）
- R2 段階のスキル（`plan-review`・`design-security-review`・`implement`・`review-gate`・`test-gate`・`fix-loop`・`retro`・`close`）の frontmatter に `user-invocable: false` があり、`disable-model-invocation: true` が無い
- R3 `plan-issue`・`grill-me` は `disable-model-invocation: true`。`proceed`・`issue-bootstrap` は `disable-model-invocation` が無い
- R4 `.claude/agents/` に 7 本があり、それぞれ frontmatter の `tools:` が `Read, Grep, Glob` だけ。`.claude/review-agents/` が無い
- R5 `scripts/claude/*.sh` と `.github/workflows/*.yml` に `ultra`・`claude-code-action` が無い
- R6 古い流れの参照が無い: `CLAUDE.md`・`docs/runbooks/*.md`（`legacy/` を除く）・`.claude/skills/*/SKILL.md`・`.claude/agents/*.md`・`scripts/claude/*.sh`・`scripts/migration_verify/*.py`・`docs/*/templates/*.md`・`docs/claude-code-structure.md`（2026-10-25 計画変更記録 5 で `docs/runbooks/frontend-verify.md` の `/test`・`/code-review`・`/close` の書き方〔`` `/test` `` の形〕も対象に足す）に、`/implement I`・`/code-review I`・`/test I`・`/fix-loop I`・`/retro I`・`/close I`・`/security-review I`・`/plan-issue-review`・`review-agents` のどれも無い（同じ語を `$ARGUMENTS` で書いた形も含む）
  - R6 の FG: 検索対象を一時フォルダに写し、`docs/runbooks/workflow.md` の写しに `/test I123` を 1 行、`.claude/skills/close/SKILL.md` の写しに `review-agents/` を 1 行足して R6 を実行し、それぞれ非ゼロで終わることを確かめる（検索対象のパスを引数で差し替えられる形にする）
- R7 `scripts/claude/*.sh` の `claude -p` の行はすべて `timeout` を伴い、`--system-prompt` と `claude-sonnet-4-6` が無い

F: `flow-stage.sh`（fixtures の記録を一時フォルダに置いて実行）
- F1 最後の行が `STAGE_DONE: plan NEXT: plan-review` → 出力 `NEXT_STAGE: plan-review`・exit 0
- F2 `STAGE_DONE:` 行が 3 行あるとき、最後の行の NEXT を返す
- F3 `STAGE_DONE:` 行が無い → exit 2
- F4 記録ファイルが無い → exit 2
- F5 NEXT が一覧に無い語（例 `NEXT: deploy`）→ exit 2
- F6 本文の途中の引用（行頭でない `STAGE_DONE:`）は数えない
- F9 `run-all.sh` に失敗するテストを 1 本入れたフォルダを渡すと非ゼロ

G: `gate-check.sh`（一時の git リポジトリで、記録とコミットを作って実行）
- G1 最新のコードレビュー記録が `VERDICT: OK`・`REVIEWED_COMMIT` が HEAD → exit 0
- G2 `REVIEWED_COMMIT` の後に `docs/reviews/` だけ変えたコミット → exit 0
- G3 `REVIEWED_COMMIT` の後に `scripts/` を変えたコミット → exit 1
- G4 最新の記録が `VERDICT: HIGH` → exit 1（古い記録が OK でも、最新を見る）
- G5 `REVIEWED_COMMIT` 行が無い → exit 1
- G6 `RISK: YES` で、敵対的レビュー記録が無い／最新が `VERDICT: HIGH` → exit 1。最新が `VERDICT: OK` → exit 0
- G7 コードレビュー記録が 1 本も無い → exit 1
- G8 `RISK: YES` で、敵対的レビュー記録は `VERDICT: OK` だが、その `REVIEWED_COMMIT` の後に `scripts/` を変えたコミットがある → exit 1
- G9 コードレビュー記録は OK で HEAD と一致しているが、作業ツリーに `scripts/` のコミットしていない変更（または未追跡のファイル）がある → exit 1。`docs/reviews/` の未追跡ファイルだけなら exit 0
- G10 日本語のファイル名（`scripts/日本語.sh`）をレビューの後に足したコミット → exit 1（ファイル名の引用符で判定をすり抜けない）

S: スキルの中身（守りの文が消えたら落ちる。各項目に FG）
- S1 `plan-issue` に「承認ポイントを提示して停止」が無く、`proceed` を呼ぶ手順がある
- S2 `implement` に「/implement を実行して初めて」が無く、`/simplify` を呼ぶ手順がある
- S3 `test-gate`・`close` の最初の手順で `gate-check.sh` を実行し、exit 1 なら `review-gate` に戻ると書いてある
- S4 `fix-loop` の終わりが `NEXT: review-gate` だけで、`/test に戻る` が無い
- S5 `review-gate` が `code-review.sh` を実行し、敵対的レビューの修正の後に `code-review.sh` を実行し直すと書いてある
- S6 `retro` が `issue-bootstrap` を呼ぶ手順を持ち、「ユーザーの判断を待つ」が無い
- S7 段階のスキルとユーザー用スキルが、止める条件を `docs/runbooks/workflow.md` の節を指して参照している
- S8 `code-review.sh` の組み込み `/code-review medium origin/develop...HEAD` と `/security-review` の実行行が、どちらも `--permission-mode plan` と `timeout` を伴う。最初に `git fetch origin develop` がある
- S9 `code-review.sh` の CI 待ち: `gh` の偽物（PATH に置いたスタブ）で「ずっと pending」を返すと `CI_WAIT: TIMEOUT`・exit 3、「fail」を返すと `CI_WAIT: FAIL`・exit 1（待ち時間は環境変数で数秒に縮める）
- S10 `review-gate` が `code-review.sh` を `run_in_background` で実行し、exit 3 は 1 回だけやり直すと書いてある
- S11 `retro`・`issue-bootstrap` に「コマンドの出力・ログ・環境変数・記録の中身を貼らない」がある
- S12 `docs/runbooks/workflow.md` の止める条件 2 に、安全装置の集合（`.claude/settings.json`・`scripts/claude/hooks/`・`.github/`・`.pre-commit-config.yaml`・`.secrets.baseline`）があり、`code-review.sh` の `path_risk_trigger` の集合と一致する（集合の一致を比べる。片方だけに足すと落ちる）
- S13〜S20 fix-loop 1〜4 回目で足した守り（詳細は「再発防止記録」1〜4。タイマーと PR コメントはスクリプト経由・`CI_WAIT: NO_PR`・繰り返しの上限〔4 回目・5 回目の文言〕・test-gate の dirty は fix-loop へ）。いずれも FG 付き
- S21 I187 の決まりの組み込み（受け入れ条件 15）: `implement` に `docs/runbooks/frontend-verify.md` の手順で Playwright MCP を使って画面を確かめる手順がある。`test-gate` に `check-frontend-evidence.sh`・`check-manual-test-executor.sh`・`check-permission-prompt.sh` の 3 本と、その判定が 0 以外のとき「fix-loop に回さない」がある。FG: それぞれの写しから 1 つずつ消すと不合格になる

D: 文書
- D1 設計書 `docs/proposals/I193_official_base_flow.md` に §2〜§7 の見出しがあり、§2 に `https://code.claude.com/docs/en/best-practices` がある
- D2 設計書 §3 の表に L1〜L14 の行がある
- D3 設計書 §4 の表に `/code-review`・`/security-review`・`/simplify`・`/verify` の行があり、それぞれ「入れる」か「入れない」がある
- D4 `docs/runbooks/workflow.md` に止める 3 条件の節（要件・基本設計・UI/UX／取り消せない操作／安全側の選択肢）と「## 自律判断の記録」の説明がある
- D5 `CLAUDE.md` に「ユーザー承認なしにコード変更」が無く、`workflow.md` の止める条件への参照がある
- D6 `docs/runbooks/workflow.md` に、着手済みイシューは各ワークツリーの古いスキルで最後まで進める旨がある
- D7 `docs/runbooks/workflow.md` の「使うスキル」に `/issue-bootstrap`・`/grill-me`・`/plan-issue`・`/proceed` があり、段階のスキルはユーザーが打たないと書いてある

## 決定論ゲート（自動実走）
<!--
  I084: review-gate（code-review.sh）がこの見出し直後の単一 bash ブロックを 1 行 1 コマンドで抽出し、実走して実 exit code を VERDICT に注入する。
-->
```bash
bash scripts/claude/tests/test_i193_official_flow.sh
bash scripts/claude/tests/test_review_verdict.sh
bash scripts/claude/tests/test_review_gates.sh
bash scripts/claude/tests/test_adversarial_trigger.sh
bash scripts/claude/tests/test_fix_review.sh
bash scripts/claude/tests/test_i181_review_slim.sh
bash scripts/claude/tests/test_i182_docs.sh
bash scripts/claude/tests/test_i185_harness_docs.sh
bash scripts/claude/tests/test_i114_retro_plain_output.sh
bash scripts/claude/tests/test_i180_retro_triage.sh
bash scripts/claude/tests/test_review_commit_lifecycle.sh
bash scripts/claude/tests/test_auto_test_template_lint.sh
bash scripts/claude/tests/test_settings_permissions.sh
bash -n scripts/claude/gate-check.sh
bash -n scripts/claude/flow-stage.sh
bash -n scripts/claude/tests/run-all.sh
```

TC-13（`run-all.sh`）はゲートの既定の時間上限（120 秒）を超えうるので、ここには書かず、CI（TC-14）と /test で実行する。

## 再発防止記録（fix-loop・2026-10-25）
- なぜ失敗したか: review-gate の基本レビュー（組み込み `/code-review` の指摘を自作レビュー役が採用）で、gate-check がパス判定を再現していない（High）・test-gate ⇄ review-gate の繰り返し・close 後の記録の分裂・CI 待ちが今の HEAD と全ジョブを見ていない・背景のプロセスの取り残し・レビュー中の HEAD の移動（Medium）が見つかった。共通の原因は「決定論の判定を 1 か所で持たず、後段がその一部だけを読む」「待つ・戻す処理の終わり方を、相手の状態（どのコミットか・何回目か）で決めていない」
- 何を変えたか: gate-check がパス判定を自分で再評価し、失敗の理由（REASON）を出す。test-gate・close は理由で戻り先を分け、gate-check で戻すのは 2 回続けない。close は CI 失敗時に記録を open に戻す。wait_ci は PR の headRefOid と手元の HEAD の一致・全ジョブの完了を待つ。背景のレビューは子孫まで止める。HEAD が動いたら BLOCKER。flow-stage.sh はルートへ cd
- セキュリティ上の考慮点: F1 は安全装置の変更を敵対的レビュー無しで通す fail-open だった。F4 は「CI を正とする」前提の抜けだった。どちらも fail-closed にした
- 次回どう防ぐか: TC-01 の G11〜G13・C4b・C10・C10b・C11・C12・F10 が回帰を止める（修正前の版では G11・C4b が合格してしまうことを実際に確かめた）。CI の Harness Tests が毎回流す

## 再発防止記録 2（fix-loop 2 回目・2026-10-25）
- なぜ失敗したか: 1 回目に足した仕組みの細部に穴があった（proceed の見分けが行番号で、記録の別の節への書き込みでずれる・gate-check が 2 点間の差を見るので develop の取り込みを数える・決定論ゲートの節とテンプレートを記録の場所として通す・porcelain の引用・PyYAML が無いときの握りつぶし）。共通の原因は「比べる値に、比べたいもの以外の変化が混ざる」こと
- 何を変えたか: STAGE_COUNT で見分ける・ブランチ自身の変更をファイルごとに比べる（merge-base から・行番号と index 行を除く）・決定論ゲートの節は抜き出したコマンドで比べる・記録の場所からテンプレートを外す・-z で読む・ジョブ名を読めないときは NO_JOBS で止める
- セキュリティ上の考慮点: M2 は、レビューの後に実行されるコマンド（決定論ゲート）をレビューなしで変えられる穴だった
- 次回どう防ぐか: TC-01 の F11・S13・G14〜G17・C10b（修正前の版で G14・G15・F11 が誤った結果になることを実際に確かめた）

## 再発防止記録 3（fix-loop 3 回目・2026-10-25）
- なぜ失敗したか: (1) 背景の実行の上限を確かめないまま長い処理とタイマーを任せ、2 回目には「実測した」と誤って書いた（実際は 7 分ほどで終わっていた）。(2) 「レビューの後に変わったか」の比べ方に、2 回目と同じ種類の穴（記録だけのコミット・バイナリ・文脈行・テンプレート・参考の出力の表）が残っていた
- 何を変えたか: 背景の実行が 700 秒を超えても止まらないことを実測し、それでも判定行が無ければやり直して止まる側に倒した。未報告の敵対的レビューの観点は合格に数えない。比べ方は粗く確実な形（ファイルの中身〔blob〕の比較＋develop が同じファイルに触れたら止まる側）にした。記録の場所の定義を 1 か所（is_record_path）にした
- セキュリティ上の考慮点: 未報告を合格に数える偽の OK と、バイナリ・テンプレートの素通りを塞いだ
- 次回どう防ぐか: TC-01 の G18〜G20・C13〜C15・S14〜S16（修正前の版で G18・G20 が素通りすることを実際に確かめた）。実測していないことを「実測した」と書かない（retro で扱う）

## 再発防止記録 4（fix-loop 4 回目・2026-10-25）
- なぜ失敗したか: (1) code-review.sh は PR を取れないと CI 待ちを丸ごと飛ばしていた（CI が赤でも先へ進みうる）。(2) review-gate の手順に `sleep 900`・`gh pr review` を直接書いていて、settings の allow に一致せず承認画面が出た。(3) 最初の修正のテストは文字列があるかだけを見ていて、分岐が壊れても緑のままだった（テストレビューで差し戻し）
- 何を変えたか: PR の引き方を `find_pr_num`（0=番号 / 1=gh の失敗 / 2=PR 無し）にし、1・2 はどちらも exit 1＋`CI_WAIT: NO_PR` で止める。タイマーと PR コメントを `review-timer.sh`・`post-review-comment.sh` に移した。gate-check の重なりの判定はパイプをやめて here-string にした（大きな一覧で SIGPIPE→141 になり「重ならない」に倒れていた）。review-gate ⇄ fix-loop の繰り返しの上限（4 回目から High・Blocker だけ・5 回目は止める）を足した
- セキュリティ上の考慮点: CI の失敗の素通り（fail-open）と、pipefail による重なりの見落とし（fail-open）を塞いだ
- 次回どう防ぐか: TC-01 の C16〜C22（code-review.sh・post-review-comment.sh を一時のリポジトリとスタブの gh で丸ごと実行）・G21（3000 件の一覧）・S17〜S20。古い版を差し込むと C16〜C18・G21・C19・C20・C22 が落ちることを実際に確かめた。fail-closed の修正は、文字列の検査でなく実行して確かめる

## 再発防止記録 5（fix-loop 5 回目・2026-10-25）
- なぜ失敗したか: close が「レビュー済みの HEAD か」（gate-check）を確かめた後に develop を取り込んでいた。きれいに取り込めたときは、取り込んだ後の中身がレビューを通らないままマージ依頼に進む（確かめた後に HEAD を動かす順番の誤り）。あわせて、繰り返しの上限が実装をやり直す前の周まで数えていた
- 何を変えたか: close は base 追従を先に、gate-check を後にした（gate-check の G19 が「develop も同じファイルを変えていた取り込み」を止める）。上限の数え方の区切りに `STAGE_DONE: implement` を足した
- セキュリティ上の考慮点: レビューの迂回を、新しい判定を足さずに今ある判定の位置で塞いだ（最後の守りは GitHub のブランチ保護）
- 次回どう防ぐか: TC-01 の S22・FG-S22・S19。HEAD を動かす操作は、それを確かめるゲートより前に置く

## 実行記録
- 計画時（2026-10-24）: 新設の TC-01 と、更新する TC-02〜TC-11 は実装前のため未実行。既存のテスト 33 本の現状は 31 合格・2 不合格（TC-06 の D8・TC-07 の DOC6。計画 §4.1）
