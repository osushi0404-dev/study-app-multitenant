#!/usr/bin/env python3
import ast
import fnmatch
import functools
import json
import os
import posixpath
import re
import shlex
import subprocess
import sys
import textwrap

def _load():
    try:
        return json.load(sys.stdin)
    except Exception as e:
        print(f"[guard] invalid hook input: {e}", file=sys.stderr)
        return {}

def _block(msg: str, raw: str):
    print(f"[guard] {msg}\ncommand: {raw}", file=sys.stderr)
    sys.exit(2)

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())

# --- git checkout/restore on a file with uncommitted worktree changes 防止 ---
# トークナイズは shlex.split()（クォート対応）で行う。素朴な str.split() だと
# `git checkout -- "my file.py"` のような空白パスを取りこぼし黙って素通し（データ消失）する。
_SHELL_OPS = ("&&", "||", "|", ";")

def _segments(cmd: str) -> list:
    """コマンドをクォート対応で分割し、shell 演算子区切りごとのトークン列リストを返す。
    クォート不整合（実シェルでもエラー）の場合は素朴分割にフォールバック。
    語にくっついた演算子（`git checkout feat; git log -- x`）も区切る（I174: 区切らないと後ろの `-- x` を
    checkout の対象と誤読する）。"""
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|")
        lex.whitespace_split = True
        lex.commenters = ""
        toks = list(lex)
    except ValueError:
        toks = cmd.split()
    segs, seg, glue = [], [], False
    for t in toks:
        # リダイレクトの一部（`>|`・`2>&1`・`>&2`）は区切りではないので、直前の語に戻す
        if seg and t in ("|", "&") and seg[-1].endswith((">", "<")):
            seg[-1] += t
            glue = t == "&"
            continue
        if glue:
            seg[-1] += t
            glue = False
            continue
        if t in _SHELL_OPS or (t and set(t) <= set(";&|")):
            if seg:
                segs.append(seg)
                seg = []
        else:
            seg.append(t)
    if seg:
        segs.append(seg)
    return segs

# --- 見張りが判定のために実行する git（I174 security-review の Blocker） ---
# git は設定（core.fsmonitor・フィルタ等）や、実行した場所のリポジトリの .git/config でコマンドを実行する。
# 見張りが人の承認より前にコマンドを実行しないよう、git を実行してよい場所を「このリポジトリとその worktree」
# に一致で限り、判定対象のコマンドの -c・環境変数は渡さない。git の探索（近い .git）も使わず、git-dir を明示する。
_GIT_SAFE_OPTS = ("-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null")

def _clean_git_env() -> dict:
    """見張りの環境から GIT_ で始まる変数を除いたもの（紛れ込んだ GIT_DIR・GIT_CONFIG_* 等の影響を受けない）。"""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

@functools.lru_cache(maxsize=1)
def _trusted_repos() -> tuple:
    """信頼する (最上位, git-dir) の組。プロジェクト（Claude Code が渡す CLAUDE_PROJECT_DIR。無ければ見張りの
    作業ディレクトリ）の `git worktree list` から得る。Bash の作業ディレクトリが入れ子のリポジトリに移っていても、
    そこを信頼しないため（作業ディレクトリは入れ子の判定〔_nested_git〕で外れる）。"""
    env = _clean_git_env()
    anchor = os.environ.get("CLAUDE_PROJECT_DIR") or None
    try:
        out = subprocess.run(["git", *_GIT_SAFE_OPTS, "worktree", "list", "--porcelain"],
                             capture_output=True, text=True, env=env, cwd=anchor).stdout
        res = []
        for line in out.splitlines():
            if not line.startswith("worktree "):
                continue
            root = os.path.realpath(line[len("worktree "):])
            gd = subprocess.run(["git", "-C", root, *_GIT_SAFE_OPTS, "rev-parse", "--absolute-git-dir"],
                                capture_output=True, text=True, env=env).stdout.strip()
            if gd:
                res.append((root, os.path.realpath(gd)))
        return tuple(res)
    except Exception:
        return ()

def _under(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")

def _nested_git(cur: str, root: str) -> bool:
    """cur から root（含まない）までのあいだに別の .git（入れ子のリポジトリ）があるなら True。"""
    p = cur
    while _under(p, root) and p != root:
        if os.path.lexists(os.path.join(p, ".git")):
            return True
        p = os.path.dirname(p)
    return False

def _git_resolve(loc, need_worktree: bool = True):
    """判定する場所を、信頼する (作業ディレクトリ, 最上位, git-dir) に解決する。信頼しない場所は None。
    --git-dir・--work-tree・GIT_DIR・GIT_WORK_TREE は信頼する値と一致するときだけ受け入れる（リポジトリの中に
    作った偽の git-dir は一致しない）。指定が無ければ、信頼する最上位の配下で入れ子のリポジトリの外のときだけ。"""
    cwd, opts, env = loc or (None, [], {})
    cur = os.path.realpath(cwd) if cwd else os.getcwd()
    gd = wt = None
    i = 0
    while i < len(opts):
        o = opts[i]
        v = opts[i + 1] if i + 1 < len(opts) else ""
        if o == "-C":
            cur = os.path.realpath(os.path.join(cur, v))
        elif o == "--git-dir":
            gd = os.path.realpath(os.path.join(cur, v))
        elif o == "--work-tree":
            wt = os.path.realpath(os.path.join(cur, v))
        elif o.startswith("--git-dir="):
            gd = os.path.realpath(os.path.join(cur, o.split("=", 1)[1]))
        elif o.startswith("--work-tree="):
            wt = os.path.realpath(os.path.join(cur, o.split("=", 1)[1]))
        i += 2 if o in ("-C", "--git-dir", "--work-tree", "-c") else 1
    if gd is None and env.get("GIT_DIR"):
        gd = os.path.realpath(os.path.join(cur, env["GIT_DIR"]))
    if gd is not None and os.path.isfile(gd):
        # worktree の .git は「gitdir: <置き場所>」を書いたファイル（読むだけで実行はしない）
        try:
            with open(gd, encoding="utf-8") as f:
                line = f.readline().strip()
            if line.startswith("gitdir:"):
                gd = os.path.realpath(os.path.join(os.path.dirname(gd), line[len("gitdir:"):].strip()))
        except OSError:
            return None
    if wt is None and env.get("GIT_WORK_TREE"):
        wt = os.path.realpath(os.path.join(cur, env["GIT_WORK_TREE"]))
    for root, rgd in _trusted_repos():
        if wt is not None and wt != root:
            continue
        if gd is not None:
            # --git-dir だけで --work-tree が無いとき、本物の git は作業ディレクトリを作業ツリーとして扱う。
            # ファイルの変更を調べるとき（need_worktree）、作業ディレクトリがその git-dir の最上位と一致しなければ
            # 調べる場所がずれるので信頼しない。今のブランチ（HEAD）は git-dir だけで決まるので問わない
            if gd == rgd and (wt is not None or cur == root or not need_worktree):
                return (cur, root, rgd)
            continue
        if _under(cur, root) and not _nested_git(cur, root):
            return (cur, root, rgd)
    return None

def _git_loc_trusted(loc, need_worktree: bool = True) -> bool:
    return _git_resolve(loc, need_worktree) is not None

def _git_run(loc, args, need_worktree: bool = True):
    """git を判定対象のコマンドと同じ場所で、信頼する git-dir と最上位を明示して実行する（コマンドの -c・環境変数は
    渡さない）。loc は _git_loc の結果（None は見張りの作業ディレクトリ）。信頼しない場所・失敗は None。"""
    r = _git_resolve(loc, need_worktree)
    if r is None:
        return None
    cur, root, gd = r
    try:
        p = subprocess.run(["git", f"--git-dir={gd}", f"--work-tree={root}", *_GIT_SAFE_OPTS] + args,
                           capture_output=True, text=True, cwd=cur, env=_clean_git_env())
        return p.stdout if p.returncode == 0 else None
    except Exception:
        return None

def _worktree_dirty(path: str, loc=None, staged: bool = False) -> bool:
    """<path>（'.' 可）にワークツリー変更があれば True。untracked('??')は除外。
    staged=True（コミットから戻す形）はステージ済みの変更も数える（I174）。
    git 不在/失敗は False（fail-open＝既存方針と同じ）。"""
    out = _git_run(loc, ["status", "--porcelain", "--no-renames", "--untracked-files=no", "--", path])
    if out is None:
        return False
    for line in out.splitlines():
        if len(line) >= 2 and line[:2] != "??" and (line[1] != " " or (staged and line[0] != " ")):
            return True
    return False

def _revert_targets(sub: str, args: list) -> list:
    """checkout/restore のうちワークツリーを破壊し得る pathspec を返す。破壊しない形は []。"""
    if sub == "checkout" and any(a in ("-b", "-B", "--orphan") or _has_short([a], "b") or _has_short([a], "B")
                                 for a in args):
        return []  # ブランチ作成（`-qb` のようにまとめて書いた形も）
    if sub == "restore":
        has_staged = ("--staged" in args) or ("-S" in args)
        has_worktree = ("--worktree" in args) or ("-W" in args)
        if has_staged and not has_worktree:
            return []  # index のみ・ワークツリー非破壊
    cand = args[args.index("--") + 1:] if "--" in args else args
    return [a for a in cand if not a.startswith("-")]

def _revert_from_commit(sub: str, args: list) -> bool:
    """コミットから戻す形（ステージ済みの変更も消える）なら True。
    `git checkout <コミット> -- <file>`・`git restore -s/--source …`・`git restore -S -W …`。"""
    if sub == "checkout":
        if "--" in args:
            return any(not a.startswith("-") for a in args[:args.index("--")])
        # `git checkout HEAD <path>`（-- なし）も、位置引数が 2 つ以上なら先頭はコミット（I174）
        return len([a for a in args if not a.startswith("-")]) >= 2
    has_staged = ("--staged" in args) or ("-S" in args) or any(
        a.startswith("-") and not a.startswith("--") and "S" in a for a in args)
    return has_staged or any(a in ("-s", "--source") or a.startswith("--source=") for a in args)

_DYN_MARKS = ("$", "`", "__SUBST_")
_BRACE_RE = re.compile(r"\{[^{}]*(,|\.\.)[^{}]*\}")

def _scoped(text: str) -> bool:
    """`( … )`（サブシェル）・popd があり、cd の効く範囲が読み解いた列から分からないなら True。
    `$( )`・`$(( ))`・`<( )`・`f()` は場所の範囲を変えないので数えない。"""
    return bool(re.search(r"(?<![$<>(])\((?![()])", text) or re.search(r"\bpopd\b", text))

# パイプ・& の前後の cd（サブシェルで動くので後ろに効かない）
_CD_PIPE_RE = re.compile(r"\b(cd|pushd)\b[^;&|\n]*(?<![|&>])[|&](?![|&>])|(?<![|&>])[|&](?![|&>])[^;&|\n]*\b(cd|pushd)\b")
# 条件付きの cd（`A && cd X; git …`・`A || cd X; git …`・`cd X || true; git …`）。cd が実行されないまま後ろが動きうる。
# `cd X && git …`（cd の成功後にだけ git が動く）・`cd X || exit` は一意
_CD_COND_RE = re.compile(r"(&&|\|\|)\s*(cd|pushd)\b[^;&|\n]*(;|\n|\|\|)|\b(cd|pushd)\b[^;&|\n]*\|\|(?!\s*(exit|return)\b)")
# cd を含みうる入れ子のシェル（中の cd は外に効かない）
_NESTED_SHELL_RE = re.compile(r"\b(ba|z|da)?sh\b\s+(-\w*c\b|<<)|\beval\b|\bxargs\b|\bparallel\b|\bfind\b[^;&|\n]*-exec")

def _loc_ambiguous(text: str, cmds=None) -> bool:
    """git を実行する場所が 1 つに決まらないなら True（I174 0-15: 推測で通す・止めるをせず確認にする）。
    cd / pushd / popd が無ければ一意。あれば、`( … )`・パイプ・`&`・入れ子のシェルの中にありうる・
    元へ戻る（`cd -`・`~-`・`$OLDPWD`）・先が読めない（変数・`$(…)`）・先が存在しない（失敗して留まる）のどれかで一意でない。"""
    cmds = _parse(text) if cmds is None else cmds
    cds = [c for c in cmds if not c["ctr"] and c["toks"] and c["toks"][0] in ("cd", "pushd", "popd")]
    if not cds:
        return False
    if _scoped(text) or _CD_PIPE_RE.search(text) or _NESTED_SHELL_RE.search(text) or _CD_COND_RE.search(text):
        return True
    base = None
    for c in cds:
        d = _cd_target(c["toks"])
        if d is None or d in ("-", "~-") or "OLDPWD" in d or any(m in d for m in _DYN_MARKS):
            return True
        base = _join_dir(base, d)
        if not os.path.isdir(base):
            return True
    return False

def _git_revert_check(cmd: str, opaque: bool = False, ambiguous: bool = False):
    """複合コマンドを分割し、未コミットの変更を消しうる git の操作（checkout/restore のファイル指定・git rm -f・
    checkout-index -f・read-tree -u --reset・mv -f）を判定する。
    ("block", パス): 文字どおりの対象に変更がある（停止）。("ask", 理由): 場所が 1 つに決まらない（ambiguous）、
    または対象が読めず（`$(…)`・変数・xargs／find〔opaque〕・中かっこ・--pathspec-from-file）その場所に変更がある（確認）。
    I174 0-15: 場所や対象を推測して通す・止めるをしない。"""
    cd_dir = None
    for toks in _segments(cmd):
        d = _cd_target(toks)
        if d is not None:
            cd_dir = _join_dir(cd_dir, d)
            continue
        g = _git_find(toks)
        if not g:
            continue
        gi, si = g
        sub, args = toks[si], toks[si + 1:]
        loc = _git_loc(toks, gi, si, cd_dir)
        pos = [a for a in args if not a.startswith("-")]
        unreadable = opaque
        if sub in ("checkout", "restore"):
            staged = _revert_from_commit(sub, args)
            targets = _revert_targets(sub, args)
            unreadable = unreadable or any(a.startswith("--pathspec-from-file") for a in args)
        elif sub == "rm" and _has_short(args, "f", "--force") and "--cached" not in args:
            staged, targets = True, pos
        elif sub == "checkout-index" and _has_short(args, "f", "--force"):
            staged, targets = False, [":/"] if _has_short(args, "a", "--all") else pos
        elif sub == "read-tree" and _has_short(args, "u") and "--reset" in args:
            staged, targets = True, [":/"]                       # -m は変更を残す（消えるのは --reset）
        elif sub == "mv" and _has_short(args, "f", "--force") and len(pos) >= 2:
            dst = pos[-1]
            base = os.path.join(loc[0] or ".", dst)
            # 移動先がディレクトリなら、その中の同じ名前のファイルが上書きされる
            staged, targets = True, [os.path.join(dst, os.path.basename(x)) for x in pos[:-1]] \
                if os.path.isdir(base) else [dst]
        else:
            continue
        if not targets and not unreadable:
            continue
        # 場所が 1 つに決まらない・読めない・信頼しない場所（このリポジトリと worktree の外・入れ子のリポジトリ・
        # 偽の git-dir）では git を実行せず確認（security-review の Blocker）
        if ambiguous or _git_loc_dynamic(loc) or not _git_loc_trusted(loc):
            return ("ask", f"git {sub} を実行する場所が 1 つに決まらない（cd の範囲・戻り先・-C 等の先が読めない）")
        # 中かっこ（sub/{b,c}.py）は bash が展開するので、文字どおりの名前では調べられない
        unreadable = unreadable or any(m in t for t in targets for m in _DYN_MARKS) or \
            any(_BRACE_RE.search(t) for t in targets)
        if unreadable:
            if _worktree_dirty(":/", loc, staged):
                return ("ask", f"git {sub} で戻す対象が読めない（コマンド・変数・xargs 等で渡している）うえ、変更のあるファイルがある")
            continue
        for t in targets:
            if _worktree_dirty(t, loc, staged):
                return ("block", t)
    return None

def _git_revert_target_on_dirty(cmd: str, opaque: bool = False, ambiguous: bool = False):
    """_git_revert_check のうち停止するもの（文字どおりの対象に変更がある）の対象のパスを返す。無ければ None。"""
    r = _git_revert_check(cmd, opaque, ambiguous)
    return r[1] if r and r[0] == "block" else None

# --- git push の保護ブランチ宛先判定（I080） ---
PROTECTED_BRANCHES = ("develop", "main")

# I174: git の前に書く、実行場所・設定を変えるオプション（値を 1 つ取る）
_GIT_GLOBAL_VALUE = ("-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env")

def _git_find(toks):
    """単純コマンドの git の位置とサブコマンドの位置 (gi, si) を返す。git でなければ None。
    git は絶対パス・git.exe（WSL）でも同じ（basename で判定）。前置きの環境変数（GIT_DIR=…）は飛ばす。"""
    gi = 0
    while gi < len(toks) and _ENV_ASSIGN_RE.match(toks[gi]):
        gi += 1
    if gi >= len(toks) or os.path.basename(toks[gi]) not in ("git", "git.exe"):
        return None
    si = gi + 1 + _skip_opts(toks[gi + 1:], _GIT_GLOBAL_VALUE)
    return (gi, si) if si < len(toks) else None

def _git_loc(toks, gi, si, cd_dir, genv=None):
    """git の実行場所 (cwd, 前置きオプション, 環境変数) を返す（_git_run に渡す）。
    genv は読み解きの途中で外した前置きの GIT_DIR= / GIT_WORK_TREE=（入れ子の外側の分を含む）。"""
    opts, i = [], gi + 1
    while i < si:
        t = toks[i]
        if t in ("-C", "--git-dir", "--work-tree", "-c") and i + 1 < si:
            opts += [t, toks[i + 1]]
            i += 2
            continue
        if t.startswith(("--git-dir=", "--work-tree=")):
            opts.append(t)
        i += 1
    env = dict(genv or {})
    env.update(a.split("=", 1) for a in toks[:gi] if a.split("=", 1)[0] in ("GIT_DIR", "GIT_WORK_TREE"))
    return cd_dir, opts, env

def _git_loc_dynamic(loc) -> bool:
    """実行場所に変数・置換が入っていて、どこで動くか確かめられないなら True。"""
    cwd, opts, env = loc
    return any(ch in v for v in [cwd or ""] + opts + list(env.values()) for ch in ("$", "`", "__SUBST_"))

def _cd_target(toks):
    """cd / pushd なら移動先（オプション・-- を除く。引数なしは ~）を返す。それ以外は None。"""
    if not toks or toks[0] not in ("cd", "pushd"):
        return None
    pos = toks[1 + _skip_opts(toks[1:], ()):]
    return os.path.expanduser(pos[0] if pos else "~")

def _join_dir(base, d):
    return os.path.join(base, d) if base else d

def _current_branch(loc=None):
    """現ブランチ名を返す（loc は _git_loc の結果。None は見張りの作業ディレクトリ）。
    git 不在/失敗は None（fail-open＝既存 HEAD チェックと同方針）。"""
    out = _git_run(loc, ["rev-parse", "--abbrev-ref", "HEAD"], need_worktree=False)
    return out.strip() if out is not None else None

def _norm_push_dest(token: str, cur_branch):
    """push 宛先トークンを正規化して宛先ブランチ名を返す（判定不能は None）。
    'src:dst' なら dst 採用 → force-shorthand '+'（先頭/dst 側いずれも）除去 →
    'refs/heads/' 接頭辞除去 → 'HEAD' / '@' は現ブランチ解決 → glob（refs/heads/*）は保護ブランチに一致すればその名前。"""
    t = token
    if ":" in t:
        t = t.split(":", 1)[1]          # 'src:dst' の dst を採用
    t = t.lstrip("+")                    # force-shorthand '+'（先頭 / dst 側）を除去
    if t.startswith("refs/heads/"):
        t = t[len("refs/heads/"):]
    if t in ("HEAD", "@"):
        return cur_branch               # None 可（detached/fail-open）
    if any(ch in t for ch in "*?["):
        return next((b for b in PROTECTED_BRANCHES if fnmatch.fnmatchcase(b, t)), None)
    return t or None

# I174: 値を取る push のオプション（値を remote と読み違えないため）
_PUSH_VALUE_OPTS = ("-o", "--push-option", "--receive-pack", "--exec", "--repo")

def _git_push_parts(toks):
    """単純コマンドが git push なら (git の位置, push の位置) を返す。非該当は None。
    git は絶対パス・git.exe（WSL）でも同じ（basename で判定）。"""
    gi = next((i for i, t in enumerate(toks) if os.path.basename(t) in ("git", "git.exe")), None)
    if gi is None or "push" not in toks[gi + 1:]:
        return None
    return gi, toks.index("push", gi + 1)

def _push_dest_on_branch(toks) -> bool:
    """git push の宛先が今のブランチで決まる（宛先を書かない・HEAD・@）なら True。"""
    parts = _git_push_parts(toks)
    if not parts:
        return False
    refspecs = _push_positionals(toks[parts[1] + 1:])[1:]
    return not refspecs or any(r.lstrip("+") in ("HEAD", "@") for r in refspecs)

def _push_dest_dynamic(toks) -> bool:
    """git push の宛先・実行場所が変数・置換・xargs の {} などで決まり、静的に確かめられないなら True。"""
    parts = _git_push_parts(toks)
    if not parts:
        return False
    after = " ".join(toks[parts[1] + 1:])
    return any(ch in after for ch in ("$", "`", "{", "(", "__SUBST_"))

def _push_positionals(after):
    """push 以降の位置引数（[0]=remote、以降=refspec）。値を取るオプションの値は除く。"""
    out, skip = [], False
    for a in after:
        if skip:
            skip = False
        elif a in _PUSH_VALUE_OPTS:
            skip = True
        elif not a.startswith("-"):
            out.append(a)
    return out

def _push_protected_target(cmd: str, ambiguous: bool = False):
    """git push が protected ブランチを名前/refspec で宛先にするなら宛先名を返す。非該当は None。
    複合コマンドは _segments(I081)で分割して各セグメントを判定。宛先が今のブランチで決まる形は、
    git -C の先・その前の cd の先のブランチを見る（I174）。
    --all/--mirror・--repo は positional を持たない/前提を崩すため main() 側の独立チェックで扱う。"""
    cd_dir = None
    for toks in _segments(cmd):
        d = _cd_target(toks)
        if d is not None:
            cd_dir = _join_dir(cd_dir, d)
            continue
        parts = _git_push_parts(toks)
        if not parts:
            continue
        gi, pi = parts
        refspecs = _push_positionals(toks[pi + 1:])[1:]      # [0]=remote、以降=refspec
        cdir = _git_loc(toks, gi, pi, cd_dir)
        cur = None
        if not refspecs:                                     # 宛先明示なし → 現ブランチが宛先
            if ambiguous:
                continue                                     # 場所が 1 つに決まらない → 確認（push_dynamic）
            cur = _current_branch(cdir)
            if cur in PROTECTED_BRANCHES:
                return cur
            continue
        for rs in refspecs:
            if rs.lstrip("+") == ":":
                return "main / develop（: は同じ名前のブランチをすべて push する）"
            if cur is None and not ambiguous:
                cur = _current_branch(cdir)
            dest = _norm_push_dest(rs, cur)
            if dest in PROTECTED_BRANCHES:
                return dest
    return None

# --- git push force フラグ判定（_segments ベース・I083 欠陥2/F1） ---
_FORCE_LONG = ("--force", "--force-with-lease", "--force-if-includes")

def _is_force_flag(tok: str) -> bool:
    """push の force 系フラグなら True。--push-option=force 等の非 force 用法は False。"""
    if tok.startswith("--"):
        return tok.split("=", 1)[0] in _FORCE_LONG
    if tok.startswith("-") and len(tok) > 1:          # 単一ダッシュ短縮クラスタ（-f/-uf/-fu）
        # 単一ダッシュで 'f' を含む全クラスタを force として扱う（git push の短縮フラグで 'f' は -f のみ）。
        # 注: '-rf' 等の非実在フラグも True になるが、push セグメント内で '-rf' は無効構文＝実害なし。
        return "f" in tok[1:]
    return False

def _push_has_force(cmd: str) -> bool:
    """push を含むセグメントの push 以降トークンに force 系フラグがあれば True。
    複合コマンド・短縮結合形に頑健（_segments でセグメント分割）。protected 宛先の force は
    _push_protected_target が先に block するため、ここで捕捉する漏れは非保護宛に限定される。"""
    for toks in _segments(cmd):
        parts = _git_push_parts(toks)
        if parts:
            after = toks[parts[1] + 1:]
            if any(_is_force_flag(t) for t in after):
                return True
            # 宛先の前の + も force（git push origin +feature/x・+HEAD:x）。[0] は remote
            if any(rs.startswith("+") or ":+" in rs for rs in _push_positionals(after)[1:]):
                return True
    return False

# --- 動的・不透明 push 判定（ask degrade・I083 欠陥1/R5） ---
_WRAP_SHELLS = ("sh", "bash", "dash", "zsh")

def _push_is_dynamic(cmd: str) -> bool:
    """静的に宛先を確定できない push なら True（ask に degrade する対象）。
    (i) 直接 push の push 以降引数に動的メタ文字（宛先トークン分離に依存しない）。
    (ii) 構造的に不透明なラッパー（eval/sh -c/bash -c/git -c alias.）が push を隠蔽。
    脅威モデル=事故。push トークンが完全隠蔽される eval "$VAR" 形は対象外（既知の限界）。"""
    if not (re.search(r"\bgit\b", cmd) and re.search(r"\bpush\b", cmd)):
        return False
    for toks in _segments(cmd):
        if not toks:                       # _segments は空セグメントを返さないが防御的に
            continue
        # (i) 直接 push: push 以降の引数領域に動的メタ文字（$(...) の空白で shlex が壊れてもすり抜けない）
        parts = _git_push_parts(toks)
        if parts:
            after = " ".join(toks[parts[1] + 1:])
            if any(ch in after for ch in "$`{("):
                return True
            # git -C・--git-dir・--work-tree の先が読めない（変数・置換）push は、宛先のブランチを確かめられない
            if any(ch in t for t in toks[parts[0] + 1:parts[1]] for ch in "$`"):
                return True
        # (ii) 構造的に不透明なラッパー（先頭トークンで判定＝branch/remote 名の偶然一致を排除）
        head = toks[0]
        if head == "eval" and any("push" in t for t in toks[1:]):
            return True
        if head == "git":
            for i, t in enumerate(toks[:-1]):
                if t == "-c" and toks[i + 1].startswith("alias.") and "push" in toks[i + 1]:
                    return True
    # sh -c・bash -lc・ヒアドキュメント・xargs / parallel の中の push は、_analyze が読み解いた単純コマンドごとに
    # 判定する（"push_dynamic"）。文字列の一致で判定すると `xargs grep "git push"` まで確認になる（I174 第 3 周）
    return False

# 高リスク Edit/Write パス（リポジトリルート相対で照合）。
# 価値判断寄り（依存/スキーマ/インフラ）のため、編集時に ask（プロンプト）を出す。
# 注: ハードブロック(exit 2)ではなく ask。承認すれば編集可（I079 案D）。
HIGH_RISK_EDIT_PATTERNS = [
    r"(?:^|/)(?:backend|frontend)/Dockerfile(?:\.dev)?$",   # コンテナ定義
    r"(?:^|/)frontend/nginx\.conf$",                        # 配信設定
    r"(?:^|/)backend/requirements[^/]*\.txt$",              # 依存マニフェスト
    r"(?:^|/)backend/pyproject\.toml$",                     # 依存/ビルド設定
    r"(?:^|/)frontend/package(?:-lock)?\.json$",            # 依存/ロックファイル
    r"(?:^|/)[^/]+/migrations/[^/]*\.py$",                  # DBマイグレーション(手書き)
    r"(?:^|/)backend/init-db\.sql$",                        # DB初期化SQL
]

def _repo_relative(path: str) -> str:
    """file_path を可能ならリポジトリルート相対に正規化する（絶対/相対・`./`・OS差を吸収）。"""
    p = path.replace("\\", "/")
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            root = r.stdout.strip().replace("\\", "/")
            if root and p.startswith(root + "/"):
                p = p[len(root) + 1:]
    except Exception:
        pass  # git 不在環境では生のパスで照合
    while p.startswith("./"):
        p = p[2:]
    return p

# --- worktree 横断書込のブロック（I095） ---
# 別トラック（別 worktree）の作業ツリーへの直接書込を技術強制で禁止する（worktree.md §9）。
# 読み取りは許可・書込のみブロック。fail-safe（境界確定不能はブロック）・エスケープ無し（DANGER_OK 非解除）。
_REDIR_OPS = (">>", ">|", ">")   # 長いものから判定（">>" を ">" より先に）

def _worktree_roots():
    """全 worktree ルート（realpath 正規化）のリストを返す。git 失敗/非ゼロは None（fail-safe 対象）。"""
    try:
        r = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            return None
        roots = []
        for line in r.stdout.splitlines():
            if line.startswith("worktree "):
                roots.append(os.path.realpath(line[len("worktree "):].strip()))
        return roots
    except Exception:
        return None

def _current_worktree_root():
    """現 worktree ルート（realpath 正規化）。失敗は None。"""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True
        )
        return os.path.realpath(r.stdout.strip()) if r.returncode == 0 else None
    except Exception:
        return None

