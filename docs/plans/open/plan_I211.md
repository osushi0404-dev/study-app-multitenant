# I211 計画書: ハーネスのテストの python・PyYAML・pre-commit の版を CI と手元でぴったり揃え、版を上げた後も揃ったままにする

## 基本情報
- **計画書ID**: plan_I211
- **関連イシュー**: #356
- **Draft PR**: #357
- **作成根拠資料**: docs/issues/open/I211.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I211_review.md
- **作成日**: 2026-10-28

## 1. 背景/目的
- I204 でハーネスのテストが頼る道具を一覧（`scripts/claude/tests/required-tools.txt`）にまとめたが、確かめるのは「下限」だけ。手元は python 3.12.3・PyYAML 6.0.1（apt）・pre-commit 4.5.1（pipx）、CI は python 3.11.17（`actions/setup-python` の `'3.11'`）・PyYAML 6.0.3・pre-commit 4.7.0（その日の最新）で、どれも食い違っている（I204 の手動テスト No.1・No.3 の記録）。
- 目的: (1) 3 つの道具の版を手元と CI で同じ 1 つに揃える。(2) 版を上げても揃ったままにする。上げる流れは「版を書いた場所を書き換える → 手元で流す → push すると CI が同じ版で流れる」。片方だけずれたら機械的に止まる。

### 調査結果
- **原因の概要**: 版を「ぴったり」書く場所が無く、CI は「下限以上の最新」を、手元は OS や pipx で入った版を使っているため、同じ版を見ていない。
- **詳細**:
  - CI: `.github/workflows/ci.yml:158-166`。`actions/setup-python` の `python-version: '3.11'`（その時点の 3.11 の最新パッチ）→ `check-tools.sh --pip-specs`（`PyYAML>=6.0`・`pre-commit>=4.0`）を `pip install -r`。
  - 手元: `python3` は Ubuntu の OS の python（3.12.3）。PyYAML は `sudo apt install python3-yaml`、pre-commit は `pipx install pre-commit`（`required-tools.txt:6-10`）。
  - `check-tools.sh:67` は `sort -V -C` で下限だけを比べる。
- **環境前提の確認（2026-10-28）**: 手元に uv は無い（`command -v uv` 無し）。pipx 1 個あり（`/usr/bin/pipx`）。pyenv 無し。`.python-version` 無し。`.gitignore:9` に `.venv` あり。uv の最新は 0.13.6、`astral-sh/setup-uv` の最新は v10.3.2（`gh api` で確認）。
- **スパイク（成立）**: `pipx run uv`（一時の環境。手元には入れていない）で scratchpad に最小のプロジェクト（`pyproject.toml`・`.python-version`=`3.11.18`・`[tool.uv] required-version = "==0.13.6"`・`package = false`）を作って確かめた。
  1. `uv lock` → python 3.11.18 を取ってきて 12 個を解決（成立）
  2. リポジトリのルートで `uv run --locked --project <そのフォルダ> bash scripts/claude/tests/check-tools.sh` → 作業場所はリポジトリのルートのまま。`python3 3.11.18`・`PyYAML 6.0.3`・`pre-commit 4.7.0`。そのほかの道具も OK（成立）
  3. `required-version` を `==0.13.5` にする → `error: Required uv version ==0.13.5 does not match the running version 0.13.6`・exit 2（uv の版のずれを uv 自身が止める。成立）
  4. `pyproject.toml` に依存を足してロックファイルとずらす → `uv run --locked` が `The lockfile at uv.lock needs to be updated`・exit 1（成立）
  5. `.python-version` を `3.11.17` にする → uv は `Python 3.11.17` を探しに行く（作業場所ではなく `--project` のフォルダの `.python-version` を読む。成立）
  6. `uv run` の中では `VIRTUAL_ENV=<そのフォルダ>/.venv`・`python3`・`pre-commit` はそのフォルダの `.venv/bin` のもの（成立）
  7. `detect-secrets==1.5.0 scan uv.lock` → `results: {}`（ロックファイルのハッシュ値は誤検出されない。成立）
  8. setup-uv v10.3.2 の `action.yml`: `version-file`（pyproject.toml の `required-version` を読む）・`python-version`（UV_PYTHON を上書き）の入力がある（成立）
