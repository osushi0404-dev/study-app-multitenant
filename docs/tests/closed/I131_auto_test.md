# I131 自動テスト（organization_id 改名漏れ修正・validate-slug／登録 API 回帰）

- 関連: docs/issues/open/I131.md / docs/plans/open/plan_I131.md / GitHub #239 / Draft PR #248
- 対象: `backend/accounts/tests/test_I131_org_id_rename.py`（新規・`accounts/tests/` パッケージも新設）
- 実行: `docker compose exec backend python -m pytest accounts/tests/test_I131_org_id_rename.py -q`
- テストレベル: API 結合（DRF `APIClient`・未認証。ビュー/serializer とモデル定義の不整合はモデルを実際に通す結合レベルでのみ捕捉できるため）

## fixture 方針
`test_I115_public_unauth.py` に倣う。`--no-migrations` のためテスト DB に personal 組織は存在せず、**全組織を fixture で自作**する:

```python
@pytest.fixture(autouse=True)
def _disable_django_ratelimit(settings):
    """登録ビューの @ratelimit(10/5m) は redis カウンタが実行間共有のため
    反復実行で flaky になる。公式スイッチで無効化（E2E CI と同方式・I131 計画 リスク3）。"""
    settings.RATELIMIT_ENABLE = False


@pytest.fixture
def setup(db):
    cat = OrganizationCategory.objects.create(name="テストI131", slug="test-cat-i131")
    # type デフォルトは 'personal' のため、personal 以外には明示的に type="school" を
    # 与える（slug なし登録の既定組織検索 type='personal' に誤って拾われない・実装時修正）
    org = Organization.objects.create(
        name="組織I131", slug="org-i131", type="school", category=cat, is_active=True)
    inactive = Organization.objects.create(
        name="非アクティブI131", slug="org-inactive-i131", type="school",
        category=cat, is_active=False)
    personal = Organization.objects.create(
        name="個人利用I131", slug="personal", type="personal", category=cat, is_active=True)
    subject = Subject.objects.create(name="科目I131", slug="subj-i131", organization=org)
    subject_p = Subject.objects.create(name="科目P_I131", slug="subj-p-i131", organization=personal)
    return {"org": org, "inactive": inactive, "personal": personal,
            "subject": subject, "subject_p": subject_p}
```

登録ペイロード（有効系の共通形・パスワードは Django validators 通過値）:
```python
def _payload(user_id, subject_id):
    return {
        "user_id": user_id,
        "email": f"{user_id}@example.com",
        "password": "I131TestPass123!",  # pragma: allowlist secret（テスト用ダミー値）
        "password_confirm": "I131TestPass123!",  # pragma: allowlist secret
        "subject_ids": [subject_id],
    }
```

## テストケース

| TC | 内容 | 手順 | 期待値 | 実施者 |
|----|------|------|--------|--------|
| TC-AUTO-01 | validate-slug 有効 slug 200（本バグの再発防止） | 未認証 `APIClient()` で `GET /api/organizations/validate-slug/org-i131/` | `status_code == status.HTTP_200_OK`。`response.json() == {"valid": True, "organization_name": "組織I131", "organization_id": setup["org"].id}`（**body 完全一致** = キー集合固定・過剰露出なし） | Claude |
| TC-AUTO-02 | （TDD RED 確認用・**独立したテスト関数は書かない**） | 実装前に TC-AUTO-01/05/06/07 を先行実行し RED を記録する手順を指す（下記「TDD RED 確認」参照） | 実装前: 01→500・05/06→400・07→400(既存GREEN想定は下記参照)／実装後: 全 GREEN | Claude |
| TC-AUTO-03 | validate-slug 存在しない slug 404（既存挙動不変） | 未認証で `GET /api/organizations/validate-slug/no-such-org-i131/` | `status_code == status.HTTP_404_NOT_FOUND`。`response.json() == {"valid": False, "message": '組織 "no-such-org-i131" は見つかりません'}`（**body 完全一致** = ルート不在等の別要因 404 と区別） | Claude |
| TC-AUTO-04 | validate-slug 非アクティブ組織 404（既存挙動不変） | 未認証で `GET /api/organizations/validate-slug/org-inactive-i131/` | `status_code == status.HTTP_404_NOT_FOUND`。`response.json() == {"valid": False, "message": '組織 "org-inactive-i131" は見つかりません'}` | Claude |
| TC-AUTO-05 | 登録 API・組織 slug ルート 201（本バグの再発防止） | 未認証で `POST /api/auth/register/org-i131/`・`_payload("i131_user_a", setup["subject"].id)`・`format='json'` | `status_code == status.HTTP_201_CREATED`。body の `organization == "組織I131"`。`User.objects.get(user_id="i131_user_a").organization_id == setup["org"].id`（**指定組織に所属**）。`UserSubjectAccess.objects.filter(user=user, subject=setup["subject"]).count() == 1` | Claude |
| TC-AUTO-06 | 登録 API・slug なしルート 201（personal 既定・本バグの再発防止） | 未認証で `POST /api/auth/register/`・`_payload("i131_user_b", setup["subject_p"].id)` | `status_code == status.HTTP_201_CREATED`。`User.objects.get(user_id="i131_user_b").organization_id == setup["personal"].id` | Claude |
| TC-AUTO-07 | 登録 API・無効 slug 400（既存挙動不変） | 未認証で `POST /api/auth/register/no-such-org-i131/`・`_payload("i131_user_c", setup["subject"].id)` | `status_code == status.HTTP_400_BAD_REQUEST`。`response.json()["error"]["main_message"] == "組織の設定に失敗しました"`（views.py:79-84 の分岐 = AttributeError 経由の「エラーが発生しました」と**文言で区別**） | Claude |
| TC-AUTO-08 | 全体回帰 | `docker compose exec backend python -m pytest --tb=short -q` | 新規 TC 全 PASS + 既存 **84 件** PASS（baseline 2026-07-19・回帰なし） | Claude |

注:
- TC 番号と実装するテスト関数の対応: 独立したテスト関数を書くのは **TC-AUTO-01 / 03 / 04 / 05 / 06 / 07** の 6 つ。TC-AUTO-02 は手順（実装前の先行実行）、TC-AUTO-08 はコマンド実行（全体回帰）であり関数は書かない。
- 期待値の status は `rest_framework.status` の定数で assert する（規約準拠）。
- TC-AUTO-05/06 は DB 副作用（User/UserSubjectAccess）まで assert する（serializer→create の縦貫通確認）。認証メールは locmem backend のため実送信されず、送信失敗時もビューは継続する設計（views.py:112-114）のため 201 判定に影響しない。
- 認可: 両エンドポイントとも既存 `AllowAny` 維持（変更なし）。未認証クライアントで全 TC を実行すること自体が現行認可の回帰固定。

## TDD RED 確認（実装前に実施・AC「修正前は FAIL」に対応）＝ TC-AUTO-02
テストファイル作成後、**実装前の現行コード**に対して先に実行し RED/GREEN の内訳を確認・記録してから修正する:
- 想定: TC-AUTO-01 → **500 で RED**（views.py:230 AttributeError）／ TC-AUTO-05/06 → **400 で RED**（views.py:88 AttributeError）／ TC-AUTO-03/04 → GREEN（404 分岐は健在）／ TC-AUTO-07 → GREEN（組織不在分岐は views.py:88 より先に return）
- serializers.py:91 の FieldError は views.py:88 修正後に初めて到達するため、**RED の段階では顕在化しない**（3 箇所同時修正で GREEN 化することが検証になる）
- 記録欄: 実装前 `test_I131_org_id_rename.py` → **3 failed, 3 passed**（TC-AUTO-01 = 500・TC-AUTO-05/06 = 400 で RED ✅／TC-AUTO-03/04/07 = 既存挙動 GREEN・想定どおり・2026-07-19 確認済み）

## false-green 自己検証（否定系 assert・実装後に失敗注入で確認）
否定・回帰系 TC（404/400 の body 完全一致・所属組織 assert）は現行コードでも合格し得るため、**失敗条件を注入して RED になることを確認**してから採用する（復元は必ず Edit ツールで行い、`git restore` は使わない＝実装差分保護。復元後に `git diff` が実装差分のみであることを確認）:
- 注入1（validate-slug 404 body）: views.py の 404 分岐 `'valid': False` を一時的に `'ok': False` へ変更 → TC-AUTO-03/04 が **RED（body 不一致）** になることを確認 → 復元。
- 注入2（登録の所属組織）: views.py:88 の右辺を一時的に `setup` 外の固定値（例: `organization.id + 1`）へ変更 → TC-AUTO-05 が **RED（所属組織不一致 or 400）** になることを確認 → 復元。
- 記録欄: 注入1 → **RED（2 failed・TC-AUTO-03/04 が body 不一致で失敗）✅** ／ 注入2 → **RED（2 failed・TC-AUTO-05/06 が所属組織不一致で失敗）✅**（いずれも Edit で復元済み・復元後の `git diff` は実装差分 3 行のみ・2026-07-19）

## 実施記録（2026-07-19 /implement）
- **RED（実装前）**: `test_I131_org_id_rename.py` → **3 failed, 3 passed**（TC-AUTO-01 = 500・TC-AUTO-05/06 = 400 で RED／TC-AUTO-03/04/07 GREEN・想定どおり）
- **GREEN（実装後）**: `test_I131_org_id_rename.py` → **6 passed**（TC-AUTO-01/03/04/05/06/07）
  - 実装時修正: fixture の `org`/`inactive` に `type="school"` を明示（`Organization.type` デフォルト 'personal' のため、slug なし登録の既定組織検索に誤って拾われ TC-AUTO-06 が別要因 400 になる問題。テスト実装詳細の修正・本体コード無関係）
- **false-green 注入検証（Edit で注入→確認→Edit で復元）**: 上記記録欄のとおり 2 注入とも RED ✅。復元後の `git diff -- backend/accounts/views.py backend/accounts/serializers.py` は計画の 3 行のみであることを確認済み
- **TC-AUTO-08（全体回帰）**: `python -m pytest --tb=short -q` → **90 passed**（既存 baseline 84 + 新規 6・回帰なし）

## /test 実施記録（2026-07-19・環境パリティ最終確認）
- Backend 全体（Docker）: `python -m pytest --tb=short -q` → **90 passed**（TC-AUTO-01/03/04/05/06/07 含む・回帰なし）
- Frontend Jest（Docker）: **3 suites / 10 passed**
- E2E（Playwright・`docker compose --profile e2e run --rm e2e`）: **7 passed**（認証フロー・問題管理認可 I102・テナント分離・クイズセッション）
- 停止条件該当なし（全自動テスト PASS）
