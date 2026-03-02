#!/usr/bin/env python3
"""
extract_atomic_lines.py
原本 CLAUDE_original.md から「検証対象の意味のある行」を抽出する。
出力: docs/migration/reports/atomic_lines.txt
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/migration/CLAUDE_original.md"
OUTPUT = ROOT / "docs/migration/reports/atomic_lines.txt"

# スキップする行のパターン
SKIP_PATTERNS = [
    re.compile(r"^\s*$"),            # 空行
    re.compile(r"^#+\s"),            # 見出し行
    re.compile(r"^```"),             # コードフェンス
    re.compile(r"^\s*[-*]\s*$"),     # 箇条書きのみの空マーカー
    re.compile(r"^---+$"),           # 区切り線
    re.compile(r"^\|[-| ]+\|$"),     # テーブル区切り行
]

def is_meaningful(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    for pat in SKIP_PATTERNS:
        if pat.match(stripped):
            return False
    # 短すぎる行（3文字以下）はスキップ
    if len(stripped) <= 3:
        return False
    return True

def main():
    if not SOURCE.exists():
        print(f"ERROR: {SOURCE} が見つかりません", file=sys.stderr)
        sys.exit(1)

    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    atomic = []
    in_code_block = False

    for line in lines:
        stripped = line.strip()
        # コードブロック内の行はスキップ
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if is_meaningful(line):
            atomic.append(stripped)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(atomic) + "\n", encoding="utf-8")
    print(f"OK: {len(atomic)} 行を抽出 → {OUTPUT}")
    return len(atomic)

if __name__ == "__main__":
    main()
