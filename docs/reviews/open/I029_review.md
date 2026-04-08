# I029 レビュー

## 対象
`.claude/settings.json` allow 拡充・deny 追加・PostToolUse フック追加

---

## レビュー観点

### 1. 受け入れ条件との照合

| 受け入れ条件 | 確認 |
|------------|------|
| `git fetch`・`git rev-parse --abbrev-ref HEAD` が確認ダイアログなしで実行される | |
| `git push -u origin <feature branch>` が確認ダイアログなしで実行される | |
| `python3 scripts/*` が確認ダイアログなしで実行される | |
| `git push -u origin develop/main` は deny でブロックされる | |
| Edit/Write 後に .py/.json/.yaml の構文チェックが自動で走る | |
| 構文エラー時は非ゼロ終了で Claude にフィードバックされる | |
| 既存の deny ルール・pretooluse_guard.py の動作が変わらない | |

### 2. セキュリティレビュー

- [ ] deny ルールに `-u` 形式（develop・main）と `HEAD` 形式が明示追加されているか
- [ ] guard.py に `subprocess` で HEAD を実ブランチ名に解決するロジックが追加されているか
- [ ] guard.py の push 系チェック 3 箇所（force push・保護ブランチ・HEAD）が `re.match` に統一されているか
- [ ] コミットメッセージ内に保護ブランチ名を含む場合に誤ブロックされないか（AT-2・MT-5 確認）
- [ ] `python3 *`（過剰）でなく `python3 scripts/*` 等に絞られているか
- [ ] pretooluse_guard.py の既存ガードが引き続き機能しているか（AT-2 確認）
- [ ] posttooluse_check.py がファイル不在・読み取り不可時にゼロ終了するか（フック自体でブロックしない）

### 3. 計画書との一致確認

- [ ] 変更ファイルが計画書記載の 3 ファイルのみか（`.claude/settings.json`・`posttooluse_check.py`・`pretooluse_guard.py`）
- [ ] allow に追加したパターンが計画書の 6 件と一致するか
- [ ] deny に追加したパターンが計画書の 3 件と一致するか（`-u origin develop`・`-u origin main`・`-u origin HEAD`）
- [ ] guard.py の push チェックが `re.match` に統一されているか（force push・保護ブランチ・HEAD の 3 箇所）

### 4. コードレビュー（posttooluse_check.py）

- [ ] yaml の import エラー（未インストール時）を try/except で処理しているか
- [ ] ファイルパスの取得が `tool_input.file_path` から正しく行われているか
- [ ] 終了コードが仕様通りか（エラー時のみ非ゼロ）

---

## レビュー結果

- **結果**: （OK / NG）
- **コメント**:
