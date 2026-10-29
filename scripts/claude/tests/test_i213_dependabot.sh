#!/usr/bin/env bash
# I213: 壊れても気づきにくく、壊れると被害が大きい決まりだけを確かめる（設定の中身の写しはしない。書き間違いは pre-commit の check-dependabot）。
#   D2 dependabot.yml に target-branch を書かない（書くとセキュリティの修正の PR に設定が効かない）
#   W1 action は 40 桁の SHA＋版のコメントで固定 / W2 pull_request で動くワークフローに secrets が無い（Dependabot の PR に secrets は渡らない）
#   W3 E2E のパスワードは ::add-mask:: の後で $GITHUB_ENV に書く / I1 土台イメージは指紋（@sha256:）で固定
#   V1 名前の無い保存領域は frontend の /app/node_modules だけ（標準の起動コマンドの --renew-anon-volumes が消すのはこれだけ）
# 項目は docs/tests/open/I213_auto_test.md の TC-01。各項目に写しで失敗注入（FG）を付ける。
# 実行: bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i213_dependabot.sh
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)" || exit 1
cd "$REPO_ROOT" || exit 1

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=[%s] got=[%s]\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }

FILES=(.github/dependabot.yml .github/workflows/ci.yml .github/workflows/e2e.yml .github/workflows/dependency-audit.yml
       backend/Dockerfile frontend/Dockerfile frontend/Dockerfile.dev docker-compose.yml)

# $1=項目 $2=見る場所（リポジトリのルートか写し）。食い違いを出して 1、無ければ 0
chk() {
  python3 -I - "$1" "$2" <<'PY'
import glob, os, re, sys, yaml
item, root = sys.argv[1], sys.argv[2]
def P(p): return os.path.join(root, p)
def text(p): return open(P(p), encoding="utf-8").read()
def load(p): return yaml.safe_load(text(p))
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")
errs = []
if item == "D2":
    for u in load(".github/dependabot.yml").get("updates") or []:
        if "target-branch" in u:
            errs.append(f"{u.get('package-ecosystem')} {u.get('directory')}: target-branch を書かない")
elif item == "W1":
    files = sorted(glob.glob(P(".github/workflows/*.yml")))
    if not files:
        errs.append("ワークフローがありません")
    USES = re.compile(r"\s*(?:-\s+)?uses:\s")
    OK = re.compile(r"\s*(?:-\s+)?uses:\s+[\w.-]+/[\w./-]+@[0-9a-f]{40}\s+#\s+v\d+(?:\.\d+)*(?:\s.*)?")
    for f in files:
        for n, l in enumerate(open(f, encoding="utf-8").read().split("\n"), 1):
            if USES.match(l) and not OK.fullmatch(l):
                errs.append(f"{os.path.basename(f)}:{n}: SHA と版のコメントで固定していない: {l.strip()}")
elif item == "W2":
    for f in sorted(glob.glob(P(".github/workflows/*.yml"))):
        t = open(f, encoding="utf-8").read()
        d = yaml.safe_load(t)
        on = d.get("on", d.get(True))   # PyYAML は on: を True として読む
        trig = set(on) if isinstance(on, (dict, list)) else {on}
        if trig & {"pull_request", "pull_request_target"} and "secrets." in t:
            errs.append(f"{os.path.basename(f)}: pull_request で動くワークフローで secrets を使っている")
elif item == "W3":
    steps = load(".github/workflows/e2e.yml")["jobs"]["e2e"]["steps"]
    gen = [i for i, s in enumerate(steps) if "openssl rand -hex" in (s.get("run") or "")]
    init = [i for i, s in enumerate(steps) if s.get("name") == "Initialize E2E database"]
    if len(gen) != 1 or not init or gen[0] > init[0]:
        errs.append(f"パスワードを作る step がちょうど 1 つで、DB の初期化より前（今 {gen}・{init}）")
    else:
        ls = steps[gen[0]]["run"].split("\n")
        mask = [i for i, l in enumerate(ls) if "::add-mask::" in l]
        env = [i for i, l in enumerate(ls) if '>> "$GITHUB_ENV"' in l]
        if not mask or not env or mask[0] > env[0]:
            errs.append("::add-mask:: を $GITHUB_ENV への書き込みより前に置く")
elif item == "I1":
    FROM = re.compile(r"\s*FROM\s+(?:--\S+\s+)*(\S+)(?:\s+as\s+(\S+))?", re.I)
    for df in ("backend/Dockerfile", "frontend/Dockerfile", "frontend/Dockerfile.dev"):
        stages = set()
        for l in text(df).split("\n"):
            m = FROM.match(l)
            if not m:
                continue
            if m.group(1) not in stages and not DIGEST.search(m.group(1)):
                errs.append(f"{df}: 指紋（@sha256:）で固定していない: {m.group(1)}")
            if m.group(2):
                stages.add(m.group(2))
    for name, svc in (load("docker-compose.yml").get("services") or {}).items():
        img = svc.get("image")
        if img and not DIGEST.search(img):
            errs.append(f"docker-compose.yml の {name}: 指紋（@sha256:）で固定していない: {img}")
elif item == "V1":
    anon = []
    for name, svc in (load("docker-compose.yml").get("services") or {}).items():
        for v in svc.get("volumes") or []:
            if isinstance(v, str) and ":" not in v:
                anon.append((name, v))
            elif isinstance(v, dict) and v.get("type", "volume") == "volume" and not v.get("source"):
                anon.append((name, v.get("target")))
    if anon != [("frontend", "/app/node_modules")]:
        errs.append(f"名前の無い保存領域は frontend の /app/node_modules だけ（今 {anon}）")
else:
    errs.append(f"知らない項目: {item}")
for e in errs:
    print(e)
sys.exit(1 if errs else 0)
PY
}

