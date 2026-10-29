#!/usr/bin/env python3
"""SessionStart hook: セッション開始時に作業の状態を Claude に渡す（I185 P5）。

並行ワークツリーで「マージ済みか」「最新のイシュー番号」の認識が古くなるのを防ぐ。
stdout はそのまま Claude の文脈に入る（hooks.md）。

GitHub のタイトルの自由文は出さない。公開リポジトリのイシューは誰でも作れ、
そのタイトルが毎セッションの文脈に入ると指示の書き込みの入口になるため
（I185 security-review Medium）。出すのは番号・日付・タイトル中の最初の I### だけ。
どのコマンドが失敗・タイムアウトしても exit 0（セッションの開始を止めない）。

I200: 許可の判定の一部は primary（元のフォルダ）の設定で行われるため、primary を origin/develop へ早送りする
（develop にいて追跡済みファイルがきれいで、早送りだけで済むときだけ。何も消さない・sync_primary）。
"""
import json
import re
import subprocess
import sys
import time

TIMEOUT_SEC = 5
PR_LIMIT = 5
UNAVAILABLE = "取得できませんでした"
ISSUE_ID = re.compile(r"\b(I[0-9]{3})\b", re.ASCII)  # PR は「fix: I178 …」の形なので先頭に限らず最初の 1 つ
DATE = re.compile(r"^([0-9]{4}-[0-9]{2}-[0-9]{2})", re.ASCII)


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
    return f"#{value}" if isinstance(value, int) and not isinstance(value, bool) else "#-"


def _issue_id(item: dict) -> str:
    match = ISSUE_ID.search(str(item.get("title") or ""))
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
    elif not latest_issue:
        lines.append("GitHub の最新イシュー: なし")
    else:
        lines.append(f"GitHub の最新イシュー: {_number(latest_issue)} {_issue_id(latest_issue)}")
    return "\n".join(lines)


PRIMARY_SKIP_AFTER_SEC = 12   # 既存の行を集めた後、これを過ぎていたら primary をそろえない
# sync_primary の中で fetch・merge の前にこれを過ぎていたらやめる。fetch・merge は打ち切りに SIGTERM の後 2 秒待つので
# 最長 7 秒、merge の後の rev-parse が 5 秒で、15＋7＋5＝27 秒 < フックの 30 秒
PRIMARY_STOP_AFTER_SEC = 15


def _run_git_soft(args: list[str]) -> str | None:
    """primary を書き換える git（fetch・merge）用。打ち切りは SIGTERM で行い、git が自分で .lock を片付けられる
    ようにする（subprocess.run の timeout は SIGKILL で、index.lock 等が残り以後の git が失敗する・コードレビューの F2）。"""
    try:
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except OSError:
        return None
    try:
        out, _ = p.communicate(timeout=TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        p.terminate()
        try:
            p.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            p.kill()
            p.communicate()
        return None
    return out if p.returncode == 0 else None


def _primary_path() -> str | None:
    """git worktree list --porcelain の最初の worktree 行（＝primary）。外から渡された値は使わない。"""
    out = _run(["git", "worktree", "list", "--porcelain"])
    if out is None:
        return None
    for line in out.splitlines():
        if line.startswith("worktree "):
            return line[len("worktree "):] or None
    return None


def sync_primary(start: float) -> str:
    """I200: primary を origin/develop へ早送りする。develop にいて追跡済みファイルがきれいで、
    早送りだけで済むときだけ動き、何も消さない（未追跡のファイルを上書きしうるときは git 自身が止める）。
    合わないとき・失敗したときは理由と手で行うコマンドを 1 行で返すだけ（docs/runbooks/worktree.md §9）。"""
    def late(limit: float) -> bool:
        return time.monotonic() - start > limit

    if late(PRIMARY_SKIP_AFTER_SEC):
        return "primary: 時間が足りないのでそろえません"
    primary = _primary_path()
    if not primary:
        return "primary: 確かめられませんでした"
    manual = f"手で: cd {primary} && git switch develop && git pull --ff-only"
    head = _run(["git", "-C", primary, "symbolic-ref", "--short", "HEAD"])
    if head is None:
        return f"primary: develop にいないのでそろえません（今: ブランチなし）。{manual}"
    if head.strip() != "develop":
        return f"primary: develop にいないのでそろえません（今: {head.strip()}）"
    status = _run(["git", "-C", primary, "status", "--porcelain", "--untracked-files=no"])
    if status is None:
        return f"primary: 状態を読めませんでした。{manual}"
    if status.strip():
        return "primary: 未コミットの変更があるのでそろえません"
    if late(PRIMARY_STOP_AFTER_SEC):
        return "primary: 時間が足りないのでそろえません"
    _run_git_soft(["git", "-C", primary, "fetch", "--quiet", "origin", "develop"])  # 失敗しても手元の origin/develop で続ける
    if late(PRIMARY_STOP_AFTER_SEC):
        return "primary: 時間が足りないのでそろえません"
    before = _run(["git", "-C", primary, "rev-parse", "--short", "HEAD"])
    if _run_git_soft(["git", "-C", primary, "merge", "--ff-only", "--quiet", "origin/develop"]) is None:
        return f"primary: そろえられませんでした（早送りできない・ファイルがぶつかる・ロック中など）。{manual}"
    after = _run(["git", "-C", primary, "rev-parse", "--short", "HEAD"])
    if before is None or after is None or before.strip() == after.strip():
        return "primary: 最新です"
    return f"primary: develop を origin/develop へ早送りしました（{before.strip()}..{after.strip()}）"


def collect() -> str:
    start = time.monotonic()
    branch_out = _run(["git", "branch", "--show-current"])
    branch = None if branch_out is None else (branch_out.strip() or "(detached HEAD)")
    status_out = _run(["git", "status", "--porcelain"])
    dirty = None if status_out is None else len(status_out.splitlines())
    prs = _gh_json(["pr", "list", "--state", "merged", "--base", "develop",
                    "--limit", str(PR_LIMIT), "--json", "number,title,mergedAt"])
    issues = _gh_json(["issue", "list", "--state", "all", "--limit", "1", "--json", "number,title"])
    if issues is None or (issues and not isinstance(issues[0], dict)):
        latest = None  # 取れなかった・形が壊れている
    else:
        latest = issues[0] if issues else {}  # 0 件なら「なし」
    text = format_context(branch, dirty, prs, latest)  # 既存の行を先に組み立てておく（primary の失敗で失わない）
    try:
        return text + "\n" + sync_primary(start)
    except Exception:  # noqa: BLE001 — primary の行の失敗で既存の行を失わない
        return text + "\nprimary: 確かめられませんでした"


def main() -> None:
    try:
        print(collect())
    except Exception:  # noqa: BLE001 — セッションの開始は決して止めない
        print(f"[sessionstart] 作業の状態: {UNAVAILABLE}")
    sys.exit(0)


if __name__ == "__main__":
    main()
