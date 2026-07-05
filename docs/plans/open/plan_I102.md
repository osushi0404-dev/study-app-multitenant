## 基本情報
- **計画書ID**: plan_I102
- **関連イシュー**: #192
- **Draft PR**: #195
- **作成根拠資料**: docs/issues/open/I102.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I102_review.md
- **作成日**: 2026-07-06

---

## 1. 背景/目的

問題管理 API（`ProblemViewSet` = `/api/problems/`）と管理画面（`QuizManagement` = `/quiz-management`）が、**組織管理者でない一般ユーザー（`role='user'`）にも参照・更新系を許している**。問題オーサリングは組織管理者の機能であり、`role='user'` は開発者/組織が用意したコンテンツを quiz 経由で消費する学習者である。

本イシューは **`ProblemViewSet` 全体（参照 list/retrieve ＋ 更新系 create/update/destroy・AI生成・画像）を組織管理者（`role == 'admin'`）限定**にし、FE・BE の二重ガードで担保する。

### 調査結果

**環境前提**（確認済み）:
- Docker サービス稼働中（backend / db healthy）。テストは `docker compose exec backend pytest` で実行可能。
- 既存 problems テストのベースライン: **45 passed**（`docker compose exec backend pytest problems/tests -q`、2026-07-06 実行）。

**コード現状**（確認済み）:
- `backend/problems/views.py:150` — `ProblemViewSet.permission_classes = [permissions.IsAuthenticated]` のみ（admin 限定でない）。custom action（`generate_ai`/`generate_adaptive`/`upload_image`/`delete_image`）に permission override は無く、viewset レベルの `permission_classes` が全アクションへ適用される。
- `backend/problems/views.py:23` — `IsOrgAdmin(permissions.BasePermission)` が既存（`request.user.role == 'admin'` 判定）。
- `frontend/src/components/AdminRoute.tsx:25` — 既存 `AdminRoute` は `is_staff || is_superuser` 判定（プラットフォーム staff 用。`role` とは独立フィールド）。→ 流用不可。
- `frontend/src/components/Layout.tsx:70` — `isOrgAdmin = user?.role === 'admin'` が既に定義され「科目管理」に使用（:75-77）。「問題管理」（:74）は条件なしで全ユーザーに表示。
- `frontend/src/services/types.ts:22` — `user.role: 'user' | 'admin'` は FE に露出済み。
- `/api/problems/` を GET/POST/PUT/DELETE する FE は `QuizManagement`（本イシューで admin 化）のみ。`quiz.service.ts` は `QuizManagement` からのみ import され実使用は `updateProblem` のみ（他メソッドは呼び出し0の死コード）。
- 非admin の出題・回答・結果は `QuizSessionViewSet`（`/api/quiz/*`）経由で `ProblemViewSet` を叩かない。
- `backend/accounts/management/commands/seed_e2e.py` の E2E ユーザーは `e2e_user_a`・`e2e_user_b` とも `role='admin'`（:69, :85）。**非admin identity が存在しない**。
- `e2e/global-setup.ts` は user A・B の storageState のみ生成、`e2e/playwright.config.ts` も同様。

**既存テストへの影響**（確認済み）:
- `/api/problems/` を叩く既存テストは **`test_I073_image_update.py` のみ**。fixture `env` の `user`/`user2` が `role='user'`（:132-139）で問題 CRUD（POST/PUT）を叩き 201/200 を期待。**I102 適用で 403 化し破綻する**ため fixture の admin 化が必須。
- `test_views.py` は quiz エンドポイントのみ、`test_I006` は `/api/subjects/` のみで影響なし。

### 原因の概要
`ProblemViewSet` の権限が「認証済みか否か」だけで判定され、問題オーサリングが管理者機能であることが認可に反映されていない。参照も全認証ユーザーに開いているが、確定した利用モデルでは `/api/problems/` の参照を必要とする非admin は存在しない（read consumer は管理画面のみ）。

---

## 2. 受け入れ条件（Acceptance Criteria）

