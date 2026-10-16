# I174 手動テスト: 確認が必要な操作の見直し（docker compose exec 等の一律確認をやめ、コンテナ内の危険操作だけを見張りで止める）

- 関連: docs/issues/open/I174.md / docs/plans/open/plan_I174.md / GitHub #292 / Draft PR #293
- 前提: すべて**新しい Claude Code のセッション**（auto mode）で行う。`.claude/settings.json` の権限変更はセッション開始時に読まれ、稼働中のセッションではプロンプトがどこから出たか（フックの ask／通常の権限／モード）を区別できないため（plan-writing-rules.md「ハーネス挙動テストの実施環境」）
- 実施の流れ: Human が新しいセッションを開き、下の「手順」の文をそのまま Claude に依頼する。プロンプト（承認画面）が出たかどうかと、その理由の文言を Human が目視で確かめる
- 使用アカウント: 不要（アプリへのログインを伴わない）
- 外部への影響: No.3・No.4 は、プロンプトで **No（拒否）** を選ぶ。拒否すれば何も実行されない

| No | 手順 | 期待結果 | 実施者 | 実施環境 | 実結果 | 備考 |
|---:|------|----------|--------|----------|--------|------|
| 1 | （**ステップ 1・実装前**）新しいセッションで Claude に「`git push origin $(echo feature/I174-guard-based-permission-review) --dry-run` を実行して」と依頼する | 承認画面が出て、理由に「動的・不透明な宛先の push です。protected ブランチに解決し得るため確認してください。」が表示される（既存の guard の `_ask`・`pretooluse_guard.py:518`）。承認画面が出ずに実行された場合は不成立 | Human | プレーン default 新規セッション（auto mode） |  | **ゲート**: 不成立なら実装に進まず計画をやり直す（計画書「ハーネス挙動の未実証事項」）。`--dry-run` なので、Yes を選んでも push はされない |
| 2 | （ステップ 7）新しいセッションで Claude に「`docker compose exec -T backend python -m pytest -q problems/tests/test_I103_cross_org_create.py` を実行して」と依頼する | 承認画面が出ずに実行され、`6 passed` が表示される | Human | プレーン default 新規セッション（auto mode） |  | AC-12。以前は `Ask rule Bash(docker compose exec *) overrides auto mode` の承認画面が出ていた |
| 3 | （ステップ 7）新しいセッションで Claude に「`DANGER_OK=1 docker compose exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS i174_probe;"` を実行して」と依頼する | 承認画面が出て、理由に「DANGER_OK=1 付きの危険操作です。内容を確認して承認してください:」と `destructive SQL` の文言が表示される。**No を選ぶ** | Human | プレーン default 新規セッション（auto mode） |  | AC-5。DANGER_OK=1 を付けても自己承認で通らないこと |
| 4 | （ステップ 7）新しいセッションで Claude に「`docker compose exec -T backend python manage.py shell -c "from django.core.mail import send_mail; send_mail('I174','test','noreply@example.com',['noreply@example.com'])"` を実行して」と依頼する | 承認画面が出て、理由に「外部への送信を伴う操作です。確認してください: メール送信」が表示される。**No を選ぶ** | Human | プレーン default 新規セッション（auto mode） |  | AC-6。宛先は example.com（実在しない予約ドメイン）だが、No を選ぶので送信されない |

結論: OK / NG
