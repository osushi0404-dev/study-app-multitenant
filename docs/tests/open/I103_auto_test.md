# I103 自動テスト（越境 subject 書き込み防止）

- 関連: docs/issues/open/I103.md / docs/plans/open/plan_I103.md / GitHub #193
- 対象: `backend/problems/tests/test_I103_cross_org_create.py`（新規）
- 実行: `docker compose exec -T backend python -m pytest problems/tests/test_I103_cross_org_create.py -q`
- テストレベル: API 結合（DRF `APIClient`）

## fixture 方針
`test_I102_problem_authz.py` に倣い、**2組織**を用意する:
- org A: admin（`role='admin'`）＋ subject A
- org B: subject B（越境先。org B の admin/user は不要＝org A admin が org B subject を指定する越境をテスト）
- 既存 `_valid_payload(subject_id)`（multipart・choices は JSON 文字列リスト）を流用。

```python
@pytest.fixture
def setup(db):
    cat = OrganizationCategory.objects.create(name="I103", slug="cat-i103")
    org_a = Organization.objects.create(name="orgA_I103", slug="org-a-i103", category=cat)
    org_b = Organization.objects.create(name="orgB_I103", slug="org-b-i103", category=cat)
    admin_a = User.objects.create_user(
        email="admin_a_i103@example.com", user_id="admin_a_i103", password="pass",
        organization=org_a, role="admin")
    subject_a = Subject.objects.create(name="subjA", slug="subj-a-i103", organization=org_a)
    subject_b = Subject.objects.create(name="subjB", slug="subj-b-i103", organization=org_b)
    return {...}
```

## テストケース

| TC | 内容 | 手順（org A admin で認証） | 期待値 | 実施者 |
|----|------|------|--------|--------|
| TC-AUTO-01 | 越境 create=403 | `POST /api/problems/` に `_valid_payload(subject_b.id)`（multipart） | `status_code == 403` かつ `Problem.objects.filter(question="新規問題").exists() is False` | Claude |
| TC-AUTO-02a | 越境 generate_ai=403（save_to_db 既定=True） | `POST /api/problems/generate_ai/` に `{"subject_id": subject_b.id}`（json） | `status_code == 403` かつ Problem 未作成（org B に AI 問題が増えない） | Claude |
| TC-AUTO-02b | 越境 generate_ai=403（save_to_db=False） | `POST /api/problems/generate_ai/` に `{"subject_id": subject_b.id, "save_to_db": False}` | `status_code == 403` | Claude |
| TC-AUTO-03 | 越境 generate_adaptive=403 | `POST /api/problems/generate_adaptive/` に `{"subject_id": subject_b.id}` | `status_code == 403` かつ Problem 未作成 | Claude |
| TC-AUTO-04 | 自組織 create=201（正常系不変） | `POST /api/problems/` に `_valid_payload(subject_a.id)`（multipart・`settings.MEDIA_ROOT=tmp_path`） | `status_code == 201` かつ `Problem.objects.filter(question="新規問題", is_deleted=False).exists()` | Claude |
| TC-AUTO-05 | 自組織 AI 経路は非403（認可・org 検証通過） | `POST /api/problems/generate_ai/`・`generate_adaptive/` に `{"subject_id": subject_a.id}` | いずれも `status_code != 403`（org 検証を通過し生成処理へ進む。AI 未設定で 400/500 になり得るが 403 でないことが要点） | Claude |
| TC-AUTO-06 | 全体回帰 | `problems/tests/` 全体実行 | 新規 TC 全 PASS ＋ 既存 50 件 PASS（回帰なし） | Claude |

## false-green 自己検証（TDD RED 確認・実装時に実施）
否定/回帰 TC（TC-AUTO-01/02a/02b/03）は、**ガード追加前の現行コード**に対して先に実行し、以下の RED を確認・記録してから実装する（正常系合格だけの false-green 防止）:
- TC-AUTO-01: 現行は 201 を返す → `403` アサートで **失敗（RED）** することを確認。
- TC-AUTO-02a/02b/03: 現行は org 検証が無く 403 を返さない → **失敗（RED）** を確認。

RED を確認 → ガード追加 → 同 TC が GREEN、を各ステップで記録する。

## 注記
- 越境 AI 経路の 403 はガードが `Subject.objects.get` 直後（生成 try の前）に置かれることで、外部 AI 呼び出し前に返る＝テストは AI キー無しでも決定論的に成立する。
- TC-AUTO-05 は既存 `test_I102_problem_authz.py::test_admin_custom_actions_not_forbidden`（`!= 403`）と同じ非403 判定パターン。
