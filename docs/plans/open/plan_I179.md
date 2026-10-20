# I179 計画書: ワークツリー運用の見直し

## 基本情報
- **計画書ID**: plan_I179
- **関連イシュー**: #299
- **Draft PR**: #300
- **作成根拠資料**: docs/issues/open/I179.md（起点イシュー・設計確認メモ＝grill-me 3 回分）
- **実装後評価**: docs/reviews/open/I179_review.md
- **作成日**: 2026-10-20

## 1. 背景/目的
- **背景**: ハーネス改善用に 2 つ目のワークツリーを作ろうとした際、`docs/runbooks/worktree.md` が「1 トラック＝1 ワークツリー」前提で、同一トラックの 2 つ目が定義されていなかった。公式（Claude Code）のワークツリー機能と比較評価した結果、問題 A〜H が見つかった（詳細はイシュー「現状の問題」）。
- **目的**:
  1. ワークツリーの作成・片付けを公式機能（`claude --worktree`・`.worktreeinclude`・自動片付け）に寄せる。自作は公式に無い部分（ポート割当・Docker の後始末・横断書込ガード・採番）だけにする。
  2. 運用ルールを今の使い方（同一トラックで複数ワークツリー・1 つのワークツリーで複数イシューを順番に扱う）に合わせる。
- **基本方針（ユーザー指示）**: 公式の処理を置き換える・無効にする案は採らない（WorktreeCreate / WorktreeRemove フックは使わない）。

## 調査結果

### 原因の概要
ワークツリーの決まりと自作スクリプトは、公式のワークツリー機能が入る前の「2 トラック・各 1 ワークツリー」の形に合わせて作られた。そのため、今の使い方と公式の仕組み（本体フォルダの中にワークツリーを作る・設定ファイルを自動でコピーする・自動で片付ける）のどちらとも合っていない。

### 詳細な原因分析
| 問題 | 発生箇所（具体） | 技術的な原因 |
|------|-----------------|-------------|
| A 同一トラック複数が未定義 | `worktree.md` §1「トラック = 1 作業ツリー」・§2・§10 | 作成当時の構成を前提に書いた |
| B 次イシューへの移り方が無い | `worktree.md` 全体（記載なし） | 単一作業ツリーでブランチを切り替える前提だった |
| C 共有物の注意不足 | `worktree.md` §7 | git stash スタック・git config がワークツリー共有である点の洗い出し漏れ |
| D §10 の陳腐化 | `worktree.md` §10「2026-07 時点」の手書き表 | 手書きの一覧は構造的に古くなる |
| E wt-remove の使い勝手 | `scripts/claude/wt-remove.sh` 40〜50 行目（`DANGER_OK=1` が常に必須）・16 行目（`$BASE/wt-$TRACK` 固定） | Docker を使わないワークツリーを想定していなかった |
| F 公式機能との二重化 | `scripts/claude/wt-new.sh` 全体 | 公式の `.worktreeinclude`・自動片付けより前に作られた |
| G `/plan-issue` が失敗し得る | `.claude/skills/plan-issue/SKILL.md` 23〜25 行目・`docs/runbooks/issue-flow.md` 219〜221 行目 | `git checkout develop` を経由する。git は同じブランチを 2 つのワークツリーで同時にチェックアウトできない |
| H ガードの入れ子誤判定 | `scripts/claude/hooks/pretooluse_guard.py` 263〜279 行目 `_cross_worktree`・371〜386 行目 `_block_cross_worktree` | 「現ワークツリー以外のどれかの root の配下か」で判定しており、パスを含む最も内側の root を見ていない。入れ子ワークツリーの自分のファイルは親 root の配下でもあるため「別ワークツリー」と誤判定する |

### スパイク・実機確認の結果
grill-me 中のスパイク（2026-10-19・Claude Code 2.1.302・使い捨てリポジトリ）は S1〜S6 をイシューに記録済み。計画作成時（2026-10-20）に以下を追加で確認した。

| ID | 確認内容 | 方法 | 結果 |
|----|---------|------|------|
| S7 | G: 別ワークツリーが develop をチェックアウト中に、旧手順（`git checkout develop`）は失敗し、新手順（`git fetch origin` → `git checkout --no-track -b feature/I999-x origin/develop`）は成功するか。未コミットのイシューファイルは持ち越されるか | scratchpad の `spike/g_branch.sh` を bash で実行 | 成立。旧手順 `fatal: 'develop' is already used by worktree at ...`（exit 128）。新手順 exit 0・未コミットファイルは残る・上流ブランチは未設定（`--no-track` の効果。push 時の `-u` で設定される） |
| S8 | 本体の中の入れ子ワークツリー（`.claude/worktrees/harness-2`）を、gitignore 済みの `backend/.env`・`.env` がある状態で親から `git worktree remove` できるか。親の `git status` にどう出るか。ブランチは残るか | scratchpad の `spike/nested_remove.sh` を bash で実行 | 成立。`.gitignore` に `.claude/worktrees/` が無いと親の `git status` に `?? .claude/` が出る（本体が「未コミット変更あり」に見える）。追加後は出ない。remove は exit 0、ブランチ `worktree-harness-2` は残る |
| S10 | （実装ステップ6の実機確認・2026-10-21・2.1.304）公式 `claude -p --worktree` で作ったワークツリーを `wt-remove.sh` で撤去できるか | 使い捨て primary 役で `claude -p --worktree harness-2` → `wt-remove.sh` | **不成立（計画変更の起点）**。公式機能はワークツリーを `claude session harness-2 (pid N start M)` の理由で `git worktree lock` し、`-p` のセッション終了後も（pid のプロセスが無くても）ロックが残る。素の `git worktree remove` は `cannot remove a locked working tree` で exit 128。データ有りの場合は `down -v` の後に remove が失敗する順序の問題も生じる。サブエージェント（`isolation: worktree`）のワークツリーはロックされない。→ 4-6 にロックの扱いを追加 |
| S9 | Compose プロジェクトのコンテナ・named volume をラベルで検出できるか | `docker ps -a -q --filter label=com.docker.compose.project=<名前>`・`docker volume ls -q --filter label=...` を読み取りのみで実行 | 成立。`study-app-multitenant` はコンテナ 7・volume 5 を返し、`wt-harness`（Docker 未使用）は空 |

