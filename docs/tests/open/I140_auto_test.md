# I140 自動テスト（personal 組織自動作成フォールバック廃止・slug なし登録回帰）

- 関連: docs/issues/open/I140.md / docs/plans/open/plan_I140.md / GitHub #251 / Draft PR #254
- 対象: `backend/accounts/tests/test_I140_personal_org_fallback.py`（新規・`accounts/tests/` パッケージは I131 で作成済み）
- 実行: `docker compose exec backend python -m pytest accounts/tests/test_I140_personal_org_fallback.py -q`
- テストレベル: API 結合（DRF `APIClient`・未認証。personal 不在時の登録挙動はルーティング〜ビュー〜DB を通す結合レベルでのみ検証できる。`--no-migrations` のテスト DB が「personal 不在」を決定論的に再現）

## fixture 方針
`test_I131_org_id_rename.py` に倣う。**personal 組織（type='personal'・is_active=True）は意図的に作らない**のが本イシューの前提状態:

```python
@pytest.fixture(autouse=True)
def _disable_django_ratelimit(settings):
    """登録ビューの @ratelimit(10/5m) は redis カウンタが実行間共有のため
    反復実行で flaky になる。公式スイッチで無効化(I131 と同方式)。"""
    settings.RATELIMIT_ENABLE = False


@pytest.fixture
def setup(db):
    """personal 組織を作らない(--no-migrations の素の DB = personal 不在状態)。
    ペイロードを有効値にするための school 組織・科目のみ用意する。"""
    cat = OrganizationCategory.objects.create(name="テストI140", slug="test-cat-i140")
    org = Organization.objects.create(
        name="組織I140", slug="org-i140", type="school", category=cat, is_active=True)
    subject = Subject.objects.create(name="科目I140", slug="subj-i140", organization=org)
    return {"cat": cat, "org": org, "subject": subject}
```

登録ペイロード（I131 と同形・パスワードは Django validators 通過値）:
```python
def _payload(user_id, subject_id):
    return {
        "user_id": user_id,
        "email": f"{user_id}@example.com",
        "password": "I140TestPass123!",  # pragma: allowlist secret（テスト用ダミー値）
        "password_confirm": "I140TestPass123!",  # pragma: allowlist secret
        "subject_ids": [subject_id],
    }
```

期待 400 body（views.py:78-84 の既存分岐・**完全一致** = 広域 except 経由の「エラーが発生しました」400 と区別）:
```python
EXPECTED_400_BODY = {
    "error": {
        "main_message": "組織の設定に失敗しました",
        "sub_message": "無効な組織URLまたはシステムエラー",
    }
}
```

## テストケース

| TC | 内容 | 手順 | 期待値 | 実施者 |
|----|------|------|--------|--------|
| TC-AUTO-01 | personal 不在・slug なし登録 400（本バグの再発防止） | 未認証 `APIClient()` で `POST /api/auth/register/`・`_payload("i140_user_a", setup["subject"].id)`・`format='json'` | `status_code == status.HTTP_400_BAD_REQUEST`。`response.json() == EXPECTED_400_BODY`（**body 完全一致**） | Claude |
| TC-AUTO-02 | 上記の際に組織が新規作成されない（自動作成廃止の固定） | TC-AUTO-01 と同一リクエストの前後で `Organization.objects.count()` を取得 | 前後で件数不変。かつ `Organization.objects.filter(slug='personal').exists() is False` | Claude |
| TC-AUTO-03 | 上記の際に error ログが記録される（環境異常の可観測化） | `caplog.at_level(logging.ERROR, logger='django')` 下で TC-AUTO-01 と同一リクエスト | `caplog.records` に `levelno == logging.ERROR` かつメッセージに `"Personal organization"` を含むレコードが 1 件以上存在 | Claude |
| TC-AUTO-04 | personal が非アクティブのみ存在する場合も 400（発現条件「非アクティブ化された環境」の固定） | fixture に加え `Organization.objects.create(name="個人利用I140", slug="personal", type="personal", category=cat, is_active=False)` を作成し、TC-AUTO-01 と同一リクエスト | `status_code == 400`・`response.json() == EXPECTED_400_BODY`・`Organization.objects.count()` 前後不変（非アクティブを active 化したり複製したりしない） | Claude |
| TC-AUTO-05 | フォールバック自動作成コードの不在（決定論 grep・exit code 判定） | `! grep -q "Organization.objects.create" backend/accounts/views.py` を実行（合格=exit 0） | exit 0（ビュー内に組織作成コードが存在しない = 文言変更で再実装されても検出できる。plan-review Info 指摘を反映し旧ログ文言依存から強化）。**実装前は exit 1（NG）になることを確認済み**（下記「事前検証」） | Claude |
| TC-AUTO-06 | 全体回帰 | `docker compose exec backend python -m pytest --tb=short -q` | 新規 TC 全 PASS + 既存 **90 件** PASS（baseline 2026-07-19・`test_I131_org_id_rename.py` の 6 件含む・回帰なし） | Claude |

