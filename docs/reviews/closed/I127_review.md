# I127 実装レビュー（DRF スロットル導入・API 全体の基本レート制限）

- 関連: docs/issues/open/I127.md / docs/plans/open/plan_I127.md / GitHub #232 / Draft PR #236
- レビュー対象コミット: b88abc9（feat 実装）・fb203cc（docs 案F 更新）・7c50de6（手動テスト記録）

## レビュー観点（計画に対応）

### 1. 設定の正しさと集約（最重要）
- [ ] `settings.py` の追加が計画のコード例と一致（無条件の `DEFAULT_THROTTLE_CLASSES = ['core.throttling.AppAnonRateThrottle', 'core.throttling.AppUserRateThrottle']`・`DEFAULT_THROTTLE_RATES {'anon': '60/min', 'user': '300/min'}`・`NUM_PROXIES: 1`・`API_THROTTLE_ENABLED = RATELIMIT_ENABLE`）
- [ ] `core/throttling.py` が計画のコード例と一致（有効スイッチ・レート値を**リクエスト時に settings からライブ評価**・発見4/案F）
- [ ] レート値がコード中にハードコードされていない（settings 集約・TC-AUTO-04）
- [ ] `REST_FRAMEWORK` 本体（:142）に参照コメント 1 行が追加されている（リスク6対応）
- [ ] スイッチのコメントに「django-ratelimit と DRF スロットルの両方に効く」旨が明記されている（リスク5対応）

### 2. 認可・既存挙動の不変更
- [ ] permission_classes・認可分岐の変更が**一切ない**（git diff で確認。スロットルは防御の追加のみ）
- [ ] django-ratelimit（`accounts/views.py` の 7 箇所の `@ratelimit`）・`RatelimitMiddleware`・requirements が不変更（I129 スコープに踏み込んでいない。`FieldValidationView` の `throttle_classes` 1 行差し替えは発見5 の退行是正でユーザー承認済み・計画変更点8）
- [ ] `CacheService` のプロパティ化（変更点9・発見6）が属性名・本番動作を変えていない（呼び出し側変更ゼロの確認）
- [ ] E2E workflow（`.github/workflows/e2e.yml`）が不変更（既存 `RATELIMIT_ENABLE=false` で連動）

### 3. 429 応答の品質
- [ ] 429 で `Retry-After` ヘッダと統一 JSON（`main_message: 'リクエストが多すぎます'`）が返る（TC-AUTO-01/02）
- [ ] `custom_exception_handler` の既存分岐（404/403/401/500・ValidationError）が退行していない（全体回帰）
- [ ] FE は `case 429` 追加のみで既存 case・`/auth/` スキップ・400 素通しが不変更（TC-FE-02）

### 4. テストの決定論性
- [ ] `backend/conftest.py` の autouse 無効化（`API_THROTTLE_ENABLED=False`・リクエスト時評価のため import 順に依存しない）により既存テストへの 429 混入がない（TC-AUTO-06: 既存 76 件 PASS）
- [ ] スロットル TC が locmem **全 4 エイリアス**差し替え＋cache clear で相互汚染しない（スパイク発見1の反映）
- [ ] 実行順依存が解消されている（発見4・6: スロットル TC→I073 の順の再現ペアと全体回帰の両方で PASS）
- [ ] TDD RED（案B 時点の記録）と false-green 注入検証（TC-AUTO-05・TC-AUTO-03(a)(b)）が記録済み
- [ ] 注入復元後の `git diff` が実装差分のみ

### 5. 計画との一致
- [ ] 変更ファイルが計画の変更点一覧（変更点1〜9）のみ（計画外変更なし）
- [ ] 実装コードが計画書のコード例と一致

## 敵対的レビュー観点（独立サブエージェント向け・「合格を反証せよ」）
- 通常利用が 429 に当たらないという主張を反証せよ: 登録画面 initial load・ログイン直後のダッシュボード・クイズ回答・通知ポーリングの実リクエスト数/分を数え、60/min（未認証）・300/min（認証済み）を超えるシーケンスが本当に存在しないか。
- `NUM_PROXIES: 1` の設定で、(a) 本番 nginx 経由の実クライアント IP 識別、(b) XFF 偽装による回避、(c) 開発環境の直アクセス、のいずれかが壊れないか（DRF `get_ident` の実装を根拠に反証）。
- `RATELIMIT_ENABLE=false` で DRF スロットルが**完全に**無効化されるか（案F ではクラスは常時定義・`allow_request` の先頭で `API_THROTTLE_ENABLED` を判定して素通しする設計。`FieldValidationView` の明示指定を含む全ビューで漏れがないか、rates/NUM_PROXIES 残置が副作用を起こさないかを反証）。
- conftest の autouse 無効化が、スロットル TC 自身の override と競合して false-green にならないか（fixture とデコレータの適用順序を根拠に反証）。
- Redis 断時（`IGNORE_EXCEPTIONS: True`）に 500 やリクエスト全拒否にならず、フェイルオープンすることを反証・実証せよ。

## 結果

### 実装結果評価
- /code-review 判定 **OK**（決定論ゲート: omission-lint OK・FINAL VERDICT OK・高リスク No）。記録: `docs/reviews/I127_code_review_20260719_1149.md`
- 受け入れ条件 6 件すべて実装済みと照合確認。指摘は Low 2 件（FE テストの axios 内部構造依存・429 トースト二重表示）のみで、いずれも別イシュー候補の改善提案（ブロッカーなし）。

### テスト結果
- 自動（/test 2026-07-19）: BE 全体 **84 passed**（既存 76＋新規 8）・FE **3 suites / 9 passed**。false-green 注入検証 3 件・TDD RED 記録は auto_test 参照。
- E2E: PR #236 CI 全 6 チェック **PASS**（E2E Tests (Playwright) 3m13s）。
- 手動: No.1〜4 **全合格**（実 Redis 429・スイッチ off/復元・CI・429 トースト目視スクリーンショット確認）。記録: `docs/tests/open/I127_manual_test.md`

### 総合判定
**合格**（自動・手動・CI・レビューすべて PASS。残指摘は Low の別イシュー候補のみ）
