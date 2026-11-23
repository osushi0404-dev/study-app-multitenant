# I615 レビュー: 外で動く入口をレビュー済みの写しで動かし、人に `!` を頼まなくする

## 変更概要
- 外で動く入口（`OUTSIDE_SCRIPTS`）を、作業ツリーがレビュー済みかを問わず BASE の写しで動かす。入口か部品・レビュー役の定義を変えたときと写しを作れないときだけ、終了コード 75 で止めて `!` を案内する
- 写しの作り方を `.claude/hooks/reviewed-snapshot.sh` にまとめ、F1（写しを消す競合）を直す。F2（フックの子の python に `-I`）を直す
- 見張りが、作業ツリーを書き換える git の操作を中で動く形で流すのを止める（I586 の事故の予防）

## 変更点
- `.claude/hooks/reviewed-hook.sh`: 写しの作り方の正（`reviewed_snapshot`・`--snapshot`）・置き場所 `claude-reviewed-snapshots`・置いてある写しを消さない（F1）
- `.claude/hooks/unreviewed.py`: `run` が写しの入口を動かす・部品（`parts`）とブランチの変更が重なれば 75
- `scripts/claude/hooks/pretooluse_guard.py`: ほかの判定が通す形のうち、git の更新を中で動く形で流すものを止める
- `scripts/claude/hooks/sessionstart_context.py`: 子に `-I`（F2）
- `scripts/claude/fix-diagnosis-review.sh`: 部品を同じフォルダから読む
- テスト・手順書（danger-ops.md・harness-audit.md）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/hooks/`（起動役）・`scripts/claude/hooks/`（見張り・セッション開始のフック）・`scripts/claude/fix-diagnosis-review.sh`・`scripts/claude/tests/`・`docs/runbooks/danger-ops.md`・`docs/runbooks/harness-audit.md`

## テスト結果
- 自動: `test_i599_unreviewed_scripts.sh` pass=56・見張りのテスト一式・CI すべて OK（`docs/tests/open/I615_auto_test.md`「実行記録」）。コードレビュー OK（止める指摘なし・Low/Medium 6 件は台帳）・敵対的レビュー OK（V1〜V6 確認済み）
- 手動: No.1〜No.6 すべて OK（実施者はすべて Claude）

## 計画との差分
- あり: 写しの作り方を新しいファイルでなく `reviewed-hook.sh` の中に置いた（Write が拒まれたため）・見張りの判定をほかの判定の後に置いた（既存の確認を上書きしないため）・`test_pretooluse_checkout_guard.sh` の期待を 3 件直した（計画変更記録）

## ロールバック
- PR を revert する。`~/.cache/claude-reviewed-snapshots/` は消してよい

## 自律判断の記録
- [plan] 設計確認メモの「両方流す」を、ユーザーに確かめて「入口か部品を変えたときは、その入口だけ新しい版を `!` で流し正式な結果にする」に変えた — 敵対的レビューの周の上限を 1 回で使い切り、2 回目は差分だけを見て何もレビューしないため（2026-11-22・ユーザーの回答）
- [plan] 「人に `!`」の終了コードを 3 から 75 に変えた — 入口そのものの終了コード 3（CI 待ちの時間切れなど）とスキルの分岐で重ならないため
- [plan] 新しい版を頼む手順はスキルに書かず、起動役の案内の文と danger-ops.md に置いた — どの入口でも同じ動きで、写しを増やさないため
- [implement] 写しの作り方を新しいファイルでなく reviewed-hook.sh の中に置いた — Write が拒まれ、.claude/hooks/ はサンドボックスから書けないため（結果は同じ・計画変更記録）
- [implement] 見張りの新しい判定は、ほかの判定がすべて通すとしたコマンドにだけかける — 既存の確認（承認画面）の判定を止めに変えないため（計画変更記録）
- [implement] /simplify の指摘のうち、部品の対応表化・設定から外に出る語を作る案・一覧の一本化は見送った — 計画で決めた方式・決まり（計画変更記録）
- [test-gate] 作業記録との比べ（manual No.5）は HOME を一時フォルダに向けて流した — キャッシュの置き場所 ~/.cache がサンドボックスの中から書けないため（作業記録は同じものを読む）

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: test-gate