def _cross_worktree(path):
    """path が別 worktree 配下なら True / どの別 worktree 配下でもなければ False /
    境界を確定できなければ None（fail-safe 対象）。境界一致は realpath＋末尾 os.sep 接頭辞で
    行い、兄弟ディレクトリ名の部分一致（<root>-foo）を誤判定しない。"""
    if not path or not isinstance(path, str):
        return None
    roots = _worktree_roots()
    cur = _current_worktree_root()
    if roots is None or cur is None:
        return None
    ap = os.path.realpath(os.path.abspath(path))
    for root in roots:
        if root == cur:
            continue
        if ap == root or ap.startswith(root + os.sep):
            return True
    return False

def _edit_path(data: dict) -> str:
    """書込ツールの対象パス（Edit/Write/MultiEdit=file_path, NotebookEdit=notebook_path）。"""
    ti = data.get("tool_input") or {}
    p = ti.get("file_path") or ti.get("notebook_path") or ""
    return p if isinstance(p, str) else ""

def _split_redir_target(tok: str):
    """リダイレクト演算子が埋め込まれたトークンの右側（宛先候補）を返す。無ければ None。
    例: '>>/p'→'/p'・'>|/p'→'/p'・'>/p'→'/p'・'x>/p'→'/p'・'2>/p'→'/p'。'>' 単体は None。"""
    for op in _REDIR_OPS:
        idx = tok.find(op)
        if idx != -1:
            rhs = tok[idx + len(op):]
            return rhs or None
    return None

def _bash_write_targets(cmd: str) -> list:
    """Bash コマンドから書込先の絶対パスのみを抽出する（ヒューリスティック）。
    対象: リダイレクト（>/>>/>| の単体・付着・語中埋め込み）・tee・cp/mv の宛先・sed -i の対象。
    src 側（読み取り）は対象外・相対/変数越しは対象外（絶対パスのみ）。"""
    targets = []
    for toks in _segments(cmd):
        if not toks:
            continue
        # リダイレクト（全コマンド共通）
        i, n = 0, len(toks)
        while i < n:
            t = toks[i]
            if t in _REDIR_OPS:                 # 演算子単体 → 次トークンが宛先
                if i + 1 < n:
                    targets.append(toks[i + 1])
            elif any(op in t for op in _REDIR_OPS):   # 付着/語中埋め込み
                rhs = _split_redir_target(t)
                if rhs:
                    targets.append(rhs)
            i += 1
        # コマンド別の宛先
        head = os.path.basename(toks[0]) if toks[0] else ""
        rest = toks[1:]
        if head == "tee":
            targets += [a for a in rest if not a.startswith("-")]
        elif head in ("cp", "mv"):
            if "-t" in rest:                    # cp/mv -t <dir> src...
                ti = rest.index("-t")
                if ti + 1 < len(rest):
                    targets.append(rest[ti + 1])
            else:
                positional = [a for a in rest if not a.startswith("-")]
                if len(positional) >= 2:
                    targets.append(positional[-1])   # 末尾＝宛先（src は対象外）
        elif head == "sed":
            if any(a == "-i" or a.startswith("-i") or a.startswith("--in-place") for a in rest):
                targets += [a for a in rest if not a.startswith("-")]   # in-place 対象（絶対パスのみ後段で選別）
    # 絶対パスのみ（相対 src・sed script 等を除外）
    return [t for t in targets if t.startswith("/")]

def _has_write_intent(cmd: str) -> bool:
    """Bash に書込語（リダイレクト・tee・cp・mv・sed -i）が含まれるか（未カバー警告の判定用）。"""
    for toks in _segments(cmd):
        if not toks:
            continue
        for t in toks:
            if t in _REDIR_OPS or any(op in t for op in _REDIR_OPS):
                return True
        head = os.path.basename(toks[0]) if toks[0] else ""
        if head in ("tee", "cp", "mv"):
            return True
        if head == "sed" and any(a == "-i" or a.startswith("-i") or a.startswith("--in-place")
                                 for a in toks[1:]):
            return True
    return False

def _bash_uncovered_risk(cmd: str) -> bool:
    """絶対パス宛先の抽出では捕捉できない書込リスク（`cd` 後の相対書込・変数/コマンド置換・
    不透明ラッパー越しの宛先）があるか。no-silent-caps 警告用。
    読み取り（例: `cp /other/src ./dest`）や単純な相対書込では False（誤警告しない）。"""
    if not _has_write_intent(cmd):
        return False
    for toks in _segments(cmd):
        if not toks:
            continue
        head = os.path.basename(toks[0]) if toks[0] else ""
        if head == "cd":                                   # cwd が変わる → 相対宛先を分類できない
            return True
        if head == "eval" or (head in _WRAP_SHELLS and "-c" in toks):   # 不透明ラッパー
            return True
        if any(("$" in t) or ("`" in t) for t in toks):    # 変数/コマンド置換越しの宛先
            return True
    return False

def _block_cross_worktree(kind: str, path: str):
    """別 worktree への書込／判定不能を exit 2 でブロックする（DANGER_OK でも解除しない）。"""
    roots = _worktree_roots()
    cur = _current_worktree_root()
    if not path or roots is None or cur is None:
        reason = "対象パスを取得できない" if not path else "worktree 境界を確定できない"
        print(f"[guard] {reason}ため{kind}をブロックしました（fail-safe）。"
              f"git の状態/入力を確認してください: {path!r}", file=sys.stderr)
        sys.exit(2)
    ap = os.path.realpath(os.path.abspath(path))
    x_root = next((r for r in roots if r != cur and (ap == r or ap.startswith(r + os.sep))), None)
    where = f"別 worktree（{x_root}）" if x_root else "別 worktree"
    print(f"[guard] {where}への{kind}は禁止です。"
          f"トラック境界を越える変更は worktree.md §9 のファイル経由で引き継いでください: {path}",
          file=sys.stderr)
    sys.exit(2)

