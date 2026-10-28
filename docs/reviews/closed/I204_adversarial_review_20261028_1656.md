# 敵対的レビュー [I204]（別プロセス・2026-10-28 16:56）

- 見た範囲: origin/develop...45a54ecd61c76c90462f3aa331ea82b41b4ea3e7
- 所要時間: 86 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- 一覧: docs/plans/open/plan_I204.md の「## 必ず確かめる項目」（5 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 1 | 実験必須 | 実験で確認 | P1-E1=ran  | 確認済み（実験） |
| V3 | 2 | 実験必須 | 実験で確認 | P2-E1=ran P2-E2=ran  | 確認済み（実験） |
| V4 | 2 | 実験必須 | 実験で確認 | P2-E1=ran P2-E3=ran  | 確認済み（実験） |
| V5 | 3 | 実験必須 | 実験で確認 | P3-E1=ran P3-E2=ran  | 確認済み（実験） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 43 秒 | 1 | 0 | $0.5374 | ― | ― | ― |
| 2 | 報告あり | 81 秒 | 1 | 0 | $0.5544 | ― | ― | ― |
| 3 | 報告あり | 63 秒 | 1 | 0 | $0.5381 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; d=$(mktemp -d); for s in "--extra-index-url=http://x.invalid" "http://x.invalid/a.whl" "-e git+https://x.invalid/x" "PyYAML>=6.0 --index-url=http://x" "PyYAML>=6.0;python_version>\"3\"" "PyYAML>=6.0 @ http://x" "PyYAML>=6.0,<7"; do printf "x | true | - | %s | y\n" "$s" > "$d/l.txt"; out=$(timeout 60 bash scripts/claude/tests/check-tools.sh --pip-specs "$d/l.txt" 2>/dev/null); rc=$?; echo "rc=$rc out=[$out] spec=$s"; done'
~~~
出力の先頭:
~~~
is_error=false
rc=2 out=[] spec=--extra-index-url=http://x.invalid
rc=2 out=[] spec=http://x.invalid/a.whl
rc=2 out=[] spec=-e git+https://x.invalid/x
rc=2 out=[] spec=PyYAML>=6.0 --index-url=http://x
rc=2 out=[] spec=PyYAML>=6.0;python_version>"3"
rc=2 out=[] spec=PyYAML>=6.0 @ http://x
rc=2 out=[] spec=PyYAML>=6.0,<7
~~~

### 観点 2

#### P2-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 60 bash scripts/claude/tests/test_i204_tool_sync.sh 2>&1 | tail -60'
~~~
出力の先頭:
~~~
is_error=false
PASS L1 実物の一覧の形が正しい（--pip-specs が exit 0）
PASS L1 道具は 6 つ
PASS L2 実物の一覧で全部そろう（一覧の行の数だけ OK）
PASS FG-L3 通らない道具は exit 1・名前と入れ方・ほかは OK
PASS FG-L4 下限より古い python3 は exit 1
PASS FG-L5 版を読めない道具は exit 1
PASS FG-L6a 形の崩れた行は exit 2（a | true | - | -）
PASS FG-L6a 形の崩れた行は exit 2（a | true | abc | - | x）
PASS FG-L6a 形の崩れた行は exit 2（ | true | - | - | x）
PASS FG-L6b pip の指定は通さない（--extra-index-url=http://example.invalid）
PASS FG-L6b pip の指定は通さない（PyYAML @ https://example.invalid/x.whl）
PASS FG-L6b pip の指定は通さない（-e git+https://example.invalid/x）
PASS FG-L6b pip の指定は通さない（PyYAML>=6.0 --index-url=http://example.invalid）
PASS L7 --pip-specs は一覧の pip の列だけ
PASS FG-R1 道具が足りなければテストを流さず exit 1
PASS R2 道具がそろえばテストを流す
PASS FG-P1 pre-commit が無いと TC-C1 は不合格（SKIP しない）
PASS FG-P2 Skipped（対象外）でも TC-C1 は不合格
PASS C1 CI の Harness Tests は一覧に従う
PASS FG-C 写しの ci.yml（py312）は食い違いで不合格
PASS FG-C 写しの ci.yml（extra_pip）は食い違いで不合格
PASS FG-C 写しの ci.yml（extra_uses）は食い違いで不合格
PASS FG-C 写しの ci.yml（old_install）は食い違いで不合格
PASS S1 実物に「道具が無ければ SKIP」の分岐が無い
PASS S1 見たファイルが 40 本以上
PASS FG-S2 前の TC-C1 の形は当たる
PASS FG-S2 前の test_compose_ports.sh の形は当たる
PASS FG-S2 前の guard_bash_oracle.py の形は当たる
PASS S3 離れた SKIP・環境の状態の SKIP は当たらない
---
pass=29 fail=0
~~~

