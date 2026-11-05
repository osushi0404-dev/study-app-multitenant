# ハーネスの総点検の範囲

ハーネス（Claude に作業を任せる仕組み）を総点検するとき（I185 のような点検・I222 の公式の道具への置き換えの点検など）に、範囲から漏らさないものの一覧（I223）。点検の記録には、どの項目を見たか・見なかったか（と理由）を書く。

| 項目 | どこを見るか |
|------|------------|
| スキル | `.claude/skills/` |
| レビュー役 | `.claude/agents/` |
| スクリプト | `scripts/claude/` |
| 見張りと設定 | `scripts/claude/hooks/`・`.claude/settings.json`（手元の `.claude/settings.local.json` も） |
| 手順書 | `docs/runbooks/`・`CLAUDE.md` |
| 記録の置き方 | `docs/issues/`・`docs/plans/`・`docs/tests/`・`docs/reviews/` |
| MCP | `.mcp.json` |
| CI | `.github/`（ワークフロー・CODEOWNERS・Dependabot）・`.pre-commit-config.yaml` |
| **GitHub の認証・鍵・アカウント**（I223） | 下の表 |

## GitHub の認証・鍵・アカウント

Claude が GitHub を操作する名義と鍵は、リポジトリの外にもある。I223 より前はどの点検にも入っておらず、人の bot アカウントの停止で作業が 6 日止まった。

| 見ること | どこを見るか |
|---------|------------|
| Claude が操作する名義（GitHub App）・権限・入れているリポジトリ | 組織の Settings → GitHub Apps・`docs/runbooks/github-app-setup.md`「2.」 |
| 秘密の鍵ファイルの置き場所と権限、受け取る鍵の期限 | `~/.config/github-app/`（700・600）・`~/.cache/github-app/`・`scripts/claude/gh-app/gh-app-token` |
| リポジトリの外の仕組みが、リポジトリの版と同じか | `bash scripts/claude/gh-app/install.sh --check` |
| テスト用のセッションが読み取りだけの鍵で起きるか | `scripts/claude/test-session.sh`・`scripts/claude/tests/test_i223_gh_app.sh` |
| リポジトリの協力者の一覧と権限 | `gh api repos/osushi0404-dev/study-app-multitenant/collaborators` |
| ブランチの守りの設定 | `docs/runbooks/branch-protection-setup.md` |
| 手元に残る古い鍵（個人の鍵〔PAT〕・本物の `gh` に保存されたログイン） | 表の下の「古い鍵の点検コマンド」 |
| 自動化の量（書き込みの回数・頻度）が、名義の使い方と GitHub の利用の制限に合っているか | 直近の作業の push・コメント・イシューの書き換えの回数 |

### 古い鍵の点検コマンド

```bash
grep -c -E '^[[:space:]]*export[[:space:]]+(GITHUB_PERSONAL_ACCESS_TOKEN|GH_TOKEN|GITHUB_TOKEN)=' ~/.bashrc ~/.profile
GH_APP_READONLY= GH_APP_DISABLE=1 gh auth status --json hosts --jq '.hosts["github.com"][] | .login + " " + .tokenSource + " " + .state'
```

- 1 行目: 古い鍵を `export` する行を、値を出さずにファイルごとに数える（0 でないファイルの行を消す。`docs/runbooks/github-app-setup.md`「9.」）。ファイルが無いときのエラーは無視してよい
- 2 行目: 入口から App の鍵を渡さずに（`GH_APP_DISABLE=1`。読み取りだけの指定があると無視されるので空にする）、本物の `gh` が使う鍵を、名義・鍵の出どころ（環境変数か、保存されたログインのファイルか）・状態で出す。`--json` で要る欄だけを取り出すので鍵は出ない。`env -u` の形はワークツリーのセッションの見張りが止めるので使わない
