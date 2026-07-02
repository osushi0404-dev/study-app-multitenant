# I084 手動テスト

対象: code-review 決定論ゲート実走の実挙動・文書反映。自動（source-only 単体）で覆えない「実 `/code-review` フロー上の挙動」と「文書規約の反映」を確認する。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `docs/tests/templates/auto_test_template.md` を Read し `## 決定論ゲート（自動実走）` セクション規約（許可コマンド・チェーン不可・heavy は /test 委譲の注記）が追加されているか確認 | 当該見出しと注記コメント・```bash 例が存在 | Claude | ✅ OK | AC7・見出し＋注記コメント確認 |
| 2 | `.claude/review-agents/code-reviewer.md` を Read し「決定論ゲートは注入済み実結果を使い読解で PASS 断定しない」旨の追記を確認 | 該当文言が存在 | Claude | ✅ OK | AC5・「決定論ゲートの扱い（必須）」段落確認 |
| 3 | `docs/tests/open/I084_auto_test.md` に `## 決定論ゲート（自動実走）` セクションがあり `bash scripts/claude/tests/test_review_gates.sh` を宣言（ドッグフーディング）しているか確認 | 当該宣言が存在 | Claude | ✅ OK | AC9 |
| 4 | `bash scripts/claude/tests/test_review_gates.sh` を実行し PASS/FAIL 集計を確認 | fail=0 | Claude | ✅ OK | PASS=67 FAIL=0 |
| 5 | `extract_gate_commands docs/tests/open/I084_auto_test.md` を source-only で呼び、宣言された 2 コマンドが返るか確認 | `test_review_gates.sh`・`test_review_verdict.sh` の 2 行 | Claude | ✅ OK | 宣言 2 コマンドを返した |
| 6 | feature ブランチで実 `/code-review I084`（`scripts/claude/code-review.sh I084`）を実行し、生成された `docs/reviews/I084_code_review_*.md` に `### 決定論ゲート実行結果`（各ゲートの exit code）セクションが注入され、決定論ゲート実走済みであることを確認 | 証跡セクションが記録に存在し、宣言ゲートの実 exit code が並ぶ。ゲート全 pass なら末尾 `VERDICT` は LLM 判定を尊重、FAIL 時は `VERDICT: BLOCKER` | Claude（本セッションで実行済み） | ✅ OK | `I084_code_review_20260702_0200.md` に証跡セクション＋両ゲート exit=0＋FINAL VERDICT OK を確認 |
| 7 | No.6 の記録が PR コメントにも投稿され、Blocker/High/OK の案内メッセージが FINAL VERDICT と一致するか確認 | PR コメント本文＝記録ファイルと一致・routing 一致 | Claude（本セッションで実行済み） | ✅ OK | PR #174 の最新 review コメントに証跡＋`VERDICT: OK`・案内「✅ コードレビュー完了」と一致 |

## 停止条件
- 自動（test_review_gates.sh / test_review_verdict.sh）が 1 件でも FAIL → STOP・`/fix-loop I084`。
- No.6/No.7 で Human が NG → STOP・`/fix-loop I084`。
