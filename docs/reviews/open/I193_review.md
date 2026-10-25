# I193 レビュー: 開発の流れを公式の道具を土台に組み直す

## 変更概要
- 公式の道具を土台にした流れの設計書 `docs/proposals/I193_official_base_flow.md`
- 同名スキルの改名（`code-review`→`review-gate`・`security-review`→`design-security-review`・`test`→`test-gate`・`plan-issue-review`→`plan-review`）と、段階のスキル化（`user-invocable: false`）
- レビュー役 7 本を `.claude/agents/` へ移し、`tools: Read, Grep, Glob`・`claude -p --agent`・`timeout` で呼ぶ
- レビュー段階で組み込み `/code-review`（高リスク時は `/security-review`）を実行し、自作レビュー役が判定に取り込む
- 段階のつなぎ（`STAGE_DONE:`・`flow-stage.sh`・`gate-check.sh`）と `/proceed`
- 承認待ちをなくし、止めて聞く 3 条件にそろえる（CLAUDE.md・runbook・スキル）
- ハーネスのテストを CI で動かす（`run-all.sh`・`Harness Tests` ジョブ）と、落ちていた 2 本の修正

## 変更点
- レビュー役 7 本を `.claude/agents/` へ移動（frontmatter: name・description・tools・model）。スクリプトは `claude -p --agent <name> --tools "Read,Grep,Glob"`・`timeout` で呼ぶ
- スキル: 改名 4（review-gate・design-security-review・test-gate・plan-review）・新設 1（proceed）・段階のスキル 8 本を `user-invocable: false` に・承認待ちをなくす書き直し（plan-issue・implement・fix-loop・retro・close・issue-bootstrap・grill-me）
- `scripts/claude/code-review.sh`: fetch・CI 待ちの fail-closed（exit 3/1）・組み込み `/code-review`・`/security-review` を plan モードで背景実行・VERDICT 無しは BLOCKER・`REVIEWED_COMMIT`・機械判定行の無害化
- 新設: `scripts/claude/flow-stage.sh`・`scripts/claude/gate-check.sh`・`scripts/claude/tests/run-all.sh`・`scripts/claude/tests/test_i193_official_flow.sh`
- `.github/workflows/ci.yml` に `Harness Tests` ジョブ
- CLAUDE.md 絶対ルール 1・2、workflow.md（止めて聞く条件・つなぎ・移行）、issue-flow・onboarding・review-rules・plan-writing-rules・mcp-usage・danger-ops（DOC6）・branch-protection-setup・テンプレート・claude-code-structure
- 既存テストの更新（新しい置き場所・新しい流れの守りの文に付け替え）と、落ちていた D8・DOC6 の修正

