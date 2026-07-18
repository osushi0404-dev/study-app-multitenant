## 基本情報
- **計画書ID**: plan_I127
- **関連イシュー**: #232
- **Draft PR**: #236
- **作成根拠資料**: docs/issues/open/I127.md（起点イシュー・grill-me 設計確認メモ確定済み）
- **実装後評価**: docs/reviews/open/I127_review.md
- **作成日**: 2026-07-18

---

## 1. 背景/目的

DRF に `DEFAULT_THROTTLE_CLASSES` / `DEFAULT_THROTTLE_RATES` が未設定のため、**認証系以外の API 全体にレート制限が存在しない**。特に未認証で到達できる公開エンドポイント（`GET /api/subjects/public/`・`GET /api/organizations/subjects/public/`、I115 で復旧・#228 マージ済み）への組織 slug 総当たり・スクレイピングを減速する仕組みがない（I115 security-review の残余リスク Low の根治）。

- **原因の概要**: DRF はレート制限が初期状態でオフになっており、プロジェクト初期にオンにする設計判断が行われないまま現在に至っている。認証系（ログイン等）だけは django-ratelimit で個別に守られているが、それ以外の API は無制限。
- **詳細な原因分析**:
  1. `backend/core/settings.py:142-162` の `REST_FRAMEWORK` にスロットル関連キーがない → DRF の既定（スロットル無効）が全ビューに適用される。
  2. 認証エンドポイントは `backend/accounts/views.py` の `@ratelimit`（django-ratelimit・IP キー・5/5m 等の 7 箇所）で保護済み（本イシューでは不変更。DRF への一本化は I129 #235）。
  3. E2E CI 用の無効化スイッチ `RATELIMIT_ENABLE`（`settings.py:288`）は存在するが、現状は django-ratelimit にしか効かない。
- **根本原因（コードレベル）**: `REST_FRAMEWORK` 設定辞書に `DEFAULT_THROTTLE_CLASSES` / `DEFAULT_THROTTLE_RATES` が存在しないこと（設定不在・コードのバグではない）。

## 調査結果

### 環境前提確認（2026-07-18 実施）
- `docker compose ps` → backend / db / redis 稼働中（frontend は Up だが unhealthy 表示・Jest 実行には支障なし＝下記 baseline で確認済み）。
- 前提: I115（PR #228）は **develop へマージ済み**（`gh pr view 228` → MERGED・2026-07-18T02:51Z 確認）。回帰テストが使う未認証公開エンドポイントは develop 上で 200 を返す。
- 新規依存なし（DRF 3.15.2 標準機能のみ）→ requirements 変更なし・Dockerfile/compose 波及なし。

