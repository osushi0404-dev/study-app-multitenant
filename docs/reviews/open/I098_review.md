# I098 レビュー: 全 worktree 横断採番スクリプトへの一元化

## 基本情報
- 関連イシュー: #184 / Draft PR: #188
- 対象計画書: docs/plans/open/plan_I098.md
- レビュー目的: 採番の全 worktree 横断化により二重採番を根治し、採番権威を単一化する。人手規律（primary で採番）への依存を撤廃する。
- 期待する成果:
  - `scripts/claude/next-issue-num.sh` が全 worktree 横断＋git 履歴で一意番号を算出（再現ケース回避）。
  - 採番 bash の重複 4 箇所がスクリプト呼び出しに一元化。
  - worktree.md §8 の人手規律撤廃。
  - I094 decoy 反証を含む決定論テストが green。

## 変更概要
イシュー採番を全 worktree 横断（untracked 含む）＋git 履歴の forward cross-scan に一元化する `scripts/claude/next-issue-num.sh` を新規作成し、issue-flow.md（3 箇所）・issue-bootstrap/SKILL.md（1 箇所）の重複採番 bash を同スクリプト呼び出しに置換。worktree.md §8 の人手規律（primary で採番）を撤廃し権威単一化に更新。決定論テスト `test_next_issue_num.sh`（21 アサーション）を追加。

## 変更点
- **新規** `scripts/claude/next-issue-num.sh`: `git worktree list` 全 worktree の docs/issues FS 最大（untracked 含む）＋`git log --all`（`:/docs/issues` 固定＝CWD 非依存）で `max+1` を 3 桁 stdout 出力。アンカー正規表現 `/I?\K\d+(?=\.md$)`（I094 decoy 排除）。read-only（I095 整合）。gate なし（false-green/過剰・脆弱のため不採用）。
- **新規** `scripts/claude/tests/test_next_issue_num.sh`: TC-N1（再現ケース）〜N7（CWD 非依存回帰・横断 false-green 反証）＋TC-DOC1〜4。**21/21 PASS**。
- `docs/runbooks/issue-flow.md`（3 箇所）・`.claude/skills/issue-bootstrap/SKILL.md`（1 箇所）: 採番 bash をスクリプト呼び出しに置換。
- `docs/runbooks/worktree.md` §8: 人手規律撤廃 → 権威単一化。
- **plan フェーズの敵対的レビューで是正**: (1) git 履歴 pathspec の CWD 相対バグ（サブディレクトリ実行で履歴脱落→二重採番）を `:/` 固定で解消、(2) 当初計画の gate（発火不能な false-green／実リポジトリで `I042` open/closed 共存を誤検出する脆弱版）を棄却。

## 影響範囲
- Backend/Frontend/DB: なし
- Config/Infra: `scripts/claude/next-issue-num.sh`（新規）・`scripts/claude/tests/test_next_issue_num.sh`（新規）・`docs/runbooks/issue-flow.md`・`docs/runbooks/worktree.md`・`.claude/skills/issue-bootstrap/SKILL.md`

## テスト結果
- 自動: `bash scripts/claude/tests/test_next_issue_num.sh` → **pass=21 fail=0**（TC-N1〜N7・TC-DOC1〜4）。実リポジトリで `next-issue-num.sh` → `099`（root/subdir 一致）。pytest/Jest/E2E は非該当（bash＋markdown のみ）。
- 手動: `docs/tests/open/I098_manual_test.md` 全 4 項目 **OK**（No1 出力 099/exit0・No2 21 PASS・No3 横断 max 098+1=099 一致・No4 記述整合）。Human 実施項目なし（全て Claude 実施可）。
- code-review: **VERDICT OK**（決定論ゲート exit0・omission-lint OK・CI 全 pass）。

## 計画との差分
- なし / あり（理由）

## ロールバック
- 新規 2 ファイル削除 ＋ 文書 3 ファイルを revert（DB 非関与）
