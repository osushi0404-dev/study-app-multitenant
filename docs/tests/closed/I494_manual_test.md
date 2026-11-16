# I494 手動テスト: 学ぶ科目を後から選び直せるようにする

- 環境: app-1 の compose（frontend は `docker compose port frontend 3000` のポート。2026-11-16 は `http://localhost:3020`）。手順は `docs/runbooks/frontend-verify.md`（Playwright MCP・ログインのパスワードは秘密の名前 `E2E_TEST_PASSWORD` で入力する）
- アカウント: `e2e_user_c@example.com`（組織 A `e2e-org-a`・一般ユーザー・科目 0 件）。組織 A には「E2E Quiz Subject」「E2E Subject A」がある（開発の DB にほかの科目があれば一緒に出る）
- 幅: 1440×900 と 390×844

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `e2e_user_c` でログインし `/dashboard` を開く（1440）。「学ぶ科目を選ぶ」を押す | 「学習を開始」のカードに「学ぶ科目がまだ選ばれていません。設定画面で学ぶ科目を選んでください」と「学ぶ科目を選ぶ」が出て、「クイズを始める」は押せない。押すと URL が `/settings#learning-subjects` になり、「学ぶ科目」のカードの見出しが上の固定のバーに隠れずに見え、見出しにフォーカスがある | Claude | OK | 案内と「学ぶ科目を選ぶ」が出て、「クイズを始める」は押せない。押すと `/settings#learning-subjects`、見出し「学ぶ科目」（level 2）が固定のバーの下に見え、フォーカスあり（枠は「フォーカス表示強化」の設定のもの） |
| 2 | カードで「E2E Quiz Subject」にチェックを付けて「学ぶ科目を保存」。`/dashboard` に戻る | 保存の前は全部未チェックで「学ぶ科目を保存」は押せない（触る前は赤い注意を出さない・fix-loop 2 回目で変更）。チェックすると押せる。保存すると toast「学ぶ科目を保存しました」。ダッシュボードの科目の選択に「E2E Quiz Subject」が出て、0 件の案内が消え、「クイズを始める」が押せる（押すと `/quiz?subject=<その番号>`） | Claude | OK | 保存の前は赤い注意なし・保存ボタンは押せない。チェック後に押せる。toast「学ぶ科目を保存しました」。ダッシュボードの科目の選択に「E2E Quiz Subject」、案内は消え、「クイズを始める」で `/quiz?subject=2` |
| 3 | `/settings` で「E2E Subject A」を足し「E2E Quiz Subject」を外して保存。`/dashboard` に戻る（画面の再読み込みはしない） | 保存の応答のあと、ダッシュボードの科目の選択が「E2E Subject A」だけになる（古い一覧が出ない）。再読み込みしても同じ | Claude | OK | 保存の後、メニューで戻ったダッシュボードの選択肢が「すべて」「E2E Subject A」だけ。再読み込みの後も同じ |
| 4 | 開発者ツールの代わりに `browser_run_code_unsafe` で `PUT /api/user/subjects/` を 500 に差し替え、チェックを変えて保存 | カードの中に「学ぶ科目を保存できませんでした。時間をおいてもう一度お試しください」が残って出る。チェックの状態は押す前のまま。差し替えを外して保存すると成功し、赤い表示が消える | Claude | OK | `PUT` を 500 にすると、カードの中に「学ぶ科目を保存できませんでした。時間をおいてもう一度お試しください」。チェックは 2 つとも付いたまま。差し替えを外して保存すると成功し、赤い表示が消えた（表示の直後の画像はボタンが押せない色に見えるが、保存中の一瞬の状態。続けて押して成功・Jest でも失敗の後にボタンが押せることを確かめた） |
| 5 | `browser_run_code_unsafe` で `GET /api/user/subjects/` と `GET /api/user/subjects/available/` を `[]` に差し替えて `/dashboard` と `/settings` を開く | ダッシュボードは「科目がまだ登録されていません。組織の管理者に科目の登録を依頼してください」（「学ぶ科目を選ぶ」は無い）。設定画面のカードは「この組織には選べる科目がありません。組織の管理者に科目の登録を依頼してください」で「学ぶ科目を保存」が無い | Claude | OK | ダッシュボード: 管理者への依頼の案内・「学ぶ科目を選ぶ」なし・「クイズを始める」は押せない。設定画面: 「この組織には選べる科目がありません。…」で「学ぶ科目を保存」なし |
| 6 | 390×844 で No.1 の状態のダッシュボードと設定画面のカードを見る | 案内とボタンが横にはみ出さない。カードのチェックの一覧・説明・「学ぶ科目を保存」が 1 列で読め、押せる | Claude | OK | 390×844 でダッシュボードの案内とボタン、設定画面のカードがはみ出さず 1 列で読める |
| 7 | 終わったら `docker compose run --rm --no-deps e2e-init` で E2E の利用者を作り直し、`e2e_user_c` で `/dashboard` を開く | `e2e_user_c` が科目 0 件に戻り、No.1 と同じ案内が出る（E2E の TC-27 の前提を崩さない） | Claude | OK | `docker compose run --rm --no-deps e2e-init` の後、`e2e_user_c` で 0 件の案内が出た |

## 画面確認
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
| 2026-11-16 12:25 | b158a1fe | `/dashboard`（1440）→「学ぶ科目を選ぶ」→ `/settings#learning-subjects` | e2e_user_c | 0 件の案内とボタン。カードの見出しが隠れずフォーカスあり・触る前に赤い注意なし | そのとおり | no1-settings-c-1440.png, no7-dashboard-c-reset.png |
| 2026-11-16 12:26 | b158a1fe | カードで「E2E Quiz Subject」を選んで保存 → ダッシュボード | e2e_user_c | 保存の toast。選択肢に出て、クイズを始められる | そのとおり（`/quiz?subject=2`） | no2-settings-saved-c.png, no2-dashboard-selector-c.png |
| 2026-11-16 12:26 | b158a1fe | 「E2E Subject A」を足し「E2E Quiz Subject」を外して保存 → ダッシュボード・再読み込み | e2e_user_c | 選択肢が「E2E Subject A」だけ | そのとおり | no3-dashboard-selector-c.png |
| 2026-11-16 12:27 | b158a1fe | `PUT /api/user/subjects/` を 500 に差し替えて保存 | e2e_user_c | カードの中に失敗の表示が残り、チェックは消えない | そのとおり。差し替えを外して保存すると成功 | no4-save-failed-c.png |
| 2026-11-16 12:27 | b158a1fe | 選んだ科目・組織の科目の取得を `[]` に差し替えてダッシュボード・設定画面 | e2e_user_c | 管理者への依頼の案内。カードは保存ボタンなし | そのとおり | no5-dashboard-no-org-subjects.png, no5-settings-no-org-subjects.png |
| 2026-11-16 12:43 | b158a1fe | 390×844 でダッシュボードと設定画面のカード | e2e_user_c | はみ出さず 1 列で読める | そのとおり | no6-dashboard-c-390.png, no6-settings-c-390.png |

| 2026-11-16 13:13 | 90e4b7a5 | `/dashboard` →「学ぶ科目を選ぶ」→ `/settings#learning-subjects` のアクセシビリティの木 | e2e_user_c | チェックボックスのまとまりが「学ぶ科目」という名前のグループで、見た目は前と同じ | そのとおり | no1-settings-c-group.png, no1-settings-c-final.png |
結論: OK（コンソールのエラーは開発サーバーの WebSocket とログイン前の `/api/settings/` の 401 だけで、既知のもの）
