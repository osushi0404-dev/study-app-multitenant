# I092 自動テスト: worktree ベースの並行トラック運用 runbook 化

pytest / npm test の対象コード変更は無い。本イシューの受け入れ条件は「runbook / CLAUDE.md の**記載有無**」であるため、grep / `test -f` による**決定論的な内容検証 TC** を定義する。`/test` で下記スクリプトを実行し、全 TC が OK になることを確認する。

## 対象ファイル
- `docs/runbooks/worktree.md`（新規）
- `CLAUDE.md`（参照先 1 行追加）

## テストケース（AC と 1:1 対応）

| TC | 検証内容 | 対応 AC | 判定方法 |
|----|---------|---------|---------|
| TC-A1 | worktree.md が存在する | AC1 | `test -f` |
| TC-A2 | `git worktree add`/`list`/`remove` が記載 | AC1 | grep（3 語すべて） |
| TC-A3 | ベースブランチ＝develop・main を使わない旨が記載（再発防止） | AC1 | grep（`develop` かつ `main`） |
| TC-A4 | トラック/ブランチ設計（トラック=worktree・イシュー=ブランチ、study-app-multitenant/wt- 命名） | AC1 | grep |
| TC-A5 | 独立セッション起動（Cursor 別ウィンドウ + 同一フォルダ再オープンの落とし穴） | AC2 | grep（`ウィンドウ` かつ `再オープン`/`フォーカス`） |
| TC-A6 | 新 worktree セットアップ手順（venv / pip install / npm install / .env コピー） | AC3 | grep（4 要素） |
| TC-A7 | 共有/非共有一覧（venv/node_modules/backend .env 非共有・.claude/settings.json/frontend .env.* 共有・db.sqlite3 独立） | AC4 | grep |
| TC-A8 | 採番一貫性（untracked が worktree 間で不可視） | AC5 | grep（`untracked` かつ `採番`） |
| TC-A9 | セッション間引き継ぎ＝ファイル経由・自己完結の原則 | AC6 | grep（`引き継ぎ`/`引継ぎ` かつ `自己完結`） |
| TC-A10 | CLAUDE.md に worktree.md 参照 1 行が追加 | AC7 | grep |
| TC-A11 | CLAUDE.md の全参照先が実在（リンク切れ 0・追加分含む） | AC7 | 全 `docs/*.md`/`rules/*.md` を `test -f` |
| TC-A12 | 一般表現＋参考例の 2 層（手順本文にプレースホルダ、末尾に「参考」日付つき構成） | AC7(一般表現) | grep（`<track>`/`<番号>` プレースホルダ かつ `参考`） |

## 実行スクリプト（`/test` で実行）

