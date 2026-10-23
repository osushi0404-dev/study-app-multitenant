#!/usr/bin/env bash
# I182（plan_I182.md 4-3・4-4・4-9）: GitHub から復旧できない操作の守りを決定論検証する。
#   N: git commit / push の --no-verify を見張りが止める   D: リモートブランチの削除を見張りが確認にする
#   E: 編集の確認は settings.json の ask（公式）に任せ、見張りは二重に判定しない
#   C: CI の秘密情報の検査（detect-secrets）が外されていない・ワークフローの GITHUB_TOKEN が読み取りだけ
# 実行: bash scripts/claude/tests/test_i182_secret_gates.sh
set -uo pipefail
unset CLAUDE_PROJECT_DIR
REPO_ROOT="$(git rev-parse --show-toplevel)"
GUARD="$REPO_ROOT/scripts/claude/hooks/pretooluse_guard.py"
cd "$REPO_ROOT" || exit 1
TMP="$(mktemp -d)"
trap 'rm -r "$TMP"' EXIT

bash_json() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$1"; }
edit_json() { python3 -c 'import json,sys; print(json.dumps({"tool_name":sys.argv[2],"tool_input":{"file_path":sys.argv[1],"old_string":"a","new_string":"b","content":"x"}}))' "$1" "${2:-Edit}"; }
run() { local out code; out=$(printf '%s' "$2" | python3 "$1" 2>/dev/null); code=$?
        if [ "$code" = "0" ] && printf '%s' "$out" | grep -q '"permissionDecision":[[:space:]]*"ask"'; then echo "ASK"; else echo "$code"; fi; }

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }

# --- N・D（「期待|名前|コマンド」） ---
CASES=(
  "2|N1|git commit --no-verify -m x"
  "2|N2|git commit -n -m x"
  "2|N3|git commit -anm x"
  "0|N4|git commit -m -n"
  "0|N5|git commit -mn"
  "2|N6|git push --no-verify origin feature/x"
  "ASK|N7|DANGER_OK=1 git commit --no-verify -m x"
  "0|N8|git commit -m \"fix -n option\""
  "0|N9|git push -n origin feature/x"
  "2|N10|git commit -a -n -m x"
  "2|N11|git commit -S -n -m x"
  "0|N12|git commit -uno -m x"
  "0|N13|git commit -Skeyid -m x"
  "ASK|D1|git push origin --delete feature/x"
  "ASK|D2|git push -d origin feature/x"
  "ASK|D3|git push origin :feature/x"
  "ASK|D4|git push --prune origin feature/x"
  "2|D5|git push origin :develop"
  "0|D6|git push origin feature/x"
  "ASK|D7|bash -c \"git push origin --delete feature/x\""
)
for c in "${CASES[@]}"; do
  IFS='|' read -r want name cmd <<<"$c"
  ck "$name $cmd" "$want" "$(run "$GUARD" "$(bash_json "$cmd")")"
done

# 偽合格の防止（FG-N1・FG-D1）: 複製から新しい規則を外すと、規則に当たる TC がすべて 0（素通し）になる
python3 - "$GUARD" "$TMP/norule.py" <<'PY'
import sys
s = open(sys.argv[1], encoding="utf-8").read()
for a, b in (('if sub == "commit" and _commit_no_verify(args):', 'if False:'),
             ('if "--no-verify" in args:', 'if False:'),
             ('if _push_deletes(args):', 'if False:')):
    if s.count(a) != 1:
        sys.exit(3)
    s = s.replace(a, b)
open(sys.argv[2], "w", encoding="utf-8").write(s)
PY
if [ -f "$TMP/norule.py" ]; then
  for c in "${CASES[@]}"; do
    IFS='|' read -r want name cmd <<<"$c"
    case "$name" in N1|N2|N3|N6|N10|N11) fam="FG-N1" ;; D1|D2|D3|D4|D7) fam="FG-D1" ;; *) continue ;; esac
    ck "$fam $name は規則を外すと素通しになる" 0 "$(run "$TMP/norule.py" "$(bash_json "$cmd")")"
  done
else
  ck "FG-N1/FG-D1 規則を外す置き換えができる" yes no
fi

# --- E7: 見張りは Edit/Write の編集の確認をしない（settings.json の ask に任せる・別ワークツリーの停止だけ） ---
for p in .github/workflows/ci.yml .pre-commit-config.yaml backend/requirements.txt docs/x.md; do
  ck "E7 見張りは Edit $p を素通し（確認は settings.json の ask）" 0 "$(run "$GUARD" "$(edit_json "$p")")"
