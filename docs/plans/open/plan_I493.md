# I493 計画書: API のスキーマから画面の型を作る（ダッシュボードの overview から）

## 基本情報
- **計画書ID**: plan_I493
- **関連イシュー**: #493
- **Draft PR**: #497
- **作成根拠資料**: docs/issues/open/I493.md（GitHub #493 の本文の写し）
- **実装後評価**: docs/reviews/open/I493_review.md
- **作成日**: 2026-11-13

## 1. 背景/目的
- **原因の概要**: 画面の型と API の応答が別々に手で書かれていて、ずれても機械で気づけない。I473 の「ダッシュボードの数字が 0 のまま」は、この形の不具合だった。
- **目的**: API の仕様書（OpenAPI のスキーマ）をシリアライザから作り、画面の TS の型をそのスキーマから作る。作り直し忘れは CI で止める。今回置き換えるのはダッシュボードの overview だけ。残りは #496 で置き換える（grill-me で確定）。

### 調査結果（2026-11-13・スパイク実施済み）
- **環境**: `docker compose ps` で backend・frontend・db・redis が起動中。ホストの Node は v24.14.1。frontend のコンテナは Node v18.20.8・TypeScript 4.9.5。CI の Node は 18。ホストに Django の入った Python は無いので、スキーマは backend のコンテナか CI で作る。
- **依存の監査（実走）**:
  - `drf-spectacular==0.30.0`（2026-07-06 公開・PyPI の JSON で確認）: 依存も含めて `pip-audit` で脆弱性なし（backend のコンテナで実行）。
  - `openapi-typescript@7.13.0`（2026-02-11 公開）＋ `typescript@5.9.3`: `npm audit` で 0 件。7 系は TypeScript 5 を前提にする（peerDependencies `typescript: ^5.x`）。
  - `openapi-typescript@6.7.6` は TypeScript の前提が無いが、`undici`→`@fastify/busboy` で high が 2 件あるので使わない。
  - `@redocly/openapi-core` は Node 18.17 以上が要る。CI の Node 18（18.20 系）で足りる。
- **スパイク 1（全部の API でスキーマを作る）**: 警告 61・エラー 136 が出た。シリアライザの無い APIView（`DashboardAnalyticsView`・`ChangePasswordView` など 12 種）は省かれ、ViewSet の多くは `get_queryset` が匿名ユーザーで例外になり、型が string に落ちる。→ 全 API を契約に入れると、中身の正しくない型ができる。
- **スパイク 2（契約に入れるパスを `PREPROCESSING_HOOKS` で一覧に絞る・`--validate --fail-on-warn`）**: `extend_schema(parameters=[OverviewQuerySerializer], responses=OverviewSerializer)` と、`OrgSubjectField` に `extend_schema_field(OpenApiTypes.INT)` を付けると、警告 0 で通った（終了コード 0）。出たスキーマでは、必須のキーが全部 `required` に入り、`accuracy_rate` は Today・Totals で `nullable: true`、WeakSubject で null 不可、`kind` は enum（`weak_subject`・`unstudied_subject`）、`subject_id` のクエリは integer・省略可。
  - 部品の名前は `Day`・`Today`・`Totals`・`KindEnum` のように一般的な名前になる。→ 後で別の API を契約に足したとき名前がぶつからないよう、`Dashboard` で始まる名前にする（変更点 B2）。
- **スパイク 5（計画レビューの Warning 1 を受けて・名前の付け替え）**: スパイク 2 に、7 つのシリアライザへの `extend_schema_serializer(component_name=...)`（`TotalsSerializer` を先に、継承した `TodaySerializer` を後に付ける。実装でクラスの定義に付けるのと同じ順）と、`ENUM_NAME_OVERRIDES`（`'DashboardRecommendationKindEnum': 'dashboard.serializers.RECOMMENDATION_KIND_CHOICES'`・値は `(KIND_WEAK, KIND_UNSTUDIED)`）を足して作った。`--validate --fail-on-warn` で終了コード 0。部品は `DashboardDay`・`DashboardOverview`・`DashboardRecommendation`・`DashboardRecommendationKindEnum`・`DashboardStreak`・`DashboardToday`・`DashboardTotals`・`DashboardWeakSubject` の 8 つで、`DashboardToday` と `DashboardTotals` は別々に出た。→ 変更点 B2 はこのとおり効く
- **スパイク 3（型の生成）**: スパイク 2 のスキーマから `openapi-typescript` 7.13.0 で `.d.ts` を作り、frontend のコンテナの TypeScript 4.9.5 で `tsc --noEmit --strict` が通った。作った型の中身は普通の `interface`/`type` だけ。
- **スパイク 4（`--check` の確かめ）**: 同じ型なら `--check` は終了コード 0。1 か所変えた写し（`has_data: boolean`→`string`）に `--check` をかけると「Generated types are not up-to-date!」で終了コード 1。
- **既存の型の使われ方**: `DashboardOverview` を使うのは `frontend/src/pages/Dashboard.tsx:45`・`frontend/src/pages/__tests__/Dashboard.test.tsx:11`・`frontend/src/services/dashboard.service.ts:3`。`AnswerCounts`・`DashboardDay`・`WeakSubject`・`DashboardRecommendation` は `frontend/src/services/types.ts` の中でしか使われていない（grep で確認）。
- **CI**: `.github/workflows/ci.yml` の backend-test が `requirements.txt`＋`requirements-dev.txt` を入れて pytest を流す。backend-lint が `pip-audit -r requirements.txt` を流す。Node のジョブはどれも `frontend/` が対象。
- **Docker**: backend の Dockerfile は `base` で `requirements.txt` を入れる（dev・production の両方に入る）。frontend の Dockerfile は `COPY . .` で `frontend/` の全部をイメージに入れ、`.dockerignore` は無い。
- **既存テストの基準**: pytest・Jest・E2E は develop の最新（PR #490 マージ後）の CI が全部緑。手元での流し直しはしない（CI が正）。

