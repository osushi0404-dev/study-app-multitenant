#!/usr/bin/env python3
"""I599: レビュー前の中身に届く `bash scripts/claude/…` を見分ける（plan_I599.md 4-1）。

「レビュー済み」は、このブランチが develop から分かれた時点（git merge-base HEAD origin/develop＝BASE）の
中身と同じこと。サンドボックスの外に出す一覧（.claude/settings.json の excludedCommands）の `bash scripts/claude/*`
は文字の一致だけで外に出すので、BASE と違う中身に届くときは、見張り（scripts/claude/hooks/pretooluse_guard.py）が
コマンドを書き換えてサンドボックスの中で動かす。scripts/claude/code-review.sh は、ゲートの行を手元で流すかに使う。

置き場所が .claude/hooks/ なのは、サンドボックスから書けず（Edit は承認が要る）、scripts/claude/ のたどりの外に
あるため（判定を直しても、呼び元が中に回らない）。Python の標準ライブラリだけを使う。

CLI: python3 .claude/hooks/unreviewed.py check -- '<コマンド>'
  終了コード 0=レビュー済み（外のままでよい）・1=中で動かす・3=承認が要る・2=使い方の誤り
"""
from __future__ import annotations

import os
import re
import shlex
import subprocess  # nosec B404 — git を引数の配列で呼ぶだけ（shell を通さない）
import sys
from dataclasses import dataclass, field

SCRIPTS = "scripts/claude/"
# 起動役（.claude/hooks/reviewed-hook.sh）も同じ基準・同じ -c を使う（テストが一致を確かめる）
BASE_REF = "origin/develop"
# 見張りの _GIT_SAFE_OPTS と同じ（.git/config はサンドボックスの中から書けるので、命令を動かす設定を無効にする）
GIT_SAFE_OPTS = ("-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-c", "submodule.recurse=false")
GIT_TIMEOUT = 8
# 読み取りの上限（超えたら中で動かす。見張りの締め切り 20 秒を超えて Bash がすべて止まるのを防ぐ）
MAX_FILE_BYTES = 1_000_000
MAX_TOTAL_BYTES = 20_000_000
MAX_FILES = 2000
# まとめて拾う入口: このファイルに届いたら、前置きの下のファイルすべてに届く（run-all.sh は tests/test_*.sh を拾う。
# 名前でたどれないので表で持つ）
RUNNER_GLOBS = {"scripts/claude/tests/run-all.sh": ("scripts/claude/tests/",)}
# scripts/claude/ のスクリプトに渡した引数のうち、この拡張子の既存のファイルは動かされうるものとして出発点に足す
# （run-all.sh・stress-repeat.sh など。入口ごとの表にしない）
EXEC_SUFFIXES = (".sh", ".py")
# test-session.sh: 引数を claude -p にそのまま渡すので、許可の表に無い引数は承認を求める
TEST_SESSION = "scripts/claude/test-session.sh"
TS_WITH_VALUE = {"--model", "--permission-mode", "--permission-prompts", "--max-turns", "--output-format",
                 "--setting-sources"}
TS_NO_VALUE = {"--verbose"}
# 参照の語にこれがあれば、どのファイルに当たるか決まらない（「..」で外へ・変数・置き換え・glob・~・引用符の残り）
UNTRACEABLE_RE = re.compile(r"\.\.|[$`*?\[~'\"\\]")
TRIGGER_RE = re.compile(r"(?<![\w./-])['\"]?bash['\"]?\s+['\"]?(?:\./|/\S*/)?" + re.escape(SCRIPTS))
TOKEN_RE = re.compile(r"[\w./-]+")
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._/-]")


@dataclass
class Result:
    rewrite: bool = False
    ask_reason: str | None = None
    reached: list[str] = field(default_factory=list)
    why: str = ""


def triggered(command: str) -> bool:
    """外に出す一覧の `bash scripts/claude/*` に当たりうるか（`bash` のすぐ後ろが scripts/claude/ のパス。
    当たらなければ git を呼ばない。grep などで scripts/claude/ を読むだけのコマンドは、もともと中で動く）。"""
    return SCRIPTS in command and TRIGGER_RE.search(command) is not None


