# I178 敵対的レビュー記録

- **対象**: PR #298（feature/I178-codeowners-approval-gate）
- **起動条件**: code-review 20261017_1945 で RISK=YES・FINAL_VERDICT=OK
- **上限**: 最大 3 周・サブエージェント総数 15

---

## 第 1 周（2026-10-17〜18・4 エージェント並列）

| # | 観点 | NEW_CRITICAL | NEW_HIGH |
|---|---|---|---|
| 1 | ロジック回避・実機 repro（固定） | 0 | 0 |
| 2 | テストの false-green・tautology（固定） | 0 | 1 |
| 3 | 要件・脅威モデルの網羅漏れ（固定） | 0 | 0 |
| 4 | 文書整合・計画との一致（動的） | 0 | 0 |
| | **合計** | **0** | **1** |

### findings と対応

| 重大度 | 観点 | 指摘 | 対応 |
|---|---|---|---|
| High | false-green | runbook 用ゲート（TC-05/06/09〜12/18）は文言がファイルのどこかにあるかしか見ず、develop・main の表の行や §3 の手順を消す・旧設定に戻しても全ゲート合格（8 通りの改変で実測） | **修正**。`scripts/claude/tests/test_i178_branch_protection_doc.sh` を新設（TC-19・決定論ゲート 18 行目）。節ごとに切り出し、各設定行の完全一致 1 回・項目行の重複なし・ステップ 3 の指示行・Restrict 見出し直後のオン指示・close step 5.5 の develop/main の順序を検証。失敗注入 14 通りすべて exit 1・無改変 exit 0 |
| Medium | ロジック回避 | AC-4 確認の「空コミットの確認用 PR」では、Code Owners 要件がファイル変更を含む PR にしか働かないため、正しく設定しても bot の承認で APPROVED になり誤判定する | **修正**。手動 No.7・runbook §4 確認 5・計画 5-2 を「1 行のファイル変更を含む PR」に変更。No.7 で `files` が 1 件以上であることも確認 |
| Medium | false-green | 手動 No.6 は失敗さえすれば合格で、BEHIND・承認取り消し等の別理由の失敗でも通る | **修正**。No.6 に実行前の前提確認（APPROVED・BEHIND/DIRTY でない・承認が head と同じ）と、期待エラー文（push 権限の不足）を追加。runbook に確認 6 として同じ手順を追加 |
| Medium | 文書整合 | 計画 R7・§7 の「close で CLEAN になれば兆候として気づける」は、pr-base-sync が CLEAN も合格扱いのため成り立たない | **修正**。計画 R7・§7 から当該主張を取り消し、「検知の仕組みは無い・/retro で別イシュー化を判断」に変更 |
| Medium | 文書整合 | runbook §4 確認 4 の見出しは develop・main だが手順は develop のみで、main は bot の承認で APPROVED になり得る | **修正**。確認 4 を develop に限定し、main は確認 6（push 制限）と設定画面で確認する旨を追記 |
| Medium | 要件網羅 | issue-flow.md ステップ 25（Claude が develop にローカルマージして push）が設定と矛盾 | **対応見送り（/retro へ）**。develop への直 push は I178 以前から「Require a pull request」と CLAUDE.md で禁止済みの既存の食い違いで、I178 が持ち込んだものではない。GitHub とガードが拒否するため抜け道でもない |
| Medium | 要件網羅 | workflow.md のリリース・hotfix 手順が main/develop への直 push のまま。main への反映経路が未定義 | **一部修正**。runbook §1.5 に「main への反映は develop → main の PR（bot 作成・oshui0404 承認・マージ）」を追記。workflow.md・onboarding.md の旧手順の書き換えは既存の食い違いのため /retro へ |
| Low | 要件網羅 | 設定変更から #298 マージまで develop でも Code Owners が効かない移行期間の説明が無く、AC-2 の検証対応（No.3〜4）が区別力を持たない | **修正**。runbook §1.5「設定変更直後の develop」を追記。計画 AC-2 の検証に No.7 を追加し、No.3 の備考に区別を明記 |
| Low | 要件網羅 | runbook §6 の緊急手順（§5 で緩める）では自作 PR をマージできない | **修正**。§6 を「Do not allow bypassing を一時的にオフ → 管理者として迂回マージ → すぐオンに戻す」に変更 |
| Low | 文書整合 | ロールバック手順が計画 5-2・イシューと §8・runbook で食い違い（main の承認まで外れる書き方） | **修正**。計画 5-2 とイシューを §8・runbook と同じ書き方にそろえた |
| Low | 文書整合 | §3 ステップ 1 が新規作成手順のままで、既存ルールの Edit が書かれていない | **修正**。ステップ 1 に Edit の分岐、ステップ 4 に Save changes の書き分けを追記 |
| Low | 文書整合 | 表と手順の並びが画面と逆（bypass と Restrict）。下位項目 Restrict pushes that create matching branches の扱いが無い | **修正**。表・手順・計画 5-5 を画面の並びに合わせ、下位項目を ON（既定のまま）と明記 |
| Low | ロジック回避 | 必須チェックの送信元が固定されておらず、write 権限の bot が statuses API で同名チェックを success にできる（承認判断の材料を偽装できる） | **対応見送り（/retro へ）**。I178 以前からの既存リスクで、マージには oshui0404 の承認と操作が要る。送信元を GitHub Actions に固定する手順の追加は別イシュー候補 |
| Low | tautology | TC-07 は誤記の完全一致のみ、TC-13 は step 5.5 の書き分けの入れ替えを検知しない | **一部修正**。TC-13 の入れ替えは TC-19 で検知。TC-07 の言い回し揺れは残余 |

### 修正内容（コミット）

- `scripts/claude/tests/test_i178_branch_protection_doc.sh`（新規）
- `docs/runbooks/branch-protection-setup.md`（表の並び・下位項目・§1.5 追記・§3 Edit・§4 確認 4〜6・§6）
- `docs/tests/open/I178_auto_test.md`（TC-19 追加）・`docs/tests/open/I178_manual_test.md`（No.1〜3・6・7）
- `docs/plans/open/plan_I178.md`（AC 表・影響範囲・5-2・5-3b・5-5・7・R7）・`docs/issues/open/I178.md`（実装対象・ロールバック）

第 1 周は NEW_HIGH 1 件のため、修正後に第 2 周へ進む。

VERDICT: HIGH