## 2. 受け入れ条件
- [ ] AC1: シリアライザから OpenAPI のスキーマ（`backend/openapi.yaml`）が作られ、overview の応答の各キー（`has_data`・`today`・`streak`・`totals`・`last_7_days`・`weak_subjects`・`recommendations` と入れ子のキー）が、必須・型・null を許すか（`accuracy_rate`）まで `OverviewSerializer` と一致する（→ TC-03）
- [ ] AC2: スキーマから TS の型（`frontend/src/types/api/schema.d.ts`）が作られ、`Dashboard.tsx`・`dashboard.service.ts` がその型を使っている（→ TC-10・TC-13）
- [ ] AC3: シリアライザを変えて作り直し忘れると CI が落ちる。失敗の注入で確かめる（→ TC-01・TC-02・TC-20・TC-21）
- [ ] AC4: 形の違う応答・キーの欠けた応答で、画面が 0 で埋めずにエラーの文を出す（`Dashboard.test.tsx` の TC-22）が引き続き通る（→ TC-11）
- [ ] AC5: 足した依存に high/critical の脆弱性が無い（`pip-audit`・`npm audit`）（→ TC-22・TC-23）
- [ ] AC6: 既存のテスト・E2E に退行が無い（→ CI・手動 No.1）

## 3. 影響範囲
| 区分 | 対象 | 内容 |
|---|---|---|
| Backend | `backend/requirements.txt`・`backend/core/settings.py`・`backend/core/openapi.py`（新設） | `drf-spectacular` を入れ、契約に入れるパスの一覧と設定を置く |
| Backend | `backend/dashboard/serializers.py`・`backend/dashboard/views.py`・`backend/problems/serializers.py` | スキーマ用の注釈（部品の名前・応答・クエリ・`OrgSubjectField` の型） |
| Backend | `backend/openapi.yaml`（新設・作ったもの）・`backend/core/tests/test_I493_openapi_contract.py`（新設） | 作ったスキーマと、そのずれ・中身のテスト |
| Frontend | `tools/api-types/`（新設・`package.json`・`package-lock.json`） | 型を作る道具（TypeScript 5）。画面の本体とは別の置き場 |
| Frontend | `frontend/src/types/api/schema.d.ts`（新設・作ったもの）・`frontend/src/types/api/index.ts`（新設） | 作った型と、画面が使う名前 |
| Frontend | `frontend/src/services/dashboard.service.ts`・`frontend/src/services/types.ts`・`frontend/src/pages/Dashboard.tsx`・`frontend/src/pages/__tests__/Dashboard.test.tsx` | 手書きの overview の型を消し、作った型に置き換える |
| Config/Infra | `.github/workflows/ci.yml` | 型のずれを確かめるジョブ `api-types` を足す |
| Config/Infra | `.github/dependabot.yml` | `tools/api-types` の npm を見張りに足す |
| Config/Infra | Docker | `backend/Dockerfile` は変えない（`base` が `requirements.txt` を入れるので dev・production に自動で入る）。`frontend/Dockerfile` は変えない（道具はリポジトリ直下の `tools/` に置くので、`frontend/` のイメージに入らない）。`docker-compose.yml` は変えない。実装後に backend・celery のイメージを作り直す（`docker compose up -d --build backend celery celery-beat`） |
| Docs | `docs/runbooks/common-commands.md`・`docs/runbooks/branch-protection-setup.md` | 型を作り直すコマンド・必須チェックの一覧に `API Types Up To Date` を足す |
| Frontend（条件つき） | `frontend/package.json` | ESLint が作った型で落ちたときだけ `eslintConfig.ignorePatterns` を足す（依存は変えない） |
| DB | なし | |

## 4. 変更点一覧（具体）