def _git(root: str, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    r = subprocess.run(["git", *GIT_SAFE_OPTS, "-C", root, *args], capture_output=True, text=True,  # nosec B603 B607
                       timeout=GIT_TIMEOUT, env=env, check=False)
    if r.returncode != 0:
        raise RuntimeError(f"git {args[0]} が失敗した（exit={r.returncode}）")
    return r.stdout


def _lines(text: str) -> list[str]:
    """git の -z の出力（NUL 区切り。名前に改行・引用符があってもそのまま）を名前の列にする。"""
    return [x for x in text.split("\0") if x]


def _normalize(tok: str, root: str) -> str | None:
    """参照の語をリポジトリからの相対パスにする。scripts/claude/ の外・たどれない形は None。"""
    if UNTRACEABLE_RE.search(tok):
        return None
    p = tok
    if p.startswith(root + "/"):
        p = p[len(root) + 1:]
    while p.startswith("./"):
        p = p[2:]
    return p if p.startswith(SCRIPTS) else None


def _segments(command: str) -> list[list[str]] | None:
    """コマンドを制御の記号で区切った語の列にする。読めなければ None。"""
    try:
        lex = shlex.shlex(command, posix=True, punctuation_chars=";&|()")
        lex.whitespace_split = True
        lex.commenters = ""
        toks = list(lex)
    except ValueError:
        return None
    segs, cur = [], []
    for t in toks:
        if set(t) <= set(";&|()"):
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        segs.append(cur)
    return segs


def _files(root: str, base: str) -> tuple[list[str], set[str]]:
    """(scripts/claude/ の全ファイル, BASE と違うファイル)。git を 2 回だけ呼ぶ。"""
    listed = _lines(_git(root, "ls-files", "-z", "-t", "--cached", "--others", "--exclude-standard", "--", SCRIPTS))
    files, untracked = set(), set()
    for x in listed:
        tag, _, name = x.partition(" ")
        files.add(name)
        if tag == "?":
            untracked.add(name)
    diff = _lines(_git(root, "diff", "-z", "--name-only", "--no-ext-diff", "--no-textconv", base, "--", SCRIPTS))
    return sorted(files), set(diff) | untracked


class _Limit(Exception):
    pass


def _reach(root: str, start: set[str], files: list[str], changed: set[str]) -> list[str]:
    """start から、名前（相対パスかファイル名）で呼ぶファイルをたどり、届いた変更（最大 5 件）を返す。
    各ファイルは 1 回だけ読み、語を引いて辺を張る。上限を超えたら _Limit。"""
    if len(files) > MAX_FILES:
        raise _Limit(f"scripts/claude/ のファイルが {MAX_FILES} を超えた")
    fileset = set(files)
    by_name: dict[str, list[str]] = {}
    for f in files:
        by_name.setdefault(os.path.basename(f), []).append(f)
        by_name.setdefault(f, []).append(f)
    seen: set[str] = set()
    hits: list[str] = []
    todo = list(start)
    total = 0
    while todo and len(hits) < 5:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        if f in changed:
            hits.append(f)
            continue
        for prefix in RUNNER_GLOBS.get(f, ()):
            todo.extend(g for g in files if g.startswith(prefix))
        path = os.path.join(root, f)
        if os.path.islink(path) and not os.path.realpath(path).startswith(os.path.join(root, SCRIPTS)):
            raise _Limit(f"{f} が scripts/claude/ の外を指すリンク")
        if f not in fileset or not os.path.isfile(path):
            continue
        size = os.path.getsize(path)
        total += size
        if size > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
            raise _Limit(f"{f} の読み取りが上限（1 ファイル {MAX_FILE_BYTES}・合計 {MAX_TOTAL_BYTES} バイト）を超えた")
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        for tok in set(TOKEN_RE.findall(text)):
            for key in (tok, os.path.basename(tok)):
                todo.extend(by_name.get(key, ()))
    return hits


def _same_as_base(root: str, base: str, rel: str) -> bool:
    """rel が追跡されていて、BASE と中身が同じか。"""
    try:
        return rel in _lines(_git(root, "ls-files", "-z", "--", rel)) and \
            _git(root, "rev-parse", f"{base}:{rel}").strip() == _git(root, "hash-object", "--", rel).strip()
    except RuntimeError:
        return False


def _test_session_ask(args: list[str], root: str, base) -> str | None:
    i = 0
    while i < len(args):
        a = args[i]
        if not a.startswith("-"):
            i += 1
            continue
        name, eq, val = a.partition("=")
        if name in TS_NO_VALUE and not eq:
            i += 1
        elif name in TS_WITH_VALUE:
            i += 1 if eq else 2
        elif name == "--settings":
            v = val if eq else (args[i + 1] if i + 1 < len(args) else "")
            i += 1 if eq else 2
            rel = os.path.relpath(os.path.realpath(os.path.join(root, v)), root)
            b = base()
            if b is None or rel.startswith("..") or not os.path.isfile(os.path.join(root, rel)) \
                    or not _same_as_base(root, b, rel):
                return (f"test-session.sh にレビュー前の設定ファイル（{v}）を渡しています。子のセッションのフックは"
                        "サンドボックスの外で動きます。中身を確かめて承認してください（I599）")
        else:
            return (f"test-session.sh に許可の表に無い引数（{name}）を渡しています。子のセッションの設定・道具を変え、"
                    "サンドボックスの外で動かせます。確かめて承認してください（I599）")
    return None


def check(command: str, cwd: str | None = None) -> Result:
    """コマンドを判定する。cwd はリポジトリの最上位（無ければ git で求める）。失敗したときは中で動かす（安全側）。"""
    if not isinstance(command, str) or not triggered(command):
        return Result()
    try:
        return _check(command, cwd)
    except Exception as e:  # noqa: BLE001 — 判定できないときは中で動かす
        return Result(rewrite=True, why=f"判定できなかった（{type(e).__name__}）")


def _check(command: str, cwd: str | None) -> Result:
    root = os.path.realpath(cwd) if cwd else os.path.realpath(_git(os.getcwd(), "rev-parse", "--show-toplevel").strip())
    cache: dict[str, str | None] = {}

    def base() -> str | None:
        if "b" not in cache:
            try:
                cache["b"] = _git(root, "merge-base", "HEAD", BASE_REF).strip() or None
            except RuntimeError:
                cache["b"] = None
        return cache["b"]

    res = Result()
    start: set[str] = set()
    untraceable = []
    segs = _segments(command)
    if segs is None:
        res.rewrite, res.why = True, "コマンドを読み切れない"
        return res
    # 見るのは「bash のすぐ後ろが scripts/claude/ のパス」の区切りだけ（外に出す一覧に当たりうる形）。
    # 引用符の中の文（コミットのメッセージなど）は 1 つの語なので当たらない
    for seg in segs:
        for j in range(len(seg) - 1):
            if seg[j] != "bash" or SCRIPTS not in seg[j + 1]:
                continue
            script, args = seg[j + 1], seg[j + 2:]
            rel = _normalize(script, root)
            if rel is None:
                untraceable.append(script)
                continue
            start.add(rel)
            if rel == TEST_SESSION:
                res.ask_reason = res.ask_reason or _test_session_ask(args, root, base)
            for a in args:
                if SCRIPTS in a and _normalize(a, root) is None:
                    untraceable.append(a)
                    continue
                if a.startswith("-") or not a.endswith(EXEC_SUFFIXES):
                    continue
                p = os.path.realpath(a if a.startswith("/") else os.path.join(root, a))
                if not os.path.isfile(p):
                    continue
                arel = _normalize(p, root)
                if arel is None:
                    untraceable.append(a)
                else:
                    start.add(arel)
    if untraceable:
        res.rewrite, res.why, res.reached = True, "たどれない参照", untraceable[:5]
        return res
    b = base()
    if b is None:
        res.rewrite, res.why = True, f"レビュー済みの基準（merge-base HEAD {BASE_REF}）を求められない"
        return res
    files, changed = _files(root, b)
    if not changed:
        return res
    try:
        hits = _reach(root, start, files, changed)
    except _Limit as e:
        res.rewrite, res.why = True, str(e)
        return res
    if hits:
        res.rewrite, res.reached, res.why = True, sorted(hits), "レビュー前の中身に届く"
    return res


def rewrite_command(command: str, res: Result) -> str:
    """元のコマンドの前に印の echo を付ける（echo は外に出す一覧に無いので、コマンド全体がサンドボックスの中で動く）。"""
    names = ", ".join(SAFE_NAME_RE.sub("_", x)[:200] for x in res.reached[:5]) or res.why[:200]
    msg = (f"[I599] レビュー前の中身があるので、サンドボックスの中で動かします（届いた変更: {names}）。"
           "外で動かす必要があれば、ユーザーに ! で流してもらう（docs/runbooks/danger-ops.md）")
    msg = re.sub(r"['\r\n\\]", "_", msg)   # 単一引用符の中で効く文字を消す（理由の文にもファイル名が入りうる）
    return f"echo '{msg}' >&2 && {command}"


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[0] != "check" or argv[1] != "--":
        print("使い方: unreviewed.py check -- '<コマンド>'", file=sys.stderr)
        return 2
    res = check(argv[2])
    if res.ask_reason:
        print(res.ask_reason)
        return 3
    if res.rewrite:
        print(f"{res.why}: {', '.join(res.reached)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