### スパイク実証（2026-07-18・稼働中 backend コンテナで実施・成立）
計画の中核設計「`override_settings`（LocMemCache＋低レート）で実エンドポイントの 429 を決定論的に検証できる」を実証した:
- `AnonRateThrottle().parse_rate('60/min')` → `(60, 60)`・`UserRateThrottle().parse_rate('300/min')` → `(300, 60)`（レート表記が有効・DRF 3.15.2）。
- `override_settings(REST_FRAMEWORK={...anon '3/min'...}, CACHES={全エイリアス locmem}, ALLOWED_HOSTS=['testserver'])` + 未認証 `APIClient` で `GET /api/organizations/subjects/public/?slug=personal` を 4 連打 → **1〜3 回目 200・4 回目 429・`Retry-After: 60` ヘッダ付与**を確認。
- **設計上の重要発見1**: `CACHES` を差し替える際は `default` だけでなく**全エイリアス（`default`/`sessions`/`problems`/`analytics`）**を差し替える必要がある（`sessions` はセッションミドルウェア、`sessions`/`problems` は `core/cache_service.py:25` が参照。`default` のみの差し替えは `InvalidCacheBackendError` で 500）。
- **設計上の重要発見2**: 429 時の統一 JSON は現状 `{'error': {'main_message': 'エラーが発生しました', 'sub_message': None, 'details': {}}}`（汎用文言）。`core/exceptions.py` の `custom_exception_handler` に 429 分岐がないため（:47-62 は 404/403/401/500 のみ）。→ 変更点3で 429 分岐を追加する。
- `Retry-After` ヘッダは DRF が `Throttled.wait` から自動付与（追加実装不要・スパイクで実測）。
- **設計上の重要発見3（2026-07-19・実装ステップ1で検出→ユーザー承認済み）**: DRF はレート表 `THROTTLE_RATES` を**初回 import 時にクラス属性としてスナップショット**するため、`override_settings` のレート変更だけでは反映されず、スロットル TC が実行順依存で不安定になる（実測: 先行 TC の `3/min` が残留し TC-AUTO-05 が 4 回目 429 で FAIL・単体実行では PASS）。対処 = **テスト用サブクラス方式（案B）**: テストモジュール内に `rate = '3/min'` 固定のサブクラス（DRF 公式のオーバーライド手段・DRF 本家テストと同イディオム）と、settings の実レート値を `get_rate()` でライブ参照するサブクラスを定義し、`DEFAULT_THROTTLE_CLASSES` へ**文字列パス**で渡す（DRF 3.15.2 の `perform_import` はリスト要素を文字列前提で import するため、クラスオブジェクト直渡しは不成立＝実測）。低レート `[200,200,200,429]`・実レート 10×200 の同一プロセス内切替をスパイクで実証済み。本番コードへの影響なし。monkeypatch 方式（グローバルなクラス属性の書き換え）は次善として却下。
- **設計上の重要発見4（2026-07-19・plan-review 指摘対応の検証で検出→案F ユーザー承認済み）**: DRF は `DEFAULT_THROTTLE_CLASSES` も**初回 import 時に `APIView.throttle_classes` クラス属性へスナップショット**する（`rest_framework/views.py:110`。最初の API リクエストで URLconf→views が import された瞬間に固定・コンテナ内で実証）。このため案B（settings 経由でテスト用サブクラスを差し込む）はクラスリスト側の固定に無力で実行順依存が残る（実測: ファイル一括で TC-AUTO-05 が 2 件 FAIL・全体回帰で既存テスト 8 件が 429 巻き添えの計 11 件 FAIL・各 TC 単独実行は PASS）。conftest の settings 書き換えによる無効化も同じ理由で構造的に不確実。→ 対処 = **案F（アプリ専用スロットルクラス方式・2026-07-19 ユーザー承認）**: 可変部分（有効スイッチ・レート値）を**リクエスト時に settings からライブ評価**する `core/throttling.py` の自前クラスを本番設計とし、`DEFAULT_THROTTLE_CLASSES` は**無条件の定数**にする（いつスナップショットされても同値＝順序問題が原理的に消滅）。テストは標準 `override_settings`／pytest `settings` フィクスチャのみで制御でき、案B のテスト用サブクラス・文字列パス機構は不要となり削除。案C（テスト側で `APIView.throttle_classes` を monkeypatch）は「テスト側の対症療法で設計の歪みが残る」ためユーザー判断で却下。
- **設計上の重要発見5（2026-07-19・案F 検討中に検出→案F で同時是正）**: `accounts/views.py:549` `FieldValidationView` は素の `AnonRateThrottle` を明示指定しており、I127 でレート値を無条件定義すると **`RATELIMIT_ENABLE=false` でも当該ビューだけ 60/min が有効化される退行**が生じる（従来は DRF 既定レート None のため実質無効。無効化スイッチ AC 違反・E2E CI 影響リスク）。→ `AppAnonRateThrottle` への 1 行差し替えでスイッチ・レート集約に載せる（変更点8）。
- **設計上の重要発見6（2026-07-19・案F 実装後の全体回帰で検出→根治をユーザー承認済み）**: `core/cache_service.py:333` のモジュールレベルシングルトン `cache_service = CacheService()` が、`__init__` でキャッシュ**実体**（`caches[alias]` の返すインスタンス）を属性に固定する既存負債。全体回帰ではこのモジュールの初回 import がスロットル TC の CACHES=locmem override 中に発生し、**シングルトンが locmem 実体を永久保持** → override 復元後の I073 キャッシュ無効化テスト 2 件が FAIL（スロットル TC→I073 の順で決定的に再現・単独 PASS）。I127 が壊したのではなく、発見4 と同じ「初期化時スナップショット vs 実行時解決」問題がプロジェクト自身のコードに存在し、I127 のテストで顕在化したもの。→ 根治 = **4 つのキャッシュ属性を使用時解決の `@property` へ変更**（変更点9。属性名不変＝呼び出し側変更ゼロ・本番動作同一。`caches[alias]` の参照解決は軽量で毎回呼ぶのが Django の想定）。

### 既存テスト baseline（事前実行・2026-07-18）
- Backend: `docker compose exec backend python -m pytest -q` → **76 passed**（warnings 3・クリーン）。
- Frontend: `docker compose exec frontend npm test -- --watchAll=false` → **2 suites / 7 passed**（クリーン）。
- `backend/conftest.py` は**存在しない**（新規作成に衝突なし）。`backend/core/tests/` も存在しない（新規作成）。

### 既存レート制限との併存（イシュー確定・不変更）
- django-ratelimit（`accounts/views.py` の 7 箇所・IP キー・5/5m 等）は**そのまま維持**。DRF スロットルを全体に重ねる。ログイン POST では DRF `initial()`（スロットル）→ ハンドラ内 `@ratelimit` の順で両方が効く（anon 60/min ≫ 5/5m のため実質の律速は従来どおり django-ratelimit）。
- django-ratelimit の 403 応答・死にミドルウェア（`RATELIMIT_VIEW` 未定義）の是正は **I129（#235）のスコープ**（本計画では触れない）。

### クライアント IP 識別（NUM_PROXIES）
- 本番は nginx 1 段構成で `X-Forwarded-For` を付与（`nginx/default.conf:27` 確認済み）。DRF 既定（`NUM_PROXIES: None`・スパイクで確認）のままだと、本番では `REMOTE_ADDR`=nginx の IP に全未認証ユーザーが集約され **60/min を全員で共有**してしまう。→ `NUM_PROXIES: 1` を設定する（XFF の末尾=nginx が付与した実クライアント IP を採用。XFF ヘッダが無い直アクセス時は `REMOTE_ADDR` に自動フォールバック＝開発環境も安全）。

### E2E・テスト環境の無効化経路（既存資産の確認）
- `.github/workflows/e2e.yml:20` — `RATELIMIT_ENABLE: "false"` 設定済み（django-ratelimit 用・累積 POST が 5/5m を超えるため）。DRF スロットルを同スイッチに連動させれば **E2E 側の変更は不要**。
- `docker-compose.yml:46` — `RATELIMIT_ENABLE` はホスト env パススルー済み（手動テストでの切替に利用可能）。
- pytest は `core.settings` をそのまま使用（`backend/pytest.ini`・テスト専用 settings なし）→ 単体テストの無効化は conftest.py の autouse フィクスチャで行う（変更点4）。

### フロントエンド現状（429 の扱い）
- `frontend/src/services/api.ts:177-200` の `handleApiError` に 429 分岐がなく、429 は default 節「予期しないエラーが発生しました」に落ちる。toast は `react-hot-toast`（:2）。`/auth/` URL はスキップ（:169）・400 は呼び出し側処理（:174）という既存方針は不変更。
- api.ts は `export const apiClient = new ApiClient()`（:234）のシングルトン。レスポンスインターセプタは 1 本（:56-126）で、401 リフレッシュ処理の後に `handleApiError` が呼ばれる（429 は 401 分岐に入らず素通しで `handleApiError` へ・:122-124）。

### 適用規約（rules/ より抽出）
- Django: `test_*.py` 命名・`@pytest.mark.django_db`・未認証は素の `APIClient`・`rest_framework.status` 定数で assert（規約 L978-1123）。設定値のハードコード禁止（settings 集約）。Ruff/行長120/bandit MEDIUM 以上修正（pre-commit 自動強制）。
- React: 既存パターン踏襲（`handleApiError` の switch に case 追加のみ・新規状態管理なし）。テストは既存の Jest + Testing Library 構成に追随。

## 2. 受け入れ条件（Acceptance Criteria）
イシューの AC をそのまま採用:
- [ ] 未認証リクエストが設定レートを超過すると 429 を返す（回帰テストで固定）
- [ ] 通常利用（登録画面の科目取得・ログイン・クイズ回答のフロー）がレート制限に抵触しない（既存自動テスト・E2E が引き続き全 PASS）
- [ ] レート値（anon `60/min`・user `300/min`）が全体一律で適用され、設定値がハードコードでなく settings に集約されている
- [ ] DRF スロットルが `RATELIMIT_ENABLE=false` で無効化される（E2E CI の既存スイッチに連動）
- [ ] テスト実行環境でスロットルがテストを不安定化させない（回帰テストは LocMemCache＋低レートへ差し替え・その他テストはスロットル無効）
- [ ] 429 受信時にフロントで「リクエストが多すぎます。しばらく待ってから再試行してください」のトーストが表示される

