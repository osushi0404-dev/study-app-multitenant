#!/usr/bin/env bash
# I174: .claude/settings.json の permissions（allow / ask / deny）の中身を JSON として決定論検証する。
# 実行: bash scripts/claude/tests/test_settings_permissions.sh
#
# grep での存在確認では「ask から allow に移した」ような後退を検出できないため、
# どのリストに入っているかまで確かめる（敵対的レビュー第 1 周 #14）。
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
SETTINGS="$REPO_ROOT/.claude/settings.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 判定本体: 引数の settings.json が I174 の期待どおりなら exit 0、違えば理由を出して exit 1
cat > "$TMP/check.py" <<'PY'
import json, sys
full = json.load(open(sys.argv[1], encoding="utf-8"))
p = full["permissions"]
allow, ask, deny = p.get("allow", []), p.get("ask", []), p.get("deny", [])
errs = []
# guard が唯一の決定論ゲートなので、Bash の PreToolUse フック登録と権限モードも確かめる（第 2 周 #18）
pre = (full.get("hooks") or {}).get("PreToolUse") or []
if not any(h.get("matcher") == "Bash" and any("pretooluse_guard.py" in x.get("command", "") for x in h.get("hooks", []))
           for h in pre):
    errs.append("Bash の PreToolUse フック（pretooluse_guard.py）が登録されていない")
if p.get("defaultMode") in ("bypassPermissions", "dontAsk") or full.get("defaultMode") in ("bypassPermissions", "dontAsk"):
    errs.append("権限モードが確認なしの設定になっている")
if full.get("disableAllHooks"):
    errs.append("disableAllHooks でフックが止まっている")
for h in pre:
    if h.get("matcher") == "Bash":
        for x in h.get("hooks", []):
            if x.get("type") != "command" or not x.get("command", "").startswith("python3 ") \
                    or "pretooluse_guard.py" not in x.get("command", ""):
                errs.append(f"Bash のフックが guard を正しく呼んでいない: {x}")
for wide in ("Bash(*)", "Bash", "Bash(docker *)", "Bash(docker compose *)", "Bash(docker-compose *)"):
    if wide in allow:
        errs.append(f"allow に広すぎる {wide} がある")
keep_ask = ["Bash(git rebase *)", "Bash(psql *)", "Bash(rm *)", "Bash(mv *)", "Bash(cp *)",
            "Bash(chmod *)", "Bash(chown *)"]
removed = ["Bash(git merge *)", "Bash(git reset *)", "Bash(git cherry-pick *)",
           "Bash(docker compose exec *)", "Bash(docker compose run *)", "Bash(docker compose down *)",
           "Bash(docker-compose exec *)", "Bash(docker-compose run *)", "Bash(docker-compose down *)"]
if sorted(ask) != sorted(keep_ask):
    errs.append(f"ask が期待と違う: {ask}")
for r in keep_ask:
    if r in allow:
        errs.append(f"ask に残すべき {r} が allow にある")
for r in removed:
    if r in ask or r in allow:
        errs.append(f"外したはずの {r} が残っている")
if any(e.startswith(("Bash(docker compose exec", "Bash(docker-compose exec")) for e in allow + ask):
    errs.append("docker compose exec 系の行が残っている")
if any(e.startswith("Write(") for e in allow + ask + deny):
    errs.append("効かない Write(...) ルールが残っている")
for r in ["Read(**/.env)", "Read(**/.env.e2e)", "Edit(**/.env)", "Edit(**/.env.e2e)",
          "Read(**/.env.local)", "Edit(**/.env.local)", "Read(**/.env.*.local)", "Edit(**/.env.*.local)",
          "Read(**/secrets/**)", "Edit(**/secrets/**)", "Read(**/*.pem)", "Edit(**/*.pem)",
          "Read(**/*.key)", "Edit(**/*.key)"]:
    if r not in deny:
        errs.append(f"deny に {r} が無い")
