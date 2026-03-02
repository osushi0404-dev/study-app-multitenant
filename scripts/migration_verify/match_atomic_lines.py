#!/usr/bin/env python3
"""
match_atomic_lines.py
atomic_lines.txt の各行が移植先ファイルに存在するか確認する。
出力: docs/migration/reports/migration_report.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ATOMIC_LINES_FILE = ROOT / "docs/migration/reports/atomic_lines.txt"
OUTPUT = ROOT / "docs/migration/reports/migration_report.json"

# 移植先ファイルの検索対象
SEARCH_DIRS = [
    ROOT / "docs/runbooks",
    ROOT / ".claude/skills",
    ROOT / "CLAUDE.md",
]

def collect_destination_text() -> str:
    """移植先ファイルの全テキストを結合して返す"""
    parts = []
    for target in SEARCH_DIRS:
        if target.is_file():
            parts.append(target.read_text(encoding="utf-8"))
        elif target.is_dir():
            for md in sorted(target.rglob("*.md")):
                parts.append(md.read_text(encoding="utf-8"))
    return "\n".join(parts)

def main():
    if not ATOMIC_LINES_FILE.exists():
        print(f"ERROR: {ATOMIC_LINES_FILE} が見つかりません。先に extract_atomic_lines.py を実行してください", file=sys.stderr)
        sys.exit(1)

    atomic_lines = [
        line.strip()
        for line in ATOMIC_LINES_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    dest_text = collect_destination_text()

    matched = []
    unmatched = []

    for line in atomic_lines:
        if line in dest_text:
            matched.append(line)
        else:
            unmatched.append(line)

    report = {
        "total": len(atomic_lines),
        "matched": len(matched),
        "unmatched_count": len(unmatched),
        "unmatched": unmatched,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"総行数: {report['total']}")
    print(f"一致:   {report['matched']}")
    print(f"未一致: {report['unmatched_count']}")

    if unmatched:
        print("\n--- 未一致行（最大20件） ---")
        for line in unmatched[:20]:
            print(f"  {line}")
        if len(unmatched) > 20:
            print(f"  ...他 {len(unmatched) - 20} 件")
        print(f"\n詳細: {OUTPUT}")

    return report['unmatched_count']

if __name__ == "__main__":
    count = main()
    sys.exit(0 if count == 0 else 1)
