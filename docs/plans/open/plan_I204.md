# I204 計画書: ハーネスのテストが頼る道具を CI と手元で同期する

## 基本情報
- **計画書ID**: plan_I204
- **関連イシュー**: #340
- **Draft PR**: #354
- **作成根拠資料**: docs/issues/open/I204.md（起点イシュー。設計確認メモは 2026-10-28 の grill-me 2 回分）
- **実装後評価**: docs/reviews/open/I204_review.md
- **作成日**: 2026-10-28

## 1. 背景/目的
- 背景: CI（GitHub の `ubuntu-latest`）と手元（WSL）で、ハーネスのテストが頼る道具を揃える仕組みが無い。I197 では、CI にある shellcheck が手元に無く、TC-C1 が黙って SKIP して手元では合格に見え、CI で初めて落ちた
- 目的: ハーネスのテストが頼る道具と版を 1 か所の一覧で正にし、`run-all.sh` の冒頭（CI と手元で同じ）で確かめる。黙って SKIP する分岐をやめる。CI が入れる道具も一覧から読み、一覧と CI のワークフローの食い違いをテストで止める

### 調査結果
#### A. 今の食い違い（2026-10-28・手元 WSL と CI の設定）
| 道具 | 手元 | CI（Harness Tests） | 頼るテスト |
|---|---|---|---|
| python3 | 3.12.3（`/usr/bin/python3`） | 3.11（`actions/setup-python`） | ほぼ全部 |
| PyYAML | 6.0.1（apt の python3-yaml） | `pip install pyyaml`（版の指定なし） | `test_i109`・`test_i182` ほか |
| git | あり | runner に最初からある | ほぼ全部 |
| docker compose | あり | runner に最初からある | `test_compose_ports.sh` |
| pre-commit | 4.5.1（pipx） | **入れていない** | （無し。本計画で TC-C1 が使う） |
| shellcheck | **無し**（pre-commit の仮想環境の中にだけある） | runner に最初からある（ubuntu の版。`.pre-commit-config.yaml` の v0.10.0.1 とは別） | `test_review_commit_lifecycle.sh` TC-C1 |

- tmux・claude・flock・timeout など、テストの中で偽物を使うか、ハーネス本体の前提として既に使っている基本コマンド（bash・coreutils・grep・sed・awk・flock・timeout）は一覧に入れない（偽物を使う／ubuntu と WSL の基本の道具で、無ければ多数のテストが即座に落ちる＝黙って合格にならない）
- 根本原因: 道具と版の「正」が無く、CI と手元が別の出どころから道具を得ている。テストは「無ければ飛ばす」で食い違いを隠す

#### B. 「無ければ飛ばす」分岐（全件・`grep -rnE "command -v|shutil\.which|未インストール|not installed|SKIP" scripts/claude/tests/`）
| 場所 | 理由 | 扱い |
|---|---|---|
| `test_review_commit_lifecycle.sh:158-163` TC-C1 | shellcheck が無い | 直す（4.4）。今の手元で `SKIP=1` を再現した（PASS=30 FAIL=0 SKIP=1） |
| `test_compose_ports.sh:11-14` | docker compose が無い | 直す（4.5） |
| `guard_bash_oracle.py:147-149` | bash が無い | 直す（4.6） |
| `test_pretooluse_worktree_guard.sh:224` NOREG・`:296` X21 | origin/develop を取れない・別ドライブのワークツリーが無い（環境の状態） | 対象外（設計確認メモ） |
| `guard_corpus_diff.py:97-121` | 作業記録が無い（環境の状態） | 対象外（設計確認メモ） |

#### C. スパイク（2026-10-28・このセッション）
- `pre-commit run shellcheck --files <scripts/ の下のファイル>`: 合格は exit 0・`shellcheck....Passed`、違反は exit 1・`Failed`。**`scripts/` の外のファイルだけを渡すと exit 0・`(no files to check)Skipped`**（hook の `files: ^scripts/`）。→ TC-C1 は終了コードに加えて `Passed` の行を合格の条件にする（4.4）
- 未ステージの変更があっても `--files` のときは退避（stash）しない（I204.md に未ステージの変更がある状態で流し、変更が残ることを確かめた）
- 一時の git リポジトリに `.pre-commit-config.yaml` を写して流すと、手元のキャッシュ（`~/.cache/pre-commit/`）を使ってネットワーク無しで動く（`/tmp/claude-1000/-mnt-c-app-study-app-multitenant/eae01040-b592-4132-b688-b8326aa5a249/scratchpad/pc_spike.sh`）
- 固定の版の shellcheck で TC-C1 の 4 ファイルは Passed（grill-me で確認）。`test_compose_ports.sh` は手元で pass=13（SKIP しない）
#### D. ベースライン（2026-10-28・develop 843ff0a）
- `test_review_commit_lifecycle.sh` PASS=30 FAIL=0 SKIP=1・`test_compose_ports.sh` pass=13 fail=0・`test_guard_bash_oracle.sh` exit 0（cases=4560 見逃し=0 余計な停止=0）

