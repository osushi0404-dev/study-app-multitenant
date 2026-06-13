# I061 レビュー: フロントエンド依存脆弱性の是正（npm audit critical/high 解消）

## 基本情報
- **レビューID**: I061_review
- **レビュー目的**: 実装結果評価
- **対象計画書**: docs/plans/open/plan_I061.md
- **関連イシュー**: #126 / Draft PR: #127
- **実装完了日**: （未記入）

## 変更概要
- `frontend` の npm audit critical（`shell-quote`）+ クリーン high 6件（axios/fast-uri/underscore/@babel-systemjs/jsonpath/bfj）を是正し CI を緑化。
- react-scripts 固着の high 5件は risk-accept（dev/build 時のみ・CRA 移行は別イシュー）。

## 変更点
- `frontend/package-lock.json`: `npm audit fix`（非 --force）でクリーン7件を非脆弱版へ
- `frontend/package.json`: `axios` `^1.6.7`→`^1.17.0`、必要時 `overrides` 補完

## 影響範囲
- Backend/DB: なし。Frontend: 依存更新のみ（UI/挙動の新規変更なし、axios はランタイム依存のためスモーク必須）。

## レビュー観点（本イシュー固有）
- [ ] `--force`／react-scripts メジャー更新を使っていないか（破壊回避）
- [ ] axios 更新が 1.x 内に留まり、利用6ファイルの通信が従来どおりか
- [ ] residual high 5件が計画書 §9 に risk-accept として根拠記録されているか（範囲が膨らんでいないか）
- [ ] overrides を追加した場合、既存 nth-check/postcss と同形式で最小限か
- [ ] 全 TC（TC-01〜TC-09）が pass しているか（特に TC-01 critical ゲート exit 0）

## テスト結果
- 自動（implement 時にローカル実行）: TC-01〜TC-09 すべて pass。critical=0（exit 0）/ shell-quote→1.8.4 / axios→1.17.0 / クリーン high 6 解消 / build exit 0 / unit 7 passed / tsc exit 0 / 残存 high=react-scripts 固着5件 / 脆弱性 30→18（moderate 9→4）。`/test` で環境パリティ再確認予定。
- 手動（/test 2026-06-13）: No.1〜6（axios API スモーク: ログイン/ダッシュボード/クイズ/設定/パスワードリセット/インターセプタ）すべて **OK**。No.7（PR #127 CI 全緑）**OK**。No.8（develop マージ後の #125 緑化）は close 以降に確認。
- 実装メモ: bfj/jsonpath/underscore は `npm audit fix` では未解決（react-scripts が bfj@7.1.0 を pin）。根本の underscore を計画ステップ3どおり override（`^1.13.8`）し3件一括解消（react-scripts 破壊なし）。

## 計画との差分
- あり: bfj/jsonpath は `npm audit fix` で解消できず（react-scripts が bfj@7.1.0 を pin）、計画ステップ3どおり根本の `underscore ^1.13.8` override に切り替えて3件を連鎖解消（react-scripts 破壊なし・計画の想定範囲内）。
- collateral（許容範囲）: `npm audit fix` の副作用で patch/minor 更新が併発（react-router 6.30.3→6.30.4 / express 4.22.1→4.22.2 / ws 8.18.3→8.21.0 / qs 6.14.2→6.15.2 / @remix-run/router 1.23.2→1.23.3 等）。後方互換・build/test pass 確認済み。
- CI 実績: PR #127 全ジョブ緑（**Frontend Lint & Security pass**＝critical 解消を実証）。

## ロールバック
- `frontend/package.json` / `package-lock.json` の変更のみ。`git revert` で原状復帰可能。
