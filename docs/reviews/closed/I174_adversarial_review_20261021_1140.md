# I174 敵対的レビュー（/code-review 20261021_0905 の後・第 3 周＝最終周）

- 対象: HEAD f50eac1（第 2 周の修正 `I174_adversarial_review_20261021_1129.md` の後）
- 周回: 第 3 周（3 エージェント並列・各 20 分の時間上限・実測 3〜10 分）。この /code-review の累計エージェント数 9
- KNOWN_FINDINGS: 過去の `I174_adversarial_review_*.md` の全 findings・計画 0-11〜0-14 の先送り一覧・fix テストレビュー 2 件の指摘

## 観点と結果

| 観点 | NEW_CRITICAL | NEW_HIGH | 備考 |
|------|------|------|------|
| 1. ロジック回避・実機 repro | 0 | 3 | Low 2 |
| 2. テストの false-green・tautology | 0 | 1 | Low 2 |
| 3. 要件・脅威モデルの網羅漏れ | 0 | 1 | Low 2（High は観点 1 の #1 と同じ型） |

## findings（この周では修正していない）

| # | 重大度 | 観点 | 指摘 | 証跡の要点 |
|---|------|------|------|------|
| 1 | High | ロジック・要件 | 第 2 周 #6（`( … )`・popd の無いコマンドは cd の先だけを見る）で、bash が元の場所に戻る／留まる cd を読めなくなった: `cd -`・`cd ~-`・`cd "$OLDPWD"`・`cd -- -`（元の場所へ戻る）、`cd nosuchdir; git …`（失敗して留まる）、`cd "$X" && git …`（未設定なら留まる）。未コミット変更の消失・develop への push が素通し（d753d25 ではすべて 2＝第 2 周の修正による後退） | `cd sub && ls && cd - && git checkout -- f.txt` を実行すると変更が消えた。`cd ../r && git status && cd - && git push origin HEAD` で remote に develop ができた |
| 2 | High | ロジック | 第 2 周 #5（`--` 無しの checkout は、変更ファイルの一覧以外の `$(…)` なら切り替えとして通す）で、`git checkout "$(git rev-parse --show-toplevel)"`（全体を戻す）・`git checkout $(git rev-parse --show-toplevel)/f.txt`・`git checkout $(git grep -l <語>)` が素通し（後退） | 実行すると「Updated 1 path from the index」で変更が消えた |
| 3 | High | ロジック | `cd "$(git rev-parse --show-toplevel)/sub" && git checkout -- s.txt`・`cd "$(…)" && cd sub && …`・`cd $D && …` が素通し（`_CD_HERE_RE` は最上位そのものの形だけ・読めない場所の判定は「変更なし」になる。第 2 周より前からある） | 実行すると sub/s.txt の変更が消えた |
| 4 | High | テスト | `checkout-index` の `-a`/`--all` を全体として扱う判定を外してもどのゲートも落ちない（`git checkout-index -f -a` が 2→0） | 複製 M1 で全ゲート合格 |
| 5 | Low | ロジック | パイプ・`&` の中の cd も後ろに引き継ぐ（`cd sub \| true; git checkout -- f.txt` が 0） | 不自然な書き方 |
| 6 | Low | ロジック（止めすぎ） | `git mv -f <x> <ディレクトリ>/` がディレクトリ内の関係ない変更で止まる | — |
| 7 | Low | テスト・止めすぎ | `read-tree -u -m` は変更を消さないのに止める。判定を外しても落ちない | 実機で中身は DIRTY のまま |
| 8 | Low | テスト | `_git_revert_target_on_dirty` の `_CD_HERE_RE` の分岐は `_analyze` 側が受け持っていて効き目がない | 複製 M7 で差なし |
| 9 | Low | 要件 | danger-ops.md に push.default の upstream / tracking・checkout-index / read-tree / mv が書かれていない | — |
| 10 | Low | 要件（止めすぎ・推定） | `_scoped` が引用符の中の `(`（`grep "(I174)"`）でも「範囲が分からない」に倒れる | コードを読んだだけ |

## 決定論ゲート

f50eac1 時点で gates=38 failed=0（第 2 周の記録のとおり）。この周は修正していない。

## 判定

上限（3 周・エージェント 9 / 15）に到達し、新規 High 4 件が残った。**上限到達・未収束**。自動で OK にせず、ユーザーへエスカレーションする。

傾向: この /code-review の 3 周の High 11 件のうち 8 件が「git がどこで実行されるか（cd・`( … )`・`cd -`・読めない場所）」と「対象が読めるか（`$(…)`・xargs・find・中かっこ）」の読み違いで、第 1 周で止める側に倒す → 第 2 周で止めすぎを緩める → 第 3 周で緩めすぎ、と往復している。bash の実行場所を静的に正確に再現することはできないため、指摘ごとの修正（3 回目の fix-loop の案 B）では収束しない。

VERDICT: HIGH
