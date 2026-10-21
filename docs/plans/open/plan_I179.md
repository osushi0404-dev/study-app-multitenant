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
- [ ] ~~ガード（計画変更記録 5）: 別のワークツリーを消す・変更を捨てる Bash 操作と相対パス・`cd` 越しの書込をブロック~~ → **計画変更記録 6 で廃止**。代わりに `git clean` で `f` を 2 つ以上重ねる形だけ `DANGER_OK=1` 必須にし（失敗注入あり → TC-GC1〜GC7・FG-GC1）、ほかは §9 の運用（こまめな commit/push・`wt-remove.sh`・別ワークツリーの中身を消さない）と GitHub の保護に任せる
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
  - 変更: `.gitignore`・`scripts/claude/wt-remove.sh`・`scripts/claude/hooks/pretooluse_guard.py`・`.claude/skills/plan-issue/SKILL.md`・`.claude/skills/issue-bootstrap/SKILL.md`・`docs/runbooks/worktree.md`・`docs/runbooks/issue-flow.md`・`docs/runbooks/common-commands.md`・`docs/runbooks/danger-ops.md`（2026-10-21 追加・4-12）・`scripts/claude/tests/test_wt_lifecycle.sh`・`scripts/claude/tests/test_wt_port_offset.sh`・`scripts/claude/tests/test_pretooluse_worktree_guard.sh`
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
> このファイルには計画変更記録 2〜5 の変更も入る（詳細は各記録）: ①Docker の volume 削除（`down -v`・`volume rm/prune`・`system prune --volumes`）を `DANGER_OK=1` 必須に＝正規表現（空白をまとめた文字列）∪トークン判定（記録 2〜4・5 の対応済み分）②別ワークツリーの削除・破棄（`_bash_destroy_targets`）③相対パスと `cd` を反映した書込・削除の判定 ④`/mnt/<ドライブ>/` 配下の大文字小文字を区別しない所有者判定（②〜④は記録 5）。**②③は計画変更記録 6 で廃止**（`git clean -ff` の承認制だけ残す）。

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
**修正方針**: 作成は公式の `claude --worktree`、設定ファイルのコピーは `.worktreeinclude`、ポートは `wt-ports.sh` が受け持つため、役目が無くなる。`origin/develop` 基点の保証は公式の `worktree.baseRef` 既定（`"fresh"`＝`origin/<既定ブランチ>`）が受け持つ。既定ブランチは手元の `refs/remotes/origin/HEAD` で決まるため、`worktree.md` §2 の「作る前の確認」で `origin/develop` を指すことを確かめる（2026-10-21 敵対的レビューで訂正）。

### 4-6. `scripts/claude/wt-remove.sh`（E）
**修正方針**: 消すデータが無いワークツリーは許可なしで撤去でき、データがあるときだけ従来どおり `DANGER_OK=1` を求める。消す相手を確定できないとき（名前の指定・作業フォルダが別・同名の別ワークツリー）は `DANGER_OK=1` でも止め、docker が使えないときは止めて `KEEP_DATA=1` でだけ消さずに撤去する（2026-10-21 敵対的レビューで改訂・下の表）。撤去対象は「`git worktree list` に登録されたワークツリーのパス」で指定し、公式配置（`<primary>/.claude/worktrees/<name>`）も旧配置（`/mnt/c/app/wt-harness`）も同じ形で扱う。
- 使い方: `[DANGER_OK=1] bash scripts/claude/wt-remove.sh <ワークツリーのパス>`（旧 `<track>` 指定は廃止）
- 指定パスの realpath が `git worktree list` のどれとも一致しなければ exit 2（登録外のフォルダは消さない）。
- 現行の安全策は維持: primary 拒否・撤去対象の内側から実行したら拒否・未コミット変更で中止・未 push で中止・`down -v` 失敗時は remove しない・`--force` を使わない。
- **データ判定**（新規・2026-10-21 敵対的レビュー第 1・2 周で改訂）:
  - Compose プロジェクト名（既定名）＝撤去対象フォルダ名を小文字にし、英数字・`_`・`-` 以外を除き、先頭の `_`・`-` を除いたもの（Compose の既定と同じ規則）。
  - `docker ps -a -q`・`docker volume ls -q` を `--filter label=com.docker.compose.project=<既定名>` で実行し、戻り値を次の 5 通りにする（`detect_data`）。
    | 戻り値 | 条件 | 扱い |
    |-------|------|------|
    | 0 データ無し | 両方とも空 | `down -v` を実行せず撤去（`DANGER_OK` 不要） |
    | 1 データあり | どちらかが空でない（かつ下の 4 に当たらない） | `DANGER_OK=1` 必須 → `docker compose -p <既定名> down -v`（撤去対象のフォルダで実行・`-p` で消す相手を固定） |
    | 2 名前を確定できない | 環境変数 `COMPOSE_PROJECT_NAME`／直下 `.env` の `COMPOSE_PROJECT_NAME`・`COMPOSE_FILE`（`export`・空白・`=`/`:` 区切り）／compose ファイル 8 種の最上位 `name:`／既定名が空 | **`DANGER_OK=1` でも中止**（何も消さない。指定を外して再実行） |
    | 3 docker が使えない | `docker` コマンドが無い／`ps`・`volume ls` が失敗 | 中止。`KEEP_DATA=1`（`DANGER_OK` とは別の合図）のときだけ `down -v` をせずに撤去（データは残す） |
    | 4 作業フォルダが別 | コンテナの `com.docker.compose.project.working_dir` ラベルが撤去対象と違う | **`DANGER_OK=1` でも中止** |
  - 既定名が別のワークツリー（フォルダが存在するもの）の既定名と同じで、戻り値が 1・2・4 のときは **`DANGER_OK=1` でも中止**（データの持ち主を区別できない）。
  - データありで止めたときのバックアップ案内は、撤去対象のプロジェクトを `-p` で指定した `pg_dump` を primary で実行する具体的なコマンドにする（`scripts/db_backup.sh` は今いるフォルダのプロジェクトが対象のため使えない）。
