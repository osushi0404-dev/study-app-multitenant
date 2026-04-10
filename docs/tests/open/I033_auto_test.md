# I033 自動テスト: GitHub Projects カンバンと Milestones（Phase 1〜3）の設定

## 対象
GitHub 設定のみの変更であり、Backend/Frontend のコード変更はないため自動テスト（ユニットテスト・統合テスト）の対象外。

## gh CLI による検証コマンド（実施後に実行）

```bash
REPO="osushi0404-dev/study-app-multitenant"

# Milestone 3件の存在確認
gh api repos/$REPO/milestones --jq '.[].title'
# 期待出力: Phase 1 / Phase 2 / Phase 3 の 3件

# Projects ボードの存在確認
gh project list --owner osushi0404-dev --format json | jq '.[].title'
# 期待出力: "AI Dev Improvement（Phase 1〜3）" を含む

# Issue の Milestone 紐づき確認（Phase 1 例）
gh api repos/$REPO/issues/58 --jq '.milestone.title'
# 期待出力: "Phase 1: ..."

gh api repos/$REPO/issues/60 --jq '.milestone.title'
# 期待出力: "Phase 1: ..."

# I034/I035/I036 の GitHub Issue 登録確認
gh issue list --state all --limit 10 --json number,title | jq '.[] | select(.title | startswith("I03"))'
```

結果:
- Milestone 確認:
- Projects 確認:
- Issue 紐づき確認:
