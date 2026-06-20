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
| TC-11a | 回帰: 両 review-agent の VERDICT 行が無改変 | `grep -q 'VERDICT: <BLOCKER\|HIGHRISK\|OK>' .claude/review-agents/plan-reviewer.md && grep -q 'VERDICT: <BLOCKER\|HIGH\|OK>' .claude/review-agents/code-reviewer.md && echo OK \|\| echo NG` | `OK` |
| TC-11b | 回帰: 既存 P1〜P8 見出しが全て残存（plan-reviewer は P1/P3/P4/P5/P8 が `### `、P2/BP/モダンは別見出し） | `for n in P3 P4 P5 P8; do grep -q "^### $n\." .claude/review-agents/plan-reviewer.md \|\| { echo NG; break; }; done; echo OK` | `OK`（最終行 `OK`） |

## 実行結果記録欄

| TC | 結果 | 実行日時 | 備考 |
|----|------|---------|------|
| TC-01 | | | |
| TC-02 | | | |
| TC-03 | | | |
| TC-04 | | | |
| TC-05 | | | |
| TC-06 | | | |
| TC-07a | | | |
| TC-07b | | | |
| TC-08a | | | |
| TC-08b | | | |
| TC-09 | | | |
| TC-10 | | | |
| TC-11a | | | |
| TC-11b | | | |

> 注: TC-03 / TC-11b 等の閾値・見出し名は実装後の実ファイルに合わせて微修正する場合がある（その際は本文書も同時更新する）。
