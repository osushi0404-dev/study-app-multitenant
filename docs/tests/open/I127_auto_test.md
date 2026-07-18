# I127 自動テスト（DRF スロットル導入・429 回帰・スイッチ連動・通常利用レンジ）

- 関連: docs/issues/open/I127.md / docs/plans/open/plan_I127.md / GitHub #232 / Draft PR #236
- 対象: `backend/core/tests/test_I127_throttling.py`（新規）・`backend/conftest.py`（新規）・`frontend/src/services/__tests__/api.test.ts`（新規）
- 実行: BE `docker compose exec backend python -m pytest core/tests/test_I127_throttling.py -q` ／ FE `docker compose exec frontend npm test -- --watchAll=false`
- テストレベル: BE = API 結合（実 URL ルーティング〜DRF スロットル〜`custom_exception_handler` の配線を検証）／ FE = ユニット（レスポンスインターセプタの分岐）

## fixture / ヘルパ方針（BE）

- **スロットル有効化コンテキスト**: conftest の autouse フィクスチャ（`settings.API_THROTTLE_ENABLED = False`・全テストでスロットル無効）を前提に、スロットル TC だけが `override_settings(API_THROTTLE_ENABLED=True, ...)` で明示的に再有効化する。
- **案F: アプリ専用スロットルクラス方式（2026-07-19 ユーザー承認・発見4）**: DRF はスロットル設定（クラスリスト・レート表）を初回 import 時にクラス属性へスナップショットするため、settings 経由のクラス差し替え（旧案B のテスト用サブクラス＋文字列パス方式）は実行順依存が残る。本番の `core/throttling.py` アプリ専用クラスが**有効スイッチとレート値をリクエスト時に settings からライブ評価**するため、テストは標準の `override_settings` だけで決定論的に制御できる（テスト用サブクラス・文字列パス機構は廃止）:

```python
THROTTLE_TEST_CACHES = {
    alias: {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': f'throttle-test-{alias}',
    }
    # default 以外も必須（sessions はセッションミドルウェア、sessions/problems は
    # core/cache_service.py:25 が参照。default のみだと InvalidCacheBackendError で 500）
    for alias in ('default', 'sessions', 'problems', 'analytics')
}


def low_rate_rest_framework():  # 低レート差し替え（アプリ専用クラスがリクエスト時にライブ参照する）
    return {
        **settings.REST_FRAMEWORK,
        'DEFAULT_THROTTLE_RATES': {'anon': '3/min', 'user': '3/min'},
    }
```

- 各 TC は override 突入直後に `caches['default'].clear()` を実行（LocMemCache の LOCATION はプロセス内で共有されるため、TC 間のスロットル履歴汚染を防ぐ）。
- 未認証 TC のルートは `GET /api/organizations/subjects/public/?slug=personal`（personal 組織はマイグレーション 0014 で必ず存在・I115 で未認証 200 確定済み・#228 マージ済み）。
- 認証済み TC は `test_I104_subject_authz.py` の fixture パターンに倣い組織＋一般ユーザーを作成し `APIClient.force_authenticate` で `GET /api/subjects/`（`IsAuthenticated`・200）を使用。

## テストケース

