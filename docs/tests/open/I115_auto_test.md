# I115 自動テスト（SubjectViewSet.public の未認証 200 復旧・両ルート回帰）

- 関連: docs/issues/open/I115.md / docs/plans/open/plan_I115.md / GitHub #213 / Draft PR #228
- 対象: `backend/problems/tests/test_I115_public_unauth.py`（新規）
- 実行: `docker compose exec backend python -m pytest problems/tests/test_I115_public_unauth.py -q`
- テストレベル: API 結合（DRF `APIClient`・URL ルーティング〜`get_permissions`〜action までの配線を検証）

## fixture 方針
`test_I104_subject_authz.py` に倣う。テナントスコープ検証のため2組織を作る:
- org_a（slug=`org-a-i115`・科目2件）/ org_b(slug=`org-b-i115`・科目1件）
- ユーザー作成は不要（未認証テストのため）。I104 回帰は既存テストファイルの再実行で担保

```python
BOTH_ROUTES = ["/api/subjects/public/", "/api/organizations/subjects/public/"]


@pytest.fixture
def setup(db):
    cat = OrganizationCategory.objects.create(name="テストI115", slug="test-cat-i115")
    # public は is_active=True の組織のみ返すため、前提条件として明示する（code-review Low 対応）
    org_a = Organization.objects.create(
        name="組織A_I115", slug="org-a-i115", category=cat, is_active=True)
    org_b = Organization.objects.create(
        name="組織B_I115", slug="org-b-i115", category=cat, is_active=True)
    sub_a1 = Subject.objects.create(name="科目A1_I115", slug="subj-a1-i115", organization=org_a)
    sub_a2 = Subject.objects.create(name="科目A2_I115", slug="subj-a2-i115", organization=org_a)
    sub_b1 = Subject.objects.create(name="科目B1_I115", slug="subj-b1-i115", organization=org_b)
    return {"org_a": org_a, "org_b": org_b,
            "sub_a1": sub_a1, "sub_a2": sub_a2, "sub_b1": sub_b1}
```

## テストケース

| TC | 内容 | 手順 | 期待値 | 実施者 |
|----|------|------|--------|--------|
| TC-AUTO-01 | 未認証 200 + テナントスコープ + 露出フィールド（両ルート） | 未認証 `APIClient()` で `GET {route}?slug=org-a-i115`（`@pytest.mark.parametrize("route", BOTH_ROUTES)`） | `status_code == status.HTTP_200_OK`。レスポンスは list・`len == 2`。name 集合が `{"科目A1_I115", "科目A2_I115"}` と一致（org_b の `科目B1_I115` を**含まない**）。各要素のキー集合が `{"id", "name", "description"}` と**完全一致**（過剰露出なし） | Claude |
| TC-AUTO-02 | （TDD RED 確認用・**独立したテスト関数は書かない**） | 実装前に TC-AUTO-01/03 を先行実行し RED を記録する手順を指す（下記「TDD RED 確認」参照） | 実装前: `401`（RED）／実装後: `200`（GREEN） | Claude |
| TC-AUTO-03 | 存在しない slug は空リスト 200（両ルート・既存挙動不変） | 未認証で `GET {route}?slug=no-such-org-i115`（parametrize） | `status_code == status.HTTP_200_OK`・レスポンス `== []` | Claude |
| TC-AUTO-05 | レガシー slug 変換の既存挙動不変（両ルート） | 未認証で `GET {route}`（slug 未指定）と `GET {route}?slug=register`（parametrize） | いずれも `status_code == status.HTTP_200_OK`・レスポンス `== []`（両者とも `'personal'` に解決される。personal 組織はマイグレーション 0014 で必ず存在し、テスト fixture は personal に科目を作らないため空リストで決定論的） | Claude |
| TC-AUTO-04 | 認可退行なし（I104 回帰 + 全体回帰） | `docker compose exec backend python -m pytest problems/tests -q`（`test_I104_subject_authz.py` 5件を含む全体） | 新規 TC 全 PASS + 既存 **68 件** PASS（更新系 403/admin CRUD/未認証 list 401 の I104 テストが引き続き GREEN） | Claude |

注:
- TC 番号と実装するテスト関数の対応: 独立したテスト関数を書くのは **TC-AUTO-01 / 03 / 05** の3つ（各 parametrize で両ルート網羅）。TC-AUTO-02 は手順（実装前の先行実行）、TC-AUTO-04 はコマンド実行（全体回帰）であり関数は書かない。
- TC-AUTO-05 は fixture の組織データを使わないため `setup` ではなく `db` fixture を受け取る（code-review Low 対応・余分な DB 操作と誤読の回避）。
- 期待値の status は `rest_framework.status` の定数で assert する（規約準拠）。
- TC-AUTO-01 のレスポンスはページネーションなしの素の JSON 配列（`public` は `Response(list(subjects))` を直接返す・`views.py:82`）。

## TDD RED 確認（実装前に実施・AC「修正前は 401 で FAIL」に対応）＝ TC-AUTO-02
TC-AUTO-01/03/05（未認証 200 系）は、**実装前の現行コード**に対して先に実行し RED を確認・記録してから修正する:
- 現行は `get_permissions()` の else 分岐で `IsAuthenticated` が課されるため、両ルートとも **401 → status assert で失敗（RED）**
- TC-AUTO-03/05 も現行では 401 のため RED（空リスト以前に到達しない）
- 記録欄: 実装前 `test_I115_public_unauth.py` → **`8 failed, 0 passed`**（両ルート×全 TC が 401 で FAIL・2026-07-18 確認済み ✅）

## false-green 自己検証（否定系 assert・実装後に失敗注入で確認）
TC-AUTO-01 の否定 assert（org_b 科目の非混入・フィールド集合の完全一致）は現行コードでも（200 になりさえすれば）合格するため、**失敗条件を注入して RED になることを確認**してから採用する:
- 注入1（テナントスコープ）: `public` の `Subject.objects.filter(organization=organization)` を一時的に `Subject.objects.all()` へ変更 → TC-AUTO-01 が **RED（org_b 科目混入で失敗）** になることを確認 → 戻す。
- 注入2（露出フィールド）: `.values('id', 'name', 'description')` に一時的に `'slug'` を追加 → TC-AUTO-01 が **RED（キー集合不一致で失敗）** になることを確認 → 戻す。
- **復元は必ず Edit ツールで注入前の内容に戻す**（`git restore` / `git checkout -- <file>` は禁止＝実装差分が未コミットの場合、注入と実装差分が共に失われるため）。復元後に `git diff` が実装差分のみであることを確認する。結果（RED 確認の有無）を本文書に記録する。
- 記録欄: 注入1 → **RED（2 failed・org_b 科目混入で失敗）✅** ／ 注入2 → **RED（2 failed・キー集合不一致で失敗）✅**（いずれも Edit で復元済み・復元後の `git diff` は実装差分2行のみ）

## 実施記録（2026-07-18 /implement）
- **RED（実装前）**: `test_I115_public_unauth.py` → **8 failed**（全 TC が 401・想定どおり）
- **GREEN（実装後）**: `test_I115_public_unauth.py` → **8 passed**（TC-AUTO-01×2・03×2・05×4）
- **false-green 注入検証（Edit で注入→確認→Edit で復元）**:
  - 注入1: `public` のクエリを `Subject.objects.all()` に一時変更 → TC-AUTO-01 **RED（2 failed）** ✅
  - 注入2: `.values()` に `'slug'` を一時追加 → TC-AUTO-01 **RED（2 failed）** ✅
  - 復元後の `git diff -- backend/problems/views.py` は `public` 分岐追加の2行のみであることを確認済み
- **TC-AUTO-04（全体回帰）**: `problems/tests` → **76 passed**（既存 68 + 新規 8・回帰なし）
