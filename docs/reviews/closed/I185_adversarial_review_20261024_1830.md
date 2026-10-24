# 敵対的レビュー [I185] ── 1 周目

- **実施日**: 2026-10-24
- **見直した範囲**: `git diff origin/develop...93d5199`
- **体制**: 固定 3 観点 × 1 体（各 15 分上限・攻め筋 3 本まで）。3 体とも時間内に報告（時間切れなし）。タイマーは 3 体の完了後に止めた
- **基本レビュー**: `docs/reviews/closed/I185_code_review_20261024_1805.md`（FINAL_VERDICT: OK・RISK: YES）

## 観点 1: ロジック回避・実機 repro

| 重大度 | 指摘内容 | 該当箇所 | 対応 |
|---|---|---|---|
| Medium | P4 で `allowed-tools` を外したのに、それを必須として扱う箇所が 3 つ残っている（`lint_skills.py` の必須項目・`review-rules.md` のチェックリスト 1・`plan-reviewer.md` の観点）。今後のレビューで P4 を戻させる方向に働く | `scripts/migration_verify/lint_skills.py:16`・`docs/runbooks/review-rules.md:148`・`.claude/review-agents/plan-reviewer.md:102` | 修正（3 か所とも書き換え・TC-14⑧ を追加） |
| Medium | security-review で Bash を禁止すると、検索専用ツールがないこの環境ではファイルを探せず、コードを読まずに「変更なし」へ流れやすい | `.claude/skills/security-review/SKILL.md:6` | 修正（`disallowed-tools: Write, NotebookEdit` に変更） |
| Low | 取り出す「最初の I###」自体は第三者が選べる（なりすましの番号）。`\d` が ASCII 以外の数字に一致し、bool の番号が「#True」と出る | `scripts/claude/hooks/sessionstart_context.py` | 修正（ASCII の数字だけ・bool を除外。番号のなりすましは命令文が入らないので受け入れ） |

問題なしと確かめたもの: タイトル・日付に改行や命令文を入れても出力に漏れない／gh が固まっても 5 秒で打ち切り exit 0（最悪 20 秒でフックの上限 30 秒に収まる）／exit 2 化で正しい tsconfig.json・ci.yml を誤って止めない。

## 観点 2: テストの false-green・tautology

| 重大度 | 指摘内容 | 該当箇所 | 対応 |
|---|---|---|---|
| High | TC-14⑤ は推奨案で進む文と条件 ⑥ の文字列しか見ておらず、「満たさないときは停止する」の行と条件 ①〜⑤ を消しても合格する | `scripts/claude/tests/test_i185_harness_docs.sh`（TC-14⑤a・⑤b） | 修正（停止の行と条件 ①〜⑤ を個別に確認。停止の行を壊した版で不合格になることを確認） |
| Medium | TC-11 は GitHub を一切呼ばない版でも全件合格する（見出しは gh 失敗時にも出る） | `scripts/claude/tests/test_sessionstart_context.sh`（TC-11a） | 修正（偽の gh を PATH の先頭に置いて値が出ることを確認する TC-11f。gh を呼ばない版で不合格になることを確認） |
| Medium | TC-13 は settings.json のどこかに名前があれば合格し、登録先のイベント名を打ち間違えても気づけない | `docs/tests/open/I185_auto_test.md`（TC-13） | 修正（`hooks.SessionStart[*].hooks[*].command` を JSON で確かめる TC-11g。名前を打ち間違えた設定で不合格になることを確認） |
| Medium | TC-14② は frontmatter の外の行でも合格する | `test_i185_harness_docs.sh`（TC-14②） | 修正（frontmatter の中だけを見る。本文へ移した版で不合格になることを確認） |
| Medium | TC-14③ は順番を見ておらず、レビューを承認の後に戻しても合格する | `test_i185_harness_docs.sh`（TC-14③） | 修正（順番の確認 ③c と、古い「完了したら承認ポイントを提示して停止」がないことの確認 ③d。挿入した版で不合格になることを確認） |

## 観点 3: 要件・脅威モデルの網羅漏れ

| 重大度 | 指摘内容 | 該当箇所 | 対応 |
|---|---|---|---|
| Medium | P3（条件を満たせば承認なしで修正へ進む）が、CLAUDE.md の絶対ルール 2「ユーザー承認なしにコード変更を開始しない」・workflow.md の承認の記述・fix-loop の description と食い違う | `CLAUDE.md` §1-2・`docs/runbooks/workflow.md`・`.claude/skills/fix-loop/SKILL.md:3` | 修正（ユーザーの一任を受け、「`/fix-loop` の入力＋承認済みの計画の範囲内の修正は絶対ルール 2 の承認を満たす」と fix-loop と workflow.md に明記。CLAUDE.md は変えない。TC-14⑤l〜⑤n） |
| Medium | `/plan-issue` の中で呼ぶ `plan-issue-review.sh` が、承認前に「`/implement` を実行」と案内する。Blocker 時の案内も新手順と食い違う | `scripts/claude/plan-issue-review.sh:157-167`・`.claude/skills/plan-issue/SKILL.md` | 修正（スクリプトの案内を承認前に伝えないと SKILL に明記。スクリプトは `/plan-issue-review` でも使うので変えない・TC-14③e） |
| Medium | 観点 1 の 1 件目と同じ（P4 の消費箇所） | 同上 | 同上 |
| Medium | P3 の条件 ⑥ が、レビュー用スクリプト・レビュー役の指示・テスト・pre-commit 設定を除外していない（「判定を緩めれば通る」修正が自動で通りうる） | `.claude/skills/fix-loop/SKILL.md` | 修正（条件 ⑥ に追加・TC-14⑤b2） |
| Low | security-review・retro に古い順番の書き方が残っている | `.claude/skills/security-review/SKILL.md:3,11`・`.claude/skills/retro/SKILL.md:166` | 修正 |
| Low | スクリプトが判定前に失敗したときの扱いがない | `.claude/skills/plan-issue/SKILL.md` | 修正（承認ポイントを出さずに停止・TC-14③f） |
| Low | レビューへのリンク追記で計画書が未コミットのまま残る | `scripts/claude/plan-issue-review.sh:146-150` | 修正（リンクを commit/push してから提示すると SKILL に明記） |

SessionStart がレビュー用スクリプトの判定（stdout の VERDICT・FIX_GATE）を壊す経路はない、と確認された。

## 集計と判定

- 新規: Critical 0・High 1・Medium 10（重複 1 を含む）・Low 4
- High 1 件を直したので、直した差分（`93d5199` 以降）を 2 周目で見直す
- 修正のコミット: d5b7482（テスト・P2・P3・P4・P5 の修正）と、P3 の承認の扱いの明記（このコミット）

REVIEWED_COMMIT: 93d5199d87067d81f5f145d0e0ab25452a470e9b
ROUNDS: 1
VERDICT: HIGH