- **ベースライン**: I204 の CI（run 40652000911）で Harness Tests は `run-all: pass=47 fail=0`。手元の `check-tools.sh` は 6 行 OK（上の版で）。

## 2. 受け入れ条件
イシューの AC を、uv を使う形に読み替えた対応（読み替えの理由は 9 の D1）:
- [ ] AC1: python は 3.11（CI・アプリと同じ）の 1 つのパッチ版に揃い、手元は `bash scripts/claude/tests/run-all.sh` の 1 コマンドで、uv が python 3.11 と PyYAML・pre-commit を決めた版で作り直してから流す（OS の python は入れ替えない）
- [ ] AC2: 版を書く場所が道具ごとに 1 か所で、CI と手元の両方がそこを読む。python は `scripts/claude/tests/.python-version`、PyYAML・pre-commit は `scripts/claude/tests/uv.lock`、uv 自身は `scripts/claude/tests/pyproject.toml` の `required-version`
- [ ] AC3: `check-tools.sh` を uv の環境で流すと、3 つの道具が `.python-version`・`uv.lock` の版とぴったり一致して OK。CI の Harness Tests も同じ版で緑
- [ ] AC4: 版が違う（上でも下でも）と `check-tools.sh` が止まり、入れ方（`bash scripts/claude/tests/run-all.sh` で流す）を示す
- [ ] AC5: CI が版の正を読まない形にずれると `test_i204_tool_sync.sh` が止まる（CI だけ上げた＝setup-uv に `python-version`・`version` を書く／setup-python を足す／install を足す。正だけ上げた＝`pyproject.toml` と `uv.lock` のずれは `uv run --locked` と `uv lock --check` が止める）
- [ ] AC6: 版を上げる手順（書き換える場所 → 手元で流す → push）が runbook（`docs/runbooks/onboarding.md`）に書かれている
- [ ] AC7: `ci_check` が `apt-get -y install`・`npm i` などオプションを挟む・短縮形の install も拾う
- [ ] AC8: `check-tools.sh` で通らないコマンドの出力が空のとき、字下げの空行が出ない

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `.github/workflows/ci.yml`（harness-tests ジョブだけ）。手元の開発環境（pipx で uv 0.13.6 を入れる。各ワークツリーの `scripts/claude/tests/.venv` を uv が初回に作る）。`.github/dependabot.yml`・ほかの CI ジョブ（backend・frontend・lint・dependency-audit）は変えない
- 依存関係ファイル: `backend/requirements*.txt`・`frontend/package*.json` は変えない（Dockerfile・docker-compose.yml への波及なし）。新しく `scripts/claude/tests/pyproject.toml`・`uv.lock` を足す（ハーネスのテスト専用。アプリのイメージには入らない）

## 4. 変更点一覧（具体）

### 修正アプローチ
uv の「プロジェクト」をハーネスのテスト専用に `scripts/claude/tests/` に置き、版の正を uv の公式のファイル（`.python-version`・`uv.lock`・`pyproject.toml` の `required-version`）にする。手元も CI も `bash scripts/claude/tests/run-all.sh` という同じ入口で流し、`run-all.sh` が uv の環境の外で呼ばれたら `uv run --locked` で自分を流し直す。CI は setup-uv が同じ `pyproject.toml` から uv の版を読み、python は uv が `.python-version` から入れる。`check-tools.sh` は「下限」をやめ、正のファイルとのぴったり一致を確かめる。

