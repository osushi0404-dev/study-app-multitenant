# 敵対的レビュー [I200]（別プロセス・2026-10-29 23:18）

- 見た範囲: origin/develop...2e5262026c2a5ed5dd9300e958d0ae62c50b4e07
- 所要時間: 998 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- 一覧: docs/plans/open/plan_I200.md の「## 必ず確かめる項目」（8 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V2 | 1 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V3 | 1 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V4 | 1 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V5 | 2 | 読んで可 | 未実施 | ― | 未検証（未実施） |
| V6 | 2 | 実験必須 | 未実施 | ― | 未検証（未実施） |
| V7 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V8 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 992 秒 | 0 | 0 | $0.1011 | ― | ― | ― |
| 2 | 報告あり | 921 秒 | 0 | 0 | $0.2779 | ― | ― | ― |
| 3 | 報告あり | 969 秒 | 0 | 0 | $0.0833 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 実行していない（締め切り）
~~~
bash -c '
G=scripts/claude/hooks/pretooluse_guard.py
T=$(mktemp -d /tmp/p1e1.XXXXXX)
cat > $T/run.py <<"PY"
import json,subprocess,sys
G=sys.argv[1]
def run(label,payload):
    p=subprocess.run(["python3",G],input=json.dumps(payload),capture_output=True,text=True,timeout=60)
    ask="ask" in p.stdout and "permissionDecision" in p.stdout
    print(label, "ASK" if (p.returncode==0 and ask) else p.returncode)