- [ ] AC1: 非admin（`role != 'admin'`）が `GET/POST /api/problems/`・`GET/PUT/PATCH/DELETE /api/problems/{id}/`・`POST /api/problems/generate_ai/`・`POST /api/problems/generate_adaptive/`・`POST /api/problems/{id}/images/upload/`・`DELETE /api/problems/{id}/images/delete/{asset_id}/`（参照含む全経路）を叩くと **HTTP 403** を返す。
- [ ] AC2: admin（`role == 'admin'`）は参照・更新系を従来どおり 200/201 で実行できる。
- [ ] AC3: role ベースの新ガード `OrgAdminRoute`（`user.role === 'admin'`）が新設され、非admin が `/quiz-management` に遷移するとアクセス不可（`AdminRoute` と同一のインライン権限エラー表示）となる。org admin は `is_staff` の値に依らず到達できる。
- [ ] AC4: 非admin では `Layout.tsx` のナビに「問題管理」項目が表示されない（org admin には表示される）。
- [ ] AC5: BE 認可回帰テスト（role 別の結合テスト）が追加され全て PASS する。
- [ ] AC6: 既存 `test_I073_image_update.py` の fixture を admin 化し、当該テスト群が引き続き PASS する。
- [ ] AC7: E2E インフラに非admin identity（`seed_e2e.py` の `e2e_user_c`（`role='user'`）＋ `global-setup.ts` の storageState ＋ `playwright.config.ts` のプロジェクト）が追加され、E2E authz スモークが非admin 遮断・admin 到達を検証して PASS する。

---

## 3. 影響範囲（Backend / Frontend / DB / Config）

- **Backend**: `problems/views.py`（`ProblemViewSet.permission_classes`）、`problems/tests/`（認可回帰テスト新設＋`test_I073_image_update.py` fixture 整合）、`accounts/management/commands/seed_e2e.py`（非admin `e2e_user_c` 追加）
- **Frontend**: `components/OrgAdminRoute.tsx`（新設）、`App.tsx`（`quiz-management` ルート保護）、`components/Layout.tsx`（「問題管理」ナビ限定表示）
- **E2E**: `e2e/global-setup.ts`・`e2e/playwright.config.ts`（非admin storageState）、`e2e/tests/problem-management-authz.spec.ts`（新設）
- **DB**: なし（マイグレーションなし。seed はテストデータのみ）
- **Config/Infra**: `.claude/settings.json`（本 PR に allowlist の docs/issues 追加を同梱。機能に影響なし）

---

## 4. 変更点一覧（ファイル / 関数 / 変更内容）

| ファイル | 対象 | 変更内容 |
|---------|------|---------|
| `backend/problems/views.py` | `ProblemViewSet.permission_classes` | `[permissions.IsAuthenticated]` → `[permissions.IsAuthenticated, IsOrgAdmin]`（:150 を置換） |
| `backend/problems/tests/test_I102_problem_authz.py` | 新設 | role 別 authz 結合テスト（非admin=全経路403 / admin=200-201） |
| `backend/problems/tests/test_I073_image_update.py` | `env` fixture | `user`→org1 admin、`user2`→org2 admin（`role='admin'`）に変更 |
| `backend/accounts/management/commands/seed_e2e.py` | `handle` | 非admin `e2e_user_c@example.com`（`role='user'`・org_a）を追加 |
| `frontend/src/components/OrgAdminRoute.tsx` | 新設 | `user.role === 'admin'` 判定の route ガード（`AdminRoute` 構造踏襲・判定のみ差し替え） |
| `frontend/src/App.tsx` | `quiz-management` ルート | `<OrgAdminRoute>` でラップ＋ import 追加 |
| `frontend/src/components/Layout.tsx` | `menuItems` | 「問題管理」項目を既存 `isOrgAdmin` 条件付き表示に移動 |
| `e2e/global-setup.ts` | ユーザー配列 | `e2e_user_c` の storageState（`.auth/user_c.json`）生成を追加 |
| `e2e/playwright.config.ts` | `projects` | 非admin storageState を使うプロジェクト追加（または spec 内 `test.use`） |
| `e2e/tests/problem-management-authz.spec.ts` | 新設 | 非admin=メニュー非表示＋`/quiz-management` 遮断／admin=到達 |

---

## 5. 実装手順（ステップ）

> 各ステップの検証は自動テスト文書（`I102_auto_test.md`）の TC を参照する（ステップ本文に検証コマンドは書かない）。

### ステップ1: BE 認可（core・最優先） ＋ 認可回帰テスト
**修正方針**: `ProblemViewSet` 全体を admin 限定にし、非admin が参照含む全経路で 403 になることを回帰テストで固定する。これがセキュリティの核。

- `backend/problems/views.py` の `ProblemViewSet.permission_classes` を変更:
  ```python
  class ProblemViewSet(MultipartFormDataMixin, viewsets.ModelViewSet):
      serializer_class = ProblemSerializer
      permission_classes = [permissions.IsAuthenticated, IsOrgAdmin]  # 変更（read+write を admin 限定）
      ...
  ```