## 2. 受け入れ条件
イシューの AC と同じ（番号を振る）。
- AC1: ハーネスのテストが頼る道具と版の一覧が 1 か所にある（`scripts/claude/tests/required-tools.txt`）
- AC2: テストの最初（`run-all.sh` の冒頭）に一覧を確かめ、足りなければ不合格にしてどれが足りないか・どう入れるかを出すことを、ハーネステストで固定している（pre-commit の shellcheck が使えない環境で TC-C1 が黙って合格にならない）
- AC3: 個々のテストに「道具が無ければ SKIP して合格」の分岐が残っていない（TC-C1・`test_compose_ports.sh`・`guard_bash_oracle.py`）
- AC4: 一覧の python は「3.11 以上」を確かめ、満たさなければ不合格にする
- AC5: shellcheck は CI と手元で `.pre-commit-config.yaml` に固定した同じ版を使う（pre-commit 経由）
- AC6: CI の Harness Tests が一覧に従っていて、一覧と CI のワークフローの食い違いを確かめるテストがある
- AC7: 既存のハーネステスト（`bash scripts/claude/tests/run-all.sh`）・CI がすべて pass する

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra（ハーネス）: 新規 `scripts/claude/tests/required-tools.txt`・新規 `scripts/claude/tests/check-tools.sh`・`scripts/claude/tests/run-all.sh`・`scripts/claude/tests/test_review_commit_lifecycle.sh`・`scripts/claude/tests/test_compose_ports.sh`・`scripts/claude/tests/guard_bash_oracle.py`・新規 `scripts/claude/tests/test_i204_tool_sync.sh`・`.github/workflows/ci.yml`（Harness Tests の 1 step だけ・`path_risk_trigger()` に当たる）・`docs/runbooks/onboarding.md`
- 依存関係ファイル（requirements*.txt・package*.json）・Dockerfile・docker-compose.yml は変えない

## 4. 変更点一覧（具体）

### 4.1 道具と版の一覧（AC1・AC4・AC5）
修正方針: 1 行 1 道具の一覧を `scripts/claude/tests/required-tools.txt` に置く。列は ` | ` で区切る 5 列。pre-commit が持つ道具（shellcheck）は版を書かず、`.pre-commit-config.yaml` を参照する。

```text
# ハーネスのテスト（scripts/claude/tests/run-all.sh）が頼る道具の一覧（I204）。CI（.github/workflows/ci.yml の Harness Tests）と手元の正。
# run-all.sh の冒頭で check-tools.sh がこの一覧を確かめ、足りなければテストを流さずに不合格にする。
# CI は「CI で pip で入れるもの」の列を check-tools.sh --pip-specs で読んで入れる。道具を足す・変えるときはこの一覧を書き換える。
# 列: 名前 | 確かめるコマンド | 版の下限（- は問わない） | CI で pip で入れるもの（- は入れない） | 入れ方（手元）
python3 | python3 --version | 3.11 | - | python 3.11 以上（CI は actions/setup-python の python-version。版をぴったり揃えるのは後続のイシュー）
PyYAML | python3 -c 'import yaml; print(yaml.__version__)' | 6.0 | PyYAML>=6.0 | sudo apt install python3-yaml
git | git --version | - | - | sudo apt install git（CI は runner に最初からある）
docker compose | docker compose version | - | - | Docker Desktop の WSL 連携を有効にする（CI は runner に最初からある）
pre-commit | pre-commit --version | 4.0 | pre-commit>=4.0 | pipx install pre-commit（docs/runbooks/pre-commit.md）
shellcheck | out=$(pre-commit run shellcheck --files scripts/claude/tests/check-tools.sh 2>&1) && grep -E '^shellcheck\.+Passed$' <<< "$out" | - | - | pre-commit 経由（版は .pre-commit-config.yaml の shellcheck-py。初回はネットワークから入る）
```
- 確かめるコマンドに `|` は書かない（列の区切りと区別できないため。check-tools.sh が列の数で止める）

