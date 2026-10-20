#!/usr/bin/env python3
"""I174（plan_I174.md 0-13）: 本物の bash を「正解」にした差分テスト。

危険なコマンドを、前置きの文脈 × つなぎ方 × 書き方 × 包み方 で組み合わせたスクリプトを生成し、
(1) mktemp -d の中で本物の bash に実行させて、危険なコマンドが実際に実行されるかを調べる
    （git と rm は「危険な引数で呼ばれたら印を出すだけ」の関数に置き換えて export -f する。
     ほかに使うのは echo・cat・wc・tr などの無害なコマンドだけ）
(2) 同じスクリプトを guard に判定させる
bash が危険なコマンドを実行するのに guard が停止（2）しなければ不合格（確認〔ASK〕への格下げも不合格）。
bash が実行しない形で guard が止めた・確認にした「余計な停止」も不合格（コメント等の読み飛ばしが外れたことを検知する）。
guard が見つからない・読み込めないときに全件を「停止」と誤読しないよう、先に対照の 2 件を確かめる。

使い方: python3 scripts/claude/tests/guard_bash_oracle.py [-v]
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

REPO = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
GUARD = os.environ.get("GUARD") or os.path.join(REPO, "scripts/claude/hooks/pretooluse_guard.py")
MARK = "__RAN__"
STUBS = (
    # git: reset --hard・push --force・保護ブランチ（main / develop）への push で印を出す（bash が展開した後の引数で見る）
    # （-f・--force-with-lease・+参照・HEAD:main の形も印を出す。将来 DANGERS に足したときに「実行しない形」と誤分類しないため）
    'git(){ case "$1" in reset) [ "$2" = "--hard" ] && echo ' + MARK + ';; '
    'push) case " $* " in *" --force "*|*" --force-with-lease"*|*" -f "*|*" +"*|*" main "*|*" develop "*'
    '|*":main "*|*":develop "*|*"/main "*|*"/develop "*) echo ' + MARK + ';; esac;; esac; }\n'
    'rm(){ case " $* " in *" -r""f "*|*" -f""r "*|*" -R""f "*|*" -f""R "*|*" -r "*|*" -R "*) echo ' + MARK + ';; esac; }\n'
    # git.exe（WSL から Windows の git を呼ぶ形）も同じ印を出す
    'git.exe(){ git "$@"; }\n'
    "export -f git rm git.exe\n"
)
RM = "rm -r" + "f"   # ソース上の連続表記を避ける（このファイルを検索・編集するコマンドへの誤反応防止）

# 危険なコマンド: (先頭の語, 残り)。継続で折るときに位置を選ぶため分けておく
DANGERS = [
    ("git", "reset --hard origin/develop"),
    ("git", "push --force origin develop"),
    ("git", "push origin main"),
    (RM.split()[0], RM.split()[1] + " build_tmp"),
    # 引数そのものを $'…' のエスケープで書く形（bash は \x6d を m に展開する）
    ("git", "reset $'\\x2d\\x2dhard' origin/develop"),
    ("git", "push origin $'\\x6dain'"),
    ("git", "push $'\\055\\055force' origin feature/x"),
    (RM.split()[0], "$'-\\x72f' build_tmp"),
    # STUBS で印を出す別の書き方（第 2 周: 印を広げても、それを通るケースが無ければ測れない）
    ("rm", "-f" + "r build_tmp"),
    ("rm", "-f" + "R build_tmp"),
    ("git", "push -f origin feature/x"),
    ("git", "push origin +feature/x"),
    ("git", "push origin HEAD:main"),
    # 第 3 周: git.exe・-f の無い rm -r
    ("git.exe", "reset --hard origin/develop"),
    ("git.exe", "push origin main"),
    ("rm", "-r build_tmp"),
]
# 前置きの文脈: (前置き, 使えるつなぎ方)。改行でしかつなげないもの（ヒアドキュメント・コメント）は "\n" だけ
NL_ONLY = ("\n",)
ANY = ("\n", " && ", "; ")
CONTEXTS = [
    ("", ("",)),
    ('echo "fix #293"', ANY),
    ("echo 'fix #293'", ANY),
    ("echo $'it\\'s'", ANY),
    ("echo PR#293", ANY),
    ('echo "C:\\\\"', ANY),
    ("echo $((1 << 2))", ANY),
    ("wc -c <<< EOF", ANY),
    ("tr a-z A-Z <<< 'hello'", ANY),
    ("echo a # memo \\", NL_ONLY),
    ("# Windows: C:\\work\\", NL_ONLY),
    ("cat > n.md <<'EOF'\nline \\\nEOF", NL_ONLY),
    ("cat > n.md <<EOF\nline\nEOF", NL_ONLY),
    ("cat > n.md <<-EOF\n\tline\n\tEOF", NL_ONLY),
    ("cat > n.md <<'EOF-PR'\ndon't\nEOF-PR", NL_ONLY),
    ("cat > n.md <<\"EOF\"\n# x \\\nEOF", NL_ONLY),
]


def forms(head: str, rest: str):
    """書き方: 1 行・先頭の語の後で折る・最後の引数の前で折る。"""
    words = rest.split()
    yield f"{head} {rest}"
    yield f"{head} \\\n  {rest}"
    yield f"{head} {' '.join(words[:-1])} \\\n  {words[-1]}"


def wraps(body: str):
    """包み方: そのまま・bash -c '…'（単一引用符を含まないとき）・bash <<'X' … X。"""
    yield body
    if "'" not in body:
        yield f"bash -c '{body}'"
    if "\nX\n" not in body and not body.startswith("X\n"):
        yield f"bash <<'X'\n{body}\nX"


def cases():
    for head, rest in DANGERS:
        for pre, joins in CONTEXTS:
            for join in joins:
                for f in forms(head, rest):
                    for w in wraps(f"{pre}{join}{f}" if pre else f):
                        yield w
        # bash が実行しない形（コメント・ヒアドキュメントの本文・引用符の中）: 余計な停止を測る
        one = f"{head} {rest}"
        yield f"# {one}"
        yield f"echo ok # {one}"
        yield f"cat > n.md <<'EOF'\n{one}\nEOF"
        yield f"cat > n.md <<EOF\n{one}\nEOF"
        yield f'echo "{one}"'
        yield f"echo '{one}'"
        yield f"git commit -m \"docs: {one} の説明\""
        # 入れ子のシェルの中のコメント・ヒアドキュメントの本文（内側の読み飛ばしが外れたことも余計な停止で検知する）
        yield f"bash <<'X'\necho ok # {one}\nX"
        yield f"bash <<'X'\ncat > n.md <<'EOF'\n{one}\nEOF\nX"
        if "'" not in one:
            yield f"bash -c 'echo ok # {one}'"


def run_bash(script: str) -> bool:
    d = tempfile.mkdtemp(prefix="i174_oracle_")
    try:
        p = subprocess.run(["bash", "-c", STUBS + script], cwd=d, capture_output=True, text=True, timeout=10,
                           env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": d})
        return MARK in p.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def run_guard(script: str) -> str:
    p = subprocess.run([sys.executable, "-I", GUARD], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": script}}),
                       capture_output=True, text=True, cwd=REPO, timeout=60)
    if p.returncode == 2:
        return "2"
    if p.returncode == 0 and '"ask"' in p.stdout:
        return "ASK"
    return str(p.returncode)


def main() -> int:
    if not shutil.which("bash"):
        print("SKIP: bash がありません")
        return 0
    verbose = "-v" in sys.argv
    if not os.path.isfile(GUARD):
        print(f"FAIL guard がありません: {GUARD}")
        return 1
    # 対照: 無害なコマンドは 0・危険なコマンドは 2。guard が動いていないと終了コード 2 を「停止」と誤読するため
    control = {"echo ok": "0", "git reset --hard origin/develop": "2"}
    for c, want in control.items():
        if run_guard(c) != want:
            print(f"FAIL 対照 {c!r} が {run_guard(c)}（期待 {want}）: guard が正しく動いていません")
            return 1
    scripts = list(dict.fromkeys(cases()))
    with ThreadPoolExecutor(12) as ex:
        ran = list(ex.map(run_bash, scripts))
        got = list(ex.map(run_guard, scripts))
    miss = [(s, g) for s, r, g in zip(scripts, ran, got) if r and g != "2"]
    over = [(s, g) for s, r, g in zip(scripts, ran, got) if not r and g != "0"]
    for s, g in miss:
        print(f"FAIL bash は実行するのに guard={g} :: " + s.replace("\n", "⏎"))
    for s, g in over:
        print(f"FAIL bash は実行しないのに guard={g}（余計な停止） :: " + s.replace("\n", "⏎"))
    print("---")
    print(f"cases={len(scripts)} bash実行={sum(ran)} 見逃し={len(miss)} 余計な停止={len(over)}")
    if verbose:
        print("（見逃しには確認〔ASK〕への格下げを含む）")
    return 1 if miss or over else 0


if __name__ == "__main__":
    sys.exit(main())
