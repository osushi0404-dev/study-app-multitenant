## 基本情報
- **計画書ID**: plan_I115
- **関連イシュー**: #213
- **Draft PR**: #228
- **作成根拠資料**: docs/issues/open/I115.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I115_review.md
- **作成日**: 2026-07-17

---

## 1. 背景/目的

未認証の新規登録画面用エンドポイント `SubjectViewSet.public` が **401 を返す既存バグ**を修正し、未認証での科目リスト取得（`@action(permission_classes=[AllowAny])` の設計意図）を復旧する。

- **原因の概要**: 「この API は誰でも見てよい」と宣言してあるのに、権限を一括で決める別の仕組みがその宣言を黙って上書きしてしまい、未ログインだと弾かれてしまう状態。
- **詳細な原因分析**:
  1. 未認証で `GET /api/subjects/public/` を実行 → DRF はビューの `get_permissions()` を呼んで適用する権限を決定する。
  2. `SubjectViewSet.get_permissions()`（`backend/problems/views.py:84-89`）は override されており、`self.action` が更新系なら `IsAuthenticated + IsOrgAdmin`、**それ以外はすべて `IsAuthenticated`** を返す。
  3. `@action(permission_classes=[AllowAny])` は `self.permission_classes` 経由（`get_permissions()` の**デフォルト実装**が参照）でしか効かないため、override により無効化される。
  4. `public` は override 内のどの分岐にも明示されておらず else に落ち、`IsAuthenticated` が課され 401。
- **根本原因（コードレベル）**: `backend/problems/views.py:87-89` — `get_permissions()` の else 分岐に `public` が落ちる（命令的 override が宣言的な action 単位権限を上書きする DRF の既知の相互作用）。I104 は更新系分岐のみ変更しており本バグは I104 以前から存在（退行ではない）。

## 調査結果

### 環境前提確認（2026-07-17 実施）
- `docker compose ps` → 停止中だったため `docker compose up -d backend db` で起動済み（backend / db / redis 稼働）。
- 手動テスト No.4（登録画面の目視）はフロントも必要 → 実施時に `docker compose up -d frontend` を起動する。

### バグ再現の実測（2026-07-17・develop 789826e）
`docker compose exec backend python manage.py shell -c "..."`（未認証 `APIClient`）で両ルートとも 401 を確認:
- `GET /api/subjects/public/?slug=personal` → **401**
- `GET /api/organizations/subjects/public/?slug=personal` → **401**

### ルーティング（両ルート登録の根拠）
- `backend/problems/urls.py:7` — `router.register(r'subjects', SubjectViewSet)` → `/api/subjects/public/`
- `backend/core/urls.py:24-27,36` — `organizations_router.register(r'subjects', SubjectViewSet)` → `/api/organizations/subjects/public/`
- 新規登録画面が実際に使うのは後者: `frontend/src/pages/Register.tsx:173` → `SubjectService.getSubjectsWithLoading` → `frontend/src/services/subjectService.ts:19`（`/api/organizations/subjects/public/?slug=${slug}`）。ルートは `/register` および `/register/:organizationSlug`（`frontend/src/App.tsx:70-71`）。
- 修正は viewset 共通の1箇所で両ルートに効く。回帰テストは**両ルート**を固定する（grill 確定）。

### public アクションの返却仕様（既存・不変更）
- `backend/problems/views.py:48-82`。レスポンス: `200` / JSON 配列 `[{"id": int, "name": str, "description": str}]`（`slug` 指定組織の科目のみ・`order_by('name')`）。
- 組織が存在しない/非アクティブな slug → `200` / `[]`（空リスト）。`slug` 未指定 → `'personal'`、`'register'` → `'personal'` 変換（レガシー対応）。
- 露出フィールドは科目名・説明のみ（個人情報なし）。エラーレスポンスは発生しない設計（常に 200）。

### 現行の権限マトリクス（I104 確定仕様・public 以外は不変更）
| action | 適用権限（修正後） | 修正前との差分 |
|--------|------------------|--------------|
| create/update/partial_update/destroy | `IsAuthenticated + IsOrgAdmin` | なし |
| public | **`AllowAny`（本修正で復旧）** | 401 → 200 |
| list/retrieve ほか | `IsAuthenticated` | なし |

### テスト baseline（事前実行済み・2026-07-17）
- `docker compose exec backend python -m pytest problems/tests -q` → **68 passed**（クリーン）。
- うち科目認可（`test_I104_subject_authz.py`）5 件・is_correct 露出（`test_I078_is_correct_exposure.py`）7 件は本イシューの回帰確認対象。

