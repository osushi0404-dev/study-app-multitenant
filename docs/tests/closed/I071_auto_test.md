# 自動テスト: I071 レビュー観点に P9（プライバシー・コンプライアンス）を追加

- **関連イシュー**: #145
- **計画書**: docs/plans/open/plan_I071.md
- **実行方法**: 各 TC のコマンドを `bash` で実行し、期待結果（終了コード・出力）と一致することを確認する。すべて Claude が決定論的に実行可能（ファイル内容の grep / 存在確認）。
- **判定**: 各コマンドは一致時に `OK`、不一致時に `NG` を出力するワンライナーとして記述する。

| TC | 目的 | コマンド | 期待結果 |
|----|------|---------|---------|
| TC-01 | framework §2 表に P9 行 | `grep -qE '^\| P9 \|' docs/proposals/review_perspective_framework.md && echo OK \|\| echo NG` | `OK` |
| TC-02 | framework §3 に P9 詳細＋P2境界 | `grep -q '^### P9\. プライバシー・コンプライアンス' docs/proposals/review_perspective_framework.md && grep -q 'P2 との境界' docs/proposals/review_perspective_framework.md && echo OK \|\| echo NG` | `OK` |
| TC-03 | framework §4 含めないもの表＋§5 両マッピングに P9 | `[ "$(grep -c 'P9' docs/proposals/review_perspective_framework.md)" -ge 6 ] && grep -q 'P9\. プライバシー・コンプライアンス \|' docs/proposals/review_perspective_framework.md && echo OK \|\| echo NG` | `OK`（§2/§3/§4/§5×2/§8 で 6 箇所以上） |
| TC-04 | plan-reviewer に P9 観点＋該当時運用 | `grep -q '^### P9\. プライバシー・コンプライアンス' .claude/review-agents/plan-reviewer.md && grep -q '対象外' .claude/review-agents/plan-reviewer.md && echo OK \|\| echo NG` | `OK` |
| TC-05 | plan-reviewer 高リスク判定に P9 越境条件 | `awk '/## 高リスク判定/{f=1} f&&/越境/{print}' .claude/review-agents/plan-reviewer.md \| grep -q '越境' && echo OK \|\| echo NG` | `OK` |
| TC-06 | code-reviewer に P9 観点 | `grep -q '^### P9\. プライバシー・コンプライアンス' .claude/review-agents/code-reviewer.md && echo OK \|\| echo NG` | `OK` |
| TC-07a | plan-issue に「P9 影響なし」運用 | `grep -q 'P9 影響なし' .claude/skills/plan-issue/SKILL.md && echo OK \|\| echo NG` | `OK` |
| TC-07b | implement 条件付き確認に P9 | `grep -q '条件付き確認（P3・P5・P6・P9）' .claude/skills/implement/SKILL.md && echo OK \|\| echo NG` | `OK` |
| TC-08a | criteria §6 に C2↔P9 ＋ C1 注記 | `grep -q 'C2 .* ↔ P9' docs/proposals/learning_app_quality_criteria.md && grep -q 'C1 .* ↔ .*観点なし（意図的）' docs/proposals/learning_app_quality_criteria.md && echo OK \|\| echo NG` | `OK` |
| TC-08b | review-rules.md L5 が P1〜P9 | `grep -q 'レビュー観点フレームワーク（P1〜P9）' docs/runbooks/review-rules.md && echo OK \|\| echo NG` | `OK` |
| TC-09 | §8 プレースホルダが確定（「対応予定」不在・「追加済み」存在） | `! grep -q 'P9 の実体追加は I071（#145）で対応予定' docs/proposals/review_perspective_framework.md && grep -q 'I071（#145）で追加済み' docs/proposals/review_perspective_framework.md && echo OK \|\| echo NG` | `OK` |
| TC-10 | 回帰: ライブ消費箇所に「P1〜P8 / 8観点」取りこぼしなし | `grep -rn 'P1〜P8\|8観点' docs/proposals/review_perspective_framework.md docs/proposals/learning_app_quality_criteria.md docs/runbooks/review-rules.md \| grep -v 'I046' \| grep -q . && echo NG \|\| echo OK` | `OK`（§6 L228 の I046 歴史記述のみ許容、他に残存なし） |
| TC-11a | 回帰: 両 review-agent の VERDICT テンプレート行が無改変 | `grep -q 'VERDICT: <BLOCKER' .claude/review-agents/plan-reviewer.md && grep -q 'VERDICT: <BLOCKER' .claude/review-agents/code-reviewer.md && echo OK \|\| echo NG` | `OK`（`<BLOCKER` は機械判定契約のテンプレート行にのみ出現＝実出力 `VERDICT: OK` 等とは別。両ファイルに残存すれば契約が無改変） |
| TC-11b | 回帰: 既存 P3/P4/P5/P8 見出しが全て残存（plan-reviewer。P1 も `### P1.`、P2/BP/モダンは別見出し） | `pass=true; for n in P3 P4 P5 P8; do grep -q "^### $n\." .claude/review-agents/plan-reviewer.md \|\| pass=false; done; $pass && echo OK \|\| echo NG` | `OK`（1 つでも見出しが欠ければ `pass=false` で `NG`。break 後の無条件 echo による誤合格を排除） |

## 実行結果記録欄

| TC | 結果 | 実行日時 | 備考 |
|----|------|---------|------|
| TC-01 | ✅ OK | 2026-06-21 | §2 表に P9 行あり |
| TC-02 | ✅ OK | 2026-06-21 | §3 `### P9.` 詳細＋「P2 との境界」あり |
| TC-03 | ✅ OK | 2026-06-21 | P9 出現 12 箇所（≥6）・§4 含めないもの表に P9 行 |
| TC-04 | ✅ OK | 2026-06-21 | plan-reviewer に `### P9.`＋「対象外」運用語 |
| TC-05 | ✅ OK | 2026-06-21 | 高リスク判定ブロックに「越境」条件あり |
| TC-06 | ✅ OK | 2026-06-21 | code-reviewer に `### P9.` |
| TC-07a | ✅ OK | 2026-06-21 | plan-issue に「P9 影響なし」運用 |
| TC-07b | ✅ OK | 2026-06-21 | implement 見出し「（P3・P5・P6・P9）」 |
| TC-08a | ✅ OK | 2026-06-21 | criteria §6 に C2↔P9＋C1「観点なし（意図的）」 |
| TC-08b | ✅ OK | 2026-06-21 | review-rules.md L5 が「P1〜P9」 |
| TC-09 | ✅ OK | 2026-06-21 | 「対応予定」消去・「I071（#145）で追加済み」確定 |
| TC-10 | ✅ OK | 2026-06-21 | ライブ消費箇所に「P1〜P8/8観点」残存なし（I046 歴史記述のみ除外） |
| TC-11a | ✅ OK | 2026-06-21 | 両 agent の VERDICT テンプレート行が無改変 |
| TC-11b | ✅ OK | 2026-06-21 | plan-reviewer の P3/P4/P5/P8 見出し全残存 |

**自動テスト結果サマリー**: 専用 TC 14 件すべて PASS（FAIL 0）。pytest/Jest/E2E は Backend/Frontend 変更なしのため **非該当**（実行せず）。

> 注: TC-03 / TC-11b 等の閾値・見出し名は実装後の実ファイルに合わせて微修正する場合がある（その際は本文書も同時更新する）。
