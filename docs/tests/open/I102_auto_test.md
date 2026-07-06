# I102 自動テスト: 問題管理を組織管理者権限に限定

実行コマンド（例・実行は `/test` に委譲）:
- Backend: `docker compose exec backend pytest problems/tests -q`
- E2E: `docker compose exec frontend`（or e2e ランナー）で Playwright authz spec

結果:
- backend: （/test 実行時に記入）
- frontend/E2E: （/test 実行時に記入）

---

## TC-AUTO-01: 非admin は問題参照系（list/retrieve）で 403
**対象**: `test_I102_problem_authz.py`
**前提**: `role='user'` のユーザーで `force_authenticate`。自組織に問題1件が存在。
**手順/期待値**:
| 手順 | エンドポイント | 期待 status |
|------|---------------|-------------|
| GET 一覧 | `GET /api/problems/` | **403** |
| GET 詳細 | `GET /api/problems/{id}/` | **403** |

アサーション: `response.status_code == 403`。

## TC-AUTO-02: 非admin は問題更新系・AI生成・画像で 403
**対象**: `test_I102_problem_authz.py`
**前提**: `role='user'` のユーザーで `force_authenticate`。
**手順/期待値**:
| 手順 | エンドポイント | 期待 status |
|------|---------------|-------------|
| 作成 | `POST /api/problems/` | **403** |
| 更新 | `PUT /api/problems/{id}/` | **403** |
| 部分更新 | `PATCH /api/problems/{id}/` | **403** |
| 削除 | `DELETE /api/problems/{id}/` | **403** |
| AI生成 | `POST /api/problems/generate_ai/` | **403** |
| 適応生成 | `POST /api/problems/generate_adaptive/` | **403** |
| 画像追加 | `POST /api/problems/{id}/images/upload/` | **403** |
| 画像削除 | `DELETE /api/problems/{id}/images/delete/{asset_id}/` | **403** |

アサーション: 各 `response.status_code == 403`。
補足（IDOR 確認）: `upload_image`（views.py の `@action images/upload`）・`delete_image` はいずれも内部で `self.get_object()` を呼び、`get_queryset` の org 絞り込み（`subject__organization=request.user.organization`）＋明示 org チェックを通す。認可（IsOrgAdmin）追加後も get_object 経由が維持されていることを実装時に確認する（org 絞り込みを迂回する自前実装になっていないこと）。

## TC-AUTO-02b: 未認証（匿名）は 401
**対象**: `test_I102_problem_authz.py`
**前提**: 認証なし（`force_authenticate` しない）。
**手順/期待値**: `GET /api/problems/` → **401**（`IsAuthenticated` により、`IsOrgAdmin` の 403 より前に弾かれる＝認可レイヤーの責務分離を明示）。
アサーション: `response.status_code == 401`。

## TC-AUTO-03: admin は参照・更新系を従来どおり実行できる
**対象**: `test_I102_problem_authz.py`
**前提**: `role='admin'`（自組織）で `force_authenticate`。
**手順/期待値**:
| 手順 | エンドポイント | 期待 status |
|------|---------------|-------------|
| GET 一覧 | `GET /api/problems/` | **200** |
| GET 詳細 | `GET /api/problems/{id}/` | **200** |
| 作成 | `POST /api/problems/`（有効な choices 付き） | **201** |
| 更新 | `PUT /api/problems/{id}/` | **200** |
| 削除 | `DELETE /api/problems/{id}/` | **204**（`ProblemViewSet` は `destroy()` を override せず DRF 既定＝論理削除でも HTTP は 204 No Content。`perform_destroy` が `is_deleted=True` にする。実装時に実返却を確認し実態に合わせる） |

アサーション: 各 status が上記に一致。作成後 `Problem.objects.filter(...).exists()` が True。

