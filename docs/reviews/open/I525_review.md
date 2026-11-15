# I525 レビュー: 敵対的レビューの延長を引数で受け取り、Claude の Bash からサンドボックスの外で起動できるようにする

## 変更概要
- `scripts/claude/adversarial-review.sh` が延長の値を引数 `--round-limit <N>` でも受け取り、review-gate の延長の起動を `bash scripts/claude/adversarial-review.sh --round-limit 3 I###`（サンドボックスの外に出る形）にする

## 変更点
- `scripts/claude/adversarial-review.sh`: 引数 `[--round-limit <N>] I###`（順は問わない・引数が環境変数より優先）。上限の値が 1 以上の整数でなければ `ADVERSARIAL_ERROR: USAGE`・exit 2（環境変数の誤った値で上限を外す穴をふさいだ）。冒頭のコメント
- `.claude/skills/review-gate/SKILL.md`: 延長の起動を `bash scripts/claude/adversarial-review.sh --round-limit 3 "$ARGUMENTS"` にし、前置きしない理由を 1 文
- `scripts/claude/tests/test_i197_adversarial_process.sh`: `run` を引数を渡せる `run_args` の包みにし、A9e〜A9i・FG-A9e・FG-A9h を足した
- `scripts/claude/tests/test_i525_skill_sandbox_form.sh`（新規）: S1〜S3・FG 4 件

## 影響範囲
- Backend/Frontend/DB/Config: なし（ハーネスのスクリプト・手順書・テストだけ）

## テスト結果
- 自動: TC-01 pass=170 fail=0・TC-02 pass=7 fail=0（手元・実装時）。関係する既存テスト 6 本（i181・i193・i197 ledger・i202・i205・i224）pass=6 fail=0
- 手動: （未実施）

## 計画との差分
- なし

## ロールバック
- このブランチのコミットを `git revert` する

## 自律判断の記録
- [plan] 案 (a)（引数で受け取る）だけを採り、(c)（装置ファイルを数えない）は採らない — (a) だけで AC1 を満たし、(c) は安全装置の確かめを緩める
- [plan] 引数と環境変数の両方があるときは引数を採り、環境変数は残す。上限の値は 1 以上の整数だけ（環境変数の誤った値が上限を外す fail-open の穴も同時にふさぐ）
- [plan] 実機の確かめ（手動 No.2）は、このイシューの敵対的レビューの 1 周目を `--round-limit 2`（既定値）で起動して行う
STAGE_DONE: plan NEXT: plan-review
- [plan-review] 計画レビュー OK（Info 3 件は対応任意。S1 の検出範囲・fail-open の是正・worktree.md は計画で扱い済みのため直さない）
STAGE_DONE: plan-review NEXT: implement
- [implement] /simplify の 4 観点: run と run_args の重複（共通化・簡素化の 2 観点）を直し、run を run_args の包みにした。見送り: USAGE のケースのリポジトリの共有（数秒の短縮より、ケースごとに分けて互いに影響しない方を採る）・S1 を env/timeout の前置きにも広げる案・DIRTY の原因の表示（サンドボックスの検知が確実でない）・worktree.md の前置き（計画で範囲外・retro の候補）
STAGE_DONE: implement NEXT: review-gate
- [review-gate] コードレビュー OK・高リスクではない（NOT_REQUIRED）。ただし台帳 F1・F2（上限の値の確かめに上の限りが無く、桁の大きな値で上限が外れる・延長 1 周の決まりを守らない）はこのイシューの目的（上限の判定を緩めない）を崩すので、一覧に回さず直す。受け付ける値を 1〜3 にする計画変更（計画変更記録 1）→ 計画レビューをやり直す
STAGE_DONE: review-gate NEXT: plan-review
- [plan-review] 再レビュー OK（Warning 3: 実装を ^[1-3]$ に直すのは implement で行う・手動 No.2 は敵対的レビューが不要の判定だったので test-gate で必ず行う・worktree.md は retro）
STAGE_DONE: plan-review NEXT: implement
