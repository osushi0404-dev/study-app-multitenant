# I452 レビュー: クイズの回答から復習の予定を作り、ダッシュボードから今日の復習を始められるようにする

- 関連: docs/issues/open/I452.md / docs/plans/open/plan_I452.md / GitHub #452 / Draft PR #464

## 変更概要
（implement 段階で記入）

## 変更点
（implement 段階で記入）

## 影響範囲
（implement 段階で記入）

## テスト結果
（test-gate 段階で記入）

## 計画との差分
（implement 段階で記入）

## ロールバック
PR を revert し、migration `0022_quizsession_mode` を戻す（`python manage.py migrate problems 0021`）。計画書 7 章。

## 自律判断の記録
- [plan-issue] 画面の細部 U1〜U3（結果を見る・今日の復習の印・読み込み失敗の再読み込み）をユーザーに確認し、推奨どおりで確定 — イシューに無い UI の文言・流れのため（止めて聞く条件 1）
- [plan-issue] 間違い分析・適応的な問題選択を画面につなぐ後続を I466（#466）として起票し、I455 の F4 を同梱 — 設計確認メモの決定（計画の段階で起票）
- [plan-issue] 同梱の 14 件の扱いを計画書 9 章で決めた（同梱 7・I190 に渡す 4・残す 3）— 変更点に当たるものは同梱、I190 の担当のものは渡す

STAGE_DONE: plan NEXT: plan-review
- [plan-review] 判定 HIGHRISK。Warning 3 件（カードの初期値・習熟度のキャッシュのキーと消す処理・TC-14 の合否）を計画書・テスト文書で直し、再レビューはしない — 方式・範囲・受け入れ条件を変えないため

STAGE_DONE: plan-review NEXT: design-security-review
