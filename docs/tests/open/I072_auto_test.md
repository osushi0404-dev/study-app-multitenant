# 自動テスト: I072 否定・回帰系の決定論テストの false-green 検出ゲート追加

- **関連イシュー**: #148
- **計画書**: docs/plans/open/plan_I072.md
- **実行方法**: 各 TC のコマンドを `bash` で実行し、期待結果と一致することを確認する。すべて Claude が決定論的に実行可能。
- **ドッグフーディング（必須）**: TC-05・TC-06 は否定・回帰系アサーションのため、本イシューが導入する規約に従い、**失敗条件を注入して NG を返すことまで確認**する（下部「ドッグフーディング検証」欄に記録）。

| TC | 種別 | 目的 | コマンド | 期待結果 |
|----|------|------|---------|---------|
| TC-01 | 存在 | plan-writing-rules に false-green 原則サブセクション | `grep -q '^### 否定・回帰系の決定論テストの自己検証（false-green 禁止）' docs/runbooks/plan-writing-rules.md && grep -q '失敗条件を注入して実際に不合格' docs/runbooks/plan-writing-rules.md && echo OK \|\| echo NG` | `OK` |
| TC-02 | 存在 | plan-issue/SKILL の L169 が一般形へ更新 | `grep -q 'false-green' .claude/skills/plan-issue/SKILL.md && grep -q '否定・不在・回帰・無改変を検証する決定論テスト' .claude/skills/plan-issue/SKILL.md && echo OK \|\| echo NG` | `OK` |
| TC-03 | 存在 | plan-reviewer P4 に false-green 検出 bullet | `grep -q 'false-green な常時 OK でないか' .claude/review-agents/plan-reviewer.md && echo OK \|\| echo NG` | `OK` |
| TC-04 | 存在 | code-reviewer P4 に false-green 検出 bullet | `grep -q 'false-green な常時 OK でないか' .claude/review-agents/code-reviewer.md && echo OK \|\| echo NG` | `OK` |
| TC-05 | 回帰/無改変 | 既存ゲート項目が残存＋lint 非ゼロ終了要件が一般化後も残存 | `grep -q '計画書の各実装ステップ本文内に検証コマンドが残っていないか' .claude/skills/plan-issue/SKILL.md && grep -q '非ゼロ終了' .claude/skills/plan-issue/SKILL.md && echo OK \|\| echo NG` | `OK` |
| TC-06 | 否定/不在 | 追加した false-green 行に I071 固有トークンが無い（一般形） | `grep -h 'false-green' docs/runbooks/plan-writing-rules.md .claude/skills/plan-issue/SKILL.md .claude/review-agents/plan-reviewer.md .claude/review-agents/code-reviewer.md \| grep -E 'P9\|VERDICT\|HIGHRISK' && echo NG \|\| echo OK` | `OK`（I071 固有トークンを含む false-green 行が 1 つも無ければ OK） |

## 実行結果記録欄

| TC | 結果 | 実行日時 | 備考 |
|----|------|---------|------|
| TC-01 | | | |
| TC-02 | | | |
| TC-03 | | | |
| TC-04 | | | |
| TC-05 | | | |
| TC-06 | | | |

## ドッグフーディング検証（TC-05・TC-06 が失敗条件で NG を返すこと）

否定・回帰系 TC は false-green でないことを失敗注入で確認する（本イシューが導入する規約の自己適用）。

| TC | 失敗注入の方法 | 期待（注入時） | 結果 |
|----|--------------|--------------|------|
| TC-05 | 「非ゼロ終了」を含まないコピーに対して TC-05 を実行（例: 一時ファイルから当該語を除去） | `NG` を返す | |
| TC-06 | false-green 行を含むコピーに `P9` を一時挿入して TC-06 を実行 | `NG` を返す | |

> 注: 失敗注入は一時コピー/`/dev/null` 等の非破壊手段で行い、実ファイルは改変しない。
