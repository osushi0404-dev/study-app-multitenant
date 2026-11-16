# I491 手動テスト: I473 のレビューの残り（科目のキャッシュ・連続日数・E2E の比べ方・境界値・QuizAnswer の見張り）

使うアカウント: 開発の DB の確かめ用の利用者 `verify_i487@example.com`（組織「確かめI487組織」・科目 確かめ数学/確かめ英語。パスワードは `e2e/.env.e2e` の `E2E_TEST_PASSWORD`）。開発の起動のたびに `dashboard-verify-seed` が作り直し、期待値は `docker compose logs dashboard-verify-seed` の最後の `種:` から下に出る（手順の正: `docs/runbooks/frontend-verify.md` §11）。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `docker compose logs dashboard-verify-seed` の最後の `種:` から下で「全科目」の `連続日数: N日` を読む。Playwright MCP で `http://localhost:3000/login` を開き、上のアカウントでログインして `/dashboard` を開く | ダッシュボードの連続日数の欄に、ログの N と同じ日数が出る（窓で読む作りに変えても、窓より短い連続の数え方が変わらない） | Claude |  | ブランチのコードが開発の backend に載っていること（`docker compose exec backend` で `dashboard/selectors.py` に `STREAK_WINDOW_DAYS` があること）を先に確かめる |
| 2 | 同じ画面で、科目の選択（ダッシュボードの科目のプルダウン）に出る科目を見る | 「確かめ数学」「確かめ英語」の 2 つが出る（キャッシュの形を変えても、選んだ科目が今までどおり出る） | Claude |  | 開き直して 2 回目（キャッシュから読む）も同じ 2 つが出ること |

## 画面確認
<!-- frontend/src は変えないので、check-frontend-evidence.sh の対象外。上の行の観測はこの表にも残す -->
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

結論: OK / NG
