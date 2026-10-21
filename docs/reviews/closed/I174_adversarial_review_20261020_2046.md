# I174 敵対的レビュー（/code-review 20261019_0037 の後・第 3 周＝最終周）

- 対象: HEAD dd941c5（第 2 周の修正 `I174_adversarial_review_20261020_2020.md` の後）
- 周回: 第 3 周（3 エージェント並列・各 20 分の時間上限・実測 3〜24 分）。この /code-review の累計エージェント数 9
- KNOWN_FINDINGS: 過去の `I174_adversarial_review_*.md` の全 findings・計画 0-11〜0-13 の先送り一覧

## 観点と結果

| 観点 | NEW_CRITICAL | NEW_HIGH | 備考 |
|------|------|------|------|
| 1. ロジック回避・実機 repro | 0 | 1 | Medium 3 |
| 2. テストの false-green・tautology | 0 | 1 | Medium 1・Low 1 |
| 3. 要件・脅威モデルの網羅漏れ | 0 | 1 | Medium 4・Low 1 |

## findings（この周では修正していない）

| # | 重大度 | 観点 | 指摘 | 証跡の要点 |
|---|------|------|------|------|
| 1 | High | 要件 | 未コミット変更があるファイルの `git checkout/restore <file>` の停止が、作業場所を変える形で効かない（`git -C . checkout -- f`・`git -C sub restore f`・`cd sub && git checkout -- f`・`pushd`・`bash -c 'cd … && git restore …'`・`git --work-tree=. checkout`）。`_git_revert_target_on_dirty` が git の直後の語しか見ず、`_worktree_dirty` が見張りの作業ディレクトリで調べる（第 2 周 #2 の push と同型） | 一時リポジトリで `git -C . checkout -- sub/f.txt` が guard=0、実行すると未コミットの追記が消えた。本リポジトリの `docs/issues/open/I157.md` でも `git -C . checkout -- …`→0 |
| 2 | High | ロジック | 宛先を `$(…)` で決める push は最上位なら確認だが、`bash -lc '…'`・`sh -ec '…'`・`bash <<'EOF' … EOF`・`timeout 60 bash -lc …` の中では素通し。(ii) が `-c` の完全一致しか見ず、`_cmd_danger` の入れ子 push 判定が (i) の「宛先を静的に決められない」判定を持たない | develop の worktree で `bash -lc 'git push -q -u origin $(git branch --show-current)'` を実行 → 一時 remote に develop ができた |
| 3 | High | テスト | `_cmd_danger` の `git.exe` 対応を外してもどのゲートも落ちない（`git.exe reset --hard`・`git.exe clean -fdx` が 2→0 になる） | 複製 M4 で 6 ゲートすべて rc=0 |
| 4 | Medium | ロジック | cd の引き継ぎが `len(toks)==2` だけ（`cd -- X`・`cd -P X` は読まない）。`--git-dir`・`--work-tree`・`GIT_DIR=` も今のブランチの判定先に反映しない | `( cd -- ../devwt && git push -q origin )` で remote に develop |
| 5 | Medium | ロジック | parallel / xargs の値を取るオプション一覧が狭い（parallel `-a`・`--arg-file`・`--halt`・`--colsep`・`-I`、xargs `--arg-file`）。安全網も同じ語で止まる | `xargs --arg-file list.txt rm -rf` で対象が消えた |
| 6 | Medium | ロジック（誤停止） | 第 2 周 #1 の (iii) 拡大で、`git diff --name-only \| xargs grep -n "git push"` などの読み取りが確認になる。`bash -c 'grep -rn "git push" docs'` も (ii) で確認 | 4 形すべて ASK |
| 7 | Medium | 要件 | ステージ済みだけの変更（` M` でなく `M `）を変更ありと判定しない。`git checkout HEAD -- f`・`git restore -s HEAD -SW f` でステージ済みの変更が消える | 実行で STAGED が消えた |
| 8 | Medium | 要件 | `git -c remote.origin.push=HEAD:main push origin`、2 回に分けた `git config remote.origin.push HEAD:main`／`git config push.default matching` → `git push` が素通し | remote に main ができた |
| 9 | Medium | 要件 | `git restore/checkout --pathspec-from-file=…`・`git rm -rf <dir>` が未コミットの変更を消すのに素通し | 実行で変更が消えた |
| 10 | Medium | 要件 | `rm -r <dir>`（-f なし・端末なしで確認が出ない）・`find … -exec rm {} +`・`find … \| xargs rm` が素通し（danger-ops の「rm -rf / find -delete」と同じ結果） | guard=0 |
| 11 | Medium | テスト | container の S28・S29 が作業ツリーの `backend/.env` に依存（第 2 周 #8 の S19 と同型） | `.env` 無しの複製で fail=2 |
| 12 | Low | 要件 | `git -c clean.requireForce=false clean -d` が -f なしで消せるのに素通し | 実行で追跡外ファイルが消えた |
| 13 | Low | テスト | cd 引き継ぎの `pushd` と `~` の分岐を通るテストが無い | grep で 0 件 |

## 決定論ゲート

dd941c5 時点で gates=38 failed=0（第 2 周の記録のとおり）。この周は修正していない。

## 判定

上限（3 周・エージェント 9 / 15）に到達し、新規 High 3 件が残った。**上限到達・未収束**。自動で OK にせず、ユーザーへエスカレーションする。

傾向: 第 2 周・第 3 周の High は「コマンドがどこで実行されるか（`-C`・`cd`・`--work-tree`）」「入れ子のシェルの中でも最上位と同じ判定が当たるか」の 2 つに集中している。push・checkout/restore・clean・reset の判定が、それぞれ別の関数で、最上位の文字列と単純コマンドの 2 経路に分かれて書かれており、一方を直すと他方が残る（第 2 周 #2 → 第 3 周 #1・#2）。

VERDICT: HIGH