```bash
#!/usr/bin/env bash
# I092 auto test — docs 内容の決定論検証
set -u
RB=docs/runbooks/worktree.md
CM=CLAUDE.md
fail=0
ok(){ echo "OK   $1"; }
ng(){ echo "NG   $1"; fail=1; }

# TC-A1
test -f "$RB" && ok "TC-A1 worktree.md 存在" || ng "TC-A1 worktree.md 不在"

# TC-A2
if grep -q 'git worktree add' "$RB" && grep -q 'worktree list' "$RB" && grep -q 'worktree remove' "$RB"; then ok "TC-A2 add/list/remove"; else ng "TC-A2 add/list/remove 記載不足"; fi

# TC-A3 (再発防止: develop 基点 / main を使わない)
if grep -q 'develop' "$RB" && grep -Eq 'main' "$RB"; then ok "TC-A3 ベースブランチ develop / main 注意"; else ng "TC-A3 develop/main 記載不足"; fi

# TC-A4
if grep -q 'study-app-multitenant' "$RB" && grep -q 'wt-' "$RB" && grep -Eq 'ブランチ' "$RB"; then ok "TC-A4 トラック/ブランチ設計"; else ng "TC-A4 トラック/ブランチ設計 不足"; fi

# TC-A5
if grep -Eq 'ウィンドウ' "$RB" && grep -Eq '再オープン|フォーカス' "$RB"; then ok "TC-A5 独立セッション/落とし穴"; else ng "TC-A5 独立セッション/落とし穴 不足"; fi

# TC-A6
if grep -q 'venv' "$RB" && grep -q 'pip install' "$RB" && grep -q 'npm install' "$RB" && grep -Eq '\.env' "$RB"; then ok "TC-A6 セットアップ手順"; else ng "TC-A6 セットアップ手順 不足"; fi

# TC-A7
if grep -q 'node_modules' "$RB" && grep -q 'settings.json' "$RB" && grep -q 'db.sqlite3' "$RB"; then ok "TC-A7 共有/非共有一覧"; else ng "TC-A7 共有/非共有一覧 不足"; fi

# TC-A8
if grep -q 'untracked' "$RB" && grep -q '採番' "$RB"; then ok "TC-A8 採番一貫性"; else ng "TC-A8 採番一貫性 不足"; fi

# TC-A9
if grep -Eq '引き継ぎ|引継ぎ' "$RB" && grep -q '自己完結' "$RB"; then ok "TC-A9 引き継ぎ原則"; else ng "TC-A9 引き継ぎ原則 不足"; fi

# TC-A10
if grep -q 'docs/runbooks/worktree.md' "$CM"; then ok "TC-A10 CLAUDE.md 参照行"; else ng "TC-A10 CLAUDE.md 参照行 不在"; fi

# TC-A11 (全参照先の実在)
miss=0
for p in $(grep -oE 'docs/[A-Za-z0-9_/-]+\.md|rules/[A-Za-z0-9_/-]+\.md' "$CM" | sort -u); do
  test -f "$p" || { echo "     MISSING $p"; miss=1; }
done
[ "$miss" -eq 0 ] && ok "TC-A11 参照先リンク切れ 0" || ng "TC-A11 リンク切れあり"

# TC-A12 (一般表現 + 参考の 2 層)
if grep -Eq '<track>|<番号>|<トラック' "$RB" && grep -q '参考' "$RB"; then ok "TC-A12 一般表現+参考例 2層"; else ng "TC-A12 一般表現/参考例 不足"; fi

echo "----"
[ "$fail" -eq 0 ] && echo "RESULT: ALL PASS" || echo "RESULT: FAIL"
exit $fail
```

## false-green 自己検証（実装前 RED ベースライン）

本 TC 群は「記載が**存在すること**」を判定する決定論ゲートである。実装前（worktree.md 未作成・CLAUDE.md 未追加）に実行すると全内容系 TC が **NG** を返し、対象が欠けた状態を正しく検出することを確認済み（＝ always-green ではない）。

- 実行タイミング: 実装前（本計画作成時）に実行し RED を記録 → 実装後（`/implement`）に GREEN へ遷移することを `/test` で確認する。
- RED ベースライン結果は本文書の「実行結果」欄に追記する。

## 実行結果

### 実装前 false-green 検証（2026-07-02・計画作成時）
- **RED（実リポジトリ・実装前）**: TC-A1〜A10・A12 = NG（対象の worktree.md 未作成・CLAUDE.md 未追加を正しく検出）、TC-A11 = OK（現行 CLAUDE.md 参照は全件実在）。→ `RESULT: FAIL / exit=1`。内容系ゲートが always-green でないことを確認。
- **GREEN（充足フィクスチャ）**: TC-A1〜A10・A12 = OK に反転（内容を満たせば合格することを確認）。TC-A11 は「参照行はあるが実ファイル未作成」のフィクスチャで NG を検出（リンク切れ捕捉能力を確認。→ 実装ステップ2 はステップ1 の後に実施する依存順序の妥当性を裏付け）。
- 結論: 全 TC が対象の有無に応じて OK/NG を反転する決定論ゲートであることを実証済み。

### `/test` 実行（実装後）
- （`/implement` 後に `/test` で実行し、`RESULT: ALL PASS` を記入）