- 撤去後にブランチは消さない（`git worktree remove` はブランチを残す・S8）。完了メッセージで「ブランチ `<名前>` は残っています」と表示する。
- **入れ子の検査**（2026-10-21 追加・敵対的レビュー第 1 周）: 撤去対象の中に、`git worktree list` の登録済みワークツリー（フォルダが存在するもの）か、深さ 2 以上の `.git` があれば中止する（`.claude/worktrees/` は gitignore 済みのため、`git status` にも `git worktree remove` にも引っかからず、中身ごと消えてしまう）。フォルダが既に無い登録（prunable）は数えず、案内に `git worktree prune` を出す。
- **ロックの扱い**（2026-10-21 追加・S10）: 破壊的操作（`down -v`）より前に、`git worktree list --porcelain` の `locked` 行を調べる。
  - 理由が `claude session <name> (pid N ...)` で、`/proc/N` も `ps -p N` も見つからない → 終了済みセッションの取り残しとして、`git worktree remove` の直前に `git worktree unlock` する（完了メッセージで解除を表示）。
  - プロセスが見つかる（使用中。pid の再利用も含め安全側に倒す）／`ps` が無く確認できない／理由がそれ以外・理由なし → exit 2 で中止し、終了または `git worktree unlock <パス>` の手順を表示する（何も消さない）。
- **処理の順番**（どこで止まっても、それより後の操作は行わない）:
  1. 引数の検査・登録済みワークツリーとの照合（登録外は exit 2）
  2. primary 拒否・内側からの実行拒否
  3. 未コミット変更・未 push の検査（あれば exit 2）
  4. 入れ子の検査（あれば exit 2）
  5. ロックの判定（使用中・確認できない・その他の理由は exit 2。終了済みセッションのロックは「後で外す」と記録するだけ）
  6. データ判定と同名の検査（上の表。0 → 7 を飛ばす／1 → `DANGER_OK=1` が無ければ exit 2／2・4・同名 → exit 2／3 → `KEEP_DATA=1` が無ければ exit 2、あれば 7 を飛ばす）
  7. `docker compose -p <既定名> down -v`（撤去対象のフォルダで実行。失敗したら exit 2・remove しない）
  8. 終了済みセッションのロックを `git worktree unlock`
  9. `git worktree remove`（`--force` なし）→ 完了メッセージ（ロック解除・残ったブランチ名）
  - 例: 「データ無し・終了済みのロック」（TC-R13）は 1〜5 → 6 で「無し」→ 8 → 9。

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

### 4-12. `docs/runbooks/danger-ops.md`（2026-10-21 追加・計画変更記録 4）
**修正方針**: 「Docker」の例に、ガードが新たに止める `volume rm / prune`・`system prune --volumes` と、ワークツリーの撤去は `wt-remove.sh` を使い、消す相手を確定できない場合は許可があっても止まること（`worktree.md` §4 への参照）を加える。docker が使えないときに消さずに撤去する合図は `KEEP_DATA=1`（`DANGER_OK` とは別・消す操作の許可ではない）であることも 1 行で書く。→ TC-D12

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
- 公式方式で作ったワークツリーは、`wt-remove.sh` で片付けられる（`git worktree remove` は直接使わない＝§9）。PR を revert した後は `wt-remove.sh` の入れ子検査も無くなるため、`git worktree remove` の前に必ず `git worktree list` と `find <ワークツリー> -mindepth 2 -name .git` で中に入れ子（登録の無い `.git` を含む）が無いことを確かめる（gitignore 済みの入れ子は `--force` なしでも未コミットの作業ごと消える）。Docker 使用時は先に、`docs/runbooks/danger-ops.md` に従い承認を得て `DANGER_OK=1 docker compose -p <名前> down -v`。

## 8. Risk & 回避策
| リスク | 回避策 |
|-------|-------|
| I174 と `pretooluse_guard.py` が衝突する | 変更は 2 関数の判定部分だけに留める。I174 が先にマージされたら develop を取り込み直してガードのテストを再実行（ステップ1） |
| `wt-remove.sh` のデータ判定が「無し」と誤判定して volume を消し漏らす／消してはいけないもの（primary・別のワークツリー）を消す | 誤判定しても「無し」側は `down -v` を実行しない（データを消さない）だけで、消す操作は常に `DANGER_OK=1` が要る。`down -v` は `-p <既定名>` で相手を固定し、名前を確定できない・作業フォルダが別・同名の別ワークツリーがある場合は `DANGER_OK=1` でも実行しない（4-6 の表） |
| Compose のラベルが付かない匿名 volume（`-v` なしで `down` した後など）は判定に出ない | 匿名 volume は Postgres 等の名前付きデータではない。`worktree.md` の取り残しの手順に `docker volume ls -f dangling=true` で確認できることを書き、削除は破壊的操作として `DANGER_OK=1` の手順に従う旨を書く |
| `.worktreeinclude` は primary に `backend/.env` が無いと黙ってコピーしない | `wt-ports.sh` が Docker 起動前に `backend/.env` の有無を確かめて止める（4-4） |
| 公式機能の仕様が今後変わる（自動片付けの条件・ブランチ名など） | 手動 M1・M3・M6 で 2.1.304 の挙動を確認して記録。`worktree.md` には公式文書へのリンクを置き、細かい仕様は書き写さない |
| `claude --worktree` を primary 以外で実行すると、その中に入れ子が作られ、外側を撤去すると巻き込まれる | `worktree.md` §2 に「必ず primary で作る」と理由を書く。~~`git worktree remove` が拒否する~~（誤り。`.claude/worktrees/` は gitignore 済みのため git は拒否せず中身ごと消す・2026-10-21 敵対的レビュー）→ `wt-remove.sh` が撤去前に中の入れ子（登録済み・未登録の `.git`）を検出して止める |

