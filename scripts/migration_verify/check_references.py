#!/usr/bin/env python3
"""
check_references.py
runbooks / skills / CLAUDE.md 内のファイル参照パスが実在するか確認する。
コードブロック内のシェル変数・globパターンは除外する。
出力: docs/migration/reports/broken_references.txt
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs/migration/reports/broken_references.txt"

SEARCH_TARGETS = [
    ROOT / "docs/runbooks",
    ROOT / ".claude/skills",
    ROOT / "CLAUDE.md",
]

# ファイルパスとして検出するパターン
PATH_PATTERN = re.compile(
    r"(?:^|[\s`(\[])((docs|\.claude|scripts|rules|\.github)/[^\s`)\]\"'\n]+\.(?:md|py|sh|yml|yaml|json))"
)

def is_template_path(path: str) -> bool:
    """シェル変数・globパターン・テンプレートパターンはスキップ"""
    skip_patterns = [
        "$", "{", "}", "*", "?",      # シェル変数・glob
        "XXX", "YYY", "IXXX", "IYYY", # テンプレートプレースホルダー
        "ISSUE_NUM", "REVIEW_NUM", "ARGUMENTS",
        "LAST_NUM", "NEXT_NUM", "PLAN_FILE",
    ]
    return any(s in path for s in skip_patterns)

def strip_code_blocks(text: str) -> str:
    """コードブロック内の内容を削除して参照チェックの誤検知を防ぐ"""
    # ``` ... ``` ブロックを削除
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # インラインコード `...` を削除
    text = re.sub(r"`[^`\n]+`", "", text)
    return text

def collect_files():
    files = []
    for target in SEARCH_TARGETS:
        if target.is_file():
            files.append(target)
        elif target.is_dir():
            files.extend(sorted(target.rglob("*.md")))
    return files

def main():
    broken = []
    checked = set()

    for src_file in collect_files():
        raw_text = src_file.read_text(encoding="utf-8")
        # コードブロックを除去してから参照を検出
        text = strip_code_blocks(raw_text)

        for match in PATH_PATTERN.finditer(text):
            ref_path = match.group(1)
            if ref_path in checked:
                continue
            checked.add(ref_path)

            # テンプレート・変数・globパターンはスキップ
            if is_template_path(ref_path):
                continue

            full = ROOT / ref_path
            if not full.exists():
                broken.append({
                    "source": str(src_file.relative_to(ROOT)),
                    "reference": ref_path,
                })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    if broken:
        lines = []
        for item in broken:
            lines.append(f"[BROKEN] {item['reference']}")
            lines.append(f"         referenced in: {item['source']}")
        OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"参照切れ: {len(broken)} 件")
        for item in broken:
            print(f"  {item['reference']}  (in {item['source']})")
    else:
        OUTPUT.write_text("参照切れ: 0 件\n", encoding="utf-8")
        print("参照切れ: 0 件 ✅")

    return len(broken)

if __name__ == "__main__":
    count = main()
    sys.exit(0 if count == 0 else 1)
