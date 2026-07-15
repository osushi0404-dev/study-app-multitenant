# plan_I104: 科目管理を組織管理者権限に限定（非admin の科目 update/destroy を禁止・/subject-management ルートガード追加・参照は全ユーザー維持）

## 基本情報
- **計画書ID**: plan_I104
- **関連イシュー**: #196
- **Draft PR**: #（作成後に追記）
- **作成根拠資料**: docs/issues/open/I104.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I104_review.md
- **作成日**: 2026-07-15

---

## 1. 背景/目的

科目管理 API（`SubjectViewSet`）と画面（`/subject-management`）で、**組織管理者でない一般ユーザー（`role='user'`）が科目を編集・削除できる**認可穴がある。I102（問題管理を admin 限定化）の `/retro` で発見された、`quiz-management` と同型の穴の科目側。

本 I104 は、**科目の参照は全ユーザーに開いたまま**、更新系（create/update/partial_update/destroy）を組織管理者（`role == 'admin'`）に限定し、FE・BE の二重ガードで担保する。

### I102 との差異（重要）
問題(I102)は「参照も admin 限定」にしたが、科目は非admin も参照が必要（新規登録画面での科目選択・ダッシュボードでの科目表示が依存）。よって科目は「**参照(list/retrieve)=全ユーザー / 更新系=admin**」とする。

---

## 2. 調査結果

### 現状コード（根本原因）
`backend/problems/views.py` `SubjectViewSet.get_permissions()`（L84-88）:
```python
def get_permissions(self):
    """create は org admin のみ許可（update/destroy は別イシュー）"""
    if self.action == 'create':
        return [permissions.IsAuthenticated(), IsOrgAdmin()]
    return [permissions.IsAuthenticated()]
```
- `create` のみ `IsOrgAdmin`。`update`/`partial_update`/`destroy` は else に落ち `IsAuthenticated` のみ = **非admin が編集・削除可能**。コメントに「update/destroy は別イシュー」と既知未対応を明記。
- `perform_update`（L129-132）: `serializer.save()` 後にキャッシュ無効化。`perform_destroy`（L134-137）: `instance.delete()`（**物理削除**）後にキャッシュ無効化。→ destroy 成功時の DRF 既定ステータスは **204**、update は **200**。
- `public` アクション（L48）: `@action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny], url_path='public')` = 未認証登録用。**本イシューでは不変更**。

### FE 現状
`frontend/src/App.tsx`:
- `quiz-management`（L79）は既に `<OrgAdminRoute>` でラップ済み（I102）。
- `subject-management`（L84）・`subject-management/:id`（L85）は **未ラップ** = 非admin が直接 URL 入力で管理 UI に到達可能。

`frontend/src/components/OrgAdminRoute.tsx`（I102 新設）: `role !== 'admin'` の場合 MUI `<Alert severity="error">このページにアクセスする権限がありません。管理者権限が必要です。</Alert>` を表示（未ログインは `/login` へ Navigate）。**本イシューはこのガードを再利用**する（新規部品なし）。

### 再利用する既存部品
- BE: `IsOrgAdmin`（`role == 'admin'` 判定、I102 で導入済み）
- FE: `OrgAdminRoute`（`role === 'admin'` 判定、I102 で新設済み）
- テスト雛形: `backend/problems/tests/test_I102_problem_authz.py` / `test_I006_subject_org_admin.py`（fixture・APIClient パターンを踏襲）

### `public` 挙動の保全（設計判断）
最小変更として **`public` を含む else 分岐は一切変更しない**。`update`/`partial_update`/`destroy` を admin 分岐へ移すだけなので、`list`/`retrieve`/`public` の権限評価経路は変更前後で**同一**＝挙動保全がコード構造上保証される（`public` は明示的にスコープ外）。

### ベースライン
- 既存テスト `test_I006_subject_org_admin.py`（TC-001〜012）・`test_I102_problem_authz.py` は develop 上で PASS 済みの前提。本セッションでは docker テスト実行を見送ったため、ベースライン再実行と本 I104 追加テストは実装ステップ（`/test`）で一括実行・記録する。

---