### 4.2 一覧を確かめるスクリプト（AC2・AC4）
新規 `scripts/claude/tests/check-tools.sh`（`test_` で始まらないので run-all.sh はテストとして流さない）:
- 使い方: `bash scripts/claude/tests/check-tools.sh [一覧のパス]`／`bash scripts/claude/tests/check-tools.sh --pip-specs [一覧のパス]`。一覧の既定はスクリプトと同じフォルダの `required-tools.txt`。確かめるコマンドはリポジトリのルートで流す（`git rev-parse --show-toplevel`）
- 行の読み方: 空行と `#` で始まる行は飛ばす。` | ` で 5 列に分け、前後の空白を除く。次のどれかなら `⛔ 一覧の行の形が違います: <行>` を出して exit 2（その時点で止める）:
  - 列が 5 つでない・名前か確かめるコマンドが空
  - 版の下限が `-` でも `^[0-9]+(\.[0-9]+)*$` でもない
  - pip の列が `-` でも `^[A-Za-z0-9][A-Za-z0-9._-]*(>=|==)[0-9]+(\.[0-9]+)*$` でもない（`-i`・`--extra-index-url`・URL・`-e` などの pip の指定を通さない）
- 確かめ方（1 行ずつ）: `timeout 300 bash -c "<確かめるコマンド>"` の出力（stdout と stderr）と終了コードを取る
  - 0 以外 → `⛔ 足りない道具: <名前>（\`<確かめるコマンド>\` が通らない）。入れ方: <入れ方>` と、出力の最後の 5 行を字下げして出す
  - 下限があり、出力の最初の `[0-9]+(\.[0-9]+)+`（bash の `[[ =~ ]]` で取る。パイプを使わない）が無い → `⛔ 版を読めない道具: <名前>`
  - 下限があり、読んだ版が下限より古い（`sort -V` で比べる）→ `⛔ 版が古い道具: <名前> <版>（下限 <下限>）。入れ方: <入れ方>`
  - それ以外 → `OK: <名前> <版（下限が - なら出力の 1 行目）>`
- 終了コード: 全部 OK で 0、足りない・古い・読めないが 1 つでもあれば 1（全部の行を確かめてからまとめて返す）、一覧が読めない・形が違うと 2
- `--pip-specs`: 形を確かめた後、pip の列が `-` でない行の pip の列を一覧の順に 1 行ずつ出す（今の一覧なら `PyYAML>=6.0` と `pre-commit>=4.0`）。道具は確かめない

### 4.3 `run-all.sh` の冒頭で確かめる（AC2）
修正方針: `cd "$REPO_ROOT"` の直後・テストのループの前で一覧を確かめ、足りなければテストを 1 本も流さずに exit 1。
```bash
# ハーネスのテストが頼る道具を一覧（required-tools.txt）で先に確かめる（I204）。CI も手元も同じこの確認を通る
if ! bash scripts/claude/tests/check-tools.sh; then
  echo "⛔ ハーネスのテストが頼る道具がそろっていません（一覧: scripts/claude/tests/required-tools.txt）。テストは流していません"
  exit 1
fi
```
- 道具の確認は `TEST_DIR` を差し替えても同じ一覧で行う（確認を飛ばす方法を作らない）
- 冒頭のコメント（2〜4 行）に「最初に一覧の道具を確かめる」を足す

### 4.4 TC-C1 を pre-commit の固定の版にする（AC3・AC5）
`scripts/claude/tests/test_review_commit_lifecycle.sh` 158〜163 行を置き換える:
```bash
echo "== TC-C1: shellcheck（.pre-commit-config.yaml の固定の版を pre-commit 経由で使う・I204） =="
# 道具がそろっているかは run-all.sh の冒頭（check-tools.sh）で確かめる。ここで飛ばさない。
# 対象外（Skipped）でも exit 0 になるので、Passed の行まで合格の条件にする
C1_OUT="$(pre-commit run shellcheck --files "$PLAN_REVIEW" "$CODE_REVIEW" "$ISSUE_REVIEW" "$TEST_SELF" 2>&1)"; C1_RC=$?
C1_PASSED=no; grep -qE '^shellcheck\.+Passed$' <<< "$C1_OUT" && C1_PASSED=yes
ck TC-C1-shellcheck "0 yes" "$C1_RC $C1_PASSED"
[ "$C1_RC $C1_PASSED" = "0 yes" ] || printf '%s\n' "$C1_OUT" | tail -20
```
- `skip` の数え（20 行の `skip=0`・174 行の `SKIP=%d`）を消す（飛ばす項目が無くなる）