### 適用規約（rules/ultimate_django_coding_standards.md より抽出）
- テスト: `test_*.py` 命名・`@pytest.mark.django_db`・未認証は素の `APIClient`・`rest_framework.status` 定数で assert・複数ルートは `@pytest.mark.parametrize`（規約 L978-1123）。
- 認可: action 単位の権限分岐は `get_permissions()` の `self.action` 分岐パターン（`get_serializer_class` と同型・L421-429）。過剰開放しない（`AllowAny` は `public` のみ）。
- lint: Ruff / 行長120 / bandit MEDIUM 以上修正対象（自動強制）。docstring は公開 API に必須。
- React 規約: FE コード変更なしのため新たに適用される実装ルールなし。

## 2. 受け入れ条件（Acceptance Criteria）
イシューの AC をそのまま採用:
- [ ] 未認証で `GET /api/subjects/public/?slug=personal` と `GET /api/organizations/subjects/public/?slug=personal`（登録画面の実経路)の**両ルート**が **200** を返す
- [ ] 未認証で存在しない slug を叩いた場合の既存挙動（空リスト 200）は不変
- [ ] admin/非admin の既存の認可（create/update/destroy=admin、list/retrieve=認証ユーザー）が退行しない（I104 の回帰テストが引き続き PASS）
- [ ] 両ルートの未認証 200 を検証する回帰テストが追加され、修正前は 401 で FAIL・修正後は PASS することを確認済み（false-green でない）
- [ ] 新規登録画面（依存確認済み）で未認証で科目リストが表示されることを目視確認

## 3. 影響範囲
- **Backend**: `backend/problems/views.py`（`SubjectViewSet.get_permissions` のみ）、`backend/problems/tests/test_I115_public_unauth.py`（新規）
- **Frontend**: コード変更なし（`frontend/src/pages/Register.tsx` / `frontend/src/services/subjectService.ts` は依存確認済み・目視確認のみ）
- **DB**: なし
- **Config/Infra**: なし。依存関係ファイル変更なし → Dockerfile/compose 波及なし

## 4. 変更点一覧

| ファイル | 対象 | 変更内容 |
|---------|------|---------|
| `backend/problems/views.py` | `SubjectViewSet.get_permissions()`（:84-89） | 更新系分岐と else の間に `if self.action == 'public': return [permissions.AllowAny()]` を追加（イシューのコード例どおり）。docstring は既に「public(未認証登録用)は @action の AllowAny を維持」と記載済みのため不変更（実装が記述に追随する） |
| `backend/problems/tests/test_I115_public_unauth.py`（新規） | — | 両ルートの未認証 200・テナントスコープ・存在しない slug の空リスト 200・レガシー slug 変換（未指定/`register`→`personal`）・I104 認可回帰（テスト計画 TC-AUTO-01〜05） |

### 実装コード例

**修正アプローチ**: `get_permissions()` の override に `public` を明示する分岐を1つ追加し、`@action` が宣言している「未認証許可」を override 内でも保全する。他 action の権限リストは1文字も変えない。

`backend/problems/views.py`（:87-89 → 以下に変更）:
```python
    def get_permissions(self):
        """参照(list/retrieve)は認証ユーザー、更新系(create/update/partial_update/destroy)は
        組織管理者(role=='admin')限定（I104）。public(未認証登録用)は @action の AllowAny を維持。"""
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsOrgAdmin()]
        if self.action == 'public':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]
```
（差分は `if self.action == 'public': return [permissions.AllowAny()]` の2行のみ。import 追加不要 = `permissions` は既存 import）

## 5. 実装手順（TDD・単一垂直スライス）

本修正は「BE 権限1分岐 + 回帰テスト」の単一スライス（FE はコード変更なしのため縦貫通は BE→登録画面の目視確認で完結）。

- **ステップ1: 回帰テスト先行（RED 確認）**
  1. `test_I115_public_unauth.py` にテスト関数（TC-AUTO-01/03/05）を追加。
  2. 現行コードに対し実行: TC-AUTO-01/03/05（未認証 200 系）が **RED（401）** であることを確認・記録（= TC-AUTO-02）。既存 I104 テストは GREEN のまま → auto_test「TDD RED 確認」参照。
- **ステップ2: get_permissions 修正（ステップ1完了が前提）**
  1. 上記コード例どおり `public` 分岐を追加 → TC-AUTO-01/03/05 全 GREEN。
  2. テナントスコープ否定 TC の false-green 注入検証を実施 → auto_test「false-green 自己検証」参照。
  3. 全体回帰（problems/tests 68 件 + 新規）→ TC-AUTO-04 参照。