#### P2-E2: 実行した
~~~
bash -c 'ulimit -v 2097152; set -u; T=$(mktemp -d); git -C "$T" init -q; mkdir -p "$T/scripts/claude/tests" "$T/t" "$T/fakebin"; cp scripts/claude/tests/run-all.sh scripts/claude/tests/check-tools.sh scripts/claude/tests/required-tools.txt "$T/scripts/claude/tests/"; printf "#!/usr/bin/env bash\ntouch %s/mark\n" "$T" > "$T/t/test_mark.sh"; printf "#!/usr/bin/env bash\nexit 1\n" > "$T/fakebin/docker"; chmod +x "$T/fakebin/docker"; cd "$T"; PATH="$T/fakebin:$PATH" TEST_DIR=t timeout 60 bash scripts/claude/tests/run-all.sh 2>&1 | tail -15; echo "rc=${PIPESTATUS[0]}"; ls "$T/mark" 2>&1'
~~~
出力の先頭:
~~~
is_error=true
Exit code 2
OK: python3 3.12.3（下限 3.11）
OK: PyYAML 6.0.1（下限 6.0）
OK: git git version 2.43.0
⛔ 足りない道具: docker compose（`docker compose version` が通らない）。入れ方: Docker Desktop の WSL 連携を有効にする（CI は runner に最初からある）

OK: pre-commit 4.5.1（下限 4.0）
⛔ 足りない道具: shellcheck（`out=$(pre-commit run shellcheck --files scripts/claude/tests/check-tools.sh 2>&1); grep -E '^shellcheck\.+Passed$' <<< "$out" && exit 0; printf '%s\n' "$out"; exit 1` が通らない）。入れ方: pre-commit 経由（版は .pre-commit-config.yaml の shellcheck-py。初回はネットワークから入る）
    An error has occurred: InvalidConfigError:
    =====> .pre-commit-config.yaml is not a file
    Check the log at /home/tacic/.cache/pre-commit/pre-commit.log
⛔ ハーネスのテストが頼る道具がそろっていません（一覧: scripts/claude/tests/required-tools.txt）。テストは流していません
rc=1
ls: cannot access '/tmp/tmp.G7Ip66z38N/mark': No such file or directory
~~~

#### P2-E3: 実行した
~~~
bash -c 'ulimit -v 2097152; set -u; T=$(mktemp -d); mkdir -p "$T/bin"; printf "#!/usr/bin/env bash\necho something-else\nexit 0\n" > "$T/bin/pre-commit"; chmod +x "$T/bin/pre-commit"; PATH="$T/bin:$PATH" timeout 60 bash scripts/claude/tests/test_review_commit_lifecycle.sh 2>&1 | grep -E "TC-C1|PASS=|FAIL=" | tail; echo "rc=${PIPESTATUS[0]}"'
~~~
出力の先頭:
~~~
is_error=false
== TC-C1: shellcheck（.pre-commit-config.yaml の固定の版を pre-commit 経由で使う・I204） ==
FAIL TC-C1-shellcheck  expected[0 yes] got[0 no]
==== I069 commit-lifecycle tests: PASS=30 FAIL=1 ====
rc=1
~~~

### 観点 3

#### P3-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 170 bash scripts/claude/tests/test_i204_tool_sync.sh' 2>&1 | grep -E 'FG-C|^PASS C1|pass=|fail=|FAIL' | head -30
~~~
出力の先頭:
~~~
is_error=false
PASS C1 CI の Harness Tests は一覧に従う
PASS FG-C 写しの ci.yml（py312）は食い違いで不合格
PASS FG-C 写しの ci.yml（extra_pip）は食い違いで不合格
PASS FG-C 写しの ci.yml（extra_uses）は食い違いで不合格
PASS FG-C 写しの ci.yml（old_install）は食い違いで不合格
pass=29 fail=0
~~~

#### P3-E2: 実行した
~~~
python3 -I -c '
import re
INSTALL = re.compile(r"\b(?:pip3?|pipx|apt|apt-get|brew|npm|conda)\s+install\b")
for s in ["apt-get -y install jq","sudo apt-get -y install jq","apt-get install jq","python -m pip install foo","pip install foo","npm ci","npm i foo","sudo apt -y install jq","curl -sSL https://example.invalid/x.sh | sh"]:
    print(bool(INSTALL.search(s)), s)