注:
- 独立したテスト関数を書くのは **TC-AUTO-01〜04** の 4 つ（02/03 は 01 と同一リクエストだが、失敗内容を切り分けるため関数は分ける）。TC-AUTO-05 は grep コマンド、TC-AUTO-06 は pytest コマンド実行であり関数は書かない。
- 期待値の status は `rest_framework.status` の定数で assert する（規約準拠）。
- caplog は `'django'` ロガーが `propagate: True`（`core/enhanced_logging.py:322-326`・計画の調査結果）であることを前提に捕捉する。
- 認可: `AllowAny` 維持（変更なし）。未認証クライアントで全 TC を実行すること自体が現行認可の回帰固定。

## TDD RED 確認（実装前に実施・AC「修正前は FAIL」に対応）
テストファイル作成後、**実装前の現行コード**に対して先に実行し RED/GREEN の内訳を確認・記録してから修正する:
- 想定: TC-AUTO-01 → **RED**（現行はフォールバック create が IntegrityError → 広域 except の 400 「エラーが発生しました」= body 不一致）／ TC-AUTO-03 → **RED**（error ログなし・現行は create 失敗で warning にも到達しない）／ TC-AUTO-04 → **RED**（同上）／ TC-AUTO-02 → **GREEN の可能性あり**（IntegrityError で create が失敗し組織が残らないため。この TC の実効性は下記 false-green 注入で担保）
- TC-AUTO-05 は実装前 NG（exit 1）を事前検証済み（下記）。
- 記録欄: （実装時に記入）

## 決定論 TC の事前検証（TC-AUTO-05・失敗注入 = 現行コードそのもの）
`! grep -q "Organization.objects.create" backend/accounts/views.py` は「フォールバックが存在する状態」を検出して NG になることが実効性の条件。現行コード（= 失敗状態そのもの）に対して実行し **exit 1（NG）** を確認する:
- 記録欄（旧判定式・plan-review 前）: 2026-07-20 実施 `! grep -q "Personal organization was missing" ...` → **exit 1（NG）✅**
- 記録欄（強化後の判定式）: 2026-07-20 実施 → **exit 1（NG）✅**（現行 views.py:156 の `Organization.objects.create(` を検出して不合格 = 実装後に exit 0 へ転じることで「組織作成コードの不在」を機械判定できる）

## false-green 自己検証（否定系 assert・実装後に失敗注入で確認）
TC-AUTO-02（組織が新規作成されない）は**現行コードでも合格し得る**（IntegrityError で create 自体が失敗するため）。実装後に失敗条件を注入して RED になることを確認してから採用する（復元は必ず Edit ツールで行い、`git restore` は使わない＝実装差分保護。復元後に `git diff` が実装差分のみであることを確認）:
- 注入: `_get_organization` の `if not personal:` 節に、一時的に `personal = Organization.objects.create(name='注入', slug='personal', type='personal', is_active=True, category=OrganizationCategory.objects.first()); return personal`（category 付き = IntegrityError にならない自動作成）を挿入 → **TC-AUTO-01（201 化で body 不一致）・TC-AUTO-02（件数増加）・TC-AUTO-03（error ログなし）が RED** になることを確認 → Edit で復元。
- 記録欄: （実装時に記入）

## 実施記録
（/implement 時に記入）