- **ステップ3: 登録画面の復旧目視（ステップ2完了が前提）**
  1. 未認証ブラウザで登録画面の科目リスト表示を確認 → manual_test No.4（Human）。

依存関係: ステップ2はステップ1の RED 記録が前提。ステップ3はステップ2の完了が前提。サービス再起動: 不要（dev サーバーのホットリロードで反映）。

## 6. テスト計画

### 自動テスト（詳細: `docs/tests/open/I115_auto_test.md`）
- テストレベル: **API 結合テスト**（DRF `APIClient`・URL ルーティング〜権限適用〜レスポンスまでを両ルートで検証。ユニットより結合を選ぶ理由 = バグの本体が「ルート→ get_permissions → action」の配線にあるため）。
- 再発防止: 未認証 200 を両ルートで固定（本バグの回帰テスト・TDD で修正前 401 の FAIL を記録）。
- 認可テスト: 他 action の認可退行は I104 テスト再実行 + 全体回帰で担保。テナントスコープ（他組織の科目が混ざらない）も否定 TC で固定。

### 手動テスト（詳細: `docs/tests/open/I115_manual_test.md`）
- Claude: 新規テスト・全体回帰の実行、dev 環境実 API の修正後 200 確認。
- Human: 未認証ブラウザで `http://localhost:3000/register` の科目リスト表示（アカウント不要 = 未認証確認のため）。

## 7. ロールバック
- `views.py` の追加2行を削除し、`test_I115_public_unauth.py` を削除すれば従来動作（401）へ完全に戻る。DB 変更なしのためマイグレーション不要。

## 8. Risk & 回避策
- **リスク1（最重要・情報露出）**: `AllowAny` 分岐の追加を誤って他 action に波及させ、認可が緩む。→ 回避: 分岐は `self.action == 'public'` の完全一致1箇所のみ（部分一致・in 判定を使わない）。I104 回帰テスト（更新系 403・未認証 list 401）+ 全体回帰で他 action の認可を固定。
- **リスク2**: `public` の返却内容が想定より広い（テナント越境・過剰フィールド）。→ 回避: 返却コードは不変更（slug 指定組織の id/name/description のみ）。TC-AUTO-01 でフィールド集合とテナントスコープを assert し、false-green 注入検証で否定 assert の実効性を確認。
- **リスク3**: 未認証公開により `public` がスクレイピング/列挙の対象になる（slug 総当たりで組織の科目名が読める）。→ 回避: 本エンドポイントの公開は元々の設計意図（登録画面用）で、露出は科目名/説明のみ・個人情報なし（イシュー確定）。レート制限等の新設は本イシューのスコープ外（既存方針不変更）。
- **リスク4**: 登録画面が BE 修正だけでは復旧しない（FE 側の未知の依存）。→ 回避: コード読解では `getSubjectsWithLoading` がエラー時 `[]` を返すだけで、200 復旧すれば表示される見込み。manual No.4 で検証し、NG なら実装を中断→計画書更新→承認の正規手順で対応。

## セキュリティ・ベストプラクティスチェック
- **認証・認可（本イシューの主対象）**: 変更は「元々 `@action(AllowAny)` で公開が宣言されていた `public` の復旧」のみ。最小権限は維持（`AllowAny` の適用は `self.action == 'public'` 完全一致に限定・更新系 admin/参照認証済みは不変更）。認可マトリクスを調査結果に明記。
- **情報露出**: 返却は slug 指定組織の科目 id/name/description のみ（個人情報・機密なし・返却コード不変更）。テナントスコープを否定 TC で固定。
- **入力バリデーション**: `slug` は `Organization.objects.filter(slug=..., is_active=True)` の ORM 完全一致（SQL インジェクション不可・既存コード不変更）。
- **OWASP**: A01（アクセス制御）= 本修正は宣言済み公開の復旧であり新規緩和ではない。XSS/CSRF: GET のみ・レスポンスは JSON 配列（変更なし）。
- **依存ライブラリ**: 追加なし → pip-audit/npm audit の新規対象なし。
- **bandit**: 対象は views.py の2行追加のみ。`AllowAny` は bandit 検出対象外（MEDIUM 以上の新規指摘は想定なし。pre-commit で自動検証される）。

