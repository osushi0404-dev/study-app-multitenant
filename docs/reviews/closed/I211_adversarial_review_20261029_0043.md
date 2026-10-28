# 敵対的レビュー [I211]（別プロセス・2026-10-29 00:43）

- 見た範囲: origin/develop...03678432331d74a63fc4f847fea56483d0ab05d8
- 所要時間: 93 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- 一覧: docs/plans/open/plan_I211.md の「## 必ず確かめる項目」（5 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 実験必須 | 実験で確認 | P1-E2=ran  | 確認済み（実験） |
| V2 | 1 | 実験必須 | 実験で確認 | P1-E1=ran P1-E2=ran P1-E3=ran  | 確認済み（実験） |
| V3 | 2 | 実験必須 | 実験で確認 | P2-E1=ran P2-E2=ran  | 確認済み（実験） |
| V4 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 69 秒 | 1 | 0 | $0.6660 | ― | ― | ― |
| 2 | 報告あり | 88 秒 | 1 | 0 | $0.7780 | ― | ― | ― |
| 3 | 報告あり | 29 秒 | 0 | 0 | $0.2736 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; env -i PATH=/usr/bin:/bin HOME=/tmp timeout 60 bash scripts/claude/tests/run-all.sh; echo "exit=$?"'
~~~
出力の先頭:
~~~
is_error=false
⛔ uv がありません。入れ方: docs/runbooks/onboarding.md「手元の準備（ハーネスのテスト）」。テストは流していません
exit=1
~~~

#### P1-E2: 実行した
~~~
bash -c 'ulimit -v 2097152; VIRTUAL_ENV="$PWD/scripts/claude/tests/.venv" HARNESS_UV_REEXEC= timeout 60 bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i211_version_pin.sh; echo "exit=$?"'
~~~
出力の先頭:
~~~
is_error=false
⛔ 版が違う道具: python3 3.12.3（正 3.11.18・scripts/claude/tests/.python-version）。入れ方: bash scripts/claude/tests/run-all.sh で流す（uv が .python-version の python を入れる）
⛔ 版が違う道具: PyYAML 6.0.1（正 6.0.3・scripts/claude/tests/uv.lock）。入れ方: bash scripts/claude/tests/run-all.sh で流す（uv が uv.lock の版を入れる）
OK: uv uv 0.13.6 (x86_64-unknown-linux-gnu)
OK: git git version 2.43.0
OK: docker compose Docker Compose version v5.6.0
⛔ 版が違う道具: pre-commit 4.5.1（正 4.7.0・scripts/claude/tests/uv.lock）。入れ方: bash scripts/claude/tests/run-all.sh で流す（uv が uv.lock の版を入れる）
OK: shellcheck shellcheck...............................................................Passed
⛔ ハーネスのテストが頼る道具がそろっていません（一覧: scripts/claude/tests/required-tools.txt）。テストは流していません
exit=1
~~~

#### P1-E3: 実行した
~~~
bash -c 'ulimit -v 2097152; HARNESS_UV_REEXEC=1 VIRTUAL_ENV=/nonexistent timeout 60 bash scripts/claude/tests/run-all.sh; echo "exit=$?"'
~~~
出力の先頭:
~~~
is_error=false
⛔ uv で流し直しても uv の環境に入れませんでした（VIRTUAL_ENV=/nonexistent）
exit=1
~~~

### 観点 2

#### P2-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 60 bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i211_version_pin.sh' 2>&1 | head -60
~~~
出力の先頭:
~~~
is_error=false
OK: python3 3.11.18（正 scripts/claude/tests/.python-version）
OK: PyYAML 6.0.3（正 scripts/claude/tests/uv.lock）
OK: uv uv 0.13.6 (x86_64-unknown-linux-gnu)
OK: git git version 2.43.0
OK: docker compose Docker Compose version v5.6.0
OK: pre-commit 4.7.0（正 scripts/claude/tests/uv.lock）
OK: shellcheck shellcheck...............................................................Passed
run-all: pass=1 fail=0
~~~

