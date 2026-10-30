# I219 レビュー: セッションの開始時の primary の早送りを裏で動かし、打ち切りで index.lock を残さない

## 変更概要
セッションの開始時の primary の早送りを裏の処理（`--sync-primary`）に分け、開始時のフックは前回の結果を 1 行出して裏の処理を起動するだけにした（待たない）。裏の処理は 1 本ずつ（flock）・I200 の条件のまま・打ち切りは 60 秒で、fetch・merge は SIGTERM で打ち切る。フックの読み取りの git はすべて `GIT_OPTIONAL_LOCKS=0` で、打ち切られてもロックを残さない。

## 変更点
- 5-1〜5-3 `scripts/claude/hooks/sessionstart_context.py`: `primary_line_and_spawn`（開始時）・`sync_primary_bg`／`_sync_primary_steps`（裏の処理）・`_state_paths`／`_write_result`（`~/.cache/claude-primary-sync/`・0700・`os.replace`）・`_run`（`GIT_OPTIONAL_LOCKS=0`・`grace` つきの打ち切り）。時間の上限の定数と `_run_git_soft` を消した
- テスト `scripts/claude/tests/test_sessionstart_context.sh`: TC-07 を裏の処理の形に書き直し、TC-08（待たない・結果）・TC-09（1 本ずつ）・TC-10（ロックを取らない・SIGTERM）と FG-07・FG-09・FG-10 を足した（24 件）
- 5-4 `docs/runbooks/worktree.md` §2・§9
- 記録: `docs/tests/closed/I200_manual_test.md` の M-04b（NG）・`docs/reviews/backlog/I200.md` の F8 を消した

## 影響範囲
- ハーネスの開始時のフックとそのテスト・手順書だけ。アプリのコードの変更なし

## テスト結果
- 自動: `test_sessionstart_context.sh` 24 件・run-all 50 本・PR #403 の CI すべて pass
- 手動（すべて Claude）: M-01〜M-03 OK（フックの所要 2.2〜2.5 秒・裏の処理が実際の primary で結果を書く・ロック無し）。M-04 はマージ後

## 計画との差分
- 計画変更記録 1（計画レビューの Warning）・2（開始時の読み取りの打ち切りに待ちを付けない。/simplify の指摘）

## 振り返り

### I219 振り返り（かんたんなまとめ）

#### 良かった点
- 計画の前に、実際の primary で git の所要時間を測った（1〜5 秒）。ロックを取らない指定で速さは変わらないこと、速い別のコマンドは誤ることも分かり、根拠のある設計にできた（理由: I200 では小さい一時のリポジトリだけで確かめて、実環境の遅さを見逃した）
- 「裏の処理がセッションの終了で殺されないか」という未確認の前提を、実装の最後に実際のセッションで確かめた（理由: 殺されるなら作りが成り立たない前提だった）
- レビューは 1 回で通り、敵対的レビューも不要で、I200 よりずっと軽く終わった

#### 今回の問題への直接の対処
- 開始時の最悪の時間の見積もりを誤った（35 秒になるのを 25 秒と書いた）。整理の点検が見つけ、読み取りの打ち切りに待ちを付けない形に直した
- 手順書（worktree.md）の「打ち切りは SIGTERM」が、直した後の実装（読み取りはすぐ打ち切る）とずれたまま残った。軽い指摘の一覧に回した（I218 の「手順書に実装の細部を写さない」の決まりの対象）
- 計画書の本文も同じずれがあったので、振り返りの中で直した

#### 同じ問題を次回から防ぐ改善
- 新しい決まりは足さない。見積もりの誤りは整理の点検がその場で捕まえ、手順書のずれは I218 で扱う「手順書に実装の細部を写さない」の決まりで防ぐ（I200 の M-05 と同じ形。2 回目なので I218 にコメントで追記）
- コミットを裏の処理に続けて流して、shellcheck で止まったことにすぐ気づかなかった。手戻りは小さく、その場で直したので決まりは足さない

