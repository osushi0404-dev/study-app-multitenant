# I178 自動テスト: CODEOWNERS で承認者を管理者に限定し、develop・main で Code Owners の承認を必須にする

対象（再オープン分・2026-10-24）: `docs/runbooks/branch-protection-setup.md`・`docs/runbooks/issue-flow.md`・`docs/runbooks/workflow.md`・`docs/runbooks/onboarding.md`・`docs/plans/closed/plan_I032.md`（移動）・`scripts/claude/tests/test_i178_branch_protection_doc.sh`（削除）・`.github/CODEOWNERS` ほか（無改変の確認）

**合否判定インターフェース**: すべて exit code に統一する（合格 = exit 0 / 不合格 = 非ゼロ）。出力値の目視比較は合否基準にしない。不在判定は `! grep -q ...` の形で書き、合格時に exit 0 を返す。

**実行環境**: ホスト（ワークツリー `harness-1`）。GitHub API は使わない。

初回分（2026-10-17〜2026-10-21）の TC・結果は、このファイル後半の「初回分の記録」に残す。初回分の決定論ゲートは、再オープンで書き換える文言と削除する `test_i178_branch_protection_doc.sh` を検証していたため、実走をやめる。

---

## 決定論ゲート（自動実走）
<!--
  /code-review（code-review.sh）がこのブロックを 1 行 1 コマンドで実走し、実 exit code を VERDICT に注入する。
  ファイルの不在・無改変の検証（RTC-19・RTC-20・RTC-23）は allowlist 外のため /test で実施する。
-->
```bash
! grep -q "自分で承認できず" docs/runbooks/branch-protection-setup.md
! grep -q "ユーザーが作った PR はマージできない" docs/runbooks/branch-protection-setup.md
! grep -q "一時的にオフ" docs/runbooks/branch-protection-setup.md
! grep -q "I178 の /retro で確認する" docs/runbooks/branch-protection-setup.md
! grep -q "のままであることを確認する" docs/runbooks/branch-protection-setup.md
grep -q "作成者が .oshui0404. 本人の PR では Code Owners の要件がかからず" docs/runbooks/branch-protection-setup.md
grep -q "bot や外部の人が作った PR を .oshui0404. が承認しない限りマージできない" docs/runbooks/branch-protection-setup.md
grep -qxF "### 自分が作った PR をマージしたい" docs/runbooks/branch-protection-setup.md
grep -qxF "### 確認 5: （I178 の再オープンで廃止）" docs/runbooks/branch-protection-setup.md
grep -q "bot に承認を頼む" docs/runbooks/branch-protection-setup.md
grep -q "効き目は確認 4・6" docs/runbooks/branch-protection-setup.md
! grep -q "確認 4〜6" docs/runbooks/branch-protection-setup.md
! grep -q "git push.*develop" docs/runbooks/issue-flow.md
! grep -q "git push.*main" docs/runbooks/issue-flow.md
! grep -q "^git merge" docs/runbooks/issue-flow.md
! grep -qx "git checkout develop" docs/runbooks/issue-flow.md
grep -q "oshui0404 が GitHub の PR 画面で承認・マージする" docs/runbooks/issue-flow.md
! grep -q "git push.*main" docs/runbooks/workflow.md
! grep -q "git push.*develop" docs/runbooks/workflow.md
! grep -q "git push.*develop" docs/runbooks/onboarding.md
! grep -q "git push.*main" docs/runbooks/onboarding.md
! grep -q "^git merge" docs/runbooks/workflow.md
! grep -q "^git checkout main" docs/runbooks/workflow.md
grep -q "gh pr create --base main --head develop" docs/runbooks/workflow.md
grep -q "gh pr create --base develop --head hotfix/" docs/runbooks/workflow.md
grep -q "main がまだ初期コミットだけの間は" docs/runbooks/workflow.md
grep -q "develop → main の PR を作り" docs/runbooks/onboarding.md
grep -q "I032" docs/plans/closed/plan_I032.md
# docs/tests・docs/plans・docs/reviews にある過去の記録は検索の対象外（RTC-21）
! grep -rq "test_i178_branch_protection_doc" scripts .claude .github docs/runbooks
grep -qxF '* @oshui0404' .github/CODEOWNERS
```

