#!/usr/bin/env bash
set -euo pipefail

# check-memo-body-paths.sh — P3 決定論ゲート（I068）
# 設計確認メモに登場するファイルパスが、本文の構造化セクション（実装対象/影響範囲）に
# 反映されているか（memo ⊆ body）を機械判定する。
# 呼び出し元: .claude/skills/grill-me/SKILL.md（本文整合の直後）。backstop: plan-reviewer.md。
# 終了コード: 0=整合 / 1=不一致あり / 2=実行不可（引数不正・イシューファイル未検出）。

ISSUE="${1:-}"

# 引数検証（パストラバーサル防止）: ^I[0-9]{3}$ のみ受け付け、不正ならパスを構築せず終了する。
if ! [[ "$ISSUE" =~ ^I[0-9]{3}$ ]]; then
  echo "⚠️ 不正なイシュー番号です（期待形式: I###）: '${ISSUE}'" >&2
  exit 2
fi

# git リポジトリ外なら git のエラーコード（128 等）でなく exit 2 に正規化する（呼び出し元の 0/1/2 規約を守る）。
if ! REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  echo "⚠️ git リポジトリ外では実行できません（exit 2・skip 扱い）" >&2
  exit 2
fi
cd "$REPO_ROOT" || exit 2

# イシューファイル探索（open → closed）。未検出は非ブロックの実行不可（exit 2）。
ISSUE_FILE=""
for f in "docs/issues/open/${ISSUE}.md" "docs/issues/closed/${ISSUE}.md"; do
  if [ -f "$f" ]; then ISSUE_FILE="$f"; break; fi
done
if [ -z "$ISSUE_FILE" ]; then
  echo "⚠️ イシューファイルが見つかりません: ${ISSUE}.md" >&2
  exit 2
fi

# セクション抽出: "## <見出し>" 行の次行から、次の "## " 見出し直前までを出力する。
section() {
  awk -v h="$1" '
    $0 == h { inblock = 1; next }
    /^## /  { inblock = 0 }
    inblock { print }
  ' "$ISSUE_FILE"
}

# バックティック囲みのパス様トークン（/ と拡張子を含む）を抽出・正規化する。
# 散文中の誤検出を避けるため、バックティック囲みかつ full-path 形のみを対象とする。
extract_paths() {
  # shellcheck disable=SC2016  # バックティックは正規表現リテラル（コマンド置換ではない）
  grep -oE '`[^`]+`' \
    | tr -d '`' \
    | grep -E '/.+\.[A-Za-z0-9]+$' \
    | sort -u
}

# メモ集合（プレースホルダ行 未特定/未定 を除外）。空集合でも非エラーで継続する。
memo_paths="$(section '## 設計確認メモ（/grill-me）' | grep -vE '未特定|未定' | extract_paths || true)"
# メモに検証対象パスが無ければ早期に整合扱いで終了（空文字を comm に渡さない・意図を明確化）。
if [ -z "$memo_paths" ]; then
  echo "✅ 設計確認メモにファイルパスの記載なし（検証対象なし）"
  exit 0
fi
# 本文集合（実装対象 ＋ 影響範囲）。
body_paths="$( { section '## 実装対象（既知のもの）'; section '## 影響範囲（想定）'; } | extract_paths || true)"

# memo ⊆ body 判定: メモにあって本文に無いパス（comm は sort 済み入力前提・extract_paths で sort 済み）。
missing="$(comm -23 <(printf '%s\n' "$memo_paths") <(printf '%s\n' "$body_paths") | sed '/^$/d' || true)"

if [ -n "$missing" ]; then
  echo "⚠️ 設計確認メモに登場するが本文（実装対象/影響範囲）に無いパス:"
  printf '%s\n' "$missing" | sed 's/^/  - /'
  echo "→ 各パスを本文に追記するか、意図的除外なら本文にその旨を明記して整合させてください。"
  exit 1
fi

echo "✅ memo ⊆ body 整合（設計確認メモのパスは全て本文に反映済み）"
exit 0