## 3. 影響範囲
- **Backend**: `backend/core/settings.py`（Rate Limiting セクション）・`backend/core/throttling.py`（新規・案F）・`backend/core/exceptions.py`（429 分岐追加）・`backend/accounts/views.py`（`FieldValidationView` のスロットルをアプリ専用クラスへ 1 行差し替え・発見5）・`backend/core/cache_service.py`（キャッシュ属性の使用時解決化・発見6）・`backend/conftest.py`（新規）・`backend/core/tests/__init__.py`＋`backend/core/tests/test_I127_throttling.py`（新規）
- **Frontend**: `frontend/src/services/api.ts`（429 case 追加）・`frontend/src/services/__tests__/api.test.ts`（新規）
- **DB**: なし
- **Config/Infra**: なし（新規依存なし・requirements/package.json 不変更 → Dockerfile/compose 波及なし。E2E workflow も既存 `RATELIMIT_ENABLE=false` のまま不変更）
- **全 DRF エンドポイントの挙動変化**: レート超過時に新たに 429 が返り得る（通常利用レンジでは発生しない設計・TC-AUTO-05 で固定）。django-ratelimit 保護下の認証系は従来挙動（403）のまま（是正は I129）。

## 4. 変更点一覧

**修正アプローチ**: DRF 標準スロットルを settings に追加するだけで API 全体へ一律適用されるため、実装の中心は「設定 2 キー＋IP 識別 1 キー」。それを (a) 既存 `RATELIMIT_ENABLE` スイッチへの連動、(b) テストの決定論化（conftest で全テスト無効化＋回帰テストだけ明示有効化）、(c) 429 応答のユーザー向け整形（BE 統一 JSON・FE トースト）で包む。

| # | ファイル | 対象 | 変更内容 |
|---|---------|------|---------|
| 1 | `backend/core/settings.py` | Rate Limiting セクション（:286-289）＋`REST_FRAMEWORK` 本体（:142） | スロットル 3 キーを追加（クラスは `core.throttling` のアプリ専用クラスを**無条件**定義）＋DRF スロットル有効スイッチ `API_THROTTLE_ENABLED = RATELIMIT_ENABLE` を追加（下記コード例・発見4/案F）。あわせて `REST_FRAMEWORK` 本体（:142）に「スロットル設定は Rate Limiting セクション参照」の参照コメント 1 行を追加（リスク6回避策） |
| 2 | `backend/core/exceptions.py` | `custom_exception_handler`（:60 の 500 分岐の手前） | 429 分岐を追加（`main_message: 'リクエストが多すぎます'`・`sub_message: 'しばらく時間をおいて再度お試しください'`） |
| 3 | `backend/conftest.py`（新規） | — | 全単体テストでスロットルを無効化する autouse フィクスチャ（下記コード例） |
| 4 | `backend/core/tests/__init__.py`・`backend/core/tests/test_I127_throttling.py`（新規） | — | 429 回帰・無効化スイッチ・通常利用レンジの TC（TC-AUTO-01〜05・詳細は auto_test） |
| 5 | `frontend/src/services/api.ts` | `handleApiError` の switch（:177-200） | `case 429` を追加しトースト表示（下記コード例） |
| 6 | `frontend/src/services/__tests__/api.test.ts`（新規） | — | 429 トーストの回帰テスト＋既存 500 トーストの退行なし確認（TC-FE-01/02） |
| 7 | `backend/core/throttling.py`（新規） | — | 有効スイッチ・レート値をリクエスト時に settings からライブ評価するアプリ専用スロットルクラス（発見4/案F・下記コード例） |
| 8 | `backend/accounts/views.py` | `FieldValidationView`（:549） | `AnonRateThrottle` → `AppAnonRateThrottle` に 1 行差し替え（発見5 の退行是正・スイッチ/レート集約への追随） |
| 9 | `backend/core/cache_service.py` | `CacheService.__init__`（:23-28） | 4 つのキャッシュ属性を初期化時固定から使用時解決の `@property` へ変更（発見6 の既存負債根治・属性名不変で呼び出し側変更ゼロ） |

### 実装コード例