## Danger Ops（有）
- **何を**: `wt-remove.sh` の `docker compose down -v`（named volume の削除）の条件を次のように変える（2026-10-21 敵対的レビュー第 1・2 周で改訂）。
  - データ無し（当該プロジェクトのコンテナ・named volume が 0）→ `down -v` を実行しない（許可不要）。
  - データあり → 従来どおり `DANGER_OK=1` 必須。実行は `docker compose -p <既定名> down -v` で、消す相手を撤去対象のプロジェクトに固定する。
  - 消す相手を確定できない（名前の指定・作業フォルダのラベルの不一致・同名の別ワークツリー）→ `DANGER_OK=1` でも実行しない。
  - docker が使えない → 実行できないので中止。`KEEP_DATA=1` のときだけ、`down -v` をせずにワークツリーだけ撤去する（データは消えずに残る。`DANGER_OK` は「消す」専用の合図のまま、「消さずに撤去」には別の合図を使う）。
  - ガード（`pretooluse_guard.py`）: `docker compose … down -v`（グローバルオプション・`-p`・クォート・短縮結合・`sh -c` を含む）と `docker volume rm/remove/prune`・`docker system prune --volumes` を `DANGER_OK=1` 必須にする（取り残しの片付け手順の二重ガード）。
- **なぜ**: 消すデータが無いワークツリーの撤去にまで破壊的操作の許可を求めており、許可の意味が薄れている。一方で、許可を出したときに消える相手が撤去対象以外（primary など）になる経路は、許可の意味を壊すので構造的に無くす。
- **どう承認**: 本計画書の承認ポイントで明示承認（2026-10-20）。敵対的レビュー対応の改訂は既定基準（理想・最適で問題なければ進めて OK）に基づき実装し事後報告。いずれも「消す範囲を狭める／消す前に止める」方向で、`docs/runbooks/danger-ops.md`（破壊的操作は承認制）と矛盾しない。
- **ロールバック**: 判定分岐を外せば従来挙動（常に `DANGER_OK=1` 必須）に戻る。データには影響しない。
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
| `wt-remove.sh` のデータ無しなら許可不要・あり/判定失敗なら必須・ブランチは残す | イシューに明記（2026-10-21 改訂: 消す相手を確定できなければ許可があっても停止・docker 不在は `KEEP_DATA=1`・`-p` 固定。計画変更記録 2・3・4） |
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

### 計画変更記録 2（2026-10-21・敵対的レビュー第 1 周の findings 対応）
敵対的レビュー（`docs/reviews/I179_adversarial_review_20261021_*.md`）の High 4 件・Medium・Low への対応。いずれも fail-closed（安全側）の追加で、許可を広げる変更は「docker が使えない環境で `DANGER_OK=1` のとき `down -v` をせずに撤去する」1 点のみ（データは消さずに残す方向）。
| 変更 | 内容 | 起点 |
|------|------|------|
| `worktree.md` §2「作る前の確認」 | 公式の基点は手元の `refs/remotes/origin/HEAD` で決まる（実物は `origin/main`＝空ツリー）。`git symbolic-ref` で確認し、違えば `git remote set-head origin --auto`。primary のブランチが I179 以降であることの確認も追加 | High（基点） |
| `wt-remove.sh` 撤去前チェック（3）入れ子 | 撤去対象の中に登録済みのワークツリー・未登録の `.git` があれば中止（gitignore 済みの入れ子は git が拒否せず中身ごと消すため。計画 Risk 表の前提を訂正） | High（入れ子の巻き込み） |
| `pretooluse_guard.py` | `docker compose <グローバルオプション> down -v` と `docker volume rm/prune`・`docker system prune --volumes` を `DANGER_OK=1` 必須にする（取り残しの片付け手順の二重ガード） | High（ガードの抜け） |
| `test_wt_lifecycle.sh` | docker スタブが実行フォルダを記録し、`down -v` が撤去対象の中で走ることを検証（R3b・FG5） | High（テストの false-green） |
| `wt-remove.sh` データ判定 | `.env` の `export`/空白付き `COMPOSE_PROJECT_NAME`・`COMPOSE_FILE`、`compose.yaml`・override の `name:` も「名前を確定できない」に。docker が使えない場合を別の戻り値（3）にし、`DANGER_OK=1` なら `down -v` をせずに撤去（データは残る）。同じプロジェクト名の別ワークツリーがあり、データがあれば `DANGER_OK=1` でも中止 | Medium・Low |
| `wt-remove.sh` ロック | `ps` が無ければ中止（生存を確認できないときに「終了済み」へ倒さない）。`/proc/<pid>` でも生存を確認 | Medium |
| `wt-ports.sh` | 他のワークツリーの `.env` に無いポート変数は既定ポートとして数える（primary の `.env` にポート以外の行しか無い場合の衝突見逃し） | Low |
| `worktree.md` §2・§6・§9・§11 | セッションを別ウィンドウで開く手順を復元、§6 の例を各ワークツリーのセッションで実行する形に、§9 に入れ子での作業フォルダ判定の限界、別環境（Windows 側）の Claude のロックの限界、§11 に wt-harness の untracked ファイル（イシューファイル等）を primary へ移す手順 | Medium・Low |
| `test_i179_worktree_docs.sh` | 不在チェックは対象ファイルの存在も条件にする（ファイル削除で PASS しない）。FG-D1 にファイル削除の注入 3 通りを追加 | Low |
- **理想基準での評価**: 採用。いずれも「人が気づけない失敗を決定論で止める」方向で、ガードとスクリプトの安全性を上げる。ガードの既知の限界（入れ子での作業フォルダ判定）は、代わりの判定（`CLAUDE_PROJECT_DIR`）がサブエージェントを壊すため、文書で限界を明示して受容する。
- **承認**: 既定基準（2026-10-20）に基づき実装し事後報告。計画変更のため、敵対的レビュー通過後に `/plan-issue-review I179` を挟む。

