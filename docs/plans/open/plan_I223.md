# I223 計画書: GitHub の操作を GitHub App に移したことを記録と仕組みに残し、点検の範囲に GitHub の認証を入れる

## 基本情報
- **計画書ID**: plan_I223
- **関連イシュー**: #412
- **Draft PR**: #414
- **作成根拠資料**: docs/issues/open/I223.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I223_review.md
- **作成日**: 2026-11-05

## 1. 背景/目的
- 背景: Claude が GitHub を操作する名義を、人の bot アカウント（`osushi0404-bot`・10-30 に停止）から GitHub App（`osushi0404-claude`）に切り替えた（11-05）。ただし、鍵を受け取る仕組みと `gh` の入口はリポジトリの外（`~/.local/bin/`）に置いただけでレビューを通っていない。GitHub の MCP は今も別の個人の鍵（PAT）で動き、手順書には bot と PAT を前提にした記述が残る。テスト用のセッション（`claude -p`）も App の書き込みの鍵を使えてしまう
- 目的: 名義と鍵の仕組みを 1 つ（App）にまとめてリポジトリに入れ、手順書だけで設定し直せるようにする。テスト用のセッションには読み取りだけの鍵を渡す。点検の範囲と計画レビューの観点に GitHub の認証・鍵・アカウントを入れる

### 調査結果
- **原因の概要**: 自動化の量を大きく増やしたのに、それを担う名義（人の bot アカウント）と鍵の仕組みがどの点検の範囲にも入っておらず、見直されなかった。切り替えも急ぎでリポジトリの外に置いた
- **今のリポジトリの外の仕組み（2026-11-05 に読んだ）**:
  - `~/.local/bin/gh-app-token`: App の秘密の鍵ファイル（`~/.config/github-app/app.pem`・権限 600）で JWT を作り、`POST /app/installations/178606088/access_tokens`（`repositories: ["study-app-multitenant"]`）で 1 時間の鍵を受け取り、`~/.cache/github-app/token`（フォルダは 700）に控える。残り 10 分を切ったら取り直す
  - `~/.local/bin/gh`: `GH_APP_DISABLE` が空なら上の鍵を `GH_TOKEN` に入れて `/usr/bin/gh` を動かす
  - `~/.gitconfig`: `credential.https://github.com.helper`（と gist）を `!/home/tacic/.local/bin/gh auth git-credential` に差し替え
  - git の作者: 元のリポジトリの `.git/config` に `user.name osushi0404-claude[bot]`・`user.email 352511081+osushi0404-claude[bot]@users.noreply.github.com`
  - `PATH` は `~/.local/bin` が `/usr/bin` より前（`which -a gh` の 1 番目が `~/.local/bin/gh`）
  - `/usr/bin/gh` の保存されたログイン（`~/.config/gh/hosts.yml`）は `osushi0404-bot` のもので、今は無効（`GH_APP_DISABLE=1 gh auth status` が「token … is invalid」）
- **App の鍵で動かない呼び出し**: `grep -rnE "gh api user|api/user|\.login" .claude scripts docs/runbooks` で 0 件。スキル・スクリプトの `gh` の使い方（`gh pr view/list/checks/edit/ready/review --comment`・`gh issue create/list/comment/edit`）は App の鍵で動く（I220 の review-gate・close と、この計画の下書き PR #414・イシュー #412 の本文の更新で実際に動いた）。直す所なし
- **GitHub の MCP**: `.mcp.json` の `github`（`@modelcontextprotocol/server-github@2025.4.8`・`GITHUB_PERSONAL_ACCESS_TOKEN`）。鍵の値は `~/.bashrc` で設定（ファイル名だけ確かめた・値は読んでいない）。スキル・スクリプトから `mcp__github__*` を呼ぶ所は無い。見張り（`.claude/settings.json:198` の matcher・`pretooluse_guard.py:2931-2934,3708`）と、そのテスト（`test_pretooluse_gh_pr_guard.sh`・`test_settings_permissions.sh`）は MCP の操作の名前を見ているだけで、MCP を外しても壊れない（安全装置なので触らない）
- **MCP を外すと影響する所（消費箇所の全件・`grep -rnlE "mcp__github|mcp-github-setup|\.mcp\.json|server-github" .claude docs/runbooks scripts CLAUDE.md .github`）**:
  - 直す: `.mcp.json`・`scripts/claude/tests/test_i187_frontend_verify_config.sh:56-59`（② github の args が変わっていない）・`docs/runbooks/mcp-usage.md:11,54-56,86`・`docs/runbooks/mcp-github-setup.md`（全体）・`CLAUDE.md:32`（参照先）
  - 直さない: `scripts/claude/check-permission-prompt.sh:69`（`--mcp-config .mcp.json` は playwright のため）・`scripts/claude/code-review.sh:624`（`.mcp.json` をハーネスの種類に分ける）・`scripts/claude/tests/test_i205_stop_criteria.sh:136`（同）・`test_check_permission_prompt.sh:65`（引数の確かめ）・`docs/runbooks/frontend-verify.md:16,86`（playwright の話）
