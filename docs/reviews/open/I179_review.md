# I179 レビュー: ワークツリー運用の見直し

## 変更概要
- ワークツリーの作成を公式の `claude --worktree`（primary で実行）に切り替え、設定ファイルのコピーを公式の `.worktreeinclude` に任せる。
- 自作は公式に無い部分だけにする: ポート割当（`wt-ports.sh` 新設・`wt-new.sh` 廃止）、Docker データの後始末（`wt-remove.sh` 改修）、入れ子ワークツリーでの横断書込ガードの判定修正。
- `/plan-issue` のブランチ作成を、develop をチェックアウトしない形に変更。
- `worktree.md` を複数ワークツリー前提に書き直し（共有物の注意・撤去の使い分け・旧 `wt-harness` の移行手順）。

## 変更点
- （実装後に記入）計画書 4-1〜4-11 との対応

## 影響範囲
- Backend/Frontend/DB/Config: Backend・Frontend・DB はなし。Config/Infra は計画書「3. 影響範囲」のとおり

## レビュー観点（敵対的レビューで反証を試みる点）
- ガード: 許可が広がるのは「入れ子ワークツリーが自分自身に書く」場合だけか。親→入れ子・入れ子→親・兄弟間・symlink 経由・fail-safe・`DANGER_OK` 非解除が崩れていないか
- `wt-remove.sh`: 「データ無し」と誤判定して `DANGER_OK` なしで進む経路が無いか（プロジェクト名の算出・`COMPOSE_PROJECT_NAME`・`name:`・docker の失敗）。登録外のフォルダを消せないか
- `wt-ports.sh`: 入れ子配置のワークツリーを含めて走査しているか・自分自身を除いているか・2 回実行で壊れないか
- `wt-new` の参照の取り残し（closed の記録類以外）
- `worktree.md` だけを読んで、文脈の無い人が作成〜撤去〜移行を実行できるか
- 公式の自動片付けを壊していないか（WorktreeCreate / WorktreeRemove が無いこと）

## テスト結果
- 自動: （/test で記入）
- 手動: （/test で記入）

## 計画との差分
- なし / あり（理由）

## 残作業（/close 時に確定）
- 既存 `wt-harness`（`/mnt/c/app/wt-harness`）の移行: I178・I179 が完了・クローズした後に、primary から `bash scripts/claude/wt-remove.sh /mnt/c/app/wt-harness` で撤去し、必要なら primary で `claude --worktree harness-<連番>` で作り直す
- ハーネス改善用 2 つ目のワークツリーの作成（本イシューの起点の要望）: 本 PR のマージ後、primary で `claude --worktree harness-2`

## ロールバック
- PR を revert（`wt-new.sh` も履歴から戻る）。個別には計画書「7. ロールバック」のとおり
