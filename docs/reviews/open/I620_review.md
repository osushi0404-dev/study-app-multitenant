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
- 手動: Claude の 13 項目すべて OK（No.12 は 1 回 NG → fix-loop で直して再確認）・人の分は無し。画面確認 13 行（`docs/tests/open/I620_manual_test.md`）
- CI: 2 回目の差分のレビューの時点（f90f78c5）で全ジョブ成功（backend・frontend・API の型・ハーネス・E2E）

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
- [retro] 台帳の残り: F4〜F12（Low・アプリ本体）と敵対的レビューの Medium 2 件・Low 1 件 → #636（I636）。一覧（docs/reviews/backlog/）に回す行は 0 件
- [retro] 改善案の振り分け: 360px の配置の E2E → #630 に同梱／パスキーの部品の共通化と I619 の秒の境目のテスト → #629 に同梱／開発サーバーのソケット → #500 に同梱／確かめ用の初期データ・通知の重なり・settings.spec の不安定さ → #636／見張りの承認・/simplify の不具合・設計ルール昇格 → 見送り（理由は振り返り）
- [retro] 残余リスクの処遇を計画書に書いた（L1・L2・L4・L5 受け入れ・L3・L6・M1・M2 対処済み・敵対的の Medium 2 件は #636）

## 振り返り

### かんたんなまとめ

#### 良かった点
- 画面の配置と文言を、計画レビューの前に案（画面の見本）で 1 回だけ確かめた（理由: 決まっていない画面の文言をあとで直す手戻りが無かった）
- 実装の途中で画面を実際に動かして、テストでは見つからない不具合を 2 つ見つけた（リンクの URL が画面のポートとずれる・ログイン前の画面がログイン画面へ飛ばされる）（理由: レビューより前に直せた）
- 大事な守り（本人確認・組織の絞り込み・失効・同時使用）のテストは、守りを一時的に外して「落ちる」ことを確かめた（理由: 見せかけの合格を防げた）

#### 今回の問題への直接の対処
- レビューで中程度の指摘が 3 件出た（追加した人が今のページに無いとリンクが出ない・登録画面で 5 分を過ぎると最初の登録が失敗する・設定が空だと起動できない）。2 件目は、整理の段階（/simplify）の「無駄を減らす」提案を採ったことで生まれた。→ 3 件とも fix-loop で直した。/simplify の提案でも、期限のある値の使い回しは採らないと記録に書いた
- 手動テストで、幅 360px のメンバーの表が崩れていた（文字が 1 文字ずつ縦に折り返す）。画面のテストでは大きさを測れず、E2E も広い画面でしか見ていなかった。→ 表を横に流す形に直し、E2E に幅 360px の確かめを足した
- レビューで止めなかった軽い指摘 9 件と、敵対的レビューの中程度 2 件・軽い 1 件、確かめ用の初期データの不足、通知がメニューに重なる件、E2E の不安定さ → 後続のイシュー I636（#636）にまとめた

#### 同じ問題を次回から防ぐ改善
- 幅の狭い画面での崩れが、I619 に続いて 2 回目だった。新しい画面を足すときに、狭い幅で崩れないことを E2E で確かめる決まりが無かったため。→ 全画面の押す的のイシュー #630 に、「各画面を幅 360px でも開き、はみ出し・ボタンの縦伸び・表の横流しを E2E で確かめる」を同梱した
- パスキーの一覧・削除の確認・日付の整形が、設定画面とメンバー管理で重なっている。I619 の部品を作り変えることになるので今回は見送った。→ I619 の後続 #629 に同梱した（I619 のテストの秒の境目の不安定さも同じく）
- 画面の確認のとき、別のワークツリーの開発サーバーのエラー表示が出て時間を取られた。→ 画面の作りの移行 #500 に同梱した

#### 見送ったもの（理由つき）
- 見張りが、コンテナの中の読むだけのコマンドでも承認を求めた件（ユーザーから 2 回質問があった）: 3 回のうち 1 回はテストで確かめれば済む進め方の問題、2 回は見張りが正しかった。秘密の値の表示は取り戻せないので、見張りは緩めない。確かめ用の利用者を手で作る必要は I636 で無くす
- /simplify の提案で不具合が入った件: 直後のレビューで止まり、手戻りは 1 回の修正で済んだ。手順を足すほどではない
- セキュリティの設計レビューの気づき（ローテーション後のトークンの記録）を、確認の観点に足すこと: 今回の技術に固有で、ほかのイシューで繰り返す形ではない

### 詳細版