---

## 計画時ベースライン（Red・失敗注入・再オープン分）

2026-10-24 /plan-issue で実測（書き換え前の状態）。ゲートは code-review.sh と同じ抽出規則・`! grep` の扱い（内側の exit 1 だけを合格）で実行した。

| TC | 実測 exit | 判定 |
|---|---|---|
| ゲート 1〜13・15〜19・22〜27 行目 | すべて 1 | ✅ Red（旧記述が残り、新記述が無い） |
| ゲート 14・20・21 行目（RTC-09b・RTC-17b・RTC-17c） | 0 | 既存状態（issue-flow.md・onboarding.md に該当の push 行がもともと無い＝再発防止の行）。**注入版**（`git push origin HEAD:develop`・行頭に空白のある `git push -u origin main` を書いた一時ファイルを検索）= どちらも **1** ✅（2026-10-24・plan-review 20261024_1452 Warning 対応で追加） |
| ゲート 28 行目（RTC-18） | 0 | 既存状態（`docs/plans/closed/plan_I032.md` は open 側と同じ内容で既にある＝重複）。**注入版**（存在しないファイルを指定）= **2** ✅ |
| ゲート 29 行目（RTC-21） | 0 | 既存状態（参照 0 件）。**注入版**（`test_i178_branch_protection_doc.sh` を呼ぶ行を書いた一時ディレクトリを検索）= **1** ✅ |
| ゲート 30 行目（RTC-22） | 0 | 既存状態。**注入版**（所有者を `@osushi0404-bot` に差し替えた CODEOWNERS）= **1** ✅ |
| RTC-19 | 1 | ✅ Red（open に重複が残っている） |
| RTC-20 | 1 | ✅ Red（テストがまだある） |
| RTC-23 | 0 | 既存状態。**注入版**（比較先を CODEOWNERS 追加前の `6c88d9f^1` にした）= **1** ✅ |

---

## RTC-01〜RTC-05: runbook から No.7 と矛盾する記述が消えている（AC-R1）
- RTC-01: 「自分で承認できず」が無い（§1.5 運用の旧文） / ゲート 1 行目
- RTC-02: 「ユーザーが作った PR はマージできない」が無い（§6 の旧文） / ゲート 2 行目
- RTC-03: 「一時的にオフ」が無い（§6 の bypass を外す旧手順） / ゲート 3 行目
- RTC-04: 「I178 の /retro で確認する」が無い（§1.5 役割 3 の旧注記） / ゲート 4 行目
- RTC-05: 「のままであることを確認する」が無い（§4 確認 5 の旧期待結果） / ゲート 5 行目
- 期待: すべて exit 0

## RTC-06〜RTC-08: runbook に No.7 の事実と新しい手順がある（AC-R1）
- RTC-06: §1.5 運用に「作成者が `oshui0404` 本人の PR では Code Owners の要件がかからず」 / ゲート 6 行目
- RTC-07: §概要に「bot や外部の人が作った PR を `oshui0404` が承認しない限りマージできない」 / ゲート 7 行目
- RTC-08a: §6 の見出し「### 自分が作った PR をマージしたい」（行の完全一致） / ゲート 8 行目
- RTC-08b: §4 の見出し「### 確認 5: （I178 の再オープンで廃止）」（行の完全一致） / ゲート 9 行目
- RTC-08c: §6 に「bot に承認を頼む」手順 / ゲート 10 行目
- RTC-08d: §4 確認 1・2 の段落が「効き目は確認 4・6」 / ゲート 11 行目
- RTC-08e: 旧文「確認 4〜6」が無い（新旧の併記を検知・plan-review 20261024_1452 Info 対応） / ゲート 12 行目
- 期待: すべて exit 0（バッククォートはゲート行に書けないため、任意の 1 文字 `.` で表す）

