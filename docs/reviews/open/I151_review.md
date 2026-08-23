# I151 実装レビュー（Django 5.2 LTS 更新・未使用の django-guardian / django-extensions の除去）

- 関連: docs/issues/open/I151.md / docs/plans/open/plan_I151.md / GitHub #267 / Draft PR #269
- レビュー対象コミット: （実装後に記入。1 段目 `fix(I151): ...` / 2 段目 `chore(I151): ...`）

## レビュー観点（計画に対応）

### 1. 変更の局所性（計画外変更がないこと）
- [ ] 差分が `backend/requirements.txt` / `backend/requirements-dev.txt` / `backend/core/settings.py` の 3 ファイルのみである
- [ ] `settings.py` の差分が `THIRD_PARTY_APPS` からの `'django_extensions',` と `'guardian',` の 2 行削除のみで、`AUTHENTICATION_BACKENDS`・`REST_FRAMEWORK`・`MIDDLEWARE` に変更がない
- [ ] アプリコード（`accounts` / `core` / `problems` / `studylogs` / `dashboard`）に変更がない
- [ ] マイグレーションファイルが新規追加されていない
- [ ] `.github/workflows/ci.yml` / `e2e.yml` / `backend/Dockerfile` / `backend/pytest.ini` に変更がない（計画 §4 のとおり）

### 2. 依存更新の正確性
- [ ] `requirements.txt` が確定セットと**完全一致**する（TC-AUTO-11A 宣言側）
- [ ] 実際にインストールされたバージョンが宣言と一致する（TC-AUTO-11A / 11B 実インストール側＝再ビルド漏れがない）
- [ ] `==` の完全固定が維持されている（範囲指定に変わっていない）
- [ ] 据え置きと決めたパッケージ（celery 5.3.4 等）が変更されていない
- [ ] django-redis 7.0.0 でキャッシュが実際に読み書きできる（`default` / `sessions` / `problems` / `analytics` の 4 alias。計画時に実測済みだが、再ビルド後の実環境で再確認する）
- [ ] `django-guardian` と `django-extensions` の行が削除されている（コメントアウトではなく行ごと）

### 3. 未使用アプリ 2 件（guardian / django-extensions）の除去の完全性
- [ ] `requirements.txt` / `settings.py` に guardian・django-extensions が残っていない（TC-AUTO-05 判定 1・2・いずれも実装前 exit 1 を確認済み）
- [ ] Python コード全体に guardian・django_extensions の参照がない（TC-AUTO-06 判定 1・2・いずれも実装前 exit 1 を確認済み）
- [ ] `ANONYMOUS_USER_NAME` 等の専用設定がない（TC-AUTO-07・ダミー注入で exit 1 を確認済み）
- [ ] `manage.py check` が**警告 0**（TC-AUTO-04・実装前 exit 1 を確認済み）
- [ ] `guardian_*` の 2 テーブルが**意図的に残置**されており、削除するマイグレーションや SQL が含まれていない
- [ ] django-extensions がテーブルを持たないことを前提に、残置物の確認が不要であることを記録している

### 4. 脆弱性の解消
- [ ] `pip-audit -r requirements.txt` が exit 0（TC-AUTO-01）
- [ ] `pip-audit -r requirements-dev.txt` が exit 0（TC-AUTO-02）
- [ ] `.github/workflows/ci.yml` の監査対象を**広げていない**（イシュー決定 4・I152 の領域を侵していない）
- [ ] 計画時に増えた `PYSEC-2026-3717`（Fix: 5.2.17）も解消されている

### 5. マイグレーションの健全性
- [ ] drift なし（TC-AUTO-08）
- [ ] まっさらな DB での `migrate` が通る（TC-AUTO-09）
- [ ] 検証用の使い捨て DB が後片付けされている（開発 DB に影響していない）
- [ ] テスト記録に「マイグレーション検証の担保経路（a)(b)(c)」が明記されている

### 6. 無退行（依存更新の本丸）
- [ ] backend テストが **94 件 pass**（ベースラインと同数・TC-AUTO-03）
- [ ] **skip・削除・条件緩和による緑化をしていない**（件数一致で機械判定）
- [ ] 認可・テナント境界の 7 モジュールが更新前後で同じ結果（AC-18 の記録表が埋まっている）
- [ ] frontend Jest が 10 件 pass（TC-AUTO-12）
- [ ] E2E が全件 pass（TC-AUTO-13）
- [ ] CI の全 6 チェックが SUCCESS（TC-AUTO-14）

### 7. celery と推移的依存
- [ ] worker のログでタスクの**成功**が確認できる（TC-AUTO-10・beat が投げただけの確認になっていない）
- [ ] ログに `ERROR` / `Traceback` がない
- [ ] 再ビルド後の `pip freeze` が `docs/tests/open/I151_pip_freeze.txt` に記録・コミットされており、除去した 2 パッケージが含まれていない（TC-AUTO-15 判定 1・2）
- [ ] `celery` / `celery-beat` が**再ビルド後のイメージ**で起動している（旧イメージのままになっていない）

