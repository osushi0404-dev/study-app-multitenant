#!/bin/bash
# I178 決定論テスト: branch-protection-setup.md の develop・main の設定表と §3 ステップ 3 の手順、
# close スキル step 5.5 の develop/main の書き分けを、節ごとに行の完全一致で検証する。
# 文言がファイルのどこかにあるだけでは合格にしない（§1.5 や §5 に同じ語があっても表の後退を検知する）。
# 対象は RUNBOOK / SKILL で差し替え可能（失敗注入用・test_pr_base_sync.sh の TARGET_SCRIPT と同方式）。
set -u

cd "$(git rev-parse --show-toplevel)" || exit 1
RUNBOOK="${RUNBOOK:-docs/runbooks/branch-protection-setup.md}"
SKILL="${SKILL:-.claude/skills/close/SKILL.md}"

PASS=0
FAIL=0
ok() { echo "OK: $1"; PASS=$((PASS + 1)); }
ng() { echo "NG: $1"; FAIL=$((FAIL + 1)); }

# 開始行（完全一致）の次の行から、終了行（完全一致）の手前までを出力する
section() {
  awk -v start="$2" -v end="$3" '
    $0 == start { on = 1; next }
    on && $0 == end { exit }
    on { print }
  ' "$1"
}

# 節の中に、その行がちょうど 1 回だけある（矛盾する重複行・欠落の両方を検知する）
expect_once() {
  local label="$1" body="$2" line="$3" n
  n=$(printf '%s\n' "$body" | grep -cxF -- "$line")
  if [ "$n" -eq 1 ]; then ok "$label: $line"; else ng "$label: $line（${n} 件）"; fi
}

# 節の中で、その設定項目の行がちょうど 1 行だけある（ON 行と OFF 行の併記を検知する）
expect_item_once() {
  local label="$1" body="$2" item="$3" n
  n=$(printf '%s\n' "$body" | grep -cF -- "| $item |")
  if [ "$n" -eq 1 ]; then ok "$label: 項目「$item」は 1 行"; else ng "$label: 項目「$item」が ${n} 行"; fi
}

COMMON_ROWS=(
  "| Require a pull request before merging | **ON** |"
  "| Dismiss stale pull request approvals when new commits are pushed | **ON** |"
  "| Require review from Code Owners | **ON** |"
  "| Require status checks to pass before merging | **ON** |"
  "| Require branches to be up to date before merging | **ON** |"
  "| Do not allow bypassing the above settings | **ON** |"
  "| Restrict who can push to matching branches | **ON**（\`oshui0404\` のみ） |"
  "| Restrict pushes that create matching branches | **ON**（既定のまま） |"
  "| Allow force pushes | OFF |"
  "| Allow deletions | OFF |"
)
ITEMS=(
  "Require a pull request before merging"
  "Required number of approvals before merging"
  "Dismiss stale pull request approvals when new commits are pushed"
  "Require review from Code Owners"
  "Do not allow bypassing the above settings"
  "Restrict who can push to matching branches"
)

check_table() {
  local label="$1" body="$2" approvals="$3" row item
  if [ -z "$body" ]; then ng "$label: 節が見つからない"; return; fi
  expect_once "$label" "$body" "$approvals"
  for row in "${COMMON_ROWS[@]}"; do expect_once "$label" "$body" "$row"; done
  for item in "${ITEMS[@]}"; do expect_item_once "$label" "$body" "$item"; done
}

DEVELOP=$(section "$RUNBOOK" "### develop ブランチ" "### main ブランチ")
MAIN=$(section "$RUNBOOK" "### main ブランチ" "## 1.5 承認者の限定（I178）")
check_table "develop 表" "$DEVELOP" "| Required number of approvals before merging | **1** |"
check_table "main 表" "$MAIN" "| Required number of approvals before merging | **1**（本番ゲート） |"

STEP3=$(section "$RUNBOOK" "### ステップ 3: 各項目を設定" "### ステップ 4: 保存")
if [ -z "$STEP3" ]; then
  ng "ステップ 3: 節が見つからない"
else
  for line in \
    "- **Require approvals** をオンにし、数値を \`1\` に設定" \
    "- **Dismiss stale pull request approvals when new commits are pushed** をオン" \
    "- **Require review from Code Owners** をオン" \
    "- 検索ボックスに \`oshui0404\` を入力して追加する（一覧に \`oshui0404\` だけが表示されていること）" \
    "- **Restrict pushes that create matching branches** はオンのまま（既定）" \
    "- チェックボックスをオン（管理者も対象）"; do
    expect_once "ステップ 3" "$STEP3" "$line"
  done
  # Restrict の見出しの直後の行がオン指示であること（見出しだけ残してオフにする後退を検知する）
  if printf '%s\n' "$STEP3" | grep -A1 -xF "**Restrict who can push to matching branches**:" | tail -1 | grep -qxF -- "- チェックボックスをオン"; then
    ok "ステップ 3: Restrict who can push の直後がオン指示"
  else
    ng "ステップ 3: Restrict who can push の直後がオン指示でない"
  fi
  if printf '%s\n' "$STEP3" | grep -q "オフのまま.*承認"; then
    ng "ステップ 3: 承認をオフのままにする旧手順が残っている"
  else
    ok "ステップ 3: 承認をオフのままにする旧手順なし"
  fi
fi

# close スキル step 5.5: 行頭の空白を除いて連結し、develop と main の書き分けの順序を検証する
STEP55=$(section "$SKILL" "5.5) base 追従の最終チェック（マージ依頼の直前・必須）:" "6) ユーザーへ GitHub 上で Approve & Merge を依頼（承認とマージはユーザー \`oshui0404\` だけが行える。" | sed 's/^[[:space:]]*//' | tr -d '\n')
if printf '%s' "$STEP55" | grep -qF -- "develop はCode Owners（\`oshui0404\`）の承認が必須、main は承認 1 件が必須で push・マージできるのは\`oshui0404\` だけの設定のため"; then
  ok "close step 5.5: develop と main の書き分け"
else
  ng "close step 5.5: develop と main の書き分けが無い・入れ替わっている"
fi

echo "---"
if [ "$FAIL" -eq 0 ]; then
  echo "RESULT: OK (${PASS} assertions)"
  exit 0
fi
echo "RESULT: NG (${FAIL} failed / $((PASS + FAIL)) assertions)"
exit 1