### 4-1. 新規: `scripts/claude/tests/pyproject.toml`
修正方針: ハーネスのテストが頼る python の道具と uv の版を、uv の公式の形で書く。
```toml
# ハーネスのテスト（scripts/claude/tests/run-all.sh）の python の道具の版の正（I211）。
# 版を上げる手順: docs/runbooks/onboarding.md「手元の準備（ハーネスのテスト）」
[project]
name = "harness-tests"
version = "0"
requires-python = "==3.11.*"
dependencies = ["PyYAML>=6.0", "pre-commit>=4.0"]

[tool.uv]
package = false
required-version = "==0.13.6"
```
- ぴったりの版は `uv.lock` が持つ（`dependencies` は範囲。上げるときは `uv lock --upgrade-package <名前>`）

### 4-2. 新規: `scripts/claude/tests/.python-version`
- 中身は `3.11.18` の 1 行（uv で取れる 3.11 の最新。CI の setup-python が今入れる 3.11.17 とも違うので、ここで 1 つに決める）

### 4-3. 新規: `scripts/claude/tests/uv.lock`
- `uv lock --project scripts/claude/tests` が作る（手で書かない）。今日の解決では PyYAML 6.0.3・pre-commit 4.7.0（実装時に lock が決めた版を計画変更記録に書く）

### 4-4. `scripts/claude/tests/run-all.sh`
修正方針: (a) uv の環境の外で呼ばれたら、uv の環境で自分を流し直す。(b) 引数でテストのファイルを渡せば、それだけを流す（手元で一部のテストを流すときも同じ版の環境で流すため。決定論ゲートもこの形で書く）。
```bash
PROJ="scripts/claude/tests"
# uv の環境（scripts/claude/tests/.venv）の外なら、uv で版をそろえてから流し直す（I211）
if [ -f "$PROJ/pyproject.toml" ] && [ "${VIRTUAL_ENV:-}" != "$REPO_ROOT/$PROJ/.venv" ]; then
  if [ -n "${HARNESS_UV_REEXEC:-}" ]; then
    echo "⛔ uv で流し直しても uv の環境に入れませんでした（VIRTUAL_ENV=${VIRTUAL_ENV:-}）"; exit 1
  fi
  if ! command -v uv >/dev/null 2>&1; then
    echo "⛔ uv がありません。入れ方: docs/runbooks/onboarding.md「手元の準備（ハーネスのテスト）」。テストは流していません"; exit 1
  fi
  HARNESS_UV_REEXEC=1 exec uv run --locked --project "$PROJ" bash "$PROJ/run-all.sh" "$@"
fi
```
- 引数があるときは `for t in "$@"`、無いときは今までどおり `"$TEST_DIR"/test_*.sh`。引数のファイルが無ければ `⛔` で exit 1
- `REPO_ROOT` は `git rev-parse --show-toplevel` の値を `cd … && pwd -P` でそろえて比べる（WSL のパスの表記ゆれで流し直しが止まらなくなるのを防ぐ）
- `pyproject.toml` が無いリポジトリ（テストの一時のリポジトリ）では流し直さない

### 4-5. `scripts/claude/tests/check-tools.sh`
修正方針: 一覧の列を 4 つにし（CI で pip で入れるものの列と `--pip-specs` を消す。CI は pip を使わなくなる）、版の列は `-`（問わない）か `lock`（正のファイルとぴったり一致）だけにする。
- `lock` の正: 名前が `python3` なら一覧と同じフォルダの `.python-version` の 1 行目、それ以外は同じフォルダの `uv.lock` の `[[package]]` のうち `name` が名前を小文字にしたものの `version`（awk で読む。python の版によらない）
- 正が読めない（ファイルが無い・名前が無い）→ `⛔ 版の正が読めません` で exit 2（一覧・設定の誤り）
- 版が違う → `⛔ 版が違う道具: <名前> <今の版>（正 <正の版>・<正のファイル>）。入れ方: <入れ方>` で exit 1
- 一致 → `OK: <名前> <版>（正 <正のファイル>）`
- 通らないコマンドの出力が空なら字下げの行を出さない（`[ -n "$out" ] &&`）
- 冒頭のコメントの呼び出し元・使い方・終了コードを書き換える

