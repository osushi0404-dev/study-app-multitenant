#!/usr/bin/env bash
# I599（plan_I599.md 4-1・4-2・4-6・auto_test TC-01〜TC-21）: レビュー前の中身（git merge-base HEAD origin/develop と違う
#   scripts/claude/ の中身）に届く `bash scripts/claude/…` を、見張りがサンドボックスの中で動くように書き換えること・
#   フックの起動役が分かれた時点の写しでフックを動かすこと・code-review.sh のゲートがレビュー前の中身を手元で流さないこと。
#   一時フォルダに小さなリポジトリ（scripts/claude/ の写しと .claude/hooks/ の本物の写し）を作り、origin/develop に当たる
#   参照を置いて、本物の見張り（scripts/claude/hooks/pretooluse_guard.py）を JSON で流す。本物のリポジトリには何も書かない。
#   FG: 判定・見張り・起動役の写しを壊すと、対応する確かめが不合格になること
# 実行: bash scripts/claude/tests/test_i599_unreviewed_scripts.sh
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 - "$REPO_ROOT" "$TMP" <<'PY'
import json, os, shutil, subprocess, sys, time

REAL, TMP = sys.argv[1], sys.argv[2]
GUARD = os.path.join(REAL, "scripts/claude/hooks/pretooluse_guard.py")
CODE_REVIEW = os.path.join(REAL, "scripts/claude/code-review.sh")
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false",
       "-c", "core.hooksPath=/dev/null"]
results = []


def ck(name, ok):
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name)


def w(path, text, mode=0o644):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(path, mode)


def env_for(root, home=None, path=None):
    e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    e["CLAUDE_PROJECT_DIR"] = root
    e["HOME"] = home or os.path.join(TMP, "home")
    if path:
        e["PATH"] = path
    return e


def make_repo(name, unreviewed_src=None):
    r = os.path.join(TMP, name)
    sc = os.path.join(r, "scripts/claude")
    w(f"{sc}/a.sh", '#!/usr/bin/env bash\nsource "$(dirname "$0")/lib.sh"\necho a\n')
    w(f"{sc}/lib.sh", "echo lib\n")
    w(f"{sc}/b.sh", "echo b\n")
    w(f"{sc}/test-session.sh", 'exec claude -p "$@"\n')
    w(f"{sc}/tests/run-all.sh", 'for t in scripts/claude/tests/test_*.sh; do bash "$t"; done\n')
    w(f"{sc}/tests/test_x.sh", 'touch "$MARK_X"\n')
    w(f"{sc}/tests/stress-repeat.sh", 'bash "$2"\n')
    w(f"{sc}/hooks/h.py", 'import sys\nprint("V1", __file__, sys.stdin.read().strip())\n')
    w(f"{r}/.claude/settings.json", "{}\n")
    w(f"{r}/.gitignore", "*.tmp\nigndir/\n")
    w(f"{sc}/c.sh", 'bash "$(dirname "$0")/helper.tmp"\n')
    hooks = os.path.join(r, ".claude/hooks")
    os.makedirs(hooks, exist_ok=True)
    shutil.copy(unreviewed_src or os.path.join(REAL, ".claude/hooks/unreviewed.py"), f"{hooks}/unreviewed.py")
    shutil.copy(os.path.join(REAL, ".claude/hooks/reviewed-hook.sh"), f"{hooks}/reviewed-hook.sh")
    subprocess.run(["git", "init", "-q", "-b", "work", r], check=True)
    subprocess.run([*GIT, "-C", r, "add", "-A"], check=True)
    subprocess.run([*GIT, "-C", r, "commit", "-q", "-m", "base"], check=True)
    subprocess.run([*GIT, "-C", r, "update-ref", "refs/remotes/origin/develop", "HEAD"], check=True)
    return r


def guard(root, command, guard_path=GUARD, path=None):
    """見張りを流し、出力の JSON（無ければ {}）を返す。"""
    p = subprocess.run([sys.executable, guard_path], cwd=root, capture_output=True, text=True, timeout=60,
                       input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command, "timeout": 7}}),
                       env=env_for(root, path=path))
    out = p.stdout.strip()
    return (json.loads(out).get("hookSpecificOutput", {}) if out else {}), p.returncode


def rewritten(root, command, **kw):
    o, rc = guard(root, command, **kw)
    ui = o.get("updatedInput") or {}
    return rc == 0 and ui.get("command", "").startswith("echo '[I599] ") and ui["command"].endswith(command) \
        and ui.get("timeout") == 7


