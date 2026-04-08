# plan_I029_settings_json_allow拡充とPostToolUseフック追加

## 基本情報
- **計画書ID**: plan_I029_settings_json_allow拡充とPostToolUseフック追加
- **関連イシュー**: #60 (I029)
- **作成根拠資料**: docs/proposals/I026_ai_dev_improvement_proposal.md（改善案 A）
- **実装後評価**: （未作成）
- **作成日**: 2026-04-08

---

## 1. 背景/目的

`.claude/settings.json` の `permissions.allow` に未登録のコマンドが多く、日常的なワークフロー中に確認ダイアログが頻発している。`git fetch`・`git rev-parse --abbrev-ref HEAD` などの読み取り専用コマンドでも毎回ユーザー承認を求められ、スキル（/plan-issue・/close 等）が途中で止まる。

allow を拡充してユーザーの介入を「本当に重要な判断」のみに絞ることで、スキルが途切れなく動くようにする。
また PostToolUse フックを追加し、ファイル編集後に構文エラーを即時検出できる仕組みを整える。

---

## 2. 受け入れ条件

- [ ] `git fetch`・`git rev-parse --abbrev-ref HEAD` が確認ダイアログなしで実行される
- [ ] `git push -u origin <feature branch>` が確認ダイアログなしで実行される
- [ ] `python3 scripts/*` が確認ダイアログなしで実行される
- [ ] `git push -u origin develop` / `git push -u origin main` は deny で引き続きブロックされる
- [ ] develop/main ブランチ上で `git push -u origin HEAD` を実行してもブロックされる
- [ ] Edit/Write 後に `.py`・`.json`・`.yaml` の構文チェックが自動で走る
- [ ] 構文エラーがある場合、PostToolUse フックが非ゼロ終了して Claude にフィードバックされる
- [ ] 既存の deny ルール・pretooluse_guard.py の動作が変わらない

---

## 3. 影響範囲

- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra:
  - `.claude/settings.json`（allow・deny・hooks の変更）
  - `scripts/claude/hooks/posttooluse_check.py`（新規作成）
  - `scripts/claude/hooks/pretooluse_guard.py`（HEAD push 検出の軽微な追加）

---

## 4. 変更点一覧

### 4-1. `.claude/settings.json` — allow への追加

| 追加するパターン | 用途 |
|----------------|------|
| `Bash(git fetch *)` | リモートブランチ状態の確認（/plan-issue・/close 等で使用） |
| `Bash(git rev-parse *)` | ブランチ名取得（`--abbrev-ref HEAD` 等）・コミット解決 |
| `Bash(git push -u origin *)` | 新ブランチの初回 push（`-u` フラグ付き） |
| `Bash(python3 scripts/*)` | hooks スクリプトの手動テスト実行 |
| `Bash(python3 -m py_compile *)` | Python 構文チェックの直接実行 |
| `Bash(python3 -m json.tool *)` | JSON の構文確認・整形 |

### 4-2. `.claude/settings.json` — deny への追加

| 追加するパターン | 理由 |
|----------------|------|
| `Bash(git push -u origin develop)` | allow に `git push -u origin *` を追加することで生じるギャップを塞ぐ |
| `Bash(git push -u origin main)` | 同上 |
| `Bash(git push -u origin HEAD)` | `git push -u origin HEAD` は develop/main 上でも文字列に branch 名が現れないため、既存 deny・guard.py の正規表現をすり抜ける |

※ `git push -u origin HEAD` は guard.py の修正（4-5）と組み合わせた二重防御とする。

### 4-3. `.claude/settings.json` — PostToolUse フック追加

```json
"PostToolUse": [
  {
    "matcher": "Edit|Write",
    "hooks": [
      {
        "type": "command",
        "command": "python3 \"$CLAUDE_PROJECT_DIR\"/scripts/claude/hooks/posttooluse_check.py"
      }
    ]
  }
]
```

### 4-4. `scripts/claude/hooks/posttooluse_check.py`（新規作成）

**チェック対象と内容**:

| 拡張子 | チェック内容 | 使用する方法 |
|--------|------------|------------|
| `.py` | Python 構文チェック | `py_compile.compile(path, doraise=True)` |
| `.json` | JSON 構文チェック | `with open(path) as f: json.load(f)` |
| `.yaml` / `.yml` | YAML 構文チェック | `with open(path) as f: yaml.safe_load(f)` |
| その他 | スキップ | — |

**終了コードの設計**:
- 構文エラーあり → 非ゼロ終了（Claude へフィードバック、修正を促す）
- 構文エラーなし / 対象外ファイル → ゼロ終了（サイレント）
- ファイルが存在しない / 読み取り不可 → ゼロ終了（サイレント。Hook 自体のエラーで作業を止めない）

