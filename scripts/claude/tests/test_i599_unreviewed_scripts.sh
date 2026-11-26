#!/usr/bin/env bash
# I599（第 2 版・plan_I599.md 4-1〜4-5・auto_test TC-01〜TC-17）: scripts/claude/ のスクリプトは既定でサンドボックスの中。
#   外に出すのは起動役（python3 .claude/hooks/unreviewed.py run）だけで、起動役は分かれた時点の写しの一覧のスクリプトを動かし、
#   入口か部品・レビュー役の定義を変えたとき・写しを作れないときは 75 で止まる（I615）。見張りは単体の形を起動役の形に
#   付け替え、起動役の形（単体・最上位の cwd）と test-session.sh の引数を確かめ、git の更新を中で動く形で流すのを止める（I615）。フックは分かれた時点の写しで動く。
#   一時フォルダに小さなリポジトリ（scripts/claude/ の写しと .claude/hooks/ の本物の写し）を作り、origin/develop に当たる
#   参照を置いて流す。本物のリポジトリには何も書かない。本体の確かめは同じフォルダの i599_cases.py
#   FG: 判定・起動役・見張りの写しを壊すと、対応する確かめが不合格になること
# 実行: bash scripts/claude/tests/test_i599_unreviewed_scripts.sh
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 -B "$REPO_ROOT/scripts/claude/tests/i599_cases.py" "$REPO_ROOT" "$TMP"
