# 敵対的レビュー [I200]（別プロセス・2026-10-29 23:49）

- 見た範囲: 2e5262026c2a5ed5dd9300e958d0ae62c50b4e07...5e9884a4d1d66e83a27f63b095e887e58e16614d
- 所要時間: 119 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 1 件は下の表）
- 一覧: docs/plans/open/plan_I200.md の「## 必ず確かめる項目」（8 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 2 | 読んで可 | 実験で確認 | P2-E1=ran  | 確認済み（実験） |
| V7 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V8 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 63 秒 | 1 | 1 | $0.4574 | ― | ― | ― |
| 2 | 報告あり | 113 秒 | 1 | 0 | $0.4543 | ― | ― | ― |
| 3 | 報告あり | 27 秒 | 0 | 0 | $0.2536 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 拒否された
~~~
bash -c '
G=scripts/claude/hooks/pretooluse_guard.py
T=$(mktemp -d /tmp/p1e1.XXXXXX)
cat > $T/run.py <<"PY"
import json,subprocess,sys
G=sys.argv[1]
def run(label,payload):
    p=subprocess.run(["python3",G],input=json.dumps(payload),capture_output=True,text=True,timeout=20)
    ask="ask" in p.stdout and "permissionDecision" in p.stdout
    print(label, "ASK" if (p.returncode==0 and ask) else p.returncode)
def B(label,cmd): run(label,{"tool_name":"Bash","tool_input":{"command":cmd}})
def W(label,path,content): run(label,{"tool_name":"Write","tool_input":{"file_path":path,"content":content}})
def E(label,path,old,new): run(label,{"tool_name":"Edit","tool_input":{"file_path":path,"old_string":old,"new_string":new}})
B("V1 force push","git push --force origin feature/x")
B("V1 push develop","git push origin develop")
B("V1 push delete","git push origin --delete feature/x")
B("V1 reset hard","git reset --hard")
B("V1 down -v","docker compose down -v")
B("V1 DROP TABLE","docker compose exec -T db psql -U postgres -c \"DROP TABLE users\"")
B("V1 rm -rf ctr","docker compose exec -T backend rm -rf /app/x")
B("V1 cat .env","cat backend/.env")
B("X1 psql UPDATE no WHERE","docker compose exec -T db psql -U postgres -d learning_app -c \"UPDATE accounts_user SET is_active=false\"")
B("X2 psql DELETE no WHERE","docker compose exec -T db psql -U postgres -d learning_app -c \"DELETE FROM accounts_user\"")
B("X3 sed -i app","docker compose exec -T backend sed -i s/a/b/ /app/config/settings.py")
B("X4 export bare","docker compose exec -T backend sh -c export")
WF=".github/workflows/zz_i200_probe.yml"
W("V3 W version only",WF,"      - uses: actions/checkout@v5\n")
W("V3 W secrets",WF,"env:\n  X: ${{ secrets.FOO }}\n")
W("V3 W write",WF,"permissions:\n  contents: write\n")
E("V3 E secrets",WF,"a","${{ secrets.FOO }}")
P=".pre-commit-config.yaml"
E("V4 E add exclude",P,"- id: detect-secrets","- id: detect-secrets\n        exclude: ^docs/")
W("V4 W without detect-secrets",P,"repos: []\n")
PY
timeout 100 python3 $T/run.py $G 2>&1
'
~~~
出力の先頭:
~~~

~~~

### 観点 2

#### P2-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 120 bash scripts/claude/tests/test_sessionstart_context.sh 2>&1 | tail -n 30'
~~~
出力の先頭:
~~~
is_error=false
PASS TC-11a 通常は exit 0 で branch と直近のマージを出す
PASS TC-11b 出力は 10 行以内
PASS TC-11c gh が失敗しても exit 0・取得できませんでした・7 秒
PASS TC-11d git の外でも exit 0
PASS TC-11e タイトルの自由文を出さない
PASS TC-11f GitHub の値（PR・最新イシュー）を番号と I### で出す
PASS TC-11g settings.json の SessionStart に登録されている
PASS TC-07a origin が進んでいれば primary を早送りする
PASS TC-07b 2 回目は最新です
PASS TC-07c 未コミットの変更があれば動かず、変更が残る
PASS FG-07 判定を消すと 07c の条件で HEAD が動く（TC-07c が捕まえる）
PASS TC-07d develop 以外にいれば動かない
PASS TC-07e 早送りできなければ動かず、手で行うコマンドを出す
PASS TC-07f 未追跡のファイルは残して早送りする
PASS TC-07g 未追跡のファイルとぶつかるなら動かず、中身が残る
PASS TC-07i git が遅くても 15 秒で終わり、既存の行と primary の行を出す
pass=16 fail=0
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I200] ── 観点: 1. ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | V2 | `cp -t <dir>` の形でコンテナ内の `/app` に書く操作が通る疑いがある。既知 findings の F9 と同じで、脅威モデルの外のため新規には数えない。 | `_ctr_write_targets`（pretooluse_guard.py:2403-2417） | 静的読解のみ |
| Low | V1 | コンテナ内の `psql` で WHERE なしの `UPDATE` は、`_RISKY_WORDS` に当たらず通る疑いがある。`.update(` しか語の一覧に無いため。計画の TC-02 は WHERE なしの `DELETE` のみを扱う。実験が拒否されたため未確認で、確認なしの `UPDATE` は I200 以前から (B) の穴だった可能性がある。 | `_RISKY_WORDS`（pretooluse_guard.py:2320 付近） | 静的読解のみ。実験 P1-E1 は denied |

実験 P1-E1 は denied で、出力が空だった。実験で確かめられた項目は無い。次の 4 項目はどれも静的読解で確かめた。実験が拒否された原因は、実験役の権限で `python3` の heredoc 実行が許されなかったことだと推測している。残りの往復は 1 回だが、同じ形の実験は再び拒否される見込みが高いので、再提出はしない。

