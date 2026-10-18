# I178 手動テスト: CODEOWNERS で承認者を管理者に限定し、develop・main で Code Owners の承認を必須にする

対象: GitHub のブランチ保護設定（develop・main）と、設定後の PR の状態

**前提**: ステップ 1〜3 の自動テスト（TC-01〜TC-19）が合格し、ユーザーが計画書 5-5 の表のとおりブランチ保護を設定した後に行う。bot は保護設定を読めないため、設定値そのものはユーザーが画面で確認し、効き目は PR の状態（`reviewDecision`・`mergeStateStatus`）と API の応答で間接的に確認する。

**使うアカウント**: ユーザー = `oshui0404`（管理者・承認者）／ bot = `osushi0404-bot`（Claude が `gh` で操作）

**使う PR**: No.3〜No.6・No.8 は本イシューの PR #298（bot が作成）。No.7 はマージ後にユーザーが作る確認用 PR（ブランチ `check/I178-codeowners`）。

**実施の順番と記録の残し方**（adversarial 第2周 Medium 対応）:

1. **/test**: No.1〜No.3 を行い、結果をこのファイルに記入してコミット・push する（承認前なので承認の取り消しは起きない）。
2. **/close**: Ready にした後に No.4、ユーザーの承認後に No.5・No.6 を行う。No.4〜No.6 の結果はこのファイル（closed へ移動後）に記入する。
3. **No.8**: No.4〜No.6 の結果をコミット・push する。このコミット自体が「承認後の新しいコミット」になるので、承認が取り消されること（Dismiss stale の効き目）を確かめる。その後、ユーザーが再承認してマージする。
4. **マージ後**: No.7 と TC-17 を行う。結果は、bot が作る記録用 PR（`docs(I178): マージ後確認の記録`・develop 宛て）でこのファイルと自動テスト文書に記入し、ユーザーが承認・マージする。

