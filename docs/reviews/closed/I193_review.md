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
- [review-gate] 6 回目の基本レビューは OK。敵対的レビュー 1 周目（`I193_adversarial_review_20261025_1110.md`）は、I194 までの暫定の決まりで範囲を例外ファイル（ci.yml の Harness Tests）とその結果を使う CI 待ちに絞り、3 体とも報告して新規 High 0 → 通過。Medium（ワークフローのファイルの一部が読めないと、読めた分だけで CI 待ちが OK になる）と Low 2 件は retro に回す — GitHub の必須チェックが最後の守りで、High に直結しない
- [test-gate] 手動 No.8 の NG は設計書（`docs/proposals/`。記録の場所の外）の直しなので、自分では直さず fix-loop へ回した
- [fix-loop] 6 回目は案 A（設計書 §3 に L15・L16 を足す）。案 B（fix 系のレビュー役を消す）は、直しの診断・テストの空振りを止める場所が無くなるので採らなかった。診断・実装・テストのレビューはすべて PASS
- [review-gate] 7 回目の基本レビュー（`I193_code_review_20261025_1121.md`）は HIGH（High 2・Medium 5・Low 2）。test-gate を通った後なので上限の数え方では 1 回目。直すのは High 2 件だけにし、Medium 5 件（レビュー役の失敗を BLOCKER に合成して fix-loop を消費する・レビュー開始時の作業ツリーの確認・背景実行の上限・待つワークフローの決め打ち・組み込みのレビューを plan モードだけで読み取り専用にしている）と Low 2 件は retro に回す — どれも High に直結しない。基本レビューが毎回ブランチ全体を見て、100KB で切れた差分の別の場所から新しい指摘を出す（7 回目の High 2 件も以前からある部分）のは、retro で「2 回目以降は差分に絞る」を扱う
- [fix-loop] 7 回目は診断メモ `I193_fix_diagnosis_20261025_1135.md`。H1 は案 A（ユーザーが選んだときだけ受け入れの記録を作る。gate-check は変えない）、H2 は案 A（高リスクで /security-review が動かなければ HIGH・基盤の失敗は 1 回だけ実行し直す）。診断・実装・テストのレビューはすべて PASS。全体のテストの 1 回目が関係の無いテストまで一斉に落ちたが、単体では合格・流し直しで全部合格（一時的な環境の揺れ）
- [review-gate] 8 回目の基本レビューは OK。敵対的レビュー 2 周目（通算 2 周で上限。`I193_adversarial_review_20261025_1200.md`）は 1 周目からの差分だけを見て、3 体とも新規 High 0 → 通過。上限を使い切ったので直さず、Medium 4 件（失敗の印の部分一致で止まりすぎる・失敗の文言が 2 か所・実行し直しの回数を数える手順が無い・受け入れの記録の書き手を決定論で確かめない）と Low は retro に回す
- [human-test] No.5（`/` の候補の出方）は、ユーザーの指摘（「自分でできないか」）を受けて、Claude が tmux で起動した `claude` の画面を読み取って実施し OK。当初 Human に振った理由（`claude -p` は一覧を出さない）は誤りだった。No.6 はユーザーが develop の必須チェックに `Harness Tests` を登録し、Claude が API で確かめた
- [retro] Claude で確かめられる項目を Human に振った件（No.5）→ I195（#329）に同梱（コメント 6392967828）— I195 が「Human の振り分けの決まりを新しい流れへ移す」イシューで範囲が重なる。予防策は「Claude で実施可」に対話画面（tmux）を足す・Human の行に「試した手段:」を必須にして `check-manual-test-executor.sh` で止める・決定論のテストで固定。ユーザーの指示（2026-10-25「確実に実現・達成できるようにして」）に対応。スキル・スクリプトの直しは retro の書ける場所の外で、I193 に足すとレビューと手動テストをやり直すことになるため、同梱にした。ユーザーの確認（「コメントで確実に実現できるか」）を受け、コメントだけでは計画で見落とされうるので、#329 の本文の受け入れ条件に 4 項目として追加した（計画レビューが受け入れ条件と計画を突き合わせて止める）。I195 は I193 のマージ後すぐに着手する（ユーザーの選択）
- [retro] レビューと直しの行き来の長さ（基本レビュー 8 回・fix-loop 7 回）→ ユーザーの指示（2026-10-25）で I193 の後に起票する「レビュー時間の原因調査」に材料を渡す（下の「調査の材料」）。close の報告で起票を案内する。PR が develop と衝突して CI が動かず待ち続けた件・記録だけの push で CI が走り直す件も、時間の原因として同じ調査に含める
- [retro] main の必須チェックに `Harness Tests` が無い → 見送り（ユーザーの任意の操作として案内済み）— main 宛ての PR はふだんの流れで使っていない（過去に試しの 1 件だけ）
- [retro] review-gate の STAGE_DONE の書き忘れ（2 回目）・fix-loop の診断メモの順序の誤り（2 回目）・確かめていない「実測した」の主張（2 回目の M4）→ 見送り — どれも次の周の review-gate・fix-loop のレビューか自分で捕まえ、手戻りは 1 周以内。`/proceed` は STAGE_COUNT が増えないと止まる決定論の守りがある
- [retro] review・敵対的レビューで retro に回した Medium・Low（ワークフローの一部が読めないと CI 待ちが OK になる・/security-review がパス判定 YES のときだけ・ジョブ名の完全一致・失敗の印の部分一致で止まりすぎる・失敗の文言が 2 か所・実行し直しの回数の手順・受け入れの記録の書き手の確認・計画書の受け入れ条件を緩める変更を gate-check が止めない・レビュー役の失敗を BLOCKER に合成する・plan モードだけで読み取り専用）→ 見送り — 止まりすぎる側（fail-closed）か、GitHub の必須チェック・Code Owners の承認が最後の守りとして残るもの。新しい流れの最初の数イシューで実害が出たら、そのときに起票する（その場で捕まって手戻りの無い見逃しに手順を足さない）
- [close] fix-loop の診断メモ・テスト結果（`I193_fix_diagnosis_*`・`I193_fix_test_result_*`。名前に `_review_` を含まない）も、レビュー記録と一緒に closed へ移した — close の手順の回収の範囲（`*_review_*`）から漏れ、直下に残るため。手順の範囲の直しは、新しい流れの記録の名前に合わせる見直しとして I195 着手時までに気づいた側で扱う（記録の場所だけの問題で実害は散らかりのみ）
- [close] I188（#319）・I192（#325）は「I193 で残作業が無ければ取り下げ」のユーザー決定どおり、マージ後に取り下げを判断する（取り下げ＝イシューを閉じる操作はユーザーの確認のうえで行う）