### 環境前提確認（2026-10-20）
- Claude Code: `2.1.304`（スパイク時 2.1.302 から更新。公式方式の挙動は手動テスト M1・M3・M6 で 2.1.304 で再確認する）
- Docker: 稼働中（`docker compose ls -a` で `study-app-multitenant` を確認）
- git worktree: `study-app-multitenant`（I174）・`wt-harness`（本イシュー）の 2 つ
- Compose ファイルに最上位の `name:` は無い（プロジェクト名＝ディレクトリ名）

### 既存テストのベースライン（2026-10-20・変更前）
| テスト | 結果 |
|-------|------|
| `scripts/claude/tests/test_wt_lifecycle.sh` | pass=55 fail=0 |
| `scripts/claude/tests/test_wt_port_offset.sh` | pass=34 fail=0 |
| `scripts/claude/tests/test_pretooluse_worktree_guard.sh` | pass=27 fail=0 |

### 消費箇所の全件列挙（`git grep`・closed の記録類を除く）
**`wt-new` の参照**:
| 箇所 | 対応 |
|------|------|
| `scripts/claude/wt-new.sh` | 削除 |
| `docs/runbooks/worktree.md` 31・37・62・80・91・92・114・121・122・130 行目 | 公式方式・`wt-ports.sh` の記述へ書き換え |
| `docs/runbooks/common-commands.md` 25・26 行目 | `wt-ports.sh` へ書き換え |
| `scripts/claude/tests/test_wt_lifecycle.sh` 2・10・55・87〜140・201・218〜226 行目 | wt-new 部分を削除し、テスト用ワークツリーは `git worktree add` で直接作る |
| `scripts/claude/tests/test_wt_port_offset.sh` 2・6・11・56・124 行目 | `wt-ports.sh` を対象に書き換え |
| `docs/issues/open/I179.md` | 本イシュー自身（経緯の記録として残す） |

**「トラック＝1 ワークツリー」「primary 特別扱い」の参照（概念の消費箇所）**:
| 箇所 | 対応 |
|------|------|
| `docs/runbooks/worktree.md` §1・§2・§8・§10 | 書き換え |
| `docs/runbooks/issue-flow.md` 61・199 行目「（対応 worktree: wt-harness）」 | ワークツリー名の固定を外す（下記） |
| `.claude/skills/issue-bootstrap/SKILL.md` 70 行目「（対応 worktree: wt-harness）」 | 同上 |
| `scripts/claude/tests/test_i107_track_label_docs.sh`（`worktree.md` に `track:app`/`track:harness` が 1 行以上） | ラベル対応を残すので変更不要（回帰ゲートとして実行） |
| `scripts/claude/tests/test_next_issue_num.sh` DOC3a/3b（`worktree.md` に `next-issue-num.sh`・「権威」） | §8 の「採番権威の単一化（`next-issue-num.sh`）」は残すので変更不要（回帰ゲートとして実行） |

**`git checkout develop` の参照**: `.claude/skills/plan-issue/SKILL.md` 23 行目・`docs/runbooks/issue-flow.md` 219 行目が対象。`issue-flow.md` 369 行目（ステップ25・ローカル merge）と `docs/runbooks/workflow.md` 203〜228 行目（リリース/hotfix）はイシューのスコープ外。`docs/runbooks/legacy/` は過去の記録のため対象外。

**参照先の実在性**: 計画書・テスト文書に書いたパスのうち新規作成予定（`scripts/claude/wt-ports.sh`・`.worktreeinclude`・`scripts/claude/tests/test_i179_worktree_docs.sh`）以外は `git grep` / Read で実在を確認済み。

