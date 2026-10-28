# I195 自動テスト: Claude で確かめられる手動テストを人に振らない仕組みを固める

実行コマンド（例）: アプリのコード変更が無いため `docker compose exec backend python -m pytest`・`docker compose exec frontend npm test`・E2E は非該当（CI では今までどおり動く）

結果:
- backend: 非該当
- frontend: 非該当

## テストケース

合否はすべて終了コード（合格=exit 0・不合格=非ゼロ）。否定の判定（「起動しない」「残さない」「通さない」「無い」）には失敗注入（FG: 本体の一時コピーの判定の要を壊す／指示ファイルの写しから行を消す・足すと、対応する項目が不合格になることを確かめる）を付ける。本物の tmux・claude は使わない（手動テストで確かめる）。

| TC | 内容 | 期待値 | 結果 |
|---|---|---|---|
| TC-01 | `bash scripts/claude/tests/test_tui_capture.sh`（新規。下の T1〜T9・FG） | exit 0・`fail=0` | implement で実行（2026-10-28）: 実装前（Red）はスクリプトが無く fail=1 → 実装後 pass=37 fail=0（/simplify の後も同じ） |
| TC-02 | `bash scripts/claude/tests/test_check_manual_test_executor.sh`（例の書き方を `試した手段:` に変え、X19・X20・FG を足し、X9 を消す） | exit 0・`fail=0`（ベースライン pass=23） | implement で実行（2026-10-28）: 実装前（Red）pass=19 fail=9 → 実装後 pass=28 fail=0 → /simplify で X18・FG-X18 を消して pass=26 fail=0 |
| TC-03 | `bash scripts/claude/tests/test_i193_official_flow.sh`（S21 に `s21_rules`・FG を足し、470 行の I193 の記録の判定を消す） | exit 0・`fail=0`（ベースライン pass=160） | implement で実行（2026-10-28）: 実装前（Red）pass=166 fail=6 → 実装後 pass=172 fail=0（/simplify の後も同じ） |
| TC-04 | `bash scripts/claude/tests/run-all.sh`（CI の Harness Tests ジョブで確かめる。手元では流し直さない） | CI の Harness Tests が pass | review-gate で確認（2026-10-28）: `CI_WAIT: OK`（Harness Tests を含む全ジョブ pass） |

### TC-01 の項目（`test_tui_capture.sh`）
一時のフォルダに偽物の `tmux`（呼ばれた引数を 1 行ずつ記録する。`capture-pane` では `❯ /plan-` と候補の 1 行 `/plan-issue  説明` を出す。`TUI_FAKE_NOPROMPT=1` のときは `❯` の無い画面を出す）と `claude`（何もしない）を置き、`PATH="<一時のフォルダ>:$PATH"` で `bash scripts/claude/tui-capture.sh` を流す。`which tmux` が無い環境でも動く。

