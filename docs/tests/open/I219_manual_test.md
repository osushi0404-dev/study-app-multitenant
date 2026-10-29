# I219 手動テスト: セッションの開始時の primary の早送りを裏で動かし、打ち切りで index.lock を残さない

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M-01 | （マージ前）このブランチで `claude -p --setting-sources user --settings .claude/settings.json "開始時の文脈にある primary: で始まる行をそのまま 1 行だけ出して"` を流し、かかった時間を測る | 「primary: まだ結果がありません（裏でそろえています）」か「primary: 前回 …」が出る。フックの所要が 5 秒以内（`time` でフックを直接動かして測る）。primary に `.git/index.lock` が無い | Claude | OK（2026-10-30・実装の最後）: 前回の結果を消してから新しいセッションを始めると「primary: まだ結果がありません（裏でそろえています）」。フックを直接動かした所要は 2.3 秒（5 秒以内）。`claude -p` のセッションが終わった後も裏の処理は殺されず、実際の primary で動いて `~/.cache/claude-primary-sync/` に結果「最新です」を書いた（計画のリスク表の前提が成り立った）。primary に `.git/index.lock` は無い | 実際の primary は今 develop で最新なので、裏の処理の結果は「最新です」になる見込み |
| M-02 | （マージ前）M-01 の 1 分後に同じことをもう一度 | 「primary: 前回（<時刻>）: 最新です」が出る。primary に `.git/index.lock` が無い | Claude | OK（2026-10-30）: 2 回目の新しいセッションの開始時の文脈に「primary: 前回（10-30 08:34）: 最新です」。primary に `.git/index.lock` は無い | 裏の処理が実際の primary で動き、結果を書いたことを確かめる |
| M-03 | 最初のコミットで書いた `docs/tests/closed/I200_manual_test.md` の M-04b を読む | NG の結果・原因（status の遅さ・SIGKILL のロック）・I219 で直すことが書かれている | Claude | | |
| M-04 | （マージ後）マージで develop が進んだ状態で、どれかのワークツリーで新しいセッションを始め、1 分後にもう一度始める | 2 回目の開始時の文脈に「primary: 前回（…）: develop を origin/develop へ早送りしました（…）」が出て、`git worktree list` の primary の行の HEAD が `git rev-parse origin/develop` と同じ。primary に `.git/index.lock` が無い | Claude | | I200 の M-04b の確かめ直し |
