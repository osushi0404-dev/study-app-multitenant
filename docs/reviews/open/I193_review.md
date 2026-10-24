# I193 レビュー: 開発の流れを公式の道具を土台に組み直す

## 変更概要
- 公式の道具を土台にした流れの設計書 `docs/proposals/I193_official_base_flow.md`
- 同名スキルの改名（`code-review`→`review-gate`・`security-review`→`design-security-review`・`test`→`test-gate`・`plan-issue-review`→`plan-review`）と、段階のスキル化（`user-invocable: false`）
- レビュー役 7 本を `.claude/agents/` へ移し、`tools: Read, Grep, Glob`・`claude -p --agent`・`timeout` で呼ぶ
- レビュー段階で組み込み `/code-review`（高リスク時は `/security-review`）を実行し、自作レビュー役が判定に取り込む
- 段階のつなぎ（`STAGE_DONE:`・`flow-stage.sh`・`gate-check.sh`）と `/proceed`
- 承認待ちをなくし、止めて聞く 3 条件にそろえる（CLAUDE.md・runbook・スキル）
- ハーネスのテストを CI で動かす（`run-all.sh`・`Harness Tests` ジョブ）と、落ちていた 2 本の修正

## 変更点
- レビュー役 7 本を `.claude/agents/` へ移動（frontmatter: name・description・tools・model）。スクリプトは `claude -p --agent <name> --tools "Read,Grep,Glob"`・`timeout` で呼ぶ
- スキル: 改名 4（review-gate・design-security-review・test-gate・plan-review）・新設 1（proceed）・段階のスキル 8 本を `user-invocable: false` に・承認待ちをなくす書き直し（plan-issue・implement・fix-loop・retro・close・issue-bootstrap・grill-me）
- `scripts/claude/code-review.sh`: fetch・CI 待ちの fail-closed（exit 3/1）・組み込み `/code-review`・`/security-review` を plan モードで背景実行・VERDICT 無しは BLOCKER・`REVIEWED_COMMIT`・機械判定行の無害化
- 新設: `scripts/claude/flow-stage.sh`・`scripts/claude/gate-check.sh`・`scripts/claude/tests/run-all.sh`・`scripts/claude/tests/test_i193_official_flow.sh`
- `.github/workflows/ci.yml` に `Harness Tests` ジョブ
- CLAUDE.md 絶対ルール 1・2、workflow.md（止めて聞く条件・つなぎ・移行）、issue-flow・onboarding・review-rules・plan-writing-rules・mcp-usage・danger-ops（DOC6）・branch-protection-setup・テンプレート・claude-code-structure
- 既存テストの更新（新しい置き場所・新しい流れの守りの文に付け替え）と、落ちていた D8・DOC6 の修正

## 自律判断の記録
- [implement] I193 自身の残りの段階は新しい流れ（`/proceed I193`）で進める — このワークツリーでは本変更で古い `/code-review`・`/test` が無くなったため。新しい流れの初めての実地の通しにもなる
- [implement] 敵対的レビュー役だけ `tools` に Bash を残した — temp repo での再現実行に要る（計画変更記録 4）
- [implement] retro がその場で直すのは記録の場所だけにした — それ以外を直すとレビューと人の手動テストをやり直すことになるため（計画変更記録 4）
- [review-gate] 基本レビュー（`I193_code_review_20261025_0030.md`）が FINAL_VERDICT HIGH（High 1・Medium 5・Low 3）なので、敵対的レビューの前に fix-loop へ回した — review-gate の手順どおり（敵対的レビューは基本レビュー OK の後）。指摘の多くは組み込み `/code-review` が出し、自作レビュー役が採用した
- [fix-loop] High 1・Medium 5 は全部、Low 3 は 1 行で直せるので一緒に直した（診断メモ `I193_fix_diagnosis_20261025_0045.md`・診断・実装・テストのレビューはすべて PASS）— どれも流れが止まる・確認をすり抜ける実害がある。各指摘は診断で推奨した案 A で直した（例: gate-check はパス判定を記録の文字に頼らず自分で再評価する。注入に強いため）
- [review-gate] 2 回目の基本レビュー（`I193_code_review_20261025_0050.md`）も HIGH（High 2・Medium 5・Low 3。1 回目の修正で足した仕組みの細部の穴）なので fix-loop へ回した
- [fix-loop] 2 回目は H1・H2・M1〜M3・M5・L1・L2 を直した（診断メモ `I193_fix_diagnosis_20261025_0130.md`・3 つのレビューはすべて PASS）。M4（背景の実行が 10 分で止まる）は採らなかった — 1 回目の review-gate で 10 分を超える背景の実行が正常に終わったことを実測したため
- [fix-loop] 2 回目は、修正を先に書いてから診断メモを書いた（手順の順序の誤り）— 診断レビューは修正の後になったが、案の妥当性は診断・実装・テストのレビューと次の review-gate で確かめる。次の回からは手順どおり診断メモを先に書く

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/skills/`・`.claude/agents/`（`.claude/review-agents/` から移動）・`scripts/claude/`・`scripts/claude/tests/`・`.github/workflows/ci.yml`・`CLAUDE.md`・`docs/runbooks/`・`docs/*/templates/`・`docs/claude-code-structure.md`・`docs/proposals/I193_official_base_flow.md`

## テスト結果
- （/test 時に記入）

## 計画との差分
- （実装後に記入）

## ロールバック
- ステップごとのコミットを `git revert`（改名は `git mv` なので元に戻る）。必須チェックに登録した `Harness Tests` は、ユーザーがブランチ保護の設定から外す

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: fix-loop

STAGE_DONE: fix-loop NEXT: review-gate

STAGE_DONE: fix-loop NEXT: review-gate
