#!/usr/bin/env bash
# テスト用のセッション（claude -p）の入口（I223）。GitHub へは読み取りだけの App の鍵を渡し、書き込みを GitHub の側で拒否させる
# （gh の入口と git の credential helper が GH_APP_READONLY を引き継ぐ。docs/runbooks/github-app-setup.md）。
# 使い方: bash scripts/claude/test-session.sh <claude -p に渡す引数…>
# MCP は --mcp-config で渡したものだけ（--strict-mcp-config・I225。手元の設定の MCP が読み取りだけの鍵を迂回しないように）
# テスト用: CLAUDE_BIN=<コマンド> で起動する claude を差し替えられる
export GH_APP_READONLY=1
exec "${CLAUDE_BIN:-claude}" -p --strict-mcp-config "$@"