**直 push の検知の形（RTC-09・RTC-12・RTC-13・RTC-17b/c）**: 行頭に限らず、`git push` の後に `develop`・`main` が出る行をすべて不合格にする（`git push origin HEAD:develop`・`git push -u origin main` 等の別の書き方も検知する・plan-review 20261024_1452 Warning 対応）。対象は書き換える 3 ファイルだけ。`branch-protection-setup.md` と `danger-ops.md` には「行わない」「止める」の説明として同じ文字列があるため対象外とし、手動 RNo.1 で分類する。3 ファイルで当たる行は、書き換え前は書き換え対象の 4 行だけ（2026-10-24 実測）。

## RTC-09〜RTC-11: issue-flow.md ステップ 25 が PR 経由になっている（AC-R2・AC-R3）
- RTC-09a: `git push` の後に `develop` が出る行が無い / ゲート 13 行目
- RTC-09b: `git push` の後に `main` が出る行が無い / ゲート 14 行目
- RTC-10a: 行頭の `git merge` が無い / ゲート 15 行目
- RTC-10b: `git checkout develop` だけの行が無い / ゲート 16 行目（L221 の `git checkout --no-track -b feature/…` は行の完全一致なので当たらない）
- RTC-11: 「oshui0404 が GitHub の PR 画面で承認・マージする」がある / ゲート 17 行目
- 期待: すべて exit 0

## RTC-12〜RTC-16: workflow.md のリリース・hotfix が PR 経由になっている（AC-R2・AC-R3）
- RTC-12: `git push` の後に `main` が出る行が無い / ゲート 18 行目
- RTC-13: `git push` の後に `develop` が出る行が無い / ゲート 19 行目
- RTC-14a: 行頭の `git merge` が無い / ゲート 22 行目
- RTC-14b: 行頭の `git checkout main` が無い / ゲート 23 行目（hotfix は `git checkout --no-track -b hotfix/… origin/main` にする）
- RTC-15: リリースの `gh pr create --base main --head develop` がある / ゲート 24 行目
- RTC-16a: hotfix の develop への反映 `gh pr create --base develop --head hotfix/` がある / ゲート 25 行目
- RTC-16b: main への hotfix の制約「main がまだ初期コミットだけの間は」がある / ゲート 26 行目
- 期待: すべて exit 0。タグの push（`git push origin vX.X.X`）・hotfix ブランチの push（`git push -u origin hotfix/…`）には `develop`・`main` が出ないので当たらない

## RTC-17: onboarding.md の main へのマージが PR 経由（AC-R2・AC-R3）
- RTC-17a: 「develop → main の PR を作り」がある / ゲート 27 行目
- RTC-17b・RTC-17c: `git push` の後に `develop`・`main` が出る行が無い / ゲート 20・21 行目
- 期待: すべて exit 0

## RTC-18・RTC-19: plan_I032.md が closed にある（AC-R4）
- RTC-18: `docs/plans/closed/plan_I032.md` がある（ファイルが無いと grep は exit 2。closed 側は計画時点で既にあり、open 側は同じ内容の重複。誤って closed 側を消す事故を防ぐ） / ゲート 28 行目
- RTC-19（/test で実行）: open に残っていない
  ```bash
  [ ! -e docs/plans/open/plan_I032.md ]
  ```
- 期待: どちらも exit 0

## RTC-20・RTC-21: test_i178_branch_protection_doc.sh が無く、参照もされていない（AC-R5）
- RTC-20（/test で実行）:
  ```bash
  [ ! -e scripts/claude/tests/test_i178_branch_protection_doc.sh ]
  ```
