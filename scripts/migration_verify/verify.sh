#!/usr/bin/env bash
# verify.sh — CLAUDE.md 完全移行の自動検証スクリプト
# 使用法: bash scripts/migration_verify/verify.sh
# 出力:   docs/migration/reports/summary.md

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

REPORTS_DIR="docs/migration/reports"
mkdir -p "$REPORTS_DIR"

SUMMARY="$REPORTS_DIR/summary.md"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

echo "=== CLAUDE.md 移行検証 開始 ($TIMESTAMP) ==="
echo ""

# --- ステップ0: 前提ファイル確認 ---
echo "[0/5] 前提ファイル確認..."
PREREQS=(
    "docs/migration/CLAUDE_original.md"
    "docs/migration/migration_map.yml"
    "docs/migration/MANIFEST.md"
)
for f in "${PREREQS[@]}"; do
    if [ ! -f "$f" ]; then
        echo "ERROR: 前提ファイルが見つかりません: $f" >&2
        exit 1
    fi
done
echo "  ✅ 前提ファイル OK"

# --- ステップ1: atomic_lines 抽出 ---
echo ""
echo "[1/5] atomic_lines 抽出..."
python3 scripts/migration_verify/extract_atomic_lines.py
ATOMIC_COUNT=$(wc -l < docs/migration/reports/atomic_lines.txt || echo 0)

# --- ステップ2: 移植先との照合 ---
echo ""
echo "[2/5] 移植先との照合..."
set +e
python3 scripts/migration_verify/match_atomic_lines.py
set -e
UNMATCHED=$(python3 -c "
import json
d = json.load(open('docs/migration/reports/migration_report.json'))
print(d['unmatched_count'])
")

# --- ステップ3: 参照切れチェック ---
echo ""
echo "[3/5] 参照切れチェック..."
set +e
python3 scripts/migration_verify/check_references.py
set -e
BROKEN=$(grep -c "^\[BROKEN\]" docs/migration/reports/broken_references.txt 2>/dev/null) || BROKEN=0

# --- ステップ4: Skill lint ---
echo ""
echo "[4/5] Skill lint..."
set +e
python3 scripts/migration_verify/lint_skills.py
set -e
LINT_ERRORS=$(python3 -c "
import json
d = json.load(open('docs/migration/reports/skills_lint_report.json'))
print(d['errors'])
")

# --- ステップ5: シークレットスキャン ---
echo ""
echo "[5/5] シークレットスキャン..."
set +e
python3 scripts/migration_verify/scan_secrets.py
set -e
SECRETS=$(grep -c "^\[" docs/migration/reports/secrets_scan_report.txt 2>/dev/null) || SECRETS=0

# --- 判定 ---
echo ""
echo "=== 結果サマリー ==="
OVERALL="OK"
if [ "$UNMATCHED" -gt 0 ] || [ "$BROKEN" -gt 0 ]; then
    OVERALL="NG"
fi

# --- summary.md 生成 ---
cat > "$SUMMARY" << EOF
# 移行検証レポート

- **実行日時**: $TIMESTAMP
- **総合判定**: $OVERALL

## チェック結果

| チェック項目 | 件数 | 判定 |
|-------------|------|------|
| atomic_lines 総数 | $ATOMIC_COUNT 行 | — |
| 未一致行（移植漏れ） | $UNMATCHED 件 | $([ "$UNMATCHED" -eq 0 ] && echo "✅ OK" || echo "❌ NG") |
| 参照切れ | $BROKEN 件 | $([ "$BROKEN" -eq 0 ] && echo "✅ OK" || echo "❌ NG") |
| Skill lint エラー | $LINT_ERRORS 件 | $([ "$LINT_ERRORS" -eq 0 ] && echo "✅ OK" || echo "⚠️  WARNING") |
| シークレット検出 | $SECRETS 件 | $([ "$SECRETS" -eq 0 ] && echo "✅ OK" || echo "⚠️  WARNING") |

## 詳細レポート

- 未一致一覧: \`docs/migration/reports/migration_report.json\`
- 原本行リスト: \`docs/migration/reports/atomic_lines.txt\`
- 参照切れ: \`docs/migration/reports/broken_references.txt\`
- Skill lint: \`docs/migration/reports/skills_lint_report.json\`
- シークレット: \`docs/migration/reports/secrets_scan_report.txt\`

## 再実行コマンド

\`\`\`bash
bash scripts/migration_verify/verify.sh
\`\`\`

## 次のアクション

EOF

if [ "$OVERALL" = "OK" ]; then
    cat >> "$SUMMARY" << EOF
✅ 全チェック通過。PR4をマージしてください。
EOF
else
    cat >> "$SUMMARY" << EOF
❌ NG のため、このPRはマージしないでください。
PR3（chore/claude-migration-content）へ戻り、以下を修正してください:

EOF
    if [ "$UNMATCHED" -gt 0 ]; then
        echo "- 移植漏れ $UNMATCHED 件: \`docs/migration/reports/migration_report.json\` の \`unmatched\` を参照" >> "$SUMMARY"
    fi
    if [ "$BROKEN" -gt 0 ]; then
        echo "- 参照切れ $BROKEN 件: \`docs/migration/reports/broken_references.txt\` を参照" >> "$SUMMARY"
    fi
fi

echo ""
echo "総合判定: $OVERALL"
echo "  未一致行: $UNMATCHED 件"
echo "  参照切れ: $BROKEN 件"
echo "  Skill lint エラー: $LINT_ERRORS 件"
echo "  シークレット: $SECRETS 件"
echo ""
echo "サマリー → $SUMMARY"

if [ "$OVERALL" = "NG" ]; then
    exit 1
fi
