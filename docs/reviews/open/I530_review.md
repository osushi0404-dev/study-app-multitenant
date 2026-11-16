# I530 レビュー: マージ前の最終確認の CI 待ちをレビュー段階の wait_ci に一本化する

## 変更概要
- マージ前の最終確認（`pr-base-sync.sh final`）の CI 待ちを、自前の判定（`ci_wait`）からレビュー段階の `code-review.sh` の `wait_ci` を呼ぶ形（`run_wait_ci`）に置き換えた。CI のチェックが未登録・一部だけのときに待たずに合格する穴をふさいだ

## 変更点
- `scripts/claude/pr-base-sync.sh`: `ci_wait` を消し `run_wait_ci`（別の bash で `wait_ci` を呼び、戻り値と `CI_WAIT:` 行を今のメッセージ・exit 1 に対応させる）を置いた。`PBS_CI_TIMEOUT`・`PBS_CI_INTERVAL` と I498 の既定の読み込みを消した。`CLEAN|HAS_HOOKS` でも CI を待つ
- `scripts/claude/code-review.sh`: `wait_ci` の前のコメントの並びと文言だけ（動きは変えない）
- `scripts/claude/tests/test_pr_base_sync.sh`: スタブを `wait_ci` の呼び方に合わせ、T22〜T26 と失敗の注入 FG1・FG2 を足した
- `scripts/claude/tests/test_i498_ci_wait_timeout.sh`: 新しい形に合わせた（環境変数・T5・T6・FG1〜FG3）
- `docs/reviews/backlog/I498.md`（F1・F2・F3・R1）・`I224.md`（F1）: 同梱して直した行を消した

## 影響範囲
- Backend/Frontend/DB: なし
- Config: ハーネスのスクリプト（`pr-base-sync.sh`・`code-review.sh` のコメント）とテスト 2 本・一覧 2 本

## テスト結果
- 自動: （実装後に書く）
- 手動: （close の手順 5.5 で書く）

## 計画との差分
- あり（テストの組み方と期待の細部だけ。計画書の計画変更記録の 2〜5 行目）: FG2 の T3 を見ない・失敗の注入を `CASE_SCRIPT` で 1 ケースずつ流す形・T4 の正規表現・shellcheck を pre-commit 経由で

## ロールバック
- この PR のコミットを revert する

## 自律判断の記録
- [plan] I498（PR #528・マージ依頼中）のブランチを取り込んで作った — このイシューの変更点が I498 の上にしかない。#528 のマージの後にこのイシューのマージを依頼する
- [plan] 最終確認の合格の道すべて（`CLEAN|HAS_HOOKS` を含む）で CI を待つことにした — イシューの目的「全部そろって合格するまで待ってから合格と言う」の範囲。CI が終わっていれば照会 1 回で済む
- [plan] 上限・間隔の上書きを `CI_WAIT_TIMEOUT`・`CI_POLL_INTERVAL` 1 つにし、`PBS_CI_TIMEOUT`・`PBS_CI_INTERVAL` を消した — 使うのはテストだけで、2 つの名前は review-gate と値がずれる元
- [plan] 一覧の I498 F1・F2・F3・R1 と I224 F1 を同梱、I498 F4 は残した — 理由は計画書 §9
- [plan-review] 計画レビュー OK（Info 3 件）。Info の 1 件目（失敗のメッセージに gh pr checks の文字があると TC-03 が落ちる）は文言を直した。残り 2 件は対応不要 — 相対パスの前提は wait_ci が元から持つ・TC-05 の形のずれは TC-05 自身が先に落ちる
- [implement] I498 のテストの FG2 で T3 を見ないことにした — final が `wait_ci` そのものを呼ぶようになり、既定を変えても 2 つの上限が食い違わなくなった（AC2 の結果）。T3 自体は、pr-base-sync.sh に別の既定を書き戻したとき（FG1）を捕まえるので残す
- [implement] /simplify の 4 観点の指摘のうち、失敗の注入の組み方（全体の流し直し → 1 ケースずつ）・FG2 の T3 の確かめ・古いコメントと名前を直した。見送り: 共有ファイルへの切り出し（I498 で、code-review.sh を写して動かす既存のテスト 5 本以上が壊れるため採らないと決めた）・`wait_ci` に上限の行を出させる（`wait_ci` の変更はイシューの範囲外。式は code-review.sh 本体の時間切れのメッセージと同じ書き方）・合格の 2 つの分岐をまとめる（✅ の文言が変わり、手動テストの期待とずれる）・BEHIND の後に待ちを 2 回通る（安全側に倒した意図した形・一覧 I498 F4 と同じ話）・テストが `wait_ci` の内側の呼び方に合わせたスタブを持つ（本物の `wait_ci` を通して穴が塞がることを確かめるのが目的）
- [review-gate] 1 回目（4e9a85c7 の記録）は FINAL_VERDICT: BLOCKER — 台帳は OK（Low 4 件）だが、決定論ゲートの 3 行（`pre-commit run shellcheck …`・`bash -c "…"` 2 行）が実走できる形でなく fail-closed。fix-loop でゲートの書き方を直す
- [fix-loop] 案 A（ゲートの行を `classify_gate` が実走する形に分け、shellcheck は `bash -n` に置き換える）で直した — 診断レビュー PASS（`docs/reviews/I530_fix_diagnosis_review_20261116_1239.md`）。安全境界（`classify_gate`）を広げず、新しいテストのファイルも作らない最小の形。shellcheck は pre-commit と CI が流す
- [review-gate] 2 回目（差分のレビュー・`docs/reviews/I530_code_review_20261116_1242.md`）は FINAL_VERDICT: OK・ゲート 15 行すべて exit=0・CI_WAIT: OK・高リスク NO（敵対的レビュー不要）。台帳の残り Low 4 件（F1〜F4）は retro が振り分ける

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: fix-loop

STAGE_DONE: fix-loop NEXT: review-gate

STAGE_DONE: review-gate NEXT: test-gate
