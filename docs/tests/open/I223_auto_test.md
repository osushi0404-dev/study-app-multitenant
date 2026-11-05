# I223 自動テスト: GitHub App の鍵の仕組みをリポジトリに入れ、テスト用のセッションを読み取りだけにする

実行コマンド（例）: 下の「決定論ゲート」（アプリのコード変更なし。pytest・Jest・E2E は CI が流す）

結果:
- backend: 対象外
- frontend: 対象外

## テストケース
| TC | 内容 | 合否の判定 | 結果 |
|---|---|---|---|
| TC-01 | 実装対象のファイルを見ている既存のテスト 7 本（`test_i187_frontend_verify_config.sh`・`test_check_permission_prompt.sh`・`test_i197_adversarial_process.sh`・`test_i107_track_label_docs.sh`・`test_i179_worktree_docs.sh`・`test_i185_harness_docs.sh`・`test_next_issue_num.sh`）と新しい `test_i223_gh_app.sh`、計画変更記録 3 で触る起動の行を見ている `test_i193_official_flow.sh`（R7・S8）・`test_fix_review.sh` が合格する | 各スクリプトが exit 0（下の決定論ゲート） | 実装前のベースライン（2026-11-05・feature/I223 の 63a6e9f2）: 既存の 7 本とも exit 0（14/26/113/6/16/17/21 件合格）。`test_i223_gh_app.sh` は実装前のため未実行。test_i187 は ② を直すまで今の形で合格（4-7 で「github が無い」に直す） |
| TC-02 | `test_i223_gh_app.sh` の G1〜G5（`curl`・`openssl`・本物の `gh`・`claude` は一時フォルダの偽物。秘密の鍵ファイルと本物の GitHub は使わない）: **G1** `GH_APP_READONLY=1` のとき、`gh-app-token` が GitHub に送る本文の `permissions` がすべて `read`（7 つ）で、控えは `token-readonly` に書かれ `token` に書かれない／指定が無いときは本文に `permissions` が無い **G2** 有効な書き込みの鍵が `token` に控えてあっても、`GH_APP_READONLY=1` では返さず、読み取りだけの鍵を受け取って返す **G3** `GH_APP_READONLY=1` で、GitHub の応答の `permissions` に `write` が 1 つでもあれば exit 1 で鍵を出さず、控えも作らない **G4** `gh` の入口に `GH_APP_READONLY=1` と `GH_APP_DISABLE=1` を両方付けても、本物の `gh` に読み取りだけの鍵が `GH_TOKEN` で渡る／`GH_APP_DISABLE=1` だけなら鍵を渡さない **G5** テスト用のセッションを起こす 3 か所（`test-session.sh`・`check-permission-prompt.sh`・`review-process-lib.sh` の `run_claude_logged`）が、`CLAUDE_BIN` の偽物に `GH_APP_READONLY=1` を渡す **G6**（計画変更記録 3）`scripts/claude/*.sh` の `claude -p` の呼び出しの論理行（行末の `\` でつなぐ・コメントは除く）がすべて `GH_APP_READONLY=1` を持つ（`export GH_APP_READONLY=1` するファイルは除く） | スクリプトが exit 0。FG は G6 も（`plan-issue-review.sh`・複数行の `fix-review-lib.sh` の写しから指定を消す）。各 G に FG（スクリプトの写しを `sed` で壊す: G1 本文から `permissions` を消す／G2 控えのファイル名を同じにする／G3 権限の確かめを消す／G4 `GH_APP_READONLY` の条件を消す／G5 各 3 か所の `GH_APP_READONLY=1` を消す）を付け、壊した写しでは該当の G が不合格になることをテストの中で確かめる | 実装前のため未実行 |
| TC-03 | コミットの前の検査（`detect-secrets-hook --baseline .secrets.baseline`・CI の pre-commit も同じ）が、偽の秘密の鍵ファイル（RSA の秘密の鍵の見出し行で始まるファイル）と App の鍵の形の文字列（`ghs_` ＋ 36 文字）を見つけて止め、何も無いファイルは通す（受け入れ条件 2 の決定論のチェックが App の鍵の形にも効くことの確かめ。検査そのものは今あるもの。2026-11-05 の計画のコミットで、この文書に見出し行をそのまま書いたら同じ検査がコミットを止めた＝入口でも効いている） | 偽の鍵 2 つで非 0・何も無いファイルで 0（一時フォルダのファイルで流す。スクラッチパッドの `tc03_detect_secrets.sh`。FG は「何も無いファイルは 0」の側で兼ねる） | OK（2026-11-05・計画の段階・63a6e9f2）: `fake_key.txt: rc=1`・`fake_token.txt: rc=1`・`clean.txt: rc=0`・`fail=0` |

新しい決定論テストは G1〜G5 だけにする（plan_I223.md §9: 壊れても気づきにくく、壊れると本物の書き込みが起きる所）。手順書の文言・総点検の一覧・`.mcp.json` の中身（test_i187 ② の直しを除く）はレビューで見る。

## 実行記録
- 2026-11-05・plan（実装前）: TC-01 の既存 7 本とも exit 0。TC-03 OK

## TC-03 の手順（1 回だけ流す。`bash <このスクリプト> <リポジトリのルート>`）
```bash
set -uo pipefail
ROOT="$1"; D="$(mktemp -d)"; trap 'rm -rf "$D"' EXIT
python3 -I - "$D" <<'PY'
import os, random, string, sys
d = sys.argv[1]; r = random.Random(223)
pick = lambda n: "".join(r.choice(string.ascii_letters + string.digits) for _ in range(n))
h = "-" * 5; kind = "RSA " + "PRIVATE KEY"   # 見出し行をこの文書に直接書くと、この文書自体が秘密の検査に当たるため分けて組む
open(os.path.join(d, "fake_key.txt"), "w").write(f"{h}BEGIN {kind}{h}\n" + pick(64) + f"\n{h}END {kind}{h}\n")
open(os.path.join(d, "fake_token.txt"), "w").write("token = ghs_" + pick(36) + "\n")
open(os.path.join(d, "clean.txt"), "w").write("nothing secret here\n")
PY
fail=0
for f in fake_key.txt fake_token.txt clean.txt; do
  (cd "$ROOT" && detect-secrets-hook --baseline .secrets.baseline "$D/$f") >/dev/null 2>&1; rc=$?
  echo "$f: rc=$rc"
  if [ "$f" = clean.txt ]; then [ "$rc" -eq 0 ] || fail=1; else [ "$rc" -ne 0 ] || fail=1; fi
done
exit "$fail"
```

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i223_gh_app.sh
bash scripts/claude/tests/test_i187_frontend_verify_config.sh
bash scripts/claude/tests/test_check_permission_prompt.sh
bash scripts/claude/tests/test_i197_adversarial_process.sh
bash scripts/claude/tests/test_i107_track_label_docs.sh
bash scripts/claude/tests/test_i179_worktree_docs.sh
bash scripts/claude/tests/test_i185_harness_docs.sh
bash scripts/claude/tests/test_next_issue_num.sh
bash scripts/claude/tests/test_i193_official_flow.sh
bash scripts/claude/tests/test_fix_review.sh
```
