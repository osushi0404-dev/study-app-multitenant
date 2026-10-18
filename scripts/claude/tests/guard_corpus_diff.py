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
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
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
    a = ap.parse_args()

    path = os.path.join(CACHE_DIR, os.path.basename(REPO) + ".json")
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

    with tempfile.TemporaryDirectory() as td:
        base = os.path.join(td, "guard_base.py")
        src = subprocess.run(["git", "show", f"{a.base}:{GUARD_REL}"], capture_output=True, text=True, cwd=REPO)
        if src.returncode != 0:
            print(f"SKIP: {a.base} に guard がありません")
            return 0
        with open(base, "w", encoding="utf-8") as fh:
            fh.write(src.stdout)
        cur = os.path.join(REPO, GUARD_REL)
        with open(cur, encoding="utf-8") as fh:
            if fh.read() == src.stdout:
                # コミットの前に使うゲート。変更をコミットした後（コードレビュー時など）は比べるものが無い
                print(f"SKIP: guard に {a.base} からの変更がありません（コミットの前に流すゲート）")
                return 0
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
    inc = hit(w) - hit(b)
    if inc > n * a.limit / 100:
        print(f"FAIL: 確認＋停止が {inc} 件増えた（上限は記録の {a.limit}%＝{n * a.limit / 100:.0f} 件）")
        return 1
    print(f"OK: 増減 {inc:+d} 件（上限 {n * a.limit / 100:.0f} 件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
