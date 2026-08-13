# I146 自動テスト: 外部コード寄稿の受付方針明示と cross-repo PR ゲート

対象: `scripts/claude/hooks/pretooluse_guard.py`・`scripts/claude/pr-base-sync.sh`・`.claude/settings.json`・`.claude/skills/close/SKILL.md`・`CONTRIBUTING.md`・`SECURITY.md`・`.github/pull_request_template.md`・`docs/runbooks/workflow.md`

**合否判定インターフェース**: すべて exit code に統一する（合格 = exit 0 / 不合格 = 非ゼロ）。出力値の目視比較は合否基準にしない。不在判定は `! grep -q ...` の形で書き、合格時に exit 0 を返す。

**実行環境**: ホスト（`test -f /.dockerenv` = exit 1 で確認済み）。Python 3.12.3 / gh 2.88.1。

---

## 計画時ベースライン（TDD Red・2026-08-04 実測）

| 検証 | コマンド | 実測 |
|---|---|---|
| 方針文書が不在 | `ls CONTRIBUTING.md SECURITY.md` | **exit 2**（両方不在）✅ Red |
| cross-repo 判定が未実装 | `grep -l "isCrossRepository" scripts/claude/pr-base-sync.sh .claude/skills/close/SKILL.md scripts/claude/hooks/pretooluse_guard.py` | **ヒット 0（exit 1）** ✅ Red |
| MCP matcher が未登録 | `grep -c "mcp__github__merge_pull_request" .claude/settings.json` | **0** ✅ Red |
| guard が `gh pr merge` を素通し | guard へ stdin JSON 投入 | **exit 0** ✅ Red |
| 新規テストが不在 | `ls scripts/claude/tests/test_pretooluse_gh_pr_guard.sh` | **exit 2** ✅ Red |
| PVR が無効 | `gh api repos/osushi0404-dev/study-app-multitenant/private-vulnerability-reporting --jq .enabled` | **false** ✅ Red |
| 既存テスト（回帰基準） | `bash scripts/claude/tests/test_pr_base_sync.sh` | `RESULT: OK (16/16 cases, 23 assertions)` |
| 既存テスト（回帰基準） | `bash scripts/claude/tests/test_pretooluse_push_guard.sh` | `pass=87 fail=0` |

---

## TC-01: `pr-base-sync.sh` の cross-repo ガード（T1〜T21）

方式: 一時ディレクトリの `gh` / `git` スタブを PATH 先頭に挿して実行（実 GitHub 非依存）。`CROSS_VALUE` / `GH_FAIL_CROSS` でケースごとに fork 判定値を注入する。

```bash
bash scripts/claude/tests/test_pr_base_sync.sh
```

| 期待 | 内容 |
|---|---|
| exit 0 | 全ケース PASS（`RESULT: OK (21/21 cases, ...)`） |
| T1〜T16 | 従来どおりの終了コード（自前 PR＝`CROSS_VALUE` 既定 `false`）→ AC-7 |
| T17 | sync・cross-repo → exit 1、かつ `merge` が呼ばれない（`log_not "merge"`）→ AC-5 |
| T18 | final・cross-repo → exit 1 → AC-5 |
| T19 | 照会失敗（`GH_FAIL_CROSS=1`）→ exit 1 → AC-6 |
| T20 | 空値 → exit 1 → AC-6 |
| T21 | 想定外値（`hoge`）→ exit 1 → AC-6 |

## TC-02: TC-01 の false-green 裏取り（判定行の注入）

`pr-base-sync.sh` のコピーを作り cross-repo 判定を無効化（`case "$CROSS" in` の `true)` 分岐を `exit 0` 化）し、`TARGET_SCRIPT` で差し替えて TC-01 を実行する。

```bash
sed 's/^  true)$/  true) exit 0;;\n  __disabled__)/' scripts/claude/pr-base-sync.sh > /tmp/claude-1000/guard_nocross.sh
TARGET_SCRIPT=/tmp/claude-1000/guard_nocross.sh bash scripts/claude/tests/test_pr_base_sync.sh
```

| 期待 | 内容 |
|---|---|
| **非ゼロ終了** | `NG: T17 ...` が出力され、テストが壊れた実装を不合格にする（合格してしまうなら T17 は false-green） |

（注入の sed 式は実装時に対象行へ合わせて確定する。要件は「cross-repo 判定行だけを無効化し、他の分岐を壊さないこと」。）

## TC-03: `pretooluse_guard.py` の cross-repo ポリシー（G1〜G22）

```bash
bash scripts/claude/tests/test_pretooluse_gh_pr_guard.sh
```