**変更点1** `backend/core/settings.py`（:286-289 の Rate Limiting セクションを以下に変更）:
```python
# Rate Limiting
# デフォルト True（本番・開発環境）。E2E CI では RATELIMIT_ENABLE=false を設定して無効化する（12-Factor App）。
# このスイッチは django-ratelimit（accounts の認証系）と DRF スロットル（API 全体・I127）の両方に効く。
RATELIMIT_ENABLE = os.environ.get('RATELIMIT_ENABLE', 'True').lower() != 'false'
RATELIMIT_USE_CACHE = 'default'

# DRF スロットル（I127: API 全体の基本レート制限。使用キャッシュは default=Redis・
# IGNORE_EXCEPTIONS=True のため Redis 断時はフェイルオープン=可用性優先）
# クラスリストは無条件の定数とし、有効スイッチ・レート値は core/throttling.py の
# アプリ専用クラスがリクエスト時にライブ評価する（import 時スナップショット回避・調査結果 発見4）。
API_THROTTLE_ENABLED = RATELIMIT_ENABLE  # DRF スロットル有効スイッチ（リクエスト時にライブ参照される）
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = [
    'core.throttling.AppAnonRateThrottle',
    'core.throttling.AppUserRateThrottle',
]
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '60/min',   # 未認証: IP ごと（登録画面の科目取得等は数 req/min で余裕）
    'user': '300/min',  # 認証済み: ユーザーごと（1 問/秒のクイズ回答=60 req/min でも 300/min に余裕で抵触しない）
}
# 本番は nginx 1 段（X-Forwarded-For 付与・nginx/default.conf）。XFF が無い直アクセスは
# REMOTE_ADDR に自動フォールバックするため開発環境でもこの値のままでよい。
REST_FRAMEWORK['NUM_PROXIES'] = 1
```
（`REST_FRAMEWORK` 本体（:142）でなくここで追記するのは、レート制限の設定・スイッチを 1 セクションに集約するため。3 キーとも無条件定義＝on/off はアプリ専用クラスが `API_THROTTLE_ENABLED` をリクエスト時に評価して決める）

**変更点7** `backend/core/throttling.py`（新規・全文）:
```python
from django.conf import settings
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LiveSettingsRateMixin:
    """有効スイッチとレート値をリクエスト時に settings から読む（I127）。

    DRF はスロットル設定（DEFAULT_THROTTLE_CLASSES/RATES）を初回 import 時に
    クラス属性へスナップショットするため、settings の実行時変更が反映されない。
    可変部分をここでライブ評価することで挙動を settings に一元化する（計画 発見4）。
    """

    def allow_request(self, request, view):
        if not settings.API_THROTTLE_ENABLED:
            return True
        return super().allow_request(request, view)

    def get_rate(self):
        return settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'][self.scope]


class AppAnonRateThrottle(LiveSettingsRateMixin, AnonRateThrottle):
    pass


class AppUserRateThrottle(LiveSettingsRateMixin, UserRateThrottle):
    pass
```

**変更点8** `backend/accounts/views.py`（`FieldValidationView`・発見5）:
```python
# import: from rest_framework.throttling import AnonRateThrottle → from core.throttling import AppAnonRateThrottle
    throttle_classes = [AppAnonRateThrottle]
```

**変更点2** `backend/core/exceptions.py`（500 分岐の直前に追加。※FE トースト文言（grill 確定）と BE `sub_message` は**意図的に別文言**: BE は既存 500 分岐の文体「しばらく時間をおいて〜」に合わせる。ユーザーが見るのは FE トーストのみ・plan-review Info 指摘に対する明示化）:
```python
        elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            custom_error_data['error']['main_message'] = 'リクエストが多すぎます'
            custom_error_data['error']['sub_message'] = 'しばらく時間をおいて再度お試しください'
```

**変更点3** `backend/conftest.py`（新規・全文）:
```python
import pytest


@pytest.fixture(autouse=True)
def _disable_api_throttling(settings):
    """単体テストでは DRF スロットルを無効化する（I127）。
    core/throttling.py のアプリ専用クラスが本フラグをリクエスト時に評価するため、
    ビューの import タイミングに依存せず確実に無効化される（計画 発見4・案F）。
    スロットル自体を検証するテストは override_settings(API_THROTTLE_ENABLED=True)
    で明示的に再有効化する（core/tests/test_I127_throttling.py 参照）。"""
    settings.API_THROTTLE_ENABLED = False
```
（プレーンな bool 設定のため DRF `api_settings` のリロード有無に依存しない。django-ratelimit が参照する `RATELIMIT_ENABLE` には触れないので、認証系の既存挙動はテストでも不変）

**変更点5** `frontend/src/services/api.ts`（`case 404:` ブロックの後に追加）:
```typescript
      case 429:
        toast.error('リクエストが多すぎます。しばらく待ってから再試行してください');
        break;
```

## 5. 実装手順（TDD・単一垂直スライス）

「settings（制限発生）→ exceptions（BE 応答整形）→ api.ts（FE 表示）」を 1 スライスで貫通する。

- **ステップ1: 回帰テスト先行（RED 確認）**
  1. `backend/conftest.py`・`backend/core/tests/`（TC-AUTO-01〜05）・`frontend/src/services/__tests__/api.test.ts`（TC-FE-01/02）を作成。
  2. 現行コードに対し実行し、**RED を記録**: TC-AUTO-02（429 body 文言）・TC-AUTO-03(b)（スイッチ有効側）・TC-AUTO-04（レート値）・TC-AUTO-05（実レート値取得）・TC-FE-01（429 トースト）が FAIL、TC-AUTO-01 は DRF 機構検証のため実装前でも GREEN（役割分担は auto_test 注記参照）、既存 76 件＋FE 7 件は GREEN のまま → auto_test「TDD RED 確認」参照。