done
ck "E7 見張りは Write .github/workflows/new.yml を素通し" 0 "$(run "$GUARD" "$(edit_json "$REPO_ROOT/.github/workflows/new.yml" Write)")"

# --- C: CI の検査とワークフローの権限（PyYAML で読む。YAML 1.1 の `on` は True に読まれる） ---
cat > "$TMP/c.py" <<'PY'
import sys, yaml
kind, path = sys.argv[1], sys.argv[2]
d = yaml.safe_load(open(path, encoding="utf-8"))
def fail(msg):
    print(msg); sys.exit(1)
# C1〜C3 は「今の形以外は不合格」の許可リストで見る（continue-on-error・if・with・stages・files・paths 等、
# 検査を事実上外す書き方を 1 つずつ数え上げない。I182 敵対的レビュー）。形を変えるときはここも直す
if kind == "C1":   # Backend Lint & Security の pre-commit で detect-secrets を飛ばしていない
    job = next((j for j in d.get("jobs", {}).values() if j.get("name") == "Backend Lint & Security"), None)
    if not job:
        fail("Backend Lint & Security のジョブが無い")
    if set(job) - {"name", "runs-on", "steps"}:
        fail(f"ジョブに許可していないキーがある: {sorted(set(job) - {'name', 'runs-on', 'steps'})}")
    st = next((s for s in job.get("steps", []) if str(s.get("uses", "")).startswith("pre-commit/action@")), None)
    if not st:
        fail("pre-commit/action のステップが無い")
    if set(st) - {"name", "uses", "env"} or set(st.get("env") or {}) - {"SKIP"}:
        fail(f"pre-commit/action のステップに許可していないキーがある: {sorted(st)}")
    skip = [x.strip() for x in str((st.get("env") or {}).get("SKIP", "")).split(",")]
    if "detect-secrets" in skip:
        fail("SKIP に detect-secrets がある")
elif kind == "C2":  # pre-commit に detect-secrets が baseline 付きで、全ファイル・既定の段階で走る
    if set(d) - {"repos"}:
        fail(f"最上位に許可していないキーがある: {sorted(set(d) - {'repos'})}")
    hooks = [h for r in d.get("repos", []) for h in r.get("hooks", [])]
    h = next((h for h in hooks if h.get("id") == "detect-secrets"), None)
    want = {"id": "detect-secrets", "args": ["--baseline", ".secrets.baseline"], "exclude": r"package-lock\.json"}
    if h != want:
        fail(f"detect-secrets のフックが想定の形でない: {h}")
elif kind == "C3":  # develop 宛ての PR で常に動く（paths 等で絞らない）
    on = d.get("on", d.get(True)) or {}
    pr = on.get("pull_request") or {}
    if set(pr) - {"branches"} or "develop" not in (pr.get("branches") or []):
        fail(f"pull_request が develop 宛てで絞りなしになっていない: {pr}")
elif kind == "C4":  # GITHUB_TOKEN が読み取りだけ
    if d.get("permissions") != {"contents": "read"}:
        fail(f"最上位の permissions が contents: read だけでない: {d.get('permissions')}")
    for name, j in d.get("jobs", {}).items():
        p = j.get("permissions")
        if p is not None and (not isinstance(p, dict) or any(v not in ("read", "none") for v in p.values())):
            fail(f"ジョブ {name} が permissions を広げている: {p}")
PY
cy() { python3 "$TMP/c.py" "$1" "$2" >/dev/null 2>&1; echo $?; }
CI=.github/workflows/ci.yml; E2E=.github/workflows/e2e.yml; PC=.pre-commit-config.yaml
ck "C1 ci.yml の pre-commit で detect-secrets が走る" 0 "$(cy C1 "$CI")"
ck "C2 pre-commit に detect-secrets（baseline 付き）がある" 0 "$(cy C2 "$PC")"
ck "C3 ci.yml は develop 宛ての PR で動く" 0 "$(cy C3 "$CI")"
ck "C4 ci.yml の GITHUB_TOKEN は読み取りだけ" 0 "$(cy C4 "$CI")"
ck "C4 e2e.yml の GITHUB_TOKEN は読み取りだけ" 0 "$(cy C4 "$E2E")"
# 偽合格の防止（FG-C1〜FG-C4）: 後退を注入した複製は不合格になる
python3 - "$CI" "$E2E" "$PC" "$TMP" <<'PY'
import sys, yaml, copy
ci, e2e, pc, tmp = sys.argv[1:]
load = lambda p: yaml.safe_load(open(p, encoding="utf-8"))
dump = lambda d, n: yaml.safe_dump(d, open(f"{tmp}/{n}", "w", encoding="utf-8"), allow_unicode=True)
def lint_job(d):
    return next(j for j in d["jobs"].values() if j.get("name") == "Backend Lint & Security")