def untouched(root, command, **kw):
    o, rc = guard(root, command, **kw)
    return rc == 0 and o == {}


def asked(root, command, **kw):
    o, rc = guard(root, command, **kw)
    return rc == 0 and o.get("permissionDecision") == "ask"


def cli(root, *args):
    """判定の CLI を流す（CompletedProcess）。"""
    return subprocess.run([sys.executable, os.path.join(root, ".claude/hooks/unreviewed.py"), *args], cwd=root,
                          capture_output=True, text=True, env=env_for(root))


def broken_unreviewed(name, old, new):
    """判定の写しを壊したもの（FG）。"""
    src = open(os.path.join(REAL, ".claude/hooks/unreviewed.py"), encoding="utf-8").read()
    assert old in src, f"FG の置き換え元が見つからない: {old}"
    p = os.path.join(TMP, f"unreviewed_{name}.py")
    w(p, src.replace(old, new, 1))
    return p


def run_cases(r):
    """TC-01〜TC-08・TC-20 を、リポジトリ r で流し、全部の結果を返す（FG では壊した判定の写しで流す）。"""
    sc = os.path.join(r, "scripts/claude")
    out = {}
    out["TC-01"] = untouched(r, "bash scripts/claude/a.sh")
    out["TC-07"] = all(rewritten(r, c) for c in [
        "bash scripts/claude/../../x.sh", "bash scripts/claude/$X", "bash scripts/claude/`echo a`.sh",
        "bash scripts/claude/*.sh", "bash scripts/claude/~x"])
    outside = os.path.join(TMP, "outside.sh")
    w(outside, "echo outside\n")
    out["TC-06"] = rewritten(r, f"bash scripts/claude/tests/run-all.sh {outside}") and \
        rewritten(r, f"bash scripts/claude/tests/stress-repeat.sh 1 {outside}") and \
        untouched(r, f"bash scripts/claude/tests/run-all.sh {os.path.join(TMP, 'missing.sh')}")
    w(f"{sc}/lib.sh", "echo lib changed\n")
    o, rc = guard(r, "bash scripts/claude/a.sh")
    out["TC-03"] = rc == 0 and (o.get("updatedInput") or {}).get("command", "").startswith("echo '[I599] ") \
        and "scripts/claude/lib.sh" in o["updatedInput"]["command"]
    out["TC-04"] = untouched(r, "bash scripts/claude/b.sh")
    out["TC-20"] = rewritten(r, "bash scripts/claude/b.sh && bash scripts/claude/a.sh")
    subprocess.run([*GIT, "-C", r, "checkout", "-q", "--", "scripts/claude/lib.sh"], check=True)
    w(f"{sc}/new.sh", "echo new\n")
    w(f"{sc}/tests/test_new.sh", "bash scripts/claude/new.sh\n")
    out["TC-02"] = rewritten(r, "bash scripts/claude/tests/test_new.sh")
    os.remove(f"{sc}/new.sh"); os.remove(f"{sc}/tests/test_new.sh")
    w(f"{sc}/tests/test_y.sh", "echo y\n")
    out["TC-05"] = rewritten(r, "bash scripts/claude/tests/run-all.sh")
    os.remove(f"{sc}/tests/test_y.sh")
    subprocess.run([*GIT, "-C", r, "update-ref", "-d", "refs/remotes/origin/develop"], check=True)
    out["TC-08"] = rewritten(r, "bash scripts/claude/b.sh")
    subprocess.run([*GIT, "-C", r, "update-ref", "refs/remotes/origin/develop", "HEAD"], check=True)
    return out


# ---- 本物の判定 ----
r = make_repo("main")
res = run_cases(r)
for k in sorted(res):
    ck(f"{k} {'書き換えない' if k in ('TC-01', 'TC-04') else '中で動くように書き換える'}", res[k])

sc = os.path.join(r, "scripts/claude")
# TC-02 の追加（セキュリティ設計レビュー）: 名前に ' と改行があっても印から命令を足せない
w(f"{sc}/tests/te'st\nz.sh", "echo z\n")
o, _ = guard(r, "bash scripts/claude/tests/run-all.sh")
cmd = (o.get("updatedInput") or {}).get("command", "")
prefix = cmd[: cmd.find(" >&2 && ")]
ck("TC-02b 名前の ' と改行は印の中で _ になり、構文は壊れない",
   cmd.startswith("echo '[I599] ") and prefix.count("'") == 2 and "\n" not in prefix
   and subprocess.run(["bash", "-n", "-c", cmd]).returncode == 0)
os.remove(f"{sc}/tests/te'st\nz.sh")

# TC-23: 引用符の中の文（コミットのメッセージなど）は当たらない（implement で git commit が中に回って失敗した）
w(f"{sc}/new.sh", "echo new\n")
ck("TC-23 引用符の中の `bash scripts/claude/…` の文では書き換えない",
   untouched(r, 'git commit -m "bash scripts/claude/new.sh を足す"')
   and rewritten(r, 'git status && bash scripts/claude/new.sh'))
os.remove(f"{sc}/new.sh")

# TC-24（F1）: 振り向けがスクリプト名にくっついても取り違えない・振り向けの形で区切りが壊れない
w(f"{sc}/new.sh", "echo new\n")
ok24 = all(rewritten(r, c) for c in ["bash scripts/claude/new.sh>/dev/null", "bash scripts/claude/new.sh 2>&1",
                                     "bash scripts/claude/new.sh < /dev/null", "bash scripts/claude/new.sh 2>/dev/null"])
os.remove(f"{sc}/new.sh")
ok24 = ok24 and untouched(r, "bash scripts/claude/b.sh>/dev/null") and untouched(r, "bash scripts/claude/b.sh 2>&1")
ck("TC-24 振り向けつきでもレビュー前のスクリプトは中・変更の無いものは外のまま（F1）", ok24)


def tc24b(root):
    """振り向けの後ろの引数も同じ命令の引数として見る（F7）: ① test-session の許可のモード ② 引数のテストのファイル。"""
    w(os.path.join(root, "scripts/claude/tests/test_new.sh"), "echo new\n")
    got = (asked(root, "bash scripts/claude/test-session.sh x >log --permission-mode bypassPermissions"),
           rewritten(root, "bash scripts/claude/tests/stress-repeat.sh 3 2>/dev/null scripts/claude/tests/test_new.sh"))
    os.remove(os.path.join(root, "scripts/claude/tests/test_new.sh"))
    return got


ck("TC-24b 振り向けの後ろの引数も見る（F7）", all(tc24b(r)))


def tc26(root):
    """置き換え・かっこを含むコマンド（F11・F12）: test-session は常に承認。それ以外は、変更が無ければ外のまま、
    レビュー前の中身があれば読み切らずに中。"""
    ts_ = "bash scripts/claude/test-session.sh x"
    forms = ["bash scripts/claude/b.sh $(true)", "{ bash scripts/claude/b.sh; }", 'bash scripts/claude/b.sh "$HOME"']
    got = [asked(root, f"{ts_} $(true) --permission-mode bypassPermissions"),
           asked(root, f"{ts_} <(true) --permission-mode bypassPermissions")]
    got += [untouched(root, c) for c in forms]
    w(os.path.join(root, "scripts/claude/lib.sh"), "echo changed\n")
    got += [rewritten(root, c) for c in forms]
    subprocess.run([*GIT, "-C", root, "checkout", "-q", "--", "scripts/claude/lib.sh"], check=True)
    return got


ck("TC-26 置き換え・かっこ: test-session は承認・変更が無ければ外のまま・あれば中（F11・F12）", all(tc26(r)))


def tc27(root):
    """F12 のスキルの形（変更なしで外のまま）と F13 の本文の形（変更があっても当たらない）。"""
    got = [untouched(root, 'bash scripts/claude/issue-review.sh --file "$DRAFT"'),
           untouched(root, 'N=$(bash scripts/claude/issue-source.sh gh-number I599)')]
    w(os.path.join(root, "scripts/claude/lib.sh"), "echo changed\n")
    got.append(untouched(root, 'gh pr edit 1 --body "$(cat <<\'EOF\'\n説明 bash scripts/claude/x.sh を使う\nEOF\n)"'))
    got.append(rewritten(root, 'timeout 60 bash scripts/claude/a.sh'))
    subprocess.run([*GIT, "-C", root, "checkout", "-q", "--", "scripts/claude/lib.sh"], check=True)
    return got


ck("TC-27 スキルの呼び出しは変更が無ければ外のまま・本文の文字には当たらない（F12・F13）", all(tc27(r)))


