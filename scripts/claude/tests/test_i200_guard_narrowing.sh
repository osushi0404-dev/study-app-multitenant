#!/usr/bin/env bash
# shellcheck disable=SC2016  # ワークフローの ${{ … }} を展開しない文字としてそのまま渡すため（意図的）
# I200: 見張り（pretooluse_guard.py）の確認を「本当に危ない操作」だけに絞ったことを決定論で確かめる。
# 実行: bash scripts/claude/tests/test_i200_guard_narrowing.sh
#
# 見張りに JSON を渡して判定だけを見る（コマンドは実行しない）。期待値: 2＝停止・ASK＝確認・0＝通す。
# ケースは docs/tests/open/I200_auto_test.md の TC-01〜TC-05 と 1 対 1。0=全 PASS / 1=FAIL あり。
set -uo pipefail
unset CLAUDE_PROJECT_DIR
REPO_ROOT="$(git rev-parse --show-toplevel)"
GUARD="${GUARD:-$REPO_ROOT/scripts/claude/hooks/pretooluse_guard.py}"
cd "$REPO_ROOT" || exit 1
TMP="$(mktemp -d)"
trap 'rm -r "$TMP"' EXIT

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
judge() {  # judge <見張り> <JSON> [作業フォルダ]
  local out code; out=$(cd "${3:-$REPO_ROOT}" && printf '%s' "$2" | python3 "$1" 2>/dev/null); code=$?
  if [ "$code" = "0" ] && printf '%s' "$out" | grep -q '"permissionDecision":[[:space:]]*"ask"'; then echo ASK; else echo "$code"; fi; }
bash_json() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$1"; }
b() { judge "${2:-$GUARD}" "$(bash_json "$1")"; }
# 見張りの複製の関数の定義行の直後に 1 行差し込む（test_i182_guard_failsafe.sh の inject と同じ方法）
inject() {  # inject <出力> <定義行> <差し込む行>
  python3 - "$GUARD" "$1" "$2" "$3" <<'PY'
import sys
src, dst, head, line = sys.argv[1:]
s = open(src, encoding="utf-8").read()
if s.count(head + "\n") != 1:
    sys.exit(3)
open(dst, "w", encoding="utf-8").write(s.replace(head + "\n", head + "\n    " + line + "\n"))
PY
}

# ---- TC-01 普通の操作は通る＋ FG ----
printf 'print("ok")\n' > "$TMP/ok.py"
printf "import shutil; shutil.rmtree('/app/x')\n" > "$TMP/bad.py"
ck 01a 0   "$(b "docker compose cp $TMP/ok.py backend:/tmp/x.py")"
ck 01b 0   "$(b 'docker compose exec -T backend python /tmp/x.py')"
ck 01c 0   "$(b "docker compose exec -T backend python manage.py shell -c \"exec(open('/tmp/x.py').read())\"")"
ck 01d 0   "$(b 'docker compose exec -T -e PYTHONPATH=/tmp backend python -m pytest --co -q -p x accounts/tests.py')"
ck 01e 0   "$(b 'docker compose exec -T backend python manage.py seed_e2e')"
ck 01f 0   "$(b "docker compose exec -T db psql -U postgres -d learning_app -tAc 'select 1'")"
ck 01g 0   "$(b 'git rebase --help')"
ck 01h 0   "$(b 'docker compose run --rm backend python manage.py check')"
ck FG-01a ASK "$(b "docker compose cp $TMP/bad.py backend:/tmp/x.py")"
ck FG-01b 2   "$(b "docker compose exec -T backend python -c \"import os; os.remove('/app/x')\"")"
ck FG-01c 2   "$(b 'docker compose exec -T backend python manage.py shell -c "User.objects.all().delete()"')"
ck FG-01d ASK "$(b 'docker compose exec -T backend sh -c "echo x > /app/manage.py"')"
ck FG-01e ASK "$(b 'docker compose cp backend:/app/.env /tmp/x')"
ck FG-01f 2   "$(b "docker compose run --rm backend sh -c \"python -c \\\"import shutil; shutil.rmtree('/app/x')\\\"\"")"
ck FG-01g ASK "$(b "docker compose cp $TMP/ok.py backend:/app/manage.py")"
# 敵対的レビュー 1 周目・コードレビューの F3／F4／F6（リダイレクト以外の書き込み・/tmp/../・ダンプと環境変数の表示）
ck FG-01h ASK "$(b 'docker compose exec -T backend sed -i s/a/b/ /app/config/settings.py')"
ck FG-01i ASK "$(b 'docker compose exec -T backend tee /app/manage.py')"
ck FG-01j ASK "$(b 'docker compose exec -T backend cp /tmp/x /app/manage.py')"
ck FG-01k ASK "$(b 'docker compose exec -T backend mv /tmp/x /app/manage.py')"
ck FG-01l ASK "$(b 'docker compose exec -T backend sh -c "echo x > /tmp/../app/manage.py"')"
ck FG-01m ASK "$(b "docker compose cp $TMP/ok.py backend:/tmp/../app/manage.py")"
ck FG-01n ASK "$(b 'docker compose exec -T db pg_dump -U postgres learning_app')"
ck FG-01o ASK "$(b 'docker compose exec -T backend sh -c set')"
ck FG-01p ASK "$(b 'docker compose exec -T backend sh -c "export -p"')"
ck 01i 0   "$(b 'docker compose exec -T backend cp /app/manage.py /tmp/x')"

# ---- TC-02 (A)〜(C) の代表は今までどおり停止・確認 ----
ck 02a 2   "$(b 'git push --force origin feature/x')"
ck 02b 2   "$(b 'git push origin develop')"
ck 02c ASK "$(b 'git push origin --delete feature/x')"
ck 02d 2   "$(b 'git reset --hard')"
ck 02e 2   "$(b 'docker compose down -v')"
ck 02f 2   "$(b "docker compose exec -T db psql -U postgres -c 'DROP TABLE users'")"
ck 02g 2   "$(b "psql -U postgres -h localhost -c 'TRUNCATE users'")"
ck 02g2 2  "$(b "psql -U postgres -h localhost -c 'DELETE FROM users'")"
ck 02g3 2  "$(b "docker compose exec -T db psql -U postgres -c 'DELETE FROM users'")"
ck 02h 2   "$(b 'rm -rf backend/x')"
ck 02i ASK "$(b 'cat backend/.env')"
ck 02k ASK "$(b "docker compose exec -T backend python -c \"import requests; requests.post('http://x')\"")"
ck 02l ASK "$(b 'docker compose exec -T backend python manage.py shell -c "from django.core.mail import send_mail; send_mail(1,2,3,[4])"')"
ck 02m ASK "$(b 'DANGER_OK=1 docker compose down -v')"

# ---- TC-03 読みきれない書き方は危ない語のときだけ確認 ----
ck 03a 0   "$(b 'echo "abc')"
ck 03b ASK "$(b 'echo "rm -rf x')"
ck 03c ASK "$(b 'echo "curl https://x')"
ck 03h 0   "$(b 'echo "add odd')"
if inject "$TMP/g_analyze.py" "def _analyze(text: str) -> dict:" 'raise ValueError("i200")'; then
  ck 03d 0   "$(b 'echo ok' "$TMP/g_analyze.py")"
  ck 03e ASK "$(b 'git push origin feature/x' "$TMP/g_analyze.py")"
  ck 03i ASK "$(b 'docker compose down -v' "$TMP/g_analyze.py")"
  # コードレビューの F1: 読み解きが例外でも、別 worktree への書き込みの停止は外さない（語の判定より前で止める）
  # 一時のリポジトリに主とワークツリーを作り、主の中から別のワークツリーへの書き込みを渡す（CI にも別の worktree が無いため）
  WTR="$TMP/wtr"; mkdir -p "$WTR/main"; git -C "$WTR/main" init -q
  git -C "$WTR/main" -c user.name=t -c user.email=t@example.com commit -q --allow-empty -m base
  git -C "$WTR/main" worktree add -q "$WTR/other" -b other
  ck 03j 2 "$(judge "$TMP/g_analyze.py" "$(bash_json "cp a.txt $WTR/other/i200_probe_never_written.txt")" "$WTR/main")"
else ck "03d-e,i 差し込み" ok NOINJECT; fi
if inject "$TMP/g_main.py" "    data = _load()" 'raise RuntimeError("i200")'; then
  ck 03f 0   "$(b 'echo ok' "$TMP/g_main.py")"
  ck 03g ASK "$(b 'rm -rf x' "$TMP/g_main.py")"
else ck "03f-g 差し込み" ok NOINJECT; fi
# FG-03: 危ない語から rm を消した複製では 03b が通ってしまう（＝03b が語の一覧を確かめている）
python3 - "$GUARD" "$TMP/g_norm.py" <<'PY'
import sys
s = open(sys.argv[1], encoding="utf-8").read()
old = '    "rm", "rmdir",'
assert s.count(old) == 1
open(sys.argv[2], "w", encoding="utf-8").write(s.replace(old, '    "rmdir",'))
PY
ck FG-03 0 "$(b 'echo "rm -rf x' "$TMP/g_norm.py")"

# ---- TC-04 ワークフローの編集 ----
WR="$TMP/repo"; mkdir -p "$WR/.github/workflows"; git -C "$WR" init -q
WF="$WR/.github/workflows/x.yml"
cat > "$WF" <<'YML'
name: X
on:
  pull_request:
permissions:
  contents: read
jobs:
  a:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4.4.0
      - name: Old
        env:
          OLD: ${{ secrets.OLD }}
        run: echo old