### 計画変更記録 3（2026-10-21・敵対的レビュー第 2 周の findings 対応）
| 変更 | 内容 | 起点 |
|------|------|------|
| `wt-remove.sh` の `down -v` | `docker compose -p <既定名> down -v` で消す相手を固定。名前を確定できない（戻り値 2）・作業フォルダのラベルが別（4・新規）・同名の別ワークツリーは `DANGER_OK=1` でも中止 | High（DANGER_OK で別プロジェクトを消す経路） |
| `wt-remove.sh` の docker 不在 | `DANGER_OK=1` で「消さずに撤去」する経路を廃止し、`KEEP_DATA=1` に分離（`DANGER_OK` は消す専用） | High（合図の二重の意味） |
| `wt-remove.sh` のバックアップ案内 | `scripts/db_backup.sh`（今いるフォルダが対象）ではなく、撤去対象を `-p` で指定した `pg_dump` を primary で実行するコマンドを表示 | High（バックアップが効かない） |
| `wt-remove.sh` その他 | prunable な登録を入れ子・同名の検査から除外し `git worktree prune` を案内・`.env` の `:` 区切りも検出・先頭行の取得をパイプから展開に（pipefail の SIGPIPE） | Medium・Low |
| `pretooluse_guard.py` | Docker の volume 削除の判定を正規表現からトークン判定（`_docker_volume_wipe`）に置き換え。docker 本体のオプション・クォート・短縮結合（`-vt`）・`sh -c`/`eval`・改行/`&`/サブシェルの後を捕捉し、コミットメッセージ・grep の引数・ヒアドキュメントの本文は誤ブロックしない。`docker volume remove`・`system prune --volumes` も対象 | Medium・Low |
| `wt-ports.sh` | 他のワークツリーの `.env` の `export`・空白・クォート付きの値も読む | Low |
| `worktree.md` | §2 確認 1 の未設定時（fatal）と共有 ref の注記・確認 2 にガードの確認を追加、§4 を `-p` 固定・中止条件・`KEEP_DATA=1`・バックアップ手順に更新、§11 にクローズ済みイシューの除外・gitignore 済みファイル（`settings.local.json`）の扱い・`--untracked-files=all` | Medium・Low |
| テスト | R1c2・R20a/R20c・R21・R22/R22b・R23・compose ファイル 8 種と `name :`・行頭空白・DV10〜DV23・FG-DV1（判定関数の除去）・P15、ckhas/cknot をヒアストリング化（pipefail の誤判定防止）、R23 の判定を行全体一致に | Medium・Low |
- **理想基準での評価**: 採用。破壊的操作は「消す相手を構造的に固定し、確定できなければ許可があっても止める」が原則で、許可（`DANGER_OK`）の意味を「この撤去対象のデータを消す」の 1 つに保つ。
- **承認**: 既定基準（2026-10-20）に基づき実装し事後報告。

### 計画変更記録 4（2026-10-21・fix-loop＝敵対的レビュー第 3 周の findings 対応）
- 診断: `docs/reviews/I179_fix_diagnosis_20261021_0220.md`（診断レビュー PASS）。ユーザー指示「理想的・最適なものを基準として問題なければ進めて OK」により案 A を採用。
| 変更 | 内容 | 起点 |
|------|------|------|
| `pretooluse_guard.py` | Docker の volume 削除の判定を「(1) 生の文字列への正規表現 ∪ (2) トークン判定」の和集合にする。(1) は develop の規則を土台に、compose のグローバルオプション・短縮結合・`docker.exe`・`volume rm/remove/prune`・`system prune --volumes` を追加。(2) は (1) が取りこぼす docker 本体のオプション・クォートだけを補う。ヒアドキュメント除外は撤回。トークン判定の `down` はサブコマンドの位置だけを見る | High 2 件（後退・ヒアドキュメントの穴） |
| テスト | DV-sh（第 3 周の再現入力 28 形）・DV-tok（トークン層でしか捕まらない形を前置コマンド・eval・& の後で）・NOREG（develop のガードで止まる入力は今も止まる）・FG-DV2/FG-DV3（各層が停止要因である証明）・R21b〜d・R22c・P15a〜e・バックアップ案内の検証 | High・Medium |
| `wt-remove.sh` | バックアップ案内を「`up -d db` → `-p` 付き `pg_dump` → `test -s` で空でないことを確認」の 3 手順に、再実行の案内を `bash <スクリプト>` の形に | Medium・Low |
| 文書 | イシュー（受け入れ条件・Danger Ops ほか）に改訂を注記・`danger-ops.md` の Docker の例・`worktree.md` §4「止まったときの片付け」・取り残し手順の条件・§5(C)・§11（コピーしない untracked の削除・未 push の入れ子）・計画 4-6 冒頭と設計判断表 | Medium |
- 受容（誤ブロック）: 正規表現の層は、コミットメッセージや grep の引数の中の文字列でも止める（develop から続く既知の種類。安全装置が後退しないことを優先。`DANGER_OK=1` 前置か言い換えで解ける）。`down --volumes=false` も安全側で止める。
- 理想基準での評価: 採用。安全装置の判定方式の変更は「旧方式で止まる入力は新方式でも止まる」を機械で保証してから行う（NOREG を常設）。