- RTC-21: `scripts`・`.claude`・`.github`・`docs/runbooks` に名前の参照が無い / ゲート 29 行目（docs/tests・docs/plans・docs/reviews の過去の記録は対象外）
- 期待: どちらも exit 0

## RTC-22・RTC-23: 変えないものが変わっていない（AC-R6）
- RTC-22: CODEOWNERS に `* @oshui0404` の行がある / ゲート 30 行目
- RTC-23（/test で実行）: CODEOWNERS・pr-base-sync・close スキル・review-rules が develop から無改変
  ```bash
  git diff --quiet origin/develop -- .github/CODEOWNERS scripts/claude/pr-base-sync.sh .claude/skills/close/SKILL.md docs/runbooks/review-rules.md
  ```
- 期待: どちらも exit 0。GitHub の設定は bot から読めないため、変えていないことは計画書 R5-7 と手順に設定変更が無いことで担保する

## 実行結果（再オープン分）

| TC | 実行日 | 結果 | 備考 |
|---|---|---|---|
| ゲート 30 行（RTC-01〜RTC-18・RTC-21・RTC-22） | 2026-10-24 | ✅ 全件 exit 0 | /implement 完了時（ステップ R1〜R4 反映後）。code-review.sh と同じ抽出規則・`! grep` の扱いで実行。/test で再実行する |
| RTC-19・RTC-20・RTC-23 | 2026-10-24 | ✅ 全件 exit 0 | /implement 完了時。RTC-23 の注入版（比較先 `6c88d9f^1`）は引き続き exit 1 |

---

# 初回分の記録（2026-10-17〜2026-10-21）

対象: `.github/CODEOWNERS`・`docs/runbooks/branch-protection-setup.md`・`.claude/skills/close/SKILL.md`・`scripts/claude/pr-base-sync.sh`（無改変の確認）

**実行環境**: ホスト（ワークツリー `/mnt/c/app/wt-harness`）。gh 2.88.1。GitHub API を使う TC（TC-03・TC-04・TC-17）は bot アカウント（write 権限）で実行できることを確認済み。

**初回分の決定論ゲート（18 行・実走をやめた）**: TC-01〜TC-16・TC-18・TC-19 を 1 行ずつ並べたもの。行の一覧は、初回の /test 時点（commit `1d74938`）のこのファイルを参照（`git show 1d74938:docs/tests/open/I178_auto_test.md`）。

**ゲート行の書き方（code-review 20261017_1936 対応）**: code-review.sh は `|`・バッククォート・`$(`・`;`・`&`・`>` を含む行と、`grep` / `! grep` / `bash scripts/claude/tests/*.sh` 等の許可リスト以外のコマンド（`test`・`git diff` 等）を実走せず fail-closed（BLOCKER）にする。そのため、TC-01 は `test -f` の代わりに `grep -q`（ファイルが無いと exit 2）、TC-07 は `|` を使わず 2 行に分割、TC-13・TC-18a は該当文字（バッククォート・`|`）を任意の 1 文字 `.` で表す。TC-15 は完全な無改変確認（`git diff --quiet`）を /test で行い、ゲートでは前提の文言が残っていることを `grep` で確認する。書き換えた 6 行は、変更前のファイル（`origin/develop` の版・前提文言を壊した pr-base-sync・CODEOWNERS 不在）で非ゼロになることを確認済み（2026-10-17）。

---

## 計画時ベースライン（Red・失敗注入・2026-10-17 実測）

実装前の状態で全 TC を実行した結果。追加内容を確かめる TC がすべて非ゼロで終わることが、そのまま失敗注入（対象が無い・壊れている状態で NG を返すこと）の確認になる。無改変・既存状態を確かめる TC（TC-03・TC-15・TC-16）は、別途注入版で非ゼロを確認した。

