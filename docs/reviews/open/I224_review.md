# I224 レビュー: GitHub への書き込み（イシューの書き換え・コメント・push）の回数を絞り、短い間に集中しないようにする

## 変更概要
- push を要る 3 時点（下書き PR の作成・review-gate の CI 待ちの前・close の最後の確認の前）にまとめ、ほかの段階は手元のコミットだけにする
- イシュー本文の同期を grill-me の終わりの 1 回だけにする
- 同時に複数のセッションで書き込まない決まりを `workflow.md` に書く
- 押し戻しを決定論のテスト（`test_i224_push_points.sh`）で止める

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/skills/` の 10 本・`docs/runbooks/workflow.md`・`docs/runbooks/worktree.md`・`docs/runbooks/plan-writing-rules.md`・`scripts/claude/tests/test_i224_push_points.sh`・`docs/reviews/backlog/I226.md`

## テスト結果
- 自動: （test-gate で記入）
- 手動: （test-gate で記入）

## 計画との差分
- （実装後に記入）

## ロールバック
- PR を revert する

## 自律判断の記録
- [plan] 決まりの正を `workflow.md` の 1 節にし、スキルは参照だけにした — 写しを増やさない（I195）
- [plan] `STAGE_DONE: close NEXT: merge` を close の手順 3 のコミットに入れる — 結線のためだけの 4 回目の push を無くす
- [plan] PR へのレビューの記録のコメントは変えない — grill-me で決めた範囲（push・イシュー本文）の外で、PR でレビューを読む導線を変えるのは別の判断
- [plan] この I224 の plan-issue〜implement は古いスキルのまま進め、push は手順が許す範囲でまとめる（docs と STAGE_DONE を 1 回で送る）— 計画レビューを通す前に新しい決まりで動かない
- [plan-review] PLAN_VERDICT: OK（20261107_2215）。Warning 3 件・Info 1 件を計画書・テスト文書に反映し、再レビューはしない — 方式・範囲・受け入れ条件を変えない追記だけ（計画変更記録 1）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