## 振り返り

### かんたんなまとめ

#### 良かった点
- 新しい流れ（記録の `STAGE_DONE:` で次の段階を決める仕組み）で、I193 自身を計画レビューからテストまで最後まで通せた（理由: 作った仕組みを実際の流れで確かめられ、段階を飛ばす・戻る判断がすべて記録だけで決まった）
- 組み込みの `/code-review`・`/security-review`・`/simplify` を土台にし、自作は公式で止まらない漏れだけに絞れた（理由: 設計書で「公式で止まるか」を 1 行ずつ確かめてから自作を残したため）
- 繰り返しが長引いたとき、精密に直し続けず、範囲を狭める・止まる側に倒すに切り替えた（理由: 過去の振り返りで決めた「直しを過剰にしない」が効いた）

#### 今回の問題への直接の対処
- 手動テスト No.5 を、本当は Claude が確かめられるのに人に頼んだ。対話の画面は `claude -p` では見えないと思い込み、tmux という画面を裏で動かす方法を試さなかった。→ ご指摘のあと Claude が tmux で確かめて OK にし、記録を直した

#### 同じ問題を次回から防ぐ改善
- Claude ができる確認を人に振ってしまう問題。「Claude ができること」の一覧に無いものは、試す前に人に振られていた。人に振る理由のチェックも、理由が書いてあれば中身が間違っていても通していた。→ I195 にまとめて対応する。一覧に「対話の画面は tmux で確かめる」を足す。人に振る行には「何を試してだめだったか」を必ず書かせ、書いていなければ判定スクリプトが止める。この決まりが消えたらテストが落ちるようにする
- レビューと直しの行き来が 8 回続き、時間がかかりすぎた。基本のレビューが毎回ブランチ全体を見直し、前からある部分の別の穴を毎回出していた。→ ご指示どおり、I193 の後に原因調査のイシューを立てる。回数・指摘の中身などの材料を下に残した

### 詳細版

#### 良かった点
- 新しい流れ（flow-stage.sh・gate-check.sh・STAGE_DONE）で I193 自身を plan-review → design-security-review → implement → review-gate ⇄ fix-loop → test-gate → human-test まで通せた（実地の通し）
- 設計書 §3 で漏れごとに「GitHub で止まるか」「自作で載せるか」を判定し、自作を公式で止まらない漏れに限定できた
- 繰り返しが長引いた時点で、上限（3 回続けて HIGH なら High だけ・5 回で止める）を足し、精密化をやめて粗い fail-closed に倒した

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | 手動テスト | 対話画面（TUI）の観測手段を試さずに Human に振った | No.5 を Claude が tmux で実施し OK。手動テスト記録の実施者・理由を訂正（47fefb5） |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | スキル・規約 | 「Claude で実施可」が閉じた列挙で、列挙に無い観測手段は試す前に Human になる。Human の理由の判定は「空かどうか」だけで中身の誤りを通す | plan-issue・test-gate の実施者の基準に「対話画面にだけ出る表示は tmux で起動して画面を読む」を足し、Human の行に「試した手段:」を必須にして check-manual-test-executor.sh で無ければ不合格・画面系の理由で tmux が無ければ不合格にする。決まりを消した版で落ちるテストを足す（I195 #329 に同梱） | `.claude/skills/plan-issue/SKILL.md`・`.claude/skills/test-gate/SKILL.md`・`docs/runbooks/plan-writing-rules.md`・`docs/tests/templates/manual_test_template.md`・`scripts/claude/check-manual-test-executor.sh`・`scripts/claude/tests/` |
| P2 | プロセス | 基本レビューが毎回ブランチ全体（100KB で切れる差分）を見直し、以前からある部分の別の穴を High で出す。review-gate ⇄ fix-loop に当初は上限が無かった | ユーザー指示の「レビュー時間の原因調査」イシュー（I193 の後に起票）で扱う。仮説: 2 回目以降は前回からの差分に絞る・大きい PR の分割の目安・記録だけの push で CI を走らせない・PR の衝突を CI 待ちの前に確かめる・fix-loop の 3 レビューの要否 | `.claude/skills/review-gate/SKILL.md`・`scripts/claude/code-review.sh`・`.github/workflows/ci.yml` ほか（調査で確定） |

#### なぜを繰り返す原因分析
- P1: Why1 No.5 を Human に振った → Why2 `claude -p` で一覧が出ないので観測できないと判断した → Why3 「Claude で実施可」の列挙に対話画面が無く、列挙の外を試す手順が無い → Why4 Human の理由を判定するスクリプトが中身を見ず、誤った理由でも通る。根本原因: 実施者の振り分けで「試した手段」を求める手順と決定論の判定が無い（I193 固有の文脈を除いても成立）
- P2: Why1 基本レビューが 8 回 → Why2 毎回新しい High が出た → Why3 毎回ブランチ全体を見て、以前からある部分から別の穴を出した → Why4 2 回目以降の見る範囲と繰り返しの上限が設計に無かった。根本原因: review-gate の再レビューの範囲と上限の決まりが無い

#### 調査の材料（レビュー時間の原因調査イシュー向け）
- 計画レビュー 3 回（`I193_plan_review_20261024_2239`・`_2313`・`_20261025_0310`。3 回目は I187 との整合の範囲追加）・design-security-review 2 回（範囲追加の後にもう 1 回）
- 基本レビュー 8 回（00:30・00:50・01:11・01:58・03:26・10:53・11:21・11:46。結果は HIGH・HIGH・HIGH・HIGH・HIGH・OK・HIGH・OK）。1 回の所要は約 10〜20 分
- fix-loop 7 回（各回で診断・実装・テストの 3 レビュー。差し戻しは診断 1 回・テスト 1 回）
- 敵対的レビュー 2 周（10:53 の後・11:46 の後。範囲を例外ファイルに絞って新規 High 0）
- 指摘の種類: 4 回目までは前の回の直しで足した仕組みの細部の穴が中心。7 回目の High 2 件は以前からある部分（差分が 100KB で切れ、見る場所が毎回変わる）
- 待ちの無駄: PR が develop と衝突して CI が動かず、5 回目の基本レビューが来ない CI を待ち続けた。記録だけの push でも CI が走り直した
- 03:45〜10:44 は作業の中断（会話の外）で、所要時間に含めない

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/skills/`・`.claude/agents/`（`.claude/review-agents/` から移動）・`scripts/claude/`・`scripts/claude/tests/`・`.github/workflows/ci.yml`・`CLAUDE.md`・`docs/runbooks/`・`docs/*/templates/`・`docs/claude-code-structure.md`・`docs/proposals/I193_official_base_flow.md`

## テスト結果
- 2026-10-25 test-gate 1 回目: 自動（TC-01〜TC-14）は全部合格（run-all 39 本・CI 7 ジョブ pass）。手動は Claude の分の No.1〜No.4・No.7 が OK、No.6 は CI の確認だけ OK。No.8 が NG（設計書で fix-loop のレビュー役と I187 の判定スクリプトの根拠の行が無い）→ fix-loop
- 2026-10-25 test-gate 2 回目: 自動は全部合格（run-all 39 本・CI 7 ジョブ pass）。手動の Claude の分は No.1〜No.4・No.7・No.8 が OK、No.6 は CI の確認が OK。Human の分（No.5・No.6 の必須チェックの登録）をユーザーに依頼して止まる

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

STAGE_DONE: review-gate NEXT: test-gate

STAGE_DONE: test-gate NEXT: fix-loop

STAGE_DONE: fix-loop NEXT: review-gate

STAGE_DONE: fix-loop NEXT: review-gate

STAGE_DONE: review-gate NEXT: test-gate

STAGE_DONE: test-gate NEXT: human-test

STAGE_DONE: human-test NEXT: retro

STAGE_DONE: retro NEXT: close