- `backend/problems/tests/test_I102_problem_authz.py` を新設（role 別に全経路を叩く結合テスト）。
- **IDOR 確認**: `upload_image`（`@action` url_path=`images/upload`）・`delete_image` は既存実装で `problem = self.get_object()` を呼び（views.py:607, 724）、`get_queryset` の org 絞り込み（:161）＋明示 org チェック（:610, 727）を通す。`IsOrgAdmin` 追加後も get_object 経由が維持され、org 絞り込みを迂回する自前実装になっていないことを実装時に確認する（他組織問題への画像操作＝IDOR が残らないこと）。
- → TC-AUTO-01〜03b・TC-AUTO-02b（匿名401）参照。
- 依存: なし（後続ステップの前提）。

### ステップ2: 既存テスト整合（`test_I073` fixture admin 化）
**修正方針**: ステップ1で 403 化する `test_I073_image_update.py` の被験ユーザーを「認可済み admin」にする（画像更新の振る舞いを検証するテストであり認可テストではないため）。

- `env` fixture の `user`（org1）・`user2`（org2）に `role="admin"` を付与:
  ```python
  user = User.objects.create_user(..., organization=org, role="admin")
  user2 = User.objects.create_user(..., organization=org2, role="admin")
  ```
- `test_other_org_cannot_edit`・`test_cross_org_subject_rejected` は user2 が org2 admin になることで、role ゲート 403 ではなく越境（SEC-1/get_queryset）による従来の拒否（400/404）を検証する意図が保たれる。
- → TC-AUTO-04 参照。
- 依存: ステップ1完了が前提。

### ステップ3: FE ガード（`OrgAdminRoute` ＋ ルート ＋ ナビ）
**修正方針**: BE と同じ「組織管理者」概念（`role === 'admin'`）で FE を二重ガードする。既存 `AdminRoute`（is_staff 判定）は流用しない。

- `frontend/src/components/OrgAdminRoute.tsx` を新設（`AdminRoute` の構造を踏襲し判定のみ `user.role !== 'admin'` に差し替え）:
  ```tsx
  import React from 'react';
  import { Navigate } from 'react-router-dom';
  import { useAuth } from '../contexts/AuthContext';
  import { Box, CircularProgress, Alert } from '@mui/material';

  interface OrgAdminRouteProps { children: React.ReactNode; }

  const OrgAdminRoute: React.FC<OrgAdminRouteProps> = ({ children }) => {
    const { user, loading } = useAuth();
    if (loading) {
      return (<Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}><CircularProgress /></Box>);
    }
    if (!user) { return <Navigate to="/login" replace />; }
    if (user.role !== 'admin') {
      return (<Box sx={{ p: 3 }}><Alert severity="error">このページにアクセスする権限がありません。管理者権限が必要です。</Alert></Box>);
    }
    return <>{children}</>;
  };

  export default OrgAdminRoute;
  ```
- `frontend/src/App.tsx`: `quiz-management` ルート（:78）を `<OrgAdminRoute><QuizManagement /></OrgAdminRoute>` でラップ＋ import 追加。
- `frontend/src/components/Layout.tsx`: 「問題管理」項目（:74）を既存 `isOrgAdmin ? [...] : []`（:75-77）ブロック内に移動:
  ```tsx
  ...(isOrgAdmin ? [
    { text: '問題管理', icon: <Quiz />, path: '/quiz-management' },
    { text: '科目管理', icon: <School />, path: '/subject-management' },
  ] : []),
  ```
- → TC-MANUAL No.1-4 参照（画面挙動）。
- 依存: なし（ステップ1と並行実施可能）。

### ステップ4: E2E インフラ拡張 ＋ authz スモーク
**修正方針**: 「非admin が UI で遮断される」ことを通しで検証するため、非admin identity を E2E に追加する（I104/I078 でも再利用できる基盤投資）。

- `backend/accounts/management/commands/seed_e2e.py`: 非admin ユーザーを追加:
  ```python
  User.objects.filter(email='e2e_user_c@example.com').delete()
  User.objects.create_user(
      email='e2e_user_c@example.com', user_id='e2e_user_c',
      password=self.e2e_password, organization=org_a, role='user',
  )
  ```
- `e2e/global-setup.ts`: `e2e_user_c` でログインし `.auth/user_c.json` を生成（既存 user A/B と同パターン）。
- `e2e/playwright.config.ts`: 非admin storageState を使うプロジェクト追加（または spec 内 `test.use({ storageState: '.auth/user_c.json' })`）。
- `e2e/tests/problem-management-authz.spec.ts` を新設: 非admin(`user_c`)→「問題管理」メニュー非表示＋`/quiz-management` 直アクセスで権限エラー／admin(`user_a`)→到達。
- → TC-AUTO-05（E2E）参照。
- 依存: ステップ1（BE 403）・ステップ3（FE ナビ/ルート）完了が前提。