承認の後、マージまでの間に develop が先に進んで PR が `BEHIND` になった場合は、bot が追従のコミット（`bash scripts/claude/pr-base-sync.sh final`）を push する。この場合も承認は取り消されるので、CI の完了を待ってからユーザーに再承認を依頼する（runbook §6「承認したのに BLOCKED に戻った」）。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | GitHub → Settings → Branches → `develop` のルールの **Edit** を開き、計画書 5-5 の表の develop 列と見比べる | 「Require approvals」がオンで数値が `1`、「Dismiss stale pull request approvals when new commits are pushed」「Require review from Code Owners」「Do not allow bypassing the above settings」「Restrict who can push to matching branches」とその下の「Restrict pushes that create matching branches」がオン。Restrict の一覧に `oshui0404` だけが表示されている | Human | | AC-2・AC-5。計画書 5-5 の表と runbook §1 の表は同じ値・同じ並び（runbook 側は TC-19 で検証） |
| 2 | 同じ画面で `main` のルールを開き、5-5 の表の main 列と見比べる | No.1 と同じ項目がすべてオンで、Restrict の一覧に `oshui0404` だけが表示されている | Human | | AC-2・AC-5。main は CODEOWNERS が届くまで Code Owners 要件が効かないため、この画面確認が main の確認の中心になる（runbook §4 確認 4） |
| 3 | 設定後、bot で `gh pr view 298 --json reviewDecision,isDraft` を実行する | `reviewDecision` が `REVIEW_REQUIRED`（設定前の実測は空文字） | Claude | | AC-2（承認要件が付いたこと）。PR #298 のマージ前は develop に CODEOWNERS が無いため、No.3〜No.5 は「承認 1 件の要件」の確認であり、Code Owners の効き目は No.7 で確認する（runbook §1.5「設定変更直後の develop」） |
| 4 | /close で PR #298 を Ready にした後、`bash scripts/claude/pr-base-sync.sh final` を実行し、続けて `gh pr view 298 --json reviewDecision,mergeStateStatus` を実行する | pr-base-sync が exit 0（「CI 全グリーン（BLOCKED＝Approve 待ち等）」）。`reviewDecision=REVIEW_REQUIRED`・`mergeStateStatus=BLOCKED` | Claude | | AC-2・AC-7 |
| 5 | ユーザーが PR #298 の Files changed → Review changes → **Approve** を押す。その後、bot で `gh pr view 298 --json reviewDecision,mergeStateStatus` を実行する | `reviewDecision=APPROVED`。GitHub の PR 画面で、ユーザーには「Merge pull request」ボタンが押せる状態で表示される | Human（承認）＋ Claude（確認） | | AC-3 |
| 6 | No.5 の直後。(1) bot で `gh pr view 298 --json reviewDecision,mergeStateStatus,headRefOid,reviews,statusCheckRollup` を実行し、runbook §4 確認 6 の前提 4 点（`APPROVED`・`BEHIND`/`DIRTY` でない・最新の承認の commit が `headRefOid` と同じ・必須チェック 5 件がすべて `SUCCESS`）を確かめる。(2) **ユーザーの了承を得てから** bot で `gh api -X PUT repos/osushi0404-dev/study-app-multitenant/pulls/298/merge -f merge_method=merge` を実行する | (1) の前提がすべて成り立つ。(2) API が失敗し、`gh pr view 298 --json state` が `OPEN` のまま。応答の `message` が runbook §4 確認 6 の「合格」基準（`push` または `authorized` を含み、`review`・`approv`・`status check` を含まない。大文字小文字は区別しない）に当たる | Claude | | AC-5（bot はマージできない）。`gh pr merge` は API を呼ぶ前に手元で `BLOCKED` を判定して汎用の文で止まり、push 制限と他の理由を区別できないため、API を直接呼ぶ（adversarial 第2周 Medium 対応）。(1) が成り立たない場合は (2) を行わず、状態を整えてからやり直す。`message` が「前提崩れ」基準に当たる場合もやり直す。「判断保留」の場合は文をそのまま記録し、ユーザーに確認する（plan-review 20261018_1145 Warning 対応で基準を明文化）。万一成功した場合は承認済みの内容がマージされるだけで実害は無いが、push 制限が効いていないため No.2 を見直す |
| 7 | **マージ後**。ユーザーが develop から `check/I178-codeowners` ブランチを作り、`check_codeowners.txt`（1 行）を追加して develop 宛ての PR を作る。**ユーザーの了承を得てから** bot で `gh pr review <PR番号> --approve` を実行し、`gh pr view <PR番号> --json reviewDecision,mergeStateStatus,files` を実行する。確認後、`gh pr close <PR番号> --delete-branch` で閉じ、ブランチも削除する | `files` が 1 件以上。bot の承認後も `reviewDecision=REVIEW_REQUIRED`・`mergeStateStatus=BLOCKED` のまま。PR はマージされずに close され、ブランチ `check/I178-codeowners` も削除される | Human（PR 作成）＋ Claude（承認・確認・close） | | AC-2（develop の Code Owners の効き目）・AC-4。Code Owners の要件はファイル変更を含む PR にだけ働くため、空コミットの PR では正しく設定していても bot の承認で `APPROVED` になり判定を誤る（adversarial 第1周 Medium 対応）。bot による承認の記録が GitHub に残ることは grill-me で了承済み。CODEOWNERS が develop に入っている必要があるためマージ後に行う（TC-17 も同時に実行する） |
| 8 | No.6 の後、bot が No.4〜No.6 の結果を記入したこのファイルをコミット・push し、`gh pr view 298 --json reviewDecision,mergeStateStatus` を実行する | push 前は `APPROVED`、push 後は `reviewDecision=REVIEW_REQUIRED`（承認が取り消される）。その後ユーザーが再承認すると `APPROVED` に戻る | Claude（push・確認）＋ Human（再承認） | | AC-5（Dismiss stale の効き目）・攻撃シナリオ 3（承認後の追加 push）。記録のためのコミットを、そのまま承認取り消しの確認に使う（adversarial 第2周 Low 対応） |
