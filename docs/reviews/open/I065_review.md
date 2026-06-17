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

## レビュー観点（実装後に記入）
- [ ] 回収 glob が lifecycle ファイル（`IXXX_review.md`）を誤回収しない（`*_review_*` 設計）
- [ ] plan リンク更新が冪等・二重 `closed/` 化しない
- [ ] 遡及移動で総数保存（消失ゼロ）・デッドリンクゼロ
- [ ] review スクリプトの保存先・投稿フローが不変
- [ ] `review-rules.md` と新挙動に齟齬がない（I064 整合）

## テスト結果
- 自動: （未実行）
- 手動: （未実行）

## 計画との差分
- なし（実装後に記入）

## ロールバック
- コミット前: `git checkout -- .` / 未コミットの `git mv` は `git reset` で復元。コミット後: `git revert`。