def _ask(reason: str):
    """PreToolUse の permissionDecision=ask を返す（プロンプト化）。"""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)

def _check_edit_write(data: dict):
    """Edit/Write の対象が高リスクパスなら ask を返す。非該当は素通り(exit 0)。"""
    tool_input = data.get("tool_input") or {}
    path = tool_input.get("file_path") or ""
    if not isinstance(path, str) or not path.strip():
        sys.exit(0)
    rel = _repo_relative(path)
    for pat in HIGH_RISK_EDIT_PATTERNS:
        if re.search(pat, rel):
            _ask(f"高リスクファイル（依存/スキーマ/インフラ）の編集です。確認してください: {rel}")
    sys.exit(0)

# --- I174: 危険操作・外部送信・秘密情報・コンテナ内操作の判定 ---
# 方針（plan_I174.md 0 章・0-9）:
#   - コマンドを「単純コマンド」の列に読み解いてから判定する（付着した ; && | ( )・$(...)・`...`・
#     ヒアドキュメント・リダイレクト・包むコマンド〔sh -c・eval・env・timeout・sudo 等〕を展開する）。
#   - 危険操作・外部送信・秘密情報は列挙で判定し、ホスト・コンテナの両方に当てる。
#   - docker compose exec|run（docker-compose も同じ）の中の操作は、許可リストに入るものだけを素通しにし、
#     それ以外は人の確認（ask）に回す（fail-safe）。素の docker exec|run は列挙だけで判定する。
#   - 脅威モデルは「事故」（Claude が普段書くコマンドでの事故を防ぐ。意図的な回避は対象外）。
_MAX_WRAP_DEPTH = 4                 # sh -c・eval・$(...) の入れ子を展開する深さの上限
_MAX_SCRIPT_BYTES = 1_000_000       # 中身を読む実行ファイルの大きさの上限
# コンテナ内パス → リポジトリ相対パス（docker-compose.yml の backend/celery の volumes に合わせる。
# マウントを変えたらここも更新する）。長い接頭辞から順に照合する。
_CONTAINER_MOUNTS = (("/app/docs/", "docs/"), ("/app/", "backend/"))
_FRONTEND_MOUNTS = (("/app/", "frontend/"),)   # frontend サービスは ./frontend:/app をマウントする
_CONTAINER_WORKDIR = "/app/"
_DOCKER_CLIS = ("docker", "docker-compose")
_PYTHON_RE = re.compile(r"^python(\d+(\.\d+)?)?$")
_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_OPS = ("&&", "||", "|&", ">>", "<<<", ">&", "&>", "<&", ">|", "<>", ";", "&", "|", "(", ")", "<", ">", "\n")
_SEPARATORS = {"&&", "||", ";", "&", "\n", "(", ")", "|", "|&"}
_HEREDOC_RE = re.compile(r"<<(-?)[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_.-]*)\2")   # 区切り語は EOF-PR・END.SQL も可
_HEREDOC_STORE = []                 # ヒアドキュメント本文（$(...) の中から参照されても失われないよう共有する）
_SUBST_STORE = []                   # $(...) / `...` の中身（-c "$(cat <<EOF ...)" のコードを取り出すために共有する）

# Python コード（manage.py shell / python -c / ヒアドキュメント本文 / 実行ファイル）の判定は、構文木（ast）で行う
# （_code_ast）。下の正規表現は、構文として読めないコードのときだけ使う予備（fix-loop 2026-10-17・案 C）。
_CODE_DANGER = (
    (r"(?<!cache)\.\s*delete\s*\(|\b_raw_delete\s*\(", "データ削除（.delete()）"),
    (r"\bobjects\b[^;\n]*?\.update\s*\(", "QuerySet の一括更新（.update()）"),
    (r"\b(qs|queryset|\w+_qs)\s*\.\s*update\s*\(", "QuerySet の一括更新（.update()）"),
    (r"\.\s*bulk_update\s*\(", "一括更新（bulk_update）"),
    (r"call_command\(\s*['\"](flush|sqlflush|reset_db|loaddata)['\"]", "管理コマンドによる DB 全消去・上書き"),
    (r"call_command\(\s*['\"]migrate['\"][^)]*['\"]zero['\"]", "管理コマンドによるマイグレーション巻き戻し"),
    (r"\bshutil\s*\.\s*rmtree\b|\bos\s*\.\s*(remove|unlink|rmdir|removedirs)\s*\(|\.\s*(unlink|rmdir)\s*\(",
     "ファイルの削除（shutil.rmtree / os.remove 等）"),
    (r"\bcache\s*\.\s*clear\s*\(|\.\s*flush(all|db)\s*\(", "キャッシュ（Redis）の全消去"),
)
_CODE_EXTERNAL = (
    (r"\b(send_mail|send_mass_mail|mail_admins|mail_managers)\b", "メール送信"),
    (r"\bdjango\.core\.mail\b", "メール送信（django.core.mail）"),
    (r"\bEmail(Message|MultiAlternatives)\b", "メール送信"),
    (r"\.email_user\(|\bsend_verification_email\b|\bPasswordResetForm\b", "メール送信"),
    (r"\.(delay|apply_async)\(", "celery タスクの起動"),
    (r"\b\w+_task\s*\(", "celery タスク関数の直接実行"),
    (r"\bsend_study_reminders_task\b", "学習リマインダー送信タスク"),
    (r"auth/register/|reverse\(\s*(viewname\s*=\s*)?['\"](\w+:)?register", "登録 API（確認メールを送信）"),
    (r"auth/password-reset/|reverse\(\s*(viewname\s*=\s*)?['\"](\w+:)?password_reset['\"]",
     "パスワード再設定依頼 API（メールを送信）"),
    (r"\bAIQuestionGenerator\b|problems/generate_(ai|adaptive)/|\bopenai\.|['\"](\w+:)?problem-generate-(ai|adaptive)['\"]",
     "OpenAI への送信"),
    (r"\b(smtplib|socket|requests|urllib|httpx|http\.client)\b", "外部への通信"),
    (r"\bsubprocess\b|\bos\s*\.\s*(system|popen|exec\w*|spawn\w*)\s*\(", "外部コマンドの実行"),
    (r"\bos\s*\.\s*environ\b(?!\s*\.\s*setdefault)|\bgetenv\s*\(|/proc/|['\"][^'\"]*\.env['\"]|"
     r"\b(SECRET_KEY|DATABASES|EMAIL_HOST_PASSWORD|OPENAI_API_KEY|SENDGRID_API_KEY|SIMPLE_JWT|SIGNING_KEY|"
     r"settings_dict|_wrapped)\b",
     "秘密情報（環境変数・.env・設定の鍵）の参照"),
)
_DJANGO_CTX_RE = re.compile(r"\bdjango\b|\bmanage\.py\b|\.models\b|DJANGO_SETTINGS_MODULE|\bconnection\b|"
                            r"\bsettings\.|\bopenai\b|\bsmtplib\b")   # 予備（構文として読めないホストのコード）だけで使う

# --- 構文木（ast）による Python コードの判定 ---
_APP_MODULES = ("django", "rest_framework", "problems", "accounts", "studylogs", "core", "celery", "openai")
_SAFE_IMPORT_ROOTS = ("django", "rest_framework", "problems", "accounts", "studylogs", "core", "json",
                      "datetime", "collections", "pprint", "math", "re", "decimal", "uuid", "itertools",
                      "functools", "statistics", "time", "zoneinfo", "os", "sys", "textwrap", "string",
                      "inspect", "importlib", "secrets", "logging", "glob", "hashlib")
_NET_IMPORT_ROOTS = ("smtplib", "socket", "requests", "urllib", "urllib3", "httpx", "http", "ftplib",
                     "telnetlib", "paramiko", "boto3", "aiohttp", "openai")
_EXEC_IMPORT_ROOTS = ("subprocess", "pty", "multiprocessing")
_ORM_QS_METHODS = ("filter", "exclude", "all", "order_by", "select_related", "prefetch_related", "annotate",
                   "only", "defer", "distinct", "none", "using", "values", "values_list", "reverse")
_MAIL_FUNCS = ("send_mail", "send_mass_mail", "mail_admins", "mail_managers")
_MAIL_CLASSES = ("EmailMessage", "EmailMultiAlternatives", "PasswordResetForm")
# 秘密を含む設定の名前（SIMPLE_JWT は SIGNING_KEY に SECRET_KEY を持つ）。属性・文字列・import のどの形でも確認に回す
_SECRET_SETTINGS = ("SECRET_KEY", "DATABASES", "EMAIL_HOST_PASSWORD", "OPENAI_API_KEY", "SENDGRID_API_KEY",
                    "SIMPLE_JWT")
_SECRET_NAMES = _SECRET_SETTINGS + ("SIGNING_KEY", "PASSWORD", "DB_PASSWORD")
_SECRET_ATTRS = ("settings_dict", "_wrapped")   # DB 接続情報（パスワードを含む）・設定の全体
# メール送信・OpenAI への送信を伴う API のルート名（reverse で指定されたとき。名前空間 accounts: 等は外して比べる）
_EXTERNAL_ROUTES = ("register", "register_with_org", "password_reset", "problem-generate-ai",
                    "problem-generate-adaptive")
_DANGER_MANAGE = ("flush", "sqlflush", "reset_db", "loaddata")
# compose の中で素通しにしてよい呼び出しの名前（関数名・メソッド名）。ここに無い呼び出しがあれば確認に回す
_SAFE_CALLS = frozenset((
    # 組み込み・表示・変換
    "print", "len", "list", "dict", "set", "tuple", "str", "int", "float", "bool", "sorted", "reversed",
    "range", "enumerate", "zip", "min", "max", "sum", "any", "all", "isinstance", "type", "repr", "round",
    "abs", "hasattr", "getattr", "format", "next", "iter", "divmod", "chr", "ord", "pprint", "vars", "id",
    "defaultdict", "most_common", "ceil", "floor", "load",
    # 文字列・辞書・リスト（読み取りか、コードの中だけの変更）
    "items", "keys", "values", "get", "append", "extend", "join", "split", "rsplit", "strip", "lstrip",
    "rstrip", "startswith", "endswith", "lower", "upper", "replace", "count", "index", "find",
    "splitlines", "encode", "decode", "copy", "setdefault", "sort", "add", "title", "zfill", "ljust", "rjust",
    # ORM の読み取り
    "filter", "exclude", "order_by", "select_related", "prefetch_related", "annotate", "aggregate", "only",
    "defer", "distinct", "exists", "first", "last", "latest", "earliest", "in_bulk", "values_list", "using",
    "none", "iterator", "explain", "get_user_model", "get_model", "Q", "F", "Count", "Sum", "Avg", "Max",
    "Min", "Value", "Coalesce", "Subquery", "OuterRef", "Exists", "TruncDate", "Cast", "ExpressionWrapper",
    "dates", "datetimes", "get_fields", "get_field", "get_models", "get_app_config", "model_to_dict",
    "get_full_name", "get_short_name", "get_username", "has_usable_password",
    # 1 件だけの書き込み（ループの中のものは危険操作として先に止める）
    "save", "create", "get_or_create", "set_password", "check_password", "refresh_from_db", "full_clean",
    "has_perm", "has_perms",
    # テスト用クライアント
    "force_authenticate", "force_login", "login", "logout", "credentials", "post", "put", "patch", "head",
    "options", "json", "reverse", "resolve",
    # キャッシュの読み取り・1 件の削除
    "get_many", "has_key", "ttl",
    # 日時・JSON・設定
    "now", "today", "timedelta", "date", "datetime", "isoformat", "strftime", "strptime", "astimezone",
    "localdate", "weekday", "isoweekday", "timestamp", "total_seconds",
    "localtime", "make_aware", "dumps", "loads", "setup", "override_settings", "dedent",
    "time", "perf_counter", "monotonic", "process_time",
    # 標準ライブラリの読み取り（ソース・版・ファイル名の一覧・ハッシュ・乱数の文字列・ログの抑止）
    "getsource", "getsourcefile", "getfile", "getdoc", "getmembers", "signature", "version",
    "glob", "iglob", "token_urlsafe", "token_hex", "get_hasher", "make_password", "hexdigest", "sha256",
    "md5", "getLogger", "disable", "sqrt",
    # DB の読み取り（execute の SQL は別に判定する）
    "cursor", "fetchall", "fetchone", "fetchmany",
))

def _ast_dotted(node) -> str:
    """属性の連鎖を 'a.b.c' の文字列にする（呼び出しを含む部分は '()' を付ける）。"""
    parts = []
    while True:
        if isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        elif isinstance(node, ast.Call):
            parts.append("()")
            node = node.func
        elif isinstance(node, ast.Name):
            parts.append(node.id)
            break
        else:
            parts.append("?")
            break
    return ".".join(reversed(parts))

