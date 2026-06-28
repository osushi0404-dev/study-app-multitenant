# I081 手動テスト（統合・実セッション挙動）

決定論的なフック単体検証は `I081_auto_test.md`（TC-G/TC-D）で担保。本書は **実リポジトリ・実セッションでの統合挙動**を確認する。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `bash scripts/claude/tests/test_pretooluse_checkout_guard.sh` を実行 | `pass=N fail=0` で終了コード 0。全 TC-G が PASS | Claude | OK | 決定論スクリプトの実走 |
| 2 | `common-commands.md` / `danger-ops.md` を Read し、複合禁止・`; echo "exit=$?"` 不可・Read 閲覧・「原則/例外」・checkout 取り消し注意・相互参照の記載を確認 | 全項目の文言が存在する | Claude | OK | TC-D1〜D3 の目視裏取り |
| 3 | `code-reviewer.md` / `plan-reviewer.md` を Read し、コマンド衛生・破壊的取り消しの gate 観点を確認 | 両ファイルに2観点が存在する | Claude | OK | TC-D4 の目視裏取り |
| 4 | 実リポジトリで使い捨てファイルを作成・コミット後にワークツリーを変更し（dirty）、`git checkout -- <使い捨て>` を実行 | PreToolUse フックがブロック（プロンプト/`exit 2`・"discard uncommitted changes" メッセージ）。未コミット変更が消えない | Claude | OK | 使い捨てファイルで安全に実施。`DANGER_OK=1` 前置時のみ通ることも確認 |
| 5 | 実リポジトリで `git checkout <別ブランチ>`（ブランチ切替）や clean ファイルの revert を実行 | ブロックされず通常どおり実行できる（誤検知なし） | Claude | OK | 通常運用を妨げないことの確認 |
| 6 | 追記した 4 ファイル（runbook 2・review-agent 2）の追記分にイシュー番号（`I079`/`I080` 等）が含まれないことを確認 | イシュー番号の混入なし（一般形） | Claude | OK | TC-D5 の目視裏取り |

> 全項目 Claude で実施可能（ファイル確認・コマンド/スクリプト実行・使い捨てファイルでのフック挙動確認）。ブラウザ/UX 操作はなし。

## 実施結果（/test・2026-06-28）
- **No.1**: `test_pretooluse_checkout_guard.sh` → **pass=14 fail=0**（OK）
- **No.2/3/6**: runbook・review-agent の文言を grep -F／diff で確認（TC-D1〜D5 PASS・追記差分にイシュー番号なし）（OK）
- **No.4（ライブ）**: 実リポジトリで tracked ファイルを dirty にして `git checkout -- <file>` → **PreToolUse フックが exit 2 でブロック**（メッセージ「git checkout/restore would discard uncommitted changes in '...'. Edit で戻すか…」を実観測）。未コミット変更は消えず、Edit で復元（規約どおりの運用を実演）（OK）
- **No.5（ライブ）**: `git checkout -- CLAUDE.md`（clean）と `git checkout <現ブランチ>` → いずれも**ブロックされず no-op**（誤検知なし）（OK）
