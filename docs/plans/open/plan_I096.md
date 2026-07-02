# I096 計画書: worktree lifecycle スクリプト（作成・撤去）で foot-gun を機械化

## 基本情報
- **計画書ID**: plan_I096
- **関連イシュー**: #182
- **Draft PR**: #186
- **作成根拠資料**: docs/issues/open/I096.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I096_review.md
- **作成日**: 2026-07-02

## 1. 背景/目的

worktree の作成・撤去が**手動多段**で、`worktree.md` が自ら「重大」「静かに壊れる」と警告する foot-gun が未ガードのまま人手規律に委ねられている:
- **§3 重大**: `git worktree add` の基点を `origin/develop` にしないと（例: `main`）、テンプレート・スクリプト・アプリコードの無い**空ツリー**ができる。
- **§5B 静かに壊れる**: backend `.env` は `env_file` の `required: false` 参照のため、コピー忘れでも `docker compose up` は失敗せず、`SECRET_KEY`/`DB_PASSWORD` が insecure な既定値のまま**静かに起動**する。
- **§5D volume 漏れ**: 撤去時に `docker compose down -v` → `git worktree remove` の順で行わないと named volume（Postgres データ含む）が残留・累積する。
- **§5C 分離崩壊**: `COMPOSE_PROJECT_NAME` を global export すると worktree ごとの分離が壊れる。

本イシューは lifecycle を束ねる**ヘルパースクリプト**（`wt-new.sh` / `wt-remove.sh`）を `scripts/claude/` に追加し、これら foot-gun を**機械化で不可能化・自動化**する。I095（横断書込ガード）と対になる「作成・撤去時 foot-gun の機械化」。

## 調査結果

### 環境前提確認（本セッションで実行・確認済み）
- `git 2.43.0`（worktree サブコマンド対応）・`bash 5.2.21`・`docker 29.2.1`・`docker compose v5.1.0` いずれも稼働環境に存在。
- `git worktree list` 実出力:
  ```
  /mnt/c/app/study-app-multitenant  (primary checkout・先頭)
  /mnt/c/app/wt-harness             (linked worktree)
  ```
  → **primary checkout は `git worktree list` の先頭エントリ**であることを実測確認。`dirname` = `/mnt/c/app` が base ディレクトリになる（`/mnt/c/app` を直書きせず導出可能）。
- 既存 `scripts/claude/*.sh` の規約: `#!/usr/bin/env bash` + `set -euo pipefail` + `REPO_ROOT="$(git rev-parse --show-toplevel)"` + `"${1:?Usage...}"`。テストは temp git repo + `ck()` pass/fail ハーネス（`test_pretooluse_worktree_guard.sh` の型）。本計画はこれらを踏襲する。
- `docker compose down -v` は既存 `pretooluse_guard.py` が `DANGER_OK=1` 前置を要求する danger-op（L487）。撤去スクリプトはこの契約と**同一のゲート**を内部に持たせて整合させる（下記 §4-2）。

### スパイク実証（primary/base 導出・in-session 検証済み）
plan-writing-rules「スパイク実証(1)」に基づき、核ロジック（primary=先頭エントリ、base=その親）をスクラッチで実 worktree に対して検証した。結果 **成立**:
```
git worktree list --porcelain | sed -n 's/^worktree //p' | head -1
  → /mnt/c/app/study-app-multitenant
dirname → /mnt/c/app
```
→ `sed -n 's/^worktree //p' | head -1` でパス中の空白にも頑健に primary を取得でき、`dirname` で base を導出できることを実証した（`awk '$2'` は空白パスを取りこぼすため sed を採用）。

### in-session で実証不能な項目（自動テストで代替検証）
- 実際の `git worktree add` / `docker compose up -d,down -v` を稼働リポジトリで実行すると本番 worktree/コンテナに副作用が出るため、**temp git repo（origin=bare + develop）＋ `docker` スタブ（PATH shim）** で振る舞いを決定論検証する（Docker デーモン非依存）。これは plan-writing-rules(1) の「実行可能な確認で再現」を満たす。

