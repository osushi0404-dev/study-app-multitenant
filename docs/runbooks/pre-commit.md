# pre-commit 運用手順

## 概要

`git commit` のたびに `pre-commit` が秘密情報の検出と基本的なコードの検査を流す。入れ方（初回だけ）は `docs/runbooks/onboarding.md` の手元の準備。

## フック一覧

設定の正は `.pre-commit-config.yaml`（細かい引数はここに写さない）。

| フック | 対象 | 役割 |
|--------|------|------|
| `detect-secrets` | 全体（`package-lock.json` を除く） | 秘密（API キー・パスワード・JWT など）の書き込みを見つける |
| `check-yaml`・`end-of-file-fixer`・`trailing-whitespace`・`check-added-large-files`・`check-merge-conflict` | 全体 | YAML の構文・末尾の改行・行末の空白・大きなファイル・衝突の印 |
| `ruff` | `backend/`（migrations を除く） | Python の lint と import の整理。直せるものは自動で直す |
| `bandit` | `backend/`（migrations・tests を除く） | Python のセキュリティの検査。設定は `backend/.bandit`（`B101` を除き LOW 以上が対象。Low は `# nosec BXXX` で 1 件ずつ抑える） |
| `check-dependabot` | `.github/dependabot.yml` | Dependabot の設定の形の検査 |
| `shellcheck` | `scripts/` | シェルスクリプトの構文・誤り・古い書き方 |
| `eslint` | `frontend/src/` | TypeScript/TSX の lint（警告も止める）。下の「ESLint のフックの流し方」 |

- フックが失敗するとコミットは止まる。全ファイルに流すときは `pre-commit run --all-files`
- マージ・cherry-pick・rebase で作るコミットではフックが動かない（`docs/runbooks/danger-ops.md`「GitHub から復旧できる範囲」）

## ESLint のフックの流し方（I468）

ワークツリーのホストには `frontend/node_modules` が無い（依存は frontend コンテナの中だけ・`docs/runbooks/worktree.md` §5）。そのため ESLint のフックは `scripts/claude/lint-frontend.sh` が、次の順で流せるところで `npm run lint` を流す。

| 順 | 条件 | 流す場所 | かかる時間 |
|---:|------|----------|-----------|
| 1 | Docker が使えて、このワークツリーの frontend コンテナが起動中 | 起動中のコンテナ（`docker compose exec -T frontend npm run lint`） | 数秒 |
| 2 | Docker が使えて、コンテナが起動していない | 使い捨てのコンテナ（`docker compose run --rm --no-deps -T --build --entrypoint npm frontend run lint`。終わったら消える） | 15〜30 秒ほど（初回はイメージの準備で数分） |
| 3 | Docker が使えない（`docker` が無い・Docker が起動していない）で、ホストに `frontend/node_modules/.bin/eslint` がある | ホスト | 数秒 |
| 4 | どれでもない | 流さずにコミットを止める（理由と対処を表示） | — |

- 止まったとき（4）は Docker（Docker Desktop）を起動してからコミットし直す。`SKIP=eslint` で飛ばさない
- Claude の Bash から `pre-commit run eslint …` を直接流すと、サンドボックスの中で動いて Docker に届かず 4 で止まる（`git commit` と `docker` はサンドボックスの外で動くので届く・I468）。ESLint だけ確かめたいときは `git commit` に任せるか、`docker compose exec -T frontend npm run lint` を単体で流す
- 使い捨てのコンテナに `--entrypoint npm` を付けるのは、`frontend/Dockerfile.dev` の入口が引数を無視して開発サーバーを起動するため。`--build` は `package*.json` が変わったときに依存を作り直すため（変わっていなければ層の再利用で数秒）
- 起動中のコンテナ（1）の依存は、起動したときのまま。`package*.json` を変えたら `docker compose up -d --build --renew-anon-volumes` で作り直す（作り直さずに食い違っても、CI の ESLint が止める）
- `--build` のたびに、使われなくなったイメージ（`docker image ls` で `<none>` と出るもの・数 MB）が残る。溜まったら `docker image prune` で消せる（任意。コンテナ・データは消えない）
- CI は別の段（`.github/workflows/ci.yml` の「ESLint」）で流すので、CI の pre-commit の段は `SKIP: eslint` のまま

## detect-secrets の誤検知への対処

テスト用のダミーの値や文書の例が誤検知されたとき:
- **Claude が直すとき**: その行に `# pragma: allowlist secret` を足す（例: `dummy_password = "example_only"  # pragma: allowlist secret`）
- **`.secrets.baseline` で除外するとき**: 人が `detect-secrets audit .secrets.baseline` で対話で処理する（`n` = 誤検知）。`.secrets.baseline` の編集は安全装置で、`.claude/settings.json` の `ask`（承認画面が出る）

## `.secrets.baseline` の作り直し

detect-secrets の版を上げた・検知の種類を変えたときに作り直す。

```bash
detect-secrets scan --force-use-all-plugins --exclude-files "package-lock\.json" > .secrets.baseline
```

- **`--force-use-all-plugins` は必須**。付けないと `JwtTokenDetector` などが baseline から消え、以後 JWT が検出されなくなる（エラーにならないので気づけない）
- 作り直した後は誤検知を上の方法で除く
- `e2e/.auth/` の JWT のファイルは `e2e/.gitignore` で追跡しないので、検査の対象にならない