| TC | 内容 | 手順 | 期待値 | 実施者 |
|----|------|------|--------|--------|
| TC-AUTO-01 | レート超過で 429＋Retry-After（anon/user 両系統） | `override_settings(API_THROTTLE_ENABLED=True, REST_FRAMEWORK=low_rate_rest_framework(), CACHES=locmem)` で (a) 未認証 4 連打 (b) `force_authenticate` 済みで 4 連打（2 関数） | (a)(b) とも 1〜3 回目 `status.HTTP_200_OK`・4 回目 `status.HTTP_429_TOO_MANY_REQUESTS`。429 応答に `Retry-After` ヘッダが存在し `1 <= int(Retry-After) <= 60` | Claude |
| TC-AUTO-02 | 429 の統一 JSON 文言（exceptions.py の 429 分岐） | TC-AUTO-01(a) の 4 回目レスポンスの body を assert | `body['error']['main_message'] == 'リクエストが多すぎます'`・`body['error']['sub_message'] == 'しばらく時間をおいて再度お試しください'`・`body['error']['details'] == {}` | Claude |
| TC-AUTO-03 | `RATELIMIT_ENABLE` スイッチ連動（env 解釈＋無効化動作の両方向） | (a) `subprocess.run([sys.executable, '-c', "<django.setup() して settings.API_THROTTLE_ENABLED を検査>"], env=...)` を `RATELIMIT_ENABLE=false`／未設定 の 2 パターンで実行（parametrize・DB 不要） (b) in-process で `override_settings(API_THROTTLE_ENABLED=False, REST_FRAMEWORK=low_rate_rest_framework(), CACHES=locmem)` の下、未認証 10 連打 | (a) env `false` → `API_THROTTLE_ENABLED is False`・未設定 → `True`（いずれも exit 0） (b) 低レート（3/min）超過でも全 `status.HTTP_200_OK`＝スイッチ off でスロットル無効 | Claude |
| TC-AUTO-04 | スロットル設定の settings 集約と確定値 | 現行プロセスの `settings.REST_FRAMEWORK` を直接 assert | `DEFAULT_THROTTLE_CLASSES == ['core.throttling.AppAnonRateThrottle', 'core.throttling.AppUserRateThrottle']`（**文字列パスのリスト**で完全一致・無条件定義）・`DEFAULT_THROTTLE_RATES == {'anon': '60/min', 'user': '300/min'}`・`NUM_PROXIES == 1` | Claude |
| TC-AUTO-05 | 通常利用レンジで 429 にならない（否定系） | `override_settings(API_THROTTLE_ENABLED=True, CACHES=locmem)`（レートは差し替えず実 settings 値をアプリ専用クラスがライブ参照・ハードコードしない）で (a) 未認証 10 連打 (b) 認証済み 10 連打 | 全リクエスト `status.HTTP_200_OK`（429 が 1 件もない）。登録画面 initial load（数 req）を上回る 10 req で代表 | Claude |
| TC-AUTO-06 | BE 全体回帰 | `docker compose exec backend python -m pytest -q`（全体） | 既存 **76 件**＋新規 TC 全 PASS（conftest の autouse 無効化により既存テストに 429 混入なし） | Claude |
| TC-FE-01 | 429 トースト | `react-hot-toast` を jest.mock し、`(apiClient as any).instance.interceptors.response.handlers[0].rejected` を `{response: {status: 429}, config: {url: '/api/subjects/'}}` で呼ぶ | Promise が元エラーで reject され、`toast.error` が `'リクエストが多すぎます。しばらく待ってから再試行してください'` で 1 回呼ばれる | Claude |
| TC-FE-02 | 既存分岐の退行なし（500） | 同ハンドラを `{response: {status: 500}, config: {url: '/api/subjects/'}}` で呼ぶ | `toast.error` が `'サーバーエラーが発生しました'` で呼ばれる（switch 追加による既存 case の破壊なし） | Claude |
| TC-FE-03 | FE 全体回帰 | `docker compose exec frontend npm test -- --watchAll=false` | 既存 **2 suites / 7 件**＋新規 suite 全 PASS | Claude |

注:
- TC 番号と実装するテスト関数の対応: 独立した関数を書くのは **TC-AUTO-01(a)(b) / 03(a)(b) / 04 / 05(a)(b)**（TC-AUTO-02 は 01(a) 内の body assert・TC-AUTO-06 / TC-FE-03 はコマンド実行）。
- 期待値の status は `rest_framework.status` の定数で assert する（規約準拠）。
- TC-AUTO-01 の 4 回目が確実に 429 になるのは、レート窓 60 秒 ≫ テスト実行時間（ms オーダー）のため決定論的。`Retry-After` の値は経過時間依存のため範囲 assert とする。
- TC-AUTO-03(a) のサブプロセスは `django.setup()` のみで DB 接続しない（settings 定義の検査のみ・コンテナ内で実行）。環境変数→settings の解釈は (a)、スイッチ off でスロットルが実際に効かないことは (b) が担い、AC「`RATELIMIT_ENABLE=false` で無効化」の連鎖全体を固定する。
- TC-FE-01/02 はインターセプタの rejected ハンドラ直接呼び出し方式（axios モックライブラリ未導入のため・plan 設計判断）。`/auth/` URL スキップ（`api.ts:169`）を踏まないよう `url` は `/api/subjects/` を使う。401 リフレッシュ分岐（`api.ts:80`）は 429/500 では通らない。

## TDD RED 確認（実装前に実施・ステップ1）