### 修正アプローチ
バックエンドでは、`drf-spectacular` が「契約に入れる」と一覧に書いたパスだけでスキーマを作る。警告が 1 つでもあれば失敗にする（`--fail-on-warn`）。こうすると、スキーマに入った API の型はいつも正確になる。作ったスキーマ（`backend/openapi.yaml`）はリポジトリに入れ、pytest で「コードから作り直したものと同じか」を確かめる。

フロントエンドでは、`tools/api-types` に置いた `openapi-typescript` でスキーマから型（`frontend/src/types/api/schema.d.ts`）を作り、リポジトリに入れる。CI では `--check` で「スキーマから作り直したものと同じか」を確かめる。

画面は、作った型に付けた短い名前（`frontend/src/types/api/index.ts`）を使う。実行時の形の確かめ（`isDashboardOverview`）は残し、作った型に合わせる。

### A. 契約に入れるパスと設定（backend）
- **方針**: 契約に入れるパスを 1 か所の一覧で持ち、その一覧だけでスキーマを作る。スキーマを見せる URL（Swagger UI など）は足さない（grill-me で確定）。
- `backend/requirements.txt`: `drf-spectacular==0.30.0` を足す（`djangorestframework` の次の行）。設定（`INSTALLED_APPS`・`DEFAULT_SCHEMA_CLASS`）が本番でも読まれるので、dev 用ではなく本体の依存に入れる。
- `backend/core/openapi.py`（新設）:
  ```python
  """API の契約（OpenAPI のスキーマ）に入れるパスの一覧（I493）

  ここに足したパスだけが backend/openapi.yaml と画面の型（frontend/src/types/api/schema.d.ts）に入る。
  足すときは、警告 0（--fail-on-warn）で作れるように、ビューとシリアライザに注釈を付ける。
  """
  CONTRACT_PATHS = frozenset({
      '/api/dashboard/overview/',
  })


  def only_contract_paths(endpoints, **kwargs):
      """drf-spectacular の PREPROCESSING_HOOKS。endpoints は (path, path_regex, method, callback) の並び"""
      return [endpoint for endpoint in endpoints if endpoint[0] in CONTRACT_PATHS]
  ```
- `backend/core/settings.py`:
  - `THIRD_PARTY_APPS` に `'drf_spectacular'` を足す。
  - `REST_FRAMEWORK` に `'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema'` を足す。
  - `SPECTACULAR_SETTINGS` を足す:
    ```python
    # API の契約（OpenAPI のスキーマ）の作り方（I493）。スキーマを見せる URL は作らない
    SPECTACULAR_SETTINGS = {
        'TITLE': 'study-app API',
        'VERSION': '1.0.0',
        'SERVE_INCLUDE_SCHEMA': False,
        'PREPROCESSING_HOOKS': ['core.openapi.only_contract_paths'],
        'ENUM_NAME_OVERRIDES': {
            'DashboardRecommendationKindEnum': 'dashboard.serializers.RECOMMENDATION_KIND_CHOICES',
        },
    }
    ```

### B. ダッシュボードの注釈（backend）
- **B1** `backend/dashboard/views.py` の `DashboardOverviewView.get` に `@extend_schema(parameters=[OverviewQuerySerializer], responses={200: OverviewSerializer})` を付ける。応答やエラーの中身は変えない。400 の応答の形は今回スキーマに入れない（画面がエラーの body を型で読んでいないため。#496 で他の API とまとめて決める）。
- **B2** `backend/dashboard/serializers.py`:
  - `RECOMMENDATION_KIND_CHOICES = (KIND_WEAK, KIND_UNSTUDIED)` を置き、`RecommendationSerializer.kind` の `choices` に使う（enum の名前の付け替え〔A の `ENUM_NAME_OVERRIDES`〕と、選択肢の正を 1 か所にする）。
  - 各シリアライザに `@extend_schema_serializer(component_name=...)` を付け、部品の名前を `DashboardOverview`・`DashboardToday`・`DashboardTotals`・`DashboardStreak`・`DashboardDay`・`DashboardWeakSubject`・`DashboardRecommendation` にする。`TodaySerializer` は `TotalsSerializer` を継承しているので、注釈を引き継いで同じ名前にならないよう、両方に個別に付ける（→ TC-03 で名前が別々かを確かめる）。
  - 19 行目のコメント（「画面の型（frontend/src/services/types.ts の DashboardOverview）と同じ形」）を、「この形から backend/openapi.yaml と画面の型（frontend/src/types/api/schema.d.ts）を作る（I493）」に直す。
- **B3** `backend/problems/serializers.py` の `OrgSubjectField` に `@extend_schema_field(OpenApiTypes.INT)` を付ける。科目の主キーは整数だが、クラスに queryset が無いので、drf-spectacular が型を決められず string にして警告を出すため。動き（受け付ける値）は変えない。

### C. 作ったスキーマとテスト（backend）
- `backend/openapi.yaml`（新設）: `docker compose exec -T backend python manage.py spectacular --file openapi.yaml --validate --fail-on-warn` で作ったもの（`./backend` は backend のコンテナの `/app` に共有されている）。手で直さない。
- `backend/core/tests/test_I493_openapi_contract.py`（新設）:
  - `generate_schema_text(tmp_path)`: `call_command('spectacular', '--file', <tmp>, '--validate', '--fail-on-warn')` で作った中身を返す。警告があれば `--fail-on-warn` で失敗する。
  - `assert_schema_file_matches(committed_path, generated_text)`: 2 つが違えば、作り直すコマンドを書いた文で `AssertionError` を出す。
  - TC-01・TC-02・TC-03・TC-04 を置く（→ 自動テスト文書）。

### D. 型を作る道具（tools/api-types・新設）
- **方針**: 画面は TypeScript 4.9.5（`react-scripts` 5 の制約）のままにし、道具だけを TypeScript 5 で動かす。`frontend/` の外に置くので、frontend のイメージ（`COPY . .`）に入らず、画面の `npm ci` にも混ざらない。
- `tools/api-types/package.json`:
  ```json
  {
    "name": "api-types",
    "private": true,
    "description": "backend/openapi.yaml から画面の型（frontend/src/types/api/schema.d.ts）を作る（I493）",
    "scripts": {
      "generate": "openapi-typescript ../../backend/openapi.yaml -o ../../frontend/src/types/api/schema.d.ts",
      "check": "openapi-typescript ../../backend/openapi.yaml -o ../../frontend/src/types/api/schema.d.ts --check"
    },
    "devDependencies": {
      "openapi-typescript": "7.13.0",
      "typescript": "5.9.3"
    }
  }
  ```
- `tools/api-types/package-lock.json`: `npm install --prefix tools/api-types --ignore-scripts` で作る。
- `node_modules` はルートの `.gitignore` の `node_modules/` で除外済み（変えない）。

### E. 作った型と画面の置き換え（frontend）
- `frontend/src/types/api/schema.d.ts`（新設）: `npm --prefix tools/api-types run generate` で作ったもの。手で直さない。
- `frontend/src/types/api/index.ts`（新設）:
  ```ts
  // API の型は backend/openapi.yaml から作った schema.d.ts を正にする（I493）。ここでは画面が使う短い名前を付けるだけ
  import type { components } from './schema';

  type Schemas = components['schemas'];

  export type DashboardOverview = Schemas['DashboardOverview'];
  export type DashboardRecommendationKind = Schemas['DashboardRecommendationKindEnum'];
  ```
- `frontend/src/services/types.ts`: 60〜97 行目（`AnswerCounts`・`DashboardDay`・`WeakSubject`・`DashboardRecommendation`・`DashboardOverview` とその前のコメント）を消す。他の型は触らない（#496）。
- `frontend/src/services/dashboard.service.ts`:
  - `DashboardOverview` を `../types/api` から読む。`AnalyticsData`・`AnalyticsFilters`・`UserSettings` は今のまま `./types` から読む。
  - `isDashboardOverview` は残す。型は実行時に消えるので、API の応答を受けるところで形を確かめるのは、型を作るようにした後も要る（TC-22 の 0 埋めの防止）。`last_7_days` が空でないことのような、型では書けない決まりもここで見る。
  - `kind` の確かめを、作った型に結びつける: `const RECOMMENDATION_KINDS: readonly DashboardRecommendationKind[] = ['weak_subject', 'unstudied_subject'];` を置き、`(RECOMMENDATION_KINDS as readonly unknown[]).includes(rec.kind)` で見る。API から選択肢が消えたら `tsc` が落ちる。
  - 22 行目のコメント（形の正）を「形の正は backend/openapi.yaml（OverviewSerializer から作る）」に直す。
- `frontend/src/pages/Dashboard.tsx:45`: `DashboardOverview` を `../types/api` から読み、`Subject` は `../services/types` から読む。他は変えない。
- `frontend/src/pages/__tests__/Dashboard.test.tsx:11`: `DashboardOverview` を `../../types/api` から読む。テストの中身は変えない。