### 4-6. `scripts/claude/tests/required-tools.txt`
```
# 列: 名前 | 確かめるコマンド | 版（- は問わない・lock は .python-version / uv.lock とぴったり） | 入れ方（手元）
python3 | python3 --version | lock | bash scripts/claude/tests/run-all.sh で流す（uv が .python-version の python を入れる）
PyYAML | python3 -c 'import yaml; print(yaml.__version__)' | lock | bash scripts/claude/tests/run-all.sh で流す（uv が uv.lock の版を入れる）
uv | uv --version | - | pipx install uv==<pyproject.toml の required-version>（docs/runbooks/onboarding.md）
git | （今のまま）
docker compose | （今のまま）
pre-commit | pre-commit --version | lock | bash scripts/claude/tests/run-all.sh で流す（uv が uv.lock の版を入れる）
shellcheck | （今のまま）
```
- 冒頭のコメント（正・CI の読み方）を書き換える。uv の版は `required-version` を uv 自身が確かめるので `-`

### 4-7. `.github/workflows/ci.yml`（harness-tests ジョブだけ）
```yaml
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v10
        with:
          # uv の版は pyproject.toml の required-version、python は .python-version、道具は uv.lock が正（I211）。
          # ここに python-version・version を書かない・install を足さない（test_i204_tool_sync.sh が止める）
          version-file: scripts/claude/tests/pyproject.toml
      - name: Configure git identity for temporary test repositories
        run: （今のまま）
      - name: Run harness tests
        run: bash scripts/claude/tests/run-all.sh
```
- `actions/setup-python` と「Install test dependencies」の step を消す（`run-all.sh` が `uv run --locked` で入れる）

### 4-8. `scripts/claude/tests/test_i204_tool_sync.sh`
- L: 一覧の列を 4 つに。L1 の道具は 7 つ（uv を足す）。L4（下限）・L6b・L7（`--pip-specs`）を消し、L5 は `lock` の行で版を読めない場合に書き換える。L6a は列が 3 つの行・版の列が `3.11` の行で exit 2
- `names()` は前後の空白を除いてから `#` を見る（一覧 I204 F5）。字下げしたコメントの写しで確かめる項目を足す
- R: 写しの一覧を 4 列に
- C: `ci_check` を書き換える。uses は `actions/checkout`・`astral-sh/setup-uv` だけ／setup-uv がちょうど 1 つで `with` は `version-file: scripts/claude/tests/pyproject.toml` だけ（`python-version`・`version` を書かない）／install は 0 個／最後の step は `bash scripts/claude/tests/run-all.sh`。install の検出は `(pip3?|pipx|uv|apt-get|apt|brew|npm|pnpm|yarn|conda)` の後に、オプション（`-` で始まる語）と `pip`・`tool` の語を挟んで `install|i|ci|add|sync` が来る形（一覧 I204 F3・敵対的レビューの Medium）
- 写しの `ci.yml` の種類: setup-uv に `python-version: '3.12'`／`version: 0.9.0`／`version-file` を消す／`actions/setup-python` を足す／`some/setup-tool@v1` を足す／`run:` に `pip install foo`・`sudo apt-get -y install foo`・`npm i foo`・`uv pip install foo`・`python -m pip install foo`・`uv sync` を足す（それぞれ不合格）

### 4-9. 新規: `scripts/claude/tests/test_i211_version_pin.sh`
- V（ぴったりの確かめ）・X（`run-all.sh` の流し直しと引数）・K（実物の版の正の形）の項目。中身は `docs/tests/open/I211_auto_test.md` の TC-01 の表

