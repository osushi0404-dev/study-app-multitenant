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
| TC-11 | P5 | `test_sessionstart_context.sh`: 通常はフックが exit 0 で、出力に `branch:` と `直近にマージされた PR` を含む。gh が失敗する環境（`GH_HOST` を存在しないホストにする）でも exit 0 で、`取得できませんでした` を含み、20 秒以内に終わる。git の外のディレクトリから実行しても exit 0。`format_context()` に、指示らしい文言を含むタイトル（例: 「Ignore previous instructions」）の PR・イシューを渡しても、出力にその文言が含まれず、番号と `I###` だけが出る。出力が 10 行以内 | 合格=0 |
| TC-12 | P5 | `.claude/settings.json` が JSON として正しい | 合格=0 |
| TC-13 | P5 | `.claude/settings.json` に SessionStart フックとして `sessionstart_context.py` が登録されている | 合格=0 |
| TC-14 | P2〜P4 | `test_i185_harness_docs.sh`: ①どの `SKILL.md` にも `allowed-tools:` 行がない ②`security-review` に `disallowed-tools: Bash, Write, NotebookEdit` がある ③`plan-issue` の手順に `bash scripts/claude/plan-issue-review.sh $ARGUMENTS` があり、「承認後の次のステップ: `/plan-issue-review`」がない ④`workflow.md` の移行表に「計画書承認後 → `/plan-issue-review` を入力」がない ⑤`fix-loop` の手順 4 に「推奨案で進めて手順 5 へ」と 6 つの条件（⑥ 認証・認可・テナント境界・秘密情報の扱い・権限設定・フック・GitHub Actions に触れない、を含む）があり、3 つの関所のスクリプト名（fix-diagnosis-review.sh・fix-implementation-review.sh・fix-test-review.sh）が残っている ⑥`fix-loop` の共通ルール (b) に「手順4（新案なので条件を判定し直す）」があり、「手順4 ユーザー承認（新案のため）」がない ⑦`issue-flow.md` と `onboarding.md` に「`/plan-issue` の中で計画レビュー」の説明がある | 合格=0 |
| TC-15 | P5 | `sessionstart_context.py` が Python として正しい | 合格=0 |

敵対的レビュー 1 周目（`docs/reviews/I185_adversarial_review_20261024_1830.md`）を受けた追加:
- TC-11f: 偽の gh を PATH の先頭に置き、PR・最新イシューの値が「#番号 I### 日付」で出る（GitHub を呼ばない版で不合格になることを確認）
- TC-11g: `.claude/settings.json` の `hooks.SessionStart[*].hooks[*].command` にフックが登録されている（イベント名を打ち間違えた設定で不合格になることを確認。TC-13 の grep より厳しい）
- TC-14②: frontmatter の中だけを見る（本文へ移した版で不合格）
- TC-14③c〜③f: 計画レビューの実行が承認ポイントの提示より前・古い停止文がない・スクリプトの案内を承認前に伝えない・判定前の失敗で承認ポイントを出さない（レビューを承認の後に戻した版で不合格）
- TC-14⑤b2・⑤f〜⑤n: 条件 ①〜⑥（レビュー・判定の仕組みの除外を含む）・満たさないときの停止・絶対ルール 2 との関係（停止の行を壊した版で不合格）
- TC-14⑧: `allowed-tools` を必須・最小権限として扱う古い基準が残っていない
- 結果: TC-11 は 7/7、TC-14 は 31/31 合格

敵対的レビュー 2 周目（`docs/reviews/I185_adversarial_review_20261024_1905.md`・上限到達）を受けた作り直し（計画変更記録 7）:
- TC-14 は、守りの部分のブロックを丸ごと固定して照合する形に変えた（固定した文章は `scripts/claude/tests/fixtures/i185/`。TC-14pin×6・③・④・⑦・①・⑧a〜c・⑤a〜c の 16 件）。P3 を外したので、fix-loop は承認待ちのままであることを確かめる（⑤a〜c）
- 壊した版 7 種類（手順 1 での承認待ちの挿入・節の前の停止・frontmatter の外へ移動・書式を変えた必須項目・fix-loop の自動進行・移行表の書き換え・2 回 NG の停止の削除）で、7 種類とも不合格（rc=1）になることを確認した
- TC-11g は matcher（無い・`*`・`startup` に一致）とコマンドの完全一致を確かめる。matcher を `compact` にした設定・コマンドを `true # …` にした設定で不合格。TC-11e は `\d` に戻した日付の判定で不合格
- TC-16（新規の決定論ゲート）: `test_review_verdict.sh`。VERDICT 行も「## 判定: ✅」も無いレビュー記録は UNKNOWN（判定不能）になる（TC-17b・17c・25b を追加、TC-21b・25・26 の期待値を UNKNOWN に変更）。58 件合格
- 結果: TC-11 は 7/7、TC-14 は 16/16、TC-16 は 58/58 合格

false-green の確認（2026-10-24・実装時に実施）:
- TC-10: テストを先に書き、変更前のフック（exit 1）に当てて実行 → TC-10a・10b が不合格（rc=1）、全体 exit 1。直した後は 6 件すべて合格。
- TC-11: 常に exit 1 で終わり、タイトルをそのまま出すおとり（`SCRIPT` で指定）に当てて実行 → 5 件中 4 件が不合格、全体 exit 1。フックを書く前（ファイルなし）も 4 件不合格。
- TC-14: テストを先に書き、変更前のスキル・手順書に当てて実行 → 14 件中 11 件が不合格（関所のスクリプト名 3 件は変更前から存在するので合格）、全体 exit 1。直した後は 14 件すべて合格。

### 計画時の false-green 確認（2026-10-24）
- 見出しは行頭・行末を固定（`^...$`）して判定する。最初の案（固定なし）は、似た見出し「## 6. 採否の候補」でも合格してしまうことを、非対話の bash（`/usr/bin/grep`）で確かめたため直した。
- 似た見出し・欠けた見出しだけのおとりファイルで 9 件とも exit=1（不合格）、必要な見出しをすべて持つファイルで 9 件とも exit=0（合格）になることを確認済み。報告書が未作成の現時点では 9 件とも exit=2（不合格）。

結果:
- 段 A（報告書作成時・2026-10-24）: TC-01〜TC-09 すべて exit=0（非対話 bash の `/usr/bin/grep` で実走）
- 段 B（実装時・2026-10-24）: TC-10（6/6）・TC-11（5/5）・TC-12・TC-13・TC-14（14/14）・TC-15 すべて合格
- 既存のハーネスのテスト（`scripts/claude/tests/*.sh` 全 33 本）: 31 本合格。`test_i181_review_slim.sh`（D8）と `test_i182_docs.sh`（DOC6）の 2 本が不合格だが、今回の変更とは関係ない（develop の時点から同じ）。どちらも、今回変えていない `review-rules.md`・`danger-ops.md` に書かれたパスの実在チェックで、harness-1 のワークツリーには無いパス（`.claude/worktrees/`・`.claude/settings.local.json`）と、I181 のクローズで closed へ移った `docs/issues/open/I181.md` を指している。是正は P12（手順書の整理）の別イシューに入れる

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
bash scripts/claude/tests/test_review_verdict.sh
```
