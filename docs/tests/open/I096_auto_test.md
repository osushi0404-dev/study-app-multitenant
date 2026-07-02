# I096 自動テスト: worktree lifecycle スクリプト（作成・撤去）

実行は下記「決定論ゲート（自動実走）」セクションのコマンドで行う（code-review が自動実走する）。個別実行もそのコマンドを参照。

結果:
- backend: 該当なし（ハーネススクリプトのため・pytest 非該当）
- frontend: 該当なし（Jest 非該当）
- 専用自動テスト `test_wt_lifecycle.sh`: **未実装（実装ステップで作成・実走して更新）**

## テスト方式

`test_wt_lifecycle.sh` は `mktemp -d` に **bare origin repo（`main` に only-main-file / `develop` に only-develop-file・`backend/.env`・`e2e/.env.e2e`・`docker-compose.yml` を含む）** を作り、それを clone した **primary temp checkout** の中でスクリプトを実行する。`docker` は **PATH スタブ**（`$DOCKER_LOG` に `docker $*` を追記。`down` 呼出時は `WT_PATH/.git` の存在を `present=yes/no` として記録＝順序検証用）に差し替え、**Docker デーモン非依存**で判定する。実 `docker compose` は呼ばない。`0`=正常終了 / `2`=明示エラー停止。

## テストケース一覧

### wt-new: 作成（TC-N1〜N9）
| TC | 入力/前提 | 期待 |
|----|-----------|------|
| TC-N1 | `wt-new.sh app 001 my-feature`（happy path） | exit 0・`<base>/wt-app` が worktree として作成される（`git worktree list` に出る）・branch=`feature/I001-my-feature`。**base は primary temp の親**（`/mnt/c/app` 直書きなら temp では不一致→検出） |
| TC-N2 | TC-N1 後、新 worktree の内容を確認 | **only-develop-file が存在し only-main-file が存在しない**＝基点が `origin/develop` に固定（`main` 基点の空/誤ツリーでない） |
| TC-N3 | TC-N1 後、新 worktree の `backend/.env` を確認 | source（primary の `backend/.env`）と同一内容がコピーされている（`cmp` 一致） |
| TC-N4 | primary の `backend/.env` を消して `wt-new.sh app 002 x`（`--env-source` 既定） | exit 2・`.env source が存在しません` 出力・**worktree は作成されない**（add 前に停止＝orphan 非作成を `git worktree list` で確認） |
| TC-N5 | `wt-new.sh app 003 x`（`--up` なし） | exit 0・`$DOCKER_LOG` に `up` が**含まれない**（既定 OFF） |
| TC-N6 | `wt-new.sh app 004 x --up` | exit 0・`$DOCKER_LOG` に `compose up -d` が含まれる |
| TC-N7 | 番号非数字 `wt-new.sh app abc x` / 概要に空白 `wt-new.sh app 005 "a b"` / track にスラッシュ `wt-new.sh a/b 006 x` | いずれも exit 2・`worktree list` 不変（不正引数で停止） |
| TC-N8 | 既存 branch 名で `wt-new.sh app 007 dup`（`feature/I007-dup` を事前作成） | exit 2・`branch が既に存在`・worktree 非作成 |
| TC-N9 | 既存 path で `wt-new.sh app 008 x`（`<base>/wt-app` を事前作成済み＝TC-N1 の残り or ダミー） | exit 2・`worktree path が既に存在` |
| TC-N10 | `wt-new.sh app 010 x --env-source`（**値なし**で末尾指定）※W2 回帰 | exit 2・`--env-source に値がありません`（`shift 2` 範囲外の無言 exit にならない）・worktree 非作成 |

