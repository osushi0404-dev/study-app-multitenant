# 敵対的レビュー [I213]（別プロセス・2026-10-29 10:32）

- 見た範囲: origin/develop...d4dc801d038f5c8855511b7a67d1aca3fdf113b9
- 所要時間: 78 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 1 件は下の表）
- 一覧: docs/plans/open/plan_I213.md の「## 必ず確かめる項目」（6 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V2 | 1 | 実験必須 | 実験で確認 | P1-E1=ran P1-E2=ran  | 確認済み（実験） |
| V3 | 1 | 実験必須 | 実験で確認 | P1-E1=ran P1-E2=ran  | 確認済み（実験） |
| V4 | 2 | 実験必須 | 実験で確認 | P2-E1=ran  | 確認済み（実験） |
| V5 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 74 秒 | 1 | 0 | $0.6253 | ― | ― | ― |
| 2 | 報告あり | 54 秒 | 1 | 1 | $0.5722 | ― | ― | ― |
| 3 | 報告あり | 19 秒 | 0 | 0 | $0.2679 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 60 bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i213_dependabot.sh' 2>&1 | tail -30
~~~
出力の先頭:
~~~
is_error=false
OK: python3 3.12.3（正 scripts/claude/tests/.python-version）
OK: PyYAML 6.0.3（正 scripts/claude/tests/uv.lock）
OK: uv uv 0.13.6 (x86_64-unknown-linux-gnu)
OK: git git version 2.43.0
OK: docker compose Docker Compose version v5.6.0
OK: pre-commit 4.7.0（正 scripts/claude/tests/uv.lock）
OK: shellcheck shellcheck...............................................................Passed
run-all: pass=1 fail=0
~~~

#### P1-E2: 実行した
~~~
bash -c 'ulimit -v 2097152; set -u; d=$(mktemp -d); for f in .github/workflows/ci.yml .github/workflows/e2e.yml .github/workflows/dependency-audit.yml .github/dependabot.yml backend/Dockerfile frontend/Dockerfile frontend/Dockerfile.dev docker-compose.yml; do mkdir -p $d/$(dirname $f); cp $f $d/$f; done; sed -i "0,/actions\/checkout@[0-9a-f]\{40\} # v4.4.0/s##actions/checkout@main#" $d/.github/workflows/ci.yml; sed -i "s#image: postgres:15-alpine#image: postgres:15-alpine#" $d/.github/workflows/ci.yml; grep -n "checkout@main" $d/.github/workflows/ci.yml; grep -n "image: " $d/.github/workflows/ci.yml; sed -n "1,40p" scripts/claude/tests/test_i213_dependabot.sh >/dev/null; echo done'
~~~
出力の先頭:
~~~
is_error=false
18:      - uses: actions/checkout@main
46:        image: postgres:15-alpine
62:        image: redis:7-alpine
done
~~~

### 観点 2

#### P2-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 60 bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i213_dependabot.sh'
~~~
出力の先頭:
~~~
is_error=false
OK: python3 3.12.3（正 scripts/claude/tests/.python-version）
OK: PyYAML 6.0.3（正 scripts/claude/tests/uv.lock）
OK: uv uv 0.13.6 (x86_64-unknown-linux-gnu)
OK: git git version 2.43.0
OK: docker compose Docker Compose version v5.6.0
OK: pre-commit 4.7.0（正 scripts/claude/tests/uv.lock）
OK: shellcheck shellcheck...............................................................Passed
run-all: pass=1 fail=0
~~~

#### P2-E2: 拒否された
~~~
bash -c 'ulimit -v 2097152; timeout 60 docker compose --profile e2e config --format json | python3 -I -c "import json,sys; d=json.load(sys.stdin); print({n:[v for v in s.get(\"volumes\",[]) if not v.get(\"source\")] for n,s in d[\"services\"].items()}); print(list(d.get(\"volumes\",{})))"'
~~~
出力の先頭:
~~~

~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I213] ── 観点: 1. ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Medium | V3 / 指紋固定の抜け | `ci.yml` の `services:` にある `postgres:15-alpine` と `redis:7-alpine` は指紋なしのまま残っている。TC-01 I1 が見るのは Dockerfile と `docker-compose.yml` の `image:` だけなので、ここは検査されない。Dependabot の `docker-compose` ecosystem もワークフロー内の `services` は読まないと見られる。そのため固定も更新も届かない。「土台イメージがすべて指紋付き」(V3) と「タグの付け替えで CI が別の中身を動かさない」という狙いに穴がある。ただし CI のサービスコンテナは secrets を持たず、被害は限定的。 | .github/workflows/ci.yml:46,62 / scripts/claude/tests/test_i213_dependabot.sh:67-82 | P1-E2: `ci.yml` の 46 行目と 62 行目に指紋なしの `image:` が残っていることを確認した。静的読解でも I1 の検査範囲外と確認した。 |
| Low | V2 | W1 の正規表現は `uses: ./local` や `docker://` を許さない。将来ローカル action を足すと誤検知で不合格になる。事故の方向は安全側なので実害は小さい。 | test_i213_dependabot.sh:42-47 | 静的読解 |

