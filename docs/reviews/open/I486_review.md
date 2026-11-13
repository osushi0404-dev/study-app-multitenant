# I486 レビュー: 敵対的レビューの実験の環境（コンテナ）と空振りの見分けを決定論にする

## 変更概要
- 敵対的レビューの起動時に、見る範囲に `backend/` の変更があれば、スクリプトがこのワークツリーの backend のコンテナを起こして確かめる（起こせなければ止める・待ちは締め切りの外）
- 実験の空振りの見分けを「どこかの行に見つからない形がある」に粗くし、言い直しの案内に新しい id を出す
- review-gate §3-1 の手で起こす手順を消す・台帳 I228 の F1・F2・F6・F7・F8 を消す

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB/Config: ハーネス（`scripts/claude/adversarial-review.sh`・テスト・review-gate・adversarial-reviewer.md・台帳）だけ

## テスト結果
- 自動: TC-01〜03 合格（test_i197 pass=154 fail=0・台帳と review-gate の否定の確かめ exit 0）。関係する test_i202・i181・i193 も手元で合格。CI 合格（CI_WAIT: OK）
- 手動: No.1（実際の docker でこのワークツリーの backend を起こし healthy・ラベル一致・exec 可）OK／No.2（review-gate に Claude の判断が残らない）OK

## 計画との差分
- なし

## ロールバック
- PR を revert する

## 自律判断の記録
- [plan] コンテナは「止める」でなく「起こす」（常に `up -d --build --wait backend`）、起こせない・別のワークツリーのコンテナなら止める — 止めると手で起こす手続きが残り AC「手順書に Claude の判断が残らない」に反するため
- [plan] `wt-ports.sh` はスクリプトから呼ばない — ワークツリーの設定を作る操作で責務の外。衝突は up の失敗で止まる
- [plan] `ADVERSARIAL_ERROR: CONTAINER` は実行し直さずに止める — 原因が記録の場所で直せないため（既存の exit 2 の決まり）
- [plan-review] 計画レビュー OK。Warning 3 件は計画変更記録のとおり直し、方式・範囲・AC は変えないので再レビューしない。Info（noexec の取りすぎ）はリスク欄に書いてあり許容 — 止める側に倒れるだけのため
- [implement] test_i202 の N18・N19 に合わせ、新しい既定値は別の `:` 行・所要秒は `SECONDS` にした（計画変更記録に 1 行） — 既定値の行を変えない・時計を読むのは adv_now だけ、の既存の決まりを守るため
- [implement] /simplify（4 観点）で採った: コンテナの id の数の分岐を消し inspect の失敗に任せる／作業フォルダを `pwd -P` でそろえて比べる（wt-remove.sh と同じそろえ方）／正規表現の行末の `\s*` を外す／テストの案内の確かめをヘルパー `hint_has` に・`yn` の書き方にそろえる／docker のスタブの inspect を実物どおり空の対象で失敗させる — どれも振る舞いを変えない整理
- [implement] /simplify で見送った: 毎回 `--build`（依存を変えたときだけにする案）— 計画で確実さを優先して決めた。作り直されるのは COPY の層だけで締め切りの外／終了コード 127 での判定 — `| tail` で隠れる（I455 の実例は is_error=false）ので文字の手掛かりが要る／id の重複をスクリプトで振り直す — レビュー役の ITEM 行が新しい id を知る必要があり範囲の外（AC は案内）／コンテナの確かめの共通化・a36 と a44 の統合・次の id を noexec のときだけ数える — 小さく、既存のテストや別スクリプトに手が広がるため

- [review-gate] 基本レビュー OK・敵対的レビューは NOT_REQUIRED（docs/reviews/I486_code_review_20261113_0907.md）。止めない指摘 F1〜F6（Medium 2・Low 4）は台帳に残し retro で扱う — 止める条件に当たらない（ハーネス・再現なし）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
