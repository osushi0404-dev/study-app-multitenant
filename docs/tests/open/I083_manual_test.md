# I083 手動テスト

対象: push ガード（動的宛先 ask 化・force 取りこぼし修正）。
大半は Claude が決定論テストスクリプト実行で代替可。ハーネス統合（ask の実プロンプト描画）のみ実セッション目視が必要なため **実施環境列** を付す。

| No | 手順 | 期待結果 | 実施者 | 実施環境 | 実結果 | 備考 |
|---:|------|----------|--------|----------|--------|------|
| 1 | `bash scripts/claude/tests/test_pretooluse_push_guard.sh` を実行 | 全 TC PASS（fail=0・総数=既存40＋I083 追加分） | Claude | — | | 決定論ロジック全体 |
| 2 | `bash scripts/claude/tests/test_pretooluse_checkout_guard.sh` を実行 | 14 件 PASS（無回帰） | Claude | — | | I081 ガード無回帰 |
| 3 | `python -c "import ast; ast.parse(open('scripts/claude/hooks/pretooluse_guard.py').read())"` で構文確認 | エラーなし（exit 0） | Claude | — | | フック構文 |
| 4 | `docs/claude-code-structure.md` の限界注記を Read し、旧「既知の限界（静的形のみ・後続イシューで根治予定）」が「対応済み（I083 / ask degrade）」へ更新され、残余既知限界（`eval "$VAR"` 完全隠蔽）が明記されているか確認 | 注記が更新済み・残余限界が honest scoping として記載 | Claude | — | | TC-DOC1 と対応 |
| 5 | `git diff develop -- .claude/settings.json` で差分が無いことを確認 | 差分なし（settings 不変） | Claude | — | | AC: settings 変更しない |
| 6 | プレーン default 権限の新規セッションで develop 相当ブランチ上にて `git push origin $(git rev-parse --abbrev-ref HEAD)` を実行し、**確認プロンプト（ask）が表示**され、拒否すると push されないことを目視 | フック由来の確認プロンプトが表示される（自動実行されない）。承認すれば実行・拒否すれば中止 | Human | プレーン default 新規セッション | | ask JSON がハーネスで実プロンプトとして描画されるかの統合確認。稼働中セッションでは発生源を区別できないため別環境で実施 |
| 7 | 同セッションで feature ブランチ上にて `git push origin feature` を実行し、**無確認で通過**することを目視 | 確認プロンプトなしで通常実行（静的安全 push の無回帰） | Human | プレーン default 新規セッション | | 過剰 ask が無いことの体感確認 |

## 備考
- No.6/7 は「フックの ask/通常権限/モード」の区別が稼働中セッションでは不可能なため、プレーン default の新規セッションで実施する（plan-writing-rules「ハーネス挙動テストの実施環境」）。
- No.1〜5 は Claude が `/test` 実行時に自動実行・記録する。
