# 危険操作（Danger Ops）ルール

以下は原則「計画書に明記」＋「ユーザー明示承認」＋「PRに danger-approved」＋「実行時 DANGER_OK=1」でのみ実行する。

## 例
- DB: DROP / TRUNCATE / WHEREなし UPDATE・DELETE / 大量更新・削除 / 破壊的マイグレーション
  - `manage.py flush` / `sqlflush` / `reset_db`（DB 全消去）・`manage.py migrate <app> <移動先>`（巻き戻し。`zero` を含む）・`manage.py loaddata`（既存の行の上書き）
  - ダンプ・SQL ファイルの流し込み（`psql -f <ファイル>` / `psql ... < <ファイル>`・`pg_restore --clean`）・`dropdb`
  - `manage.py shell` / `python -c` 内の `.delete()`・QuerySet の一括 `update()`・`bulk_update()`・`call_command('flush')` など
- Git: force push / reset --hard / 大規模rebase / **未コミット変更があるファイルへの `git checkout/restore <file>`**（下記注記）
- Docker: down -v / --volumes（データ消失）・`redis-cli FLUSHALL` / `FLUSHDB`（ログイン状態・celery の待ち行列・レート制限カウンタの全消去）
- Files: rm -rf / secrets 操作

## 見張り（pretooluse_guard.py）の扱い（I174）

- 上の操作は、ホストで直接実行・`docker exec <コンテナ>`・`docker compose exec/run`・`docker-compose`・`sh -c` で包んだ形の**どれで実行しても**、PreToolUse フック（`scripts/claude/hooks/pretooluse_guard.py`）が止める（exit 2）。`manage.py shell < <ファイル>` などで実行するファイルの中身も確認する。
- **`DANGER_OK=1 を付けても`、見張りは人の承認を求める**（承認画面が出る）。Claude が自分で `DANGER_OK=1` を付けて通すことはできない。上の「ユーザー明示承認」を技術的に強制するためである。
- `rm -rf /` と `rm -rf /*`・mkfs・dd・shred・別 worktree への書き込みは、`DANGER_OK=1` でも止める（解除不可）。
- **外部への送信**（メール送信・celery タスクの起動・登録 API とパスワード再設定依頼 API・OpenAI による AI 問題生成）は、データを壊さないが外へ出るため、見張りが人の確認を求める。
- **見張りを避ける書き方を使わない**: 変数・`eval`・base64 などで命令を組み立てる形、`docker compose cp` でファイルを送ってから実行する形、コンテナの中で作ったファイルを実行する形は、見張りが中身を判定できない。危険操作や外部送信をこうした書き方で行わない（判定できない部分は auto mode の判断が第 2 層になる）。

## 未コミット変更の取り消し（`git checkout/restore <file>`）

作業ツリーに**未コミット変更があるファイル**の一時変更を取り消す際、`git checkout/restore <file>` を使わない。同ファイルの未コミット分も HEAD に戻り**消失**する（一時的なテスト注入を戻すつもりが、未コミットの実装ごと失う事故になる）。

- 一時変更は **Edit ツールで元に戻す**（取り消したい行だけをピンポイントで復元する）。
- clean なファイルの revert やブランチ切替（`git checkout <branch>` / `-b` / `git switch`）は通常どおり可。
- PreToolUse フック（`scripts/claude/hooks/pretooluse_guard.py`）が、未コミット変更があるファイルへの `git checkout/restore <file>` を `DANGER_OK=1` 無しでブロックする。どうしても必要な場合のみ `DANGER_OK=1` を前置する。

## 実行テンプレ
- 影響範囲:
- 代替案:
- ロールバック:
- 実行コマンド（DANGER_OK=1 付き）:
