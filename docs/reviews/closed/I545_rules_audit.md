# I545 規約の点検の結果（2026-11-17）

対象: `rules/ultimate_django_coding_standards.md`・`rules/react-coding-standards-integrated.md`・`docs/runbooks/ux-rules.md`・`docs/runbooks/backend-check.md`（変更前は `origin/develop` の版）。

物差し: あるべき姿（最新化・漏れ・最適化）。前提の版は LTS 優先（イシューの設計確認メモ）。結果の意味: そのまま＝中身を変えずに残す／直す＝中身を直して残す／消す＝残さない（理由つき）／足す＝新しく書いた。

## 1. 前提の版（出典と照らした日: 2026-11-17）

| 道具 | 前提の版 | 区分 | サポートの終わり | 出典 |
|---|---|---|---|---|
| Django | 5.2（最新 5.2.19） | LTS | 2028-04 | https://www.djangoproject.com/download/ |
| Python | 3.14 | 最新の安定版で Django 5.2 が対応する最新（3.15 は 2026-10 に出たが 5.2 は未対応） | 2030-10 | https://devguide.python.org/versions/ ・ https://docs.djangoproject.com/en/5.2/faq/install/ |
| PostgreSQL | 18（18.7） | 最新の安定版（Django 5.2 は 14 以上） | 2030-11-14 | https://www.postgresql.org/support/versioning/ ・ https://docs.djangoproject.com/en/5.2/ref/databases/ |
| psycopg | 3.3（3.3.9） | 最新の安定版・Django が推奨 | 公開の予定なし | https://pypi.org/pypi/psycopg/json ・ https://docs.djangoproject.com/en/5.2/ref/databases/ |
| DRF | 3.18（3.18.3） | 最新の安定版（Django 5.2・6.0・6.1） | 公開の予定なし | https://pypi.org/pypi/djangorestframework/json |
| Celery | 5.7（5.7.0） | 最新の安定版（Python 3.10〜3.14） | 公開の予定なし | https://pypi.org/pypi/celery/json |
| Redis | 8.10（8.10.3） | 最新の安定版 | 公開の予定なし | https://github.com/redis/redis/releases |
| Node.js | 26（26.13.1） | 最新の Active LTS | 2029-04-30 | https://nodejs.org/en/about/previous-releases ・ https://github.com/nodejs/release#release-schedule |
| React | 19.3（19.3.1） | 最新の安定版 | 公開の予定なし | https://registry.npmjs.org/react/latest |
| TypeScript | 7.0（7.0.2）＋6.x | 最新の安定版。7.0 は API が無く、API を使う道具は 6.0 を並べる（公式の勧め） | 公開の予定なし | https://registry.npmjs.org/typescript/latest ・ https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/ |
| Vite | 8.3（8.3.8） | 最新の安定版（Node.js ^20.19 か 22.12 以上） | 公開の予定なし | https://registry.npmjs.org/vite/latest |
| Vitest | 5.1（5.1.0） | 最新の安定版（Vite 6.4 以上・Node.js 22.12 以上） | 公開の予定なし | https://registry.npmjs.org/vitest/latest ・ https://vitest.dev/guide/ |
| MSW | 3.0（3.0.6） | 最新の安定版（Node.js 22 以上） | 公開の予定なし | https://registry.npmjs.org/msw/latest ・ https://mswjs.io/docs/migrations/2.x-to-3.x |
| TanStack Query | 5.107（5.107.1） | 最新の安定版 | 公開の予定なし | https://registry.npmjs.org/@tanstack/react-query/latest |
| MUI | 9.5（9.5.0） | 最新の安定版 | 公開の予定なし | https://registry.npmjs.org/@mui/material/latest |
| React Router | 8.5（8.5.1・`react-router`） | 最新の安定版 | 公開の予定なし | https://reactrouter.com/home ・ https://reactrouter.com/start/declarative/installation |
| React Hook Form | 7.92（7.92.0） | 最新の安定版 | 公開の予定なし | https://registry.npmjs.org/react-hook-form/latest |
| Zod | 4.6（4.6.7） | 最新の安定版 | 公開の予定なし | https://registry.npmjs.org/zod/latest |
| @hookform/resolvers | 7.0（7.0.6） | 最新の安定版 | 公開の予定なし | https://registry.npmjs.org/@hookform/resolvers/latest |

## 2. 道具の確定の根拠（計画書 4.2）

