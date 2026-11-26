# I636 レビュー: 登録用リンクとメンバー管理のレビューの残りを直す

## 変更概要
- I620 のレビューの残り（敵対的レビューの M1・M2・L、コードレビューの F4〜F12）を直し、確かめ用の初期データ・通知の場所（上の中央）・settings.spec の不安定さを整える（計画書 `docs/plans/open/plan_I636.md`）

## 変更点
- （実装後に書く）

## 影響範囲
- Backend/Frontend/DB/Config: accounts（モデルの判定・権限・シリアライザ・ビュー・サービス・初期データ）・OpenAPI・画面（通知・メニュー・メンバー管理・登録画面）・E2E。DB と設定の変更は無い

## テスト結果
- 自動: （実装後に書く）
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

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