### 実験で確認できたこと
- P1-E1: `run-all.sh` の実行が exit 0 で、出力は `pass=1 fail=0`。ここで確認できたのは、実物 6 項目が合格することと、写しを壊した FG が不合格になることをテスト内部で検査していること。ただし FG が合格した内訳は、出力の先頭部分だけでは見えていない。
- P1-E2: `@main` を写しの `ci.yml` に注入できたことは確認した。ただし W1 を実際に走らせて不合格になる結果までは取れていない。この項目は W1 の正規表現（`@[0-9a-f]{40}` を必須とする）を読んで確かめた。テスト内の FG-W1a（`@v4` 注入）と FG-W1b（`@v10.3.3` 注入）は、実物のテストが `pass=1 fail=0` で通っていることから合格している。
- `@main` のような SHA でない書き方は、同じ正規表現で不合格になる。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=experiment EXP=P1-E1,P1-E2
> ITEM: V3 RESULT=experiment EXP=P1-E1,P1-E2
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I213] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| — | — | 反証失敗(新規指摘なし) | — | — |

反証失敗(新規指摘なし)。探索した仮説:
- **V1 の判定が常に OK になる可能性。**
  - `chk V1` は compose の全サービスの `volumes` を走査し、名前の無い保存領域が `[("frontend","/app/node_modules")]` だけであることを要求する。
  - `:` を含まない短縮記法と、`source` の無い長記法の両方を拾う。
  - FG(失敗を注入する写し)は `postgres_data` の次の行に名前の無い保存領域を足す。
  - `sed` の対象行は `docker-compose.yml:10` に実在する。
- **実験の結果。** P2-E1 では `run-all: pass=1 fail=0` で、実物の 6 項目と FG がすべて期待どおりに通った。FG が不合格にならなければ `ck` が FAIL を出して `fail>0` になるので、FG は実際に効いている。
- **DB・redis の保存領域が名前付きか。**
  - `docker-compose.yml:10` が `postgres_data:`、`:29` が `redis_data:`で、名前付き。
  - 名前の無い保存領域は `:127` の `/app/node_modules` だけ。
  - したがって `--renew-anon-volumes` で消えるのは frontend の node_modules だけで、DB・redis の中身は残る。
- **P2-E2 は未取得。** `docker compose config` の実験は拒否されたため、compose の実際の解決結果は静的読解で代替した。
- **V5 の実物。**
  - `.github/dependabot.yml` に `target-branch` は無い。
  - 8 対象すべてに `security-minor-and-patch`(`applies-to: security-updates`)がある。
  - D2 の判定は `updates` の各要素に `target-branch` があるかを見ており、tautology ではない。
- **tautology(実装の写し)になっていないか。** V1 は「消えてよい保存領域は frontend の node_modules だけ」という不変条件を見ている。設定の写しではない。

> ITEM: V4 RESULT=experiment EXP=P2-E1
> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I213] ── 観点: 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。探索した仮説:
- **uv を見張らない理由が runbook にあるか**: 見つけた。`dependency-audit.md:52` に、Dependabot の uv の版と `required-version` の「ぴったりの版」がぶつかると書いてある。版の上げ方は onboarding.md への参照があり、`dependabot.yml` 冒頭のコメントとも一致する。
- **PR の受け取り方がイシューの Q3 と食い違わないか**: 食い違いはない。
  - 通し方の表（`dependency-audit.md:62-66`）は Q3 と同じ。minor・patch のまとめとセキュリティの修正は、CI が緑ならユーザーがマージする。
  - セキュリティの修正は、major でも CI が緑ならマージする。
  - CI が赤い PR と、セキュリティ以外の major は、マージせずイシューを立てる。major の PR は通知として開いたまま置く。
  - 自動マージは使わない。
- **ラベル・待つ日数・target-branch の説明**: 食い違いはない。`dependabot.yml` の実物とも一致する。
- **「取り込んだあと手元でやること」の抜け**: 抜けはない。`--pull` が不要な理由（指紋で固定するため）は計画の D3 と整合する。
- **想定攻撃の網羅**: 乗っ取られた版を CI が通すケースは、計画のセキュリティ節で Medium の残余リスクとして明記され、待つ日数と Malware alerts で対処している。見落としはない。
- **宛先の注意**: 既定ブランチを変えたときに Dependabot の PR の宛先も変わる、という注意が書いてある。
- **止まったときの確認先**: 書いてある。

実験は不要と判断した（V6 は「読んで可」）。

> ITEM: V6 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 1
REVIEWED_COMMIT: d4dc801d038f5c8855511b7a67d1aca3fdf113b9
ROUNDS: 1
VERDICT: HIGH
