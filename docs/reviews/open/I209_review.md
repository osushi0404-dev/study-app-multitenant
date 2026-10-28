# I209 レビュー: ハーネスの古いイシューを棚卸しし、今の流れで不要なものを閉じる

- 計画書: docs/plans/open/plan_I209.md
- 判定の一覧: docs/reviews/open/I209_triage.md
- Draft PR: #355

## 変更概要
開いている `track:harness` のイシュー 52 件（#349 を除く）を判定し、閉じる 37 件・統合 4 件を理由のコメント付きで閉じ、残す 11 件の本文の先頭に「今の流れでの読み替え」を足す。閉じるイシューの小さな指摘は残すイシューか `docs/reviews/backlog/I209.md` に移す。

## 変更点
- GitHub のイシュー（閉じる 41 件・本文の先頭の追記 11 件）
- `docs/reviews/open/I209_triage.md`・`docs/reviews/open/I209_original_bodies/`・`docs/reviews/backlog/I209.md`
- コードの変更なし

## 影響範囲
- GitHub のイシュー（`track:harness`）と記録のファイルだけ。Backend・Frontend・DB・ハーネスのスクリプト・設定は変えない

## テスト結果
- 2026-10-28 test-gate（HEAD 1dc998e4・gate-check OK）
- 自動: CI（Harness Tests を含む）が pass（review-gate で CI_WAIT OK）。TC-01（52 件の番号）・TC-03（F1〜F9）は exit 0、失敗注入は exit 1。TC-02 は CI の D3
- 手動（実施者はすべて Claude）: No.1〜No.5 すべて OK（閉じた 41 件の状態・理由のコメント／残す 11 件の本文の完全一致／統合先への同梱／ユーザー確認が閉じる操作より前／開いているのは #349 と残す 11 件だけ）
- check-frontend-evidence.sh・check-manual-test-executor.sh とも exit 0

## 計画との差分
（implement 以降で記入）

## ロールバック
- 閉じたイシューは `gh issue reopen <番号>`、本文は `gh issue edit <番号> --body-file docs/reviews/open/I209_original_bodies/<番号>.md`、記録のファイルは PR の revert（計画書 7）

## 自律判断の記録
- [plan] 判定の一覧の置き場所を `docs/reviews/open/I209_triage.md` にした — 計画書が短く保て、close で closed へ一緒に移る
- [plan] 52 件の判定案は 4 つのサブエージェントで 13 件ずつ作り、割れた 7 件（#154・#172・#189・#233・#278・#279・#291）は Claude が根拠を確かめて決めた — 本文が約 23 万字あり 1 つの文脈では読み切れない
- [plan] ユーザーの確認は implement の最初で取る — 計画レビューで判定が変わっても見せ直しにならない
- [plan] 追記の前の本文を `docs/reviews/open/I209_original_bodies/` に残す — test-gate が別のセッションでも元の本文と比べられ、ロールバックの元にもなる
- [plan] `python3 -c` の承認画面について — ユーザーに問われた。許可にない書き方だったので、以後は `gh` の `--jq` と読み取りの道具を使う（設定は変えない）
- [plan-review] Warning 3 件は直した（一覧の統合の書き方を計画書にそろえた・本文の取り出しを --template で完全一致にした・TC-03 の失敗注入は実装で流す）— 方式・範囲・受け入れ条件は変えないので再レビューしない
- [implement] ユーザー確認: 閉じる・統合する一覧 41 件に OK（2026-10-28・外した番号: なし。ユーザーの条件「ループエンジニアリング・ハーネスエンジニアリングのベストプラクティスと、開発をサクサク進める観点で問題なければ OK」— Claude が見直し、閉じる 12 件〔④〕は文章の決まりを増やさない方針に合い、仕組みで直す不具合〔#172・#237・#250・#321 など〕は残す・統合で消していないので問題なしと判断。#291 の SKIP の素通りは直した後に必ず review-gate を通るので一覧 F6 で足りる）
- [implement] 本文の記録（`.md`・`.header.md`）を先に commit して整形を済ませてから組み立てた — 記録のファイルと GitHub の本文を 1 字も違わずそろえるため（11 件とも `cmp` 一致）
- [implement] #172 を閉じるコメントが見張りに誤ブロックされた（#172 の不具合の再現）ので、オプション名を言い換えて閉じ直し、実例を #335 にコメントした — 計画にないコメントだが、統合先で直すときの回帰テストの入力として残す価値がある
- [implement] 反映の結果は全件を流した後に GitHub から取り直してまとめて書いた — 状態は GitHub が正
- [implement] /simplify は呼ばなかった — コードの変更が無く（記録のファイルだけ）、未 push・未コミットの変更も無いので対象が空。反映の検証（3.5）では計画書の実装対象の記録ファイルがすべてブランチにあることを確かめた
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
- [review-gate] code-review.sh: CI_WAIT OK・FINAL_VERDICT OK・ADVERSARIAL_STAGE NOT_REQUIRED（docs/reviews/I209_code_review_20261028_1955.md）。台帳は Low 8 件（F1〜F8・記録の書き方）で止める指摘なし — 決まりどおり retro が扱う
STAGE_DONE: review-gate NEXT: test-gate
- [test-gate] 手動 No.1 は理由の文の完全一致ではなく「判定の語・理由の行・統合先の番号」の有無で照らした — #172 は見張りに止められて言い換えたため（台帳 F4）。No.2 の一時ファイルはスクラッチに作った（台帳 F8）
STAGE_DONE: test-gate NEXT: retro
