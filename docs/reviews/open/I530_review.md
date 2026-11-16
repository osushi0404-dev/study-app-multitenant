# I530 レビュー: マージ前の最終確認の CI 待ちをレビュー段階の wait_ci に一本化する

## 変更概要
- （実装後に書く）

## 変更点
- （実装後に書く）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: ハーネスのスクリプト（`pr-base-sync.sh`・`code-review.sh` のコメント）とテスト 2 本・一覧 2 本

## テスト結果
- 自動: （実装後に書く）
- 手動: （close の手順 5.5 で書く）

## 計画との差分
- なし

## ロールバック
- この PR のコミットを revert する

## 自律判断の記録
- [plan] I498（PR #528・マージ依頼中）のブランチを取り込んで作った — このイシューの変更点が I498 の上にしかない。#528 のマージの後にこのイシューのマージを依頼する
- [plan] 最終確認の合格の道すべて（`CLEAN|HAS_HOOKS` を含む）で CI を待つことにした — イシューの目的「全部そろって合格するまで待ってから合格と言う」の範囲。CI が終わっていれば照会 1 回で済む
- [plan] 上限・間隔の上書きを `CI_WAIT_TIMEOUT`・`CI_POLL_INTERVAL` 1 つにし、`PBS_CI_TIMEOUT`・`PBS_CI_INTERVAL` を消した — 使うのはテストだけで、2 つの名前は review-gate と値がずれる元
- [plan] 一覧の I498 F1・F2・F3・R1 と I224 F1 を同梱、I498 F4 は残した — 理由は計画書 §9

STAGE_DONE: plan NEXT: plan-review