## 3. 受け入れ条件（Acceptance Criteria）
- [ ] 非admin（`role != 'admin'`）が `PUT /api/subjects/{id}/`・`PATCH /api/subjects/{id}/`・`DELETE /api/subjects/{id}/` を叩くと **403** を返す（副作用なし）
- [ ] 非admin が `GET /api/subjects/`・`GET /api/subjects/{id}/` は従来どおり **200**（参照は維持）
- [ ] admin（`role == 'admin'`）は科目の作成(201)・更新(200)・削除(204)を従来どおり実行できる
- [ ] 未認証は `GET /api/subjects/` が **401**（`IsAuthenticated` が前段で遮断・回帰確認）
- [ ] 非admin が `/subject-management`・`/subject-management/:id` に直接遷移すると `OrgAdminRoute` の権限エラー（MUI Alert「管理者権限が必要です」）が表示され管理 UI に到達しない
- [ ] 上記を検証する認可回帰テストが追加され全て PASS する

---

## 4. 影響範囲

| 区分 | 対象 | 変更 |
|------|------|------|
| Backend | `backend/problems/views.py` `SubjectViewSet.get_permissions()` | `update`/`partial_update`/`destroy` を `[IsAuthenticated, IsOrgAdmin]` に。`create` は現状維持（admin）。`list`/`retrieve`/`public` は現状維持 |
| Backend | `backend/problems/tests/test_I104_subject_authz.py`（新規） | 認可回帰テスト |
| Frontend | `frontend/src/App.tsx` | `subject-management`・`subject-management/:id` ルートを `<OrgAdminRoute>` でラップ |
| DB | なし | — |
| Config/Infra | なし | 依存追加なし → P3/P5/P8 影響なし（Dockerfile / docker-compose 波及なし） |

---

## 5. 変更点一覧（ファイル/関数）

### 5-1. `backend/problems/views.py` — `SubjectViewSet.get_permissions()`
**修正方針**: 更新系（create/update/partial_update/destroy）を admin 分岐に集約し、参照系（list/retrieve）と `public` は現状の `IsAuthenticated` / `AllowAny` を保全する。

```python
def get_permissions(self):
    """参照(list/retrieve)は認証ユーザー、更新系(create/update/partial_update/destroy)は
    組織管理者(role=='admin')限定（I104）。public(未認証登録用)は @action の AllowAny を維持。"""
    if self.action in ('create', 'update', 'partial_update', 'destroy'):
        return [permissions.IsAuthenticated(), IsOrgAdmin()]
    return [permissions.IsAuthenticated()]
```

### 5-2. `frontend/src/App.tsx` — subject-management ルート
**修正方針**: `quiz-management`（I102）と同一パターンで 2 ルートを `<OrgAdminRoute>` でラップ。エラー表示・リダイレクト挙動は `OrgAdminRoute` に委譲（I102 実装と同一）。

```tsx
<Route path="subject-management" element={<OrgAdminRoute><SubjectManagement /></OrgAdminRoute>} />
<Route path="subject-management/:id" element={<OrgAdminRoute><SubjectDetail /></OrgAdminRoute>} />
```

### 5-3. `backend/problems/tests/test_I104_subject_authz.py`（新規）
`test_I102_problem_authz.py` の fixture・APIClient パターンを踏襲。TC 詳細は auto_test 文書参照。

---

## 6. 実装手順（ステップ）

**依存関係**: ステップ1（BE 認可）とステップ2（FE ガード）は独立・並行実施可。ステップ3（テスト）はステップ1完了が前提。

### ステップ1: BE — `get_permissions()` 是正（垂直: 認可レイヤー）
- `SubjectViewSet.get_permissions()` を 5-1 の通り修正。
- → 検証は TC-AUTO-01〜05 参照。

### ステップ2: FE — ルートガード追加
- `App.tsx` の subject-management 系 2 ルートを 5-2 の通り `<OrgAdminRoute>` でラップ。
- → 検証は手動テスト TC-MANUAL-01〜03 参照。

### ステップ3: 認可回帰テスト追加
- `backend/problems/tests/test_I104_subject_authz.py` を新規作成（auto_test の全 TC）。
- → TC-AUTO-01〜05 を実行・記録。

---

## 7. テスト計画

### 自動（BE 認可回帰・pytest）— `test_I104_subject_authz.py`
| TC | 内容 | 期待 |
|----|------|------|
| TC-AUTO-01 | 非admin が PUT/PATCH/DELETE `/api/subjects/{id}/` | すべて **403**・DB 未改変（科目名変わらず・レコード残存） |
| TC-AUTO-02 | 非admin が GET `/api/subjects/`・`/api/subjects/{id}/` | **200**（参照維持） |
| TC-AUTO-03 | admin が create/update/destroy | **201 / 200 / 204** |
| TC-AUTO-04 | 未認証で GET `/api/subjects/` | **401** |
| TC-AUTO-05 | 非admin の create（既存 I006 と重複するが本 TC でも固定） | **403**・DB 未生成 |

