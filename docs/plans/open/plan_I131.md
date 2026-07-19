## 基本情報
- **計画書ID**: plan_I131
- **関連イシュー**: #239
- **Draft PR**: #248
- **作成根拠資料**: docs/issues/open/I131.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I131_review.md
- **作成日**: 2026-07-19

---

## 1. 背景/目的

`Organization` モデルの主キー改名（`organization_id` → `id`・migration 0021）の**改名漏れ**により壊れている API を修正し、新規登録導線を復旧する。

- **原因の概要**: データベース上の組織の ID 欄の名前を昔の `organization_id` から `id` に変えた際、プログラム側の参照を 3 箇所だけ直し忘れており、その 3 箇所を通る API（組織 URL 確認・新規登録）が必ず失敗する状態。
- **詳細な原因分析**:
  1. `backend/accounts/models.py:34` で `Organization` の PK は `id = models.AutoField(primary_key=True)` に改名済み（コメント「organization_idから変更」・migration `0021_rename_organization_id_to_id.py`）。
  2. **validate-slug**（`GET /api/organizations/validate-slug/<slug>/`）: 組織検索は成功するが、レスポンス組み立て（`views.py:230` `organization.organization_id`）で `AttributeError` → `except Exception`（views.py:239-244）が 500 に丸める。有効 slug で**常に 500**。
  3. **登録 API**（`POST /api/auth/register/`・`/api/auth/register/<slug>/`）: `_get_organization()` は必ず組織を返す（personal 自動作成つき・views.py:131-166）ため、直後の `views.py:88` `organization.organization_id` が**全リクエストで** `AttributeError` → `except Exception`（views.py:121-129）が 400 に丸める。**新規登録が全件不能**。
  4. さらに `serializers.py:91` の `Organization.objects.filter(organization_id=value)` は `Organization` に存在しないフィールドのため `FieldError`（実測済み）。views.py:88 だけ直しても serializer 検証で再び 400 になる（3 箇所すべての修正が必要）。
  5. いずれも広域 `except Exception` がエラーを丸めるため露見せず、両エンドポイントに自動テストが存在しないため回帰検知の網もなかった。
- **根本原因（コードレベル）**: 改名漏れ 3 箇所 — `backend/accounts/views.py:88`・`:230`（属性参照）、`backend/accounts/serializers.py:91`（クエリフィルタ）。

## 調査結果

### 環境前提確認（2026-07-19 実施）
- `docker compose ps` → backend / db / redis / frontend / celery 稼働中（backend healthy）。
- テスト実行は `docker compose exec backend python -m pytest`（既存慣例どおり）。

### バグ再現の実測（2026-07-19・APIClient・HTTP_HOST=localhost）
- `GET /api/organizations/validate-slug/personal/` → **500** `{"valid":false,"message":"エラーが発生しました"}`。サーバーログ: `views.py:230 AttributeError: 'Organization' object has no attribute 'organization_id'`（「Valid organization found: 個人利用」の後に発生）。
- `POST /api/auth/register/`（空 body）→ **400** `{"error":{"main_message":"エラーが発生しました","sub_message":"'Organization' object has no attribute 'organization_id'",...}}`。ログ: `views.py:88` の同一 AttributeError。**組織決定（personal）成功後・serializer 検証前に落ちるため、ペイロードの有効/無効に関係なく全件失敗**。
- `Organization.objects.filter(organization_id=1)` → **FieldError: Cannot resolve keyword 'organization_id' into field**（shell 実測。Choices に `id` はあるが `organization_id` はない）。

### 旧属性参照の全件列挙（grep・backend 全体・.venv/migrations 除外）
| 箇所 | 内容 | 分類 |
|------|------|------|
| `accounts/views.py:88` | `organization.organization_id`（登録ビュー） | **改名漏れ（修正対象）** |
| `accounts/views.py:230` | `organization.organization_id`（validate-slug） | **改名漏れ（修正対象）** |
| `accounts/serializers.py:91` | `Organization.objects.filter(organization_id=value)` | **改名漏れ（修正対象）** |
| `accounts/serializers.py:29,47,58,100` | API 入力フィールド名 `organization_id`（契約・維持） | 正当（不変更） |
| `accounts/serializers.py:63` | `Subject.objects.filter(organization_id=...)` | 正当（Subject の FK attname） |
| `accounts/serializers.py:107-108`・`accounts/views.py:106` | `user.organization_id` | 正当（User の FK attname） |
| `core/subject_service.py:42,46,90,97` | `user.organization_id` | 正当（FK attname） |
| `problems/views.py:105〜762`（14 箇所） | `user/subject/problem.organization_id`・`MediaAsset/ProblemMediaAsset` 作成時の FK attname | 正当（FK attname） |

→ 修正対象は **accounts の 3 箇所のみ**。レスポンスキー名・serializer の入力フィールド名 `organization_id` は API 契約として維持（FE 影響なし）。

### ルーティング・FE 消費箇所
- validate-slug: `backend/accounts/urls.py:24-26`。FE 消費は `frontend/src/pages/Register.tsx:110-122` のみ（`valid` / `organization_name` のみ参照。404 以外のエラーは一律「組織の確認中にエラーが発生しました」表示 = 現在 500 でこの文言が出続ける）。
- 登録: `backend/accounts/urls.py:17-18`（slug なし/あり両ルート・同一ビュー）。

### テスト前提（pytest 設定・スロットル）
- テスト baseline（2026-07-19・develop b7286cd 相当）: `docker compose exec backend python -m pytest --tb=short -q` → **84 passed**（クリーン）。
- `backend/pytest.ini`: `testpaths = .`・`--no-migrations` → **テスト DB に migration 0014 の personal 組織は存在しない**。イシューの「personal は必ず存在」は dev 実環境の話であり、テストは fixture で組織を自作する。`accounts/tests/` パッケージ（`__init__.py` あり）は problems/core と同じ慣例で新設すれば自動発見される。
- DRF スロットル（I127）: `backend/conftest.py` の autouse fixture が `API_THROTTLE_ENABLED=False` で無効化（考慮不要）。
- **django-ratelimit（別系統・要対応）**: 登録ビューは `@ratelimit(key='ip', rate='10/5m')`（views.py:61）付き。`RATELIMIT_ENABLE` は env デフォルト True（settings.py:290）でテストでも有効・redis カウンタは実行間で共有されるため、**登録 TC の反復実行が 5 分窓で 429/403 化し flaky になり得る**。→ 新規テストファイルにファイルローカル autouse fixture `settings.RATELIMIT_ENABLE = False` を置いて無効化する（E2E CI が env で無効化しているのと同じ公式スイッチ・django-ratelimit はリクエスト時に評価）。
- メール送信: 登録成功時の認証メールは pytest-django の test 環境（locmem backend）で実送信されず、送信失敗時もビューが継続する設計（views.py:112-114）のため 201 判定に影響しない。

### 適用規約（rules/ultimate_django_coding_standards.md より抽出）
- テスト: `test_*.py` 命名・fixture ベース・未認証は素の `APIClient`・`rest_framework.status` 定数で assert・AAA 構成（規約 L978-1123）。
- 認可: 変更なし（両ビューとも既存の `AllowAny` を維持。権限クラスに触れない）。
- lint: Ruff / bandit MEDIUM 以上修正対象（pre-commit で自動強制）。
- React 規約: FE コード変更なしのため新たに適用される実装ルールなし。

### スコープ判断（イシューからの拡張・承認ポイント第1項）
イシューは validate-slug（views.py:230）のみを実装対象とするが、調査で**同一根本原因（organization_id 改名漏れ）の残り 2 箇所が新規登録を全件 400 にしている**ことが実測で確定した。イシューの目的「組織スラッグ経由の新規登録の復旧」は 230 だけ直しても達成されない（組織名表示は直るが登録送信が失敗する）ため、**3 箇所すべてを I131 で修正することを推奨**する（根治・同一改名スイープの完結。修正は計 3 行・レスポンス/API 契約は不変更）。
- 代替案（非推奨）: 登録 API 分を別イシュー化 — タイトル案「I139: 登録API（auth/register）が organization_id 改名漏れで全件400 — 新規登録不能の修正」。この場合 I131 完了後も登録は壊れたまま。
- 承認された場合、イシュー本文（実装対象・スコープ・AC・ユーザー影響）を本計画と整合するよう更新し、`gh issue edit 239 --body-file docs/issues/open/I131.md` で GitHub に同期する（実装ステップ0）。

## 2. 受け入れ条件（Acceptance Criteria）
イシューの AC ＋ スコープ拡張分（*印）:
- [ ] 有効な組織スラッグで `GET /api/organizations/validate-slug/<slug>/` が 200・`valid: true`・正しい `organization_name`/`organization_id` を返す（回帰テストで固定）
- [ ] 無効なスラッグで 404・`valid: false` を返す（既存挙動の維持・回帰テストで固定）
- [ ] *有効ペイロードで `POST /api/auth/register/<slug>/`（組織 slug 経由）と `POST /api/auth/register/`（personal 既定）が 201 を返し、ユーザーが指定組織に所属し科目アクセス権が作成される（回帰テストで固定）
- [ ] 登録画面 `/register/personal` で組織名が表示され「組織の確認中にエラーが発生しました」が出ない（手動確認）
- [ ] *登録画面から新規登録が完了する（手動確認）
- [ ] 既存テストが全 PASS（baseline 84 件）
- [ ] 回帰テストは修正前に FAIL（validate-slug: 500・登録: 400）することを確認済み（false-green でない）

