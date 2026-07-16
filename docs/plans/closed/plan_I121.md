# plan_I121: frontend 依存監査の緊急是正 — npm audit fix（非破壊）で critical 解消・CI ブロック解除

## 基本情報
- **計画書ID**: plan_I121
- **関連イシュー**: #223（docs/issues/open/I121.md）
- **Draft PR**: #224
- **作成根拠資料**: docs/issues/open/I121.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I121_review.md
- **作成日**: 2026-07-16

## 1. 背景/目的

### 原因の概要
リポジトリを一切変更していないのに、npm の脆弱性データベースに新しい報告（websocket-driver の critical 2 件・ws の high 1 件）が公開されたことで、CI の監査チェックが不合格になり、**すべての PR がマージできない状態**になっている。

### 詳細な原因分析
- CI「Frontend Lint & Security」ジョブ（`.github/workflows/ci.yml:123-125`）の `npm audit --audit-level=critical --omit=dev` が exit 1 で fail（frontend 無変更の PR #219 でも fail を実証・2026-07-16）。
- develop の定期監査（dependency-audit.yml）も 2026-07-15 22:48 に fail し #220 が自動起票済み。
- 対象パッケージは CRA（react-scripts 5.0.1）のツールチェーン推移依存。react-scripts は package.json の `dependencies` 側にあるため `--omit=dev` でも監査対象。
- ゲートは critical のみ fail 対象のため、**fail の直接原因は websocket-driver（critical）のみ**。

### 目的
`npm audit fix`（非破壊・semver 互換範囲のロックファイル更新のみ）を frontend に適用し、critical を 0 件にして CI ブロックを解除する。

## 2. 調査結果（2026-07-16 実測・すべて本セッションで実走）

### 環境前提確認
- node v24.14.1 / npm 11.11.0（ホスト WSL2）。frontend/node_modules インストール済み。
- CI ゲート実物: `.github/workflows/ci.yml:123-125`（`npm audit --audit-level=critical --omit=dev`・working-directory: frontend）— 本計画では**変更しない**。

### 現状監査（CI ゲート同一条件）
- `npm audit --audit-level=critical --omit=dev` → **exit 1**・**25 件（critical 1 / high 7 / moderate 7 / low 10）**。イシュー記載と一致。
- critical = websocket-driver（GHSA-mp7j-qc5w-4988 / GHSA-xv26-6w52-cph6）。ws（GHSA-96hv-2xvq-fx4p・high）も「fix available via `npm audit fix`」表記。

### fix の模擬適用（scratchpad コピーで実証・リポジトリ無改変）
package.json / package-lock.json を scratchpad にコピーし `npm audit fix --package-lock-only` を実適用して確認:
- **更新内容**: 17 パッケージの semver 互換更新（add 1 / remove 1 / change 15）。主要: websocket-driver 0.7.4→0.7.5、ws 7.5.10→7.5.12、@babel/core 7.28.0→7.29.7、js-yaml・form-data・http-proxy-middleware・launch-editor 等。
- **package.json は無変更**（diff で確認）→ `overrides` 追記は**不要**（既存 overrides: nth-check / postcss / underscore はそのまま）。
- **適用後の残存: 18 件（low 9 / moderate 4 / high 5 / critical 0）**。2 回目の fix 実行でも変化なし（収束確認済み）。
- **CI ゲート同一条件で exit 0** を確認（gate_exit=0）。
- **対象 3 GHSA は監査結果から消失**（`npm audit --omit=dev --json` に 0 ヒット。修正前は 3 ヒット＝TC の false-green でないことも同時に確認済み）。

### 残存 18 件のスコープ外根拠（AC の実測記録）
| 残存指摘 | 深刻度 | 理由 |
|---------|--------|------|
| serialize-javascript 系（css-minimizer-webpack-plugin / rollup-plugin-terser / workbox 経由で react-scripts に到達） | high | `npm audit fix --force`（react-scripts@0.0.0 への破壊的変更）でしか解消不可。ビルド時のみ使用・本番バンドル露出なし |
| uuid / sockjs / webpack-dev-server 系 | moderate | 同上（--force 必須）。dev サーバ用途・本番露出なし |
| @tootallnate/once / http-proxy-agent / jsdom / jest 系 | low | npm audit は「fix available」と表示するが、実際は 2 回適用しても解消されない（依存制約上、非破壊では到達不能。実測で収束確認済み）。テスト実行時のみ使用 |