テストレベル: **結合（DRF APIClient）**。認可・テナント境界の検証が目的のため E2E は不要（イシュー「含まない」）。

### 手動（FE ルートガード）
| TC | 内容 |
|----|------|
| TC-MANUAL-01 | 非admin で `/subject-management` 直接遷移 → Alert「管理者権限が必要です」表示・管理 UI 非表示 |
| TC-MANUAL-02 | 非admin で `/subject-management/:id` 直接遷移 → 同上 |
| TC-MANUAL-03 | admin で両ルート遷移 → 従来どおり管理 UI 表示 |

詳細は `docs/tests/open/I104_auto_test.md` / `I104_manual_test.md`。

---

## 8. ロールバック
- BE: `get_permissions()` を元の `if self.action == 'create'` 形に戻す。
- FE: `<OrgAdminRoute>` ラップを外す。
- テストファイル削除。
- DB 変更なし → マイグレーションのロールバック不要。

---

## 9. Risk & 回避策
| Risk | 回避策 |
|------|--------|
| `public`（未認証登録用）を誤って認可対象に含め登録画面が壊れる | else 分岐を一切変更しない（`public` はスコープ外・経路不変）。手動でも登録画面の科目取得を回帰確認可 |
| 参照(list/retrieve)まで絞ってダッシュボード・登録画面が壊れる | TC-AUTO-02 で非admin の GET 200 を固定。`list`/`retrieve` は現状維持 |
| admin の既存操作が 403 になる回帰 | TC-AUTO-03 で admin の 201/200/204 を固定 |
| FE ガードのみで BE が素通り（片側ガード） | BE(get_permissions)・FE(OrgAdminRoute) の二重ガード。BE 側を TC-AUTO で担保 |

---

## セキュリティ・ベストプラクティスチェック
- **認可（最小権限）**: 更新系を `IsOrgAdmin` に限定。許可範囲を**狭める**変更で最小権限原則に適合。BE・FE 二重ガード。
- **入力バリデーション**: 本変更は認可のみ。入力処理は不変更 → 追加のサニタイズ不要。
- **機密データ**: パスワード・トークン・個人情報の扱いに変更なし。
- **OWASP**: A01（Broken Access Control）を是正する変更そのもの。XSS/SQLi/CSRF の新規面なし。
- **依存ライブラリ**: 追加・更新なし → pip-audit/npm audit 対象外。
- **スキャンツール**: コード追加は認可分岐とテストのみ。bandit MEDIUM 以上相当の新規リスクなし。

## テスト計画チェック
- 認可変更のため**認可・テナント境界テストを必須計上**（TC-AUTO-01〜05）。再発防止テスト = 本 TC 群がそれに該当（quiz と同型穴の再発防止）。テストレベルは結合を選択（理由: 認可は viewset+permission の結合層で決まる）。

## データ整合性・運用性・コスト設計チェック
- DB 変更なし・外部API/非同期/バッチなし・新規インフラなし → **P3/P5/P8 影響なし**。依存関係ファイル不変更 → Dockerfile/compose 波及なし。

## 性能・UX設計チェック
- FE はルートガード追加のみ（新規 UI なし）。エラー状態表示は `OrgAdminRoute` の既存 Alert に委譲。ローディングは `OrgAdminRoute` の既存 `CircularProgress`。破壊的操作の新規導線なし。パフォーマンス懸念（N+1・キャッシュ・ページネーション）なし → **P6 影響なし（新規設計不要）**。

## プライバシー・コンプライアンスチェック
- 個人情報・未成年データの新規取扱いなし。テナント越境・目的外利用なし（むしろ操作範囲を管理者に限定）→ **P9 影響なし**。高リスク判定（I043）非該当・`/security-review` 対象外。

## 設計品質チェック
- Fat View 化なし（分岐追加のみ）・Raw SQL なし・Props drilling なし。定数ハードコードなし（`role` 判定は既存 `IsOrgAdmin`/`OrgAdminRoute` に集約）。例外処理の新規面なし。

---

## 10. 承認ポイント（設計判断の出所）

