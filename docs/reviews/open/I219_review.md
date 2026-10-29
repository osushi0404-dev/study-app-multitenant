# I219 レビュー: セッションの開始時の primary の早送りを裏で動かし、打ち切りで index.lock を残さない

## 変更概要
（実装後に記入）

## 変更点
（計画書 `docs/plans/open/plan_I219.md` の 4・5 と対応。実装後に記入）

## 影響範囲
- ハーネスの開始時のフックとそのテスト・手順書だけ。アプリのコードの変更なし

## テスト結果
（test-gate で記入）

## 計画との差分
（計画変更記録があれば要約）

## ロールバック
- PR を revert する。`~/.cache/claude-primary-sync/` の結果のファイルは残っても害が無い

## 自律判断の記録
- [plan] 計画の前に、実際の primary での読み取りの git の所要時間を測った（読み取りだけの診断）。`status` は 1〜5 秒でばらつき、`GIT_OPTIONAL_LOCKS=0` でも速さは変わらない（ロックを取らないだけ）。`diff-index` は索引の stat が古いと誤るので替えない — 裏の処理の打ち切りを 60 秒にした根拠
- [plan] 一覧 `docs/reviews/backlog/I200.md` の F8（時間の見積もりのコメント）を同梱 — 時間の見積もりの仕組み自体を消すため
- [plan-review] 計画レビュー 1 は OK（高リスク判定なし）。Warning 5・Info 2 は方式を変えずに直した（計画変更記録 1）— 再レビューは不要と判断

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: implement