## 3. 影響範囲
- **Backend**: `accounts/views.py`（2 行）・`accounts/serializers.py`（1 行）・`accounts/tests/`（新規パッケージ: `__init__.py` + `test_I131_org_id_rename.py`）
- **Frontend**: コード変更なし（レスポンスキー・API 契約維持のため。`Register.tsx` は目視確認のみ）
- **DB**: なし（モデル・マイグレーション不変更。改名は 0021 で完了済み）
- **Config/Infra**: なし。依存関係ファイル変更なし → Dockerfile/compose 波及なし

## 4. 変更点一覧

| ファイル | 対象 | 変更内容 |
|---------|------|---------|
| `backend/accounts/views.py` | `UserRegistrationView.create`（:88） | `organization.organization_id` → `organization.id`（1 行） |
| `backend/accounts/views.py` | `OrganizationSlugValidationView.get`（:230） | `organization.organization_id` → `organization.id`（1 行） |
| `backend/accounts/serializers.py` | `UserRegistrationSerializer.validate_organization_id`（:91） | `filter(organization_id=value, ...)` → `filter(id=value, ...)`（1 行） |
| `backend/accounts/tests/__init__.py`（新規） | — | 空ファイル（tests パッケージ化・problems/core と同慣例） |
| `backend/accounts/tests/test_I131_org_id_rename.py`（新規） | — | validate-slug（200/404/非アクティブ 404）＋登録 API（両ルート 201・無効 slug 400）の回帰テスト（TC-AUTO-01〜08） |

### 実装コード例

**修正アプローチ**: 改名漏れ 3 箇所の参照を現行フィールド名 `id` に揃えるだけの最小修正。外部契約（レスポンスキー `organization_id`・serializer 入力フィールド名 `organization_id`）は一切変えないため、FE・API 利用者への影響はない。

`backend/accounts/views.py:88`:
```python
            mutable_data['organization_id'] = organization.id
```
`backend/accounts/views.py:230`:
```python
                    'organization_id': organization.id
```
`backend/accounts/serializers.py:88-95`:
```python
    def validate_organization_id(self, value):
        """組織IDの検証"""
        if not Organization.objects.filter(
            id=value,
            is_active=True
        ).exists():
            raise serializers.ValidationError('無効な組織IDです')
        return value
```
（差分は 3 行のみ。import 追加不要）

## 5. 実装手順（TDD・単一垂直スライス）

本修正は「BE 属性参照 3 行 + 回帰テスト」の単一スライス（FE はコード変更なしのため縦貫通は BE→登録画面の目視・実登録で完結）。

- **ステップ0: イシュー本文の整合更新（承認後・実装前）**
  1. `docs/issues/open/I131.md` の実装対象・スコープ・AC・ユーザー影響をスコープ拡張後の確定値に更新（タイトルは「organization_id 改名漏れ修正（validate-slug 500・登録 API 400）」に拡張）。
  2. `gh issue edit 239 --body-file docs/issues/open/I131.md` で GitHub 同期（`gh` 不可なら警告のみで続行）。
- **ステップ1: 回帰テスト先行（RED 確認・ステップ0 完了が前提）**
  1. `backend/accounts/tests/`（`__init__.py`）と `test_I131_org_id_rename.py` に TC-AUTO-01/03/04/05/06/07 のテスト関数を追加（ファイルローカル autouse で `RATELIMIT_ENABLE=False`）。
  2. 現行コードに対し実行: TC-AUTO-01（500）・TC-AUTO-05/06/07（400）が **RED**、TC-AUTO-03/04（404 既存挙動）が GREEN であることを確認・記録（= TC-AUTO-02）→ auto_test「TDD RED 確認」参照。
- **ステップ2: 3 箇所修正（ステップ1 の RED 記録が前提）**
  1. 上記コード例どおり 3 行を修正 → 新規 TC 全 GREEN。
  2. 否定系 TC の false-green 注入検証を実施 → auto_test「false-green 自己検証」参照。
  3. 全体回帰（baseline 84 件 + 新規）→ TC-AUTO-08 参照。
