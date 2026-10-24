# I187 手動テスト: フロント開発の検証ループを整える

- 実施者: Claude = Playwright MCP・Bash・Read で自分で観測できるもの。Human = 承認画面が出るかどうか（Claude からは見えない）など、Claude では観測できないもの
- 「実施環境」列: 権限・MCP の読み込みに依存する確認は、設定を変えたあとの新しいセッションでないと確かめられないため明記する
- 使うアカウント: `e2e_user_a@example.com`（組織 A・管理者）・`e2e_user_c@example.com`（組織 A・一般ユーザー）。パスワードは `e2e/.env.e2e` の `E2E_TEST_PASSWORD`（Playwright MCP の `--secrets` で名前だけを入力する。Claude は値を読まない）。ログインできないときだけ `docker compose exec backend python manage.py seed_e2e --scenario tenant_isolation --password <値>` をユーザーが流す
- URL: このワークツリーで `bash scripts/claude/wt-ports.sh` を実行したあと、`docker compose port frontend 3000` が出すポートを使い `http://localhost:<ポート>`（下では `<URL>` と書く）

| No | 手順 | 期待結果 | 実施者 | 実施環境 | 実結果 | 備考 |
|---:|------|----------|--------|----------|--------|------|
| M-01 | ステップ 1 の設定後、このワークツリーで Claude Code を開き直す。Claude が `mcp__playwright__browser_navigate` で `<URL>/login` を開き、続けて `mcp__playwright__browser_evaluate` で `document.title` を取ろうとする | ①MCP の操作の一覧に `mcp__playwright__browser_*` が出ている ②`browser_navigate` では承認画面が出ない ③`browser_evaluate` では承認画面が出る（ユーザーは「No」を選ぶ） | Human | Human 目視（設定変更後の新規セッション） |  |  |
| M-02 | `docker compose port frontend 3000` を実行し、出たポートで `<URL>/login` を `browser_navigate` で開いて `browser_snapshot` を取る | ポートが 3000 ではなく `wt-ports.sh` が割り当てた値（例 3010）で、スナップショットにメールアドレス欄・パスワード欄・ログインボタン（`data-testid` が `email-input`・`password-input`・`login-button`）がある | Claude | — |  |  |
| M-03 | `e2e_user_a@example.com` でログインする（パスワード欄に `E2E_TEST_PASSWORD` を入力してログインボタンを押す） | URL が `<URL>/dashboard` になる。ツールの出力にパスワードの値が出ず、出る場合は `<secret>E2E_TEST_PASSWORD</secret>` になっている | Claude | — |  |  |
| M-04 | user_a のまま、ナビの「問題管理」を押して `/quiz-management` へ移り、検索や絞り込みの入力欄に文字を入れる。`browser_take_screenshot` でファイル名 `.evidence/I187/quiz-management-a-1.png` を付けて撮り、Read で画像を見る | 画面に「問題管理」の一覧が表示され、権限エラー（「このページにアクセスする権限がありません。管理者権限が必要です。」）が出ない。入力した文字が入力欄に残っている。画像ファイルが `.evidence/I187/` にあり、Read で同じ画面が見える | Claude | — |  |  |
| M-05 | ログアウトし（または新しいタブで）`e2e_user_c@example.com` でログインして `/dashboard` を開き、続けて `<URL>/quiz-management` を直接開く。それぞれ `.evidence/I187/dashboard-c-1.png`・`quiz-management-c-1.png` を撮る | `/dashboard` のナビに「問題管理」が無い。`/quiz-management` に「このページにアクセスする権限がありません。管理者権限が必要です。」が表示される | Claude | — |  |  |
| M-06 | M-04・M-05 の画像を Read で見る | 画像の中身がスナップショットの内容と一致する（user_a は問題管理の一覧・user_c は権限エラー） | Claude | — |  |  |
| M-07 | `browser_console_messages` でコンソールの内容を取る（M-04 の画面で） | コンソールのメッセージ一覧が返る。`error` の行があれば内容を記録する（確認できることが合否。エラーの有無は合否にしない） | Claude | — |  |  |
| M-08 | `browser_navigate` で `https://example.com/` を開こうとする | 画面が開かず、エラー（`net::ERR_BLOCKED_BY_CLIENT` などの「止められた」旨）が返る。`http://127.0.0.1:<ポート>/login` は開ける | Claude | — |  |  |
| M-09 | `git status --porcelain` と `git check-ignore -v .evidence/I187/quiz-management-a-1.png` を実行する | `git status` に `.evidence/` が出ない。`check-ignore` が `.gitignore` の `.evidence/` の行を示す | Claude | — |  |  |
| M-10 | 本イシューのテスト記録（この文書の「## 画面確認」）に M-04・M-05 の行を書き、`bash scripts/claude/check-frontend-evidence.sh I187` を実行する。次に `BASE_REF` を `frontend/src` を変えたコミットより前に向けた一時リポジトリでの結果として、TC-07 のテストスクリプトの出力（E1〜E12）を見る | 本イシューは `frontend/src` を変えていないので「対象外」と出て exit 0。TC-07 の出力で、行なし（E2）・画像なし（E4）は exit 1、画像あり（E3）・理由つき（E5）は exit 0 | Claude | — |  |  |
| M-11 | `docker compose exec frontend npm run typecheck` と `docker compose exec frontend npm run lint` を実行し、PR の CI の「Frontend Type Check」「Frontend Lint & Security」のログで実行されたコマンドを見る（`gh run view --log`） | 手元の 2 つが exit 0。CI のログに `npm run typecheck`・`npm run lint -- -f github-actions` が出ていて、ジョブが success | Claude | — |  |  |
| M-12 | 新しいセッションで Claude が `docker compose --profile e2e run --rm e2e npx playwright test tests/auth.spec.ts --retries=0` を実行する。続けて `docker compose --profile e2e run --rm e2e npx playwright install` を実行しようとする | 1 つ目は承認画面が出ずに実行され、テストが合格する。2 つ目は承認画面が出る（ユーザーは「No」を選ぶ） | Human | Human 目視（設定変更後の新規セッション） |  |  |
| M-13 | 落とし穴の確認: ①ホストで chromium が起動すること（M-02 で MCP のブラウザが起動したことで代える） ②`RATELIMIT_ENABLE=false docker compose up -d backend` のあと E2E（既定コマンド）を 5 分以内に 2 回流す ③e2e コンテナの中で `window.isSecureContext` を確かめる使い捨ての spec（`tests/tmp-secure-context.spec.ts`・コミットしない）を `--retries=0` で流す ④`docker compose exec frontend npm run typecheck` が exit 0 の状態で画面を開く | ①MCP でブラウザが起動している（M-02） ②2 回とも global-setup が 403 にならず合格 ③spec が `isSecureContext === true` で合格（設定を入れる前は false で不合格になることも確かめる） ④画面にエラーのオーバーレイが出ない。終わったら `docker compose up -d backend` で元に戻し、使い捨ての spec を消す | Claude | — |  |  |
| M-14 | E2E の失敗時の記録: わざと失敗する使い捨ての spec（`tests/tmp-fail.spec.ts`・コミットしない）を e2e コンテナで `--retries=0` で流し、`e2e/test-results/` を見る。次に同じ spec を `CI=true` を付けて流す（`docker compose --profile e2e run --rm -e CI=true e2e npx playwright test tests/tmp-fail.spec.ts --retries=0`） | 1 回目: `test-results/` の中に `test-failed-1.png` と `trace.zip` がある。2 回目: `test-failed-1.png` はあり、`trace.zip` は無い。終わったら使い捨ての spec を消す | Claude | — |  |  |
| M-15 | 計画書の「16. フロント開発設定の点検結果」を読む | 起動（初回・2 回目）・再コンパイル・Jest・型チェック・lint の所要時間が秒で書かれ、別イシューのタイトル案（Vite への移行など）に数字が付いている。点検にかけた時間が 30 分以内と書かれている | Claude | — |  |  |
| M-16 | `git diff origin/develop...HEAD --name-only` の一覧を、I185・I186・I188 のイシュー（範囲・実装対象）と突き合わせる | I185 の範囲（工程・スキル・フック・ゲート・権限の総点検）・I186（定期見直し）・I188（公式機能への置き換え）の作業が含まれていない。重なるファイル（`.claude/settings.json`・スキル）は、今の develop に対する追記だけになっている | Claude | — |  |  |
| M-17 | 公式 `/run` を実行する（このワークツリーで「アプリを起動して画面を見せて」と頼む） | `/run` が CLAUDE.md の参照から `docs/runbooks/frontend-verify.md` の手順（`docker compose up -d`・`docker compose port frontend 3000` の URL）で起動・画面確認をする | Claude | — |  |  |
| M-18 | （/security-review で追加）新しいセッションで `browser_take_screenshot` をファイル名 `backend/.env` で呼ぶ。続けて `.evidence/I187/guard-ok.png` で呼ぶ | 1 つ目は見張りに止められ、`backend/.env` の更新日時（`stat -c %y backend/.env`）が呼ぶ前と変わらない。2 つ目は保存される | Claude | 設定変更後の新規セッション |  |  |

## 画面確認
<!-- 列: 日時・コミット・画面と操作・アカウント・期待した結果・実際の結果・画像（.evidence/I187/ のファイル名。カンマ区切り。確認できない場合は「理由: …」） -->
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|

結論: OK / NG
