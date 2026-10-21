# I174 敵対的レビュー（/code-review 20261021_1559 の後・第 3 周）

- 対象: HEAD 02c0f14（第 2 周の修正）。範囲は `git show 02c0f14` とその直接の影響
- 基本レビュー: `docs/reviews/I174_code_review_20261021_1559.md`（FINAL_VERDICT: OK・RISK: YES）
- 周回: 第 3 周（最後。3 エージェント並列・各 15 分の時間上限・実測 3〜4 分）

## 観点と結果

| 観点 | NEW_CRITICAL | NEW_HIGH | 備考 |
|------|------|------|------|
| 1. ロジック回避・実機 repro | 0 | 1 | Medium 1 |
| 2. テストの false-green・tautology | 0 | 1 | Medium 2・Low 1 |
| 3. 要件・脅威モデルの網羅漏れ | 0 | 1 | Medium 2 |

## findings と対応

| # | 重大度 | 観点 | 指摘 | 対応 |
|---|------|------|------|------|
| 1 | High | ロジック | 第 2 周で後戻り: cd の直後の区切りが `\|`（`cd sub \| true && git checkout -- f.txt`）でも cd 先で判定し素通し。bash ではパイプの中の cd はサブシェルで元の場所は変わらず、変更が消える（実測。02c0f14^ では確認） | cd の直後の区切りは `&&`（最後の cd なら無しも可）だけ。後ろの cd の直前も `&&`／`;` だけ（`cd a && ls \| cd b`）。テスト G122・G123 |
| 2 | High | テスト | GIT_DIR の正規表現が単独の代入しか拾わず、`X=1 GIT_DIR=<develop>; export GIT_DIR; git push` が素通し（実測で develop を push） | 精密化をやめ、区切りごとの語に `GIT_DIR=`／`GIT_WORK_TREE=` の代入があれば一意でない（`_other_chdir`）。テスト XP91・XP92 |
| 3 | High | 要件 | 第 2 周の「最初の cd より後ろの `;` の後の git は一意でない」が、普段のコミット＋push（`cd <repo> && git add … && git commit … \| grep …; git push -q`）に当たり、作業記録 13 件が 0→確認（I174 の目的と逆） | 対象を「飛ばされうる cd（同じつながりで前に cd 以外のコマンドか `\|\|` がある）」があるときに絞る。行頭の cd は対象外（実在する場所への cd の失敗は残余リスク）。作業記録で 02c0f14^ と比べた判定の変化 13→0 件。テスト XP94 |
| 4 | Medium | ロジック | `env -Cwt`・`env -vC wt`・`sudo -Dsub` を見落とす。さらに `env -vC X git …` はオプションの値を読み違え、git そのものを見落とす | `_other_chdir` で短いオプションのまとめ・くっつけを拾う。`_skip_opts` がまとめた短いオプションの値を getopt と同じに読み飛ばす（`_short_bundle_takes_next`）。テスト G124〜G126・XP93（`env -vC <develop> git push origin main` は停止） |
| 5 | Medium | 要件 | `_OTHER_CHDIR_RE` を文字列全体に当てるため、コミットメッセージや `rg env -C 3` に反応し push が確認になる | 区切りごとの語で、前置き（env・sudo・nohup など）の位置だけを見る。テスト XP95・XP96 |
| 6 | Medium | テスト | 「最初の cd より前は `&&`／`;` だけ」を外しても全件通る | G120（`true \| cd other`）・G121（`true \|\| cd other`） |
| 7 | Medium | テスト | 単独の `GIT_DIR=…;` の枝を外しても全件通る | #2 で枝を一本化。XP92 |
| 8 | Medium | 要件 | `env -C`・`sudo -D` の先を「いちばんありそうな場所」として計算せず、保護ブランチへの宛先なし push が停止でなく確認 | 受け入れ（確認は残り素通しにはならない）。計画 0-16 の残余に記録 |
| 9 | Low | テスト | `len(cmds) < len(segs)` を外しても結果が変わる入力を作れなかった | 受け入れ（fail-safe の防御） |

偽合格の防止テスト FG-M（変数の場所の push）は、新しい `_other_chdir` も同じ形を確認にするため、複製でこれも外すよう更新した。

## 決定論ゲート

gates=38 failed=0（container 769・settings 12・push 185・checkout 137・worktree 30・adversarial_trigger 40・matrix 301・作業記録の再判定 新しく確認・停止 0・差分テスト 3,984 件 見逃し 0）。作業記録の Bash コマンドを 02c0f14^（第 2 周の前）と比べた判定の変化 0 件。

## 判定

新規 High 3 件（修正済み）。3 周の上限に到達。

VERDICT: HIGH
