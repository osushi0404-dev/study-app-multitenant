# I032 手動テスト: GitHub Branch protection rules 設定手順書の作成と適用

| No | 手順 | 期待結果 | 実結果 | 備考 |
|---:|------|----------|--------|------|
| 1 | `docs/runbooks/branch-protection-setup.md` を開き、設定値一覧（develop / main の差分）が記載されていることを確認する | develop: approvals=0 / main: approvals=1 の差異が明記されている | OK | |
| 2 | 手順書の「CI 必須チェックの名前」セクションに全5ジョブ名が記載されていることを確認する | Backend Lint & Security / Backend Tests / Frontend Type Check / Frontend Lint & Security / Frontend Tests が列挙されている | OK | |
| 3 | 手順書に従って GitHub Settings で `develop` の Branch protection rules を設定する | エラーなく保存できる | OK | ユーザー操作 |
| 4 | 手順書に従って GitHub Settings で `main` の Branch protection rules を設定する | エラーなく保存できる | OK | ユーザー操作 |
| 5 | `develop` ブランチへ直 push を試みる（例: `git push origin HEAD:develop`） | GitHub が拒否する（`remote: error: GH006: Protected branch update failed`） | OK | |
| 6 | `main` ブランチへ直 push を試みる（例: `git push origin HEAD:main`） | GitHub が拒否する | OK | |
| 7 | CI が失敗する変更（例: flake8 エラーを含むコミット）で PR を作成し、マージを試みる | CI 失敗のため GitHub がマージをブロックする | スキップ | CI の status checks 登録により代替確認済み |
| 8 | `main` への PR を approve なしにマージしようとする | 1 approval 必須エラーで GitHub がブロックする | OK | PR #75 でブロック確認済み |

結論: OK