実装前の現行コードに対して先行実行し、以下の RED を記録してから実装する:
- **TC-AUTO-02** → RED（現行の 429 body は汎用文言 `'エラーが発生しました'`・スパイクで実測済み）
- **TC-AUTO-03(b)** → RED（現行 settings にスロットルキーなし・(a) は現状でも「キーなし」のため注意: **(b) が RED になることが本 TC の実装前検証**）
- **TC-AUTO-04** → RED（`DEFAULT_THROTTLE_RATES` キー不在で KeyError/assert 失敗）
- **TC-AUTO-05** → RED（同上・実レート値の取得で失敗）
- **TC-FE-01** → RED（現行は default 節 `'予期しないエラーが発生しました'` が呼ばれる）
- **TC-AUTO-01 は実装前でも GREEN**（override で有効化した DRF 機構自体の検証のため・スパイクで確認済み）。本 TC の役割は機構の配線固定であり、設定の存在は TC-AUTO-03/04 が固定する。
- 既存テスト（BE 76 件・FE 7 件）は GREEN のまま（baseline 済み）。
- 記録欄（2026-07-19 実装前実行 ✅）: BE `core/tests/test_I127_throttling.py` → **5 failed, 2 passed**（RED = TC-AUTO-01(a)+02 統一 JSON 文言・TC-AUTO-03(b) スイッチ有効側・TC-AUTO-04 レート値・TC-AUTO-05(a)(b) 実レート値取得／GREEN = TC-AUTO-01(b)・03(a) いずれも予測どおりの機構検証）。FE `api.test.ts` → **1 failed, 1 passed**（RED = TC-FE-01・現行文言 `'予期しないエラーが発生しました'` を実測／GREEN = TC-FE-02）。既存テストへの影響なし（conftest 追加後の全体回帰は TC-AUTO-06 で確認）。
- **追記（2026-07-19・案F 移行）**: 発見4（クラスリストの import 時スナップショット→実行順依存。案B 実装のファイル一括実行で TC-AUTO-05 2 件 FAIL・全体回帰で既存テスト巻き添え計 11 件 FAIL を実測）により、案B を案F（アプリ専用スロットルクラス）へ置換し TC-AUTO-01/03/04/05 の手順・期待値を再定義した。上記 RED 記録は案B 時点の事実として保持する。案F での GREEN・実行順非依存（ファイル一括＋全体回帰の両方で PASS）の確認は「実施記録」に記載。

## false-green 自己検証（否定系 TC・実装後に失敗注入で確認）

- **TC-AUTO-05（「429 にならない」の否定系）**: 実装後、`backend/core/settings.py` の `'anon': '60/min'` を一時的に `'3/min'` へ Edit で変更 → TC-AUTO-05(a) が **RED（4 回目以降 429）** になることを確認 → Edit で `'60/min'` に復元。
- **TC-AUTO-03（スイッチ連動の否定系）**: 実装後、(1) `backend/core/throttling.py` の `allow_request` のスイッチ判定 2 行を一時的に削除 → TC-AUTO-03(b) が **RED（スイッチ off でも 429）** → Edit で復元。(2) `backend/core/settings.py` の `API_THROTTLE_ENABLED = RATELIMIT_ENABLE` を一時的に `= True` 固定へ変更 → TC-AUTO-03(a) が **RED（false 環境でも True）** → Edit で復元。
- **復元は必ず Edit ツールで注入前の内容に戻す**（`git restore` 禁止＝実装差分保護）。復元後に `git diff -- backend/core/settings.py backend/core/throttling.py` が実装差分のみであることを確認する。
- 記録欄（2026-07-19 実施 ✅）: (1) `'anon': '60/min'` → `'3/min'` 注入 → TC-AUTO-05(a) **RED**（4 回目以降 429）→ Edit で復元。(2) `throttling.py` の `allow_request` スイッチ判定 2 行を削除 → TC-AUTO-03(b) **RED**（スイッチ off でも 429）→ Edit で復元。(3) `API_THROTTLE_ENABLED = RATELIMIT_ENABLE` → `= True` 固定へ変更 → TC-AUTO-03(a) **RED**（`[false-False]` のみ FAIL＝false 環境でも True）→ Edit で復元。復元後 `git diff -- backend/core/settings.py backend/core/throttling.py` は実装差分のみ・`core/tests/test_I127_throttling.py` → **8 passed** を確認。

## 実施記録
（/implement で記入）
- 2026-07-19（plan-review 指摘対応・発見4〜6 対処時の中間検証）: BE `core/tests/test_I127_throttling.py` 単独 → **8 passed**／発見4・6 の再現ペア（スロットル TC→I073 の順）→ **28 passed**／全体回帰 `python -m pytest -q` → **84 passed**（既存 76＋新規 8・実行順依存の解消を確認）。FE `npm test -- --watchAll=false` → **3 suites / 9 passed**（既存 7＋新規 2）。false-green 注入検証は /implement ステップ2で実施予定。