| TC | 実測 exit | 判定 |
|---|---|---|
| TC-01 | 1 | ✅ Red（CODEOWNERS 不在） |
| TC-02a / TC-02b | 2 / 2 | ✅ Red |
| TC-03 | 0 | 既存状態（`oshui0404`=admin）。**注入版**（bot `osushi0404-bot` で照会）= **1** ✅ |
| TC-04 | 2 | ✅ Red（CODEOWNERS を含まないブランチでは API が 404 → 非ゼロ） |
| TC-05〜TC-14 | すべて 1 | ✅ Red（TC-07・TC-08 は現行 runbook に誤記・旧記述があるため不合格＝否定判定が実際に NG を返す） |
| TC-15 | 0 | 無改変。**注入版**（比較先を変更前の develop `85a0b9c` にして差分がある状態）= **1** ✅ |
| TC-16 | 0 | 既存テスト `RESULT: OK (21/21 cases, 30 assertions)`（回帰の基準） |
| TC-17 | 2 | ✅ Red（develop に CODEOWNERS が無いため 404 → 非ゼロ） |
| TC-18a / TC-18b | 1 / 1 | ✅ Red（旧差異表・旧 develop 表の行が残っているため不合格＝否定判定が実際に NG を返す） |

---

## TC-01: CODEOWNERS が存在する（AC-1）
- コマンド: 決定論ゲート 1 行目
- 期待: exit 0

## TC-02: CODEOWNERS の中身が `* @oshui0404` の 1 行だけ（AC-1）
- TC-02a（決定論ゲート 2 行目）: `* @oshui0404` と完全一致する行がある → exit 0
- TC-02b（/test で実行）: コメント・空行以外の行がちょうど 1 行
  ```bash
  [ "$(grep -cvE '^[[:space:]]*(#|$)' .github/CODEOWNERS)" -eq 1 ]
  ```
- 期待: どちらも exit 0

## TC-03: CODEOWNERS の所有者がリポジトリの管理者である（AC-1・R1）
- /test で実行:
  ```bash
  [ "$(gh api repos/osushi0404-dev/study-app-multitenant/collaborators/oshui0404/permission --jq .permission)" = admin ]
  ```
- 期待: exit 0（`oshui0404` の権限が `admin`）

## TC-04: GitHub の CODEOWNERS 検査で問題が 0 件（AC-1・ステップ 1 のゲート）
- ステップ 1 の push 後に /test で実行（後続ステップへ進む条件）。ref はカレントブランチから取る（ブランチ名の書き間違いで「ブランチ不在の 404」と「検査エラー」が混ざらないようにする・plan-review 20261017_1916 Info 対応）:
  ```bash
  [ "$(gh api "repos/osushi0404-dev/study-app-multitenant/codeowners/errors?ref=$(git rev-parse --abbrev-ref HEAD)" --jq '.errors | length')" -eq 0 ]
  ```
- 期待: exit 0（`errors` が空配列。所有者名の誤り・権限不足・構文エラーがあると 1 件以上になる）。CODEOWNERS を含まないブランチでは API が 404 を返し、空文字との比較で非ゼロになる（計画時ベースラインで確認済み）

## TC-05: runbook に「Require review from Code Owners」がある（AC-6）
- コマンド: 決定論ゲート 3 行目 / 期待: exit 0

## TC-06: runbook に「Restrict who can push to matching branches」がある（AC-6）
- コマンド: 決定論ゲート 4 行目 / 期待: exit 0

## TC-07: runbook に「自己 approve」「セルフ approve」の誤記が無い（AC-6）
- コマンド: 決定論ゲート 5・6 行目 / 期待: exit 0

## TC-08: runbook に develop を「承認不要」とする記述が無い（AC-6）
- コマンド: 決定論ゲート 7 行目 / 期待: exit 0

## TC-09: runbook に新設セクション「承認者の限定（I178）」がある（AC-6）
- コマンド: 決定論ゲート 8 行目 / 期待: exit 0

## TC-10: runbook に main の制約（CODEOWNERS が届かない）が書かれている（AC-6・R3）
- コマンド: 決定論ゲート 9 行目 / 期待: exit 0

