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
- 計画書 §6 ステップ1〜3 のとおり実装（2026-07-17）。fix 直前の再監査でドリフトなし（25 件・critical 1＝計画時と同一）を確認してから `npm audit fix --prefix frontend` を 1 回実行。変更は frontend/package-lock.json のみ（93 insertions / 52 deletions・package.json 無変更）。
- plan review: VERDICT OK（Warning 1 件＝ステップ1 の単体コマンド化は実装前に計画書へ反映済み）。code review: VERDICT OK・高リスク No・修正要指摘ゼロ（Low 1 件は plan review Info の再掲・対応不要判定）。

## テスト結果
- 自動: TC-01〜TC-06 **全 PASS**（実装時 2026-07-17・/test 再実行 2026-07-17 の 2 回とも同値）。ゲート exit 0・3 GHSA 消失（3→0）・非破壊性 4 項目 OK・Jest 2 suites / 7 tests PASS（ベースライン一致）・build exit 0・残存 18 件（critical 0・模擬適用予測と完全一致）。false-green 検証は計画時に実施済み（修正前状態で TC-01 exit 1・TC-02 3 ヒットを実測）。
- CI: PR #224 全 6 ジョブ green。ブロック原因の「Frontend Lint & Security」npm audit ステップは `18 vulnerabilities（critical 0）` で成功（M1/M2 OK）。
- 手動: M1/M2 OK（2026-07-17）。M3（#220 クローズ）・M4（PR #219 の CI 復旧確認）はマージ後実施。

## 計画との差分
- なし（変更ファイル・更新パッケージ・残存件数すべて計画書の模擬適用実測どおり）

## ロールバック
- lockfile 更新コミットの revert → `npm ci` で復元。データ・インフラ影響なし。
