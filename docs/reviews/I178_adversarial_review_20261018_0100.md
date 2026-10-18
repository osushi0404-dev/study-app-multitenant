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

第 1 周は NEW_HIGH 1 件のため、修正後に第 2 周へ進む（第1周修正コミット 84b1d76）。修正で計画書を変えたため、第 2 周の前に /plan-issue-review を再実行した（20261018_1126・指摘なし）。

---

## 第 2 周（2026-10-18・3 エージェント並列）

| # | 観点 | NEW_CRITICAL | NEW_HIGH |
|---|---|---|---|
| 1 | ロジック回避・実機 repro（固定） | 0 | 0 |
| 2 | テストの false-green・tautology（固定） | 0 | 1 |
| 3 | 要件・脅威モデルの網羅漏れ（固定） | 0 | 0 |
| | **合計** | **0** | **1** |

### findings と対応

| 重大度 | 観点 | 指摘 | 対応 |
|---|---|---|---|
| High | false-green | 第1周で新設した test_i178 のステップ 3 検証は Restrict の 1 か所しか見出し直後を見ず、「Require a pull request before merging」（親スイッチ）・status checks のオフ、force push/削除のオン、bypass 見出しの差し替えが合格する（実測 exit 0） | **修正**。test_i178 を全文比較方式に作り直した。runbook の develop 表・main 表・ステップ 3、close の step 5.5・step 6 の 5 節を見出し行で切り出し、期待値と完全一致で比較。開始・終了見出しが無ければ節が空になり NG。第2周レビューアの改変版 11 件（下の Medium・Low の分を含む）と第1周の 14 通りの計 25 通りすべて exit 1・無改変 exit 0 |
| Medium | false-green | 表の矛盾行の検知が 6 項目だけで、セルの空白の違い・HTML コメントで隠した ON 行・表の外の行でも合格する | **修正**（上と同じ全文比較で解消。改変版 D・E・G・H・J が exit 1） |
| Medium | ロジック回避 | 確認 6・No.6 の `gh pr merge` は API を呼ぶ前に手元で `BLOCKED` を判定し、汎用の文（base branch policy prohibits the merge）で止まるため、push 制限と他の理由を区別できない。前提に CI 結果も無い | **修正**。前提に必須チェック 5 件 SUCCESS を追加し、GitHub のマージ API（`gh api -X PUT .../pulls/<N>/merge -f merge_method=merge`）を直接呼んで応答の `message` で判定する手順に変更（runbook §4 確認 6・手動 No.6・計画 5-2）。`--auto` を付けないことも明記 |
| Medium | 要件網羅 | マージ後の No.7・TC-17 の記録先が無い。承認後に No.4〜6 の結果をコミットすると承認が取り消される流れも書かれていない | **修正**。手動テスト文書に「実施の順番と記録の残し方」を追加（No.1〜3 は /test でコミット、No.4〜6 は /close で記入、その記録コミットで承認取り消しを確かめる No.8 を新設、マージ後の No.7・TC-17 は記録用 PR `docs(I178): マージ後確認の記録` で記入）。計画ステップ 5 にも追記 |
| Medium | 文書整合 | 第1周の「空コミット PR は不可」の修正がイシュー本文（設計確認メモ・AC-4 の確認方法・解決方針の検証）に入っていない | **修正**。設計確認メモの手順 1 に訂正注記（1 行のファイル変更・ブランチ名・後片付け）を追加し、解決方針の検証を 5 点に更新 |
| Low | 文書整合 | イシューの AC-2 の確認方法が No.7 を含まず、#298 マージ前は Code Owners の効き目を区別できない | **修正**。イシュー AC-2 に設定画面確認と No.7 の位置づけを追記 |
| Low | 手順の具体性 | No.6 の後に develop が進んだ場合の再承認の流れ、No.7 のブランチ名の確定・後片付けが無い | **修正**。手動テスト文書の冒頭に BEHIND 時の流れを追加。No.7 のブランチ名を `check/I178-codeowners` に確定し、`gh pr close <N> --delete-branch` を追加 |
| Low | 脅威と検証の対応 | 攻撃シナリオ 3（承認後の追加 push）の確認が「追従時にたまたま観測」で記録先が無い。runbook 確認 4 の「main は確認 6 で確認」に対応する手動テストが無い | **修正**。No.8 で専用に確認。runbook 確認 4 の main の記述を「設定画面で確認し、develop → main の PR を作ったときに確認 6」に変更。計画の攻撃シナリオ 3 を No.8 に更新 |
| Low | 文書整合 | レビュー文書のステータス・対象表が古い。イシュー AC-1 の表現（「`* @oshui0404` のみ」）が計画・実ファイル（コメント行あり）と食い違う | **修正**。レビュー文書のステータスと対象表（test_i178 追加）を更新。イシュー AC-1 を「コメント以外の行が `* @oshui0404` の 1 行のみ」にそろえた |
| Low | 確認手順の誤判定 | runbook 確認 1・2 の期待エラー文が PR 必須の文だけで、Restrict の一覧に無い bot が実行すると push 権限不足の文になり得る | **修正**。期待結果を「push が拒否される」にし、理由の文が実行アカウントで変わることを明記 |
| Low | 第1周修正のリスク | §6 の緊急手順に、bypass 設定を戻した後の確認が無い | **修正**。戻した後に設定画面で §1 の表と突き合わせる一文を追加 |
| Low | tautology | 旧手順の否定判定の語順固定・close step 5.5 への矛盾文の追加を検知しない | **修正**（全文比較で解消。改変版 F・K が exit 1） |

