#!/bin/bash
# I178 決定論テスト: branch-protection-setup.md の develop・main の設定表と §3 ステップ 3 の手順、
# close スキル step 5.5〜6 を、節ごとに期待する全文と完全一致で比較する。
# 行単位の存在確認では、親スイッチのオフ・矛盾行の併記・空白の違い・コメントで隠す等の後退を
# 取りこぼすため（adversarial 第2周 High）、節の全文を固定する。設定を変えるときは、この期待値と
# 計画書 5-5 の表を同時に更新すること。
# 対象は RUNBOOK / SKILL で差し替え可能（失敗注入用・test_pr_base_sync.sh の TARGET_SCRIPT と同方式）。
set -u

cd "$(git rev-parse --show-toplevel)" || exit 1
RUNBOOK="${RUNBOOK:-docs/runbooks/branch-protection-setup.md}"
SKILL="${SKILL:-.claude/skills/close/SKILL.md}"

PASS=0
FAIL=0

# 開始行（完全一致）の次の行から、終了行（完全一致）の手前までを出力する。
# 開始行・終了行のどちらかが無ければ何も出力しない（節の取り違えで誤って合格しないため）。
section() {
  awk -v start="$2" -v end="$3" '
    $0 == start { on = 1; next }
    on && $0 == end { found = 1; exit }
    on { buf = buf $0 "\n" }
    END { if (found) printf "%s", buf }
  ' "$1" 2>/dev/null
}

# 節の全文が期待値と完全一致すること。不一致なら差分を表示する。
expect_block() {
  local label="$1" actual="$2" expected="$3"
  if [ -z "$actual" ]; then
    echo "NG: $label（節が見つからない）"
    FAIL=$((FAIL + 1))
  elif [ "$actual" = "$expected" ]; then
    echo "OK: $label"
    PASS=$((PASS + 1))
  else
    echo "NG: $label（期待値との差分）"
    diff <(printf '%s\n' "$expected") <(printf '%s\n' "$actual") | sed 's/^/    /'
    FAIL=$((FAIL + 1))
  fi
}

IFS= read -r -d '' EXPECTED_DEVELOP <<'EOF'

| 設定項目 | 値 |
|---------|---|
| Require a pull request before merging | **ON** |
| Required number of approvals before merging | **1** |
| Dismiss stale pull request approvals when new commits are pushed | **ON** |
| Require review from Code Owners | **ON** |
| Require status checks to pass before merging | **ON** |
| Require branches to be up to date before merging | **ON** |
| Required status checks（5件） | 後述 |
| Do not allow bypassing the above settings | **ON** |
| Restrict who can push to matching branches | **ON**（`oshui0404` のみ） |
| Restrict pushes that create matching branches | **ON**（既定のまま） |
| Allow force pushes | OFF |
| Allow deletions | OFF |

EOF

IFS= read -r -d '' EXPECTED_MAIN <<'EOF'

| 設定項目 | 値 |
|---------|---|
| Require a pull request before merging | **ON** |
| Required number of approvals before merging | **1**（本番ゲート） |
| Dismiss stale pull request approvals when new commits are pushed | **ON** |
| Require review from Code Owners | **ON** |
| Require status checks to pass before merging | **ON** |
| Require branches to be up to date before merging | **ON** |
| Required status checks（5件） | 後述 |
| Do not allow bypassing the above settings | **ON** |
| Restrict who can push to matching branches | **ON**（`oshui0404` のみ） |
| Restrict pushes that create matching branches | **ON**（既定のまま） |
| Allow force pushes | OFF |
| Allow deletions | OFF |

develop と main は同じ設定にする（I178）。表の並びは GitHub の設定画面（classic branch protection）の並びに合わせている。

---

EOF

IFS= read -r -d '' EXPECTED_STEP3 <<'EOF'

以下のチェックボックスを設定値一覧に従って ON/OFF します（develop と main で同じ手順）。

**Require a pull request before merging**:
- チェックボックスをオン
- **Require approvals** をオンにし、数値を `1` に設定
- **Dismiss stale pull request approvals when new commits are pushed** をオン
- **Require review from Code Owners** をオン