def B(label,cmd): run(label,{"tool_name":"Bash","tool_input":{"command":cmd}})
def W(label,path,content): run(label,{"tool_name":"Write","tool_input":{"file_path":path,"content":content}})
def E(label,path,old,new): run(label,{"tool_name":"Edit","tool_input":{"file_path":path,"old_string":old,"new_string":new}})
def M(label,path,old,new): run(label,{"tool_name":"MultiEdit","tool_input":{"file_path":path,"edits":[{"old_string":old,"new_string":new}]}})
# V1 代表
B("V1 force push","git push --force origin feature/x")
B("V1 push develop","git push origin develop")
B("V1 push delete","git push origin --delete feature/x")
B("V1 reset hard","git reset --hard")
B("V1 down -v","docker compose down -v")
B("V1 DROP TABLE container","docker compose exec -T db psql -U postgres -c \"DROP TABLE users\"")
B("V1 rm -rf container","docker compose exec -T backend rm -rf /app/x")
B("V1 cat .env","cat backend/.env")
B("V1 requests.post","docker compose exec -T backend python -c \"import requests; requests.post(chr(104)+chr(116)+chr(116)+chr(112)+chr(58)+chr(47)+chr(47)+chr(120))\"")
B("V1 send_mail","docker compose exec -T backend python manage.py shell -c \"from django.core.mail import send_mail; send_mail(1,2,3,[4])\"")
# V1/V2 抜け道の探索
B("X1 psql UPDATE no WHERE","docker compose exec -T db psql -U postgres -d learning_app -c \"UPDATE users SET password=NULL\"")
B("X2 psql UPDATE lower","docker compose exec -T db psql -U postgres -d learning_app -c \"update accounts_user set is_active=false\"")
B("X3 sed -i app","docker compose exec -T backend sed -i s/a/b/ /app/config/settings.py")
B("X4 tee app","docker compose exec -T backend tee /app/manage.py")
B("X5 cp app","docker compose exec -T backend cp /tmp/x /app/manage.py")
B("X6 mv app","docker compose exec -T backend mv /tmp/x /app/manage.py")
B("X7 redirect tmp-dotdot","docker compose exec -T backend sh -c \"echo x > /tmp/../app/manage.py\"")
B("X8 cp dotdot","docker compose cp ./nonexist backend:/tmp/../app/manage.py")
B("X9 pg_dump","docker compose exec -T db pg_dump -U postgres learning_app")
B("X10 set","docker compose exec -T backend sh -c set")
B("X11 python os.remove","docker compose exec -T backend python -c \"import os; os.remove(chr(47)+chr(97))\"")
B("X12 pathlib unlink variant","docker compose exec -T backend python -c \"import pathlib; pathlib.Path(chr(47)+chr(97)).write_text(chr(120))\"")
B("X13 manage.py migrate zero","docker compose exec -T backend python manage.py migrate accounts zero")
B("X14 manage.py sqlflush|dbshell","docker compose exec -T backend python manage.py sqlflush")
# V3
WF=".github/workflows/zz_i200_probe.yml"
W("V3 W version only",WF,"jobs:\n  a:\n    steps:\n      - uses: actions/checkout@v5\n")
W("V3 W secrets.",WF,"env:\n  X: ${{ secrets.FOO }}\n")
W("V3 W secrets[]",WF,"env:\n  X: ${{ secrets[\"FOO\"] }}\n")
W("V3 W write",WF,"permissions:\n  contents: write\n")
W("V3 W pull_request_target",WF,"on:\n  pull_request_target:\n")
W("V3 W github.event",WF,"run: echo ${{ github.event.pull_request.title }}\n")
E("V3 E secrets",WF,"a","${{ secrets.FOO }}")
M("V3 M secrets",WF,"a","${{ secrets.FOO }}")
E("V3 E version only",WF,"checkout@v4","checkout@v5")
W("V3x W GITHUB_TOKEN passthrough",WF,"env:\n  T: ${{ github.token }}\n")
W("V3x W abs path",__import__("os").path.abspath(WF),"env:\n  X: ${{ secrets.FOO }}\n")
W("V3x W ../ path","scripts/../.github/workflows/zz_i200_probe.yml","env:\n  X: ${{ secrets.FOO }}\n")
W("V3x W .yaml","./.github/workflows/zz_i200_probe.yaml","env:\n  X: ${{ secrets.FOO }}\n")
W("V3x W upper SECRETS","./.github/workflows/zz_i200_probe.yml","env:\n  X: ${{ SECRETS.FOO }}\n")
# V4
P=".pre-commit-config.yaml"
E("V4 E remove detect-secrets",P,"- id: detect-secrets","- id: other")
E("V4 E add exclude",P,"- id: detect-secrets","- id: detect-secrets\n        exclude: ^docs/")
E("V4 E add files",P,"- id: detect-secrets","- id: detect-secrets\n        files: ^docs/")
E("V4 E add args --exclude-files",P,"- id: detect-secrets","- id: detect-secrets\n        args: [--exclude-files, docs]")
E("V4 E rev only",P,"rev: v1","rev: v2")
M("V4 M remove detect-secrets",P,"- id: detect-secrets","- id: other")
W("V4 W without detect-secrets",P,"repos: []\n")
PY
python3 $T/run.py $G 2>&1
'
~~~

### 観点 2

#### P2-E1: 実行していない（締め切り）
~~~
cat > /tmp/p2e1.sh <<'EOF'
set -u
HOOK="$1"
export GIT_AUTHOR_NAME=a GIT_AUTHOR_EMAIL=a@a GIT_COMMITTER_NAME=a GIT_COMMITTER_EMAIL=a@a GIT_TERMINAL_PROMPT=0
T=$(mktemp -d); cd "$T"
git init -q --bare -b develop origin.git
git clone -q origin.git seed 2>/dev/null
( cd seed && git checkout -q -b develop && echo 1 > a && git add a && git commit -qm c1 && git push -q origin develop )
run() {
  name=$1; setup=$2; seedfile=$3
  rm -rf p w
  git clone -q origin.git p
  ( cd p && git checkout -q develop 2>/dev/null; git worktree add -q -b feat_$name ../w )
  ( cd seed && echo "$name" > "$seedfile" && git add "$seedfile" && git commit -qm "n-$name" && git push -q origin develop )
  ( cd p && eval "$setup" )
  before=$(cd p && git rev-parse --short HEAD)
  out=$(cd w && timeout 50 python3 "$HOOK" 2>&1 | grep '^primary')
  after=$(cd p && git rev-parse --short HEAD)
  echo "== $name: before=$before after=$after"
  echo "   out: $out"
  echo "   status: $(cd p && git status --porcelain | tr '\n' '|')"
}
run clean ":" n_clean.txt
run dirty "echo x >> a" n_dirty.txt
run otherbr "git checkout -q -b other" n_other.txt
run diverged "echo y > own.txt && git add own.txt && git commit -qm own" n_div.txt
run untracked_clash "echo MINE > clash.txt" clash.txt
echo "clash content: $(cat p/clash.txt)"
run untracked_other "echo MINE > keep.txt" n_keep.txt
echo "keep content: $(cat p/keep.txt)"
EOF
bash -c 'ulimit -v 2097152; timeout 120 bash /tmp/p2e1.sh "$PWD/scripts/claude/hooks/sessionstart_context.py"'
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

