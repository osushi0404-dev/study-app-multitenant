# I174 敵対的レビュー記録（fix-loop 後のやり直し・第 3 周・上限到達）

- 対象: ブランチ `feature/I174-guard-based-permission-review`（head 47456c4・第 2 周の修正の後）
- 前周: `docs/reviews/I174_adversarial_review_20261017_1443.md`（第 1 周）・`_20261017_1930.md`（第 2 周）
- 周回: やり直しの第 3 周（上限）・エージェント 4（固定 3 観点＋動的 1 観点「余計な確認・誤ブロック」）。各エージェントに 30 分の上限を付けた（実測 4〜7 分）

## 集計
- NEW_CRITICAL: 1 ／ NEW_HIGH: 4（ロジック回避 Critical 1・High 2、余計な確認 High 1、要件 High 1、テスト 0）
- 指摘はすべてオーケストレーターが guard に流して再現を確かめ、修正した

## findings（Critical / High）
| # | 重大度 | 内容 | 観点 | 修正 |
|---|---|---|---|---|
| 1 | Critical | `if X; then rm -rf x; fi`・`while …; do git reset --hard …; done`・`for …; do git clean -fdx …; done` の本体（`then` / `do` の後ろ）を判定しない。予約語が先頭のコマンドとして扱われていた（I174 の前からの穴を含む） | ロジック回避 | 予約語（if・then・elif・else・while・until・do）を包むコマンドとして外す（A164〜A169・H13〜H15・S78・S79） |
| 2 | High | 第 2 周で dd / shred / mkfs をコマンド名の判定にした結果、上の制御構文の中と `parallel` / `strace` 経由が素通り（後退） | ロジック回避 | #1 の修正と、`parallel`・`strace`・`ltrace` を包むコマンドに追加（H14〜H16）。`ssh` / `kubectl exec` の先は残余リスク |
| 3 | High | `.env` の glob の照合が固定の候補（.env・.env.local・.env.prod）だけで、実在する `e2e/.env.e2e`・`frontend/.env.development` を `.env.e2*` 等で読むと素通り（後退） | ロジック回避 | glob の記号の前までが `.env` の頭か `.env` で始まるかで判定（S75・S76）。`secrets/` の下の glob も（S77） |
| 4 | High | 第 2 周の `.env` の glob の判定が広すぎ、`grep … docs/reviews/*`・`head docs/runbooks/*`・git の pathspec・Python の `'*'`・`ALLOWED_HOSTS=['*']`・`glob.glob('docs/*')` が「秘密情報」の確認になった（作業記録で +23 件） | 余計な確認 | シェルの glob は `.` で始まるものだけを `.env` 系と見る・鍵は拡張子付きの glob だけ・Python の文字列は glob の記号を含むものを対象外（P93〜P99・S74） |
| 5 | High | `python3 - < f.py`・`python3 /dev/stdin < f.py`・`python3 -q - x < f.py` で、流し込むファイルの中身を判定しない（第 2 周の修正はパイプにしか効いていなかった） | 要件 | `<` のファイルを読んで判定（F25〜F28） |

## 同時に直した Low
- `cp` / `mv` で上書きしたファイルの実行のテストが無い → F24 を追加

## 先送り（Medium / Low）
計画書 0-11 の「先送り」に追記（`export -p` 等・パス無しの `dotenv_values()`・`column` 等での `.env`・`'->' &` の結合・テストの覆い隠し 2 件）。

## 承認待ちの実測（余計な確認の観点・作業記録 3,373 件）
| 区分 | 45cdfa5 | 47456c4 |
|---|---|---|
| 確認＋停止 | 150（4.45%） | 190（5.63%） |
47456c4 の増加 +40 件のうち 23 件は #4 の誤判定（今回の修正で解消）、14 件は同じコマンド内で書いたファイルの中身が見えるようになった分（意図どおり）。

## テスト（修正後）
- container 682・checkout 18・worktree 30・push 87・settings 12・adversarial 40（すべて fail=0）
- 修正前（47456c4）の guard で流すと、新しいケースのうち 31 件が狙いどおり失敗（偽合格でない）

## 判断（オーケストレーター）
上限の 3 周に達し、この周で新規 Critical 1・High 4 が出た。すべて修正しテストで確かめたが、修正後の再レビューは行っていない。SKILL 3-2 に従い自動 OK にせず「上限到達」としてユーザーに判断を求める。

VERDICT: HIGH
