# I620 レビュー: 組織の管理者が 1 回だけ使える登録用リンクを発行し、パスキーの初回登録と再登録に使う

## 変更概要
- 組織の管理者の「メンバー管理」（一覧・ユーザー ID だけの作成・登録用リンクの発行と失効・パスキーの一覧と削除）と、リンクから開くパスキーの登録画面を足す。運営の編集画面と管理コマンドからも発行できるようにする。発行の時点で古いパスキーと refresh トークンを失効させる（simplejwt の失効の表を入れる）

## 変更点
- Backend: `RegistrationLink`（値は SHA-256 だけ・1 人に開いたリンクは 1 つ）とマイグレーション 0025・サービス `accounts/registration_links.py`（発行・失効・使用・管理者のパスキー削除）・権限 `IsOrgMemberManager`・`MemberViewSet`（`/api/members/`）・運営の 3 つの action（`/api/admin/users/{id}/…`）・公開の 2 つの API（`/api/auth/registration-links/options|complete/`）・管理コマンド `issue_registration_link`・`token_blacklist`・スロットル 2 つ・`UserSerializer`／`AdminUserSerializer` の `organization_is_individual`・パスキーの処理の切り出し（`build_registration_options`・`verify_and_create_passkey`）
- Frontend: メンバー管理 `pages/MemberManagement.tsx`・登録画面 `pages/PasskeySetup.tsx`・部品 `components/members/`（リンクの表示・確認・パスキーの一覧・操作のまとめ・追加・運営の欄）・`useMembers`／`useMemberCredentials`・`member.service.ts`・`AuthContext.completeRegistrationLink`・メニュー・ルート・設定のパスキーの欄の案内・`api.ts` の公開の画面・`qrcode.react` 4.2.0
- テスト: `accounts/tests/test_I620_registration_links.py`・Jest 5 ファイル・E2E `e2e/tests/registration-link.spec.ts`・経路の表とスロットルの設定の一覧

## 影響範囲
- Backend/Frontend/DB/Config: 計画書 3

## テスト結果
- 自動: `docs/tests/open/I620_auto_test.md` の結果のとおり（裏側 40 件・画面の関係 70 件・E2E 2 件が手元で通過。正は CI）
- 手動: test-gate で行う（implement では画面確認の 5 行を記録）

## 計画との差分
- あり（計画書の「計画変更記録」の implement の 7 行。どれも方式・範囲・受け入れ条件は変えない）

## ロールバック
- 計画書 7

