# I179 レビュー: ワークツリー運用の見直し

## 変更概要
- ワークツリーの作成を公式の `claude --worktree`（primary で実行）に切り替え、設定ファイルのコピーを公式の `.worktreeinclude` に任せる。
- 自作は公式に無い部分だけにする: ポート割当（`wt-ports.sh` 新設・`wt-new.sh` 廃止）、Docker データの後始末（`wt-remove.sh` 改修）、入れ子ワークツリーでの横断書込ガードの判定修正。
- `/plan-issue` のブランチ作成を、develop をチェックアウトしない形に変更。
- `worktree.md` を複数ワークツリー前提に書き直し（共有物の注意・撤去の使い分け・旧 `wt-harness` の移行手順）。

## 変更点
| 計画 | 変更したファイル | 内容 |
|------|----------------|------|
| 4-1 | `.worktreeinclude`（新規） | `backend/.env`・`e2e/.env.e2e` |
| 4-2 | `.gitignore` | `.claude/worktrees/` を追加 |
| 4-3 | `scripts/claude/hooks/pretooluse_guard.py` | `_owning_root`（最長一致）を追加し、`_cross_worktree`・`_block_cross_worktree` の判定と表示をそれで行う |
| 4-4 | `scripts/claude/wt-ports.sh`（新規） | wt-new のポート割当を移植。自分自身を走査から除外・primary 拒否・`backend/.env` 検査・割当済みなら不変・既存行を残して追記（末尾改行なしの既存行にも対応） |
| 4-5 | `scripts/claude/wt-new.sh` | 削除 |
| 4-6 | `scripts/claude/wt-remove.sh` | 引数を登録済みワークツリーのパスに変更・`detect_data` によるデータ判定・ブランチ名の案内・ロックの扱い（終了済み Claude セッションのロックだけ解除・使用中/その他は破壊的操作の前に中止。2026-10-21 計画変更） |
| 4-7 | `.claude/skills/plan-issue/SKILL.md`・`docs/runbooks/issue-flow.md` ステップ5 | `git fetch origin` ＋ `git checkout --no-track -b ... origin/develop` |
| 4-8 | `.claude/skills/issue-bootstrap/SKILL.md`・`docs/runbooks/issue-flow.md` | 「（対応 worktree: …）」を外す |
| 4-9 | `docs/runbooks/worktree.md` | 全面書き直し（§1〜§11） |
| 4-10 | `docs/runbooks/common-commands.md` | `wt-ports.sh` の案内に置き換え |
| 敵対的レビュー第 1・2 周 | `wt-remove.sh`・`wt-ports.sh`・`pretooluse_guard.py`・`worktree.md`・テスト 4 本 | 入れ子の検査・`-p` 固定の `down -v`・確定できなければ `DANGER_OK=1` でも中止・`KEEP_DATA=1`・作業フォルダのラベル確認・ガードのトークン判定（`_docker_volume_wipe`）・作る前の確認（origin/HEAD）・移行手順。詳細は計画書「計画変更記録 2・3」と `docs/reviews/I179_adversarial_review_20261021_1200.md` |
| 4-11 | `test_pretooluse_worktree_guard.sh`・`test_wt_port_offset.sh`・`test_wt_lifecycle.sh`・`test_i179_worktree_docs.sh`（新規） | G1〜G7・FG-G1／P1〜P13・FG-P1・FG-P2／R0〜R12・C1・FG1・FG3／D1〜D11・DOC1・FG-D0・FG-D1 |

### 実装時の確認記録（2026-10-21）
- ガード: 修正前のガード（`git show HEAD:...` で取り出した複製）に同じテストを当てると G1・G2・G7 が FAIL（pass=31 fail=4）、修正後は pass=35 fail=0。再発防止テストが修正前の不具合を捕まえることを確認した。
- 各テストの失敗注入（FG-G1・FG-P1・FG-P2・FG1・FG3・FG-D1 の 10 通り）は、注入した複製で狙った TC が FAIL になることをテスト内で確認している（FG-D1 は「FAIL になった TC が注入対象であること」まで確認）。

