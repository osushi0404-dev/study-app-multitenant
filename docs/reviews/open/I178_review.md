# I178 レビュー: CODEOWNERS で承認者を管理者に限定し、develop・main で Code Owners の承認を必須にする

- **関連イシュー**: #297
- **計画書**: docs/plans/open/plan_I178.md
- **Draft PR**: #298
- **ステータス**: PR #298 マージ済み（2026-10-20・`6c88d9f`）。マージ後確認を記録用 PR #305 で完了（2026-10-21）。AC-4 は一部不成立（作成者がコードオーナー本人の PR）→ 文書の是正が必要

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
| AC-1 | CODEOWNERS が `* @oshui0404` の 1 行のみ | ✅ | TC-01〜TC-04 exit 0・TC-19 で全文一致・TC-17（マージ後の develop で GitHub の CODEOWNERS 検査 `{"errors":[]}`） |
| AC-2 | develop・main で Code Owners の承認が必須 | ✅（設定）／⚠️ 効き目は作成者による | 手動 No.1・No.2 で設定画面を確認・No.3 で `reviewDecision=REVIEW_REQUIRED`。No.7 で、作成者がコードオーナー本人の PR には要件がかからないことが判明（AC-4 参照） |
| AC-3 | ユーザーの承認で APPROVED・マージ可能 | ✅ | 手動 No.5（#298 で `oshui0404` の承認により `APPROVED`、`oshui0404` がマージ） |
| AC-4 | bot の承認ではマージ要件を満たさない | ❌ 一部不成立 | 手動 No.7: 作成者が `oshui0404`（唯一のコードオーナー）の PR #306 では、bot の承認で `APPROVED` になった。bot 作成の PR #305 では `oshui0404` にレビュー依頼が出て `REVIEW_REQUIRED`。bot・外部による単独マージは Restrict で止まる（No.6 代替で確認）ため、守りたかった経路は維持。文書の記述（ユーザー作成 PR はマージできない）と AC-4 の書き方の是正が必要 |
| AC-5 | Dismiss stale・Restrict who can push・bypass 不可が有効 | ✅ | 手動 No.1・No.2 で設定画面を確認。効き目は記録用 PR #305 で確認: No.6 代替（bot のマージ API が HTTP 405「You're not authorized to push to this branch」で拒否）・No.8 代替（承認後の push で `DISMISSED`・`REVIEW_REQUIRED`） |
| AC-6 | runbook の更新と誤記の除去 | ✅ | TC-05〜TC-12・TC-18・TC-19 exit 0（runbook 全体の SHA-256・設定表とステップ 3 の全文一致） |
| AC-7 | close スキル・pr-base-sync の前提が設定と一致 | ✅ | TC-13〜TC-16・TC-19 exit 0（close step 5.5〜6 の全文一致・pr-base-sync 無改変・既存テスト 21/21） |

---

## 再オープン分（2026-10-24）

- **計画書**: docs/plans/open/plan_I178.md「R. 再オープン分」
- **Draft PR**: #314
- **ステータス**: 計画中

### レビュー対象

| # | 対象 | 種別 |
|---|---|---|
| 1 | `docs/runbooks/branch-protection-setup.md` | 変更（§概要・§1.5・§4 確認 1・2 と確認 5・§6 の「自分が作った PR」の節を削除） |
| 2 | `docs/runbooks/issue-flow.md` | 変更（ステップ 25） |
| 3 | `docs/runbooks/workflow.md` | 変更（本番リリースフロー・hotfix） |
| 4 | `docs/runbooks/onboarding.md` | 変更（main へのマージの Q&A） |
| 5 | `docs/plans/open/plan_I032.md` | 削除（closed に同じ内容がある重複） |
| 6 | `scripts/claude/tests/test_i178_branch_protection_doc.sh` | 削除 |
| 7 | `.github/CODEOWNERS`・GitHub の設定・`pr-base-sync.sh`・close スキル・review-rules.md | 無改変の確認 |

### 重点レビュー観点

1. **事実との一致**: runbook の記述が手動 No.7 の結果（作成者が `oshui0404` 本人の PR には Code Owners の要件がかからない・マージは `oshui0404` だけ）と矛盾しないか。ユーザー作成 PR の扱いは書かない（ユーザーは PR を作らない・計画変更 2）ので、書いてある文が bot・外部が作った PR に限って正しいことを見る。
2. **実行できる手順か**: 書き換えたリリース・hotfix・ステップ 25 の手順が、ブランチ保護（PR 必須・承認 1・Restrict・bypass 不可・必須チェック）の下でそのまま実行できるか。main に CI が無い間の hotfix の制約が書かれているか。
3. **取りこぼし**: 直 push 手順・矛盾する記述が、対象の 4 ファイル以外に残っていないか（計画書 R3-2 の検索）。
4. **変えないものを変えていないか**: CODEOWNERS・設定・pr-base-sync・close スキル。
5. **false-green でないこと**: 合格している既存状態の TC が、失敗注入で不合格になることを確認しているか。

### 結果

| # | 受け入れ条件 | 判定 | 根拠 |
|---|---|---|---|
| AC-R1 | runbook の No.7 との矛盾の是正 | | |
| AC-R2 | 直 push 手順が残っていない | | |
| AC-R3 | ステップ 25・リリース・hotfix・onboarding が PR 経由 | | |
| AC-R4 | open に plan_I032.md が無い | | |
| AC-R5 | test_i178 が無く参照も無い | | |
| AC-R6 | CODEOWNERS・設定が無改変 | | |