### 計画変更記録 5（2026-10-21・敵対的レビュー第 4 周＝2 回目の /code-review の第 1 周の findings 対応）
- 記録: `docs/reviews/I179_adversarial_review_<第 4 周以降>.md`。ユーザー判断（2026-10-21）: 「別のワークツリーを消す・捨てる操作」は注意書きではなく I179 の中でガードで止める（危険は I179 の入れ子配置が生むため）。進め方は既定基準（理想・最適で問題なければ OK・サクサク進める）。
- 対応済み（コミット e7a1842）: Docker の volume 削除の正規表現の層を、develop と同じく空白（改行・行継続）をまとめた文字列に当てる（High: `docker compose down \⏎ -v` が前置コマンド等と組むと素通り＝後退）。DV-sh・NOREG に行継続の形と `bash -c "$(cat <<'EOF' …)"` を追加。

| 変更 | 内容 | 起点 |
|------|------|------|
| `pretooluse_guard.py`: 別ワークツリーの削除・破棄（新規 `_bash_destroy_targets`） | セグメントごとに次を「対象パス」として取り出し、`_owning_root` で所有者が現ワークツリー以外、または対象の中に別のワークツリーの root がある（例: primary で `rm -r .claude`）ならブロック。①`rm`（オプションの形を問わず非オプション引数すべて）②`find` の開始パス（`-delete` または `-exec`/`-execdir` に `rm` があるとき）③`git -C <dir>`・`--git-dir`・`--work-tree` が別ワークツリーを指し、サブコマンドが読み取り系の許可リスト（status・log・diff・show・rev-parse・ls-files・branch・worktree list・config --get 等）以外 ④`git clean` で `f` が 2 個以上（`-ff`・`-f -f`・`-fdf`）かつ実行場所の中に別のワークツリーの root がある ⑤`git worktree remove`（当初は `-f`/`--force` があるときだけ→第 5 周改訂で `--force` の有無を問わず） | High（③観点：入れ子配置で他ワークツリーの未コミット作業が消える） |
| `pretooluse_guard.py`: 相対パスと `cd` | 書込先（既存 `_bash_write_targets`）と上の削除・破棄の対象は、相対パスも「実効の作業フォルダ」基準で絶対パスにして判定する。実効の作業フォルダは、同じコマンド内の前のセグメントの `cd <固定のパス>` を反映する（`cd` の引数に変数・置換があれば以降は判定不能として既存の警告のみ） | High（同上・相対パスで入れ子へ書ける） |
| `pretooluse_guard.py`: 大文字小文字 | `/mnt/<ドライブ>/` 配下（drvfs）は大文字小文字を区別せずに所有者を判定する | Medium（①観点） |
| 解除の扱い | 書込の横断ガードと同じく `DANGER_OK=1` でも解除しない（正規の撤去は `wt-remove.sh`。スクリプト内部のコマンドはガードの対象外）。メッセージで §9 と `wt-remove.sh` を案内 | 設計 |
| 対象外（§9 に「止められないもの」として明記） | 変数・コマンド置換・`eval`/`sh -c` の中身のパス、`xargs` 経由、公式の自動片付け（外側のワークツリーが「変更なし」と判定され、中のサブエージェントの入れ子ごと消える恐れ＝§2 にも注意） | 受容（粗く漏れにくい判定に絞り、シェル文法の再現はしない＝第 2〜3 周の後退の教訓） |
| `wt-remove.sh` | 戻り値 4・同名で止まったときもバックアップ手順を表示。データありで volume だけ（コンテナなし）のときは、`DANGER_OK` なしの停止メッセージに持ち主を機械で確かめられない旨と volume 名・作成日時を表示する（判断材料を渡す）。`DANGER_OK=1` なら従来どおり `-p <既定名> down -v` を実行する（volume には作業フォルダのラベルが無く、`down` だけで止めた後の普通の状態なので、ここで止めると正規の撤去が常にできなくなる。同名の登録済みワークツリーは既存の SAME_NAME で止まる）→ TC-R1b2・R1b3。戻り値 2 の案内を「該当行を消してコミット・push」にし、元の名前のデータは §4「取り残し」で片付ける旨を表示 | Medium（①③④観点） |
| `wt-ports.sh` | 自分の `.env` の割当済み判定を `export`・空白付きの書き方にも合わせる | Low（④観点） |
| `worktree.md` | §4「止まったときの片付け」: volume だけで持ち主を確定できないときは手順 3 をしない・戻り値 2 の進め方。§9: 削除・破棄のガードと対象外。§2: 公式の自動片付けと入れ子の注意。§11: 両方にあって中身が違うファイルは `cmp` で確かめ新しい方を残す | Medium・Low |
| テスト | TC-X（止める側・通す側：自分のワークツリー内の `rm -r build`・`git -C <別> status`・`git clean -fdx`・`/tmp` の削除。当初は `git worktree remove`（`--force` なし）も通す側だったが第 5 周改訂で止める側へ）・FG-X（判定を外した複製で止める側が素通りすること）・`DANGER_OK=1` が区切りの後ろでは効かないこと・ヒアドキュメント除外ヘルパーの再導入を捕まえる TC（追加済み）・R（戻り値 4／同名のバックアップ表示・volume だけの表示）・P（`export` 付きの自分の `.env`） | — |
- **第 5 周の findings による改訂（2026-10-21）**: ⑤を「`git worktree remove` は `--force` の有無を問わず止める」に変更（中の入れ子は gitignore 済みで git の未コミット検査に出ないため `--force` なしでも入れ子ごと消える＝High。`-ff` の素通りも同時に解消。撤去は `wt-remove.sh` に一本化。TC-X36 を通す側から止める側へ）。区切りの解析で `#` をコメント扱いしない・クォートが閉じていないときは区切り文字で粗く分ける（後ろのコマンドを見落とす High 2 件）。作業フォルダの反映に `pushd`・`popd`・`cd -`・`env -C`・`GIT_WORK_TREE=`/`GIT_DIR=` を追加（Medium）。ワイルドカードは手前のフォルダ全体ではなく、パターンに当たる名前の中に別ワークツリーがあるときだけ止める（`rm -r tmp_*` 等の誤ブロック＝Medium）。§9 の「止められないもの」に rm/find/mv/git 以外の消し方とヒアドキュメント本文の誤ブロックを追記。TC-X21b・X42〜X57・X60〜X66・R1（追加）。
- **第 6 周の findings による改訂（2026-10-21・fix-loop 2 回目・診断 `docs/reviews/I179_fix_diagnosis_20261021_1358.md` 案 A・ユーザー承認「理想・最適で問題なければ OK・サクサク」）**: 第 5 周のワイルドカードの細かい判定（パターン照合）を**廃止**し、展開を含むパス（`* ? [ {`）は最初の展開文字の手前の固定部分のフォルダを基準に粗く判定する（中身も消す操作は中に別ワークツリーがあれば止める・非再帰の操作はパターンの段数より浅い位置に別ワークツリーがあれば止める・パターンの意味は解釈しない）。`~+`・`~-` を今のフォルダ・直前のフォルダとして判定。括弧（サブシェル）の中の `cd` を外に持ち越さない。前置コマンドの後ろは既知のコマンド名の位置をすべて候補にして読む（値を取るオプションを列挙しない）、前置部分の `-C<dir>`・`sudo -D` も作業フォルダの変更として扱う。展開を含む `mv` は全引数を移動元として見る。§2 の手動手順のコピーを作ったワークツリーのセッションで行う形に、§4 に登録の無い `.git` の片付け手順。**primary 直下の `rm -r tmp_*`・`mv *.md docs/` は止まる（誤ブロックとして受容・§9 に回避）**。TC-X60/X61 を止める側へ・X67〜X93・FG-X3/X4。
- **第 7 周の findings による補正（2026-10-21・/code-review 3 回目・設計は変えない）**: 前置きを「シェル内で動く（`command`・`builtin`・`time`）」と「別プロセス（`env`・`sudo`・`timeout`・`exec`・`nice` 等）」に分け、`cd` を無視するのは後者の後だけにした（予約語・変数代入・`command` の後の `cd` を無視していた fix-loop 2 回目の実装ミス）。作業フォルダの変更（`-C` 等）は候補ごとに手前の部分全体から読む。展開を含む `cp`/`mv` の宛先は中身も見る（`cp f .claude/worktrees/n*` が入れ子に書き込む）。sed は `-e`/`-f` が無ければ最初の位置引数をスクリプトとして除く（`sed -i '2{…}'` の誤ブロック解消）。7 章ロールバックに入れ子の確認と `DANGER_OK` を追記、§4 の登録の無い `.git` に `git worktree repair` と確かめ方を追記。TC-X94〜X115。
- **第 8 周の findings による改訂（2026-10-21・fix-loop 3 回目・診断 `docs/reviews/I179_fix_diagnosis_20261021_1523.md` 案 A・ユーザー回答「理想・最適を基準に問題なければ OK・サクサク」）**: 作業フォルダを順に追う方式（括弧の目印・`cd`/`pushd`/`popd`/`cd -` の追跡・前置きのシェル内／別プロセスの区別）を**廃止**し、セッションの作業フォルダとコマンド中のすべての移動先を「基準の候補」とする和集合の判定に変更。前置きはすべて後ろの既知のコマンド名を候補にする。sed のスクリプト除外を撤回（すべての引数をパスとして見る）。`mv` はすべての引数（`-t`・`--target-directory=` の値を含む）を移動元として見る。誤ブロックとして受容: 1 つのコマンドで別ワークツリーへ移動してから自分側を変更する形・primary で展開文字を含む sed のスクリプト（§9 に回避）。公式のサンドボックス（`sandbox.filesystem.denyWrite`）は、禁止した中の一部だけ許可する設定が無く入れ子のセッション・`isolation: worktree` のサブエージェントと両立しない恐れが大きいため不採用（将来の再検討候補）。TC-X116〜X136・FG-X5、X66/X69/X113/X114 を止める側へ、FG-X4 を削除。
- **第 9 周の findings による改訂（2026-10-21・fix-loop 4 回目・診断 `docs/reviews/I179_fix_diagnosis_20261021_1619.md` 案 A・ユーザー判断「普通の書き方による事故を守る対象にする」）**: **脅威モデルを明記**＝守る範囲は Claude が普通の書き方で起こす事故。意図的な回避の書き方（`CDPATH`/`HOME` で行き先が決まる `cd`・`coproc`・同じコマンドで作ったシンボリックリンク・GNU の長いオプションの省略形・逆順の相対移動のループ・サブシェルの `cd` の後の `..` で抜ける形）は対象外として §9 に明記。直した点: `..` を含む相対の移動先は書いた順の直前の位置だけを基準にする（入れ子のセッションで `cd backend && cd ..` が止まる止めすぎの解消）・候補集めは増えなくなるまで（上限 8 回）・移動先の `~+`/`~-` を全候補に置き換える・cp/mv で宛先指定のオプション（`-t` を含む短いオプションの塊・`--t…`）があれば位置引数と連結値をすべて宛先として見る。§9 の回避手順を「別の Bash 呼び出しに分ける」に訂正。TC-X137〜X148。以後の敵対的レビューのプロンプトにはこの脅威モデルを渡す。
- **第 10 周の findings による改訂（2026-10-21・fix-loop 5 回目・診断 `docs/reviews/I179_fix_diagnosis_20261021_1826.md` 案 A・ユーザー回答「理想・最適を基準に問題なければ OK・サクサク」）**: 第 10 周の計測で、和集合の候補集めが移動先の数に対して指数的に増え（`cd` 3 個で 1GB 超）、メモリを使い切ってセッションが落ちた（Critical。ガードの異常終了はフックが止めないため、後ろの危険操作の検査まで素通りになり得た）。あわせて第 9 周の「直前の位置」が `cd -`・`popd`・`git -C` でずれる後退（High）。**作業フォルダの連鎖を解釈しない方式に変更**: 基準の候補はセッションの作業フォルダと、各移動先を 1 回だけ解いたものに限る（線形）。増えなくなるまでまわすループと「直前の位置」を削除。連鎖を解かないと宛先が決まらない形（相対を含む 2 つ以上の移動先・`cd -`・`popd`・引数なしの `pushd`・`~+`/`~-`）では、相対パスの削除・書込と読み取り以外の git 操作を判定不能として止め、分けて実行するよう案内する（絶対パスの対象は通常どおり判定）。判定中の例外は exit 2 で止める（fail-closed）。**誤ブロックとして受容**: 移動を 2 つ以上含むコマンドの中の相対パスの削除・書込・git の変更（`cd backend && cd .. && git add -A` を含む。第 9 周で通すようにした形を止める側へ戻す）・`cp -t` で移動元も宛先とみなす止めすぎ（第 10 周 Medium・見送り）。いずれも §9 に回避を記載。TC-X146〜X148 を止める側へ・X149〜X161・FG-X5 を判定不能の検出に変更。

