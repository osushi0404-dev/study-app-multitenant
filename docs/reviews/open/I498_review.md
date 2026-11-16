# I498 レビュー: マージ前の最終確認の CI 待ちの上限を code-review.sh と 1 か所にまとめる

## 変更概要
- CI 待ちの上限の既定を `scripts/claude/code-review.sh` の `CI_WAIT_TIMEOUT_DEFAULT`（1980 秒）1 か所にまとめ、`scripts/claude/pr-base-sync.sh` はそこから読む
- close 手順 5.5・proceed の `merge` で、最終確認を背景の実行（`run_in_background: true`）で流す

## 変更点
- （実装後に記入）計画: docs/plans/open/plan_I498.md §4

## 影響範囲
- ハーネスのスクリプト 2 本・手順書 2 本・新しいテスト 1 本。Backend・Frontend・DB・`.github/`・`.claude/settings.json` は変えない
- review-gate の CI 待ちの既定も 1200 秒から 1980 秒に延びる

## テスト結果
- （test-gate で記入）docs/tests/open/I498_auto_test.md・docs/tests/open/I498_manual_test.md

## 計画との差分
- （実装後に記入）

## ロールバック
- この PR のコミットを revert する（データ・設定の変更なし）

## 自律判断の記録
- [plan] 値の置き場所を新しい共有ファイルでなく code-review.sh の変数にした — code-review.sh を一時のフォルダに写して動かす既存のテストが 5 本以上あり、新しいファイルの読み込みを足すと写しの組み合わせを全部直す必要があるため（計画書 §9）
- [plan] 既定を 1980 秒にした（イシューの「1200 秒以上」の範囲） — CI で時間の上限を持つ一番長いジョブ（Harness Tests・30 分）より長くし、テストのジョブが延びても待ちが CI より先に諦めないようにするため（計画書 §9）
- [plan] 調べる途中で見つけた `pr-base-sync.sh` の `ci_wait` の「チェックが未登録だと待たずに通る」穴は、このイシューでは直さず retro で起票を決める — イシューの目的（待ち不足で落ちない）と逆向きの話で、マージは GitHub の承認が止めるため（計画書 §9）

STAGE_DONE: plan NEXT: plan-review