- **ステップ3: dev 実環境・画面の復旧確認（ステップ2 完了が前提）**
  1. dev 実環境で validate-slug 200 / 無効 slug 404 を確認 → manual_test No.3（Claude・修正前実測 500 との比較）。
  2. 登録画面の組織名表示・実登録完了を確認 → manual_test No.4/5（Human）。

依存関係: ステップ1→2→3 は直列。サービス再起動: 不要（dev サーバーのホットリロードで反映）。

## 6. テスト計画

### 自動テスト（詳細: `docs/tests/open/I131_auto_test.md`）
- テストレベル: **API 結合テスト**（DRF `APIClient`・URL ルーティング〜ビュー〜serializer〜DB までの配線を検証。バグの本体が「ビュー/serializer とモデル定義の不整合」にあるため、モデルを実際に通す結合レベルでのみ捕捉できる）。
- 再発防止: 有効系（validate-slug 200・登録 201×両ルート）を固定（TDD で修正前 500/400 の FAIL を記録）。404/400 系は body の完全一致 assert で「別要因の 404/400」による false-green を排除。
- 認可テスト: 認可変更なし（両エンドポイントとも既存 `AllowAny` 維持）。未認証 `APIClient` で叩くこと自体が現行認可の回帰固定になる。
- テナント境界: 登録 TC で「ユーザーが指定組織に所属する」「他組織の科目 id はエラーになる（serializer 既存検証・TC-AUTO-07 の無効 slug 400 と合わせ既存挙動維持）」を assert。

### 手動テスト（詳細: `docs/tests/open/I131_manual_test.md`）
- Claude: 新規テスト・全体回帰の実行、dev 実環境 API の修正後 200/404 確認（修正前実測との比較）。
- Human: シークレットウィンドウで `/register/personal` の組織名表示確認＋実登録完了（具体アカウント値は manual_test に明記・新規作成）。

## 7. ロールバック
- 3 行を旧参照に戻し、`backend/accounts/tests/` を削除すれば従来動作（validate-slug 500・登録 400）へ完全に戻る。DB 変更なしのためマイグレーション不要。

## 8. Risk & 回避策
- **リスク1（見落とし）**: 改名漏れが 3 箇所以外にも残存している。→ 回避: `.organization_id` を backend 全体 grep し**全件分類済み**（調査結果の表・残りはすべて FK attname の正当利用）。全体回帰 84 件で他機能の無退行も固定。
- **リスク2（契約変更の混入）**: 修正時にレスポンスキーや serializer 入力フィールド名まで変えて FE を壊す。→ 回避: 変更は右辺の属性参照/フィルタキーのみ（計画のコード例で固定）。TC がレスポンス body の完全一致を assert。
- **リスク3（登録テストの flaky 化）**: django-ratelimit の redis カウンタが実行間共有で 5 分窓の反復実行が制限に達する。→ 回避: テストファイルの autouse fixture で `RATELIMIT_ENABLE=False`（公式スイッチ・リクエスト時評価を確認済み）。
- **リスク4（テスト DB 前提差）**: `--no-migrations` により personal 組織が存在せず、dev 前提の TC が誤動作。→ 回避: fixture で組織を自作。personal 既定ルート TC（TC-AUTO-06）は type='personal' の組織を fixture で作成して検証。
- **リスク5**: 登録画面が BE 修正だけでは完了しない（FE 側の未知の依存）。→ 回避: FE は既存コードのまま 201/レスポンス形式も不変。manual No.5 で実登録を検証し、NG なら中断→計画書更新→承認の正規手順で対応。
- **補足（スコープ外の既知事項）**: `except Exception` の丸め・`Organization.slug` の `unique=False`（同一 slug 複数時に `.first()` が任意の 1 件を返す）は既存挙動でありイシューのスコープ外（変更しない）。

## セキュリティ・ベストプラクティスチェック
- **認証・認可**: 権限クラス変更なし（両エンドポイントとも既存 `AllowAny` の公開設計を維持。未認証登録導線の復旧であり新規開放ではない）。最小権限に変化なし。
- **情報露出**: validate-slug の返却は組織 name と id のみ（キー `organization_id` は既存契約・FE 未使用）。組織 PK の未認証露出は本エンドポイントの元々の設計で、登録 API でも組織 id は入力契約として既に公開。新規露出なし。TC で body キー集合を完全一致固定。
- **入力バリデーション**: slug は URL converter `<slug:slug>` + ORM 完全一致（不変更）。登録は既存 serializer 検証（パスワード validators・user_id regex・科目所属チェック）を素通しで維持（`filter` のキー名修正のみ・検証意味は不変: PK 一致 + is_active）。
- **機密データ**: 登録データ（メール・パスワード）の取り扱いコードは不変更（改名 3 行のみ）。ログ出力も不変更。
- **OWASP**: A01/A03 とも新規リスクなし（SQLi: ORM のみ・XSS/CSRF: JSON API・変更なし）。
- **依存ライブラリ**: 追加なし → pip-audit/npm audit の新規対象なし。
- **bandit**: 変更 3 行に該当パターンなし（pre-commit で自動検証）。