### 修正内容（コミット）

- `scripts/claude/tests/test_i178_branch_protection_doc.sh`（全文比較方式に作り直し）
- `docs/runbooks/branch-protection-setup.md`（§4 確認 1・2・4・6、§6）
- `docs/tests/open/I178_manual_test.md`（記録の流れ・No.6・No.7・No.8 新設）・`docs/tests/open/I178_auto_test.md`（TC-19 の説明・結果）
- `docs/plans/open/plan_I178.md`（AC-5・5-2・5-3b・ステップ 5・7・承認ポイント・攻撃シナリオ 3）・`docs/issues/open/I178.md`（設計確認メモの訂正・解決方針の検証・AC-1・AC-2・AC-5）・`docs/reviews/open/I178_review.md`

第 2 周は NEW_HIGH 1 件のため、修正後に第 3 周（上限）へ進む（第2周修正コミット 5572158）。修正で計画書を変えたため、第 3 周の前に /plan-issue-review を再実行した（20261018_1145・Warning 2 件。1 件はスクリプト冒頭の注記で対応済み、もう 1 件は確認 6・No.6 の合否基準を明文化して 4753390 で対応）。

---

## 第 3 周（2026-10-18・3 エージェント並列・上限）

| # | 観点 | NEW_CRITICAL | NEW_HIGH |
|---|---|---|---|
| 1 | ロジック回避・実機 repro（固定） | 0 | 0 |
| 2 | テストの false-green・tautology（固定） | 0 | 1 |
| 3 | 要件・脅威モデルの網羅漏れ（固定） | 0 | 1 |
| | **合計** | **0** | **2** |

サブエージェント総数: 第1周 4 + 第2周 3 + 第3周 3 = 10（上限 15）。

### findings（未対応・/fix-loop へ引き継ぐ）

| 重大度 | 観点 | 指摘 | 対応案 |
|---|---|---|---|
| High | false-green | test_i178 が全文比較するのは 5 節だけ。§3 ステップ 2（ブランチ名パターン）・ステップ 5（main の設定）は対象外。`section()` は最初の見出しだけを切り出すため、同じ見出しの古い表を後ろに足しても見逃す（改変 F・G・A で test_i178 exit 0・ゲート 18 行全合格を実測） | runbook 全体を期待値と全文比較する（または節の見出しが 1 回だけであることの確認＋ステップ 1〜5 と概要・§1.5 の比較対象への追加） |
| High | 要件網羅 | /close step 6 の文言は「Approve & Merge を依頼」で、test_i178 がそれを固定している。手動テストには「No.5 では承認だけでマージしない」指示が無い。文書どおりに承認と同時にマージすると、No.6（bot のマージ拒否）と No.8（承認取り消し）が実行できなくなる | 手動テスト No.5・runbook 確認 6 に「承認のみ・マージは No.8 の後」を明記し、/close step 6 で Claude がユーザーへ出す依頼を手動テスト文書に従わせる記述を追加 |
| Medium | 要件網羅 | No.6 で万一マージが成功した場合の分岐（No.8 の代わり・No.4〜6 の記録先）が無い | No.6 成功時は No.4〜6・No.8 の記録とやり直しを記録用 PR／別の確認用 PR で行う分岐を追加 |
| Medium | 要件網羅 | マージ後の No.7・TC-17 が NG の場合の扱い（イシューの再オープン・fix-loop・設定の戻し）と、レビュー文書の AC 判定表を埋める工程が無い | 記録用 PR の対象にレビュー文書を加え、NG 時の手順を定める |
| Medium | ロジック回避 | No.6 の備考「成功したら No.2 を見直す」は誤り（#298 の宛先は develop なので No.1） | No.1 に修正 |
| Medium | ロジック回避 | No.8 の結果の記入先が無い（#298 にコミットすると承認が再び取り消される） | 記録用 PR の対象に No.8 を加える |
| Low | 文書整合 | 手動テストの前提「TC-01〜TC-19 合格」に、マージ後にしか実行できない TC-17 が含まれる。runbook 確認 5 の close に `--delete-branch` が無い | 前提を「TC-17 を除く」に修正、確認 5 をそろえる |
| Low | 手順 | No.8 の push 後、CI 完了を待ってから再承認を依頼する手順が無い。/test・/close で後に回す項目の扱いが手動テスト側にしか無い | No.8 に CI 待ちを追記 |
| Low | 手順のリスク | runbook 確認 6 にユーザー了承の手順が無い。`gh api -X PUT .../merge` は I146 のガードを素通しする（実測） | 確認 6 に「実行前に oshui0404 の了承を得る」を追加 |
| Low | 誤判定（未実測） | 合否判定が message 全体の語で行われ、URL に `review` が含まれると誤判定し得る。bot トークンの権限不足と区別できない | URL を除いて判定し、HTTP ステータスも記録する |
| Low | 設計の抜け道（未実測） | PR の宛先ブランチ変更（`gh pr edit --base`）では Dismiss stale が働かない可能性 | /retro へ（実機確認が必要・既知 (4) に近い） |

### 判定

上限（3 周）到達時点で新規 High 2 件が残るため、**上限到達・未収束**として打ち切り、最終判定を HIGH に固定してユーザーへエスカレーションする。

VERDICT: HIGH
