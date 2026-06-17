# plan_I061: フロントエンド依存脆弱性の是正（npm audit critical/high 解消）

## 基本情報
- **計画書ID**: plan_I061
- **関連イシュー**: #126
- **Draft PR**: #127
- **作成根拠資料**: docs/issues/open/I061.md（設計確認メモ /grill-me + plan-issue 精密監査で補正済み）
- **実装後評価**: （未作成）
- **作成日**: 2026-06-13

---

## 1. 背景/目的

`frontend` の `npm audit --audit-level=critical --omit=dev` が **exit 1**（critical `shell-quote@1.8.3` 残存）。CI `Frontend Lint & Security` が hard fail し、develop ベースの全 PR（I060=PR #125 含む）が緑にできない。`frontend/package-lock.json` は develop と同一で、本問題は時限式 advisory 公開により表面化したもの（I060 とは無関係）。

本イシューは **react-scripts を壊さずに直せる脆弱性（critical 1 + クリーン high 6）を是正**して CI を緑化する。react-scripts 5.0.1 に固着する high 5件は `--force`（`react-scripts@0.0.0` 破壊）を要するため risk-accept し、根拠を残す（CRA 移行は別イシュー）。

---

## 2. 調査結果（精密監査・実体突き合わせ）

### `npm audit --omit=dev --json` 分類（high+critical = 12 パッケージ）
| 分類 | パッケージ | fixAvailable | 本イシューでの扱い |
|------|-----------|--------------|-------------------|
| critical | `shell-quote` 1.1.0–1.8.3 | audit fix（非 --force） | **是正** |
| high(クリーン) | `axios` 1.0.0–1.15.2 / `fast-uri` ≤3.1.1 / `underscore` ≤1.13.7 / `@babel/plugin-transform-modules-systemjs` 7.12.0–7.29.0 / `jsonpath` * / `bfj` 7.1.0–9.1.2 | audit fix（非 --force） | **是正** |
| high(react-scripts 固着) | `workbox-webpack-plugin` / `workbox-build` / `serialize-javascript` / `rollup-plugin-terser` / `react-scripts` 本体 | `react-scripts@0.0.0`（MAJOR/破壊）のみ | **risk-accept** |

### ベースライン（修正前・実測）
- `npm audit --audit-level=critical --omit=dev` → **exit 1**（critical=1）＝CI 赤を再現
- サマリ: `{critical:1, high:11, moderate:9, low:9}`（high 11 のうち 6 がクリーン、5 が react-scripts 固着）

### 実体
- `frontend/package.json`: `axios` は **直接依存 `^1.6.7`**（脆弱範囲 ≤1.15.2 に該当）。利用箇所6ファイル: `src/services/api.ts` / `src/services/auth.service.ts` / `src/services/dashboard.service.ts` / `src/services/quiz.service.ts` / `src/pages/PasswordReset.tsx` / `src/pages/Settings.tsx`
- 既存 `overrides`: `nth-check`(>=2.0.1) / `postcss`(>=8.4.31)（＝推移的セキュリティ修正に overrides を使う前例あり）
- `react-scripts` `5.0.1`（固定）。`fast-uri` は ajv 経由のビルド時依存（ランタイム外）で 3.1.2 によりクリーン解消可
- scripts: `build=react-scripts build` / `test=react-scripts test` / 型チェックは CI の "Frontend Type Check" 相当（`tsc --noEmit`）
- `node_modules` 導入済み（ローカル audit/build 実行可）

---

## 3. 受け入れ条件（イシュー AC と一致）
- [ ] `cd frontend && npm audit --audit-level=critical --omit=dev` が exit 0（critical ゼロ）
- [ ] critical `shell-quote` が解消
- [ ] クリーン high 6件（axios/fast-uri/underscore/@babel-systemjs/jsonpath/bfj）が解消
- [ ] react-scripts 固着の残存 high 5件の risk-accept 根拠が本計画書に記録（§9）
- [ ] `npm run build` / フロントテスト / 型チェック が pass（axios 利用6ファイルのスモークテスト含む）
- [ ] PR #127 の CI が緑、develop マージ後に PR #125 の CI も緑化

