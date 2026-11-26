# I636 レビュー: 登録用リンクとメンバー管理のレビューの残りを直す

## 変更概要
- I620 のレビューの残り（敵対的レビューの M1・M2・L、コードレビューの F4〜F12）を直し、確かめ用の初期データ・通知の場所（上の中央）・settings.spec の不安定さを整える（計画書 `docs/plans/open/plan_I636.md`）

## 変更点
- 裏側: パスキー削除の形の違う ID を 404 に（`views.py`）／メンバーの作成を `registration_links.create_member` に移し、重複の競合を 400 に／`User.can_manage_members`（組織の条件は `invitable()` の 1 か所）を権限と `UserSerializer` で使い、`organization_is_individual` を `UserSerializer` から外した／`MemberCreateSerializer` のエラー文を日本語に／`seed_e2e` に `e2e_staff`・`e2e_solo` を足し、DEBUG が偽なら止める
- テスト: complete の側の使えないリンク（4 種・1 回目の確かめの後に使えなくなる場合・引き直しを外した注入）／同時使用（待ち合わせで順序を作る・鍵を外した注入）／作成の競合とエラー文／設定の読み込み（`load_dotenv` を止めた子のプロセス）／メンバー管理を使える条件（8 通り）と初期データ
- 画面: 通知を上の中央に（最大幅 `min(350px, calc(100vw - 128px))`）／メニューと画面の入口を `can_manage_members` で／登録画面は押したときの取り直しが 400 なら使えないリンクの表示に／リンクのダイアログは最後の値を閉じ終わりまで持つ／追加の流れの発行中は［メンバーを追加］とその人の［登録用リンク］を押せない／表の枠に `role="region"`・名前・`tabIndex`、ユーザー ID のセルは中の `Box` で最小の幅、操作の並びは `wrap` と `role="group"`
- E2E: TC-30 は表の枠を名前で探し、3 つのボタンの行を 360px で確かめ、通知が出ている間に重ならずにログアウトする／TC-28 は保存の応答を待ってから読み直す
- 手順書: `frontend-verify.md` §5 に `e2e_staff`・`e2e_solo` を足し、`e2e_user_b` の役割を直した

## 影響範囲
- Backend/Frontend/DB/Config: accounts（モデルの判定・権限・シリアライザ・ビュー・サービス・初期データ）・OpenAPI・画面（通知・メニュー・メンバー管理・登録画面）・E2E。DB と設定の変更は無い

## テスト結果
- 自動（implement・手元）: backend `accounts`・OpenAPI の契約・組織の境界の 271 件が通過。frontend の関係する 8 ファイル 69 件・型チェック・リントが通過。E2E 全体（`--retries=0`）が 21 件通過・`--repeat-each=2` で 42 件通過（TC-28 は再現せず）。失敗の注入: 削除の ID・作成の競合・エラー文・メニュー・登録画面・二度押し・表の並びのテストは直す前に落ちることを確かめた。行の鍵・鍵つきの引き直しを外した版のテストは 200 になる。ダイアログの直しを外すと TC-09 が落ち、通知を右上に戻すと TC-30 が落ちることを確かめてから戻した
- 手動: （test-gate で書く）

## 計画との差分
- なし

## ロールバック
- PR を revert する（マイグレーションは無い）

