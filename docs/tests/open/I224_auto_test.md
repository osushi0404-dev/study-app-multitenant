<!--
## 自動テスト品質基準
各テストケースが以下を満たすことを確認してください:
- アサーションに具体的な期待値（status_code の数値・body の具体フィールド等）があるか
- 「正常レスポンスを確認」のような曖昧な記述になっていないか
- 他テナントデータへのアクセス拒否テストが含まれているか（認可変更がある場合）
- テストが実装詳細をトレースするだけでなく、仕様を検証する形になっているか
-->

# I224 自動テスト: GitHub への書き込み（イシューの書き換え・コメント・push）の回数を絞り、短い間に集中しないようにする

実行コマンド（例）: 下の「決定論ゲート（自動実走）」のコマンド（pytest・Jest・E2E は対象外。アプリのコードを変えない）

結果:
- backend: 対象外
- frontend: 対象外

## テストケース

| TC | 対象 | 中身と期待値（合格=exit 0） | 失敗の注入（FG） |
|---|---|---|---|
| TC-01 | 既存のハーネステスト | CI の Harness Tests（`run-all.sh`）が全 PASS。手元では流し直さない（CI が正） | 既存のテストの FG のまま |
| TC-02 | 書き込みの時点（`test_i224_push_points.sh`） | P1: `plan-issue`・`review-gate`・`close` 以外のスキルに `commit/push`・`commit・push`・`コミット・push`・`git push` が無い。P2: 行の先頭の `git push` が `plan-issue` 2・`review-gate` 1・`close` 1。P3: `gh issue edit` は `grill-me` だけ。P4: `workflow.md` に「## GitHub への書き込みの時点」がある。スクリプト全体が `fail=0` で exit 0 | テストの中で一時フォルダの写しを壊す: `retro` に `commit/push` を足す（P1 NG）・`review-gate` の `git push` を 2 行にする（P2 NG）・`retro` に `gh issue edit` を足す（P3 NG）・節の見出しを消す（P4 NG） |
| TC-03 | 同時書き込みの決まり | `workflow.md` に「同時に複数のセッションで」の語がある（下の `grep -q` が exit 0） | 実装前は exit 1（下の記録） |
| TC-04 | 構文 | `test_i224_push_points.sh` の `bash -n` が exit 0 | — |

## 実行記録

| 日時 | TC | 結果 | メモ |
|---|---|---|---|
| 2026-11-07 | TC-03（実装前） | 期待どおり NG | `workflow.md` に「GitHub への書き込みの時点」「同時に複数のセッションで」が無い（どちらも exit 1） |
| 2026-11-07 | TC-02（実装前の数え） | — | 行の先頭の `git push`: `plan-issue` 2・`review-gate` 0・`close` 1。`gh issue edit` は `grill-me` だけ。テストは実装前のため未作成 |
| 2026-11-07 | TC-02（テストを先に書き、本体を直す前） | 期待どおり NG | P1 が 13 か所・P2（`review-gate` 0 行）・P4（節なし）で不合格 |
| 2026-11-07 | TC-02・TC-03・TC-04（実装と /simplify の後） | OK | `test_i224_push_points.sh` pass=9 fail=0（FG 4 つとも、その決まりで不合格になることを含む）・`grep -q` exit 0・`bash -n` exit 0 |
| 2026-11-07 | TC-01（変えたスキル・手順書を読むテスト 17 本だけ手元で） | OK | `test_i185_harness_docs.sh`（固定ファイルを `--update` で作り直した後）・`test_i193_official_flow.sh` ほか 17 本がすべて exit 0。全体は CI |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i224_push_points.sh
bash scripts/claude/tests/test_i185_harness_docs.sh
grep -q 同時に複数のセッションで docs/runbooks/workflow.md
bash -n scripts/claude/tests/test_i224_push_points.sh
```