def tc25(root):
    """git が無視するファイル: ① 直接流す（他に変更なし） ② 追跡済みのスクリプトが名前で呼ぶ（他に変更なし）
    ③ 無視されるフォルダの中のファイルを直接流す。3 つとも中で動く。"""
    rsc = os.path.join(root, "scripts/claude")
    w(f"{rsc}/evil.tmp", "echo evil\n")
    w(f"{rsc}/helper.tmp", "echo helper\n")
    w(f"{rsc}/igndir/x.sh", "echo x\n")
    got = (rewritten(root, "bash scripts/claude/evil.tmp"), rewritten(root, "bash scripts/claude/c.sh"),
           rewritten(root, "bash scripts/claude/igndir/x.sh"))
    for f in ("evil.tmp", "helper.tmp"):
        os.remove(f"{rsc}/{f}")
    shutil.rmtree(f"{rsc}/igndir")
    return got


ck("TC-25 git が無視するファイルは、直接・名前で呼ぶ先・無視されるフォルダの中のどれでも中で動く（F2）", all(tc25(r)))

# TC-09: scripts/claude/ を含まないコマンドは git を呼ばない
shim = os.path.join(TMP, "shim")
w(f"{shim}/git", f'#!/usr/bin/env bash\ntouch "{TMP}/git_called"\nexec /usr/bin/git "$@"\n', 0o755)
ck("TC-09 scripts/claude/ を含まないコマンドは今までどおり（出力なし・判定が git を呼ばない）",
   untouched(r, "ls docs", path=f"{shim}:{os.environ['PATH']}") and not os.path.exists(f"{TMP}/git_called"))

# TC-10: 前に付ける書き換えが意味を変えない
import importlib.util
spec = importlib.util.spec_from_file_location("u599", os.path.join(r, ".claude/hooks/unreviewed.py"))
u = importlib.util.module_from_spec(spec); sys.modules["u599"] = u; spec.loader.exec_module(u)
shapes = ["false", "false || true", "printf a | cat", "true; false", "cat <<'E'\nx\nE", "# c\ntrue", "DANGER_OK=1 true"]


def same(prefix_fn):
    for c in shapes:
        new = prefix_fn(c)
        if subprocess.run(["bash", "-n", "-c", new]).returncode != 0:
            return False
        a = subprocess.run(["bash", "-c", c], capture_output=True).returncode
        b = subprocess.run(["bash", "-c", new], capture_output=True).returncode
        if a != b:
            return False
    return True


ck("TC-10 書き換えの前置きは構文と終了コードを変えない",
   same(lambda c: u.rewrite_command(c, u.Result(rewrite=True, reached=["scripts/claude/x.sh"]))))

# TC-11: 確認（ask）にも書き換えが付く
w(f"{sc}/new.sh", "echo new\n")
o, _ = guard(r, "bash scripts/claude/new.sh; printenv")
ck("TC-11 確認（ask）にも書き換えが付く", o.get("permissionDecision") == "ask" and
   (o.get("updatedInput") or {}).get("command", "").startswith("echo '[I599] "))
os.remove(f"{sc}/new.sh")

# TC-12: test-session.sh の引数
ts = "bash scripts/claude/test-session.sh x"
ok12 = untouched(r, f"{ts} --model haiku --permission-mode default --max-turns 3") \
    and asked(r, f"{ts} --settings /tmp/s.json") and asked(r, f"{ts} --settings=/tmp/s.json") \
    and untouched(r, f"{ts} --settings .claude/settings.json") and asked(r, f"{ts} --mcp-config m.json")
# F4: 許可のモードの値・プロジェクトの設定を読まない子
ok12 = ok12 and asked(r, f"{ts} --permission-mode bypassPermissions") and asked(r, f"{ts} --permission-mode=dontAsk") \
    and untouched(r, f"{ts} --permission-mode auto") and asked(r, f"{ts} --setting-sources user") \
    and asked(r, f"{ts} --setting-sources=") and untouched(r, f"{ts} --setting-sources user,project") \
    and untouched(r, f"{ts} --setting-sources user --settings .claude/settings.json") \
    and asked(r, f"{ts} --setting-sources user --settings .gitignore")
w(f"{r}/.claude/settings.json", '{"hooks": {}}\n')
ok12 = ok12 and asked(r, f"{ts} --settings .claude/settings.json")
subprocess.run([*GIT, "-C", r, "checkout", "-q", "--", ".claude/settings.json"], check=True)
ck("TC-12 test-session.sh: 許可の表の引数は通し、それ以外・レビュー前の設定は承認", ok12)

# TC-19: 判定の CLI の終了コード
w(f"{sc}/new.sh", "echo new\n")
ck("TC-19 判定の CLI の終了コード（0 済み・1 中・3 承認・2 使い方）",
   tuple(cli(r, *a).returncode for a in (("check", "--", "bash scripts/claude/b.sh"),
                                         ("check", "--", "bash scripts/claude/new.sh"),
                                         ("check", "--", f"{ts} --mcp-config m.json"), ())) == (0, 1, 3, 2))
os.remove(f"{sc}/new.sh")

# TC-21: 読み取りの上限
def huge_case(root):
    """変更の無い大きなファイルに届く形（変更のあるファイルは読まずに当たりになるので、上限が効くのは読むときだけ）。"""
    w(os.path.join(root, "scripts/claude/huge.sh"), "#" * 1_200_000 + "\n")
    subprocess.run([*GIT, "-C", root, "add", "-A"], check=True)
    subprocess.run([*GIT, "-C", root, "commit", "-q", "-m", "huge"], check=True)
    subprocess.run([*GIT, "-C", root, "update-ref", "refs/remotes/origin/develop", "HEAD"], check=True)
    w(os.path.join(root, "scripts/claude/lib.sh"), "echo changed\n")
    t = time.time()
    p = cli(root, "check", "--", "bash scripts/claude/huge.sh")
    subprocess.run([*GIT, "-C", root, "checkout", "-q", "--", "scripts/claude/lib.sh"], check=True)
    return p, time.time() - t


p, dt = huge_case(make_repo("huge"))
big_ok = p.returncode == 1 and "を超えた" in p.stdout and dt < 20
for i in range(2001):
    w(f"{sc}/many/f{i}.txt", "x\n")
t0 = time.time()
p = cli(r, "check", "--", "bash scripts/claude/b.sh")
many_ok = p.returncode == 1 and "を超えた" in p.stdout and time.time() - t0 < 20
shutil.rmtree(f"{sc}/many")
ck("TC-21 大きなファイル・多すぎるファイルは打ち切って中で動かす（20 秒以内）", big_ok and many_ok)

# ---- 起動役（TC-13〜TC-15） ----
def home_of(root):
    h = os.path.join(TMP, "home_" + os.path.basename(root))
    os.makedirs(h, exist_ok=True)
    return h


home = home_of(r)
fsm = os.path.join(TMP, "fsmonitor_called")
subprocess.run(["git", "-C", r, "config", "core.fsmonitor", f"touch {fsm}; false"], check=True)


def launch(root):
    """起動役を流す。HOME はリポジトリごと（写しの置き場所をリポジトリの間で混ぜない）。"""
    return subprocess.run(["bash", os.path.join(root, ".claude/hooks/reviewed-hook.sh"), "scripts/claude/hooks/h.py"],
                          cwd=root, input="JSONIN", capture_output=True, text=True, timeout=60,
                          env=env_for(root, home=home_of(root)))


p = launch(r)
ck("TC-13 変更が無ければ作業ツリーのフック・git の fsmonitor は動かない",
   p.returncode == 0 and p.stdout.startswith("V1 " + os.path.join(r, "scripts/claude/hooks/h.py"))
   and not os.path.exists(fsm))
