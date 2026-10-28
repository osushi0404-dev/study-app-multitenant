# I210 レビュー: ハーネスのテスト N10（敵対的レビューの締め切り）が実時間に依存して揺れるのを直す

- 計画書: docs/plans/open/plan_I210.md
- イシュー: docs/issues/open/I210.md（#352）
- Draft PR: #353

## 変更概要
（実装後に書く）

## 変更点
（実装後に書く）

## 影響範囲
- ハーネスだけ（`scripts/claude/adversarial-review.sh`・`scripts/claude/check-frontend-evidence.sh`・テスト 4 本の書き換えと 3 本の新規・`docs/reviews/backlog/I206.md`・`docs/reviews/backlog/I195.md`）。アプリ本体・DB・設定の変更なし

## テスト結果
（test-gate の後に書く）

## 計画との差分
（実装後に書く）

## ロールバック
- PR を revert する（計画書 7）

## 自律判断の記録
- [plan] 時刻の注入点は `adv_now`（`ADV_CLOCK_FILE` のファイルを読む）1 つにした — 判定の 2 か所と `step_timeout` がすべて `remaining()` を通るため。コマンドを渡す形は任意のコマンドの実行になるので避けた
- [plan] 鍵の待ちの順番は、本体が鍵の前に書く `exec_in1.txt` を偽物の実験役が待つ形で作る — `/proc/locks` は `flock 9` の鍵を表示しない（スパイクで確認）。偽の時計だけでは FG-N10 が揺れる
- [plan] 規則（`! … | grep -q`）を実物で流したら 4 か所（grill-me の時点の見立ては 3 か所）。`test_i202` の `d3_bl` も同じ見逃しの向きなので直す。`test_i193` 527 行は一覧 I195 F11 を同梱して消す — 規則に除外の印を作らないため
- [plan] AC1 の負荷は CPU の数だけのループ（`stress-repeat.sh`）にした — I195 で落ちたのは CPU が埋まっていたとき。新しい道具を入れずに手元と CI で同じ形にできる

- [plan-review] 判定 OK（高リスク No）。Warning 2 件（stress-repeat.sh の失敗注入・表示の経過の秒）は計画に足し、規則の誤検知の Warning は許容した — 方式・範囲・受け入れ条件は変わらないので再レビューはしない

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
