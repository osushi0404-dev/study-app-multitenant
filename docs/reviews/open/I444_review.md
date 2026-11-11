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
- 自動: `test_i444_guard_gaps.sh` 56 件・見張りの既存テスト（container_guard・i200・matrix・oracle・i182_corpus_base）すべて pass・PR #451 の CI pass（review-gate）。TC-06 の過去コマンドでの比較（15738 件）は新しく確認 3 件・新しく停止 0 件で OK
- 手動（すべて Claude）: M-01〜M-04 OK（コンテナ内の普通の操作は承認なし・危ない形は承認画面・見張りの行数 −40・手順書と実物が一致）

## 計画との差分
- 計画変更記録 1〜5（計画レビューの指摘・/simplify の指摘・corpus diff を決定論ゲートから外す・そのスクリプトの説明）。方式・範囲・受け入れ条件の変更なし

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
- [fix-loop] 止める指摘 F1（corpus diff がゲートで時間切れ）は案 A（ゲートから外し、TC-06 で手で流して記録）で直した — 所要が作業記録の件数に比例し 120 秒のゲートに収まらない。速くする案・上限を延ばす案は新しいコードや共有の仕組みの変更が要る（診断 `docs/reviews/I444_fix_diagnosis_20261111_1915.md`・診断レビュー OK）
- [fix-loop] 2 回目: 記録の場所だけの直しでは差分のレビューがレビュー役を呼ばず F1 が閉じないので、誤解の元だった `test_guard_corpus_diff.sh` の冒頭のコメントを直した（案 A・診断 `docs/reviews/I444_fix_diagnosis_20261111_2000.md`）。「記録の場所だけの直しでは止める指摘が閉じない」仕組みの穴は retro へ
- [review-gate] コードレビュー 3 周目 OK・敵対的レビュー 1 周目 OK（V1〜V5 確認済み・新規の Critical/High なし）。台帳の Medium・Low（F2〜F7・`ps -C node` 等の誤検出・`install -d`・`-vt/app/x`）は止めない指摘として retro へ — 止める条件の一覧に当たらないため
- [test-gate] M-02 のホストの `ps e` は `ps` が許可の一覧に無く見張りと関係なく承認画面が出るので、見張りのホストの判定は TC-01 で確かめたものとして OK にした — 承認画面の出どころを分けて記録するため

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
