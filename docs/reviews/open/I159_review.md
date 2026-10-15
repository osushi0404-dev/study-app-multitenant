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
- （実装後に記入）

## テスト結果
- （実装後に記入）

## 計画との差分
- （実装後に記入）

## ロールバック
- 計画書 §8 のとおり（取り込み前 / 取り込み後 / develop 反映後の 3 段階）
