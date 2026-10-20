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
- あり（計画変更・2026-10-21）: 実装ステップ6の実機確認（手動 M1・M4）で、公式 `claude -p --worktree` のワークツリーにセッション終了後もロックが残り、`wt-remove.sh` で撤去できないことが分かった（計画書 S10）。4-6 にロックの扱いを追加し、`worktree.md` §2・§4 とテスト（R13〜R15・FG4・D3）を更新した。計画書「計画変更記録」参照。`/code-review` の前に `/plan-issue-review` を挟む。
- あり（いずれも計画の意図の範囲内の細部）:
  - 4-8: 「（対応 worktree: wt-harness）」に加え、同じ行の対になる「（対応 worktree: study-app-multitenant）」も外した（トラックとワークツリーを 1 対 1 で結ばないという同じ意図。片方だけ残すと規約が食い違う）。
  - D2 の除外に `docs/reviews/I179_*`（`docs/reviews/` 直下に置かれる I179 自身の計画レビュー・コードレビュー記録）を加えた。計画の「I179 自身の記録は除く」の具体化。
  - 4-6: Compose のプロジェクト名の変換に「先頭の `_`・`-` を除く」を加え（Compose の既定の規則に合わせた）、変換後の名前が空なら「判定失敗」とした（fail-closed 側の追加）。
  - テストの追加: R9b（フォルダ名の変換）・FG-D0（注入なしの複製が PASS すること＝複製の作り方で FAIL していないことの確認）。旧 `test_wt_port_offset.sh` の runbook 文言検査（DOC1）は計画どおり `test_i179_worktree_docs.sh` へ移した。
- 計画外の消費箇所を 1 件発見（未対応・残作業へ）: GitHub ラベルの説明文（`track:harness`「ハーネス改善トラック（worktree: wt-harness）」・`track:app`「学習アプリ開発トラック（worktree: study-app-multitenant）」）。リポジトリ設定の外部変更のため本 PR では変えない。

## 残作業（/close 時に確定）
- 既存 `wt-harness`（`/mnt/c/app/wt-harness`）の移行: I178・I179 が完了・クローズした後に、primary から `bash scripts/claude/wt-remove.sh /mnt/c/app/wt-harness` で撤去し、必要なら primary で `claude --worktree harness-<連番>` で作り直す
- ハーネス改善用 2 つ目のワークツリーの作成（本イシューの起点の要望）: 本 PR のマージ後、primary で `claude --worktree harness-2`
- GitHub ラベル `track:harness`・`track:app` の説明文からワークツリー名を外す（`gh label edit track:harness --description "ハーネス改善トラック"`・`gh label edit track:app --description "学習アプリ開発トラック"`）。`wt-harness` の移行と同時に行う

## ロールバック
- PR を revert（`wt-new.sh` も履歴から戻る）。個別には計画書「7. ロールバック」のとおり