## 2. 受け入れ条件（イシュー AC と一致）
- [ ] 作成スクリプトが引数検証（番号=数字・`track`/`概要` は `[A-Za-z0-9._-]` のみ）と worktree path/branch の既存衝突検査を行い、不正時は明示エラー（exit 2）で停止する
- [ ] worktree の作成先は primary checkout（`git worktree list` 先頭）の親ディレクトリから導出する（`/mnt/c/app` を直書きしない）
- [ ] 作成スクリプトが基点を `origin/develop` に固定し、`main` 等の誤基点で空ツリーを作れない
- [ ] 作成スクリプトが backend `.env` を primary（または `--env-source`）から新 worktree 配下へコピーし、欠落/コピー失敗時は明示エラー（exit 2）で停止する
- [ ] 作成スクリプトは既定で `up` せず、`--up` 指定時のみ `docker compose up -d` する
- [ ] 撤去スクリプトが撤去前に未コミット変更・未 push コミット（remote-tracking に無い HEAD）を検出したら `--force` を使わず中止する
- [ ] 撤去スクリプトの `docker compose down -v` は `DANGER_OK=1` 未設定時は実行されず明示エラー（exit 2）で停止する（設定時のみ実行）
- [ ] 撤去スクリプトが `docker compose down -v`（当該ディレクトリ）→ `git worktree remove` の順で実行する
- [ ] `COMPOSE_PROJECT_NAME` が global export されている場合に警告が出る
- [ ] 上記を検証する自動テストが `scripts/claude/tests/` に追加され PASS（Docker デーモン非依存＝`docker` スタブで検証）
- [ ] `docs/runbooks/worktree.md` §3/§5 がスクリプト利用手順に更新されている（手動手順は fallback として保持）

## 3. 影響範囲
- Backend: なし（`.env` の**コピー**のみ・中身は変更しない）
- Frontend: なし
- DB: なし（named volume の回収は既存 danger-ops 手順に従う）
- Config/Infra: `scripts/claude/wt-new.sh`（新規）・`scripts/claude/wt-remove.sh`（新規）・`scripts/claude/tests/test_wt_lifecycle.sh`（新規）・`docs/runbooks/worktree.md`
- 参照のみ（新規作成・改変しない）: `e2e/.env.e2e`（source に在れば作成スクリプトが `cp` する対象・中身は読まない）／`scripts/db_backup.sh`（撤去前の任意バックアップとして案内するのみ）

## 4. 変更点一覧（具体）

### 4-1. `scripts/claude/wt-new.sh`（新規）
**修正アプローチ**: worktree 作成の定型手順（fetch → add(origin/develop 固定) → `.env` コピー検証 → 任意 up）を 1 スクリプトに束ね、各 foot-gun 回避を機械化する。すべて fail-fast（不正・欠落・衝突は `exit 2`）。

