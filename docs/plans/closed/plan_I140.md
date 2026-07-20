## 基本情報
- **計画書ID**: plan_I140
- **関連イシュー**: #251
- **Draft PR**: #254
- **作成根拠資料**: docs/issues/open/I140.md（起点イシュー・grill-me 済み）
- **実装後評価**: docs/reviews/open/I140_review.md
- **作成日**: 2026-07-19

---

## 1. 背景/目的

登録 API の personal 組織自動作成フォールバックが `category`（NOT NULL FK）未指定で `IntegrityError` になる潜在バグを根治する。

- **原因の概要**: slug なしの新規登録で「個人利用」組織が見つからない場合、プログラムが組織を自動作成しようとするが、必須項目のカテゴリを渡し忘れているため必ず失敗する。通常環境では「個人利用」組織が最初から存在するため表面化していない。
- **詳細な原因分析**:
  1. `UserRegistrationView._get_organization()`（`backend/accounts/views.py:147-166`）は slug なし登録時に `type='personal'`・`is_active=True` の組織を検索し、不在なら `Organization.objects.create(name='個人利用', slug='personal', type='personal', is_active=True)` を実行する（views.py:154-161）。
  2. `Organization.category` は `null=True` なしの FK（`backend/accounts/models.py:51-56`・`on_delete=PROTECT`）のため、この create は **`IntegrityError`（NOT NULL 違反）** になる。
  3. 発生した例外は `create()` の広域 `except Exception`（views.py:121-129）が 400 「エラーが発生しました」に丸めるため、原因が露見しない。
  4. dev/本番 DB では migration 0014 が personal 組織を、0017/0018 が personal カテゴリと紐付けを作成済みのため通常は到達しない。**personal 組織が不在/非アクティブの環境**（初期化不備・データ初期化後）でのみ slug なし登録が全件失敗する。
  5. このパスには自動テストが存在せず、実行されたことがない（I131 code-review の静的解析で発見・モデル定義と突き合わせて裏取り済み）。
- **根本原因（コードレベル）**: migration で「personal 組織は常に存在する」前提が確立しているにもかかわらず、未認証の登録 API 内に検証されていない組織自動作成パス（隠れた書き込みパス）が残置され、しかも必須 FK `category` を渡していない実装漏れがある。

**解決方針（grill-me で (b) 確定・2026-07-19）**: フォールバック自動作成を**廃止**し、personal 組織不在時は None を返して既存の 400 分岐（views.py:78-84・「組織の設定に失敗しました」）に載せる。ログは `logger.error` で環境異常を明示する。400/500 の意味論是正（personal 不在の 500 化）は I142（#253）へ引き継ぎ済み（I142 本文に追記済み）。

## 調査結果

### 環境前提確認（2026-07-19 実施）
- `docker compose ps` → backend / db / redis / celery 稼働中（backend healthy）。frontend は unhealthy だが本イシューは FE 変更なし・手動テストも API のみのため影響なし。
- テスト実行: `docker compose exec backend python -m pytest`（既存慣例どおり）。

### 既存テストの事前実行（baseline・2026-07-19）
- `docker compose exec backend python -m pytest --tb=short -q` → **90 passed**（クリーン。I131 の 6 件を含む。develop b81a94d = PR #248 マージ済みを確認）。

### コード読解による確定事項
- `create()` には **`_get_organization` が None を返した場合の 400 分岐が既に存在**する（views.py:78-84）。レスポンス body は `{"error": {"main_message": "組織の設定に失敗しました", "sub_message": "無効な組織URLまたはシステムエラー"}}`・status 400。→ (b) はフォールバック create を削って None を返すだけで実現でき、例外ハンドリング設計（I142 スコープ）に踏み込まない。
- この 400 分岐は slug 不正時（`test_I131_org_id_rename.py::test_register_unknown_slug_returns_400` = TC-AUTO-07）で回帰固定済み。同じ分岐に personal 不在ケースを載せるため、既存 TC と新規 TC が同一契約を二方向から固定する。
- ロガー: ビューは `logging.getLogger('django')` を使用。`core/enhanced_logging.py:322-326` で `'django'` ロガーは `propagate: True`・level INFO → **pytest の caplog で捕捉可能**（`caplog.at_level(logging.ERROR, logger='django')`）。
- migration 前提: personal 組織は 0014（作成）・0017（personal カテゴリ作成）・0018（category 紐付け）で保証。dev DB に存在確認済み（I131 manual No.3 で `organization_id: 3` を実測）。
- テスト DB: `backend/pytest.ini` は `--no-migrations` → **personal 組織は存在しない = 「personal 不在」状態が素の DB で決定論的に再現できる**（イシュー「制約・引き継ぎ情報」どおり）。
- django-ratelimit: 登録ビューは `@ratelimit(key='ip', rate='10/5m')`（views.py:61）。I131 と同様、新規テストファイルにファイルローカル autouse fixture で `RATELIMIT_ENABLE = False` を置いて決定論化する。
- DRF スロットル（I127）は `backend/conftest.py` の autouse fixture で無効化済み（考慮不要）。

