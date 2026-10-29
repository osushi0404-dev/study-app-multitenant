#!/usr/bin/env python3
"""SessionStart hook: セッション開始時に作業の状態を Claude に渡す（I185 P5）。

並行ワークツリーで「マージ済みか」「最新のイシュー番号」の認識が古くなるのを防ぐ。
stdout はそのまま Claude の文脈に入る（hooks.md）。

GitHub のタイトルの自由文は出さない。公開リポジトリのイシューは誰でも作れ、
そのタイトルが毎セッションの文脈に入ると指示の書き込みの入口になるため
（I185 security-review Medium）。出すのは番号・日付・タイトル中の最初の I### だけ。
どのコマンドが失敗・タイムアウトしても exit 0（セッションの開始を止めない）。

I200・I219: 許可の判定の一部は primary（元のフォルダ）の設定で行われるため、primary を origin/develop へ早送りする
（develop にいて追跡済みファイルがきれいで、早送りだけで済むときだけ。何も消さない）。早送りは裏の処理
（`--sync-primary`）で行い、開始時のフックは前回の結果を 1 行出して裏の処理を起動するだけで、待たない（I219）。
"""
import datetime
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys

TIMEOUT_SEC = 5
PR_LIMIT = 5
UNAVAILABLE = "取得できませんでした"
ISSUE_ID = re.compile(r"\b(I[0-9]{3})\b", re.ASCII)  # PR は「fix: I178 …」の形なので先頭に限らず最初の 1 つ
DATE = re.compile(r"^([0-9]{4}-[0-9]{2}-[0-9]{2})", re.ASCII)
# I219: 読み取りの git は索引の書き直し（optional lock）をしない。打ち切られても .git/index.lock を残さない
GIT_ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}


def _run(args: list[str], timeout: float = TIMEOUT_SEC, grace: float = 0) -> str | None:
    """コマンドを動かして stdout を返す（失敗・打ち切りは None）。grace が 0 より大きいときは、打ち切りを SIGTERM で
    行い grace 秒待ってから SIGKILL（必須のロックを取る fetch・merge 用。SIGKILL だけだと git が .lock を片付けられない）。
    読み取りは GIT_OPTIONAL_LOCKS=0 でロックを取らないので、すぐ打ち切る（開始時のフックの最悪の時間を延ばさない・I219）。"""
    try:
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=GIT_ENV)
    except OSError:
        return None
    try:
        out, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if grace > 0:
            p.terminate()
            try:
                p.communicate(timeout=grace)
                return None
            except subprocess.TimeoutExpired:
                pass
        p.kill()
        p.communicate()
        return None
    return out if p.returncode == 0 else None


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


# --- I219: primary の早送り（裏の処理）と、その結果の受け渡し ---
BG_GIT_TIMEOUT_SEC = 60   # 裏の処理の git 1 回の打ち切り（実際の primary の status は 1〜5 秒・plan_I219.md 調査結果）


def _bg_timeout() -> float:
    """裏の処理の打ち切り。CLAUDE_PRIMARY_SYNC_TIMEOUT はテスト用（短くするだけ。判定は変えない）。"""
    try:
        v = float(os.environ.get("CLAUDE_PRIMARY_SYNC_TIMEOUT", ""))
        return v if 0 < v <= BG_GIT_TIMEOUT_SEC else BG_GIT_TIMEOUT_SEC
    except ValueError:
        return BG_GIT_TIMEOUT_SEC


def _primary_path() -> str | None:
    """git worktree list --porcelain の最初の worktree 行（＝primary）。外から渡された値は使わない。"""
    out = _run(["git", "worktree", "list", "--porcelain"])
    if out is None:
        return None
    for line in out.splitlines():
        if line.startswith("worktree "):
            return line[len("worktree "):] or None
    return None


def _state_paths(primary: str) -> tuple[str, str]:
    """結果のファイルと排他の .lock の場所（リポジトリの外）。CLAUDE_PRIMARY_SYNC_DIR はテスト用（置き場所だけ）。"""
    base = os.environ.get("CLAUDE_PRIMARY_SYNC_DIR") or os.path.join(
        os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "claude-primary-sync")
    os.makedirs(base, mode=0o700, exist_ok=True)
    key = hashlib.sha1(primary.encode("utf-8")).hexdigest()[:16]
    return os.path.join(base, key + ".json"), os.path.join(base, key + ".lock")


