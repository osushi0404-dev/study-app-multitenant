# I127 手動テスト（DRF スロットル導入・実環境 429・スイッチ・トースト表示）

- 関連: docs/issues/open/I127.md / docs/plans/open/plan_I127.md / GitHub #232 / Draft PR #236
- 前提: `docker compose up -d backend db redis frontend`（実 Redis 経路の確認を含むため redis 必須）
- 使用アカウント: **不要**（全項目とも未認証で実施可能。登録画面は未認証設計・API 連打も未認証エンドポイントを使用）

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | 実 Redis 経路での 429 発生: `for i in $(seq 60); do curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8000/api/organizations/subjects/public/?slug=personal"; done` を実行後、61 回目として `curl -i "http://localhost:8000/api/organizations/subjects/public/?slug=personal"` でヘッダ・body を取得 | 1〜60 回目は `200`。61 回目は `429`・`Retry-After` ヘッダ付き・body が `{"error": {"main_message": "リクエストが多すぎます", "sub_message": "しばらく時間をおいて再度お試しください", "details": {}}}` | Claude | ✅ 2026-07-19: 60 連打すべて `200`・61 回目 `429`＋`Retry-After: 60`＋期待どおりの統一 JSON body。65 秒待機後 `200` 復帰（窓解除）も確認 | 実行後は同一 IP の未認証 API が最長 60 秒 429 になる（60 秒待って解除確認）。backend を直叩きできない場合は `http://localhost:3000/api/...`（dev proxy 経由）で代替 |
| 2 | 無効化スイッチ: `RATELIMIT_ENABLE=false docker compose up -d backend` で再作成後、No.1 と同じリクエストを 70 回実行 | 全リクエスト `200`（429 が発生しない） | Claude | ✅ 2026-07-19: スイッチ off で 70 連打すべて `200`（直前が 429 状態でも制限なし）。env なしで再作成後は 429 復活（Redis 残存カウンタで 61 連打全 `429`→窓経過後 `200`）を確認。WSL からは `WSLENV=RATELIMIT_ENABLE` 併用で docker.exe へ env を伝搬 | docker-compose.yml:46 の env パススルーを利用。**実施後に必ず** `docker compose up -d backend`（env なし）で再作成し既定（有効）へ復元・No.1 相当で 429 復活を確認 |
| 3 | E2E 回帰: Draft PR #236 の CI 結果を `gh pr checks 236` で確認 | E2E（`RATELIMIT_ENABLE=false` 設定済み・workflow 不変更）を含む全チェックが PASS | Claude | ✅ 2026-07-19: 全 6 チェック PASS（Backend Tests / Backend Lint & Security / Frontend Tests / Type Check / Lint & Security / **E2E Tests (Playwright) 3m13s pass**） | ローカル代替: `docker compose --profile e2e run --rm e2e` |
| 4 | 429 トーストの目視: 【準備・Claude】`backend/core/settings.py` の `'anon': '60/min'` を一時的に `'3/min'` へ変更（dev サーバー自動リロード・4 連打で 429 になることを curl で事前実測）。【実施・Human】未認証ブラウザ（シークレットウィンドウ）で `http://localhost:3000/register/personal` を開き、素早く 4 回リロードする | 4 回目のリロード後、画面に赤系トースト「**リクエストが多すぎます。しばらく待ってから再試行してください**」が表示される（組織確認欄にインラインのエラー文言が併記されるのは正常・画面は崩れない） | Human | ✅ 2026-07-19: ステップ2（科目選択）到達時の科目取得が 429 となり、赤系トースト「**リクエストが多すぎます。しばらく待ってから再試行してください**」の表示をスクリーンショットで確認。画面は空状態メッセージ表示のまま崩れなし。復元後 `git diff -- backend/core/settings.py` 差分なし（コミット済み実装と一致）。付随観察: (1) SubjectService の失敗コールバック由来の汎用トースト「エラーが発生しました…」が併出（既存パターン・二重表示は UX 改善候補）。(2) 科目領域の文言が「利用可能な科目がありません」となる（429 起因でも空状態文言＝既存挙動） | 【後始末・Claude】`'60/min'` へ Edit で復元し `git diff -- backend/core/settings.py` が実装差分のみであることを確認。アカウント不要。**注**: URL は必ず `/register/personal`（スラッグ付き）を使う。ページ読み込みごとに飛ぶ未認証 API は組織スラッグ検証（`/api/organizations/validate-slug/`）のみで、科目取得はウィザードのステップ2でしか発火しない（スラッグなし `/register` のリロードでは API が 1 件も飛ばずトーストは出ない＝2026-07-19 実施時に判明・手順を是正） |

**実施順**: No.1 → No.2 → No.4 → No.3（No.3 は push 後の CI 完了待ちのため最後）。

**Claude/Human の判定根拠**（feedback_manual_test_executor 準拠）: No.1-3 はコマンド実行・出力確認のため Claude。No.4 のみブラウザのトースト表示の目視が必要なため Human（準備・復元は Claude が実施し Human の作業はリロード操作と目視のみ）。
