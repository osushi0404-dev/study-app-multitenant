# I159 レビュー: frontend 依存の critical 脆弱性（proxy-addr / shell-quote）を npm audit fix で解消

## 基本情報
- **対象計画書**: docs/plans/open/plan_I159.md
- **関連イシュー**: #276（docs/issues/open/I159.md）
- **Draft PR**: #277（取り込み先: PR #269・I151）

## レビュー目的
- 変更が frontend/package-lock.json の範囲内更新のみであること（package.json・ソースコード・CI 定義が無変更・追加/削除/メジャー更新なし）
- `npm audit fix --force` が使われていないこと（react-scripts 5.0.1 不変）
- CI ゲート同一条件（`npm audit --audit-level=critical --omit=dev`）で exit 0 に戻っていること
- 対象 3 advisory（GHSA-jqcg-44mw-7w3h / GHSA-395f-4hp3-45gv / GHSA-pqg4-j6r4-53mv）が消え、proxy-addr ≥ 2.0.8・shell-quote ≥ 1.11.0 になっていること
- 本番バンドルに入る更新（axios 1.17.0→1.20.0・react-router-dom 6.30.4→6.30.6 等）で回帰がないこと（Jest・型チェック・ESLint・ビルド・E2E）
- ユーザー決定のマージ経路どおり、I151 ブランチへの取り込み後に PR #269 の 6 チェックがすべて SUCCESS であること

## 期待する成果
- I151 と本イシューの相互待ちが解け、I151（PR #269）を含む全 PR の CI が通る状態に戻る
- frontend の定期監査イシュー #220 がクローズされる

## 変更概要
- frontend で `npm audit fix`（`--force` なし）を実行し、package-lock.json の 34 パッケージを範囲内更新（proxy-addr 2.0.7→2.0.8・shell-quote 1.8.4→1.12.0・axios 1.17.0→1.20.0・react-router-dom 6.30.4→6.30.6 ほか）。critical 0 件で CI ゲートを回復。

## 変更点
- `frontend/package-lock.json`: 範囲内更新のみ（計画 §6 ステップ2）。模擬適用との差は qs 6.16.1（計画時 6.16.0）のみ
- package.json・ソースコード・CI 定義: 変更なし（TC-04・TC-05 で機械検証）

## 影響範囲
- Backend/DB/Config: なし
- Frontend: lockfile のみ
- Docker: 定義変更なし（compose の frontend は `-V` 付きの再作成で反映）

## 実装結果評価
- 計画 §6 ステップ1〜5 を実施（2026-10-15）。再監査でドリフトなし（critical 2・total 85）を確認後、`npm audit fix --prefix frontend` を 1 回実行。I159 ブランチ（fa3347d）を I151 ブランチへ `--no-ff` で取り込み（729dfbd）・衝突なし。
- ステップ6（開発サーバー）: ホストの `npm start` でコンパイル成功まで確認。画面表示は M4a〜M4c（Claude 実施・2026-10-15 ユーザー合意で Human から変更）で確認する。

## テスト結果
- 自動: TC-00〜TC-10 全 PASS（詳細は I159_auto_test.md）
- CI: PR #277 は Backend Lint & Security のみ pip-audit で FAILURE（既知）・他 5 チェック SUCCESS（M1）。PR #269 は取り込み後 6 チェックすべて SUCCESS（M2・AC-4）
- 手動: M1/M2 OK・M3 一部実施（curl 不許可）・M4a/M4b/M4c OK（M4c の Console エラー 6 件は修正前と完全同一の既存挙動・/login のみ）・M5/M6 は #269 マージ後

## 計画との差分
- qs の解決版が 6.16.1（計画時の模擬適用は 6.16.0）。模擬適用後に公開されたパッチ版で範囲内。TC-05 の許容範囲として記録
- 計画 §6 ステップ5 に「#269 マージ直前に I159 ブランチの最新を再取り込み」を補足（手順の明確化のみ）

## code-review 指摘への対応（2026-10-15・1 回目 VERDICT: HIGH）
- High（AC-6 画面表示未確認）: M4 を Claude 実施（M4a CSS 同一性・M4b CI E2E・M4c 手元 Docker＋Playwright）に変更して実施し OK
- High（omission-lint）: auto_test の TC-02 スクリプトが `grep -q` を fenced ブロック内に含んでいたため。文字列検索を監査 JSON の構造照合（`$S/tc02.js`）に書き換え、テンプレート準拠の「決定論ゲート（自動実走）」節（自動実走ゲートなし）を追加。omission_lint 関数で修正前 HIGH・修正後 OK、TC-02 の失敗注入（修正前 exit 1／修正後 exit 0）を再実測
- 1 回目のレビューは PR #277 単体の既知 CI 失敗（pip-audit）でスクリプトの CI 確認が止まるため、PR を持たない一時ブランチで実行（CI の根拠は合流 PR #269 の 6 チェック全 SUCCESS）。2 回目も同様

## ロールバック
- 計画書 §8 のとおり（取り込み前 / 取り込み後 / develop 反映後の 3 段階）
