# I512 レビュー: 計画で受け入れた残余リスクを、後続イシュー・最優先から外して一覧へ回す

## 変更概要
- 計画書の「## 8. Risk & 回避策」の表に「処遇」の列を足し、`受け入れ` の R 番号を code-reviewer が FINDING 行の目印 `ACCEPTED=R<番号>` で示す。retro の振り分け（`code-review.sh --route`）が計画書と照合し、Medium 以下・再現なし・アプリ本体でない行を一覧へ回す。止める判定は変えない
- I430 の F1〜F3 を受け入れのまま `docs/reviews/backlog/I430.md` へ

## 変更点
- `scripts/claude/code-review.sh`: FINDING・LEDGER 行の任意の目印 `ACCEPTED=R<番号>`（無い行は前と 1 文字も変えない）・`accepted_risks()`（計画書の 8 の表を読む）・`accepted_why_not()`・`route` モードで目印が効く行だけ `SECURITY=yes`・`guard の Medium 以上` の理由を外す・一覧の行に `SECURITY=` と「計画で受け入れ（R<番号>）」・`--route` の入口で種類と番号の形を先に確かめ、`find_plan_file()` で計画書を選ぶ
- `.claude/agents/code-reviewer.md`: 目印を付ける決まりと FINDING 行の欄
- `docs/plans/templates/plan_template.md`: 8 の表に「処遇」の列
- `.claude/skills/retro/SKILL.md` 4-0・`docs/runbooks/review-rules.md`: 目印の扱い・一覧の行の形
- `scripts/claude/tests/test_i512_accepted_risk.sh`（新規・34 項目）・`test_i202_ledger_cleanup.sh`（一覧の行の形と FG の元の文字列の追従）
- 一覧: `I430.md` に F1〜F3 を足した・同梱して直した `I480.md` F1・`I208.md` F3 を消した

## 影響範囲
- Backend/Frontend/DB/Config: ハーネスだけ（`scripts/claude/code-review.sh`・`.claude/agents/code-reviewer.md`・`docs/plans/templates/plan_template.md`・`.claude/skills/retro/SKILL.md`・`docs/runbooks/review-rules.md`・テスト・一覧）

## テスト結果
- 自動: CI 全ジョブ合格（最後は 0a59b190）。決定論ゲート `test_i512_accepted_risk.sh`（43/43）・`test_i202_ledger_cleanup.sh`（163/163）・`test_i205_stop_criteria.sh`（91/91）を `code-review.sh` が実走して OK。test-gate に委譲された重いテストは無い
- 手動: No.1〜No.3 すべて Claude が実施して OK（Human の項目なし）

## 計画との差分
- あり（計画変更記録の 2026-11-14 implement の行）: /simplify の結果で関数の形と計画書の探し方を変えた・I208 F3 の後半も直した・FG の元の文字列の追従。方式・範囲・受け入れ条件は変えない

## ロールバック
- PR を revert する（plan §7。目印のある記録が develop にあれば先に目印を消す）

## 振り返り

### I512 振り返り（かんたんなまとめ）

#### 良かった点
- 受け入れ条件 8 つはすべて満たし、I430 の 3 件（F1〜F3）も一覧に移せた（理由: 計画で受け入れたリスクが毎回「最優先の後続」になる連鎖を止めるのが目的だったため）
- 計画書と照らし合わせて合わなければ今までどおりに倒す作りにし、照合の失敗 8 通りと「止める判定は変わらない」ことを、壊すと落ちるテストで固定した（理由: レビュー役の自己申告だけで一覧に落ちる穴を作らないため）
- 整理役 4 体の指摘で、既にあった計画書の探し方（作り直しの計画書も読む）を使う形に直せた

#### 今回の問題への直接の対処
- レビューで「計画書に同じ R 番号が『回避』と『受け入れ』の 2 行あると、受け入れが効いてしまう」穴が見つかった。照合は合わなければ安全側に倒す作りなのに、重複の扱いを決めていなかったため。→ この PR の中で直す（このイシューの目的そのものの穴なので、後続イシューに回さない）。同じ番号に受け入れでない行が 1 つでもあれば効かせない形にし、壊すと落ちるテストを足す
- CI で 1 回落ちた。テストの書き方を整える自動チェック（shellcheck）の指摘に合わせて書き換えたところ、リポジトリの別の決まり（パイプの後ろで grep を早く終わらせる形を否定と組み合わせない）に反した。その決まりを守るテストが CI で捕まえ、件数で比べる形に直した（手戻りは 1 周だけ）

#### 同じ問題を次回から防ぐ改善
- I430 で入れたサンドボックスの影響の測定（約束していたもの）: この作業では、承認画面での止まりは 0 回。ただし次の 2 つの引っかかりが出た。① イシューの本文を下書きのファイルへ書き出す手順が、サンドボックスの中で動いて GitHub の鍵を読めずに失敗した。② 手元でまとめてテストを流す道具が、一時ファイルの置き場を書けずに起動しなかった。→ どちらも既存のイシュー（#428・#445）にまとめて書いた。どちらも回避の手順があり、今すぐ止まるものではないため
- 見送り: CI で落ちたパイプの書き方は、既にある決定論のテストがその場で捕まえたので、新しい手順は足さない

