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
（test-gate で記入）

## 計画との差分
（計画変更記録があれば要約）

## ロールバック
- PR を revert する。`~/.cache/claude-primary-sync/` の結果のファイルは残っても害が無い

## 自律判断の記録
- [plan] 計画の前に、実際の primary での読み取りの git の所要時間を測った（読み取りだけの診断）。`status` は 1〜5 秒でばらつき、`GIT_OPTIONAL_LOCKS=0` でも速さは変わらない（ロックを取らないだけ）。`diff-index` は索引の stat が古いと誤るので替えない — 裏の処理の打ち切りを 60 秒にした根拠
- [plan] 一覧 `docs/reviews/backlog/I200.md` の F8（時間の見積もりのコメント）を同梱 — 時間の見積もりの仕組み自体を消すため
- [plan-review] 計画レビュー 1 は OK（高リスク判定なし）。Warning 5・Info 2 は方式を変えずに直した（計画変更記録 1）— 再レビューは不要と判断
- [implement] 計画のリスク表の前提（フックから切り離した裏の処理が、`claude -p` のセッションの終了でも殺されない）を、実装の最後に実環境で確かめた（M-01・M-02 OK。フックの所要 2.3 秒・裏の処理が実際の primary で結果を書いた・ロック無し）
- [implement] /simplify（変更が小さいので 4 観点を 1 本のレビュー役にまとめた）の指摘で、開始時の読み取りの打ち切りに 2 秒の待ちが付き最悪 35 秒になる誤りを直した（計画変更記録 2）。テストの写し 2 か所も整理した
- [implement] 実装のコミットが shellcheck（意図的な単一引用符）で止まっていたのに、裏で続けて流した run-all の結果を待つまで気づかなかった。抑制を理由つきで書いて直し、run-all はコミットの後に流し直した（I200 の振り返りの「手元の run-all はコミットの後」を実行）

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate
