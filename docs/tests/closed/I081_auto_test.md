# I081 自動テスト（決定論）

対象: `scripts/claude/hooks/pretooluse_guard.py`（Bash 経路の checkout/restore データ消失防止）、runbook（`common-commands.md`/`danger-ops.md`）、review-agents（`code-reviewer.md`/`plan-reviewer.md`）。

> 実行は必ず `bash scripts/claude/tests/test_pretooluse_checkout_guard.sh`（対話シェルへ貼らない＝ugrep ラッパー回避・既存テスト規約）。

## フック挙動（temp git repo を立てて検証）

| TC | 内容 | 入力（command・stdin JSON `{"tool_name":"Bash","tool_input":{"command":...}}`） | 期待 |
|----|------|------|------|
| TC-G1 | clean ファイルへの `checkout -- file` は素通し | `git checkout -- tracked.txt`（変更なし） | **exit 0** |
| TC-G2 | ブランチ作成は素通し | `git checkout -b newbr` | **exit 0** |
| TC-G3 | **dirty** ファイルへの `checkout -- file` を block | `git checkout -- tracked.txt`（worktree 変更あり） | **exit 2** |
| TC-G4 | **dirty** ファイルへの `restore file` を block | `git restore tracked.txt`（worktree 変更あり） | **exit 2** |
| TC-G5 | **dirty** 時の全体 pathspec `checkout .` を block | `git checkout .` | **exit 2** |
| TC-G6 | ブランチ切替（実在 dirty パスでない名前）は素通し | `git checkout develop`（`develop` という名のファイルなし） | **exit 0** |
| TC-G7 | `DANGER_OK=1` 前置で迂回 | `DANGER_OK=1 git checkout -- tracked.txt`（dirty） | **exit 0** |
| TC-G8a | `restore --staged`（index のみ）は素通し | `git restore --staged tracked.txt`（staged 変更） | **exit 0** |
| TC-G8b | untracked ファイルは素通し | `git checkout -- untracked.txt`（untracked） | **exit 0** |
| TC-G9 | 危険 bash の既存ハードブロック回帰維持 | `git push --force origin x` | **exit 2** |
| TC-G10 | **空白を含むパス**（dirty）も検出して block（`shlex` 担保） | `git checkout -- "my file.txt"`（worktree 変更あり） | **exit 2** |
| TC-G11 | **`&&` 後続**の checkout（dirty）も検出（`shlex` が `&&` を単一トークン化＝実測確認済み） | `git push origin main && git checkout -- g11.txt`（dirty） | **exit 2** |
| **TC-G-FALSEGREEN** | 判定の失敗注入（false-green 排除・**自動化**） | 判定呼び出し行 `target = _git_revert_target_on_dirty(cmd)` を sed で `target = None` に置換した**複製フック**へ dirty を投入 → 続けて実体へ同じ dirty を投入 | 複製＝**exit 0**（素通し）／実体＝**exit 2**（block）。両者の差で「block は判定行に依存」を機械裏取り |

### false-green の二重担保
- **対検証**: TC-G1（clean→exit0）と TC-G3（dirty→exit2）は **同一コマンド** `git checkout -- tracked.txt`。block が「常時」ではなく **dirty 条件依存**であることを対で裏取り（常時 block の過剰反応も、常時 pass の取りこぼしも排除）。
- **注入検証**: TC-G-FALSEGREEN で判定を外すと dirty でも素通しになることを確認。