#### P2-E2: 実行した
~~~
bash -c 'ulimit -v 2097152; d=$(mktemp -d); printf "%s\n" "python3 | echo Python 3.11.18rc1 | lock | x" > $d/required-tools.txt; printf "3.11.18\n" > $d/.python-version; timeout 60 bash scripts/claude/tests/check-tools.sh $d/required-tools.txt; echo rc=$?; printf "3.11.18\r\n" > $d/.python-version; timeout 60 bash scripts/claude/tests/check-tools.sh $d/required-tools.txt; echo rc=$?'
~~~
出力の先頭:
~~~
is_error=false
OK: python3 3.11.18（正 /tmp/tmp.HPbjmicuK6/.python-version）
rc=0
OK: python3 3.11.18（正 /tmp/tmp.HPbjmicuK6/.python-version）
rc=0
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I211] ── 観点: 1. ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | ロジック回避 | `ci_check` は job / step の `env:`（`UV_PYTHON` など）を見ない。普通の書き方で `env: UV_PYTHON: 3.12` を足すと、`.python-version` 以外から python が決まる。ただし `check-tools.sh` が `.python-version` とぴったり比べるので、CI は落ちる（fail-closed）。止まるのはテストが流れた後で、`test_i204_tool_sync.sh` 自体は通る。 | test_i204_tool_sync.sh:90-130 | 静的読解のみ。`check-tools.sh:83-87` が版の不一致で exit 1 になる。 |
| Low | 抜け道（意図的） | 偽の `VIRTUAL_ENV` を指定して流し直しを避けても、`check-tools.sh` が OS の python を止める。 | run-all.sh:13 | P1-E2 で確認した。`VIRTUAL_ENV` を `.venv` に偽装して流すと、python3 3.12.3・PyYAML 6.0.1・pre-commit 4.5.1 の 3 件が `⛔ 版が違う道具` になり、テストを流さずに exit 1 になった。 |

Critical / High に当たる新規の欠陥は、反証を試みたが見つからなかった。

実験で確かめたこと:
- P1-E1: PATH に uv が無いと、`⛔ uv がありません。…テストは流していません` を出して exit 1 になる。V2 の「uv が無ければテストを流さずに exit 1」を確認した。
- P1-E2: 流し直しを避けても、版が違えばテストを流す前に止まる。V1・V2 の fail-closed を確認した。
- P1-E3: `HARNESS_UV_REEXEC=1` で `VIRTUAL_ENV` が一致しないと、流し直しの無限ループにならず `⛔` で exit 1 になる。V2 の X4 相当を確認した。

読んで確かめたこと:
- CI の harness-tests の python・PyYAML・pre-commit の版は、`.python-version` と `uv.lock` だけから決まる。
  - setup-uv には `version-file` しか書けない。`ci_check` が `with` を完全一致で固定している。
  - setup-python や install を足すと `ci_check` が弾く。
  - 抜け道の `env:` もあるが、`check-tools.sh` が最終的に止める。

> ITEM: V1 RESULT=experiment EXP=P1-E2
> ITEM: V2 RESULT=experiment EXP=P1-E1,P1-E2,P1-E3
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I211] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | false-green の余地 | 版の列が `lock` の道具は、出力の最初の `N.N…` だけを取り出して比べる。そのため `3.11.18rc1` のような接尾辞が付いていても、正の `3.11.18` と一致して OK になる。CRLF 行末の `.python-version` も `trim` で吸収されて OK になる。今の 3 つの道具（python3・PyYAML・pre-commit）は接尾辞付きの版を出さないので、実害は出ていない。 | check-tools.sh:77 | P2-E2: 出力が `Python 3.11.18rc1` でも `OK: python3 3.11.18`（rc=0）。`.python-version` が CRLF でも OK（rc=0）。 |
| Low | tautology（名前だけ） | FG-V2 は `.python-version` を `0.0.1` にしており、これは実際より低い値だ。しかしテスト名は「正より新しい」と書いてある。FG-V3 の `99.0.0` と「正より古い」も同じく逆になっている。比較は完全一致だけなので、向きによって結果が変わる処理は無い。実害は無い。 | test_i211_version_pin.sh:32,36 | 静的読解（check-tools.sh:83 は完全一致だけ） |
| Low | FG の弱さ | FG-C は `ci_check` が exit 1 を返すことだけを期待する。そのため `ci_mut` が失敗して写しが壊れた場合や `ci_check` がクラッシュした場合も、不合格として合格扱いになりうる。ただし C1 が実物の ci.yml で exit 0 を要求しているので、今の構成では起きない。 | test_i204_tool_sync.sh:158-166 | 静的読解 |

