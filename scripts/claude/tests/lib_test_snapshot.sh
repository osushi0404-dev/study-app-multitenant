#!/usr/bin/env bash
# lib_test_snapshot.sh — テスト用の「レビュー済みの写し」を作る（I593）。
# 審査の入口は、写し（最上位に .complete・作業ツリーと別の場所）から動いたときだけ「写しの版」と数える
# （scripts/claude/reviewer-agents-lib.sh の reviewer_from_snapshot）。一時リポジトリの中の scripts/claude を直接流すと
# 「作業ツリーの版」になり高リスクに倒れるので、本番と同じく写しから流すテストはこれで写しを作る。
# 使い方: . scripts/claude/tests/lib_test_snapshot.sh; make_test_snapshot <一時リポジトリ> → 写しの最上位を出す（<リポジトリ>.snap）
make_test_snapshot() {
  local repo="$1" snap="$1.snap"
  rm -rf "$snap"
  mkdir -p "$snap/scripts" "$snap/.claude" "$snap/docs/runbooks" || return 1
  cp -R "$repo/scripts/claude" "$snap/scripts/" || return 1
  # 定義と決まりは一時リポジトリにあればそれを、無ければこのリポジトリのものを写す（本番の写しは BASE の両方を持つ）
  local top p s; top="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)" || return 1
  for p in .claude/agents docs/runbooks/review-rules.md; do
    s="$repo"; [ -e "$repo/$p" ] || s="$top"
    cp -R "$s/$p" "$snap/$p" || return 1
  done
  touch "$snap/.complete"
  printf '%s\n' "$snap"
}