## TC-11: runbook に「PR は必ず bot（Claude）が作成する」運用が書かれている（AC-6・R4）
- コマンド: 決定論ゲート 10 行目 / 期待: exit 0

## TC-12: runbook に、承認後のコミットで承認が取り消される旨が書かれている（AC-6・R6）
- コマンド: 決定論ゲート 11 行目 / 期待: exit 0

## TC-13: close スキル step 5.5 の前提が「Code Owners の承認が必須」になっている（AC-7）
- コマンド: 決定論ゲート 12 行目 / 期待: exit 0

## TC-14: close スキル step 6 に再承認の依頼が書かれている（AC-7・R6）
- コマンド: 決定論ゲート 13 行目 / 期待: exit 0

## TC-15: `pr-base-sync.sh` を変更していない（AC-7）
- TC-15g（決定論ゲート 14 行目）: 前提の文言「CLEAN は要求しない＝Approve 待ちの BLOCKED は正常」が残っている → exit 0
- TC-15（/test で実行）: ファイル全体が無改変
  ```bash
  git diff --quiet origin/develop -- scripts/claude/pr-base-sync.sh
  ```
- 期待: どちらも exit 0

## TC-16: `pr-base-sync.sh` の既存テストが合格する（AC-7・回帰）
- コマンド: 決定論ゲート 15 行目
- 期待: exit 0（`RESULT: OK (21/21 cases, 30 assertions)`）

## TC-17: マージ後、develop の CODEOWNERS 検査で問題が 0 件（AC-1・マージ後）
- PR #298 のマージ後に実行:
  ```bash
  [ "$(gh api 'repos/osushi0404-dev/study-app-multitenant/codeowners/errors?ref=develop' --jq '.errors | length')" -eq 0 ]
  ```
- 期待: exit 0

## TC-18: runbook から旧設定の表の行が消えている（AC-6）
- plan-review 20261017_1916→1921 Warning 対応。TC-07・TC-08 は日本語の文言しか見ないため、英語の表の行が残っても検知できない穴を塞ぐ。
- TC-18a（決定論ゲート 16 行目）: 旧「develop と main の差異」表の `| Required approvals | 0 |` 行が無い
- TC-18b（決定論ゲート 17 行目）: 旧 develop 表の `Require approvals（サブオプション）` 行が無い
- 期待: どちらも exit 0

