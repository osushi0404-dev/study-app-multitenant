# I547 レビュー: レビュー役 5 つの指示を BP のあるべき姿に見直す（最新化・漏れ・最適化）

## 変更概要
- 5 つのレビュー役の指示を、公式の書き方（サブエージェント・プロンプト・2026-11-27 に照合）に照らして直し、すり抜けた実例のある観点を 6 つ足し、写しと強い言い回しを刈った。節ごとの判定は `docs/reviews/open/I547_agents_audit.md`

## 変更点
- `.claude/agents/` の 5 つ: 入力の扱いを 1 節に・道具は 1 行・観点の見出しを P1〜P9 に・規約の節と §16 の扱い・足した観点（流れの途中の状態・時間がたつと現れるデータ・受け入れのリスクの根拠・UX の決まりの照合・画面と API の受け渡し）・高リスク判定の条件とスキル点検は review-rules の参照に・古い言い方と食い違いの直し
- `docs/runbooks/review-rules.md`: 新しい節「高リスク判定の条件」・記録の連番の説明
- `docs/runbooks/plan-writing-rules.md`・`docs/runbooks/harness-audit.md`・`rules/ultimate_django_coding_standards.md`・`docs/plans/templates/plan_template.md`: 1 文ずつ
- `scripts/claude/tests/` の 3 本: 写しの一致を見る項目を、1 か所・写しが無いことを見る形に（D6・D9・TC-02・TC-02b・TC-14⑧b）
- 一覧から直した 3 行を消した（I430 F7・I486 F6・I546 F3）。#594・#640 にコメント

## 影響範囲
- Backend/Frontend/DB/Config: なし（ハーネスのレビュー役の指示・手順書と規約の 1 文ずつ）

## テスト結果
- 自動: 決定論ゲート 29 行（定義の文字を読む既存のテスト 11 本・TC-02〜TC-06）が review-gate のスクリプトの実走と手元で exit 0。CI は 2 回とも `CI_WAIT: OK`。test-gate に委ねられた重いテストは無い。`gate-check.sh` OK
- 手動: 7 行すべて Claude で OK（`docs/tests/open/I547_manual_test.md`）。人の手動テストは無い

## 計画との差分
- なし

## ロールバック
- PR を revert する（文書だけ）

## 自律判断の記録
<!-- 各段階が、止めずに自分で決めたことを `- [段階] 決めたこと — 理由` で足す。段階の結線の行（STAGE_DONE:）はこのファイルの末尾に足す -->
- [plan] 点検を計画の前に済ませ、点検の表 `docs/reviews/open/I547_agents_audit.md` を変更点の正にした — 計画に書いていない書き換えをしないため（I546 と同じ）
- [plan] 判定の基準は定義の中に 1 行で残し、高リスク判定の条件の一覧は `review-rules.md` に 1 つにした — 審査の写しに入るのは定義と review-rules だけ（I593）で、ほかの手順書への参照だけにするとブランチが自分の審査の基準を変えられるため
- [plan] 前置きに `effort` などを足さない — 審査の入口が 4 項目しか受け付けず、足すとマージの後の審査が止まる（`scripts/claude/reviewer-agents-lib.sh:47`）。#640 に渡す
- [plan] 同梱 E（受け入れのリスクの根拠）は Blocker にした — 計画レビューを通ると実装まで止まる場所が無いため
- [plan-review] 計画レビュー OK（Warning 5・Info 1）。全部を計画書・テスト文書の追記で直し、やり直しはしない — 方式・範囲・受け入れ条件を変えないため（計画変更記録）
- [implement] 写しの一致を見るテストの項目（i181 D6・D9・i593 TC-02・i185 TC-14⑧b）を、1 か所・参照を見る形に変えた — 写しを 1 つにすると落ちる項目で、写しを残すと AC4 に反するため（計画変更記録・計画レビューのやり直し OK）
- [implement] bug のイシューから「画面と API の受け渡し」（#473・#488）の観点をコードレビュー役に足した — 2 回起き、どちらもマージ後に画面で見つかったため（計画変更記録）
- [implement] /simplify の 4 観点の指摘を直した（review-rules の中の写しも (b) の 1 か所に・テストは集合で写しの無さを見る・レビュー役は節だけを Grep で読む）。節をスクリプトが入力に入れる案は #640 の範囲なので見送った — 写しと無駄を減らし、範囲は変えないため
- [review-gate] 基本レビュー（`docs/reviews/I547_code_review_20261127_0946.md`）は HIGH（止める指摘 F1・flow）。fix-loop へ回す。AC7 の実測: 起動役が 75 を出さず「変更前の版で審査します」と出て、記録に「審査の版: 写し b4af25e8…」が出た — I593 の仕組みがマージ後に動くことを確かめた
- [fix-loop] F1 は案 B（2 つのレビュー役は review-rules を Read し、計画レビュー役は節と (b) の 2 つの一覧で判定）で直した — 判定に要る情報を確実に読ませる形のうち一番短く、F3 も同時に消えるため。診断レビュー OK（`docs/reviews/I547_fix_diagnosis_review_20261127_0956.md`）
- [review-gate] 差分のレビュー（`docs/reviews/I547_code_review_20261127_1001.md`）は OK（F1・F3 は resolved、新しい Low の F7・F8 は台帳に残す）。敵対的レビューは不要（高リスク NO）
- [test-gate] 手動 No.1 で点検の表の行の名前に無い見出し（敵対的レビュー役の「実機 repro」）を見つけ、表の AR3 に足した — 記録の場所の直しで、判定は「そのまま」のため

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