### 計画変更記録 6（2026-10-21・敵対的レビュー第 11 周の後・ユーザー判断）
| 変更 | 内容 | 理由 |
|------|------|------|
| `pretooluse_guard.py`: 別ワークツリーの削除・破棄と相対パス・`cd` 越しの書込の判定（`_bash_destroy_targets` 一式・約 250 行）を**廃止** | 計画変更記録 5 の②③と、その第 5〜10 周の改訂をすべて取り下げる。I095 の絶対パスの書込ガードと、入れ子の持ち主の判定（H）は残す | 第 11 周でも普通の書き方の見逃し 2 件（移動先の `n*`・`&>`）と止めすぎ・文書の食い違いが続いた。コマンドの文字列からシェルの動きを読み取る方式は、足すほど抜け道・止めすぎ・不具合（第 10 周のメモリ爆発）が出る。守る対象は push していない手元の変更だけで、develop/main は GitHub 側で保護され（bot は PR を出すだけ）、ローカルが壊れても GitHub から復旧できる。費用に見合わない |
| `pretooluse_guard.py`: `_git_clean_ff` を追加 | `git clean` で `f` が合計 2 つ以上（`-ffdx`・`-f -f`・`--force -f`）なら `DANGER_OK=1` 必須。既存の `git reset --hard` と同じ承認制 | primary で打つと入れ子ワークツリーが未コミットの作業ごと全部消える、影響の大きい 1 形だけを文字列 1 つの一致で止める（抜け道探しの対象にしない） |
| §9・`danger-ops.md` | 削除・破棄は技術的には止めず、こまめな commit/push・`wt-remove.sh`・別ワークツリーの中身を消さない運用に任せると明記 | 同上 |
| テスト | TC-X1〜X161・FG-X1〜X5・X21b を削除し、TC-GC1〜GC7・FG-GC1 を追加 | 同上 |
- 承認: ユーザー判断（2026-10-21「GitHub は壊れないので復旧できる。もっとサクサク進めたい」→ 案 B＋`git clean -ff` の承認制に「ok」）。

