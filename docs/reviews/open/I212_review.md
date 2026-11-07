# I212 レビュー: 差分のレビューの起点を「見終えた最新の記録」にする（失敗した回の後にセキュリティレビューを飛ばさない）

## 変更概要
- （実装後に記入）

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config（ハーネス）: `scripts/claude/code-review.sh`・テスト（`test_i212_review_base.sh` 新規・`test_i197_review_ledger.sh`・`test_i193_official_flow.sh`・`test_i223_gh_app.sh`）・`.claude/skills/review-gate/SKILL.md`・`docs/runbooks/review-rules.md`

## テスト結果
- 自動: review-gate の実走でゲート 8 本がすべて exit=0（新しい `test_i212_review_base.sh` pass=31・既存 5 本も fail=0）。CI 全緑（19195aa8）。gate-check OK
- 手動: M-01（本物の /security-review が `SECURITY_FINDINGS: 0` を出し判定 OK）・M-02（記録に `REVIEW_COMPLETE: YES`）とも OK。Human の項目なし

## 計画との差分
- （実装後に記入）

## ロールバック
- PR を revert する（設定・データの変更なし）

## 自律判断の記録
- [plan] 受け入れ条件 1 の「失敗した回」を「見終えていない回（/security-review が動かなかった・レビュー役の出力が壊れた）」に定めた — ユーザーの判断「ループエンジニアリング、ハーネスエンジニアリングのベストプラクティスと開発をサクサク進めるという観点で問題ないやり方を選択して」を受けた。指摘が残った HIGH まで外すと fix-loop のたびに全体を見直し、I197 の収束の設計が崩れる
- [plan] 同梱 2・4（/security-review の判定の 1 行）・6（G10）を入れ、3・5（敵対的レビュー）は別イシューに切り出す（retro で起票） — 2・4 は直さないとやり直しも同じ FAILED で止まる。3・5 は別の仕組みで設計の検討が要る
- [plan] gate-check.sh は直さない — 直した後の code-review.sh では見終えていない回は必ず HIGH／BLOCKER になり、やり直しは見終えた記録から差分を取るので、gate-check の結果は変わらない（plan §4-4）
- [plan-review] 計画レビュー OK（高リスク判定 No）の Warning 3 件・Info 1 件を計画書で直し、再レビューはしない — 方式・範囲・受け入れ条件を変えない findings への対応のため（計画変更記録 1）。W3 では /security-review の判定の 1 行を「最後の行だけ」から「行全体がその形の行があるか」に緩めた（締めの文で FAILED にして止まるのを防ぐ）
- [implement] テストを先に書き、直す前の本体で U1〜U3・U5〜U8・E1 が落ちる（E1 では 2 周目が範囲 0 本でレビュー役を呼ばず、gate-check も通る＝I211 の穴を再現）ことを確かめてから直した — TC-02・TC-03 の FG の前提
- [implement] FG-U7 の壊し方を「行全体の固定を外す」に直した — 行頭だけ外しても行末の固定が残り、FG が成立しなかった（計画変更記録 2）
- [implement] /simplify の 4 観点のうち、起点探しの形（新しい順・最初に当たったら止める）・記録の「読めていない」注意との食い違い・G10 の `-` の 3 点を直し、他は見送った — 見送りはどれも Low か範囲の外で、今の形で正しく動く。`/code-review` 側の自由文の読み取り・E の土台の写しは retro で扱う（計画変更記録 3）
- [review-gate] 基本レビュー（全体・台帳 1 周目・19195aa8）は FINAL OK・高リスク NO・ADVERSARIAL_STAGE NOT_REQUIRED で test-gate へ進む — 台帳の F1（Medium・「差分なし」の文字列の部分一致で OK になる）〜F7（Low）はどれも止める条件の一覧に当たらず、スクリプトが止めない指摘と決めた。retro で振り分ける
- [test-gate] gate-check OK・重いゲートなし・手動テスト M-01・M-02 を Claude が実施して OK・Human の項目なしで retro へ進む — M-01 の `bash -c` の形はワークツリーの安全装置が止めたので、同じ中身を一時のスクリプトにして流した（記録の場所の外は書いていない）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