| 設計判断 | 内容 | 出所 |
|---------|------|------|
| 更新系 = `[IsAuthenticated, IsOrgAdmin]` | create/update/partial_update/destroy を admin 限定 | **イシューに明記** |
| 参照 = `IsAuthenticated`（全ユーザー維持） | list/retrieve は絞らない | **イシューに明記**（I102 との差異） |
| `public` = AllowAny 維持・スコープ外 | else 分岐不変更で経路保全 | **イシューに明記**（含まない） |
| FE = `OrgAdminRoute` 再利用 | 2 ルートをラップ・エラー表示委譲 | **イシューに明記** |
| destroy 期待値 = 204 / update = 200 | `perform_destroy` 物理削除・DRF 既定 | コード確認で確定（仮定でなく実測） |
| テストファイル名 `test_I104_subject_authz.py` | I102 命名踏襲 | 仮定で決めた（命名規約の踏襲・軽微） |

「仮定で決めた」項目はテストファイル名のみ（既存命名規約の機械的踏襲であり設計影響なし）。それ以外はすべてイシュー明記事項。
```

## レビュー結果
- [20260715_1335 判定: ✅ 完了](../../reviews/I104_plan_review_20260715_1335.md)

## セキュリティレビュー結果

**実施日**: 2026-07-15

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| — | 認証・認可 | なし。更新系を `[IsAuthenticated, IsOrgAdmin]` に狭める変更。最小権限に適合。`IsOrgAdmin.has_permission` は `is_authenticated and role=='admin'` を要求 | 参照(list/retrieve)は `IsAuthenticated` 維持・`public` は経路不変（else 分岐を触らない） |
| — | マルチテナント | なし。`get_queryset()` が `subject_service.get_user_subjects(request.user)` で自組織スコープ。他組織 subject への update/destroy は queryset 外＝404 | admin であっても他組織 subject は 404（越境不可） |
| — | 入力検証 | なし。認可分岐のみ変更。入力処理・serializer 不変更 | — |
| — | 機密情報 | なし。ログ・レスポンスの露出面に変更なし | — |
| — | OWASP Top 10 | A01(Broken Access Control) を是正する変更。IDOR は既存 queryset スコープで防御済（同一組織内で全 admin が科目管理可＝設計意図） | 新規の XSS/SQLi/CSRF 面なし |
| — | ファイル操作 | なし。`perform_create` のフォルダ生成は既存・admin のみ到達（不変） | — |
| — | 外部通信 | なし | — |
| — | 依存ライブラリ | なし。追加・更新なし | — |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | `PUT/PATCH/DELETE /api/subjects/{id}/` | 一般(role=user) | 自組織の科目を改変・削除 | 403 で拒否・DB 未改変 | Yes: TC-AUTO-01 | No | なし | — |
| 2 | `POST /api/subjects/` | 一般 | 科目新規作成 | 403・未生成 | Yes: TC-AUTO-05 | No | なし | — |
| 3 | `GET /api/subjects/`, `/{id}/` | 一般 | 参照 | 200 維持（回帰） | Yes: TC-AUTO-02 | No | なし | — |
| 4 | `PUT/DELETE /api/subjects/{id}/` | 他組織 admin | 越境で他組織科目を改変 | 404（queryset 外） | 任意: TC-AUTO-06 追加推奨 | No | 既存 queryset 防御に依存 | Low |
| 5 | `/subject-management` 直 URL | 一般（画面） | 管理 UI 到達 | OrgAdminRoute で Alert・UI 非描画 | No | Yes: TC-MANUAL-01/02 | FE のみ（BE が本丸ガード） | — |
| 6 | `GET /api/subjects/public/` | 未認証 | 登録画面用科目取得 | 経路不変（AllowAny） | No | Yes: TC-SMOKE-01 | pre-existing 挙動に依存 | Low |

**サマリー**: Blocker 0 / High 0 / Medium 0 / Low 2（#4 越境404・#6 public 未認証、いずれも既存防御依存で新規リスクなし）。

### 残余リスク処遇
（/retro で決定する）
- Low #4: 越境 admin の 404 を固定する TC-AUTO-06 は任意追加（既存 queryset 防御に依存・本 PR で退行なし）。
- Low #6: `public` 未認証到達性は経路不変。TC-SMOKE-01 で /test 時にスモーク確認。401 なら pre-existing bug として別イシュー化を検討。
