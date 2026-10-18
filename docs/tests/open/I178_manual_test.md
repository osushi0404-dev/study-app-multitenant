# I178 手動テスト: CODEOWNERS で承認者を管理者に限定し、develop・main で Code Owners の承認を必須にする

対象: GitHub のブランチ保護設定（develop・main）と、設定後の PR の状態

**前提**: ステップ 1〜3 の自動テスト（TC-01〜TC-16）が合格し、ユーザーが計画書 5-5 の表のとおりブランチ保護を設定した後に行う。bot は保護設定を読めないため、設定値そのものはユーザーが画面で確認し、効き目は PR の状態（`reviewDecision`・`mergeStateStatus`）で間接的に確認する。

**使うアカウント**: ユーザー = `oshui0404`（管理者・承認者）／ bot = `osushi0404-bot`（Claude が `gh` で操作）

**使う PR**: No.3〜No.6 は本イシューの PR #298（bot が作成）。No.7 はマージ後にユーザーが作る確認用 PR。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | GitHub → Settings → Branches → `develop` のルールの **Edit** を開き、計画書 5-5 の表の develop 列と見比べる | 「Require approvals」がオンで数値が `1`、「Dismiss stale pull request approvals when new commits are pushed」「Require review from Code Owners」「Do not allow bypassing the above settings」「Restrict who can push to matching branches」とその下の「Restrict pushes that create matching branches」がオン。Restrict の一覧に `oshui0404` だけが表示されている | Human | | AC-2・AC-5。計画書 5-5 の表と runbook §1 の表は同じ値・同じ並び（runbook 側は TC-19 で検証） |
| 2 | 同じ画面で `main` のルールを開き、5-5 の表の main 列と見比べる | No.1 と同じ項目がすべてオンで、Restrict の一覧に `oshui0404` だけが表示されている | Human | | AC-2・AC-5 |
| 3 | 設定後、bot で `gh pr view 298 --json reviewDecision,isDraft` を実行する | `reviewDecision` が `REVIEW_REQUIRED`（設定前の実測は空文字） | Claude | | AC-2（承認要件が付いたこと）。PR #298 のマージ前は develop に CODEOWNERS が無いため、No.3〜No.5 は「承認 1 件の要件」の確認であり、Code Owners の効き目は No.7 で確認する（runbook §1.5「設定変更直後の develop」） |
| 4 | /close で PR #298 を Ready にした後、`bash scripts/claude/pr-base-sync.sh final` を実行し、続けて `gh pr view 298 --json reviewDecision,mergeStateStatus` を実行する | pr-base-sync が exit 0（「CI 全グリーン（BLOCKED＝Approve 待ち等）」）。`reviewDecision=REVIEW_REQUIRED`・`mergeStateStatus=BLOCKED` | Claude | | AC-2・AC-7 |
| 5 | ユーザーが PR #298 の Files changed → Review changes → **Approve** を押す。その後、bot で `gh pr view 298 --json reviewDecision,mergeStateStatus` を実行する | `reviewDecision=APPROVED`。GitHub の PR 画面で、ユーザーには「Merge pull request」ボタンが押せる状態で表示される | Human（承認）＋ Claude（確認） | | AC-3 |
| 6 | No.5 の直後。(1) bot で `gh pr view 298 --json reviewDecision,mergeStateStatus,headRefOid,reviews` を実行し、`reviewDecision=APPROVED`・`mergeStateStatus` が `BEHIND`/`DIRTY` でない・承認（reviews の最新 APPROVED の commit）が `headRefOid` と同じことを確かめる。(2) **ユーザーの了承を得てから** bot で `gh pr merge 298 --merge` を実行する | (1) の前提がすべて成り立つ。(2) コマンドが失敗し、エラー文に push 権限の不足（`not authorized to push` 等）が示される。`gh pr view 298 --json state` が `OPEN` のまま | Claude | | AC-5（bot はマージできない）。(1) は push 制限以外の理由（BEHIND・承認取り消し等）で失敗して合格と誤判定するのを防ぐ前提（adversarial 20261017 第1周 Medium 対応）。(1) が成り立たない場合は (2) を行わず、状態を整えてからやり直す。エラー文が push 権限の不足でない場合は不合格として No.2 の設定を見直す。万一成功した場合は承認済みの内容がマージされるだけで実害は無いが、push 制限が効いていないため No.2 を見直す。確認後、ユーザーがマージする |
| 7 | **マージ後**。ユーザーが develop 宛てに、1 行のファイル変更を含む確認用 PR を作る（例: ブランチ `check/I178-codeowners` で `check_codeowners.txt` を追加）。**ユーザーの了承を得てから** bot で `gh pr review <PR番号> --approve` を実行し、`gh pr view <PR番号> --json reviewDecision,mergeStateStatus,files` を実行する。確認後、`gh pr close <PR番号>` で閉じる | `files` が 1 件以上。bot の承認後も `reviewDecision=REVIEW_REQUIRED`・`mergeStateStatus=BLOCKED` のまま。PR はマージせずに close される | Human（PR 作成）＋ Claude（承認・確認・close） | | AC-2（develop の Code Owners の効き目）・AC-4。Code Owners の要件はファイル変更を含む PR にだけ働くため、空コミットの PR では正しく設定していても bot の承認で `APPROVED` になり判定を誤る（adversarial 20261017 第1周 Medium 対応）。bot による承認の記録が GitHub に残ることは grill-me で了承済み。CODEOWNERS が develop に入っている必要があるためマージ後に行う（TC-17 も同時に実行する） |
