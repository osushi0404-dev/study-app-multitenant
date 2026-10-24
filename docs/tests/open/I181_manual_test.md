# I181 手動テスト: レビュー工程の余分・過剰を見直して開発を速くする

**共通の準備**: リポジトリのファイル・GitHub には、本イシューの通常の工程（`/code-review` の記録のコミット・PR コメント）以外で書き込まない。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | 本イシューの `/code-review I181`（実装後・ステップ 6 の push の後）で出た `docs/reviews/I181_code_review_<ts>.md` を Read し、スクリプトの標準出力の固定行を見る | 記録の決定論ゲートの証跡に `高リスク判定: NO（LLM=NO / path=NO）` があり、標準出力に `ADVERSARIAL_STAGE: NOT_REQUIRED` と「✅ コードレビュー完了。`/test I181` を実行してください。」が出ている | Claude | ✅ 2026-10-24: `docs/reviews/I181_code_review_20261024_1136.md` の 13 行目が `高リスク判定: NO（LLM=NO / path=NO）`。標準出力は `RISK: NO`・`FINAL_VERDICT: OK`・`ADVERSARIAL_STAGE: NOT_REQUIRED`・「✅ コードレビュー完了。`/test I181` を実行してください。」。LLM の該当条件欄は「harness 固有・Yes にしない」条件に該当と明記。CI（`gh pr checks 311`）は 6 件すべて pass | 新しい判定が本イシュー自身（スキル・スクリプト・レビュー指示・runbook・テストの変更）に効いていることの確認。YES が出たら、その理由（LLM か path か・該当条件）を `I181_review.md` に記録し、計画書「レビューの重さ」のとおり扱う |
| 2 | `.claude/skills/code-review/SKILL.md` の §3 を、文脈を持たない人が読む想定で通読する（Read） | 3-1 の 1〜5（周回の残りの数え方・`{REVIEW_BASE}` の決め方・HEAD の控え方・3 体＋`sleep 900` を 1 メッセージで裏で起動・時間切れで `TaskStop`）と、3-2 の上限到達時の選択肢の順（方式の見直し → 1 周延長 → 受け入れ）が、どれも具体的なコマンドやツール名まで書かれ、「適宜」「必要に応じて」で済ませた手順が無い | Claude | ✅ 2026-10-24: SKILL.md 34〜63 行を通読。3-1 の 1（`ROUNDS:` 行の合計・行が無い旧記録は見出しを数え、無ければ 1 周）・2（最新記録の `REVIEWED_COMMIT:` か `origin/develop`）・3（`git rev-parse HEAD`）・4（Agent ツールと Bash ツールを 1 メッセージで `run_in_background: true`・`sleep 900`）・5（ID を控え、`TaskStop` の `task_id` に渡す・時間切れの記録と数え方）と、3-2 の選択肢の順（方式の見直し → 1 周延長 → 受け入れ）が、すべてツール名・コマンド・行の名前まで書かれている。「適宜」「必要に応じて」は無い | plan-writing-rules「指示ファイルへの条件分岐追加時のコマンド粒度パリティ」の確認 |
| 3 | 3-6 の表の 6 の起票案（fix-loop の 3 ゲートの統合）を、ユーザーに提示する | 起票するかをユーザーが判断する（起票した場合はイシュー番号を `I181_review.md` に記録） | Human | | 起票は `/issue-bootstrap`（ユーザー操作）。本イシューの合否には関係しない |

結論: （実施後に記入）