| 項目 | 入力 | 期待値 | FG（失敗注入） |
|---|---|---|---|
| T1（AC1） | `--wait 0 '/plan-'` | exit 0。標準出力に `/plan-issue`。記録に `new-session -d -s tui-capture-<数> -x 200 -y 50 -c <ルート> claude --permission-mode manual`・`send-keys -t tui-capture-<数> -l -- /plan-`・`capture-pane -p -t tui-capture-<数>`・`kill-session -t tui-capture-<数>` がこの順に 1 回ずつ | FG-T1: `trap` の `kill-session` を消した写しで、記録に `kill-session` が無く不合格 |
| T2（AC1） | `'!ls'`・`'  !ls'`・`'/plan-' '!ls'` | どれも exit 2。記録に `new-session` が無い（何も起動しない） | FG-T2: `!` の判定を消した写しで、exit 0（不合格） |
| T3 | 入力なし・`--wait abc '/x'`・`--start-timeout -1 '/x'` | どれも exit 2。記録に `new-session` が無い | — （使い方の誤り。FG は T2 と同じ形で足りる） |
| T4（AC1） | `--wait 0 '/config' '{Down}' '{Enter}' '{Escape}'` | exit 0。記録に `send-keys -t … -l -- /config`・`send-keys -t … Down`・`send-keys -t … Enter`・`send-keys -t … Escape`（キーの 3 つは `-l` なし） | FG-T4: キーの判定を消した写し（全部 `-l`）で、`send-keys -t … Down` が無く不合格 |
| T5 | `--wait 0 '{Foo}'` | exit 0。記録に `send-keys -t … -l -- {Foo}`（決まった 6 つ以外は文字として送る） | — |
| T6（AC1） | `TUI_FAKE_NOPROMPT=1` で `--start-timeout 0 --wait 0 '/x'` | exit 2。記録に `send-keys` が無く、`kill-session` がある（起動しても画面が出なければ閉じる） | FG-T6: 待ちの時間切れの判定を消した写しで、exit 0（不合格） |
| T7 | PATH を一時のフォルダ 1 つだけにする。そこに置くのは本物の `git`・`sleep` へのリンク（スクリプトが外のコマンドとして使うのはこの 2 つと `tmux`・`claude` だけ）と偽物の `claude`（tmux なしの場合）、または偽物の `tmux`（claude なしの場合）。スクリプトは本物の `bash` の絶対パスで流す | どちらも exit 2。tmux なしの場合は何も起動しない | — |
| T8（AC1） | スクリプト本体 | 起動の行が `claude --permission-mode manual` の固定の文字で、引数から組み立てていない（`new-session` を含む行に `$1`・`$@`・`$*` が無い） | FG-T8: 起動の行に `"$@"` を足した写しで不合格 |
| T9（AC1） | `--wait 0 '-x hello'` | exit 0。記録に `send-keys -t … -l -- -x hello`（`-` で始まる入力もオプションにならない） | FG-T9: `--` を消した写しで、記録が `send-keys -t … -l -x hello` になり不合格 |

### TC-02 の項目（`test_check_manual_test_executor.sh`。変える・足すものだけ）
| 項目 | 備考の書き方 | 期待値 |
|---|---|---|
| X1 | `試した手段: Playwright MCP・tui-capture.sh。どちらも実機の操作感は分からない` | exit 0 |
| X3 | `試した手段: 画面が見えない`（承認画面の言葉あり・スクリプトの名前なし） | exit 1 |
| X5 | `試した手段: `（後ろが空） | exit 1 |
| X11 | `試した手段: 実機の操作感（a \| b）のため` | exit 0 |
| X12 | `試した手段: 新しいセッションでないと見えない`（言い換えの 6 語） | exit 1 |
| X16 | `試した手段: check-permission-prompt.sh は Claude Code の承認画面だけを見るので使えない。bot は自分の PR を承認できない` | exit 0 |
| X17 | `試した手段: bot は自分の PR を承認できない` | exit 1 |
| X19（AC4・AC6・再発防止） | 前の書き方だけの行。例は I193 の No.5 の当初の書き方: 手順「`claude` を起動し `/` を入力して候補を見る」・備考 `Claude で確かめられない理由: claude -p は一覧を出さない` | exit 1 |
| X20 | `試した手段：`（全角のコロン）の後ろに `Playwright MCP。Figma は開けない` | exit 0 |
| FG-X19 | 本体の写しで空の判定（`if [ -z "$tried" ]`）を `if false` にし、X19 の文書に当てる | exit 0（＝規則が無いと通ってしまう。項目は「exit 0 になる」で合格） |
| X9 | （消す） | 終わったイシュー（I187）の記録を判定にかけない（AC7） |