## テストスクリプト（新規 `scripts/claude/tests/test_pretooluse_checkout_guard.sh`）
```bash
#!/usr/bin/env bash
# I081: pretooluse_guard.py の checkout/restore データ消失防止を決定論検証する。
# 実行: bash scripts/claude/tests/test_pretooluse_checkout_guard.sh
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
GUARD="$REPO_ROOT/scripts/claude/hooks/pretooluse_guard.py"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cd "$TMP" || exit 1
git init -q
git config user.email t@example.com
git config user.name tester
printf 'orig\n' > tracked.txt
git add tracked.txt
git commit -qm init

json() { printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$1"; }
run()  { echo "$(json "$1")" | python3 "$GUARD" >/dev/null 2>&1; echo $?; }

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }

# clean baseline
ck "G1 clean checkout -- file" 0 "$(run 'git checkout -- tracked.txt')"
ck "G2 branch create -b"       0 "$(run 'git checkout -b newbr')"
git checkout -q -            2>/dev/null || true   # 元ブランチへ戻す（-b で移っていた場合）

# make worktree dirty
printf 'changed\n' >> tracked.txt
ck "G3 dirty checkout -- file" 2 "$(run 'git checkout -- tracked.txt')"
ck "G4 dirty restore file"     2 "$(run 'git restore tracked.txt')"
ck "G5 dirty checkout ."       2 "$(run 'git checkout .')"
ck "G6 branch switch name"     0 "$(run 'git checkout develop')"
ck "G7 DANGER_OK bypass"       0 "$(run 'DANGER_OK=1 git checkout -- tracked.txt')"

# staged-only change -> restore --staged は素通し
git add tracked.txt
ck "G8a restore --staged"      0 "$(run 'git restore --staged tracked.txt')"

# untracked -> 素通し
printf 'x\n' > untracked.txt
ck "G8b untracked checkout"    0 "$(run 'git checkout -- untracked.txt')"

# 危険 bash 回帰
ck "G9 force push exit2"       2 "$(run 'git push --force origin x')"

# 空白を含むパス（dirty）も shlex で検出
printf 'orig\n' > "my file.txt"
git add "my file.txt"
git commit -qm spacefile
printf 'changed\n' >> "my file.txt"
# JSON 内のダブルクオートは \" でエスケープして渡す
ck "G10 dirty spaced path"     2 "$(echo '{"tool_name":"Bash","tool_input":{"command":"git checkout -- \"my file.txt\""}}' | python3 "$GUARD" >/dev/null 2>&1; echo $?)"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
```

## runbook / review-agent 文言（grep・決定論）

| TC | 内容 | コマンド（概念） | 期待 |
|----|------|------|------|
| TC-D1 | `common-commands.md` に複合禁止・`; echo "exit=$?"` 不可・Read 閲覧が明記 | `grep -q` 複数キーワード（`単体` / `束ねない` 等） | 全一致（exit 0） |
| TC-D2 | `common-commands.md` に「原則・例外許容」が明記（完全禁止でない） | `grep -q '原則'` ＋ `grep -q '例外'` | exit 0 |
| TC-D3 | `danger-ops.md` に checkout/restore データ消失注意・`common-commands.md` からの相互参照 | `danger-ops.md` に `checkout` 注記 ＋ `common-commands.md` に `danger-ops` 参照 | exit 0 |
| TC-D4 | `code-reviewer.md`/`plan-reviewer.md` に「複合化」「checkout/restore 取り消し」gate が追加 | 各ファイルに2キーワード | exit 0 |
| TC-D5 | **追記文言にイシュー番号が含まれない**（一般形） | 追記 4 ファイルの diff 範囲を `grep -E 'I0[0-9]{2}'` | **一致 0 件**（失敗注入: `I079` を埋めると検出＝NG） |

> TC-D1〜D5 は実装後に実コマンドを確定し、`bash` 実行で記録する。TC-D5 は否定系のため `I079` 等を一時挿入すると NG（非ゼロ）になることを注入確認してから採用する。

## 結果記録
- **/implement（TDD・2026-06-28 実測）**: `bash scripts/claude/tests/test_pretooluse_checkout_guard.sh` → **pass=14 fail=0**。Red（実装前）で G3/G4/G5/G10/G11・FALSEGREEN real-blocks が FAIL することを確認 → Green で全 PASS。
  - TC-G1〜G11: **PASS** / TC-G-FALSEGREEN（注入で素通し・実体で block の対）: **PASS**
  - TC-D1〜D5（runbook/review-agent 文言・イシュー番号不在）: **PASS**（grep -F で確認・追記差分の `+` 行にイシュー番号なし）
  - 既存 Edit/Write ask 経路（高リスク → ask）の非退行も確認（`backend/requirements.txt` → ask）
- pytest / Jest / E2E: 非該当（アプリコード変更なし）
- /test での最終確認（環境パリティ・手動統合 M1〜6）: ⏳
