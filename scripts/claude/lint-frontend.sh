#!/usr/bin/env bash
# pre-commit の ESLint のフック（I468）。ワークツリーではホストに node_modules が無い（docs/runbooks/worktree.md §5）ので、
# Docker が使えればコンテナの中で、使えなければホストの eslint で流す。どれもできなければ止める（黙って通さない）。
# 呼び出し元: .pre-commit-config.yaml の eslint のフック。引数は読まない。
# 終了コード: lint の終了コード・流せないとき 1。説明: docs/runbooks/pre-commit.md「ESLint のフックの流し方」
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

# デーモンに届くか（docker info より軽い。デーモンが止まっていれば 0 以外）
if command -v docker >/dev/null 2>&1 && docker version --format '{{.Server.Version}}' >/dev/null 2>&1; then
  # パイプにしない（pipefail の下で grep -q の早い終了が前のコマンドを落としうる・I210）。1 行ちょうどの一致で見る
  running=$(docker compose ps --status running --services 2>/dev/null || true)
  if grep -qx frontend <<<"$running"; then
    echo "ESLint: 起動中の frontend コンテナで流します" >&2
    exec docker compose exec -T frontend npm run lint
  fi
  echo "ESLint: 使い捨ての frontend コンテナで流します（初回はイメージの準備に数分かかることがあります）" >&2
  # --entrypoint npm: frontend/Dockerfile.dev の入口は引数を無視して npm start するため
  # --build: package*.json が変わったら依存を作り直す（変わっていなければ層の再利用で数秒）
  exec docker compose run --rm --no-deps -T --build --entrypoint npm frontend run lint
fi

if [ -x frontend/node_modules/.bin/eslint ]; then
  echo "ESLint: Docker が使えないので、ホストの frontend/node_modules で流します" >&2
  cd frontend && exec npm run lint
fi

echo "⛔ ESLint を流せません: Docker が使えず（docker が無い・Docker が起動していない）、ホストにも frontend/node_modules/.bin/eslint がありません" >&2
echo "   対処: Docker（Docker Desktop）を起動してから、もう一度コミットしてください（docs/runbooks/pre-commit.md「ESLint のフックの流し方」）" >&2
exit 1  # 流せない（黙って通さない）