```bash
#!/usr/bin/env bash
set -euo pipefail
# wt-new: worktree を作成し foot-gun を機械化する（I096）。
# Usage: [args] wt-new.sh <track> <番号(数字)> <概要> [--env-source <path>] [--up]

usage() { echo "Usage: $0 <track> <番号(数字)> <概要> [--env-source <path>] [--up]" >&2; exit 2; }

TRACK="${1:-}"; NUM="${2:-}"; DESC="${3:-}"
{ [ -n "$TRACK" ] && [ -n "$NUM" ] && [ -n "$DESC" ]; } || usage
shift 3
ENV_SOURCE=""; DO_UP=0
while [ $# -gt 0 ]; do
  case "$1" in
    --env-source)
      [ -n "${2:-}" ] || { echo "[wt-new] --env-source に値がありません" >&2; exit 2; }
      ENV_SOURCE="$2"; shift 2 ;;
    --up)         DO_UP=1; shift ;;
    *) echo "[wt-new] 不明な引数: $1" >&2; usage ;;
  esac
done

# 引数検証（決定論・無言変換なし）
printf '%s' "$NUM"   | grep -Eq '^[0-9]+$'        || { echo "[wt-new] 番号は数字のみ: '$NUM'" >&2; exit 2; }
printf '%s' "$TRACK" | grep -Eq '^[A-Za-z0-9._-]+$' || { echo "[wt-new] track に不正文字: '$TRACK'" >&2; exit 2; }
printf '%s' "$DESC"  | grep -Eq '^[A-Za-z0-9._-]+$' || { echo "[wt-new] 概要に不正文字（空白不可）: '$DESC'" >&2; exit 2; }

# primary/base 導出（/mnt/c/app を直書きしない）
PRIMARY="$(git worktree list --porcelain | sed -n 's/^worktree //p' | head -1)"
[ -n "$PRIMARY" ] || { echo "[wt-new] primary checkout を特定できません" >&2; exit 2; }
BASE="$(dirname "$PRIMARY")"
WT_PATH="$BASE/wt-$TRACK"
BRANCH="feature/I${NUM}-${DESC}"

# 衝突事前検査（fail-fast・git の生失敗に委ねない）
[ -e "$WT_PATH" ] && { echo "[wt-new] worktree path が既に存在: $WT_PATH" >&2; exit 2; }
git show-ref --verify --quiet "refs/heads/$BRANCH" && { echo "[wt-new] branch が既に存在: $BRANCH" >&2; exit 2; }

# .env source 決定（既定=primary/backend/.env）・存在検証（欠落なら add 前に停止＝orphan worktree を作らない）
ENV_SRC="${ENV_SOURCE:-$PRIMARY/backend/.env}"
[ -f "$ENV_SRC" ] || { echo "[wt-new] .env source が存在しません: $ENV_SRC" >&2; exit 2; }

# COMPOSE_PROJECT_NAME 検出（§5C）
[ -n "${COMPOSE_PROJECT_NAME:-}" ] && \
  echo "[wt-new] ⚠️ COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME が設定されています。worktree 分離が壊れる恐れ（§5C）" >&2

# 作成（基点を origin/develop に固定＝§3 重大の回避）
git fetch origin
git worktree add "$WT_PATH" -b "$BRANCH" origin/develop

# backend .env コピー（中身は読まない・cp と test -f のみ＝§5B の回避）
cp "$ENV_SRC" "$WT_PATH/backend/.env"
[ -f "$WT_PATH/backend/.env" ] || { echo "[wt-new] .env コピー失敗: $WT_PATH/backend/.env" >&2; exit 2; }

# e2e/.env.e2e は source と同じ worktree に在れば同様コピー（非致命）
SRC_ROOT="$(dirname "$(dirname "$ENV_SRC")")"   # .../backend/.env → .../（source worktree root）
if [ -f "$SRC_ROOT/e2e/.env.e2e" ]; then
  cp "$SRC_ROOT/e2e/.env.e2e" "$WT_PATH/e2e/.env.e2e" || echo "[wt-new] e2e/.env.e2e コピーをスキップ（非致命）" >&2
fi

# 任意 up（既定 OFF・§6 ポート衝突のため opt-in）
if [ "$DO_UP" -eq 1 ]; then
  ( cd "$WT_PATH" && docker compose up -d )
fi
echo "[wt-new] 作成完了: $WT_PATH (branch=$BRANCH, base=origin/develop)"
```

- **修正方針**: 「引数検証 → 導出 → 衝突検査 → `.env` source 検証（add 前）→ fetch → add(origin/develop) → コピー → 任意 up」の順で、失敗し得る各段を明示エラーで止める。`.env` の**中身は読まない**（`cp`+`test -f` のみ）＝deny リストと非衝突。

### 4-2. `scripts/claude/wt-remove.sh`（新規）
**修正アプローチ**: 撤去手順（撤去前チェック → `down -v`（DANGER_OK ゲート）→ `git worktree remove`）を束ね、作業消失と volume 漏れを機械化で防ぐ。