- **bot・`gh auth login` を前提にした手順書の記述**: `docs/runbooks/branch-protection-setup.md:68`（`osushi0404-bot` の名前）・`docs/runbooks/issue-flow.md:68`（`gh auth login` で認証済みが前提）。`branch-protection-setup.md` の他の「bot」は Claude の名義の一般名で、App も `osushi0404-claude[bot]` なので意味は変わらない（§1.5 の冒頭で、今の bot は App だと 1 行足す）
- **テスト用のセッションを起こす所**: `scripts/claude/check-permission-prompt.sh:70`（承認画面の判定）・`scripts/claude/review-process-lib.sh:28`（`run_claude_logged`・code-review.sh・adversarial-review.sh の検証役）と、手動テストで手で書く `claude -p`（I220 の M-03・M-04・M-06 など。`--disallowedTools "Bash(gh issue:*)" "Bash(gh api:*)"` だけで `gh pr`・`git push` は止めていない）
- **スパイク（未知リスク・2026-11-05 に実証・成立）**: App の鍵は受け取るときに権限を絞れる（`access_tokens` の本文に `permissions`）。スクラッチパッドのスクリプトで `{"contents":"read","issues":"read","pull_requests":"read","metadata":"read","actions":"read","checks":"read","statuses":"read"}` を付けて受け取ると、応答の `permissions` がすべて `read` になった。その鍵で `gh api repos/osushi0404-dev/study-app-multitenant/issues/412 --jq .number` → `412`・`gh pr list` → 読めた。書き込みの `gh api -X POST …/issues/412/reactions -f content=eyes` → `HTTP 403 Resource not accessible by integration`。`git push --dry-run`（その鍵を渡す credential helper）→ `Permission to … denied to osushi0404-claude[bot]`・`403`。**GitHub の側で書き込みが止まる**（文字列の見張りではない）
- **秘密情報がリポジトリに入らない手当て（今あるもの）**: コミットの前（`.pre-commit-config.yaml` の detect-secrets）と CI（`ci.yml` の pre-commit）で `.secrets.baseline` の `PrivateKeyDetector`・`GitHubTokenDetector` が動く。`test_i182_secret_gates.sh` が detect-secrets の外れを見ている。`.gitignore` に `*.pem` は無い
- **総点検の一覧**: いつでも見られる場所には無い（`grep -rnlE "総点検|点検の一覧"` で I185 の計画書・記録だけ）。I185 の点検の範囲は `.claude/settings.json`・`.claude/skills/`・`scripts/claude/`・`docs/runbooks/` だった（`plan_I185.md:29`）
- **台帳の残りの一覧**: 実装対象のファイルに当たるのは `docs/runbooks/onboarding.md`（I211-F7・A3・A1・I220-F4）・`scripts/claude/check-permission-prompt.sh`（I200-F7）・`docs/runbooks/plan-writing-rules.md`（I209-F1）。`FILE=-` は 0 件（§9）
- **既存のテストのベースライン**: 実装対象のファイルを見ている `test_i187_frontend_verify_config.sh`・`test_check_permission_prompt.sh`・`test_i197_adversarial_process.sh`・`test_i107_track_label_docs.sh`・`test_i179_worktree_docs.sh`・`test_i185_harness_docs.sh`・`test_next_issue_num.sh` を実装前に流す（TC-01。結果は auto_test に記録）
- **環境前提**: `openssl`・`curl`・`python3`・`/usr/bin/gh`・`detect-secrets`・`pre-commit`・`claude` がある（`which -a` で確認・スパイクで使用）。App の秘密の鍵ファイルはこの端末の `~/.config/github-app/app.pem` にある

## 2. 受け入れ条件
- [ ] 鍵を受け取る仕組みと `gh` の入口がリポジトリ（`scripts/claude/gh-app/`）にあり、手順書（`docs/runbooks/github-app-setup.md`）の手順だけで新しい端末（WSL）に設定できる
- [ ] 秘密の鍵ファイルと受け取った鍵がリポジトリに入らない（決定論のチェックで確かめる）
- [ ] 手順書に `osushi0404-bot` を前提にした記述が残っていない
- [ ] App の鍵で動かない呼び出しが無い（あれば直した）
- [ ] 総点検の一覧に GitHub の認証・鍵・アカウントがあり、計画の観点に名義と鍵の仕組みの確認がある
- [ ] テスト用のセッション（`claude -p`）を起こすときの既定で、GitHub への書き込み（`gh issue`・`gh pr`・`gh api`・`git push` など）がすべて止まる（読み取りだけの App の鍵を渡し、GitHub の側で拒否させる）
- [ ] `.mcp.json` に GitHub の MCP が無く、手順書に MCP の個人の鍵（PAT）を前提にした手順が残っていない
- [ ] bot が戻った後の片付けが済んでいる、または `docs/reviews/backlog/I223.md` に残っている
- [ ] 既存のハーネステスト・CI がすべて pass する

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `scripts/claude/gh-app/`（新規 3 本）・`scripts/claude/test-session.sh`（新規）・`scripts/claude/check-permission-prompt.sh`・`scripts/claude/review-process-lib.sh`・`scripts/claude/code-review.sh`・`scripts/claude/plan-issue-review.sh`・`scripts/claude/issue-review.sh`・`scripts/claude/fix-review-lib.sh`（計画変更記録 3）・`scripts/claude/tests/test_i223_gh_app.sh`（新規）・`scripts/claude/tests/test_i187_frontend_verify_config.sh`・`.mcp.json`・`.gitignore`・`CLAUDE.md`（参照先の行）・`docs/runbooks/`（`github-app-setup.md`〔`mcp-github-setup.md` から改名〕・`harness-audit.md`〔新規〕・`mcp-usage.md`・`branch-protection-setup.md`・`issue-flow.md`・`onboarding.md`・`plan-writing-rules.md`）・`.claude/agents/plan-reviewer.md`・`docs/reviews/backlog/I223.md`（新規）
- リポジトリの外（この端末）: `~/.local/bin/gh-app-token`・`~/.local/bin/gh` をリポジトリの版で置き換える／`~/.bashrc` の `GITHUB_PERSONAL_ACCESS_TOKEN` の行を消す
- 安全装置（`path_risk_trigger` の集合: `.github/*`・`.pre-commit-config.yaml`・`.secrets.baseline`・`pretooluse_guard.py`・`.claude/settings.json`・`.claude/settings.local.json`）には触らない
- 依存関係ファイルの変更なし（Dockerfile・docker-compose.yml への波及なし）

## 4. 変更点一覧（具体）

### 修正アプローチ
1. リポジトリの外の 2 本を、少し整えてリポジトリ（`scripts/claude/gh-app/`）に入れ、端末に入れる手順をスクリプト 1 本（`install.sh`）にまとめる。秘密の鍵ファイルと受け取った鍵は `$HOME` の下だけに置く（今と同じ）
2. 鍵の受け取りに「読み取りだけ」の形（`GH_APP_READONLY=1`）を足す。テスト用のセッションを起こす所はすべてこの形で起こし、GitHub の側で書き込みを拒否させる（スパイクで成立を確かめた）。手で書く `claude -p` は、新しい入口 `scripts/claude/test-session.sh` を通す決まりにする
3. GitHub の MCP を外し、GitHub の操作を `gh`（App の鍵）だけにする。MCP の PAT の手順書を App の手順書に置き換える
4. 手順書の bot・`gh auth login` の前提を直し、総点検の常設の一覧と、計画レビュー役の観点を足す
5. bot が戻らないとできない片付けは、やり残しの一覧に回す

### 4-1. `scripts/claude/gh-app/gh-app-token`（新規・今の `~/.local/bin/gh-app-token` をもとにする）
修正方針: 1 時間の鍵を出す。読み取りだけの形を足し、書き込みの鍵と控えを分ける。読み取りだけの形で GitHub が書き込みの権限を返したら、鍵を出さずに止める（fail-closed）。
```bash
#!/usr/bin/env bash
# GitHub App（osushi0404-claude）の 1 時間の鍵を出す。残り 10 分を切ったら取り直す（I223）。
# GH_APP_READONLY=1 のときは読み取りだけの鍵（テスト用のセッション向け）。控えは書き込みの鍵と別のファイル。
# 秘密の鍵ファイルと控えは $HOME の下だけに置く（リポジトリに入れない）。
set -euo pipefail
CLIENT_ID="${GH_APP_CLIENT_ID:-Iv23licv2TJyaXdBHe4W}"          # 秘密ではない（App の公開の番号）
INSTALLATION_ID="${GH_APP_INSTALLATION_ID:-178606088}"         # 同上
REPO="${GH_APP_REPO:-study-app-multitenant}"
KEY="${GH_APP_KEY:-${HOME}/.config/github-app/app.pem}"
CACHE_DIR="${GH_APP_CACHE_DIR:-${HOME}/.cache/github-app}"
READ_PERMS='{"contents":"read","issues":"read","pull_requests":"read","metadata":"read","actions":"read","checks":"read","statuses":"read"}'
if [ -n "${GH_APP_READONLY:-}" ]; then
  CACHE="${CACHE_DIR}/token-readonly"; PERMS=",\"permissions\":${READ_PERMS}"
else
  CACHE="${CACHE_DIR}/token"; PERMS=""
fi
umask 077
mkdir -p "$CACHE_DIR"
# （控えの読み・JWT の作成は今と同じ。curl に --max-time 20 を足す）
# 本文: {"repositories":["${REPO}"]${PERMS}}
# 応答を python3 -I で読み、GH_APP_READONLY=1 のときは permissions の値がすべて "read" でなければ
# 「読み取りだけの鍵を受け取れませんでした」と stderr に出して exit 1（控えに書かない）
# 控えは mktemp → mv（今と同じ）
```

### 4-2. `scripts/claude/gh-app/gh`（新規・今の `~/.local/bin/gh` をもとにする）
修正方針: `gh` を呼ぶたびに App の鍵を渡して本物の `gh` を動かす。同じフォルダの `gh-app-token` を使う。`GH_APP_READONLY=1` のときは `GH_APP_DISABLE` を無視する（読み取りだけの指定を、退避の指定で外せないようにする）。
```bash
#!/usr/bin/env bash
# gh を GitHub App の鍵で動かす（I223）。GH_APP_READONLY=1 なら読み取りだけの鍵。
# GH_APP_DISABLE=1（読み取りだけの指定が無いとき）は鍵を渡さずに本物の gh を動かす（App が使えないときの退避）
REAL_GH="${GH_APP_REAL_GH:-/usr/bin/gh}"
if [ -n "${GH_APP_READONLY:-}" ] || [ -z "${GH_APP_DISABLE:-}" ]; then
  GH_TOKEN="$("$(dirname "$0")/gh-app-token")" || { echo "gh-app-token: 鍵を受け取れませんでした" >&2; exit 1; }
  export GH_TOKEN
fi
exec "$REAL_GH" "$@"
```

### 4-3. `scripts/claude/gh-app/install.sh`（新規）
修正方針: 新しい端末で 1 回流せば、上の 2 本を `~/.local/bin` に入れ、git の credential helper を差し替える。`--check` で、入っているものがリポジトリの版と同じか・設定がそろっているかだけを確かめる（何も変えない）。秘密の鍵ファイルは作らない・動かさない（手順書の手順で人が置く）。
- 前提の確かめ（足りなければ何も変えずに exit 1）: `openssl`・`curl`・`python3`・本物の `gh`（`/usr/bin/gh`）がある／秘密の鍵ファイル（`GH_APP_KEY` の既定 `~/.config/github-app/app.pem`）があり権限が 600／`PATH` で `~/.local/bin` が `/usr/bin` より前
- 入れる: `install -m 755 scripts/claude/gh-app/gh-app-token scripts/claude/gh-app/gh ~/.local/bin/`（前の版があれば `~/.cache/github-app/backup/` に日時つきで写してから）
- git の設定: `git config --global --replace-all credential.https://github.com.helper ''` と `git config --global --add credential.https://github.com.helper "!$HOME/.local/bin/gh auth git-credential"`（gist も同じ。今の `~/.gitconfig` と同じ形）
- 作者: `git config user.name 'osushi0404-claude[bot]'`・`git config user.email '352511081+osushi0404-claude[bot]@users.noreply.github.com'`（このリポジトリの設定。ワークツリーで共有）
- 最後に `~/.local/bin/gh api repos/osushi0404-dev/study-app-multitenant --jq .full_name` で疎通を見る（読むだけ）
- `--check`: 2 本が `cmp` で同じ・credential helper・作者・`PATH` の順がそろっていれば exit 0、違えば違う所を出して exit 1

### 4-4. `scripts/claude/test-session.sh`（新規）
修正方針: テスト用のセッションの入口。読み取りだけの鍵の指定を付けて `claude -p` を起こす（引数はそのまま渡す）。
```bash
#!/usr/bin/env bash
# テスト用のセッション（claude -p）の入口（I223）。GitHub へは読み取りだけの App の鍵を渡し、書き込みを GitHub の側で拒否させる。
# 使い方: bash scripts/claude/test-session.sh <claude -p に渡す引数…>
export GH_APP_READONLY=1
exec "${CLAUDE_BIN:-claude}" -p "$@"
```