## 自律判断の記録
- [plan] refresh トークンの失効の表（`token_blacklist`）を #501 から同梱する — 受け入れ条件「ログイン中の状態を切る」に公式の仕組みが要る。#501 の本文は入れる順を問わないとしている。ログアウトの例外の扱いと表の掃除は #501 に残す
- [plan] リンクの値は URL の `#token=` に入れ、DB は SHA-256 だけ — サーバーのログ・Referer に載せない・漏れても使えない形
- [plan] 範囲の外（ほかの組織・運営）は 404、範囲の中で対象にできない人（自分・無効）は 400 — 規約 §5 と、管理者に理由が分かること
- [plan] 運営の画面は `UserEdit.tsx` に部品を 1 つ足すだけ — 範囲を広げない
- [plan] 人の手動テストは置かない — 登録の処理は I619 で実機を確かめた同じもの。スマホでの QR の読み取りは手元のアプリ（localhost）に届かず確かめられないので、QR に入る値を TC-21 で確かめる
- [plan] 画面の配置と文言の案をユーザーに確かめた（2026-11-26・案のとおり）
- [plan-review] 計画レビューの Warning 4・Info 2 をすべて直した（TC-02 は 404・TC-21 は QR に入る値を確かめる・手動 No.5/No.8・R2・R7）。方式・範囲は変わらないので再レビューはしない — 計画変更記録のとおり
- [design-security-review] Blocker 0・Medium 2（M1: rotation 後の refresh も失効の対象か・M2: 画面のキャッシュのキーに見ている人）を必須の条件として計画書とテスト文書に入れた。Low 6 のうち 4 は受け入れ（retro で処遇を決める）・2 は必須の条件 — 方式・範囲・受け入れ条件は変わらないので計画レビューはやり直さない
- [implement] リンクの土台を `REGISTRATION_LINK_BASE_URL`（既定はパスキーを許す最初の画面）にした — 画面で確かめて、`FRONTEND_URL` と画面の origin がずれる環境では登録できないと分かったため
- [implement] `api.ts` の 401 でログイン画面へ移さない画面に登録画面を足した — ログイン前に通知の設定を読む既存の動きでリンクを開けなかったため
- [implement] 運営の欄は部品 `StaffCredentialsCard` にし、`AdminUserSerializer` に `organization_is_individual` を足した — 運営の画面に相手の組織の種類を知る手段が無かったため
- [implement] 画面の確認で、開発サーバーの通知（ソケット）が別のワークツリー（ポート 3000）につながり古いエラー表示が出ていた。確認の間は `routeWebSocket` でソケットを止めた（画面の動きそのものは正しく、配信されている JavaScript で確かめた）。手順書への反映は retro で決める
- [implement] 手元の E2E の全体で `settings.spec.ts` の TC-28 が並行のときだけ 1 回落ちた（単独では通過）。I620 は設定画面に触れていないので直さない。CI の結果で確かめる
- [implement] I619 の `test_tc01_register_options_requires_auth_and_recent_reauth` が 1 回落ちた（境目の秒の切り捨て・流し直しで通過）。I620 の範囲外。retro で扱いを決める
- [implement] `docker compose exec … npm install` の後に開発サーバーが依存を見失ったので、手順書の標準の起動（`up -d --build --renew-anon-volumes frontend`）で作り直した（`rm -rf` のキャッシュ消しは見張りが止めたので使わなかった）
- [implement] /simplify の指摘のうち直したもの: 公開の API の認証を外す・E004・本人確認の権限を mixin の 1 か所に・`select_related`・作成直後の集計の省略・登録画面の challenge の取り直しを失敗の後だけに・使っていない属性と型・`reauthHeaders` の共用・`get_serializer_class` の削除・テストの型と行の探し方
- [implement] /simplify の指摘のうち見送ったもの: パスキーの一覧・削除の確認・日付の整形を I619 の `PasskeysCard` と共通の部品に切り出す（I619 の部品を作り変えることになり範囲が広がる。retro で後続にするか決める）／本人確認のフックとダイアログの組をまとめるラッパー（同上）／`complete` のリンクを 1 回だけ引く形（challenge の消費を先にコミットする I619 の決まりを崩すので見送り）／自分のパスキーの一覧を本人確認のときだけ取る（ダイアログの表示が遅れるので見送り）／`can_manage_members` のように判定の結果を返す形（`organization_is_individual` は受け入れ条件 3 とテストで決めた値。共有の personal 組織の管理者は運営だけで、メンバー管理を開いても 403 になるだけ。retro で扱いを決める）／`IsOrgMemberManager` の 1 回の EXISTS

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
- [review-gate] コードレビュー（台帳の 1 周目）が HIGH（止める指摘 F1〜F3・いずれも Medium・delta）。fix-loop へ。敵対的レビューは基本レビューが OK になってから
STAGE_DONE: review-gate NEXT: fix-loop
- [fix-loop] F1〜F3 を診断メモの推奨案（各 案 A）で直した — 診断レビュー OK。F2 は /simplify で入れた使い回しを戻した
STAGE_DONE: fix-loop NEXT: review-gate
- [review-gate] 差分のレビュー OK（docs/reviews/I620_code_review_20261126_1434.md）・敵対的レビュー 1 周目 OK（未検証 0・Critical/High 0・docs/reviews/I620_adversarial_review_20261126_1445.md）
STAGE_DONE: review-gate NEXT: test-gate
- [test-gate] gate-check OK。Claude の手動テスト 13 項目のうち No.12（幅 360px でメンバーの表が横に流れず、文字が 1 文字ずつ折り返す）が NG → fix-loop。確かめ用に開発の DB に運営 i620_staff・個人利用 i620_solo を作った（パスワードは e2e_user_a のものを写した）
STAGE_DONE: test-gate NEXT: fix-loop