```bash
#!/usr/bin/env bash
set -euo pipefail
# wt-remove: worktree を撤去する（I096）。down -v は DANGER_OK=1 必須。
# Usage: [DANGER_OK=1] wt-remove.sh <track>

TRACK="${1:?Usage: [DANGER_OK=1] $0 <track>}"
printf '%s' "$TRACK" | grep -Eq '^[A-Za-z0-9._-]+$' || { echo "[wt-remove] track に不正文字: '$TRACK'" >&2; exit 2; }

PRIMARY="$(git worktree list --porcelain | sed -n 's/^worktree //p' | head -1)"
[ -n "$PRIMARY" ] || { echo "[wt-remove] primary checkout を特定できません" >&2; exit 2; }
BASE="$(dirname "$PRIMARY")"
WT_PATH="$BASE/wt-$TRACK"

[ -d "$WT_PATH" ] || { echo "[wt-remove] worktree path が存在しません: $WT_PATH" >&2; exit 2; }
WT_REAL="$(cd "$WT_PATH" && pwd -P)"
# primary を誤って撤去しない
[ "$WT_REAL" = "$(cd "$PRIMARY" && pwd -P)" ] && { echo "[wt-remove] primary checkout は撤去できません" >&2; exit 2; }
# CWD が撤去対象 WT 内だと後段の git worktree remove が拒否する → 事前に明示エラーで弾く
case "$(pwd -P)/" in
  "$WT_REAL"/*) echo "[wt-remove] 撤去対象 WT の内側からは実行できません。外（例: primary）に cd して再実行してください: $WT_PATH" >&2; exit 2 ;;
esac

# 撤去前チェック（1）未コミット変更（git 失敗は set -e で abort＝fail-safe。$() を [ ] に埋めると失敗が握り潰されるため一旦代入）
DIRTY="$(git -C "$WT_PATH" status --porcelain)"
[ -n "$DIRTY" ] && \
  { echo "[wt-remove] 未コミット変更あり。撤去中止（作業消失防止）: $WT_PATH" >&2; exit 2; }
# 撤去前チェック（2）未 push コミット（HEAD がどの remote-tracking にも含まれない＝未 push）
if [ -z "$(git -C "$WT_PATH" branch -r --contains HEAD 2>/dev/null)" ]; then
  echo "[wt-remove] HEAD が未 push（remote に無い）。撤去中止（作業消失防止）: $WT_PATH" >&2; exit 2
fi

# COMPOSE_PROJECT_NAME 検出（§5C）
[ -n "${COMPOSE_PROJECT_NAME:-}" ] && \
  echo "[wt-remove] ⚠️ COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME が設定されています（§5C・分離が壊れている恐れ）" >&2

# volume 回収は danger-op（DANGER_OK=1 必須＝pretooluse_guard.py と同一契約）
if [ "${DANGER_OK:-}" = "1" ]; then
  # 当該ディレクトリで named volume を回収（§5D）。down 失敗時は remove へ進まず対処を案内
  ( cd "$WT_PATH" && docker compose down -v ) || {
    echo "[wt-remove] docker compose down -v が失敗しました。docker 稼働・compose ファイルを確認し、手動対応後に 'git worktree remove $WT_PATH' を実行してください。" >&2
    exit 2; }
else
  echo "[wt-remove] docker compose down -v は破壊的操作です（Postgres 開発データ削除を含む）。" >&2
  echo "[wt-remove] 必要なら 'scripts/db_backup.sh' で事前バックアップのうえ 'DANGER_OK=1 $0 $TRACK' で再実行してください。" >&2
  exit 2
fi

# remove（--force は使わない＝撤去前チェックで担保）。cwd は変えていないので内部からの remove ではない
git worktree remove "$WT_PATH"
echo "[wt-remove] 撤去完了: $WT_PATH"
```

- **修正方針**: `down -v` を `DANGER_OK=1` 未設定時は実行しない（＝`pretooluse_guard.py` L487 の契約と同一化）ことで、Claude が `bash wt-remove.sh` 経由で無言に volume を消す抜けを塞ぐ。未コミット/未 push は `--force` を使わず中止し、git 既定が弾かない「clean だが未 push」も機械化で捕捉する。