### 適用規約（rules/ultimate_django_coding_standards.md より抽出）
- テスト: `test_*.py` 命名・fixture ベース・未認証は素の `APIClient`・`rest_framework.status` 定数で assert・AAA 構成。
- ログ出力: 適切なレベルで記録（環境異常は error が適切）。
- 認可: 変更なし（`AllowAny` 維持・権限クラスに触れない）。
- React 規約: FE コード変更なしのため新たに適用される実装ルールなし。

### 参照実装（I131 で確立済みの慣例を踏襲）
- テスト配置: `backend/accounts/tests/`（パッケージ作成済み）・ファイル名 `test_I140_personal_org_fallback.py`（イシュー別ファイルの慣例）。
- fixture・ペイロード形: `test_I131_org_id_rename.py` の `_payload()`/`setup` 形を踏襲（personal 組織は**意図的に作らない**のが本イシューの前提状態）。

## 2. 受け入れ条件（Acceptance Criteria）
イシューの AC そのまま:
- [ ] personal 組織が存在しない状態での `POST /api/auth/register/`（slug なし）が 400 を返し、`error.main_message` が「組織の設定に失敗しました」（既存分岐の流用・応答形式変更なし）— 回帰テストで固定
- [ ] 上記の際に Organization レコードが新規作成されない（自動作成フォールバックの廃止）— 回帰テストで固定
- [ ] 上記の際にサーバーログへ personal 組織不在の `logger.error` が記録される — 回帰テストで固定（caplog）
- [ ] personal 組織が存在する通常状態の登録挙動に回帰がない（`test_I131_org_id_rename.py` が引き続き PASS）
- [ ] 既存テストが全 PASS（baseline 90 件）
- [ ] 再発防止テストは修正前に FAIL することを確認済み（TDD RED・false-green でない）

## 3. 影響範囲
- **Backend**: `accounts/views.py`（`_get_organization` の else 節のみ）＋ `accounts/tests/test_I140_personal_org_fallback.py`（新規）
- **Frontend**: なし（レスポンス契約は既存 400 分岐の流用で不変更）
- **DB**: なし（スキーマ・マイグレーション変更なし。書き込みパスの削除のみ）
- **Config/Infra**: なし。依存関係ファイル変更なし → Dockerfile/compose 波及なし
- **Docs**: I142（#253）への 500 化引き継ぎ追記は grill-me 時に実施済み（実装フェーズの作業ではない）

## 4. 変更点一覧

| ファイル | 対象 | 変更内容 |
|---------|------|---------|
| `backend/accounts/views.py` | `UserRegistrationView._get_organization`（:154-162） | フォールバックの `Organization.objects.create(...)` ブロックを削除し、`logger.error` ＋ `return None` に置換 |
| `backend/accounts/tests/test_I140_personal_org_fallback.py`（新規） | — | personal 組織不在時の slug なし登録の回帰テスト（TC-AUTO-01〜04） |

### 実装コード例

**修正アプローチ**: `_get_organization` の else 節（slug なし）で personal 組織が見つからない場合に、組織を自動作成する代わりに環境異常を error ログへ記録して None を返す。None は `create()` の既存 400 分岐（views.py:78-84）が受けるため、呼び出し側・レスポンス契約・例外ハンドリングには一切触れない。

`backend/accounts/views.py:147-166`（else 節全体・修正後）:
```python
        else:
            # デフォルト：personal組織を取得
            personal = Organization.objects.filter(
                type='personal',
                is_active=True
            ).first()

            if not personal:
                # personal 組織は migration 0014/0017/0018 で常に存在する前提。
                # 不在は環境異常のため自動作成せず、既存の 400 分岐（create() 側）に委ねる
                logger.error(
                    "Personal organization (type='personal', is_active=True) not found. "
                    "Environment is misconfigured; slug-less registration rejected."
                )
                return None

            logger.info(f"Using personal organization: {personal.name}")
            return personal
```
（差分: create ブロック 8 行の削除・error ログ＋`return None` の追加。import 追加不要・他メソッド不変更）

## 5. 実装手順（TDD・単一垂直スライス）

本修正は「BE の書き込みパス削除 + 回帰テスト」の単一スライス（FE・DB 変更なし。API 契約も既存分岐流用で不変のため、縦貫通は BE→dev 実環境 API 確認で完結）。