**Require status checks to pass before merging**:
- チェックボックスをオン
- **Require branches to be up to date before merging** をオン
- **Status checks that are required** の検索ボックスに各ジョブ名を入力して追加（5件）:
  - `Backend Lint & Security`
  - `Backend Tests`
  - `Frontend Type Check`
  - `Frontend Lint & Security`
  - `Frontend Tests`

**Do not allow bypassing the above settings**:
- チェックボックスをオン（管理者も対象）

**Restrict who can push to matching branches**:
- チェックボックスをオン
- 検索ボックスに `oshui0404` を入力して追加する（一覧に `oshui0404` だけが表示されていること）
- **Restrict pushes that create matching branches** はオンのまま（既定）

**Allow force pushes**: オフのまま（デフォルト）

**Allow deletions**: オフのまま（デフォルト）

EOF

IFS= read -r -d '' EXPECTED_CLOSE <<'EOF'
   ```bash
   bash scripts/claude/pr-base-sync.sh final
   # PR番号は省略可（step 0 と同じ・カレントブランチの PR を自動特定。明示指定も可）
   ```
   合格条件は「**BEHIND / DIRTY でない ＋ CI 全グリーン**」（CLEAN は要求しない。develop は
   Code Owners（`oshui0404`）の承認が必須、main は承認 1 件が必須で push・マージできるのは
   `oshui0404` だけの設定のため（main には CODEOWNERS が無い・`docs/runbooks/branch-protection-setup.md`）、
   承認前の正常な最終状態は BLOCKED＝CI 全緑・承認待ちのみ）。
   - exit 0 → step 6 のマージ依頼へ進む
   - exit 1 → STOP してユーザーに報告（マージコンフリクト・CI fail・DRAFT 残留等。自動解決しない）
   - exit 2 → mergeStateStatus=UNKNOWN が継続。値を報告し続行可否をユーザーに確認
EOF


# $(...) は末尾の改行を落とすため、番兵 x を付けて取り出し、後で外す
DEVELOP=$(section "$RUNBOOK" "### develop ブランチ" "### main ブランチ"; echo x); DEVELOP=${DEVELOP%x}
MAIN=$(section "$RUNBOOK" "### main ブランチ" "## 1.5 承認者の限定（I178）"; echo x); MAIN=${MAIN%x}
STEP3=$(section "$RUNBOOK" "### ステップ 3: 各項目を設定" "### ステップ 4: 保存"; echo x); STEP3=${STEP3%x}
CLOSE=$(section "$SKILL" "5.5) base 追従の最終チェック（マージ依頼の直前・必須）:" "6) ユーザーへ GitHub 上で Approve & Merge を依頼（承認とマージはユーザー \`oshui0404\` だけが行える。"; echo x); CLOSE=${CLOSE%x}

expect_block "runbook §1 develop の表" "$DEVELOP" "$EXPECTED_DEVELOP"
expect_block "runbook §1 main の表" "$MAIN" "$EXPECTED_MAIN"
expect_block "runbook §3 ステップ 3" "$STEP3" "$EXPECTED_STEP3"
expect_block "close step 5.5" "$CLOSE" "$EXPECTED_CLOSE"

# close step 6 の 2 行（終了行とその次の行）も固定する
STEP6=$(grep -A1 -xF -- "6) ユーザーへ GitHub 上で Approve & Merge を依頼（承認とマージはユーザー \`oshui0404\` だけが行える。" "$SKILL" 2>/dev/null)
EXPECTED_STEP6="6) ユーザーへ GitHub 上で Approve & Merge を依頼（承認とマージはユーザー \`oshui0404\` だけが行える。
   承認の後に develop への追従などでコミットが入ると承認は取り消されるため、その場合は再承認を依頼する）"
expect_block "close step 6" "$STEP6" "$EXPECTED_STEP6"

echo "---"
if [ "$FAIL" -eq 0 ]; then
  echo "RESULT: OK (${PASS} blocks)"
  exit 0
fi
echo "RESULT: NG (${FAIL} failed / $((PASS + FAIL)) blocks)"
exit 1