### 4-5. `scripts/claude/check-permission-prompt.sh`・`scripts/claude/review-process-lib.sh`（と、計画変更記録 3 の 4 か所）
修正方針: 新しいセッションを起こす所をすべて読み取りだけの鍵にする。
- 計画変更記録 3: `code-review.sh:153`（`out=$(GH_APP_READONLY=1 timeout …`）・`plan-issue-review.sh:131`・`issue-review.sh:40`・`fix-review-lib.sh:81`（どれも `| GH_APP_READONLY=1 timeout … claude -p`）にも同じ指定を付ける
- `check-permission-prompt.sh`: `"${CLAUDE_BIN:-claude}" -p …`（70 行目）の前に `GH_APP_READONLY=1` を付ける（`if ! GH_APP_READONLY=1 "${CLAUDE_BIN:-claude}" -p …`）。冒頭の説明に「GitHub への書き込みは読み取りだけの鍵で GitHub が拒否する（承認なしで通る判定でも書き込まれない・I223）」を 1 行足す
- `review-process-lib.sh`: `timeout "$secs" "${CLAUDE_BIN:-claude}" -p …`（28 行目）を `GH_APP_READONLY=1 timeout …` にする。冒頭の「考え方」に 1 行足す

### 4-6. `scripts/claude/tests/test_i223_gh_app.sh`（新規）
修正方針: 壊れても気づきにくく、壊れると本物の書き込みが起きるところだけを見る（plan-writing-rules.md「決定論テストの対象の選び方」）。`curl`・`openssl`・本物の `gh`・`claude` は、一時フォルダの偽物に差し替える（`PATH`・`GH_APP_REAL_GH`・`CLAUDE_BIN`・`GH_APP_CACHE_DIR`・`GH_APP_KEY`）。秘密の鍵ファイルも本物の GitHub も使わない。ケースは auto_test の TC-02 の G1〜G6（G6 は計画変更記録 3: `scripts/claude/*.sh` の `claude -p` の呼び出しの論理行がすべて `GH_APP_READONLY=1` を持つ静的な検査。`export GH_APP_READONLY=1` するファイルは除く）。各ケースに、スクリプトの写しを `sed` で壊して不合格になることを確かめる FG を付ける

### 4-7. GitHub の MCP を外す
- `.mcp.json`: `mcpServers.github` を消す（`playwright` はそのまま）
- `scripts/claude/tests/test_i187_frontend_verify_config.sh:56-59`: ②を「github の MCP が無い（I223 で外した）」= `"github" not in servers` に直す
- `docs/runbooks/mcp-usage.md`: 11 行目の表の行を「GitHub MCP | 廃止（I223） | GitHub の操作は `gh`（App の鍵）だけ。`docs/runbooks/github-app-setup.md`」にする／「## 3. GitHub MCP」の本文を「I223 で外した。GitHub の操作は `gh` を使う（名義と鍵を App の 1 つにするため）」にする／86 行目の「既存の GitHub MCP は `@2025.4.8` と固定しており」の例を playwright（`@0.0.83`）に置き換える
- `CLAUDE.md:32`: 「GitHub MCP セットアップ: docs/runbooks/mcp-github-setup.md」→「GitHub の名義（App）と鍵の設定: docs/runbooks/github-app-setup.md」。同じ節に「ハーネスの総点検の範囲: docs/runbooks/harness-audit.md」を 1 行足す（参照先だけ・ルールは増やさない）

### 4-8. `docs/runbooks/github-app-setup.md`（`mcp-github-setup.md` を `git mv` で改名して書き直す）
修正方針: 新しい端末（WSL）で、この手順だけで App の名義に設定できるようにする。中身:
1. 何をしているか（App の鍵は 1 時間で切れる・`gh` の入口が毎回渡す・git の push も同じ入口・テスト用のセッションは読み取りだけの鍵）
2. App の設定（作り方の要点と今の値）: 組織 `osushi0404-dev` の下・このリポジトリだけに入れる・権限は Contents・Issues・Pull requests・Workflows を読み書き、Actions・Checks・Commit statuses を読み取り、それ以外はなし・App の番号（Client ID・Installation ID）は `gh-app-token` の既定値。develop・main の push 制限の一覧に App を入れない
3. 秘密の鍵ファイルを置く: App の設定画面で鍵を作り、`~/.config/github-app/app.pem` に置いて `chmod 600`（フォルダは 700）。リポジトリの中に置かない・コマンドの引数や履歴に鍵の中身を出さない
4. `bash scripts/claude/gh-app/install.sh` を流す → `bash scripts/claude/gh-app/install.sh --check` が exit 0
5. 確かめる: `gh auth status` に `osushi0404-claude[bot] (GH_TOKEN)`・`git push` が通る
6. テスト用のセッション: `bash scripts/claude/test-session.sh …` で起こす（読み取りだけの鍵）。決まりの正は `plan-writing-rules.md`
7. 困ったとき: 鍵を受け取れない（鍵ファイルの場所・権限・App の Installation の有無）／`GH_APP_DISABLE=1` は退避で、今は保存されたログイン（bot）が無効なので使えない
8. 守ること: 秘密の鍵ファイル・控え（`~/.cache/github-app/`）をリポジトリや他人と共有しない／漏れたら App の設定画面で鍵を消して作り直す／控えの書き込みの鍵は同じ端末のプログラムからは読めるので、テスト用のセッションでわざと読む書き方は守りの対象外（文字列ガードと同じく「普通の書き方の事故」を止めるもの）
9. 前の仕組み（I223 より前）: MCP の PAT の手順は廃止。手元の `GITHUB_PERSONAL_ACCESS_TOKEN` は消し、PAT は持ち主のアカウントの GitHub の設定画面（Settings → Developer settings → Personal access tokens）で失効させる