---

## 4. 影響範囲
| 層 | 影響 |
|----|------|
| Backend | なし（P3/P5/P8 影響なし） |
| Frontend | `frontend/package.json`（axios 直接依存の floor 引き上げ／必要時 overrides 追加）・`frontend/package-lock.json`（再生成）。axios はランタイム依存のため API クライアントのスモークテスト必須（P6: UI 変更なし・ローディング/空/エラー状態の新規実装なし） |
| DB | なし |
| Config/Infra | `frontend/package.json` / `frontend/package-lock.json`。Dockerfile/compose のビルド対象は `npm ci` で lockfile を参照するため、lockfile 更新が反映される（追加の波及なし） |

**セキュリティ影響**: 本イシュー自体が依存 CVE の是正。基準＝`npm audit` の **critical/high を是正対象**（react-scripts 固着の high は --force 必須のため risk-accept、ランタイム外と明記）。認証・認可・入力処理のコード変更なし。

---

## 5. 変更点一覧（ファイル別）
- `frontend/package-lock.json`: `npm audit fix`（非 --force）でクリーン7件（shell-quote/axios/fast-uri/underscore/@babel-systemjs/jsonpath/bfj）を非脆弱版へ更新
- `frontend/package.json`: `axios` を `^1.6.7` → `^1.17.0`（安全 floor 明示）。`npm audit fix` でクリーン化が lockfile に定着しない transitive が残った場合のみ `overrides` を補完（shell-quote/fast-uri 等。既存 nth-check/postcss と同形式）

---

## 6. 実装手順（ステップ）

依存是正は「縦スライス」が存在しないため、**未知リスク（npm audit fix がビルドを壊さないか）を先頭**に置き、最小変更→検証の順で進める。各検証は自動テスト文書の TC に委譲（本文に検証コマンドを書かない）。

### ステップ1: クリーン7件の是正【未知リスク先行】
- `cd frontend && npm audit fix`（**非 --force**）を実行し、`package-lock.json` を更新する。
- `--force` は使わない（`react-scripts@0.0.0` 破壊を誘発するため）。
- → TC-01, TC-02 参照

### ステップ2: axios 直接依存の floor 引き上げ
- `frontend/package.json` の `axios` を `^1.6.7` → `^1.17.0` に変更し `npm install` で lockfile を整合させる。
- 実装時の注意: ステップ1 の `npm audit fix` が既に `^1.6.7` 範囲内で安全版（1.17.x 等）へ lockfile を更新している場合がある。その場合でも package.json の floor 明示（`^1.17.0`）は将来の意図しないダウングレード防止として実施する（実体が既に更新済みなら `npm install` は no-op 相当）。
- → TC-03 参照

### ステップ3: 残存クリーン high の overrides 補完（必要時のみ）
- ステップ1後に audit でクリーン対象がなお high/critical として残る場合のみ、`overrides` に該当パッケージの非脆弱版を追記する（既存 nth-check/postcss と同形式）。残っていなければ本ステップはスキップ。
- → TC-04 参照

### ステップ4: ビルド・テスト・型チェック・スモークテスト
- `npm run build` / フロントテスト / `tsc --noEmit` を実行し pass を確認。
- axios 利用6ファイル経路（ログイン・ダッシュボード・クイズ・設定・パスワードリセット）のスモークテスト（手動）。
- → TC-05, TC-06, TC-07 / 手動テスト参照

### ステップ5: 最終監査と残存 high の記録
- `npm audit --audit-level=critical --omit=dev` が exit 0 を確認。
- 残存 high（react-scripts 固着の5件）を列挙記録し risk-accept とする。
- → TC-01, TC-08 参照

**依存関係**: ステップ1 → ステップ2 →（必要時）ステップ3 → ステップ4 → ステップ5（順次）。

---

## 7. テスト計画（自動/手動）
- 自動（`docs/tests/open/I061_auto_test.md`）: TC-01〜TC-09。audit ゲート・各 CVE 解消・build/test/typecheck・moderate/low の before/after を機械検証。
- 手動（`docs/tests/open/I061_manual_test.md`）: axios 1.x 更新後の API 通信スモーク（ブラウザ実操作＝Human）と CI 緑確認。
- 再発防止テスト: TC-01（critical ゲート exit 0）が CI 赤の再発を検知する回帰テストを兼ねる。ベースラインは修正前 exit 1（実測）。
- 認可・テナント境界テスト: 該当なし（認証/認可コードの変更なし。axios はクライアント層の依存更新のみ）。

---

## 8. ロールバック
- `frontend/package.json` / `frontend/package-lock.json` の変更のみ。`git revert` または該当コミット取り消しで原状復帰。サービス再起動・マイグレーション不要。

---

## 9. Risk & 回避策 ＋ residual high の risk-accept 記録
| Risk | 回避策 |
|------|--------|
| `npm audit fix` が想定外の transitive を上げてビルド破壊 | 非 --force のみ実行。ステップ4 の build/test/typecheck で即検知。壊れたら revert |
| axios 1.6→1.17 の minor 挙動差で API 通信が変化 | 1.x 内（semver 非破壊）。利用6ファイルを手動スモーク。差異が出たら呼び出し側を調整（計画外の大改修が必要なら STOP→提案） |
| overrides 追加が react-scripts と衝突 | 既存 nth-check/postcss と同形式に限定。ステップ3 は必要時のみ。build で検証 |

**residual high の risk-accept（AC 充足の記録）**: `workbox-webpack-plugin` / `workbox-build` / `serialize-javascript` / `rollup-plugin-terser` / `react-scripts` の5件は、npm の修正案が `react-scripts@0.0.0`（破壊的スタブ）のみで、react-scripts 5.0.1 を壊さずには解消不能。いずれも **dev/build 時のみ使用（本番ランタイムのバンドルに脆弱経路を持ち込まない）**ため、本イシューでは是正せず受容する。恒久対策は **react-scripts からの移行（CRA→Vite 等）を別イシュー**で扱う。
> 補足（`--omit=dev` でも検出される理由）: CRA は `react-scripts` を `devDependencies` ではなく `dependencies` に置く構成のため、`npm audit --omit=dev` でも除外されない。よって「dev/build 時のみ使用」と「`--omit=dev` で出る」は矛盾しない。**実装者は本5件に `--force` を適用しないこと**（react-scripts 破壊を招く）。

---

## 10. 設計判断の明示
| 設計判断 | 区分 |
|----------|------|
| スコープ A（react-scripts を壊さず直せるものだけ是正） | イシューに明記（設計確認メモ #1=A） |
| 完了基準を `--audit-level=critical` exit 0 にする（high ゼロは目標にしない） | イシューに明記（#2） |
| residual high 5件を risk-accept（react-scripts 移行は別イシュー） | イシューに明記（#1/#3） |
| axios を `^1.17.0` に引き上げ（1.x 内） | イシューに明記（#1） |
| クリーン化は `npm audit fix` 主体・overrides は補完（必要時のみ） | 仮定（実装容易性）→ 承認ポイントで確認 |

---

## 11. 承認ポイント（チェックリスト）
1. スコープ A（critical + クリーン high 6 を是正／react-scripts 固着 high 5 は risk-accept）でよいか
2. 完了基準を `npm audit --audit-level=critical --omit=dev` exit 0 とし、high ゼロは目標にしない方針でよいか
3. `axios` を `^1.6.7`→`^1.17.0`（1.x 内・6ファイルをスモーク）でよいか
4. ★ クリーン化は `npm audit fix`（非 --force）主体、定着しない分のみ `overrides` 補完（必要時）という実装方針でよいか
5. テスト計画（TC-01〜08 + 手動スモーク）でよいか

## レビュー結果
- [20260613_1840 判定: ✅ 完了](../../reviews/closed/I061_plan_review_20260613_1840.md)（Warning4/Info2 はテスト・文書品質。レビュー後に計画書・テスト文書へ反映済み）
