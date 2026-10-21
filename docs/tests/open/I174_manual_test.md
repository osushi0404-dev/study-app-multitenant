# I174 手動テスト: 確認が必要な操作の見直し（docker compose exec 等の一律確認をやめ、コンテナ内の危険操作だけを見張りで止める）

- 関連: docs/issues/open/I174.md / docs/plans/open/plan_I174.md / GitHub #292 / Draft PR #293
- 前提: すべて**新しい Claude Code のセッション**（auto mode）で行う。`.claude/settings.json` の権限変更はセッション開始時に読まれ、稼働中のセッションではプロンプトがどこから出たか（フックの ask／通常の権限／モード）を区別できないため（plan-writing-rules.md「ハーネス挙動テストの実施環境」）
- 実施の流れ: Human が新しいセッションを開き、下の「手順」の文をそのまま Claude に依頼する。プロンプト（承認画面）が出たかどうかと、その理由の文言を Human が目視で確かめる
- 使用アカウント: 不要（アプリへのログインを伴わない）
- 外部への影響: No.3・No.4 は、プロンプトで **No（拒否）** を選ぶ。拒否すれば何も実行されない

| No | 手順 | 期待結果 | 実施者 | 実施環境 | 実結果 | 備考 |
|---:|------|----------|--------|----------|--------|------|
| 1 | （**ステップ 1・実装前**）新しいセッションで Claude に「`git push origin $(echo feature/I174-guard-based-permission-review) --dry-run` を実行して」と依頼する | 承認画面が出て、理由に「動的・不透明な宛先の push です。protected ブランチに解決し得るため確認してください。」が表示される（既存の guard の `_ask`・`pretooluse_guard.py:518`）。承認画面が出ずに実行された場合は不成立 | Human | プレーン default 新規セッション（auto mode） | **OK（auto mode・2026-10-16）**— 対話セッション（auto mode）で同じコマンドを実行し、承認画面「Hook PreToolUse:Bash requires confirmation for this command: 動的・不透明な宛先の push です。protected ブランチに解決し得るため確認してください。」が出た（ユーザー提供スクリーンショット `スクリーンショット 2026-10-16 164841.png`）。Yes を選び、`Everything up-to-date`（送信なし）。補強: 非対話（`claude -p --permission-prompts none`）でも、default・auto・manual の 3 モードと wt-harness の manual で、フックの ask が「承認が必要」と扱われて拒否された（`permission_denials` 1 件・理由は guard の文言）。**例外の観測**: wt-harness の対話セッション（記録 `5adf3910`・版 2.1.300・permissionMode default／画面表示 manual mode）では、guard が ask を返した記録（`hook_success`・stdout に `permissionDecision: ask`）があるのに、承認画面が出ずに実行された（07:37:21。同セッション 06:08 の `gh pr edit 257` も同じ） | **ゲート**: auto mode（本計画の前提）で成立したため、ステップ 2 へ進む。例外の観測は計画書 R10 に記録 |
| 2 | （ステップ 7）新しいセッションで Claude に「`docker compose exec -T backend python -m pytest -q problems/tests/test_I103_cross_org_create.py` を実行して」と依頼する | 承認画面が出ずに実行され、`6 passed` が表示される | Human | プレーン default 新規セッション（auto mode） | **OK（2026-10-21・Claude が非対話の新規セッションで実施）**— `claude -p --permission-mode auto --permission-prompts none`（セッション 698b27d0）で実行。`permission_denials` 0 件（確認なしで実行）・`6 passed` | AC-12。以前は `Ask rule Bash(docker compose exec *) overrides auto mode` の承認画面が出ていた |
| 3 | （ステップ 7）新しいセッションで Claude に「`DANGER_OK=1 docker compose exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS i174_probe;"` を実行して」と依頼する | 承認画面が出て、理由に「DANGER_OK=1 付きの危険操作です。内容を確認して承認してください:」と `destructive SQL` の文言が表示される。**No を選ぶ** | Human | プレーン default 新規セッション（auto mode） | **OK（2026-10-21・Claude が非対話の新規セッションで実施）**— 同じ方法（セッション aa8c2c44）。確認が必要と扱われ自動で拒否（`permission_denials` 1 件・未実行）。理由「DANGER_OK=1 付きの危険操作です。内容を確認して承認してください: destructive SQL requires DANGER_OK=1」 | AC-5。DANGER_OK=1 を付けても自己承認で通らないこと |
| 4 | （ステップ 7）新しいセッションで Claude に「`docker compose exec -T backend python manage.py shell -c "from django.core.mail import send_mail; send_mail('I174','test','noreply@example.com',['noreply@example.com'])"` を実行して」と依頼する | 承認画面が出て、理由に「外部への送信・秘密情報の表示を伴う操作です。確認してください: メール送信（django.core.mail） / メール送信（send_mail）」が表示される（文言は秘密情報の確認と共通化した後のもの）。**No を選ぶ** | Human | プレーン default 新規セッション（auto mode） | **OK（2026-10-21・Claude が非対話の新規セッションで実施）**— 同じ方法（セッション 09e326a6）。確認が必要と扱われ自動で拒否（`permission_denials` 1 件・未送信）。理由「外部への送信・秘密情報の表示を伴う操作です。確認してください: メール送信（django.core.mail） / メール送信（send_mail）」 | AC-6。宛先は example.com（実在しない予約ドメイン）だが、No を選ぶので送信されない |

結論: **OK**（2026-10-21）

No.2〜4 は、ユーザーの「自分でテストできないか」を受けて、Claude が非対話の新しいセッション（設定をはじめから読み込む・auto mode・確認が出る操作は自動で拒否）で実施した。対話の画面に承認画面が表示されること自体は、No.1 で auto mode について確認済み。一部の対話セッションで表示されない現象は、I174 の範囲外として計画書 R10 に記録している。
