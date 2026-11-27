#!/usr/bin/env python3
"""I599（第 2 版・plan_I599.md 4-1・4-2）: scripts/claude/ のスクリプトをサンドボックスの外で動かす唯一の入口と、その判定。

既定はサンドボックスの中。外に出す一覧（.claude/settings.json の excludedCommands）は
`python3 .claude/hooks/unreviewed.py run *` だけで、ここ（run）が、外で動く必要のある決まったスクリプト
（OUTSIDE_SCRIPTS）だけを動かす。I615: 動かすのは、このブランチが develop から分かれた時点（git merge-base HEAD
origin/develop＝BASE）の写し（作り方の正は .claude/hooks/reviewed-hook.sh の reviewed_snapshot）の入口で、作業フォルダは
リポジトリの最上位。流す入口・その部品（入口が読み込む・呼ぶ scripts/claude/ の直下のファイル）・使うレビュー役の定義
（.claude/agents/*.md）のどれかがブランチで変わっていれば動かさず、ユーザーに `!` で新しい版を流してもらう（75）。
I593: 審査の入口（REVIEW_ENTRIES）は、写しに reviewer-agents-lib.sh があれば、変わっていても写しの版で流す（定義も写しの版）。
「ブランチで変わった」= BASE との差・追跡していない新規・git が無視するファイル。見張り（scripts/claude/hooks/pretooluse_guard.py）は
route() で、単体の形の `bash scripts/claude/<一覧の名前> …` を run の形に付け替え、run の形を確かめ、test-session.sh の引数を確かめる。

置き場所が .claude/hooks/ なのは、サンドボックスから書けず（Edit は承認が要る）、scripts/claude/ の外にあるため。
Python の標準ライブラリだけを使う。

CLI:
  python3 .claude/hooks/unreviewed.py run <名前> [引数…]   終了コード: スクリプトのもの／2=名前の誤り／4=サンドボックスの中で
                                                            動いている／75=人に `!` で流してもらう（入口か部品を変えた・
                                                            基準を求められない・写しを作れない）
  python3 .claude/hooks/unreviewed.py dirty                 0=scripts/claude/ にレビュー前の中身なし／1=あり・求められない
                                                            （code-review.sh のゲートが使う）
"""
from __future__ import annotations

import os
import re
import shlex
import subprocess  # nosec B404 — git を引数の配列で呼ぶだけ（shell を通さない）
import sys
from dataclasses import dataclass