いずれも react-scripts ツールチェーン固定に起因し、ゲート（critical）非対象。根治は CRA→Vite 移行（別の中期イシュー・2026-07-15 ユーザー決定どおり）。

### 既存テストの事前実行（ベースライン）
- frontend Jest: `npm test -- --watchAll=false` → **2 suites / 7 tests 全 PASS**（49.9s・exit 0）。既存の React act() 警告あり（pre-existing・合否に影響なし）。
- backend: 変更なしのため対象外（lockfile のみの変更で backend に波及しない）。

## 3. 受け入れ条件（イシューの AC を転記・実現可能性は上記実測で確認済み）
- [ ] `npm audit --audit-level=critical --omit=dev` が exit 0（CI ゲートと同一条件・critical 0 件）→ TC-01
- [ ] websocket-driver（GHSA-mp7j-qc5w-4988 / GHSA-xv26-6w52-cph6）と ws（GHSA-96hv-2xvq-fx4p）が監査結果から消えている → TC-02
- [ ] package.json の依存宣言に破壊的変更がない（react-scripts 5.0.1 不変・audit fix --force 不使用）→ TC-03
- [ ] CI 全ジョブ（Frontend Lint & Security 含む）が green → M1/M2
- [ ] マージ後に #220 をクローズ（`gh issue close 220 --comment "I121 で対応済み"`）→ M3
- [x] （計画段階で確定）適用後の残存件数を計画書に実測記録 → 上記「残存 18 件のスコープ外根拠」に記録済み

## 4. 影響範囲
| 領域 | 影響 |
|------|------|
| Backend | なし |
| Frontend | package-lock.json のみ（semver 互換の推移依存更新 17 件）。package.json・ソースコードは無変更（模擬適用で実証済み） |
| DB | なし |
| Config/Infra | CI 定義・監査条件は変更しない |
| Docker | frontend/Dockerfile は `npm ci --only=production`（lockfile 準拠インストール）のため、更新後 lockfile が自動反映される。Dockerfile 自体の変更は不要。docker-compose の frontend-test は `npm install`（差分更新）で同様に追従 |

## 5. 変更点一覧
| ファイル | 変更内容 |
|---------|---------|
| frontend/package-lock.json | `npm audit fix` による semver 互換更新（17 パッケージ。websocket-driver 0.7.4→0.7.5・ws 7.5.10→7.5.12 ほか） |
| docs/issues/open/I121.md | 実測確定値の反映は不要（イシュー AC どおり本計画書に記録） |

package.json は変更しない（模擬適用で無変更を実証済み。変更が発生した場合は計画との不一致として停止・報告する）。

## 6. 実装手順

### 修正アプローチ
frontend で `npm audit fix`（`--force` なし）を 1 回実行し、package-lock.json の semver 互換更新のみで critical を解消する。模擬適用で結果（残存 18 件・ゲート exit 0・package.json 無変更）を実証済みのため、未知リスクは advisory DB のドリフト（実装時に新規 advisory が増えている可能性）のみ。

### ステップ1: npm audit fix の適用（唯一の変更ステップ）
- **修正方針**: 非破壊 fix で lockfile を更新し、node_modules も同時に同期させる（`npm audit fix` は install を伴うため追加操作不要）。
- 実行: `npm audit fix --prefix frontend`（`--force` は使わない。単体コマンド＝allowlist 一致のため `&&` 結合を使わない・plan review Warning 対応）
- 直後に変更ファイルが package-lock.json のみであることを確認する → TC-03 参照
- 万一 package.json に変更が出た場合・新規 critical が fix 不可で残る場合は**停止してユーザーへ報告**（計画との不一致）。

### ステップ2: 検証（ステップ1 完了が前提）
- 監査ゲート・GHSA 消失・非破壊性・回帰（Jest・build）を自動テスト文書の TC-01〜TC-05 で検証し、結果を docs/tests/open/I121_auto_test.md に記録する。

