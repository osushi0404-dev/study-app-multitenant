#!/usr/bin/env python3
"""SessionStart hook: セッション開始時に作業の状態を Claude に渡す（I185 P5）。

並行ワークツリーで「マージ済みか」「最新のイシュー番号」の認識が古くなるのを防ぐ。
stdout はそのまま Claude の文脈に入る（hooks.md）。

GitHub のタイトルの自由文は出さない。公開リポジトリのイシューは誰でも作れ、
そのタイトルが毎セッションの文脈に入ると指示の書き込みの入口になるため
（I185 security-review Medium）。出すのは番号・日付・タイトル先頭の I### だけ。
どのコマンドが失敗・タイムアウトしても exit 0（セッションの開始を止めない）。
"""
import json
import re
import subprocess
import sys

TIMEOUT_SEC = 5
PR_LIMIT = 5
UNAVAILABLE = "取得できませんでした"
ISSUE_ID = re.compile(r"^(I\d{3})\b")
DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def _run(args: list[str]) -> str | None:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=TIMEOUT_SEC)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def _gh_json(args: list[str]) -> list | None:
    out = _run(["gh", *args])
    if out is None:
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, list) else None


def _number(item: dict) -> str:
    value = item.get("number")
    return f"#{value}" if isinstance(value, int) else "#-"


def _issue_id(item: dict) -> str:
    match = ISSUE_ID.match(str(item.get("title") or ""))
    return match.group(1) if match else "-"


def _date(item: dict) -> str:
    match = DATE.match(str(item.get("mergedAt") or ""))
    return match.group(1) if match else "-"


def format_context(branch: str | None, dirty: int | None,
                   prs: list | None, latest_issue: dict | None) -> str:
    """表示用の文字列を作る。GitHub の値は番号・日付・I### だけに絞る。"""
    lines = ["[sessionstart] 作業の状態（GitHub の値は番号と I### だけを出し、タイトルの文章は出していない）"]
    lines.append(f"branch: {branch or UNAVAILABLE}")
    lines.append(f"未コミットの変更: {UNAVAILABLE if dirty is None else f'{dirty} 件'}")
    if prs is None:
        lines.append(f"直近にマージされた PR（develop 宛て）: {UNAVAILABLE}")
    else:
        items = [f"{_number(p)} {_issue_id(p)} {_date(p)}" for p in prs[:PR_LIMIT] if isinstance(p, dict)]
        lines.append("直近にマージされた PR（develop 宛て）: " + ("、".join(items) or "なし"))
    if latest_issue is None:
        lines.append(f"GitHub の最新イシュー: {UNAVAILABLE}")
    else:
        lines.append(f"GitHub の最新イシュー: {_number(latest_issue)} {_issue_id(latest_issue)}")
    return "\n".join(lines)


def collect() -> str:
    branch_out = _run(["git", "branch", "--show-current"])
    branch = None if branch_out is None else (branch_out.strip() or "(detached HEAD)")
    status_out = _run(["git", "status", "--porcelain"])
    dirty = None if status_out is None else len(status_out.splitlines())
    prs = _gh_json(["pr", "list", "--state", "merged", "--base", "develop",
                    "--limit", str(PR_LIMIT), "--json", "number,title,mergedAt"])
    issues = _gh_json(["issue", "list", "--state", "all", "--limit", "1", "--json", "number,title"])
    latest = None if issues is None else (issues[0] if issues and isinstance(issues[0], dict) else {})
    return format_context(branch, dirty, prs, latest)


def main() -> None:
    try:
        print(collect())
    except Exception:  # noqa: BLE001 — セッションの開始は決して止めない
        print(f"[sessionstart] 作業の状態: {UNAVAILABLE}")
    sys.exit(0)


if __name__ == "__main__":
    main()