---

## 6. テスト計画（自動 / 手動）

### 自動テスト（`I102_auto_test.md`）
- **BE 結合テスト**（`test_I102_problem_authz.py`）: role 別に全エンドポイントを叩き、非admin=403・admin=200/201 を検証（TC-AUTO-01〜03）。
- **既存テスト整合**（`test_I073_image_update.py`）: fixture admin 化後に当該20テストが PASS（TC-AUTO-04）。
- **E2E**（`problem-management-authz.spec.ts`）: 非admin 遮断・admin 到達（TC-AUTO-05）。

**テストレベルの選択**: 認可は結合テスト（DRF テストクライアントで role 別にエンドポイントを叩く）で検証。UI 遮断の通し確認は E2E。FE ガード単体の分岐は E2E でカバー（コンポーネント単体テストは追加しない）。

**false-green 防止**: 認可回帰テスト（非admin=403）は、`permission_classes` 変更**前**の現状では 200 を返す（ベースライン 45 passed が示すとおり非admin CRUD が通る）。変更**後**に 403 になることで初めて PASS する＝検証対象が壊れれば（permission を戻せば）不合格になる真のゲート。TC-AUTO-04（既存テスト整合）も、fixture を admin 化しなければ 403 で FAIL する。

### 手動テスト（`I102_manual_test.md`）
- 非admin ログインで「問題管理」メニュー非表示・`/quiz-management` 直アクセス遮断（Human: ブラウザ目視）。
- admin ログインで問題管理に到達・CRUD 可能（Human）。
- `OrgAdminRoute.tsx` の判定が `role === 'admin'` であること（Claude: ファイル確認）。

---

## 7. ロールバック
- 変更は認可の厳格化（許可範囲を狭める）とガード追加のみ。DB変更・破壊的マイグレーションなし。
- 切り戻し: `git revert` で PR のコミットを戻せば、`ProblemViewSet.permission_classes` は `[IsAuthenticated]` に、FE は元の全ユーザー表示に戻る。データ影響なし。

## 8. Risk & 回避策
- **Risk1: org admin が is_staff=False で FE から締め出される** → `OrgAdminRoute` は `role === 'admin'` で判定するため回避（既存 `AdminRoute`（is_staff）は使わない）。
- **Risk2: 既存 CI が test_I073 で赤化** → ステップ2で fixture を admin 化して回避（AC6）。
- **Risk3: I078 を先にマージすると is_correct が open read に漏れる** → I102（本 PR）を I078 より先にマージする hard 依存を PR 説明・イシューに明記済み。
- **Risk4: 非admin の既存正常利用を壊す** → 調査で `/api/problems/` の非admin 実利用者ゼロを確認済み（`quiz.service.getProblems` 未使用・出題は quiz 経由）。破壊なし。

## 9. 承認ポイント（後述）

---

## 13. 性能・UX設計（フロントエンド変更あり）
- **パフォーマンス**: N+1・キャッシュ影響なし（`ProblemViewSet.list` の per-user キャッシュは admin のみ到達で不変）。DB クエリ増減なし。
- **エラー状態**: 非admin が `/quiz-management` へ直接遷移した場合、`OrgAdminRoute` が既存 `AdminRoute` と同一のインライン権限エラー Alert（「このページにアクセスする権限がありません。管理者権限が必要です。」）を表示。未認証時は `/login` リダイレクト。
- **ナビ**: 非admin にはメニュー項目自体を出さない（デッドリンク回避）。UI レイアウトの他要素は不変。
- **アクセシビリティ**: MUI `Alert severity="error"` を使用（既存 `AdminRoute` と同等）。

## 15. プライバシー・コンプライアンス設計（テナントデータの操作範囲変更）
- 本変更は問題（テナントデータ）の**操作範囲を組織管理者に限定**する厳格化であり、マルチテナントの操作境界を明確化する（C2）。
- 個人情報・未成年データの新規収集・越境・目的外利用は無し。高リスク判定（未成年データ越境等）には該当せず、`/security-review` 必須対象ではない。ただし認可変更のため、通常のレビューで最小権限の原則を確認する。
- テナント越境（他組織 subject への create）は本イシューの対象外（I103 で対応）。本イシューの `IsOrgAdmin` は「非admin 遮断」のみを担い、admin 間の越境は get_queryset の org スコープ＋I103 が担保する。

## レビュー結果
- [20260706_0707 判定: ✅ 完了](../../reviews/I102_plan_review_20260706_0707.md)
