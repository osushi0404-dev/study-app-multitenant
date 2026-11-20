# I599 自動テスト: サンドボックスの中から scripts/claude/ に書いたスクリプトをレビュー前に外で流せる穴を塞ぐ（第 2 版）

実行コマンド: `bash scripts/claude/tests/test_i599_unreviewed_scripts.sh`（CI の Harness Tests が `run-all.sh` で流す）

結果:
- 第 2 版は実装前のため未実行

## テストケース
共通の土台: 一時フォルダに git リポジトリを作り、`scripts/claude/` の小さな写し（一覧の名前の `issue-source.sh`〔流されたら印のファイルを書き、引数を出す〕・`test-session.sh`・一覧に無い `other.sh`・`tests/test_x.sh`・`hooks/h.py`）・`.claude/hooks/` の本物の写し・`.gitignore`（`*.tmp`・`igndir/`）を置いてコミットし、`refs/remotes/origin/develop` をそのコミットに向ける。見張りは本物の `scripts/claude/hooks/pretooluse_guard.py` を `CLAUDE_PROJECT_DIR=<一時のリポジトリ>` で JSON を渡して流す。`HOME` は一時フォルダ。

| TC | 何を確かめるか | 入力・操作 | 期待（終了コードで判定） | 失敗の注入（FG） |
|---|---|---|---|---|
| TC-01 | 見張り: 一覧の名前の単体の形は起動役の形に付け替える | `bash scripts/claude/issue-source.sh body I1`（`timeout` 7 つき） | `updatedInput.command` が `bash .claude/hooks/reviewed-run.sh issue-source.sh body I1`・`timeout` が残る・`permissionDecision` なし | 付け替えを外した判定の写しで不合格 |
| TC-02 | 見張り: 単体でない形・一覧に無い名前は何もしない（中で動く） | `timeout 5 bash scripts/claude/issue-source.sh x`・`X=1 bash …`・`bash … $(true)`・`` bash … `x` ``・`bash … \| cat`・`bash … >o`・`bash …; ls`・`{ bash …; }`・`bash scripts/claude/other.sh`・`bash scripts/claude/../../x.sh`・`bash scripts/claude/tests/run-all.sh x.sh`・`git commit -m "bash scripts/claude/issue-source.sh"` | どれも出力なし・終了 0 | 単体の確かめを外した写しで `$(true)` の形が付け替えられて不合格 |
| TC-03 | 再発防止（I597 の形）: 新しく書いたスクリプトは外に出ない | 追跡していない `scripts/claude/new.sh` を置き `bash scripts/claude/new.sh`・`bash .claude/hooks/reviewed-run.sh new.sh` | 前は見張りの出力なし（中）・後ろは起動役が終了 2 で `new.sh` は動かない | 一覧に `new.sh` を足した写しで不合格 |
| TC-04 | 見張り: 起動役を単体でない形で流すと止める | `bash .claude/hooks/reviewed-run.sh issue-source.sh x; ls`・`… $(true)`・`X=1 bash .claude/hooks/reviewed-run.sh …`・`… >o` | どれも見張りが終了 2 | 止める確かめを外した写しで不合格 |
| TC-05 | 見張り: `test-session.sh` の引数 | スクリプトの形と起動役の形で、許可の表の引数（`--model haiku --permission-mode default`）・`--settings /tmp/s.json`・`--settings=/tmp/s.json`・`--mcp-config m.json`・`--permission-mode bypassPermissions`・`--setting-sources user`・`--setting-sources user --settings .gitignore`・`--setting-sources user --settings .claude/settings.json` | 表の引数と最後の形は承認なし（スクリプトの形は付け替えあり）。ほかは `ask`（スクリプトの形は `updatedInput` も付く） | 表を「何でも可」にした写しで不合格 |
| TC-06 | 見張り: 判定を読み込めないとき | 判定のファイルを壊した写しで `bash .claude/hooks/reviewed-run.sh issue-source.sh x`・`bash scripts/claude/issue-source.sh x` | 前は終了 2（止める）・後ろは出力なし（中） | 読み込めないときも通す写しで不合格 |
| TC-07 | 起動役: レビュー前の中身が無ければ一覧のスクリプトを動かす | `bash .claude/hooks/reviewed-run.sh issue-source.sh a "b c"` | 終了 0・印のファイルができる・引数がそのまま届く | 起動役が常に止める写しで不合格 |
| TC-08 | 起動役: レビュー前の中身があれば止める | ① 追跡済みの `other.sh` を書き換え ② 追跡していない `scripts/claude/n.sh` ③ 無視される `scripts/claude/evil.tmp` のそれぞれで TC-07 と同じ | どれも終了 3・印のファイルができない・標準エラーに `! bash scripts/claude/issue-source.sh` の案内 | 差を見ない写し（①）・無視されるファイルを数えない写し（③）で不合格 |
| TC-09 | 起動役: 基準を求められないときは止める | `origin/develop` を消して TC-07 と同じ | 終了 3・印ができない | 基準の失敗を「なし」に倒す写しで不合格 |
| TC-10 | 起動役: 名前の確かめ | `other.sh`（一覧に無い）・`../x.sh`・`tests/test_x.sh`・名前なし | どれも終了 2 で動かない | 名前の確かめを外した写しで `other.sh` が動いて不合格 |
| TC-11 | `code-review.sh` のゲート | ゲートに `bash scripts/claude/tests/test_x.sh`（流されたら印）を書いた自動テスト文書で `run_declared_gates` を、変更なし・`other.sh` を変えた状態で流す | 変更なしは印ができる・変更ありは印ができず証跡に `⏭`・`GATE_VERDICT=OK` | `gate_reviewed` を常に真にした写しで、変更ありでも印ができて不合格 |
| TC-12 | フックの起動役（第 1 版の TC-13〜TC-15 を残す） | 変更なし・`hooks/h.py` を変えた・基準なし・`.git/config` に `core.fsmonitor` | 作業ツリー／写し（`.complete`・標準入力が届く）／作業ツリーと理由。`core.fsmonitor` は動かない | 第 1 版と同じ |
| TC-13 | 設定 | `test_settings_permissions.sh` | 外に出す一覧に `bash scripts/claude/*` が無く `bash .claude/hooks/reviewed-run.sh *` がある・allow に起動役・フックはすべて `reviewed-hook.sh` を通す | `bash scripts/claude/*` を戻した写し・フックを素の形に戻した写しで不合格 |
| TC-14 | 基準と安全な `-c` が判定・2 つの起動役・見張りで同じ | 4 つのファイルの文字 | 一致 | 起動役の `-c` を 1 つ消した文字列で不合格 |
| TC-15 | 手順書・一覧 | 下の決定論ゲートの `grep` | すべて 0 | 文言を消した写しで不合格（ゲートの `grep` そのもの） |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i599_unreviewed_scripts.sh
bash scripts/claude/tests/test_settings_permissions.sh
grep -q 'reviewed-run.sh' docs/runbooks/danger-ops.md
grep -q 'reviewed-hook.sh' docs/runbooks/danger-ops.md
grep -q 'I599' docs/runbooks/harness-audit.md
! grep -q 'F1 SEV=Medium REPRO=no KIND=guard SECURITY=yes FILE=.claude/settings.json' docs/reviews/backlog/I430.md
```

## 実行記録
- 第 1 版（2026-11-20）: TC-01〜TC-27 を作り、review-gate 5 周の指摘（F1・F2・F4・F7・F8・F11・F12）ごとに足した。fix-loop の再発防止の記録は git の履歴（このファイルの第 1 版）とレビューの記録（`docs/reviews/I599_code_review_*.md`・`docs/reviews/I599_fix_diagnosis_*.md`）にある。要点: シェルの構文を読んで塞ぐ方式は「漏れる」「壊す」が交互に出て収まらなかった（計画書の調査結果 5）
- 第 2 版: 実装前のため未実行