### 4.5 `test_compose_ports.sh` の SKIP をやめる（AC3）
- 11〜14 行（docker compose が無ければ `SKIP` で exit 0）を消す
- 5 行のコメントを「docker compose config は Docker デーモン不要（パース/展開のみ）。docker compose があることは run-all.sh の冒頭（check-tools.sh）で確かめる（I204）」にする
- docker compose が無いと `render_ports` が空になり D1 が不合格になる（黙って合格にならない）

### 4.6 `guard_bash_oracle.py` の SKIP をやめる（AC3）
- 147〜149 行（bash が無ければ `SKIP` で 0）を消す。`shutil` をほかで使っていなければ import も消す
- bash が無ければ、規則の確認で bash を呼ぶところが例外で落ちる（不合格）

### 4.7 CI が一覧から入れる（AC5・AC6）
`.github/workflows/ci.yml` の Harness Tests の「Install test dependencies」の step（161〜163 行）だけを置き換える:
```yaml
      - name: Install test dependencies
        # 道具は一覧（scripts/claude/tests/required-tools.txt）が正（I204）。pip で入れるものは一覧の列から読む。
        # 道具を足す・変えるときは一覧を書き換える（test_i204_tool_sync.sh が一覧とこのジョブの食い違いを止める）
        run: |
          bash scripts/claude/tests/check-tools.sh --pip-specs > "$RUNNER_TEMP/harness-requirements.txt"
          pip install -r "$RUNNER_TEMP/harness-requirements.txt"
```
- ほかの step・ジョブ・`on:`・`permissions`・`python-version` は変えない。shellcheck は pre-commit が TC-C1（と一覧の確認）の初回に `.pre-commit-config.yaml` の版を入れる
- secrets は使わない（今の Harness Tests も使っていない）

### 4.8 一覧と CI・SKIP の分岐のテスト（AC2・AC3・AC6）
新規 `scripts/claude/tests/test_i204_tool_sync.sh`（項目は auto_test の TC-01 の表）:
- 一覧の確認（L）: 実物の一覧の形・6 つの道具が載っている・実物で exit 0。写しの一覧で、通らない確かめるコマンド・古い版・読めない版・形の崩れ・pip の列の pip の指定（`--extra-index-url=…`）が、それぞれ exit 1／1／1／2／2 と決まった文言になる。`--pip-specs` の出力
- `run-all.sh` の冒頭（R）: 一時の git リポジトリに `run-all.sh`・`check-tools.sh` と写しの一覧を置き、印を書くだけのテストを `TEST_DIR` に置く。足りない道具がある一覧では exit 1・印が無い（テストを流していない）・足りない道具の名前が出る。そろった一覧では exit 0・印がある
- TC-C1（P）: 偽物の `pre-commit`（PATH の先頭）が ①exit 127 ②exit 0 で `shellcheck....(no files to check)Skipped` を出す、のどちらでも `test_review_commit_lifecycle.sh` が不合格（exit 0 以外・`FAIL TC-C1-shellcheck`）
- CI との食い違い（C。python 1 回で `ci.yml` を PyYAML で読む）: Harness Tests のジョブについて ①`python-version` が一覧の python3 の下限と同じ ②`check-tools.sh --pip-specs` の出力を `pip install -r` する step がある ③ジョブの中の `pip|pip3|pipx|apt|apt-get|brew|npm|conda` の install はその 1 つだけ・`uses:` は `actions/checkout`・`actions/setup-python` だけ ④最後の step が `bash scripts/claude/tests/run-all.sh`。写しの `ci.yml` で、`python-version` を `3.12`・`pip install foo` の step を足す・`uses: some/setup-tool@v1` を足す・一覧を読む step を前の `pip install pyyaml` に戻す、のどれも不合格
- SKIP の分岐の規則（S。python 1 回）: `scripts/claude/tests/` の `*.sh`・`*.py` で、`command -v`・`shutil.which`・`type -P` の行から 3 行以内に `SKIP` があれば、その場所を出して不合格。実物で当たり無し・見たファイルが 40 本以上。写しで、前の TC-C1・`test_compose_ports.sh`・`guard_bash_oracle.py` の形は当たり、`BASH_BIN="$(command -v bash)"`（`test_wt_lifecycle.sh` の形）・環境の状態の SKIP（NOREG の形）は当たらない
  - 粗い文字列の規則で、普通の書き方の事故を止める（意図した回避は対象外）。テストの行そのものが規則に当たらないよう、規則の文字列と写しは分けた文字列をつないで作る（除外の印を作らない＝規則に抜け道を作らない）

