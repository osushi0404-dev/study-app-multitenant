# 診断レビュー [I223]

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 根本原因 | 原因は成立している。`gh` 9行目の `"$dir/gh-app-token"` は直接実行だ。git は実行権を 100644 で記録するため、CI の checkout では Permission denied になる。G1〜G3 は `bash` 経由なので通り、G4 だけが落ちる。この説明は実コードと整合する。 | `scripts/claude/gh-app/gh:9` |
| Info | 対応方針 | 案 A（`bash "$dir/gh-app-token"`）の推奨は妥当だ。案 B と案 C を退けた理由も筋が通っている。本番は `install -m 755` で入れる経路なので影響しない。なお、`gh-app-token` の shebang に頼る作りも同時になくなる。 | `gh:9` |
| Info | 対応方針 | テストの写し（`copy_scripts` の `cp`）は、/mnt/c では元の実行権を引き継ぐ。このため手元では CI と同条件にならなかった。診断が提案する「写しを `chmod 644` にする」と「入口の `bash ` を消す失敗注入で G4 が NG になることの確認」は、再発防止として適切だ。`fg` 用の写しも `copy_scripts` を通るので一緒に効く。 | `test_i223_gh_app.sh:154-158` |
| Info | 影響調査 | 同型の探索範囲が `scripts/claude/gh-app` と `test-session.sh` に限られている。`scripts/claude/*.sh` 全体の「`bash` なしでリポジトリ内ファイルを直接実行する所」は明示されていない。ただし、ほかのテスト 50 本は CI で合格している。他スクリプトは `bash scripts/claude/...` で呼ぶ規約だという記載もある。実害の可能性は低い。 | 影響調査 |

## 影響調査の網羅性評価
- 原因となった `gh` の直接実行、`install.sh`、credential helper、手順書の呼び方、FG の対象行は確認されている。
- fail-closed であることと、セキュリティ上の影響がないことも確認されている。
- 範囲は gh-app 周辺が中心だ。ただし CI 全体が他で通っていることが、実質的な裏付けになっている。
- 修正後に `install.sh` で入れ直す手順も書かれている。
- 重大な漏れはない。

VERDICT: OK
