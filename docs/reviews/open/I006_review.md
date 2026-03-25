# レビュー文書: I006 企業・団体ごとの科目追加機能

## 基本情報
- **関連イシュー**: #006
- **関連計画書**: I006_plan
- **作成日**: 2026-03-24
- **ステータス**: レビュー待ち

---

## レビューチェックリスト

### Backend

#### accounts/serializers.py
- [ ] `UserSerializer` に `organization_name` フィールドが追加されている
- [ ] `source='organization.name'` で FK をたどっている
- [ ] `default=None` で organization なしユーザーも安全に扱える
- [ ] `read_only_fields` に `organization_name` が含まれている

#### problems/views.py — IsOrgAdmin パーミッション
- [ ] `IsOrgAdmin.has_permission` が `user.role == 'admin'` をチェックしている
- [ ] `message` が日本語で設定されている

#### problems/views.py — SubjectViewSet
- [ ] `get_permissions()` が実装されている
- [ ] `create` のみ `IsOrgAdmin` が適用されている（`update`/`destroy` は別イシュー）
- [ ] `list`, `retrieve` は `IsAuthenticated` のみ（既存動作を維持）
- [ ] `perform_create` が `transaction.atomic()` でラップされている
- [ ] `perform_create` でスラッグが自動生成されている
- [ ] スラッグ生成: ASCII slugify → 空の場合 UUID フォールバック
- [ ] スラッグ重複回避ループが存在する（同一組織内）
- [ ] `organization_id=request.user.organization_id` が設定されている
- [ ] `subject_service.invalidate_cache(org_id)` が呼ばれている
- [ ] `perform_create` 内でメディアフォルダ（`problem/`, `explanation/`）が作成されている
- [ ] フォルダパスが `org/{org.slug}/subjects/{slug}/problem(explanation)/` である
- [ ] `.gitkeep` ファイルを作成する
- [ ] フォルダ作成失敗時に例外が伝播し科目もロールバックされる

---

### Frontend

#### services/types.ts
- [ ] `User.organization_name?: string` が追加されている

#### QuizManagement.tsx
- [ ] `useAuth()` から `user` を取得している
- [ ] `isOrgAdmin = user?.role === 'admin'` で表示制御している（`is_staff` ではない）
- [ ] `fetchSubjects()` の後に組織名がアコーディオン見出しに表示される
- [ ] `newSubjectName` state が追加されている
- [ ] `addingSubject` state でボタン disabled 制御されている
- [ ] `handleAddSubject` が `POST /api/subjects/` を呼んでいる
- [ ] 成功後に `setNewSubjectName('')` でフォームがクリアされる
- [ ] 成功後に `fetchSubjects()` が呼ばれ一覧が更新される
- [ ] エラーレスポンスのメッセージがトーストで表示される
- [ ] `onKeyDown` で Enter キーによる追加が可能
- [ ] `ExpandMoreIcon` が正しく import されている
- [ ] MUI `Accordion` 関連コンポーネントが正しく import されている

---

### セキュリティ

- [ ] `role='user'` が `POST /api/subjects/` を呼んでも 403 が返ることを確認
- [ ] フロントエンドの `role` チェックは UX 用であり、バックエンドの `IsOrgAdmin` が本質的な保護
- [ ] 他組織の科目を作成できないことを確認（`perform_create` が `request.user.organization_id` を強制セット）

---

### テスト

- [ ] `test_I006_subject_org_admin.py` が新規作成されている
- [ ] 自動テストが全件パスする（TC-AUTO-001 〜 TC-AUTO-012）
- [ ] TC-AUTO-009: API経由でフォルダ作成を確認（シグナルではなく perform_create 経由）
- [ ] TC-AUTO-010: フォルダ作成失敗時に科目がロールバックされることを確認
- [ ] 手動テスト仕様書（I006_manual_test.md）の全テストケースがパスする

---

### 既存機能への影響

- [ ] `GET /api/subjects/` が正常動作する（role='user' でも一覧取得可能）
- [ ] `GET /api/organizations/subjects/` が正常動作する
- [ ] `POST /api/problems/` が正常動作する
- [ ] `UserSubjectAccess` のキャッシュ無効化シグナルが引き続き動作する
- [ ] ログイン API (`POST /api/auth/login/`) のレスポンスに `organization_name` が追加されている

---

## 実装後の確認コマンド

```bash
# role='admin' ユーザーで科目作成
curl -X POST \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{"name": "テスト科目"}' \
  http://localhost:8000/api/subjects/

# role='user' ユーザーで 403 確認
curl -X POST \
  -H "Authorization: Bearer {user_token}" \
  -H "Content-Type: application/json" \
  -d '{"name": "不正科目"}' \
  http://localhost:8000/api/subjects/

# フォルダ確認
ls -la backend/media/org/{org_slug}/subjects/{subject_slug}/
```

---

## レビュー結果

| 項目 | 結果 | コメント |
|------|------|---------|
| API 設計 | - | |
| セキュリティ | - | |
| テスト充足度 | - | |
| 既存機能への影響 | - | |
| コード品質 | - | |

**総合判定**: ✅ OK（自動テスト 12/12 PASS）

---

## NG 時の対応事項

（実装後に記入）