- **ステップ2: 実装（ステップ1の RED 記録が前提）**
  1. 変更点7（throttling.py）→ 変更点1（settings）→ 変更点8（accounts 1 行）→ 変更点2（exceptions 429 分岐）→ 変更点5（api.ts case 429）を適用。
  2. TC-AUTO-01〜05・TC-FE-01/02 全 GREEN → TC-AUTO-06（BE 全体回帰 76＋新規）・TC-FE-03（FE 全体回帰）。
  3. 否定系 TC の false-green 注入検証を実施 → auto_test「false-green 自己検証」参照。
- **ステップ3: 実環境での縦貫通確認（ステップ2完了が前提）**
  1. dev 実サーバー（Redis 実経路）で 429 発生・`RATELIMIT_ENABLE=false` での無効化を確認 → manual_test No.1-3（Claude）。
  2. 登録画面でトースト表示を目視確認 → manual_test No.4（Human）。
  3. E2E は PR の CI（`RATELIMIT_ENABLE=false` 設定済み）で全 PASS を確認 → manual_test No.5（Claude）。

依存関係: ステップ2はステップ1の RED 記録が前提。ステップ3はステップ2の完了が前提。サービス再起動: settings.py 変更は dev サーバーの自動リロードで反映（manual No.2 の env 切替時のみ `docker compose up -d backend` で再作成・手順に明記）。

## 6. テスト計画

### 自動テスト（詳細: `docs/tests/open/I127_auto_test.md`）
- テストレベル: **API 結合テスト**（実 URL ルーティング〜スロットル〜例外ハンドラまでを検証。ユニットでなく結合を選ぶ理由 = 検証対象が settings→DRF dispatch→exception handler の配線だから）＋ **FE ユニットテスト**（インターセプタの分岐）。
- 決定論化: 429 系 TC は `override_settings` で **`API_THROTTLE_ENABLED=True`＋低レート値（`DEFAULT_THROTTLE_RATES` を `'3/min'` に差し替え）＋LocMemCache（全 4 エイリアス・発見1）** を適用し、テスト冒頭で cache clear。アプリ専用クラス（変更点7）がスイッチ・レートをリクエスト時にライブ評価するため実行順に依存しない（発見4・案F。案B のテスト用サブクラスは廃止）。実レート値（60/300）はテストから `settings` 参照で assert（ハードコード検知）。
- 再発防止: 「anon 超過 429（Retry-After 付き・統一 JSON 文言）」「`RATELIMIT_ENABLE=false` で無効」「通常利用レンジ（10 連続リクエスト）で 429 なし」を固定。
- 認可テスト: 認可変更なし（既存 I104/I115 テストは全体回帰 TC-AUTO-06 で退行検知）。

### 手動テスト（詳細: `docs/tests/open/I127_manual_test.md`）
- Claude: dev 実サーバー（実 Redis 経路）で 61 連打→429・`RATELIMIT_ENABLE=false` 切替→無制限・E2E CI 結果確認。
- Human: 登録画面（アカウント不要・一時低レート設定下）で 429 トーストの目視確認 1 件のみ。

## 7. ロールバック
- 変更点1・2 を元に戻し（settings の追記ブロックと exceptions の 429 分岐を削除）、`backend/conftest.py`・`backend/core/tests/`・FE の `case 429` と新規テストを削除すれば完全に従来動作へ戻る。DB 変更なし・マイグレーション不要。
- 運用中の緊急停止: コード変更なしで `RATELIMIT_ENABLE=false` を backend 環境変数に設定し再起動すれば DRF スロットルのみならず全レート制限が無効化される（切り戻しスイッチ）。