d = load(ci)
for s in lint_job(d)["steps"]:
    if str(s.get("uses", "")).startswith("pre-commit/action@"):
        s.setdefault("env", {})["SKIP"] = "eslint,detect-secrets"
dump(d, "fg_c1.yml")
d = load(pc)
d["repos"] = [r for r in d["repos"] if not any(h.get("id") == "detect-secrets" for h in r.get("hooks", []))]
dump(d, "fg_c2.yml")
d = load(ci)
j = lint_job(d)
j["steps"] = [s for s in j["steps"] if not str(s.get("uses", "")).startswith("pre-commit/action@")]
dump(d, "fg_c3.yml")
d = load(e2e)
d.pop("permissions", None)
dump(d, "fg_c4a.yml")
d = load(ci)
next(iter(d["jobs"].values()))["permissions"] = {"contents": "write"}
dump(d, "fg_c4b.yml")
# 検査を事実上外す書き方（I182 敵対的レビュー）: ステップ・ジョブ・フック・トリガーに 1 キー足す
def pc_step(d):
    return next(s for s in lint_job(d)["steps"] if str(s.get("uses", "")).startswith("pre-commit/action@"))
for n, f in (("fg_c1_coe", lambda d: pc_step(d).update({"continue-on-error": True})),
             ("fg_c1_stepif", lambda d: pc_step(d).update({"if": False})),
             ("fg_c1_with", lambda d: pc_step(d).update({"with": {"extra_args": "ruff --all-files"}})),
             ("fg_c1_jobif", lambda d: lint_job(d).update({"if": "github.event_name == 'push'"})),
             ("fg_c3_paths", lambda d: (d.get("on") or d[True])["pull_request"].update({"paths": ["backend/**"]}))):
    d = load(ci); f(d); dump(d, f"{n}.yml")
def ds_hook(d):
    return next(h for r in d["repos"] for h in r.get("hooks", []) if h.get("id") == "detect-secrets")
for n, f in (("fg_c2_stages", lambda d: ds_hook(d).update({"stages": ["manual"]})),
             ("fg_c2_files", lambda d: ds_hook(d).update({"files": "^backend/"})),
             ("fg_c2_top", lambda d: d.update({"exclude": ".*"}))):
    d = load(pc); f(d); dump(d, f"{n}.yml")
PY
ck "FG-C1 SKIP に detect-secrets を足すと不合格" 1 "$(cy C1 "$TMP/fg_c1.yml")"
ck "FG-C2 pre-commit から detect-secrets を消すと不合格" 1 "$(cy C2 "$TMP/fg_c2.yml")"
ck "FG-C3 pre-commit/action のステップを消すと不合格" 1 "$(cy C1 "$TMP/fg_c3.yml")"
ck "FG-C4 e2e.yml の permissions を消すと不合格" 1 "$(cy C4 "$TMP/fg_c4a.yml")"
ck "FG-C4 ci.yml のジョブに contents: write を足すと不合格" 1 "$(cy C4 "$TMP/fg_c4b.yml")"
ck "FG-C5 pre-commit/action に continue-on-error を足すと不合格" 1 "$(cy C1 "$TMP/fg_c1_coe.yml")"
ck "FG-C5 pre-commit/action に if を足すと不合格" 1 "$(cy C1 "$TMP/fg_c1_stepif.yml")"
ck "FG-C5 pre-commit/action に with（extra_args）を足すと不合格" 1 "$(cy C1 "$TMP/fg_c1_with.yml")"
ck "FG-C5 Backend Lint & Security のジョブに if を足すと不合格" 1 "$(cy C1 "$TMP/fg_c1_jobif.yml")"
ck "FG-C5 detect-secrets に stages: [manual] を足すと不合格" 1 "$(cy C2 "$TMP/fg_c2_stages.yml")"
ck "FG-C5 detect-secrets に files を足すと不合格" 1 "$(cy C2 "$TMP/fg_c2_files.yml")"
ck "FG-C5 pre-commit の最上位に exclude を足すと不合格" 1 "$(cy C2 "$TMP/fg_c2_top.yml")"
ck "FG-C5 pull_request に paths を足すと不合格" 1 "$(cy C3 "$TMP/fg_c3_paths.yml")"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
