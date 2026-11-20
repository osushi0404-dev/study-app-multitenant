# I599 自動テスト: サンドボックスの中から scripts/claude/ に書いたスクリプトをレビュー前に外で流せる穴を塞ぐ

実行コマンド: `bash scripts/claude/tests/test_i599_unreviewed_scripts.sh`（CI の Harness Tests が `run-all.sh` で流す）

結果:
- 実装前のため未実行（テストのファイルは実装のステップ 1 で作る）

## テストケース
共通の土台（TC-01）: 一時フォルダに git リポジトリを作り、`scripts/claude/` の小さな写し（`a.sh`〔`lib.sh` を名前で `source`〕・`lib.sh`・`b.sh`〔何も呼ばない〕・`tests/run-all.sh`・`tests/test_x.sh`・`tests/stress-repeat.sh`・`test-session.sh`）と `.claude/hooks/unreviewed.py`・`.claude/settings.json` を置いてコミットし、`refs/remotes/origin/develop` をそのコミットに向ける。見張りは `CLAUDE_PROJECT_DIR=<一時のリポジトリ>` で、本物の `scripts/claude/hooks/pretooluse_guard.py` を `{"tool_name":"Bash","tool_input":{"command":…}}` の JSON で流す。`HOME` は一時フォルダに替える。

