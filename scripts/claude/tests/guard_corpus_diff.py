#!/usr/bin/env python3
"""I174（plan_I174.md 0-12）: 過去の作業記録の Bash コマンドを、コミット済み（基準）の guard と作業ツリーの guard の
両方で判定し、確認・停止の増減を出す。修正した本人が、コミットの前に余計な確認・誤停止の増加に気づくためのゲート。

使い方: python3 scripts/claude/tests/guard_corpus_diff.py [--base REV]（既定 HEAD）[--rebuild] [--limit PCT]（既定 1.0）
- 作業記録（~/.claude/projects/<このリポジトリ>/**/*.jsonl）から Bash コマンドを抜き出し、
  ~/.cache/claude-guard-corpus/<リポジトリ名>.json に保存する（リポジトリには入れない。公開リポジトリのため）。
- 基準と作業ツリーを同じ時点・同じ作業ディレクトリで判定するので、環境の差（変更のあるファイル等）は結果に混ざらない。
- 確認＋停止の増加が記録の PCT% を超えたら exit 1。素通し→停止は一覧を出す（意図どおりかを人が見る）。
- 作業記録が無い環境（CI 等）では SKIP（exit 0）。
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

REPO = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
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


def _project_dir() -> str:
    return os.path.expanduser("~/.claude/projects/" + REPO.replace("/", "-"))


def build_corpus(path: str) -> list:
    """作業記録から Bash コマンドを抜き出す（同じ呼び出し ID は 1 件）。"""
    seen, out = set(), []
    for f in glob.glob(_project_dir() + "/**/*.jsonl", recursive=True):
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


def judge(guard: str, cmd: str) -> str:
    p = subprocess.run([sys.executable, "-I", guard], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
                       capture_output=True, text=True, cwd=REPO, timeout=60)
    if p.returncode == 2:
        return "block"
    if p.returncode == 0 and '"ask"' in p.stdout:
        return "ask"
    return "pass" if p.returncode == 0 else f"rc{p.returncode}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="HEAD")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--limit", type=float, default=1.0)
    ap.add_argument("--guard", default=None, help="作業ツリーの guard の代わりに比べるファイル（ゲート自体の検証用）")
    a = ap.parse_args()

    path = os.path.join(CACHE_DIR, os.path.basename(REPO) + ".json")
    if os.path.isdir(CACHE_DIR):
        os.chmod(CACHE_DIR, 0o700)                   # 以前の版で作ったキャッシュも本人だけに絞る
    if a.rebuild or not os.path.exists(path):
        if not os.path.isdir(_project_dir()):
            print("SKIP: 作業記録が無い環境です（CI 等）")
            return 0
        cmds = build_corpus(path)
    else:
        cmds = json.load(open(path, encoding="utf-8"))
    if not cmds:
        print("SKIP: 作業記録に Bash コマンドがありません")
        return 0

    git = lambda *args: subprocess.run(["git", *args], capture_output=True, text=True, cwd=REPO)
    with tempfile.TemporaryDirectory() as td:
        base = os.path.join(td, "guard_base.py")
        src = git("show", f"{a.base}:{GUARD_REL}")
        if src.returncode != 0:
            print(f"SKIP: {a.base} に guard がありません")
            return 0
        cur = os.path.abspath(a.guard) if a.guard else os.path.join(REPO, GUARD_REL)
        with open(cur, encoding="utf-8") as fh:
            same = fh.read() == src.stdout
        if same and a.base == "HEAD":
            # 未コミットの変更が無い（コミットの後・コードレビュー時）: develop との分かれた点などと比べる（base_rev）
            rev, why = base_rev(git)
            src = git("show", f"{rev}:{GUARD_REL}") if rev else src
            if not rev or src.returncode != 0:
                print(f"SKIP: {why if not rev else '比べる前の版の guard がありません'}")
                return 0
            a.base = why
        with open(base, "w", encoding="utf-8") as fh:
            fh.write(src.stdout)
        with ThreadPoolExecutor(12) as ex:
            b = list(ex.map(lambda c: judge(base, c), cmds))
            w = list(ex.map(lambda c: judge(cur, c), cmds))

    n = len(cmds)
    hit = lambda xs: sum(1 for x in xs if x in ("ask", "block"))
    trans = Counter(f"{x}->{y}" for x, y in zip(b, w) if x != y)
    print(f"作業記録 {n} 件（基準 {a.base} → 作業ツリー）")
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