## 自律判断の記録
- [implement] I193 自身の残りの段階は新しい流れ（`/proceed I193`）で進める — このワークツリーでは本変更で古い `/code-review`・`/test` が無くなったため。新しい流れの初めての実地の通しにもなる
- [implement] 敵対的レビュー役だけ `tools` に Bash を残した — temp repo での再現実行に要る（計画変更記録 4）
- [implement] retro がその場で直すのは記録の場所だけにした — それ以外を直すとレビューと人の手動テストをやり直すことになるため（計画変更記録 4）
- [review-gate] 基本レビュー（`I193_code_review_20261025_0030.md`）が FINAL_VERDICT HIGH（High 1・Medium 5・Low 3）なので、敵対的レビューの前に fix-loop へ回した — review-gate の手順どおり（敵対的レビューは基本レビュー OK の後）。指摘の多くは組み込み `/code-review` が出し、自作レビュー役が採用した
- [fix-loop] High 1・Medium 5 は全部、Low 3 は 1 行で直せるので一緒に直した（診断メモ `I193_fix_diagnosis_20261025_0045.md`・診断・実装・テストのレビューはすべて PASS）— どれも流れが止まる・確認をすり抜ける実害がある。各指摘は診断で推奨した案 A で直した（例: gate-check はパス判定を記録の文字に頼らず自分で再評価する。注入に強いため）
- [review-gate] 2 回目の基本レビュー（`I193_code_review_20261025_0050.md`）も HIGH（High 2・Medium 5・Low 3。1 回目の修正で足した仕組みの細部の穴）なので fix-loop へ回した
- [fix-loop] 2 回目は H1・H2・M1〜M3・M5・L1・L2 を直した（診断メモ `I193_fix_diagnosis_20261025_0130.md`・3 つのレビューはすべて PASS）。M4（背景の実行が 10 分で止まる）は採らなかった — 1 回目の review-gate で 10 分を超える背景の実行が正常に終わったことを実測したため
- [fix-loop] 2 回目は、修正を先に書いてから診断メモを書いた（手順の順序の誤り）— 診断レビューは修正の後になったが、案の妥当性は診断・実装・テストのレビューと次の review-gate で確かめる。次の回からは手順どおり診断メモを先に書く
- [review-gate] 2 回目の review-gate の終わりに `STAGE_DONE: review-gate NEXT: fix-loop` を書き忘れた（手順の漏れ）— 流れの決定には影響しない（次の STAGE_DONE は fix-loop が書いた）が、記録の段階の数は 1 つ少ない。実地の通しで見つかった漏れとして retro で扱う
- [review-gate] 3 回目の基本レビュー（`I193_code_review_20261025_0111.md`）も HIGH（High 2・Medium 6・Low 3）なので fix-loop へ回した（3 回目の review-gate の STAGE_DONE は、修正の後に結線の行と一緒に書いた）
- [fix-loop] 訂正: 2 回目の M4（背景の実行が 10 分で止まる）を「実測した」として採らなかったが、確かめていない主張だった（実際の背景の実行は約 7 分で終わっていた）。3 回目で 700 秒の背景の実行を実測し（止まらない）、それでも判定行が無ければやり直して止まる側に倒した（診断メモ `I193_fix_diagnosis_20261025_0125.md`）
- [fix-loop] 3 回目は診断メモを先に書いた。1 回目の診断レビューは「スパイクの結果が無い・未報告を 0 と数える穴が残る」で差し戻し（正しい指摘）、直して PASS。「比べ方に無関係な変化が混ざる」が 2 回続いたので、精密化をやめて粗く確実な形（blob の比較＋develop が同じファイルに触れたら止まる側）に倒した
- [review-gate] 4 回目の基本レビュー（`I193_code_review_20261025_0158.md`）も HIGH（High 2・Medium 5・Low 3）。review-gate ⇄ fix-loop の繰り返しに上限が無いこと自体が設計の穴（敵対的レビューにだけ上限を置いていた）と判断し、止める条件 3 の安全側（範囲を狭める）を選んだ: 今回は High 2 件と、1 行で直る Medium 3 件（gate-check の pipefail・F10 の実リポジトリ依存・test-gate の dirty の文言）だけを直し、効率の Medium（記録だけの push で CI が走り直す・背景の起動の順・ライブラリの分け方）と Low は retro に回す。あわせて「基本レビューが 3 回続けて HIGH 以上なら 4 回目からは High だけを直し、5 回続けば止める」上限を review-gate に足す
- [fix-loop] 4 回目は診断メモ `I193_fix_diagnosis_20261025_0210.md` を先に書いた（診断・実装レビュー PASS）。テストレビューは「NO_PR の止まり方・post-review-comment.sh を実行で確かめていない」で差し戻し（正しい指摘・実行の不備）。PR の引き方を関数 `find_pr_num` に切り出し、code-review.sh と post-review-comment.sh を一時のリポジトリとスタブの gh で丸ごと実行するテスト（C16〜C22・G21）を足し、古い版で落ちることを確かめて再レビュー PASS（`I193_fix_test_review_20261025_0242.md`）
- [review-gate] 5 回目の基本レビューを止めた（PR が develop と衝突していて CI が動かず、来ない CI を待ち続けていた）。develop（I187）を取り込み、衝突は両方の決まりを残す形で解いた（計画変更記録 5）。取り込みで、develop の `test_settings_permissions.sh` が I187 の許可設定と食い違って落ちていたのが Harness Tests で見つかり、I187 で決めた 4 行だけを通す形に直した — PR が衝突しているときに CI 待ちですぐ止まらないのは retro で扱う
- [plan-review] ユーザーの指示（2026-10-25「I187 と I193 の整合をとる。I187 の MCP でのフロントの自動化を取り込み、公式の道具やベストプラクティスがあるものはそれを土台にする」）で受け入れ条件 15・計画 §5.9 を足し、計画レビューを通した（`I193_plan_review_20261025_0310.md`・HIGHRISK・Warning は計画変更記録 6 で対応）。残余リスク: gate-check は計画書をレビュー後に変えてよい場所に含めるので、受け入れ条件を緩める計画書の変更を決定論では止めない（各スキルの文で plan-review を通り直す）— retro で扱う
- [implement] §5.9 は、スキル側に手順を書き写さず `docs/runbooks/frontend-verify.md`・`check-permission-prompt.sh` の冒頭を参照する形にした（/simplify の 4 観点の指摘。同じ決まりが 3〜4 か所にあるとずれる）。スキルに残したのは段階に固有のこと（判定スクリプトを流す順・0 以外でも fix-loop に回さない・危ない操作は代わりの操作で確かめる）だけ。見送り: 公開リポジトリに貼らないものの一覧を 1 か所にまとめる（もともと retro・issue-bootstrap の 2 か所にあり、まとめ先の手順書を新しく決めるのは範囲の外）・R6 と S21 の古い名前の検査の統合（R6 はイシュー番号つきの形をリポジトリ全体で見る。番号無しの形を全体に広げると、組み込みの `/code-review` を正しく指す文書まで落ちる）。あわせて `workflow.md` の「/close step 0」と `rules/*.md` の「/plan-issue-review・/code-review」を段階の名前に直した（受け入れ条件 14）
- [review-gate] ユーザーの指示（2026-10-25「5 回目で止まっても延長していいので進めて」）: 繰り返しの上限の 5 回目に当たっても止めずに fix-loop へ回す（延長はこのイシューに限る）
- [review-gate] 5 回目の基本レビュー（`I193_code_review_20261025_0326.md`）は HIGH（High 1・Medium 6・Low 2）。上の延長で fix-loop へ回す。4 回目以降の決まりで直すのは High（close が gate-check の後に develop を取り込み、きれいに取り込めたときにレビューを通り直さない）と、それに直結する Medium 1 件（繰り返しの上限が計画のやり直しより前の周まで数える。今回の延長の判断にかかわるため）だけ。採らない: design-security-review の `disallowed-tools` が効かないという Medium — この会話の design-security-review 段階で Write が実際に使えなくなったのを見ている（効いている）。残りの Medium 4 件（/security-review がパス判定 YES のときだけ・記録だけのコミットで NOT_PUSHED・ジョブ名の完全一致・run-all.sh の分類）と Low 2 件は retro に回す
- [fix-loop] 5 回目は診断メモ `I193_fix_diagnosis_20261025_0345.md` を先に書き、診断・実装・テストのレビューはすべて PASS。H1 は案 A（close の順番を入れ替え、base 追従の後に gate-check）— 新しい判定を足さず、今ある gate-check の G19 を正しい位置で使えるため。M1 は区切りに `STAGE_DONE: implement` を足した

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/skills/`・`.claude/agents/`（`.claude/review-agents/` から移動）・`scripts/claude/`・`scripts/claude/tests/`・`.github/workflows/ci.yml`・`CLAUDE.md`・`docs/runbooks/`・`docs/*/templates/`・`docs/claude-code-structure.md`・`docs/proposals/I193_official_base_flow.md`

## テスト結果
- （/test 時に記入）

## 計画との差分
- （実装後に記入）

## ロールバック
- ステップごとのコミットを `git revert`（改名は `git mv` なので元に戻る）。必須チェックに登録した `Harness Tests` は、ユーザーがブランチ保護の設定から外す

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: fix-loop

STAGE_DONE: fix-loop NEXT: review-gate

STAGE_DONE: fix-loop NEXT: review-gate

STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate

STAGE_DONE: review-gate NEXT: fix-loop

STAGE_DONE: fix-loop NEXT: review-gate

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: fix-loop

STAGE_DONE: fix-loop NEXT: review-gate
