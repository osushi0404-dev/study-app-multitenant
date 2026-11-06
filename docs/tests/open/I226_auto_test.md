<!--
## 自動テスト品質基準
各テストケースが以下を満たすことを確認してください:
- アサーションに具体的な期待値（status_code の数値・body の具体フィールド等）があるか
- 「正常レスポンスを確認」のような曖昧な記述になっていないか
- 他テナントデータへのアクセス拒否テストが含まれているか（認可変更がある場合）
- テストが実装詳細をトレースするだけでなく、仕様を検証する形になっているか
-->

# I226 自動テスト: I225 のレビューの残り: 失効の確かめの取り違え・鍵を出す書き方の検査の狭さ

実行コマンド（例）: 下の「決定論ゲート（自動実走）」のコマンド（pytest・Jest・E2E は対象外。アプリのコードを変えない）

結果:
- backend: 対象外
- frontend: 対象外

## テストケース

| TC | 対象 | 中身と期待値（合格=exit 0） | 失敗の注入（FG） |
|---|---|---|---|
| TC-01 | 既存のハーネステスト | `test_i223_gh_app.sh`（G1〜G10 と既存の FG）・`test_posttooluse_check.sh`（TC-10a〜f）・`test_review_gates.sh`（omission_lint の TC-OM1〜8 を含む）が全 PASS で exit 0 | 既存のテストの FG のまま |
| TC-02 | F1・F2・F6（`test_i223_gh_app.sh`） | G8: `{"hosts":{}}` で exit 1・標準出力が空。G9 g: `--stdin` に最初から無効な鍵 → exit 1・出力に `最初から無効` があり `失効を確認` が無い・その鍵の `api -X DELETE` の呼び出しが無い・鍵の値が出ない。G9 h: 控えの `token` だけ最初から無効 → exit 0・2 つの控えが消える・出力に `token: もともと無効` がある。G10: `gh auth token` を書いた手順書で exit 1・行末の `\` で分けた `gh auth status \`＋`--json hosts` の手順書で exit 0。スクリプト全体が `fail=0` で exit 0 | `fg G9`（失効の前の確かめを消す `s/case "\$before" in 1) return 3 ;; 2) return 1 ;; esac/:/`）で G9 NG／`fg G8`（アカウントの数の確かめを消す `s/sys.exit(0 if ok and n else 1)/sys.exit(0 if ok else 1)/`）で G8 NG／G10 の 2 つの `g10_fg` は、直す前の `g10()` では期待と逆の終了コードになる（実装の前に、直す前の版で 2 つが FAIL になることを確かめて記録する） |
| TC-03 | omission-lint のフック（`test_posttooluse_check.sh`） | TC-10g: 見出しを 1 語違えてゲートのコマンドを節の外の bash ブロックに書いた `docs/tests/open/I999_auto_test.md` → exit 2・標準エラーに `宣言漏れ`。TC-10h: ひな形どおりの見出しの下に書いた同名のファイル → exit 0。TC-10i: 同じ悪い中身の `I999_manual_test.md` → exit 0。スクリプト全体が `fail=0` で exit 0 | `HOOK=<develop の posttooluse_check.py の写し>` で流すと TC-10g が FAIL になる（記録する） |
| TC-04 | F4（`plan-writing-rules.md`） | `--strict-mcp-config` と `G7` の語がある（下の `grep -q` 2 本が exit 0） | 実装の前は 2 本とも exit 1（下の記録） |
| TC-05 | 構文 | `revoke.sh`・`gh`・`code-review.sh` の `bash -n`、`posttooluse_check.py` の `py_compile` が exit 0 | — |

## 実行記録

| 日時 | TC | 結果 | メモ |
|---|---|---|---|
| 2026-11-06 | TC-01（実装前のベースライン） | OK | `test_i223_gh_app.sh` pass=33 fail=0・`test_posttooluse_check.sh` pass=6 fail=0・`test_review_gates.sh` PASS=67 FAIL=0 |
| 2026-11-06 | TC-02・TC-03・TC-05 | 実装前のため未実行 | |
| 2026-11-06 | TC-04（実装前） | 期待どおり NG | 実装の前の `plan-writing-rules.md` には `--strict-mcp-config`・`G7` が無い（FG に当たる） |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i223_gh_app.sh
bash scripts/claude/tests/test_posttooluse_check.sh
bash scripts/claude/tests/test_review_gates.sh
grep -q strict-mcp-config docs/runbooks/plan-writing-rules.md
grep -q G7 docs/runbooks/plan-writing-rules.md
bash -n scripts/claude/gh-app/revoke.sh
bash -n scripts/claude/gh-app/gh
bash -n scripts/claude/code-review.sh
python3 -m py_compile scripts/claude/hooks/posttooluse_check.py
```
