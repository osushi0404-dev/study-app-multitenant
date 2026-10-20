#!/bin/bash
# I178 決定論テスト: branch-protection-setup.md の develop・main の設定表と §3 ステップ 3 の手順、
# close スキル step 5.5〜6 を、節ごとに期待する全文と完全一致で比較する。
# 行単位の存在確認では、親スイッチのオフ・矛盾行の併記・空白の違い・コメントで隠す等の後退を
# 取りこぼすため（adversarial 第2周 High）、節の全文を固定する。
# さらに節の列挙から漏れた部分（他のステップ・§1.5・§4〜§6・同じ見出しの重複）の後退も検知するため
# （adversarial 第3周 High・fix-loop 20261018 案 A）、runbook はファイル全体の SHA-256 も固定する。
# runbook を正当に直すときは、内容をレビューし、計画書 5-5 の表とこのスクリプトの節の期待値を確かめてから、
# RUNBOOK_SHA256 を `sha256sum docs/runbooks/branch-protection-setup.md` の値に更新すること。
# close スキルは他のイシューでも変わるため、ファイル全体は固定せず、step 5.5 の全文と step 6 の先頭 3 行だけを固定する
# （step 6 の 4 行目以降や新しい step 7 への追記は検知しない。設計上の残余）。
# 対象は RUNBOOK / SKILL で差し替え可能（失敗注入用・test_pr_base_sync.sh の TARGET_SCRIPT と同方式）。
set -u

cd "$(git rev-parse --show-toplevel)" || exit 1
RUNBOOK="${RUNBOOK:-docs/runbooks/branch-protection-setup.md}"
SKILL="${SKILL:-.claude/skills/close/SKILL.md}"
CODEOWNERS="${CODEOWNERS:-.github/CODEOWNERS}"
# 秘密情報ではなく runbook の SHA-256（detect-secrets の誤検知を抑止）
RUNBOOK_SHA256="7ca974289148098c70bfd5445156df8d01cb714a6ccea584b2196467cb3a7740"  # pragma: allowlist secret

PASS=0
FAIL=0

# runbook 全体がレビュー済みの版から変わっていないこと
actual_sha=$(sha256sum "$RUNBOOK" 2>/dev/null | cut -d' ' -f1)
if [ "$actual_sha" = "$RUNBOOK_SHA256" ]; then
  echo "OK: runbook 全体がレビュー済みの版と一致（SHA-256）"
  PASS=$((PASS + 1))
else
  echo "NG: runbook がレビュー済みの版から変わっている（SHA-256: ${actual_sha:-取得失敗}）。内容をレビューし、計画書 5-5 と節の期待値を確かめてから RUNBOOK_SHA256 を更新すること"
  FAIL=$((FAIL + 1))
fi

# 見出し行がファイル内にちょうど 1 回だけあること（同じ見出しの重複で節の取り違えを起こさないため）
expect_heading_once() {
  local label="$1" file="$2" line="$3" n
  n=$(grep -cxF -- "$line" "$file" 2>/dev/null)
  if [ "${n:-0}" -eq 1 ]; then
    echo "OK: $label の見出しは 1 回"
    PASS=$((PASS + 1))
  else
    echo "NG: $label の見出しが ${n:-0} 回"
    FAIL=$((FAIL + 1))
  fi
}

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

STEP6_HEAD="6) ユーザーへ GitHub 上で Approve & Merge を依頼（承認とマージはユーザー \`oshui0404\` だけが行える。"

expect_heading_once "runbook §1 develop" "$RUNBOOK" "### develop ブランチ"
expect_heading_once "runbook §1 main" "$RUNBOOK" "### main ブランチ"
expect_heading_once "runbook §1.5" "$RUNBOOK" "## 1.5 承認者の限定（I178）"
expect_heading_once "runbook §3 ステップ 3" "$RUNBOOK" "### ステップ 3: 各項目を設定"
expect_heading_once "runbook §3 ステップ 4" "$RUNBOOK" "### ステップ 4: 保存"
expect_heading_once "close step 5.5" "$SKILL" "5.5) base 追従の最終チェック（マージ依頼の直前・必須）:"
expect_heading_once "close step 6" "$SKILL" "$STEP6_HEAD"

expect_block "runbook §1 develop の表" "$DEVELOP" "$EXPECTED_DEVELOP"
expect_block "runbook §1 main の表" "$MAIN" "$EXPECTED_MAIN"
expect_block "runbook §3 ステップ 3" "$STEP3" "$EXPECTED_STEP3"
expect_block "close step 5.5" "$CLOSE" "$EXPECTED_CLOSE"

# close step 6 の 3 行（見出し行と続く 2 行）も固定する
STEP6=$(grep -A2 -xF -- "$STEP6_HEAD" "$SKILL" 2>/dev/null)
EXPECTED_STEP6="${STEP6_HEAD}
   承認の後に develop への追従などでコミットが入ると承認は取り消されるため、その場合は再承認を依頼する）
   手動テスト文書に、承認の後・マージの前に行う確認がある場合は、まず承認だけを依頼し、その確認を終えてからマージを依頼する。そのような確認がない場合は、承認とマージを一度に依頼する。"
expect_block "close step 6" "$STEP6" "$EXPECTED_STEP6"

# CODEOWNERS は全文を固定する（後に書いた行が優先されるため、末尾に別の所有者の行を足すだけで
# 承認者が入れ替わる。存在確認の grep では見逃す・adversarial 再ステージ第2周 Medium）
IFS= read -r -d '' EXPECTED_CODEOWNERS <<'EOF'
# 全ファイルの所有者をリポジトリ管理者に限定する（I178）。
# develop・main のブランチ保護「Require review from Code Owners」と組み合わせ、
# 管理者以外（bot・外部の人）の承認ではマージ要件を満たさないようにする。
# 設定と理由: docs/runbooks/branch-protection-setup.md
* @oshui0404
EOF
ACTUAL_CODEOWNERS=$(cat "$CODEOWNERS" 2>/dev/null; echo x); ACTUAL_CODEOWNERS=${ACTUAL_CODEOWNERS%x}
expect_block ".github/CODEOWNERS 全文" "$ACTUAL_CODEOWNERS" "$EXPECTED_CODEOWNERS"

echo "---"
if [ "$FAIL" -eq 0 ]; then
  echo "RESULT: OK (${PASS} checks)"
  exit 0
fi
echo "RESULT: NG (${FAIL} failed / $((PASS + FAIL)) checks)"
exit 1
