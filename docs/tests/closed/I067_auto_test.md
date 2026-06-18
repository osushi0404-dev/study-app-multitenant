# I067 自動テスト（計画駆動）

- **関連計画書**: docs/plans/open/plan_I067.md
- **正とする自動テスト**: 下記 TC-01〜TC-08（追記文言の存在を `grep -F` で機械検証＋frontmatter 妥当性）
- **既定テスト**: pytest / Jest / Playwright E2E は **非該当**（Backend/Frontend/DB のコード変更なし）。`/test` 実行時に「非該当」と明示記録する。
- 実行者: すべて Claude（Bash `grep`／`head` で機械実行・記録）

> 本イシューは新 `test/SKILL.md`（計画駆動）設計のドッグフーディング。app/非app の分岐ではなく、計画書が指定する本 TC を正として実行する。

| TC | 対象 | コマンド | 期待結果 |
|----|------|---------|---------|
| TC-01 | plan-issue invariant＋既コミット自動判定分岐 | `grep -F "feature ブランチで初コミット" .claude/skills/plan-issue/SKILL.md && grep -F "ISSUE_ALREADY_ON_BASE" .claude/skills/plan-issue/SKILL.md` | 両 grep がヒット（exit 0）。invariant と `git log` 自動判定（既コミット経路マーカー）が存在する |
| TC-02 | test 計画駆動節＋description | `grep -F "自動テストの選択（計画駆動）" .claude/skills/test/SKILL.md && grep -F "plan-specified" .claude/skills/test/SKILL.md` | 両 grep がヒット（exit 0）。計画駆動節と更新後 description が存在する |
| TC-03 | test フォールバック文言 | `grep -F "指定していない場合のみ" .claude/skills/test/SKILL.md && grep -F "フォールバック" .claude/skills/test/SKILL.md` | 両 grep がヒット（exit 0）。指定なし時のみ既定にフォールバックする旨が存在する |
| TC-04 | test 非該当記録＋分岐なし宣言 | `grep -F "非該当" .claude/skills/test/SKILL.md && grep -F "app/非app の区別では分岐しない" .claude/skills/test/SKILL.md` | 両 grep がヒット（exit 0）。既定テストの非該当記録指示と app/非app 非分岐の宣言が存在する |
| TC-05 | retro ハンドオフ invariant | `grep -F "ローカル作成（未コミット）のまま" .claude/skills/retro/SKILL.md` | grep がヒット（exit 0）。バックログ issue を未コミットのまま残す invariant が存在する |
| TC-06 | close scoped staging＋決定論ゲート | `grep -F "git add -u" .claude/skills/close/SKILL.md && grep -F "git add -A" .claude/skills/close/SKILL.md && grep -F "決定論ゲート" .claude/skills/close/SKILL.md` | 3 grep すべてヒット（exit 0）。`git add -u` 採用・`git add -A` 等の禁止注記・スコープ外検出の決定論ゲートが存在する |
| TC-07 | 4 スキルの frontmatter 妥当性 | `for f in plan-issue test retro close; do head -7 .claude/skills/$f/SKILL.md \| grep -q "disable-model-invocation: true" && echo "$f OK" \|\| echo "$f NG"; done` | 4 ファイルすべて `OK`（frontmatter が破壊されていない） |
| TC-08 | test 停止条件＋欠損フォールバック | `grep -F "指定する専用自動テストが1件でも失敗" .claude/skills/test/SKILL.md && grep -F "auto_test.md が存在しない場合" .claude/skills/test/SKILL.md` | 両 grep がヒット（exit 0）。計画書指定テストの失敗が STOP トリガーに含まれ、auto_test.md 欠損時の既定フォールバックが明記されている |

## 既定テスト（フォールバック）— 本イシューでは非該当
| 種別 | 判定 | 理由 |
|------|------|------|
| pytest（Backend） | 非該当 | Backend コード変更なし |
| Jest（Frontend） | 非該当 | Frontend コード変更なし |
| Playwright E2E | 非該当 | UI/フロー変更なし |

## 実行記録（/implement 時の実装後検証）
2026-06-18 実装直後に全 TC を実行（PASS=8 FAIL=0）。決定論ゲート・自動判定ロジックは機能検証も実施済み。

| TC | 結果(PASS/FAIL) | 備考 |
|----|------|------|
| TC-01 | PASS | invariant＋`ISSUE_ALREADY_ON_BASE` 自動判定を確認 |
| TC-02 | PASS | 計画駆動節＋description（plan-specified）を確認 |
| TC-03 | PASS | 指定なし時のフォールバック文言を確認 |
| TC-04 | PASS | 非該当記録＋「app/非app の区別では分岐しない」を確認 |
| TC-05 | PASS | retro バックログ未コミット invariant を確認 |
| TC-06 | PASS | `git add -u`＋`git add -A` 禁止＋決定論ゲートを確認 |
| TC-07 | PASS | 4 スキルの frontmatter（disable-model-invocation）健全 |
| TC-08 | PASS | 停止条件に計画書指定テスト失敗＋auto_test.md 欠損フォールバックを確認 |

### 機能検証（決定論ロジックの敵対的確認）
| 検証 | ケース | 結果 |
|------|--------|------|
| close ゲート | I067 のみ staged | PASS（通過・正当 close を妨げない） |
| close ゲート | I068 混入 | TRIPPED（スコープ外検出・中断） |
| close ゲート | I0670（別 issue・アンカー検証） | TRIPPED（`I067` と `I0670` を正しく区別） |
| plan-issue 判定 | I067（develop に既コミット） | `ISSUE_ALREADY_ON_BASE`（既コミット経路） |
| plan-issue 判定 | I999（未存在） | 未コミット経路（通常フロー） |

### 既定テスト（フォールバック）
| 種別 | 判定 | 理由 |
|------|------|------|
| pytest / Jest / Playwright E2E | 非該当 | Backend/Frontend/DB/UI のコード変更なし |
