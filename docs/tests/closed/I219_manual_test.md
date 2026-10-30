# I219 手動テスト: セッションの開始時の primary の早送りを裏で動かし、打ち切りで index.lock を残さない

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M-01 | （マージ前）このブランチで `claude -p --setting-sources user --settings .claude/settings.json "開始時の文脈にある primary: で始まる行をそのまま 1 行だけ出して"` を流し、かかった時間を測る | 「primary: まだ結果がありません（裏でそろえています）」か「primary: 前回 …」が出る。フックの所要が 5 秒以内（`time` でフックを直接動かして測る）。primary に `.git/index.lock` が無い | Claude | OK（2026-10-30・test-gate・レビュー済みの HEAD）: 前回の結果を消して開始時のフックを動かすと 2.2 秒で戻り「primary: まだ結果がありません（裏でそろえています）」。primary に `.git/index.lock` は無い。（実装の最後にも `claude -p` の新しいセッションで確かめ、セッションの終了の後も裏の処理が殺されず実際の primary で結果を書いた） | 実際の primary は今 develop で最新なので、裏の処理の結果は「最新です」になる見込み |
| M-02 | （マージ前）M-01 の 1 分後に同じことをもう一度 | 「primary: 前回（<時刻>）: 最新です」が出る。primary に `.git/index.lock` が無い | Claude | OK（2026-10-30・test-gate）: 裏の処理が結果を書いた後にフックを動かすと 2.5 秒で戻り「primary: 前回（10-30 09:02）: 最新です」。primary に `.git/index.lock` は無い（実装の最後の `claude -p` の 2 回目でも同じ形の行が出た） | 裏の処理が実際の primary で動き、結果を書いたことを確かめる |
| M-03 | 最初のコミットで書いた `docs/tests/closed/I200_manual_test.md` の M-04b を読む | NG の結果・原因（status の遅さ・SIGKILL のロック）・I219 で直すことが書かれている | Claude | OK（2026-10-30）: `docs/tests/closed/I200_manual_test.md` の M-04b に、NG の結果・原因（status が 4.7 秒で打ち切り 5 秒に当たった・SIGKILL でロックが残った）・I219 で直すことが書かれている（このブランチの 2 つ目のコミット） | |
| M-04 | （マージ後）マージで develop が進んだ状態で、どれかのワークツリーで新しいセッションを始め、1 分後にもう一度始める | 2 回目の開始時の文脈に「primary: 前回（…）: develop を origin/develop へ早送りしました（…）」が出て、`git worktree list` の primary の行の HEAD が `git rev-parse origin/develop` と同じ。primary に `.git/index.lock` が無い | Claude | | I200 の M-04b の確かめ直し |