| 決めたこと | 根拠（出典） |
|---|---|
| ビルドは Vite・CRA を使わない | React の公式は、枠組みを使わずに作るときのビルドの道具として Vite・Parcel・Rsbuild を挙げ、CRA を挙げていない（https://react.dev/learn/creating-a-react-app ） |
| テストは Vitest | Vite と設定を共有する。Vitest は Vite 6.4 以上が前提（https://vitest.dev/guide/ ） |
| API の差し替えは MSW 3 | 通信の層で差し替える。3.x の import の形（`msw/http`）・`onUnhandledFrame`（https://mswjs.io/docs/migrations/2.x-to-3.x ） |
| サーバーの状態は TanStack Query・`queryOptions` | 公式の `queryOptions` の案内（https://tanstack.com/query/latest/docs/framework/react/guides/query-options ） |
| `forwardRef` を新しく使わない | React 19 で `ref` が props になり、`forwardRef` は将来廃止（https://react.dev/blog/2024/12/05/react-19 ） |
| TypeScript 7 は `tsc`、道具は 6 | 7.0 は API を持たない（公式の発表） |
| psycopg 3 | Django の文書が psycopg 3 を推奨し、psycopg2 は将来の非推奨を予告（https://docs.djangoproject.com/en/5.2/ref/databases/ ） |
| `CheckConstraint(condition=...)` | `check` は 5.1 で非推奨（https://docs.djangoproject.com/en/5.2/ref/models/constraints/ ） |
| `SECURE_BROWSER_XSS_FILTER` を書かない・CSP | 4.0 で設定が削除された（https://docs.djangoproject.com/en/5.2/releases/4.0/ ） |
| トークンを localStorage に置かない | OWASP「Do not store session identifiers in local storage」（https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html ） |
| `get_permissions` と `@action` の注意 | DRF の `@action` は viewset の `permission_classes` を上書きでき、`get_permissions` の例は `self.action` で分ける（https://www.django-rest-framework.org/api-guide/viewsets/ ）。`get_permissions` が `@action` の指定を読まないことは DRF のコード（`get_permissions` は `self.permission_classes` を読む）による |
| 「今日」は `timezone.localdate()` | 日時から日付へは先に今のタイムゾーンへ直す（https://docs.djangoproject.com/en/5.2/topics/i18n/timezones/ ） |
| アクセシビリティの目標 WCAG 2.2 AA | W3C 勧告・2024-12-12（https://www.w3.org/TR/WCAG22/ ） |
| MUI・axios・同期のビューを使い続ける | 入れ替える利点が無い（MUI はアクセシブルな部品があり全画面で使用・axios はインスタンス 1 つで割り込みを集約・同期の WSGI で時間のかかる処理は Celery） |

## 3. 節ごとの点検

### 3.1 `rules/ultimate_django_coding_standards.md`（元 1,710 行 → 新 §0〜§16）

