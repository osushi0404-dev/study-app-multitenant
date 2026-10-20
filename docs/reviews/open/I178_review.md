# I178 レビュー: CODEOWNERS で承認者を管理者に限定し、develop・main で Code Owners の承認を必須にする

- **関連イシュー**: #297
- **計画書**: docs/plans/open/plan_I178.md
- **Draft PR**: #298
- **ステータス**: /test 完了（2026-10-20）・/close 待ち。手動 No.4〜No.6・No.8 は /close 中、No.7・TC-17 はマージ後

---

## レビュー対象

| # | 対象 | 種別 |
|---|---|---|
| 1 | `.github/CODEOWNERS` | 新規 |
| 2 | `docs/runbooks/branch-protection-setup.md` | 変更（develop・main の設定値・承認者の限定・確認手順・トラブルシューティング） |
| 3 | `.claude/skills/close/SKILL.md` | 変更（step 5.5・6 の文言） |
| 4 | `scripts/claude/pr-base-sync.sh` | 無改変の確認 |
| 5 | `scripts/claude/tests/test_i178_branch_protection_doc.sh` | 新規（敵対的レビュー第1周 High 対応・第2周で全文比較に変更） |
| 6 | GitHub リポジトリ設定（develop・main のブランチ保護） | ユーザーが UI で変更 |

## 重点レビュー観点

1. **承認者の名前が正しいか**: CODEOWNERS の `@oshui0404` が管理者アカウントと一致し、GitHub の検査で問題が 0 件か（間違えると誰も承認できなくなる）。
2. **抜け道が残っていないか**: bot の承認・bot のマージ・承認後の差し替え・main に CODEOWNERS が無い間の扱い、のそれぞれが設定の組み合わせで塞がれているか。
3. **文書と設定の一致**: runbook の設定表・手順・確認方法・ロールバックが計画書 5-5 の表と一致しているか。develop と main で手順の書き方がそろっているか（片方だけ省略が無いか）。
4. **誤記の除去**: 「自己 approve 可」「承認不要」が残っていないか。
5. **運用の明示**: 「PR は bot が作る」「承認後のコミットで再承認」「Dependabot の PR も承認が必要」が書かれているか。
6. **無改変の確認**: `pr-base-sync.sh` の判定ロジックと既存テストが変わっていないか。
7. **false-green でないこと**: 否定・無改変の TC が、失敗注入で実際に非ゼロを返すことを確認しているか。

## 結果

2026-10-20 `/test I178`（HEAD 1d74938・ブランチ保護の設定変更後・PR #298 の CI 6 件 pass）。code-review 20261019_0005 は OK、敵対的レビュー再ステージ（20261020_0900）は第2周で通過。AC-1 は TC-17（マージ後）、AC-2〜AC-5 は /close 中とマージ後の手動確認で確定させ、記録用 PR で更新する。

| # | 受け入れ条件 | 判定 | 根拠 |
|---|---|---|---|
| AC-1 | CODEOWNERS が `* @oshui0404` の 1 行のみ | ✅（暫定） | TC-01〜TC-04 exit 0（TC-04: feature ブランチで GitHub の CODEOWNERS 検査 `{"errors":[]}`）・TC-19 で全文一致。develop での検査（TC-17）はマージ後 |
| AC-2 | develop・main で Code Owners の承認が必須 | ✅（設定）・効き目は確認中 | 手動 No.1・No.2 で設定画面を確認・No.3 で `reviewDecision=REVIEW_REQUIRED`。develop での効き目の区別は No.7（マージ後） |
| AC-3 | ユーザーの承認で APPROVED・マージ可能 | 未（/close 中） | 手動 No.5 |
| AC-4 | bot の承認ではマージ要件を満たさない | 未（マージ後） | 手動 No.7 |
| AC-5 | Dismiss stale・Restrict who can push・bypass 不可が有効 | ✅（設定）・効き目は /close 中 | 手動 No.1・No.2 で設定画面を確認。効き目は No.6（bot のマージ拒否）・No.8（承認取り消し） |
| AC-6 | runbook の更新と誤記の除去 | ✅ | TC-05〜TC-12・TC-18・TC-19 exit 0（runbook 全体の SHA-256・設定表とステップ 3 の全文一致） |
| AC-7 | close スキル・pr-base-sync の前提が設定と一致 | ✅ | TC-13〜TC-16・TC-19 exit 0（close step 5.5〜6 の全文一致・pr-base-sync 無改変・既存テスト 21/21） |