### 4-9. `.gitignore`
- 末尾に `*.pem`（I223・秘密の鍵ファイルを誤って置いても入らないように）を足す

### 4-10. 手順書の bot・`gh auth login` の前提
- `docs/runbooks/branch-protection-setup.md:68`: 「bot アカウント `osushi0404-bot` は書き込み権限を持つため」→「Claude の名義（GitHub App `osushi0404-claude[bot]`・I223 より前は bot アカウント）は書き込み権限を持つため」。§1.5「### 運用」の先頭に「- この手順書の「bot」は Claude が GitHub を操作する名義のこと（I223 から GitHub App `osushi0404-claude[bot]`。設定は `docs/runbooks/github-app-setup.md`）。」を足す
- `docs/runbooks/issue-flow.md:68`: 「`gh auth login`で認証済みであることが前提」→「`gh` が GitHub App の鍵で動くことが前提（`docs/runbooks/github-app-setup.md`）」
- `docs/runbooks/onboarding.md`: 「## 手元の準備（ハーネスのテスト）」の前に「## 手元の準備（GitHub の名義）」を足し、「Claude は GitHub App の名義で GitHub を操作する。新しい端末では `docs/runbooks/github-app-setup.md` の手順で設定する」の 2 行だけを書く

### 4-11. テスト用のセッションの決まり（`docs/runbooks/plan-writing-rules.md`）
- 「外部/ハーネス挙動依存のスパイク実証」(2) の「まず `claude -p` で新しいセッションを起動して確かめられないかを試す」の後に「（手で起こすときは `bash scripts/claude/test-session.sh <引数>`。GitHub へは読み取りだけの鍵になり、書き込みは GitHub が拒否する・I223。`check-permission-prompt.sh` と検証役の起動も同じ）」を足す
- 「ハーネス挙動テストの実施環境」の表の `claude -p の判定` の行の用途に「手で起こすときは `scripts/claude/test-session.sh`」を足す

### 4-12. 総点検の常設の一覧（`docs/runbooks/harness-audit.md`・新規）
修正方針: ハーネスの総点検（I185 のような点検・I222 の公式の道具の点検）で、範囲から漏らさないものの一覧を 1 か所に置く。中身は短く、項目と「どこを見るか」だけ:
- スキル（`.claude/skills/`）・レビュー役（`.claude/agents/`）・スクリプト（`scripts/claude/`）・見張りと設定（`scripts/claude/hooks/`・`.claude/settings.json`）・手順書（`docs/runbooks/`）・記録の置き方（`docs/`）・MCP（`.mcp.json`）・CI（`.github/`）
- **GitHub の認証・鍵・アカウント**（I223）: Claude が操作する名義（App）と権限・入れているリポジトリ／秘密の鍵ファイルの置き場所と権限・受け取る鍵の期限／リポジトリの外の仕組み（`~/.local/bin/`・`~/.gitconfig`）がリポジトリの版と同じか（`install.sh --check`）／リポジトリの協力者の一覧と権限／ブランチの守りの設定（`branch-protection-setup.md`）／手元に残る古い鍵（PAT・`gh` の保存されたログイン）／自動化の量（書き込みの回数）が名義の使い方に合っているか
- 点検の記録には、どの項目を見たか・見なかったかを書く

### 4-13. 計画レビュー役の観点（`.claude/agents/plan-reviewer.md`）
- 「### P5. 運用性・障害対応性」の末尾に 1 行足す: 「- **名義と鍵（ハーネス）**: GitHub への書き込みの量（回数・頻度・自動の起票やコメント）を大きく増やす計画、または GitHub の認証・鍵の仕組みを変える計画で、それを担う名義（GitHub App）・鍵の仕組み・GitHub の利用の制限に合っているかが計画書に書かれているか（I223。bot アカウントの停止で 6 日止まった）」
- 決定論のチェックにはしない（量が「大きく増える」かは判断で、文字列で決められないため）

### 4-14. この端末の設定（リポジトリの外）
- `bash scripts/claude/gh-app/install.sh` で、今の `~/.local/bin/gh-app-token`・`~/.local/bin/gh` をリポジトリの版に置き換える（前の版は `~/.cache/github-app/backup/` に写る）→ M-02
- `~/.bashrc` の `export GITHUB_PERSONAL_ACCESS_TOKEN=` の行を、値を表示せずに消す（`sed -i '/^export GITHUB_PERSONAL_ACCESS_TOKEN=/d' ~/.bashrc`。行の形が違えば消さずに止めて、行番号だけを出す）→ M-08。PAT の失効は持ち主のアカウントでしかできないので、close でユーザーにお願いする（受け入れ条件ではない）

### 4-15. `docs/reviews/backlog/I223.md`（新規・bot が戻らないとできない片付け）
- 書く行（`- B<n> SEV=Low REPRO=no KIND=harness FILE=- | 内容 | 一覧に回した理由: bot の停止中で、できない／決められない`）:
  - B1: 隠れている PR #404 を閉じる（bot が戻って見えるようになったら）
  - B2: 古いブランチ `feature/I220-claude-files-issues` を消す（PR #404 を閉じた後）
  - B3: `osushi0404-bot` を協力者から外すかを決める（grill-me の答え: 戻るまで残す）。外すなら、手元の保存されたログイン（`gh auth logout -h github.com -u osushi0404-bot`）も消す
  - B4: MCP に使っていた PAT が bot のものなら、bot が戻った後に bot の設定画面で失効させる
- close の時点で bot が戻っていて済んだ行は消す

## 5. 実装手順（ステップ）
1. 鍵の仕組み（4-1・4-2・4-3）とテスト（4-6 の G1〜G4）を書く（未知リスクだった読み取りだけの鍵はスパイクで成立済み。まず仕組みとテストを固める）→ TC-02 参照
2. テスト用のセッションの入口（4-4・4-5）と G5 を書く（ステップ 1 の後）→ TC-02・TC-01 参照
3. この端末に入れ直す（4-14 の前半。ステップ 1 の後）。以後の push・`gh` はリポジトリの版で動く → M-01・M-02 参照
4. GitHub の MCP を外す（4-7）・手順書を書く・直す（4-8・4-9・4-10・4-11・4-12）・計画レビュー役の観点（4-13）（ステップ 1〜3 と並行可）→ TC-01・TC-03・M-05〜M-07 参照
5. ~~`~/.bashrc` の PAT の行を消す~~ → close でユーザーにお願いする（計画変更記録 2）→ M-08 参照
6. やり残しの一覧を書く（4-15）→ M-09 参照
7. 組み込みの `/simplify` で整理し、push する