## 2. 受け入れ条件
イシューの受け入れ条件 13 項目をそのまま採用する（対応 TC を併記）。
- [ ] `worktree.md` に primary から `claude --worktree <track>-<連番>` で 2 つ目以降を作る手順があり、その手順で作成でき、`backend/.env`（と `e2e/.env.e2e`）がコピーされる → TC-D3・手動 M1
- [ ] `wt-ports.sh` が既存ワークツリー（入れ子配置を含む）と衝突しないポートを直下 `.env` に生成し、衝突する指定では非ゼロ終了する → TC-P1〜P12・FG-P1・手動 M2
- [ ] `wt-new.sh` が削除され、実行手順としての参照が残っていない → TC-D1・D2・D10
- [ ] `.claude/settings.json` に WorktreeCreate / WorktreeRemove フックが無い → TC-D7・ゲート行
- [ ] `worktree.md` から primary の特別扱いと §10 の手書き表が除かれ、`git worktree list` 案内とトラック⇔ラベル対応が残る → TC-D3・D4・test_i107
- [ ] `worktree.md` §7 に stash・git config 共有の注意がある → TC-D3
- [ ] `worktree.md` に撤去の使い分け・取り残しの発見と削除・既存 `wt-harness` の移行手順・入れ子配置の検索の注意がある → TC-D3
- [ ] `wt-remove.sh` がデータ無しなら `DANGER_OK` なしで撤去、データあり・判定失敗なら停止（3 通り）。公式配置も撤去でき（終了済みセッションのロックを含む）、ブランチが残る → TC-R0〜R15・FG1・FG3・FG4・手動 M4
- [ ] `/plan-issue` と `issue-flow.md` ステップ5 が develop をチェックアウトせず `origin/develop` 基点でブランチを作り、別ワークツリーが develop をチェックアウト中でも成功する → TC-D5・D6・手動 M5
- [ ] ガード: 入れ子ワークツリー自身への書込は許可、親→入れ子・入れ子→親・兄弟間はブロック（失敗注入あり） → TC-G1〜G7・FG-G1
- [ ] サブエージェント `isolation: worktree` で `.env` コピー・自分のファイルへの書込・変更なしなら自動片付け を実機確認 → 手動 M3
- [ ] 既存テストと追加テストがすべて通る → 決定論ゲート全行
- [ ] 完了記録に「既存 `wt-harness` の移行（I178・I179 完了後）」が残作業として書かれている → 手動 M8（/close 時）

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし（`wt-remove.sh` が Docker の named volume を消すために許可を求める条件が変わる。Danger Ops 参照）
- Config/Infra:
  - 新規: `.worktreeinclude`・`scripts/claude/wt-ports.sh`・`scripts/claude/tests/test_i179_worktree_docs.sh`
  - 削除: `scripts/claude/wt-new.sh`
  - 変更: `.gitignore`・`scripts/claude/wt-remove.sh`・`scripts/claude/hooks/pretooluse_guard.py`・`.claude/skills/plan-issue/SKILL.md`・`.claude/skills/issue-bootstrap/SKILL.md`・`docs/runbooks/worktree.md`・`docs/runbooks/issue-flow.md`・`docs/runbooks/common-commands.md`・`scripts/claude/tests/test_wt_lifecycle.sh`・`scripts/claude/tests/test_wt_port_offset.sh`・`scripts/claude/tests/test_pretooluse_worktree_guard.sh`
  - 変更しない: `.claude/settings.json`（フックを足さないことを検査するだけ）・`docker-compose.yml`
- 依存関係ファイル（requirements*.txt / package*.json）: 変更なし
- サービス再起動: 不要（Docker のサービスに関わるファイルは変えない。ガードは呼び出しごとに読み込まれるので即時反映）

## 4. 変更点一覧（具体）

### 修正アプローチ
公式の `claude --worktree` を作成の正規手段にし、公式で足りない 3 点（ポート割当・Docker データの後始末・入れ子でのガード判定）だけを自作で補う。あわせて、ルール文書と `/plan-issue` の手順を複数ワークツリー前提に直す。

### 4-1. `.worktreeinclude`（新規・F）
**修正方針**: 公式機能で、gitignore 済みの設定ファイルを新しいワークツリーへ自動コピーさせる。`--worktree`・サブエージェント・`EnterWorktree` のどれで作っても同じようにコピーされる（S3）。
```gitignore
# 公式 .worktreeinclude（I179）: 新しいワークツリーへコピーする gitignore 済みファイル
backend/.env
e2e/.env.e2e
```

### 4-2. `.gitignore`（H/F 関連）
**修正方針**: 本体の中に作られるワークツリーが、本体の「未コミット変更」に見えないようにする（S8）。検索ツール（Cursor・Claude の Grep/Glob）からも外れる。
```gitignore
# Claude Code 公式ワークツリー（I179）
.claude/worktrees/
```

### 4-3. `scripts/claude/hooks/pretooluse_guard.py`（H）
**修正方針**: 対象パスを含むワークツリー root のうち「最も内側（最長一致）」を所有者とし、所有者が現ワークツリーでなければ別ワークツリーと判定する。親→入れ子・入れ子→親・兄弟間のブロック、fail-safe（境界を確定できなければブロック）、`DANGER_OK` で解除しない点は変えない。
```python
def _owning_root(ap, roots):
    """ap を含むワークツリー root のうち最も内側（最長一致）を返す。どれにも含まれなければ None。
    入れ子ワークツリー（<primary>/.claude/worktrees/<name>）では、親 root より入れ子 root が優先される。"""
    best = None
    for root in roots:
        if ap == root or ap.startswith(root + os.sep):
            if best is None or len(root) > len(best):
                best = root
    return best

def _cross_worktree(path):
    # （docstring・前段の None 判定は現行どおり）
    ap = os.path.realpath(os.path.abspath(path))
    owner = _owning_root(ap, roots)
    return owner is not None and owner != cur
```
`_block_cross_worktree` のメッセージ用 `x_root` も `_owning_root(ap, roots)` に置き換える（現行は最初に一致した root を出すため、入れ子では親 root を表示してしまう）。