### 4-10. `docs/runbooks/onboarding.md`「手元の準備（ハーネスのテスト）」
- 初回: `pipx install uv==0.13.6`（版は `scripts/claude/tests/pyproject.toml` の `required-version`）→ `bash scripts/claude/tests/run-all.sh`（初回は uv が python と道具を入れる）
- 一部だけ流す: `bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_xxx.sh`
- 版を上げる手順（道具ごと）:
  - PyYAML・pre-commit: `uv lock --project scripts/claude/tests --upgrade-package <名前>` → `bash scripts/claude/tests/run-all.sh`（uv が手元を入れ直して流す）→ commit・push（CI が同じ `uv.lock` で流す）
  - python: `scripts/claude/tests/.python-version`（と、マイナー版を変えるなら `requires-python`）を書き換え → `uv lock --project scripts/claude/tests` → 手元で流す → push
  - uv: `required-version` を書き換え → `pipx install --force uv==<新しい版>` → 手元で流す → push（CI の setup-uv は同じ行を読む）
- 片方だけずれたときに止まる場所（uv の `required-version`・`--locked`、`check-tools.sh`、`test_i204_tool_sync.sh`）を 1 行ずつ

### 4-11. `docs/reviews/backlog/I204.md`
- F2・F3・F5 の行を消す（同梱して直した）。F1・F4 は残す

## 5. 実装手順（ステップ）
1. **手元に uv を入れ、版の正のファイルを作る**（未知リスク先行: 実物のリポジトリで uv の環境が作れるか）: `pipx install uv==0.13.6`（9 の D3）。4-1・4-2 を書き、`uv lock --project scripts/claude/tests` で 4-3 を作る → TC-05 参照
2. **入口と確かめ（テストを先に）**: 4-9 の新しいテストと 4-8 の書き換えを先に書き、今の実装で不合格になることを見る（Red）→ 4-4・4-5・4-6 を直す → TC-01・TC-02 参照（ステップ 1 が前提）
3. **CI**: 4-7 を直して push し、runner でも同じ版になるかを見る（ステップ 2 が前提。C の項目が実物の `ci.yml` で合格になるのはこのステップの後）→ TC-06・手動 No.1 参照
4. **runbook と一覧**: 4-10・4-11（ステップ 3 と並行してよい）
5. 影響を受ける既存のテストを流す → TC-03・TC-04 参照

## 6. テスト計画
### 自動
- テストレベル: シェルの決定論テスト（写しの一覧・写しの `ci.yml`・偽物の `uv` で失敗を注入する）。アプリの pytest・Jest・E2E は非該当
- 新規 `test_i211_version_pin.sh`（TC-01）、書き換え `test_i204_tool_sync.sh`（TC-02）、影響の確認 `test_i193_official_flow.sh`（TC-03・F9 が `run-all.sh` を流す）・`test_review_commit_lifecycle.sh`（TC-04・pre-commit を使う）、ロックの確認（TC-05）、CI（TC-06）
- 決定論ゲートは `bash scripts/claude/tests/run-all.sh <テスト>` の形で書き、uv の環境で流す
### 手動（実施者はすべて Claude）
- CI のログで版を読む／手元の `run-all.sh` の流し直しの版が CI と同じ／uv の環境の外で `check-tools.sh` が止まる／版を上げる手順の通し（scratchpad の写しで）

## 7. ロールバック
- PR を revert する（ファイルの追加・書き換えだけ。DB・データの変更なし）。手元の uv は `pipx uninstall uv`、各ワークツリーの `scripts/claude/tests/.venv` は消してよい（`.gitignore` 済み）

