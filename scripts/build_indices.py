#!/usr/bin/env python3
"""
build_indices.py — docs/work/ をスキャンして索引を再生成する。

Usage:
    python3 scripts/build_indices.py [--dry-run]
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = ROOT / "docs" / "work"
INDICES_DIR = ROOT / "docs" / "indices"
WORK_INDEX = INDICES_DIR / "WORK_INDEX.md"
REVIEW_INDEX = INDICES_DIR / "REVIEW_INDEX.md"
REVIEW_SEQ = INDICES_DIR / "review_seq.json"


def parse_frontmatter(text: str) -> dict:
    """YAML-like front matter を簡易パース（--- ブロック）。"""
    result = {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return result
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip().strip('"')
    return result


def collect_work_items() -> list[dict]:
    items = []
    for state in ("open", "closed"):
        state_dir = WORK_DIR / state
        if not state_dir.exists():
            continue
        for issue_dir in sorted(state_dir.iterdir()):
            if not issue_dir.is_dir() or issue_dir.name.startswith("."):
                continue
            issue_file = issue_dir / "00_issue.md"
            plan_file = next(issue_dir.glob("10_plan*.md"), None)
            title = "-"
            branch = "-"
            if issue_file.exists():
                fm = parse_frontmatter(issue_file.read_text(encoding="utf-8"))
                title = fm.get("title", "-").strip('"')
                branch = fm.get("branch", "-")
            updated = "-"
            if plan_file:
                fm = parse_frontmatter(plan_file.read_text(encoding="utf-8"))
                updated = fm.get("created_at", "-")
            items.append({
                "issue": issue_dir.name,
                "title": title,
                "state": state,
                "branch": branch,
                "plan": plan_file.name if plan_file else "-",
                "updated": updated,
            })
    return items


def collect_reviews() -> list[dict]:
    reviews = []
    for state in ("open", "closed"):
        state_dir = WORK_DIR / state
        if not state_dir.exists():
            continue
        for issue_dir in sorted(state_dir.iterdir()):
            if not issue_dir.is_dir() or issue_dir.name.startswith("."):
                continue
            for review_file in sorted(issue_dir.glob("30_review_*.md")):
                fm = parse_frontmatter(review_file.read_text(encoding="utf-8"))
                reviews.append({
                    "rid": fm.get("rid", "-"),
                    "issue": issue_dir.name,
                    "plan_ref": fm.get("plan_ref", "-"),
                    "state": fm.get("status", "-"),
                    "date": fm.get("created_at", "-"),
                })
    return reviews


def compute_next_rid(reviews: list[dict]) -> int:
    """現在の review ファイルから最大 RID + 1 を返す。"""
    max_n = 0
    for r in reviews:
        m = re.match(r"R(\d+)", r["rid"])
        if m:
            max_n = max(max_n, int(m.group(1)))
    return max_n + 1


def build_work_index(items: list[dict]) -> str:
    header = (
        "# WORK_INDEX\n\n"
        "> 自動生成ファイル — `scripts/build_indices.py` で更新される。手動編集禁止。\n\n"
        "| Issue | Title | State | Branch | Plan | Updated |\n"
        "|-------|-------|-------|--------|------|---------|\n"
    )
    rows = ""
    for it in items:
        rows += f"| #{it['issue']} | {it['title']} | {it['state']} | `{it['branch']}` | {it['plan']} | {it['updated']} |\n"
    return header + rows


def build_review_index(reviews: list[dict]) -> str:
    header = (
        "# REVIEW_INDEX\n\n"
        "> 自動生成ファイル — `scripts/build_indices.py` で更新される。手動編集禁止。\n\n"
        "| RID | Issue | Plan Ref | State | Date |\n"
        "|-----|-------|----------|-------|------|\n"
    )
    rows = ""
    for r in reviews:
        rows += f"| {r['rid']} | #{r['issue']} | {r['plan_ref']} | {r['state']} | {r['date']} |\n"
    return header + rows


def main():
    parser = argparse.ArgumentParser(description="Rebuild docs/indices/ from docs/work/")
    parser.add_argument("--dry-run", action="store_true", help="Print output without writing files")
    args = parser.parse_args()

    if not WORK_DIR.exists():
        print(f"ERROR: {WORK_DIR} does not exist.", file=sys.stderr)
        sys.exit(1)

    items = collect_work_items()
    reviews = collect_reviews()
    next_rid = compute_next_rid(reviews)

    work_index_content = build_work_index(items)
    review_index_content = build_review_index(reviews)
    seq_content = json.dumps({"next": next_rid}, indent=2) + "\n"

    if args.dry_run:
        print("=== WORK_INDEX.md ===")
        print(work_index_content)
        print("=== REVIEW_INDEX.md ===")
        print(review_index_content)
        print("=== review_seq.json ===")
        print(seq_content)
        print("(dry-run: no files written)")
        return

    INDICES_DIR.mkdir(parents=True, exist_ok=True)
    WORK_INDEX.write_text(work_index_content, encoding="utf-8")
    REVIEW_INDEX.write_text(review_index_content, encoding="utf-8")
    REVIEW_SEQ.write_text(seq_content, encoding="utf-8")

    print(f"OK: {WORK_INDEX} ({len(items)} items)")
    print(f"OK: {REVIEW_INDEX} ({len(reviews)} reviews)")
    print(f"OK: {REVIEW_SEQ} (next RID = R{next_rid:05d})")


if __name__ == "__main__":
    main()