### F. CI・Dependabot・手順書
- `.github/workflows/ci.yml` にジョブ `api-types` を足す（`frontend-test` の後、`harness-tests` の前）。action は他のジョブと同じ SHA で固定する。secrets は使わない（`permissions: contents: read` はファイル全体の設定のまま）。
  ```yaml
  # I493: 画面の型（frontend/src/types/api/schema.d.ts）が backend/openapi.yaml から作り直したものと同じかを見る。
  # backend/openapi.yaml がシリアライザと同じかは backend-test の pytest（core/tests/test_I493_openapi_contract.py）が見る
  api-types:
    name: API Types Up To Date
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4.4.0
      - uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4.4.0
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: tools/api-types/package-lock.json
      - name: Install dependencies
        # 依存の install スクリプトを動かさない（道具は install スクリプト無しで動く・計画時のスパイク 3 で確認）
        run: npm ci --ignore-scripts
        working-directory: tools/api-types
      - name: Generated types are up to date
        run: npm run check
        working-directory: tools/api-types
      - name: Failure injection (stale types must fail the check)
        # 古い型の写しに --check をかけて、落ちることを毎回確かめる（道具の版上げで --check が効かなくなったら気づくため）
        run: |
          cp ../../frontend/src/types/api/schema.d.ts "$RUNNER_TEMP/stale.d.ts"
          echo "export type Stale = 1;" >> "$RUNNER_TEMP/stale.d.ts"
          if ./node_modules/.bin/openapi-typescript ../../backend/openapi.yaml -o "$RUNNER_TEMP/stale.d.ts" --check; then
            echo "::error::古い型でも --check が通った（ずれを止められない）"
            exit 1
          fi
        working-directory: tools/api-types
      - name: npm audit
        run: npm audit --audit-level=high
        working-directory: tools/api-types
  ```
- `.github/dependabot.yml`: `/frontend` の npm の塊の後に、`directory: "/tools/api-types"` の npm の塊を足す（`schedule`・`labels`・`cooldown`・`groups` は `/frontend` と同じ）。
- `docs/runbooks/common-commands.md`: 「## モデル変更時の必須手順（migration drift 防止）」の後に「## API の形を変えたとき（型の作り直し・I493）」を足す。中身は次の 3 つ:
  - 作り直す 2 つのコマンド（`docker compose exec -T backend python manage.py spectacular --file openapi.yaml --validate --fail-on-warn`・`npm --prefix tools/api-types ci --ignore-scripts`〔初回だけ〕・`npm --prefix tools/api-types run generate`）
  - 契約に入れる API を足すときは `backend/core/openapi.py` の `CONTRACT_PATHS` に足すこと
  - 2 つの作ったファイルを手で直さないこと
- `docs/runbooks/branch-protection-setup.md`: §2 の必須チェックの一覧に `API Types Up To Date` を足し（6→7 件）、§3 ステップ 3 の一覧（今は 5 件で `Harness Tests` が抜けている）を §2 と同じ 7 件にそろえる。§2 の説明に「`API Types Up To Date`（I493）は、画面の型が API のスキーマと同じかを見る」を 1 文足す。
- （ESLint が作った型で落ちたときだけ）`frontend/package.json` の `eslintConfig` に `ignorePatterns` を足す（「8. Risk & 回避策」の ESLint の行）。

## 5. 実装手順（ステップ）
1. **バックエンドのスキーマ（未知のリスクを先に）**: A・B・C を入れ、`backend/openapi.yaml` を作る。部品の名前の付け替え（B2 の継承と `ENUM_NAME_OVERRIDES`）は、計画時のスパイク 5 で効くことを確かめた。→ TC-01〜TC-04 参照
2. **型を作る道具と作った型**: D と E の `schema.d.ts`・`index.ts` を作る（ステップ 1 が前提）。→ TC-20 参照
3. **画面の置き換え**: E の残り（`types.ts`・`dashboard.service.ts`・`Dashboard.tsx`・`Dashboard.test.tsx`）（ステップ 2 が前提）。→ TC-10〜TC-13 参照
4. **CI・Dependabot・手順書**: F（ステップ 2 が前提。ステップ 3 と並べてよい）。→ TC-21〜TC-23 参照
5. backend・celery のイメージを作り直す（`docker compose up -d --build backend celery celery-beat`。`requirements.txt` を変えたため。スパイクで backend のコンテナに一時的に入れた `drf-spectacular` も、作り直しで正しい入れ方に置き換わる）。

## 6. テスト計画
### 自動（詳細は docs/tests/open/I493_auto_test.md）
- pytest（ユニット・結合）: TC-01 スキーマのずれ／TC-02 失敗の注入／TC-03 overview の形／TC-04 契約のパス
- Jest・型検査・lint: TC-10 `npm run typecheck`／TC-11 `Dashboard.test.tsx`（TC-22 を含む）／TC-12 `npm run lint`／TC-13 手書きの overview の型が残っていない
- CI の `api-types` ジョブ: TC-20 型のずれ／TC-21 失敗の注入／TC-22 `npm audit`
- 既存: TC-23 `pip-audit`（backend-lint）。E2E（CI）
- 認可・テナント境界: 応答の中身もビューの権限（`permissions.IsAuthenticated`）も変えないので、新しい認可のテストは作らない。I473 の `test_I473_overview.py` の他組織・未ログインのテストが引き続き通ることで確かめる（CI）
### 手動（詳細は docs/tests/open/I493_manual_test.md）
- No.1 ダッシュボードが今までどおり数字を出す（Playwright MCP）
- No.2 手順書のコマンドで作り直すと差分が出ない
- No.3 スキーマを見せる URL が無い