**V3 の結論**

- 比較は `[ "$ver" = "$want" ]` の完全一致だけで、版が上でも下でも合格にならない。
- 正のファイルが無い、または名前が無いときは exit 2 になる。
- P2-E1 では、手元の実物で 3 つの道具が正とぴったり一致した（python3 3.11.18・PyYAML 6.0.3・pre-commit 4.7.0）。`test_i211_version_pin.sh` も `run-all: pass=1 fail=0` で通った。
- `head -60` で出力を切ったので、項目ごとの PASS 行（FG-V2〜V7 など）は実験の出力に出ていない。この点は注意が要る。ただし各項目の判定は `rc` と文言の両方を見ており、静的読解でも false-green の経路は見つからなかった。
- 実害のある false-green は確認できなかった。

**V4 の結論**

`INSTALL` の正規表現は、次の 5 つを拾う。

- `apt-get -y install`
- `npm i`
- `uv pip install`
- `python -m pip install`
- `uv sync`

`uv run …` と `echo install` は拾わない。これは C2 と FG-C の失敗注入で確かめている。

> ITEM: V3 RESULT=experiment EXP=P2-E1,P2-E2
> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I211] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | 手順の不要な工程 | onboarding の「python（パッチ版）」の行は、`.python-version` を書き換えたあとに `uv lock` を流すよう書いてある。uv.lock はパッチ版を持たないので、パッチ版を上げても uv.lock は変わらない。流しても害は無く、手順がずれる原因にはならない。 | docs/runbooks/onboarding.md（版を上げる手順の表） | 静的読解。pyproject.toml の `requires-python = "==3.11.*"` はパッチ版を持たない。 |

反証失敗（新規の Critical/High なし）。V5 の手順に沿って版を上げたとき、手元と CI の版は揃ったまま上がる。

探索した仮説:
1. **版を上げる手順の抜け（PyYAML・pre-commit・python パッチ版・python マイナー版・uv）**
   - PyYAML・pre-commit は `uv lock --upgrade-package` で uv.lock だけが変わる。手元は `run-all.sh` の `uv run --locked` で入れ直され、CI は同じ uv.lock を読む。
   - python パッチ版は `.python-version` を `--project` の指す scripts/claude/tests から uv が読む。手元も CI も同じ値で python を取る。
   - python マイナー版は `.python-version` だけを変えると K1 が止める。runbook にもその旨がある。
   - uv は `required-version` を書き換える。手元の uv が古ければ uv 自身が止め、CI の setup-uv は同じ行を `version-file` で読む。
2. **片方だけ上がった場合に止まる場所**
   - `pyproject.toml` と uv.lock のずれは `--locked` が止める。
   - `.python-version` と、`.python-version` に合わないパッチ版の python は `check-tools.sh` の `lock` が止める。
   - ci.yml への版指定や install の追加は `test_i204_tool_sync.sh` が止める。
   - 手順に未対応のずれは見つからなかった。
3. **CI の版読み取りの前提**
   - setup-uv は working directory の `.python-version` を読まないが、python は uv が `--project` から取るので揃う。
   - ci.yml の差分では setup-uv の入力は `version-file` だけで、`python-version` は無い。
   - fix-loop の記録で FG-K2 まで CI が走っていることから、`version-file` による版の読み取りは実機で動いている。

実験は返さない。V5 は静的読解（read）で確かめられる項目で、裏付けに実験は要らない。

> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 03678432331d74a63fc4f847fea56483d0ab05d8
ROUNDS: 1
VERDICT: OK
