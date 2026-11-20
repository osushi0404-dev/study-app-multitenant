# I597 自動テスト: DB の控えの入口を Claude から流せる形で直す

実行コマンド（例）: `bash scripts/claude/tests/run-all.sh scripts/claude/tests/test_i597_db_backup.sh`

結果:
- backend: 対象なし（アプリのコードの変更なし）
- frontend: 対象なし

## テストケース

| TC | 対象 | 確かめること | 期待値（合否は終了コード） |
|---|---|---|---|
| TC-01 | `scripts/claude/tests/test_i597_db_backup.sh` の S 項目 | 写しのリポジトリ・偽の `docker` で、S1 成功（`backup_t1_<日時>.sql` が 1 つ・中身が偽の出力と同じ・権限 600・`backup_partial_*` が無い・出力に `✅ 控えを取りました`）／S2 `pg_dump` が終了コード 1（途中まで出力）→ 入口が 1・`backup_*.sql` が 0 個／S3 出力が空・終了コード 0 → 1・0 個／S4 完了の行が無い（途中で切れた）→ 1・0 個／S5 完了の行はあるが `\restrict` と対の `\unrestrict` が欠けた → 1・0 個／S6 `\restrict` の無い古い形（完了の行あり）→ 0・1 個／S7 名前 `../x`・`a b`・`""`（空）・引数 2 つ → 2・0 個・偽の `docker` が呼ばれていない／S8 人の包み `scripts/db_backup.sh` が S2 の条件で非 0・0 個、S1 の条件で 0・1 個・案内の行が出る／S9 失敗の出力に入口の案内 `bash scripts/claude/db-backup.sh` が出る | テストのスクリプトが exit 0（全項目 PASS） |
| TC-02 | 入口・人の包みの構文 | `bash -n` が通る | exit 0 |
| TC-03 | 同じテストの FG 項目（失敗の注入・写しだけを壊す） | FG1 入口の写しから `trap` の行を消す → S2 が「残る」で不合格になる／FG2 完了の行の確かめを消す → S4 が不合格になる／FG3 人の包みを今の形（`docker compose exec … > "$OUTPUT"`）に戻す → S8 が不合格になる | テストのスクリプトが exit 0（FG が期待どおり不合格を検出） |
| TC-04 | `.gitignore` | `.github_token` の行がある（`.github_token` が git から外れる）・つながった行が無い | 下のゲートの 2 行が exit 0 |
| TC-05 | `docs/runbooks/danger-ops.md` | 控えの節があり、入口のコマンドが書いてある | 下のゲートの 2 行が exit 0 |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i597_db_backup.sh
bash -n scripts/claude/db-backup.sh
bash -n scripts/db_backup.sh
grep -q "^\.github_token$" .gitignore
! grep -q "tokenbackup" .gitignore
grep -q "## 破壊的な DB の操作の前の控え" docs/runbooks/danger-ops.md
grep -q "bash scripts/claude/db-backup.sh" docs/runbooks/danger-ops.md
```

## 実行記録
- 2026-11-20 plan: TC-01〜TC-03 は実装前のため未実行（テストのスクリプト・入口が無い）
- 2026-11-20 plan: TC-04・TC-05 の 4 行を直す前の状態で流し、4 行とも rc=1（不合格）を確かめた（直す前の状態がそのまま失敗の注入になる）。合格は実装の後に確かめる
