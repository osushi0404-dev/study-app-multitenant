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

第 1 周は NEW_HIGH 1 件のため、修正後に第 2 周へ進む（第1周修正コミット a1ae23e）。修正で計画書を変えたため、第 2 周の前に /plan-issue-review を再実行した（20261020_2003・Warning 3 件。修正推奨の 1 件＝計画 3-4 への CONTRIBUTING.md・SECURITY.md の検索結果の追記を 30834f6 で対応。残り 2 件は対応不要と判定済み）。

---

## 第 2 周（2026-10-20・3 エージェント並列）

| # | 観点 | NEW_CRITICAL | NEW_HIGH |
|---|---|---|---|
| 1 | ロジック回避・実機 repro（固定） | 0 | 0 |
| 2 | テストの false-green・tautology（固定） | 0 | 0 |
| 3 | 要件・脅威モデルの網羅漏れ（固定） | 0 | 0 |
| | **合計** | **0** | **0** |

サブエージェント総数: 第1周 3 + 第2周 3 = 6（上限 15）。新規 Critical/High 0 件の周回のため**ステージ通過**。

### findings と対応

ステージは通過したが、Medium は確認作業の実行可能性・正確さに関わる具体的な指摘のため、通過後に修正した（修正の確認は失敗注入と全テストの再実行で行った）。

| 重大度 | 観点 | 指摘 | 対応 |
|---|---|---|---|
| Medium | ロジック回避（第1周修正の妥当性） | 確認 1・2 を「bot だけ」としたが、bot（Claude）の develop・main への push は Claude 側のガードが止める（実測 exit 2）ため実行できず、誰がどのアカウントで行うかが決まっていない。人の端末で行うと `oshui0404` の資格情報で push され得る | **修正**。runbook 確認 1・2 を「I178 以降は直 push の確認を行わない」に変更。PR 必須・bypass 不可・Restrict は設定画面で確認し、効き目は確認 4〜6 で確かめる |
| Medium | false-green | CODEOWNERS は後に書いた行が優先されるため、末尾に `* @osushi0404-bot` を足すと承認者が bot に変わるが、決定論ゲートと test_i178 は見逃す（/test の TC-02b だけが検知） | **修正**。test_i178 に `.github/CODEOWNERS` の全文固定を追加。失敗注入 6 通りすべて exit 1 |
| Medium | 脅威モデル漏れ | 自動マージ（auto-merge）が予約されていると、ユーザーが承認しただけでマージが走り、No.6・No.8 の順番が崩れる。経路が脅威モデルにも確認にも無い | **修正**。実測でリポジトリ設定は `allow_auto_merge=false`・PR #298 の `autoMergeRequest=null`（bot は予約できない）。runbook §1.5 運用に記載し、手動 No.5 の前提に `autoMergeRequest` が `null` であることの確認を追加。計画に R9 を追加 |
| Medium | 失敗時の分岐が実行できない | No.5 の後に止めて設定を直すと、残った承認が数えられて No.3・No.4 の期待値と合わず、やり直しが合格しない | **修正**。「No.4・No.5 が期待どおりにならない場合」に、ユーザーが PR 画面で自分の承認を取り消す（Dismiss review）手順を追加 |
| Low | 第1周修正の反映漏れ | 追従のコミットで承認が残ることもある旨が、手動テスト・イシュー・計画 R6 に反映されていない。計画ステップ 5 が「Issue を開き直す」のまま | **修正**。手動テストの BEHIND 時の説明・イシューの制約・計画 R6・計画ステップ 5 をそろえた |
| Low | 失敗時の分岐が不完全 | No.6 成功時の代わりの確認で、(1) が再びマージに成功した場合の扱いが無い。main（No.2）の見直しも無い | **修正**。develop と main の両方の設定を見直し、新しい記録用 PR で繰り返す手順を追加 |
| Low | 区別力（未実測） | No.8 は Dismiss stale がオフでも「Require approval of the most recent reviewable push」がオンなら同じ結果になり得る | **残余**（攻撃シナリオ 3 はどちらの設定でも塞がる。設定値は No.1 の画面で確認する） |
| Low | 行き止まり | No.6 成功時の代わりの確認 (1) で記録用 PR 自体がマージされると (2) ができない | **修正**（上の「繰り返す」手順で解消） |

### 修正内容

- `docs/runbooks/branch-protection-setup.md`（確認 1・2 を「行わない」に・§1.5 運用に自動マージ）。runbook の SHA-256 を `7ca97428…` に更新
- `scripts/claude/tests/test_i178_branch_protection_doc.sh`（CODEOWNERS の全文固定・RUNBOOK_SHA256 の更新）
- `docs/tests/open/I178_manual_test.md`（No.5 の前提・失敗時の分岐・BEHIND 時の説明）・`docs/tests/open/I178_auto_test.md`（TC-19）
- `docs/plans/open/plan_I178.md`（5-2・ステップ 5・R6・R9）・`docs/issues/open/I178.md`（制約）
- 確認: test_i178 `RESULT: OK (14 checks)`・CODEOWNERS の失敗注入 6 通りと第3周の改変 9 通りはすべて exit 1・TC-01〜TC-18 全件 exit 0・決定論ゲート 18 行すべて合格

### 判定

第 2 周で新規 Critical/High 0 件のため、敵対的レビューステージを通過。

VERDICT: OK
