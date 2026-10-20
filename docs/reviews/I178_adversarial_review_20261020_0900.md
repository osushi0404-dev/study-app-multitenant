# I178 敵対的レビュー記録（fix-loop 後の再ステージ）

- **対象**: PR #298（feature/I178-codeowners-approval-gate）
- **起動条件**: code-review 20261019_0005 で RISK=YES・FINAL_VERDICT=OK
- **既知 findings**: 前回ステージ `docs/reviews/I178_adversarial_review_20261018_0100.md` の第1〜3周の全件、fix-loop 診断メモ `docs/reviews/I178_fix_diagnosis_20261018_1300.md` で残余・/retro 送りとしたもの
- **上限**: 最大 3 周・サブエージェント総数 15

---

## 第 1 周（2026-10-19・3 エージェント並列）

| # | 観点 | NEW_CRITICAL | NEW_HIGH |
|---|---|---|---|
| 1 | ロジック回避・実機 repro（固定） | 0 | 0 |
| 2 | テストの false-green・tautology（固定） | 0 | 0 |
| 3 | 要件・脅威モデルの網羅漏れ（固定） | 0 | 1 |
| | **合計** | **0** | **1** |

途中経過: 第 1 周の実行中に、作業ツリー `/mnt/c/app/wt-harness` が別セッション（I179）によって `feature/I179-worktree-operation-review` に切り替えられた。I179 側は計画レビューまで完了・push 済みで、I178 が終わるまで wt-harness に触らないことをユーザー経由で確認し、2026-10-20 に I178 のブランチへ戻して再開した（stash は使わず、作業ツリーに未コミットの変更は無かった）。

### findings と対応

| 重大度 | 観点 | 指摘 | 対応 |
|---|---|---|---|
| High | 要件網羅（fix-loop M1 の修正の妥当性） | 「No.6 でマージが成功してしまった場合」の No.8 の代わりの確認を、ユーザーが作る No.7 の PR で「ユーザーの承認の後」に行うとしていたが、作成者は自分の PR を承認できないため実行できない。設定を直した後に push 制限を確かめ直す手順も無い | **修正**。代わりの確認を bot が作る記録用 PR で行う形に変更（ユーザーが承認 → bot がマージ API を呼んで push 制限による拒否を確認 → bot が 1 行のコミットを push して承認取り消しを確認）。No.7 の PR がこの確認に使えない理由も明記 |
| Medium | ロジック回避（同上） | 同じ代わりの確認を bot の承認で代用すると、Code Owners 必須では最初から `REVIEW_REQUIRED` のため、Dismiss stale がオフでも誤って合格になる | **修正**（上と同じ。ユーザーの承認を得られる bot 作成 PR を使う） |
| Medium | 手順のリスク | runbook 確認 1・2 で `oshui0404` の実行を想定していたため、「Do not allow bypassing」の設定ミスがあると確認の操作そのものが main への直接 push として通る（main は初期コミットのみ・1119 コミットが入り得る） | **修正**。確認 1・2 は bot だけが実行し、`oshui0404` は実行しないと明記。PR 必須と bypass 不可は設定画面で確認する |
| Medium | 要件網羅 | No.8・No.4・No.5 が期待どおりにならない場合の分岐が無く、設定を直さないままマージに至り得る | **修正**。手動テストの「確認が失敗した場合」に No.4・No.5 と No.8 の分岐を追加（マージせずに止め、設定を直してやり直す） |
| Medium | 記録の網羅 | レビュー文書の AC 判定表のうち AC-1（TC-17 で確定）・AC-3（No.5）の記入工程が無い | **修正**。記録用 PR で AC 判定表の未記入分を記入し、AC-1 は TC-17 で確定させる旨を手動テスト・計画に追記。AC-6・AC-7 は /test で記入 |
| Low | 流れの整合 | #298 の宛先 develop は既定ブランチでないため、マージしても Issue #297 は自動では閉じない。計画ステップ 4 の参照に No.8 が無い | **修正**。「確認が失敗した場合」の Issue の扱いを「開いたまま（閉じていれば開き直す）」に変更。計画ステップ 4 に No.8 と失敗時の分岐を追記。/retro が No.4〜No.8 より前に終わる点は /retro で扱う |
| Low | 文書の前提（未実測） | 追従のコミットで差分が変わらない場合は承認が残る可能性がある | **修正**。runbook §1.5 運用・§6 を「取り消された場合だけ再承認」に変更（runbook の SHA-256 を更新） |
| Low | 確認の区別力（未実測） | No.6 の合格基準は `push` を含む別理由の拒否（secret scanning の push protection 等）でも合格になり得る | **残余**（可能性はごく低い。判断保留の基準と HTTP ステータスの記録で補う） |
| Low | tautology（残余の書き方） | test_i178 は close step 6 の先頭 3 行だけを固定しており、step 6 の 4 行目以降や新しい step 7 への追記は検知しない。記録上「step 5.5〜6 の外」と書いていたのは不正確 | **修正**（書き方のみ）。test_i178 の冒頭コメントを「step 5.5 の全文と step 6 の先頭 3 行だけを固定。後ろへの追記は設計上の残余」に訂正 |

### 修正内容

- `docs/runbooks/branch-protection-setup.md`（確認 1・2 を bot のみに・§1.5 運用・§6）。runbook の SHA-256 を `c41631a4…` に更新（設定の表・ステップ 3 の節は無変更で全文一致を確認）
- `scripts/claude/tests/test_i178_branch_protection_doc.sh`（RUNBOOK_SHA256 の更新・冒頭コメントの訂正）
- `docs/tests/open/I178_manual_test.md`（記録の対象・失敗時の分岐）・`docs/plans/open/plan_I178.md`（5-2・ステップ 4・ステップ 5）
- 確認: test_i178 `RESULT: OK (13 checks)`・第3周の改変 9 通りは引き続きすべて exit 1・TC-01〜TC-18 全件 exit 0・決定論ゲート 18 行すべて合格

第 1 周は NEW_HIGH 1 件のため、修正後に第 2 周へ進む。

VERDICT: HIGH