'
~~~
出力の先頭:
~~~
is_error=false
False apt-get -y install jq
False sudo apt-get -y install jq
True apt-get install jq
True python -m pip install foo
True pip install foo
False npm ci
False npm i foo
False sudo apt -y install jq
False curl -sSL https://example.invalid/x.sh | sh
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I204] ── 観点: ロジック回避・実機 repro

## findings
反証失敗（新規指摘なし）。探索した仮説:
- pip の列に別の取得元を渡せるか。`--extra-index-url=`・URL・`-e`・`--index-url` の後置・環境マーカー（`;python_version>"3"`）・`@ URL`・範囲指定（`,<7`）の 7 通りを実験した（P1-E1）。すべて exit 2 で stdout が空だった。
- `PIP_RE` の `^…$` を改行で回避できるか。一覧は行単位で読み、列数も 5 に固定しているので、改行は混ざらない。
- `ci.yml` の変更が Harness Tests の step 以外に及んでいないか。差分は 1 hunk だけで、`on:`・`permissions`・secrets・`pull_request_target` は触れていない。

| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| なし | V1 | 差分は「Install test dependencies」の step だけだった。 | .github/workflows/ci.yml:159-166 | 静的読解 |
| なし | V2 | 7 通りの pip の指定が、すべて exit 2 で stdout が空だった。 | check-tools.sh:17,41 | P1-E1: 7 件とも rc=2 out=[] |

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=experiment EXP=P1-E1
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I204] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。探索した仮説:
- FG-R1 の「テストを流していない」が tautology ではないか。R2 で同じ印のファイルが作られるので、印が無いことは本物の判定になっている。P2-E1 で FG-R1 と R2 の両方が PASS した。
- FG-P1 と FG-P2 が、無関係な失敗で偶然通っていないか。どちらも `FAIL TC-C1-shellcheck` の文言まで確かめている。P2-E1 で PASS した。
- pre-commit が `Passed` を出さず exit 0 だけを返す場合に、TC-C1 が黙って合格にならないか。P2-E3 で `expected[0 yes] got[0 no]` の FAIL になり、全体も rc=1 だった。
- 実物の一覧で `TEST_DIR` を変えても、冒頭の確認が飛ばされないか。P2-E2 では、通らない `docker` を PATH の先頭に置いて `TEST_DIR=t` で流した。結果は `⛔ 足りない道具: docker compose`・`テストは流していません`・rc=1 で、印のファイルは作られなかった。

P2-E2 の注記が 2 つある。
- 実験は一時リポジトリに `.pre-commit-config.yaml` を写さなかった。このため shellcheck も同時に「足りない」と出ている。
- 同じ理由で、実験の外側の `ls` が exit 2 を返しただけである。run-all.sh 自体は rc=1 で、判定には影響しない。

> ITEM: V3 RESULT=experiment EXP=P2-E1,P2-E2
> ITEM: V4 RESULT=experiment EXP=P2-E1,P2-E3
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I204] ── 観点: 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Medium | 3 | `ci_check` の INSTALL 正規表現は `install` が道具名の直後に来る形しか拾わない。`apt-get -y install jq`・`sudo apt -y install jq` のようにオプションを挟んだ形は検出されない。`npm i foo`・`curl … \| sh` も同様に検出されない。Harness Tests にこれらを足しても食い違いのテストは通りうる。計画 4.8 ③の「一覧を通らない install を止める」に抜けがある。ただし、`pip install foo` の追加と `uses:` の追加は止まる（FG-C3・FG-C4 が PASS）。普通の書き方の事故として起きうる範囲だが、V5 で挙げた形（pip install・新しい uses）は止まる。Critical/High にはしない。 | scripts/claude/tests/test_i204_tool_sync.sh の `INSTALL = re.compile(...)` | P3-E2 の結果: `apt-get -y install jq`・`sudo apt-get -y install jq`・`sudo apt -y install jq`・`npm i foo` はいずれも False（検出されない）。`apt-get install jq`・`python -m pip install foo` は True |

V5 の実測結果（P3-E1）は次のとおり。
- C1（実物の `ci.yml`）は PASS。
- FG-C の `py312`・`extra_pip`・`extra_uses`・`old_install` は、写しがすべて食い違いとして不合格になった。
- `test_i204_tool_sync.sh` は `pass=29 fail=0`。

V5 の対象は「一覧を通らない install」「新しい `uses:`」「`python-version` の食い違い」で、いずれも不合格になることを確認した。

既知の台帳 F3（setup-python の step が消えると python-version の検査が働かない）と実質同一の指摘は、再報告していない。

> ITEM: V5 RESULT=experiment EXP=P3-E1,P3-E2
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 45a54ecd61c76c90462f3aa331ea82b41b4ea3e7
ROUNDS: 1
VERDICT: OK