**プランレビュー（20260702_2027・VERDICT OK）反映**:
- W1: CWD が撤去対象 WT 内なら後段 `git worktree remove` が拒否するため、`case "$(pwd -P)/" in "$WT_REAL"/*)` で事前に明示エラー停止（→ TC-R7）。
- W2: `--env-source` を値なしで渡すと `shift 2` が範囲外で `set -e` 発火・無言 exit するため、値の非空検査を追加（→ TC-N10）。
- W4: `docker compose down -v` 失敗時は `|| { 案内; exit 2; }` で「手動対応後に remove」を案内（→ TC-R8）。
- Info6: 未コミットチェックの `$()` を `[ ]` 内に直書きすると git 失敗が握り潰され silent pass になるため、一旦 `DIRTY=$(...)` へ代入（git 失敗は `set -e` で abort＝fail-safe）。
- Info5（remote-only ブランチ衝突は fetch 前検査では検出しない）: **対応任意として受容**。単一開発者の worktree 管理が対象で、`git worktree add -b` 自身がローカル同名ブランチ存在時に失敗するため主要な事故は防げる。ネットワーク往復（`ls-remote`）を毎回課すのは要件規模に対し過剰と判断。

### 4-3. `scripts/claude/tests/test_wt_lifecycle.sh`（新規）
- `test_pretooluse_worktree_guard.sh` の型を踏襲（temp git repo + `ck()` + false-green 注入）。
- **セットアップ**: `mktemp -d` に (a) bare origin repo（`backend/.env`・`e2e/.env.e2e`・`docker-compose.yml`・`main` にonly-main-file / `develop` に only-develop-file を持つ）を作り、(b) それを clone して primary temp checkout とする。TC-R6（primary 保護）用に clone 先ディレクトリ名を `wt-primary` にする回でのみ `WT_PATH==PRIMARY` を成立させる。(c) `docker` スタブ（PATH shim・`$DOCKER_LOG` に `docker $*` を追記、`down` 呼出時は `$WT_REAL/.git` の存在を `present=yes/no` として記録＝順序検証）を `$TMP/bin` に置き PATH 先頭に付与。**失敗注入**: 環境変数 `DOCKER_FAIL_ON`（例 `down`）を設定した回は、引数にその語を含むとき `exit 1` する（TC-R8 用・通常回は未設定で成功）。
- 各スクリプトは `( cd "$PRIMARY_TMP" && PATH="$TMP/bin:$PATH" bash "$SCRIPT" ... )` で実行し exit code / 生成物 / `$DOCKER_LOG` を検証。TC 詳細は `docs/tests/open/I096_auto_test.md` 参照。

### 4-4. `docs/runbooks/worktree.md`（§3/§5 更新）
- **§3**（作成/削除）: 冒頭に「**推奨: `scripts/claude/wt-new.sh` / `wt-remove.sh` を使う**（下記の手動手順は fallback）」を追記し、`bash scripts/claude/wt-new.sh <track> <番号> <概要> [--env-source <path>] [--up]` と `DANGER_OK=1 bash scripts/claude/wt-remove.sh <track>` の使用例を示す。既存の手動 `git worktree add ... origin/develop` / `docker compose down -v` → `remove` 手順は「fallback（スクリプトを使わない場合）」として保持。
- **§5**（セットアップ）: `.env` コピー・`up` の手動手順に「`wt-new.sh` が自動化（`.env` 存在検証・`--up` opt-in）」の追記。§5B/§5C/§5D の注意書きは残し、各スクリプトが機械化している旨を 1 行ずつ付す。
- 手動手順は削除せず fallback として残す（AC 準拠・plan-writing-rules「条件分岐のコマンド粒度パリティ」）。

## 5. 実装手順（ステップ）

