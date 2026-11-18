# I432 レビュー: Dependabot #377（@playwright/test 1.64.1）で E2E が落ちる原因を直して取り込む

## 変更概要
- CI の E2E のジョブの Node.js を 18 → 26 に上げ、`@playwright/test` を 1.59.1 → 1.65.1、手元の E2E のコンテナのイメージを v1.65.1-jammy に上げる。#377・#376 は取り込み済みとして閉じる（計画: docs/plans/open/plan_I432.md）

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.github/workflows/e2e.yml`・`e2e/package.json`・`e2e/package-lock.json`・`docker-compose.yml`（e2e のイメージ）・`docs/runbooks/frontend-verify.md`

## テスト結果
- 自動: （実装後に記入）
- 手動: （test-gate で記入）

## 計画との差分
- なし

## ロールバック
- PR #575 の revert（設定とロックファイルだけ）

## 自律判断の記録
- [plan] 取り込み方は「このブランチで同じ版上げ・#377/#376 は閉じる」にした — Node.js とイメージと npm の版を 1 本の PR でそろえて確かめられ、#377（1.65.0）と #376（1.65.1）の版のずれも無くせるため（計画書 §9）
- [plan] E2E のジョブの Node.js は 26（規約 §0）にし、画面の Node.js 18 は #551 に残した — E2E のジョブは `e2e/` の別の package で画面と別に動き、規約 §16 の #551 の行は画面のコードとの差の表と読んだため（計画書 §9）
- [plan] 1.65 での E2E の事前の確かめは手元でせず CI に任せた — 手順書の `RATELIMIT_ENABLE=false docker compose …` は前置きがあるためサンドボックスの外で動く対象に当たらず `.env` を読めずに止まった。前置きなしではログインの制限で落ちる（計画書 §1 スパイク）。手順書の形がサンドボックスの中で動かないことは retro で扱う
- [plan] `.github/` を変えるが止めて聞かずに進めた — 変えるのは Node.js の版の 1 行だけで守りを緩めない（TC-01・TC-02）。直し方は grill-me の報告でユーザーに示した後に `/plan-issue` が打たれ、マージはユーザーが承認する（計画書 §9）
- [plan] #377・#376 を閉じるのは test-gate の手動 No.5 にした — CI が緑と確かめた後に行い、AC4 を close の前に満たすため