## 高リスク判定
- **判定: Yes**（plan-review 2026-07-17 で確定・計画時の自己評価 No を上書き）。機械的な該当条件 =「認証・認可・ロール変更（`IsAuthenticated` → `AllowAny` への権限クラス変更）」「外部公開 API の変更（未認証アクセス可能エンドポイントの復旧）」。
- 計画時の自己評価（No）の根拠 —(1) 元々 `@action(AllowAny)` で公開が宣言されていた復旧のみ、(2) 露出は科目名/説明のみで個人情報なし、(3) 他 action 不変更 + 回帰テスト固定 — はレビューでも合理的と評価されており、security-review は主にリスク3（スクレイピング/列挙・レート制限方針）の確認に限定される見込み。
- **確定フロー**: `/plan-issue-review I115`（✅ 済）→ **`/security-review I115`** → `/implement I115`。

## 各種チェック結果
- **P3（データ整合性/DB）影響なし**: DB 変更なし。
- **P5（運用設計/外部API/非同期/バッチ）影響なし**: 外部連携・非同期なし。
- **P6（性能・UX）影響なし**: FE コード変更なし（既存の Loading/エラー処理は `getSubjectsWithLoading` に実装済み・不変更）。`public` のクエリは `values()` の単純 SELECT（既存・N+1 なし・キャッシュ不使用は未認証のための既存設計）。
- **P8（コスト）影響なし**: 新規インフラ/外部サービスなし。
- **P9（プライバシー）影響なし**: 個人情報・未成年データの新規取扱いなし（科目名/説明のみ・既存仕様の復旧）。

## 設計判断の明示
| 設計判断 | 出所 |
|---------|------|
| `get_permissions()` に `if self.action == 'public': return [permissions.AllowAny()]` を追加（分岐順: 更新系→public→else） | イシュー明記（解決方針のコード例どおり） |
| 両ルート（`/api/subjects/public/`・`/api/organizations/subjects/public/`）を回帰テストで固定 | イシュー明記（grill 確定） |
| FE コード変更なし・登録画面は目視確認のみ | イシュー明記（grill 確定） |
| 他 action の権限・`public` の返却内容は不変更 | イシュー明記（スコープ「含まない」） |
| テストファイル名 `test_I115_public_unauth.py` | 仮定で決めた（既存 `test_I###_*.py` 命名に準拠） |
| 両ルートは `@pytest.mark.parametrize` で網羅 | 仮定で決めた（規約のパラメータ化パターン準拠・実装詳細） |
| TC にテナントスコープ検証（他組織の科目が混ざらない・フィールドは id/name/description のみ）を含める | 仮定で決めた（イシュー C2「過剰な情報露出を増やさない…再確認」の具体化。返却コードは不変更のため回帰固定のみ） |
| 存在しない slug の空リスト 200 も両ルートで検証 | 仮定で決めた（AC は「既存挙動不変」とのみ記載。両ルート化はテナントスコープ TC と同型のため低コスト） |
| レガシー slug 変換（未指定/`register`→`personal`）の既存挙動も TC-AUTO-05 で固定 | plan-review の Info 指摘を反映（2026-07-17。personal 組織はマイグレーション 0014 で必ず存在するため決定論的） |

→ 「仮定で決めた」4項目は次の承認ポイントで確認する。

## 9. 承認ポイント（チェックリスト）
- [ ] 修正方式: `get_permissions()` へ `public` 分岐追加（イシューのコード例どおり・2行・他 action 不変更）— でよいか
- [ ] テストファイル名 `test_I115_public_unauth.py`・両ルートは parametrize で網羅 — でよいか
- [ ] TC にテナントスコープ検証（他組織科目の非混入・露出フィールドは id/name/description のみ）を含める（C2 再確認の具体化・返却コード自体は不変更）— でよいか
- [ ] 存在しない slug → 空リスト 200 の検証も両ルートで実施 — でよいか
- [ ] ~~高リスク判定 No（security-review 省略・plan-review 後に /implement へ）— でよいか~~ → **plan-review で高リスク判定 Yes に確定（2026-07-17）。/security-review I115 を経由するフローに変更**
- [ ] 手動テスト: Human 実施は「未認証ブラウザで `http://localhost:3000/register` の科目リスト表示確認」1件のみ（アカウント不要）— でよいか

## セキュリティレビュー結果

**実施日**: 2026-07-18

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Low | 認証・認可/マルチテナント | `public` の未認証公開により、**任意の有効な組織 slug を指定すれば誰でもその組織の科目カタログ（id/name/description）を読める**。テナント内限定情報のつもりで科目説明に内部情報を書く運用が将来発生すると露出する | これは登録画面用の**既存の設計意図**（イシュー確定・新規公開ではなく復旧）。**必須防御条件: 露出フィールドを `values('id', 'name', 'description')` の3つに固定**（TC-AUTO-01 のキー集合完全一致 assert + false-green 注入検証で恒久固定）。科目 description に機密を書かない運用は既存前提を維持 |
| Low | OWASP(A05)/可用性 | DRF に `DEFAULT_THROTTLE_CLASSES` が未設定（`core/settings.py:142-157` 確認・既存状態）のため、未認証 `public` への大量リクエスト（slug 総当たり列挙・スクレイピング）を減速する仕組みがない | 本イシュー以前からの既存構成（401 バグ発生前も public は公開設計）であり、露出は科目名/説明のみ・DB 負荷は単純 SELECT。**レート制限新設はスコープ外**（計画リスク3で明示済み）。処遇は /retro で判断 |