## 7. ロールバック
- PR を revert する。DB の変更は無い。revert の後、backend・celery のイメージを作り直す（`docker compose up -d --build backend celery celery-beat`）。

## 8. Risk & 回避策
| リスク | 回避策 |
|---|---|
| 手元と CI で作ったスキーマの中身が違う（版・並び順） | Python 3.11・`drf-spectacular` の版を固定する。手元でも CI と同じ backend のコンテナの中で作る。ずれたら TC-01 が CI で落ちるので気づける |
| `component_name` が継承で引き継がれ、Today と Totals の名前がぶつかる | 両方に個別に付ける。ぶつかると drf-spectacular が警告を出し、`--fail-on-warn` で TC-01 が落ちる。TC-03 で名前が別々かも確かめる |
| `ENUM_NAME_OVERRIDES` が効かず `KindEnum` のままになる | 計画時のスパイク 5 で効くことを確かめた。TC-03 で名前を毎回確かめる |
| 作った `.d.ts` を ESLint・pre-commit（行末の空白・最後の改行）が直してしまい、`--check` とずれる | スパイク 3 の出力は最後が改行で、行末の空白も無い。ずれれば TC-12・TC-20 で分かる。ESLint（TC-12・pre-commit の eslint）が作った `schema.d.ts` で落ちたときは、作ったファイルを手で直さず、`frontend/package.json` の `eslintConfig` に `"ignorePatterns": ["src/types/api/schema.d.ts"]` を足す（作ったファイルは lint の対象にしないのが一般的なやり方。手で書く `index.ts` は対象のまま）。このときは計画変更記録に 1 行書く（方式・範囲・受け入れ条件は変えないので、計画レビューはやり直さない） |
| 新しいジョブ `api-types` が落ちても、必須チェックに入っていないとマージを止められない | `docs/runbooks/branch-protection-setup.md` の必須チェックの一覧（§2 と §3 のステップ 3）に `API Types Up To Date` を足す。登録は管理者の設定画面の操作で、bot には権限が無いので、close の段階でユーザーに登録をお願いする（`develop`・`main`） |
| 道具の版上げで `--check` が効かなくなる | TC-21 の失敗の注入を CI で毎回流す |
| 一覧に無い API を、作った型の対象だと思い込む | `CONTRACT_PATHS` の説明と手順書に書く。#496 で順に足す |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 今回置き換えるのは overview だけ。残りは #496（イシューに明記）
- スキーマを見せる URL（Swagger UI など）は出さない（イシューに明記）
- `drf-spectacular` 0.30.0・`openapi-typescript` 7.13.0。道具は画面の本体とは別の置き場で TypeScript 5 で動かし、画面の TypeScript は上げない（イシューに明記）
- 作ったスキーマ・型はリポジトリに入れ、CI で作り直したものと比べる（イシューに明記）

Claude が決めた（技術的な選択と理由）:
- 契約に入れるパスを `CONTRACT_PATHS` の一覧で絞り、`--fail-on-warn` にする（仮定で決めた）— 全 API を入れると警告 61・エラー 136 で、中身の正しくない型ができる（スパイク 1）。一覧で絞れば、入った API の型はいつも正確で、足すときも警告 0 が条件になる
- 道具の置き場はリポジトリ直下の `tools/api-types/`（仮定で決めた）— `frontend/` の中に置くと、`.dockerignore` が無いため道具の `node_modules` が画面のイメージ（`COPY . .`）に入りうる。画面の `npm ci` とも分けられる
- `drf-spectacular` は `requirements.txt` に入れる（仮定で決めた）— `INSTALLED_APPS`・`REST_FRAMEWORK` の設定は本番でも読まれ、dev だけに入れると本番で import に失敗する。URL を足さないので、本番で外から見える入口は増えない
- `isDashboardOverview`（実行時の形の確かめ）は残す（仮定で決めた）— 型は実行時に消える。API の応答を受けるところで形を確かめるのが BP で、TC-22 の 0 埋めの防止はこれに頼っている。実行時の確かめをスキーマから作る道具（zod・ajv など）を足すのは、依存が増えるので #496 で他の画面とまとめて考える
- スキーマのずれの確かめは pytest（backend-test）、型のずれの確かめは新しいジョブ `api-types` で行う（仮定で決めた）— スキーマを作るには Django の環境が要り、backend-test にもうそろっている。型を作るには Node と道具が要る。役目ごとに既存の環境を使う
- 失敗の注入は、テストと CI に毎回流す形で入れる（仮定で決めた）— 一度だけの実験だと、道具の版上げで確かめが効かなくなっても気づけない
- 部品の名前に `Dashboard` を付ける（仮定で決めた）— #496 で他の API を足したとき、`Day`・`KindEnum` などの一般的な名前はぶつかりやすい
- 400 の応答の形はスキーマに入れない（仮定で決めた）— 画面はエラーの body を型で読んでいない。全 API のエラーの形は #496 でまとめて決める
- 要件・基本設計・UI/UX の価値判断に当たる仮定: なし（画面の見た目・文言・操作の流れは変えない）