## TC-19: runbook の develop・main の設定表と手順、close step 5.5〜6 を節の全文で検証する（AC-6・AC-7）
- adversarial 第1周 High 対応で新設し、第2周 High 対応で方式を変更した。TC-05〜TC-12 は文言がファイルのどこかにあるかしか見ない。第1周版（行ごとの存在確認）も、親スイッチのオフ・矛盾行の併記・空白の違い・コメントで隠す等の後退を取りこぼした。
- コマンド: 決定論ゲート 18 行目（`bash scripts/claude/tests/test_i178_branch_protection_doc.sh`）
- 検証内容: 次の 5 つの節を、見出し行（完全一致）で切り出し、スクリプト内の期待値と**全文の完全一致**で比較する。開始・終了の見出しのどちらかが無ければ節が空になり NG。(1) runbook §1 develop の表（`### develop ブランチ`〜`### main ブランチ`）(2) runbook §1 main の表（`### main ブランチ`〜`## 1.5 承認者の限定（I178）`）(3) runbook §3 ステップ 3（`### ステップ 3: 各項目を設定`〜`### ステップ 4: 保存`）(4) close step 5.5（`5.5) …`〜step 6 の 1 行目）(5) close step 6 の 2 行
- 設定を変えるときは、このスクリプトの期待値と計画書 5-5 の表を同時に更新する
- **fix-loop 20261018 で追加（adversarial 第3周 High・案 A）**: (6) runbook 全体の SHA-256 が `RUNBOOK_SHA256` と一致する（節の列挙から漏れた部分の後退も検知する。runbook を正当に直すときは、内容をレビューしてから値を更新する）(7) 節の切り出しに使う見出し 7 つ（runbook 5・close 2）がファイル内にちょうど 1 回だけ (8) close step 6 は追加した一文を含む 3 行を固定
- **再ステージ第2周で追加（Medium）**: (9) `.github/CODEOWNERS` を全文で固定する（後に書いた行が優先されるため、末尾に別の所有者の行を足すだけで承認者が入れ替わる。決定論ゲート 1・2 行目の存在確認では見逃す。`CODEOWNERS` 環境変数で差し替え可能）
- 期待: exit 0（`RESULT: OK (14 checks)`）
- 失敗注入（2026-10-18・`RUNBOOK`/`SKILL` で対象を差し替え）: 第1周の 14 通り（develop の Code Owners を OFF・develop の承認を 0・main の Restrict を OFF・develop の Restrict に bot を追加・main の Code Owners 行を削除・ステップ 3 の Code Owners をオフ・develop 表を旧設定へ・両表と手順から Code Owners と Restrict を削除・develop 表に OFF 行を併記・Restrict の見出し直後をオフ・変更前の runbook・step 5.5 の develop/main 入れ替え・変更前の close スキル・runbook 不在）と、第2周のレビューアが第1周版で合格すると実測した 11 通り（PR 必須の親スイッチをオフ・force push/削除をオン・status checks をオフ・セルの空白を変えた OFF 行の併記・force push の矛盾行の併記・語順を変えた旧手順・ON 行をコメントで隠す・bypass の見出しの差し替え・close スキルに矛盾する文を追加 等）の計 25 通りすべてで **exit 1**。無改変の対照は exit 0

---

## 実行結果

| TC | 実行日 | 結果 | 備考 |
|---|---|---|---|
| TC-04 | 2026-10-17 | ✅ exit 0 | /implement ステップ 1 のゲート。CODEOWNERS push 直後（3d6f029）に `{"errors":[]}` を確認してから後続へ進んだ |
| TC-01〜TC-16・TC-18 | 2026-10-17 | ✅ 全件 exit 0 | /implement 完了時（ステップ 1〜3 反映後）。TC-16 は `RESULT: OK (21/21 cases, 30 assertions)`。/test で再実行する |
| TC-19 | 2026-10-18 | ✅ exit 0 | adversarial 第1周対応後。`RESULT: OK (43 assertions)`・失敗注入 14 通りすべて exit 1 |
| TC-19 | 2026-10-18 | ✅ exit 0 | adversarial 第2周対応後（全文比較に変更）。`RESULT: OK (5 blocks)`・失敗注入 25 通りすべて exit 1 |
| TC-19 | 2026-10-18 | ✅ exit 0 | fix-loop 20261018 対応後（runbook 全体の SHA-256・見出し 1 回・close step 6 の 3 行）。`RESULT: OK (13 checks)`。失敗注入: 第3周の改変を現行ファイルに入れ直した 9 通り（ステップ 5 で main の Restrict をオフ・ステップ 2 のパターン変更・同じ見出しの旧表の追加・§1.5 運用に矛盾文・§6 末尾に矛盾手順・概要の差し替え・確認 5 を空 PR に戻す・close step 6 の一文削除・close step 6 の見出し重複）すべて exit 1。第1周・第2周の 25 通りも引き続きすべて exit 1。close スキルの step 5.5〜6 の外への矛盾文の追加（第3周 E）は exit 0（ファイル全体を固定しない設計上の残余・診断メモ 20261018_1300 で決定） |
| TC-19 | 2026-10-20 | ✅ exit 0 | adversarial 再ステージ第1周対応後（runbook の確認 1・2・運用・§6 を変更し、SHA-256 を `c41631a4…` に更新）。変更直後は SHA-256 不一致で exit 1 となり、変更の検知が働くことを実地で確認。更新後 `RESULT: OK (13 checks)` |
| TC-19 | 2026-10-20 | ✅ exit 0 | adversarial 再ステージ第2周の Medium 対応後。`.github/CODEOWNERS` の全文固定を追加（`RESULT: OK (14 checks)`）し、runbook の SHA-256 を `7ca97428…` に更新。CODEOWNERS の失敗注入 6 通り（末尾に bot を所有者として追加・所有者の行を削除・同じ行に bot を併記・行末に空白・docs だけ bot を所有者に・ファイル不在）すべて exit 1。第3周の改変 9 通りも引き続きすべて exit 1 |
| TC-01〜TC-16・TC-18・TC-19 | 2026-10-20 | ✅ 全件 exit 0 | **/test I178**（HEAD 1d74938・ブランチ保護の設定変更後）。TC-01〜TC-16・TC-18 は `ALL=PASS`（TC-03・TC-04 は GitHub API で実測・TC-16 は `RESULT: OK (21/21 cases, 30 assertions)`）、TC-19 は `RESULT: OK (14 checks)`、決定論ゲート 18 行は code-review.sh の規則で `gates=18 bad=0`。PR #298 の CI は 6 件すべて pass（Backend Lint & Security・Backend Tests・E2E Tests (Playwright)・Frontend Lint & Security・Frontend Tests・Frontend Type Check）。pytest・Jest・E2E のローカル実行は非該当（Backend・Frontend の変更なし・計画 7 章） |
| TC-17 | 2026-10-21 | ✅ exit 0 | PR #298 のマージ（`6c88d9f`）後に `gh api "repos/osushi0404-dev/study-app-multitenant/codeowners/errors?ref=develop"` → `{"errors":[]}`（develop 上の CODEOWNERS を GitHub が問題なく解釈） |

