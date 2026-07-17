#!/usr/bin/env bash
# I117: auto_test テンプレート（docs/tests/templates/auto_test_template.md）と
# omission-lint（scripts/claude/code-review.sh の omission_lint()・I084）の整合を検証する恒久テスト。
# テンプレ既定に沿って書いた文書が omission-lint で誤 HIGH になる罠（I098/I109 で実発生）の退行を検知する。
# 合格 = exit 0。失敗した TC を stderr に出力して非ゼロ終了する（実行不可は exit 2）。
set -u

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "NG: git リポジトリ外では実行できません" >&2; exit 2; }
TPL="$REPO_ROOT/docs/tests/templates/auto_test_template.md"
CR="$REPO_ROOT/scripts/claude/code-review.sh"
[ -f "$TPL" ] || { echo "NG: テンプレート不在: $TPL" >&2; exit 2; }
[ -f "$CR" ] || { echo "NG: code-review.sh 不在: $CR" >&2; exit 2; }

TMP_DOC="$(mktemp)"
TMP_DECOY="$(mktemp)"
trap 'rm -f "$TMP_DOC" "$TMP_DECOY"' EXIT

# omission_lint() の複製（code-review.sh の I084-OM-GREP と同一パターン。乖離は TC-07 で機械検知）
OM_PATTERN='(bash[[:space:]]+scripts/claude/tests/[^[:space:]]+\.sh|grep[[:space:]]+-[qL]|python3[[:space:]]+-m[[:space:]]+json\.tool|bash[[:space:]]+-n[[:space:]]|python3[[:space:]]+-m[[:space:]]+py_compile)'
omission_lint() {
  local f="$1" outside hit
  outside=$(awk '
    /^## 決定論ゲート（自動実走）/ { insec=1; next }
    /^## / && insec { insec=0 }
    /^```/ { fence = !fence; next }
    { if (!insec && fence) print }
  ' "$f")
  hit=$(printf '%s\n' "$outside" | grep -oE "$OM_PATTERN" | head -1)
  if [ -n "$hit" ]; then echo HIGH; else echo OK; fi
}

# ゲートセクション外／内のテキスト抽出（fence 行を含む生テキスト）
outside_section() {
  awk '
    /^## 決定論ゲート（自動実走）/ { insec=1; next }
    /^## / && insec { insec=0 }
    { if (!insec) print }
  ' "$TPL"
}
inside_section() {
  awk '
    /^## 決定論ゲート（自動実走）/ { insec=1; next }
    /^## / && insec { insec=0 }
    { if (insec) print }
  ' "$TPL"
}

FAIL=0
ok() { echo "OK: $1"; }
ng() { echo "NG: $1" >&2; FAIL=1; }

# TC-01: ゲートセクション外に fenced ```bash/```sh ブロックが 0 件（heavy 含む全 fenced が対象・AC1）
fence_count=$(outside_section | grep -cE '^```(bash|sh)[[:space:]]*$')
if [ "$fence_count" -eq 0 ]; then
  ok "TC-01 ゲートセクション外の fenced bash/sh ブロック 0 件"
else
  ng "TC-01 ゲートセクション外に fenced bash/sh ブロックが ${fence_count} 件存在（誤 HIGH の罠が復活）"
fi

# TC-02: 冒頭誘導注記の存在（ゲートセクションへの誘導＋omission-lint 言及・AC2）
if outside_section | grep -q 'omission-lint' && outside_section | grep -q 'ゲート系コマンド'; then
  ok "TC-02 冒頭誘導注記（ゲートセクション誘導＋omission-lint 言及）が存在"
else
  ng "TC-02 冒頭誘導注記が見つからない（ゲート系コマンドの誘導 or omission-lint 言及の欠落）"
fi

# TC-03: allowlist 6 キーワードがゲートセクション内コメントに全て存在し、セクション外に列挙の複製が無い（AC3）
tc03=0
for kw in 'bash scripts/claude/tests/' 'grep -q' 'grep -L' 'python3 -m json.tool' 'bash -n' 'python3 -m py_compile'; do
  if ! inside_section | grep -qF -- "$kw"; then
    ng "TC-03 ゲートセクション内コメントに allowlist キーワード欠落: ${kw}"
    tc03=1
  fi
done
for dup in 'scripts/claude/tests' 'json.tool' 'py_compile'; do
  if outside_section | grep -qF -- "$dup"; then
    ng "TC-03 ゲートセクション外に allowlist 列挙の複製あり: ${dup}（集約方針違反・乖離ポイント増）"
    tc03=1
  fi
done
[ "$tc03" -eq 0 ] && ok "TC-03 allowlist 列挙はゲートセクション内 1 箇所に集約（6/6 キーワード存在・複製 0）"

# TC-04: 是正後テンプレそのもの → omission-lint OK（AC4）
v=$(omission_lint "$TPL")
if [ "$v" = "OK" ]; then
  ok "TC-04 テンプレそのものが omission-lint OK"
else
  ng "TC-04 テンプレそのものが omission-lint ${v}（期待: OK）"
fi

# TC-05: ゲートセクションに実コマンドを書いた生成文書 → omission-lint OK（AC4）
sed 's|^# 例:.*|bash scripts/claude/tests/test_auto_test_template_lint.sh|' "$TPL" > "$TMP_DOC"
v=$(omission_lint "$TMP_DOC")
if [ "$v" = "OK" ]; then
  ok "TC-05 ゲートセクションに実コマンドを記載した生成文書が omission-lint OK"
else
  ng "TC-05 生成文書が omission-lint ${v}（期待: OK・テンプレ通りに書くと HIGH の罠が残存）"
fi

# TC-06: decoy 反証 — セクション外 fenced に allowlist コマンドを注入 → HIGH を検知（false-green 防止・AC5）
awk '
  /^## 決定論ゲート（自動実走）/ && !inj {
    print "```bash"
    print "bash scripts/claude/tests/test_decoy_injected.sh"
    print "```"
    inj=1
  }
  { print }
' "$TPL" > "$TMP_DECOY"
v=$(omission_lint "$TMP_DECOY")
if [ "$v" = "HIGH" ]; then
  ok "TC-06 decoy（セクション外 fenced への allowlist コマンド注入）を HIGH として検知"
else
  ng "TC-06 decoy が ${v}（期待: HIGH・検知器が機能していない false-green 状態）"
fi

# TC-07: 本スクリプトの複製パターンが code-review.sh の I084-OM-GREP 行と一致（複製乖離検知）
cr_pattern=$(sed -n "/I084-OM-GREP/s/.*grep -oE '\([^']*\)'.*/\1/p" "$CR")
if [ -z "$cr_pattern" ]; then
  ng "TC-07 code-review.sh から I084-OM-GREP パターンを抽出できない（マーカー消失または構造変更）"
elif [ "$cr_pattern" = "$OM_PATTERN" ]; then
  ok "TC-07 複製パターンが code-review.sh の I084-OM-GREP と一致"
else
  ng "TC-07 複製パターンが code-review.sh と乖離（code-review.sh: ${cr_pattern}）"
fi

if [ "$FAIL" -eq 0 ]; then
  echo "✅ test_auto_test_template_lint: 全 TC 合格"
  exit 0
else
  echo "❌ test_auto_test_template_lint: 失敗 TC あり" >&2
  exit 1
fi
