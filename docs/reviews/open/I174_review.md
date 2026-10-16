# I174 レビュー: 確認が必要な操作の見直し（docker compose exec 等の一律確認をやめ、コンテナ内の危険操作だけを見張りで止める）

- 関連: docs/issues/open/I174.md / docs/plans/open/plan_I174.md / GitHub #292 / Draft PR #293

## 変更概要
- 見張り（`pretooluse_guard.py`）を「コマンドの書き出し」ではなく「実際に何をするか」で判定する形に作り替え、`.claude/settings.json` の一律の確認（`docker compose exec *` など 9 行）を外した。
- 判定は 3 種類: 常に止める（ルートの rm -rf・mkfs・dd・shred・別 worktree への書き込み）／危険操作（exit 2・`DANGER_OK=1` を付けると人の承認）／外部送信（人の確認）。

## 変更点
- `scripts/claude/hooks/pretooluse_guard.py`
  - `DANGER_OK=1` 付きの危険操作は素通しせず `permissionDecision=ask` を返す（既存の解除経路すべて）
  - 破壊的 SQL の判定を単語境界・引用符非依存に是正（先頭の DROP/TRUNCATE/DELETE と単一引用符の見逃しを修正）
  - `rm -rf` をトークン単位で判定（ルートだけ解除不能・grep の検索文字列とヒアドキュメント本文への誤反応を修正）
  - コンテナ内の危険操作（flush/sqlflush/reset_db・migrate の巻き戻し・loaddata・dropdb・psql の流し込み・pg_restore --clean・redis FLUSHALL/FLUSHDB・shell と python -c 内の削除と一括更新）を、書き出しに依存せず判定（`sh -c`・`eval` の中身も展開）
  - 外部送信（メール・celery の起動・登録とパスワード再設定依頼の API・OpenAI）に ask を返す
  - 実行ファイルの中身も判定（`manage.py shell < ファイル`・`python ファイル.py`・コンテナ内の `sh`/`bash ファイル`。`/app/docs/`→`docs/`・`/app/`→`backend/` に読み替え。ホストの bash スクリプトと `scripts/claude/` は対象外）
  - 判定は先頭の `DANGER_OK=1` と環境変数の代入を外したコマンドで行う
- `scripts/claude/tests/test_pretooluse_container_guard.sh`（新規・118 件）
- `scripts/claude/tests/test_pretooluse_push_guard.sh`・`test_pretooluse_checkout_guard.sh`（DANGER_OK=1 の期待値を ASK に）
- `.claude/settings.json`（ask 9 行・効いていない exec の allow 10 行・`Write(...)` 10 行を削除）
- `docs/runbooks/danger-ops.md`（対象操作の追記・見張りの扱いの節を追加）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/settings.json`・`scripts/claude/hooks/pretooluse_guard.py`・`scripts/claude/tests/test_pretooluse_*.sh`・`docs/runbooks/danger-ops.md`（新しいセッションから全セッションに効く）

## テスト結果
- 自動: 決定論ゲート全 30 行 exit 0（`docs/tests/open/I174_auto_test.md` の実施記録）。TC-12 は I146 マージ後
- 手動: No.1（スパイク）OK（auto mode）。No.2〜No.4 はステップ 7（新しいセッション）で実施

## 計画との差分
- あり（計画書に追記済み）:
  1. 判定を先頭の `DANGER_OK=1` を外したコマンドで行い、先頭の環境変数の代入も読み飛ばす処理を追加した。既存の DOK3 が確認なしで通る穴を塞ぐため（AC-5 を満たすのに必要）
  2. 関数の構成を計画のスケッチ（`_sql_reasons`・`_container_danger_reasons`）から、`_segment_danger`（1 セグメントの SQL・DB・Redis・shell）＋`_exec_files`／`_file_reasons`（実行ファイル）に整理した。判定の中身は計画どおり
  3. 旧 psql 判定の 3 つのメッセージを `destructive SQL requires DANGER_OK=1` に 1 本化した

## 気づいた点（本イシューの範囲外）
- `DANGER_OK=1 bash scripts/claude/wt-remove.sh <track>` の中の `docker compose down -v` は、guard から見えない（スクリプト自身が DANGER_OK=1 を要求する既存の挙動）。DANGER_OK=1 を付けると人の承認なしで実行される（計画書 R7）
- `pretooluse_guard.py` の `\bdd\b`・`\bshred\b`・`\bmkfs` は、コマンド行の文字列全体を見るので、grep の検索文字列などにも反応する止めすぎ（計画書 R8。本セッションでも `shred` を含む grep が止められた）
- 対話セッションの一部（wt-harness・版 2.1.300・permissionMode default）では、guard が ask を返しても承認画面が出ずに実行された（計画書 R10・手動テスト No.1）。I146 の手動テストの「gh pr 系が止まらない」も同じ現象の可能性が高い

## ロールバック
- PR を revert する。一時的には `.claude/settings.json` の ask に `Bash(docker compose exec *)` などを戻し、セッションを開き直す
