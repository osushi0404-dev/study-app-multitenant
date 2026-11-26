<!--
## 手動テスト品質基準
- 期待結果は「正常に〜できる」ではなく具体的な画面表示・動作で記載すること
- 権限別の動作差異がある場合は各ロールの期待結果を明記すること
- 実施者: docs/runbooks/plan-writing-rules.md「実施者の区別」で決める（原則 Claude。Human の行は備考に「試した手段: …」が必須。scripts/claude/check-manual-test-executor.sh が確かめる）
-->

# I636 手動テスト: 登録用リンクとメンバー管理のレビューの残りを直す

前提: 手元のアプリを起動し（`docs/runbooks/frontend-verify.md` §3）、`seed_e2e`（`tenant_isolation`）を流した後の利用者を使う。画面は Playwright MCP で開く。パスキーの操作は §5 の仮想の認証器を付けてから行う。E2E は e2e コンテナで流す（§8・パスキーの E2E は §8 の上書きのファイルを重ねる）。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `docker compose exec backend pytest accounts/tests/test_I620_registration_links.py -k "without_row_lock_both_succeed" -p no:randomly` を 10 回流す（AC3） | 10 回とも 1 passed（行の鍵を外した状態では 2 本とも 200 になる＝本来の `test_tc07_concurrent_complete_only_once` が落ちる状態）。あわせて本来のテストを 3 回流して 3 回とも passed | Claude | | OK（2026-11-27・ab93e429）: `without_row_lock_both_succeed` を 10 回流して 10 回とも 1 passed（鍵を外すと 2 本とも 200・パスキー 2 個＝本来のテストは落ちる状態）。本来の `test_tc07_concurrent_complete_only_once` は 3 回とも passed（各 4.7〜4.9 秒・待ち合わせの時間切れを含む） |  |
| 2 | e2e コンテナで E2E 全体を `--retries=0` で 3 回流す（並行・既定の workers。パスキーの spec のため §8 の上書きを重ねる）（AC13） | 3 回とも全件 passed。`tests/settings.spec.ts` の TC-28 が 3 回とも通る。落ちたらトレースから原因を書き、計画書 §4-13 の直しを入れてからやり直す | Claude | | NG（2026-11-27）: `--repeat-each=3`（63 件）を 2 回流した。1 回目は TC-30 が 1 件落ちた（管理者のページが本人確認の前にログイン画面に戻った。トレースでは、ログインの直後に 401 → 画面の更新の宛先 `/api/auth/token/refresh/` が 404（裏側は `/api/auth/refresh/`）→ ログアウト。前からある更新の宛先の食い違いで I636 の変更ではない・retro で別のイシューにする）。2 回目は TC-28 が 1 件落ちた: 保存の応答の `daily_study_goal_minutes` が 50（入れたのは 45）。原因: 開発の StrictMode で設定画面の読み込みの効果が 2 回走り、遅れて届いた 2 回目の応答が `resetSettingsForm` で入力を保存済みの値に戻す（`frontend/src/pages/Settings.tsx` の `loadSettings` に、古い応答を捨てる処理が無い）。負荷で 2 回目の応答が入力の後に届くと起きる。→ fix-loop（計画の対象の外のファイルなので計画変更記録と計画レビューを通す）。なお `--repeat-each` は同じ TC-28 を同じ利用者で同時に流すので、AC13 の「全体を 3 回」はやり直しでは全体を 3 回、順に流す |  |
| 3 | 組織の管理者（`e2e_user_a`）でログインし、幅 1280px と 360px で、ログイン直後の通知が出ている間にダッシュボード・`/members` を見る。`/members` で Tab を順に押す | 通知「ログインしました」が上の中央に出て、右上のユーザーメニューのボタンにも左のメニューのボタンにも重ならない（360px でも）。通知が出ている間にユーザーメニューを開ける。`/members` の表の枠に Tab でフォーカスが入り（枠が見える）、矢印キーで横に動く。表の中のボタンは横に並ぶ（360px で高さ 44〜56px） | Claude |  |  |
| 4 | `e2e_solo`（本人ひとりの組織の管理者）・`e2e_user_c`（一般）・`e2e_staff`（運営）でログインし、メニューを見て `/members` を直接開く。`e2e_staff` は `/admin/users` から `e2e_user_c` の編集画面を開く | `e2e_solo`・`e2e_user_c`・`e2e_staff` はメニューに「メンバー管理」が無く、`/members` は「このページにアクセスする権限がありません」。`e2e_staff` は `/admin/users` に入れて、`e2e_user_c` の編集画面に「パスキーと登録用リンク」の欄がある。`e2e_user_a` には「メンバー管理」がある | Claude |  |  |
| 5 | `e2e_user_a` で［＋ メンバーを追加］→ 追加 → 本人確認 → リンクのダイアログの［閉じる］を押し、閉じる途中の画面を撮る。行の［登録用リンク］から発行したダイアログも同じく閉じる | 閉じる途中も見出し「『<ユーザーID>』の登録用リンク」と QR が残り、『』にならない。閉じ終わるとリンクの値は画面のどこにも無い | Claude |  |  |
| 6 | No.5 のリンクを別の文脈で開いた後、管理者の画面で同じ人に［リンクを取り消す］→ 開いていた登録画面で［パスキーを登録］ | 「このリンクは使えません。管理者に新しいリンクを発行してもらってください」が出て［パスキーを登録］が消える | Claude |  |  |

## 画面確認
<!-- frontend/src を変えたイシューでは 1 行以上必要（test-gate 段階の check-frontend-evidence.sh が確かめる）。
     画像の列は .evidence/I###/ 直下のファイル名（カンマ区切り）。確かめられない理由があるときは「理由: …」。
     書き方: docs/runbooks/frontend-verify.md -->
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

結論: OK / NG
