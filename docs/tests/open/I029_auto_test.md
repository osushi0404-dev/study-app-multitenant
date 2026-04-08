# I029 自動テスト

## 対象
`scripts/claude/hooks/posttooluse_check.py` のユニットテスト

---

## 自動テストの方針

本イシューの変更対象は以下の 3 ファイル（設定ファイル・スクリプトのみ）：
- `.claude/settings.json`
- `scripts/claude/hooks/posttooluse_check.py`（新規）
- `scripts/claude/hooks/pretooluse_guard.py`（HEAD push 検出追加・push 系チェックを re.match に統一）

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

### AT-1 実行結果（2026-04-08）

| ケース | 期待 | 結果 |
|--------|------|------|
| AT-1-1: 正常な .py | exit 0 | ✅ exit 0 |
| AT-1-2: 構文エラーの .py | exit 1 | ✅ exit 1（SyntaxError フィードバックあり） |
| AT-1-3: 正常な .json | exit 0 | ✅ exit 0 |
| AT-1-4: 不正な .json | exit 1 | ✅ exit 1（JSON エラーフィードバックあり） |
| AT-1-5: 対象外 .md | exit 0 | ✅ exit 0 |
| AT-1-6: 存在しないファイル | exit 0 | ✅ exit 0（サイレント） |

---

## AT-2: pretooluse_guard.py の動作確認（既存 + HEAD push 検出 + re.match 誤検知防止）

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

# re.match 誤検知防止: コミットメッセージ内に保護ブランチ名が含まれても通過する
echo '{"tool_name": "Bash", "tool_input": {"command": "git commit -m \"fix: protect develop and main branches\""}}' \
  | python3 scripts/claude/hooks/pretooluse_guard.py
echo "exit: $?"   # 期待: 0（commit コマンドのためブロックされない）
```

### AT-2 実行結果（2026-04-08）

| ケース | 期待 | 結果 |
|--------|------|------|
| AT-2-1: 正常なコマンド | exit 0 | ✅ exit 0 |
| AT-2-2: 既存 deny（git push origin develop） | exit 2 | ✅ exit 2 |
| AT-2-3: HEAD push（feature ブランチ上） | exit 0 | ✅ exit 0 |
| AT-2-4: 誤検知防止（commit メッセージに develop を含む） | exit 0 | ✅ exit 0 |
| AT-2-5: HEAD push（develop ブランチ上） | exit 2 | ⚠️ 実行不可（下記参照） |

**AT-2-5 について**

`git checkout develop` すると `pretooluse_guard.py` 自体も develop 版（HEAD チェックなし）に切り替わるため、feature ブランチで追加したロジックをマージ前に統合テストすることは構造的に不可能。

ロジックの正しさはインラインデバッグで確認済み：
- `re.match(r"git\s+push\b.*\bHEAD\b", "git push -u origin HEAD")` → マッチ
- `git rev-parse --abbrev-ref HEAD`（develop 上）→ `"develop"`
- `"develop" in ("develop", "main")` → `True` → ブロック処理に到達

**マージ後に develop 上で AT-2-5 を実行して最終確認すること。**