def _ast_str(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None

def _is_cache_ref(node, cache_names=()) -> bool:
    """node が Django のキャッシュ（cache・caches['x']・それを代入した変数）を指すか。"""
    if isinstance(node, ast.Subscript):
        return _ast_dotted(node.value).split(".")[-1] == "caches"
    if isinstance(node, ast.Name) and node.id in cache_names:
        return True
    return _ast_dotted(node).split(".")[-1] == "cache"

class _CodeVisitor(ast.NodeVisitor):
    """Python コードの呼び出し・import・属性の参照を、書き方の揺れに関係なく調べる。"""

    def __init__(self):
        self.danger, self.external, self.unknown = [], [], []
        self.imports_app = False
        self.loop = 0
        self.dict_names, self.qs_names, self.cache_names = set(), set(), set()
        self.setdefault_environ = set()
        self.aliases = {}                        # from x import y as z の z → y（別名の呼び出しを元の名前で判定する）
        self.settings_names = {"settings"}       # django.conf の settings とその別名
        self.environ_names = set()               # from os import environ（as 別名）

    # --- ループ（中の save / delete は一括操作） ---
    def _loop(self, node):
        self.loop += 1
        self.generic_visit(node)
        self.loop -= 1
    visit_For = visit_AsyncFor = visit_While = _loop
    visit_ListComp = visit_SetComp = visit_DictComp = visit_GeneratorExp = _loop

    # --- 代入（辞書の変数・QuerySet の変数を覚える） ---
    def visit_Assign(self, node):
        v = node.value
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if isinstance(v, (ast.Dict, ast.DictComp)) or (isinstance(v, ast.Call) and _ast_dotted(v.func) == "dict"):
            self.dict_names.update(names)
        elif "objects" in _ast_dotted(v).split(".") or (
                isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr in _ORM_QS_METHODS):
            self.qs_names.update(names)
        elif _is_cache_ref(v, self.cache_names):
            self.cache_names.update(names)
        self.generic_visit(node)

    # --- import ---
    def _import(self, mod: str, names=()):
        root = (mod or "").split(".")[0]
        if root in _APP_MODULES:
            self.imports_app = True
        if root in _NET_IMPORT_ROOTS:
            self.external.append(f"外部への通信（import {root}）")
        if root in _EXEC_IMPORT_ROOTS:
            self.external.append(f"外部コマンドの実行（import {root}）")
        if (mod or "").startswith("django.core.mail") or any(n in _MAIL_FUNCS + _MAIL_CLASSES for n in names):
            self.external.append("メール送信（django.core.mail）")
        if root not in _SAFE_IMPORT_ROOTS:
            self.unknown.append(f"import {mod}")

    def visit_Import(self, node):
        for a in node.names:
            self._import(a.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        mod = node.module or ""
        self._import(mod, [a.name for a in node.names])
        for a in node.names:
            if a.asname:
                self.aliases[a.asname] = a.name
            if a.name in _SECRET_NAMES:
                self.external.append(f"秘密情報（import {a.name}）の参照")
            if mod == "django.conf" and a.name == "settings":
                self.settings_names.add(a.asname or a.name)
        self.generic_visit(node)

    # --- 属性・名前の参照（秘密情報） ---
    def visit_Attribute(self, node):
        d = _ast_dotted(node)
        if d.endswith("os.environ") and id(node) not in self.setdefault_environ:
            self.external.append("秘密情報（os.environ）の参照")
        if node.attr in _SECRET_SETTINGS or node.attr in _SECRET_ATTRS or \
                (node.attr == "__dict__" and d.split(".")[-2:-1] and d.split(".")[-2] in self.settings_names):
            self.external.append(f"秘密情報（{node.attr}）の参照")
        self.generic_visit(node)

    def visit_Name(self, node):
        if node.id in self.environ_names and id(node) not in self.setdefault_environ:
            self.external.append("秘密情報（environ）の参照")

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            if _URL_EXTERNAL_RE.search(node.value):
                self.external.append("メール送信・OpenAI への送信を伴う API のパス")
            if "/proc/" in node.value and "environ" in node.value:
                self.external.append("秘密情報（/proc/*/environ）の参照")
            if node.value in _SECRET_NAMES:
                self.external.append(f"秘密情報（'{node.value}'）の参照")
            # open() 以外（Path(...).read_text()・dotenv_values(...) 等）で読む .env も、パスの文字列で捕まえる。
            # Python の文字列は glob として展開されないので、glob の記号を含む文字列（'*'・r'.*' 等）は対象外
            if not re.search(r"[*?\[]", node.value) and _secret_path(node.value):
                self.external.append(f"秘密情報（{node.value}）の参照")

    # --- 呼び出し ---
    def visit_Call(self, node):
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
        if isinstance(f, ast.Name):
            name = self.aliases.get(name, name)               # 別名で import した関数は元の名前で判定する
        recv = f.value if isinstance(f, ast.Attribute) else None
        rd = _ast_dotted(recv) if recv is not None else ""
        args = [_ast_str(a) for a in node.args]
        kws = {k.arg: k.value for k in node.keywords}
        handled = False
        # 危険操作
        if name in ("delete", "_raw_delete"):
            if recv is not None and _is_cache_ref(recv, self.cache_names):
                handled = True                                # cache.delete('k') / caches['x'].delete('k') は 1 件の削除
            else:
                self.danger.append("データ削除（.delete()）")
        if name == "update" and recv is not None:
            parts = rd.split(".")
            is_qs = (isinstance(recv, ast.Call) and isinstance(recv.func, ast.Attribute)
                     and recv.func.attr in _ORM_QS_METHODS) or "objects" in parts or rd.endswith("_set") or \
                (isinstance(recv, ast.Attribute) and isinstance(recv.value, (ast.Name, ast.Attribute))
                 and "()" not in parts and len(parts) >= 2 and parts[0] not in ("os", "sys", "self")) or \
                (isinstance(recv, ast.Name) and (recv.id in self.qs_names or recv.id in ("qs", "queryset")
                                                 or recv.id.endswith("_qs")))
            if is_qs:
                self.danger.append("QuerySet の一括更新（.update()）")
            elif isinstance(recv, ast.Name) and recv.id in self.dict_names:
                handled = True                                # 辞書の update
        if name == "bulk_update":
            self.danger.append("一括更新（bulk_update）")
        if (name == "clear" and recv is not None and (_is_cache_ref(recv, self.cache_names) or "caches" in rd)) \
                or name in ("flushall", "flushdb"):
            self.danger.append("キャッシュ（Redis）の全消去（sessions・celery・レート制限と共有）")
        if self.loop and name in ("save", "delete", "update", "set_password", "create"):
            self.danger.append(f"ループでの一括操作（.{name}()）")
        if name == "call_command" and args and args[0]:
            sub = args[0]
            if sub in _DANGER_MANAGE:
                self.danger.append(f"管理コマンドによる DB 全消去・上書き（{sub}）")
            elif sub == "seed_e2e" and ("--flush" in args or (isinstance(kws.get("flush"), ast.Constant)
                                                             and kws["flush"].value)):
                self.danger.append("管理コマンドによる DB 全消去（seed_e2e flush）")
            elif sub == "migrate" and (len([a for a in args[1:] if a and not a.startswith("-")]) >= 2
                                       or "migration_name" in kws):
                self.danger.append("管理コマンドによるマイグレーションの巻き戻し")
            elif sub in _SAFE_MANAGE or sub in ("migrate", "makemigrations"):
                handled = True
        if name == "rmtree" or (rd.endswith("os") and name in ("remove", "unlink", "rmdir", "removedirs")) or \
                (name in ("unlink", "rmdir") and recv is not None):
            self.danger.append("ファイルの削除（shutil.rmtree / os.remove 等）")
        if name == "execute" and node.args:
            sql = _ast_str(node.args[0])
            if sql is not None and _sql_is_destructive(sql):
                self.danger.append("文字列中の破壊的 SQL（execute）")
            elif sql is not None and _sql_is_safe_read(sql):
                handled = True
        # 外部送信・秘密情報
        if name in _MAIL_FUNCS or name in _MAIL_CLASSES or name in ("email_user", "send_verification_email"):
            self.external.append(f"メール送信（{name}）")
        if name in ("delay", "apply_async"):
            self.external.append("celery タスクの起動")
        # タスクを起点にした呼び出し（t()・t.apply()・t.run()・t.s().apply() 等。別名は元の名前に戻す）
        task = next((p for p in (self.aliases.get(q, q) for q in _ast_dotted(f).split(".")) if p.endswith("_task")),
                    None)
        if task:
            self.external.append(f"celery タスクの実行（{task}）")
        if name in ("system", "popen") and rd.endswith("os") or name.startswith(("exec", "spawn")) and rd.endswith("os"):
            self.external.append("外部コマンドの実行（os.system 等）")
        if name == "AIQuestionGenerator" or rd.startswith("openai"):
            self.external.append("OpenAI への送信")
        if name in ("reverse", "reverse_lazy"):
            view = args[0] if args else _ast_str(kws.get("viewname"))
            if view and view.split(":")[-1] in _EXTERNAL_ROUTES:
                self.external.append(f"メール送信・OpenAI への送信を伴う API（reverse('{view}')）")
        if name in ("getattr", "vars") and node.args and _ast_dotted(node.args[0]).split(".")[-1] in self.settings_names:
            if name == "vars" or len(node.args) < 2 or _ast_str(node.args[1]) is None:
                self.external.append(f"秘密情報（{name}(settings, ...) で設定をまとめて参照）")
        if name == "getenv":
            self.external.append("秘密情報（getenv）の参照")
        if name == "setdefault" and recv is not None and rd.endswith("os.environ"):
            self.setdefault_environ.add(id(recv))             # 書き込みなので秘密情報の参照ではない
            handled = True
        if name == "open":
            path = args[0] if args else None
            mode = args[1] if len(args) > 1 else _ast_str(next((k.value for k in node.keywords if k.arg == "mode"),
                                                                 ast.Constant(value="r")))
            if path and _secret_path(path):
                self.external.append("秘密情報ファイル（.env 等）の読み出し")
            if mode is not None and not any(ch in mode for ch in "wax+"):
                handled = True                                # 読み取りの open
        # compose の許可リスト（一覧に無い呼び出し）
        # .set() は組み込みの set() と同名だが、多対多の関係を置き換える（外す）書き込みなので一覧外として扱う
        safe = (name in _SAFE_CALLS and not (name == "set" and recv is not None)) or \
            (name.startswith("get_") and name.endswith("_display"))
        if not handled and not safe and not (isinstance(f, ast.Name) and name[:1].isupper()):
            self.unknown.append(f"{name or _ast_dotted(f)}()")
        self.generic_visit(node)

@functools.lru_cache(maxsize=64)
def _code_ast(code: str):
    """Python コードを構文木で調べる。(読めたか, 危険操作, 外部送信・秘密情報, 一覧外の呼び出し, アプリを import するか)。"""
    try:
        tree = ast.parse(textwrap.dedent(code))
    except (SyntaxError, ValueError):
        return False, (), (), (), False
    v = _CodeVisitor()
    # environ の別名と setdefault の受け手を先に覚えるため、import と呼び出しを先に見てから全体を見る
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "os":
            v.environ_names.update(a.asname or a.name for a in node.names if a.name == "environ")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "setdefault" \
                and (_ast_dotted(node.func.value).endswith("os.environ")
                     or _ast_dotted(node.func.value) in v.environ_names):
            v.setdefault_environ.add(id(node.func.value))
    v.visit(tree)
    uniq = lambda xs: tuple(dict.fromkeys(xs))
    return True, uniq(v.danger), uniq(v.external), uniq(v.unknown), v.imports_app
_SQL_VERB_RE = re.compile(r"^\s*(drop|truncate|alter|update|delete|insert|create|grant|revoke|with|merge)\b", re.I)
_SECRET_PATH_RE = re.compile(r"(^|/)(\.env(\.[^/]*)?|secrets/.*|[^/]*\.(pem|key))$|^/proc/(\d+|self)/environ$")

def _secret_path(arg: str) -> bool:
    """引数が秘密情報のファイル（.env・鍵・/proc の environ）を指し得るなら True。.example は除く。
    ブレース展開（{.env,x}）と glob（.env*・.e*・/proc/*/environ）で書いたものも、当たり得れば True。"""
    alts = [arg]
    m = re.search(r"\{([^{}]*,[^{}]*)\}", arg)
    if m:
        alts = [arg[:m.start()] + a + arg[m.end():] for a in m.group(1).split(",")]
    for a in alts:
        if a.endswith(".example"):
            continue
        if a.startswith("/proc/") and a.endswith("environ"):
            return True
        base = a.rsplit("/", 1)[-1]
        if re.search(r"[*?\[]", base):
            # glob: シェルの * は . で始まるファイルに当たらないので、. で始まる glob だけを .env 系と見る。
            # glob の記号の前までが .env の頭（.・.e・.en）か .env で始まれば当たり得る（.env.e2* 等）。
            # 鍵ファイルは拡張子を書いたもの（*.pem・*.key）、secrets/ の下はすべて（docs/* などは秘密扱いしない）
            prefix = re.split(r"[*?\[]", base, maxsplit=1)[0]
            dot_env = base.startswith(".") and (".env".startswith(prefix) or prefix.startswith(".env")) \
                and not prefix.startswith(".env.example")
            if dot_env or base.endswith((".pem", ".key")) or re.search(r"(^|/)secrets/", a):
                return True
        elif _SECRET_PATH_RE.search(a):
            return True
    return False
_SECRET_VAR_RE = re.compile(r"\$\{?[A-Za-z_]*(KEY|SECRET|PASSWORD|TOKEN|PASS)[A-Za-z_]*\}?")
_SECRET_READERS = ("cat", "less", "more", "head", "tail", "grep", "rg", "sed", "awk", "strings", "cp",
                   "base64", "xxd", "od", "tac", "nl", "bat", "vi", "vim", "nano", "sort", "uniq", "diff",
                   "cmp", "jq", "wc", "cut", "tr", "file")
_PATTERN_FIRST = ("grep", "rg", "sed", "awk")   # 最初の位置引数がパターン（パスではない）コマンド
# .env に並ぶ設定名に当たりうる検索語（grep -r で .env の行が表示されうるもの）
_ENV_NAME_HINT_RE = re.compile(r"(?i)key|secret|pass|token|api|email|smtp|db_|database|dsn|sendgrid|openai|"
                               r"redis|_url|host|user|=|\.\*|^\.$|^\^")
# curl の引数に当てる外部送信の列挙（_CODE_EXTERNAL のうち API のパスで判定するもの）
_URL_EXTERNAL_RE = re.compile(r"auth/register/|auth/password-reset/|problems/generate_(ai|adaptive)/")

# docker compose exec|run の中の許可リスト（plan_I174.md 0-5・0-9）
_SAFE_MANAGE = ("test", "check", "showmigrations", "sqlmigrate", "help", "version")
_SAFE_SQL_RE = re.compile(r"^\s*(select|show|explain(?!\s*\(|\s+analy[sz]e)|create\s+database|with)\b", re.I)
_UNSAFE_SQL_RE = re.compile(r"\b(lo_export|lo_import|pg_read_file|pg_read_binary_file|pg_write\w*|"
                            r"pg_terminate_backend|pg_cancel_backend|pg_reload_conf|dblink\w*|set_config|"
                            r"copy|insert|update|delete|merge|truncate|drop|alter|grant|revoke|nextval|setval)\b", re.I)
_SAFE_META_RE = re.compile(r"^\\(d[a-zA-Z+]*|l\+?|conninfo|x|timing|pset|echo|q)$")
_SAFE_REDIS = ("PING", "INFO", "KEYS", "GET", "TTL", "PTTL", "EXISTS", "DBSIZE", "SCAN", "TYPE",
               "HGETALL", "LRANGE", "SMEMBERS", "LLEN", "HLEN", "SCARD", "STRLEN")
_SAFE_READ_CMDS = ("ls", "pwd", "cat", "head", "tail", "grep", "wc", "which", "whoami", "id", "true",
                   "date", "uname", "hostname", "stat", "file", "du", "df", "ps", "test", "[", "cut", "tr",
                   "jq", "diff", "cmp", "basename", "dirname", "realpath", "readlink", "cd", "env")
_PIPE_FILTERS = ("grep", "head", "tail", "wc", "sort", "cut", "tr", "jq", "uniq", "cat")
_SAFE_COMPOSE_DEFAULT = ("e2e",)    # コンテナ内のコマンドを書かず既定コマンドで動かしてよいサービス
_CURL_FLAGS = set("sSfIiLkv")
_CURL_VALUE_OPTS = ("-H", "--header", "-w", "--write-out", "-m", "--max-time", "--connect-timeout", "-o",
                    "--output", "-X", "--request", "-A", "--user-agent", "-e", "--referer")
_CURL_BAD_RE = re.compile(r"^(-d|--data.*|-F|--form.*|-T|--upload-file|-x|--proxy.*|--resolve|--connect-to|"
                          r"-K|--config|-O|--remote-name.*|--json|-b|--cookie|-c|--cookie-jar|-u|--user)$")
_COMPOSE_EXEC_BOOL = ("-T", "-d", "-i", "-t", "-it", "-ti", "--rm", "--no-deps", "--service-ports",
                      "--use-aliases", "--build", "--quiet-pull", "--detach", "--interactive", "--tty",
                      "--no-TTY", "--privileged", "--remove-orphans")

def _strip_env(toks: list) -> list:
    """先頭の環境変数の代入（`FOO=1 cmd ...` の `FOO=1`）を除いたトークン列を返す。"""
    i = 0
    while i < len(toks) and _ENV_ASSIGN_RE.match(toks[i]):
        i += 1
    return toks[i:]

def _split_ops(tok: str) -> list:
    """shlex が連結した記号トークン（例 ';('）を演算子ごとに分ける。記号だけでない語はそのまま。"""
    if not tok or any(ch not in ";&|()<>\n" for ch in tok):
        return [tok]
    out, i = [], 0
    while i < len(tok):
        for op in _OPS:
            if tok.startswith(op, i):
                out.append(op)
                i += len(op)
                break
        else:
            out.append(tok[i])
            i += 1
    return out

_COMMENT_PREV = " \t;&|()<>"     # この文字の直後の # は語の始まり＝コメント（bash と同じ）

def _is_comment_start(s: str, i: int) -> bool:
    """s[i] の # がコメントの始まりなら True（行頭か、空白・; & | ( ) < > の直後）。引用符の判定は呼び出し側。"""
    return s[i] == "#" and (i == 0 or s[i - 1] in _COMMENT_PREV)

def _scan_quotes(s: str, state=None):
    """s を読み終えた時点の (引用符の状態〔None / "'" / '"'〕, 行末までコメントの中か) を返す。
    引用符の外の `#`（行頭か、空白・; & | ( ) < > の直後＝_is_comment_start）から行末まではコメントとして飛ばす
    （`# don't` の ' を数えない）。"""
    i, in_comment = 0, False
    while i < len(s):
        ch = s[i]
        if state == "'":
            state = None if ch == "'" else state
        elif ch == "\\" and state != "'":
            i += 1
        elif ch == "#" and state is None and _is_comment_start(s, i):
            nl = s.find("\n", i)
            if nl == -1:
                in_comment = True
                break
            i = nl
        elif ch in ("'", '"'):
            state = ch if state is None else (None if state == ch else state)
        i += 1
    return state, in_comment

def _quote_state(s: str, state=None):
    """s を読み終えた時点の引用符の状態（None / "'" / '"'）を返す（コメントは飛ばす）。"""
    return _scan_quotes(s, state)[0]

def _strip_comments(text: str) -> str:
    """引用符の外のコメント（# から行末）を取り除き、改行は残す（shlex に任せると改行ごと消えて
    次の行のコマンドが前の行の引数としてつながるため）。"""
    out, state = [], None
    for line in text.split("\n"):
        q, i, cut = state, 0, len(line)
        while i < len(line):
            ch = line[i]
            if q == "'":
                q = None if ch == "'" else q
            elif ch == "\\" and q != "'":
                i += 1
            elif ch == "#" and q is None and _is_comment_start(line, i):
                cut = i
                break
            elif ch in ("'", '"'):
                q = ch if q is None else (None if q == ch else q)
            i += 1
        out.append(line[:cut])
        state = q
    return "\n".join(out)

def _cut_heredocs(text: str) -> str:
    """ヒアドキュメントの本文を _HEREDOC_STORE に移し、演算子の位置に __HEREDOC_n__ を置いたテキストを返す。
    引用符の中の `<<`（例: bash -c "cat <<EOF ..."）と、コメントの中の `<<`（例: # 例: cat <<EOF）は
    ヒアドキュメントとして扱わない（次の行の本当のコマンドを本文として飲み込まないため）。"""
    lines = text.split("\n")
    out, i, state = [], 0, None
    while i < len(lines):
        line = lines[i]
        pending = []
        start_state = state

        def repl(m):
            q, in_comment = _scan_quotes(line[:m.start()], start_state)
            if q is not None or in_comment:
                return m.group(0)                    # 引用符の中・コメントの中（# 例: cat <<EOF）
            pending.append((m.group(3), m.group(1) == "-"))
            return f" __HEREDOC_{len(_HEREDOC_STORE) + len(pending) - 1}__ "
        if "<<<" not in line:
            line = _HEREDOC_RE.sub(repl, line)
        state = _quote_state(line, start_state)
        out.append(line)
        i += 1
        for word, strip_tabs in pending:
            body = []
            while i < len(lines):
                cur = lines[i].lstrip("\t") if strip_tabs else lines[i]
                i += 1
                if cur.strip() == word:
                    break
                body.append(lines[i - 1])
            _HEREDOC_STORE.append("\n".join(body))
    return "\n".join(out)

def _subst_mark(body: str, quote) -> str:
    """$(...) の中身を _SUBST_STORE に入れ、位置の目印 __SUBST_n__ を返す（引用符の外なら前後に空白）。"""
    _SUBST_STORE.append(body)
    mark = f"__SUBST_{len(_SUBST_STORE) - 1}__"
    return mark if quote == '"' else f" {mark} "

def _subst_content(k: int):
    """目印 k の $(...) が `cat <<EOF ... EOF` か `cat <ファイル>` なら、その中身（コードや SQL）を返す。"""
    try:
        cmds, _subs = _raw_commands(_SUBST_STORE[k], False, False)
    except Exception:
        return None
    if len(cmds) != 1:
        return None
    c = cmds[0]
    t = _strip_env(c["toks"])
    if t[:1] != ["cat"]:
        return None
    args = [a for a in t[1:] if not a.startswith("-")]
    if c["heredoc"] is not None and not args:
        return c["heredoc"]
    if len(args) == 1 and c["heredoc"] is None:
        return _read_exec_file(args[0], False)
    return None

def _resolve_marks(tok: str) -> str:
    """トークンの中の __SUBST_n__ を、中身が分かるものだけ置き換える（分からないものは目印のまま）。"""
    def repl(m):
        body = _subst_content(int(m.group(1)))
        return body if body is not None else m.group(0)
    return re.sub(r"__SUBST_(\d+)__", repl, tok) if "__SUBST_" in tok else tok

def _cut_substitutions(text: str):
    """$(...) と `...` の中身を取り出し、その位置を目印に置き換える（単一引用符の中は対象外）。"""
    out, subs, i, n, quote = [], [], 0, len(text), None
    while i < n:
        ch = text[i]
        if quote == "'":
            out.append(ch)
            if ch == "'":
                quote = None
            i += 1
            continue
        if ch == "'" and quote is None:
            quote = "'"
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            quote = None if quote == '"' else '"'
            out.append(ch)
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            out.append(text[i:i + 2])
            i += 2
            continue
        if text.startswith("$(", i) and not text.startswith("$((", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if text[j] == "(":
                    depth += 1
                elif text[j] == ")":
                    depth -= 1
                j += 1
            subs.append(text[i + 2:j - 1])
            out.append(_subst_mark(text[i + 2:j - 1], quote))
            i = j
            continue
        if ch == "`":
            j = text.find("`", i + 1)
            j = n if j == -1 else j
            subs.append(text[i + 1:j])
            out.append(_subst_mark(text[i + 1:j], quote))
            i = j + 1
            continue
        out.append(ch)
        i += 1
    return "".join(out), subs

def _new_cmd(toks: list, ctr: bool, compose: bool = False) -> dict:
    return {"toks": toks, "ctr": ctr, "compose": compose, "piped": False, "stdin": None, "stdin_ctr": ctr,
            "heredoc": None, "herestr": None, "writes": False, "write_to": [], "note": None, "workdir": None,
            "service": None}

# 同じコマンドの中で書き込まれるファイル（ファイル名 → 書き込む中身の列。中身が見えない書き込みは None）。
# 判定の時点のディスクには書き込む前の古い中身があるため、実行ファイルの判定ではこちらも合わせて見る。
_WRITTEN = {}

def _record_writes(c: dict):
    """単純コマンド c が書き込むファイルを _WRITTEN に記録する（cat/tee のヒアドキュメントは中身も）。"""
    toks = c["toks"]
    head = os.path.basename(toks[0]) if toks else ""
    targets = list(c["write_to"])
    if head == "tee":
        targets += [a for a in toks[1:] if not a.startswith("-")]
    elif head == "sed" and _has_short(toks[1:], "i", "--in-place"):
        targets += [a for a in toks[1:] if not a.startswith("-")][1:]
    elif head in ("cp", "mv", "install", "ln", "rsync") and len(toks) > 2:
        targets.append(toks[-1])
    body = c["heredoc"] if c["heredoc"] is not None else c["herestr"]
    for t in targets:
        _WRITTEN.setdefault(os.path.basename(t), []).append(body if head in ("cat", "tee") else None)

def _raw_commands(text: str, ctr: bool, compose: bool, loc=(None, None)):
    """テキストを単純コマンド（dict）の列と、$(...) の中身の列に分ける（包むコマンドの展開はしない）。"""
    text = _strip_comments(_cut_heredocs(text))      # ヒアドキュメント本文を抜いてからコメントを除く
    text, subs = _cut_substitutions(text)
    lex = shlex.shlex(text, posix=True, punctuation_chars=";&|()<>\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""                               # コメントは _strip_comments で処理済み（a#b・URL の # は語の一部）
    try:
        toks = []
        for t in lex:
            toks += _split_ops(t)
    except ValueError:
        c = dict(_new_cmd(text.split(), ctr, compose), workdir=loc[0], service=loc[1])
        c["note"] = "引用符が閉じていない"
        return [c], subs
    cmds, cur, i = [], dict(_new_cmd([], ctr, compose), workdir=loc[0], service=loc[1]), 0

    def flush():
        nonlocal cur
        if cur["toks"] or cur["heredoc"] is not None or cur["stdin"] or cur["herestr"] is not None:
            _record_writes(cur)
            cmds.append(cur)
        cur = dict(_new_cmd([], ctr, compose), workdir=loc[0], service=loc[1])
    while i < len(toks):
        t = toks[i]
        if t in _SEPARATORS:
            flush()
            cur["piped"] = t in ("|", "|&")
            i += 1
            continue
        m = re.fullmatch(r"__HEREDOC_(\d+)__", t)
        if m:
            k = int(m.group(1))
            cur["heredoc"] = _HEREDOC_STORE[k] if k < len(_HEREDOC_STORE) else ""
            i += 1
            continue
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        if t.isdigit() and nxt is not None and nxt[:1] in ("<", ">"):
            i += 1                                   # 2>&1 の 2（fd 番号）
            continue
        if t == "<":
            cur["stdin"] = nxt
            i += 2
            continue
        if t == "<<<":
            cur["herestr"] = nxt or ""
            i += 2
            continue
        if t in (">", ">>", ">&", "&>", "<&", ">|", "<>"):
            if t != "<&" and nxt is not None and not nxt.isdigit() and nxt not in ("/dev/null", "-"):
                cur["writes"] = True                 # ファイルへの書き込み（fd の複製・/dev/null は除く）
                cur["write_to"].append(nxt)
            i += 2                                   # 出力先は引数に入れない
            continue
        cur["toks"].append(_resolve_marks(t))       # -c "$(cat <<EOF ...)" の中身をコードとして戻す
        i += 1
    flush()
    return cmds, subs

def _skip_opts(toks: list, value_opts: tuple) -> int:
    """toks の先頭からオプションを読み飛ばした位置を返す（value_opts は値を 1 つ取るオプション）。"""
    i = 0
    while i < len(toks) and toks[i].startswith("-") and toks[i] != "-":
        if toks[i] == "--":
            return i + 1
        i += 2 if (toks[i] in value_opts) else 1
    return i

_DOCKER_GLOBAL_VALUE = ("--context", "-c", "-H", "--host", "--config", "-l", "--log-level")
_COMPOSE_GLOBAL_VALUE = ("-f", "--file", "-p", "--project-name", "--project-directory", "--env-file",
                         "--profile", "--ansi", "--progress", "--parallel")
_EXEC_VALUE = ("-e", "--env", "-u", "--user", "-w", "--workdir", "--index", "--env-file", "-v", "--volume",
               "--name", "--entrypoint", "-p", "--publish", "-l", "--label", "--network", "--pull", "--mount",
               "--platform", "--cap-add", "--cap-drop", "--add-host", "--hostname", "-h", "--memory", "-m",
               "--cpus", "--restart", "--gpus", "--ipc", "--pid", "--security-opt", "--tmpfs", "--ulimit",
               "--volumes-from", "--detach-keys", "--device", "--dns", "--expose", "--link", "--log-driver",
               "--log-opt", "--runtime", "--shm-size", "--stop-signal", "--user", "--group-add")

def _docker_parts(toks: list) -> dict:
    """docker / docker-compose のコマンドを分解する（subs・args・inner・compose・entrypoint・workdir・unknown）。"""
    head = os.path.basename(toks[0])
    rest = toks[1:]
    compose = head == "docker-compose"
    if head == "docker":
        rest = rest[_skip_opts(rest, _DOCKER_GLOBAL_VALUE):]
        if rest[:1] == ["compose"]:
            compose, rest = True, rest[1:]
    if compose:
        rest = rest[_skip_opts(rest, _COMPOSE_GLOBAL_VALUE):]
    if not compose and rest[:1] == ["container"] and rest[1:2] in (["exec"], ["run"], ["inspect"], ["cp"]):
        rest = rest[1:]                              # docker container exec|run|inspect|cp
    subs = (["compose"] if compose else []) + rest[:1]
    res = {"subs": subs, "args": rest[1:], "inner": None, "compose": compose, "entrypoint": None,
           "workdir": None, "unknown": False}
    if subs[-1:] in (["exec"], ["run"]):
        args, j = rest[1:], 0
        while j < len(args) and args[j].startswith("-") and args[j] != "-":
            a = args[j]
            name, _eq, val = a.partition("=")
            if name in _EXEC_VALUE:
                v = val if _eq else (args[j + 1] if j + 1 < len(args) else "")
                if name == "--entrypoint":
                    res["entrypoint"] = v
                if name in ("-w", "--workdir"):
                    res["workdir"] = v
                j += 1 if _eq else 2
                continue
            if a not in _COMPOSE_EXEC_BOOL:
                res["unknown"] = True                # 知らないオプション（値の有無が分からない）
            j += 1
        res["service"] = args[j] if j < len(args) else ""
        res["inner"] = args[j + 1:]
    return res

def _resolve_exec_file(path: str, in_container: bool, workdir=None, service=None):
    """実行ファイルのホスト上のパスを返す。読み替えできなければ None。"""
    root = _current_worktree_root()
    if in_container:
        base = (workdir.rstrip("/") + "/") if workdir else _CONTAINER_WORKDIR
        p = posixpath.normpath(path if path.startswith("/") else base + path)   # -w と .. を考える
        mounts = _FRONTEND_MOUNTS if service and "frontend" in service else _CONTAINER_MOUNTS
        for cpre, hpre in mounts:
            if root and (p == cpre.rstrip("/") or p.startswith(cpre)):
                return os.path.join(root, hpre + p[len(cpre):]) if p.startswith(cpre) else os.path.join(root, hpre)
        return None
    return os.path.abspath(path)

def _read_exec_file(path: str, in_container: bool, workdir=None, service=None):
    """実行ファイルの中身を返す。読めなければ None（stderr に通知）。
    同じコマンドの中で書き込まれるファイルは、ディスクの中身と書き込む中身をすべて合わせて判定する
    （どれが実行されても見逃さないため）。書き込む中身が見えなければ None（確認に回す）。"""
    written = _WRITTEN.get(os.path.basename(path))
    if written is None:
        return _read_exec_file_disk(path, in_container, workdir, service)
    if any(b is None for b in written):
        print(f"[guard] 同じコマンドの中で書き換えるファイルの中身を確認できませんでした: {path}", file=sys.stderr)
        return None
    disk = _read_exec_file_disk(path, in_container, workdir, service, quiet=True)
    return "\n".join(([disk] if disk else []) + written)

@functools.lru_cache(maxsize=256)
def _read_exec_file_disk(path: str, in_container: bool, workdir=None, service=None, quiet=False):
    """ディスク上の実行ファイルの中身を返す。ハーネス自身のコードは ""（判定しない）。読めなければ None。"""
    host = _resolve_exec_file(path, in_container, workdir, service)
    root = _current_worktree_root()
    if host and root and os.path.realpath(host).startswith(
            os.path.join(os.path.realpath(root), "scripts", "claude") + os.sep):
        return ""                                    # 判定パターンを文字列で含むため対象外
    try:
        # 普通のファイルだけを読む（/dev/zero 等の終わりの無いファイルで固まらないため）
        if not host or not os.path.isfile(host) or os.path.getsize(host) > _MAX_SCRIPT_BYTES:
            raise OSError("unresolvable, not a regular file, or too large")
        with open(host, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        if not quiet:
            print(f"[guard] 実行ファイルの中身を確認できませんでした（判定を省略）: {path}", file=sys.stderr)
        return None

def _unknown(c: dict, note: str, toks=None) -> dict:
    d = dict(c)
    d["toks"] = list(toks or [])
    d["note"] = note
    return d

# 値を 1 つ取るオプション（値を中のコマンドと読み違えないため・I174）
_XARGS_VALUE = ("-I", "-n", "-L", "-P", "-d", "-a", "-E", "-s", "--arg-file", "--delimiter", "--max-args",
                "--max-lines", "--max-procs", "--max-chars", "--eof", "--process-slot-var")
_PARALLEL_VALUE = ("-j", "--jobs", "-S", "--sshlogin", "-a", "--arg-file", "--halt", "--colsep", "-C", "-I",
                   "-n", "-N", "--max-args", "-L", "--max-lines", "--delay", "--timeout", "--results", "--joblog",
                   "--tmpdir", "--workdir", "--wd", "-d", "--delimiter", "-E", "--retries", "--memfree", "--load",
                   "--tagstring", "--tag-string", "--basefile", "--return", "--sshloginfile", "--slf", "--env",
                   "--shebang", "-P", "--max-procs", "--block", "--recstart", "--recend", "--header")

def _wrap_skip(head: str, rest: list):
    """包むコマンド（sudo・nice・timeout 等）の後ろの、中のコマンドのトークン列を返す。包むコマンドでなければ None。"""
    if head in ("time", "nohup", "command", "builtin", "setsid", "busybox", "{", "}", "!", "strace", "ltrace",
                # シェルの予約語の後ろ（if X; then Y; fi の Y・while X; do Y; done の Y）もコマンド
                "if", "then", "elif", "else", "while", "until", "do"):
        return rest[_skip_opts(rest, ()):]
    if head == "parallel":                       # parallel cmd ::: 引数（:::: ファイル・:::+ も同じ区切り）
        inner = rest[_skip_opts(rest, _PARALLEL_VALUE):]
        k = next((i for i, t in enumerate(inner) if t.startswith(":::")), len(inner))
        return inner[:k]
    if head == "exec":
        return rest[_skip_opts(rest, ("-a",)):]
    if head == "sudo":
        return rest[_skip_opts(rest, ("-u", "-g", "-C", "-h", "-p", "-U", "-r", "-t")):]
    if head == "nice":
        return rest[_skip_opts(rest, ("-n", "--adjustment")):]
    if head == "ionice":
        return rest[_skip_opts(rest, ("-c", "-n", "-p", "--class", "--classdata")):]
    if head == "stdbuf":
        return rest[_skip_opts(rest, ("-i", "-o", "-e")):]
    if head == "watch":
        return rest[_skip_opts(rest, ("-n", "--interval", "-d")):]
    if head == "timeout":
        j = _skip_opts(rest, ("-s", "--signal", "-k", "--kill-after"))
        return rest[j + 1:]
    if head == "xargs":
        return rest[_skip_opts(rest, _XARGS_VALUE):]
    if head == "flock":
        j = _skip_opts(rest, ("-w", "--timeout", "-E", "--conflict-exit-code", "-c", "--command"))
        return rest[j + 1:]
    return None

def _with_genv(c: dict, assigns: list) -> dict:
    """代入の列（`GIT_DIR=x` 等）のうち git の実行場所を変えるものを c["genv"] に足した c を返す。"""
    g = {k: v for k, v in (a.split("=", 1) for a in assigns if "=" in a) if k in ("GIT_DIR", "GIT_WORK_TREE")}
    return dict(c, genv={**c.get("genv", {}), **g}) if g else c

def _expand(c: dict, depth: int) -> list:
    """包むコマンドを外し、sh -c / eval / スクリプト / docker exec の中身を単純コマンドの列に展開する。"""
    toks = _strip_env(c["toks"])
    # 前置きの GIT_DIR= / GIT_WORK_TREE= は、git の実行場所の判定に使うので控えておく（中のコマンドにも引き継ぐ・I174）
    c = _with_genv(c, c["toks"][:len(c["toks"]) - len(toks)])
    if depth > _MAX_WRAP_DEPTH:
        return [_unknown(c, "入れ子が深すぎる", toks)]
    if not toks:
        return [c] if (c["heredoc"] is not None or c["stdin"] or c["herestr"] is not None) else []
    head = os.path.basename(toks[0])
    rest = toks[1:]

    def again(new_toks):
        d = dict(c)
        d["toks"] = new_toks
        return _expand(d, depth + 1)

    def sub(text, **kw):
        out = list(_parse(text, kw.get("ctr", c["ctr"]), depth + 1, kw.get("compose", c["compose"]),
                          (c.get("workdir"), c.get("service"))))
        return [dict(e, genv={**c["genv"], **e.get("genv", {})}) for e in out] if c.get("genv") else out
    inner = _wrap_skip(head, rest)
    if inner is not None and head in ("parallel", "watch"):
        # parallel / watch は後ろの語をつないでシェルで実行する（`parallel 'rm -rf {}' ::: x`・`watch 'git reset --hard'`）。
        # 引用符で 1 語に包んだ形もあるので、eval と同じくつないだ文字列を読み直す（I174）
        out = sub(" ".join(inner)) if inner else []
        return [dict(e, via_xargs=True) for e in out] if head == "parallel" else out
    if inner is not None and head == "xargs":
        # xargs は標準入力の語を後ろに足して実行する（push の宛先・rm の対象が見えない）
        return [dict(e, via_xargs=True) for e in again(inner)] if inner else []
    if inner is not None:
        flock_cmd = _opt_values(rest, ("-c", "--command")) if head == "flock" else []
        return (again(inner) if inner else []) + [e for s in flock_cmd for e in sub(s)]
    if head == "env":
        j = _skip_opts(rest, ("-u", "--unset", "-C", "--chdir", "-S", "--split-string"))
        k = j
        while k < len(rest) and _ENV_ASSIGN_RE.match(rest[k]):
            k += 1
        c = _with_genv(c, rest[j:k])
        return again(rest[k:]) if k < len(rest) else [dict(c, toks=toks)]   # 引数なしの env は表示
    if head == "eval":
        return sub(" ".join(rest))
    if head in ("su", "script"):
        return [e for s in _opt_values(rest, ("-c", "--command")) for e in sub(s)] or [dict(c, toks=toks)]
    if head == "find":
        out, base, k = [], [], 0
        while k < len(rest):
            if rest[k] in ("-exec", "-execdir", "-ok", "-okdir"):
                j = k + 1
                while j < len(rest) and rest[j] not in (";", "+", "\\;"):
                    j += 1
                out += [dict(e, via_find=True) for e in again(rest[k + 1:j])]
                base.append(rest[k])
                k = j + 1
                continue
            base.append(rest[k])
            k += 1
        return [dict(c, toks=[toks[0]] + base)] + out
    if head in _WRAP_SHELLS:
        flags, pos, k = [], [], 0
        while k < len(rest):                                        # -o/-O は値を 1 つ取る
            a = rest[k]
            if a in ("-o", "+o", "-O", "+O"):
                k += 2
                continue
            if a.startswith(("-", "+")) and not a.startswith("--") and not pos:
                flags.append(a)
            elif not a.startswith("--") or pos:
                pos.append(a)
            k += 1
        if any("c" in f[1:] for f in flags) and pos:
            return sub(pos[0])
        if pos and not any("s" in f[1:] for f in flags):            # sh <スクリプト>
            if not c["ctr"]:
                return [dict(c, toks=toks)]                         # ホストのシェルスクリプトは見ない
            body = _read_exec_file(pos[0], True, c["workdir"], c.get("service"))
            if body is None:
                return [_unknown(c, f"スクリプトを読めない: {pos[0]}", toks)]
            return sub(body)
        if c["heredoc"] is not None:                                # bash -s <<EOF
            return sub(c["heredoc"])
        if c["stdin"]:
            body = _read_exec_file(c["stdin"], c.get("stdin_ctr", False), c["workdir"], c.get("service"))
            if body is None:
                return [_unknown(c, f"スクリプトを読めない: {c['stdin']}", toks)]
            return sub(body)
        return [_unknown(c, "中身の見えないシェル（パイプ等）", toks)]
    if head in _DOCKER_CLIS:
        dp = _docker_parts(toks)
        if dp["inner"] is None:
            return [dict(c, toks=toks, docker=dp)]
        inner_toks = list(dp["inner"])
        if dp["entrypoint"]:
            try:
                inner_toks = shlex.split(dp["entrypoint"]) + inner_toks
            except ValueError:
                inner_toks = dp["entrypoint"].split() + inner_toks
        # ホスト側のリダイレクト（docker ... > /tmp/log）はコンテナ内の書き込みではないので引き継がない
        d = dict(c, toks=inner_toks, ctr=True, compose=dp["compose"], workdir=dp["workdir"], writes=False,
                 service=dp.get("service") or (toks[1] if head == "docker" and len(toks) > 1 else None))
        if dp["compose"] and (dp["unknown"] or dp["entrypoint"]):
            return [_unknown(d, "読めない docker compose のオプション（未知のオプション・--entrypoint）",
                             inner_toks)] + _expand(dict(d, compose=False), depth + 1)
        if not inner_toks:
            if dp["compose"] and dp["subs"][-1] == "run" and dp.get("service") in _SAFE_COMPOSE_DEFAULT:
                return []                                           # 既定コマンドで動かす e2e
            return [_unknown(d, "コンテナ内のコマンドが無い", [])]
        return _expand(d, depth + 1)
    return [dict(c, toks=toks)]

@functools.lru_cache(maxsize=64)
def _parse(text: str, ctr: bool = False, depth: int = 0, compose: bool = False, loc=(None, None)) -> tuple:
    """コマンド文字列を、包むコマンドを外した単純コマンド（dict）のタプルに読み解く。"""
    if depth > _MAX_WRAP_DEPTH:
        return (_unknown(_new_cmd([], ctr, compose), "入れ子が深すぎる"),)
    # 入れ子のシェル（sh -c '…'・bash <<'EOF' の本文）も、内側のシェルが行の継続をつなぐので同じ規則でつなぐ
    text = _join_continuations(text)
    cmds, subs = _raw_commands(text, ctr, compose, loc)
    out = []
    for c in cmds:
        out += _expand(c, depth)
    for s in subs:
        out += list(_parse(s, ctr, depth + 1, compose, loc))
    return tuple(out)

def _opt_values(toks: list, names: tuple) -> list:
    """toks から `-c X` / `-cX` / `-tAc X`（まとめ書き）/ `--command X` / `--command=X` の値をすべて返す。"""
    vals, i = [], 0
    shorts = [n[1] for n in names if not n.startswith("--") and len(n) == 2]
    while i < len(toks):
        t = toks[i]
        hit = False
        for n in names:
            if t == n and i + 1 < len(toks):
                vals.append(toks[i + 1])
                i += 2
                hit = True
                break
            if n.startswith("--") and t.startswith(n + "="):
                vals.append(t[len(n) + 1:])
                i += 1
                hit = True
                break
        if hit:
            continue
        if t.startswith("-") and not t.startswith("--") and len(t) > 2:
            body = t[1:]
            if body[-1] in shorts and body[:-1].isalpha() and i + 1 < len(toks):
                vals.append(toks[i + 1])             # -tAc X
                i += 2
                continue
            if body[0] in shorts:
                vals.append(body[1:])                # -cX（付着形）
                i += 1
                continue
        i += 1
    return vals

def _has_short(toks: list, letter: str, long_name: str = "") -> bool:
    """短いオプションのまとめ書き（-cd・-sfv 等）を含めて、letter のオプションがあれば True。"""
    for t in toks:
        if long_name and (t == long_name or t.startswith(long_name + "=")):
            return True
        if t.startswith("-") and not t.startswith("--") and letter in t[1:]:
            return True
    return False

def _strip_sql_literals(sql: str) -> str:
    return re.sub(r"'(?:[^']|'')*'", "''", sql)

def _strip_sql_comments(sql: str) -> str:
    return re.sub(r"--[^\n]*", " ", re.sub(r"/\*.*?\*/", " ", sql, flags=re.S))

def _sql_is_destructive(sql: str) -> bool:
    """SQL（; 区切りの複数文可）に DROP/TRUNCATE/ALTER TABLE/WHERE なし UPDATE・DELETE があれば True。
    SQL の文字列リテラル（'...'）とコメントの中身は判定しない。"""
    for stmt in _strip_sql_comments(_strip_sql_literals(sql)).split(";"):
        s = stmt.lower()
        if re.search(r"\b(drop|truncate)\b", s) or re.search(r"\balter\s+table\b", s):
            return True
        has_where = re.search(r"\bwhere\b", s)
        if re.search(r"\bupdate\b", s) and re.search(r"\bset\b", s) and not has_where:
            return True
        if re.search(r"\bdelete\s+from\b", s) and not has_where:
            return True
    return False

def _sql_is_safe_read(sql: str) -> bool:
    """SQL の全文が読み取り（SELECT 等）と安全なメタコマンド（\\d 等）だけなら True。"""
    text = _strip_sql_comments(_strip_sql_literals(sql))
    metas = re.findall(r"\\[A-Za-z!?+]+", text)
    if not all(_SAFE_META_RE.match(m) for m in metas):
        return False                                 # \! \gexec \copy \i \o などを行のどこにあっても不可
    body = re.sub(r"\\[A-Za-z!?+]+[^\n;]*", " ", text)
    if _UNSAFE_SQL_RE.search(body):
        return False
    stmts = [s for s in body.split(";") if s.strip()]
    return bool(metas or stmts) and all(_SAFE_SQL_RE.match(s) for s in stmts)

def _code_regex(code: str) -> tuple:
    """予備: 構文として読めないコードを正規表現で調べる (危険操作の理由, 外部送信・秘密情報の理由)。"""
    danger = [why for pat, why in _CODE_DANGER if re.search(pat, code)]
    lits = [lit for _q, lit in re.findall(r"(['\"])(.*?)\1", code, re.S)]
    if any(_SQL_VERB_RE.match(_strip_sql_comments(lit)) and _sql_is_destructive(lit) for lit in lits):
        danger.append("文字列中の破壊的 SQL")
    external = [why for pat, why in _CODE_EXTERNAL if re.search(pat, code)]
    return danger, external

def _code_findings(c: dict):
    """コマンドが実行する Python コードの判定結果を返す。Python でなければ None。
    戻り値: (見えるか, 危険操作, 外部送信・秘密情報, compose の一覧外の呼び出し)。
    - manage.py shell と、コンテナ内の Python のコードは、すべての判定を当てる。
    - ホストの素の python のコードは、アプリ（django 等）を import するときだけ危険操作を判定し、
      秘密情報と、メール送信・AI を伴う API のパスはいつも判定する（文書の書き換え等で止めないため）。"""
    code = _python_code_raw(c)
    if code is False:
        return None
    if code is None or "__SUBST_" in code:
        return False, [], [], ["中身の見えないコード"]
    manage = bool(_django_sub(c["toks"]))
    parsed, danger, external, unknown, imports_app = _code_ast(code)
    if not parsed:
        danger, external = _code_regex(code)
        unknown = ("構文として読めないコード",)
        imports_app = bool(_DJANGO_CTX_RE.search(code))
    danger, external, unknown = list(danger), list(external), list(unknown)
    if not c["ctr"] and not manage:
        if not imports_app:
            danger = []
            external = [x for x in external if "秘密情報" in x or "API" in x]
    return True, danger, external, unknown

def _django_sub(toks: list):
    """Django の管理コマンド呼び出しなら (サブコマンド, 引数) を返す。manage.py / django-admin / python -m django。"""
    for i, t in enumerate(toks):
        b = os.path.basename(t)
        if b == "manage.py" or b == "django-admin":
            return (toks[i + 1], toks[i + 2:]) if i + 1 < len(toks) else ("", [])
        if _PYTHON_RE.match(b):
            k = i + 1
            while k < len(toks) and toks[k] in ("-W", "-X", "-u", "-B", "-E", "-I", "-O", "-OO", "-s", "-S"):
                k += 2 if toks[k] in ("-W", "-X") else 1
            if toks[k:k + 2] == ["-m", "django"]:
                return (toks[k + 2], toks[k + 3:]) if k + 2 < len(toks) else ("", [])
    return None

def _python_code_raw(c: dict):
    """コマンドが実行する Python コード（文字列）を返す。見えないなら None、Python でないなら False。"""
    toks = c["toks"]
    dj = _django_sub(toks)
    if dj and dj[0] == "shell":
        codes = _opt_values(dj[1], ("-c", "--command"))
        if codes:
            return "\n".join(codes)
        if c["heredoc"] is not None:
            return c["heredoc"]
        if c["stdin"]:
            return _read_exec_file(c["stdin"], c.get("stdin_ctr", False), c["workdir"], c.get("service"))
        return None
    head = os.path.basename(toks[0]) if toks else ""
    if _PYTHON_RE.match(head) and not dj:
        rest = toks[1:]
        codes = _opt_values(rest, ("-c",))
        if codes:
            return "\n".join(codes)
        if "-m" in rest:
            return False
        pos = [a for a in rest if not a.startswith("-")]
        k = 0                                        # 最初の位置引数（- を含む。-W / -X の値は飛ばす）
        while k < len(rest) and rest[k].startswith("-") and rest[k] != "-":
            k += 2 if rest[k] in ("-W", "-X") else 1
        first = rest[k] if k < len(rest) else None
        stdin_code = first is None or first == "-" or first.startswith(("/dev/stdin", "/dev/fd/0", "/proc/self/fd/0"))
        if c["stdin"] and stdin_code:              # python3 - < f.py / python3 /dev/stdin < f.py
            return _read_exec_file(c["stdin"], c.get("stdin_ctr", False), c["workdir"], c.get("service"))
        if pos and pos[0].endswith(".py"):
            return _read_exec_file(pos[0], c["ctr"], c["workdir"], c.get("service"))
        if c["heredoc"] is not None:
            return c["heredoc"]
        return None
    return False

def _sql_of(c: dict):
    """psql / dbshell に渡る SQL（文字列）を返す。見えないなら None。"""
    toks = c["toks"]
    dj = _django_sub(toks)
    args = toks[1:]
    if dj and dj[0] == "dbshell":
        args = dj[1][dj[1].index("--") + 1:] if "--" in dj[1] else []
    sqls = _opt_values(args, ("-c", "--command"))
    if sqls:
        sql = ";\n".join(sqls)
        return None if "__SUBST_" in sql else sql            # $(...) を解決できなかった SQL は見えない扱い
    if c["heredoc"] is not None:
        return c["heredoc"]
    if c["herestr"] is not None:
        return c["herestr"]
    return None

def _is_rm_rf(toks: list) -> bool:
    if not toks or os.path.basename(toks[0]) != "rm":
        return False
    args = toks[1:]
    # I174: -f が無くても、端末につながっていない実行では確認が出ずにすべて消える
    return _has_short(args, "r", "--recursive") or _has_short(args, "R")

def _cmd_hard(c: dict) -> str:
    """解除不可で止めるコマンドなら理由を返す（ルートの rm -rf・mkfs・dd・shred）。該当なしは ""。
    コマンド名で判定する（grep のパターンや YYYY-MM-DD などの引数の中の語では止めない）。"""
    toks = c["toks"]
    if _is_rm_rf(toks) and any(t in ("/", "/*") for t in toks[1:]):
        return "rm -rf / is forbidden"
    head = os.path.basename(toks[0]).lower() if toks else ""
    if head in ("dd", "shred") or head == "mkfs" or head.startswith("mkfs."):
        return f"{head} is forbidden"
    return ""

def _git_sub(toks: list):
    rest = toks[1:]
    j = _skip_opts(rest, ("-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"))
    return (rest[j], rest[j + 1:]) if j < len(rest) else ("", [])

def _risky_git_cfg(key: str, val: str) -> bool:
    """push の宛先を保護ブランチ・全ブランチに向ける設定、強制 push になる設定、clean の確認を外す設定なら True。
    安全な値（push.default=simple/current/upstream・保護ブランチ以外への remote.*.push）は通す（I174）。"""
    k, v = key.lower(), val.strip().lower()
    if k == "push.default":
        # matching は同名の全ブランチ、upstream / tracking は上流（origin/develop から作ったブランチなら develop）へ push する
        return v in ("matching", "upstream", "tracking")
    if re.match(r"remote\.[^.]+\.push$", k):
        dst = _norm_push_dest(val.strip(), None)
        return v.startswith("+") or v.lstrip("+") == ":" or dst in PROTECTED_BRANCHES or \
            ":" not in v and v in ("main", "develop")
    if re.match(r"remote\.[^.]+\.mirror$", k):
        return v in ("true", "yes", "on", "1")
    if k == "clean.requireforce":
        return v in ("false", "no", "off", "0", "")             # 空の値も偽
    return False

def _cmd_danger(c: dict) -> list:
    """単純コマンドの危険操作の理由（DANGER_OK=1 で人の承認）。"""
    toks = c["toks"]
    if not toks:
        return []
    head = os.path.basename(toks[0])
    r = []
    if _is_rm_rf(toks):
        r.append("rm -rf requires DANGER_OK=1")
    elif head == "rm" and (c.get("via_find") or c.get("via_xargs")):
        r.append("find -exec rm / xargs rm（find -delete と同じ一括削除）requires DANGER_OK=1")
    if head in ("git", "git.exe"):
        sub, args = _git_sub(toks)
        if sub == "reset" and "--hard" in args:
            r.append("git reset --hard requires DANGER_OK=1")
        # push は最上位の文字列でも判定しているが、入れ子のシェル（bash <<'X' … X・bash -c '…'）の中の push も
        # 単純コマンドごとに同じ判定を当てる（0-13 の bash との差分テストで見つかった見逃し）
        seg = shlex.join(toks)
        if c.get("genv"):
            seg = " ".join(f"{k}={shlex.quote(v)}" for k, v in c["genv"].items()) + " " + seg
        amb = bool(c.get("loc_ambiguous"))
        if c.get("cd") and not amb:
            seg = f"cd {shlex.quote(c['cd'])} ; {seg}"
        gopts = toks[1:toks.index(sub)] if sub in toks else []
        cfg = [gopts[i + 1] for i, t in enumerate(gopts[:-1]) if t == "-c"]
        if sub in ("checkout", "restore", "rm", "checkout-index", "read-tree", "mv"):
            chk = _git_revert_check(seg, bool(c.get("via_xargs") or c.get("via_find")), amb)
            if chk and chk[0] == "block":
                r.append(_revert_reason(chk[1]))
            elif chk:
                c["git_ask"] = chk[1]                        # 確認にする理由（_analyze が "git_unsure" に集める）
        # 設定で保護ブランチへの push・強制 push・確認なしの clean を起こす形
        pos = args[_skip_opts(args, ("-f", "--file", "--blob", "--type", "--default", "--comment"))
                    if sub == "config" else 0:]
        pos = [a for a in pos if not a.startswith("-")]
        if sub == "config" and len(pos) >= 2 and pos[0] in ("set",):
            pos = pos[1:]
        if sub == "config" and len(pos) >= 2 and _risky_git_cfg(pos[0], pos[1]):
            r.append(f"push の宛先・clean の確認を変える設定（{pos[0]}）requires DANGER_OK=1")
        # `-c remote.origin.mirror`（= を省くと真）も同じに読む
        if sub in ("push", "clean") and any(_risky_git_cfg(*(x.split("=", 1) if "=" in x else (x, "true"))) for x in cfg):
            r.append(f"push の宛先・clean の確認を変える設定（-c）付きの git {sub} requires DANGER_OK=1")
        if sub == "push":
            dest = _push_protected_target(seg, amb)
            if dest:
                r.append(f"push to protected branch '{dest}' is forbidden "
                         f"(release/hotfix は計画書明記＋danger-approved＋DANGER_OK=1 のみ)")
            if _push_has_force(seg):
                r.append("force push requires DANGER_OK=1")
        # -d / -x が無くても、追跡済みのディレクトリの中の追跡されていないファイル（未コミットの記録等）は消える
        if sub == "clean" and _has_short(args, "f", "--force") and not _has_short(args, "n", "--dry-run"):
            r.append("追跡されていないファイルの削除（git clean -f）requires DANGER_OK=1")
    dp = c.get("docker")
    if dp:
        subs, args = dp["subs"], dp["args"]
        if subs[:2] == ["compose", "down"] and _has_short(args, "v", "--volumes"):
            r.append("docker compose down -v/--volumes requires DANGER_OK=1")
        if subs[:2] == ["compose", "rm"] and _has_short(args, "v", "--volumes"):
            r.append("ボリュームごと削除（docker compose rm -v）requires DANGER_OK=1")
        if subs[:1] == ["volume"] and args[:1] and args[0] in ("rm", "prune"):
            r.append(f"ボリュームの削除（docker volume {args[0]}）requires DANGER_OK=1")
        if subs[:1] == ["system"] and args[:1] == ["prune"] and "--volumes" in args:
            r.append("ボリュームの削除（docker system prune --volumes）requires DANGER_OK=1")
    dj = _django_sub(toks)
    if dj:
        sub, args = dj
        pos = [a for a in args if not a.startswith("-")]
        if sub in ("flush", "sqlflush", "reset_db"):
            r.append(f"DB 全消去（{sub}）requires DANGER_OK=1")
        elif sub == "loaddata":
            r.append("既存データの上書き（loaddata）requires DANGER_OK=1")
        elif sub == "migrate":
            vals = {args[k + 1] for k, a in enumerate(args[:-1]) if a in ("--database", "--settings",
                                                                          "--pythonpath", "-v", "--verbosity")}
            if len([a for a in pos if a not in vals]) >= 2:
                r.append("マイグレーションの巻き戻し（migrate <app> <移動先>）requires DANGER_OK=1")
        elif sub == "seed_e2e" and "--flush" in args:
            r.append("DB 全消去（seed_e2e --flush）requires DANGER_OK=1")
        elif sub == "dbshell":
            sql = _sql_of(c)
            if (sql is not None and _sql_is_destructive(sql)) or c["stdin"] or c["piped"]:
                r.append("dbshell での破壊的 SQL・流し込み requires DANGER_OK=1")
    if head == "psql":
        sql = _sql_of(c)
        if sql is not None and _sql_is_destructive(sql):
            r.append("destructive SQL requires DANGER_OK=1")
        if _opt_values(toks[1:], ("-f", "--file")) or c["stdin"] or c["piped"]:
            r.append("ダンプ・SQL ファイルの流し込み（psql -f / < / パイプ）requires DANGER_OK=1")
    if head == "dropdb":
        r.append("データベースの削除（dropdb）requires DANGER_OK=1")
    if head == "pg_restore" and _has_short(toks[1:], "c", "--clean"):
        r.append("既存データを消して復元（pg_restore --clean）requires DANGER_OK=1")
    if head == "redis-cli":
        text = " ".join(toks[1:] + [c["heredoc"] or "", c["herestr"] or ""])
        if re.search(r"\bflush(all|db)\b", text, re.I):
            r.append("Redis の全消去（FLUSHALL/FLUSHDB）requires DANGER_OK=1")
    if head == "find" and "-delete" in toks:
        r.append("find -delete requires DANGER_OK=1")
    f = _code_findings(c)
    if f:
        r += [f"{why} requires DANGER_OK=1" for why in f[1]]
    return r

def _grep_recursive_secret(c: dict) -> bool:
    """grep -r が --include なしで .env を含むディレクトリを読むなら True（rg は .gitignore を守るので対象外）。"""
    toks = c["toks"]
    args = toks[1:]
    if not (_has_short(args, "r", "--recursive") or _has_short(args, "R", "--dereference-recursive")):
        return False
    if any(a.startswith("--include") for a in args):
        return False
    pos = [a for a in args if not a.startswith("-")]
    patterns = _opt_values(args, ("-e", "-f", "--regexp", "--file"))
    if not patterns:
        patterns, pos = pos[:1], pos[1:]
    if not any(_ENV_NAME_HINT_RE.search(p) for p in patterns):
        return False                                 # .env の設定名に当たらない検索語なら秘密は出ない
    for d in (pos or ["."]):
        host = _resolve_exec_file(d, True, c["workdir"]) if c["ctr"] else os.path.abspath(d)
        if not host or not os.path.isdir(host):
            continue
        for _dirpath, _dirs, files in _walk_shallow(host, 2):
            if any(_SECRET_PATH_RE.search(f) and not f.endswith(".example") for f in files):
                return True
    return False

def _walk_shallow(top: str, depth: int):
    base = top.rstrip(os.sep).count(os.sep)
    for dirpath, dirs, files in os.walk(top):
        if dirpath.count(os.sep) - base >= depth:
            dirs[:] = []
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", ".venv", "__pycache__")]
        yield dirpath, dirs, files

def _cmd_external(c: dict) -> list:
    """単純コマンドの外部送信・秘密情報の理由（人の確認）。"""
    toks = c["toks"]
    if not toks:
        return []
    head = os.path.basename(toks[0])
    r = []
    dj = _django_sub(toks)
    if dj and dj[0] == "generate_ai_problems":
        r.append("OpenAI への送信（generate_ai_problems）")
    if dj and dj[0] == "sendtestemail":
        r.append("メール送信（sendtestemail）")
    if dj and dj[0] == "diffsettings":
        r.append("設定の表示（diffsettings は秘密情報を含む）")
    if head == "celery" and "call" in toks:
        r.append("celery タスクの起動（celery call）")
    if head == "curl" and any(_URL_EXTERNAL_RE.search(a) for a in toks[1:]):
        r.append("メール送信・OpenAI への送信を伴う API の呼び出し（curl）")
    f = _code_findings(c)
    if f:
        r += f[2]
        # 実行するファイルを引数で指定した python（python3 $G など）では、パイプで流れるのはデータでコードではない
        # ただし `python - 引数` と `python /dev/stdin` は標準入力（パイプの中身）をコードとして実行する
        first = next((a for a in toks[1:] if a == "-" or not a.startswith("-")), None)
        script_arg = _PYTHON_RE.match(head) and not dj and first is not None and first != "-" \
            and not first.startswith(("/dev/", "/proc/"))
        if not f[0] and c["piped"] and not c["compose"] and not script_arg:
            r.append("パイプで流し込むコード（中身が見えない）")
    paths = [a for a in toks[1:] if not a.startswith("-")]
    if head in _PATTERN_FIRST and not _opt_values(toks[1:], ("-e", "-f", "--regexp", "--file")):
        paths = paths[1:]
    secret_path = any(_secret_path(a) for a in paths)
    if head in _SECRET_READERS and secret_path:
        r.append("秘密情報ファイルの読み出し")
    if head == "git" and _git_sub(toks)[0] in ("diff", "show", "blame", "cat-file", "grep") and secret_path:
        r.append("秘密情報ファイルの表示（git）")
    if c["stdin"] and _secret_path(c["stdin"]):
        r.append("秘密情報ファイルの読み出し（< で流し込み）")
    if head in ("grep",) and _grep_recursive_secret(c):
        r.append("秘密情報ファイルを含むディレクトリの再帰検索（grep -r。--include で絞るか rg を使う）")
    if head == "printenv" or (head == "env" and not [a for a in toks[1:] if not a.startswith("-")]):
        r.append("環境変数（秘密情報を含む）の表示")
    if (c["ctr"] or head in ("echo", "printf")) and any(_SECRET_VAR_RE.search(a) for a in toks[1:]):
        r.append("秘密の環境変数の展開")
    if head == "gh" and (toks[1:3] == ["auth", "token"] or "--show-token" in toks
                         or (toks[1:3] == ["auth", "status"] and _has_short(toks[3:], "t"))):
        r.append("GitHub のトークンの表示")
    dp = c.get("docker")
    if dp:
        subs, args = dp["subs"], dp["args"]
        if subs[:2] == ["compose", "config"] and not any(
                a in ("--services", "--volumes", "--profiles", "--images", "--hash", "-q", "--quiet") for a in args):
            r.append("環境変数（秘密情報を含む）の表示（docker compose config）")
        if subs[-1:] == ["inspect"]:
            fmt = _opt_values(args, ("-f", "--format"))
            if not fmt or any(re.search(r"\bEnv\b|json\s+\.\s*\}\}|json\s+\.Config\s*\}\}", x) for x in fmt):
                r.append("環境変数（秘密情報を含む）の表示（docker inspect）")
        if subs[-1:] == ["cp"]:
            r.append("コンテナからのファイルの取り出し（docker cp）")
    return r

def _code_safe(c: dict) -> bool:
    """compose の中の Python コードが、見えていて、すべての呼び出しと import が一覧に入るなら True。"""
    f = _code_findings(c)
    return bool(f) and f[0] and not f[1] and not f[2] and not f[3]

def _container_safe(c: dict) -> bool:
    """docker compose exec|run の中の単純コマンドが許可リストに入るなら True（plan_I174.md 0-5・0-9）。"""
    toks = c["toks"]
    if c["note"] or c["herestr"] is not None or c["writes"] or not toks:
        return False
    head = os.path.basename(toks[0])
    rest = toks[1:]
    if c["piped"] and head not in _PIPE_FILTERS:
        return False
    dj = _django_sub(toks)
    if dj:
        sub, args = dj
        if sub in _SAFE_MANAGE:
            return True
        if sub == "makemigrations":
            return "--check" in args or "--dry-run" in args
        if sub == "migrate":                             # 巻き戻しは _cmd_danger が先に止める
            return not any(a.startswith(("--fake", "--prune", "--run-syncdb")) for a in args)
        if sub == "shell":
            return _code_safe(c)                         # 見えて、すべての呼び出しが一覧に入る
        if sub == "dbshell":
            sql = _sql_of(c)
            return sql is not None and _sql_is_safe_read(sql)
        return False
    if c["heredoc"] is not None and head not in ("psql", "redis-cli") and not _PYTHON_RE.match(head):
        return False
    if head == "ruff":
        return (rest[:1] == ["check"] and not any(a.startswith(("--fix", "--unsafe-fixes")) for a in rest)) or \
            (rest[:1] == ["format"] and ("--check" in rest or "--diff" in rest))
    if head in ("pytest", "flake8", "bandit", "pip-audit", "mypy", "eslint", "tsc", "jest"):
        return not any(a.startswith(("--fix", "--basetemp")) for a in rest)
    if _PYTHON_RE.match(head):
        k = 0
        while k < len(rest) and rest[k] in ("-W", "-X", "-u", "-B", "-E", "-I", "-O", "-OO", "-s", "-S", "-b", "-q"):
            k += 2 if rest[k] in ("-W", "-X") else 1        # -m より前のインタプリタのオプションだけを読み飛ばす
        if rest[k:k + 2] in (["-m", "pytest"], ["-m", "flake8"], ["-m", "mypy"]):
            return True
        if rest[:1] in (["--version"], ["-V"]):
            return True
        return _code_safe(c)
    if head == "pip":
        return rest[:1] in (["freeze"], ["list"], ["show"], ["check"], ["--version"]) or rest[:2] == ["index", "versions"]
    if head == "npm":
        if rest[:1] == ["audit"]:
            return "fix" not in rest
        return rest[:1] in (["test"], ["ls"], ["outdated"], ["view"], ["--version"]) or \
            rest[:2] in (["run", "lint"], ["run", "typecheck"], ["run", "build"], ["run", "test"])
    if head == "npx":
        return rest[:1] in (["tsc"], ["eslint"], ["jest"]) and "--fix" not in rest
    if head == "psql":
        if _opt_values(rest, ("-o", "--output", "-L", "--log-file", "-f", "--file")) or c["stdin"]:
            return False
        sql = _sql_of(c)
        return sql is not None and _sql_is_safe_read(sql)
    if head == "redis-cli":
        if "--scan" in rest:
            return True
        sub = rest[_skip_opts(rest, ("-h", "-p", "-n", "-a", "-u")):]
        return bool(sub) and sub[0].upper() in _SAFE_REDIS
    if head == "celery":
        sub = rest[_skip_opts(rest, ("-A", "--app", "-b", "--broker", "--workdir", "-l", "--loglevel")):]
        return sub[:1] in (["inspect"], ["status"], ["report"])
    if head == "sed":
        if _has_short(rest, "i", "--in-place") or "-n" not in rest and "--quiet" not in rest:
            return False
        scripts = _opt_values(rest, ("-e", "--expression"))
        if not scripts:
            pos = [a for a in rest if not a.startswith("-")]
            scripts = pos[:1]
        return bool(scripts) and all(re.fullmatch(r"(\d+|\$)?(,(\d+|\$))?p|/[^/]*/p", s) for s in scripts)
    if head == "find":
        return not any(a in ("-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprint0",
                             "-fprintf", "-fls") for a in rest)
    if head == "sort":
        return not any(a == "-o" or a.startswith(("--output", "-o")) for a in rest)
    if head == "uniq":
        return len([a for a in rest if not a.startswith("-")]) <= 1
    if head in ("echo", "printf"):
        return not any("$" in a for a in rest)
    if head == "curl":
        k, urls = 0, []
        while k < len(rest):
            a = rest[k]
            if _CURL_BAD_RE.match(a.split("=", 1)[0]):
                return False
            if a in _CURL_VALUE_OPTS:
                v = rest[k + 1] if k + 1 < len(rest) else ""
                if a in ("-o", "--output") and v != "/dev/null":
                    return False
                if a in ("-X", "--request") and v.upper() not in ("GET", "HEAD"):
                    return False
                k += 2
                continue
            if a.startswith("--"):
                if a not in ("--silent", "--show-error", "--fail", "--head", "--include", "--location",
                             "--insecure", "--verbose"):
                    return False
            elif a.startswith("-"):
                if not set(a[1:]) <= _CURL_FLAGS:
                    return False
            else:
                urls.append(a)
            k += 1
        return bool(urls) and all(re.match(r"https?://(localhost|127\.0\.0\.1|backend)(:\d+)?(/|$)", u) for u in urls)
    if head in ("node",) and rest[:1] == ["--version"]:
        return True
    if head == "ps":                       # BSD 形式の e（ps auxe 等）は各プロセスの環境変数＝秘密情報を表示する
        return not any(not a.startswith("-") and "e" in a for a in rest)
    return head in _SAFE_READ_CMDS

def _describe(c: dict) -> str:
    s = " ".join(c["toks"])[:80]
    return f"{s}（{c['note']}）" if c["note"] else (s or "（コマンドなし）")

def _analyze(text: str) -> dict:
    """コマンド文字列の判定結果をまとめて返す（main から使う）。"""
    cmds = _parse(text)
    res = {"hard": "", "danger": [], "external": [], "container": [], "unsure": [], "push_dynamic": [],
           "git_unsure": []}
    # git を実行する場所が 1 つに決まるか（I174 0-15）。決まらなければ、場所に依存する git の判定は確認にする
    amb = _loc_ambiguous(text, cmds)
    cd = None
    for c in cmds:
        t = c["toks"]
        d = None if c["ctr"] else _cd_target(t)
        if d is not None:
            cd = _join_dir(cd, d)
        c["cd"] = cd
        c["loc_ambiguous"] = amb
        # 宛先・実行場所が静的に決まらない push（入れ子の $(…)・xargs / parallel が語を足す形・
        # 場所が 1 つに決まらないのに今のブランチで宛先が決まる形）は確認
        g = _git_find(t)
        if not c["ctr"] and g and t[g[1]] == "push" and (
                _push_dest_dynamic(t) or c.get("via_xargs") or (amb and _push_dest_on_branch(t))
                or _git_loc_dynamic(_git_loc(t, g[0], g[1], cd, c.get("genv")))
                or (_push_dest_on_branch(t) and not _git_loc_trusted(_git_loc(t, g[0], g[1], cd, c.get("genv")), False))):
            res["push_dynamic"].append(_describe(c))
        res["hard"] = res["hard"] or _cmd_hard(c)
        d, e = _cmd_danger(c), _cmd_external(c)
        if c.get("git_ask"):
            res["git_unsure"].append(c["git_ask"])
        res["danger"] += d
        res["external"] += e
        if c["compose"] and not d and not e and not _container_safe(c):
            res["container"].append(_describe(c))
        if c["note"] == "引用符が閉じていない":
            res["unsure"].append("引用符が閉じていない")   # 読み取りが代替経路に落ちた（0-13: 素通しにしない）
    for k in ("danger", "external", "container", "unsure", "push_dynamic", "git_unsure"):
        res[k] = list(dict.fromkeys(res[k]))
    return res

# --- 安全網（plan_I174.md 0-12）: 精密判定が何も返さなかったコマンドの最後の層（確認に回すだけで止めない） ---
_SN_SEPS = frozenset((";", "&", "|", "&&", "||", "|&", ";;", "(", ")", "{", "}", "\n", "!", "`", "$"))
_SN_KEYWORDS = frozenset(("if", "then", "elif", "else", "while", "until", "do", "time", "coproc"))
_SN_WRAPPERS = frozenset(("sudo", "nohup", "env", "nice", "timeout", "xargs", "exec", "command", "builtin", "stdbuf",
                          "ionice", "setsid", "strace", "ltrace", "parallel", "watch", "flock", "busybox"))
_SN_KEYWORDS_EXTRA = ("function",)              # function f { ... } の f はコマンドではないが、{ で位置が戻る

def _sn_judge(seg: list, cds: tuple = ()) -> dict:
    """コマンドの位置から始まる 1 つのコマンドを、精密判定にかけ直した結果（_analyze と同じ形。独自の見分け方は持たない）。
    引用符の中の $( )・`...`・ヒアドキュメントを含むコマンドは、組み直すと意味が変わる（中身が見えない扱いになる）うえ、
    精密判定が中身を読んで判定済みなので、かけ直さない。"""
    if any("$(" in t or "`" in t or "__HEREDOC_" in t for t in seg):
        return {"hard": "", "danger": [], "external": [], "container": [], "git_unsure": [], "push_dynamic": []}
    # 手前の cd を付けて、git の場所の判定に引き継ぐ（場所が 1 つに決まらなければ _analyze が確認側に倒す）
    return _analyze(" ; ".join([shlex.join(c) for c in cds] + [shlex.join(seg)]))

def _safety_net(text: str) -> dict:
    """文法に依存しない区切り（区切り記号・予約語・包むコマンド）でコマンドの位置を見つけ、そこから始まる各コマンドを
    精密判定にかけ直した結果を、_analyze と同じ形（hard / danger / external / container）でまとめて返す。
    精密判定が読み落とした文法（function の本体・coproc・プロセス置換 <( ) の中 等）を素通しにしないための最後の層。
    ヒアドキュメントの本文・引用符の中・コメントは見ない。"""
    body = _strip_comments(_cut_heredocs(text))
    lex = shlex.shlex(body, posix=True, punctuation_chars=";&|()<>\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    try:
        toks = []
        for t in lex:
            toks += _split_ops(t)
    except ValueError:
        toks = body.split()
    # git_unsure / push_dynamic（確認）も集める。捨てると、確認に回した形が安全網の経路で素通しになる（I174 0-15）
    res, i, at_cmd = {"hard": "", "danger": [], "external": [], "container": [], "git_unsure": [], "push_dynamic": []}, 0, True
    cds = []
    while i < len(toks):
        t = toks[i]
        if t in ("<", ">") and i + 1 < len(toks) and toks[i + 1] == "(":
            i += 2                                          # プロセス置換 <( ) / >( ) の中はコマンド
            at_cmd = True
            continue
        if t in _SN_SEPS or t.startswith("$("):
            at_cmd = True
            i += 1
            continue
        if t[:1] in ("<", ">") or (t[:-1].isdigit() and t[-1:] in ("<", ">")) or re.fullmatch(r"\d*[<>]+&?\d*", t):
            i += 2                                          # リダイレクトと宛先は飛ばす
            continue
        if not at_cmd:
            at_cmd = t in ("-exec", "-execdir", "-ok", "-okdir")   # find -exec の後ろはコマンド
            i += 1
            continue
        base = os.path.basename(t)
        if _ENV_ASSIGN_RE.match(t) or base in _SN_KEYWORDS:
            i += 1                                          # コマンドの位置のまま
            continue
        if base in _SN_KEYWORDS_EXTRA:
            i += 2                                          # function と関数名
            continue
        if base in _SN_WRAPPERS:
            i += 1
            while i < len(toks) and (toks[i].startswith("-") or toks[i].isdigit() or _ENV_ASSIGN_RE.match(toks[i])):
                i += 1                                      # 包むコマンドのオプション・数値・VAR=値
            continue
        j = i
        while j < len(toks) and toks[j] not in _SN_SEPS:
            j += 1
        if _cd_target(toks[i:j]) is not None:
            cds.append(toks[i:j])
        an = _sn_judge(toks[i:j], tuple(cds))
        res["hard"] = res["hard"] or an["hard"]
        for k in ("danger", "external", "container", "git_unsure", "push_dynamic"):
            res[k] += an.get(k, [])
        at_cmd = False
        i += 1
    for k in ("danger", "external", "container", "git_unsure", "push_dynamic"):
        res[k] = list(dict.fromkeys(res[k]))
    return res

def _revert_reason(target: str) -> str:
    return (f"git checkout/restore would discard uncommitted changes in '{target}'. "
            f"Edit で戻すか、どうしても必要なら DANGER_OK=1 を前置してください。")

def _danger_reasons(cmd: str, pcmd: str) -> list:
    """DANGER_OK=1 で人の承認に切り替わる危険操作の理由を集める（該当なしは []）。
    cmd は空白を正規化したコマンド、pcmd は改行を保ったコマンド（読み解き用）。
    push 系の既存判定は、ヒアドキュメントの本文を除き、改行を区切りにしたテキストで行う（本文の誤反応を防ぐ）。"""
    cmd = _norm(re.sub(r"__HEREDOC_\d+__", " ", _strip_comments(_cut_heredocs(pcmd))).replace("\n", " ; "))
    reasons = []
    amb = _loc_ambiguous(pcmd)
    dest = _push_protected_target(cmd, amb)
    if dest:
        reasons.append(f"push to protected branch '{dest}' is forbidden "
                       f"(release/hotfix は計画書明記＋danger-approved＋DANGER_OK=1 のみ)")
    if re.search(r"\bgit\b.*\bpush\b.*\s(--all|--mirror)\b", cmd, re.I):
        reasons.append("git push --all/--mirror pushes all refs incl. protected; requires DANGER_OK=1")
    # vestigial --repo flag sets the remote without a positional arg, which evades the
    # positional-based protected detector（security-review/I080）。
    if re.search(r"\bgit\b.*\bpush\b.*\s--repo(\s|=)", cmd, re.I):
        reasons.append("git push --repo can evade protected-branch detection and is unused here; requires DANGER_OK=1")
    # I083: pure _segments ベース。protected 宛先は上で先に理由化済み。
    if _push_has_force(cmd):
        reasons.append("force push requires DANGER_OK=1")
    target = _git_revert_target_on_dirty(cmd, ambiguous=amb)
    if target:
        reasons.append(_revert_reason(target))
    reasons += _analyze(pcmd)["danger"]
    return list(dict.fromkeys(reasons))

_ANSI_C_SIMPLE = {"n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "f": "\f", "v": "\v", "e": "\x1b",
                  "E": "\x1b", "\\": "\\", "'": "'", '"': '"', "?": "?"}

def _ansi_c_decode(text: str, j: int):
    """text[j:] を $'…' の中身として bash と同じ規則で展開し、(展開した文字列, 閉じの ' の位置) を返す。
    \\xHH・\\NNN（8 進）・\\uHHHH・\\UHHHHHHHH・\\n 等を展開する。知らないエスケープは bash と同じく \\ ごと残す。"""
    n, out = len(text), []
    while j < n and text[j] != "'":
        ch = text[j]
        if ch != "\\" or j + 1 >= n:
            out.append(ch)
            j += 1
            continue
        e = text[j + 1]
        if e in _ANSI_C_SIMPLE:
            out.append(_ANSI_C_SIMPLE[e])
            j += 2
        elif e in "xuU":
            width = {"x": 2, "u": 4, "U": 8}[e]
            m = re.match(r"[0-9A-Fa-f]{1,%d}" % width, text[j + 2:])
            if m:
                out.append(chr(int(m.group(0), 16)))
                j += 2 + len(m.group(0))
            else:
                out.append("\\" + e)
                j += 2
        elif e in "01234567":
            m = re.match(r"[0-7]{1,3}", text[j + 1:])
            out.append(chr(int(m.group(0), 8) & 0xFF))
            j += 1 + len(m.group(0))
        elif e == "c" and j + 2 < n:
            out.append(chr(ord(text[j + 2]) & 0x1F))  # \cX（制御文字）
            j += 3
        else:
            out.append("\\" + e)
            j += 2
    return "".join(out), j

def _join_continuations(text: str) -> str:
    """bash と同じ規則で行の継続（\\ と改行）を取り除く（前後をそのままつなげる）。
    単一引用符の中・ヒアドキュメントの本文・コメントの中の \\ は継続ではないので残す
    （残さないと、本文の最後の行の \\ で終わりの行が吸収され、後ろのコマンドを本文として読み飛ばす）。"""
    out, i, n = [], 0, len(text)
    sq = dq = comment = False
    pending = []                                     # この行で始まるヒアドキュメント（タブを除くか, 終わりの語）
    while i < n:
        c = text[i]
        if c == "\n":
            out.append(c)
            i += 1
            comment = False
            if pending and not sq and not dq:
                for strip_tabs, delim in pending:    # 本文は終わりの行までそのまま写す
                    while i < n:
                        j = text.find("\n", i)
                        end = n if j < 0 else j + 1
                        line = text[i:end].rstrip("\r\n")
                        out.append(text[i:end])
                        i = end
                        if (line.lstrip("\t") if strip_tabs else line) == delim:
                            break
                pending = []
            continue
        if comment:
            out.append(c)
            i += 1
            continue
        if c == "\\" and not sq:
            if text.startswith("\n", i + 1):
                i += 2                                # 行の継続: \ と改行を取り除く
                continue
            if text.startswith("\r\n", i + 1):
                i += 2                                # bash では \ が CR だけを打ち消し、LF は区切りのまま
                continue
            out.append(text[i:i + 2])
            i += 2
            continue
        if c == "$" and not sq and not dq and text.startswith("$'", i):
            # ANSI-C 引用 $'…' は、bash と同じ規則でエスケープ（\x6d・\055・\n 等）を展開し、同じ文字列の "…" に
            # 書き換える（ほかの読み取りの処理が $'…' を知らず、\' で閉じたと読み違えて後ろを飲み込むため。
            # 展開しないと $'\x6dain'〔= main〕のような宛先や引数を別の文字列と読み違える）
            s, j = _ansi_c_decode(text, i + 2)
            for ch in ("\\", '"', "$", "`"):
                s = s.replace(ch, "\\" + ch)
            out.append('"' + s + '"')
            i = j + 1
            continue
        if c == "'" and not dq:
            sq = not sq
        elif c == '"' and not sq:
            dq = not dq
        elif c == "#" and not sq and not dq and (i == 0 or text[i - 1] in " \t\n;&|()<>"):
            comment = True
        elif c == "<" and not sq and not dq and text.startswith("<<<", i):
            out.append("<<<")                         # ヒアストリング（1 文字ずらして << と読み違えない）
            i += 3
            continue
        elif c == "<" and not sq and not dq and text.startswith("<<", i):
            m = _HEREDOC_RE.match(text, i)
            if m:
                pending.append((m.group(1) == "-", m.group(3)))
                out.append(m.group(0))
                i += len(m.group(0))
                continue
        out.append(c)
        i += 1
    return "".join(out)

def main():
    data = _load()
    tool_name = data.get("tool_name")
    if tool_name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        # I095: 別 worktree 配下への書込は禁止（パス未取得/境界不能も fail-safe で block）
        path = _edit_path(data)
        x = _cross_worktree(path) if path else None
        if x is True or x is None:
            _block_cross_worktree("編集", path)
        if tool_name in ("Edit", "Write"):
            _check_edit_write(data)  # 既存の高リスク ask は Edit/Write のみ（現状維持）
        sys.exit(0)
    if tool_name != "Bash":
        sys.exit(0)
    tool_input = data.get("tool_input") or {}
    raw = tool_input.get("command") or ""
    if not isinstance(raw, str) or not raw.strip():
        sys.exit(0)

    # I174: 行の継続（\ の直後の改行）は、bash と同じく 1 つのコマンドとして読む（区切りの改行と取り違えると、
    # `git reset \⏎ --hard` が 2 つのコマンドに分かれて素通りする）
    raw = _join_continuations(raw)
    danger_ok = raw.lstrip().startswith("DANGER_OK=1 ")
    # I174: 判定は DANGER_OK=1 を外したコマンドで行う（先頭トークンで判定する eval / sh -c 等を
    # DANGER_OK=1 の前置で見逃さないため。DANGER_OK=1 の扱いは danger_ok で別に決める）。
    cmd = re.sub(r"^DANGER_OK=1\s+", "", _norm(raw))
    # I174: 読み解き（_analyze）は改行を保ったコマンドで行う（ヒアドキュメントの本文と区切りを失わないため）。
    pcmd = re.sub(r"^\s*DANGER_OK=1[ \t]+", "", raw)
    try:
        an = _analyze(pcmd)
    except Exception as e:                       # 判定の失敗で素通しにしない（fail-safe）
        _ask(f"見張りがコマンドを読み解けませんでした（{type(e).__name__}）。内容を確認してください。")

    # hard-block（DANGER_OK=1 でも解除しない）。I174: rm -rf はルート（/・/*）だけをここで止め、
    # それ以外の rm -rf は下の危険操作（DANGER_OK=1 で人の承認）で扱う。mkfs・dd・shred はコマンド名で判定する。
    if an["hard"]:
        _block(an["hard"], raw)

    # I095: worktree 横断書込のブロック（DANGER_OK でも解除しない＝danger_ok ゲートの外）。
    _wt_targets = _bash_write_targets(cmd)
    for _tgt in _wt_targets:
        x = _cross_worktree(_tgt)
        if x is True or x is None:
            _block_cross_worktree("Bash 書込", _tgt)
    # no silent caps: 絶対パス宛先を抽出できないが cd/変数/ラッパー越しで別 worktree を
    # 指し得る経路のみ限界を明示（読み取り・単純な相対書込では誤警告しない）。
    if not _wt_targets and _bash_uncovered_risk(cmd):
        print("[guard] worktree ガードは絶対パス宛先のみ検査します（cd/変数展開越しの宛先は非対象）",
              file=sys.stderr)

    # 危険操作（danger-ops.md）。I174: DANGER_OK=1 は素通しではなく人の承認（ask）に切り替える。
    # settings.json の ask ルールに頼らず、決定論的に人の承認を求める（CLAUDE.md 絶対ルール 4）。
    reasons = _danger_reasons(cmd, pcmd)
    if reasons:
        if danger_ok:
            _ask("DANGER_OK=1 付きの危険操作です。内容を確認して承認してください: " + " / ".join(reasons))
        _block(reasons[0], raw)

    # I174: 外部送信（メール・celery の起動・OpenAI）と秘密情報の表示は、データを壊さないが外へ出るため人の確認にする。
    external = an["external"]
    if external:
        _ask("外部への送信・秘密情報の表示を伴う操作です。確認してください: " + " / ".join(external))

    # I174: コンテナ内の操作は、許可リストに入るものだけ素通しにする（それ以外は人の確認＝fail-safe）。
    if an["container"]:
        _ask("コンテナ内の操作を安全と確認できませんでした（許可リストにない・流し込み・読めない書き方）。"
             "確認してください: " + " / ".join(an["container"]))

    # I083 欠陥1: 動的・不透明な宛先の push は静的に安全と断言できないため ask に degrade する。
    # 危険操作の判定の後に置くことで、rm -rf 等の同居 danger-op を ask で先食いしない。
    # I174: DANGER_OK=1 でも ask にする（宛先が保護ブランチに解決し得るため）。
    # コメントとヒアドキュメントの本文は判定しない（_danger_reasons の push の判定と同じ前処理）
    # I174 0-15: 場所・対象が 1 つに決まらない、未コミットの変更を消しうる git の操作は確認
    if an["git_unsure"]:
        _ask("未コミットの変更を消すかもしれない git の操作です（" + " / ".join(an["git_unsure"]) + "）。確認してください。")
    if an["push_dynamic"] or _push_is_dynamic(
            _norm(re.sub(r"__HEREDOC_\d+__", " ", _strip_comments(_cut_heredocs(pcmd))).replace("\n", " ; "))):
        _ask("動的・不透明な宛先の push です。protected ブランチに解決し得るため確認してください。")

    # I174 0-12: 安全網。上の精密判定がすべて素通しにしたコマンドでも、コマンドの位置ごとに精密判定をかけ直し、
    # 精密判定と同じ扱いにする（解除不可は停止・危険操作は停止〔DANGER_OK=1 なら確認〕・外部送信等は確認）。
    try:
        net = _safety_net(pcmd)
    except Exception as e:                       # 安全網の失敗でも素通しにしない
        _ask(f"見張りが内容を読み切れませんでした（安全網の読み取りに失敗: {type(e).__name__}）。確認してください。")
    if net["hard"]:
        _block(net["hard"], raw)
    if net["danger"]:
        if danger_ok:
            _ask("DANGER_OK=1 付きの危険操作です。内容を確認して承認してください: " + " / ".join(net["danger"]))
        _block(net["danger"][0], raw)
    if net["external"] or net["container"] or net["git_unsure"] or net["push_dynamic"]:
        _ask("見張りが読み落としかけた書き方の中に、確認が必要な操作があります: "
             + " / ".join(net["external"] + net["container"] + net["git_unsure"] + net["push_dynamic"]))
    # I174 0-13: 読み取りが代替経路に落ちた形（引用符が閉じていない等）は、何も見つからなくても確認にする
    if an["unsure"]:
        _ask("見張りがコマンドを読みきれませんでした（" + " / ".join(an["unsure"]) + "）。確認してください。")

    sys.exit(0)

if __name__ == "__main__":
    main()
