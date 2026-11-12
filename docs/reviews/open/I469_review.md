# I469 レビュー: 見張りの値を取る文字の表の読み残しを直す

- 計画書: docs/plans/open/plan_I469.md
- イシュー: docs/issues/open/I469.md（GitHub #469）
- Draft PR: #475

## 変更概要
見張り（`scripts/claude/hooks/pretooluse_guard.py`）の値を取る文字の表の読み残しを直す。su の `--session-command`（F2）・くっつけた値の秘密のファイル（`grep -f.env`・`--file=.env`・`--exclude-from=.env`・`sed`・`rg`・`awk` の `-f`。F3）・パイプの受け手の python の値付きのオプション（F7）・grep の再帰検索の値付きの長いオプション（一覧 I463 F5）を、離して書いた形と同じ判定にする。止める対象（規則）は増やさない。

## 変更点
- `scripts/claude/hooks/pretooluse_guard.py`: `_OPTSPEC` の su に `--session-command`、grep に値を取る長いオプション 7 つを足した。su・script の `-c` の値を読む名前に `--session-command` を足した。`_FILE_VALUE_OPTS`（新規）の値を秘密のファイルを探す `paths` に足す。パイプの受け手の python のスクリプト名を `_getopt("python", …)` で読む（`-c`・`-m` は今と同じに通す）。`_grep_recursive_secret` の `--include` を表で読む
- 新規: `scripts/claude/tests/test_i469_guard_optspec_leftovers.sh`（TC-01〜TC-04・失敗の注入 4 つ）
- `scripts/claude/tests/guard_must_stop_cases.txt`: 止めるべき形を 12 件足した
- `docs/reviews/backlog/I463.md`: 同梱した F5 の行を消した

## 影響範囲
- 見張り（PreToolUse フック）の判定。全ワークツリーの Bash の確認・停止
- ハーネステスト（新規 1 本・止めるべき形の一覧）・軽い指摘の一覧（`docs/reviews/backlog/I463.md`）

## テスト結果
（test-gate で書く）

## 計画との差分
計画変更記録（計画書）のとおり。
- design-security-review: 同じ原因の rg・awk のくっつけた値も範囲に入れた（計画レビュー 1606 を通し直した）
- implement: /simplify で `_grep_recursive_secret` の `--include` を表で読むようにした（判定は同じ）

## ロールバック
`git revert` で見張りとテストを戻す（データ・設定の変更なし）。

## 自律判断の記録
- [plan] 受け入れ条件の su の形を `su -C` から `su --session-command`（離した形・`=` の形）に置き換えた — `-C` はどの版の su にも無く何も実行しない（手元の `--help`・各版の文書）。守りたいもの（su で包んだ強制 push を止める）は同じで、事実の訂正
- [plan] python の `-c`・`-m` は今と同じに通す — パイプの中身はコードとして実行されない。I463 で見送った「`python3 -c "$X" | …` が新しく確認になる」を起こさない
- [plan] くっつけた値を秘密のファイルとして探すのは、中身を読むオプション（grep `-f`・`--file`・`--exclude-from`、sed `-f`・`--file`）だけ — 除く指定やパターンの値まで足すと確認が増える
- [plan] 一覧 I463 F5（grep の値付きの長いオプション）を同梱、F4（flock の読みすぎ）は残す — F5 は表に足すだけで秘密の表示の取りこぼしが直る。F4 は止める側に倒れるだけ
- [design-security-review] 同じ原因の rg・awk のくっつけた値（`rg -f.env`・`awk --file=.env`）も直す範囲に入れ、計画レビューをやり直す — 離した形は今も確認になり、止める対象を増やさない範囲の中。範囲を広げたので計画レビューを通し直す
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