| 元の見出し（行） | 結果 | 新しい置き場所・理由 | 根拠 |
|---|---|---|---|
| # Ultimate Django/Python バックエンドコーディング規約 v2.0（1） | 直す | 題を「Django/Python バックエンド コーディング規約」にし、冒頭に対象・物差し・使い方を書いた。「バイブコーディング最適化版」などの宣伝の文は消した | — |
| ## 自動強制範囲（linter が担当）（7） | 直す | §15 に移した。中身と設定の照合は #520 | — |
| ## 手動レビュー対象（linter が検出できない項目）（16） | 直す | §15 に移し、規約の節の番号で書いた | — |
| ## 📋 目次（28） | 消す | 見出しで足りる（短くなったため） | — |
| ## 1. 対象と前提（47） | 直す | §0 前提の版・§1 使う道具 | 1 の表 |
| ### 技術スタック（最新版）（49） | 直す | §0（版を出典つきで確定）・§1（uv/Poetry の列挙・mypy strict を消し、実際の道具に） | 1 の表 |
| ### 基本原則（62） | 直す | 早期リターン・単一責任を §3 に残した。12-factor は §2 の設定の決まりに。Clean Architecture・DRY・KISS・YAGNI の言葉だけの列挙は消した（一般論） | — |
| ## 2. プロジェクト構成（72） | 直す | §2 を実際の構成（`core`・`accounts` など）と置き場所の表にした | リポジトリの実際の構成 |
| ### 理想的なディレクトリ構造（74） | 消す | 実際の構成（`src/apps/`・`settings/` 分割ではない）と違う架空の構成。§2 の表に置き換えた | — |
| ## 3. コード品質と命名規則（127） | 直す | §3 | https://peps.python.org/pep-0008/ |
| ### 命名規則（129）（コードの中のコメント 131・135・139・143・146 を含む） | 直す | §3 の 1 行に（PEP 8 への参照） | PEP 8 |
| ### 静的解析設定（pyproject.toml）（153） | 消す | 実際の `backend/pyproject.toml`（line-length 120・E/F/W）と違う写し。設定は実ファイルが正。mypy の導入は #559 | — |
| ## 4. モデル設計（176） | 直す | §4 | constraints の文書 |
| ### ベストプラクティスモデル例（178） | 直す | 長い例を消し、決まり（TextChoices・DecimalField・on_delete・制約・索引・save に業務を書かない）の言い切りにした。`CheckConstraint(check=)` を `condition=` に直した（5.1 で非推奨） | https://docs.djangoproject.com/en/5.2/ref/models/constraints/ |
| ### カスタムマネージャー（286） | 直す | このアプリの形（`OrgScopedQuerySet`）として §5 に置き換えた | `problems/querysets.py` |
| ### マイグレーション（310）（コードの中のコメント 338・345 を含む） | そのまま（I050 の決まり）・足す | §4 に例ごと残した（このアプリの事故から来た決まり）。マージ後に書き換えない・データのマイグレーションを分けて戻す処理を書く、を足した | https://docs.djangoproject.com/en/5.2/topics/migrations/ |
| ## 5. API設計（DRF）（362） | 直す | §6 | DRF の文書 |
| ### ViewSetベストプラクティス（364） | 直す | 長い例を消し、薄いビュー・既定 `IsAuthenticated`・権限・ページ分けの決まりにした。`get_permissions` と `@action` の注意を足した（一覧 I209 F8）。クエリの値の検証は、一覧の絞り込みは django-filter の FilterSet、それ以外はクエリ用のシリアライザーと使い分けを決めた（fix-loop） | DRF viewsets・permissions |
| ### 高度なシリアライザー（484） | 直す | 入力の検証・action ごとの出力（見せてはいけない項目を出さない）の決まりにした。`create` の中で `transaction` と通知を行う例は §7（サービスに置く）と矛盾するので消した | — |
| ## 6. サービス/セレクタパターン（564） | そのまま（考え方）・直す | §7 | — |
| ### セレクタ（読み取り専用）（566）（コメント 568） | 直す | §7 の 1 行と §2 の置き場所に | `dashboard/selectors.py` |
| ### サービス（書き込み・業務ロジック）（624）（コメント 626） | 直す | §7。例の `except Exception` → `ValidationError(f"...{e}")`（内部の情報が漏れる）を悪い例にし、良い例を書いた。f-string のログを `%s` に（§11） | https://docs.python.org/3/howto/logging.html#optimization |
| ## 7. クエリ最適化（765） | 直す | §8 | https://docs.djangoproject.com/en/5.2/topics/db/optimization/ |
| ### N+1問題の回避（767）（コメント 769・775・783） | 直す | §8 の言い切りと、N+1 のテスト（`django_assert_num_queries`）を足した | pytest-django |
| ### 高度なクエリ最適化（789） | 消す | Subquery・Exists の一般的な使い方の解説。公式の最適化の文書への参照に置き換えた | 同上 |
| ## 8. 認証・認可・セキュリティ（839） | 直す | §10 | デプロイのチェックリスト |
| ### カスタム認証（841） | 消す | 実際に無い `AuthService`・`django_otp` の例。認証は simplejwt（§1）と §10 のトークンの決まりに置き換えた | — |
| ### カスタムパーミッション（877） | 直す | §10（権限クラスで止める・`permissions.py` に置く） | DRF permissions |
| ### セキュリティ設定（905）（コメント 907・911・917・925・930・936・949・961） | 直す | §10。設定の写しを消し、決まり（秘密は環境変数・`check --deploy`・廃止された設定を書かない）にした。`SECURE_BROWSER_XSS_FILTER`（4.0 で削除）を推奨から外した。Argon2（依存が無い）・`CSRF_COOKIE_HTTPONLY` の写しを消した | Django 4.0 のリリースノート・デプロイのチェックリスト |
| ## 9. テスト戦略（976） | 直す | §13 | pytest-django |
| ### pytest設定（978）（コメント 980） | 消す | 実際の `backend/pytest.ini` と違う写し（`--cov-fail-under=85`・`src/apps`）。設定は実ファイルが正 | — |
| ### 完全なテスト例（1003） | 直す | 長い例を消し、必ず書くテスト（認証なし・他の組織・入力の誤り・正常）の決まりにした。中身が `pass` のテストの例を消した | — |
| ### ファクトリーパターン（1125）（コメント 1127） | 消す | factory_boy・Faker は入っていない。テストのデータの作り方は既存のテストに合わせる | `backend/requirements-dev.txt` |
| ## 10. 非同期処理（1163） | 直す | §12 Celery | Celery の文書 |
| ### Celeryタスク（1165）（コメント 1167） | 直す | §12。例の `autoretry_for=(Exception,)`＋手での `retry`＋`except: pass`（§14 の悪い例そのもの）を消し、決まり（ID を渡す・冪等・一時的な例外だけ再試行・時間の上限・組織で絞る）にした | https://docs.celeryq.dev/en/stable/userguide/tasks.html |
| ### Django非同期ビュー（1256）（コメント 1258） | 消す | このアプリは同期のビューだけ（§1）。「Django 4.1+」の古い例 | — |
| ## 11. ロギング・監視（1298） | 直す | §11 | logging HOWTO |
| ### 構造化ログ設定（1300）（コメント 1302） | 消す | structlog は入っていない。設定は `core/enhanced_logging.py` が正 | — |
| ### ロギング実装例（1371） | 直す | §11 の決まり（`getLogger(__name__)`・`%s`・個人情報を出さない・`logger.exception`） | #437・#484 |
| ## 12. CI/CD・運用（1418） | 消す | コードの書き方でない（CI は `.github/workflows/` が正・進め方は I546） | — |
| ### Makefile（1420） | 消す | Makefile は無い | — |
| ### GitHub Actions CI/CD（1476）（コメント 1478） | 消す | 実際の CI と違う写し | — |
| ## 13. Cursor/Claude Code運用規約（1571） | 消す | 進め方の決まり（`CLAUDE.md`・`docs/runbooks/`・I546 の範囲）。中身の一部（秘密を書かない・print を使わない・ビューに業務を書かない・生 SQL）は §3・§6・§10・§11・§14 に決まりとして残した | — |
| ### ガードレール設定（1573）（コメント 1575） | 消す | 同上 | — |
| ### プロンプトテンプレート（1607）（1609・1614・1617・1624 の見出しはテンプレートの中） | 消す | 同上（環境の版も古い） | — |
| ## 14. ベストプラクティス集（1633） | 直す | §14 よくある間違い | — |
| ### ✅ 必ず守るべき原則（1635） | 直す | 早期リターン・単一責任（§3）・冪等・トランザクション境界（§7）・タイムアウト（§14）に振り分けた。「依存性注入」「防御的プログラミング」の言葉だけの列挙は消した | — |
| ### ⚠️ アンチパターン（1646）（コメント 1649・1664） | 直す | §14 に残し、良い例の f-string のログを直した | — |
| ### 📊 パフォーマンスチェックリスト（1677） | 直す | §8 に統合（ページ分けは §6） | — |
| ### 🔒 セキュリティチェックリスト（1687） | 直す | §10・§11 に統合 | — |
| ## まとめ（1700） | 消す | 宣伝の文 | — |

