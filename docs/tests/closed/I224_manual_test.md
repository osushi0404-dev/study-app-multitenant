<!--
## 手動テスト品質基準
- 期待結果は「正常に〜できる」ではなく具体的な画面表示・動作で記載すること
- 実施者: docs/runbooks/plan-writing-rules.md「実施者の区別」で決める（原則 Claude。Human の行は備考に「試した手段: …」が必須。scripts/claude/check-manual-test-executor.sh が確かめる）
-->

# I224 手動テスト: GitHub への書き込み（イシューの書き換え・コメント・push）の回数を絞り、短い間に集中しないようにする

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M-01 | I224 自身のブランチへの push の回数を数える: `git reflog show --date=iso refs/remotes/origin/feature/I224-batch-github-writes`（test-gate で数え、close の後にもう一度数えて retro・close の報告に書く） | implement の後（新しいスキルで動く review-gate〜close）の `update by push` が 3 回以内（review-gate の前 1・fix-loop のやり直しごとに +1・close 1・BEHIND のときの取り込み +1）。review-gate の CI 待ちが `CI_WAIT: OK` で通っている（push を前提にする確認が壊れていない）。PR へのコメントの回数（`gh pr view 420 --json comments,reviews` の件数）も並べて記録する | Claude | OK（2026-11-07 test-gate の時点・05c7ae2f）: push は計 3 回（22:12 plan-issue の ①・22:15 古いスキルでの計画文書・22:28 review-gate の ②）。implement より後は review-gate の 1 回だけで、`CI_WAIT: OK`。PR へのコメントは 0・レビューのコメントは 2（計画レビュー・コードレビュー）。close の ③ の後の最終の数は close の報告に書く（見込み: 計 4 回・implement より後は 2 回） | plan-issue〜implement は古いスキルで動くので数に入れない（区切りは implement の結線のコミット） |
| M-02 | 新しいスキルを読み、段階の終わりの指示を確かめる: `review-gate` の「## 1.」の最初に `git push`、`test-gate`・`retro` の結線に push が無い、`close` の手順 3 のコミットに `STAGE_DONE: close NEXT: merge` が入る、`proceed` の `merge` の行が依頼の前に `pr-base-sync.sh final` を流す | 4 点とも計画 4-2 のとおり | Claude | OK（2026-11-07・05c7ae2f）: `review-gate` 16〜19 行に送る手順と `git push`。`test-gate`・`retro` の「push」は「push しない」の参照だけ。`close` 126 行の手順 3 のコミットに `STAGE_DONE: close NEXT: merge`。`proceed` 35 行の `merge` が `pr-base-sync.sh final` を流す | TC-02 の P1・P2 で数は機械的に確かめる。ここは流れとして読めるか |

結論: OK
