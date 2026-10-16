#!/usr/bin/env python3
import functools
import json
import os
import re
import shlex
import subprocess
import sys

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
    クォート不整合（実シェルでもエラー）の場合は素朴分割にフォールバック。"""
    try:
        toks = shlex.split(cmd)
    except ValueError:
        toks = cmd.split()
    segs, seg = [], []
    for t in toks:
        if t in _SHELL_OPS:
            if seg:
                segs.append(seg)
                seg = []
        else:
            seg.append(t)
    if seg:
        segs.append(seg)
    return segs

def _worktree_dirty(path: str) -> bool:
    """<path>（'.' 可）にワークツリー変更があれば True。untracked('??')は除外。
    git 不在/失敗は False（fail-open＝既存方針と同じ）。"""
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain", "--", path],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            return False
        for line in r.stdout.splitlines():
            if len(line) >= 2 and line[:2] != "??" and line[1] != " ":
                return True
        return False
    except Exception:
        return False

def _revert_targets(sub: str, args: list) -> list:
    """checkout/restore のうちワークツリーを破壊し得る pathspec を返す。破壊しない形は []。"""
    if sub == "checkout" and any(a in ("-b", "-B", "--orphan") for a in args):
        return []  # ブランチ作成
    if sub == "restore":
        has_staged = ("--staged" in args) or ("-S" in args)
        has_worktree = ("--worktree" in args) or ("-W" in args)
        if has_staged and not has_worktree:
            return []  # index のみ・ワークツリー非破壊
    cand = args[args.index("--") + 1:] if "--" in args else args
    return [a for a in cand if not a.startswith("-")]

def _git_revert_target_on_dirty(cmd: str):
    """複合コマンドを分割し、git checkout/restore の pathspec が dirty なら最初の該当パスを返す。"""
    for toks in _segments(cmd):
        if "git" not in toks:
            continue
        rest = toks[toks.index("git") + 1:]
        if not rest or rest[0] not in ("checkout", "restore"):
            continue
        for t in _revert_targets(rest[0], rest[1:]):
            if _worktree_dirty(t):
                return t
    return None

# --- git push の保護ブランチ宛先判定（I080） ---
PROTECTED_BRANCHES = ("develop", "main")

def _current_branch():
    """現ブランチ名を返す。git 不在/失敗は None（fail-open＝既存 HEAD チェックと同方針）。"""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True
        )
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None

def _norm_push_dest(token: str, cur_branch):
    """push 宛先トークンを正規化して宛先ブランチ名を返す（判定不能は None）。
    'src:dst' なら dst 採用 → force-shorthand '+'（先頭/dst 側いずれも）除去 →
    'refs/heads/' 接頭辞除去 → 'HEAD' は現ブランチ解決。"""
    t = token
    if ":" in t:
        t = t.split(":", 1)[1]          # 'src:dst' の dst を採用
    t = t.lstrip("+")                    # force-shorthand '+'（先頭 / dst 側）を除去
    if t.startswith("refs/heads/"):
        t = t[len("refs/heads/"):]
    if t == "HEAD":
        return cur_branch               # None 可（detached/fail-open）
    return t or None

def _push_protected_target(cmd: str):
    """git push が protected ブランチを名前/refspec で宛先にするなら宛先名を返す。非該当は None。
    複合コマンドは _segments(I081)で分割して各セグメントを判定。
    --all/--mirror・--repo は positional を持たない/前提を崩すため main() 側の独立チェックで扱う。"""
    for toks in _segments(cmd):
        if "git" not in toks or "push" not in toks:
            continue
        after = toks[toks.index("push") + 1:]
        positionals = [a for a in after if not a.startswith("-")]
        refspecs = positionals[1:] if positionals else []   # [0]=remote、以降=refspec
        cur = None
        if not refspecs:                                     # 宛先明示なし → 現ブランチが宛先
            cur = _current_branch()
            if cur in PROTECTED_BRANCHES:
                return cur
            continue
        for rs in refspecs:
            if cur is None:
                cur = _current_branch()
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
        if "git" in toks and "push" in toks:
            after = toks[toks.index("push") + 1:]
            if any(_is_force_flag(t) for t in after):
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
        if "git" in toks and "push" in toks:
            after = " ".join(toks[toks.index("push") + 1:])
            if any(ch in after for ch in "$`{("):
                return True
        # (ii) 構造的に不透明なラッパー（先頭トークンで判定＝branch/remote 名の偶然一致を排除）
        head = toks[0]
        if head == "eval" and any("push" in t for t in toks[1:]):
            return True
        if head in _WRAP_SHELLS and "-c" in toks:
            ci = toks.index("-c")
            wrapped = toks[ci + 1] if ci + 1 < len(toks) else ""
            if "push" in wrapped:
                return True
        if head == "git":
            for i, t in enumerate(toks[:-1]):
                if t == "-c" and toks[i + 1].startswith("alias.") and "push" in toks[i + 1]:
                    return True
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

# --- I174: 危険操作・外部送信・コンテナ内操作の判定 ---
# 方針（plan_I174.md 0 章）:
#   - コマンドを「単純コマンド」の列に読み解いてから判定する（付着した ; && | ( ) $(...) `...`・
#     ヒアドキュメント・リダイレクト・包むコマンド〔sh -c・eval・env・timeout 等〕を展開する）。
#   - 危険操作・外部送信・秘密情報は列挙で判定し、ホストとコンテナの両方に当てる。
#   - コンテナ内（docker exec / docker compose exec|run / docker-compose exec|run）の操作は、
#     許可リストに入るものだけを素通しにし、それ以外は人の確認（ask）に回す（fail-safe）。
_MAX_WRAP_DEPTH = 4                 # sh -c・eval・$(...) の入れ子を展開する深さの上限
_MAX_SCRIPT_BYTES = 1_000_000       # 中身を読む実行ファイルの大きさの上限
# コンテナ内パス → リポジトリ相対パス（docker-compose.yml の backend/celery の volumes に合わせる。
# マウントを変えたらここも更新する）。長い接頭辞から順に照合する。
_CONTAINER_MOUNTS = (("/app/docs/", "docs/"), ("/app/", "backend/"))
_CONTAINER_WORKDIR = "/app/"
_DOCKER_CLIS = ("docker", "docker-compose")
_PYTHON_RE = re.compile(r"^python(\d+(\.\d+)?)?$")
_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_OPS = ("&&", "||", "|&", ">>", "<<<", ">&", "&>", "<&", ">|", "<>", ";", "&", "|", "(", ")", "<", ">", "\n")
_SEPARATORS = {"&&", "||", ";", "&", "\n", "(", ")", "|", "|&"}
_HEREDOC_RE = re.compile(r"<<(-?)[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")

# 危険操作・外部送信の列挙（Python コード＝manage.py shell / python -c / ヒアドキュメント本文 / 実行ファイル）
_CODE_DANGER = (
    (r"\.delete\(", "データ削除（.delete()）"),
    (r"\b(objects|qs|queryset|\w+_qs)\b[^\n]*?\.update\(", "QuerySet の一括更新（.update()）"),
    (r"\.bulk_update\(", "一括更新（bulk_update）"),
    (r"call_command\(\s*['\"](flush|sqlflush|reset_db|loaddata)['\"]", "管理コマンドによる DB 全消去・上書き"),
    (r"call_command\(\s*['\"]migrate['\"][^)]*['\"]zero['\"]", "管理コマンドによるマイグレーション巻き戻し"),
)
_CODE_EXTERNAL = (
    (r"\b(send_mail|send_mass_mail|mail_admins|mail_managers)\b", "メール送信"),
    (r"\bdjango\.core\.mail\b", "メール送信（django.core.mail）"),
    (r"\bEmail(Message|MultiAlternatives)\b", "メール送信"),
    (r"\.email_user\(|\bsend_verification_email\b|\bPasswordResetForm\b", "メール送信"),
    (r"\.(delay|apply_async)\(", "celery タスクの起動"),
    (r"\b\w+_task\s*\(", "celery タスク関数の直接実行"),
    (r"\bsend_study_reminders_task\b", "学習リマインダー送信タスク"),
    (r"auth/register/", "登録 API（確認メールを送信）"),
    (r"auth/password-reset/", "パスワード再設定依頼 API（メールを送信）"),
    (r"\bAIQuestionGenerator\b|problems/generate_(ai|adaptive)/|\bopenai\.", "OpenAI への送信"),
)
_SQL_VERB_RE = re.compile(r"^\s*(drop|truncate|alter|update|delete|insert|create|grant|revoke)\b", re.I)
_SECRET_PATH_RE = re.compile(r"(^|/)(\.env(\.[^/]*)?|secrets/.*|[^/]*\.(pem|key))$")
_SECRET_READERS = ("cat", "less", "more", "head", "tail", "grep", "rg", "sed", "awk", "strings", "cp",
                   "base64", "xxd", "od", "tac", "nl", "bat", "vi", "vim", "nano")

# コンテナ内の許可リスト（plan_I174.md 0-5）
_SAFE_MANAGE = ("test", "check", "showmigrations", "sqlmigrate", "dumpdata", "diffsettings", "help",
                "version", "collectstatic")
_SAFE_SQL_RE = re.compile(r"^\s*(select|show|explain(?!\s+analyze)|create\s+database)\b", re.I)
_SAFE_META_RE = re.compile(r"^\\(d[a-zA-Z+]*|l\+?|conninfo|x|timing|pset|echo|q)(\s|$)")   # \! \copy \i \g は不可
_SAFE_REDIS = ("PING", "INFO", "KEYS", "GET", "TTL", "PTTL", "EXISTS", "DBSIZE", "SCAN", "--SCAN", "TYPE",
               "HGETALL", "LRANGE", "SMEMBERS", "LLEN", "HLEN", "SCARD", "STRLEN")
_SAFE_READ_CMDS = ("ls", "pwd", "cat", "head", "tail", "grep", "wc", "which", "whoami", "id", "echo", "true",
                   "date", "uname", "hostname", "stat", "file", "du", "df", "ps", "printf", "test", "[", "sort",
                   "uniq", "cut", "tr", "jq", "diff", "cmp", "basename", "dirname", "realpath", "readlink")

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

def _cut_heredocs(text: str):
    """ヒアドキュメントの本文を取り出し、演算子の位置に __HEREDOC_n__ を置いたテキストと本文の一覧を返す。"""
    lines = text.split("\n")
    out, bodies, i = [], [], 0
    while i < len(lines):
        line = lines[i]
        pending = []

        def repl(m):
            pending.append((m.group(3), m.group(1) == "-"))
            return f" __HEREDOC_{len(bodies) + len(pending) - 1}__ "
        if "<<<" not in line:
            line = _HEREDOC_RE.sub(repl, line)
        out.append(line)
        i += 1
        for word, strip_tabs in pending:
            body = []
            while i < len(lines):
                cur = lines[i].lstrip("\t") if strip_tabs else lines[i]
                i += 1
                if cur == word:
                    break
                body.append(lines[i - 1])
            bodies.append("\n".join(body))
    return "\n".join(out), bodies

def _cut_substitutions(text: str):
    """$(...) と `...` の中身を取り出し、その位置を __SUBST__ に置き換える（単一引用符の中は対象外）。"""
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
            out.append(" __SUBST__ ")
            i = j
            continue
        if ch == "`":
            j = text.find("`", i + 1)
            j = n if j == -1 else j
            subs.append(text[i + 1:j])
            out.append(" __SUBST__ ")
            i = j + 1
            continue
        out.append(ch)
        i += 1
    return "".join(out), subs

def _new_cmd(toks: list, ctr: bool) -> dict:
    return {"toks": toks, "ctr": ctr, "piped": False, "stdin": None, "heredoc": None, "herestr": None,
            "note": None}

def _raw_commands(text: str, ctr: bool):
    """テキストを単純コマンド（dict）の列と、$(...) の中身の列に分ける（包むコマンドの展開はしない）。"""
    text, bodies = _cut_heredocs(text)
    text, subs = _cut_substitutions(text)
    lex = shlex.shlex(text, posix=True, punctuation_chars=";&|()<>\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    try:
        toks = []
        for t in lex:
            toks += _split_ops(t)
    except ValueError:
        c = _new_cmd(text.split(), ctr)
        c["note"] = "引用符が閉じていない"
        return [c], subs
    cmds, cur, piped, i = [], _new_cmd([], ctr), False, 0

    def flush():
        nonlocal cur
        if cur["toks"] or cur["heredoc"] is not None or cur["stdin"] or cur["herestr"] is not None:
            cmds.append(cur)
        cur = _new_cmd([], ctr)
    while i < len(toks):
        t = toks[i]
        if t in _SEPARATORS:
            flush()
            cur["piped"] = t in ("|", "|&")
            i += 1
            continue
        m = re.fullmatch(r"__HEREDOC_(\d+)__", t)
        if m:
            cur["heredoc"] = bodies[int(m.group(1))]
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
            i += 2                                   # 出力先は引数に入れない
            continue
        cur["toks"].append(t)
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
               "--name", "--entrypoint", "-p", "--publish", "-l", "--label", "--network", "--pull")

def _docker_parts(toks: list):
    """docker / docker-compose のコマンドを (サブコマンド列, コンテナ内コマンド or None) に分解する。"""
    head = os.path.basename(toks[0])
    rest = toks[1:]
    if head == "docker":
        rest = rest[_skip_opts(rest, _DOCKER_GLOBAL_VALUE):]
        if rest[:1] == ["compose"]:
            rest = rest[1:]
            rest = rest[_skip_opts(rest, _COMPOSE_GLOBAL_VALUE):]
            subs = ["compose"] + rest[:1]
        else:
            subs = rest[:1]
    else:
        rest = rest[_skip_opts(rest, _COMPOSE_GLOBAL_VALUE):]
        subs = ["compose"] + rest[:1]
    if subs[-1:] in (["exec"], ["run"]):
        args = rest[1:]
        j = _skip_opts(args, _EXEC_VALUE)
        return subs, rest[1:], args[j + 1:]          # [j] はサービス名 / コンテナ名
    return subs, rest[1:], None

def _resolve_exec_file(path: str, in_container: bool):
    """実行ファイルのホスト上のパスを返す。読み替えできなければ None。"""
    root = _current_worktree_root()
    if in_container:
        p = path if path.startswith("/") else _CONTAINER_WORKDIR + path
        for cpre, hpre in _CONTAINER_MOUNTS:
            if p.startswith(cpre) and root:
                return os.path.join(root, hpre + p[len(cpre):])
        return None
    return os.path.abspath(path)

@functools.lru_cache(maxsize=256)
def _read_exec_file(path: str, in_container: bool):
    """実行ファイルの中身を返す。ハーネス自身のコードは ""（判定しない）。読めなければ None（stderr に通知）。"""
    host = _resolve_exec_file(path, in_container)
    root = _current_worktree_root()
    if host and root and os.path.realpath(host).startswith(
            os.path.join(os.path.realpath(root), "scripts", "claude") + os.sep):
        return ""                                    # 判定パターンを文字列で含むため対象外
    try:
        if not host or os.path.getsize(host) > _MAX_SCRIPT_BYTES:
            raise OSError("unresolvable or too large")
        with open(host, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        print(f"[guard] 実行ファイルの中身を確認できませんでした（判定を省略）: {path}", file=sys.stderr)
        return None

def _unknown(ctr: bool, note: str, toks=None) -> dict:
    c = _new_cmd(list(toks or []), ctr)
    c["note"] = note
    return c

def _expand(c: dict, depth: int) -> list:
    """包むコマンドを外し、sh -c / eval / スクリプト / docker exec の中身を単純コマンドの列に展開する。"""
    toks = _strip_env(c["toks"])
    if depth > _MAX_WRAP_DEPTH:
        return [_unknown(c["ctr"], "入れ子が深すぎる", toks)]
    if not toks:
        return [c] if (c["heredoc"] is not None or c["stdin"] or c["herestr"] is not None) else []
    head = os.path.basename(toks[0])
    rest = toks[1:]
    nc = dict(c)

    def again(new_toks):
        d = dict(c)
        d["toks"] = new_toks
        return _expand(d, depth + 1)
    if head in ("time", "nohup", "command", "builtin", "exec", "sudo", "{", "}", "!"):
        return again(rest[_skip_opts(rest, ("-u", "-g"))] if head == "sudo" else rest)
    if head == "nice":
        return again(rest[_skip_opts(rest, ("-n", "--adjustment"))])
    if head == "timeout":
        j = _skip_opts(rest, ("-s", "--signal", "-k", "--kill-after"))
        return again(rest[j + 1:])
    if head == "xargs":
        j = _skip_opts(rest, ("-I", "-i", "-n", "-L", "-P", "-d", "-a", "-E", "-s"))
        return again(rest[j:])
    if head == "env":
        j = _skip_opts(rest, ("-u", "--unset", "-C", "--chdir", "-S", "--split-string"))
        k = j
        while k < len(rest) and _ENV_ASSIGN_RE.match(rest[k]):
            k += 1
        return again(rest[k:]) if k < len(rest) else [c]          # 引数なしの env は表示（秘密情報）
    if head == "eval":
        return list(_parse(" ".join(rest), c["ctr"], depth + 1))
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
            return list(_parse(pos[0], c["ctr"], depth + 1))
        if pos and not any("s" in f[1:] for f in flags):            # sh <スクリプト>
            if not c["ctr"]:
                return [c]                                          # ホストの bash スクリプトは見ない
            body = _read_exec_file(pos[0], True)
            if body is None:
                return [_unknown(True, f"スクリプトを読めない: {pos[0]}", toks)]
            return list(_parse(body, True, depth + 1))
        if c["heredoc"] is not None:                                # bash -s <<EOF
            return list(_parse(c["heredoc"], c["ctr"], depth + 1))
        if c["stdin"]:
            body = _read_exec_file(c["stdin"], False)
            if body is None:
                return [_unknown(c["ctr"], f"スクリプトを読めない: {c['stdin']}", toks)]
            return list(_parse(body, c["ctr"], depth + 1))
        return [_unknown(c["ctr"], "中身の見えないシェル（パイプ等）", toks)]
    if head in _DOCKER_CLIS:
        subs, _args, inner = _docker_parts(toks)
        if inner is None:
            nc["docker_subs"] = subs
            return [nc]
        if not inner:
            return [_unknown(True, "コンテナ内のコマンドが無い", toks)]
        d = dict(c)
        d["toks"], d["ctr"] = inner, True
        return _expand(d, depth + 1)
    nc["toks"] = toks
    return [nc]

@functools.lru_cache(maxsize=64)
def _parse(text: str, ctr: bool = False, depth: int = 0) -> tuple:
    """コマンド文字列を、包むコマンドを外した単純コマンド（dict）のタプルに読み解く。"""
    if depth > _MAX_WRAP_DEPTH:
        return (_unknown(ctr, "入れ子が深すぎる"),)
    cmds, subs = _raw_commands(text, ctr)
    out = []
    for c in cmds:
        out += _expand(c, depth)
    for s in subs:
        out += list(_parse(s, ctr, depth + 1))
    return tuple(out)

def _opt_value(toks: list, names: tuple):
    """toks から `-c X` / `-cX` / `--command X` / `--command=X` 形式の値を返す（無ければ None）。"""
    for i, t in enumerate(toks):
        if t in names and i + 1 < len(toks):
            return toks[i + 1]
        for n in names:
            if n.startswith("--") and t.startswith(n + "="):
                return t[len(n) + 1:]
            if not n.startswith("--") and len(n) == 2 and t.startswith(n) and len(t) > 2:
                return t[2:]
    return None

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

def _sql_is_destructive(sql: str) -> bool:
    """SQL（; 区切りの複数文可）に DROP/TRUNCATE/ALTER TABLE/WHERE なし UPDATE・DELETE があれば True。
    SQL の文字列リテラル（'...'）の中身は判定しない。"""
    for stmt in _strip_sql_literals(sql).split(";"):
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
    """SQL の全文が読み取り（SELECT 等）とメタコマンド（\\d 等）だけなら True。"""
    lines = _strip_sql_literals(sql).split("\n")
    meta = [ln.strip() for ln in lines if ln.strip().startswith("\\")]
    body = "\n".join(ln for ln in lines if not ln.strip().startswith("\\"))
    if not all(_SAFE_META_RE.match(m) for m in meta):
        return False
    stmts = [s for s in body.split(";") if s.strip()]
    return bool(meta or stmts) and all(_SAFE_SQL_RE.match(s) for s in stmts)

def _code_reasons(code: str) -> tuple:
    """実行される Python コードの (危険操作の理由, 外部送信の理由) を返す。"""
    danger = [why for pat, why in _CODE_DANGER if re.search(pat, code)]
    lits = [lit for _q, lit in re.findall(r"(['\"])(.*?)\1", code, re.S)]
    if any(_SQL_VERB_RE.match(lit) and _sql_is_destructive(lit) for lit in lits):
        danger.append("文字列中の破壊的 SQL")
    external = [why for pat, why in _CODE_EXTERNAL if re.search(pat, code)]
    return danger, external

def _django_sub(toks: list):
    """Django の管理コマンド呼び出しなら (サブコマンド, 引数) を返す。manage.py / django-admin / python -m django。"""
    for i, t in enumerate(toks):
        b = os.path.basename(t)
        if b == "manage.py" or b == "django-admin":
            return (toks[i + 1], toks[i + 2:]) if i + 1 < len(toks) else ("", [])
        if _PYTHON_RE.match(b) and toks[i + 1:i + 3] == ["-m", "django"]:
            return (toks[i + 3], toks[i + 4:]) if i + 3 < len(toks) else ("", [])
    return None

def _python_code(c: dict):
    """コマンドが実行する Python コード（文字列）を返す。見えないなら None、Python でないなら False。"""
    toks = c["toks"]
    dj = _django_sub(toks)
    if dj and dj[0] == "shell":
        code = _opt_value(dj[1], ("-c", "--command"))
        if code is not None:
            return code
        if c["heredoc"] is not None:
            return c["heredoc"]
        if c["stdin"]:
            return _read_exec_file(c["stdin"], False)
        return None
    head = os.path.basename(toks[0]) if toks else ""
    if _PYTHON_RE.match(head) and not dj:
        rest = toks[1:]
        code = _opt_value(rest, ("-c",))
        if code is not None:
            return code
        if "-m" in rest:
            return False
        pos = [a for a in rest if not a.startswith("-")]
        if pos and pos[0].endswith(".py"):
            return _read_exec_file(pos[0], c["ctr"])
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
    sql = _opt_value(args, ("-c", "--command"))
    if sql is not None:
        return sql
    if c["heredoc"] is not None:
        return c["heredoc"]
    if c["herestr"] is not None:
        return c["herestr"]
    return None

def _cmd_hard(c: dict) -> bool:
    """解除不可で止めるコマンド（ルートの rm -rf）なら True。"""
    return any(t in ("/", "/*") for t in _rm_rf_targets_of(c["toks"]))

def _rm_rf_targets_of(toks: list) -> list:
    if not toks or os.path.basename(toks[0]) != "rm":
        return []
    args = toks[1:]
    rec = _has_short(args, "r", "--recursive") or _has_short(args, "R")
    force = _has_short(args, "f", "--force")
    return [a for a in args if not a.startswith("-")] if (rec and force) else []

def _git_sub(toks: list):
    rest = toks[1:]
    j = _skip_opts(rest, ("-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"))
    return (rest[j], rest[j + 1:]) if j < len(rest) else ("", [])

def _cmd_danger(c: dict) -> list:
    """単純コマンドの危険操作の理由（DANGER_OK=1 で人の承認）。"""
    toks = c["toks"]
    if not toks:
        return []
    head = os.path.basename(toks[0])
    r = []
    if _rm_rf_targets_of(toks):
        r.append("rm -rf requires DANGER_OK=1")
    if head == "git":
        sub, args = _git_sub(toks)
        if sub == "reset" and "--hard" in args:
            r.append("git reset --hard requires DANGER_OK=1")
        if sub == "clean" and _has_short(args, "f", "--force") and (_has_short(args, "d") or _has_short(args, "x")
                                                                    or _has_short(args, "X")):
            r.append("追跡されていないファイルの削除（git clean -f -d/-x）requires DANGER_OK=1")
    if c.get("docker_subs"):
        subs, args = c["docker_subs"], _docker_parts(toks)[1]
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
            if (sql is not None and _sql_is_destructive(sql)) or c["stdin"]:
                r.append("dbshell での破壊的 SQL・流し込み requires DANGER_OK=1")
    if head == "psql":
        sql = _sql_of(c)
        if sql is not None and _sql_is_destructive(sql):
            r.append("destructive SQL requires DANGER_OK=1")
        if _opt_value(toks[1:], ("-f", "--file")) is not None or c["stdin"]:
            r.append("ダンプ・SQL ファイルの流し込み（psql -f / <）requires DANGER_OK=1")
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
    code = _python_code(c)
    if code:
        r += [f"{why} requires DANGER_OK=1" for why in _code_reasons(code)[0]]
    return r

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
    if head == "celery" and "call" in toks:
        r.append("celery タスクの起動（celery call）")
    code = _python_code(c)
    if code:
        r += _code_reasons(code)[1]
    if head in _SECRET_READERS and any(_SECRET_PATH_RE.search(a) and not a.endswith(".example")
                                       for a in toks[1:] if not a.startswith("-")):
        r.append("秘密情報ファイルの読み出し")
    if head == "printenv" or (head == "env" and not [a for a in toks[1:] if not a.startswith("-")]):
        r.append("環境変数（秘密情報を含む）の表示")
    subs = c.get("docker_subs") or []
    if subs[:2] == ["compose", "config"] or subs[:1] == ["inspect"]:
        r.append("環境変数（秘密情報を含む）の表示（docker compose config / docker inspect）")
    return r

def _container_safe(c: dict) -> bool:
    """コンテナ内の単純コマンドが許可リストに入るなら True（plan_I174.md 0-5）。"""
    toks = c["toks"]
    if c["note"] or c["piped"] or c["herestr"] is not None or not toks:
        return False
    head = os.path.basename(toks[0])
    rest = toks[1:]
    dj = _django_sub(toks)
    if dj:
        sub, args = dj
        if sub in _SAFE_MANAGE:
            return True
        if sub == "makemigrations":
            return "--check" in args or "--dry-run" in args
        if sub == "migrate":
            return True                                  # 巻き戻しは _cmd_danger が先に止める
        if sub == "shell":
            code = _python_code(c)
            return bool(code) or code == ""              # 見えて危険が無い（危険・外部送信は先に判定済み）
        if sub == "dbshell":
            sql = _sql_of(c)
            return sql is not None and _sql_is_safe_read(sql)
        return False
    if c["heredoc"] is not None and head not in ("psql", "redis-cli") and not _PYTHON_RE.match(head):
        return False
    if head == "ruff":
        return rest[:1] == ["check"] or (rest[:1] == ["format"] and "--check" in rest)
    if head in ("pytest", "flake8", "bandit", "pip-audit", "mypy", "eslint", "tsc", "jest"):
        return True
    if _PYTHON_RE.match(head):
        k = 0
        while k < len(rest) and rest[k] in ("-W", "-X", "-u", "-B", "-E", "-I", "-O", "-OO", "-s", "-S", "-b", "-q"):
            k += 2 if rest[k] in ("-W", "-X") else 1        # -m より前のインタプリタのオプションだけを読み飛ばす
        if rest[k:k + 2] in (["-m", "pytest"], ["-m", "flake8"], ["-m", "mypy"]):
            return True
        if rest[:1] in (["--version"], ["-V"]):
            return True
        code = _python_code(c)
        return bool(code) or code == ""
    if head == "pip":
        return rest[:1] in (["freeze"], ["list"], ["show"], ["check"], ["--version"]) or rest[:2] == ["index", "versions"]
    if head == "npm":
        return rest[:1] in (["test"], ["audit"], ["ls"], ["outdated"], ["view"], ["--version"]) or \
            rest[:2] in (["run", "lint"], ["run", "typecheck"], ["run", "build"], ["run", "test"])
    if head == "npx":
        return rest[:1] in (["tsc"], ["eslint"], ["jest"])
    if head == "psql":
        sql = _sql_of(c)
        return sql is not None and _sql_is_safe_read(sql) and not c["stdin"]
    if head == "redis-cli":
        if "--scan" in rest:
            return True
        sub = rest[_skip_opts(rest, ("-h", "-p", "-n", "-a", "-u")):]
        return bool(sub) and sub[0].upper() in _SAFE_REDIS
    if head == "celery":
        return any(a in ("inspect", "status", "report") for a in rest)
    if head == "sed":
        return "-n" in rest and not _has_short(rest, "i", "--in-place")
    if head == "find":
        return "-exec" not in rest and "-execdir" not in rest and "-delete" not in rest
    if head == "curl":
        urls = [a for a in rest if "://" in a]
        return bool(urls) and all(re.match(r"https?://(localhost|127\.0\.0\.1|backend)(:\d+)?(/|$)", u) for u in urls)
    if head in ("node", "npm") and rest[:1] == ["--version"]:
        return True
    return head in _SAFE_READ_CMDS

def _describe(c: dict) -> str:
    s = " ".join(c["toks"])[:80]
    return f"{s}（{c['note']}）" if c["note"] else (s or "（コマンドなし）")

def _analyze(text: str) -> dict:
    """コマンド文字列の判定結果をまとめて返す（main から使う）。"""
    cmds = _parse(text)
    res = {"hard": False, "danger": [], "external": [], "container": []}
    for c in cmds:
        if _cmd_hard(c):
            res["hard"] = True
        res["danger"] += _cmd_danger(c)
        res["external"] += _cmd_external(c)
    for c in cmds:
        if c["ctr"] and not _cmd_danger(c) and not _cmd_external(c) and not _container_safe(c):
            res["container"].append(_describe(c))
    for k in ("danger", "external", "container"):
        res[k] = list(dict.fromkeys(res[k]))
    return res

def _danger_reasons(cmd: str, pcmd: str) -> list:
    """DANGER_OK=1 で人の承認に切り替わる危険操作の理由を集める（該当なしは []）。
    cmd は空白を正規化したコマンド（push 系の既存判定用）、pcmd は改行を保ったコマンド（読み解き用）。"""
    reasons = []
    dest = _push_protected_target(cmd)
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
    target = _git_revert_target_on_dirty(cmd)
    if target:
        reasons.append(f"git checkout/restore would discard uncommitted changes in '{target}'. "
                       f"Edit で戻すか、どうしても必要なら DANGER_OK=1 を前置してください。")
    reasons += _analyze(pcmd)["danger"]
    return list(dict.fromkeys(reasons))

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
    # それ以外の rm -rf は下の危険操作（DANGER_OK=1 で人の承認）で扱う。
    if an["hard"]:
        _block("rm -rf / is forbidden", raw)
    if re.search(r"\bmkfs(\.|\s)", cmd, re.I):
        _block("mkfs is forbidden", raw)
    if re.search(r"\bdd\b", cmd, re.I):
        _block("dd is forbidden", raw)
    if re.search(r"\bshred\b", cmd, re.I):
        _block("shred is forbidden", raw)

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
    if _push_is_dynamic(cmd):
        _ask("動的・不透明な宛先の push です。protected ブランチに解決し得るため確認してください。")

    sys.exit(0)

if __name__ == "__main__":
    main()