## 影響範囲
- Backend/Frontend/DB/Config: Backend・Frontend・DB はなし。Config/Infra は計画書「3. 影響範囲」のとおり

## レビュー観点（敵対的レビューで反証を試みる点）
- ガード: 許可が広がるのは「入れ子ワークツリーが自分自身に書く」場合だけか。親→入れ子・入れ子→親・兄弟間・symlink 経由・fail-safe・`DANGER_OK` 非解除が崩れていないか
- `wt-remove.sh`: 「データ無し」と誤判定して `DANGER_OK` なしで進む経路が無いか（プロジェクト名の算出・`COMPOSE_PROJECT_NAME`・`name:`・docker の失敗）。登録外のフォルダを消せないか。使用中セッションのロックを外してしまう経路（理由文字列の解釈・pid の判定）が無いか、ロック判定が `down -v` より前にあるか
- `wt-ports.sh`: 入れ子配置のワークツリーを含めて走査しているか・自分自身を除いているか・2 回実行で壊れないか
- `wt-new` の参照の取り残し（closed の記録類以外）
- `worktree.md` だけを読んで、文脈の無い人が作成〜撤去〜移行を実行できるか
- 公式の自動片付けを壊していないか（WorktreeCreate / WorktreeRemove が無いこと）

## テスト結果
- 自動: （/test で記入）
- 手動: （/test で記入）

## 計画との差分
- あり（計画変更・2026-10-21・敵対的レビュー）: 第 1 周（High 4 件）・第 2 周（High 3 件）の findings に対応して `wt-remove.sh`・ガード・`wt-ports.sh`・`worktree.md` を改訂（計画書「計画変更記録 2・3」）。Danger Ops の条件も改訂（消す相手を `-p` で固定・確定できなければ許可があっても止める・消さない撤去は `KEEP_DATA=1`）。
- あり（計画変更・2026-10-21）: 実装ステップ6の実機確認（手動 M1・M4）で、公式 `claude -p --worktree` のワークツリーにセッション終了後もロックが残り、`wt-remove.sh` で撤去できないことが分かった（計画書 S10）。4-6 にロックの扱いを追加し、`worktree.md` §2・§4 とテスト（R13〜R15・FG4・D3）を更新した。計画書「計画変更記録」参照。`/code-review` の前に `/plan-issue-review` を挟む。
- あり（いずれも計画の意図の範囲内の細部）:
  - 4-8: 「（対応 worktree: wt-harness）」に加え、同じ行の対になる「（対応 worktree: study-app-multitenant）」も外した（トラックとワークツリーを 1 対 1 で結ばないという同じ意図。片方だけ残すと規約が食い違う）。
  - D2 の除外に `docs/reviews/I179_*`（`docs/reviews/` 直下に置かれる I179 自身の計画レビュー・コードレビュー記録）を加えた。計画の「I179 自身の記録は除く」の具体化。
  - 4-6: Compose のプロジェクト名の変換に「先頭の `_`・`-` を除く」を加え（Compose の既定の規則に合わせた）、変換後の名前が空なら「判定失敗」とした（fail-closed 側の追加）。
  - テストの追加: R9b（フォルダ名の変換）・FG-D0（注入なしの複製が PASS すること＝複製の作り方で FAIL していないことの確認）。旧 `test_wt_port_offset.sh` の runbook 文言検査（DOC1）は計画どおり `test_i179_worktree_docs.sh` へ移した。
- 計画外の消費箇所を 1 件発見（未対応・残作業へ）: GitHub ラベルの説明文（`track:harness`「ハーネス改善トラック（worktree: wt-harness）」・`track:app`「学習アプリ開発トラック（worktree: study-app-multitenant）」）。リポジトリ設定の外部変更のため本 PR では変えない。

