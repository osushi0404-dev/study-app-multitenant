# I200 レビュー: 見張りの確認を「本当に危ない操作」だけに絞る

## 変更概要
承認画面（確認）を、(A) GitHub の破壊・(B) 復旧できない状態・(C) 秘密や個人情報の流出につながる操作だけに絞った。見張りは「安全と確認できない」だけでは確認を出さず、危ない語があるときだけ確認する。ワークフローと pre-commit の設定の編集は、前後の中身を比べて危ない書き換えだけ確認する。許可の設定の ask は `.secrets.baseline` だけにした。あわせて、許可の判定の元になる primary を、セッションの開始時に自動で develop へ早送りする。

## 変更点
（計画書 `docs/plans/open/plan_I200.md` の 4・5 と対応）
- 5-1〜5-3 `scripts/claude/hooks/pretooluse_guard.py`: 危ない語の判定（`_RISKY_WORDS`・`_risky_words`）・コンテナ内の一覧外は語・/tmp/ 以外への書き込み・環境変数の表示のときだけ確認（`_container_risky`）・読みきれない／例外のときは語のときだけ確認（`_ask_if_risky`・`_fail_safe` は Bash だけ）・`docker compose cp` の向き（取り出しだけ外部送信、持ち込みはコピー先と中身で判定）
- 5-4 同ファイル: ワークフロー・pre-commit の設定の編集の前後の比較（`_edit_kind`・`_edit_before_after`・`_edit_risky`）
- 5-5 `.claude/settings.json`: ask を `Edit(.secrets.baseline)` だけに。allow に `docker compose exec|run|cp`（`docker-compose` も）・`git rebase *`・`psql *`・`Edit(.github/workflows/**)`・`Edit(.github/dependabot.yml)`・`Edit(.pre-commit-config.yaml)`・`Edit(docker-compose.yml)`。重複する型チェック・lint の 4 行を消した
- 5-5b `scripts/claude/check-permission-prompt.sh`: 種類 `write`（Edit・Write の許可の確かめ。上書きしない）
- 5-6 `scripts/claude/hooks/sessionstart_context.py`: `sync_primary`（条件つきの早送り・時間の上限つき）
- 5-7 `docs/runbooks/danger-ops.md`（確認を出す基準を 1 か所に・見張りの扱い・編集の確認・復旧できる範囲の表）・`docs/runbooks/worktree.md`（§2・§9 の早送りの例外）
- テスト: 新規 `test_i200_guard_narrowing.sh`（64 件）・`test_sessionstart_context.sh` に TC-07（9 件＋FG）・`test_check_permission_prompt.sh` に 06b（6 件）。期待値の変更は `test_pretooluse_container_guard.sh`・`test_i182_guard_failsafe.sh`・`test_settings_permissions.sh`・`test_i187_frontend_verify_config.sh`（一覧は auto_test の TC-08）

## 影響範囲
- アプリのコードの変更なし。ハーネスの見張り・許可の設定・セッションの開始のフック・テスト・runbook

## テスト結果
（test-gate で記入）

## 計画との差分
（計画変更記録があれば要約）

## ロールバック
- PR を revert する（データの変更なし）。revert の後、primary を手で develop にそろえ直す

## 自律判断の記録
- [plan] 最初のコミットで I213 のマージ後の手動テスト No.6〜8 の結果を書き足した（イシューの「引き継ぎ」の節。I213 の記録は develop に入っていて書き足す PR が無いため）— あわせて確かめた 2 点: セキュリティの修正が 1 件ずつ届いた理由は Dependabot の仕様（I215 #394 に同梱）／react-scripts 由来で直せない 7 件に本番に影響する重いものは無い（I214 の優先度は上げない）
- [plan] イシューで「計画の最初に確定」としていた、確認を出している層を実測した（check-permission-prompt.sh と見張りの単体の判定）。見張りを直すだけでは足りず、許可の設定に `docker compose exec|run|cp` を足す必要があると分かったので範囲に入れた — 受け入れ条件（I166 の操作が通常モードで確認なしで通る）を満たすのに必要。`git push *` と同じ「allow＋見張りが判定」の形
- [plan] `docker compose cp` のホスト→コンテナを「取り出し」と判定する誤りを見つけ、範囲に入れた — 同じく受け入れ条件に必要
- [plan-review] 計画レビュー 1 は BLOCKER（Edit の allow 不足・Edit を確かめる道具が無い）。範囲を足して直し（計画変更記録 1）、2 回目は HIGHRISK。2 回目の Warning 4 件は方式を変えずに直した（計画変更記録 2）— 再レビューは不要と判断
- [design-security-review] Blocker・High は 0 件。Medium 5 件（ワークフローの `secrets` の書き方の取りこぼし・例外の経路での `down -v`・`docker compose cp` の `/app/` への上書き・pre-commit の `files:`／`types`・確かめの道具の上書き）は、方式を変えずに計画の細部とテストに入れた（計画変更記録 3）— 計画レビューのやり直しは不要と判断（語と条件の細部だけ）。Low 3 件（コンテナ内の `pip install`・`github.token`・git の hook）は受け入れ、retro で残余リスクとして扱う
- [implement] M-04a（実際のセッションの開始でフックが動くか）を実装ステップ 1 の直後に確かめ、隔離に止められないと分かった（前提は成立）。primary の I157.md の未コミットの変更で早送りが止まる件は、ユーザーが primary で取り消した（中身は GitHub #274 の本文にあるイシュー番号の写しだけで、失うものは無いと確認してから依頼）
- [implement] 既存のテストの期待値を新しい基準に合わせた（60 件・すべて確認→通す。停止の期待値は 0 件の変更）。見直しの中で、一律の確認をやめると (C) に当たるのに通る 3 つ（`ps auxe`・`dumpdata`・`pg_read_file`）を見つけ、確認のまま残した（計画変更記録 4）
- [implement] /simplify の 4 観点の指摘のうち、直したもの: ワークフローのパスを小文字にそろえて照合（/mnt/c の上で `.GitHub/Workflows/ci.YML` と書くと判定をすり抜けた・TC-04q）／語の正規表現の組み立て・「危ない語があれば確認」・ファイルの読み込みの写しを 1 か所に／期待値の変更で中身が空になった偽合格の防止の組（G5・G6・G10・G24〜G26）を、危ない語を含む入力に替えて意味のある組に戻した。見送ったもの: 開始時の fetch を裏で走らせる（今の所要時間で上限に収まり、複雑さに見合わない）／コンテナの許可リストを縮める・消す（範囲が大きい。retro で後続の候補）／ワークフローの確認を公式の ask に戻す（ユーザーの決定 2026-10-29 に反する）／`ps` の e の判定の重複（許可リストを縮めるときに一緒に片付く）
- [fix-loop] CI の Harness Tests の失敗（`test_i197_adversarial_process.sh` の S6）は、I197 の間だけのブランチの範囲の決まりが run-all に残っていたのが原因。案 A（S6 と FG-S6 を消す）で直した — 診断レビュー OK。消すだけで新しいコードを足さず、見張りと設定の正しさは別のテストが確かめる

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: fix-loop