base = subprocess.run(["git", "-C", r, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
w(f"{sc}/hooks/h.py", 'print("V2")\n')
p = launch(r)
snap = os.path.join(home, ".cache/claude-reviewed-hooks", base)
ck("TC-14 変更があれば分かれた時点の写しで動き、標準入力が届く",
   p.returncode == 0 and p.stdout.startswith("V1 " + os.path.join(snap, "scripts/claude/hooks/h.py"))
   and p.stdout.strip().endswith("JSONIN") and os.path.isfile(os.path.join(snap, ".complete"))
   and not os.path.exists(fsm))
subprocess.run([*GIT, "-C", r, "update-ref", "-d", "refs/remotes/origin/develop"], check=True)
p = launch(r)
ck("TC-15 基準を求められないときは作業ツリーのフックと理由",
   p.returncode == 0 and p.stdout.startswith("V2") and "[reviewed-hook]" in p.stderr)
subprocess.run([*GIT, "-C", r, "update-ref", "refs/remotes/origin/develop", base], check=True)
subprocess.run([*GIT, "-C", r, "checkout", "-q", "--", "scripts/claude/hooks/h.py"], check=True)
subprocess.run(["git", "-C", r, "config", "--unset", "core.fsmonitor"], check=True)

# ---- code-review.sh のゲート（TC-18） ----
def gates(root, override=""):
    doc = os.path.join(TMP, "auto_test.md")
    w(doc, "## 決定論ゲート（自動実走）\n```bash\nbash scripts/claude/tests/test_new.sh\n"
           "bash scripts/claude/tests/test_x.sh\n```\n")
    for m in ("mark_new", "mark_x"):
        if os.path.exists(os.path.join(TMP, m)):
            os.remove(os.path.join(TMP, m))
    w(os.path.join(root, "scripts/claude/tests/test_new.sh"), f'touch "{TMP}/mark_new"\n')
    e = env_for(root); e["MARK_X"] = os.path.join(TMP, "mark_x"); e["REVIEW_LIB_SOURCE_ONLY"] = "1"
    p = subprocess.run(["bash", "-c", f'. "$1" >/dev/null 2>&1; {override} run_declared_gates "$2"; '
                        'echo "VERDICT=$GATE_VERDICT"; printf "%s" "$GATE_EVIDENCE"', "_", CODE_REVIEW, doc],
                       cwd=root, capture_output=True, text=True, env=e, timeout=120)
    os.remove(os.path.join(root, "scripts/claude/tests/test_new.sh"))
    return p.stdout, os.path.exists(os.path.join(TMP, "mark_new")), os.path.exists(os.path.join(TMP, "mark_x"))


out, new_ran, x_ran = gates(r)
ck("TC-18 code-review.sh はレビュー前のテストを手元で流さず、変更の無いテストは流す",
   not new_ran and x_ran and "VERDICT=OK" in out and "レビュー前の中身のため手元では流さない" in out)

# ---- 「レビュー済み」の定義が判定・起動役・見張りで同じ（簡素化のレビューの指摘。写しが食い違わない） ----
lsrc = open(os.path.join(REAL, ".claude/hooks/reviewed-hook.sh"), encoding="utf-8").read()
gsrc = open(GUARD, encoding="utf-8").read()


def same_defs(lsrc, gsrc):
    safe = " ".join(u.GIT_SAFE_OPTS)
    return u.BASE_REF == "origin/develop" and "merge-base HEAD origin/develop" in lsrc and f"git {safe} -C" in lsrc \
        and "_GIT_SAFE_OPTS = (" + ", ".join(f'"{x}"' for x in u.GIT_SAFE_OPTS) + ")" in gsrc


ck("TC-22 基準（merge-base HEAD origin/develop）と git の安全な -c が判定・起動役・見張りで同じ", same_defs(lsrc, gsrc))
ck("FG TC-22: 起動役の -c を 1 つ消すと不合格", not same_defs(lsrc.replace(" -c submodule.recurse=false", "", 1), gsrc))

# ---- FG（失敗の注入） ----
fg = []
r2 = make_repo("fg_always_ok", broken_unreviewed("always_ok", "def check(command: str, cwd: str | None = None) -> Result:\n",
                                                 "def check(command: str, cwd: str | None = None) -> Result:\n    return Result()\n"))
res2 = run_cases(r2)
fg.append(("FG TC-02・03・05〜08・20: 判定が常に「済み」なら不合格",
           not any(res2[k] for k in ("TC-02", "TC-03", "TC-05", "TC-06", "TC-07", "TC-08", "TC-20"))))
r3 = make_repo("fg_no_reach", broken_unreviewed("no_reach", "        for tok in set(TOKEN_RE.findall(text)):",
                                                "        for tok in ():"))
fg.append(("FG TC-03: たどりを外すと不合格", not run_cases(r3)["TC-03"]))
r4 = make_repo("fg_any_change", broken_unreviewed("any_change", "        hits = _reach(root, start, files, changed)",
                                                 "        hits = sorted(changed)[:5]"))
fg.append(("FG TC-04: 届くかを見ないと不合格", not run_cases(r4)["TC-04"]))
r5 = make_repo("fg_no_runner", broken_unreviewed("no_runner", 'RUNNER_GLOBS = {"scripts/claude/tests/run-all.sh": ("scripts/claude/tests/",)}',
                                                 "RUNNER_GLOBS = {}"))
fg.append(("FG TC-05: まとめて拾う入口の表を空にすると不合格", not run_cases(r5)["TC-05"]))
r6 = make_repo("fg_no_args", broken_unreviewed("no_args", 'EXEC_SUFFIXES = (".sh", ".py")', "EXEC_SUFFIXES = ()"))
fg.append(("FG TC-06: 引数のファイルを見ないと不合格", not run_cases(r6)["TC-06"]))
r7 = make_repo("fg_traceable", broken_unreviewed("traceable", 'UNTRACEABLE_RE = re.compile(r"\\.\\.|[$`*?\\[~\'\\"\\\\]")',
                                                 'UNTRACEABLE_RE = re.compile(r"(?!x)x")'))
fg.append(("FG TC-07: たどれない形の確かめを外すと不合格", not run_cases(r7)["TC-07"]))
r8 = make_repo("fg_base_ok", broken_unreviewed("base_ok", '        res.rewrite, res.why = True, f"レビュー済みの基準（merge-base HEAD {BASE_REF}）を求められない"\n        return res',
                                               "        return res"))
fg.append(("FG TC-08: 基準の失敗を「済み」に倒すと不合格", not run_cases(r8)["TC-08"]))
r9 = make_repo("fg_first_only", broken_unreviewed("first_only", "    for seg in segs:\n", "    for seg in segs[:1]:\n"))
w(os.path.join(r9, "scripts/claude/lib.sh"), "echo changed\n")
fg.append(("FG TC-20: 最初の参照だけを見ると不合格", not rewritten(r9, "bash scripts/claude/b.sh && bash scripts/claude/a.sh")))
fg.append(("FG TC-10: 前置きを || にすると不合格", not same(lambda c: "echo x >&2 || " + c)))
src = open(GUARD, encoding="utf-8").read()
gcopy = os.path.join(TMP, "guard_no_ask_rewrite.py")
w(gcopy, src.replace("    if _REWRITE:\n        out[\"updatedInput\"]", "    if False:\n        out[\"updatedInput\"]", 1))
w(f"{sc}/new.sh", "echo new\n")
o, _ = guard(r, "bash scripts/claude/new.sh; printenv", guard_path=gcopy)
fg.append(("FG TC-11: _ask に書き換えを付けないと不合格", "updatedInput" not in o))
os.remove(f"{sc}/new.sh")
r10 = make_repo("fg_ts_any", broken_unreviewed("ts_any", "def _test_session_ask(args: list[str], root: str, base) -> str | None:\n",
                                               "def _test_session_ask(args: list[str], root: str, base) -> str | None:\n    return None\n"))
fg.append(("FG TC-12: test-session の表を「何でも可」にすると不合格", not asked(r10, f"{ts} --mcp-config m.json")))
r11 = make_repo("fg_cli", broken_unreviewed("cli", "        return 3\n", "        return 0\n"))
fg.append(("FG TC-19: 承認の終了コードを 0 にすると不合格", cli(r11, "check", "--", f"{ts} --mcp-config m.json").returncode != 3))
r12 = make_repo("fg_nolimit", broken_unreviewed("nolimit", "MAX_FILE_BYTES = 1_000_000", "MAX_FILE_BYTES = 10**12"))
p, _ = huge_case(r12)
fg.append(("FG TC-21: 上限を外すと不合格（打ち切りの理由が出ない）", "を超えた" not in p.stdout))
# 起動役（TC-13・TC-14）: 変更の判定を外す・常に写し
for name, old, new, tc in [
        ("always_snap", 'if "${g[@]}" diff --quiet', 'if false && "${g[@]}" diff --quiet', "TC-13"),
        ("never_snap", 'if "${g[@]}" diff --quiet', 'if true || "${g[@]}" diff --quiet', "TC-14")]:
    rr = make_repo(f"fg_{name}")
    assert old in lsrc
    w(os.path.join(rr, ".claude/hooks/reviewed-hook.sh"), lsrc.replace(old, new, 1))
    if tc == "TC-14":
        w(os.path.join(rr, "scripts/claude/hooks/h.py"), 'print("V2")\n')
    p = launch(rr)
    want = "V1 " + os.path.join(rr, "scripts/claude/hooks/h.py")
    fg.append((f"FG {tc}: 起動役の変更の判定を壊すと不合格",
               not p.stdout.startswith(want) if tc == "TC-13" else p.stdout.startswith("V2")))
rr = make_repo("fg_no_reason")
w(os.path.join(rr, ".claude/hooks/reviewed-hook.sh"),
  lsrc.replace('echo "[reviewed-hook] レビュー済みの基準', 'true "[reviewed-hook] レビュー済みの基準', 1))
subprocess.run([*GIT, "-C", rr, "update-ref", "-d", "refs/remotes/origin/develop"], check=True)
fg.append(("FG TC-15: 理由を出さないと不合格", "[reviewed-hook]" not in launch(rr).stderr))
_, new_ran, _ = gates(r, override="gate_reviewed() { return 0; };")
fg.append(("FG TC-18: ゲートの確かめを外すとレビュー前のテストが手元で流れる（不合格）", new_ran))

r13 = make_repo("fg_no_redirect", broken_unreviewed("no_redirect", 'punctuation_chars=";&|()<>")', 'punctuation_chars=";&|()")'))
w(os.path.join(r13, "scripts/claude/new.sh"), "echo new\n")
fg.append(("FG TC-24: 区切りから振り向けを外すと不合格", not rewritten(r13, "bash scripts/claude/new.sh>/dev/null")))
r14 = make_repo("fg_no_ignored", broken_unreviewed("no_ignored", "    return sorted(files | ignored), set(diff) | untracked | ignored",
                                                   "    return sorted(files), set(diff) | untracked"))
got = tc25(r14)
fg.append(("FG TC-25: 無視されるファイルを数えないと ②（名前で呼ぶ先）が不合格", not got[1]))
r15 = make_repo("fg_no_outside", broken_unreviewed("no_outside", "    if outside:\n", "    if False:\n"))
fg.append(("FG TC-25: 一覧の外の出発点を見ないと ③ が不合格", not tc25(r15)[2]))
r16 = make_repo("fg_any_mode", broken_unreviewed("any_mode", 'TS_PERMISSION_MODES = {"default", "manual", "plan", "acceptEdits", "auto"}',
                                                 'TS_PERMISSION_MODES = {"default", "manual", "plan", "acceptEdits", "auto", "bypassPermissions"}'))
fg.append(("FG TC-12（F4）: 許可のモードの表に bypassPermissions を足すと不合格", not asked(r16, f"{ts} --permission-mode bypassPermissions")))
r17 = make_repo("fg_any_sources", broken_unreviewed("any_sources", '    if sources is not None and "project" not in sources.split(",") and not settings_ok:',
                                                    "    if False:"))
fg.append(("FG TC-12（F4）: --setting-sources の確かめを外すと不合格", not asked(r17, f"{ts} --setting-sources user")))
r18b = make_repo("fg_redirect_split2", broken_unreviewed("redirect_split2", "            skip_next = True\n", "            skip_next = False\n            segs.append(cur); cur = []\n"))
fg.append(("FG TC-24b: 振り向けで命令を区切ると不合格", not all(tc24b(r18b))))
r19 = make_repo("fg_any_settings", broken_unreviewed("any_settings", '            settings_ok = settings_ok or rel == ".claude/settings.json"',
                                                    "            settings_ok = True"))
fg.append(("FG TC-12（F8）: どの設定ファイルでも代わりにすると不合格", not asked(r19, f"{ts} --setting-sources user --settings .gitignore")))
r20 = make_repo("fg_parse_all", broken_unreviewed("parse_all", '    if UNPARSED_RE.search(command):\n', "    if False:\n"))
got = tc26(r20)
fg.append(("FG TC-26: 置き換え・かっこの規則を外すと不合格", not got[0] and not all(got[5:])))
r21 = make_repo("fg_unparsed_always", broken_unreviewed("unparsed_always", "    if changed and not res.ask_reason:", "    if True:"))
fg.append(("FG TC-26・27: 変更が無くても中に回すと不合格（F12）", not all(tc26(r21)[2:5]) and not tc27(r21)[0]))
r22 = make_repo("fg_anywhere", broken_unreviewed("anywhere", 'TRIGGER_RE = re.compile(r"(?:^|[;&|({!\\n]|\\$\\()\\s*', 'TRIGGER_RE = re.compile(r"(?:)\\s*'))
fg.append(("FG TC-27: 本文の途中の文字にも当たると不合格（F13）", not tc27(r22)[2]))
for name, ok in fg:
    ck(name, ok)
print(f"---\npass={sum(results)} fail={len(results) - sum(results)}")
sys.exit(0 if all(results) else 1)
PY
