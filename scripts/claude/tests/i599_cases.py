"""I599（第 2 版）の確かめの本体。入口は test_i599_unreviewed_scripts.sh（引数: 本物のリポジトリの最上位・一時フォルダ）。"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys

REAL, TMP = sys.argv[1], sys.argv[2]
GUARD = os.path.join(REAL, "scripts/claude/hooks/pretooluse_guard.py")
CODE_REVIEW = os.path.join(REAL, "scripts/claude/code-review.sh")
JUDGE = os.path.join(REAL, ".claude/hooks/unreviewed.py")
HOOK_LAUNCHER = os.path.join(REAL, ".claude/hooks/reviewed-hook.sh")
VCS = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false",
       "-c", "core.hooksPath=/dev/null"]
LAUNCH = "python3 .claude/hooks/unreviewed.py run"
results = []


def ck(name, ok):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name)


def w(path, text, mode=0o644):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(path, mode)


def env_for(root, **extra):
    e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") and k != "SANDBOX_RUNTIME"}
    e.update({"CLAUDE_PROJECT_DIR": root, "HOME": os.path.join(TMP, "home_" + os.path.basename(root)),
              "PYTHONDONTWRITEBYTECODE": "1", "MARK": os.path.join(root, "mark")})
    e.update(extra)
    os.makedirs(e["HOME"], exist_ok=True)
    return e


def vcs(root, *args, out=False):
    p = subprocess.run([*VCS, *args], cwd=root, check=True, capture_output=out, text=True)
    return p.stdout if out else None


def make_repo(name, judge_src=None):
    r = os.path.join(TMP, name)
    sc = os.path.join(r, "scripts/claude")
    w(f"{sc}/issue-source.sh", 'printf "%s|" "$@" > "$MARK"\n')
    w(f"{sc}/test-session.sh", 'echo session\n')
    w(f"{sc}/other.sh", 'touch "$MARK"\n')
    w(f"{sc}/tests/test_x.sh", 'touch "$MARK_X"\n')
    w(f"{sc}/hooks/h.py", 'import sys\nprint("V1", __file__, sys.stdin.read().strip())\n')
    w(f"{r}/.gitignore", "*.tmp\nigndir/\nmark\n")
    w(f"{r}/.claude/settings.json", "{}\n")
    w(f"{r}/.claude/hooks/unreviewed.py", open(judge_src or JUDGE, encoding="utf-8").read())
    shutil.copy(HOOK_LAUNCHER, f"{r}/.claude/hooks/reviewed-hook.sh")
    vcs(r, "init", "-q", "-b", "work")
    vcs(r, "add", "-A")
    vcs(r, "commit", "-q", "-m", "base")
    vcs(r, "update-ref", "refs/remotes/origin/develop", "HEAD")
    return r


def broken_judge(name, old, new):
    src = open(JUDGE, encoding="utf-8").read()
    assert old in src, f"FG の置き換え元が見つからない: {old}"
    p = os.path.join(TMP, f"judge_{name}.py")
    w(p, src.replace(old, new, 1))
    return p


def guard(root, command, cwd="ROOT", guard_path=GUARD):
    data = {"tool_name": "Bash", "tool_input": {"command": command, "timeout": 7}}
    if cwd is not None:
        data["cwd"] = root if cwd == "ROOT" else cwd
    p = subprocess.run([sys.executable, "-B", guard_path], cwd=root, capture_output=True, text=True, timeout=60,
                       input=json.dumps(data), env=env_for(root))
    out = p.stdout.strip()
    return (json.loads(out).get("hookSpecificOutput", {}) if out else {}), p.returncode


def untouched(root, command, **kw):
    o, rc = guard(root, command, **kw)
    return rc == 0 and o == {}


def blocked(root, command, **kw):
    return guard(root, command, **kw)[1] == 2


def routed(root, command, want, **kw):
    o, rc = guard(root, command, **kw)
    ui = o.get("updatedInput") or {}
    return rc == 0 and ui.get("command") == want and ui.get("timeout") == 7 and "permissionDecision" not in o


def asked(root, command, **kw):
    o, rc = guard(root, command, **kw)
    return rc == 0 and o.get("permissionDecision") == "ask"


def launch(root, *args, **extra):
    """起動役を流す（外の振る舞いを見るので SANDBOX_RUNTIME を外す）。(終了コード, 印の中身, 標準エラー)"""
    mark = os.path.join(root, "mark")
    if os.path.exists(mark):
        os.remove(mark)
    p = subprocess.run([sys.executable, "-B", ".claude/hooks/unreviewed.py", "run", *args], cwd=root,
                       capture_output=True, text=True, timeout=60, env=env_for(root, **extra))
    got = open(mark, encoding="utf-8").read() if os.path.exists(mark) else None
    return p.returncode, got, p.stderr


def not_simple_forms(name="issue-source.sh"):
    s = f"bash scripts/claude/{name}"
    return [f"timeout 5 {s} x", f"X=1 {s} x", f"{s} $(true)", f"{s} `x`", f"{s} x | cat", f"{s} x >o",
            f"{s} x; ls", "{ " + s + " x; }", "bash scripts/claude/other.sh", "bash scripts/claude/../../x.sh",
            "bash scripts/claude/tests/run-all.sh x.sh", f'{VCS[0]} commit -m "{s}"']


# ---- 見張り（TC-01〜TC-06・TC-17） ----
r = make_repo("main")
ck("TC-01 一覧の名前の単体の形は起動役の形に付け替える（timeout を保つ・承認の判定は変えない）",
   routed(r, "bash scripts/claude/issue-source.sh body I1", f"{LAUNCH} issue-source.sh body I1")
   and routed(r, 'bash scripts/claude/issue-source.sh body "I 1"', f'{LAUNCH} issue-source.sh body "I 1"'))
ck("TC-02 単体でない形・一覧に無い名前は何もしない（中で動く）", all(untouched(r, c) for c in not_simple_forms()))
w(f"{r}/scripts/claude/new.sh", 'touch "$MARK"\n')
rc, got, _ = launch(r, "new.sh")
ck("TC-03 新しく書いたスクリプトは外に出ない（見張りは何もしない・起動役は一覧に無いので拒む）",
   untouched(r, "bash scripts/claude/new.sh") and rc == 2 and got is None)
os.remove(f"{r}/scripts/claude/new.sh")
L = f"{LAUNCH} issue-source.sh x"
ck("TC-04 起動役を単体でない形で流すと止める・本文やヒアドキュメントの文字だけなら止めない",
   all(blocked(r, c) for c in [f"{L}; ls", f"{L} $(true)", f"X=1 {L}", f"{L} >o", f"{VCS[0]} status; {L}",
                               f"gh pr view 1 && {L}"])
   and untouched(r, L) and untouched(r, f"cat <<'E'\n{L}\nE") and untouched(r, f"grep -q '{L}' docs/x.md")
   and untouched(r, f'{VCS[0]} commit -m "起動役 {L} を足す"'))
ts_s, ts_l = "bash scripts/claude/test-session.sh x", f"{LAUNCH} test-session.sh x"
ok5 = routed(r, f"{ts_s} --model haiku --permission-mode default",
             f"{LAUNCH} test-session.sh x --model haiku --permission-mode default") \
    and untouched(r, f"{ts_l} --model haiku --permission-mode default") \
    and untouched(r, f"{ts_l} --setting-sources user --settings .claude/settings.json")
for bad in ["--settings /tmp/s.json", "--settings=/tmp/s.json", "--mcp-config m.json",
            "--permission-mode bypassPermissions", "--setting-sources user", "--setting-sources user --settings .gitignore"]:
    o, _ = guard(r, f"{ts_s} {bad}")
    ok5 = ok5 and o.get("permissionDecision") == "ask" and \
        (o.get("updatedInput") or {}).get("command", "").startswith(LAUNCH) and asked(r, f"{ts_l} {bad}")
ck("TC-05 test-session.sh の引数: 表の外は承認（スクリプトの形・起動役の形）", ok5)
rb = make_repo("broken", broken_judge("syntax", "def route(", "def route(:"))
ck("TC-06 判定を読み込めないとき: 起動役の形は止め、スクリプトの形は何もしない（中）",
   blocked(rb, L) and untouched(rb, "bash scripts/claude/issue-source.sh x"))
w(f"{r}/x/.claude/hooks/unreviewed.py", "print('fake')\n")
ck("TC-17 cwd が最上位でない・無いとき: 起動役の形は止め、スクリプトの形は付け替えない",
   blocked(r, L, cwd=os.path.join(r, "x")) and blocked(r, L, cwd=None)
   and untouched(r, "bash scripts/claude/issue-source.sh a", cwd=os.path.join(r, "x"))
   and untouched(r, "bash scripts/claude/issue-source.sh a", cwd=None))
shutil.rmtree(f"{r}/x")

# ---- 起動役（TC-07〜TC-10・TC-16） ----
rc, got, _ = launch(r, "issue-source.sh", "a", "b c")
ck("TC-07 レビュー前の中身が無ければ一覧のスクリプトを動かし、引数がそのまま届く", rc == 0 and got == "a|b c|")


def dirty_cases(root):
    sc = os.path.join(root, "scripts/claude")
    out = []
    for setup, undo in [
            (lambda: w(f"{sc}/other.sh", "echo changed\n"), lambda: vcs(root, "checkout", "-q", "--", "scripts/claude/other.sh")),
            (lambda: w(f"{sc}/n.sh", "echo n\n"), lambda: os.remove(f"{sc}/n.sh")),
            (lambda: w(f"{sc}/evil.tmp", "echo e\n"), lambda: os.remove(f"{sc}/evil.tmp"))]:
        setup()
        rc_, got_, err = launch(root, "issue-source.sh", "a")
        out.append(rc_ == 3 and got_ is None and "! bash scripts/claude/issue-source.sh" in err)
        undo()
    return out


ck("TC-08 レビュー前の中身（書き換え・追跡していない新規・無視されるファイル）があれば止める", all(dirty_cases(r)))
vcs(r, "update-ref", "-d", "refs/remotes/origin/develop")
rc, got, _ = launch(r, "issue-source.sh", "a")
ck("TC-09 基準を求められないときは止める", rc == 3 and got is None)
vcs(r, "update-ref", "refs/remotes/origin/develop", "HEAD")
ok10 = True
for args in [("other.sh",), ("../x.sh",), ("tests/test_x.sh",), ()]:
    rc, got, _ = launch(r, *args)
    ok10 = ok10 and rc == 2 and got is None
ck("TC-10 一覧に無い名前・/・..・名前なしは拒む", ok10)
rc, got, err = launch(r, "issue-source.sh", "a", SANDBOX_RUNTIME="1")
ck("TC-16 サンドボックスの中で動いたら早く失敗する", rc == 4 and got is None and "サンドボックスの中で動いています" in err)


# ---- code-review.sh のゲート（TC-11） ----
def gates(root, override=""):
    doc = os.path.join(TMP, "auto_test.md")
    w(doc, "## 決定論ゲート（自動実走）\n```bash\nbash scripts/claude/tests/test_x.sh\n```\n")
    mark = os.path.join(TMP, "mark_x")
    if os.path.exists(mark):
        os.remove(mark)
    e = env_for(root, MARK_X=mark, REVIEW_LIB_SOURCE_ONLY="1")
    p = subprocess.run(["bash", "-c", f'. "$1" >/dev/null 2>&1; {override} run_declared_gates "$2"; '
                        'echo "VERDICT=$GATE_VERDICT"; printf "%s" "$GATE_EVIDENCE"', "_", CODE_REVIEW, doc],
                       cwd=root, capture_output=True, text=True, env=e, timeout=120)
    return p.stdout, os.path.exists(mark)


out_clean, ran_clean = gates(r)
w(f"{r}/scripts/claude/other.sh", "echo changed\n")
out_dirty, ran_dirty = gates(r)
ck("TC-11 code-review.sh: 変更が無ければゲートのテストを流し、レビュー前の中身があれば手元で流さない",
   ran_clean and "VERDICT=OK" in out_clean and not ran_dirty and "VERDICT=OK" in out_dirty and "⏭" in out_dirty)
_, ran_fg = gates(r, override="gate_reviewed() { return 0; };")
vcs(r, "checkout", "-q", "--", "scripts/claude/other.sh")


# ---- フックの起動役（TC-12） ----
def hook(root):
    return subprocess.run(["bash", ".claude/hooks/reviewed-hook.sh", "scripts/claude/hooks/h.py"], cwd=root,
                          input="JSONIN", capture_output=True, text=True, timeout=60, env=env_for(root))


rh = make_repo("hook")
fsm = os.path.join(TMP, "fsmonitor_called")
vcs(rh, "config", "core.fsmonitor", f"touch {fsm}; false")
p1 = hook(rh)
base = vcs(rh, "rev-parse", "HEAD", out=True).strip()
w(f"{rh}/scripts/claude/hooks/h.py", 'print("V2")\n')
p2 = hook(rh)
snap = os.path.join(TMP, "home_hook", ".cache/claude-reviewed-hooks", base)
vcs(rh, "update-ref", "-d", "refs/remotes/origin/develop")
p3 = hook(rh)
ck("TC-12 フックの起動役: 変更なしは作業ツリー・変更ありは分かれた時点の写し（標準入力が届く）・基準なしは作業ツリーと理由・"
   "fsmonitor は動かない",
   p1.returncode == 0 and p1.stdout.startswith("V1 " + os.path.join(rh, "scripts/claude/hooks/h.py"))
   and p2.returncode == 0 and p2.stdout.startswith("V1 " + os.path.join(snap, "scripts/claude/hooks/h.py"))
   and p2.stdout.strip().endswith("JSONIN") and os.path.isfile(os.path.join(snap, ".complete"))
   and p3.returncode == 0 and p3.stdout.startswith("V2") and "[reviewed-hook]" in p3.stderr
   and not os.path.exists(fsm))

# ---- 「レビュー済み」の定義が判定・フックの起動役・見張りで同じ（TC-14） ----
spec = importlib.util.spec_from_file_location("u599", JUDGE)
u = importlib.util.module_from_spec(spec)
sys.modules["u599"] = u
spec.loader.exec_module(u)
lsrc = open(HOOK_LAUNCHER, encoding="utf-8").read()
gsrc = open(GUARD, encoding="utf-8").read()


def same_defs(lsrc_, gsrc_):
    safe = " ".join(u.GIT_SAFE_OPTS)
    return u.BASE_REF == "origin/develop" and "merge-base HEAD origin/develop" in lsrc_ and f"{VCS[0]} {safe} -C" in lsrc_ \
        and "_GIT_SAFE_OPTS = (" + ", ".join(f'"{x}"' for x in u.GIT_SAFE_OPTS) + ")" in gsrc_


ck("TC-14 基準と git の安全な -c が判定・フックの起動役・見張りで同じ", same_defs(lsrc, gsrc))

# ---- FG（失敗の注入） ----
fg = []
r1 = make_repo("fg_no_route", broken_judge("no_route", "    new = f\"{LAUNCH} {m.group('name')}{m.group('rest')}\"",
                                           "    return Route()"))
fg.append(("FG TC-01: 付け替えを外すと不合格",
           not routed(r1, "bash scripts/claude/issue-source.sh body I1", f"{LAUNCH} issue-source.sh body I1")))
r2 = make_repo("fg_no_simple", broken_judge("no_simple", "    simple = NOT_SIMPLE_RE.search(command) is None", "    simple = True"))
fg.append(("FG TC-02・TC-04: 単体の確かめを外すと不合格",
           not untouched(r2, "bash scripts/claude/issue-source.sh $(true)") and not blocked(r2, f"{L} $(true)")))
r2b = make_repo("fg_no_boundary", broken_judge("no_boundary", '(first in OUTSIDE_FIRST_WORDS and LAUNCH_AT_BOUNDARY_RE.search(command) is not None)',
                                               "False"))
fg.append(("FG TC-04: git・gh で始まり区切りの後に起動役がある形を見ないと不合格", not blocked(r2b, f"{VCS[0]} status; {L}")))
r3 = make_repo("fg_list_new", broken_judge("list_new", '"adversarial-review.sh",', '"adversarial-review.sh", "new.sh",'))
w(f"{r3}/scripts/claude/new.sh", 'touch "$MARK"\n')
vcs(r3, "add", "-A")
vcs(r3, "commit", "-q", "-m", "new")
vcs(r3, "update-ref", "refs/remotes/origin/develop", "HEAD")
fg.append(("FG TC-03: 一覧に new.sh を足すと外に出る（確かめが一覧で効いている）", launch(r3, "new.sh")[0] == 0))
r4 = make_repo("fg_ts_any", broken_judge("ts_any", "def _test_session_ask(args: list[str], root: str, base) -> str | None:\n",
                                         "def _test_session_ask(args: list[str], root: str, base) -> str | None:\n    return None\n"))
fg.append(("FG TC-05: test-session の表を「何でも可」にすると不合格", not asked(r4, f"{ts_s} --mcp-config m.json")))
r5 = make_repo("fg_cwd", broken_judge("cwd", "def _same_dir(a: str | None, b: str) -> bool:\n",
                                      "def _same_dir(a: str | None, b: str) -> bool:\n    return True\n"))
fg.append(("FG TC-17: cwd の確かめを外すと不合格", not blocked(r5, L, cwd=os.path.join(r5, "x"))))
r6 = make_repo("fg_always_stop", broken_judge("always_stop", "    if found is None or found:\n        why", "    if True:\n        why"))
fg.append(("FG TC-07: 起動役が常に止めると不合格", launch(r6, "issue-source.sh", "a")[0] != 0))
r7 = make_repo("fg_no_diff", broken_judge("no_diff", "    return set(diff) | untracked | ignored",
                                          "    return untracked | ignored"))
r8 = make_repo("fg_no_ignored", broken_judge("no_ignored", "    return set(diff) | untracked | ignored",
                                             "    return set(diff) | untracked"))
fg.append(("FG TC-08: 差を見ない写し（①）・無視されるファイルを数えない写し（③）で不合格",
           not dirty_cases(r7)[0] and not dirty_cases(r8)[2]))
r9 = make_repo("fg_base_ok", broken_judge("base_ok", "    b = _base(root)\n    if b is None:\n        return None\n",
                                          "    b = _base(root)\n    if b is None:\n        return []\n"))
vcs(r9, "update-ref", "-d", "refs/remotes/origin/develop")
fg.append(("FG TC-09: 基準の失敗を「なし」に倒すと不合格", launch(r9, "issue-source.sh", "a")[0] != 3))
r10 = make_repo("fg_name", broken_judge("name", "if not argv or argv[0] not in OUTSIDE_SCRIPTS:",
                                        "if not argv:"))
fg.append(("FG TC-10: 名前の確かめを外すと一覧に無い other.sh が動く", launch(r10, "other.sh")[1] is not None))
r11 = make_repo("fg_sandbox", broken_judge("sandbox", '    if os.environ.get("SANDBOX_RUNTIME"):', "    if False:"))
fg.append(("FG TC-16: 中の確かめを外すと不合格", launch(r11, "issue-source.sh", "a", SANDBOX_RUNTIME="1")[0] != 4))
fg.append(("FG TC-11: gate_reviewed を常に真にすると、レビュー前の中身があってもテストが流れる", ran_fg))
fg.append(("FG TC-14: フックの起動役の -c を 1 つ消すと不合格",
           not same_defs(lsrc.replace(" -c submodule.recurse=false", "", 1), gsrc)))
for name, old, new in [
        ("always_snap", 'if [ -f "$snap/.complete" ] && [ -f "$snap/$rel" ]; then', 'if true; then'),
        ("never_snap", 'if "${g[@]}" diff --quiet', 'if true || "${g[@]}" diff --quiet')]:
    rr = make_repo(f"fg_{name}")
    assert old in lsrc
    w(os.path.join(rr, ".claude/hooks/reviewed-hook.sh"), lsrc.replace(old, new, 1))
    if name == "never_snap":
        w(os.path.join(rr, "scripts/claude/hooks/h.py"), 'print("V2")\n')
        fg.append(("FG TC-12: 差を見ないと、変更があっても作業ツリーで動いて不合格", hook(rr).stdout.startswith("V2")))
    else:
        fg.append(("FG TC-12: 常に写しにすると、作業ツリーの印にならない",
                   not hook(rr).stdout.startswith("V1 " + os.path.join(rr, "scripts/claude/hooks/h.py"))))

for name, ok in fg:
    ck(name, ok)
print(f"---\npass={sum(results)} fail={len(results) - sum(results)}")
sys.exit(0 if all(results) else 1)
