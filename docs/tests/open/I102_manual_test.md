# I102 手動テスト: 問題管理を組織管理者権限に限定

前提:
- 開発環境が稼働（`docker compose ps` で backend/frontend/db が Up）。フロントは http://localhost:3000 。
- テスト用アカウント（I102 手動テスト専用・同一組織 `cute_school`＝科目2/問題21 あり）:

  | 役割 | メールアドレス | パスワード | role | 組織 |
  |------|--------------|-----------|------|------|
  | 組織管理者 | `i102_admin@example.com` | `I102ManualTest!` | admin | cute_school |
  | 一般ユーザー | `i102_user@example.com` | `I102ManualTest!` | user | cute_school |

  ※ どちらもメール認証済み・有効化済み。パスワード認証確認済み（2026-07-07）。
  ※ 既存アカウントはパスワード不明のため専用に作成（既存アカウントは未変更）。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `i102_user@example.com` / `I102ManualTest!` で http://localhost:3000/login からログイン→ダッシュボード左のサイドバーを確認 | サイドバーに「問題管理」が**無い**（「科目管理」も無い。「ダッシュボード/学習統計/設定」は有る） | Human | | 非admin |
| 2 | 上記 `i102_user` のまま、ブラウザのアドレスバーに `http://localhost:3000/quiz-management` を入力して Enter | 管理画面が出ず「このページにアクセスする権限がありません。管理者権限が必要です。」の赤いエラーが表示される | Human | | 非admin 直アクセス遮断 |
| 3 | 一度ログアウトし `i102_admin@example.com` / `I102ManualTest!` でログイン→サイドバーを確認し「問題管理」をクリック | 「問題管理」が表示され、クリックで問題一覧画面（cute_school の問題21件）に遷移できる | Human | | admin |
| 4 | `i102_admin` で問題管理画面から「新規作成」で問題を1件作成→編集→削除 | 作成/編集/削除がいずれも成功する（403 やエラーが出ない） | Human | | admin CRUD |
| 5 | （任意）`i102_user` でログイン後、ブラウザ devtools の Console で `fetch('/api/problems/').then(r=>console.log(r.status))` を実行 | `403` が表示される | Human | | 任意。BE TC-AUTO-01（自動）で担保済み |
| 6 | `frontend/src/components/OrgAdminRoute.tsx` の判定条件を確認 | `user.role !== 'admin'` で権限エラーを返す（`is_staff`/`is_superuser` 判定を使っていない） | Claude | OK | :33 `if (user.role !== 'admin')`。is_staff はコメントのみ |
| 7 | `frontend/src/App.tsx` の `quiz-management` ルートを確認 | `<OrgAdminRoute>` でラップされている（`<AdminRoute>` ではない） | Claude | OK | :79 `<OrgAdminRoute><QuizManagement /></OrgAdminRoute>` |
| 8 | `frontend/src/components/Layout.tsx` の menuItems を確認 | 「問題管理」項目が `isOrgAdmin ? [...]` ブロック内にある | Claude | OK | :76-77 isOrgAdmin ブロック内 |
| 9 | `backend/problems/views.py` の `ProblemViewSet` を確認 | `permission_classes = [permissions.IsAuthenticated, IsOrgAdmin]` になっている | Claude | OK | :152 |
| 10 | `backend/accounts/management/commands/seed_e2e.py` を確認 | 非admin `e2e_user_c@example.com`（`role='user'`・org_a）が追加されている | Claude | OK | :73-80 |

備考:
- No.1-5 はブラウザ操作・API 挙動の目視確認のため Human 実施。No.5 の 403 はサーバー挙動で E2E/自動テストでも担保する（二重確認）。
- No.6-10 はファイル内容確認のため Claude が `/test` 実行時に自動確認・記入する。
