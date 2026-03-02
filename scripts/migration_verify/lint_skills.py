#!/usr/bin/env python3
"""
lint_skills.py
.claude/skills/**/SKILL.md のフロントマターと必須フィールドを検証する。
出力: docs/migration/reports/skills_lint_report.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / ".claude/skills"
OUTPUT = ROOT / "docs/migration/reports/skills_lint_report.json"

REQUIRED_FIELDS = ["name", "description", "allowed-tools"]

FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

def parse_frontmatter(text: str) -> dict:
    m = FRONTMATTER_PATTERN.match(text)
    if not m:
        return {}
    result = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result

def main():
    results = []
    errors = 0

    for skill_file in sorted(SKILLS_DIR.rglob("SKILL.md")):
        text = skill_file.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        missing = [f for f in REQUIRED_FIELDS if f not in fm]
        has_body = len(text.split("---", 2)) >= 3 and text.split("---", 2)[2].strip()

        entry = {
            "file": str(skill_file.relative_to(ROOT)),
            "frontmatter": fm,
            "missing_fields": missing,
            "has_body": has_body,
            "ok": len(missing) == 0 and has_body,
        }
        results.append(entry)
        if not entry["ok"]:
            errors += 1

    report = {"total": len(results), "errors": errors, "skills": results}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for entry in results:
        status = "✅" if entry["ok"] else "❌"
        print(f"{status} {entry['file']}")
        if entry["missing_fields"]:
            print(f"   欠落フィールド: {entry['missing_fields']}")
        if not entry["has_body"]:
            print(f"   本文が空です")

    print(f"\nスキルファイル数: {len(results)}, エラー: {errors}")
    return errors

if __name__ == "__main__":
    count = main()
    sys.exit(0 if count == 0 else 1)