def _write_result(path: str, message: str) -> None:
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"at": datetime.datetime.now().strftime("%m-%d %H:%M"), "message": message}, f, ensure_ascii=False)
    os.replace(tmp, path)   # 読む側が書きかけを読まない


def _sync_primary_steps(primary: str) -> str:
    """I200 の条件のまま早送りする（develop にいる・追跡済みファイルがきれい・早送りだけ。何も消さない。
    未追跡のファイルを上書きしうるときは git 自身が止める）。結果を 1 行で返す。"""
    t = _bg_timeout()
    manual = f"手で: cd {primary} && git switch develop && git pull --ff-only"
    head = _run(["git", "-C", primary, "symbolic-ref", "--short", "HEAD"], t)
    if head is None:
        return f"develop にいないのでそろえません（今: ブランチなし）。{manual}"
    if head.strip() != "develop":
        return f"develop にいないのでそろえません（今: {head.strip()}）"
    status = _run(["git", "-C", primary, "status", "--porcelain", "--untracked-files=no"], t)
    if status is None:
        return f"状態を読めませんでした。{manual}"
    if status.strip():
        return "未コミットの変更があるのでそろえません"
    _run(["git", "-C", primary, "fetch", "--quiet", "origin", "develop"], t, grace=2)  # 失敗しても手元の origin/develop で続ける
    before = _run(["git", "-C", primary, "rev-parse", "--short", "HEAD"], t)
    if _run(["git", "-C", primary, "merge", "--ff-only", "--quiet", "origin/develop"], t, grace=2) is None:
        return f"そろえられませんでした（早送りできない・ファイルがぶつかる・ロック中・時間切れなど）。{manual}"
    after = _run(["git", "-C", primary, "rev-parse", "--short", "HEAD"], t)
    if before is None or after is None or before.strip() == after.strip():
        return "最新です"
    return f"develop を origin/develop へ早送りしました（{before.strip()}..{after.strip()}）"


def sync_primary_bg() -> None:
    """裏の処理（--sync-primary）。1 本ずつ動き（flock）、結果をファイルに書く。何があっても exit 0。"""
    primary = _primary_path()
    if not primary:
        return
    result_path, lock_path = _state_paths(primary)
    with open(lock_path, "a", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return   # ほかの裏の処理が動いている
        try:
            message = _sync_primary_steps(primary)
        except Exception as e:  # noqa: BLE001 — 結果に理由を残して終わる
            message = f"確かめられませんでした（{type(e).__name__}）"
        _write_result(result_path, message)


def primary_line_and_spawn() -> str:
    """開始時のフック用。前回の結果を 1 行にし、裏の処理を起動してすぐ戻る（待たない・I219）。"""
    primary = _primary_path()
    line = "primary: 確かめられませんでした"
    if primary:
        result_path, _ = _state_paths(primary)
        try:
            with open(result_path, encoding="utf-8") as f:
                data = json.load(f)
            line = f"primary: 前回（{data.get('at', '-')}）: {data.get('message', '-')}"
        except (OSError, ValueError):
            line = "primary: まだ結果がありません（裏でそろえています）"
    try:
        subprocess.Popen([sys.executable, os.path.abspath(__file__), "--sync-primary"], start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        line += "（裏の処理を起動できませんでした）"
    return line


def collect() -> str:
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
        return text + "\n" + primary_line_and_spawn()
    except Exception:  # noqa: BLE001 — primary の行の失敗で既存の行を失わない
        return text + "\nprimary: 確かめられませんでした"


def main() -> None:
    if sys.argv[1:] == ["--sync-primary"]:
        try:
            sync_primary_bg()
        except Exception:  # noqa: BLE001 — 裏の処理は何があっても静かに終わる
            pass
        sys.exit(0)
    try:
        print(collect())
    except Exception:  # noqa: BLE001 — セッションの開始は決して止めない
        print(f"[sessionstart] 作業の状態: {UNAVAILABLE}")
    sys.exit(0)


if __name__ == "__main__":
    main()
