# I121 レビュー: frontend 依存監査の緊急是正（npm audit fix 非破壊）

## 基本情報
- **対象計画書**: docs/plans/open/plan_I121.md
- **関連イシュー**: #223（docs/issues/open/I121.md）
- **Draft PR**: #224

## レビュー目的
- 変更が frontend/package-lock.json の semver 互換更新のみであること（package.json・ソースコード・CI 定義が無変更であること）
- `npm audit fix --force` が使われていないこと（react-scripts 5.0.1 不変）
- CI ゲート同一条件（`npm audit --audit-level=critical --omit=dev`）で exit 0 に回復していること
- 残存指摘（計画時実測 18 件・critical 0）のスコープ外根拠が計画書に実測記録されていること
- 回帰（Jest・本番 build）が計画時ベースライン（2 suites / 7 tests PASS）と一致すること

## 期待する成果
- 全 PR の CI ブロックが解除され、レビュー待ちの I113（PR #219）以降のイシューフローが再開できる
- 依存脆弱性ドリフト検知（I109 の仕組み）→ 是正イシュー → クローズ（#220）の 2 段階運用が一巡し、runbook どおり機能することが実証される

## 変更概要
- frontend で `npm audit fix`（非破壊）を実行し、package-lock.json の推移依存 17 件を semver 互換更新（websocket-driver 0.7.4→0.7.5・ws 7.5.10→7.5.12 ほか）。critical 0 件化で CI ゲートを回復。

## 変更点
- `frontend/package-lock.json`: semver 互換更新のみ（計画 6 ステップ1）
- コード・CI 定義・package.json: 変更なし（TC-03 で機械検証）

## 影響範囲
- Backend/DB/Config: なし
- Frontend: lockfile のみ（本番バンドルへの脆弱性露出は従来分析どおり 0 件のまま）
- Docker: frontend/Dockerfile は `npm ci`（lockfile 準拠）のため自動追従・定義変更なし

## 実装結果評価
（実装後に記入）

## テスト結果
（実装後に記入: TC-01〜TC-06 / M1〜M4）

## 計画との差分
（実装後に記入）

## ロールバック
- lockfile 更新コミットの revert → `npm ci` で復元。データ・インフラ影響なし。
