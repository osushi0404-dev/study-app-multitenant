# I151 手動テスト（Django 5.2 LTS 更新・未使用アプリ 2 件の除去後の無退行確認）

- 関連: docs/issues/open/I151.md / docs/plans/open/plan_I151.md / GitHub #267 / Draft PR #269
- 前提: `docker compose up -d --wait`（6 サービス healthy）。**ステップ 1 の再ビルド完了後**に実施する
- UI のコード変更はないため、Human 項目は「依存更新で画面が壊れていないこと」の目視確認に絞る

## 使用アカウント

| 用途 | ユーザーID | メール | 所属組織 | データ量 | 権限 |
|---|---|---|---|---|---|
| 主（組織あり・管理者） | `osushi0404admin` | `test01@gmail.com` | 株式会社おすしはなんだか楽しいよ | 科目 3・問題 30 | staff |
| 副（個人利用・データ多め） | `osushi014` | `test014@gmail.com` | 個人利用 | 科目 11・問題 131 | 一般 |

> パスワードはユーザーご自身が設定したものを使用してください（dev DB の既存アカウントです）。テナント分離そのものの検証は E2E の `tenant_isolation` シナリオ（TC-AUTO-13）が担保します。

---

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | ステップ 1 完了後に自動テストの TC-AUTO-00〜10 / 11A / 12 を順に実行する（`docs/tests/open/I151_auto_test.md` 参照）。**TC-AUTO-02 と TC-AUTO-11B はステップ 2 完了後に実施する**（この時点では pytest 8.3.4 が正しいため） | すべて exit 0。とくに TC-AUTO-03 が **94 passed**（skip 0 件）、TC-AUTO-04 が警告 0、TC-AUTO-05/06/07 が guardian・django_extensions 不在で合格、TC-AUTO-11A が宣言・実インストールの両方で一致 | Claude | OK（2026-08-24）— TC-AUTO-00〜10 / 11A / 12 / 17 すべて exit 0。94 passed・skip 0 件・check 警告 0 | |
| 2 | TC-AUTO-09（使い捨て DB での `migrate`）を実行する | 前回残骸の除去 → `CREATE DATABASE migrate_check` → `migrate --noinput` が exit 0 で完了し、`Applying ...` のログが最後まで進む。後片付けで DB を破棄する | Claude | OK（2026-08-24）— 使い捨て DB `migrate_check` で 58 マイグレーション適用・exit 0。guardian のマイグレーション 0 件。検証後に破棄済み | 後片付けの `DROP DATABASE` はフックが承認を求める場合がある（検証専用 DB のため承認可） |
| 3 | 再作成から 1 分以上待ってから TC-AUTO-10 を実行する | 直近 3 分のログに `Task studylogs.tasks.update_daily_analytics_task[...] succeeded` があり、`ERROR` / `Traceback` が無い | Claude | OK（2026-08-24）— 直近 3 分に成功ログ 9 件・ERROR / Traceback 0 件 | beat が 30 秒間隔で投げるため 1 分待てば 2 回分出る |
| 4 | TC-AUTO-15（`pip freeze`）を実行し、出力を `docs/tests/open/I151_pip_freeze.txt` へ保存してコミットする | Django が `5.2.17`、`django-guardian` と `django-extensions` が**一覧に無い**。kombu 等の推移的依存のバージョンが記録に残る | Claude | OK（2026-08-24）— `docs/tests/open/I151_pip_freeze.txt`（81 行）に記録。Django==5.2.17・django-guardian / django-extensions は不在 | celery が落ちた場合の切り分け材料 |
| 5 | `docker compose exec -T backend curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/admin/login/` を実行する | `200`（Django 5.2 の admin が正常に描画される） | Claude | OK（2026-08-24）— `admin_login_http=200` | Django 本体のテンプレート・静的ファイル経路の生存確認 |
| 6 | 認可・テナント境界の対象モジュールを個別に実行し、モジュール名と件数を記録する。対象: `problems/tests/test_I103_cross_org_create.py` / `problems/tests/test_I104_subject_authz.py` / `problems/tests/test_I006_subject_org_admin.py` / `problems/tests/test_I078_is_correct_exposure.py` / `accounts/tests/test_I131_org_id_rename.py` / `accounts/tests/test_I140_personal_org_fallback.py` / `core/tests/test_I127_throttling.py` | 全モジュールが pass。更新前と更新後の件数が一致し、skip・削除・条件緩和が 0 件であることを記録する（AC-18） | Claude | OK（2026-08-24）— 7 モジュール全て pass（下表）。テストファイルは 1 件も変更していない | 「関連テストを実行した」ではなくモジュール名を列挙して記録する |
| 7 | ブラウザで `http://localhost:3000` を開き、`osushi0404admin`（`test01@gmail.com`）でログインする。ログイン後、ダッシュボード → 問題一覧 → クイズを 1 問回答 → 学習履歴 の順に画面を開く | ログインが成功しダッシュボードが表示される。問題一覧に自組織（株式会社おすしはなんだか楽しいよ）の科目 3 件が並び、他組織の科目が混ざらない。クイズが出題され回答が保存される。学習履歴に回答が反映される。いずれの画面でも赤いエラー表示・白画面・コンソールの 500 エラーが出ない | Human | | UI のコード変更はないため、依存更新による API 応答形の変化がないことの目視確認 |
| 8 | 後続イシュー 3 件を `/issue-bootstrap` で起票する（タイトル案はイシュー本文の決定 2 / 7-C / 7-D に記載） | 3 件が起票され、イシュー番号が記録される。内訳: guardian_* テーブル除去 / backend 依存の lockfile 導入 / celery beat スケジュールの環境別切り替え | Claude | | AC-19。django-extensions の依存移動は決定 7 の変更（更新→削除）により不要になった |
| 9 | ステップ 2（pytest 9.0.3）完了後に TC-AUTO-02 / 03 / 11B / 12 を実行する | TC-AUTO-02 が exit 0（開発依存の脆弱性 0 件）、TC-AUTO-03 が 94 passed、TC-AUTO-11B が宣言・実インストールとも 9.0.3、TC-AUTO-12 が 10 passed | Claude | OK（2026-08-24）— TC-AUTO-02 exit 0・TC-AUTO-03 94 passed・TC-AUTO-11B exit 0・TC-AUTO-12 10 passed | ここが落ちた場合は 2 段目のみ取り消す（計画 §8）。取り消したら**再ビルドが必要**（イメージには pytest 9 が残るため） |
| 10 | Draft PR #269 を push 後、TC-AUTO-13（E2E）と TC-AUTO-14（CI 6 チェック）を実行する | E2E が全件 pass。`gh pr checks 269` で SUCCESS 以外が 0 件 | Claude | | AC-13・AC-14 |
| 11 | 再ビルド後の実コンテナに対し、ログインエンドポイントへ誤ったパスワードで 6 回連続 POST する（`docker compose exec -T backend python manage.py shell -c` の `APIClient` を使用。`RATELIMIT_ENABLE` は既定の有効のまま） | 6 回目が **403（django-ratelimit の遮断）** で拒否される。5 回目までは 400/401 が返る。遮断されない場合はレート制限がフェイルオープンしている（security-review シナリオ #1・AC-21 の実挙動確認） | Claude | OK（2026-08-24）— `codes [400, 400, 400, 400, 400, 403]`。5 回目まで 400、**6 回目で 403 に遮断**。django-redis 7.0.0 上でブルートフォース防御が機能 | TC-AUTO-17 がカウンタ機構を、本項目が実際の遮断を確認する。確認後はカウンタが残るため、後続の手動確認では IP かキーを変えるか 5 分待つ |