SCRIPTS = "scripts/claude/"
# フックの起動役（.claude/hooks/reviewed-hook.sh）も同じ基準・同じ -c を使う（テストが一致を確かめる）
BASE_REF = "origin/develop"
# 見張りの _GIT_SAFE_OPTS と同じ（.git/config はサンドボックスの中から書けるので、命令を動かす設定を無効にする）
GIT_SAFE_OPTS = ("-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-c", "submodule.recurse=false")
GIT_TIMEOUT = 8
# I615: 人に `!` で流してもらうときの終了コード（入口そのものの終了コード 0〜4・124・130 と重ならない）
NEED_HUMAN = 75
AGENTS = ".claude/agents/"
SNAPSHOT_SH = ".claude/hooks/reviewed-hook.sh"
SNAPSHOT_TIMEOUT = 60
# 部品のたどりで読まない行（注釈・表示）と行末の注釈。注釈で触れるだけの名前を部品に数えない（plan_I615.md 調査結果 8）
NOT_CODE_RE = re.compile(r"\s*(?:#|(?:echo|printf)\b)")
TRAILING_COMMENT_RE = re.compile(r"\s#\s.*$")
# 外で動く必要のある入口（gh・claude -p・docker を使う。plan_I599.md 調査結果 6）。足すときはここだけ（承認が要る）
OUTSIDE_SCRIPTS = frozenset({
    "adversarial-review.sh", "check-permission-prompt.sh", "code-review.sh", "db-backup.sh",
    "dependency-audit-issue.sh", "fix-diagnosis-review.sh", "issue-review.sh", "issue-source.sh",
    "lint-frontend.sh", "plan-issue-review.sh", "post-review-comment.sh", "pr-base-sync.sh",
    "test-session.sh", "tui-capture.sh", "wt-ports.sh", "wt-remove.sh",
})
# I593: 審査の入口。写しに新しい仕組み（REVIEWER_LIB）があれば、ブランチで入口・部品・レビュー役の定義を変えていても
# 75 にせず写しの版で流す（審査は変更前の版で動く。ブランチの変更はマージの後に効く・docs/runbooks/review-rules.md）
REVIEW_ENTRIES = frozenset({
    "adversarial-review.sh", "code-review.sh", "fix-diagnosis-review.sh", "issue-review.sh", "plan-issue-review.sh",
})
REVIEWER_LIB = "reviewer-agents-lib.sh"
LAUNCH = "python3 .claude/hooks/unreviewed.py run"
# 単体の形でない文字（つなぎ・置き換え・かっこ・振り向け・ワイルドカード・改行・逃がし）。あれば付け替えない（中で動く）。
# ワイルドカード（* ? [）は外の bash が作業ツリーのファイル名に展開し、書いた引数と違うものが渡るため（I599 F23）
NOT_SIMPLE_RE = re.compile(r"[$`(){};&|<>*?\[\n\r\\]")
SCRIPT_FORM_RE = re.compile(r"\s*bash\s+" + re.escape(SCRIPTS) + r"(?P<name>[^\s/]+)(?P<rest>(?:\s.*)?)", re.S)
LAUNCH_FORM_RE = re.compile(r"\s*python3\s+\.claude/hooks/unreviewed\.py\s+run(?P<rest>(?:\s.*)?)", re.S)
# 起動役を呼ぶ形（python3 … unreviewed.py run）。単体の形・最上位の cwd でなければ見張りが止める
LAUNCH_ANY_RE = re.compile(r"python3\s+\S*unreviewed\.py['\"]?\s+['\"]?run\b")
# 外に出す型（.claude/settings.json の excludedCommands）の最初の語。起動役のほかにこれで始まるコマンドだけが外に出うる
OUTSIDE_FIRST_WORDS = frozenset({"git", "gh", "docker", "docker-compose"})
ASSIGN_PREFIX_RE = re.compile(r"\A\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)+")
LAUNCH_AT_BOUNDARY_RE = re.compile(r"(?:[;&|\n(`]|\$\()\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*"
                                   r"python3\s+\S*unreviewed\.py['\"]?\s+['\"]?run\b")
# test-session.sh: 引数を claude -p にそのまま渡すので、許可の表に無い引数は承認を求める
TEST_SESSION = "test-session.sh"
TS_WITH_VALUE = {"--model", "--permission-mode", "--permission-prompts", "--max-turns", "--output-format",
                 "--setting-sources"}
TS_NO_VALUE = {"--verbose"}
# 子のセッションの確認を外さない許可のモード（bypassPermissions・dontAsk などは承認・I599 F4）
TS_PERMISSION_MODES = {"default", "manual", "plan", "acceptEdits", "auto"}


@dataclass
class Route:
    """見張りへの答え。new_command は付け替え後のコマンド・ask_reason は承認・block_reason は止める理由。"""
    new_command: str | None = None
    ask_reason: str | None = None
    block_reason: str | None = None
    # 起動役の形のとき、見張りのほかの判定はこの同じ意味の形（bash scripts/claude/<名前> …）にかける
    # （起動役そのもの〔このファイル〕の中身を、流すスクリプトの代わりに読ませない）
    analyze_as: str | None = None


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


def _base(root: str) -> str | None:
    try:
        return _git(root, "merge-base", "HEAD", BASE_REF).strip() or None
    except (RuntimeError, OSError, subprocess.SubprocessError):
        return None


def _unreviewed_files(root: str, base: str, *where: str) -> set[str]:
    """レビュー前のファイル = BASE と違う・追跡していない新規・git が無視するファイル（git は 3 回）。where の既定は scripts/claude/。
    無視されるフォルダ（.venv・__pycache__）は --directory で 1 つにまとめて数えない（わざと避ける形として受け入れ・plan R3）。"""
    where = where or (SCRIPTS,)
    untracked = set(_lines(_git(root, "ls-files", "-z", "--others", "--exclude-standard", "--", *where)))
    ignored = {x for x in _lines(_git(root, "ls-files", "-z", "--others", "--ignored", "--exclude-standard",
                                      "--directory", "--", *where)) if not x.endswith("/")}
    diff = _lines(_git(root, "diff", "-z", "--name-only", "--no-ext-diff", "--no-textconv", base, "--", *where))
    return set(diff) | untracked | ignored