## 6. テスト計画
### 自動
- TC-01: 実装対象のファイルを見ている既存のテスト（`test_i187_frontend_verify_config.sh`・`test_check_permission_prompt.sh`・`test_i197_adversarial_process.sh`・`test_i107_track_label_docs.sh`・`test_i179_worktree_docs.sh`・`test_i185_harness_docs.sh`・`test_next_issue_num.sh`）と新しい `test_i223_gh_app.sh`、計画変更記録 3 で触る起動の行を見ている `test_i193_official_flow.sh`・`test_fix_review.sh` が exit 0（決定論ゲート）。全体（`run-all.sh`）は CI の Harness Tests
- TC-02: `test_i223_gh_app.sh` の G1〜G6（G6 はすべての `claude -p` の起動の行に読み取りだけの指定があること・計画変更記録 3。読み取りだけの鍵の本文・控えの分離・書き込みの権限が返ったら止まる・`GH_APP_DISABLE` で外せない・テスト用のセッションを起こす 3 か所が読み取りだけの指定を渡す）と FG
- TC-03: 秘密の鍵ファイルと鍵の形の文字列を、コミットの前の検査（detect-secrets・今の `.secrets.baseline`）が見つける（一時フォルダの偽の鍵で 1 回流す。受け入れ条件 2 の決定論のチェックは今ある detect-secrets（コミットの前と CI）で、それが App の鍵の形も見つけることをここで確かめる）
- テストレベル: シェルスクリプトの単体（偽物の差し替え）＋手動の実走（本物の GitHub に対する読み取り・拒否の観測）。認可の変更は GitHub の側（鍵の権限）で、M-03 で確かめる
### 手動（すべて Claude）
- M-01: 一時の `HOME` に `install.sh` で入れ、そこから `gh` で読める（新しい端末の再現）
- M-02: この端末に入れ直した後、`install.sh --check` が exit 0・`gh auth status` が App・push が通る
- M-03: `test-session.sh` で起こしたセッションで、書き込み（リアクションの追加・`git push --dry-run`）が GitHub に 403 で拒否され、読み取りは通る
- M-04: `check-permission-prompt.sh` で起こしたセッションでも、書き込みが GitHub に拒否される
- M-05: 手順書に `osushi0404-bot` を前提にした記述・PAT の手順・`gh auth login` の前提が無い
- M-06: `.mcp.json` に github が無く、新しいセッションの MCP の一覧に github が出ない
- M-07: 総点検の一覧・計画レビュー役の観点がある
- M-08: `~/.bashrc` に PAT の行が無く、新しいシェルに `GITHUB_PERSONAL_ACCESS_TOKEN` が無い
- M-09: やり残しの一覧に B1〜B4 がある（済んだ行は消えている）

## 7. ロールバック
- PR を revert する（スクリプト・手順書・`.mcp.json` が戻る）
- この端末: `~/.cache/github-app/backup/` の前の版を `~/.local/bin/` に戻す（前の仕組みと同じ動きに戻る）。MCP を戻すときは PAT を作り直して `~/.bashrc` に書き、`.mcp.json` を revert で戻す（PAT の値は消すので、戻すには作り直しが要る）
- データ・GitHub の設定の変更なし（守りの設定・App の権限は変えない）

## 8. Risk & 回避策
- R1: 読み取りだけの鍵の控えを書き込みの鍵と取り違え、テスト用のセッションに書き込みの鍵が渡る → 控えのファイルを分け（G2）、応答の権限を確かめて違えば止める（G3）。M-03 で本物の GitHub の拒否を見る
- R2: 入れ直しで今の仕組みが壊れ、push・`gh` が止まる → `install.sh` は前の版を写してから入れ、疎通を最後に見る。壊れたら写しを戻す（ロールバック）。入れ直しはステップ 3 で、PR の push の前に確かめる
- R3: テスト用のセッションが `GH_APP_READONLY` を外す・控えのファイルを直接読む・本物の `gh`（`/usr/bin/gh`）を呼ぶ → わざと回避する書き方は守りの対象外（文字列ガードと同じ「普通の書き方の事故」が対象）。`/usr/bin/gh` の保存されたログインは今は無効（bot）。手順書の「守ること」に書き、敵対的レビューにも渡す
- R4: M-03・M-04 で読み取りだけの鍵が効かず、本物の書き込みが起きる → 書き込みは #412 へのリアクション（消せる）と `git push --dry-run`（何も送らない）だけにする。リアクションが付いたら消して記録する
- R5: `~/.bashrc` の行を消し間違える → 行の形を `^export GITHUB_PERSONAL_ACCESS_TOKEN=` に限り、当たる行が 1 行のときだけ消す。消す前に `~/.bashrc` の行数を控え、消した後に 1 行だけ減ったことを確かめる（値は読まない）
- R6: MCP を外すと、今の会話のセッションで `mcp__github__*` の道具が残って見える → セッションを開き直すと消える（`.mcp.json` はセッション開始で読まれる）。M-06 は新しいセッションで見る
- R7: 既存のテストが `.mcp.json` の github を見ている（test_i187 ②）→ 4-7 で直す。TC-01 で確かめる

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ・本文）:
- GitHub の MCP を外して `gh` だけにする。見張りの MCP の部分（`.claude/settings.json`・`pretooluse_guard.py`）は触らない（ユーザーが OK）
- `osushi0404-bot` は戻るまで協力者に残す。bot が戻らないとできない片付けは待たずに `docs/reviews/backlog/I223.md` に回す
- 対象の端末は WSL（Linux）だけ
- 秘密の鍵ファイルはリポジトリに入れない。守りの設定・App の権限は変えない。App を develop・main の push 制限の一覧に入れない
- テスト用のセッションは「書き込みをすべて止める」か「App の鍵を渡さない」かを計画で決める（#412 のコメント）