---

## 再発防止記録（fix-loop 20261018）

- **なぜ失敗したか**: 認可設定の手順書（runbook）の正しさを、文書の一部を拾って確かめるテストで守ろうとした。敵対的レビューのたびに検証範囲を「文言の存在 → 行の存在 → 5 節の全文一致」と広げたが、列挙方式である限り、列挙から漏れた節・同じ見出しの重複・節の外の矛盾が次の穴になった（3 周で未収束）。あわせて、承認の後・マージの前に行う確認（No.6・No.8）を、承認とマージを一度に依頼する汎用の /close の流れに後から差し込み、順番の約束（承認だけを押す）をどこにも書かなかった。
- **何を変えたか**: test_i178 に runbook 全体の SHA-256 固定と見出しの一意性の確認を追加し（診断メモの案 A）、runbook のどこが変わっても NG にした。手動テスト・runbook・close step 6 に「承認だけを依頼し、確認の後にマージ」を明記した。確認が失敗した場合の分岐、記録先（記録用 PR に No.8 とレビュー文書の AC 判定表を追加）、見直す設定画面の取り違え（No.2 → No.1）も直した。
- **セキュリティ上の考慮点**: runbook は認可設定（誰が承認・マージできるか）の契約書であり、黙って緩められると bot や外部 PR のマージを GitHub が止めない状態に戻り得る。ハッシュ固定により、runbook の変更には必ずテストの更新（＝内容のレビュー）が伴う。bot のマージ拒否と承認取り消しの実地確認が、文書どおりの流れで確実に行われるようにした。
- **次回どう防ぐか**: 設定や手順の「契約書」にあたる文書をテストで守るときは、部分を列挙して拾う方式ではなく、ファイル全体を固定（レビュー済みの版から変わっていないこと）したうえで、意味の確認が要る節だけを全文比較する。汎用スキルの流れに個別の確認を差し込むときは、順番の約束をスキル側にも一般的な形で書き、テスト文書から参照する。同型の弱さ（部分を拾う文書テスト）の横展開は /retro で判断する。