**フック入力（PostToolUse の JSON 仕様）**:
```json
{
  "tool_name": "Edit",
  "tool_input": { "file_path": "/absolute/path/to/file.py" },
  "tool_response": { ... }
}
```
`tool_input.file_path` から対象ファイルパスを取得する。

### 4-5. `scripts/claude/hooks/pretooluse_guard.py` — HEAD push 検出を追加

`import subprocess` をファイル先頭に追加し、`if not danger_ok:` ブロック内の push チェック直後に以下を追加する：

```python
# git push ... HEAD を develop/main ブランチ上で実行した場合をブロック
if re.search(r"\bgit\s+push\b.*\bHEAD\b", cmd, re.I):
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip() in ("develop", "main"):
            _block(
                f"push via HEAD to protected branch '{result.stdout.strip()}' is forbidden",
                raw
            )
    except Exception:
        pass  # git が利用できない環境ではスキップ
```

**なぜこの実装か**: settings.json の deny パターンは文字列マッチのみのため、`HEAD` を含むコマンドが develop/main を指すかどうか判定できない。guard.py で `git rev-parse --abbrev-ref HEAD` を実行して実際のブランチ名を解決することで、確実にブロックできる。

---

## 5. 実装手順

1. `.claude/settings.json` の allow に 6 パターンを追加
2. `.claude/settings.json` の deny に 3 パターンを追加（`-u origin develop/main` + `HEAD`）
3. `.claude/settings.json` の hooks に PostToolUse セクションを追加
4. `scripts/claude/hooks/pretooluse_guard.py` に HEAD push 検出を追加
5. `scripts/claude/hooks/posttooluse_check.py` を新規作成
6. 動作確認（手動テスト）

---

## 6. テスト計画

`docs/tests/open/I029_manual_test.md` / `docs/tests/open/I029_auto_test.md` を参照。

---

## 7. ロールバック

`.claude/settings.json` を git で 1 コミット前に戻す：

```bash
git show HEAD~1:.claude/settings.json > .claude/settings.json
```

`posttooluse_check.py` を削除：
```bash
rm scripts/claude/hooks/posttooluse_check.py
```

`pretooluse_guard.py` の変更を git で元に戻す：
```bash
git show HEAD~1:scripts/claude/hooks/pretooluse_guard.py > scripts/claude/hooks/pretooluse_guard.py
```

---

## 8. Risk & 回避策

| リスク | 影響 | 回避策 |
|--------|------|--------|
| `git push -u origin *` の allow が deny を意図せずバイパスする | develop/main への直 push | deny に `-u` 形式・`HEAD` を明示追加 + guard.py の HEAD 解決チェックで三重防御 |
| PostToolUse フックが誤検知・誤ブロックする | 正常ファイルの編集が妨げられる | ファイル不在・読み取り不可時はゼロ終了（サイレント）に設計 |
| yaml ライブラリが未インストール | YAML チェックが ImportError | try/except で import し、未インストール時はスキップ |

---

## 9. セキュリティ確認

- バックエンド・フロントエンドのコード変更なし → **セキュリティ影響なし**
- `python3 scripts/*` の allow は `Write(scripts/**)` が allow に含まれないため、Claude が scripts/ に悪意あるスクリプトを勝手に作成してから実行することは不可能
- deny に `git push -u origin develop/main` と `git push -u origin HEAD` を追加し、さらに guard.py が HEAD を実ブランチ名に解決してブロックする三重防御により、バイパスリスクを排除

---

## 10. 承認ポイント

### 設計判断の区別

| 判断内容 | 根拠 |
|---------|------|
| allow に `git fetch *`・`git rev-parse *`・`git push -u origin *`・`python3` 系を追加 | イシューに明記 |
| deny に `git push -u origin develop/main` と `git push -u origin HEAD` を追加 | 仮定で決めた → **承認済み（OK）** |
| guard.py に HEAD push 検出（`subprocess` で実ブランチ解決）を追加 | 仮定で決めた → **承認済み（OK）** |
| PostToolUse を `.py`・`.json`・`.yaml` の構文チェックのみに絞る | 仮定で決めた → **承認済み（OK）** |
| 構文エラー時のみ非ゼロ終了（その他はサイレント） | 仮定で決めた → **承認済み（OK）** |

### チェックリスト

- [ ] allow の追加 6 パターンに問題ないか
- [ ] deny の追加 3 パターン（`-u origin develop`・`-u origin main`・`-u origin HEAD`）に問題ないか
- [ ] guard.py の HEAD 検出ロジック（`subprocess` で `git rev-parse --abbrev-ref HEAD` を実行）に問題ないか
- [ ] PostToolUse フックのチェック対象（.py/.json/.yaml）に過不足はないか
- [ ] posttooluse_check.py の終了コード設計（エラー時のみ非ゼロ）に問題ないか
