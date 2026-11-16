# I498 レビュー: マージ前の最終確認の CI 待ちの上限を code-review.sh と 1 か所にまとめる

## 変更概要
- CI 待ちの上限の既定を `scripts/claude/code-review.sh` の `CI_WAIT_TIMEOUT_DEFAULT`（1980 秒）1 か所にまとめ、`scripts/claude/pr-base-sync.sh` はそこから読む
- close 手順 5.5・proceed の `merge` で、最終確認を背景の実行（`run_in_background: true`）で流す

## 変更点
- `scripts/claude/code-review.sh`: `CI_WAIT_TIMEOUT_DEFAULT=1980` を `wait_ci` の前に置き、`wait_ci` と時間切れのメッセージの `1200` をこの変数に置き換えた（計画書 4-1）
- `scripts/claude/pr-base-sync.sh`: `600` をやめ、`PBS_CI_TIMEOUT` が無いときは code-review.sh を関数だけ読み込んで既定を読む。読めない・正の整数でないときは exit 1（計画書 4-2）
- `.claude/skills/close/SKILL.md` 手順 5.5・`.claude/skills/proceed/SKILL.md` の `merge`: `run_in_background: true` で流すと書いた（計画書 4-3・4-4）
- `scripts/claude/tests/test_i498_ci_wait_timeout.sh`（新規）: T1〜T6・FG1〜FG3（計画書 4-5・auto_test TC-01）

## 影響範囲
- ハーネスのスクリプト 2 本・手順書 2 本・新しいテスト 1 本。Backend・Frontend・DB・`.github/`・`.claude/settings.json` は変えない
- review-gate の CI 待ちの既定も 1200 秒から 1980 秒に延びる

## テスト結果
- （test-gate で記入）docs/tests/open/I498_auto_test.md・docs/tests/open/I498_manual_test.md

## 計画との差分
- なし（`pr-base-sync.sh` の既定を読む位置は、計画書 4-2 の「`:21` の後」のとおり `LOOP_MAX` の行の後に置いた）

## ロールバック
- この PR のコミットを revert する（データ・設定の変更なし）

## 自律判断の記録
- [plan] 値の置き場所を新しい共有ファイルでなく code-review.sh の変数にした — code-review.sh を一時のフォルダに写して動かす既存のテストが 5 本以上あり、新しいファイルの読み込みを足すと写しの組み合わせを全部直す必要があるため（計画書 §9）
- [plan] 既定を 1980 秒にした（イシューの「1200 秒以上」の範囲） — CI で時間の上限を持つ一番長いジョブ（Harness Tests・30 分）より長くし、テストのジョブが延びても待ちが CI より先に諦めないようにするため（計画書 §9）
- [plan] 調べる途中で見つけた `pr-base-sync.sh` の `ci_wait` の「チェックが未登録だと待たずに通る」穴は、このイシューでは直さず retro で起票を決める — イシューの目的（待ち不足で落ちない）と逆向きの話で、マージは GitHub の承認が止めるため（計画書 §9）
- [plan-review] PLAN_VERDICT: OK（Info 3 件のみ・計画は直さない）— Info 2（TC-02 の失敗注入の結果を記録する）は implement で行う
- [implement] /simplify（4 観点）で、close の手順書の「最長 1980 秒」の数字を消し、置き場所（`CI_WAIT_TIMEOUT_DEFAULT`）だけを書く形にした — 数字の 2 つ目の写しを作らないため（計画書 4-3 の文の数字だけを外した。方式は同じ）
- [implement] /simplify の残りは見送り: `|| CI_TIMEOUT=""` の削除・時間切れメッセージを wait_ci へ移す・T3 での出力の使い回し・スタブの共通化・ci.yml の timeout-minutes との関係のテスト — どれも挙動を変えない小さな整理か、計画書 §8 R5 で決めたこと（設定の写しのテストを作らない）で、計画のコード例から外す価値が無いため

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate
