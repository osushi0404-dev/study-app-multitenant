# I174 敵対的レビュー（/code-review 20261019_0037 の後・第 1 周）

- 対象: HEAD 8cd3a6d（a5d95ff の fix-loop〔本物の bash との差分テスト・計画 0-13〕以降）
- 基本レビュー: `docs/reviews/I174_code_review_20261019_0037.md`（FINAL_VERDICT: OK・RISK: YES → ADVERSARIAL_STAGE: REQUIRED）
- 周回: 第 1 周（3 エージェント並列・各 20〜30 分の時間上限を指示）
- KNOWN_FINDINGS: 過去の `I174_adversarial_review_*.md` 6 件の全 findings

## 観点と結果

| 観点 | NEW_CRITICAL | NEW_HIGH | 備考 |
|------|------|------|------|
| 1. ロジック回避・実機 repro | 0 | 1 | High 1・Low 1 |
| 2. テストの false-green・tautology | 0 | 0 | Medium 2・Low 2 |
| 3. 要件・脅威モデルの網羅漏れ | 0 | 0 | Medium 1・Low 1 |

## findings と対応

| # | 重大度 | 観点 | 指摘 | 対応 |
|---|------|------|------|------|
| 1 | High | ロジック | `git branch … \| xargs -n1 git push origin`・`echo main \| xargs git push origin` は、標準入力の語が宛先として後ろに足され main / develop に push しうるのに guard=0（差分テストは git を関数で置き換えるため xargs 経由は測れない） | `_push_is_dynamic` に (iii) を追加: 先頭が `xargs` / `parallel` で `git` `push` を含む push は「宛先が読めない push」として確認（ASK）。`parallel git push origin ::: main develop` は宛先が見えるので停止（2）。テスト XP1〜XP4 |
| 2 | Medium | 要件 | `git push origin +feature/x`・`+HEAD:feature/x`（参照の前の `+` は強制 push）が guard=0 | `_push_has_force` で remote の後ろの位置引数が `+` で始まる・`:+` を含むものを force と判定（停止）。テスト XP5・XP6（2）・XP7（普通の push は 0） |
| 3 | Medium | テスト | 差分テストが「確認（ASK）」も合格に数えるため、停止→確認の格下げを検知できない（複製 m9: 全件 ASK でも exit 0） | `guard_bash_oracle.py`: bash が実行する形は guard=2 だけを合格に（ASK も不合格）。現状の確認止まりは 0 件 |
| 4 | Medium | テスト | guard が無い・読み込めないと python3 の終了コード 2 を「停止」と読み、全件合格になる（`GUARD=存在しないパス` で exit 0） | guard ファイルの存在確認と対照 2 件（`echo ok`→0・`git reset --hard origin/develop`→2）を先に確かめ、外れたら不合格 |
| 5 | Low | テスト | 印を出す関数（STUBS）が狭い（`push -f`・`--force-with-lease`・`+参照`・`HEAD:main`・`rm -fr` など） | STUBS を広げた（push: `-f`・`--force-with-lease`・`+…`・`:main`/`:develop`・`/main`/`/develop`、rm: `-fr`・`-Rf`・`-fR`）。`command git` 等の外部コマンド経由は対象外のまま |
| 6 | Low | テスト | `_danger_reasons` のコメント除去を外した複製（m8）がどのテストでも落ちない（余計な停止=4 は表示だけ） | 差分テストで「bash が実行しない形で guard が 0 以外」（余計な停止）も不合格に。m8 は余計な停止=4 で不合格になることを確認 |
| 7 | Low | ロジック | `$'main\0x'` / `$'main\x00'`: bash は NUL で文字列を切るが `_ansi_c_decode` は残す | 見送り（Claude が普段書く形ではない・脅威モデル「事故」の範囲外）。先送り一覧の候補 |
| 8 | Low | 要件 | danger-ops.md に差分テストと、入れ子の `DANGER_OK=1` が解除にならないことが書かれていない | danger-ops.md 24 行目（コミット前に流すテストを 3 つに）・26 行目（入れ子の `DANGER_OK=1` は解除にならず止まる）を追記 |

## 修正の検証（複製で「壊したら落ちる」ことを確認）

- `GUARD=存在しないパス` → 「FAIL guard がありません」で不合格
- m9（main の `_block` を `_ask` に）→ 対照で不合格
- m8（`_danger_reasons` のコメント除去を外す）→ 余計な停止=4 で不合格

## 決定論ゲート（`docs/tests/open/I174_auto_test.md`・38 行）

gates=38 failed=0。主なもの: container pass=740・push pass=94（XP1〜XP7 追加）・matrix pass=301・作業記録の再判定 新しく確認・停止 0 件・差分テスト cases=1844 bash実行=1788 見逃し=0 余計な停止=0。

## 判定

新規 High 1 件（#1）があったため、この周はステージ通過にならない。修正済みの内容を対象に第 2 周を行う。

VERDICT: HIGH