1. **【未知リスク先行】テストハーネス基盤＋happy path**: `test_wt_lifecycle.sh` の temp repo + docker スタブ基盤を作り、`wt-new.sh` の happy path（作成・origin/develop 基点・`.env` コピー）を通す。実 git/docker 副作用なしで振る舞いを再現できるかを最初に顕在化させる → TC-N1〜N3 参照。
   - 依存: なし（最初に着手）。
2. **`wt-new.sh` 実装（検証・衝突・env・up 分岐）**: 引数検証／導出／衝突検査／`.env` source 検証／`--up` opt-in／`COMPOSE_PROJECT_NAME` 検出を実装 → TC-N4〜N9 参照。
   - 依存: ステップ1。
3. **`wt-remove.sh` 実装（撤去前チェック・DANGER_OK ゲート・順序）**: 未コミット/未 push 中止、`DANGER_OK=1` ゲート、`down -v`→`remove` 順序、primary 保護を実装 → TC-R1〜R6 参照。
   - 依存: ステップ1（ハーネス基盤）。ステップ2 とは並行可。
4. **false-green 注入 TC**: DANGER_OK ゲート・`.env` 欠落停止を「ガードを外した複製」で反証（注入で NG になることを確認）→ TC-FG1・TC-FG2 参照。
   - 依存: ステップ2・3。
5. **runbook 更新**: `worktree.md` §3/§5 をスクリプト利用手順に更新（手動は fallback 保持）→ TC-D1・TC-D2 参照。
   - 依存: なし（並行可）。
6. **自動テスト全実走・決定論ゲート確認**: `test_wt_lifecycle.sh` 全 TC PASS ＋ `bash -n` 構文チェック ＋ runbook grep を実走。
   - 依存: ステップ2〜5。

## 6. テスト計画
### 自動（`docs/tests/open/I096_auto_test.md`）
- `wt-new`: happy path・origin/develop 基点固定・`.env` コピー・`.env` 欠落停止（orphan worktree 非作成）・`--up` opt-in（既定 OFF）・引数検証（数字/許可文字/空白）・衝突検査（path/branch）。
- `wt-remove`: `DANGER_OK` 未設定で `down` 非実行＋非撤去・`DANGER_OK=1` で `down -v`→`remove` 順序（`present=yes` で順序実証）・未コミット中止・未 push 中止・primary 保護。
- `COMPOSE_PROJECT_NAME` 設定時の警告出力。
- **false-green 注入**: DANGER_OK ゲート除去複製では未設定でも `down` される／`.env` 検証除去複製では欠落でも進む＝実体スクリプトの当該ガードが停止要因であることを反証。
- 決定論ゲートで `test_wt_lifecycle.sh` ＋ `bash -n`（両スクリプト）＋ runbook grep を実走。
### 手動（`docs/tests/open/I096_manual_test.md`）
- Claude 実施: スクリプト/テストのファイル存在・`bash -n` 構文・runbook 追記内容の確認（すべて稼働中セッションで実施可）。
- ハーネス権限モード/フック依存の TC は無い（スクリプトは通常の bash 実行・フック挙動の新規変更なし）ため「実施環境」列は不要。

## 7. ロールバック
- 新規 3 ファイル（`wt-new.sh`・`wt-remove.sh`・`test_wt_lifecycle.sh`）を削除し、`worktree.md` §3/§5 の追記を revert すれば従来の手動運用に戻る。DB・外部状態の永続変更なし（テストは temp repo と docker スタブのみ・実 volume を触らない）。

