# I444 レビュー: 見張りに残る役目の取りこぼしを塞ぎ、許可リストと手順書の写しを整理する

## 変更概要
（実装後に書く）見張り（`scripts/claude/hooks/pretooluse_guard.py`）の、環境変数をまとめて表示する形とコンテナ内の書き先（`-t`・`--target-directory`・`mv` の移動元）の取りこぼしを塞ぐ。許可リスト（`_container_safe`）を「危ない語が当たっても通す形」だけに縮め、手順書の写しを分類と代表だけにする。corpus diff がワークツリーで SKIP になる不具合を直す。

## 変更点
（実装後に書く。計画書 4. の変更点一覧に対応させる）

## 影響範囲
- ハーネスの見張り・そのテスト・corpus diff・手順書だけ。アプリのコードの変更なし

## テスト結果
（test-gate 段階で書く）

## 計画との差分
（計画変更記録を参照して書く）

## ロールバック
PR を revert する（データの変更なし）。見張りが起動できなくなったときは、ユーザーが端末で `! git restore scripts/claude/hooks/pretooluse_guard.py`。

## 自律判断の記録
- [plan] 1〜5 はすべて見張りの役目として扱う — #430 は OPEN で、docker のコンテナの中はサンドボックスの外（計画書「調査結果」0）
- [plan] 許可リストは消さずに縮める — 全部消すと `pytest -k delete` などが確認になり受け入れ条件を満たせない（スパイクで確かめた）
- [plan] 環境変数の表示の判定をホストにも当てる — ホストの `printenv` がすでに確認であることとそろえ、判定の重複を 1 か所にする。過去の作業コマンドで誤判定（`ps -eo etimes`）が出たので `ps` の e の形を絞った
- [plan] corpus diff の直しを同梱 — 見張りを直したら流すテストがワークツリーで黙って SKIP になり、このイシューの確かめにも要る
- [plan] 一覧の F5・F7 は残し、F9・F11・F13・I219 F1・I224 F8 は同梱 — 理由は計画書 9.
- [plan-review] 計画レビュー 2 の Warning（rsync の -t・M-03 の判定の形・擬似コードの省略）は直して再レビューしない — 方式・範囲・受け入れ条件を変えないため（計画変更記録 2）
- [design-security-review] Blocker・High なし。Medium 2 件（許可リストの条件の移し損ね・環境変数の判定の移し損ね）は実装の必須条件として計画書に書き、TC-01・TC-04 と既存のテストで確かめる — 設計を変える必要がないため

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