## 8. Risk & 回避策
- R1: CI の runner で setup-uv が `required-version` を読まない・python を取れない → ステップ 3 で push して確かめ、ダメなら計画を直す（手動 No.1）
- R2: `run-all.sh` の流し直しが終わらない（`VIRTUAL_ENV` の表記ゆれ）→ `HARNESS_UV_REEXEC` で 2 回目の流し直しを止めて `⛔`（TC-01 X4）
- R3: テストのファイルを直に `bash scripts/claude/tests/test_xxx.sh` で流すと OS の python のまま → runbook に「`run-all.sh <テスト>` で流す」と書き、決定論ゲートもその形にする。直に流す呼び出しを全部なくすのは I201（変えたファイルから流すテストを選ぶ）で扱う（9 の D6）
- R4: lint ジョブの `pre-commit/action` と git の pre-commit フック（pipx の pre-commit 4.5.1）はこの版の正を読まない → 範囲外（ハーネスのテストだけ。9 の D5）
- R5: uv の環境を作るのにネットワークが要る（初回・版を上げたとき）→ pre-commit の shellcheck も同じ前提（I204）。キャッシュがあれば 2 回目からは要らない
- R6: `/mnt/c` 上の `.venv` の作成が遅い → スパイクでは 11 個で 12ms（キャッシュからの複製）。問題なし

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 版は 3.11 に揃える（手元を CI・アプリに合わせる）
- 手元は uv で python 3.11 と PyYAML・pre-commit を固定した版で入れる。OS の python は入れ替えない。公式の `astral-sh/setup-uv` を使う
- 範囲はハーネスのテストだけ。アプリの python の版上げは別イシュー
- Dependabot は別イシュー（`.github/dependabot.yml` は変えない）

Claude が決めた（技術的な選択と理由）:
- D1: 版の正を「一覧の列」ではなく uv の公式のファイル（`.python-version`・`uv.lock`・`required-version`）にする。理由: 公式の仕組みがずれを止めてくれる（スパイク 3・4）。一覧の列に書くと、CI に渡すために自作の読み出しが要り、Dependabot（後続）も読めない。AC の「1 か所」は道具ごとに 1 か所と読む（python・道具・uv の 3 つのファイルは同じフォルダに並ぶ）。I204 の「一覧が正」は「どの道具をどう確かめるか」の正として残し、「CI は一覧を通して揃える」は「CI は版の正のファイルだけを読み、install を書かない」に置き換える（イシューの制約の形を変えるが、狙い〔CI と手元が同じ正を読む・install が 1 つの経路だけ〕は同じ）
- D2: 入口は今までどおり `bash scripts/claude/tests/run-all.sh` にし、`run-all.sh` が uv の環境の外なら `uv run --locked` で自分を流し直す。理由: CI・手元・test-gate・許可ルール（`Bash(bash scripts/claude/*)`）がそのまま使え、版の違う python で全体を流す道が無くなる。`uv run` を CI と手元に直に書く案は、許可ルールの追加（安全装置の変更）が要り、呼び出しの書き忘れでずれる
- D3: 手元の uv は Claude が実装のステップ 1 で `pipx install uv==0.13.6` で入れる。理由: pipx はこのリポジトリで pre-commit を入れる方法（`docs/runbooks/pre-commit.md`）と同じで、uv の公式の入れ方の 1 つ。版を指定して入れられ、`pipx uninstall uv` で戻せる。ユーザーの作業を減らせる（設計確認メモの「ユーザーが 1 回入れる」より手間が少ない側。入れ方の手順は runbook に残す）
- D4: python は 3.11 の最新パッチ 3.11.18 に固定する（CI の setup-python が今入れる 3.11.17 とも違う）。`requires-python = "==3.11.*"` で uv がマイナー版のずれも止める
- D5: lint ジョブの `pre-commit/action`・git の pre-commit フック・ほかの CI ジョブの python は範囲外（イシューの「含む」はハーネスのテストだけ）
- D6: `run-all.sh` に「引数で渡したテストだけ流す」を足す。理由: 手元で一部のテストを流すときも同じ版の環境に入るため（AC1・AC3 の「手元で通れば CI でも通る」を一部のテストにも効かせる）。決定論ゲートもこの形で書く。変えたファイルから選ぶ仕組みは I201 の範囲
- D7: `check-tools.sh` の「下限」の比較は消す（使う行が無くなる。必要になったら足す）
- 一覧 docs/reviews/backlog/I204.md F1: 残す — shellcheck の確かめ方の話で版揃えと関係しない
- 一覧 docs/reviews/backlog/I204.md F2: 同梱 — 入れ方の列を uv に変えるので apt のヒントが無くなる
- 一覧 docs/reviews/backlog/I204.md F3: 同梱 — `ci_check` を書き換え、setup-uv を必須・setup-python を禁止にするので、step が消えたときに検査が働かない穴が無くなる
- 一覧 docs/reviews/backlog/I204.md F4: 残す — S3 のテスト名と中身の話で版揃えと関係しない
- 一覧 docs/reviews/backlog/I204.md F5: 同梱 — `names()` を触るので一緒に直す
- 要件適合性: AC の範囲を超える仕様追加は D6（一部のテストを流す引数）だけで、AC1・AC3 を一部のテストにも効かせるための最小の追加。マルチテナント・ステータス遷移は非該当
- セキュリティ: セキュリティ影響なし（アプリのコード変更なし）。CI に足す第三者の action は Astral の公式 `astral-sh/setup-uv@v10`（`uses` の許可は `test_i204_tool_sync.sh` が 2 つに固定）。uv が入れる python は uv の公式の配布物（python-build-standalone）、道具は PyPI のものを `uv.lock` のハッシュ付きで入れる（今の `pip install` は版もハッシュも固定していないので、取り込みの安全性は上がる）。`uv.lock` は detect-secrets に誤検出されない（スパイク 7）。bandit・npm audit の対象の変更なし。追加する依存（PyYAML・pre-commit）は今も入れているもので新しくない
- P3/P5/P8 影響なし（DB 変更・外部 API・非同期処理なし。新しいインフラ・費用なし〔uv・setup-uv は無料〕）
- P6 影響なし（UI なし）
- P9 影響なし（個人情報・テナントデータを扱わない）
- 設計品質: 設定値（版）は正のファイルに置き、スクリプトに版の数字を書かない（runbook の `pipx install uv==0.13.6` は例として `required-version` を参照する書き方にする）。エラーは `⛔` と終了コード（1=道具が合わない、2=一覧・設定の誤り）で、今の `check-tools.sh` の決まりを踏襲
- 要件・基本設計・UI/UX の価値判断に当たる仮定: なし（すべて技術的な選択）

Danger Ops（有無/手順/ロールバック）:
- 無（`.github/workflows/ci.yml` の変更は PR の CI で確かめ、マージはユーザー。データの変更なし）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | CI の harness-tests で、python・PyYAML・pre-commit の版が `.python-version`・`uv.lock` 以外から決まる道が無い（setup-uv に `python-version`・`version` を書く／setup-python・install を足すと TC-02 の C が落ちる。手動 No.1 で runner の版が正と一致） |
| V2 | 1 | 実験必須 | `bash scripts/claude/tests/run-all.sh` を uv の環境の外で流すと必ず uv の環境で流し直され、uv が無ければテストを流さずに exit 1（TC-01 の X1〜X4） |
| V3 | 2 | 実験必須 | `check-tools.sh` の `lock` の比較が、版が上でも下でも、正のファイルが無くても合格にしない（TC-01 の FG-V2〜FG-V7） |
| V4 | 2 | 読んで可 | `ci_check` の install の検出が `apt-get -y install`・`npm i`・`uv pip install`・`python -m pip install`・`uv sync` を拾い、`uv run` は拾わない（TC-02 の FG-C） |
| V5 | 3 | 読んで可 | 版を上げる手順（onboarding.md）に沿うと、手元と CI が同じ版のまま上がる（手動 No.4） |

