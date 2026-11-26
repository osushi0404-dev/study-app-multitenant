"""I599（第 2 版）・I610・I615 の確かめの本体。入口は test_i599_unreviewed_scripts.sh（引数: 本物のリポジトリの最上位・一時フォルダ）。"""
import fnmatch
import glob
import importlib.util
import json
import os
import re
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
    # I615: 部品を同じフォルダから読む入口と、レビュー役の定義（印に部品の場所と引数を書く）
    w(f"{sc}/code-review.sh", '. "$(dirname "${BASH_SOURCE[0]}")/review-process-lib.sh"\n'
      'REVIEWER_AGENT="code-reviewer"\nmark_it "$@"\n')
    w(f"{sc}/review-process-lib.sh", 'mark_it() { printf \'%s|\' "V1 ${BASH_SOURCE[0]}" "$@" > "$MARK"; }\n')
    w(f"{r}/.claude/agents/code-reviewer.md", "reviewer\n")
    w(f"{r}/.gitignore", "*.tmp\nigndir/\nmark\n")
    w(f"{r}/.claude/settings.json", "{}\n")
    w(f"{r}/.claude/hooks/unreviewed.py", open(judge_src or JUDGE, encoding="utf-8").read())
    shutil.copy(HOOK_LAUNCHER, f"{r}/.claude/hooks/reviewed-hook.sh")
    vcs(r, "init", "-q", "-b", "work")
    vcs(r, "add", "-A")
    vcs(r, "commit", "-q", "-m", "base")
    vcs(r, "update-ref", "refs/remotes/origin/develop", "HEAD")
    return r


def broken_judge(name, old, new, *more, src_path=JUDGE):
    """判定（既定）・見張りなどの写しを、置き換えの組（old, new, old2, new2, …）で壊して一時のファイルに書く。"""
    src = open(src_path, encoding="utf-8").read()
    pairs = [(old, new)] + list(zip(more[::2], more[1::2]))
    for o, n in pairs:
        assert o in src, f"FG の置き換え元が見つからない: {o}"
        src = src.replace(o, n, 1)
    p = os.path.join(TMP, f"judge_{name}.py")
    w(p, src)
    return p


def guard_proc(root, command, cwd="ROOT", guard_path=GUARD):
    data = {"tool_name": "Bash", "tool_input": {"command": command, "timeout": 7}}
    if cwd is not None:
        data["cwd"] = root if cwd == "ROOT" else cwd
    return subprocess.run([sys.executable, "-B", guard_path], cwd=root, capture_output=True, text=True, timeout=60,
                          input=json.dumps(data), env=env_for(root))


def guard(root, command, cwd="ROOT", guard_path=GUARD):
    p = guard_proc(root, command, cwd, guard_path)
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
            "bash scripts/claude/tests/run-all.sh x.sh", f'{VCS[0]} commit -m "{s}"',
            f"{s} x [-]-y", f"{s} x *", f"{s} x ?"]


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
w(f"{r}/--dangerously-skip-permissions", "")
ck("TC-05b test-session.sh の危ない引数をワイルドカードで書いても付け替えない（中で動く・F23）",
   untouched(r, f"{ts_s} [-]-dangerously-skip-permissions") and untouched(r, f"{ts_s} --dangerously-skip-permission?"))
os.remove(f"{r}/--dangerously-skip-permissions")


def load_judge(path):
    spec = importlib.util.spec_from_file_location("i599_judge", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["i599_judge"] = mod
    spec.loader.exec_module(mod)
    return mod


def doc_calls(root, judge):
    """スキルとサブエージェントの定義に書いた、外で動かす一覧のスクリプトの呼び出し（置き換えの後の形）。"""
    names = "|".join(re.escape(n) for n in sorted(judge.OUTSIDE_SCRIPTS))
    head = re.compile(r"\s*\S*bash scripts/claude/(?:" + names + r")(?:\s|$)")
    files = glob.glob(os.path.join(root, ".claude/skills/*/SKILL.md")) + glob.glob(os.path.join(root, ".claude/agents/*.md"))
    out = []
    for f in sorted(files):
        fenced = False
        for no, line in enumerate(open(f, encoding="utf-8").read().splitlines(), 1):
            if line.strip().startswith("```"):
                fenced = not fenced
                continue
            cands = [re.sub(r"\s+#\s.*$", "", line)] if fenced else re.findall(r"`([^`]*)`", line)
            for c in cands:
                if not head.match(c):
                    continue
                # スキルの読み込みで置き換わる引数・文書の置き場の印（<…>・I###）を、実際に入る形にする
                c = re.sub(r"\$\{?ARGUMENTS\}?|I\$\{ISSUE_NUM\}|I###", "I999", c)
                out.append((os.path.relpath(f, root), no, re.sub(r"<[^<>]*>", "x", c).strip()))
    return out


def excluded_patterns(settings_path):
    return json.load(open(settings_path, encoding="utf-8")).get("sandbox", {}).get("excludedCommands", [])


def doc_calls_routed(root, judge, patterns=None):
    """付け替えた形が、外に出る型（excludedCommands。公式は * を任意の文字列として照らす）のどれかに当たることまで見る。"""
    pats = excluded_patterns(os.path.join(REAL, ".claude/settings.json")) if patterns is None else patterns
    calls = doc_calls(root, judge)
    bad = []
    for c in calls:
        new = judge.route(c[2], REAL, REAL).new_command
        if not new or not any(fnmatch.fnmatchcase(new, p) for p in pats):
            bad.append(c)
    for f, no, c in bad:
        print(f"  付け替わらない・外に出る型に当たらない呼び出し: {f}:{no}: {c}")
    return len(calls) >= 10 and not bad


J = load_judge(JUDGE)
ck("TC-18 スキル・サブエージェントの定義に書いた一覧のスクリプトの呼び出しは、すべて単体の形で、付け替えた形が外に出る型に当たる（F22・V6）",
   doc_calls_routed(REAL, J))

# ---- 起動役（TC-07・TC-08・TC-10・TC-16・I615 の TC-01〜TC-03） ----
SNAPS = ".cache/claude-reviewed-snapshots"


def snapdir(root):
    """BASE（origin/develop の指すコミット）の写しの場所。HOME は env_for が決める。"""
    b = vcs(root, "rev-parse", "refs/remotes/origin/develop", out=True).strip()
    return os.path.join(env_for(root)["HOME"], SNAPS, b)


def lib_mark(root, *args):
    return "V1 " + os.path.join(snapdir(root), "scripts/claude/review-process-lib.sh") + "|" + "".join(a + "|" for a in args)


rc, got, _ = launch(r, "issue-source.sh", "a", "b c")
ck("TC-07 変更が無いとき写しの入口を動かし、引数がそのまま届く", rc == 0 and got == "a|b c|")

DIRTY_SETUPS = [
    (lambda sc: w(f"{sc}/other.sh", "echo changed\n"), "scripts/claude/other.sh"),
    (lambda sc: w(f"{sc}/n.sh", "echo n\n"), "scripts/claude/n.sh"),
    (lambda sc: w(f"{sc}/evil.tmp", "echo e\n"), "scripts/claude/evil.tmp")]


def undo(root, rel):
    if subprocess.run([*VCS, "ls-files", "--error-unmatch", rel], cwd=root, capture_output=True).returncode == 0:
        vcs(root, "checkout", "-q", "--", rel)
    else:
        os.remove(os.path.join(root, rel))


def dirty_cli(root, judge=None):
    jp = judge or os.path.join(root, ".claude/hooks/unreviewed.py")
    return subprocess.run([sys.executable, "-B", jp, "dirty"], cwd=root, capture_output=True, text=True,
                          timeout=60, env=env_for(root)).returncode


def dirty_cases(root):
    """dirty の CLI（code-review.sh のゲートが使う）: 書き換え・新規・無視されるファイルで 1。"""
    out = []
    for setup, rel in DIRTY_SETUPS:
        setup(os.path.join(root, "scripts/claude"))
        out.append(dirty_cli(root) == 1)
        undo(root, rel)
    return out


ck("TC-08 dirty の CLI: レビュー前の中身（書き換え・追跡していない新規・無視されるファイル）があれば 1・無ければ 0",
   all(dirty_cases(r)) and dirty_cli(r) == 0)


def unrelated_cases(root):
    """TC-01（I615）: 関係しない書き換え・新規・無視されるファイルがあっても、写しの入口と部品が動く。"""
    for setup, rel in DIRTY_SETUPS:
        setup(os.path.join(root, "scripts/claude"))
        rc_, got_, err = launch(root, "code-review.sh", "a", "b c")
        undo(root, rel)
        yield rc_ == 0 and got_ == lib_mark(root, "a", "b c") and "[unreviewed run]" not in err


PART_SETUPS = [
    lambda root: w(f"{root}/scripts/claude/code-review.sh", 'printf EVIL > "$MARK"\n'),
    lambda root: w(f"{root}/scripts/claude/review-process-lib.sh", 'mark_it() { printf EVIL > "$MARK"; }\n'),
    lambda root: w(f"{root}/.claude/agents/code-reviewer.md", "changed\n")]


def part_cases(root):
    """TC-02（I615）: 入口・部品・レビュー役の定義の書き換え（未コミット・コミット済み）で 75・何も動かない・`!` の案内。"""
    for commit in (False, True):
        for setup in PART_SETUPS:
            setup(root)
            if commit:
                vcs(root, "add", "-A")
                vcs(root, "commit", "-q", "-m", "part")
            rc_, got_, err = launch(root, "code-review.sh", "a")
            vcs(root, "reset", "-q", "--hard", "refs/remotes/origin/develop")
            yield rc_ == 75 and got_ is None and "! bash scripts/claude/code-review.sh a" in err


ck("TC-I615-01 関係しない変更があっても、起動役は写しの入口・部品を動かし、`!` を頼まない（AC1）",
   all(unrelated_cases(r)))
ck("TC-I615-02 入口・部品・レビュー役の定義を変えると（未コミット・コミット済み）、75 で何も動かさず `!` を案内する（AC2）",
   all(part_cases(r)))


def snapfail_cases(root):
    """TC-03（I615）: 基準なし・写しを作れないときは 75・何も動かさない・理由と `!` の案内。"""
    vcs(root, "update-ref", "-d", "refs/remotes/origin/develop")
    rc_a, got_a, err_a = launch(root, "issue-source.sh", "a")
    vcs(root, "update-ref", "refs/remotes/origin/develop", "HEAD")
    home = env_for(root)["HOME"]
    shutil.rmtree(os.path.join(home, ".cache"), ignore_errors=True)
    w(os.path.join(home, ".cache"), "not a dir\n")      # 写しの置き場所を作れない
    rc_b, got_b, err_b = launch(root, "issue-source.sh", "a")
    os.remove(os.path.join(home, ".cache"))
    return (rc_a == 75 and got_a is None and "基準" in err_a and "! bash scripts/claude/issue-source.sh a" in err_a
            and rc_b == 75 and got_b is None and "写しを作れません" in err_b)


ck("TC-I615-03 基準なし・写しを作れないときは、作業ツリーで動かさず 75（AC3）", snapfail_cases(make_repo("snapfail")))
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


def ran_in(p, where):
    """フックが where（写し・作業ツリーの最上位）の h.py で動き、0 で終わったか。"""
    return p.returncode == 0 and p.stdout.startswith("V1 " + os.path.join(where, "scripts/claude/hooks/h.py"))


rh = make_repo("hook")
fsm = os.path.join(TMP, "fsmonitor_called")
vcs(rh, "config", "core.fsmonitor", f"touch {fsm}; false")
snap = snapdir(rh)
p1 = hook(rh)
w(f"{rh}/scripts/claude/hooks/h.py", 'print("V2")\n')
p2 = hook(rh)
vcs(rh, "update-ref", "-d", "refs/remotes/origin/develop")
p3 = hook(rh)
ck("TC-12 フックの起動役: 変更なしも変更ありも分かれた時点の写し（標準入力が届く・I610）・基準なしは作業ツリーと理由・"
   "fsmonitor は動かない",
   ran_in(p1, snap) and ran_in(p2, snap) and p2.stdout.strip().endswith("JSONIN")
   and os.path.isfile(os.path.join(snap, ".complete"))
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

# ---- I610: フックの起動役はいつも写し・-I（TC-12b〜d・plan_I610.md 4-4） ----
# FG の置き換え元（本体に無ければ assert で落ちる）
MAKE_SNAP = '  _reviewed_snapshot_make "$root" "$base" "$cache"\n}'
CALL_SNAP = '  snap="$(reviewed_snapshot "$root" </dev/null)"'
RUN_SNAP = 'exec python3 -I "$snap/$rel" "$@"'


def launcher_variant(name, old, new, count=1):
    """起動役の写しを壊した一時のリポジトリ（本物は書き換えない）。count=-1 は最後の 1 か所だけを置き換える。"""
    assert old in lsrc, f"FG の置き換え元が見つからない: {old}"
    src = lsrc.replace(old, new, 1) if count == 1 else new.join(lsrc.rsplit(old, 1))
    rr = make_repo(name)
    w(os.path.join(rr, ".claude/hooks/reviewed-hook.sh"), src)
    return rr


def ignored_case(root):
    """TC-12b: 無視されるファイル（*.tmp）が scripts/claude/hooks/ にあっても、写しの道で動く。"""
    w(f"{root}/scripts/claude/hooks/x.tmp", "x\n")
    return ran_in(hook(root), snapdir(root))


def evil_case(root):
    """TC-12c: BASE に置いた json.py（写しにも入る）を、フックが読み込まない（-I）。"""
    w(f"{root}/scripts/claude/hooks/json.py", 'print("EVIL")\n')
    w(f"{root}/scripts/claude/hooks/h.py", 'import json\nimport sys\nprint("V1", __file__, sys.stdin.read().strip())\n')
    vcs(root, "add", "-A")
    vcs(root, "commit", "-q", "-m", "evil base")
    vcs(root, "update-ref", "refs/remotes/origin/develop", "HEAD")
    p = hook(root)
    return ran_in(p, snapdir(root)) and "EVIL" not in p.stdout


def all_dash_i(src):
    """TC-12d: フックの起動役の python3（コメントの行を除く）がすべて -I 付き。道は 2 つ（写しで動かす・
    基準なし／写しを作れないときの作業ツリー。I615 でまとめた）なので 2 か所以上。"""
    code = [x for x in src.splitlines() if not x.lstrip().startswith("#")]
    uses = [m for x in code for m in re.finditer(r"\bpython3\b(?P<after>.{0,4})", x)]
    return len(uses) >= 2 and all(m.group("after").startswith(" -I ") for m in uses)


ck("TC-12b 無視されるファイルが scripts/claude/hooks/ にあっても、フックは写しの道で動く", ignored_case(make_repo("hook_ignored")))
ck("TC-12c フックは、置き場所の json.py を読み込まない（-I）", evil_case(make_repo("hook_evil")))
ck("TC-12d フックの起動役の python3 がすべて -I 付き", all_dash_i(lsrc))

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
r6 = make_repo("fg_always_stop", broken_judge("always_stop", "    if hit:\n", "    if True:\n"))
fg.append(("FG TC-07: 起動役が常に止めると不合格", launch(r6, "issue-source.sh", "a")[0] != 0))
r7 = make_repo("fg_no_diff", broken_judge("no_diff", "    return set(diff) | untracked | ignored",
                                          "    return untracked | ignored"))
r8 = make_repo("fg_no_ignored", broken_judge("no_ignored", "    return set(diff) | untracked | ignored",
                                             "    return set(diff) | untracked"))
fg.append(("FG TC-08: 差を見ない写し（①）・無視されるファイルを数えない写し（③）で不合格",
           not dirty_cases(r7)[0] and not dirty_cases(r8)[2]))
fg.append(("FG TC-I615-02: 差を見ない写しで、コミットした部品の書き換えを見落として不合格", not all(part_cases(r7))))
r9 = make_repo("fg_base_ok", broken_judge("base_ok", "    b = _base(root)\n    if b is None:\n        return None\n",
                                          "    b = _base(root)\n    if b is None:\n        return []\n"))
vcs(r9, "update-ref", "-d", "refs/remotes/origin/develop")
fg.append(("FG TC-08: 基準の失敗を「なし」に倒すと dirty が 0 になり不合格", dirty_cli(r9) == 0))
r10 = make_repo("fg_name", broken_judge("name", "if not argv or argv[0] not in OUTSIDE_SCRIPTS:",
                                        "if not argv:"))
fg.append(("FG TC-10: 名前の確かめを外すと一覧に無い other.sh が動く", launch(r10, "other.sh")[1] is not None))
r11 = make_repo("fg_sandbox", broken_judge("sandbox", '    if os.environ.get("SANDBOX_RUNTIME"):', "    if False:"))
fg.append(("FG TC-16: 中の確かめを外すと不合格", launch(r11, "issue-source.sh", "a", SANDBOX_RUNTIME="1")[0] != 4))
fg.append(("FG TC-11: gate_reviewed を常に真にすると、レビュー前の中身があってもテストが流れる", ran_fg))
fg.append(("FG TC-14: フックの起動役の -c を 1 つ消すと不合格",
           not same_defs(lsrc.replace(" -c submodule.recurse=false", "", 1), gsrc)))
rr = launcher_variant("fg_never_snap", MAKE_SNAP, '  return 4\n}')
w(os.path.join(rr, "scripts/claude/hooks/h.py"), 'print("V2")\n')
fg.append(("FG TC-12: 写しを作らないと、変更があっても作業ツリーで動いて不合格", hook(rr).stdout.startswith("V2")))
# 消した近道（I610 の前の「git の差と未追跡が無ければ作業ツリー」）を写しを作る前に戻す
OLD_SHORTCUT = ('  if _reviewed_git "$root" diff --quiet --no-ext-diff --no-textconv '
                '"$(_reviewed_git "$root" merge-base HEAD origin/develop)" -- scripts/claude 2>/dev/null \\\n'
                '    && [ -z "$(_reviewed_git "$root" ls-files --others --exclude-standard -- scripts/claude 2>/dev/null)" ]; then\n'
                '    exec python3 -I "$root/$rel" "$@"\n  fi\n')
fg.append(("FG TC-12b: 消した近道を戻すと、無視されるファイルがあっても作業ツリーで動いて不合格",
           not ignored_case(launcher_variant("fg_old_shortcut", CALL_SNAP, OLD_SHORTCUT + CALL_SNAP))))
fg.append(("FG TC-12c: 写しで動かす最後の行の -I を外すと json.py を読み込んで不合格",
           not evil_case(launcher_variant("fg_no_isolate", RUN_SNAP, RUN_SNAP.replace(" -I", ""), count=-1))))
fg.append(("FG TC-12d: 写しの道の -I を外すと不合格", not all_dash_i(lsrc.replace(RUN_SNAP, RUN_SNAP.replace(" -I", ""), 1))))

r18 = os.path.join(TMP, "fg_doc")
shutil.copytree(os.path.join(REAL, ".claude/skills"), os.path.join(r18, ".claude/skills"))
shutil.copytree(os.path.join(REAL, ".claude/agents"), os.path.join(r18, ".claude/agents"))
with open(os.path.join(r18, ".claude/skills/grill-me/SKILL.md"), "a", encoding="utf-8") as fh:
    fh.write("\n```bash\nN=$(bash scripts/claude/issue-source.sh gh-number $ARGUMENTS)\n```\n")
fg.append(("FG TC-18: スキルに包んだ形の呼び出しを足すと不合格", not doc_calls_routed(r18, J)))
fg.append(("FG TC-18: 外に出る型から起動役の形を外すと不合格",
           not doc_calls_routed(REAL, J, [p for p in excluded_patterns(os.path.join(REAL, ".claude/settings.json"))
                                          if "unreviewed.py" not in p])))
r19 = make_repo("fg_no_glob", broken_judge("no_glob", r"*?\[\n", r"\n"))
w(f"{r19}/--dangerously-skip-permissions", "")
fg.append(("FG TC-05b・TC-02: ワイルドカードを単体でない文字から外すと付け替わる",
           not untouched(r19, f"{ts_s} [-]-dangerously-skip-permissions")))

# ---- I615: 写しの共有・作成・-I・見張り（TC-I615-04〜07） ----
def shared_case(root):
    """TC-04: フックの起動役と入口の起動役が、同じ BASE で同じ写しを使う（写しは 1 つ）。"""
    p = hook(root)
    rc_, got_, _ = launch(root, "code-review.sh", "a")
    top = os.path.join(env_for(root)["HOME"], SNAPS)
    made = sorted(x for x in os.listdir(top) if not x.startswith(".")) if os.path.isdir(top) else []
    return ran_in(p, snapdir(root)) and rc_ == 0 and got_ == lib_mark(root, "a") and len(made) == 1


def keep_case(root):
    """TC-05: 作成の処理（有無の確かめを飛ばす）は、置いてある写しを消さない（I610 F1）。"""
    snap = snapdir(root)
    os.makedirs(snap, exist_ok=True)
    w(os.path.join(snap, ".complete"), "")
    w(os.path.join(snap, "keep"), "x\n")
    base = os.path.basename(snap)
    p = subprocess.run(["bash", "-c", '. "$1" && _reviewed_snapshot_make "$2" "$3" "$4"', "_",
                        os.path.join(root, ".claude/hooks/reviewed-hook.sh"), root, base, os.path.dirname(snap)],
                       cwd=root, capture_output=True, text=True, timeout=60, env=env_for(root))
    return p.returncode == 0 and p.stdout.strip() == snap and os.path.isfile(os.path.join(snap, "keep"))


def all_child_isolated(sources):
    """TC-06: フックの python（sources: 名前→本文）が sys.executable で起こす子の引数の並びは、すべて 2 番目が "-I"。"""
    import ast
    seen = 0
    for src in sources.values():
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.List) and node.elts and ast.unparse(node.elts[0]) == "sys.executable":
                seen += 1
                second = node.elts[1] if len(node.elts) > 1 else None
                if not (isinstance(second, ast.Constant) and second.value == "-I"):
                    return False
    return seen >= 1


GIT_INSIDE_STOP = ["git merge --ff-only origin/develop 2>&1 | tail -2", "cd scripts && git switch x", "X=1 git pull",
                   "git stash pop; ls", "git switch x > o", "timeout 5 git switch x",
                   "echo $(git rev-parse HEAD) && git rebase x"]
GIT_INSIDE_PASS = ["git merge --ff-only origin/develop", "git fetch origin && git merge --ff-only origin/develop",
                   "git status | head", "git log --oneline | head -3", "git stash list | head",
                   'git commit -m "a | b; c"', "git diff > o", "DANGER_OK=1 git checkout -- x"]


def git_inside_case(root, guard_path=GUARD):
    """TC-07: git の更新を中で動く形で流すと I615 の理由で止め、単独・git どうし・読み取り・DANGER_OK=1 は止めない。"""
    stop = all(p.returncode == 2 and "I615" in p.stderr
               for p in (guard_proc(root, c, guard_path=guard_path) for c in GIT_INSIDE_STOP))
    keep = all("I615" not in guard_proc(root, c, guard_path=guard_path).stderr for c in GIT_INSIDE_PASS)
    return stop and keep


HOOK_SRCS = {f: open(f, encoding="utf-8").read() for f in sorted(glob.glob(os.path.join(REAL, "scripts/claude/hooks/*.py")))}
rg = r   # 見張りを流すだけで、リポジトリを変えない
rs = make_repo("shared")
ck("TC-I615-04 フックの起動役と入口の起動役が同じ写しを使う（AC4）", shared_case(rs))
ck("TC-I615-05 写しの作成は置いてある写しを消さない（AC5・I610 F1）", keep_case(rs))
ck("TC-I615-06 フックが sys.executable で起こす子はすべて -I（AC5・I610 F2）", all_child_isolated(HOOK_SRCS))
ck("TC-I615-07 見張りは git の更新を中で動く形で流すのを止め、単独の形は止めない（AC6）", git_inside_case(rg))

# FG（I615）
r21 = make_repo("fg_worktree_exec", broken_judge("worktree_exec", 'os.execvp("bash", ["bash", entry, *args])',
                                                 'os.execvp("bash", ["bash", SCRIPTS + name, *args])'))
fg.append(("FG TC-I615-01: 写しでなく作業ツリーの入口を動かすと、印の場所が写しでなくなり不合格", not all(unrelated_cases(r21))))
r22 = make_repo("fg_old_dirty", broken_judge("old_dirty", "    if hit:\n", "    if hit or dirty(root):\n"))
fg.append(("FG TC-I615-01: 変更があれば止める I599 の判定を戻すと 75 になり不合格", not all(unrelated_cases(r22))))
# 部品のたどり（ファイル・レビュー役）を外し、入口だけを部品にした判定の写し
r23 = make_repo("fg_no_parts", broken_judge(
    "no_parts", "        todo += [x for x in files if SCRIPTS + x not in found and _word_in(x, text)]\n", "",
    '        found |= {f"{AGENTS}{a}.md" for a in agents if _word_in(a, text, after=r"[\\w-]")}\n', ""))
fg.append(("FG TC-I615-02: 部品を見ない写しで、部品の書き換えを見落として不合格", not all(part_cases(r23))))
r24 = make_repo("fg_hit_exec", broken_judge("hit_exec", "    if hit:\n        return _need_human(",
                                            "    if hit:\n        os.chdir(root)\n        os.execvp(\"bash\", [\"bash\", SCRIPTS + name, *args])\n        return _need_human("))
fg.append(("FG TC-I615-02: 75 の代わりに作業ツリーを動かすと不合格", not all(part_cases(r24))))
r25 = make_repo("fg_snap_fallback", broken_judge("snap_fallback", "    if snap is None:\n        return _need_human(name, args, why)\n",
                                                 "    if snap is None:\n        os.chdir(root)\n        os.execvp(\"bash\", [\"bash\", SCRIPTS + name, *args])\n"))
fg.append(("FG TC-I615-03: 写しの失敗を作業ツリーに倒すと不合格", not snapfail_cases(r25)))
fg.append(("FG TC-I615-04: --snapshot の置き場所を変えると写しが 2 つになり不合格",
           not shared_case(launcher_variant("fg_two_snaps", '    reviewed_snapshot "$root" </dev/null\n    return',
                                            '    HOME="$HOME/x" reviewed_snapshot "$root" </dev/null\n    return'))))
fg.append(("FG TC-I615-05: 置く前に rm -rf \"$snap\" を戻すと、置いてある写しが消えて不合格",
           not keep_case(launcher_variant("fg_rm_snap", '      mv -T "$tmp" "$snap" 2>/dev/null || rm -rf "$tmp"',
                                          '      rm -rf "$snap"; mv -T "$tmp" "$snap" 2>/dev/null || rm -rf "$tmp"'))))
SS = os.path.join(REAL, "scripts/claude/hooks/sessionstart_context.py")
assert '[sys.executable, "-I", ' in HOOK_SRCS[SS]
fg.append(("FG TC-I615-06: sessionstart の子から -I を外すと不合格",
           not all_child_isolated({**HOOK_SRCS, SS: HOOK_SRCS[SS].replace('[sys.executable, "-I", ', "[sys.executable, ")})))
g_off = broken_judge("guard_no_inside", "def _git_update_inside(cmd: str, subs: list):\n",
                     "def _git_update_inside(cmd: str, subs: list):\n    return None\n", src_path=GUARD)
fg.append(("FG TC-I615-07: 見張りの判定を外すと、止める形が通り不合格", not git_inside_case(rg, g_off)))

for name, ok in fg:
    ck(name, ok)
print(f"---\npass={sum(results)} fail={len(results) - sum(results)}")
sys.exit(0 if all(results) else 1)
