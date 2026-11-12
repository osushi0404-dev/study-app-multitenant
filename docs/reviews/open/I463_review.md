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
- 決定論のテスト: `test_i463_guard_optspec.sh` pass=46・`test_guard_must_stop_cases.sh` pass=3（一覧 48 件）・`test_i463_optspec_help.sh` pass=2・見張りの既存テスト 8 本 fail=0・CI すべて合格（review-gate 1340）
- 作業記録での比較（TC-11・test-gate・HEAD c2310be4）: 16982 件・確認＋停止 370→370・新しく確認・停止 0 件・異常終了 0 件
- 手動テスト（Claude・`check-permission-prompt.sh`）: M-01 の 2 つ（`pytest --cov=`・`--ignore=`）は承認画面なし（exit 0）、M-02（`--junitxml=/app/…`）は承認画面あり（exit 10）。すべて OK
- レビュー: コードレビュー 1303→1340 OK・敵対的レビュー 1319（V1 未検証で HIGH）→1357 OK（通算 2 周）

## 計画との差分
計画変更記録（計画書）のとおり。方式・範囲・受け入れ条件は変えていない。
- implement: 失敗の注入の置き換え元の追従（FG-07a・07b・07d も）・`base_source`／`judge_both` への切り出し・/simplify で python・psql・grep・flock の残りの読み方を表にそろえた（`_OPTSPEC_STOP`・`_value_opts`）
- review-gate: 表と `--help` の突き合わせ（TC-13・`test_i463_optspec_help.sh`）を足し、script の `-t` と python の `--check-hash-based-pycs` を表に足した（敵対的レビュー 1319 の V1・コードレビュー 1303 の F1）

## 振り返り

### かんたんなまとめ
**良かった点**
- 読み違いの原因（どの文字が値を取るか知らずに推し量っていた）を、コマンドごとの小さな表で直した。I454 で 2 周続いた「読み方を変えるたびに別の場所が誤読する」ことは今回起きず、直す前より止める判定が弱くなった形は 0 件（止めるべき形 48 件と、過去の作業コマンド 16982 件で確かめた）
- 「止めるべき形が後退していないか」を毎回の CI で機械的に確かめる仕組みを足した。I454 では手作業の表で比べて見落としかけたところ

**今回の問題への直接の対処**
- コードレビューで、python の値を取る長いオプションが表に無く、確認だった形が通るようになる後退が 1 件見つかった。表を作るとき短いオプションだけを見ていたため。→ 表に足し、止めるべき形の一覧にも入れた
- セキュリティに関わる読み残し 3 件（su の `-C`・`grep -f.env`・python のスクリプト名の探し方）は、どれも今回の変更より前からあるもの。→ 後続のイシュー I469 にまとめ、次のハーネスの作業で最優先にした

**同じ問題を次回から防ぐ改善**
- 敵対的レビューの 1 周目が、新しい重大な穴は 0 件なのに「表の文字が正しいか」を実験せず読んだだけで HIGH になり、1 周やり直した。計画を書くときに、機械で毎回確かめられる項目をテストにしておく手順が無かったため。→ 「実験必須の項目は、先に決定論のテストで覆えないか書く」を、敵対的レビューの実験の扱いを直す既存イシュー #423 に同梱した
- 計画レビューの差し戻し・CI の失敗・fix-loop の順番の乱れは、どれもその場の仕組みで捕まえて手戻りが小さかったので、新しい手順は足さない

### 詳細（記録用）
**良かった点**
- 案 1（値を取る文字の表）で F2・F4・F6・F14〜F18・敵対的レビューの Medium・I444 F7 を一度に直し、`loose` を消した（F18 の根治）
- 予防策 `guard_corpus_diff.py --cases`（TC-09）を CI に入れ、FG で「弱くなった」「通す」を失敗にすることを確かめた

**是正処置（Corrective）**
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | セキュリティ | 表を短いオプションの `--help` だけから作り、python の値付きの長いオプションを入れなかった（コードレビュー 1303 F1） | 表に `--check-hash-based-pycs` を足し、TC-01 の 01g と止めるべき形の一覧に入れた（このイシューで直した） |
| C2 | セキュリティ | 表を使わない手書きの読み方が `_cmd_external` に残り、値の付着形・版で増えるオプションを拾えない（1340 F2・F3・F7） | I469（#469）に起票・最優先 |

**予防処置（Preventive）**
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | プロセス | 計画の「必ず確かめる項目」で実験必須にする前に、決定論の TC で覆えるかを考える手順が無い（敵対的レビュー 1319 が未検証で HIGH・1 周の手戻り） | plan-writing-rules の「必ず確かめる項目」に「実験必須にする前に決定論の TC で覆えないかを書き、覆えるなら TC を書いて読んで可にする」を足す／plan-reviewer の観点に同じ確認を足す（#423 に同梱・採否は #423 の計画で決める） | `docs/runbooks/plan-writing-rules.md`・`.claude/agents/plan-reviewer.md` |

**見送り**: 計画レビューの Blocker（必ず確かめる項目の節）・CI の失敗（I204 の SKIP の決まり）・fix-loop の順番 — どれもその場の決定論のゲート・レビューで捕まり、手戻りが小さい（自律判断の記録）

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
- [review-gate] コードレビュー 1340 は OK（止める指摘なし・F7〜F9 は Low で retro へ）、敵対的レビュー 2 周目 1357 は OK（V1〜V4 すべて確認済み）。最終判定 OK — 通算 2 周で収束
- [implement] psql のコンテナは起こさず、psql の表は PostgreSQL 15 の文書に拠った — 後退は TC-09・TC-10 で決定論で見る
- [retro] 台帳の残り（コードレビュー 1340）: F2・F3・F7（SECURITY=yes）→ I469（#469・「次のハーネスの作業で最優先」を本文に記載）／F4・F5・F6・F8・F9 → `docs/reviews/backlog/I463.md`（F1 は直して resolved）
- [retro] 改善案「実験必須の項目を計画時に決定論の TC で覆えないか書く」→ #423 に同梱（コメント）— 敵対的レビュー 1 周目が V1 の未検証だけで HIGH になり、1 周の手戻りが出た。同じ「実験必須が未検証で周を失う」損失を扱う既存イシューがある
- [retro] 見送り: 計画レビューの Blocker（高リスクの計画の「必ず確かめる項目」の節が無い）— 計画レビューがその場で捕まえ、直しは数分で手戻りなし
- [retro] 見送り: CI の失敗（新しいテストの SKIP の分岐・I204）— 決定論のテスト（`test_i204_tool_sync.sh`）が CI で捕まえ、fix-loop 1 回で直った。手元で関係するテストを選ぶ仕組みは無いが、足す工程に見合う頻度ではない
- [retro] 見送り: fix-loop で診断レビューの前に作業ツリーで直しを試した — 未コミットのまま診断レビューを通してから確定し、実害なし。記録に残した
- [retro] セキュリティの残り（計画書「セキュリティレビュー結果」の残余リスク）: 長いオプションの省略形・表に無い値付きの長いオプション・rsync を表に入れない・`--cov-report=xml:/app/…` を元から読まない、は受け入れる — 脅威モデル（普通の書き方の事故）の範囲外か変更前と同じで、Medium 以上の残りは無い。表に無い値付きの長いオプションのうち秘密に関わるもの（grep `--file=`）は I469 で扱う

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