### 4-4. `scripts/claude/wt-ports.sh`（新規・F）
**修正方針**: `wt-new.sh` のポート割当部分（I097 の規則: STEP=10・既存ワークツリーを走査して空きオフセット・衝突時は失敗）を、規則を変えずに「今いるワークツリー」向けの単独スクリプトにする。Docker を起動する前に 1 回だけ実行する。
- 使い方: `bash scripts/claude/wt-ports.sh [--port-offset N]`（今いるワークツリーが対象）
- 対象は `git rev-parse --show-toplevel` の結果。走査は `git worktree list --porcelain`（入れ子配置も含まれる）で、**自分自身は除く**。
- primary（`git worktree list` の先頭）で実行したら exit 2（primary は offset 0＝既定ポートの決まりのため）。
- `backend/.env` が無ければ exit 2（`.worktreeinclude` は元ファイルが無いと黙って飛ばすため、Docker 起動前のここで止める。§5B の「静かに insecure 起動」を防ぐ）。
- 直下 `.env` に `DB_PORT`/`REDIS_PORT`/`BACKEND_PORT`/`FRONTEND_PORT` のどれかが既にあれば、何も変えずに現在値を表示して exit 0（2 回実行しても安全）。
- 直下 `.env` が無ければ作る。ポート以外の行だけがある場合は、その行を残して末尾に 4 行を足す。`COMPOSE_PROJECT_NAME` は書かない。
- `COMPOSE_PROJECT_NAME` が設定されていれば警告（現行 wt-new と同じ）。
- 終了コード: 0=割当済み/割当成功・2=明示エラー停止。
```bash
WT="$(git rev-parse --show-toplevel)"; WT_REAL="$(cd "$WT" && pwd -P)"
PRIMARY="$(git worktree list --porcelain | sed -n 's/^worktree //p' | head -1)"
[ "$WT_REAL" = "$(cd "$PRIMARY" && pwd -P)" ] && { echo "[wt-ports] primary は既定ポート（offset 0）で使います。割当は不要です" >&2; exit 2; }
[ -f "$WT/backend/.env" ] || { echo "[wt-ports] backend/.env がありません。primary からコピーしてから再実行してください" >&2; exit 2; }
if [ -f "$WT/.env" ] && grep -Eq '^(DB|REDIS|BACKEND|FRONTEND)_PORT=' "$WT/.env"; then
  echo "[wt-ports] 割当済みのため変更しません:"; grep -E '^(DB|REDIS|BACKEND|FRONTEND)_PORT=' "$WT/.env"; exit 0
fi
# existing_ports / existing_offsets は wt-new.sh 62〜80 行目を移植し、$WT_REAL と同じワークツリーは飛ばす
# オフセット決定・衝突検査は wt-new.sh 82〜111 行目を移植（メッセージの接頭辞のみ [wt-ports]）
printf 'DB_PORT=%s\nREDIS_PORT=%s\nBACKEND_PORT=%s\nFRONTEND_PORT=%s\n' ... >> "$WT/.env"
```

### 4-5. `scripts/claude/wt-new.sh`（削除・F）
**修正方針**: 作成は公式の `claude --worktree`、設定ファイルのコピーは `.worktreeinclude`、ポートは `wt-ports.sh` が受け持つため、役目が無くなる。`origin/develop` 基点の保証は公式の `worktree.baseRef` 既定（`"fresh"`＝リモートの既定ブランチ＝`develop`）が受け持つ。

### 4-6. `scripts/claude/wt-remove.sh`（E）
**修正方針**: 消すデータが無いワークツリーは許可なしで撤去でき、データがある（または確かめられない）ときだけ従来どおり `DANGER_OK=1` を求める。撤去対象は「`git worktree list` に登録されたワークツリーのパス」で指定し、公式配置（`<primary>/.claude/worktrees/<name>`）も旧配置（`/mnt/c/app/wt-harness`）も同じ形で扱う。
- 使い方: `[DANGER_OK=1] bash scripts/claude/wt-remove.sh <ワークツリーのパス>`（旧 `<track>` 指定は廃止）
- 指定パスの realpath が `git worktree list` のどれとも一致しなければ exit 2（登録外のフォルダは消さない）。
- 現行の安全策は維持: primary 拒否・撤去対象の内側から実行したら拒否・未コミット変更で中止・未 push で中止・`down -v` 失敗時は remove しない・`--force` を使わない。
- **データ判定**（新規）:
  - Compose プロジェクト名＝撤去対象フォルダ名を小文字にし、英数字・`_`・`-` 以外を除いたもの（Compose の既定と同じ規則）。
  - 次の場合は名前を確定できないので「判定失敗」: 環境変数 `COMPOSE_PROJECT_NAME` がある／撤去対象の直下 `.env` に `COMPOSE_PROJECT_NAME=` がある／撤去対象の `docker-compose.yml` に最上位の `name:` がある。
  - `docker ps -a -q --filter label=com.docker.compose.project=<名前>` と `docker volume ls -q --filter label=com.docker.compose.project=<名前>` を実行。docker が無い・どちらかが失敗 → 判定失敗。
  - 両方とも空 → 「データ無し」: `down -v` を実行せず `git worktree remove` へ進む（`DANGER_OK` 不要）。
  - どちらかが空でない → 「データあり」／判定失敗 → 従来どおり `DANGER_OK=1` 必須 → `docker compose down -v` → `git worktree remove`。
- 撤去後にブランチは消さない（`git worktree remove` はブランチを残す・S8）。完了メッセージで「ブランチ `<名前>` は残っています」と表示する。
- **ロックの扱い**（2026-10-21 追加・S10）: 破壊的操作（`down -v`）より前に、`git worktree list --porcelain` の `locked` 行を調べる。
  - 理由が `claude session <name> (pid N ...)` で、`ps -p N` でプロセスが見つからない → 終了済みセッションの取り残しとして、`git worktree remove` の直前に `git worktree unlock` する（完了メッセージで解除を表示）。
  - プロセスが見つかる（使用中。pid の再利用も含め安全側に倒す）／理由がそれ以外・理由なし → exit 2 で中止し、終了または `git worktree unlock <パス>` の手順を表示する（何も消さない）。