### wt-remove: 撤去（TC-R1〜R6）
| TC | 入力/前提 | 期待 |
|----|-----------|------|
| TC-R1 | 撤去可能な worktree（HEAD が origin に含まれる・clean）に対し `wt-remove.sh app`（**DANGER_OK 未設定**） | exit 2・`DANGER_OK` 案内出力・`$DOCKER_LOG` に `down` が**含まれない**・worktree は**残る**（非撤去） |
| TC-R2 | 同上に `DANGER_OK=1 wt-remove.sh app` | exit 0・`$DOCKER_LOG` に `compose down -v` が含まれる・worktree が `git worktree list` から消える |
| TC-R3 | TC-R2 の `down` 記録が `present=yes` | `down -v` 実行時に `WT_PATH/.git` が存在＝**`down -v`→`remove` の順序**が実証される（remove 後なら `present=no`） |
| TC-R4 | worktree に未コミット変更を作成し `DANGER_OK=1 wt-remove.sh app` | exit 2・`未コミット変更あり`・`down` 非実行・worktree 残存 |
| TC-R5 | worktree で push していないローカルコミットを作り `DANGER_OK=1 wt-remove.sh app` | exit 2・`HEAD が未 push`・`down` 非実行・worktree 残存 |
| TC-R6 | primary 保護。**セットアップ**: primary temp checkout を `<base>/wt-primary` という名前で配置（`WT_PATH==PRIMARY` を成立させるため clone 先ディレクトリ名を `wt-primary` にする）→ `DANGER_OK=1 wt-remove.sh primary` を呼ぶ | exit 2・`primary checkout は撤去できません`（primary 保護・`down` 非実行） |
| TC-R7 | 撤去対象 WT の**内側に cd した状態**で `DANGER_OK=1 wt-remove.sh app`（`( cd "$WT_PATH" && ... )` で実行）※W1 回帰 | exit 2・`撤去対象 WT の内側からは実行できません`・`down` 非実行・worktree 残存 |
| TC-R8 | 撤去可能な worktree に対し **docker スタブを `down` で非ゼロ終了**させて `DANGER_OK=1 wt-remove.sh app`（スタブが引数に `down` を含むとき `exit 1`）※W4 回帰 | exit 2・`docker compose down -v が失敗しました` 案内出力・`git worktree remove` は実行されず worktree 残存 |

### COMPOSE_PROJECT_NAME 検出（TC-C1）
| TC | 入力/前提 | 期待 |
|----|-----------|------|
| TC-C1 | `COMPOSE_PROJECT_NAME=foo wt-new.sh app 009 x`（および remove 側） | stderr に `COMPOSE_PROJECT_NAME` 警告が出る（処理自体は継続＝軽微警告） |

### false-green 注入（TC-FG1〜FG2）
| TC | 入力/前提 | 期待 |
|----|-----------|------|
| TC-FG1 | **DANGER_OK ゲート除去複製**（`if [ "${DANGER_OK:-}" = "1" ]; then` を `if true; then` に置換した wt-remove コピー）に対し **DANGER_OK 未設定**で実行 | 除去複製では `down` が**実行される**（`$DOCKER_LOG` に `down`）＝実体スクリプトの停止要因が DANGER_OK ゲートであることを反証。実体（TC-R1）は未設定で `down` 非実行 |
| TC-FG2 | **`.env` 存在検証除去複製**（`[ -f "$ENV_SRC" ] \|\| { ...exit 2; }` 行を削除した wt-new コピー）に対し `.env` source 欠落状態で実行 | 除去複製では `.env` 検証で停止せず後続（add）へ進む＝実体スクリプトの停止要因が `.env` 検証であることを反証。実体（TC-N4）は exit 2 |

> false-green 確認の趣旨: 「未設定なら down しない」「欠落なら停止」という**否定・停止の決定論 TC** が、ガードを外した入力に対して実際に振る舞いを変える（＝合否が反転する）ことを確認し、正常系で通るだけの見かけゲートでないことを担保する（plan-writing-rules「false-green 禁止」）。

### runbook 更新（TC-D1〜D2）
| TC | 入力/前提 | 期待 |
|----|-----------|------|
| TC-D1 | `docs/runbooks/worktree.md` に `wt-new` 記述 | `grep -q "wt-new" docs/runbooks/worktree.md` が成功 |
| TC-D2 | 同上に `wt-remove` 記述 | `grep -q "wt-remove" docs/runbooks/worktree.md` が成功 |

## 決定論ゲート（自動実走）
<!--
  code-review が本見出し直後の単一 bash ブロックを 1 行 1 コマンドで抽出・実走し exit code を VERDICT に注入する。
  許可コマンドのみ・チェーン不可。heavy は /test に委譲。
-->
```bash
bash scripts/claude/tests/test_wt_lifecycle.sh
bash -n scripts/claude/wt-new.sh
bash -n scripts/claude/wt-remove.sh
grep -q "wt-new" docs/runbooks/worktree.md
grep -q "wt-remove" docs/runbooks/worktree.md
```
