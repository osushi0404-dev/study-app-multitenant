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
- 自動: run-all 50 本・見張りの 3 つ（oracle・matrix 391 件・corpus diff）が pass。新規 `test_i200_guard_narrowing.sh` 75 件・TC-07 16 件・06b 6 件。PR #397 の CI すべて success（途中の 2 回の失敗は fix-loop 1・2 で直した）
- 手動（2026-10-29〜30・すべて Claude）: M-01〜M-03・M-04a・M-05 OK（M-05 は 1 回 NG → fix-loop 3 → 敵対的レビュー 3 周目〔ユーザー承認の延長〕→ 確かめ直して OK）。M-04b はマージ後

## 計画との差分
- 計画変更記録 1〜5（`docs/plans/open/plan_I200.md`）。主なもの: Edit の allow と確かめの道具 `write` を範囲に足した（1・計画レビューの差し戻し）／設計のセキュリティレビューの Medium 5 件（3）／既存テストの見直しで見つけた (C) の 3 つを確認のまま残した（4）／敵対的レビュー 1 周目の後に、後退（F1）と書き込み先・環境変数の表示を直した（5）

## 振り返り

### I200 振り返り（かんたんなまとめ）

#### 良かった点
- 計画の前に「どこが承認画面を出しているか」を実測した。見張りを直すだけでは足りず、許可の設定にも足す必要があると最初に分かった（理由: 推測で計画していたら、実装の後に「直したのにまだ出る」で手戻りしていた）
- 既存のテスト 60 件の期待値を変えるとき、1 件ずつ理由を確かめた。その中で、方針の (C) に当たるのに通ってしまう 3 つ（環境変数の表示・DB のダンプ・DB のコンテナのファイル読み）を見つけ、確認のまま残せた（理由: 機械的に書き換えていたら守りの穴になっていた）
- 実際の承認の仕組み（通常モードの新しいセッション）で、外した確認が出ないこと・残した確認が出ることを確かめた。I166 の 6 つの操作は、変更前は全部承認画面が出て、変更後は全部出なくなった（理由: テストの上だけでなく、ユーザーが体験する形で効果を確かめられた）
- primary の自動の最新化は、実装の最初に実際のセッションで動くか確かめた（理由: 未確認の前提を後回しにしなかった）

#### 今回の問題への直接の対処
- 手順書の言い回しが見張りの実物より狭く残った。レビューの途中で見張りの確認の範囲を広げたとき、手順書の文を直す対象に入れていなかったため。→ 手順書を直し、ユーザーの承認で敵対的レビューを 1 周延長して確かめた
- 敵対的レビューの後に残った小さな取りこぼし（環境変数の表示の別の形・書き込み先の別の書き方・WHERE なしの UPDATE）と、作りの整理（許可リストの二重化）は、後続のイシュー I218 にまとめた

#### 同じ問題を次回から防ぐ改善
- **レビューの判定が日本語の「指摘なし」を読めない（3 回目）**: 組み込みのセキュリティレビューが実際に動いて「脆弱性なし」と書いても、判定のスクリプトが読めずに HIGH にし、やり直しで差分なしの OK になった。I213 と合わせて 3 回、やり直しの周が増えた。→ すでに I212 に同梱済みの直し（機械判定の 1 行を必ず出させる）の実例として追記した。I212 をハーネスの最優先にする
- **敵対的レビューの 1 周目が空振りした**: 3 つのレビュー役が、どれも実験の案を出した時点で締め切りに達し、実験が 1 本も走らなかった。全部が「未確認」で HIGH になり、1 周を丸ごと使った。締め切りをレビュー役と実験役が共有しているため。→ 実験の時間を別に確保する見直しを、I212 に同梱した（I206 で「1 件でもあれば見直す」と決めていた事態）
- **CI を 2 回、テストの作り方の誤りで落とした**: 1 回目は、前のイシュー専用の確かめが残っていたのに、手元のテストを変更のコミットの前に流したので気づけなかった。2 回目は、足したテストが手元の環境（ワークツリーが複数ある）に依存していた。→ 「イシューの範囲の確かめは run-all に置かない」と「手元の run-all はコミットの後」を I218 に入れた。環境への依存は CI がその場で捕まえ、手戻りが小さかったので、新しい決まりは足さない

