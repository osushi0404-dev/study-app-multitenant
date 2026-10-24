# I185 自動テスト: 開発環境の総点検と改善

実行コマンド: 下の「決定論ゲート」を `/code-review` が実走する（heavy なテストは無し。アプリのコード変更はない）

対象ファイル: `docs/proposals/I185_dev_env_review.md`（段 A のステップ 3 で作成）

| TC | 確かめること | 合否（exit code） |
|---|---|---|
| TC-01 | 観点一覧の見出し `## 1. ベストプラクティスの観点` がある | 合格=0 |
| TC-02 | 公式ドキュメントの出典 URL（`https://code.claude.com/docs/`）が載っている | 合格=0 |
| TC-03 | 記録の数字の見出し `## 2. 作業記録の数字` がある | 合格=0 |
| TC-04 | 数え方が「リポジトリ内の記録で数えるもの」に分けて書かれている | 合格=0 |
| TC-05 | 数え方が「手元の記録でしか数えられないもの」に分けて書かれている | 合格=0 |
| TC-06 | 漏れと手間の一覧の見出し `## 3. 止めている漏れとかかる手間` がある | 合格=0 |
| TC-07 | 公式機能との差分の見出し `## 4. 公式機能との差分` がある | 合格=0 |
| TC-08 | 改善案の見出し `## 5. 改善案` がある | 合格=0 |
| TC-09 | 採否の見出し `## 6. 採否` がある | 合格=0 |

### 段 B（計画変更記録 2 で追加・P1〜P5）

| TC | 対象 | 確かめること | 合否（exit code） |
|---|---|---|---|
| TC-10 | P1 | `test_posttooluse_check.sh`: 壊れた `.json`・`.py` を渡すとフックが exit 2 で終わり、stderr に `syntax error` を含む。正しいファイル・対象外の拡張子・`file_path` なしでは exit 0 | 合格=0 |
| TC-11 | P5 | `test_sessionstart_context.sh`: 通常はフックが exit 0 で、出力に `branch:` と `直近にマージされた PR` を含む。gh が失敗する環境（`GH_HOST` を存在しないホストにする）でも exit 0 で、`取得できませんでした` を含み、20 秒以内に終わる。git の外のディレクトリから実行しても exit 0 | 合格=0 |
| TC-12 | P5 | `.claude/settings.json` が JSON として正しい | 合格=0 |
| TC-13 | P5 | `.claude/settings.json` に SessionStart フックとして `sessionstart_context.py` が登録されている | 合格=0 |
| TC-14 | P2〜P4 | `test_i185_harness_docs.sh`: ①どの `SKILL.md` にも `allowed-tools:` 行がない ②`security-review` に `disallowed-tools: Bash, Write, NotebookEdit` がある ③`plan-issue` の手順に `bash scripts/claude/plan-issue-review.sh $ARGUMENTS` があり、「承認後の次のステップ: `/plan-issue-review`」がない ④`workflow.md` の移行表に「計画書承認後 → `/plan-issue-review` を入力」がない ⑤`fix-loop` の手順 4 に「推奨案で進めて手順 5 へ」と 5 つの条件があり、3 つの関所のスクリプト名（fix-diagnosis-review.sh・fix-implementation-review.sh・fix-test-review.sh）が残っている | 合格=0 |
| TC-15 | P5 | `sessionstart_context.py` が Python として正しい | 合格=0 |

false-green の確認（実装時に行い、結果をここに書く）:
- TC-10 は、環境変数 `HOOK` で変更前のフック（`git show` で取り出した旧版）を指定して実行し、不合格（非 0）になることを確かめる。
- TC-11 は、環境変数 `SCRIPT` で、常に exit 1 で終わるおとりを指定して実行し、不合格になることを確かめる。
- TC-14 は、環境変数 `ROOT` で変更前のファイル一式を置いた一時ディレクトリを指定して実行し、不合格になることを確かめる。

### 計画時の false-green 確認（2026-10-24）
- 見出しは行頭・行末を固定（`^...$`）して判定する。最初の案（固定なし）は、似た見出し「## 6. 採否の候補」でも合格してしまうことを、非対話の bash（`/usr/bin/grep`）で確かめたため直した。
- 似た見出し・欠けた見出しだけのおとりファイルで 9 件とも exit=1（不合格）、必要な見出しをすべて持つファイルで 9 件とも exit=0（合格）になることを確認済み。報告書が未作成の現時点では 9 件とも exit=2（不合格）。

結果:
- 段 A（報告書作成時・2026-10-24）: TC-01〜TC-09 すべて exit=0（非対話 bash の `/usr/bin/grep` で実走）

## 決定論ゲート（自動実走）
```bash
grep -q "^## 1\. ベストプラクティスの観点$" docs/proposals/I185_dev_env_review.md
grep -q "https://code\.claude\.com/docs/" docs/proposals/I185_dev_env_review.md
grep -q "^## 2\. 作業記録の数字$" docs/proposals/I185_dev_env_review.md
grep -q "^#### リポジトリ内の記録で数えるもの$" docs/proposals/I185_dev_env_review.md
grep -q "^#### 手元の記録でしか数えられないもの$" docs/proposals/I185_dev_env_review.md
grep -q "^## 3\. 止めている漏れとかかる手間$" docs/proposals/I185_dev_env_review.md
grep -q "^## 4\. 公式機能との差分$" docs/proposals/I185_dev_env_review.md
grep -q "^## 5\. 改善案$" docs/proposals/I185_dev_env_review.md
grep -q "^## 6\. 採否$" docs/proposals/I185_dev_env_review.md
bash scripts/claude/tests/test_posttooluse_check.sh
bash scripts/claude/tests/test_sessionstart_context.sh
python3 -m json.tool .claude/settings.json
grep -q "sessionstart_context\.py" .claude/settings.json
bash scripts/claude/tests/test_i185_harness_docs.sh
python3 -m py_compile scripts/claude/hooks/sessionstart_context.py
```