### I219 振り返り

#### 良かった点
- 実環境での計測（plan_I219.md 調査結果）・未確認の前提の実環境での確認（M-01・M-02）・レビュー 1 回で通過

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | ドキュメント | 計画変更記録 2 の直しを計画書の本文と手順書に反映し忘れた | 計画書の本文は retro で直した（台帳 F7）。手順書（台帳 F1）は軽い指摘の一覧 `docs/reviews/backlog/I219.md` |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | ドキュメント | 手順書に実装の細部（打ち切りの方法など）を写す作りのため、実装を直すと写しがずれる（I200 の M-05 に続き 2 回目） | I218（#398）の「手順書には分類と代表だけを書き、細部は実装を正にする」の範囲に、`worktree.md` も入れる（コメントで追記） | `docs/runbooks/worktree.md`・`docs/runbooks/danger-ops.md` |

## ロールバック
- PR を revert する。`~/.cache/claude-primary-sync/` の結果のファイルは残っても害が無い

## 自律判断の記録
- [plan] 計画の前に、実際の primary での読み取りの git の所要時間を測った（読み取りだけの診断）。`status` は 1〜5 秒でばらつき、`GIT_OPTIONAL_LOCKS=0` でも速さは変わらない（ロックを取らないだけ）。`diff-index` は索引の stat が古いと誤るので替えない — 裏の処理の打ち切りを 60 秒にした根拠
- [plan] 一覧 `docs/reviews/backlog/I200.md` の F8（時間の見積もりのコメント）を同梱 — 時間の見積もりの仕組み自体を消すため
- [plan-review] 計画レビュー 1 は OK（高リスク判定なし）。Warning 5・Info 2 は方式を変えずに直した（計画変更記録 1）— 再レビューは不要と判断
- [implement] 計画のリスク表の前提（フックから切り離した裏の処理が、`claude -p` のセッションの終了でも殺されない）を、実装の最後に実環境で確かめた（M-01・M-02 OK。フックの所要 2.3 秒・裏の処理が実際の primary で結果を書いた・ロック無し）
- [implement] /simplify（変更が小さいので 4 観点を 1 本のレビュー役にまとめた）の指摘で、開始時の読み取りの打ち切りに 2 秒の待ちが付き最悪 35 秒になる誤りを直した（計画変更記録 2）。テストの写し 2 か所も整理した
- [implement] 実装のコミットが shellcheck（意図的な単一引用符）で止まっていたのに、裏で続けて流した run-all の結果を待つまで気づかなかった。抑制を理由つきで書いて直し、run-all はコミットの後に流し直した（I200 の振り返りの「手元の run-all はコミットの後」を実行）
- [retro] 台帳の残り: 後続のイシューにする行は 0 件。F1〜F6 → `docs/reviews/backlog/I219.md`。F7（計画書の本文のずれ）は記録の場所なので retro で直した
- [retro] 改善案の振り分け: P1（手順書に実装の細部を写してずれる・I200 の M-05 に続き 2 回目）→ I218（#398）にコメントと本文で同梱／見送り: 見積もりの誤り（整理の点検がその場で捕まえ手戻りなし）・コミットを裏に続けて流して止まりに気づくのが遅れた（その場で直し手戻り小）— retro の 4 問の 2
- [fix-loop] close の最終確認の CI 失敗（一覧の注記の行が「- F」で始まり形の確かめに捕まった）は、案 A（注記の書き直し）で直した — 診断レビュー OK

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: test-gate

STAGE_DONE: test-gate NEXT: retro

STAGE_DONE: retro NEXT: close

STAGE_DONE: close NEXT: merge

STAGE_DONE: close NEXT: fix-loop

STAGE_DONE: fix-loop NEXT: review-gate

STAGE_DONE: review-gate NEXT: test-gate