### 4.9 手元の準備の手順（イシューの実装対象）
`docs/runbooks/onboarding.md`:
- 「## よくある質問」の前に「## 手元の準備（ハーネスのテスト）」を足す: 道具の正は `scripts/claude/tests/required-tools.txt`。`bash scripts/claude/tests/check-tools.sh` で確かめ、`⛔` の行の「入れ方」に沿って入れる。CI も同じ一覧を使う（`run-all.sh` の冒頭で確かめる）。道具を足す・変えるときは一覧を書き換える（CI の `ci.yml` を直に書き換えると `test_i204_tool_sync.sh` が止める）
- 「CI の内容」の箇条（56〜57 行）に「- ハーネス: `scripts/claude/tests/run-all.sh`（道具は `scripts/claude/tests/required-tools.txt`）」を足す

## 5. 実装手順（ステップ）
1. 未知リスクを先に確かめる（CI の runner で pre-commit が shellcheck を入れて TC-C1 が通るか・`docker compose` があるか）: 4.1・4.2・4.3・4.4・4.7 を入れて push し、CI の Harness Tests を見る → TC-06・手動 No.1。落ちたら原因（ネットワーク・runner の道具）を計画変更記録に書いてやり直す
2. 4.8 のテストを書き、写しの不合格（FG）を確かめる → TC-01
3. 4.5・4.6（SKIP の分岐を消す）。S の規則が、消す前の実物に当たって不合格になることを先に確かめる（Red）→ TC-01 の S1・TC-03・TC-04
4. 4.9（手順の文書）
- 依存: 2 は 1 の後（一覧・check-tools.sh を使う）。3 は 2 の後（規則のテスト）。4 は並行できる

## 6. テスト計画
### 自動（docs/tests/open/I204_auto_test.md）
- テストのレベル: ハーネスの単体（`check-tools.sh` を写しの一覧で流す）・通し（一時の git リポジトリで `run-all.sh`）・偽物の `pre-commit` での TC-C1・ワークフローの YAML の照合・規則の文字列の確認。アプリのテスト（pytest・Jest・E2E）は非該当
- 再発防止: I197 の形（道具が無いと黙って合格）は、R（run-all.sh が冒頭で止まる）・P（TC-C1 が Skipped でも不合格）・S（SKIP の分岐の規則）で固定する。CI の食い違いは C で固定する
- 否定・不在の項目にはすべて失敗注入（FG）を付ける
### 手動（docs/tests/open/I204_manual_test.md）
- No.1: PR の CI の Harness Tests が pass し、ログに一覧の確認（6 行の `OK:`）と、一覧から入れた PyYAML・pre-commit が出る（AC5・AC7）
- No.2: 手元で、PATH の先頭に「通らない `docker`」を置いて `run-all.sh` を流すと、テストを流さずに `⛔ 足りない道具: docker compose` で exit 1（AC2 を実物の一覧で）
- No.3: 手元で `check-tools.sh` を流すと 6 行とも `OK:`（python3 は 3.12.3）で exit 0

## 7. ロールバック
- PR を revert する（ハーネスのスクリプト・テスト・一覧・ワークフローの 1 step・文書だけ。データの変更は無い）。revert すると CI は前の `pip install pyyaml` に戻る

