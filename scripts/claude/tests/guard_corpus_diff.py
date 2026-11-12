#!/usr/bin/env python3
"""I174（plan_I174.md 0-12）: 過去の作業記録の Bash コマンドを、コミット済み（基準）の guard と作業ツリーの guard の
両方で判定し、確認・停止の増減を出す。修正した本人が、コミットの前に余計な確認・誤停止の増加に気づくためのゲート。

使い方: python3 scripts/claude/tests/guard_corpus_diff.py [--base REV]（既定 HEAD）[--rebuild] [--limit PCT]（既定 1.0）
- 作業記録（~/.claude/projects/<primary>・<primary>--claude-worktrees-*/**/*.jsonl）から Bash コマンドを抜き出し、
  ~/.cache/claude-guard-corpus/<primary の名前>.json に保存する（リポジトリには入れない。公開リポジトリのため）。
- 基準と作業ツリーを同じ時点・同じ作業ディレクトリで判定するので、環境の差（変更のあるファイル等）は結果に混ざらない。
- 確認＋停止の増加が記録の PCT% を超えたら exit 1。素通し→停止は一覧を出す（意図どおりかを人が見る）。
- 作業記録が無い環境（CI 等）では SKIP（exit 0）。
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

# I444: ワークツリーからでも primary とすべてのワークツリーの作業記録を読む（共通の .git が読めなければ REPO に落とす）
REPO, _COMMON = (subprocess.run(["git", "rev-parse", "--path-format=absolute", "--show-toplevel", "--git-common-dir"],
                                capture_output=True, text=True).stdout.split("\n") + ["", ""])[:2]
PRIMARY = os.path.dirname(_COMMON) if _COMMON else REPO
GUARD_REL = "scripts/claude/hooks/pretooluse_guard.py"
CACHE_DIR = os.path.expanduser("~/.cache/claude-guard-corpus")
UPSTREAM = "origin/develop"


def base_rev(git) -> tuple:
    """未コミットの変更が無いときの比べる相手 (rev, 説明)。無ければ (None, 理由)。
    I182: develop を取り込んだマージコミットが見張りの最終変更でも、取り込んだ側の変更を数えないよう、
    ブランチが develop から分かれた点と比べる。develop の上（ブランチ固有のコミットが無い）ときだけ、
    第 1 親をたどって「見張りを最後に変えたコミットの直前」と比べる。"""
    head = git("rev-parse", "HEAD").stdout.strip()
    mb = git("merge-base", "HEAD", UPSTREAM).stdout.strip()
    if mb and mb != head:
        return mb, f"{mb[:7]}（{UPSTREAM} との分かれた点）"
    last = git("log", "-1", "--first-parent", "--format=%H", "--", GUARD_REL).stdout.strip()
    if not last:
        return None, "比べる前の版の guard がありません"
    return f"{last}^1", f"{last[:7]}^1（guard を最後に変えたコミットの直前）"


def _project_dirs(primary: str = PRIMARY) -> list:
    """primary とそのワークツリーの作業記録のフォルダ（Claude Code は英数字以外を - にした名前で置く）。"""
    base = os.path.expanduser("~/.claude/projects/" + re.sub(r"[^A-Za-z0-9]", "-", primary))
    return [d for d in [base] + sorted(glob.glob(base + "--claude-worktrees-*")) if os.path.isdir(d)]


def build_corpus(path: str) -> list:
    """作業記録から Bash コマンドを抜き出す（同じ呼び出し ID は 1 件）。"""
    seen, out = set(), []
    files = [f for d in _project_dirs() for f in glob.glob(d + "/**/*.jsonl", recursive=True)]
    for f in files:
        for line in open(f, encoding="utf-8", errors="replace"):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            m = e.get("message") or {}
            if e.get("type") != "assistant" or not isinstance(m.get("content"), list):
                continue
            for c in m["content"]:
                if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Bash":
                    cmd = (c.get("input") or {}).get("command")
                    if isinstance(cmd, str) and cmd.strip() and c.get("id") not in seen:
                        seen.add(c.get("id"))
                        out.append(cmd)
    os.makedirs(CACHE_DIR, mode=0o700, exist_ok=True)
    os.chmod(CACHE_DIR, 0o700)
    # 作業のコマンドには秘密が含まれうるので、作る時点から本人だけが読める権限にする
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)
    os.chmod(path, 0o600)
    return out


def judge(guard: str, cmd: str, cwd: str = REPO) -> str:
    p = subprocess.run([sys.executable, "-I", guard], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
                       capture_output=True, text=True, cwd=cwd, timeout=60)
    if p.returncode == 2:
        return "block"
    if p.returncode == 0 and '"ask"' in p.stdout:
        return "ask"
    return "pass" if p.returncode == 0 else f"rc{p.returncode}"


def base_source(a, git, cur: str):
    """比べる前の版の guard の中身と説明を返す。取り出せなければ (None, 理由)。
    --base が既定（HEAD）で作業ツリーの guard と同じなら、develop との分かれた点などと比べる（base_rev）。"""
    src = git("show", f"{a.base}:{GUARD_REL}")
    if src.returncode != 0:
        return None, f"{a.base} に guard がありません"
    with open(cur, encoding="utf-8") as fh:
        same = fh.read() == src.stdout
    if not (same and a.base == "HEAD"):
        return src.stdout, a.base
    rev, why = base_rev(git)
    if not rev:
        return None, why
    src = git("show", f"{rev}:{GUARD_REL}")
    return (src.stdout, why) if src.returncode == 0 else (None, "比べる前の版の guard がありません")


def judge_both(td: str, src, cur: str, cmds: list, cwd: str = REPO) -> tuple:
    """変更前（src の中身を td に書き出す。None なら判定しない）と作業ツリーの guard で cmds を判定し、(変更前, 作業ツリー) を返す。"""
    base = None
    if src is not None:
        base = os.path.join(td, "guard_base.py")
        with open(base, "w", encoding="utf-8") as fh:
            fh.write(src)
    jobs = [(g, c) for g in (base, cur) if g for c in cmds]
    with ThreadPoolExecutor(12) as ex:
        res = list(ex.map(lambda gc: judge(gc[0], gc[1], cwd), jobs))
    return (res[:len(cmds)], res[len(cmds):]) if base else ([None] * len(cmds), res)


RANK = {"pass": 0, "ask": 1, "block": 2}


def run_cases(a, git, cur: str) -> int:
    """I463: 止めるべき形の一覧（1 行 1 コマンド・# と空行は飛ばす・⏎ は改行・{W} は別ワークツリー）を、変更前と作業ツリーの
    guard の両方で判定する。作業ツリーで通す・変更前より弱い判定（停止→確認を含む）・異常終了が 1 件でもあれば exit 1。
    作業記録を使わないので CI でも流せる。コマンドは実行しない（guard に JSON を渡すだけ）。"""
    lines = [ln.rstrip("\n") for ln in open(a.cases, encoding="utf-8")]
    cases = [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]
    if not cases:
        print(f"FAIL: 一覧 {a.cases} にコマンドがありません")
        return 1
    with tempfile.TemporaryDirectory() as td:
        main_dir, wt = os.path.join(td, "main"), os.path.join(td, "other-wt")
        os.makedirs(main_dir)
        g = lambda *args: subprocess.run(["git", "-C", main_dir, *args], capture_output=True, text=True, check=True)
        g("init", "-q")
        g("-c", "user.email=t@example.com", "-c", "user.name=tester", "commit", "-q", "--allow-empty", "-m", "init")
        g("branch", "-q", "other")
        g("worktree", "add", "-q", wt, "other")
        src, why = base_source(a, git, cur)
        cmds = [c.replace("⏎", "\n").replace("{W}", wt) for c in cases]
        b, w = judge_both(td, src, cur, cmds, main_dir)
    print(f"止めるべき形 {len(cases)} 件（基準 {why if src is not None else 'なし'} → 作業ツリー）")
    if src is None:
        print(f"  変更前より弱いかは見られない（{why}）。作業ツリーで通す形・異常終了だけを見る")
    bad = []
    for c, x, y in zip(cases, b, w):
        if y not in RANK:
            bad.append(f"[異常終了 {y}] {c}")
        elif y == "pass":
            bad.append(f"[通す] {c}（基準 {x}）")
        elif x in RANK and RANK[y] < RANK[x]:
            bad.append(f"[弱くなった {x}->{y}] {c}")
    for m in bad:
        print("  " + m[:240])
    if bad:
        print(f"FAIL: 止めるべき形のうち {len(bad)} 件が後退・素通し・異常終了")
        return 1
    print(f"OK: {len(cases)} 件すべて作業ツリーで確認か停止・変更前より弱い判定 0 件")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="HEAD")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--limit", type=float, default=1.0)
    ap.add_argument("--guard", default=None, help="作業ツリーの guard の代わりに比べるファイル（ゲート自体の検証用）")
    ap.add_argument("--cases", default=None, help="止めるべき形の一覧で比べる（I463。作業記録は使わない）")
    a = ap.parse_args()

    git = lambda *args: subprocess.run(["git", *args], capture_output=True, text=True, cwd=REPO)
    cur = os.path.abspath(a.guard) if a.guard else os.path.join(REPO, GUARD_REL)
    if a.cases:
        return run_cases(a, git, cur)

    path = os.path.join(CACHE_DIR, os.path.basename(PRIMARY) + ".json")
    if os.path.isdir(CACHE_DIR):
        os.chmod(CACHE_DIR, 0o700)                   # 以前の版で作ったキャッシュも本人だけに絞る
    if a.rebuild or not os.path.exists(path):
        if not _project_dirs():
            print("SKIP: 作業記録が無い環境です（CI 等）")
            return 0
        cmds = build_corpus(path)
    else:
        cmds = json.load(open(path, encoding="utf-8"))
    if not cmds:
        print("SKIP: 作業記録に Bash コマンドがありません")
        return 0

    # 未コミットの変更が無い（コミットの後・コードレビュー時）は、develop との分かれた点などと比べる（base_source）
    src, label = base_source(a, git, cur)
    if src is None:
        print(f"SKIP: {label}")
        return 0
    with tempfile.TemporaryDirectory() as td:
        b, w = judge_both(td, src, cur, cmds)

    n = len(cmds)
    hit = lambda xs: sum(1 for x in xs if x in ("ask", "block"))
    trans = Counter(f"{x}->{y}" for x, y in zip(b, w) if x != y)
    print(f"作業記録 {n} 件（基準 {label} → 作業ツリー）")
    print(f"確認＋停止: {hit(b)}（{hit(b) / n:.2%}）→ {hit(w)}（{hit(w) / n:.2%}）")
    for k, v in sorted(trans.items()):
        print(f"  {k}: {v}")
    new_block = [c for c, x, y in zip(cmds, b, w) if x != "block" and y == "block"]
    for c in new_block[:30]:
        print("  [新しく停止] " + c.replace("\n", "⏎")[:200])
    for c in [c for c, x, y in zip(cmds, b, w) if x == "pass" and y == "ask"][:30]:
        print("  [新しく確認] " + c.replace("\n", "⏎")[:200])
    # 異常終了（exit 0・2 以外）は Claude Code では止めない扱い＝素通しになるので、1 件でも不合格
    crashed = [c for c, x, y in zip(cmds, b, w) if y.startswith("rc") and not x.startswith("rc")]
    for c in crashed[:10]:
        print("  [異常終了] " + c.replace("\n", "⏎")[:200])
    if crashed:
        print(f"FAIL: 作業ツリーの guard が {len(crashed)} 件で異常終了した（素通しになる）")
        return 1
    # 判定は差し引きでなく「新しく確認・停止になった件数」で行う（消えた確認と増えた確認が打ち消し合わないように）
    new = sum(1 for x, y in zip(b, w) if y in ("ask", "block") and x not in ("ask", "block"))
    new += sum(1 for x, y in zip(b, w) if x == "ask" and y == "block")
    if new > n * a.limit / 100:
        print(f"FAIL: 新しく確認・停止になったものが {new} 件（上限は記録の {a.limit}%＝{n * a.limit / 100:.0f} 件）")
        return 1
    print(f"OK: 新しく確認・停止 {new} 件・差し引き {hit(w) - hit(b):+d} 件（上限 {n * a.limit / 100:.0f} 件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