## 8. Risk & 回避策
- **リスク1（最重要・可用性）: レート値が実利用に対して低すぎて正常利用が 429 になる** → 回避: 値の根拠（登録画面=数 req・クイズ=1 問/秒でも 60/min）＋通常利用レンジ TC（TC-AUTO-05）＋E2E 全 PASS＋手動 No.4。発生時は settings の値変更のみで調整可能（コード変更不要）。
- **リスク2: 単体テストが散発的に 429 で落ちる（不安定化）** → 回避: conftest の autouse 無効化で決定論化（変更点3）。スロットル TC 側は locmem＋明示有効化＋cache clear で相互汚染なし。案F によりクラスリストは定数・可変部分はリクエスト時評価となり、import タイミング起因の実行順依存は構造的に解消（発見4・全体回帰で検証）。
- **リスク3: 本番で全未認証ユーザーが 1 バケット共有（nginx の IP に集約）** → 回避: `NUM_PROXIES: 1`（調査結果参照）。XFF 偽装は nginx が実クライアント IP を**末尾に追記**する仕様（`$proxy_add_x_forwarded_for`）＋DRF が末尾から `NUM_PROXIES` 個目を採用するため実質不可。
- **リスク3補足（既知の制約・plan-review Info）**: 同一 NAT/プロキシ配下の複数ユーザーは anon `60/min` の 1 バケットを共有する（IP キーの原理的制約）。本イシューの目的（大量収集の減速・Low）では許容し、キー戦略・値の見直しは I129（#235）の議論材料とする。
- **リスク4: Redis 断でスロットル停止（フェイルオープン）** → 許容: 既存 `IGNORE_EXCEPTIONS: True` の可用性優先方針と整合（イシュー確定・Low）。settings コメントに明記。
- **リスク5: `RATELIMIT_ENABLE` の名前が django-ratelimit 専用に見え、DRF 側の連動が伝わらない** → 回避: settings コメントで両機構への連動を明記（変更点1）＋TC-AUTO-03 でスイッチ連動を固定。
- **リスク6: `REST_FRAMEWORK` を後段で変更するため設定が 2 箇所に分かれ、読み手が見落とす** → 回避: `REST_FRAMEWORK` 本体（:142）側に「スロットル設定は Rate Limiting セクション参照」のコメントを 1 行追加する（変更点1に含める）。

## セキュリティ・ベストプラクティスチェック
- **認証・認可**: 変更なし（permission_classes は全ビュー不変更）。スロットルは認可の後段で作用する防御の追加であり、権限緩和はゼロ。
- **入力バリデーション**: 新規入力なし（設定値のみ）。レート値は settings 集約・ハードコードなし（AC）。
- **機密データ**: 429 応答に機密情報なし（固定文言＋Retry-After 秒数のみ）。スロットルのキャッシュキーは IP/user id のみ（既存ログと同等の情報量）。
- **OWASP**: A04/A05（レート制限の欠如）への直接対処が本イシュー。XSS/CSRF/SQLi: 影響なし（GET/POST の処理内容不変更・FE はトースト固定文言のみ）。
- **依存ライブラリ**: 追加なし → pip-audit/npm audit の新規対象なし。
- **bandit**: 対象は settings/exceptions の設定的変更のみ（MEDIUM 以上の新規指摘は想定なし・pre-commit で自動検証）。
- **フレームワーク準拠**: DRF 公式のスロットル機構（AnonRateThrottle/UserRateThrottle/NUM_PROXIES）をそのまま使用。独自実装なし。

## 高リスク判定
- **自己評価: No**。認証・認可・ロールの変更なし／個人情報・テナントデータの露出変化なし／外部公開 API の返却内容不変更（新規に返るのは 429 の固定文言のみ）。I115 のような権限クラス変更を含まない「防御の追加」であり、security-review の機械的該当条件に当たらないと判断。最終判定は `/plan-issue-review I127` に委ねる（Yes に上書きされた場合は `/security-review I127` を経由）。
- **確定フロー**: `/plan-issue-review I127` →（No のまま確定なら）`/implement I127`。

## 各種チェック結果
- **P3（データ整合性/DB）影響なし**: DB 変更なし。スロットルカウンタはキャッシュ（TTL 60 秒）のみ。
- **P5（運用設計）**: 該当（可用性に関わる設定変更）。構造化ログ: 429 は既存 `RequestLoggingMiddleware` がステータスを記録（追加実装なし）。切り戻し: `RATELIMIT_ENABLE=false`（ロールバック節）。段階リリース: 不要（dev→PR CI→マージの通常フロー・値は保守的に余裕を持たせた設計）。
- **P6（性能・UX）**: 該当（FE 変更あり）。ローディング/空状態: 変更なし（トースト追加のみ・既存 handleApiError パターン踏襲）。破壊的操作: なし。性能: スロットル判定はリクエストあたりキャッシュ GET/SET 各 1 回（既存 Redis・実測影響は手動 No.1 で確認）。
- **P8（コスト）影響なし**: 新規インフラ/外部サービスなし（既存 Redis 利用）。
- **P9（プライバシー）影響なし**: 個人情報・未成年データの新規取扱いなし（IP/user id のスロットルキーは一時キャッシュ・60 秒 TTL）。