## 8. Risk & 回避策
- CI の runner に `docker compose` が無くなる／GitHub の道具が変わる → `run-all.sh` の冒頭で `⛔` を出して落ちる（黙って合格にならない）。一覧の「入れ方」を書き換えて対応する
- pre-commit が shellcheck を入れるのにネットワークが要る（CI の初回・手元のキャッシュが無いとき）→ 一覧の確認で `⛔ 足りない道具: shellcheck` と入れ方（初回はネットワーク）を出す。CI は毎回ネットワークがある。キャッシュは足さない（1 回 十数秒で、`actions/cache` の追加のほうが重い）
- pre-commit が対象外で `Skipped`（exit 0）を返す → TC-C1 は `Passed` の行まで見る（P2 で固定）
- 一覧の確かめるコマンドを `bash -c` で流す → 一覧はリポジトリの中の文書で、ワークフロー・スクリプトと同じ信頼の範囲。CI の Harness Tests のジョブは secrets を使わない
- pip の列に pip の指定（別の取得元・URL）を書かれる → 形の確認で exit 2（L6b）
- PyPI から下限だけで入れる（版を固定しない）→ 今の `pip install pyyaml` と同じ。ぴったり固定は後続のイシュー（python の版と一緒に扱う）
- 道具を CI の `ci.yml` に直に足す（一覧を通さない）→ C3 で止める
- 確認が遅くなる → `check-tools.sh` は 6 つのコマンドだけ（shellcheck の確認は 1 ファイル。キャッシュがあれば 1〜2 秒）

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ・解決方針・スコープ）:
- 範囲はハーネスのテストだけ（アプリのテストは含めない）
- docker compose も一覧に入れ、無ければ不合格（SKIP をやめる）
- python は「3.11 以上」を確かめるだけ。ぴったり揃えるのは別イシュー
- 確かめるのは `run-all.sh` の冒頭の 1 か所。`ci.yml` は一覧の道具を入れる役だけ。shellcheck は pre-commit 経由で `.pre-commit-config.yaml` の版
- 環境の状態が理由の SKIP（NOREG・X21・`guard_corpus_diff.py`）は対象外
- devcontainer は採らない

Claude が決めた（技術的な選択と理由。要件・基本設計・UI/UX の仮定は無い）:
- 一覧は `scripts/claude/tests/required-tools.txt`（` | ` 区切りの 5 列）（仮定で決めた）。理由: テストと同じ場所に置く。bash だけで読め（python が無いときも「python3 が無い」と出せる）、人が読んで分かる
- 確かめ方は「確かめるコマンド」を一覧に書いて流す形（仮定で決めた）。理由: コマンド・python のパッケージ・pre-commit のフックを 1 つの書き方で扱える。種類ごとの分岐をスクリプトに増やさない
- 確かめるスクリプトは `run-all.sh` から分けた `check-tools.sh`（仮定で決めた）。理由: 手元で単独で流せる（onboarding の手順）・写しの一覧で単体のテストができる・CI が `--pip-specs` で同じ一覧を読める
- CI は `--pip-specs` の出力を `pip install -r` する（仮定で決めた）。理由: CI が入れるものを一覧から読むので、一覧を書き換えれば CI が追従する（解決方針 d）。食い違いのテスト（C）は「一覧を読む step がある・ほかの install が無い」で固定する
- PyYAML・pre-commit も python と同じく下限だけを書く（仮定で決めた）。理由: 手元の PyYAML は apt の python3-yaml（Ubuntu の python は pip で直に入れられない）で、版の固定には仮想環境が要る。版をぴったり揃えるのは後続のイシューで python と一緒に扱う（起票コマンドに PyYAML・pre-commit も含める）。下限は手元の版（6.0.1・4.5.1）の系列
- 一覧に入れない基本コマンド（bash・coreutils・grep・sed・awk・flock・timeout）（仮定で決めた）。理由: 調査結果 A。無ければ多数のテストが即座に落ち、黙って合格にならない
- shellcheck の確認は、一覧で実際に 1 ファイルを流す（仮定で決めた）。理由: 設定に hook があるだけでは、ネットワーク・キャッシュで入らない環境を見逃す。早い段階で「shellcheck が足りない」と出す
- pre-commit のキャッシュ（`actions/cache`）は足さない（仮定で決めた）。理由: 8
- TC-C1 は `Passed` の行まで合格の条件にする（仮定で決めた）。理由: 調査結果 C（対象外は exit 0）
- SKIP の分岐の規則は「道具を探す行から 3 行以内の SKIP」（仮定で決めた）。理由: 今の 3 か所はどれも 1〜3 行以内。粗い規則でよい（普通の書き方の事故を止める）。除外の印は作らない
- 一覧 の該当なし（`docs/reviews/backlog/` に実装対象のファイル・`FILE=-` の行は無い）

要件適合性: 受け入れ条件の範囲を超えた仕様の追加は無い（`guard_bash_oracle.py` は AC3 の「SKIP の分岐が残っていない」を全件で調べて当たった同じ形）。マルチテナント・ステータス遷移は非該当

セキュリティ・ベストプラクティス:
- アプリのコード・認証認可・個人情報は変えない（bandit・npm audit の対象の変更なし）
- ワークフローの変更（`docs/runbooks/review-rules.md`「GitHub から復旧できない変更のレビュー観点」）: 変えるのは Harness Tests の 1 step だけ。`on:`・`permissions`（最上位 `contents: read`）・`pull_request_target`・secrets の参照・pre-commit の `SKIP` は変えない・足さない
- 入力の扱い: pip の列は「名前＋`>=`/`==`＋版」の形だけを通す（pip の取得元の指定・URL を入れられない）。版の下限は数字と `.` だけ
- 依存の追加: CI の Harness Tests に pre-commit（PyPI）が増える。pre-commit が入れる shellcheck-py は `.pre-commit-config.yaml` の固定の rev（手元の pre-commit と同じ）。依存の脆弱性の監査（`docs/runbooks/dependency-audit.md`）の対象の requirements は変えない。pre-commit・PyYAML は監査の対象に足さない — CI のテストの道具で、アプリ（backend・frontend のイメージ）に入らず、Harness Tests のジョブは secrets を持たない。手元では前から使っている道具（pre-commit は pipx・PyYAML は apt）で、CI に入れる版も PyPI の最新（下限以上）になる。版をぴったり固定する後続のイシューで、監査に入れるかを一緒に決める

P3/P5/P8 影響なし（DB・外部 API・非同期処理・新しいインフラの追加なし。依存関係ファイルの変更なし。CI に pip の 1 パッケージが増えるだけ）。P6 影響なし（UI・データ量の懸念なし）。P9 影響なし（個人情報・未成年データ・テナントデータを扱わない）

設計品質: 道具と版の正は一覧の 1 か所（shellcheck の版は `.pre-commit-config.yaml` の 1 か所）。CI の python-version は一覧の下限と同じであることを C1 で固定する（後続のイシューで版を揃えるときは両方を同時に直す）

Danger Ops（有無/手順/ロールバック）:
- 無（データ削除・破壊的変更・強制 push は無い）。ワークフローの変更は高リスクの例外ファイル（`path_risk_trigger()` に当たる）として、必ず確かめる項目に入れる

高リスク判定: `.github/workflows/ci.yml` を変えるので、パスの判定で Yes になる見立て（判定は plan-review）

## 必ず確かめる項目
（高リスク判定が Yes になったときに敵対的レビューが使う。No なら使わない）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | `ci.yml` の差分は Harness Tests の「Install test dependencies」の step だけで、`on:`・`permissions`・secrets の参照・`pull_request_target`・ほかのジョブは変わっていない |
| V2 | 1 | 実験必須 | pip の列に `--extra-index-url=…`・URL・`-e …` を書いた一覧では `check-tools.sh --pip-specs` が exit 2 で何も出さない（CI の pip に別の取得元を渡せない） |
| V3 | 2 | 実験必須 | 確かめるコマンドが通らない行がある一覧では、`run-all.sh` がテストを 1 本も流さずに exit 1 になる（`TEST_DIR` を変えても同じ） |
| V4 | 2 | 実験必須 | pre-commit が使えない・`Skipped` を返すとき、TC-C1 が不合格になる（黙って合格にならない） |
| V5 | 3 | 実験必須 | `ci.yml` の Harness Tests に一覧を通らない install・新しい `uses:` を足した写し、`python-version` を一覧の下限と変えた写しで、食い違いのテストが不合格になる |