要件適合性・業務ロジック:
- 受け入れ条件の範囲を超えた仕様の追加・変更は無い。応答の中身・権限（`permissions.IsAuthenticated`）・組織の範囲（`OrgSubjectField` の `available_subjects`）は変えない。B3 は型の注釈だけで、受け付ける値は変えない

セキュリティ・BP:
- 入力の確かめ・認証・認可・機密データの扱いは変えない
- スキーマを見せる URL を足さない（攻撃面を増やさない・grill-me で確定）。`backend/openapi.yaml` はリポジトリ（公開）に入るが、中身は overview の形と JWT を使うことだけで、秘密は無い
- 依存の脆弱性: 調査結果のとおり実走して 0 件。CI でも `pip-audit -r requirements.txt`（既存）と、`tools/api-types` の `npm audit --audit-level=high`（新設）で毎回見る
- スキャンの基準: bandit は MEDIUM 以上を直す（LOW は `# nosec`）。npm audit は high/critical を直す
- CI の新しいジョブは secrets を使わず、`GITHUB_TOKEN` は読み取りだけ（ファイル全体の `permissions: contents: read`）。action は SHA で固定する

データ整合性・運用・コスト:
- P3/P5/P8 影響なし（DB の変更・外部 API・非同期処理は無い）。依存の追加の波及は「3. 影響範囲」の Docker の行に書いた
- 保守: API の形を変える人は、2 つのコマンドで作り直す手間が増える。忘れても CI が止め、直し方はテストの失敗の文に出る

性能・UX:
- P6 影響なし（画面の表示・読み込み中・空・エラーの見せ方は変えない。型の読み込み先が変わるだけ）

プライバシー:
- P9 影響なし（個人情報・テナントのデータの扱いを変えない）

台帳の残り:
- 一覧 I213.md F6（`.github/dependabot.yml` の塊の写し）: 残す — 今回は塊を 1 つ足すだけで、YAML アンカーを Dependabot が読めるかは未確認のまま（I213 の判断を変える材料が無い）
- 一覧 I224.md F9・I223.md B1〜B4（`FILE=-`・ハーネス）: 残す — 本イシュー（アプリの型）と関係が無い

Danger Ops（有無/手順/ロールバック）:
- 無（データの削除・破壊的なマイグレーション・強制 push は無い）。`requirements.txt`・`package*.json` の変更は `.claude/settings.json` の ask で承認が出る

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 2 | 読んで可 | シリアライザを変えてスキーマを作り直し忘れると、CI（backend-test）が落ちる。TC-01 がコードから作ったものと `backend/openapi.yaml` を比べ、TC-02 が古い写しで `AssertionError` になることを確かめている |
| V2 | 2 | 読んで可 | スキーマを作り直して型を作り直し忘れると、CI（api-types）が落ちる。TC-20 が `--check` を流し、TC-21 が古い型の写しで `--check` が非ゼロになることを毎回確かめている（ジョブが PR で動く・`if:` やパスの絞りで飛ばされない） |
| V3 | 3 | 読んで可 | 契約に入った API の型が正確（警告で string に落ちた型が入らない）。TC-01 が `--fail-on-warn` で作り、TC-03 が overview の必須・型・null の可否を確かめている。TC-04 が契約のパスが一覧どおりかを確かめている |
| V4 | 1 | 読んで可 | 新しいジョブが secrets を使わず、action が SHA で固定され、`GITHUB_TOKEN` が読み取りだけ。スキーマを見せる URL が増えていない（手動 No.3） |
| V5 | 3 | 読んで可 | 実行時の形の確かめ（`isDashboardOverview`）が残り、形の違う応答で 0 埋めしない（TC-11 の中の Dashboard.test.tsx TC-22） |
| V6 | 1 | 読んで可 | `api-types` ジョブが依存の install スクリプトを動かさず（`npm ci --ignore-scripts`）、失敗の注入で道具をネットから取り直さない（`./node_modules/.bin/openapi-typescript`・`npx` を使わない）。`run:` に PR から来る値（`${{ github.event.* }}` など）を埋め込まない |