### 計画変更記録 7（2026-10-22・/close の base 追従で develop〔I174 マージ済み〕と競合）
| 変更 | 内容 | 理由 |
|------|------|------|
| develop（I174）を取り込み、ガードは I174 の見張りを土台にする | 競合した `pretooluse_guard.py` の `main()` 末尾と `danger-ops.md` の例は I174 側を採用。I179 の入れ子の持ち主の判定（`_owning_root`・`_path_key`）は自動で合流 | I174 は「コマンドが実際に何をするか」で判定する見張りに作り替えており、Docker のデータ削除・`git clean -f`（f の数によらず）・`rm -r` を危険操作として止める |
| I179 の Docker 判定（`_docker_volume_wipe` 一式・正規表現∪トークン判定）と `_git_clean_ff` を削除 | I174 の判定に一本化（同じ穴を二重に塞がない） | 取り込み後はどちらも呼ばれない死んだコードになっていた |
| I174 の判定に `docker volume remove`（`rm` の別名）を追加 | 1 語の追加 | I179 の TC-DV15 で、I174 の判定がこの別名を止めないことが分かった |
| テストを I174 の挙動に合わせる | DV20（コミットメッセージ中の文字列）と cat のヒアドキュメント本文は通す側へ（実行されないため。I179 の既知の誤ブロックが解消）。`docker.exe` の DV-sh を削除（I174 が `.exe` を読まない。WSL では通常 `docker` を使うため受容）。FG-DV1〜3・FG-GC1 を削除。GC5（f 1 つ）は止める側へ、GC7 は `git clean -n` を通す確認に変更 | 同上 |
- 承認: ユーザー判断（2026-10-22「ok」＝ I174 を土台に I179 の分を載せ直す）。計画変更のため `/plan-issue-review I179` → `/code-review I179`（敵対的レビューはユーザー方針で省略）を経て `/close` に戻る。計画変更のため `/plan-issue-review I179` を挟む。敵対的レビューはユーザー判断で、次の `/code-review` では 1 周・正規の手順を止めないかの確認に絞る。
- 見送り（理由）: トークン判定の前置コマンドのオプション対応（`timeout 60 docker --context x …`）は develop にもある穴で、正規表現の層がほぼ止めるため今回は扱わない。NOREG の件数下限は CI が origin/develop を常に取得できるため効果が小さい。
- 理想基準での評価: 採用。危険を生む設計（入れ子配置）と同じ変更の中で決定論のゲートを足すのが根治で、注意書き（手続き）だけでは止まらない。判定は「別ワークツリーのパスを指す破壊的操作」に絞った粗いルールにし、シェル文法を細かく再現しない（第 2〜3 周の後退の再発を避ける）。止めすぎは自分のワークツリー内の操作を通す TC で防ぐ。
- 承認: ユーザー判断（I179 の中で直す）＋既定基準。計画変更のため `/plan-issue-review I179` を挟んでから実装し、敵対的レビューの第 2 周（固定 3 観点）へ進む。

