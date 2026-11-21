# I599 自動テスト: サンドボックスの中から scripts/claude/ に書いたスクリプトをレビュー前に外で流せる穴を塞ぐ（第 2 版）

実行コマンド: `bash scripts/claude/tests/test_i599_unreviewed_scripts.sh`（CI の Harness Tests が `run-all.sh` で流す）

結果:
- 2026-11-20 implement（第 2 版）: `bash scripts/claude/tests/test_i599_unreviewed_scripts.sh` pass=30 fail=0（TC と FG）・`test_settings_permissions.sh` pass=35・`test_i525_skill_sandbox_form.sh` pass=7・影響しうる既存のテスト（`test_pretooluse_guard_matrix`・`test_guard_must_stop_cases`・`test_i200_guard_narrowing`・`test_i444_guard_gaps`・`test_review_gates`・`test_i187_frontend_verify_config`・`test_sessionstart_context`・`test_posttooluse_check`・`test_i182_guard_failsafe`）も合格

## テストケース
共通の土台: 一時フォルダに git リポジトリを作り、`scripts/claude/` の小さな写し（一覧の名前の `issue-source.sh`〔流されたら印のファイルを書き、引数を出す〕・`test-session.sh`・一覧に無い `other.sh`・`tests/test_x.sh`・`hooks/h.py`）・`.claude/hooks/` の本物の写し・`.gitignore`（`*.tmp`・`igndir/`）を置いてコミットし、`refs/remotes/origin/develop` をそのコミットに向ける。見張りは本物の `scripts/claude/hooks/pretooluse_guard.py` を `CLAUDE_PROJECT_DIR=<一時のリポジトリ>` で JSON を渡して流す。`HOME` は一時フォルダ。

