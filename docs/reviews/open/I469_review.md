# I469 レビュー: 見張りの値を取る文字の表の読み残しを直す

- 計画書: docs/plans/open/plan_I469.md
- イシュー: docs/issues/open/I469.md（GitHub #469）
- Draft PR: #475

## 変更概要
（implement で書く）

## 変更点
（implement で書く）

## 影響範囲
- 見張り（PreToolUse フック）の判定。全ワークツリーの Bash の確認・停止
- ハーネステスト（新規 1 本・止めるべき形の一覧）・軽い指摘の一覧（`docs/reviews/backlog/I463.md`）

## テスト結果
（test-gate で書く）

## 計画との差分
（なし）

## ロールバック
`git revert` で見張りとテストを戻す（データ・設定の変更なし）。

## 自律判断の記録
- [plan] 受け入れ条件の su の形を `su -C` から `su --session-command`（離した形・`=` の形）に置き換えた — `-C` はどの版の su にも無く何も実行しない（手元の `--help`・各版の文書）。守りたいもの（su で包んだ強制 push を止める）は同じで、事実の訂正
- [plan] python の `-c`・`-m` は今と同じに通す — パイプの中身はコードとして実行されない。I463 で見送った「`python3 -c "$X" | …` が新しく確認になる」を起こさない
- [plan] くっつけた値を秘密のファイルとして探すのは、中身を読むオプション（grep `-f`・`--file`・`--exclude-from`、sed `-f`・`--file`）だけ — 除く指定やパターンの値まで足すと確認が増える
- [plan] 一覧 I463 F5（grep の値付きの長いオプション）を同梱、F4（flock の読みすぎ）は残す — F5 は表に足すだけで秘密の表示の取りこぼしが直る。F4 は止める側に倒れるだけ
STAGE_DONE: plan NEXT: plan-review
