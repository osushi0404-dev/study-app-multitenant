# I605 レビュー: ほかのワークツリーの画像の移行と片付け

## 変更概要
- primary・harness-1・harness-2・study に残っていた、画像の移行の前の DB と画像ファイルを片付ける（primary は移して確かめてから消す・harness は DB を捨てる・study はファイルを消す）
- 手順書 `docs/runbooks/backend-check.md` §4 を、backend が起動の途中で止まった後でも動くコマンドに直す

## 変更点
- `docs/runbooks/backend-check.md` §4（計画書 4-1）
- 運用: 計画書 4-2（primary）・4-3（harness-1・harness-2・study）

## 影響範囲
- Backend/Frontend: なし（コードを変えない）
- DB: primary の開発の DB（移行 0024〜0027）・harness-1・harness-2 の開発の DB（保存領域ごと削除）
- Config: 各ワークツリーの `backend/media`（git の外）の削除

## テスト結果
- 自動: PR #608 の CI（run 44873034428・44873034470）が 8 件すべて pass
- 手動: M1〜M8 すべて OK（test-gate・2026-11-21・Claude が確かめた。人の手動テストは無し）

## 計画との差分
- あり（計画の目的の範囲）: primary は problems 0021 までで 0022・0023 と accounts.0022/0023・studylogs.0002 も流れた（P4 で承認）・primary のイメージを作り直した・画像を使う問題が 0 件で画面の確かめは無し・study はワークツリーごと撤去済みで A2 の study の分は流さなかった

## ロールバック
- 計画書 7 のとおり

## 自律判断の記録
<!-- 各段階が、止めずに自分で決めたことを `- [段階] 決めたこと — 理由` で足す。段階の結線の行（STAGE_DONE:）はこのファイルの末尾に足す -->
- [plan] harness-1・harness-2・study の削除は app-1 で人が `!` を付けて流す（各ワークツリーで Claude を起動しない）— 消すだけで人の承認が要り、Claude の `DANGER_OK=1 docker …` はサンドボックスの中に入って docker に届かないため（計画書 9）
- [plan] primary の結果は GitHub #605 のコメントで受け渡す — primary のセッションは app-1 のファイルに書けず、チャットでの受け渡しは禁止のため（計画書 9）
- [plan] 片付けは implement の段階で済ませ、人の承認のところで止まって `/proceed` で戻る — 危険操作は人の承認が要り、test-gate で終わった状態を確かめるため（計画書 9）
- [plan] 手順書 §4 を直し、一覧の I602 F2 を同梱する — 起動の途中で止まった後に今のコマンドが動かないため（計画書の調査結果 2）
- [plan-review] 計画レビューの Warning 3 件・Info 1 件を直し、再レビューはしない — 方式・範囲・受け入れ条件を変えない追記だけのため（計画変更記録）。M1 は docker をつなぐとサンドボックスの中で動き一覧が空になる（失敗を見逃す）と分かったので、`docker volume inspect` を単体で流す形にした
- [design-security-review] 公開のリポジトリなので、P10 のコメントと記録に書いてよい中身を件数・id・storage_key・移行の名前に絞った（Medium・計画書の「セキュリティレビュー結果」と P10）。受け渡しの方式は変えないので計画レビューはやり直さない — Blocker が無く、手順に書く条件を足しただけのため
- [implement] /simplify は手順書 1 節（Markdown 約 30 行）だけの差分なので、4 つのレビュー役を起こさずに 4 つの観点を自分で見た。直すところは無し（「流す前に数える」と各手順の 2 の SELECT の重なりは、その場で流せる形を優先して残した）。手順書の SQL 4 つは app-1 の DB の一時の表で動きを確かめてから取り消した
- [implement] 計画書 5 のステップ 2 で止まる（危険操作は人の承認・止める条件 2）。primary のセッションの作業を人に頼む
- [implement] primary の結果を #605 のコメントから写した（A3）。計画の想定との違い: problems は 0021 まで（0022・0023 も未適用）・accounts.0022/0023 と studylogs.0002 も流れた（P4 で人が承認）・イメージを作り直した。どれも primary のセッションが P4 で見せて承認を得ており、計画の目的（控え → 承認 → 移行 → 確かめ → 消す）の範囲
- [implement] primary の画面の確かめ（P8）は、画像を使う問題が 0 件になったため無し — 計画書 4-2 P8「画像を使う問題が無ければ、その旨を書く」のとおり。AC2 はその旨の記録で満たす
- [implement] study はワークツリーごと撤去されていた（2026-11-20 22:35 ごろ・I605 の外）ので、A2 の study の `rm -rf` は流さない。AC4 の study の分は「ワークツリーが無い」で満たす
- [review-gate] コードレビュー 20261121_1454 は OK（止める指摘なし）。F1（M3 が撤去済みの study を確かめる形）は記録の場所なので直した。F2〜F4（手順書の Low）は止めない指摘なので直さず、retro が振り分ける（直すと手順書の差分のレビューをやり直すことになる）
- [review-gate] 敵対的レビュー 20261121_1505 は OK（V1〜V3 確認済み・新規の Critical/High なし）。Low 2 件（M2 の study の行が撤去で常に通る・M1 の app-1 の保存領域の名前）は止めない指摘なので retro に回す

### 承認の記録
<!-- 危険操作の承認の言葉と日付（P4・P9 は #605 の primary のコメントから写す・A2 は app-1 の会話から） -->
- P4（2026-11-20・primary のセッション）: 0025 の削除に「消してよい」・0026 を空にすることに「空にしてよい」・0027 を空にすることに「空にしてよい」・accounts.0023 と studylogs.0002 を流すことに「流してよい」
- P9（2026-11-20・primary のセッション）: `backend/media`（7 個）と控え `backup_I605_before_primary_20261120_224053.sql` を消すことに「消してよい」
- A2（2026-11-21・app-1 の会話）: Claude が A1 の一覧と 3 行のコマンドを示し、「打つことを承認として扱う」と伝えたうえで、ユーザーが自分で `! docker rm harness-1-db-1 harness-2-db-1`・`! docker volume rm harness-1_postgres_data harness-2_postgres_data`・`! rm -rf /mnt/c/app/study-app-multitenant/.claude/worktrees/harness-2/backend/media` を順に流した（3 つとも成功）。study はワークツリーごと撤去済みのため対象外

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
