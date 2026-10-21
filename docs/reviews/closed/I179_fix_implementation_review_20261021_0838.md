実装コードを確認しました。判定を行います。

---

# 実装レビュー [I179]

## 指摘一覧

| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 方針一致 | `_is_volumes_flag` の `--volumes=false` → `True` 判定（`val.lower() not in ("false", "0")` により `false` は除外されるはず）なのに、DV23 は「block（安全側）」と期待している。原因は正規表現層の `--volumes\b` が `=false` 前の word boundary でもマッチするため正規表現層で止まる。テスト期待値は診断メモの受容事項と一致しており矛盾なし | `_is_volumes_flag`・DV23 |
| Info | 方針一致 | `STUB_WORKDIR-$(cd "$STUB_WT" && pwd -P)` に変更（`:-` → `-`）で「空文字列を渡す TC（R21c）」が実現できるようになった。ただし `STUB_WORKDIR` を明示的に空にしたとき `--format` 出力が0行ではなく空行1行になるため、`wt-remove.sh` 内の `while IFS= read -r d; do [ -n "$d" ] || return 4` の `return 4`（exit 2）が正しく発火する。TC R21c の期待値（exit2）と合っており問題なし | `test_wt_lifecycle.sh:50` |

**BLOCKER / HIGH 指摘: なし**

診断メモ（`I179_fix_diagnosis_20261021_0220.md`）で指摘された F1〜F5 すべての対応状況:

| 指摘 | 対応状況 |
|------|---------|
| F1（ガード後退）| `_DOCKER_WIPE_RES` 正規表現 ∪ `_docker_volume_wipe_tokens` の和集合で解消。DV-sh 28形・NOREG・FG-DV2/FG-DV3 で後退なしを機械保証 |
| F2（heredoc 除外で実行コマンドが隠れる）| `_docker_volume_wipe_tokens` から heredoc 除外ロジックを撤回。`cat <<EOF && docker compose down -v` 等 4 形が DV-sh に追加されブロックを確認 |
| F3（記録の不整合）| イシュー・計画 4-6・`danger-ops.md`・`worktree.md` §5(C) すべてに 2026-10-21 改訂注記を追加 |
| F4（止まった後の手順・バックアップ改善）| `worktree.md` §4「止まったときの片付け」新設・`backup_hint()` を 3 手順（up -d db → pg_dump → test -s）に改訂・`bash $0` 形式の再実行案内・§11 の untracked/未 push 入れ子の扱い追加 |
| F5（テストの脆弱性）| R21b〜d・R22c・P15a〜e・スタブの空ラベル対応・`_CMD_PREFIXES`/`eval`/`&` の TC・`pytest -k down -v` 許可 TC すべて追加 |

VERDICT: OK