## TC-AUTO-03b: admin はカスタムアクション（AI生成・画像）も従来どおり実行できる
**対象**: `test_I102_problem_authz.py`
**前提**: `role='admin'`（自組織）で `force_authenticate`。AI 生成は外部 API を叩くため `AIQuestionGenerator` を mock する（生成結果をスタブ）。
**手順/期待値**:
| 手順 | エンドポイント | 期待 status |
|------|---------------|-------------|
| AI生成（mock） | `POST /api/problems/generate_ai/` | **200**（`IsOrgAdmin` を通過し 403 にならない） |
| 適応生成（mock） | `POST /api/problems/generate_adaptive/` | **200** |
| 画像追加 | `POST /api/problems/{id}/images/upload/`（有効な画像） | **201** |
| 画像削除 | `DELETE /api/problems/{id}/images/delete/{asset_id}/` | **200** |

アサーション: 各 status が上記に一致（admin が全アクションで 403 にならないことを CI 回帰として固定。AC2 の「全アクション」を明示カバー）。

## TC-AUTO-04: 既存 test_I073 が fixture admin 化後も全て PASS（回帰）
**対象**: `test_I073_image_update.py`（fixture `env` の user/user2 を `role='admin'` に変更後）
**手順**: `docker compose exec backend pytest problems/tests/test_I073_image_update.py -q`
**期待値**: 20 テスト全て PASS。特に:
- `test_create_with_images_regression`: `POST /api/problems/` → **201**（admin なので通る）
- `test_other_org_cannot_edit` / `test_cross_org_subject_rejected`: user2（org2 admin）による他組織問題/subject への PUT → **400/404**（role ゲート 403 ではなく越境拒否＝従来意図を保持）

## TC-AUTO-05: E2E authz スモーク（非admin 遮断 / admin 到達）
**対象**: `e2e/tests/problem-management-authz.spec.ts`（前提: `seed_e2e` に `e2e_user_c`（`role='user'`）追加・`global-setup` で `.auth/user_c.json` 生成。spec は `browser.newContext({ storageState })` で user_c/user_a を切替＝`playwright.config.ts` 変更不要）
**手順/期待値**:
| 手順 | ユーザー | 期待 |
|------|---------|------|
| ナビ確認 | `e2e_user_c`（非admin） | サイドバーに「問題管理」項目が**存在しない** |
| 直アクセス | `e2e_user_c` で `/quiz-management` へ遷移 | 権限エラー（「このページにアクセスする権限がありません。管理者権限が必要です。」）が表示され管理 UI に到達しない |
| 到達確認 | `e2e_user_a`（admin） | 「問題管理」項目が表示され `/quiz-management` に到達（問題一覧 UI が見える） |

アサーション: Playwright の `expect(locator).not.toBeVisible()` / `expect(page.getByText('このページにアクセスする権限がありません。管理者権限が必要です。')).toBeVisible()` / admin 側で管理 UI 要素が visible。

---

## false-green 自己検証（回帰テストが実際に回帰を捕捉するか）
- **TC-AUTO-01〜03（非admin=403）**: `permission_classes` 変更**前**のベースラインでは非admin CRUD が 200/201 を返す（`pytest problems/tests` 45 passed = 現状は非admin でも通る）。変更後に 403 となって初めて PASS するため、`IsOrgAdmin` を除去すれば FAIL する真のゲート。
- **TC-AUTO-04**: fixture を admin 化しないと（`role='user'` のまま）ステップ1適用後に 403 で FAIL する。fixture admin 化で PASS に転じることを確認する。
- 確認方法: 実装ステップ1適用の直前/直後で TC-AUTO-01 を実行し、`200 → 403` の遷移を観測する（/test で記録）。

## 決定論ゲート（自動実走）
<!--
  本イシューの検証は BE 結合テスト（pytest）・E2E（Playwright）で、いずれも heavy のため /test に委譲する。
  grep 等の軽量決定論ゲート（実装トレースに留まり spec を検証しない）は false-green リスクがあるため置かない。
  → このセクションに実走コマンドは置かない（決定論ゲート無し）。
-->