実験案を返す。

# 敵対的レビュー [I200] ── 観点: 1. ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| （暫定）Medium | V2 | コンテナ内の `sed -i`・`tee`・`cp` で `/app/`（手元の `backend/`）に書く操作が、危ない語を含まないと確認なしで通る疑い。既存のコードレビューの F3 と同種で、実験で裏取りする | pretooluse_guard.py:2385 付近 | 実験 P1-E1 の結果待ち |
| （暫定）Medium | V1 | コンテナ内の `psql` で WHERE なしの `UPDATE` が、語の一覧（`.update(` だけ）に当たらず通る疑い。(B) の大量更新にあたる | `_RISKY_WORDS` | 実験 P1-E1 の結果待ち |
| （暫定）Low | V2 | 読み解きが例外になる形での別 worktree への Bash 書き込みの素通り。F1 と同種 | pretooluse_guard.py:3707 | 静的読解のみ |

実験案（V1〜V4 をまとめて確かめる）:

> EXPERIMENT_BEGIN P1-E1
bash -c '
G=scripts/claude/hooks/pretooluse_guard.py
T=$(mktemp -d /tmp/p1e1.XXXXXX)
cat > $T/run.py <<"PY"
import json,subprocess,sys
G=sys.argv[1]
def run(label,payload):
    p=subprocess.run(["python3",G],input=json.dumps(payload),capture_output=True,text=True,timeout=60)
    ask="ask" in p.stdout and "permissionDecision" in p.stdout
    print(label, "ASK" if (p.returncode==0 and ask) else p.returncode)