def dirty(root: str) -> list[str] | None:
    """レビュー前の中身（最大 5 件の名前）。無ければ []。基準を求められない・git が失敗したら None。"""
    b = _base(root)
    if b is None:
        return None
    try:
        return sorted(_unreviewed_files(root, b))[:5]
    except (RuntimeError, OSError, subprocess.SubprocessError):
        return None


def _same_as_base(root: str, base: str, rel: str) -> bool:
    """rel が追跡されていて、BASE と中身が同じか。"""
    try:   # BASE にあり、中身の指紋が同じなら、レビュー済みの中身
        return _git(root, "rev-parse", f"{base}:{rel}").strip() == _git(root, "hash-object", "--", rel).strip()
    except (RuntimeError, OSError, subprocess.SubprocessError):
        return False


def _test_session_ask(args: list[str], root: str, base) -> str | None:
    i = 0
    settings_ok = False
    sources = None
    while i < len(args):
        a = args[i]
        if not a.startswith("-"):
            i += 1
            continue
        name, eq, val = a.partition("=")
        if name in TS_NO_VALUE and not eq:
            i += 1
            continue
        if name not in TS_WITH_VALUE and name != "--settings":
            return (f"test-session.sh に許可の表に無い引数（{name}）を渡しています。子のセッションの設定・道具を変え、"
                    "サンドボックスの外で動かせます。確かめて承認してください（I599）")
        v = val if eq else (args[i + 1] if i + 1 < len(args) else "")
        i += 1 if eq else 2
        if name == "--permission-mode" and v not in TS_PERMISSION_MODES:
            return (f"test-session.sh の --permission-mode {v or '（空）'} は、子のセッションの確認を外せます。"
                    "確かめて承認してください（I599）")
        if name == "--setting-sources":
            sources = v
        if name == "--settings":
            rel = os.path.relpath(os.path.realpath(os.path.join(root, v)), root)
            b = base()
            if b is None or rel.startswith("..") or not os.path.isfile(os.path.join(root, rel)) \
                    or not _same_as_base(root, b, rel):
                return (f"test-session.sh にレビュー前の設定ファイル（{v}）を渡しています。子のセッションのフックは"
                        "サンドボックスの外で動きます。中身を確かめて承認してください（I599）")
            # プロジェクトの設定の代わりになるのは、見張りとサンドボックスを持つ .claude/settings.json だけ（I599 F8）
            settings_ok = settings_ok or rel == ".claude/settings.json"
    # プロジェクトの設定（見張り・サンドボックス）を読まない子は、レビュー済みの設定を渡すときだけ承認なしで起こす
    if sources is not None and "project" not in sources.split(",") and not settings_ok:
        return (f"test-session.sh の --setting-sources {sources or '（空）'} は、プロジェクトの設定（見張り・サンドボックス）を"
                "読まない子のセッションを作ります。確かめて承認してください（I599）")
    return None


def _split(rest: str) -> list[str] | None:
    try:
        return shlex.split(rest, comments=False, posix=True)
    except ValueError:
        return None


def _same_dir(a: str | None, b: str) -> bool:
    return bool(a) and os.path.realpath(a) == os.path.realpath(b)