その他の分類: 認証・認可の変更範囲（`AllowAny` は `self.action == 'public'` 完全一致1分岐のみ・更新系 `IsAuthenticated + IsOrgAdmin`（`views.py:24-33` role 完全一致）と参照系 `IsAuthenticated` は不変更・I104 回帰テストで固定）／入力検証（`slug` は `Organization.objects.filter(slug=..., is_active=True)` の ORM 完全一致・SQLi 不可・型逸脱は空リスト 200）／機密情報（返却は教材メタデータ3フィールドのみ・個人情報/トークンなし・ログはパスとステータスのみ）／OWASP その他（CSRF: GET のみ・JSON レンダラ。IDOR: 露出する subject id から retrieve するには認証必須）／ファイル操作（なし）／外部通信（なし）／依存ライブラリ（追加なし）: **リスクなし**

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | `GET /api/subjects/public/`・`GET /api/organizations/subjects/public/` | 未認証 | 有効な組織 slug を指定して科目リストを取得 | 露出は slug 指定組織の id/name/description のみ（それ以上を返さない） | Yes: TC-AUTO-01（テナントスコープ + フィールド集合完全一致・false-green 注入検証付き） | No | なし（既存設計意図の範囲） | 封鎖 |
| 2 | 同上 | 未認証 | slug 総当たりで組織の存在と科目カタログを列挙・スクレイピング | 過剰取得の減速（レート制限） | No（スロットル未設定＝検証対象が存在しない） | No | スロットル未設定（既存構成・スコープ外）。露出データは公開設計の範囲内 | Low |
| 3 | `GET /api/subjects/` ほか list/retrieve | 未認証 | `public` 開放に便乗して他 action へ未認証アクセス | else 分岐の `IsAuthenticated` が 401 | Yes: I104 既存 TC（`test_anonymous_gets_401`）+ TC-AUTO-04（全体回帰） | No | なし | 封鎖 |
| 4 | `POST/PUT/PATCH/DELETE /api/subjects/` | 一般（role=user） | 更新系への権限昇格 | `IsAuthenticated + IsOrgAdmin` が 403 | Yes: I104 既存 TC（更新系 403・DB 未改変）+ TC-AUTO-04 | No | なし（本修正で不変更） | 封鎖 |
| 5 | `GET {route}?slug=<不正値・存在しない値・register>` | 未認証 | slug パラメータの異常値でエラー情報・過剰データを引き出す | ORM 完全一致で不一致は空リスト 200・レガシー変換は personal のみ | Yes: TC-AUTO-03（存在しない slug）+ TC-AUTO-05（未指定/`register`） | No | なし | 封鎖 |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 0件 | 0件 |
| Medium  | 0件 | 0件 |
| Low     | 2件 | 1件 |

### 残余リスク処遇
（/retro で決定する）
- 設計 Low-1（公開カタログの越境閲覧）: 既存設計意図の範囲。露出フィールド固定 TC で継続監視。
- 設計 Low-2 / シナリオ Low-2（スロットル未設定での列挙・スクレイピング）: 既存構成・本イシュースコープ外。レート制限導入の要否を /retro で判断（別イシュー候補）。

## レビュー結果
- [20260717_2345 判定: ✅ 完了](../../reviews/closed/I115_plan_review_20260717_2345.md)
- [code-review 20260718 VERDICT: OK](../../reviews/closed/I115_code_review_20260718_0109.md)

## 完了情報
- **完了日**: 2026-07-18
- **対応者**: Claude Code
- **レビュー結果**: OK（plan-review: ✅ 完了・Warning 1/Info 1 対応済み / security-review: Blocker 0・Low 3 処遇決定済み（Low-2 は I127 #232 で根治予定） / code-review: VERDICT OK・Low 2 対応済み）
- **テスト**: Backend 76 passed（既存 68＋新規 8・TDD RED/false-green 注入検証済み）・FE Jest 7 passed・E2E 7 passed・手動テスト全 4 項目 OK
- **retro 派生**: 予防処置 3 件 → I126（#231）起票 / 残余リスク Low（レート制限）→ I127（#232）起票
