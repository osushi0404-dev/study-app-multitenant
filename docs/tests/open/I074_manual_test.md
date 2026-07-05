# I074 手動テスト: fix-loop 多段サブエージェントレビュー順次ゲート

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | 実リポジトリで `bash scripts/claude/tests/test_fix_review.sh` を実行 | `pass=N fail=0`（exit 0）。全 TC（TC-01〜TC-25）PASS | Claude | | 決定論ゲート本体 |
| 2 | `.claude/review-agents/` に `fix-diagnosis-reviewer.md`・`fix-implementation-reviewer.md`・`fix-test-reviewer.md` が存在し、各々に読み取り専用ツール記述と末尾 `VERDICT:` 行があるか確認 | 3 ファイル存在・各々に `Read/Grep/Glob` と `VERDICT: BLOCKER|HIGH|OK`（相当）が含まれる | Claude | | Read で目視 |
| 3 | 診断メモを模した一時ファイルを作り `bash scripts/claude/fix-diagnosis-review.sh I999 <memo>` を dry 実行（`claude -p` が実際に走る／走らない両系） | `claude -p` 稼働時: `docs/reviews/I999_fix_diagnosis_review_<ts>.md` が生成され `FIX_GATE: PASS|REMAND` を出力し **exit 0(PASS)／1(REMAND)**。不可時（失敗/空/タイムアウト exit124）: 「レビュー未実施」記録＋`FIX_GATE: SKIP`・exit 0（fix-loop を止めない）。VERDICT 行欠落時も `FIX_GATE: SKIP`（PASS にしない） | Claude | | exit code ゲート＋非ブロック skip（timeout・判定不能含む）の実挙動確認。実行後、commit された場合は `git rm -f docs/reviews/I999_fix_*` → `git commit -m "chore: remove test artifact I999"`（未 commit なら `rm -f docs/reviews/I999_fix_*`）＝一時 I999 記録を残さない |
| 4 | `fix-implementation-review.sh`／`fix-test-review.sh` が context に `git diff` ＋ `git diff --staged` ＋ **未追跡新規ファイル（`git ls-files --others --exclude-standard` の内容）** を組み立てているか、テストレビューは修正差分も含むかを Read で確認 | 各スクリプトの入力組み立てが計画書 §4-2 どおり（untracked 新規ファイルが context に含まれ空振りしない） | Claude | | 静的確認＋untracked 網羅性 |
| 5 | `.claude/skills/fix-loop/SKILL.md` を通読し、手順3.5→4→5→5.5→6→6.5→7 の順次ゲートと NG 差し戻し導線・連続 NG 上限=2・軽微例外・skip 記述が、既存手順と同粒度（具体コマンドまで）で矛盾なく読めるか目視 | 文脈ゼロの担当者が誤読なく運用でき、分岐パリティ（片方だけ散文止まり）がない | Human | | 記述品質の人間目視 |
| 6 | `docs/fixes/` が新設されていないこと、fix-loop アーティファクトが `docs/reviews/` 配下に集約されることを確認 | `docs/fixes/` 不在・出力パスは `docs/reviews/I###_fix_*` | Claude | | `ls` で確認 |

結論: （/test 実施後に記入）