## 自律判断の記録
<!-- 各段階が、止めずに自分で決めたことを `- [段階] 決めたこと — 理由` で足す。段階の結線の行（STAGE_DONE:）はこのファイルの末尾に足す -->
- [plan] メンバー管理を使える判定を `Organization.is_invitable`・`User.can_manage_members`（モデルの property）に置き、`UserSerializer` の `organization_is_individual` を外す — `permissions.py` に置くと import が循環する。画面と API の判定を 1 つにする
- [plan] 同時使用のテストは、鍵の中の処理に待ち合わせ（2 秒で時間切れ）を入れて順序を作り、行の鍵を外した版のテストも CI で流す — 順序に頼らず、鍵を外すと必ず落ちる形にするため
- [plan] 通知の最大幅を `min(350px, calc(100vw - 128px))` にする — 幅 360px で上のバーの左右のボタンに重ねないため（イシューの「重なるなら最大幅を抑える」の具体化）
- [plan] 表の枠に `role="region"` と読み上げの名前・`tabIndex={0}` を付ける — E2E を MUI の内部のクラス名に頼らせず、横に流れる枠をキーボードで動かせるようにするため
- [plan-review] 計画レビューの Warning 3 件（TC-03 の前提・TC-09 の期待値・TC-14 の書き戻し）はテスト文書の具体化だけなので直して再レビューしない — 方式・範囲・受け入れ条件を変えないため
- [design-security-review] Medium 1 件（`seed_e2e` に既知のパスワードの運営を足す）は、DEBUG が偽ならコマンド全体を止める防御を計画に足して解消扱いにした。Low の運営の API の 404 もテストに足した — Blocker は無く、要件・UI を変えない防御とテストの追記だけのため
- [implement] 画面の確かめは Playwright MCP（`localhost:3020`）で、ログイン直後の通知（上の中央・幅 360px でメニューに重ならない）と `/members`（表の枠 720/296・Tab で枠に入る・ボタン 44px・コンソールのエラー 0）を見た。開いた画面に、作り直す前の「Module not found」の開発用の表示（webpack の overlay）が残ったので、取り除いてから確かめた — 配っている bundle に依存が入っていること（`qrcode.react` を含む）と、frontend のログの「Compiled successfully」を確かめた。E2E（`frontend:3000`）では出ていない
- [implement] /simplify の 4 観点の指摘のうち、組織の条件を 1 か所にする・ダイアログが最後の値を自分で持つ・消したテストの墓標のコメントを消す、の 3 つを採った。URL の正規表現を締める（イシューで view で直すと決めている）・発行の 2 系統を 1 つにする（計画の範囲を超える作り直し）・事前の重複の確認を消す（普通の重複を競合の扱いに寄せることになる）・待ち合わせの時間を縮める（CI で 2 本目が遅れると鍵を外した注入のテストが不安定になる）・テスト全体のパスワードのハッシュを軽くする（差分の外）は採らなかった — 振る舞い・範囲を変えないため
- [implement] `react-scripts build` は手元で流さず、型チェック（`tsc --noEmit`）・リントで代えた。ビルドは CI が流す — 手元のビルドは `frontend/build` を作るだけで、型と依存の誤りは型チェックと開発サーバーの「Compiled successfully」で見ている
- [review-gate] 基本レビューは OK（Low 3 件・止める指摘なし。台帳に残し retro へ）。高リスクなので敵対的レビューを 1 周流し、V1〜V4 とも確認済みで OK。敵対的レビューの Low（`UserSerializer` の `can_manage_members` が `exists()` の問い合わせを 1 回足す）は直さず retro に回す — 止める基準に当たらず、OK の周の後に差分を足さないため
- [test-gate] 手動テスト No.2（E2E 全体の 3 回）を NG として fix-loop に回す。TC-28 の落ち方の原因（StrictMode で 2 回走る設定の読み込みの、遅れた応答が入力を戻す）が `Settings.tsx` にあり、計画の対象の外なので、fix-loop で計画変更記録と計画レビューを通してから直す — AC13 の未達で、原因が特定できたため（計画 §4-13 の「原因が分かれば直す」）
- [test-gate] TC-30 の 1 件の落ち方（ログイン直後の 401 で、画面の更新の宛先 `/api/auth/token/refresh/` が裏側の `/api/auth/refresh/` と食い違って 404 → ログアウト）は I636 の変更ではないので、このイシューでは直さず retro で別のイシューにする — 前からある食い違いで、直すと認証の作りに触れ、I636 の範囲を超えるため
- [test-gate] No.3〜No.6（画面）は fix-loop の後の test-gate でまとめて行う — Claude の分に NG があれば fix-loop に回す決まりで、直した後の HEAD で確かめ直すことになるため
- [fix-loop] 設定画面の読み込みの効果に後片付けを付ける案（診断メモの案 A）で直した。計画変更記録に書いて計画レビュー（`docs/reviews/I636_plan_review_20261127_0354.md`・Blocker なし）を通してから直した — React の公式の形で変更が小さく、TanStack Query への移行（案 B）は範囲を超えるため。計画レビューの Warning（計画本文の §4-4・§4-7・V1 と TC-11 の書き方が変更記録に追いついていない）も直した

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: fix-loop
