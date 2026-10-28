# 敵対的レビュー [I211]（別プロセス・2026-10-29 02:17）

- 見た範囲: 03678432331d74a63fc4f847fea56483d0ab05d8...0cba9b000273ea61e344d7044e4d35d5a79905ec
- 所要時間: 74 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- 一覧: docs/plans/open/plan_I211.md の「## 必ず確かめる項目」（5 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 実験必須 | 実験で確認 | P1-E2=ran P1-E4=ran  | 確認済み（実験） |
| V2 | 1 | 実験必須 | 実験で確認 | P1-E1=ran P1-E2=ran P1-E3=ran P1-E4=ran  | 確認済み（実験） |
| V3 | 2 | 実験必須 | 実験で確認 | P2-E1=ran  | 確認済み（実験） |
| V4 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 57 秒 | 1 | 0 | $0.5246 | ― | ― | ― |
| 2 | 報告あり | 71 秒 | 1 | 0 | $0.6136 | ― | ― | ― |
| 3 | 報告あり | 25 秒 | 0 | 0 | $0.2645 | ― | ― | ― |

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
bash -c 'ulimit -v 2097152; timeout 60 bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i211_version_pin.sh; echo "exit=$?"'
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
exit=0
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

#### P1-E4: 実行した
~~~
bash -c 'ulimit -v 2097152; VIRTUAL_ENV="$PWD/scripts/claude/tests/.venv" HARNESS_UV_REEXEC= timeout 60 bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i211_version_pin.sh; echo "exit=$?"'
~~~
出力の先頭:
~~~
is_error=false
OK: python3 3.12.3（正 scripts/claude/tests/.python-version）
⛔ 版が違う道具: PyYAML 6.0.1（正 6.0.3・scripts/claude/tests/uv.lock）。入れ方: bash scripts/claude/tests/run-all.sh で流す（uv が uv.lock の版を入れる）
OK: uv uv 0.13.6 (x86_64-unknown-linux-gnu)
OK: git git version 2.43.0
OK: docker compose Docker Compose version v5.6.0
⛔ 版が違う道具: pre-commit 4.5.1（正 4.7.0・scripts/claude/tests/uv.lock）。入れ方: bash scripts/claude/tests/run-all.sh で流す（uv が uv.lock の版を入れる）
OK: shellcheck shellcheck...............................................................Passed
⛔ ハーネスのテストが頼る道具がそろっていません（一覧: scripts/claude/tests/required-tools.txt）。テストは流していません
exit=1
~~~

### 観点 2

#### P2-E1: 実行した
~~~
bash -c 'ulimit -v 2097152; timeout 60 bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i211_version_pin.sh 2>&1 | grep -E "^(PASS|FAIL) (V[0-9]|FG-V)|run-all:|^pass="'
~~~
出力の先頭:
~~~
is_error=false
run-all: pass=1 fail=0
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I211] ── 観点: 1. ロジック回避・実機 repro

## findings
反証失敗（新規指摘なし）。探索した仮説:
- uv が無い環境で、テストを流さずに通ってしまわないか。P1-E1 では `uv がありません。…テストは流していません` を出して exit 1 になった。
- uv の環境の外で流しても、OS の python のまま流れる道が無いか。P1-E2 では uv の環境で流し直され、`python3 3.12.3`・`PyYAML 6.0.3`・`pre-commit 4.7.0` がすべて正と一致して `pass=1 fail=0`・exit 0 になった。
- 流し直しが無限に繰り返されたり、偽の環境で素通りしたりしないか。P1-E3 は `HARNESS_UV_REEXEC=1` で `VIRTUAL_ENV` が合わないと、`uv の環境に入れませんでした` を出して exit 1 になった。P1-E4 は `VIRTUAL_ENV` を `.venv` に偽装して OS の python で流しても、PyYAML 6.0.1 と pre-commit 4.5.1 が `版が違う道具` になり、テストを流さずに exit 1 になった。
- 3.12.3 に変えたことで、OS の python が正と同じ版になった。それでも PyYAML と pre-commit が正と違えば止まる（P1-E4）。python の行だけが OK になって全体が通る道は無かった。
- 差分は版の数字・`uv.lock` の wheel の行・runbook の 1 行だけで、論理の変更は無い。前回の敵対的レビューで見つかった `env:` で版を迂回する道は、`check-tools.sh` が最後に止める Low 相当で、既知の範囲として再報告しない。
- CI 側は `.github/workflows/ci.yml` の差分が無く、setup-uv に `python-version` や `version` を書く道は `ci_check` が見ている。手元での直接の実験はしていない。

> ITEM: V1 RESULT=experiment EXP=P1-E2,P1-E4
> ITEM: V2 RESULT=experiment EXP=P1-E1,P1-E2,P1-E3,P1-E4
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I211] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | tautology（名前だけ） | FG-V2 と FG-V3 は、名前（「正より新しい」「正より古い」）と実際の値（`0.0.1`・`99.0.0`）の向きが逆。`check-tools.sh:83` は完全一致だけを見るので、結果には影響しない。既知 findings と同じ内容なので、新規には数えない。 | test_i211_version_pin.sh:30-36 | 静的読解 |
| Low | FG の弱さ | V1 は、実物の python3 の版をその場で `.python-version` に書き写して比べる。そのため python が何版でも通る。`.python-version` の値そのもの（3.12.3）は K1 が形（マイナー版の一致）でしか見ていない。意図どおりの設計で、害は無い。 | test_i211_version_pin.sh:24-28 | 静的読解 |

Critical/High に当たる新規の欠陥は、本気で探したが見つからなかった（反証失敗）。

探した仮説は次のとおり。
- 版が上でも下でも、`lock` の比較が合格にならないか。`check-tools.sh:83` は完全一致だけを見る。FG-V2 と FG-V3 は終了コード 1 と `⛔ 版が違う道具` の文言の両方を確かめており、別の理由で落ちたものを合格にする経路は無い。
- 正のファイルが無いとき、または `uv.lock` に名前が無いときに合格にならないか。`want_ver` が `bad_list` で exit 2 になる。FG-V7 と FG-V6 は、終了コードと文言の両方を確かめている。
- 3.12.3 への変更が、テストを偽の合格にしないか。K1 は `.python-version` と `requires-python` のマイナー版の一致を確かめる。K2 は `uv lock --check` を実行し、FG-K2 は失敗の理由（`update`）まで見ている。`uv.lock` の差分は cp312 の wheel への差し替えだけで、整合している。
- 実験 P2-E1 は `run-all: pass=1 fail=0` で、`test_i211_version_pin.sh` 全体が変更後の HEAD で通った。grep の絞り込みが強く、項目ごとの PASS 行は出力に出ていない。この点は注意が要る。ただし、静的読解でも各項目の判定条件に false-green の経路は見つからなかった。
- V4 の `ci_check`（`test_i204_tool_sync.sh`）は今回の差分に含まれていない。install の検出の正規表現は、差分からは読めなかった。既知 findings の観点 2 の記録が、5 パターンを拾い `uv run` は拾わないことを読んで確認済みとしている。差分に変更がないので、その結論は覆らない。

> ITEM: V3 RESULT=experiment EXP=P2-E1
> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I211] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | 手順の記述の抜け | 手順表の「python（パッチ版）」の行は、`.python-version` を 3.12.3 から別のパッチ版（例: 3.12.4）へ上げる流れとして読める。runbook はこの表の直前で「OS の `python3` に合わせる」と説明している。しかし、パッチ版を上げると OS の `python3`（3.12.3）とずれる。その場合の扱いは、118 行目の「パッチ版の違いは自動では止めない」としか書いていない。手元の `check-tools.sh` は `.python-version` とぴったり比べるので、手元の uv の環境と CI は揃ったまま上がる。揃えたい対象（見張りの実体）との差が黙って開くだけで、手元と CI のずれは起きない。既知の A1（`uv lock` が要らない工程）とは別の指摘。 | docs/runbooks/onboarding.md:118,134 | 静的読解 |
| Low | 記述の古さ（既知 F7 と実質同一） | 136 行目の「例: 3.11 → 3.12」が古い。 | docs/runbooks/onboarding.md:136 | 既知 F7 と同一のため数えない |

反証失敗（新規の Critical/High なし）。V5 の手順に沿って版を上げると、手元と CI は同じ正のファイルを読む。そのため同じ版のまま上がる。

探索した仮説:
1. **PyYAML・pre-commit を上げる行（133 行目）**
   - `uv lock --upgrade-package` は `uv.lock` だけを変える。
   - 手元は `run-all.sh` の `uv run --locked` で入れ直す。
   - CI も同じ `uv.lock` を読む。
2. **python のマイナー版を 3.12 から 3.13 へ上げる行（136 行目）**
   - `.python-version` と `requires-python` を両方書き換える。
   - 片方だけだと K1 が止める。
   - `uv.lock` の wheel は `uv lock` で作り直される。今回の差分で cp311 から cp312 に変わったのと同じ形。
3. **3.12.3 固定による新しい経路**
   - 手元と CI の runner はどちらも OS の python が 3.12.3 だ。uv が `/usr/bin/python3.12` を再利用する可能性がある。
   - その場合でも `.python-version` との完全一致は保たれる。runner の OS が更新されて python が変わった場合、uv は管理下の 3.12.3 を取りに行くので、揃いは崩れない。

実験は返さない（V5 は読んで確かめる項目。上の読解で足りる）。

> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 0cba9b000273ea61e344d7044e4d35d5a79905ec
ROUNDS: 1
VERDICT: OK