| TC | 何を確かめるか | 入力・操作 | 期待（終了コードで判定） | 失敗の注入（FG） |
|---|---|---|---|---|
| TC-01 | 土台が動く | 変更なしで `bash scripts/claude/a.sh` | 見張りの出力に `updatedInput` が無い・終了 0 | 土台の `origin/develop` を消すと TC-08 の形（書き換え）になる |
| TC-02 | 新しく書いたスクリプト（I597 の形）は中で動く | 追跡していない `scripts/claude/new.sh` を置き `bash scripts/claude/tests/test_new.sh`（中で `new.sh` を名前で呼ぶ・これも新規） | `updatedInput.command` が `echo '[I599] ` で始まり、元のコマンドで終わる。`permissionDecision` が無い | `unreviewed.py` の `check()` が常に「済み」を返す写しで流すと不合格 |
| TC-03 | 変えていないスクリプトから名前で呼ぶライブラリを変えると中で動く | コミット済みの `lib.sh` を書き換え（未コミット）、`bash scripts/claude/a.sh` | `updatedInput` があり、印に `scripts/claude/lib.sh` が出る | たどり（辺を張る処理）を外した写しで不合格 |
| TC-04 | 変えたファイルに届かないスクリプトは外のまま | `lib.sh` を書き換えたまま `bash scripts/claude/b.sh` | `updatedInput` が無い | 「届くか」を見ずに変更があれば書き換える写しで不合格 |
| TC-05 | `run-all.sh` がまとめて拾うテストを足すと中で動く | 追跡していない `tests/test_y.sh` を置き `bash scripts/claude/tests/run-all.sh` | `updatedInput` がある | `_RUNNER_GLOBS` を空にした写しで不合格 |
| TC-06 | 引数で渡したファイルを動かす入口 | 変更なしで、一時フォルダの既にある `x.sh` を `bash scripts/claude/tests/run-all.sh <x.sh>`・`bash scripts/claude/tests/stress-repeat.sh 1 <x.sh>` に渡す。無いファイルを渡す | 既にあるファイルはどちらも `updatedInput` がある。無いファイルは書き換えない | `EXEC_SUFFIXES` を空にした写しで不合格 |
| TC-07 | たどれない形は変更が無くても中で動く | 変更なしで `bash scripts/claude/../../x.sh`・`bash scripts/claude/$X`・`` bash scripts/claude/`echo a`.sh ``・`bash scripts/claude/*.sh`・`bash scripts/claude/~x` | 5 つとも `updatedInput` がある | 文字の確かめを外した写しで不合格 |
| TC-08 | BASE が求められないときは中で動く | `refs/remotes/origin/develop` を消して `bash scripts/claude/b.sh` | `updatedInput` がある | BASE の失敗を「済み」に倒す写しで不合格 |
| TC-09 | `scripts/claude/` を含まないコマンドは今までどおり・git を呼ばない | `PATH` の先頭に呼ばれたら印を書く `git` を置き、`ls` を流す | 出力が空・印が無い | 起動条件を外した写しで印ができて不合格 |
| TC-10 | 前に付ける書き換えが意味を変えない | 元のコマンド 6 形（`false \|\| true`・`printf a \| cat`・`true; false`・ヒアドキュメント・頭の注釈 `# c⏎true`・`DANGER_OK=1 true`）を書き換えた形にし、`bash -n` と実行の終了コードを元と比べる | 6 形とも `bash -n` が 0・終了コードが元と同じ | 前置きを `echo … >&2;` 以外の壊れた形（`echo … >&2 \|`）にした写しで不合格 |
| TC-11 | 確認（ask）にも書き換えが付く | 新しい `scripts/claude/new.sh` を置き、既存の確認に当たる語を足したコマンド（`bash scripts/claude/new.sh; printenv`） | `permissionDecision` が `ask` で、`updatedInput` もある | `_ask()` に `updatedInput` を足す処理を外した写しで不合格 |
| TC-12 | `test-session.sh` の引数 | 変更なしで ① `bash scripts/claude/test-session.sh "x" --model haiku --permission-mode default` ② `… --settings /tmp/s.json` ③ `… --settings .claude/settings.json`（BASE と同じ） ④ ③で `.claude/settings.json` を書き換えた後 ⑤ `… --mcp-config m.json` | ①③は出力が空。②④⑤は `permissionDecision` が `ask` | 許可の表を「何でも可」にした写しで不合格 |
| TC-13 | 起動役: 変更が無ければ作業ツリーのフック | 印を出すだけのフック `scripts/claude/hooks/h.py` をコミットし、`bash .claude/hooks/reviewed-hook.sh scripts/claude/hooks/h.py` | 標準出力が作業ツリーの印・終了 0 | 起動役が常に写しを使う写しで不合格（印が違う） |
| TC-14 | 起動役: 変更があれば BASE の写し | `h.py` の印を書き換え（未コミット）て同じく流す | 標準出力が BASE の印。`$HOME/.cache/claude-reviewed-hooks/<BASE>/.complete` がある。標準入力がフックに届く（フックが読んだ JSON を出す） | 変更の判定を外した写しで不合格 |
| TC-15 | 起動役: BASE が求められないとき | `origin/develop` を消して流す | 作業ツリーの印・標準エラーに理由・終了 0 | 理由を出さない写しで不合格 |
| TC-16 | 設定のフックはすべて起動役を通る | `.claude/settings.json` の `hooks` の全 `command`（`test_settings_permissions.sh` に 1 項目） | すべて `.claude/hooks/reviewed-hook.sh scripts/claude/hooks/` を含む | 1 つを `python3 …/pretooluse_guard.py` に戻した写しで不合格 |
| TC-17 | 手順書・一覧 | 下の決定論ゲートの `grep` | すべて 0 | 文言を消した写しで不合格（ゲートの `grep` そのもの） |
| TC-18 | `code-review.sh` のゲートは、レビュー前の中身に届く行を流さない | 一時のリポジトリで、ゲートに ① 新しい `tests/test_new.sh`（流されたら印を書く） ② 変更の無い `tests/test_x.sh`（同じく印）を書いた自動テスト文書を置き、`run_declared_gates` を流す | ①の印が無く、証跡に `⏭ レビュー前の中身` がある。②の印がある。`GATE_VERDICT=OK` | 確かめの呼び出しを外した写しで①の印ができて不合格 |
| TC-19 | 判定の CLI | `python3 .claude/hooks/unreviewed.py check -- '<コマンド>'` を TC-04・TC-02・TC-12②・引数なしで | 終了コードが 0・1・3・2 | 終了コードを常に 0 にした写しで不合格 |
| TC-20 | 1 つのコマンドの複数の参照をすべて見る | `lib.sh` を書き換え、`bash scripts/claude/b.sh && bash scripts/claude/a.sh`（後ろだけが届く） | `updatedInput` がある | 最初の参照だけを見る写しで不合格 |
| TC-21 | 判定の読み取りの上限 | 1MB を超える変更の無いファイル（コミット済み）を他の変更があるときに流す、または 2,000 を超えるファイルを置き `bash scripts/claude/b.sh` | 20 秒以内に終わり `updatedInput` がある | 上限を外した写しで時間が上限を超える・書き換えが無くて不合格 |
| TC-22 | 基準と安全な `-c` が判定・起動役・見張りで同じ | 3 つのファイルの文字 | `merge-base HEAD origin/develop` と 3 つの `-c` が一致 | 起動役の `-c` を 1 つ消した文字列で不合格 |
| TC-23 | 引用符の中の文には当たらない | `git commit -m "bash scripts/claude/new.sh を足す"`（`new.sh` は新規）と `git status && bash scripts/claude/new.sh` | 前は出力なし・後ろは `updatedInput` がある | 最初の区切りだけを見る写し（FG TC-20 と同じ）で後ろが不合格 |
| TC-24 | 振り向けがスクリプト名にくっついても取り違えない（F1） | 新しい `new.sh` を `>/dev/null`・`2>&1`・`< /dev/null`・`2>/dev/null` つきで流す。変更の無い `b.sh` を `>/dev/null`・`2>&1` つきで流す | 前の 4 つは `updatedInput` がある・後ろの 2 つは出力なし | 区切りから `<>` を外した写しで不合格 |
| TC-25 | git が無視するファイル（F2） | `.gitignore` の `*.tmp`・`igndir/` で、① `bash scripts/claude/evil.tmp` ② 追跡済みの `c.sh`（`helper.tmp` を名前で呼ぶ）③ `bash scripts/claude/igndir/x.sh`。どれも他に変更なし | 3 つとも `updatedInput` がある | 無視されるファイルを数えない写しで ② が不合格・一覧の外の出発点を見ない写しで ③ が不合格 |

