# I444 レビュー: 見張りに残る役目の取りこぼしを塞ぎ、許可リストと手順書の写しを整理する

## 変更概要
見張り（`scripts/claude/hooks/pretooluse_guard.py`）の、環境変数をまとめて表示する形とコンテナ内の書き先（`-t`・`--target-directory`・`mv` の移動元）の取りこぼしを塞ぐ。許可リスト（`_container_safe`）を「危ない語が当たっても通す形」だけに縮め、手順書の写しを分類と代表だけにする。corpus diff がワークツリーで SKIP になる不具合を直す。

## 変更点
- 5-1 `pretooluse_guard.py` `_cmd_external`: 環境変数をまとめて表示する形（`printenv`・先頭に残った `env`・引数なしの `set`・`ps` の BSD 形式の e・引数なし／`-p`／`-x` の `export`・`declare`・`typeset`）をホストとコンテナで 1 か所に。`_container_risky` の同じ判定を消した
- 5-2 `_ctr_write_targets`: `-t`・`--target-directory`（rsync を除く）と `mv` の移動元
- 5-4 `_container_safe`: 危ない語が当たっても通す形だけに縮め（テスト・lint・依存の情報・読み取りの manage.py・見えて安全な Python・読み取りの SQL・ローカル宛ての curl・パイプの受け手）、`_SAFE_READ_CMDS`・`_SAFE_REDIS` を消した。古いコメント 3 か所をそろえた
- 5-6 `scripts/claude/tests/guard_corpus_diff.py`: 作業記録を primary とすべてのワークツリーから探す（`_project_dirs`）・キャッシュの名前を primary にそろえた
- テスト `scripts/claude/tests/test_i444_guard_gaps.sh`（新規・56 件・FG-01〜FG-05）
- 5-5 `docs/runbooks/danger-ops.md`（3.・4.・rebase の文）・`docs/runbooks/worktree.md` §9（打ち切り・書き込みの代表）
- 一覧: `docs/reviews/backlog/I200.md` の F9・F11・F13、`I219.md` の F1、`I224.md` の F8 を消した
- 見張りの行数: +42／−82（差し引き −40）

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
- [implement] /simplify の指摘のうち、パイプの受け手の書き出しの除外を `sort`・`uniq` だけに戻し、`ps` の e を後ろの引数でも見るようにした — どちらも今の動きより狭く・広くなっていた移し損ね（計画変更記録 3）
- [implement] 書き先の抽出 3 つの共通化と、「通す形なら書き込みの判定ごと飛ばす」構造（`pytest --junitxml=/app/r.xml` が通る）は直さず retro へ — 別ワークツリーの停止を広げる・範囲を越えるため

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