Claude が決めた（技術的な選択と理由）:
- テスト用のセッションには**読み取りだけの App の鍵**を渡す — GitHub の側で書き込みを拒否するので、`gh issue`・`gh pr`・`gh api`・`git push` のどの書き方でも止まる（スパイクで成立）。「鍵を渡さない」案は読み取りも止まり、テストで GitHub の状態を読めなくなる。`--disallowedTools` の文字列で止める案は書き方の数だけ漏れる（I179 の教訓・ローカルの守りは最小限）
- 読み取りだけの指定は環境変数 `GH_APP_READONLY=1` で、`gh` の入口・git の credential helper の両方に引き継がれる — 子のプロセスに自動で引き継がれ、`git push` も同じ入口を通るため
- 手で起こすテスト用のセッションは新しい入口 `scripts/claude/test-session.sh` を通す決まりにする（`plan-writing-rules.md`）。スクリプトが起こす 2 か所（`check-permission-prompt.sh`・`review-process-lib.sh`）はスクリプトの中で付ける — 既定を仕組みで持たせるため。検証役（読むだけの道具）にも付けるのは、付けても失うものが無く、起こし方をそろえられるため
- 記憶の場所への書き込みを止める件（I222 #402 へのコメント）は同梱しない — I222 は公式の設定で止められるかを先に調べる計画で、ここで先に自作の止め方を足すと二度手間になる。`test-session.sh` が入口になるので、I222 はここに足せばよい（I222 #402 にコメントで知らせる・retro で扱う）
- 置き場所は `scripts/claude/gh-app/`（3 本をまとめる）。入れる名前は今と同じ `~/.local/bin/gh-app-token`・`~/.local/bin/gh` — 今の `PATH`・`~/.gitconfig` をそのまま使えるため
- 入れ方はリンクでなく写し（`install -m 755`）— ワークツリーは消すことがあり、元のリポジトリもブランチを切り替えるので、リンク先が変わる・消えると `gh` と push が止まる。ずれは `install.sh --check` で見る
- App の番号（Client ID・Installation ID）はスクリプトの既定値に書く — 秘密ではない（鍵が無ければ使えない）。環境変数で上書きできる
- `GH_APP_READONLY=1` のときは `GH_APP_DISABLE` を無視する — 退避の指定で、保存されたログイン（書き込みのできる名義）に落ちないため
- 読み取りだけの形で受け取った鍵の権限を確かめて、違えば止める — GitHub が本文の `permissions` を無視する・App の権限が変わるなどで、黙って書き込みの鍵になるのを防ぐため（fail-closed）
- `curl` に `--max-time 20` を足す — GitHub が応答しないと `gh` と push が止まり続けるため。取り直しは次の呼び出しで行う（リトライはしない）
- 受け入れ条件 2 の決定論のチェックは、今ある detect-secrets（コミットの前・CI。`PrivateKeyDetector`・`GitHubTokenDetector`）を使う。新しいテストでは秘密の検査を作り直さず、それが App の鍵の形を見つけることを TC-03 で確かめる。`.gitignore` に `*.pem` を足す — 同じ検査を二重に作らず、入口でも止めるため
- MCP の手順書は改名（`mcp-github-setup.md` → `github-app-setup.md`）して書き直す — 中身が MCP でなくなり、名前が残ると読み手が MCP の手順と誤解するため。参照は `CLAUDE.md:32`・`mcp-usage.md` だけ（全件を grep で確認）
- 総点検の一覧は `docs/runbooks/harness-audit.md` に新しく置き、`CLAUDE.md` の参照先に 1 行足す — 常設の置き場所が無く、I222 の点検もここを見られるようにするため（CLAUDE.md にルールは増やさない）
- 名義と鍵の観点は計画レビュー役（`plan-reviewer.md`）の P5 に置き、計画の書き方には足さない — 必ず流れるレビュー役に 1 か所置けば足り、写しを増やさない（retro の改善案の絞り方）。決定論にはしない（§4-13）
- `branch-protection-setup.md` の「bot」の一般名は残し、名前の 1 行と、今の bot が App だという 1 行だけを直す — 意味は変わらず、確認 4・6 の手順も App で同じに動くため
- 新しい決定論テストは G1〜G5 だけ — 壊れても気づきにくく、壊れると本物の書き込みが起きる所（鍵の取り違え・指定の付け忘れ）。手順書の文言・`.mcp.json` の中身（test_i187 ②の直しを除く）・総点検の一覧はレビューで見る
- この端末の入れ直しと `~/.bashrc` の行の削除は Claude が行う（リポジトリの外の手元の設定。取り消しは前の版の写し・PAT の作り直しでできる）。PAT の失効だけは持ち主のアカウントの画面でしかできないので close でお願いする
- 台帳の残りの一覧:
  - 一覧 docs/runbooks/onboarding.md I211-F7・A3・A1: 残す — python の版を上げる手順の話で、このイシューと関係がない
  - 一覧 docs/runbooks/onboarding.md I220-F4: 残す — 流れ図の話で関係がない（TC-14⑦ が図を固定）
  - 一覧 scripts/claude/check-permission-prompt.sh I200-F7: 残す — `write` の上書き防止の話で、今回触る起動の行と関係がない
  - 一覧 docs/runbooks/plan-writing-rules.md I209-F1: 残す — 表示の反映のテストの話で関係がない