if any(e.startswith(("Read(./.env", "Edit(./.env")) for e in deny):
    errs.append("deny に ./.env 固定の行が残っている（backend/.env に効かない）")
if any(e in ("Edit(**/.env.*)",) for e in deny):
    errs.append("deny の Edit(**/.env.*) が .env.example 等の編集まで拒否する")
for e in errs:
    print(e)
sys.exit(1 if errs else 0)
PY

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
run_check() { python3 "$TMP/check.py" "$1" >/dev/null 2>&1; echo $?; }

ck "S1 実体の settings.json が期待どおり" 0 "$(run_check "$SETTINGS")"

# 偽合格の防止: 後退を注入した複製は不合格になる
python3 - "$SETTINGS" "$TMP" <<'PY'
import json, sys, copy
src, tmp = sys.argv[1], sys.argv[2]
base = json.load(open(src, encoding="utf-8"))
def write(name, mut):
    d = copy.deepcopy(base)
    mut(d["permissions"])
    json.dump(d, open(f"{tmp}/{name}.json", "w", encoding="utf-8"))
write("rm_to_allow", lambda p: (p["ask"].remove("Bash(rm *)"), p["allow"].append("Bash(rm *)")))
write("exec_back", lambda p: p["ask"].append("Bash(docker compose exec *)"))
write("write_back", lambda p: p["deny"].append("Write(./.env)"))
write("env_root_only", lambda p: (p["deny"].remove("Read(**/.env)"), p["deny"].append("Read(./.env)")))
write("allow_bash_star", lambda p: p["allow"].append("Bash(*)"))
write("allow_docker_star", lambda p: p["allow"].append("Bash(docker *)"))
write("bypass_mode", lambda p: p.__setitem__("defaultMode", "bypassPermissions"))
d = copy.deepcopy(base)
d["hooks"]["PreToolUse"] = [h for h in d["hooks"]["PreToolUse"] if h.get("matcher") != "Bash"]
json.dump(d, open(f"{tmp}/drop_bash_hook.json", "w", encoding="utf-8"))
d = copy.deepcopy(base)
d.pop("hooks")
json.dump(d, open(f"{tmp}/drop_all_hooks.json", "w", encoding="utf-8"))
d = copy.deepcopy(base)
d["disableAllHooks"] = True
json.dump(d, open(f"{tmp}/disable_all_hooks.json", "w", encoding="utf-8"))
d = copy.deepcopy(base)
for h in d["hooks"]["PreToolUse"]:
    if h.get("matcher") == "Bash":
        h["hooks"].append({"type": "command", "command": "true # pretooluse_guard.py"})
json.dump(d, open(f"{tmp}/neutered_hook.json", "w", encoding="utf-8"))
PY
ck "S2 rm を ask から allow へ移すと不合格"   1 "$(run_check "$TMP/rm_to_allow.json")"
ck "S3 exec の ask を戻すと不合格"            1 "$(run_check "$TMP/exec_back.json")"
ck "S4 Write(...) を戻すと不合格"             1 "$(run_check "$TMP/write_back.json")"
ck "S5 .env の deny をルート固定に戻すと不合格" 1 "$(run_check "$TMP/env_root_only.json")"
ck "S6 allow に Bash(*) を足すと不合格"      1 "$(run_check "$TMP/allow_bash_star.json")"
ck "S7 allow に Bash(docker *) を足すと不合格" 1 "$(run_check "$TMP/allow_docker_star.json")"
ck "S8 bypassPermissions にすると不合格"     1 "$(run_check "$TMP/bypass_mode.json")"
ck "S9 Bash のフック登録を消すと不合格"      1 "$(run_check "$TMP/drop_bash_hook.json")"
ck "S10 hooks を丸ごと消すと不合格"          1 "$(run_check "$TMP/drop_all_hooks.json")"
ck "S11 disableAllHooks を足すと不合格"      1 "$(run_check "$TMP/disable_all_hooks.json")"
ck "S12 guard を呼ばないフックを足すと不合格" 1 "$(run_check "$TMP/neutered_hook.json")"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