```bash
detect_data() {   # 0=データ無し / 1=データあり / 2=判定失敗
  [ -n "${COMPOSE_PROJECT_NAME:-}" ] && return 2
  grep -q '^COMPOSE_PROJECT_NAME=' "$WT_PATH/.env" 2>/dev/null && return 2
  grep -q '^name:' "$WT_PATH/docker-compose.yml" 2>/dev/null && return 2
  command -v docker >/dev/null 2>&1 || return 2
  local c v
  c="$(docker ps -a -q --filter "label=com.docker.compose.project=$PROJECT")" || return 2
  v="$(docker volume ls -q --filter "label=com.docker.compose.project=$PROJECT")" || return 2
  [ -z "$c$v" ] && return 0
  return 1
}
```

### 4-7. `.claude/skills/plan-issue/SKILL.md`・`docs/runbooks/issue-flow.md` ステップ5（G）
**修正方針**: develop をチェックアウトせず、取得したリモートの develop から直接ブランチを作る（S7）。`--no-track` で、新ブランチの上流が `origin/develop` に自動設定されるのを防ぐ（直後の `git push -u` で正しい上流が付く）。
```bash
git fetch origin
git checkout --no-track -b feature/I${ISSUE_NUM}-[概要を英語化したもの] origin/develop
```
SKILL.md の見出し説明「developブランチをベースに」は「`origin/develop` をベースに（develop はチェックアウトしない。別ワークツリーが develop を使っていても失敗しないため）」に変える。未コミットの変更がある場合の注意（イシューファイル以外の未コミット変更は先に片付ける）を 1 行添える。

### 4-8. `.claude/skills/issue-bootstrap/SKILL.md` 70 行目・`docs/runbooks/issue-flow.md` 61・199 行目（A の消費箇所）
**修正方針**: トラックとワークツリーを 1 対 1 で結ぶ「（対応 worktree: wt-harness）」を外す。`wt-harness` は移行で無くなる予定で、トラックは今後ラベルで区別する（確定事項）。ラベルの判定基準の文言は変えない（`test_i107_track_label_docs.sh` の対象）。

### 4-9. `docs/runbooks/worktree.md`（A〜F・移行・検索の注意）
**修正方針**: 公式方式を標準手順にし、自作は公式に無い部分だけを書く。セクション構成（案）:
| 節 | 内容 |
|----|------|
| 冒頭 | 目的（変更なし）。「トラック＝作業の束。ワークツリー＝作業場所（1 トラックに複数可）」 |
| §1 用語 | 「トラック = 1 作業ツリー」を削除。トラックは GitHub ラベル（`track:harness` / `track:app`）で区別。primary＝ワークツリーの作成元（親）。入れ子ワークツリー（`<primary>/.claude/worktrees/<name>`）を追加 |
| §2 作り方 | 必ず primary で `claude --worktree <track>-<連番>`（例 `harness-2`）。理由（作成元フォルダの中に作られる・primary は撤去しない）。基点は公式既定（リモートの既定ブランチ＝develop）。初期ブランチ `worktree-<name>` は `/plan-issue` 後に不要なら削除してよい。終了時に「残すか」を聞かれたら、続けて使うワークツリーは「残す」を選ぶ。設定ファイルは `.worktreeinclude` が自動コピー。primary に `backend/.env` が無いとコピーされない |
| §3 次のイシューへ移る | 「未コミット変更を片付けてから `/plan-issue` を実行する」（B） |
| §4 撤去 | Docker を起動したワークツリー → primary から `bash scripts/claude/wt-remove.sh <パス>`（データがあれば `DANGER_OK=1`）。それ以外 → 公式の自動片付けに任せる。取り残しの発見と削除（`docker compose ls -a` で一覧 → 該当ワークツリーが無いプロジェクトは `docker compose -p <名前> down -v`＝破壊的操作・`DANGER_OK=1`） |
| §5 セットアップ（Docker） | 現 §5 を流用。`.env` コピーは `.worktreeinclude`、ポートは `wt-ports.sh`。(B)(C)(D) の注意は維持し、機械化の説明を新スクリプトに合わせる |
| §6 ポート分離 | 現 §6 の規則（表・STEP=10・primary=0）は維持。運用を「Docker 起動前に `wt-ports.sh` を 1 回」に変更。実行し忘れても Docker がポート衝突エラーで止まる旨 |
| §7 共有されるもの | 現 §7 に追加: git stash スタック（素の `git stash` / `git stash pop` 禁止・`git stash push -u -m "<タグ>"` → SHA で `git stash apply <sha>` → タグで探して drop）・git config（hooks 含む）（C）。入れ子配置の検索の注意（`grep -r` など gitignore を見ないコマンドでは `.claude/worktrees/` の中身が混ざる。`git grep`・Grep ツールは混ざらない） |
| §8 採番 | 「primary 固定」等の人手規律の記述は既に無い。「採番権威の単一化（`next-issue-num.sh`）」は維持 |
| §9 引き継ぎ | ガード説明に「入れ子では、パスを含む最も内側のワークツリーで判定」を追記 |
| §10 | 手書き表を削除。「現在の状態は `git worktree list` で確認」と、トラック⇔ラベル対応表（`track:harness` / `track:app` と対象の説明）だけを残す（D） |
| §11 旧方式からの移行 | 既存 `wt-harness`（`/mnt/c/app/wt-harness`）: そこで進めているイシュー（I178・I179）が完了・クローズした後に、primary から `bash scripts/claude/wt-remove.sh /mnt/c/app/wt-harness` で撤去し、必要なら primary で `claude --worktree harness-<連番>` で作り直す。primary は移行しない |
| 手動 fallback | 現 §3 の手動手順は、公式機能が使えない場合の fallback として `git worktree add <primary>/.claude/worktrees/<name> -b <ブランチ> origin/develop` ＋ `.env` の手動コピーに書き換えて残す |