### TC-03 の項目（`test_i193_official_flow.sh` の S21 に足す）
| 項目 | 対象 | 期待値 | FG（失敗注入） |
|---|---|---|---|
| S21 rules-pw（AC1・AC2） | `docs/runbooks/plan-writing-rules.md` | `tui-capture.sh`・`試した手段:`・「実施者の区別」・「この基準の正はこの節」を含む | 写しから `tui-capture.sh` を含む行を全部消すと不合格 |
| S21 rules-plan（AC2） | `.claude/skills/plan-issue/SKILL.md` | 共通（「実施者の区別」・`試した手段:` を含み、`Claude で確かめられない理由` を含まない）に加えて、`bash scripts/claude/check-manual-test-executor.sh`・`plan-writing-rules.md`「実施者の区別」を含む | 写しに前の書き方の行を足すと不合格・`check-manual-test-executor.sh` の行を消すと不合格 |
| S21 rules-test（AC1・AC2） | `.claude/skills/test-gate/SKILL.md` | 共通に加えて `bash scripts/claude/tui-capture.sh` を含む | 写しから `tui-capture.sh` の行を消すと不合格 |
| S21 rules-tpl（AC2） | `docs/tests/templates/manual_test_template.md` | 共通 | 写しに `Claude で確かめられない理由:` の行を足すと不合格 |
| S21 rules-prompt（AC3） | 上の 3 つ（plan-issue・plan-writing-rules・テンプレート） | `Human` と `承認画面` の両方を含む行のうち、`check-permission-prompt.sh` を含まない行が無い | 写しに `- Human: 承認画面が出るかどうかの確認` を足すと不合格 |
| S21 rules-review（AC5） | `.claude/agents/plan-reviewer.md` | `試した手段:` と「実施者の区別」（観測手段の参照）を含む | 写しから `試した手段:` を含む行を消すと不合格 |
| （消す）470 行 | `check-manual-test-executor.sh I193` | 終わったイシュー（I193）の記録を判定にかけない（AC7） | — |

### TC-03 に足した項目（fix-loop・台帳 F3）
| 項目 | 入力 | 期待値 |
|---|---|---|
| S21 rules-prompt 大きな入力 | 違反の行 1 行の後に、Human・承認画面・`check-permission-prompt.sh` を含む行を 20000 行続けた一時のファイル | 不合格（exit 1） |
| S21 rules-prompt 読めないファイル | 無いファイル | 不合格（exit 1） |
| FG-S21 前の形 | 前の形（`! grep \| grep -qvF`）を同じ大きな入力に当てる | 合格（exit 0）＝前の形は見逃す（新しい項目が回帰を捕まえることの確認） |

## 再発防止記録（fix-loop・2026-10-28・台帳 F3）
- なぜ失敗したか: `s21_rules_prompt` を `! grep … | grep -qvF …` で書いた。`pipefail` の下では、後ろの `grep -q` が一致で先に終わると前の grep が SIGPIPE（141）で終わり、パイプの終了コードが 0 以外になって `!` で合格に反転する。出力が 64KB を超えると起きる（再現: 大きな入力で 200 回中 200 回見逃し）
- 何を変えたか: パイプと `!` をやめて awk 1 回で判定し、読めないファイルは不合格にした（`scripts/claude/tests/test_i193_official_flow.sh`）
- セキュリティ: 該当なし
- 次回どう防ぐか: 否定の判定（「無いこと」）を `! A | grep -q` の形で書かない。同じ形が `scripts/claude/check-frontend-evidence.sh:27` にもあり、変更ファイルが約 2000 件を超えると同じく反転する（scratchpad で再現）。I195 の範囲外なので retro で扱う
- 確かめた結果: `bash scripts/claude/tests/test_i193_official_flow.sh` → pass=175 fail=0（足した 3 項目を含む）

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_tui_capture.sh
bash scripts/claude/tests/test_check_manual_test_executor.sh
bash scripts/claude/tests/test_i193_official_flow.sh
```

## 実行記録
- 2026-10-28 test-gate（fix-loop の後）: `bash scripts/claude/gate-check.sh I195` → exit 0。差分のレビュー（`docs/reviews/I195_code_review_20261028_0950.md`）で決定論ゲート 3 本が exit=0、CI 全ジョブ pass。変えたのはテストのファイル 1 つだけで、手動テストの対象（`tui-capture.sh`・判定スクリプト）は変わっていないので、手動 No.1〜3 は前の結果のまま。No.4（`check-manual-test-executor.sh I195`）は流し直して exit 0
- 2026-10-28 test-gate: `bash scripts/claude/gate-check.sh I195` → exit 0（GATE_CHECK: OK）。決定論ゲート 3 本は review-gate（`docs/reviews/I195_code_review_20261028_0907.md`）で実走し、すべて exit=0。test-gate に委譲された heavy のゲートは無し。CI は Harness Tests を含む全ジョブ pass（`CI_WAIT: OK`）→ TC-04 合格
