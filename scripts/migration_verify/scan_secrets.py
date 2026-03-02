#!/usr/bin/env python3
"""
scan_secrets.py
移植先ファイルに機密情報（APIキー、トークン等）が含まれていないか確認する。
出力: docs/migration/reports/secrets_scan_report.txt
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs/migration/reports/secrets_scan_report.txt"

SEARCH_TARGETS = [
    ROOT / "docs/runbooks",
    ROOT / ".claude/skills",
    ROOT / "CLAUDE.md",
    ROOT / "docs/migration",
]

# 機密情報を示す可能性があるパターン
SECRET_PATTERNS = [
    (re.compile(r"(?i)(api[_-]?key|apikey)\s*[=:]\s*['\"]?[A-Za-z0-9+/]{20,}"), "API Key"),
    (re.compile(r"(?i)(secret|password|passwd|pwd)\s*[=:]\s*['\"]?[A-Za-z0-9+/=]{8,}"), "Secret/Password"),
    (re.compile(r"(?i)(token|bearer)\s*[=:]\s*['\"]?[A-Za-z0-9._\-]{20,}"), "Token"),
    (re.compile(r"(?i)ghp_[A-Za-z0-9]{36}"), "GitHub PAT"),
    (re.compile(r"(?i)sk-[A-Za-z0-9]{32,}"), "OpenAI Key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key"),
]

# テンプレートや例示として許容するキーワード
ALLOW_KEYWORDS = [
    "example", "sample", "test@example", "testpass", "YOUR_", "your_",
    "[トークン]", "取得したトークン", "Bearer $TOKEN",
]

def is_allowlisted(line: str) -> bool:
    return any(kw in line for kw in ALLOW_KEYWORDS)

def main():
    findings = []

    for target in SEARCH_TARGETS:
        files = [target] if target.is_file() else sorted(target.rglob("*.md")) + sorted(target.rglob("*.yml"))
        for f in files:
            if not f.is_file():
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if is_allowlisted(line):
                    continue
                for pattern, label in SECRET_PATTERNS:
                    if pattern.search(line):
                        findings.append({
                            "file": str(f.relative_to(ROOT)),
                            "line": i,
                            "label": label,
                            "content": line.strip()[:100],
                        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    if findings:
        lines = [f"機密情報の可能性: {len(findings)} 件\n"]
        for item in findings:
            lines.append(f"[{item['label']}] {item['file']}:{item['line']}")
            lines.append(f"  {item['content']}")
        OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"⚠️  機密情報の可能性: {len(findings)} 件")
        for item in findings:
            print(f"  [{item['label']}] {item['file']}:{item['line']}")
    else:
        OUTPUT.write_text("機密情報スキャン: 問題なし\n", encoding="utf-8")
        print("機密情報スキャン: 問題なし ✅")

    return len(findings)

if __name__ == "__main__":
    count = main()
    sys.exit(0 if count == 0 else 1)