### 4-10. `docs/runbooks/common-commands.md` 23〜26 行目（F の消費箇所）
**修正方針**: `wt-new.sh` の例を `bash scripts/claude/wt-ports.sh [--port-offset N]`（Docker 起動前に今いるワークツリーで 1 回）に置き換える。

### 4-11. テスト（詳細は `docs/tests/open/I179_auto_test.md`）
- `scripts/claude/tests/test_pretooluse_worktree_guard.sh`: 入れ子ワークツリーのケース（G1〜G7・FG-G1）を追加。既存 A1〜A23 は維持。
- `scripts/claude/tests/test_wt_port_offset.sh`: `wt-ports.sh` を対象に書き換え（P1〜P12・FG-P1）。runbook 文言の検査（DOC1）は `test_i179_worktree_docs.sh` へ移す。
- `scripts/claude/tests/test_wt_lifecycle.sh`: wt-new 部分（N1〜N10・C1・FG2・D1）を削除し、テスト用ワークツリーは `git worktree add` で直接作る。wt-remove のデータ判定（R0〜R11・FG3）を追加。既存 R1〜R8・FG1 は新しい引数形式で維持。
- `scripts/claude/tests/test_i179_worktree_docs.sh`（新規）: 文書・設定の存在/不在検査（D1〜D11）と失敗注入（FG-D1）。

## 5. 実装手順（ステップ）
1. **ステップ1（未知リスク先行: 入れ子ワークツリーで作業できること）**: `.gitignore` に `.claude/worktrees/` を追加、`.worktreeinclude` を新規作成、ガードを最長一致判定に修正し（4-1〜4-3）、ガードのテストに入れ子ケースを追加する。入れ子のワークツリーで自分のファイルを書けないと公式方式そのものが使えないため最初に置く。→ TC-G1〜G7・FG-G1・既存 A1〜A23 参照
   - I174（PR #293）が同じ `pretooluse_guard.py` を大きく改修中。I174 が先に develop へマージされた場合は、develop を取り込み直して衝突を解消し、ガードのテストを再実行する。
2. **ステップ2（ポート割当の切り出し）**: `wt-ports.sh` を新規作成し（4-4）、`test_wt_port_offset.sh` を書き換える。ステップ1と並行可能。→ TC-P1〜P12・FG-P1 参照
3. **ステップ3（撤去スクリプトの改修と wt-new の廃止）**: `wt-remove.sh` を改修（4-6）、`wt-new.sh` を削除（4-5）、`test_wt_lifecycle.sh` を書き換える。ステップ2の完了が前提（ポート割当の移植元を消すため）。→ TC-R0〜R11・FG1・FG3 参照
4. **ステップ4（ブランチ作成手順）**: `plan-issue/SKILL.md`・`issue-flow.md` ステップ5を変更（4-7）。他ステップと独立。→ TC-D5・D6・手動 M5 参照
5. **ステップ5（文書と消費箇所）**: `worktree.md`・`common-commands.md`・`issue-flow.md` 61/199 行目・`issue-bootstrap/SKILL.md` 70 行目を更新し（4-8〜4-10）、`test_i179_worktree_docs.sh` を作成する。ステップ1〜4の完了が前提（書く内容が実装に依存するため）。→ TC-D1〜D11・FG-D1・test_i107・test_next_issue_num 参照
6. **ステップ6（公式方式の実機確認）**: このブランチを scratchpad に clone した使い捨ての「primary 役」で、`claude --worktree`・サブエージェント・`wt-ports.sh`・`wt-remove.sh` を実際に動かす（実物の primary と `wt-harness` は触らない）。ステップ1〜5の完了が前提。→ 手動 M1〜M6 参照
7. **ステップ7（完了記録）**: `/close` 時に、完了記録へ「既存 `wt-harness` の移行（I178・I179 完了後）」と「ハーネス改善用 2 つ目のワークツリーの作成（本イシューの起点の要望）」を残作業として書く。→ 手動 M8 参照

## 6. テスト計画
### 自動
- テストレベル: すべてシェルの決定論テスト（使い捨て git リポジトリ＋docker のスタブ。実物の Docker データ・ワークツリーには触れない）。アプリのユニット/結合/E2E は対象外（アプリのコード変更なし）。
- 再発防止テスト: H（入れ子誤判定）は TC-G1/G2 が再発防止テスト。FG-G1 で旧ロジック（最初に一致した root で判定）に戻すと G1 が失敗することを確認する。
- 否定・不在系の TC はすべて失敗注入（FG-*）とセットにする。
- 詳細: `docs/tests/open/I179_auto_test.md`
### 手動
- 公式方式の実機確認（Claude・使い捨て clone）と、対話終了時の確認画面の目視（Human）。詳細: `docs/tests/open/I179_manual_test.md`
- 認可・テナント境界のテスト: 該当なし（アプリの認可変更なし）。代わりにワークツリー境界（ガード）のブロック/許可を TC-G で検証する。

## 7. ロールバック
- 本 PR を revert すれば元に戻る（`wt-new.sh` も git 履歴から復元される）。
- 個別に戻す場合: ガードは `_owning_root` 導入前の 2 関数に戻す。`wt-remove.sh` はデータ判定の分岐を外せば「常に `DANGER_OK=1` 必須」に戻る（データには影響しない）。
- 公式方式で作ったワークツリーは、通常の `git worktree remove`（Docker 使用時は先に `docker compose down -v`）で片付けられる。

