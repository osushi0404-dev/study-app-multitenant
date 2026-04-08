# I029 自動テスト

## 対象
`scripts/claude/hooks/posttooluse_check.py` のユニットテスト

---

## 自動テストの方針

本イシューの変更対象は以下の 3 ファイル（設定ファイル・スクリプトのみ）：
- `.claude/settings.json`
- `scripts/claude/hooks/posttooluse_check.py`（新規）
- `scripts/claude/hooks/pretooluse_guard.py`（HEAD push 検出追加）

Django/React のアプリケーションコードへの変更はないため、pytest / Jest によるテストは不要。
各スクリプトの動作確認は以下のコマンドで手動実行する。

---

## AT-1: posttooluse_check.py の基本動作確認（手動実行）

以下のコマンドで各ケースを確認する（CI には組み込まない）：

```bash
# 正常な Python ファイル → ゼロ終了
echo '{"tool_name": "Edit", "tool_input": {"file_path": "/tmp/test_ok.py"}, "tool_response": {}}' \
  | python3 scripts/claude/hooks/posttooluse_check.py
echo "exit: $?"   # 期待: 0

# 構文エラーのある Python ファイル → 非ゼロ終了
echo 'def foo(' > /tmp/test_broken.py
echo '{"tool_name": "Edit", "tool_input": {"file_path": "/tmp/test_broken.py"}, "tool_response": {}}' \
  | python3 scripts/claude/hooks/posttooluse_check.py
echo "exit: $?"   # 期待: 1

# 正常な JSON ファイル → ゼロ終了
echo '{"key": "value"}' > /tmp/test_ok.json
echo '{"tool_name": "Write", "tool_input": {"file_path": "/tmp/test_ok.json"}, "tool_response": {}}' \
  | python3 scripts/claude/hooks/posttooluse_check.py
echo "exit: $?"   # 期待: 0

# 不正な JSON ファイル → 非ゼロ終了
echo '{"key": }' > /tmp/test_broken.json
echo '{"tool_name": "Write", "tool_input": {"file_path": "/tmp/test_broken.json"}, "tool_response": {}}' \
  | python3 scripts/claude/hooks/posttooluse_check.py
echo "exit: $?"   # 期待: 1

# 対象外ファイル（.md） → ゼロ終了
echo '{"tool_name": "Edit", "tool_input": {"file_path": "/tmp/test.md"}, "tool_response": {}}' \
  | python3 scripts/claude/hooks/posttooluse_check.py
echo "exit: $?"   # 期待: 0

# ファイルが存在しない → ゼロ終了（サイレント）
echo '{"tool_name": "Edit", "tool_input": {"file_path": "/tmp/nonexistent.py"}, "tool_response": {}}' \
  | python3 scripts/claude/hooks/posttooluse_check.py
echo "exit: $?"   # 期待: 0
```

---

## AT-2: pretooluse_guard.py の動作確認（既存 + HEAD push 検出）

```bash
# 正常なコマンド → ゼロ終了
echo '{"tool_name": "Bash", "tool_input": {"command": "git status"}}' \
  | python3 scripts/claude/hooks/pretooluse_guard.py
echo "exit: $?"   # 期待: 0

# 既存の危険なコマンド → 非ゼロ終了
echo '{"tool_name": "Bash", "tool_input": {"command": "git push origin develop"}}' \
  | python3 scripts/claude/hooks/pretooluse_guard.py
echo "exit: $?"   # 期待: 2

# HEAD push — develop ブランチ上で実行した場合 → 非ゼロ終了
# 前提: git checkout develop してから実行すること
echo '{"tool_name": "Bash", "tool_input": {"command": "git push -u origin HEAD"}}' \
  | python3 scripts/claude/hooks/pretooluse_guard.py
echo "exit: $?"   # 期待: 2（develop 上のため）

# HEAD push — feature ブランチ上で実行した場合 → ゼロ終了
# 前提: feature ブランチにチェックアウトしてから実行すること
echo '{"tool_name": "Bash", "tool_input": {"command": "git push -u origin HEAD"}}' \
  | python3 scripts/claude/hooks/pretooluse_guard.py
echo "exit: $?"   # 期待: 0（feature ブランチのためブロックされない）
```