### I200 振り返り

#### 良かった点
- 計画の前の実測（check-permission-prompt.sh と見張り単体の判定）で、確認を出している層を切り分けた
- 既存テストの期待値の変更を 1 件ずつ理由づけし、(C) に当たる 3 つを確認のまま残した（計画変更記録 4）
- 通常モードの新しいセッションで承認画面の有無を確かめた（M-01〜M-03）
- 未実証の前提（フックが本体の隔離に止められないか）を実装ステップ 1 で確かめた（M-04a）

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | セキュリティ | 見張りの規則を列挙で作るため、同じ意味の別の書き方が漏れる（台帳 F10・F12・一覧 F9・F11・敵対的レビューの WHERE なしの UPDATE） | I218（#398）に起票（`SECURITY=yes` を含む・I212 の後に最優先） |
| C2 | 技術選択 | I200 で判定の主役を語の判定に替えたとき、許可リストを片付けなかった（/simplify の指摘） | I218 に同梱 |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | スキル・規約 | 組み込みのセキュリティレビューの「指摘なし」の判定が、文の形に頼っている（3 回目） | 組み込みのレビューへの依頼に機械判定の 1 行を必ず出させ、判定はその行だけで行う（I212 の同梱 2 に実例を追記） | `scripts/claude/code-review.sh` |
| P2 | プロセス | 敵対的レビューの締め切りをレビュー役と実験役が共有し、実験の時間が残らない | 実験の時間を締め切りとは別に確保する（方式は I212 の計画で決める） | `scripts/claude/adversarial-review.sh`・`.claude/agents/adversarial-reviewer.md`・`docs/runbooks/review-rules.md` |
| P3 | スキル・規約 | 決定論テストの対象の選び方に「イシューの間だけの決まりは run-all に置かない」が無く、手元の run-all をコミットの前に流してよいかの決まりも無い | `plan-writing-rules.md`「決定論テストの対象の選び方」に足す・実装の段階の手順か run-all で未コミットを知らせる（I218 に同梱） | `docs/runbooks/plan-writing-rules.md`・`.claude/skills/implement/SKILL.md` か `scripts/claude/tests/run-all.sh` |
| P4 | ドキュメント | 手順書に見張りの規則を言葉で写す作りのため、見張りを変えると写しがずれる | 手順書には分類と代表だけを書き、列挙は見張りの定数を正にする（I218 に同梱） | `docs/runbooks/danger-ops.md` |

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
- [review-gate] 1 回目（`docs/reviews/I200_code_review_20261029_2240.md`）が `OFFICIAL_SECURITY: FAILED` で HIGH。記録の本文では組み込みの /security-review は実際に動き、ブランチ全体（settings.json・見張り・開始のフック・check-permission-prompt.sh）を見て「報告する脆弱性はありません」と日本語の文で書いていた（判定が文の形を読めない・I212 の同梱 2 と同じ）。決まりどおり 1 回だけやり直すと（途中で記録のコミットの push 漏れ〔NOT_PUSHED〕を push して実行し直した）、`..._2252.md` は差分なしで、/security-review を動かさずに OK（I212 の穴）— 進む根拠は 1 回目の本文の全体のセキュリティレビュー。台帳の Medium F1（見張りの例外のときに別 worktree への書き込みの停止まで飛ばす）は今回の変更でできた後退なので、敵対的レビューの結果と合わせて直す方向で扱う
- [review-gate] 敵対的レビュー 1 周目（`docs/reviews/I200_adversarial_review_20261029_2318.md`）は HIGH。3 観点とも所要 920〜990 秒で、実験の案を出した時点で締め切りに達し、実験が 1 本も走らなかった（新しい Critical・High は 0）。§3-3 のとおり、未検証の V1〜V4・V6 を決定論の TC で覆って「読んで可」に下げた（計画変更記録 5）。あわせて、I200 でできた後退（台帳の F1）と、小さく直せる Medium・Low（F2・F3・F4・F6）を直した — 2 周目で直した差分も反証にかける。I206 の②（締め切りによる未検証）が 1 件以上あるので、retro で締め切りの見直しを起票する
- [fix-loop] CI の 2 回目の失敗（03j が CI に別の worktree が無くて不合格）は、テストが環境の worktree の数に依存していたのが原因。案 A（一時のディレクトリに主とワークツリーを作る）で直した — 診断レビュー OK
- [review-gate] 敵対的レビュー 2 周目（`docs/reviews/I200_adversarial_review_20261029_2349.md`）は OK（V1〜V8 確認済み・V6 は実験で確認・新しい Critical／High 0）。残った Low（`cp -t` の書き先・コンテナ内の psql の WHERE なしの UPDATE・danger-ops.md 29 行目の「リダイレクトで」の言い回しが F3 の範囲に追いついていない・ホストの psql は見張りだけが判定）は、OK の周の後に差分を足さない決まりのため直さず、retro が台帳の残りとして扱う
- [test-gate] 手動テストは M-01〜M-03 OK（M-02 の 4 つ目は試しの操作の選び方の誤りで、許可リストに入らない形で確かめ直して OK）・M-04a は実装時に OK・M-04b はマージ後。M-05 は NG（danger-ops.md の 4. が、計画変更記録 5 で広げた確認の範囲に追いついていない）で fix-loop へ
- [fix-loop] M-05 は案 A（4. の 2 か所の言い回しを実物に合わせる）で直した — 診断レビュー OK。文書だけの変更だが、敵対的レビューの上限（2 周）を使い切った後の変更なので、review-gate でユーザーに 1 周の延長を聞く
- [review-gate] 敵対的レビューの上限（通算 2 周）を使い切った後の変更（M-05 の手順書の直し）なので、ユーザーに延長を確認した。ユーザーの言葉（2026-10-30）:「1周延長して直して」→ `ADV_ROUND_LIMIT=3` で 3 周目を起動する
- [review-gate] M-05 の直しの基本レビュー（`docs/reviews/I200_code_review_20261029_2357.md`）も `OFFICIAL_SECURITY: FAILED` で HIGH。本文では /security-review が動き「報告できる脆弱性はありませんでした」（I212 の穴・3 回目）。1 回だけやり直して OK（差分なし）。根拠は 2357 の本文の全体のセキュリティレビュー
- [retro] 台帳の残り: F10・F12（`SECURITY=yes`）→ I218（#398）。F5・F7・F8・F9・F11・F13 → `docs/reviews/backlog/I200.md`。敵対的レビューの Low（WHERE なしの UPDATE・`cp -t`）と /simplify の許可リストの整理も I218 に入れた
- [retro] 改善案の振り分け: P1（「指摘なし」の取り違えの 3 回目）・P2（敵対的レビューの締め切りで実験が走らない）→ I212（#358）に同梱（コメントと本文。判定の仕組みなのでハーネスの最優先）／P3（イシューの範囲の確かめを run-all に置かない・手元の run-all はコミットの後）・P4（手順書の写し）・C1・C2 → I218（#398）を起票／見送り: 「テストを環境に依存させない」決まり — CI がその場で捕まえ、手戻りが 1 周で小さかった（retro の 4 問の 2）
- [retro] I206 の確かめる 2 点（I196 向けの取り決めだが I200 でも測った）: ① RISK=up は 0 件（コードレビューの記録 5 つ）② 締め切りによる「実行していない」は 2 件（1 周目）→ I212 に同梱した

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: fix-loop

STAGE_DONE: fix-loop NEXT: review-gate

STAGE_DONE: review-gate NEXT: fix-loop

STAGE_DONE: fix-loop NEXT: review-gate

STAGE_DONE: review-gate NEXT: test-gate

STAGE_DONE: test-gate NEXT: fix-loop

STAGE_DONE: fix-loop NEXT: review-gate

STAGE_DONE: review-gate NEXT: test-gate

STAGE_DONE: test-gate NEXT: retro

STAGE_DONE: retro NEXT: close