## 計画変更記録
（実装中に計画と違うことをするときに書く）
- 1（計画レビュー 20261028_1616 の Warning・Info 対応・2026-10-28）: Warning 1 は 4.1 の shellcheck の行の確かめるコマンドを、`Passed` の行まで見る形（`out=$(…) && grep -E '^shellcheck\.+Passed$' <<< "$out"`。`|` を使わない）にした。Warning 2 は 9「依存の追加」に監査の対象に足さない理由を書いた。Warning 3 は対応不要（ステップ 1 に前倒し済み）。Info 1: `timeout 300` は 1 行の上限で、CI のジョブの `timeout-minutes: 30` の中に収まる（6 行がすべて上限まで待っても 30 分）。Info 2: TC-02 の期待値を `PASS=31 FAIL=0` の形にした。方式・範囲・受け入れ条件は変えないので再レビューはしない

## レビュー結果
- [20261028_1616 判定: ✅ 完了](../../reviews/I204_plan_review_20261028_1616.md)

## セキュリティレビュー結果

**実施日**: 2026-10-28

バックエンド・フロントエンドのコード変更なし（ハーネスのスクリプト・テスト・一覧・`.github/workflows/ci.yml` の Harness Tests の 1 step・文書だけ）。`ci.yml` は `on: push/pull_request`（`pull_request_target` なし）・最上位 `permissions: contents: read`・`secrets.` の参照なし（変更前に確認）。

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Low | 依存ライブラリ | CI の Harness Tests が `pre-commit>=4.0`・`PyYAML>=6.0` を PyPI から下限だけで入れ、pre-commit は `.pre-commit-config.yaml` の rev（タグ `v0.10.0.1`。書き換えうる）で shellcheck-py を取得する。取得元が乗っ取られると CI のジョブの中で任意のコードが動く | 禁止: Harness Tests のジョブに secrets・`permissions` の拡大・`pull_request_target` を足さない（V1）。ジョブの持つ権限は `contents: read` の GITHUB_TOKEN だけで、今の `pip install pyyaml`（版の指定なし）と同じ水準。版の固定は後続のイシュー |
| Low | 入力検証 | 一覧の pip の列が `pip install -r` に渡るので、`--extra-index-url`・URL・`-e` を書くと別の取得元から入れられる | 必須: pip の列は `^[A-Za-z0-9][A-Za-z0-9._-]*(>=\|==)[0-9]+(\.[0-9]+)*$` だけを通し、外れたら exit 2・出力なし（4.2・FG-L6b・V2） |
| Low | 入力検証 | 一覧の「確かめるコマンド」を `bash -c` で流す（任意のコマンドを書ける） | 一覧はリポジトリの中の文書で、スクリプト・ワークフローと同じ信頼の範囲（PR で書き換えられるのはスクリプトも同じ）。外部の入力からは読まない。`timeout 300` で止まらない実行を切る |
| Low | 機密情報 | 確かめるコマンドが通らないとき出力の最後の 5 行をログに出す | 一覧のコマンドは道具の版を出すだけで、秘密を読まない。ジョブに secrets が無い |
| なし | 認証・認可／マルチテナント／OWASP Top 10／ファイル操作 | アプリの変更が無い | なし |
| なし | 外部通信 | 上の依存ライブラリの取得（PyPI・GitHub）以外の通信は足さない | なし |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | 一覧の pip の列（PR で書き換え） | PR を出せる人 | `--extra-index-url=<攻撃者のサーバ>` を書いて CI の pip に別の取得元を使わせる | `--pip-specs` が exit 2 で何も出さず、CI の step が失敗する | Yes: FG-L6b | No | ワークフローそのものを書き換える PR は同じことができる（レビューで見る・V1） | Low |
| 2 | Harness Tests のジョブ | PR を出せる人 | ジョブで動くコードから secrets・書き込みの権限を得る | ジョブに secrets が無く、`permissions` は `contents: read` のまま | Yes: C1〜FG-C5（install と `uses:` の追加を止める） | Yes: review-gate で差分が 1 step だけかを読む（V1） | なし | Low |
| 3 | 道具の確認を飛ばす | 手元の作業者（事故） | `TEST_DIR` を差し替える・テストを個別に流して、道具が無いまま合格に見せる | `run-all.sh` は `TEST_DIR` によらず一覧を確かめる。個々のテストは道具が無ければ不合格（SKIP しない） | Yes: FG-R1・FG-P1・FG-P2・S1・FG-S2 | No | 意図した回避（一覧の行を消す等）は対象外（普通の書き方の事故を止める） | Low |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 0件 | 0件 |
| Medium  | 0件 | 0件 |
| Low     | 4件 | 3件 |

### 残余リスク処遇
（retro 段階で決定する）