## 再開メモ（2026-10-21・I180 対応のため中断）
文脈ゼロのセッションが、このメモだけで I179 を再開できるように書く。

**現在地**
- 実装・fix-loop まで完了し、すべてコミット・push 済み（ブランチ `feature/I179-worktree-operation-review`・PR #300）。
- 経緯: `/code-review`（1 回目）→ 敵対的レビュー 3 周で未収束・HIGH（`docs/reviews/I179_adversarial_review_20261021_1200.md`）→ `/fix-loop`（診断 `docs/reviews/I179_fix_diagnosis_20261021_0220.md`・3 ゲート PASS・72a5edc）→ `/plan-issue-review` OK（`docs/reviews/I179_plan_review_20261021_0849.md`・指摘対応 9b4172f）→ `/code-review`（2 回目）は **CI の確認で停止**（レビュー未実施）。
- 停止の原因は I179 と無関係: CI「Backend Lint & Security」の `pip-audit` が Pillow 12.3.0 の既知脆弱性 8 件（2026-10-20 以降に公開）で失敗。I179 は `backend/`・依存ファイルを変更していない。対応は **I180（GitHub #301・track:app）**「Pillow を 13.0.0 に更新」で、同じ `wt-harness` で先に行う。

**再開の手順（I180 が develop にマージされた後）**
1. `wt-harness` が I180 のブランチなら、Docker を `docker compose down` で止め（`-v` は付けない）、tracked な変更が無いことを `git status` で確かめてから `git checkout feature/I179-worktree-operation-review`。
2. `git fetch origin` → `git merge origin/develop`（Pillow の更新を取り込む。衝突は無い見込み）→ `git push origin feature/I179-worktree-operation-review`。
3. `/code-review I179` を実行する。CI が緑になってから基本レビュー → 高リスクのため敵対的レビューステージが自動で走る。既知の指摘は上の敵対的レビューの記録に全件ある（受容済みの限界: ガードが作業フォルダで現ワークツリーを決める・別環境の Claude の pid・別クローンの volume だけの同名・文字列の中の記述での誤ブロック）。
4. 通過したら `/test I179`。手動テスト M6（対話の `claude --worktree` の終了時の画面とロックの残り方）は Human が行う。M1〜M5 は実施済み（`docs/tests/open/I179_manual_test.md`）。

**ユーザーに確認が要ること（再開後）**
- 実物の `refs/remotes/origin/HEAD` が `origin/main` を指している（公式 `claude --worktree` が空のワークツリーを作る原因）。`git remote set-head origin --auto` で `origin/develop` に合わせる必要があるが、全ワークツリー共有の参照なのでユーザーの了承を得てから行う（`worktree.md` §2「作る前の確認」）。

**このワークツリーの Docker の準備（I180 のために作成・gitignore 済み）**
- `backend/.env`（primary からコピー）と直下 `.env`（`wt-ports.sh` で offset 10: DB 5442・Redis 6389・backend 8010・frontend 3010）。I179 の再開後も残してよい（撤去時に `wt-remove.sh` が Compose のデータを判定する）。

## 残作業（/close 時に確定）
- 既存 `wt-harness`（`/mnt/c/app/wt-harness`）の移行: I178・I179 が完了・クローズした後に、primary から `bash scripts/claude/wt-remove.sh /mnt/c/app/wt-harness` で撤去し、必要なら primary で `claude --worktree harness-<連番>` で作り直す
- ハーネス改善用 2 つ目のワークツリーの作成（本イシューの起点の要望）: 本 PR のマージ後、primary で `claude --worktree harness-2`
- GitHub ラベル `track:harness`・`track:app` の説明文からワークツリー名を外す（`gh label edit track:harness --description "ハーネス改善トラック"`・`gh label edit track:app --description "学習アプリ開発トラック"`）。`wt-harness` の移行と同時に行う

## ロールバック
- PR を revert（`wt-new.sh` も履歴から戻る）。個別には計画書「7. ロールバック」のとおり
