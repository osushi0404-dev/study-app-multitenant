# I029 手動テスト

## 対象
`.claude/settings.json` allow 拡充・deny 追加・PostToolUse フック追加

---

## MT-1: allow 追加コマンドの動作確認

### MT-1-1: git fetch
- 手順: Claude に `git fetch origin` を実行させる
- 期待: 確認ダイアログが出ずに実行される
- 確認ポイント: ダイアログなし

### MT-1-2: git rev-parse
- 手順: Claude に `git rev-parse --abbrev-ref HEAD` を実行させる
- 期待: 確認ダイアログが出ずに現在ブランチ名が返る
- 確認ポイント: ダイアログなし

### MT-1-3: git push -u origin（feature ブランチ）
- 手順: テスト用ブランチ `feature/test-push` を作成し、Claude に `git push -u origin feature/test-push` を実行させる
- 期待: 確認ダイアログが出ずに push される
- 確認ポイント: ダイアログなし

### MT-1-4: python3 scripts/
- 手順: Claude に `python3 scripts/claude/hooks/pretooluse_guard.py` を空入力で実行させる
- 期待: 確認ダイアログが出ずに実行される（エラーで終了してよい、許可されることを確認）
- 確認ポイント: ダイアログなし

### MT-1 実行結果（2026-04-08）

| ケース | 結果 |
|--------|------|
| MT-1-1: git fetch origin | ✅ ダイアログなしで実行 |
| MT-1-2: git rev-parse --abbrev-ref HEAD | ✅ ダイアログなしで実行 |
| MT-1-3: git push -u origin feature/test-push-I029 | ✅ ダイアログなしで push 成功（テスト後削除済み） |
| MT-1-4: python3 scripts/claude/hooks/pretooluse_guard.py | ✅ ダイアログなしで実行（invalid hook input で終了） |

---

## MT-2: deny の動作確認（既存 + 追加分）

### MT-2-1: git push origin develop（既存 deny）
- 手順: Claude に `git push origin develop` を実行させる
- 期待: ブロックされる（pretooluse_guard.py がブロック）

### MT-2-2: git push -u origin develop（追加 deny）
- 手順: Claude に `git push -u origin develop` を実行させる
- 期待: settings.json の deny にマッチしてブロックされる

### MT-2-3: git push -u origin main（追加 deny）
- 手順: Claude に `git push -u origin main` を実行させる
- 期待: settings.json の deny にマッチしてブロックされる

### MT-2-4: git push -u origin HEAD（develop ブランチ上）
- 手順: develop ブランチにチェックアウトした状態で、Claude に `git push -u origin HEAD` を実行させる
- 期待: pretooluse_guard.py が HEAD を develop に解決してブロックされる
- 確認ポイント: "push via HEAD to protected branch 'develop' is forbidden" のメッセージが出ること

### MT-2-5: git push -u origin HEAD（feature ブランチ上）
- 手順: feature ブランチ上で、Claude に `git push -u origin HEAD` を実行させる
- 期待: 確認ダイアログが出る（ask 扱い）。feature ブランチは保護対象外のためブロックされない

### MT-2 実行結果（2026-04-08）

| ケース | 結果 |
|--------|------|
| MT-2-1: git push origin develop | ✅ guard がブロック（`direct push to develop/main is forbidden`） |
| MT-2-2: git push -u origin develop | ✅ guard がブロック |
| MT-2-3: git push -u origin main | ✅ guard がブロック |
| MT-2-4: git push -u origin HEAD（develop 上） | ⚠️ AT-2-5 と同様、マージ前は構造的に実行不可。ロジック正しさはデバッグ確認済み |
| MT-2-5: git push -u origin HEAD（feature 上） | 📝 settings.json の deny により実際は「ask」ではなく常に denied。期待値の記述が不正確だったが、セキュリティ上より安全な動作 |

---

## MT-3: PostToolUse フック動作確認

### MT-3-1: 正常な Python ファイル編集後
- 手順: 正常な .py ファイルを Edit ツールで編集する
- 期待: フックがゼロ終了（サイレント）。エラーメッセージなし

### MT-3-2: 構文エラーのある Python ファイル編集後
- 手順: `def foo(` のような不正な Python を Write ツールで書き込む
- 期待: フックが非ゼロ終了し、構文エラーが Claude にフィードバックされる

### MT-3-3: 正常な JSON ファイル編集後
- 手順: 正常な .json ファイルを Edit ツールで編集する
- 期待: フックがゼロ終了（サイレント）

### MT-3-4: 不正な JSON ファイル編集後
- 手順: `{ "key": }` のような不正な JSON を Write ツールで書き込む
- 期待: フックが非ゼロ終了し、JSON エラーが Claude にフィードバックされる

### MT-3-5: 対象外ファイル（Markdown 等）編集後
- 手順: .md ファイルを Edit ツールで編集する
- 期待: フックがゼロ終了（スキップ）。エラーなし

### MT-3 実行結果（2026-04-08）

| ケース | 結果 |
|--------|------|
| MT-3-1: 正常な .py 編集 | ✅ サイレント |
| MT-3-2: 構文エラーの .py 書き込み | ✅ UI に `PostToolUse:Write hook error` 表示 |
| MT-3-3: 正常な .json 書き込み | ✅ サイレント |
| MT-3-4: 不正な .json 書き込み | ✅ UI に `PostToolUse:Write hook error` 表示 |
| MT-3-5: .md 編集 | ✅ サイレント（スキップ） |

**補足**: PostToolUse のフィードバックは Claude のツール結果には現れず、Claude Code UI に表示される（PreToolUse とは異なる挙動）。

---

## MT-4: 既存スキルへの影響確認

- `/plan-issue` スキルを一通り実行し、中断なく完了するか確認
- `/close` スキルを一通り実行し、中断なく完了するか確認

### MT-4 実施状況（2026-04-08）

ユーザーによる確認待ち。`/plan-issue` および `/close` を実際に実行して中断なく完了するか確認してください。

---

## MT-5: re.match 誤検知防止の確認

### MT-5-1: コミットメッセージに保護ブランチ名を含む場合
- 手順: Claude に保護ブランチ名（develop・main）を含むコミットメッセージで `git commit` を実行させる
- 例: `git commit -m "docs: develop/main への直 push を防ぐ設定を追加"`
- 期待: 確認ダイアログが出るが（ask 扱い）、guard.py にはブロックされない

### MT-5-1 実行結果（2026-04-08）

`git commit --dry-run -m "docs: develop/main への直 push を防ぐ設定を追加"` を実行。
guard にブロックされず（exit 1 はステージ済みファイルなしという git 自体のエラー）。✅