| # | 入力 | CROSS_VALUE | 期待 | AC |
|---|---|---|---|---|
| G1 | `gh pr merge 257 --squash` | true | exit 2 | AC-8 |
| G2 | `gh pr merge 257` | false | exit 0 | AC-12 |
| G3 | `gh pr ready 257` | true | ASK | AC-8 |
| G4 | `gh pr edit 257 --base develop` | true | ASK | AC-8 |
| G5 | `gh pr review 257 --approve` | true | ASK | AC-8 |
| G6 | `gh pr review 257 --comment --body x` | true | exit 0 | AC-8 |
| G7 | `gh pr close 257` | true | exit 0 | AC-8 |
| G8 | `gh pr comment 257 --body x` | true | exit 0 | AC-8 |
| G9 | `gh pr view 257 --json state` | true | exit 0 | AC-8 |
| G10 | `gh pr checks 257` | true | exit 0 | AC-8 |
| G11 | `gh pr merge`（識別子なし） | true | exit 2 | AC-8 |
| G12 | `gh pr merge https://github.com/o/r/pull/257` | true | exit 2 | AC-8 |
| G13 | MCP `mcp__github__merge_pull_request` | true | exit 2 | AC-9 |
| G14 | MCP `mcp__github__update_pull_request_branch` | true | ASK | AC-9 |
| G15 | MCP `mcp__github__create_pull_request_review`（event=APPROVE） | true | ASK | AC-9 |
| G16 | MCP `mcp__github__create_pull_request_review`（event=COMMENT） | true | exit 0 | AC-9 |
| G17 | `gh pr merge 257`（`GH_FAIL_CROSS=1`） | - | ASK（block しない） | AC-11 |
| G18 | `gh pr ready 257` | false | exit 0 | AC-12 |
| G19 | MCP `mcp__github__merge_pull_request` | false | exit 0 | AC-12 |
| G20 | `ls -la` | true | exit 0（`gh` を呼ばない） | AC-12 |
| G21 | `DANGER_OK=1 gh pr merge 257` | true | exit 0（明示エスケープ） | AC-8 |
| G22 | `gh pr merge 257 && rm -rf x` | true | exit 2（既存 hard-block が先に効く） | 回帰 |
| G23 | MCP `merge_pull_request`（`pull_number` なし） | true | ASK（照会せず降格） | AC-17 |
| G24 | MCP `mcp__github__get_pull_request`（対象外ツール） | true | exit 0（`gh` を呼ばない） | AC-18 |

MCP ケースの `tool_input` キー名は**スネークケース**（`owner` / `repo` / `pull_number`、レビューは加えて `body` / `event`）。対象 3 ツールの JSON Schema を実取得して確認済み（計画書 S9）。テストと実装の双方でこのキー名を使う。

判定方法は `test_pretooluse_push_guard.sh` と同型（exit code、ASK は exit 0 かつ stdout に `"permissionDecision": "ask"` を含むこと）。Bash 用は `runj`、MCP 用は `runm` ヘルパを使う（計画書 §5-3 に定義）。

| 期待 | 内容 |
|---|---|
| exit 0 | `pass=<全件> fail=0` |

## TC-04: TC-03 の false-green 裏取り（判定関数ごとの注入）

| # | 注入（guard のコピーに sed で適用） | 検証 | 期待 |
|---|---|---|---|
| FG-A | `_gh_pr_target` の def 直後に `return None` | G1 | exit 0（＝素通し。注入で壊れることを確認） |
| FG-B | 注入なし（実体） | G1 | exit 2 |
| FG-C | `_pr_is_cross_repo` の def 直後に `return False, None`（**2-タプル**。`return False` だと `cross, head = ...` のアンパックで `TypeError` → exit 1 となり、注入テストが偽陰性になる） | G1 | exit 0 |
| FG-D | `_mcp_pr_target` の def 直後に `return None` | G13 | exit 0 |
| FG-E | 注入なし（実体） | G13 | exit 2 |

FG-A / FG-C / FG-D が exit 0 を返し、かつ FG-B / FG-E が exit 2 を返すことをテスト内で assert する（テスト自体の exit code に畳み込む）。

## TC-05: 構文検証

```bash
python3 -m py_compile scripts/claude/hooks/pretooluse_guard.py
bash -n scripts/claude/pr-base-sync.sh
bash -n scripts/claude/tests/test_pr_base_sync.sh
bash -n scripts/claude/tests/test_pretooluse_gh_pr_guard.sh
python3 -c "import json,sys; json.load(open('.claude/settings.json'))"
```

| 期待 | 全コマンド exit 0 |
|---|---|

## TC-06: 文書・設定の必須文言（存在・無改変）

すべて `grep -q`（合格 = exit 0）で判定する。