YML
ej() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Edit","tool_input":{"file_path":sys.argv[1],"old_string":sys.argv[2],"new_string":sys.argv[3]}}))' "$@"; }
wj() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Write","tool_input":{"file_path":sys.argv[1],"content":sys.argv[2]}}))' "$@"; }
mj() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"MultiEdit","tool_input":{"file_path":sys.argv[1],"edits":[{"old_string":sys.argv[2],"new_string":sys.argv[3]},{"old_string":sys.argv[4],"new_string":sys.argv[5]}]}}))' "$@"; }
CO='uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4.4.0'
NEWCO='uses: actions/checkout@0123456789abcdef0123456789abcdef01234567 # v7.0.1'
ADD='        run: echo old'
SEC="$ADD
      - env:
          X: \${{ secrets.X }}"
ck 04a 0   "$(judge "$GUARD" "$(ej "$WF" "$CO" "$NEWCO")")"
ck 04b 0   "$(judge "$GUARD" "$(ej "$WF" "$ADD" "$ADD
      - run: echo ok")")"
ck 04c ASK "$(judge "$GUARD" "$(ej "$WF" "$ADD" "$SEC")")"
ck 04d ASK "$(judge "$GUARD" "$(ej "$WF" 'contents: read' 'contents: write')")"
ck 04e ASK "$(judge "$GUARD" "$(ej "$WF" '  pull_request:' '  pull_request:
  pull_request_target:')")"
ck 04f ASK "$(judge "$GUARD" "$(ej "$WF" "$ADD" "$ADD
      - run: echo \"\${{ github.event.pull_request.title }}\"")")"
ck 04g ASK "$(judge "$GUARD" "$(ej "$WF" "$ADD" "$ADD
      - run: curl https://example.com")")"
ck 04h ASK "$(judge "$GUARD" "$(wj "$WR/.github/workflows/new.yml" 'on: push
jobs:
  a:
    steps:
      - env:
          X: ${{ secrets.X }}')")"
ck 04i 0   "$(judge "$GUARD" "$(wj "$WR/.github/workflows/new.yml" 'on: workflow_dispatch
jobs:
  a:
    runs-on: ubuntu-latest
    steps:
      - run: echo ok')")"
ck 04j ASK "$(judge "$GUARD" "$(mj "$WF" "$CO" "$NEWCO" "$ADD" "$SEC")")"
ck 04k ASK "$(judge "$GUARD" "$(ej "$WF" 'no such text' '          X: ${{ secrets.X }}')")"
ck 04l 0   "$(judge "$GUARD" "$(ej "$WF" '      - name: Old' '      - name: Old step')")"
ck 04o ASK "$(judge "$GUARD" "$(ej "$WF" "$ADD" "$ADD
      - env:
          X: \${{ secrets['X'] }}")")"
ck 04p ASK "$(judge "$GUARD" "$(ej "$WF" "$ADD" "$ADD
      - run: echo '\${{ toJSON(secrets) }}'")")"
ck 04m ASK "$(judge "$GUARD" "$(ej "$WR/./.github/../.github/workflows/x.yml" "$ADD" "$SEC")")"
ck 04n ASK "$(judge "$GUARD" "$(ej '.github/workflows/x.yml' "$ADD" "$SEC")" "$WR")"
# /mnt/c の上は大文字・小文字を区別しないので、書き方を変えても同じワークフロー（simplify の再利用の指摘）
ck 04q ASK "$(judge "$GUARD" "$(ej "$WR/.GitHub/Workflows/x.YML" "$ADD" "$SEC")")"

# ---- TC-05 pre-commit の設定の編集 ----
PC="$WR/.pre-commit-config.yaml"
cat > "$PC" <<'YML'
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.9
    hooks:
      - id: bandit
YML
DS="  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
"
ck 05a 0   "$(judge "$GUARD" "$(ej "$PC" 'rev: 1.7.9' 'rev: 1.9.4')")"
ck 05b 0   "$(judge "$GUARD" "$(ej "$PC" '      - id: bandit' '      - id: bandit
  - repo: https://github.com/python-jsonschema/check-jsonschema
    rev: 0.38.2
    hooks:
      - id: check-github-workflows')")"
ck 05c ASK "$(judge "$GUARD" "$(ej "$PC" "$DS" '')")"
ck 05d ASK "$(judge "$GUARD" "$(ej "$PC" '      - id: bandit' '      - id: bandit
        exclude: ^backend/')")"
ck 05e ASK "$(judge "$GUARD" "$(ej "$PC" "'.secrets.baseline'" "'.other.baseline'")")"
ck 05f ASK "$(judge "$GUARD" "$(wj "$PC" 'repos:
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.9
    hooks:
      - id: bandit')")"
ck 05g ASK "$(judge "$GUARD" "$(ej "$PC" '      - id: detect-secrets' '      - id: detect-secrets
        files: ^docs/')")"
ck 05h ASK "$(judge "$GUARD" "$(ej "$PC" '      - id: bandit' '      - id: bandit
        types_or: [python]')")"

printf 'pass=%d fail=%d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
