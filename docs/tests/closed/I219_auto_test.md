# I219 自動テスト: セッションの開始時の primary の早送りを裏で動かし、打ち切りで index.lock を残さない

実行コマンド: `bash scripts/claude/tests/test_sessionstart_context.sh`（CI の Harness Tests が run-all で流す）

アプリの pytest・Jest・E2E は非該当。合否はスクリプトの終了コード（全件合格 0・1 件でも不合格 1）。

一時のディレクトリに bare の origin・primary（develop をチェックアウト）・primary から作ったワークツリーを作り（I200 の TC-07 と同じ）、`CLAUDE_PRIMARY_SYNC_DIR` を一時のディレクトリにして結果のファイルの場所を分ける。gh は偽物ですぐ失敗させる。

結果:
- 変更前（2026-10-30）: `pass=16 fail=0`。TC-07 は同期の形の前提なので書き直す。ほかは実装前のため未実行

## 実行記録
- 2026-10-30（implement・コミットの後）: `bash scripts/claude/tests/test_sessionstart_context.sh` → `pass=24 fail=0`。`bash scripts/claude/tests/run-all.sh` → `run-all: pass=50 fail=0`
- CI（PR #403）: すべて success（review-gate の `code-review.sh` の CI_WAIT: OK）
- 2026-10-30（test-gate）: `bash scripts/claude/gate-check.sh I219` → `GATE_CHECK: OK`

## TC-07 裏の早送りの判定（`python3 sessionstart_context.py --sync-primary` を直接呼ぶ）
| ID | 状態 | 期待 |
|---|---|---|
| 07a | origin の develop が primary より 1 コミット進む | primary の HEAD が origin/develop と同じ。結果のファイルの 1 行に「早送りしました」 |
| 07b | 07a の後にもう一度 | 結果に「最新です」 |
| 07c | primary の追跡済みファイルに未コミットの変更 | HEAD が動かず、変更が残る。結果に「未コミットの変更」 |
| 07d | primary が develop 以外 | HEAD が動かず、結果に「develop にいない」 |
| 07e | primary に origin に無いコミット（早送りできない） | HEAD が動かず、結果に「そろえられませんでした」と手で行うコマンド |
| 07f | 未追跡のファイルがあり、ぶつからない | 早送りされ、未追跡のファイルが残る |
| 07g | 未追跡のファイルが origin の新しいファイルとぶつかる | HEAD が動かず、未追跡のファイルが中身ごと残る |
| FG-07 | 「未コミットの変更なら止める」判定を消した写しで 07c | HEAD が動く（＝07c が判定を確かめている） |

## TC-08 開始時のフックは待たずに戻り、前回の結果を出す
| ID | 状態 | 期待 |
|---|---|---|
| 08a | 結果のファイルが無い状態でフックを動かす | exit 0・5 秒以内に戻る・既存の行（branch・直近のマージ）と「primary: まだ結果がありません（裏でそろえています）」が出る・出力は 10 行以内 |
| 08b | 08a の後、裏の処理が結果を書くのを待つ（最大 60 秒・1 秒ごとに見る） | 結果のファイルが出る・primary の HEAD が origin/develop と同じ |
| 08c | もう一度フックを動かす | 「primary: 前回（<時刻>）: develop を origin/develop へ早送りしました（…）」が出る |
| 07i' | 遅い git（各 git が 6 秒待つ偽物を PATH の先頭）でフックを動かす | 25 秒以内に戻り、既存の行と primary の行が出る（I200 の TC-07i を引き継ぐ） |

## TC-09 裏の処理は 1 本ずつ
| ID | 状態 | 期待 |
|---|---|---|
| 09a | テストが結果のファイルの場所の `.lock` を `flock` で持ったまま `--sync-primary` を動かす | すぐ終わり、primary の HEAD が動かない・結果のファイルを書かない |
| FG-09 | 排他を消した写しで 09a | HEAD が動く（＝09a が排他を確かめている） |

## TC-10 打ち切られてもロックを残さない
| ID | 状態 | 期待 |
|---|---|---|
| 10a | `git` の偽物（受け取った `GIT_OPTIONAL_LOCKS` の値を記録してから本物を呼ぶ）でフックと `--sync-primary` を動かす | `status`・`branch`・`worktree list`・`symbolic-ref`・`rev-parse` の呼び出しすべてで `GIT_OPTIONAL_LOCKS=0` |
| 10b | `CLAUDE_PRIMARY_SYNC_TIMEOUT=2` と、`merge` のときだけ `exec sleep 10`（SIGTERM を受け取ったら記録する形は、偽物の中で trap を張ってから `sleep 10 & wait` で待つ）にした偽物で `--sync-primary` を動かす（打ち切りに当たる） | 結果に「そろえられませんでした」・primary に `.git/index.lock` が無い・SIGTERM で終わった（偽物が SIGTERM を受け取った記録） |
| FG-10 | 読み取りの `GIT_OPTIONAL_LOCKS=0` を外した写しで 10a | 不合格（＝10a が指定を確かめている） |

## TC-11 既存のテスト
- TC-11a〜11g（I185 の開始時のフックの確かめ）がそのまま合格
- `bash scripts/claude/tests/run-all.sh`・CI がすべて合格

## 再発防止記録
### fix-loop 1（2026-10-30・close の最終確認の CI 失敗）
- なぜ失敗したか: retro で作った `docs/reviews/backlog/I219.md` の注記が「- F7（…」で始まり、`test_i202_ledger_cleanup.sh` の D3（一覧の「- F」で始まる行はすべて決まった形）に崩れた行として捕まった
- 何を変えたか: 注記を「- 台帳の F7 …」に書き直した（診断メモ `docs/reviews/I219_fix_diagnosis_20261030_0925.md`・診断レビュー OK）
- セキュリティ上の考慮点: なし
- 次回どう防ぐか: 一覧の見出しの注記は「- F」で始めない（retro の決まりの形に合わせる）。close の前の CI が捕まえるので新しい決まりは足さない
- 確かめた結果: `bash scripts/claude/tests/test_i202_ledger_cleanup.sh` → `pass=157 fail=0`（D3 PASS）