def route(command: str, root: str, cwd: str | None) -> Route:
    """見張りが使う。root はプロジェクトの最上位、cwd はフックの入力の cwd（plan_I599.md 4-1）。
    - 起動役の形: 単体の形で、cwd が最上位のときだけ通す（test-session.sh は引数を確かめて承認）。ほかは止める
    - 単体の形の `bash scripts/claude/<一覧の名前> …`（cwd が最上位）: 起動役の形に付け替える
    - それ以外: 何もしない（外に出す型に当たらないので中で動く）"""
    if not isinstance(command, str):
        return Route()
    simple = NOT_SIMPLE_RE.search(command) is None
    # 外に出るのは、つないだ全部が外に出す型に当たるときだけ（公式）。最初の命令が起動役でも git・gh・docker でも
    # なければ（cat・python3 - など）、全体が中で動くので止めない（本文やヒアドキュメントに起動役の文字があるだけの形）
    head = ASSIGN_PREFIX_RE.sub("", command, count=1)          # 前置きの代入（X=1 …）は外して見る
    first = head.split(None, 1)[0] if head.strip() else ""
    # 起動役で始まる形は厳しく見る。git・gh・docker で始まる形は、起動役が命令の区切りの後にあるときだけ見る
    # （コミットのメッセージなど引数の文の中の起動役の文字では止めない）
    could_go_out = LAUNCH_FORM_RE.match(head) is not None or \
        (first in OUTSIDE_FIRST_WORDS and LAUNCH_AT_BOUNDARY_RE.search(command) is not None)
    if could_go_out and LAUNCH_ANY_RE.search(command):
        m = LAUNCH_FORM_RE.fullmatch(command)
        args = _split(m.group("rest")) if (m and simple) else None
        if args is None or not _same_dir(cwd, root):
            return Route(block_reason=(
                "起動役（python3 .claude/hooks/unreviewed.py run）は、プロジェクトの最上位で、つなぎ・置き換え・"
                "振り向け・前置きの無い 1 つのコマンドとして流してください（docs/runbooks/danger-ops.md・I599）"))
        same = f"bash {SCRIPTS}{m.group('rest').lstrip()}" if args else None
        if args and args[0] == TEST_SESSION:
            return Route(ask_reason=_test_session_ask(args[1:], root, lambda: _base(root)), analyze_as=same)
        return Route(analyze_as=same)
    m = SCRIPT_FORM_RE.fullmatch(command)
    if not (simple and m and m.group("name") in OUTSIDE_SCRIPTS and _same_dir(cwd, root)):
        return Route()
    args = _split(m.group("rest"))
    if args is None:
        return Route()
    new = f"{LAUNCH} {m.group('name')}{m.group('rest')}"
    ask = _test_session_ask(args, root, lambda: _base(root)) if m.group("name") == TEST_SESSION else None
    return Route(new_command=new, ask_reason=ask)


def _root() -> str:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return os.path.realpath(env)
    return os.path.realpath(_git(os.getcwd(), "rev-parse", "--show-toplevel").strip())


def _snapshot(root: str) -> tuple[str | None, str]:
    """BASE の写しの最上位と、作れないときの理由（作り方と理由の文の正は reviewed-hook.sh の reviewed_snapshot。
    GIT_ の環境変数は reviewed-hook.sh が外す）。"""
    try:
        r = subprocess.run(["bash", os.path.join(root, SNAPSHOT_SH), "--snapshot"],  # nosec B603 B607
                           cwd=root, env={**os.environ, "CLAUDE_PROJECT_DIR": root}, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=SNAPSHOT_TIMEOUT, check=False)
    except (OSError, subprocess.SubprocessError):
        return None, "レビュー済みの写しを作る処理を起こせない"
    snap = r.stdout.strip()
    if r.returncode == 0 and snap and os.path.isfile(os.path.join(snap, ".complete")):
        return snap, ""
    return None, r.stderr.strip() or "レビュー済みの写しを作れない"


def _code_text(path: str) -> str:
    """部品のたどりで読む本文（注釈・表示の行と行末の注釈を除く）。読めなければ空。"""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return ""
    return "\n".join(TRAILING_COMMENT_RE.sub("", x) for x in lines if not NOT_CODE_RE.match(x))


def _word_in(word: str, text: str, after: str = r"[\w.-]") -> bool:
    return re.search(r"(?<![\w.-])" + re.escape(word) + r"(?!" + after + r")", text) is not None


