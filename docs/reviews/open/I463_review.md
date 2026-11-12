# I463 レビュー: 見張りのオプションの値の読み方を、値を取る文字の表で直す

- 計画書: docs/plans/open/plan_I463.md
- イシュー: docs/issues/open/I463.md（GitHub #463）
- Draft PR: #465

## 変更概要
見張り（`scripts/claude/hooks/pretooluse_guard.py`）に、中を読むコマンドの「値を取る短いオプションの文字」の表（`_OPTSPEC`）と getopt と同じ読み方（`_getopt`）を足し、まとめ書きの読み違い（F15・F16・F17・F2・F4・F6・敵対的レビューの Medium・一覧の F14・F18・I444 F7）を直す。止めるべき形の一覧を変更前と作業ツリーの見張りに流して比べる `guard_corpus_diff.py --cases` を足す。

## 変更点
（implement で書く）

## 影響範囲
- 見張り（PreToolUse フック）の判定。全ワークツリーの Bash の確認・停止
- ハーネステスト（新規 2 本・既存 2 本の失敗の注入）・`docs/runbooks/danger-ops.md`・軽い指摘の一覧

## テスト結果
（test-gate で書く）

## 計画との差分
（なし）

## ロールバック
`git revert` で見張りとテストを戻す（データ・設定の変更なし）。

## 自律判断の記録
- [plan] 表に入れるコマンドを、loose を使っていた呼び出し元と F17 の読み違いが出る呼び出し元に限り、rsync は入れない — 事故の例のあるコマンドだけにして表を小さく保つ（I179 の粗い判定の方針）
- [plan] `loose` を消す — 使っていた呼び出し元がすべて表のコマンドになる（F18 の根治）
- [plan] `--cases` を CI でも流す（run-all に入れる）— 数十件で数十秒・止めるべき形の後退は気づきにくく被害が大きい
- [plan] F16 は現象が再現しないので、偽の候補が出ないことの固定で閉じる
- [plan] 一覧の I454 F14・F18 と I444 F7 を同梱、ほかは残す（計画書 9.）
- [plan-review] 1226 の Warning 3 件（FG の置き換え元の確定・長いオプションの省略形・psql の表の根拠）は計画変更記録に対応を書き、再レビューしない — 方式・範囲・受け入れ条件を変えない

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