### I512 振り返り

#### 良かった点
- AC1〜AC8 を満たした。照合の失敗 8 通り・止める判定の不変・前の形の行の互換を、失敗の注入つきの決定論テスト（35 項目）で固定した
- /simplify の 4 体で、既存の `find_plan_file()` の再利用・判定の入口の一本化・共有の `route_reasons()` に旗を足さない形に直した

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | 成果・セキュリティ | `accepted_risks()` が同じ R 番号の重複と HTML コメントの中の行を考えていなかった（計画の照合の失敗の列挙に「同じ番号の食い違い」が無かった） | このイシューの目的（fail-closed の照合）の穴なので、この PR で直す: 同じ R 番号に受け入れでない行が 1 つでもあれば効かせない・HTML コメントの中の行は読まない。失敗の注入つきの TC を TC-05 に足す（retro → fix-loop → review-gate） |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | 予期しない問題（I430 の効果の測定） | 出力をファイルへ送る形のコマンドは、外に出す設定に当たらずサンドボックスの中で動き、鍵を読めない | 本文を書き出す道具にファイルへ書く引数を足し、手順を出力を送らない 1 コマンドにする（#428 に同梱） | `.claude/skills/grill-me/SKILL.md`・`scripts/claude/issue-source.sh` |
| P2 | 予期しない問題（I430 の効果の測定） | 全テストをまとめて流す道具の一時の置き場が、サンドボックスの書き込み先の外 | 一時の置き場を `$TMPDIR` の下に向ける（#445 に同梱） | `scripts/claude/tests/run-all.sh` |

見送り: CI の `test_pipefail_negated_grep.sh` が捕まえた書き方の誤り — 既存の決定論チェックがその場で捕まえ、手戻りは 1 周だけ（2.7 の 2 問目）

### 振り返り（2 回目・fix-loop 4 回の後）

#### かんたんなまとめ
- 計画書の読み方の穴（同じ番号の食い違い → コメントの変わった書き方 → コードの囲み）が、レビューのたびに 1 つずつ見つかり、直すのに 3 周かかった。最初は 1 行ずつの特例で塞いでいたため、書き方の組み合わせが漏れ続けた。2 周目に「同じ種類が続いたら粗く安全側に倒す」に切り替え、3 周目に「本文でないところ（囲み・コメント）を全文から先に取り除いてから読む」一般的な形にして収まった。最後のレビューの残りは軽いもの（Low・再現なし）だけで、後続イシュー（最優先）は 0 件
- 同じ問題を次回から防ぐ改善: 見送り。既存の決まり（同じ種類が続いたら粗い形に倒す）がその場で効き、手戻りはこの PR の中で閉じた。手順や観点を足すほどの再発の見込みは無い（文書を機械で読む照合を作ること自体がまれ）。学びは再発防止記録（auto_test）に残した

#### 詳細
- 台帳の残り（最終・`docs/reviews/I512_code_review_20261114_0234.md`）: 後続イシュー 0 件・一覧 9 件（F2〜F6・F13〜F16 → `docs/reviews/backlog/I512.md`）
- 5 Whys（fix-loop が 4 回になった）: Why1 計画書の読み方の穴が周ごとに 1 つずつ見つかった → Why2 行ごとの特例（コメントの開き・閉じ、節の中の囲み）で塞いでいた → Why3 照合の最初の設計で「本文でないところを先に取り除く」形を選ばなかった（照合の失敗の列挙を表の中身だけで考えていた）。根本原因: 文書を機械で読む照合の設計で、文書の構造（囲み・コメント）を前処理で取り除く段を最初に置いていなかった。一般化: まれ（文書を照合するスクリプトを作るときだけ）。2.7: 実害は周回 3 回分・既存の決まり（memory「fix-loop を過剰にしない」）がその場で効いた → 見送り
- 是正処置: C1 は直した（同じ番号の食い違い・コメント・囲み。TC-05 は 17 通り・FG-05a〜h）

