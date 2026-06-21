# 自動テスト: I072 否定・回帰系の決定論テストの false-green 検出ゲート追加

- **関連イシュー**: #148
- **計画書**: docs/plans/open/plan_I072.md
- **実行方法**: 各 TC のコマンドを `bash` で実行し、期待結果と一致することを確認する。すべて Claude が決定論的に実行可能。
- **ドッグフーディング（必須）**: TC-05・TC-06 は否定・回帰系アサーションのため、本イシューが導入する規約に従い、**失敗条件を注入して NG を返すことまで確認**する（下部「ドッグフーディング検証」欄に記録）。
- **TC-06 の実行順序依存**: TC-06 は「false-green 行に I071 固有トークンが無いこと」を検証する不在アサーションで、false-green 行が未実装（0 行）の段階でも OK を返す。よって TC-06 は **TC-01〜04（false-green 行の存在を先行確認）が OK であること**を前提に評価し、単体の false-green でないことは下部ドッグフーディング（トークン注入で NG）で担保する。

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
| TC-01 | ✅ OK | 2026-06-22 | plan-writing-rules に false-green 原則サブセクション＋「失敗条件を注入」原則あり |
| TC-02 | ✅ OK | 2026-06-22 | plan-issue/SKILL L169 が一般形（false-green・否定/不在/回帰/無改変）へ更新済み |
| TC-03 | ✅ OK | 2026-06-22 | plan-reviewer P4 に false-green 検出 bullet あり |
| TC-04 | ✅ OK | 2026-06-22 | code-reviewer P4 に false-green 検出 bullet あり（plan-reviewer と同一文言） |
| TC-05 | ✅ OK | 2026-06-22 | 既存ゲート項目残存＋lint「非ゼロ終了」要件が一般化後も残存 |
| TC-06 | ✅ OK | 2026-06-22 | 追加 false-green 行に I071 固有トークン（P9/VERDICT/HIGHRISK）なし |

**自動テスト結果サマリー**: 専用 TC 6 件すべて PASS（FAIL 0）。pytest/Jest/E2E は Backend/Frontend 変更なしのため **非該当**（実行せず）。

## ドッグフーディング検証（TC-05・TC-06 が失敗条件で NG を返すこと）

否定・回帰系 TC は false-green でないことを失敗注入で確認する（本イシューが導入する規約の自己適用）。失敗注入は一時コピーに対して行い、**実ファイルは改変しない**。各コマンドは注入時に `NG` を出力すれば合格。

**TC-05 ドッグフーディング**（「非ゼロ終了」要件を除去したコピーに対して NG を返すこと）:
```bash
SKILL=.claude/skills/plan-issue/SKILL.md; TMP=$(mktemp)
grep -v '非ゼロ終了' "$SKILL" > "$TMP"   # 失敗注入: 非ゼロ終了 要件を除去
grep -q '計画書の各実装ステップ本文内に検証コマンドが残っていないか' "$TMP" && grep -q '非ゼロ終了' "$TMP" && echo OK || echo NG  # 期待: NG
rm -f "$TMP"
```

**TC-06 ドッグフーディング**（false-green 行に I071 固有トークンを挿入したコピーに対して NG を返すこと）:
```bash
TMP=$(mktemp)
printf 'false-green な常時 OK でないか P9\n' > "$TMP"   # 失敗注入: false-green 行に P9 を混入
grep -h 'false-green' "$TMP" | grep -E 'P9|VERDICT|HIGHRISK' >/dev/null && echo NG || echo OK  # 期待: NG
rm -f "$TMP"
```

| 検証 | 期待（注入時） | 結果 |
|------|--------------|------|
| TC-05 失敗注入 | `NG` | ✅ NG（2026-06-22・非ゼロ終了 除去コピーで NG を確認＝false-green でない） |
| TC-06 失敗注入 | `NG` | ✅ NG（2026-06-22・false-green 行に P9 混入で NG を確認＝false-green でない） |
