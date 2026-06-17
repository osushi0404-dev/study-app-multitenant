# I065 レビュー: レビュー監査記録のライフサイクル整理（直下蓄積の解消）

## 変更概要
- timestamped 監査記録（`I###_{code,plan,issue}_review_<ts>.md`）にライフサイクル管理を導入。`/close` を回収係にし、直下蓄積を解消する（案A・review スクリプトは不変）。

## 変更点
- `.claude/skills/close/SKILL.md`: 当該 issue の直下 timestamped 記録を `closed/` へ `git mv` ＋ plan の `## レビュー結果` リンクを `closed/` 向きに更新（step 1 末尾に追加）。
- `docs/runbooks/review-rules.md`: 「直下に蓄積・移動しない」記述を「open 中は直下、`/close` で `closed/` へ回収」に更新（I064 整合）。
- 遡及整理（一度きり）: クローズ済み I054〜I064 の直下記録61件を `closed/` へ移動＋対応 plan リンク更新。

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/skills/close/SKILL.md` / `docs/runbooks/review-rules.md` / `docs/reviews/`（既存記録移動）/ `docs/plans/closed/`（リンク更新）
- review スクリプト3本: 不変（保存先は直下のまま・I062 非衝突）

## レビュー観点（実装後・検証済み）
- [x] 回収 glob が lifecycle ファイル（`IXXX_review.md`）を誤回収しない（`*_review_*` 設計）— TC-S1 で `I999_review.md` 非回収を確認
- [x] plan リンク更新が冪等・二重 `closed/` 化しない — `reviews/closed/<base>` は `reviews/<base>` を部分文字列に含まず安全。TC-S1/TC-05 で確認
- [x] 遡及移動で総数保存（消失ゼロ）・デッドリンクゼロ — 移動前後とも総数118、TC-04/05 PASS
- [x] review スクリプトの保存先・投稿フローが不変 — `git diff scripts/claude/*.sh` 空（TC-07 PASS）
- [x] `review-rules.md` と新挙動に齟齬がない（I064 整合）— `:26-29`/`:38` をライフサイクル記述へ更新

## テスト結果
- 自動: 全 TC PASS（静的 TC-01/02/03/07・スモーク TC-S1・遡及 TC-04/05/06）。詳細は `docs/tests/open/I065_auto_test.md` 実行結果。
- 手動: No.1（回収手順の配置）・No.2（rename 履歴保持）= Claude OK。No.3（実 `/close` 観察）= 将来クローズ時に Human。

## 計画との差分
- なし。プランの3ステップ（/close 回収手順・review-rules 更新・遡及整理 I054〜I064）を計画どおり実装。
- 件数の参考値は実装時点で 直下 64→65（`/plan-issue-review` が I065 記録を1件追加）に増えたが、TC-04 を不変量検証（総数保存＋直下は open のみ）に設計していたため期待値再算出なしで PASS。最終: 直下=4・closed/=114・総数=118。

## ロールバック
- コミット前: `git checkout -- .` / 未コミットの `git mv` は `git reset` で復元。コミット後: `git revert`。