## 設計判断の明示
| 設計判断 | 出所 |
|---------|------|
| レート値 anon `60/min`・user `300/min`・全体一律（Scoped なし） | イシュー明記（grill 確定） |
| `AnonRateThrottle`/`UserRateThrottle` を `DEFAULT_THROTTLE_CLASSES` に設定 | イシュー明記 |
| `RATELIMIT_ENABLE` 連動で無効化・E2E は既存設定のまま | イシュー明記（grill 確定） |
| 回帰テストは locmem＋低レート・その他テストは無効化 | イシュー明記（grill 確定） |
| FE 429 トースト文言 | イシュー明記（grill 確定） |
| django-ratelimit 併存維持（変更しない） | イシュー明記（I129 へ分離） |
| `NUM_PROXIES: 1` を設定（本番 nginx 1 段・全員 1 バケット問題の回避） | **仮定で決めた**（調査で必要性を特定。イシューは「クライアント IP 識別は計画で確定」と grill 回答で予告済み） |
| `core/exceptions.py` に 429 分岐を追加（統一 JSON の文言整形） | **仮定で決めた**（イシュー実装対象表にないファイル。スパイクで汎用文言を確認し AC「429 を返す」の品質向上として追加。却下なら汎用文言のまま=機能影響なし） |
| スロットル設定は Rate Limiting セクションに追記（`REST_FRAMEWORK` 本体は参照コメント 1 行のみ） | **仮定で決めた**（スイッチ・レート制限設定の 1 セクション集約を優先） |
| 単体テスト無効化は `backend/conftest.py`（新規）の autouse フィクスチャ | **仮定で決めた**（イシューの「その他の単体テストはスロットル無効で実行」の実現手段。テスト専用 settings 新設より小さい） |
| FE テストはインターセプタの rejected ハンドラを直接呼ぶ方式（`__tests__/api.test.ts` 新規） | **仮定で決めた**（axios モックライブラリ未導入のため。実装詳細は auto_test 参照） |
| 通常利用レンジ TC は「10 連続リクエストで 429 なし」で代表 | **仮定で決めた**（登録画面 initial load の実発行数は数 req・10 で十分に上回る） |
| 有効スイッチ・レート値はアプリ専用クラス（`core/throttling.py`）がリクエスト時に settings をライブ評価し、クラスリストは無条件定義（案F。案B のテスト用サブクラス方式は発見4 の実行順依存が残るため廃止・案C の monkeypatch は対症療法のため却下） | **ユーザー承認済み**（2026-07-19。調査結果の発見3〜5参照） |
| `FieldValidationView`（accounts）のスロットルを `AppAnonRateThrottle` へ 1 行差し替え | **ユーザー承認済み**（2026-07-19・発見5 の退行是正） |
| `CacheService` のキャッシュ属性を使用時解決の `@property` へ変更（初期化時スナップショットの既存負債根治） | **ユーザー承認済み**（2026-07-19・発見6 参照） |

→ 「仮定で決めた」6 項目は下の承認ポイントで確認する。

## 9. 承認ポイント（チェックリスト）
- [ ] settings 変更方式: Rate Limiting セクションで `RATELIMIT_ENABLE` 連動の 3 キー追加（コード例どおり・`REST_FRAMEWORK` 本体は参照コメントのみ）— でよいか
- [ ] `NUM_PROXIES: 1` の追加（本番 nginx で全未認証ユーザーが 1 バケットに集約される問題の回避・調査結果参照）— でよいか
- [ ] `core/exceptions.py` への 429 分岐追加（イシュー実装対象表外の 1 ファイル追加。文言「リクエストが多すぎます」/「しばらく時間をおいて再度お試しください」）— でよいか
- [ ] `backend/conftest.py`（新規・autouse でテスト時スロットル無効化）の追加 — でよいか
- [ ] FE テスト方式（インターセプタ直接呼び出し・`__tests__/api.test.ts` 新規）と TC 構成 — でよいか
- [ ] 手動テスト: Human 実施は「登録画面での 429 トースト目視（アカウント不要・一時低レート設定は Claude が準備/復元）」1 件のみ — でよいか
- [ ] 高リスク判定の自己評価 No（最終判定は plan-issue-review）— でよいか

## レビュー結果
- [20260719_0145 判定: ✅ 完了](../../reviews/I127_plan_review_20260719_0145.md)
- [20260718_1443 判定: ✅ 完了](../../reviews/I127_plan_review_20260718_1443.md)
