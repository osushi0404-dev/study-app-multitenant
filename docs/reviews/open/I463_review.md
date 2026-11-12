# I463 レビュー: 見張りのオプションの値の読み方を、値を取る文字の表で直す

- 計画書: docs/plans/open/plan_I463.md
- イシュー: docs/issues/open/I463.md（GitHub #463）
- Draft PR: #465

## 変更概要
見張り（`scripts/claude/hooks/pretooluse_guard.py`）に、中を読むコマンドの「値を取る短いオプションの文字」の表（`_OPTSPEC`）と getopt と同じ読み方（`_getopt`）を足し、まとめ書きの読み違い（F15・F16・F17・F2・F4・F6・敵対的レビューの Medium・一覧の F14・F18・I444 F7）を直す。止めるべき形の一覧を変更前と作業ツリーの見張りに流して比べる `guard_corpus_diff.py --cases` を足す。

## 変更点
- `scripts/claude/hooks/pretooluse_guard.py`: 値を取る文字の表 `_OPTSPEC`（psql・python・Django の shell・sed・grep・cp・mv・ln・install・su・flock・script）と `_OPTSPEC_OPTIONAL`（sed -i）・`_OPTSPEC_STOP`（python）・`_getopt`・`_value_opts` を足し、`_opt_values` の `loose` を消して `cmd` で表を使うようにした。呼び出し元（su・script・flock の -c、`_python_code_raw`、`_django_sub`、`_sql_of`、psql の -f と読むだけの判定、grep のパターンと再帰検索、`_write_targets` の sed と cp／mv／ln／install、`python -m pytest`）を表で読む。`_OPT_PATH_RE` は読む指定（cov・cov-config・ignore・ignore-glob・deselect）も除く
- `scripts/claude/tests/guard_corpus_diff.py`: `--cases <一覧>`（止めるべき形を変更前と作業ツリーの見張りで判定し、通す・弱くなった・異常終了で exit 1）。比べる相手の決め方を `base_source`、両方の判定を `judge_both` にまとめた
- 新規: `scripts/claude/tests/guard_must_stop_cases.txt`（47 件）・`test_guard_must_stop_cases.sh`（TC-09）・`test_i463_guard_optspec.sh`（TC-01〜08）
- `test_i454_guard_env_writes.sh`・`test_i444_guard_gaps.sh`: 失敗の注入の置き換え元を新しいコードに合わせた
- `docs/runbooks/danger-ops.md`: 見張りを直したら流すテストを 4 つにした。`docs/reviews/backlog/I454.md`（F14・F18）・`I444.md`（F7）の行を消した

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
- [design-security-review] Blocker・High なし。Medium 3 件（表の文字の誤り・`paths` を絞らない・python だけの読み終わり）は計画の必須防御条件として既に TC と必ず確かめる項目に入っているので、計画は変えない — 防御はどれも計画済み
- [implement] 失敗の注入の置き換え元の追従で、FG-07b も直し、FG-07a・FG-07d は流す形・置き換えを替えた（守る形・期待値は同じ）— 偽の `-c` が出なくなり、元の形では差が出なくなったため（計画変更記録）
- [implement] /simplify の 4 体の指摘のうち、同じコマンドを表と手書きで 2 通りに読む残り（python・psql・grep・flock）と、比べる道具の重複、テストの無駄な比較を直した。止める側が増える `_cmd_external` の python の `first`・差分の外の `git commit`・`_record_writes`・flock の読み終わりは見送った — 方式・範囲・受け入れ条件を変えず、読み方を 1 つにするだけのため計画レビューはやり直さない（計画変更記録）
- [review-gate] 敵対的レビュー 1319 の HIGH（V1 が実験必須を読んで確認しただけ・新しい High は 0 件）に、表と `--help` を突き合わせる決定論の TC-13 を足して V1 を「読んで可」に下げた。あわせて止めないコードレビュー 1303 の F1（python の長いオプションの値をスクリプト名と読む後退・SECURITY=yes）も同じ表の直しなので直した — この変更が持ち込んだ後退で、受け入れ条件 4（止めるべき形が後退していない）に当たるため retro に回さない
- [review-gate] 直した差分の基本レビューで CI の Harness Tests が失敗した（`test_i204_tool_sync.sh` の S1: 新しい `test_i463_optspec_help.sh` に「道具が無ければ SKIP」の分岐がある）ので fix-loop へ回す。原因を調べるときに作業ツリーで直しを試した（未コミット）— 手順どおりなら診断レビューの後に直すので、fix-loop で診断レビューを通してから確定する
- [fix-loop] CI の失敗（I204 の S1）を案 A（SKIP の分岐を消し、コマンドが無い・`--help` を読めないときは不合格）で直した — 診断レビュー 1339 が OK。一覧に util-linux を足す案 B は、一覧の写しのテストも直す手間が増えるので採らない
- [implement] psql のコンテナは起こさず、psql の表は PostgreSQL 15 の文書に拠った — 後退は TC-09・TC-10 で決定論で見る

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
