# I178 レビュー: CODEOWNERS で承認者を管理者に限定し、develop・main で Code Owners の承認を必須にする

- **関連イシュー**: #297
- **計画書**: docs/plans/open/plan_I178.md
- **Draft PR**: #298
- **ステータス**: 計画作成済み（承認待ち）

---

## レビュー対象

| # | 対象 | 種別 |
|---|---|---|
| 1 | `.github/CODEOWNERS` | 新規 |
| 2 | `docs/runbooks/branch-protection-setup.md` | 変更（develop・main の設定値・承認者の限定・確認手順・トラブルシューティング） |
| 3 | `.claude/skills/close/SKILL.md` | 変更（step 5.5・6 の文言） |
| 4 | `scripts/claude/pr-base-sync.sh` | 無改変の確認 |
| 5 | GitHub リポジトリ設定（develop・main のブランチ保護） | ユーザーが UI で変更 |

## 重点レビュー観点

1. **承認者の名前が正しいか**: CODEOWNERS の `@oshui0404` が管理者アカウントと一致し、GitHub の検査で問題が 0 件か（間違えると誰も承認できなくなる）。
2. **抜け道が残っていないか**: bot の承認・bot のマージ・承認後の差し替え・main に CODEOWNERS が無い間の扱い、のそれぞれが設定の組み合わせで塞がれているか。
3. **文書と設定の一致**: runbook の設定表・手順・確認方法・ロールバックが計画書 5-5 の表と一致しているか。develop と main で手順の書き方がそろっているか（片方だけ省略が無いか）。
4. **誤記の除去**: 「自己 approve 可」「承認不要」が残っていないか。
5. **運用の明示**: 「PR は bot が作る」「承認後のコミットで再承認」「Dependabot の PR も承認が必要」が書かれているか。
6. **無改変の確認**: `pr-base-sync.sh` の判定ロジックと既存テストが変わっていないか。
7. **false-green でないこと**: 否定・無改変の TC が、失敗注入で実際に非ゼロを返すことを確認しているか。

## 結果

（/code-review・/test 後に記入）

| # | 受け入れ条件 | 判定 | 根拠 |
|---|---|---|---|
| AC-1 | CODEOWNERS が `* @oshui0404` の 1 行のみ | | |
| AC-2 | develop・main で Code Owners の承認が必須 | | |
| AC-3 | ユーザーの承認で APPROVED・マージ可能 | | |
| AC-4 | bot の承認ではマージ要件を満たさない | | |
| AC-5 | Dismiss stale・Restrict who can push・bypass 不可が有効 | | |
| AC-6 | runbook の更新と誤記の除去 | | |
| AC-7 | close スキル・pr-base-sync の前提が設定と一致 | | |