## 自律判断の記録
- [retro] 2 回目: 台帳の残り（最終）は後続イシュー 0 件・一覧 9 件（F2〜F6・F13〜F16 → `docs/reviews/backlog/I512.md`）。fix-loop が 4 回になったことの改善案は見送り（既存の決まりがその場で効いた・まれ）
- [retro] 台帳の残り: F1 → この PR で直す（fix-loop へ。目的の穴なので後続イシューにしない・ユーザーの以前の指示「目的の穴はその PR で直す」）／F2〜F6 → `docs/reviews/backlog/I512.md`
- [retro] I430 の効果の測定（#512 で約束）: 承認画面での止まり 0 回。サンドボックスによる引っかかり 2 件（本文の書き出し・run-all.sh）を #428・#445 にコメントで同梱。ほかに、worktree の分離の判定で複雑なシェルの書き方が拒まれた 1 件（スクリプトをファイルにして回避・実害なし・見送り）
- [retro] 改善案: P1 → #428 に同梱・P2 → #445 に同梱・CI の書き方の誤り → 見送り（既存の決定論チェックが捕まえた）
- [plan] grill-me の 4 問はユーザーの委任（「ベストなやり方で」）を受けてすべて推奨案で確定 — 取り消しやすく手間が増えず安全側に倒れる案
- [plan] アプリ本体の行には目印を効かせない — アプリ本体の Medium・SECURITY=yes が最優先から外れるのを防ぐ（効く範囲を狭める安全側）
- [plan-review] Warning 2 件は計画書・manual_test を直し、再レビューはしない — 方式・範囲・受け入れ条件を変えない
- [implement] /simplify の 4 体の指摘のうち、計画書の探し方（find_plan_file）・判定の入口の一本化・route_reasons() に旗を足さない形・テストの起動回数の削減を採用。台帳の行を名前で引く形（namedtuple）・BL_FORM の重複・入口と Python の種類の確かめの重複は見送り — 範囲の外か、既存の書き方の慣例
- [implement] 関係するテストだけを 1 本ずつ流し、全体は CI に任せた — run-all.sh はサンドボックスで uv の一時ファイルを書けない
- [review-gate] 1 回目は CI_WAIT: FAIL（Harness Tests の test_pipefail_negated_grep.sh G1: test_i512_accepted_risk.sh:171 の `! grep … | grep -qvE` が pipefail の下の否定とパイプの形）で fix-loop へ — コードレビューは CI が通ってから
- [fix-loop] 案 A（件数で判定・FG-07b を足す）で直した — 診断レビュー PASS。1 行の書き換えで shellcheck と I210 の決まりの両方を満たす
- [review-gate] 2 回目は CI_WAIT: OK・FINAL_VERDICT: OK・ADVERSARIAL_STAGE: NOT_REQUIRED（`docs/reviews/I512_code_review_20261114_0153.md`）。台帳の F1（Medium・SECURITY=yes・R 番号の重複で受け入れ側が効く）〜F6（Low）は止めない指摘なので直さず retro へ — fix-loop が直すのは止める指摘だけ（I197）
- [test-gate] gate-check OK・手動テスト 3 件を Claude が実施して OK・Human の項目なしで retro へ
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: fix-loop
- [fix-loop] 2 回目（retro から）: 台帳 F1 を案 A（受け入れでない同じ番号を引く・コメントの中を読まない）で直した — 診断レビュー PASS。安全側にしか倒れない単純な規則
STAGE_DONE: fix-loop NEXT: review-gate
- [review-gate] 3 回目は CI_WAIT: OK・FINAL_VERDICT: OK（`docs/reviews/I512_code_review_20261114_0210.md`）。F1 は resolved。新しい F7（Medium・コメントの変わった形）・F8（Low・コードの囲み）・F9（Medium・コメントの後の表の肯定テストが無い）・F10（Low）は F1 と同じ種類（計画書の読み方の穴）なので、精密化をやめて粗い fail-closed に 1 回で倒すため fix-loop へ（ユーザーの以前の指示「同種が続いたら粗い fail-closed に」「目的の穴はその PR で」）。これで収まらなければ一覧・後続へ回して打ち切る
STAGE_DONE: review-gate NEXT: fix-loop
- [fix-loop] 3 回目: 台帳 F7〜F10 を案 A（粗い fail-closed）で直した — 診断レビュー PASS。行ごとの特例の積み上げをやめた
STAGE_DONE: fix-loop NEXT: review-gate
- [review-gate] 4 回目は CI_WAIT: OK・FINAL_VERDICT: OK（`docs/reviews/I512_code_review_20261114_0222.md`）。F7〜F10 は resolved。F11（Medium・前の節の囲みの中の 8 の例を読む）は見送ると後続の最優先になり、このイシューの目的に反するため、囲みを全文から先に取り除く一般形で 1 回だけ直す（F12 も同じ直しで消える）。これを最後とし、以降の同種は止める指摘でない限り一覧・後続へ
STAGE_DONE: review-gate NEXT: fix-loop
- [fix-loop] 4 回目: 台帳 F11・F12 を案 A（囲みを全文から先に取り除く一般形）で直した — 診断レビュー PASS
STAGE_DONE: fix-loop NEXT: review-gate
- [review-gate] 5 回目は CI_WAIT: OK・FINAL_VERDICT: OK（`docs/reviews/I512_code_review_20261114_0234.md`）。F11・F12 は resolved。新しい F13〜F16 はすべて Low・再現なしなので直さず retro で一覧へ（打ち切りの決めのとおり）
STAGE_DONE: review-gate NEXT: test-gate
- [test-gate] 2 回目: gate-check OK・手動テスト No.2・No.3 を流し直して OK・Human の項目なしで retro へ
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
- [close] 記録を closed へ移した（fix の診断メモも一緒に）・PR #514 の説明を更新・develop への追従は不要（BLOCKED）・gate-check OK
STAGE_DONE: close NEXT: merge