## レビュー結果
- [20261021_2038 判定: ✅ 完了](../../reviews/I179_plan_review_20261021_2038.md)
- [20261021_1846 判定: ✅ 完了](../../reviews/I179_plan_review_20261021_1846.md)
- [20261021_1632 判定: ✅ 完了](../../reviews/I179_plan_review_20261021_1632.md)
- [20261021_1540 判定: ✅ 完了](../../reviews/I179_plan_review_20261021_1540.md)
- [20261021_1426 判定: ✅ 完了](../../reviews/I179_plan_review_20261021_1426.md)
- [20261021_1230 判定: ✅ 完了](../../reviews/I179_plan_review_20261021_1230.md)
- [20261021_1224 判定: 差し戻し（Blocker 1件）](../../reviews/I179_plan_review_20261021_1224.md)
- [20261021_0849 判定: ✅ 完了](../../reviews/I179_plan_review_20261021_0849.md)
- [20261021_0849 判定: ✅ 完了](../../reviews/I179_plan_review_20261021_0849.md)（fix-loop の計画変更記録 4 の後の再レビュー）
  - Warning（`danger-ops.md` の更新が §3 影響範囲・§4 変更点一覧に無い）は、§3 に追記し 4-12 を追加して対応済み。
  - Info（`danger-ops.md` の変更を確かめる決定論ゲートが無い）は、`test_i179_worktree_docs.sh` に D12（失敗注入つき）を追加して対応済み。
- [20261021_0031 判定: ✅ 完了](../../reviews/I179_plan_review_20261021_0031.md)（計画変更＝ロックの扱いの追加後の再レビュー）
  - Warning（ロック確認とデータ判定の順番が分散して追いにくい）は、4-6 に「処理の順番」（1〜8・TC-R13 の流れの例つき）を追記して対応済み。実装（`wt-remove.sh`）はこの順番どおりで変更不要。
  - Info（M6 が未実施）は /test で実施・記録する。
  - Info（M7 の実施者欄が空）は誤り。`I179_manual_test.md` No.7 の実施者欄は「Claude」と記載済みのため変更不要。
- [20261020_1950 判定: ✅ 完了](../../reviews/I179_plan_review_20261020_1950.md)
  - Warning（D2・D10・D11 の不在チェックに失敗注入が無い）と Info（D9 に失敗注入が無い）は、`I179_auto_test.md` の FG-D1 に 4 通りの注入を追加して対応済み（6 → 10 通り）。
  - Info（実機確認をステップ6に置く理由）は計画書の記載どおりで変更不要。