## 高リスク判定
- **判定: No**。権限クラス・認可ロジックの変更なし／新規公開エンドポイントなし／個人情報の取り扱いコード不変更（属性名の改名追随 3 行のみ）／レスポンス・API 契約不変。I115 が Yes だったのは `IsAuthenticated`→`AllowAny` の権限クラス変更があったためで、本件に権限変更はない。
- **確定フロー**: `/plan-issue-review I131` → `/implement I131`（security-review 省略。plan-review で判定に異議があれば従う）。

## 各種チェック結果
- **P3（データ整合性/DB）影響なし**: DB スキーマ・マイグレーション変更なし。登録のトランザクション境界（`transaction.atomic`）は既存のまま。
- **P5（運用設計/外部API/非同期/バッチ）影響なし**: 外部連携・非同期処理の変更なし（認証メール送信は既存コード不変更）。
- **P6（性能・UX）影響なし**: FE コード変更なし（ローディング・エラー表示は Register.tsx 実装済み・不変更）。クエリは単純 SELECT のまま。
- **P8（コスト）影響なし**: 新規インフラ/外部サービスなし。
- **P9（プライバシー）影響なし**: 個人情報の新規取得・保存・露出なし（既存登録フローの復旧。取り扱いコード不変更）。

## 設計判断の明示
| 設計判断 | 出所 |
|---------|------|
| `views.py:230` を `organization.id` へ修正・レスポンスキー名 `organization_id` 維持 | イシュー明記 |
| validate-slug の回帰テスト追加（有効 200・無効 404） | イシュー明記 |
| **スコープ拡張: `views.py:88`・`serializers.py:91` も同時修正＋登録 API 回帰テスト追加** | **仮定で決めた（調査で発見・根治推奨。承認ポイント第1項）** |
| テスト配置 `backend/accounts/tests/test_I131_org_id_rename.py`（tests パッケージ新設） | 仮定で決めた（イシューは「配置は計画で確定」と委任。problems/core の既存慣例に準拠。ファイル名は拡張スコープを反映） |
| 非アクティブ組織 slug → 404 の TC 追加 | 仮定で決めた（既存挙動の回帰固定・低コスト） |
| 404/400 系はレスポンス body 完全一致で assert | 仮定で決めた（ルート不在等の「別要因 404」による false-green 排除） |
| 登録 TC で `RATELIMIT_ENABLE=False`（ファイルローカル autouse） | 仮定で決めた（flaky 回避。E2E CI と同じ公式スイッチ） |
| テスト fixture で組織を自作（personal 含む） | 調査結果由来（`--no-migrations` のため決定論） |

→ 「仮定で決めた」項目は次の承認ポイントで確認する。

## 9. 承認ポイント（チェックリスト）
- [ ] **スコープ拡張（最重要）**: 調査で発見した同一根本原因の残り 2 箇所（`views.py:88`・`serializers.py:91` = **新規登録 API が全件 400 で不能**・実測確認済み）を I131 に含めて 3 箇所まとめて修正する（推奨・計 3 行）— でよいか。承認時はイシュー本文も整合更新＋GitHub 同期（ステップ0）。（代替: 登録分を別イシュー「I139: 登録API（auth/register）が organization_id 改名漏れで全件400 — 新規登録不能の修正」に分割。この場合 I131 後も登録は壊れたまま）
- [ ] 修正方式: 属性参照/フィルタキーの改名追随 3 行のみ・レスポンスキー/API 契約は不変更 — でよいか
- [ ] テスト配置・命名: `backend/accounts/tests/test_I131_org_id_rename.py`（tests パッケージ新設・慣例準拠） — でよいか
- [ ] 追加 TC: 非アクティブ組織 404・レスポンス body 完全一致 assert・登録 TC の `RATELIMIT_ENABLE=False` — でよいか
- [ ] 高リスク判定 No（security-review 省略・plan-review 後に /implement へ） — でよいか
- [ ] 手動テスト: Human 実施は「`/register/personal` の組織名表示確認」＋「実登録完了（新規アカウント `i131_manual` を作成・manual_test に具体値明記）」の 2 件 — でよいか

## レビュー結果
- [20260719_2119 判定: ✅ 完了](../../reviews/I131_plan_review_20260719_2119.md)