#### 良かった点
- grill-me の後、/plan-issue の中で画面の案（AskUserQuestion の見本）を 1 回だけ確かめ、UI の手戻りが無かった
- implement の画面確認（Playwright MCP）で、`FRONTEND_URL` と画面の origin のずれ・`api.ts` の 401 の扱いによるリダイレクトを見つけ、レビュー前に直した
- 否定の決定論のテスト（TC-01・03・04・05・07・08）に失敗の注入を行った

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | 予期しない問題 | /simplify の効率の指摘で、期限のある challenge を使い回した（F2）。発行を描画に結び付けた（F1）。空でありうる一覧の先頭を設定の読み込みで取った（F3） | fix-loop で直した（診断メモ `docs/reviews/I620_fix_diagnosis_20261126_1430.md`）。再発防止は auto_test の記録 |
| C2 | モダン開発 | MUI の表が狭い幅で列を縮める既定の動きを考えていなかった（No.12） | fix-loop で `minWidth` と折り返さない指定・E2E の 360px の確かめ（`docs/reviews/I620_fix_diagnosis_20261126_1520.md`） |
| C3 | ベストプラクティス | レビューの止める基準に当たらない指摘・敵対的レビューの上限の後の Medium・確かめ用の初期データの不足 | 後続 I636（#636）に集約 |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | スキル・規約 | 新しい画面の狭い幅の配置を E2E で確かめる決まりが無い（I619 No.10 に続き 2 回目） | 全画面の配置の E2E に、幅 360px のはみ出し・ボタンの縦伸び・表の横流しを入れる（#630 に同梱） | `e2e/tests/`・`docs/runbooks/ux-rules.md` §6 |
| P2 | ベストプラクティス | パスキーの一覧・削除の確認・日付の整形・本人確認の配線が画面ごとに重なる | 部品と関数に切り出す。境目の秒のテストは時刻を固定（#629 に同梱） | `frontend/src/components/settings/`・`components/members/`・`utils/`・`backend/accounts/tests/test_I619_passkeys.py` |
| P3 | 予期しない問題 | 開発サーバーのソケットが別のワークツリーのポートにつながる | 移行先の開発サーバーでソケットの接続先を画面と同じ origin にする（#500 に同梱） | `frontend/`・`docker-compose.yml`・`docs/runbooks/frontend-verify.md` §8 |

#### 観点ごとの確認
- 成果: 受け入れ条件 1〜17 を満たした（自動テスト・E2E・Claude の手動テスト 13 項目）
- プロセス: grill-me 2 回（ユーザーは BP に一任）→ 画面の案の確認 → plan-review（HIGHRISK）→ design-security-review → implement → review-gate（F1〜F3）→ fix-loop → review-gate・敵対的 1 周目 OK → test-gate（No.12 NG）→ fix-loop → review-gate・敵対的 2 周目 OK → test-gate OK
- コミュニケーション: ユーザーから承認画面について 3 回質問があった。予告していなかった 1 回目の反省を受けて、以降は予告した。3 回目は私の書き方のミス（`.env` を含めた）
- 技術選択: simplejwt の公式の失効の表を #501 から同梱（#501 にコメント済み）。リンクの値は `#` の後ろ・SHA-256。BP に沿っている
- ドキュメント: 計画書の API の表・テスト文書の期待値が、実装とレビューでそのまま使えた
- セキュリティ: 残余リスクは計画書の「残余リスク処遇」で決めた（High 以上は無し）
- 設計ルール昇格: 見送り（上の理由）
- 指示ファイルメンテナンス: plan-reviewer / code-reviewer への追加は無し（P1 は E2E の決定論で守る方が先）

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
- [fix-loop] No.12 を診断メモの案 A（表に最小の幅・折り返さない・E2E に 360px の確かめ）で直した — 診断レビュー OK。カードの並びへの切り替え（案 B）は了承した画面の配置を変えるので採らない。E2E の通知の重なりは待ってからメニューを開く形にした
STAGE_DONE: fix-loop NEXT: review-gate
- [review-gate] 差分のレビュー OK（docs/reviews/I620_code_review_20261126_1521.md）・敵対的レビュー 2 周目 OK（未検証 0・Critical/High 0・docs/reviews/I620_adversarial_review_20261126_1529.md）。通算 2 周を使い切った
STAGE_DONE: review-gate NEXT: test-gate
- [test-gate] gate-check OK・No.12 を再確認して OK。check-frontend-evidence・check-manual-test-executor とも合格。人の手動テストの項目は無い（計画 6 の理由）
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
