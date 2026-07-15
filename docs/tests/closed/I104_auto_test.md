# I104 自動テスト（BE 認可回帰）

対象: `backend/problems/tests/test_I104_subject_authz.py`（新規）
実行: `docker compose exec backend python -m pytest problems/tests/test_I104_subject_authz.py -q`

## fixture 前提
`test_I102_problem_authz.py` 踏襲。1 組織 `org` に `admin`（role='admin'）・`normal`（role='user'）・既存科目 `subject`（org 所属）を用意。更新系テストは `settings.MEDIA_ROOT = str(tmp_path)`（perform_create のフォルダ生成対策）。

| TC | 手順 | 期待結果（status_code / 副作用） |
|----|------|------|
| TC-AUTO-01 | 非admin 認証で `PUT /api/subjects/{id}/` `{"name":"改名"}`、`PATCH /api/subjects/{id}/` `{"name":"改名2"}`、`DELETE /api/subjects/{id}/` | すべて **403**。DB: `Subject.objects.get(id=...)` の `name` が変わらず・レコードが残存（`Subject.objects.filter(id=...).exists()` が True） |
| TC-AUTO-02 | 非admin 認証で `GET /api/subjects/`、`GET /api/subjects/{id}/` | 両方 **200** |
| TC-AUTO-03 | admin 認証で `POST /api/subjects/` `{"name":"新科目I104"}` → `PUT /api/subjects/{id}/` `{"name":"更新後"}` → `DELETE /api/subjects/{id}/` | **201**（`Subject.filter(name="新科目I104").exists()` True）→ **200**（name が "更新後" に更新）→ **204**（`Subject.filter(id=...).exists()` False = 物理削除） |
| TC-AUTO-04 | 未認証（force_authenticate なし）で `GET /api/subjects/` | **401** |
| TC-AUTO-05 | 非admin 認証で `POST /api/subjects/` `{"name":"不正科目I104"}` | **403**・`Subject.filter(name="不正科目I104").exists()` が False |

## 否定・回帰テストの false-green 自己検証（必須・実装時実施）
TC-AUTO-01/05 は「非admin が拒否される（403）」という否定判定。実装後に **失敗条件注入**で false-green でないことを確認する:
- `get_permissions()` の修正を一時的に元に戻す（update/destroy を else に戻す）と TC-AUTO-01 が **FAIL（200/204 を返す）** になること、修正を戻すと PASS することを確認し、結果を manual_test の該当行に記録する。
- 確認できない場合は判定ロジック（assert 対象）を修正してから採用する。

## 期待実行結果
全 5 TC PASS。既存 `test_I006_subject_org_admin.py`（12件）・`test_I102_problem_authz.py`（5件）も回帰なく PASS。

## 実行結果（/test I104・2026-07-15）
- **Backend pytest（全スイート・Docker）**: `61 passed, 3 warnings`（警告は imghdr Deprecation / Pagination UnorderedObjectList のみ・失敗なし）。I104 5TC 含む全件 PASS。
- **Frontend Jest（全スイート・Docker）**: `Test Suites: 2 passed / Tests: 7 passed`（react-router v6 deprecation 警告のみ・失敗なし）。
- **E2E（Playwright）**: 非該当（本イシュー「含まない: E2E の追加」・auto_test テスト計画で E2E 不要と明記）。
- 結論: 自動テスト全 PASS・回帰なし。