def B(label,cmd): run(label,{"tool_name":"Bash","tool_input":{"command":cmd}})
def W(label,path,content): run(label,{"tool_name":"Write","tool_input":{"file_path":path,"content":content}})
def E(label,path,old,new): run(label,{"tool_name":"Edit","tool_input":{"file_path":path,"old_string":old,"new_string":new}})
def M(label,path,old,new): run(label,{"tool_name":"MultiEdit","tool_input":{"file_path":path,"edits":[{"old_string":old,"new_string":new}]}})
# V1 代表
B("V1 force push","git push --force origin feature/x")
B("V1 push develop","git push origin develop")
B("V1 push delete","git push origin --delete feature/x")
B("V1 reset hard","git reset --hard")
B("V1 down -v","docker compose down -v")
B("V1 DROP TABLE container","docker compose exec -T db psql -U postgres -c \"DROP TABLE users\"")
B("V1 rm -rf container","docker compose exec -T backend rm -rf /app/x")
B("V1 cat .env","cat backend/.env")
B("V1 requests.post","docker compose exec -T backend python -c \"import requests; requests.post(chr(104)+chr(116)+chr(116)+chr(112)+chr(58)+chr(47)+chr(47)+chr(120))\"")
B("V1 send_mail","docker compose exec -T backend python manage.py shell -c \"from django.core.mail import send_mail; send_mail(1,2,3,[4])\"")
# V1/V2 抜け道の探索
B("X1 psql UPDATE no WHERE","docker compose exec -T db psql -U postgres -d learning_app -c \"UPDATE users SET password=NULL\"")
B("X2 psql UPDATE lower","docker compose exec -T db psql -U postgres -d learning_app -c \"update accounts_user set is_active=false\"")
B("X3 sed -i app","docker compose exec -T backend sed -i s/a/b/ /app/config/settings.py")
B("X4 tee app","docker compose exec -T backend tee /app/manage.py")
B("X5 cp app","docker compose exec -T backend cp /tmp/x /app/manage.py")
B("X6 mv app","docker compose exec -T backend mv /tmp/x /app/manage.py")
B("X7 redirect tmp-dotdot","docker compose exec -T backend sh -c \"echo x > /tmp/../app/manage.py\"")
B("X8 cp dotdot","docker compose cp ./nonexist backend:/tmp/../app/manage.py")
B("X9 pg_dump","docker compose exec -T db pg_dump -U postgres learning_app")
B("X10 set","docker compose exec -T backend sh -c set")
B("X11 python os.remove","docker compose exec -T backend python -c \"import os; os.remove(chr(47)+chr(97))\"")
B("X12 pathlib unlink variant","docker compose exec -T backend python -c \"import pathlib; pathlib.Path(chr(47)+chr(97)).write_text(chr(120))\"")
B("X13 manage.py migrate zero","docker compose exec -T backend python manage.py migrate accounts zero")
B("X14 manage.py sqlflush|dbshell","docker compose exec -T backend python manage.py sqlflush")
# V3
WF=".github/workflows/zz_i200_probe.yml"
W("V3 W version only",WF,"jobs:\n  a:\n    steps:\n      - uses: actions/checkout@v5\n")
W("V3 W secrets.",WF,"env:\n  X: ${{ secrets.FOO }}\n")
W("V3 W secrets[]",WF,"env:\n  X: ${{ secrets[\"FOO\"] }}\n")
W("V3 W write",WF,"permissions:\n  contents: write\n")
W("V3 W pull_request_target",WF,"on:\n  pull_request_target:\n")
W("V3 W github.event",WF,"run: echo ${{ github.event.pull_request.title }}\n")
E("V3 E secrets",WF,"a","${{ secrets.FOO }}")
M("V3 M secrets",WF,"a","${{ secrets.FOO }}")
E("V3 E version only",WF,"checkout@v4","checkout@v5")
W("V3x W GITHUB_TOKEN passthrough",WF,"env:\n  T: ${{ github.token }}\n")
W("V3x W abs path",__import__("os").path.abspath(WF),"env:\n  X: ${{ secrets.FOO }}\n")
W("V3x W ../ path","scripts/../.github/workflows/zz_i200_probe.yml","env:\n  X: ${{ secrets.FOO }}\n")
W("V3x W .yaml","./.github/workflows/zz_i200_probe.yaml","env:\n  X: ${{ secrets.FOO }}\n")
W("V3x W upper SECRETS","./.github/workflows/zz_i200_probe.yml","env:\n  X: ${{ SECRETS.FOO }}\n")
# V4
P=".pre-commit-config.yaml"
E("V4 E remove detect-secrets",P,"- id: detect-secrets","- id: other")
E("V4 E add exclude",P,"- id: detect-secrets","- id: detect-secrets\n        exclude: ^docs/")
E("V4 E add files",P,"- id: detect-secrets","- id: detect-secrets\n        files: ^docs/")
E("V4 E add args --exclude-files",P,"- id: detect-secrets","- id: detect-secrets\n        args: [--exclude-files, docs]")
E("V4 E rev only",P,"rev: v1","rev: v2")
M("V4 M remove detect-secrets",P,"- id: detect-secrets","- id: other")
W("V4 W without detect-secrets",P,"repos: []\n")
PY
python3 $T/run.py $G 2>&1
'
> EXPERIMENT_END P1-E1

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> ITEM: V3 RESULT=read
> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

V6 を確かめる実験案を返す。V5 は差分と計画の記述だけでは確定できず、テスト本体の差分が切れているので、今は `read` では埋めない。