- **ステップ1: 回帰テスト先行（RED 確認）**
  1. `backend/accounts/tests/test_I140_personal_org_fallback.py` に TC-AUTO-01〜04 のテスト関数を追加（ファイルローカル autouse で `RATELIMIT_ENABLE=False`・personal 組織を作らない fixture）。
  2. 現行コードに対し実行し、**全 TC が RED** であることを確認・記録 → auto_test「TDD RED 確認」参照（想定: 現行はフォールバック create が IntegrityError → 広域 except の 400 「エラーが発生しました」となり、body 不一致・ログレベル不一致で RED。組織数不変 TC は現行でも GREEN の可能性があるため false-green 注入検証で担保 = ステップ2-2）。
- **ステップ2: フォールバック廃止（ステップ1 の RED 記録が前提）**
  1. 上記コード例どおり `_get_organization` の else 節を修正 → 新規 TC 全 GREEN・フォールバック不在の決定論 grep（TC-AUTO-05）が合格（exit 0）。
  2. 否定系 TC（組織が新規作成されない）の false-green 注入検証を実施 → auto_test「false-green 自己検証」参照。
  3. 全体回帰（baseline 90 件 + 新規）→ TC-AUTO-06 参照。
- **ステップ3: dev 実環境の無退行確認（ステップ2 完了が前提）**
  1. dev 実環境（personal 組織あり＝通常状態）で slug なし登録が引き続き 201 になることを確認 → manual_test No.3（Claude）。

依存関係: ステップ1→2→3 は直列。サービス再起動: 不要（dev サーバーのホットリロードで反映・ファイル削除やサービス停止なし）。

## 6. テスト計画

### 自動テスト（詳細: `docs/tests/open/I140_auto_test.md`）
- テストレベル: **API 結合テスト**（DRF `APIClient`・未認証。「personal 不在で登録がどう振る舞うか」はルーティング〜ビュー〜DB を通す結合レベルでのみ検証できる。`--no-migrations` のテスト DB が「personal 不在」を決定論的に再現）。
- 再発防止: 400 応答は **body 完全一致** assert（広域 except 経由の「エラーが発生しました」400 と区別し、既存分岐流用を固定）。組織の非作成・error ログ（caplog）も assert。
- 認可テスト: 認可変更なし（`AllowAny` 維持）。未認証 `APIClient` で叩くこと自体が現行認可の回帰固定。
- テナント境界: 変更なし（組織の決定ロジックの分岐削除のみ。slug 指定ルートは不変更で、I131 の TC-AUTO-05/07 が既存挙動を固定済み）。

### 手動テスト（詳細: `docs/tests/open/I140_manual_test.md`）
- 全項目 Claude 実施（新規テスト・全体回帰の実行、dev 実環境での通常登録 201 確認）。FE・UI 変更がないため Human 目視項目なし。

## 7. ロールバック
- `_get_organization` の else 節を旧コード（フォールバック create）に戻し、`backend/accounts/tests/test_I140_personal_org_fallback.py` を削除すれば従来動作へ完全に戻る。DB 変更なしのためマイグレーション不要。

## 8. Risk & 回避策
- **リスク1（隠れた依存）**: フォールバック自動作成に依存する環境・テスト・スクリプトが存在し、廃止で壊れる。→ 回避: `Personal organization was missing` / フォールバック関連の参照を repo 全体 grep で確認（実装時に TC-AUTO-05 の否定 grep で固定）。dev/本番は migration で personal 組織が保証され、テスト DB は fixture 自作が慣例（I131 で確立）のため依存箇所はない見込み。全体回帰 90 件でも検証。
- **リスク2（契約変更の混入）**: 修正時にレスポンス body や既存分岐の文言まで変えて FE を壊す。→ 回避: 変更は `_get_organization` の else 節のみ（コード例で固定）。TC-AUTO-01 が body 完全一致を assert し、I131 の TC-AUTO-07 が同一分岐の既存契約を固定済み。
- **リスク3（caplog 不捕捉）**: `'django'` ロガーの設定次第で caplog が error ログを捕捉できず TC が flaky 化。→ 回避: `propagate: True` を設定ファイルで確認済み（調査結果）。`caplog.at_level(logging.ERROR, logger='django')` を明示。万一環境差で不安定な場合は実装中断→計画更新の正規手順。
- **リスク4（通常状態の退行）**: personal 組織が存在する場合の分岐を誤って壊す。→ 回避: `test_I131_org_id_rename.py`（TC-AUTO-06: slug なし 201）が既に回帰固定済み。全体回帰＋dev 実環境確認（manual No.3）で二重に検証。
- **補足（スコープ外の既知事項）**: 広域 `except Exception` の丸め・personal 不在 400 の 500 化は I142（#253）で対応（本文追記済み）。migration 未適用環境の運用手順整備はイシュースコープ外。