セキュリティ設計レビュー（計画書「セキュリティレビュー結果」）で足す確かめ:
- TC-02 に、名前に `'` と改行を含む新しいファイルを足す: 印の中の名前は `_` に置き換わり、`bash -n` が 0
- TC-12 に `--settings=/tmp/s.json`（`=` の形）を足す: `ask`
- TC-12 に F4 の形を足す: `--permission-mode bypassPermissions`・`--permission-mode=dontAsk`・`--setting-sources user`・`--setting-sources=` は `ask`。`--permission-mode auto`・`--setting-sources user,project`・`--setting-sources user --settings .claude/settings.json`（レビュー済み）は出力なし。FG: 許可のモードの表に `bypassPermissions` を足す・`--setting-sources` の確かめを外すと不合格
- TC-13 に、土台の `.git/config` に `core.fsmonitor=<印を書くコマンド>` を書いた形を足す: 印ができない

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i599_unreviewed_scripts.sh
bash scripts/claude/tests/test_settings_permissions.sh
grep -q 'reviewed-hook.sh' docs/runbooks/danger-ops.md
grep -q 'unreviewed.py' docs/runbooks/danger-ops.md
grep -q 'I599' docs/runbooks/harness-audit.md
! grep -q 'F1 SEV=Medium REPRO=no KIND=guard SECURITY=yes FILE=.claude/settings.json' docs/reviews/backlog/I430.md
```

## 実行記録
- 2026-11-20 計画: TC-01〜TC-19 は実装前のため未実行。TC-17 の `! grep -q …I430.md` は、今は F1 の行があるので不合格（exit 1）になることを確かめた（失敗の注入に当たる）
- 2026-11-20 fix-loop（CI の Harness Tests の失敗）:
  - なぜ失敗したか: フックの `command` を起動役を通す形に変えたが、古い形と完全一致を見る既存のテストが 2 本あった（`test_i187_frontend_verify_config.sh` ⑦・`test_sessionstart_context.sh` TC-11g）。計画の調査で古い形の文字列をリポジトリ全体で grep しなかった
  - 何を変えたか: 2 本の期待値を `bash "$CLAUDE_PROJECT_DIR"/.claude/hooks/reviewed-hook.sh scripts/claude/hooks/<名前>.py` に替えた（診断メモ `docs/reviews/I599_fix_diagnosis_20261120_1810.md` の案 A）
  - セキュリティ: 守りの弱まりなし（期待値を起動役を通す形に厳しくしただけ）
  - 次回どう防ぐか: 設定の書き方を変えるときは、古い形の文字列をリポジトリ全体で grep して消費箇所を全部直す（plan-writing-rules「規約是正時の消費箇所の全件列挙」。retro で振り返る）
  - 確かめた結果: 2 本を手元で流し合格（⑦ pass=14 fail=0・TC-11g を含む pass=24 fail=0）。古い形のままで不合格になることは CI の run 44706186290 で確かめ済み（失敗の注入に当たる）
- 2026-11-20 fix-loop（review-gate の止める指摘 F1・F2・F4）:
  - なぜ失敗したか: 「実在するのに git の一覧（追跡＋追跡していない新規）に無いファイル」をレビュー済みと同じに扱っていた（振り向けがくっついた名前・git が無視する名前・変更が無いときの早く返す道・名前で呼ぶ先）。test-session の表は引数の名前だけを見て、値（許可のモード・プロジェクトの設定を読むか）を見ていなかった
  - 何を変えたか: 区切りに `<>` を足す。git が無視するファイル（無視されるフォルダはまとめて 1 つにして数えない）をレビュー前に数える。出発点が実在するのに一覧に無ければ、変更が無くても中で動かす。`--permission-mode` は `default`・`manual`・`plan`・`acceptEdits`・`auto` だけ、`--setting-sources` は `project` を含むかレビュー済みの `--settings` と一緒のときだけ（診断メモ `docs/reviews/I599_fix_diagnosis_20261120_1840.md`。差し戻しの後の 2 回目で PASS）
  - セキュリティ: レビュー前の中身・守りの無い子のセッションを外で動かせる穴を塞いだ（C8）。無視されるフォルダ（`.venv`・`__pycache__`）の中を名前で呼ぶ形は残る（計画 R3・わざと避ける形）
  - 次回どう防ぐか: 「一覧に無い」「値を見ない」を済みに倒さない（判定できないものは中で動かす・承認に倒す）。許可の表は名前だけでなく値も決める
  - 確かめた結果: `bash scripts/claude/tests/test_i599_unreviewed_scripts.sh` pass=47 fail=0（TC-24・TC-25・TC-12 の追加と各 FG を含む）
