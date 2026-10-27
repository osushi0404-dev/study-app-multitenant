# I195 レビュー: Claude で確かめられる手動テストを人に振らない仕組みを固める

- 計画書: docs/plans/open/plan_I195.md
- イシュー: docs/issues/open/I195.md（#329）
- Draft PR: #351

## 変更概要
（implement で書く）

## 変更点
（implement で書く）

## 影響範囲
- ハーネスだけ（`scripts/claude/tui-capture.sh`〔新規〕・`check-manual-test-executor.sh`・`plan-writing-rules.md`・plan-issue・test-gate・手動テストのテンプレート・`plan-reviewer.md`・テスト 3 本）。アプリ本体・DB・設定（`.claude/settings.json`・`.github/`）の変更なし

## テスト結果
（test-gate で書く）

## 計画との差分
（実装で計画と違うことをしたら書く）

## ロールバック
- PR を revert する（計画書 7）

## 自律判断の記録
- [plan] 対話画面のスクリプトの成立を計画の前にスパイクで確かめた（tmux で claude を起動し `/plan-` の候補を読めた）— 未知リスクを計画の前に潰すため（plan-writing-rules.md のスパイク (1)）
- [plan] テストは偽物の tmux・claude を PATH の先頭に置いて確かめ、本物は手動テストで Claude が確かめる — CI に tmux・claude があるか分からず、`.github/` は変えないため

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: implement
