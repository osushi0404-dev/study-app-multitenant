# I046 自動テスト

## 対象ファイル
- `.claude/skills/plan-issue-review/SKILL.md`
- `.claude/skills/code-review/SKILL.md`

## 自動テスト（ファイル内容確認コマンド）

以下のコマンドを実行し、すべて期待結果を満たすことを確認する。

```bash
PIR=".claude/skills/plan-issue-review/SKILL.md"
CR=".claude/skills/code-review/SKILL.md"

echo "=== plan-issue-review ==="

echo "--- P1 セクション存在確認 ---"
grep -c "P1. 要件適合性" "$PIR"
# 期待値: 1

echo "--- P1 位置確認（ベストプラクティス より前）---"
P1_LINE=$(grep -n "P1. 要件適合性" "$PIR" | head -1 | cut -d: -f1)
BP_LINE=$(grep -n "\*\*ベストプラクティス" "$PIR" | head -1 | cut -d: -f1)
echo "P1_LINE=$P1_LINE BP_LINE=$BP_LINE"
[ "$P1_LINE" -lt "$BP_LINE" ] && echo "OK: P1 がベストプラクティスより前" || echo "NG: 順序が逆"

echo "--- P4 セクション存在確認 ---"
grep -c "P4. テスト妥当性" "$PIR"
# 期待値: 1

echo "--- P2 拡充確認（SSRF）---"
grep -c "SSRF" "$PIR"
# 期待値: 1 以上

echo "--- P2 拡充確認（JWT）---"
grep -c "JWT" "$PIR"
# 期待値: 1 以上

echo "--- P2 拡充確認（監査ログ）---"
grep -c "監査ログ" "$PIR"
# 期待値: 1 以上

echo "--- P6 拡充確認（ローディング）---"
grep -c "ローディング" "$PIR"
# 期待値: 1 以上

echo "--- P6 拡充確認（破壊的操作）---"
grep -c "破壊的操作" "$PIR"
# 期待値: 1 以上

echo "--- P7 拡充確認（アンチパターン）---"
grep -c "アンチパターン" "$PIR"
# 期待値: 1 以上

echo "--- P1/P4 末尾記述確認 ---"
grep -c "問題がなければ「問題なし」と記載する。" "$PIR"
# 期待値: 5（P3・P5・P8・P1・P4）

echo "--- 行数確認 ---"
wc -l < "$PIR"
# 期待値: 500 以下

echo ""
echo "=== code-review ==="

echo "--- P1 セクション存在確認 ---"
grep -c "P1. 要件適合性" "$CR"
# 期待値: 1

echo "--- P1 位置確認（ベストプラクティス より前）---"
P1_LINE=$(grep -n "P1. 要件適合性" "$CR" | head -1 | cut -d: -f1)
BP_LINE=$(grep -n "\*\*ベストプラクティス" "$CR" | head -1 | cut -d: -f1)
echo "P1_LINE=$P1_LINE BP_LINE=$BP_LINE"
[ "$P1_LINE" -lt "$BP_LINE" ] && echo "OK: P1 がベストプラクティスより前" || echo "NG: 順序が逆"

echo "--- P4 セクション存在確認 ---"
grep -c "P4. テスト妥当性" "$CR"
# 期待値: 1

echo "--- P4 位置確認（モダン後・P3 前）---"
P4_LINE=$(grep -n "P4. テスト妥当性" "$CR" | head -1 | cut -d: -f1)
MODERN_LINE=$(grep -n "モダンなウェブアプリ開発" "$CR" | head -1 | cut -d: -f1)
P3_LINE=$(grep -n "P3. データ整合性" "$CR" | head -1 | cut -d: -f1)
echo "P4=$P4_LINE MODERN=$MODERN_LINE P3=$P3_LINE"
[ "$P4_LINE" -gt "$MODERN_LINE" ] && [ "$P4_LINE" -lt "$P3_LINE" ] && echo "OK: P4 がモダン後・P3 前" || echo "NG: 位置が不正"

echo "--- P2 拡充確認（SSRF）---"
grep -c "SSRF" "$CR"
# 期待値: 1 以上

echo "--- P2 拡充確認（JWT）---"
grep -c "JWT" "$CR"
# 期待値: 1 以上

echo "--- P6 拡充確認（ローディング）---"
grep -c "ローディング" "$CR"
# 期待値: 1 以上

echo "--- P7 拡充確認（アンチパターン）---"
grep -c "アンチパターン" "$CR"
# 期待値: 1 以上

echo "--- 行数確認 ---"
wc -l < "$CR"
# 期待値: 500 以下

echo "--- I045 追加分保全確認 ---"
grep -c "P3. データ整合性" "$CR"
grep -c "P5. 運用性" "$CR"
grep -c "P8. コスト" "$CR"
# 期待値: 各 1
```