## 8. Risk & 回避策
| リスク | 回避策 |
|-------|-------|
| I174 と `pretooluse_guard.py` が衝突する | 変更は 2 関数の判定部分だけに留める。I174 が先にマージされたら develop を取り込み直してガードのテストを再実行（ステップ1） |
| `wt-remove.sh` のデータ判定が「無し」と誤判定して volume を消し漏らす／消してはいけないものを消す | 誤判定しても「無し」側は `down -v` を実行しない（データを消さない）だけで、消す操作は常に `DANGER_OK=1` が要る。名前を確定できない条件（`COMPOSE_PROJECT_NAME`・`name:`）と docker の失敗はすべて「判定失敗＝許可必須」にする |
| Compose のラベルが付かない匿名 volume（`-v` なしで `down` した後など）は判定に出ない | 匿名 volume は Postgres 等の名前付きデータではない。`worktree.md` の取り残しの手順に `docker volume ls -f dangling=true` で確認できることを書き、削除は破壊的操作として `DANGER_OK=1` の手順に従う旨を書く |
| `.worktreeinclude` は primary に `backend/.env` が無いと黙ってコピーしない | `wt-ports.sh` が Docker 起動前に `backend/.env` の有無を確かめて止める（4-4） |
| 公式機能の仕様が今後変わる（自動片付けの条件・ブランチ名など） | 手動 M1・M3・M6 で 2.1.304 の挙動を確認して記録。`worktree.md` には公式文書へのリンクを置き、細かい仕様は書き写さない |
| `claude --worktree` を primary 以外で実行すると、その中に入れ子が作られ、外側を撤去すると巻き込まれる | `worktree.md` §2 に「必ず primary で作る」と理由を書く。`wt-remove.sh` は `git worktree remove` を `--force` なしで使うため、中に別ワークツリーがあれば git が拒否する |

## Danger Ops（有）
- **何を**: `wt-remove.sh` の `docker compose down -v`（named volume の削除）に `DANGER_OK=1` を求める条件を「常に」から「当該 Compose プロジェクトのコンテナ・named volume が 1 つでもある場合、または判定に失敗した場合」に変える。
- **なぜ**: 消すデータが無いワークツリーの撤去にまで破壊的操作の許可を求めており、許可の意味が薄れている。
- **どう承認**: 本計画書の承認ポイントで明示承認を得る。データがあるときの `DANGER_OK=1` 必須は維持し、`docs/runbooks/danger-ops.md`（破壊的操作は承認制）と矛盾しない。データ無しのときは `down -v` 自体を実行しない（破壊的操作が起きない）。
- **ロールバック**: 判定分岐を外せば従来挙動に戻る。データには影響しない。
- **本イシューで実データは消さない**: 既存 `wt-harness` の実撤去は残作業。テストは docker のスタブで行い、実物のコンテナ・volume には触れない。手動 M4 は Docker を起動していない使い捨てワークツリーで行う。

## 各観点の該当判定
- **要件適合性**: 変更はイシューの確定事項の範囲内。イシューに無い追加は「設計判断の明示」の「仮定で決めた」項目として承認ポイントで確認する。マルチテナント・ステータス遷移: 該当なし。
- **セキュリティ**: アプリのコード変更なし。ハーネスの安全装置（ガード）の判定を変えるため、許可が広がるのは「入れ子ワークツリーが自分自身に書く」場合だけであることを TC-G1〜G7 で、fail-safe と `DANGER_OK` 非解除が保たれることを既存 A18・A19 で確認する。秘密情報（`backend/.env`）は公式機能が gitignore 済みのままコピーするだけで、中身は読まない。`.claude/worktrees/` は Docker のビルドコンテキスト外（`./backend`・`./frontend` のみ）でイメージに入らない。依存ライブラリの追加なし。bandit / npm audit の対象コード変更なし。
- **P3/P5/P8（データ整合性・運用・コスト）**: 影響なし（DB・外部 API・インフラの追加なし。運用者の手作業は wt-new の代わりに wt-ports を 1 回実行するだけで増えない）。
- **P6（性能・UX）**: 影響なし（UI なし）。
- **P9（プライバシー）**: 影響なし（個人情報・テナントデータを扱わない）。
- **設計品質**: 定数（ポート base・STEP）は `wt-ports.sh` 冒頭で定義（現行と同じ）。エラーは「exit 2＋理由と次の操作を stderr に表示」で統一（現行スクリプトと同じ）。

## 9. 承認ポイント
- [x] 計画内容（変更点/影響）: 4-1〜4-11 の変更
- [x] 設計判断（下表の「仮定」項目の可否）
- [x] Danger Ops（`wt-remove.sh` の許可条件の変更・本イシューで実データは消さない）
- [x] テスト計画（自動 TC と手動 M1〜M8・実機確認は使い捨て clone で行う）