```bash
grep -q "not accept" CONTRIBUTING.md
grep -q "受け付けていません" CONTRIBUTING.md
grep -q "SECURITY.md" CONTRIBUTING.md
grep -q "Issue" CONTRIBUTING.md
grep -q "Report a vulnerability" SECURITY.md
! grep -qE "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" SECURITY.md
grep -q "CONTRIBUTING.md" .github/pull_request_template.md
grep -q "isCrossRepository" .claude/skills/close/SKILL.md
grep -q "外部（fork）からの PR の扱い" docs/runbooks/workflow.md
grep -q "mcp__github__merge_pull_request" .claude/settings.json
grep -q "mcp__github__update_pull_request_branch" .claude/settings.json
grep -q "mcp__github__create_pull_request_review" .claude/settings.json
```

無改変の確認（既存 hook 登録が消えていないこと・AC-10 / R7）:

```bash
[ "$(grep -c 'pretooluse_guard.py' .claude/settings.json)" -eq 3 ]
grep -q '"matcher": "Bash"' .claude/settings.json
grep -q '"matcher": "Edit|Write|MultiEdit|NotebookEdit"' .claude/settings.json
```

| 期待 | 全コマンド exit 0 |
|---|---|

**false-green 裏取り**: 各 grep パターンが「変更前のファイル」に対して不一致になることを確認する（上記ベースライン表で実測済み: `isCrossRepository` ヒット 0・`mcp__github__merge_pull_request` 0 件・両文書不在）。SECURITY.md のメールアドレス不在判定（`! grep -qE`）は、ダミーの `x@example.com` を含む一時ファイルに対して**非ゼロ終了**することを確認する。

## TC-07: Private vulnerability reporting の有効化

```bash
[ "$(gh api repos/osushi0404-dev/study-app-multitenant/private-vulnerability-reporting --jq .enabled)" = "true" ]
```

| 期待 | exit 0（ベースラインは `false` のため Red から Green への遷移を確認できる） |
|---|---|

**有効化の実施者（2026-08-13 判明）**: 有効化 API は admin 権限を要求する。稼働中の `gh` 認証は bot アカウント `osushi0404-bot`（`permissions.admin = false`）のため `gh api -X PUT .../private-vulnerability-reporting` は **HTTP 404** で失敗する（GitHub は権限不足を 404 で返す）。
したがって有効化は**リポジトリ管理者アカウントでの操作**が必要:
- GitHub UI: リポジトリ **Settings** → **Advanced Security**（旧 Security & analysis）→ **Private vulnerability reporting** → **Enable**
- または管理者アカウントの `gh` で `gh api -X PUT repos/osushi0404-dev/study-app-multitenant/private-vulnerability-reporting`

有効化後、上記 TC-07 コマンドを再実行して exit 0 を確認する（読み取り側は bot トークンでも可）。

## TC-08: 既存テストの回帰

```bash
bash scripts/claude/tests/test_pretooluse_push_guard.sh
bash scripts/claude/tests/test_pr_base_sync.sh
```

| 期待 | 両方 exit 0。push guard は `pass=87 fail=0` 以上（新規 assert を足さないため 87 のまま） |
|---|---|

---

## 実行記録

（`/test` 実行時に記入する）

| TC | 実行日時 | 結果 | 備考 |
|---|---|---|---|
| TC-01 | 2026-08-05 実装時 | ✅ PASS | `RESULT: OK (21/21 cases, 30 assertions)`。Red は 6 NG（T17 の merge 副作用・T18 の push 副作用を含む）→ 実装後 全 OK |
| TC-02 | 2026-08-05 実装時 | ✅ PASS | 注入式は `sed 's/^  true)$/  true) ;;\n  __nevermatch__)/'` に確定。注入版で `RESULT: NG (3 件 / pass 27)`・非ゼロ終了（T17 exit・T17 merge 副作用・T18 push 副作用が NG）= 壊れた実装を確実に不合格にする |
| TC-03 | 2026-08-05 実装時 | ✅ PASS | `pass=34 fail=0`（G1〜G27）。Red は `pass=18 fail=16` |
| TC-04 | 2026-08-05 実装時 | ✅ PASS | FG-A/FG-C/FG-D が素通し（0）、FG-B/FG-E が block（2）。TC-03 の exit code に畳み込み済み |
| TC-05 | 2026-08-05 実装時 | ✅ PASS | `py_compile` / `bash -n`（3 ファイル）/ `json.load(settings.json)` すべて exit 0 |
| TC-06 | 2026-08-05 実装時 | ✅ PASS | 19 項目すべて OK（必須文言 14・無改変 4・false-green 裏取り 1） |
| TC-07 | 2026-08-13 | ⏸ 保留 | Private vulnerability reporting は現状 `{"enabled":false}`。ユーザー承認を得て `gh api -X PUT` を実行したが、bot アカウントに admin 権限がなく **HTTP 404**（詳細は TC-07 節の「有効化の実施者」）。**リポジトリ管理者による GitHub UI 操作待ち** |
| TC-08 | 2026-08-05 実装時 | ✅ PASS | push guard `pass=87 fail=0`・worktree guard `pass=27 fail=0`・checkout guard `pass=14 fail=0`（回帰なし） |