## セキュリティレビュー結果

**実施日**: 2026-10-28

バックエンド・フロントエンドのコード変更なし（認証・認可・シリアライザ・モデル・URL は読む対象なし）。対象は CI の harness-tests ジョブ・ハーネスのテストの道具の取り込み経路・`run-all.sh` の流し直し。

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Medium | 依存ライブラリ（CI の部品） | 第三者の action `astral-sh/setup-uv@v10` を足す。浮動タグなので、タグが差し替えられると CI で別の中身が動きうる | 必須: harness-tests の `uses` は `actions/checkout`・`astral-sh/setup-uv` の 2 つだけ（TC-02 の C1・FG-C が固定）。SHA 固定は既存の `actions/*@v4` と同じくリポジトリ全体の方針で扱う（残余リスク） |
| Low | 依存ライブラリ（道具） | uv が PyPI から PyYAML・pre-commit と依存を、python-build-standalone から python を取る | 必須: `uv.lock` のハッシュ付きで入れ、`--locked` で lock とずれたら止める（今の `pip install`〔版もハッシュも固定なし〕より安全側）。新しいライブラリは足さない（PyYAML・pre-commit は今も使用中） |
| Low | 依存ライブラリ（手元） | 手元に `pipx install uv==0.13.6` で uv を入れる | 必須: 版を指定して入れる。uv 自身の版は `required-version` で uv が確かめる |
| Low | セキュリティ設定ミス（CI） | setup-uv のキャッシュ（enable-cache の既定）を PR の実行が書き換える | GitHub のキャッシュはブランチごとに分かれ、PR からは既定ブランチのキャッシュを上書きできない。ジョブの権限・秘密情報は今と同じ（harness-tests は秘密情報を使わない） |
| Low | 入力検証 | `run-all.sh` が `VIRTUAL_ENV`・`HARNESS_UV_REEXEC` を読んで流し直しを決める | 手元・CI の自分の環境の変数で、権限の境目をまたがない。誤った値でも「流し直さない → `check-tools.sh` がぴったりの版で止める」か「`⛔` で止める」で、違う版のまま合格にならない（TC-01 X1〜X5・V） |
| — | 認証・認可／マルチテナント／機密情報／ファイル操作／外部通信 | なし（エンドポイント・データ・秘密情報・アップロード・Webhook の変更なし） | — |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | PR の `uv.lock`・`pyproject.toml` | PR を出せる人 | 悪い版・別の配布元のパッケージを lock に入れる | CI は lock のとおりにしか入れず、マージにはユーザーの承認が要る。harness-tests は秘密情報を持たない | Yes: `uv lock --check`（K2）で pyproject と lock の食い違いを止める | No（中身の妥当性は PR のレビュー） | lock の中身の差分を人が読まないと、正しい形の悪い版は通る（今の `pip install` の最新取り込みより狭い） | Low |
| 2 | PR の `.github/workflows/ci.yml` | PR を出せる人 | harness-tests に別の action・install を足し、版の正を迂回する | `uses` は 2 つだけ・install 0 個・setup-uv に `python-version`・`version` を書かない | Yes: TC-02 の C1・FG-C | No | ci.yml 自体の変更は高リスク判定（path_risk_trigger）で敵対的レビューに回る | Low |
| 3 | `astral-sh/setup-uv@v10` のタグ | 第三者（action の配布元） | タグを差し替えて CI で別の中身を動かす | harness-tests は秘密情報を持たず、書き込み権限の要る操作をしない | No | No | SHA 固定していない（既存の action と同じ） | Medium |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 0件 | 0件 |
| Medium  | 1件 | 1件 |
| Low     | 4件 | 2件 |

### 残余リスク処遇
（retro 段階で決定する）

## レビュー結果
- [20261028_2336 判定: ✅ 完了](../../reviews/I211_plan_review_20261028_2336.md)