### 設計判断の明示
| 設計判断 | 根拠 |
|---------|------|
| 人が使うワークツリーは primary で `claude --worktree <track>-<連番>` | イシューに明記 |
| `.worktreeinclude` に `backend/.env`・`e2e/.env.e2e` | イシューに明記 |
| WorktreeCreate / WorktreeRemove フックを使わない | イシューに明記 |
| `wt-new.sh` 廃止・`wt-ports.sh` 新設・規則は I097 のまま | イシューに明記 |
| `wt-remove.sh` のデータ無しなら許可不要・あり/判定失敗なら必須・ブランチは残す | イシューに明記 |
| ガードは最長一致 root で判定 | イシューに明記 |
| `/plan-issue`・ステップ5は `git fetch origin` ＋ `origin/develop` 基点 | イシューに明記 |
| `.gitignore` に `.claude/worktrees/` | イシューに明記 |
| `wt-remove.sh` の指定方法を「登録済みワークツリーのパス」に変え、旧 `<track>` 指定は廃止 | 仮定 → 2026-10-20 承認（下記「承認記録」） |
| `wt-ports.sh`: primary では止める／割当済みなら何もしない／ポート以外の行は残して追記 | 仮定 → 2026-10-20 承認（下記「承認記録」） |
| `wt-ports.sh`: `backend/.env` が無ければ止める（イシューでは「受容する小さな危険」だった点を防ぐ） | 仮定 → 2026-10-20 承認（下記「承認記録」） |
| `wt-remove.sh`: `COMPOSE_PROJECT_NAME`・最上位 `name:` があれば「判定失敗」扱い。プロジェクト名はフォルダ名を Compose と同じ規則で変換 | 仮定 → 2026-10-20 承認（下記「承認記録」） |
| ブランチ作成に `--no-track` を付ける | 仮定 → 2026-10-20 承認（下記「承認記録」） |
| `issue-bootstrap/SKILL.md`・`issue-flow.md` の「（対応 worktree: wt-harness）」を外し、`common-commands.md` も更新する（イシューの実装対象表に無い消費箇所） | 仮定 → 2026-10-20 承認（下記「承認記録」） |
| 文書検査を新規テスト `test_i179_worktree_docs.sh` にまとめる | 仮定 → 2026-10-20 承認（下記「承認記録」） |
| 公式方式の実機確認は、このブランチを clone した使い捨ての primary 役で行う（実物の primary は I174 作業中のため触らない） | 仮定 → 2026-10-20 承認（下記「承認記録」） |

### 承認記録（2026-10-20）
- ユーザー指示: 「ループエンジニアリング、ハーネスエンジニアリングのベストプラクティスとして、理想的・最適なものを基準として問題なければ進めて OK」。
- 上表の「仮定」8 項目を理想基準で再評価し、すべて変更なしで採用した。

| 項目 | 理想基準での評価 |
|------|----------------|
| `wt-remove.sh` をパス指定に | 採用。公式配置と旧配置を 1 つの形で扱え、`git worktree list` との照合で登録外のフォルダを消す経路を構造的に無くせる（名前からの推測は配置が 2 種あるため曖昧さが残る） |
| `wt-ports.sh` の primary 拒否・冪等・既存行保持 | 採用。2 回実行しても壊れない（冪等）ことはループで繰り返し呼ばれるスクリプトの前提。primary=offset 0 の規約を機械で守れる |
| `wt-ports.sh` の `backend/.env` 検査 | 採用。「黙って insecure 起動」は人が気づけない失敗で、Docker 起動直前に決定論で止めるのが最小コストの根治（受容リスクを解消） |
| `COMPOSE_PROJECT_NAME`・`name:` を判定失敗扱い | 採用。破壊的操作の判定は fail-closed が原則。名前を確定できない時に「無し」へ倒す経路を作らない |
| `--no-track` | 採用。上流の誤設定（`git pull` が develop を取り込む）という静かな不具合を作らない |
| `wt-harness` 固定表記の除去・`common-commands.md` 更新 | 採用。規約変更時の消費箇所の全件更新（plan-writing-rules）に従う。残すと文脈ゼロの担当者が旧構成で動く |
| 文書検査を専用テストに集約 | 採用。手続き（読んで確認）より決定論ゲートを優先する方針。失敗注入を内蔵し false-green を防ぐ |
| 実機確認は使い捨て clone | 採用。トラック/セッション境界を守りつつ、同じ設定・同じ CLI で実物と同じ挙動を観測できる |

### 計画変更記録（2026-10-21・実装ステップ6で発見）
- **何を**: 4-6 `wt-remove.sh` に「ロックの扱い」を追加（終了済みの Claude セッションのロックだけ外す・使用中/その他は中止）。`worktree.md` §2・§4 にロックの説明を追加し、Docker を使っていないワークツリーの取り残しも `wt-remove.sh` で撤去する案内に変更。テストに R13〜R15・FG4・D3 の `git worktree unlock` を追加。
- **なぜ**: S10 のとおり、公式方式で作ったワークツリーは終了後もロックが残る場合があり、変更前の計画では受け入れ条件「公式配置も撤去でき」を満たせない。
- **理想基準での評価**: 採用。ロックは「使用中のワークツリーを消させない」ための公式の安全装置なので、無条件に外す（`remove -f -f`）のは不可。外してよいのは「ロックしたプロセスが存在しない」と機械で確かめられる場合だけにし、それ以外は破壊的操作の前に止める（fail-closed）。pid の再利用で使用中と誤判定しても「止まる」側に倒れるだけで、データは消えない。
- **承認**: ユーザーの既定基準（「ループエンジニアリング、ハーネスエンジニアリングのベストプラクティスとして、理想的・最適なものを基準として問題なければ進めて OK」・2026-10-20）に基づき実装し、事後報告する。計画変更のため `/code-review` の前に `/plan-issue-review I179` を挟む。

## レビュー結果
- [20261020_1950 判定: ✅ 完了](../../reviews/I179_plan_review_20261020_1950.md)
  - Warning（D2・D10・D11 の不在チェックに失敗注入が無い）と Info（D9 に失敗注入が無い）は、`I179_auto_test.md` の FG-D1 に 4 通りの注入を追加して対応済み（6 → 10 通り）。
  - Info（実機確認をステップ6に置く理由）は計画書の記載どおりで変更不要。