> EXPERIMENT_BEGIN P2-E1
cat > /tmp/p2e1.sh <<'EOF'
set -u
HOOK="$1"
export GIT_AUTHOR_NAME=a GIT_AUTHOR_EMAIL=a@a GIT_COMMITTER_NAME=a GIT_COMMITTER_EMAIL=a@a GIT_TERMINAL_PROMPT=0
T=$(mktemp -d); cd "$T"
git init -q --bare -b develop origin.git
git clone -q origin.git seed 2>/dev/null
( cd seed && git checkout -q -b develop && echo 1 > a && git add a && git commit -qm c1 && git push -q origin develop )
run() {
  name=$1; setup=$2; seedfile=$3
  rm -rf p w
  git clone -q origin.git p
  ( cd p && git checkout -q develop 2>/dev/null; git worktree add -q -b feat_$name ../w )
  ( cd seed && echo "$name" > "$seedfile" && git add "$seedfile" && git commit -qm "n-$name" && git push -q origin develop )
  ( cd p && eval "$setup" )
  before=$(cd p && git rev-parse --short HEAD)
  out=$(cd w && timeout 50 python3 "$HOOK" 2>&1 | grep '^primary')
  after=$(cd p && git rev-parse --short HEAD)
  echo "== $name: before=$before after=$after"
  echo "   out: $out"
  echo "   status: $(cd p && git status --porcelain | tr '\n' '|')"
}
run clean ":" n_clean.txt
run dirty "echo x >> a" n_dirty.txt
run otherbr "git checkout -q -b other" n_other.txt
run diverged "echo y > own.txt && git add own.txt && git commit -qm own" n_div.txt
run untracked_clash "echo MINE > clash.txt" clash.txt
echo "clash content: $(cat p/clash.txt)"
run untracked_other "echo MINE > keep.txt" n_keep.txt
echo "keep content: $(cat p/keep.txt)"
EOF
bash -c 'ulimit -v 2097152; timeout 120 bash /tmp/p2e1.sh "$PWD/scripts/claude/hooks/sessionstart_context.py"'
> EXPERIMENT_END P2-E1

> ITEM: V5 RESULT=not_done
> ITEM: V6 RESULT=not_done
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I200] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | 要件の網羅 | CLAUDE.md の絶対ルール 4 は「破壊的マイグレーション」を承認制の例に挙げている。しかし、`ask` から `Edit(**/migrations/*.py)` を外したため、作成時に確認する層が無くなった。`danger-ops.md` の 37 行目は、この穴を「見張りが判定しないもの」として明記している。イシューの設計確認メモでも外すと決めており、矛盾ではなく承知の上の残余リスク。 | `.claude/settings.json` の `ask`、`danger-ops.md:37` | 静的読解 |

V7 と V8 については、確認の食い違いも新しい Critical / High も見つからなかった。

- **V7（許可の設定）**
  - allow に足した行は、計画どおりの `docker compose exec|run|cp`、`docker-compose` の同じ 3 つ、`git rebase *`、`psql *`、Edit の 4 件だけ（`settings.json` 67〜78 行）。
  - `Bash(docker compose *)` のような広い行は無い。e2e 用の `--profile e2e run` の行は残っている。
  - `ask` は `Edit(.secrets.baseline)` の 1 件だけ（104〜106 行）。
  - 秘密ファイルの deny（`Read` と `Edit` の `**/.env*`・`secrets/**`・`*.pem`・`*.key`）は全部残っている。deny は allow より優先されるので、足した allow が deny に勝つことは無い。
  - `curl`・`wget`・`ssh`・`git push` 系の deny も変わっていない。
- **V8（danger-ops.md）**
  - 17〜22 行の基準（(A)〜(C) と、残すもの）は、`settings.json` の `ask` の実物と一致する。
  - 29・30・32・33 行の記述も、計画 5-1〜5-5 と矛盾しない。

探索した仮説は次の 3 つ。
1. allow を広げたことで、deny や secrets の保護をすり抜ける経路があるか。
2. danger-ops.md の基準が、設定や見張りと食い違っていないか。
3. CLAUDE.md の絶対ルールとの整合。

> ITEM: V7 RESULT=read
> ITEM: V8 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 6
REVIEWED_COMMIT: 2e5262026c2a5ed5dd9300e958d0ae62c50b4e07
ROUNDS: 1
VERDICT: HIGH