# 写しを作る（$1=名前）。FILES を写したフォルダを返す
mkroot() { local r="$TMP/$1" f; for f in "${FILES[@]}"; do mkdir -p "$r/$(dirname "$f")"; cp "$f" "$r/$f"; done; echo "$r"; }
# 写しで 1 項目を見る（$1=FG の名前 $2=項目 $3=写し）
fg() { chk "$2" "$3" >/dev/null; ck "FG-$1 は $2 で不合格" 1 "$?"; }

# ---------- 実物 ----------
for item in D2 W1 W2 W3 I1 V1; do
  OUT="$(chk "$item" "$REPO_ROOT")"; rc=$?
  ck "$item 実物" 0 "$rc"
  [ "$rc" -eq 0 ] || printf '%s\n' "$OUT"
done

# ---------- 写しを壊す ----------
R="$(mkroot d2)"; sed -i '0,/^\(  *\)schedule:/s//\1target-branch: "develop"\n\1schedule:/' "$R/.github/dependabot.yml"; fg D2 D2 "$R"
R="$(mkroot w1a)"; sed -i 's#actions/checkout@[0-9a-f]\{40\}#actions/checkout@v4#' "$R/.github/workflows/ci.yml"; fg W1a W1 "$R"
R="$(mkroot w1b)"; sed -i 's#astral-sh/setup-uv@[0-9a-f]\{40\}#astral-sh/setup-uv@v10.3.3#' "$R/.github/workflows/ci.yml"; fg W1b W1 "$R"
R="$(mkroot w1c)"; sed -i 's#\(actions/setup-node@[0-9a-f]\{40\}\) *\# v[0-9.]*#\1#' "$R/.github/workflows/e2e.yml"; fg W1c W1 "$R"
# shellcheck disable=SC2016  # 写しに書く文字列そのもの（${{ }} を展開しない）
R="$(mkroot w2)"; sed -i 's#BASE_URL: http://localhost:3000#BASE_URL: http://localhost:3000\n          E2E_TEST_PASSWORD: ${{ secrets.E2E_TEST_PASSWORD }}#' "$R/.github/workflows/e2e.yml"; fg W2 W2 "$R"
R="$(mkroot w3a)"; sed -i '/::add-mask::/d' "$R/.github/workflows/e2e.yml"; fg W3a W3 "$R"
R="$(mkroot w3b)"; python3 -I - "$R/.github/workflows/e2e.yml" <<'PY'
import sys
f = sys.argv[1]
ls = open(f, encoding="utf-8").read().split("\n")
i = next(n for n, l in enumerate(ls) if "::add-mask::" in l)
j = next(n for n, l in enumerate(ls) if '>> "$GITHUB_ENV"' in l)
ls[i], ls[j] = ls[j], ls[i]
open(f, "w", encoding="utf-8").write("\n".join(ls))
PY
fg W3b W3 "$R"
R="$(mkroot i1a)"; sed -i 's/@sha256:[0-9a-f]*//' "$R/backend/Dockerfile"; fg I1a I1 "$R"
R="$(mkroot i1b)"; sed -i '0,/@sha256:[0-9a-f]*/s///' "$R/docker-compose.yml"; fg I1b I1 "$R"
R="$(mkroot v1)"; sed -i 's#^\(\( *\)- postgres_data:/var/lib/postgresql/data\)$#\1\n\2- /var/lib/postgresql/extra#' "$R/docker-compose.yml"; fg V1 V1 "$R"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
