# I102 手動テスト: 問題管理を組織管理者権限に限定

前提:
- 開発環境が稼働（`docker compose ps` で backend/frontend/db が Up）。
- 組織管理者（`role='admin'`）と一般ユーザー（`role='user'`）の2アカウントでログインできること。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | 一般ユーザー（`role='user'`）でログインし、サイドバーのメニューを確認 | メニューに「問題管理」項目が**表示されない**（「科目管理」も非表示・「ダッシュボード/学習統計/設定」は表示） | Human | | |
| 2 | 一般ユーザーのまま、URL に `/quiz-management` を直接入力して遷移 | 管理 UI に到達せず「このページにアクセスする権限がありません。管理者権限が必要です。」のエラーが表示される | Human | | |
| 3 | 組織管理者（`role='admin'`）でログインし、サイドバーを確認 | メニューに「問題管理」項目が**表示される** | Human | | |
| 4 | 組織管理者で「問題管理」に遷移し、問題の一覧表示・新規作成・編集・削除を実施 | 従来どおり一覧が表示され、作成/編集/削除が成功する（403 等のエラーが出ない） | Human | | |
| 5 | 一般ユーザーで `GET /api/problems/` を直接呼ぶ（ブラウザ devtools / curl 相当。認証トークン付き） | HTTP **403**（`{"detail": "管理者権限が必要です"}` 相当）が返る | Human | | API 直叩き確認。E2E/TC-AUTO でも自動検証 |
| 6 | `frontend/src/components/OrgAdminRoute.tsx` の判定条件を確認 | `user.role !== 'admin'` で権限エラーを返す（`is_staff`/`is_superuser` 判定を使っていない） | Claude | | ファイル内容確認 |
| 7 | `frontend/src/App.tsx` の `quiz-management` ルートを確認 | `<OrgAdminRoute>` でラップされている（`<AdminRoute>` ではない） | Claude | | ファイル内容確認 |
| 8 | `frontend/src/components/Layout.tsx` の menuItems を確認 | 「問題管理」項目が `isOrgAdmin ? [...]` ブロック内にある | Claude | | ファイル内容確認 |
| 9 | `backend/problems/views.py` の `ProblemViewSet` を確認 | `permission_classes = [permissions.IsAuthenticated, IsOrgAdmin]` になっている | Claude | | ファイル内容確認 |
| 10 | `backend/accounts/management/commands/seed_e2e.py` を確認 | 非admin `e2e_user_c@example.com`（`role='user'`・org_a）が追加されている | Claude | | ファイル内容確認 |

備考:
- No.1-5 はブラウザ操作・API 挙動の目視確認のため Human 実施。No.5 の 403 はサーバー挙動で E2E/自動テストでも担保する（二重確認）。
- No.6-10 はファイル内容確認のため Claude が `/test` 実行時に自動確認・記入する。
