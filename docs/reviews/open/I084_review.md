# レビュー文書: I084 code-review の決定論ゲートを実走化

## 基本情報
- **関連イシュー**: #167
- **関連計画書**: plan_I084
- **作成日**: 2026-07-01
- **ステータス**: レビュー待ち

---

## レビューチェックリスト

### scripts/claude/code-review.sh — 新規 helper（source 可能・ガード前）
- [ ] `extract_gate_commands`: `## 決定論ゲート（自動実走）` 配下の単一 ```bash ブロックのみ抽出（コメント・空行・見出し外を除外）
- [ ] `classify_gate`: 判定順が「**HEAVY（先頭コマンド anchored）** → allowlist(メタ文字ガード付き) ALLOW → その他 UNSAFE」
- [ ] HEAVY は先頭コマンド判定（部分一致でない）: `grep -q "npm test done" log` は ALLOW（false-negative 回帰・TC-CL9）
- [ ] allowlist は `bash scripts/claude/tests/*.sh` / `grep ` / `python3 -m json.tool` / `bash -n ` / `python3 -m py_compile ` のみ、かつチェーンメタ文字（`;` `&&` `||` `|` `` ` `` `$(` `>`）なしのときのみ ALLOW
- [ ] doc-sync ゲートは plain grep（存在=`grep -q` / 不在=`grep -L`）で allowlist に収まる
- [ ] `run_one_gate`: `timeout 120 bash -c` で実走し exit code を返す（command not found / timeout も非ゼロ）
- [ ] `run_declared_gates`: ALLOW 実走・exit≠0 で `GATE_VERDICT=BLOCKER`・UNSAFE も BLOCKER・HEAVY は委譲記録（FAIL でない）
- [ ] `run_declared_gates`: UNSAFE を `bash -c` に渡さない（破壊系非実走・TC-RUN8）
- [ ] `omission_lint`: 宣言セクション外の allowlist パターン行のみ HIGH・heavy/裸語は非検出
- [ ] `verdict_rank` / `combine_verdict`: `BLOCKER>HIGH>OK` の最大選択
- [ ] `inject_gate_result`: 末尾 `^VERDICT:` を FINAL に置換＋証跡見出しを prepend

### scripts/claude/code-review.sh — 本体配線
- [ ] `claude -p` 前に `run_declared_gates` / `omission_lint` を実行し CONTEXT へ証跡注入
- [ ] `claude -p` 保存後に `combine_verdict` → `inject_gate_result` で VERDICT 決定論上書き
- [ ] 既存 `case "$(detect_code_verdict "$REVIEW_FILE")"` を変更していない（書換え後の値を読む）
- [ ] `commit_review_artifact` / PR コメント投稿 / ブランチガードが無回帰

### .claude/review-agents/code-reviewer.md
- [ ] 「決定論ゲートは注入済み実 exit code を使い、読解で PASS 断定しない」旨を追記
- [ ] 証跡（コマンド＋exit code）を照合備考に併記する指示

### docs/tests/templates/auto_test_template.md
- [ ] `## 決定論ゲート（自動実走）` セクション規約を追加（許可コマンド・チェーン不可・heavy は /test 委譲の注記）
- [ ] 既存の heavy 例示ブロックが omission-lint 自傷を起こさない（allowlist 非該当）

### scripts/claude/tests/test_review_gates.sh（新規）
- [ ] `REVIEW_LIB_SOURCE_ONLY=1 source` で新規関数を単体テスト
- [ ] auto_test.md の TC-EX/CL/RUN/CB/OM/INJ/WIRE/DOC/FG/SYN を網羅
- [ ] TC-FG 群で否定/回帰 TC の「壊すと NG・実版で OK」の対を確認済み（false-green 禁止）

### ドッグフーディング
- [ ] `docs/tests/open/I084_auto_test.md` が `## 決定論ゲート（自動実走）` で `test_review_gates.sh` を宣言

### 無回帰
- [ ] `bash scripts/claude/tests/test_review_verdict.sh` PASS 維持（fail=0）

---

## セキュリティ観点
- [ ] コマンド実行面が positive allowlist ＋ チェーン拒否 ＋ heavy 除外で多層防御されている
- [ ] UNSAFE 宣言ゲートが実走されない（fail-closed BLOCKER・破壊系ブロック）

## 判定
- 判定: （レビュー時に記入）