### 3.2 `rules/react-coding-standards-integrated.md`（元 2,150 行 → 新 §0〜§16）

| 元の見出し（行） | 結果 | 新しい置き場所・理由 | 根拠 |
|---|---|---|---|
| # React フロントエンド コーディング規約 統合版 v2.0（1） | 直す | 題と冒頭を書き直した（ChatGPT 版・Claude 版の統合の文は消した） | — |
| ## 自動強制範囲（linter が担当）（6） | 直す | §15。「eslint-plugin-jsx-a11y」と書いていたが今の設定に無い点の照合は #520 | — |
| ## 手動レビュー対象（linter が検出できない項目）（15） | 直す | §15 | — |
| ## 目次（27） | 消す | 見出しで足りる | — |
| ## 1. 対象と前提（51） | 直す | §0・§1 | 1・2 の表 |
| ### 技術スタック（53） | 直す | 選択肢の列挙（Vite または Next.js・Context/Zustand/Redux・Tailwind/CSS Modules・Zod/Yup・Vitest/Jest）を 1 つずつに決めた（§1） | 2 の表 |
| ### 基本原則（63） | 直す | 型安全（§3）・責務分離（§4）に振り分け、言葉だけの列挙を消した | — |
| ## 2. プロジェクト構成（71） | 直す | §2 を実際の構成の表にした | リポジトリの実際の構成 |
| ### ディレクトリ構造（推奨）（73） | 消す | 実際の構成（`features/` は無い・`pages/`・`services/` が中心）と違う | — |
| ### ファイル命名規則（102） | 直す | §2 の表の「名前」の列（実際の名付け: `xxx.service.ts`・`camelCase.ts`） | — |
| ### バレルエクスポート（110） | 消す | `features/` 前提の決まりで、今の構成に当てはまらない | — |
| ## 3. TypeScript/型定義（116） | 直す | §3 | TS の文書 |
| ### 3.1 型定義の一元管理（最重要）（118） | 直す | §2 の「同じ型を 2 か所に書かない」と §3 の「API の型は `types/api`（OpenAPI から作る）」にした | I493 |
| ### 3.2 型定義の配置ルール（147） | 直す | §2 の表（1 つの部品だけが使う型はその部品のファイル・2 つ以上が使う型は `src/types/`。fix-loop で基準を決めた） | — |
| ### 3.3 ジェネリック型の活用（171） | 消す | 実際の API の形（DRF のページ分け）と違う架空の型の例。API の型は OpenAPI から作る | — |
| ### 3.4 型安全性のベストプラクティス（198） | 直す | §3 の `unknown`・判別できる共用体の決まり | — |
| ## 4. 命名規則（232） | 直す | §2 の名前の列・§3（一般の命名は TS の慣習で足りる） | — |
| ### 4.1 基本ルール（234） | 直す | §2 | — |
| ### 4.2 意味のある命名（246） | 消す | 一般論 | — |
| ### 4.3 イベントハンドラー命名（260） | 消す | 一般論（React の文書の慣習） | — |
| ### 4.4 真偽値の命名（276） | 消す | 一般論 | — |
| ## 5. コンポーネント設計（288） | 直す | §4 | React の文書 |
| ### 5.1 基本原則（290） | 直す | §4（`React.FC` を使わない〔#510〕・`ref` を props で受ける〔React 19〕）。Tailwind の `cn()` の例を消した | React 19 の発表 |
| ### 5.2 コンポーネントの責務分離（331） | 直す | §4（200 行で分ける）・§5（取得はフック・`useEffect` で取得しない）。`useEffect` で取得する例は TanStack Query の方針と矛盾するので消した | https://react.dev/learn/you-might-not-need-an-effect |
| ### 5.3 コンポーネントサイズ制限（388） | そのまま | §4 の「200 行」 | — |
| ### 5.4 Props設計のベストプラクティス（394） | 直す | §3・§4（`any`・`Function` を使わない）に統合 | — |
| ## 6. 状態管理（426） | 直す | §5 | — |
| ### 6.1 状態の適切な配置（428） | 直す | §5（Context は認証・通知・テーマだけ・Zustand を使わない） | — |
| ### 6.2 カスタムフックの設計（458） | 消す | `fetch` で取得する自作の `useApi` は TanStack Query の方針と矛盾 | — |
| ### 6.3 状態管理の選定基準（508） | 直す | §1 の表と §5（useQuery/SWR・Zustand/Redux の列挙を 1 つに） | — |
| ## 7. スタイリング（520） | 直す | §9（MUI） | MUI の文書 |
| ### 7.1 Tailwind CSS（推奨）（522） | 消す | このアプリは MUI（§1） | — |
| ### 7.2 CSS Modules（既存プロジェクト）（564） | 消す | 同上 | — |
| ### 7.3 デザイントークン（586） | 直す | §9（色・間隔はテーマの値） | — |
| ## 8. データ取得・API通信（610） | 直す | §5・§6 | — |
| ### 8.1 API クライアントの設計（612） | 直す | §6（axios のインスタンス 1 つ・`services/api.ts`）。`fetch` の自作クライアントの例を消した | — |
| ### 8.2 Feature ごとの API 定義（684） | 直す | §6（`services/*.service.ts` が `types/api` の型を返す） | — |
| ### 8.3 4状態UIの実装（709） | 直す | §7（`toLoadState`・失敗にやり直し・空に次の導線） | #487 |
| ## 9. フォーム処理（762） | 直す | §8 | RHF・Zod の文書 |
| ### 9.1 React Hook Form + Zod（764） | 直す | §8 に短い例（Zod 4 の `z.email()`）を残した | — |
| ## 10. エラーハンドリング（879） | 直す | §10 | — |
| ### 10.1 Error Boundary の実装（881） | 直す | §10 の 1 行（ルートごとの Error Boundary） | — |
| ### 10.2 非同期エラーハンドリング（948） | 直す | §10（クエリ・ミューテーションの `error` で受ける）。`setState` で投げ直す技巧の例を消した | — |
| ### 10.3 API エラーハンドリング（980） | 直す | §6（`extractApiErrorMessage`・サーバーのエラーの形） | `core/exceptions.py`・`utils/apiError.ts` |
| ## 11. パフォーマンス最適化（1016） | 直す | §10 | — |
| ### 11.1 メモ化の適切な使用（1018） | 直す | §10 の 1 行（測って遅いときだけ） | — |
| ### 11.2 コード分割と遅延ロード（1062） | 直す | §10 の 1 行（画面ごとの `lazy`） | — |
| ### 11.3 リスト最適化（1088） | 直す | §4（`key` に添字を使わない）。react-window は入っておらず、大きな一覧は無いので消した | — |
| ### 11.4 画像最適化（1120） | 直す | §10 の 1 行（`loading="lazy"`）。画像の配信の仕組みが無いのに `?w=` を付ける例を消した | — |
| ## 12. テスト戦略（1155） | 直す | §14 | Testing Library の文書 |
| ### 12.1 テストの優先順位（1157） | 消す | 80/15/5 の割合に根拠が無い。§14 の「必ず確かめること」に置き換えた | — |
| ### 12.2 コンポーネントテスト（1163） | 直す | §14（`getByRole`・`userEvent.setup()`） | — |
| ### 12.3 カスタムフックのテスト（1207） | 消す | 一般論（Testing Library の文書） | — |
| ### 12.4 MSW によるAPIモック（1243） | 直す | §14 に MSW 3 の形で書き直した（`rest`→`http`・`msw/http`・`onUnhandledFrame`） | MSW 2→3 の移行の手引き |
| ## 13. アクセシビリティ（a11y）（1291） | 直す | §13（目標 WCAG 2.2 AA・MUI の部品を使う・ラジオのまとまりの名前〔#536〕） | WCAG 2.2 |
| ### 13.1 基本要件（1293） | 直す | §13 | — |
| ### 13.2 キーボードナビゲーション（1357） | 直す | §13（ダイアログは MUI の `Dialog`）。自作のモーダルの例を消した | MUI の文書 |
| ### 13.3 スクリーンリーダー対応（1412） | 直す | §13。`table` に `role="table"` などを重ねて付ける例（ネイティブの要素に不要な role）を消した | — |
| ## 14. セキュリティ（1456） | 直す | §11 | OWASP |
| ### 14.1 XSS対策（1458） | 直す | §11 の 1 行（DOMPurify は入っていないので、要るときに計画書に理由を書く） | — |
| ### 14.2 環境変数の管理（1477）（コメント 1483） | 直す | §11 の 1 行（`VITE_` は誰でも読める） | — |
| ### 14.3 認証トークンの管理（1496） | 直す | §11（localStorage に置かない・リフレッシュは HttpOnly の Cookie。サーバー側は Django §10） | OWASP |
| ## 15. AI支援開発のベストプラクティス（1529） | 消す | 進め方の決まり（I546・I547 の範囲）。AUTOGEN のコメントは運用されていない | — |
| ### 15.1 AI生成コードの管理（1531） | 消す | 同上 | — |
| ### 15.2 AI理解しやすいコード構造（1547） | 消す | 一般論 | — |
| ### 15.3 プロンプトテンプレート（1570）（1576・1583・1588・1593 の見出しはテンプレートの中） | 消す | 進め方の決まり。中身（Tailwind・Zustand）も今の決まりと矛盾 | — |
| ### 15.4 AI生成コードのレビューポイント（1601） | 消す | レビューの観点は §15 と I547（レビュー役への指示） | — |
| ## 16. Git/PR/CI運用（1640） | 消す | 進め方の決まり（`docs/runbooks/workflow.md` など・I546 の範囲） | — |
| ### 16.1 ブランチ戦略（1642） | 消す | 同上 | — |
| ### 16.2 コミットメッセージ（1652）（コメント 1655） | 消す | 同上 | — |
| ### 16.3 PR テンプレート（1665）（1668・1671・1676・1679・1684・1689・1692 の見出しはテンプレートの中） | 消す | 同上 | — |
| ### 16.4 CI パイプライン（1698）（コメント 1701） | 消す | 実際の CI と違う写し（Node.js 18 など） | — |
| ## 17. コード例とテンプレート（1743） | 消す | 写しは古くなる | — |
| ### 17.1 カスタムフックテンプレート（1745） | 消す | 取得は TanStack Query のフック（§5） | — |
| ### 17.2 コンポーネントテンプレート（Tailwind）（1821） | 消す | Tailwind は使わない | — |
| ## 18. 設定ファイル（1928） | 消す | 設定は実ファイル（`frontend/package.json`・`frontend/tsconfig.json`）が正。写しは食い違う | — |
| ### 18.1 ESLint設定（.eslintrc.json）（1930） | 消す | 実際は `package.json` の `eslintConfig`。ESLint の見直しは #517〜#519 | — |
| ### 18.2 Prettier設定（.prettierrc）（2014） | 消す | Prettier は入っていない | — |
| ### 18.3 TypeScript設定（tsconfig.json）（2031） | 消す | 実ファイルが正。版上げは #560 | — |
| ### 18.4 EditorConfig（.editorconfig）（2068） | 消す | 無い | — |
| ## 19. チェックリスト（2090） | 直す | §15（レビューで見る）に統合 | — |
| ### 19.1 コードレビュー前（2092） | 直す | §15・§7・§14 | — |
| ### 19.2 パフォーマンス（2103） | 直す | §10 | — |
| ### 19.3 アクセシビリティ（2110） | 直す | §13（コントラスト 4.5:1 を残した） | — |
| ### 19.4 セキュリティ（2119） | 直す | §11 | — |
| ### 19.5 AI生成コード（2126） | 消す | 15 と同じ理由 | — |
| ## 更新履歴（2136） | 消す | git の履歴が正。点検した日は §0 | — |
| ## 参考資料（2143） | 直す | 各節の「参照」に振り分けた | — |

### 3.3 `docs/runbooks/ux-rules.md`

| 元の見出し（行） | 結果 | 新しい置き場所・理由 | 根拠 |
|---|---|---|---|
| # UX重視の設計・実装ルール（1） | 直す | 「画面の使い勝手（UX）の決まり」。コードの書き方は React 規約、計画書の節は plan-writing-rules 13) が正と書いた | — |
| ## フロントエンド設計時のUX必須確認事項（3） | 直す | 1〜6 の節に | — |
| ### 1. エラー処理のUX原則（6） | そのまま（中身）・直す（言い回し） | §1 | — |
| ### 2. ローディング・待機状態のUX（17） | 直す | §2（時間のかかる処理の例を AI の問題の生成に） | — |
| ### 3. フォーム・入力のUX（23） | 直す | §3。「入力中にリアルタイムで指摘」を「入力欄を離れたときに確かめる」に直した（入力の途中で誤りを出すと、まだ打ち終わっていない利用者に誤りを見せてしまう） | Claude の判断（公式の出典なし。W3C のフォームの検証の手引きは確かめる時機を決めていないことを確認した: https://www.w3.org/WAI/tutorials/forms/validation/ ） |
| ### 4. ナビゲーション・遷移のUX（29） | そのまま | §4 | — |
| ### 5. レスポンシブ・アクセシビリティ（35） | 直す | §6。44px の根拠を WCAG 2.2 の 2.5.5（AA の最低は 2.5.8 の 24px）と書いた。スマホの幅 360px・色だけで伝えない、を足した。aria の書き方は React 規約 §13 に寄せた | WCAG 2.2 |
| ## 計画書への必須記載項目（UX観点）（41） | 消す | 計画書の節の正は `docs/runbooks/plan-writing-rules.md` 13)（性能・UX 設計）。2 か所で違う項目を決めていた | — |
| ## UX設計（45）・### 現在のUX課題（46）・### 改善後のユーザー体験（49）・### エラー・例外時の体験（52）・### 成功指標（55）（ひな形の中の見出し） | 消す | ひな形ごと消す。13) に無い項目の扱い: 「エラー・例外時の体験」は 13) の「エラー状態の表示方針」と同じ／「現在の UX 課題」「改善後のユーザー体験」は計画書の 1) 背景/目的と 2) 受け入れ条件で書く／「成功指標」は学習の効果なら 14)、それ以外は受け入れ条件 | `docs/runbooks/plan-writing-rules.md` |
| ## UX検証チェックリスト（59） | 直す | §7。4 つの状態の行を足した | — |
| （足す） | 足す | §5 データが無いとき（#487） | #487 |

### 3.4 `docs/runbooks/backend-check.md`

| 元の見出し（行） | 結果 | 新しい置き場所・理由 | 根拠 |
|---|---|---|---|
| # バックエンドチェック必須ルール（1） | 直す | 「バックエンドを変えたときの確かめ方」。確かめは残る形（自動テスト）で行うと書いた | `docs/proposals/automation_over_manual_checks_proposal.md:125-134` |
| ## データベース・モデル整合性チェック必須ルール（3） | 直す | §3「モデルと DB が食い違ったときの診断」に短く（必須の手順から、食い違いが出たときの診断へ） | 同上 |
| ### エラー対応・ロジック修正時の自動診断手順（5）（コードの中のコメント 10・13・16・22・26・31・38・73・74・79・99・103・115 を含む） | 直す | §3 の 4 つの順番に。Django シェルで列を比べる長いコード・`backend/logs/django.log` を読む手順を消した（`makemigrations --check`・`showmigrations`・`docker compose logs` で足りる） | — |
| ### 対象となるエラーパターン（127） | 直す | §3 のエラーの例（SQLite の `no such column` を PostgreSQL の `column ... does not exist` に直した） | — |
| ### 例外ルール（136） | 消す | 診断の手順にしたので、適用しない場合の決まりが要らない | — |
| ## バックエンド修正時のAPI統合テスト必須ルール（145） | 直す | §1「自動テストで確かめる」。curl で叩く手順は Claude が実行できず（元の注記 :147）、残らないので消した | 元の :147 |
| ### バックエンドロジック修正後の自動検証手順（149）（コメント 155・157・162・167・209・215・259・263） | 消す | curl・`jq` の手順と、廃止予定の学習記録の API（#492）の道筋。§1 の API テストに置き換えた | #492 |
| ### テスト完了の判定基準（289） | 直す | 中身（状態コード・形・組織の分離・エラー）を Django 規約 §13 の「必ず書くテスト」に寄せた。「2 秒以内」は根拠が無いので消した | — |
| ### フロントエンド期待形式チェックリスト（300） | 消す | 応答の形の写しは古くなる（ダッシュボードの形は #473 で変わった）。正は OpenAPI と画面の型（I493） | I493 |
| ### テスト失敗時の対処法（340）（コメント 345・350・351・356・357） | 直す | §3 の診断の順番に統合 | — |
| ## バックエンド修正時の要件適合性テスト必須ルール（362） | 直す | §1 の 4（組織の境界のテスト）と Django 規約 §5 に寄せた。要件の確かめは計画書の受け入れ条件とテストで行う | — |
| ### 修正ロジックの要件適合性検証手順（364）（コメント 383・391・399・414） | 消す | curl とシェルの手順・`organization_id` を直接読む古い例。組織の分離は API テスト（例: `core/tests/test_I446_cross_api_tenant_isolation.py`）で確かめる | — |
| ### 修正完了時の必須報告項目（452） | 直す | §4「報告に書くこと」に短く | — |