- セキュリティ（秘密情報・認証）:
  - 秘密の鍵ファイルは `~/.config/github-app/`（700・ファイル 600）、受け取った鍵の控えは `~/.cache/github-app/`（700・`umask 077`）だけ。リポジトリ・コマンドの引数・出力・記録に鍵の値を出さない（スクリプトは鍵を標準出力にだけ出し、`gh` の入口が環境変数で渡す）
  - 最小権限: テスト用のセッションは読み取りだけの鍵。App の権限・入れているリポジトリ（このリポジトリだけ）は変えない
  - 入力: 環境変数の上書き（`GH_APP_*`）は同じ利用者の手元の設定で、外から入る値ではない。応答は `python3 -I` の JSON 読み取りだけで、シェルに展開しない
  - OWASP 相当: 該当する Web の入口なし。秘密情報の漏れ（A02）とアクセス制御（A01）を上で扱う
  - 依存の追加なし（`openssl`・`curl`・`python3`・`gh` は既にある）。bandit・npm audit の対象のコード変更なし
  - 高リスクの見立て: 秘密情報の扱いと、テスト用のセッションの書き込みの守りを変えるので、計画レビュー役の判定に委ねる（design-security-review の対象になりうる）。安全装置（`path_risk_trigger` の集合）には触らないので「止めて聞く条件」2 には当たらない
- P3 影響なし（DB の変更なし）
- P5（運用）: §11
- P8（コスト）: §12
- P6 影響なし（UI・性能に関わる変更なし）
- P9 影響なし（個人情報・テナントデータを扱わない）
- 要件・基本設計・UI/UX の仮定: なし（止まらない）

Danger Ops（有無/手順/ロールバック）:
- 無（データ削除・破壊的マイグレーション・強制 push なし。リポジトリの外の手元の設定の入れ替えは前の版を写してから行う）

## 11. 運用設計
- 外部 API: `POST https://api.github.com/app/installations/{id}/access_tokens`（`gh` を呼ぶたび。控えが有効なら呼ばない＝1 時間に 1 回ほど。読み取りだけの鍵も別に 1 時間に 1 回ほど）
- タイムアウト: `curl --max-time 20`。失敗したら `gh-app-token: 鍵を受け取れませんでした` を出して exit 1（`gh`・push はそのまま失敗する）。リトライはしない（次の呼び出しで取り直す）
- ログ: 鍵の値は出さない。失敗の理由は curl の stderr（HTTP の状態）だけ
- 切り戻し: §7

## 12. コスト・保守見積もり
- 費用: なし（GitHub App は無料。鍵の受け取りの API は App の利用の制限〔1 時間あたりの回数〕の中で 1 時間に 2 回ほど）
- 手作業: 新しい端末で鍵ファイルを置き `install.sh` を流すだけ。鍵ファイルの期限は無い（漏れたときに作り直す）。リポジトリの版を変えたら `install.sh` を流し直す（`--check` でずれが分かる）
- 属人化: 手順書と `install.sh` にまとめるので、今のリポジトリの外の手作業より減る

## 計画変更記録
- 計画レビュー（20261105_1259・OK・高リスク No）の Warning 4 件への対応: M-05・M-08 ① を複合のコマンドでなく単体の `grep` にした（W1）／手で書く `claude -p` が入口を通らないと止まらない残りの範囲は、R3 のとおり対象外とし、close の報告に書く（W2）／4-1 は実装で今のファイルの全文をもとにリポジトリへ入れる（W3・計画どおり）／M-03 ② の `--permission-prompts none` は `check-permission-prompt.sh:73`・`review-process-lib.sh` が今使っていて動く（I187・I197 の実走）ので実在は確かめ済みとし、M-03 の前に `claude -p --help` も見る（W4）。計画レビューのやり直し: 不要（findings への対応の追記だけで、方式・範囲・受け入れ条件は変えない）
- 計画変更記録 2（implement・2026-11-05）: 4-14 後半の「`~/.bashrc` の PAT の行を Claude が消す」は、自動の判定（auto mode）に「取り消せない手元の削除」として止められた。回避はせず、PAT の失効と一緒に close でユーザーにお願いする（手順は `github-app-setup.md`「9.」）。受け入れ条件 7 は `.mcp.json` と手順書が対象で、この行の削除を含まないので、受け入れ条件は変わらない。手動テスト M-08 は「ユーザーへのお願いに回したことの記録」に変え、合否には使わない。計画レビューのやり直し: 不要（リポジトリの外の手作業を 1 つお願いに回すだけで、方式・範囲・受け入れ条件は変えない）
- 計画変更記録 3（implement の `/simplify`・直す深さの観点・2026-11-05）: 調査結果の「テスト用のセッションを起こす所」に漏れがあった。`claude -p` を起こす所は、ほかに `scripts/claude/code-review.sh:153`（組み込みの /code-review・plan モード）・`scripts/claude/plan-issue-review.sh:131`・`scripts/claude/issue-review.sh:40`・`scripts/claude/fix-review-lib.sh:81`（どれもレビュー役）の 4 か所あり、そこから起きるセッションには書き込みの鍵が渡る（`grep -rnE 'CLAUDE_BIN:-claude\}"? -p|claude -p ' scripts/claude --include=*.sh` で確認）。採った方法: 4 か所にも `GH_APP_READONLY=1` を付け（4-5）、「`scripts/claude/*.sh` の `claude -p` の呼び出しの行はすべて `GH_APP_READONLY=1` を持つ（`test-session.sh` のように `export GH_APP_READONLY=1` するファイルを除く）」を静的なテスト G6 で守る（4-6。起動の所が増えても付け忘れを CI で止める）。PR へのレビューのコメントは、これらのスクリプト自身（`claude -p` の外）が書くので書き込みの鍵のまま動く。見送り: すべての起動を `test-session.sh` に通す案 — 各スクリプトの起動の形（`timeout … claude -p --agent`・`claude -p --permission-mode plan`）を既存のテスト（`test_i193_official_flow.sh` R7・S8・`test_i197_adversarial_process.sh` S1）が見ていて、通し方を変えると守りの検査を作り直すことになる。付け忘れは G6 で止まるので、置き場所を 1 つにしなくても漏れない。あわせて `/simplify` の簡素化・無駄の指摘を反映する（4-1・4-2・4-3・4-6 の中の整理だけ）。計画レビューのやり直し: 要（実装対象のファイルと決定論テストを足し、範囲を変える）

## レビュー結果
- [20261105_1259 判定: ✅ 完了](../../reviews/I223_plan_review_20261105_1259.md)