## 計画変更記録
- 計画レビュー（20261113_1218）の Warning 3 件・Info 1 件に対応した: ① スパイク 5 で名前の付け替えを先に確かめた ② 手動 No.2 を `git diff --exit-code`（コミット済みの状態）に変えた ③ ESLint が作った型で落ちたときの方針を決めた ④ 新しいジョブを必須チェックの一覧に足し、登録を close でユーザーにお願いする。方式・範囲・受け入れ条件は変えていない（④ は手順書の一覧を足すだけ）→ 計画レビューのやり直し: 不要
- セキュリティ設計レビュー（2026-11-13）の Medium 2 件に対応した: `api-types` ジョブと手順書・lock の作成で `--ignore-scripts` を付け、失敗の注入の `npx` を `./node_modules/.bin/openapi-typescript` に変えた。必ず確かめる項目に V6 を足した。方式・範囲・受け入れ条件は変えていない → 計画レビューのやり直し: 不要

## レビュー結果
- [20261113_1218 判定: ✅ 完了](../../reviews/I493_plan_review_20261113_1218.md)

## セキュリティレビュー結果

**実施日**: 2026-11-13

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Medium | 依存ライブラリ | `api-types` ジョブの `npm ci` が、道具の依存の install スクリプト（postinstall など）を PR の CI の中で動かす。依存が乗っ取られたとき、そこでコードが動く | `npm ci --ignore-scripts` にする（手順書・lock の作成も同じ）。道具は install スクリプト無しで動く（スパイク 3 は `--ignore-scripts` で入れて動いた）。secrets は渡さず、`GITHUB_TOKEN` は読み取りだけ（既存の `permissions: contents: read`） |
| Medium | 依存ライブラリ | 失敗の注入のステップで `npx openapi-typescript` を使うと、手元に無いときにネットから lock の外の版を取って動かしうる | `./node_modules/.bin/openapi-typescript` を直接呼ぶ（lock で固定した版だけを使う） |
| Low | セキュリティ設定ミス | `drf_spectacular` を `INSTALLED_APPS` に入れると、スキーマを見せる URL を誰かが足しやすくなる | 今回は URL を足さない（grill-me で確定・手動 No.3 で 404 を確認）。足すときは別イシューで認証と本番の扱いを決める |
| Low | 機密情報 | `backend/openapi.yaml` を公開リポジトリに入れる | 中身は overview の形と、JWT の bearer を使うことだけで、秘密・個人情報は無い。契約に入れるパスは `CONTRACT_PATHS` の一覧に足したものだけ |
| なし | 認証・認可 | — | `DashboardOverviewView` の `permissions.IsAuthenticated` と応答の中身は変えない |
| なし | マルチテナント | — | `OrgSubjectField` は型の注釈（`extend_schema_field(OpenApiTypes.INT)`）を足すだけで、`get_queryset`（`available_subjects`）は変えない。他組織の科目は今までどおり 400 |
| なし | 入力検証 | — | `OverviewQuerySerializer` の検証は変えない |
| なし | OWASP Top 10（XSS・SQLi・CSRF・IDOR） | — | 画面の表示・API の処理・SQL は変えない |
| なし | ファイル操作 | — | アップロード・ダウンロードは無い。スキーマ・型のファイルは開発者のコマンドと CI だけが作る |
| なし | 外部通信 | — | 実行中のアプリから外への通信は増えない。CI の `npm ci` は lock で固定した版をレジストリから取るだけ |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | `GET /api/schema/`・`/api/schema/swagger-ui/` | 未認証 | API の一覧と形を取りにいく | スキーマを見せる URL が無い（404） | No（URL を足すのは意図的な変更でしか起きないので、テストにしない・plan-writing-rules「写しのテストを作らない」） | Yes: 手動 No.3 で 404 | 無し | Low |
| 2 | `GET /api/dashboard/overview/?subject_id=<他組織の科目>` | 一般 | 型の注釈を足した `OrgSubjectField` で他組織の科目を通そうとする | 他組織・全体共有・存在しない科目は 400 で、数字を返さない | Yes: 既存の `test_I473_overview.py`（変更なしで通る・CI） | No | 無し（検証の処理を変えない） | Low |
| 3 | PR の CI（`api-types` ジョブ） | 外部の PR 作成者 | `tools/api-types/package*.json` の依存を書き換え、install スクリプトや道具で CI の中のコードを動かす | install スクリプトを動かさない・secrets が無い・トークンは読み取りだけ | No（V6 として敵対的レビューが読んで確かめる） | No | 道具そのもの（`openapi-typescript`）を書き換えれば `npm run check` で動く。secrets も書き込みの権限も無いので、被害は CI の結果の偽りだけ。必須チェックとコードオーナーの承認で止まる | Low |
| 4 | 開発者が API の形を変える | 開発者 | スキーマ・型を作り直さずにマージしようとする | CI が落ちる | Yes: TC-01・TC-02（pytest）・TC-20・TC-21（`api-types`） | No | `API Types Up To Date` を必須チェックに入れるまでは、落ちてもマージできる（close でユーザーに登録をお願いする） | Low |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 0件 | 0件 |
| Medium  | 2件（計画に反映済み） | 0件 |
| Low     | 2件 | 4件 |

### 残余リスク処遇
（retro 段階で決定する）