## 4. 漏れの点検

### 4.1 足した観点

| 観点 | 置き場所 | 出どころ |
|---|---|---|
| 組織の境界（絞り方・`# 組織で絞らない`・他組織は 404・越境のテスト） | Django §5 | #431・#461・I455・I446 |
| クエリの値の検証 | Django §6 | #479 |
| 回答の前に答えを返さない（action ごとの出力） | Django §6 | #476・I078 |
| API の受け渡しの形は OpenAPI が正 | Django §6・React §1・§6 | #460・#473・#488・I493 |
| 既定の権限 `IsAuthenticated` | Django §6 | DRF の文書・調査（`DEFAULT_PERMISSION_CLASSES = []`） |
| `get_permissions` と `@action` | Django §6 | 一覧 I209 F8 |
| 0 で割る集計 | Django §8 | #459 |
| N+1 のクエリの数のテスト | Django §8 | #461 |
| 日付と時刻（`timezone.localdate()`・画面の日付） | Django §9・React §12 | #481・Django の文書 |
| トークンの受け渡しと保存場所 | Django §10・React §11 | #501・#502・OWASP |
| CSP・廃止された設定 | Django §10 | Django 4.0 のリリースノート |
| ログに個人情報を出さない・`%s` | Django §11 | #437・#484 |
| Celery のタスクの組織の絞り・冪等・時間の上限 | Django §12 | Celery の文書 |
| マイグレーションを書き換えない・データのマイグレーションの戻し | Django §4 | Django の文書 |
| 外部の I/O のタイムアウト | Django §14 | 元の §14 の原則を具体化 |
| 利用者・組織が変わったらキャッシュを捨てる | React §5 | #491 |
| 送る形（JSON・multipart）を OpenAPI に合わせる | React §6 | #460 |
| 空のときの次の導線・スマホの幅ではみ出さない | React §7・§9・ux-rules §5・§6 | #487 |
| ラジオ・チェックのまとまりの名前 | React §13 | #536 |
| 差し替えていない通信でテストを落とす | React §14 | MSW の文書 |
| TypeScript 7 と道具用の 6 | React §0 | TS 7 の発表 |
| 依存どうしの組み合わせ（前提の版どうしは公式が対応をうたう組み合わせにする） | 両方の §0 の方針 | #499（kombu の新しい版と redis==5.0.1 が合わず celery が落ちた） |

