# I181 レビュー: レビュー工程の余分・過剰を見直して開発を速くする

## 基本情報
- **関連イシュー**: #304（docs/issues/open/I181.md）
- **計画書**: docs/plans/open/plan_I181.md
- **Draft PR**: #311
- **テスト文書**: docs/tests/open/I181_auto_test.md・docs/tests/open/I181_manual_test.md

## レビュー対象
| 計画 | 対象ファイル | 内容 |
|------|-------------|------|
| 4-1 | `scripts/claude/code-review.sh` | `path_risk_trigger()` を例外の 6 パターンに置き換え・`GIT_FILES` に `--no-renames` |
| 4-2 | `.claude/review-agents/code-reviewer.md` | harness 固有の高リスク条件を同じ集合に・一覧以外は汎用条件で Yes にしない |
| 4-3 | `.claude/review-agents/plan-reviewer.md` | 高リスク判定に同じ集合・P8 に I179 retro P1 |
| 4-4 | `.claude/skills/code-review/SKILL.md` | §3 の上限（1 体 15 分・攻め筋 3・1 周 3 体・イシュー全体 2 周・差分だけ）・タイマー＋`TaskStop`・上限到達時の種類別集計・動的観点の廃止 |
| 4-5 | `.claude/review-agents/adversarial-reviewer.md` | `{REVIEW_BASE}`・時間と攻め筋の上限・資源の上限（I179 retro P2）・守る範囲（ガードは普通の書き方の事故まで・わざと回避は Low で件数外。A10） |
| 4-6・4-9 | `docs/runbooks/review-rules.md` | GitHub が最後の守り・対象・上限・上限到達時・計画レビューのやり直しの条件 |
| 4-7 | `.claude/skills/fix-loop/SKILL.md` | 手順 3 に新しい安全装置を足す前の確認（I179 retro P1） |
| 4-8 | `scripts/claude/tests/test_adversarial_trigger.sh`（更新）・`scripts/claude/tests/test_i181_review_slim.sh`（新規） | P 群・D 群 |

## レビューの重さ（計画書「レビューの重さ」）
本イシューには敵対的レビューを回さない（設計確認メモ）。新しい判定の対象は閉じたパスの一覧で、回帰テスト（TC-P1）と失敗注入（FG-P1）で漏れなく確かめられ、例外に当たるファイル自体は触らないため。新しい判定で本イシューは `ADVERSARIAL_STAGE: NOT_REQUIRED` になる見込み（手動 No.1）。

## 実装（2026-10-24・/implement）
- テストを先に書いて赤を確認（パス判定 fail=26・記述 fail=23）→ 本体を変えて緑（パス判定 pass=60・記述 pass=29・回帰 R2〜R7 すべて fail=0）。内訳は `docs/tests/open/I181_auto_test.md`「結果」
- 計画変更記録 1: `code-review/SKILL.md` の `allowed-tools` に `TaskStop` を追加（手順を成り立たせるための付け足し。計画レビューのやり直しは不要）

## /code-review（2026-10-24）
- 基本レビュー OK・指摘なし（`docs/reviews/I181_code_review_20261024_1136.md`）。決定論ゲート 10 本すべて exit 0・CI 6 件 pass
- 高リスク判定 NO（LLM=NO / path=NO）→ `ADVERSARIAL_STAGE: NOT_REQUIRED`。計画書「レビューの重さ」の見込みどおりで、敵対的レビューは走っていない（手動 No.1 で記録）

## 実装後評価
（/test 以降に記録）