### ステップ3: コミット・プッシュ・CI 確認（ステップ2 完了が前提）
- lockfile をコミットし PR #224 へ push。CI 全ジョブの green を確認 → 手動テスト M1/M2 参照。

### ステップ4（マージ後）: #220 クローズ
- `gh issue close 220 --comment "I121 で対応済み"`（runbook の 2 段階運用 step 3）→ M3 参照。

## 7. テスト計画
- 自動: docs/tests/open/I121_auto_test.md（TC-01 ゲート exit 0 / TC-02 GHSA 不在 / TC-03 非破壊性 / TC-04 Jest 回帰 / TC-05 build）
- 手動: docs/tests/open/I121_manual_test.md（M1 CI green / M2 audit ステップログ / M3 #220 クローズ / M4 PR #219 の CI 復旧確認）
- TDD 相当の Red 状態は現状そのもの（TC-01: 現状 exit 1・TC-02: 現状 3 ヒット）で確認済み（false-green ではない）。

## 8. ロールバック
- lockfile 更新コミットの revert（`git revert <commit>`）→ `npm ci` で node_modules を旧状態に復元。データ・インフラ影響なし。

## 9. Risk & 回避策
| リスク | 回避策 |
|--------|--------|
| 計画時と実装時で advisory DB がドリフト（新規 advisory の追加で件数・fix 可否が変わる） | 実装ステップ1 の直前に `npm audit` を再実行し件数を確認。新規 critical が非破壊 fix 不可の場合は停止して報告（計画との不一致扱い） |
| semver 互換更新でもツールチェーンの挙動が変わる可能性 | TC-04（Jest 全件）・TC-05（本番 build）で回帰確認。模擬適用で更新対象 17 件が dev ツールチェーンのみであることを確認済み |
| npm バージョン差（ローカル 11.11.0 / CI）による fix 結果の差 | fix はローカルで実行し lockfile をコミットする方式のため CI は判定のみ（判定は lockfile + advisory DB で決定・runbook 記載）。差は生じない |
| レジストリ到達不可・一時障害 | リトライ。監査は package-lock.json とレジストリのみで判定されるため再現性あり |

## 10. セキュリティ・品質チェック（plan-issue 必須確認の記録）
- **セキュリティ影響**: 本計画はセキュリティを改善する側の変更（critical 1・high 2 件の advisory 解消）。コード変更なし・認証認可/入力検証/機密データの変更なし。
- **npm audit の重大度基準**: 修正対象 = critical（ゲート対象）＋非破壊で fix 可能な high（ws）。残存 high（serialize-javascript 系）は --force 必須・本番露出なしのためスコープ外（2026-07-15 ユーザー決定に基づく。根治は Vite 移行イシュー）。
- **P3（データ整合性）/ P5（運用設計）/ P8（コスト）影響なし**: DB・外部 API・非同期処理・新規インフラなし。
- **P6（性能・UX）影響なし**: UI・アプリコード変更なし。
- **P9（プライバシー）影響なし**: 個人情報・テナントデータを扱わない。
- **設計判断の明示**: 本計画の設計判断はすべてイシューに明記済み（非破壊 fix・--force 不使用・残存スコープ外・CI 条件不変）。**仮定で決めた項目はない**（package.json 無変更・残存 18 件は仮定ではなく模擬適用の実測）。

## 11. 承認ポイント
- [ ] `npm audit fix`（非破壊）のみで対応し、`--force` は使わない（模擬適用で critical 0・ゲート exit 0 を実証済み）
- [ ] 変更は frontend/package-lock.json 1 ファイルのみ（package.json 無変更を実証済み）
- [ ] 残存 18 件（high 5 / moderate 4 / low 9・critical 0）はスコープ外として許容（--force 必須または非破壊で到達不能・本番バンドル露出なし・根治は Vite 移行別イシュー）
- [ ] マージ後に #220 をクローズする（runbook step 3）

## レビュー結果
- [20260716_2021 判定: ✅ 完了](../../reviews/closed/I121_plan_review_20260716_2021.md)

## 完了情報
- **完了日時**: Fri Jul 17 01:05:46 JST 2026
- **対応者**: Claude Code
- **レビュー結果**: OK（plan review OK・code review OK・TC-01〜06 全 PASS・CI 全 6 ジョブ green）