| TC | 何を確かめるか | 入力・操作 | 期待（終了コードで判定） | 失敗の注入（FG） |
|---|---|---|---|---|
| TC-01 | 見張り: 一覧の名前の単体の形は起動役の形に付け替える | `bash scripts/claude/issue-source.sh body I1`（`timeout` 7 つき） | `updatedInput.command` が `python3 .claude/hooks/unreviewed.py run issue-source.sh body I1`・`timeout` が残る・`permissionDecision` なし | 付け替えを外した判定の写しで不合格 |
| TC-02 | 見張り: 単体でない形・一覧に無い名前は何もしない（中で動く） | `timeout 5 bash scripts/claude/issue-source.sh x`・`X=1 bash …`・`bash … $(true)`・`` bash … `x` ``・`bash … \| cat`・`bash … >o`・`bash …; ls`・`{ bash …; }`・`bash scripts/claude/other.sh`・`bash scripts/claude/../../x.sh`・`bash scripts/claude/tests/run-all.sh x.sh`・`git commit -m "bash scripts/claude/issue-source.sh"` | どれも出力なし・終了 0 | 単体の確かめを外した写しで `$(true)` の形が付け替えられて不合格 |
| TC-03 | 再発防止（I597 の形）: 新しく書いたスクリプトは外に出ない | 追跡していない `scripts/claude/new.sh` を置き `bash scripts/claude/new.sh`・`python3 .claude/hooks/unreviewed.py run new.sh` | 前は見張りの出力なし（中）・後ろは起動役が終了 2 で `new.sh` は動かない | 一覧に `new.sh` を足した写しで不合格 |
| TC-04 | 見張り: 起動役を単体でない形で流すと止める | `python3 .claude/hooks/unreviewed.py run issue-source.sh x; ls`・`… $(true)`・`X=1 python3 .claude/hooks/unreviewed.py run …`・`… >o` | どれも見張りが終了 2 | 止める確かめを外した写しで不合格 |
| TC-05 | 見張り: `test-session.sh` の引数 | スクリプトの形と起動役の形で、許可の表の引数（`--model haiku --permission-mode default`）・`--settings /tmp/s.json`・`--settings=/tmp/s.json`・`--mcp-config m.json`・`--permission-mode bypassPermissions`・`--setting-sources user`・`--setting-sources user --settings .gitignore`・`--setting-sources user --settings .claude/settings.json` | 表の引数と最後の形は承認なし（スクリプトの形は付け替えあり）。ほかは `ask`（スクリプトの形は `updatedInput` も付く） | 表を「何でも可」にした写しで不合格 |
| TC-06 | 見張り: 判定を読み込めないとき | 判定のファイルを壊した写しで `python3 .claude/hooks/unreviewed.py run issue-source.sh x`・`bash scripts/claude/issue-source.sh x` | 前は終了 2（止める）・後ろは出力なし（中） | 読み込めないときも通す写しで不合格 |
| TC-07 | 起動役: レビュー前の中身が無ければ一覧のスクリプトを動かす | `python3 .claude/hooks/unreviewed.py run issue-source.sh a "b c"` | 終了 0・印のファイルができる・引数がそのまま届く | 起動役が常に止める写しで不合格 |
| TC-08 | 起動役: レビュー前の中身があれば止める | ① 追跡済みの `other.sh` を書き換え ② 追跡していない `scripts/claude/n.sh` ③ 無視される `scripts/claude/evil.tmp` のそれぞれで TC-07 と同じ | どれも終了 3・印のファイルができない・標準エラーに `! bash scripts/claude/issue-source.sh` の案内 | 差を見ない写し（①）・無視されるファイルを数えない写し（③）で不合格 |
| TC-09 | 起動役: 基準を求められないときは止める | `origin/develop` を消して TC-07 と同じ | 終了 3・印ができない | 基準の失敗を「なし」に倒す写しで不合格 |
| TC-16 | 起動役: サンドボックスの中で動いたら早く失敗する | `SANDBOX_RUNTIME=1` を付けて TC-07 と同じ | 終了 4・印ができない・標準エラーに「サンドボックスの中で動いています」 | 中の確かめを外した写しで印ができて不合格 |
| TC-17 | 見張り: cwd が最上位でないときの起動役の形は止め、スクリプトの形は付け替えない | フックの入力の `cwd` を一時のリポジトリの下の `x/`（`x/.claude/hooks/unreviewed.py run` を置く）にして `python3 .claude/hooks/unreviewed.py run issue-source.sh a`・`bash scripts/claude/issue-source.sh a`。`cwd` 無しも同じ | 前は終了 2・後ろは出力なし。`cwd` が最上位なら TC-01 と同じ | cwd の確かめを外した写しで不合格 |
| TC-05b | 見張り: `test-session.sh` の危ない引数をワイルドカードで書く（F23） | 最上位に `--dangerously-skip-permissions` という名前のファイルを置き、`bash scripts/claude/test-session.sh x [-]-dangerously-skip-permissions`・`… --dangerously-skip-permission?`。TC-02 の形に `[-]-y`・`*`・`?` も足す | 付け替えない（出力なし・中で動く） | `NOT_SIMPLE_RE` から `*?[` を外した写しで付け替わって不合格 |
| TC-18 | スキル・サブエージェントの定義に書いた、外で動かす一覧のスクリプトの呼び出しは、すべて単体の形（F22） | `.claude/skills/*/SKILL.md`・`.claude/agents/*.md` の囲みのコードの行とバッククォートの中で、先頭の語に `bash scripts/claude/<一覧の名前>` があるものを、`$ARGUMENTS`・`I${ISSUE_NUM}`・`I###`→`I999`、`<…>`→`x` に置き換えて `route()` に渡す | 全部に `new_command` が付く（10 件以上） | grill-me の写しに `N=$(bash scripts/claude/issue-source.sh gh-number $ARGUMENTS)` を足すと不合格 |
| TC-10 | 起動役: 名前の確かめ | `other.sh`（一覧に無い）・`../x.sh`・`tests/test_x.sh`・名前なし | どれも終了 2 で動かない | 名前の確かめを外した写しで `other.sh` が動いて不合格 |
| TC-11 | `code-review.sh` のゲート | ゲートに `bash scripts/claude/tests/test_x.sh`（流されたら印）を書いた自動テスト文書で `run_declared_gates` を、変更なし・`other.sh` を変えた状態で流す | 変更なしは印ができる・変更ありは印ができず証跡に `⏭`・`GATE_VERDICT=OK` | `gate_reviewed` を常に真にした写しで、変更ありでも印ができて不合格 |
| TC-12 | フックの起動役（`.claude/hooks/reviewed-hook.sh scripts/claude/hooks/h.py`。`h.py` は自分の `__file__` と標準入力を出す。標準入力に `JSONIN` を渡す） | ① 変更なし ② `h.py` を書き換えた（未コミット） ③ ② のまま `origin/develop` を消した ④ ① で `.git/config` に `core.fsmonitor=touch <印>; false` | ① 終了 0・出力が作業ツリーの `h.py` のパスで始まる ② 終了 0・出力が `$HOME/.cache/claude-reviewed-hooks/<BASE>/scripts/claude/hooks/h.py` で始まり `JSONIN` で終わる・`.complete` がある ③ 終了 0・出力が書き換えた版・標準エラーに `[reviewed-hook]` ④ 印ができない | 常に写し（①で不合格）・差を見ない（②で不合格）・理由を出さない（③で不合格）写し |
| TC-13 | 設定 | `test_settings_permissions.sh` | 外に出す一覧に `bash scripts/claude/*` が無く `python3 .claude/hooks/unreviewed.py run *` がある・allow に起動役・フックはすべて `reviewed-hook.sh` を通す | `bash scripts/claude/*` を戻した写し・フックを素の形に戻した写しで不合格 |
| TC-14 | 基準と安全な `-c` が判定・2 つの起動役・見張りで同じ | 4 つのファイルの文字 | 一致 | 起動役の `-c` を 1 つ消した文字列で不合格 |
| TC-15 | 手順書・一覧 | 下の決定論ゲートの `grep` | すべて 0 | 文言を消した写しで不合格（ゲートの `grep` そのもの） |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i599_unreviewed_scripts.sh
bash scripts/claude/tests/test_settings_permissions.sh
grep -q 'unreviewed.py run' docs/runbooks/danger-ops.md
grep -q 'reviewed-hook.sh' docs/runbooks/danger-ops.md
grep -q 'unreviewed.py run' docs/runbooks/harness-audit.md
! grep -q 'F1 SEV=Medium REPRO=no KIND=guard SECURITY=yes FILE=.claude/settings.json' docs/reviews/backlog/I430.md
```

## 実行記録
- 第 1 版（2026-11-20）: TC-01〜TC-27 を作り、review-gate 5 周の指摘（F1・F2・F4・F7・F8・F11・F12）ごとに足した。fix-loop の再発防止の記録は git の履歴（このファイルの第 1 版）とレビューの記録（`docs/reviews/I599_code_review_*.md`・`docs/reviews/I599_fix_diagnosis_*.md`）にある。要点: シェルの構文を読んで塞ぐ方式は「漏れる」「壊す」が交互に出て収まらなかった（計画書の調査結果 5）
- 第 2 版: 上の「結果」のとおり
- 2026-11-21 fix-loop（第 2 版の 1 回目・F22・F23）: `test_i599_unreviewed_scripts.sh` pass=34 fail=0（TC-18 は直す前に 4 か所を出して不合格になることを確かめた）・`test_i525_skill_sandbox_form`・`test_settings_permissions`・`test_pretooluse_guard_matrix`・`test_guard_must_stop_cases`・`test_i200_guard_narrowing`・`test_i444_guard_gaps` 合格

## 再発防止記録（第 2 版）
- 2026-11-21 F22・F23
  - なぜ失敗したか: 「単体の形だけを外に出す」規則にしたのに、呼び出す側（スキル）を単体の形にそろえる作業と、その確かめを影響範囲に入れていなかった。単体の形の定義からワイルドカードが抜けていた
  - 何を変えたか: スキル 3 本（grill-me・issue-bootstrap・plan-issue）の呼び出しを単体の形に。`NOT_SIMPLE_RE` に `*?[`。TC-05b・TC-18。`danger-ops.md` に書き方の決まり
  - セキュリティ上の考慮点: F23 は承認の確かめのすり抜け。ワイルドカードを含む形は外に出さない（安全側）
  - 次回どう防ぐか: 規則を変えたら、その規則に従う書き手（スキル・手順書）を機械で全部確かめるテストを同時に作る（TC-18）
