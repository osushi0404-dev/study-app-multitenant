# I174 敵対的レビュー（/code-review 20261021_0905 の後・第 1 周）

- 対象: HEAD 84c0a81（3 回目の fix-loop〔計画 0-14・0d521f1〕と計画レビューの反映の後）
- 基本レビュー: `docs/reviews/I174_code_review_20261021_0905.md`（FINAL_VERDICT: OK・RISK: YES）
- 周回: 第 1 周（3 エージェント並列・各 20 分の時間上限・実測 5〜20 分）
- KNOWN_FINDINGS: 過去の `I174_adversarial_review_*.md` の全 findings・計画 0-11〜0-14 の先送り一覧・fix テストレビュー 2 件の指摘

## 観点と結果

| 観点 | NEW_CRITICAL | NEW_HIGH | 備考 |
|------|------|------|------|
| 1. ロジック回避・実機 repro | 0 | 2 | Medium 2 |
| 2. テストの false-green・tautology | 0 | 2 | Medium 1・Low 1 |
| 3. 要件・脅威モデルの網羅漏れ | 0 | 1 | Medium 1・Low 3（High は観点 1 の #1 と同じ） |

## findings と対応

| # | 重大度 | 観点 | 指摘 | 対応 |
|---|------|------|------|------|
| 1 | High | ロジック・要件 | 戻す対象を `$(…)`・バッククォート・変数・xargs で渡す checkout / restore（`git diff --name-only \| xargs git checkout --`・`git restore $(git diff --name-only)`・`for f in $(…); do git checkout -- "$f"; done`）が素通しで、実行すると変更が消えた | `_git_revert_target_on_dirty(cmd, opaque, cds)`: 対象が読めない（`$`・`` ` ``・`__SUBST_`・xargs 由来）なら、その場所（`:/`）に変更があれば止める。`_cmd_danger` は xargs 由来を opaque として渡す。テスト G32〜G34 |
| 2 | High | ロジック | 入れ子の中の `( … )` の cd を後ろに引き継ぎ（元の場所に戻ることを再現しない）、別の場所を調べて素通し（`bash -c "(cd backend && ls) && git checkout -- f"`・`pushd; popd`・ヒアドキュメント）。逆向きの誤停止もあった | 読み解いた列からはサブシェルの範囲が分からないので、**通った場所（cd の前・途中・後）をすべて候補にし、どこかで当たれば止める**（`_analyze` の `cds`・`_cmd_danger` は候補ごとに判定）。テスト G35・G36・XP60。止める側に倒した影響で XP17（develop の worktree を通った後の push）は 0→2 |
| 3 | High | テスト | `_revert_from_commit` のまとめ書き（`-SW`・`-WS`）の判定を外してもどのゲートも落ちない（G25 は `-s` で合格していた） | G41・G42（`-s` なしの `-SW`・`-WS`）を追加。外した複製で 2 件とも落ちることを確認 |
| 4 | High | テスト | `_expand` の `env` 分岐の `_with_genv` を外してもどのゲートも落ちない（`env GIT_DIR=… GIT_WORK_TREE=… git checkout -- <dirty>` を止める唯一の判定） | 別のリポジトリを指す G43〜G45（前置き・`env`・`bash -c 'env …'`）を追加。外した複製で G44・G45 が落ちることを確認 |
| 5 | Medium | ロジック | `git checkout HEAD <path>`（`--` なし）がステージ済みの変更を数えない | `_revert_from_commit`: `--` が無くても位置引数が 2 つ以上なら先頭はコミット。テスト G37・G38（`git checkout develop` は G39 で 0） |
| 6 | Medium | ロジック | xargs の `-i` は値を付けて書くとき（`-i{}`）だけ値を取るのに次の語を飛ばしていた（`xargs -i rm {}` が素通し） | `_XARGS_VALUE` から `-i` を外す。テスト H40 |
| 7 | Medium | 要件 | `remote.<名前>.mirror=true`（全参照の強制更新と削除）を判定しない | `_risky_git_cfg`: `remote.*.mirror` が真なら停止（`-c` と `git config` の両方）。テスト XP55・XP56 |
| 8 | Medium | テスト | G31 は `GIT_WORK_TREE=.` が見張りの作業ディレクトリと同じで、env の経路を測っていない | 別のリポジトリを指す G43〜G45 で測る |
| 9 | Low | 要件 | `clean.requireForce` の `0`・`no`・`off`・`git config clean.requireForce false` を判定しない | `_risky_git_cfg` で偽の値すべて・`git config` も停止。テスト H41・H42 |
| 10 | Low | 要件 | 0-14 で足した危険操作が danger-ops.md に書かれていない | danger-ops.md の「例」の Git・Files と、見張りの 2. を更新 |
| 11 | Low | 要件 | push の設定を値を見ずに止めていた（`push.default simple`・feature 宛ての `remote.origin.push` も停止） | `_risky_git_cfg`: `push.default` は matching、`remote.*.push` は保護ブランチ・`+`・glob 宛てのときだけ停止。テスト XP57〜XP59（0） |
| 12 | Low | テスト | parallel の区切り（`::::`・`:::+`）の判定を外しても落ちない（止めすぎる方向にしか効かない） | 見送り（危険な見逃しにはならない） |

### 作業記録の再判定で見つかった余計な停止（修正の途中）
- #1 の最初の実装では、場所が変数の cd（`cd $S`）の後の `git checkout -qb feat`（ブランチの作成）を「対象が読めない」として、手元のリポジトリ全体の変更で止めていた（3 件）。`-qb` のまとめ書きをブランチ作成と読むようにし、場所が変数なだけ（対象の名前は読める）のときは候補の場所で名前を調べる形に直した（新しく確認・停止 0 件に戻った）。テスト G46・G47。

## 決定論ゲート（`docs/tests/open/I174_auto_test.md`・38 行）

gates=38 failed=0。container 766・push 149・checkout 51・worktree 30・matrix 301・作業記録の再判定 新しく確認・停止 0 件・差分テスト 3,984 件 見逃し 0 余計な停止 0。

## 判定

新規 High 4 件（#1〜#4・すべて修正済み）。第 2 周で修正を含めて再度反証する。

#2 は第 2・3 周（10-20）と同じ「どこで実行されるか」の型で、今回は止める側に倒して閉じた。案 A（判定の一本化）を見送った影響がまだ続いていることを記録しておく。

VERDICT: HIGH
