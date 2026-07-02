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
| TC-A3 | ベースブランチ＝develop・main を使わない旨が記載（再発防止） | AC1 | grep（`develop` かつ `main` の**文脈アンカー** `main.{0,4}(は\|を\|初期\|ブランチ\|使わ)`。`domain`/`remains` 等の部分一致を排除） |
| TC-A4 | トラック/ブランチ設計（トラック=worktree・イシュー=ブランチ、study-app-multitenant/wt- 命名） | AC1 | grep |
| TC-A5 | 独立セッション起動（Cursor 別ウィンドウ + 同一フォルダ再オープンの落とし穴） | AC2 | grep（`ウィンドウ` かつ `再オープン`/`フォーカス`） |
| TC-A6 | 新 worktree セットアップ手順（`docker compose up` + backend `.env` コピー。venv/pip/npm は非使用） | AC3 | grep（`docker compose up` かつ `.env`） |
| TC-A7 | 共有/非共有一覧（node_modules はコンテナ管理・`.claude/settings.json` 共有・dev DB は Postgres） | AC4 | grep（`node_modules` かつ `settings.json` かつ `Postgres`） |
| TC-A13 | 並行実行の衝突（ホスト固定ポート衝突・`COMPOSE_PROJECT_NAME`） | AC(並行衝突) | grep（`COMPOSE_PROJECT_NAME` かつ `5432`/`ポート`） |
| TC-A14 | `.env` 欠落の静かな insecure 既定起動の警告（安全性） | AC3 | **近接** grep（`.env` 行の -A3 近傍に `insecure`/`既定`。分散配置での誤通過を排除） |
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

# TC-A3 (再発防止: develop 基点 / main を使わない) ※main は文脈アンカーで部分一致(domain/remains 等)を排除
if grep -q 'develop' "$RB" && grep -Eq 'main.{0,4}(は|を|初期|ブランチ|使わ)' "$RB"; then ok "TC-A3 ベースブランチ develop / main 注意"; else ng "TC-A3 develop/main 記載不足"; fi

# TC-A4
if grep -q 'study-app-multitenant' "$RB" && grep -q 'wt-' "$RB" && grep -Eq 'ブランチ' "$RB"; then ok "TC-A4 トラック/ブランチ設計"; else ng "TC-A4 トラック/ブランチ設計 不足"; fi

# TC-A5
if grep -Eq 'ウィンドウ' "$RB" && grep -Eq '再オープン|フォーカス' "$RB"; then ok "TC-A5 独立セッション/落とし穴"; else ng "TC-A5 独立セッション/落とし穴 不足"; fi

# TC-A6 (Docker: docker compose up + backend .env コピー)
if grep -q 'docker compose up' "$RB" && grep -Eq '\.env' "$RB"; then ok "TC-A6 セットアップ手順(docker)"; else ng "TC-A6 セットアップ手順 不足"; fi

# TC-A7 (共有/非共有: node_modules コンテナ管理・settings.json 共有・Postgres)
if grep -q 'node_modules' "$RB" && grep -q 'settings.json' "$RB" && grep -Eq 'Postgres|postgres' "$RB"; then ok "TC-A7 共有/非共有一覧"; else ng "TC-A7 共有/非共有一覧 不足"; fi

# TC-A13 (並行衝突: 固定ポート + COMPOSE_PROJECT_NAME)
if grep -q 'COMPOSE_PROJECT_NAME' "$RB" && grep -Eq '5432|ポート' "$RB"; then ok "TC-A13 並行ポート衝突"; else ng "TC-A13 並行ポート衝突 不足"; fi

# TC-A14 (.env 欠落の静かな insecure 既定起動の警告) ※近接一致: .env 行の近傍に警告があること
if grep -A3 -E '\.env' "$RB" 2>/dev/null | grep -Eq 'insecure|既定'; then ok "TC-A14 .env 静かな insecure 既定 警告"; else ng "TC-A14 .env 警告 不足"; fi

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
if grep -Eq '<track>|<番号>' "$RB" && grep -q '参考' "$RB"; then ok "TC-A12 一般表現+参考例 2層"; else ng "TC-A12 一般表現/参考例 不足"; fi

echo "----"
[ "$fail" -eq 0 ] && echo "RESULT: ALL PASS" || echo "RESULT: FAIL"
exit $fail
```

## false-green 自己検証（実装前 RED ベースライン）

本 TC 群は「記載が**存在すること**」を判定する決定論ゲートである。実装前（worktree.md 未作成・CLAUDE.md 未追加）に実行すると全内容系 TC が **NG** を返し、対象が欠けた状態を正しく検出することを確認済み（＝ always-green ではない）。

- 実行タイミング: 実装前（本計画作成時）に実行し RED を記録 → 実装後（`/implement`）に GREEN へ遷移することを `/test` で確認する。
- RED ベースライン結果は本文書の「実行結果」欄に追記する。

## 実行結果

### 実装前 false-green 検証（2026-07-02・計画作成時／Docker 是正版 TC で再検証）
- **RED（実リポジトリ・実装前）**: 内容系 TC（A1〜A10・A13・A12）= NG（worktree.md 未作成・CLAUDE.md 未追加を正しく検出）、TC-A11 = OK（現行 CLAUDE.md 参照は全件実在）。→ `RESULT: FAIL / exit=1`。内容系ゲートが always-green でないことを確認。
- **GREEN（充足フィクスチャ）**: A1〜A10・A13・A12 = OK に反転（内容を満たせば合格）。TC-A11 は「参照行はあるが実ファイル未作成」のフィクスチャで NG を検出（リンク切れ捕捉能力を確認 → 実装ステップ2 をステップ1 の後に行う依存順序の妥当性を裏付け）。
- 結論: 全 TC（A1〜A14）が対象の有無に応じて OK/NG を反転する決定論ゲートであることを実証済み（Docker 是正後の TC-A6=docker compose/TC-A7=Postgres/TC-A13=ポート衝突/TC-A14=.env 静かな insecure 既定警告 も RED→GREEN 反転を確認）。

### plan-issue-review 指摘（Warning 2件）への対応と decoy 反証（2026-07-02）
独立プランレビュー（判定: OK）で指摘された false-green 弱点 2 件を修正し、デコイで反証可能性を実証:
- **TC-A3**: `grep 'main'` の部分一致を文脈アンカー `main.{0,4}(は|を|初期|ブランチ|使わ)` に厳格化。デコイ（`domain`/`remains`/`maintain` を含むが main 警告を欠く）で **NG**、正フィクスチャで OK を確認（`domain` 誤通過を排除）。
- **TC-A14**: `.env` と `insecure|既定` の独立 grep を **近接一致** `grep -A3 '\.env' | grep 'insecure|既定'` に厳格化。デコイ（`.env` と `insecure` を 5 行離す）で **NG**、正フィクスチャで OK を確認。
- **TC-A12**（Info）: 非対称な `<トラック` を削除し、実際に使うプレースホルダ `<track>`/`<番号>` に限定。

### `/test` 実行（実装後）
- （`/implement` 後に `/test` で実行し、`RESULT: ALL PASS` を記入）
