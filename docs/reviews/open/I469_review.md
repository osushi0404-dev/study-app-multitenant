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
- 決定論のテスト: `test_i469_guard_optspec_leftovers.sh` pass=30（FG-01〜FG-04 を含む）・`test_guard_must_stop_cases.sh` pass=3（一覧に 12 件を足した）・見張りの既存テスト 9 本 fail=0・CI すべて合格（review-gate 1630・1647）
- 作業記録での比較（TC-07・test-gate・HEAD 0e5601ee）: 17476 件・確認＋停止 370→370・新しく確認・停止 0 件・異常終了 0 件
- 手動テスト（Claude・`check-permission-prompt.sh`）: M-00（基準）・M-02（`--exclude=.env`）は承認画面なし（exit 0）、M-01（`grep -f.env`・`--file=.env`）は承認画面あり（exit 10）。すべて OK。検索先を `/dev/null` から README.md に替えた（作業フォルダの外を読む操作には Claude Code 自体が承認を求め、見張りの判定と見分けられないため）
- レビュー: コードレビュー 1630→1647 OK・敵対的レビュー 1646（V1 未検証）→1702（V2・V3 未検証・上限到達）→ユーザーの選択で延長した 1812 OK（通算 3 周）

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
- [implement] /simplify の指摘のうち `--include` を表で読む 1 件だけ採り、python の読み方の共通化などは見送った — 共通化すると標準入力とみなす場所の違い（I463 の前から）で判定が変わる。見送りの理由は計画変更記録
- [review-gate] 敵対的レビュー 1646 の HIGH（V1 が未検証）は、V1 を決定論の TC-01〜TC-04 で覆っているので確かめ方を「読んで可」に下げて次の周へ進む — 実験が拒否されただけで、指摘（反証）は 3 観点とも 0 件。コードレビュー 1630 の Low 3 件（F1〜F3・どれも変更前からの形）は止めない指摘として台帳に残し retro へ
- [review-gate] 敵対的レビュー 1702（2 周目）が、差分が文書だけで実験をせず V2・V3 を未検証として HIGH・上限到達で止めた。ユーザーの選択「もう 1 周だけ回す」で `ADV_ROUND_LIMIT=3` の 3 周目（1812）を流し、3 項目とも実験で確認済み・OK — 同じ種類（コードが変わっていなくても前の周の確認を引き継がない）の未検証が 2 周続いたことは retro で扱う
- [test-gate] 手動テストの検索先を `/dev/null` から README.md に替え、基準の M-00 を足した — `grep x /dev/null` でも承認画面が出て（作業フォルダの外を読む操作への Claude Code 自体の確認）、見張りの判定と見分けられなかった。確かめる中身・期待は同じ
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
