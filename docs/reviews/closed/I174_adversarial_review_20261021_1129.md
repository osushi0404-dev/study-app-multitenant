# I174 敵対的レビュー（/code-review 20261021_0905 の後・第 2 周）

- 対象: HEAD d753d25（第 1 周の修正 `I174_adversarial_review_20261021_0938.md` の後）
- 周回: 第 2 周（3 エージェント並列・各 20 分の時間上限）。この /code-review の累計エージェント数 6
- KNOWN_FINDINGS: 過去の `I174_adversarial_review_*.md` の全 findings・計画 0-11〜0-14 の先送り一覧・fix テストレビュー 2 件の指摘

## 観点と結果

| 観点 | NEW_CRITICAL | NEW_HIGH | 備考 |
|------|------|------|------|
| 1. ロジック回避・実機 repro | 0 | 3 | Medium 1・Low 1 |
| 2. テストの false-green・tautology | 0 | 1 | Medium 1 |
| 3. 要件・脅威モデルの網羅漏れ | 0 | 0 | Medium 2（止めすぎ）・Low 1 |

## findings と対応

| # | 重大度 | 観点 | 指摘 | 対応 |
|---|------|------|------|------|
| 1 | High | ロジック | 第 1 周 #11（止めすぎの解消）で `push.default` を matching だけにした結果、`upstream`／`tracking` が素通し。origin/develop から作ったブランチ（worktree.md の手順どおり）では develop に push された（実機） | `_risky_git_cfg`: `push.default` は matching・upstream・tracking を停止。テスト XP61〜XP63 |
| 2 | High | ロジック | `find … -exec git checkout -- {} +`・`-execdir … git restore {}` が素通し（find 由来を「対象が読めない」と扱っていなかった） | `_cmd_danger` が find 由来（via_find）も opaque として渡す。テスト G57（`find -exec git log` は G59 で 0） |
| 3 | High | ロジック | 中かっこで並べたファイル名（`git checkout -- sub/{b,c}.py`）が素通し（文字どおりの名前で調べていた） | 中かっこ展開（`{a,b}`・`{1..3}`）を含む対象は「対象が読めない」扱い。テスト G58 |
| 4 | High | テスト | `_risky_git_cfg` の `+`（強制 push になる設定）の判定を外してもどのゲートも落ちない | XP69〜XP71 を追加。外した複製で XP69・XP70 が落ちることを確認 |
| 5 | Medium | 要件（止めすぎ） | 第 1 周 #1 の「対象が読めない」判定が、`git checkout "$BR"`・`--detach "$SHA"`・`-t "origin/$B"` などの切り替えまで止めていた（作業ツリーに変更が 1 つでもあると停止） | `--` が無く、変更ファイルの一覧（diff・ls-files・status）を渡していない checkout は、対象が読めなくても切り替えとして通す（`git checkout $(git diff --name-only)` は止める）。テスト G48〜G50 |
| 6 | Medium | 要件（止めすぎ） | 第 1 周 #2 の「通った場所すべてを候補にする」処理が、`( … )` の無い `cd X && git checkout -- …` にも効き、別のリポジトリでの作業が元の場所の変更で止まっていた。安全網も cd を引き継がずに止めていた | `_scoped`（`( … )`・popd があるか）で分ける。無ければ cd の先だけを見る（最上位・入れ子・安全網の 3 か所）。読めない cd の先でも、今の場所を指す形（`$(git rev-parse --show-toplevel)`・`$(pwd)`・`$PWD`）は元の場所も候補に残す。テスト G51・G52・G60・G61。XP17（`cd <develop> && cd .. && git push`）は 0 に戻した |
| 7 | Medium | ロジック | `git push origin :`（同名の全ブランチ）・`remote.origin.push=:`・`git config remote.origin.push :` が素通し（実機で develop が更新された） | `_push_protected_target` と `_risky_git_cfg` で `:` を保護ブランチへの push として扱う。テスト XP64・XP65 |
| 8 | Medium | テスト | G46・G47（`-qb`）はまとめ書きの判定を外しても通る（新しいブランチ名が変数のときしか効かない） | G62（変更のある作業場所での `git checkout -qb $BR` は 0）を追加 |
| 9 | Low | 要件 | `git checkout-index -f`・`git read-tree -u --reset`・`git mv -f <x> <変更ありのファイル>` で変更が消える | `_git_revert_target_on_dirty` の対象に追加。テスト G53〜G56 |
| 10 | Low | ロジック | `-c clean.requireForce=`（空の値は偽）・`-c remote.origin.mirror`（= を省くと真）・`git config -f <file> remote.origin.push …`（`-f` の値を名前と読み違え）が素通し | 空の値を偽に・値を省いた `-c` は真として判定・`git config` の値を取るオプションを飛ばす。テスト H43〜H45・XP66〜XP68 |

## 決定論ゲート（`docs/tests/open/I174_auto_test.md`・38 行）

gates=38 failed=0。container 769・push 160・checkout 66・worktree 30・matrix 301・作業記録の再判定 新しく確認・停止 0 件・差分テスト 3,984 件 見逃し 0 余計な停止 0。

## 判定

新規 High 4 件（#1〜#4・すべて修正済み）。#1 は第 1 周の止めすぎの解消で入った後退、#5・#6 は第 1 周の止める側に倒した修正の止めすぎ。第 3 周（最終周）で修正を含めて再度反証する。

VERDICT: HIGH