## セキュリティ・ベストプラクティスチェック
- **認証・認可**: 権限クラス変更なし（`AllowAny` の公開登録エンドポイント維持）。未認証リクエスト起点の DB 書き込みパス（組織＋暗黙のカテゴリ前提）を削除するため、**攻撃面はむしろ縮小**（最小権限の方向）。
- **入力バリデーション**: 変更なし（serializer 検証・URL converter は不変更。修正は組織決定の分岐のみ）。
- **機密データ**: 取り扱いコード不変更。追加する error ログに個人情報・認証情報は含まない（固定文言のみ）。
- **OWASP**: 新規リスクなし（SQLi: ORM のみ・XSS/CSRF: JSON API・変更なし）。
- **依存ライブラリ**: 追加なし → pip-audit/npm audit の新規対象なし。
- **bandit**: 変更箇所に該当パターンなし（MEDIUM 以上修正対象・pre-commit で自動検証）。

## 高リスク判定
- **判定: No**。権限クラス・認可ロジックの変更なし／新規エンドポイントなし／個人情報の取り扱い変更なし／レスポンス・API 契約不変（既存 400 分岐の流用）。書き込みパスの削除のみで、露出は増えない。
- **確定フロー**: `/plan-issue-review I140` → `/implement I140`（security-review 省略。plan-review で判定に異議があれば従う）。

## 各種チェック結果
- **P3（データ整合性/DB）影響なし**: スキーマ・マイグレーション変更なし。トランザクション境界も不変更（フォールバック create は atomic ブロック外にあった書き込みで、削除により整合性はむしろ改善）。
- **P5（運用設計/外部API/非同期/バッチ）影響なし**: 外部連携・非同期処理の変更なし。ログは既存ロガーへの error 1 行のみ（構造化ログ基盤の変更なし）。
- **P6（性能・UX）影響なし**: FE コード変更なし。クエリは既存の単純 SELECT のまま（書き込みが 1 パス減るのみ）。
- **P8（コスト）影響なし**: 新規インフラ/外部サービスなし。
- **P9（プライバシー）影響なし**: 個人情報の新規取得・保存・露出なし。

## 設計判断の明示
| 設計判断 | 出所 |
|---------|------|
| フォールバック自動作成の廃止・None 返却で既存 400 分岐に載せる（方式 (b)） | イシュー明記（grill-me 確定） |
| `logger.error` で personal 組織不在＝環境異常を明示 | イシュー明記（grill-me 確定） |
| 400 維持・500 化は I142 へ引き継ぎ | イシュー明記（grill-me 確定・I142 本文追記済み） |
| error ログの検証方法 = caplog（`propagate: True` 確認済み） | イシューが「計画で確定・caplog 想定」と委任 → 本計画で確定 |
| テストファイル名 `test_I140_personal_org_fallback.py` | イシューが「命名は計画で確定」と委任 → I131 のイシュー別ファイル慣例に準拠 |
| 400 応答の body 完全一致 assert（広域 except 400 との区別） | 仮定で決めた（I131 で確立した false-green 排除手法の踏襲） |
| personal 組織が非アクティブのみ存在するケースの TC 追加 | 仮定で決めた（イシューの発現条件「非アクティブ化された環境」の明示的な固定・低コスト） |
| フォールバック不在の決定論 grep TC（TC-AUTO-05） | 仮定で決めた（「自動作成コードが残っていない」ことの機械固定） |

→ 「仮定で決めた」3 項目は次の承認ポイントで確認する。

## 9. 承認ポイント（チェックリスト）
- [ ] 修正方式: `_get_organization` の else 節のみ変更（フォールバック create 削除 → `logger.error` + `return None`）・呼び出し側/レスポンス契約/例外ハンドリング不変更 — でよいか
- [ ] テスト配置・命名: `backend/accounts/tests/test_I140_personal_org_fallback.py`（慣例準拠） — でよいか
- [ ] 追加 TC（仮定 3 件）: ①400 応答の body 完全一致 assert ②personal 非アクティブのみ存在ケースの TC ③フォールバック不在の決定論 grep TC — でよいか
- [ ] 手動テスト: 全項目 Claude 実施（UI 変更なしのため Human 目視なし。dev 実環境の通常登録確認はテストユーザー `i140_smoke` を新規作成・残置可） — でよいか
- [ ] 高リスク判定 No（security-review 省略・plan-review 後に /implement へ） — でよいか

## レビュー結果
- [20260720_0233 判定: ✅ 完了](../../reviews/closed/I140_plan_review_20260720_0233.md)
- Info 指摘への対応（2026-07-20）: ① TC-AUTO-05 の判定式を `! grep -q "Organization.objects.create" backend/accounts/views.py` に強化（旧ログ文言依存を排除・現行コードで exit 1 の事前検証を再実施済み）。② `logger.info` の f-string は既存コードで本イシューの変更対象外のため不変更（追加する `logger.error` は固定文字列で規約準拠）。