- **V1**
  - 差分は `_RISKY_WORDS` への `pg_dump` 追加と、`_container_risky` の拡張だけ。
  - force push・保護ブランチへの push・`reset --hard`・`down -v` を判定するコードは、この差分で変わっていない。
  - コンテナ内の `DROP TABLE`・`rm -rf`・`requests`・`send_mail` は `_RISKY_WORDS` に残っている。
  - 決定論の TC-02 の 14 件で覆われている。
- **V2**
  - `_in_scratch` は `normpath` を通すので `/tmp/../app` は外と判定される。
  - `tee`・`sed -i`・`cp`・`mv` の書き込み先も確認になる。
  - 別 worktree への書き込みの停止は `_analyze` より前に移っており、読み解きが例外のときも効く。
  - 抜けは F9（`cp -t`）と F10（引数なしの `export`）だけで、どちらも既知で脅威モデルの外。
- **V3・V4**
  - この差分では判定のコードに変更が無い。
  - 決定論の TC-04・TC-05 の記録に頼った。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> ITEM: V3 RESULT=read
> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I200] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| なし | V5 | 差分で期待値を変えた既存ケースは `test_pretooluse_container_guard.sh` の C17 だけだった。旧期待値は 0、新期待値は ASK で、旧期待値が 2 の行を変えたものはない。auto_test の一覧も C17 を外して 58 件に直してあり、差分と合っている。 | test_pretooluse_container_guard.sh:476 | 静的読解（差分） |
| なし | 03j | 停止を `_analyze` の後ろに戻せば、危ない語がないので 0 になり、2 を期待する 03j は落ちる。一時のリポジトリで主とワークツリーを作るので、環境にも依存しない。 | test_i200_guard_narrowing.sh:91-96 | 静的読解 |
| なし | V6 | SIGTERM 方式（`_run_git_soft`）の変更後も、`test_sessionstart_context.sh` の TC-07a〜07g・07i と FG-07 が全部通った。未コミットの変更がある・develop 以外・早送りできない・未追跡のファイルとぶつかるときは動かず、未追跡のファイルは残る。FG-07 は判定を消すと HEAD が動くことを捕まえる。 | sessionstart_context.py:88-105 | 実験 P2-E1: `pass=16 fail=0` |

探索した仮説:
- 期待値の変更に停止（2）が紛れていないか。
- 03j が環境依存、または常に pass になっていないか。
- F2 の変更で TC-07 が回帰していないか。

> ITEM: V5 RESULT=read
> ITEM: V6 RESULT=experiment EXP=P2-E1
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I200] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | V8 | このレビュー範囲の変更(F3・F6)で見張りの確認の範囲が広がったが、`danger-ops.md` が追いついていない。29 行目は「コンテナの `/tmp/` 以外へ**リダイレクトで**書き込むか、環境変数をまとめて表示する(`ps e`・引数なしの `env`)ときだけ確認」と書いてある。実物は次のとおり。<br>・`tee`・`sed -i`・`cp`・`mv`・`install`・`ln`・`rsync` の書き込み先も確認になる(`_ctr_write_targets`)。<br>・`/tmp/` の判定は `..` を正規化する。<br>・`set`・`export -p`・`declare -p` も環境変数の表示として確認になる。<br>・`pg_dump` も語として確認になる。<br>基準そのもの(A)〜(C)とは矛盾せず、誤記は説明の細部に限られる。ただし V8 の「実物と食い違わない」には正確には当たらない。同じ 29 行目の `docker compose cp` の説明(コピー先が `/tmp/` 以外なら確認)は実物と合っている。 | `docs/runbooks/danger-ops.md:29` と `pretooluse_guard.py:2385-2417` | 静的読解 |
| Low | V7 | 残余リスクなので、新しい指摘ではない。`Bash(psql *)` を allow に足した結果、ホストの `psql` は `ask` なしで通る。判定は見張りに依存し、停止するのは `DROP` や WHERE なしの `DELETE` など、見張りが読める形だけ。計画で承知済みの範囲。 | `settings.json:74` | 静的読解 |

V7 の確認結果(`settings.json` の読み取り)は次のとおり。
- allow に足した行は、計画どおりの `docker compose exec|run|cp`、`docker-compose` の同じ 3 つ、`git rebase *`、`psql *`、Edit の 4 件だけ(67〜78 行)。
- `Bash(docker compose *)` のような広い行は無い。e2e の `--profile e2e run` の行は残っている(79〜82 行)。
- `ask` は `Edit(.secrets.baseline)` の 1 件だけ(104〜105 行)。
- 秘密ファイルの deny(`Edit(**/.env*)`・`secrets/**`・`*.pem`・`*.key`)は残っている(131〜137 行)。
- 今回の差分は `settings.json` に触れていない。

V8 の確認結果は次のとおり。
- 17〜22 行の基準と、`ask` の実物は一致する。
- 33 行目の編集の確認の記述も、計画と一致する。
- 食い違いは上の Low の 1 点だけ。Critical/High になるものではない。

探索した仮説は次の 3 つ。
1. 足した allow が deny や秘密の保護を破る経路があるか。→ 無し。
2. 今回の見張りの変更(F1・F3・F4・F6)に、`danger-ops.md` が追いついているか。→ 29 行目が古く、Low。
3. 絶対ルール 4(破壊的マイグレーション)との整合。→ 既知の台帳の記載どおり、承知の上の残余リスクで、新規ではない。

> ITEM: V7 RESULT=read
> ITEM: V8 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 5e9884a4d1d66e83a27f63b095e887e58e16614d
ROUNDS: 1
VERDICT: OK