---

## 記録欄

### AC-18: 認可・テナント境界テストの前後比較（No.6 で記入）

| モジュール | 更新前 | 更新後 | skip/削除/緩和 |
|---|---|---|---|
| `problems/tests/test_I103_cross_org_create.py` | 6 passed | 6 passed | なし |
| `problems/tests/test_I104_subject_authz.py` | 5 passed | 5 passed | なし |
| `problems/tests/test_I006_subject_org_admin.py` | 12 passed | 12 passed | なし |
| `problems/tests/test_I078_is_correct_exposure.py` | 7 passed | 7 passed | なし |
| `accounts/tests/test_I131_org_id_rename.py` | 6 passed | 6 passed | なし |
| `accounts/tests/test_I140_personal_org_fallback.py` | 4 passed | 4 passed | なし |
| `core/tests/test_I127_throttling.py` | 8 passed | 8 passed | なし |
| **全体** | **94 passed** | **94 passed** | なし |

### マイグレーション検証の担保経路（記録必須・イシュー決定 7-A）

次に同じ疑問が出たときに調べ直さずに済むよう、以下を記録する。

- **(a) ローカル**: 使い捨て DB（`migrate_check`）への `migrate`（TC-AUTO-09）
- **(b) CI**: E2E ジョブがまっさらなランナー上で `migrate` を実行（`.github/workflows/e2e.yml` の 17 行目・25 行目）
- **(c) CI**: Backend Lint & Security の「Check migration drift」（`.github/workflows/ci.yml` 29〜35 行目）
- **注意**: `backend/pytest.ini` の `--no-migrations` により、**pytest はマイグレーションを検証しない**。上記 3 経路がその穴を埋めている
- **実施結果（2026-08-24）**: (a) 使い捨て DB `migrate_check` で 58 マイグレーションを適用し exit 0（guardian のマイグレーション 0 件・検証後に破棄）。(c) `makemigrations --check --dry-run` が `No changes detected`。(b) は CI の E2E ジョブで実行される
- **更新前後の件数が同一である根拠**: テスト関連ファイル（`backend/*/tests/*` / `conftest.py` / `pytest.ini`）の変更は **0 件**。ブランチの backend 側の差分は `requirements.txt` / `requirements-dev.txt` / `core/settings.py` の 3 ファイルのみ（`git diff origin/develop...HEAD --name-only -- backend/` で確認）

### 後続イシューの起票結果（No.8 で記入）

| # | タイトル | イシュー番号 |
|---|---|---|
| 1 | 未使用の guardian_* テーブル除去（2 テーブル・バックアップ取得のうえ実施） | |
| 2 | backend 依存のロックファイル導入 | |
| 3 | celery beat のスケジュールが開発用のまま（5 タスク・crontab の import 欠落も併せて是正） | |
