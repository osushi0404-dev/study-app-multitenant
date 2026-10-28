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
（test-gate で記入）

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
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