### 4.2 足さなかった観点と理由

| 観点 | 理由 |
|---|---|
| 多言語（i18n） | 画面は日本語だけで、要件に無い |
| async のビュー・ASGI | このアプリは同期のビューと Celery で足りる（§1 に「使わない」と明記） |
| キャッシュの使い方（`core/cache_service.py`） | 事故・指摘の実例が無い。要るときに足す |
| SSR・SEO・React Server Components | ログインの後の画面だけの SPA で、要らない |
| React Compiler | 測った性能の問題が無い。画面のビルドの移行（#551）の後に、性能の問題が出たら検討する |
| Django のデプロイのチェックリストのうち `SECRET_KEY_FALLBACKS`・`CONN_MAX_AGE`・`ADMINS`・エラーの画面 | コードの書き方でなく配備・運用の設定（本番の環境の決まりを作るときに扱う） |
| Storybook・見た目の回帰テスト | 入っておらず、事故の実例が無い |
| 機能の切り替え（Feature Flag） | 段階のリリースの要件が無い |
| パスワードのハッシュ（Argon2） | Django の既定（PBKDF2）で足りる。元の規約は入っていない依存を前提にしていた |

## 5. 移行・直しのイシュー（AC9）

| 差 | 規約の節 | イシュー | 新規／同梱 |
|---|---|---|---|
| Node.js 18・CRA・Jest・user-event 13 | React §0・§1・§14 | #551 | 新規 |
| React 18・TypeScript 4.9 | React §0・§4 | #560 | 新規（#551 の後） |
| MUI 5 | React §0・§9 | #561 | 新規（#560 の後） |
| React Router 6・`react-router-dom` | React §0・§1 | #562 | 新規（#560 の後） |
| yup | React §1・§8 | #552 | 新規 |
| トークンを localStorage・本文で受け渡し | React §11・Django §10 | #553 | 新規（#501・#502 と順番を計画で決める） |
| Python 3.11 | Django §0 | #554 | 新規 |
| PostgreSQL 15 | Django §0 | #555 | 新規 |
| psycopg2 | Django §0・§1 | #556 | 新規 |
| 既定の権限が空・`SECURE_BROWSER_XSS_FILTER`・`IsOrgAdmin` の置き場所 | Django §6・§10 | #557 | 新規 |
| CSP が無い | Django §10 | #558 | 新規 |
| mypy が無い | Django §1・§3 | #559 | 新規 |
| テストの API の差し替え（axios-mock-adapter → MSW 3） | React §1・§14 | #511 | 同梱（コメント） |
| ESLint（TS 7 と道具用の 6・`vitest` の禁止を外す） | React §15 | #517 | 同梱（コメント） |
| 自動で止める範囲の照合（書き直した §15） | 両方の §15 | #520 | 同梱（コメント） |
| token_blacklist | Django §10 | #501 | 同梱（コメント） |
| トークンの更新の食い違い | React §11 | #502 | 同梱（コメント） |
| 日付の決め方 | Django §9・React §12 | #481 | 同梱（コメント） |
| クエリの値の検証 | Django §6 | #479 | 同梱（コメント） |
| `React.FC`・`forwardRef` | React §4 | #510 | 同梱（コメント） |
| recharts | React §1 | #516 | 同梱（コメント） |

| 規約の決まりのうち機械で止められるもの（Ruff の規則・非推奨の警告・`check --deploy`） | Django §3・§7・§9・§10・§11・§14・§15 | #563 | 新規（/simplify の直す深さの観点から） |
| 規約の決まりのうち ESLint で止められるもの | React §1・§4・§11・§12・§13・§14・§15 | #517 | 同梱（コメント） |

新規の 13 件は issue-review の判定がすべて「要補足」（助言・登録は止めない）。共通の指摘（根本原因が経緯の言い換え）は登録の前に直した。残りは各イシューの計画で決める細部。
