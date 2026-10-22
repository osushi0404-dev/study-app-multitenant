#!/usr/bin/env bash
# I182（plan_I182.md 4-6・4-7）: 手順書に「GitHub から復旧できる範囲」・漏れたときの手順・見張りの扱い・レビュー観点が
# 書かれ、新しい節の中のパスが実在することを決定論検証する。
# 実行: bash scripts/claude/tests/test_i182_docs.sh
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
TMP="$(mktemp -d)"
trap 'rm -r "$TMP"' EXIT
DO=docs/runbooks/danger-ops.md; RR=docs/runbooks/review-rules.md; WT=docs/runbooks/worktree.md

# 判定本体: section <ファイル> <見出しの前方一致> <必須の語...> → 見出しから次の「## 」までに全部あれば exit 0
cat > "$TMP/sec.py" <<'PY'
import sys
path, head, *words = sys.argv[1:]
lines = open(path, encoding="utf-8").read().split("\n")
start = next((i for i, l in enumerate(lines) if l.startswith(head)), None)
if start is None:
    print(f"見出しが無い: {head}"); sys.exit(1)
end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
body = "\n".join(lines[start:end])
miss = [w for w in words if w not in body]
if miss:
    print(f"節に無い語: {miss}"); sys.exit(1)
PY
# 節の中のバッククォートのパス（`/` を含むもの）が実在するか（gitignore 済み〔.env 等〕・<…>・*・空白を含むものは除く）
cat > "$TMP/paths.py" <<'PY'
import os, re, subprocess, sys
path, *heads = sys.argv[1:]
lines = open(path, encoding="utf-8").read().split("\n")
bad = []
for head in heads:
    start = next((i for i, l in enumerate(lines) if l.startswith(head)), None)
    if start is None:
        print(f"見出しが無い: {head}"); sys.exit(1)
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    for p in re.findall(r"`([^`]+)`", "\n".join(lines[start:end])):
        # `/` を含むものだけをパスとして扱う（`ci.yml`・`manage.py` のようなファイル名だけの言及は対象外）
        if any(c in p for c in "<>* ") or "/" not in p:
            continue
        if p.startswith(("http", "-")) or ":" in p:
            continue
        if os.path.exists(p.rstrip("/")):
            continue
        if subprocess.run(["git", "check-ignore", "-q", p]).returncode == 0:
            continue
        bad.append(p)
if bad:
    print(f"実在しないパス: {bad}"); sys.exit(1)
PY
sec() { python3 "$TMP/sec.py" "$@" >/dev/null 2>&1; echo $?; }
paths() { python3 "$TMP/paths.py" "$@" >/dev/null 2>&1; echo $?; }

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }

H1="## GitHub から復旧できる範囲（I182）"; H2="## 秘密情報を push してしまったとき（I182）"
H3="## 見張り（pretooluse_guard.py）の扱い"; H4="## GitHub から復旧できない変更のレビュー観点（I182）"
ck "DOC1 danger-ops に復旧できる範囲の節" 0 "$(sec "$DO" "$H1" 秘密情報 .github/workflows/ リモートブランチの削除 'イシュー・PR への書き込み')"
ck "DOC2 danger-ops に漏れたときの手順の節" 0 "$(sec "$DO" "$H2" 無効化 'push protection')"
ck "DOC3 見張りの扱いに --no-verify・20 秒・512MB" 0 "$(sec "$DO" "$H3" --no-verify '20 秒' 512MB)"
ck "DOC4 review-rules にレビュー観点の節" 0 "$(sec "$RR" "$H4" pull_request_target .secrets.baseline)"
if grep -q "GitHub から復旧できる範囲" "$WT"; then d5=0; else d5=1; fi
ck "DOC5 worktree.md が復旧できる範囲を参照" 0 "$d5"
ck "DOC6 新しい節の中のパスが実在する（danger-ops）" 0 "$(paths "$DO" "$H1" "$H2" "$H3")"
ck "DOC6 新しい節の中のパスが実在する（review-rules）" 0 "$(paths "$RR" "$H4")"

# 偽合格の防止
grep -v "^$H1" "$DO" > "$TMP/fg1.md"
ck "FG-DOC1 見出しを消すと DOC1 が不合格" 1 "$(sec "$TMP/fg1.md" "$H1" 秘密情報)"
python3 - "$DO" "$TMP/fg2.md" "$H2" <<'PY'
import sys
s = open(sys.argv[1], encoding="utf-8").read()
s = s.replace(sys.argv[3] + "\n", sys.argv[3] + "\n\n`docs/runbooks/no_such_file.md`\n", 1)
open(sys.argv[2], "w", encoding="utf-8").write(s)
PY
ck "FG-DOC2 存在しないパスを足すと DOC6 が不合格" 1 "$(paths "$TMP/fg2.md" "$H2")"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