## 8. Risk & 回避策
- **R1 テストが実 docker/git に副作用**: temp repo（bare origin+clone）と `docker` PATH スタブで隔離。実 `docker compose` は一切呼ばない（スタブがログするのみ）。`trap 'rm -rf "$TMP"' EXIT` で後始末。
- **R2 未 push 判定の誤検出/漏れ**: `git branch -r --contains HEAD` で「HEAD がどの remote-tracking にも含まれない」を未 push とする。upstream の指し先（develop 等）に依存せず、feature ブランチを push 済みなら remote-tracking が HEAD を含み安全に撤去できる。未 push なら空→中止（作業消失防止）。
- **R3 DANGER_OK ゲートの実効性が false-green**: ゲート除去複製での注入 TC（TC-FG1）で、除去時は未設定でも `down` されることを確認し、実体スクリプトのゲートが停止要因であることを反証する。
- **R4 スクリプト内 `cp` が I095 横断書込ガードに抵触**: `cp` 宛先は新規 worktree（正当な書込先）。Claude が `bash wt-new.sh ...` を実行しても guard が見るのは外側コマンド文字列のみで、内部 `cp` の絶対宛先は露出せず block されない（イシュー制約「書込先は新規/現 worktree 配下に限定」と整合）。
- **R5 `git worktree list` の空白パス取りこぼし**: `awk '$2'` ではなく `sed -n 's/^worktree //p'` でパス全体を取得し空白に頑健化。
- **R6 base ディレクトリ導出の誤り**: temp テストは base=temp 親で走るため、`/mnt/c/app` 直書きだと TC-N1 の `WT_PATH` 検証が失敗する＝導出漏れを自動検出できる。

## セキュリティ・要件適合チェック（承認ポイント用）
- **セキュリティ影響**: Django/React アプリコード変更なし（P3/P5/P6/P8/P9 影響なし）。本変更は開発ハーネスの安全ガード**強化**。`.env` は**中身を読まず** `cp`+`test -f` のみ（機密値をログ/標準出力に出さない）。`docker compose down -v`（破壊的）は `DANGER_OK=1` ゲートで明示 ack を必須化＝最小権限・既存 danger-ops 枠組み準拠。入力（`track`/`概要`/`番号`）は許可文字 allowlist で検証しコマンドインジェクション面を絞る。
- **要件適合**: AC 範囲内。仕様追加なし。同時起動ポート override は明示的に I097 へ（含まない）。
- **設計判断の出所**:
  - DANGER_OK ゲート／`.env` source=primary＋override／未 push 中止／up 既定 OFF／`COMPOSE_PROJECT_NAME` 警告のみ／docker スタブ検証 → **イシューに明記**（grill-me 設計確認メモ）。
  - 引数検証の許可文字・衝突事前検査・base=primary 親導出・`COMPOSE_PROJECT_NAME` 判定式 → **イシューに明記**（grill-me 第2ラウンド メモ）。
  - 未 push 判定を `branch -r --contains HEAD` で行う（upstream ahead ではなく remote 包含）→ **planning 中の精緻化**（メモの「未 push コミット」を、push 済み feature ブランチを誤中止しない形へ具体化。仮定ではなく git 挙動に基づく）。
  - e2e source を「`--env-source` と同じ worktree 由来」に統一 → **planning 中の精緻化**（メモの「source に在れば」を一意化）。

## 9. 承認ポイント
- [ ] 計画内容（`wt-new.sh` / `wt-remove.sh` / `test_wt_lifecycle.sh` 新規＋`worktree.md` §3/§5 更新）で妥当か
- [ ] `wt-remove` は **`DANGER_OK=1` 必須**（未設定なら `down -v` を実行せず exit 2）＝volume 回収は常に明示 ack を要する、という運用でよいか
- [ ] 未 push 判定を `git branch -r --contains HEAD`（remote-tracking に HEAD が含まれなければ中止）で行う方針でよいか（planning 中の精緻化）
- [ ] e2e `.env.e2e` は `--env-source` と同じ worktree 由来から在れば非致命コピー、という一意化でよいか（planning 中の精緻化）
- [ ] テスト計画（temp repo + docker スタブの決定論ゲート＋false-green 注入／手動は Claude 実施のファイル・構文確認）で妥当か
- [ ] Danger Ops: 有（`down -v`）。`DANGER_OK=1` ゲート＋明示コマンドで既存枠組みに整合。ロールバックは開発 DB のため不要（必要なら `scripts/db_backup.sh`）

## レビュー結果
- [20260702_2027 判定: ✅ 完了](../../reviews/I096_plan_review_20260702_2027.md)