def parts(snap: str, name: str, root: str) -> set[str]:
    """入口 name と、その部品（リポジトリ相対の名前）。写しの入口の本文から、写しの scripts/claude/ の直下のファイル名と、
    作業ツリーの .claude/agents/ のレビュー役の名前が語として出てくるものをたどる（plan_I615.md 4-3・調査結果 8）。"""
    sdir = os.path.join(snap, SCRIPTS)
    files = sorted(f for f in os.listdir(sdir) if os.path.isfile(os.path.join(sdir, f)))
    adir = os.path.join(root, AGENTS)
    agents = sorted(f[:-3] for f in os.listdir(adir) if f.endswith(".md")) if os.path.isdir(adir) else []
    found: set[str] = set()
    todo = [name]
    while todo:
        f = todo.pop()
        if SCRIPTS + f in found:
            continue
        found.add(SCRIPTS + f)
        text = _code_text(os.path.join(sdir, f))
        todo += [x for x in files if SCRIPTS + x not in found and _word_in(x, text)]
        # レビュー役は `REVIEWER_AGENT="code-reviewer"`・`code-reviewer.md` の形で書かれる（後ろの . は許す）
        found |= {f"{AGENTS}{a}.md" for a in agents if _word_in(a, text, after=r"[\w-]")}
    return found


def _need_human(name: str, args: list[str], why: str) -> int:
    cmd = " ".join([f"bash {SCRIPTS}{name}", shlex.join(args)]).strip()
    print(f"[unreviewed run] {why}ので、レビュー済みの版では流しません。ユーザーに `! {cmd}` で流してもらい、"
          "その結果をこの周の結果にしてください（docs/runbooks/danger-ops.md・I615）", file=sys.stderr)
    return NEED_HUMAN


def run(argv: list[str]) -> int:
    """起動役（外で動く。plan_I615.md 4-3）。BASE の写しの入口を、作業フォルダを最上位にして動かす。
    入口か部品・レビュー役の定義を変えたとき・写しを作れないときは動かさずに 75。"""
    if os.environ.get("SANDBOX_RUNTIME"):
        print("[unreviewed run] 起動役がサンドボックスの中で動いています（外に出す型に当たっていない）。"
              "gh・claude -p は動きません（I599）", file=sys.stderr)
        return 4
    if not argv or argv[0] not in OUTSIDE_SCRIPTS:
        print(f"[unreviewed run] 外で動かせるスクリプトの一覧に無い名前です: {argv[0] if argv else '（なし）'}"
              "（一覧は .claude/hooks/unreviewed.py の OUTSIDE_SCRIPTS）", file=sys.stderr)
        return 2
    name, args = argv[0], argv[1:]
    try:
        root = _root()
    except (RuntimeError, OSError, subprocess.SubprocessError):
        return _need_human(name, args, "リポジトリの最上位を求められない")
    snap, why = _snapshot(root)
    if snap is None:
        return _need_human(name, args, why)
    entry = os.path.join(snap, SCRIPTS, name)
    if not os.path.isfile(entry):
        return _need_human(name, args, "レビュー済みの版にこの入口が無い（ブランチで足した入口）")
    try:
        base = os.path.basename(snap)
        hit = sorted(parts(snap, name, root) & _unreviewed_files(root, base, SCRIPTS, AGENTS))
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError):
        return _need_human(name, args, "入口の部品がブランチで変わったかを確かめられない")
    if hit and name in REVIEW_ENTRIES and os.path.isfile(os.path.join(snap, SCRIPTS, REVIEWER_LIB)):
        print("[unreviewed run] ブランチで変えた審査の仕組み（" + ", ".join(hit[:5]) + "）は使わず、変更前の版で審査します"
              "（マージの後に効く・I593）", file=sys.stderr)
        hit = []
    if hit:
        return _need_human(name, args, "この入口か部品（" + ", ".join(hit[:5]) + "）をブランチで変えている")
    os.chdir(root)
    os.execvp("bash", ["bash", entry, *args])  # nosec B606 B607 — 写しの中の一覧の入口だけ・引数の配列
    return 1  # 届かない


def main(argv: list[str]) -> int:
    if argv[:1] == ["run"]:
        return run(argv[1:])
    if argv == ["dirty"]:
        try:
            found = dirty(_root())
        except (RuntimeError, OSError, subprocess.SubprocessError):
            found = None
        if found is None or found:
            print("レビュー前の中身: " + (", ".join(found) if found else "（基準を求められない）"))
            return 1
        return 0
    print("使い方: unreviewed.py run <名前> [引数…] | unreviewed.py dirty", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