### 8. コミット分割
- [ ] 1 段目（本体依存＋pytest-django）と 2 段目（pytest のみ）に分かれている（TC-AUTO-16）
- [ ] `requirements.txt` を触ったコミットが 1 つだけ（本体依存が 1 段目に集約されている）
- [ ] 2 段目を取り消せば 1 段目の成果が残る構造になっている

### 9. セキュリティ
- [ ] 認可の判定経路に変更がない（`AUTHENTICATION_BACKENDS`・権限クラスが不変）
- [ ] マルチテナントの閲覧・操作範囲に変更がない
- [ ] 機密データのログ出力・保存が増えていない
- [ ] `/security-review` を実施し、指摘があれば対応している（計画 S-4）
- [ ] bandit の新規検出がない（あれば MEDIUM 以上を修正・LOW は `# nosec`）

### 10. 記録の完全性
- [ ] `I151_auto_test.md` の実施記録がすべて埋まっている（未実施が残っていない）
- [ ] `I151_manual_test.md` の実結果が埋まっている（Human 項目 No.7 を含む）
- [ ] 後続イシュー 3 件が起票され、番号が記録されている（AC-19）
- [ ] 計画書との差分（あれば）が理由付きで記録されている

## 敵対的レビュー観点（独立サブエージェント向け・「合格を反証せよ」）

- **「94 件 pass だから無退行」を反証せよ**: `--no-migrations` により pytest はマイグレーションを検証しない。DRF 3.18 / Django 5.2 で挙動が変わるが**既存テストが触れていない経路**（シリアライザのエラー形・ページネーション・認証トークンの失効・admin）が存在しないか。件数一致は「同じテストが通った」ことしか示さず、カバーされていない範囲の退行は検出できない。
- **「guardian / django-extensions は未使用だから削除しても安全」を反証せよ**: `INSTALLED_APPS` から外すことで、両アプリが提供していた**暗黙の副作用**（guardian: マイグレーション適用・AnonymousUser 行の作成・パーミッション関連のシグナル／django-extensions: management コマンドの登録・`AutoSlugField` 等のモデルフィールド・シグナル）に依存する箇所が本当にゼロか。既存 DB と新規 DB で挙動が分岐しないか。**とくに django-extensions は grep が `django_extensions` 文字列に依存しており、`from django_extensions.db.fields import ...` 以外の経路（settings 文字列以外での間接利用）を取りこぼしていないか。**
- **「認可の判定経路は不変」を反証せよ**: DRF 3.15 → 3.18 で権限クラスの評価順・`has_object_permission` の呼ばれ方・例外の型が変わっていないか。テナント境界テスト 7 モジュールが**組織越境を本当に検出できる**内容か（緩い assert で通っているだけではないか）。
- **「TC-AUTO-03 は緑化を検出できる」を反証せよ**: 計画時点で判定式に `! grep -qE 'skipped|xfailed|deselected'` を追加し、`94 passed, 2 skipped` 形の緑化を弾くよう強化した（強化後の式が実装前ログに対し exit 0 を返すことも実測済み）。それでも抜け道が残らないか — 例えば**テストファイルごと削除して同数の新規テストを足す**、`pytest.ini` の `testpaths` を狭める、条件分岐で assert を実質無効化する、といった手段は件数一致でも検出できない。差分レビューで実際にテストコードが無改変であることを別途確認したか。
- **「celery は正常」を反証せよ**: TC-AUTO-10 は直近 3 分のログを見るだけである。**再ビルド前の古いログ**を拾って合格していないか。worker が起動直後で 1 回も実行していない場合に false-green にならないか。`ERROR` の grep がログ書式の違い（`CRITICAL` 等）を取りこぼさないか。
- **「再ビルドは完了している」を反証せよ**: `celery` / `celery-beat` / `e2e-init` が旧イメージのまま動いていないか。TC-AUTO-11A / 11B の実インストール判定は `backend` コンテナしか見ていないため、worker 側が古いままでも合格しうる。
- **「pip-audit exit 0 だから安全」を反証せよ**: 監査は既知の advisory しか見ない。DB の更新タイミング次第で結果が変わる（実際に 6 件 → 7 件へ増えた）。マージ直前に再実行しても同じ結果が保証されるか。
- **「2 段コミットで安全に退避できる」を反証せよ**: 2 段目を取り消したとき、`requirements-dev.txt` だけが戻り**イメージは pytest 9 のまま**という不整合が起きないか。§8 は「再ビルドまで行い、TC-AUTO-11B が exit 1 に戻ることで戻し漏れを検出する」としているが、この検出は**戻した後に TC を実行した場合にのみ効く**。実行を忘れた場合に気づける経路が別にあるか。

## 結果

（実装後に記入）
