# I195 レビュー: Claude で確かめられる手動テストを人に振らない仕組みを固める

- 計画書: docs/plans/open/plan_I195.md
- イシュー: docs/issues/open/I195.md（#329）
- Draft PR: #351

## 変更概要
Claude で確かめられる手動テストを人に振らないよう、手順（do）と関所（gate）を 2 段にした。対話画面（TUI）は新しいスクリプト `tui-capture.sh` で Claude が確かめる。実施者の基準は `plan-writing-rules.md`「実施者の区別」の 1 か所にまとめた。Human の行は `試した手段:` が必須で、判定スクリプトが確かめる。中身の正しさは計画レビュー役が見る。

## 変更点
- `scripts/claude/tui-capture.sh`（新規）: tmux で `claude --permission-mode manual` を起動し、入力を送り、画面を読み、必ず閉じる。`!` で始まる入力は起動前に止める。`.claude/settings.json` は変えない
- `scripts/claude/check-manual-test-executor.sh`: Human の行の備考を `試した手段:` で読む。中身が無ければ不合格（前の書き方だけの行も不合格）
- `docs/runbooks/plan-writing-rules.md`: 「実施者の区別」に対話画面の手段と `試した手段:` の書き方を足し、基準の正であることを明記した。実施環境の表に「対話画面の判定」を足し、スパイクの手段にも足した
- `.claude/skills/plan-issue/SKILL.md`・`.claude/skills/test-gate/SKILL.md`・`docs/tests/templates/manual_test_template.md`: 基準の写しを要約と参照にした。test-gate に `tui-capture.sh` の使い方を 1 行足した
- `.claude/agents/plan-reviewer.md`: 手動テストの Human の行の妥当性を見る差し戻しの行を足した
- テスト: `test_tui_capture.sh`（新規）・`test_check_manual_test_executor.sh`（書き方の変更・X19・X20・FG。X9 を削除）・`test_i193_official_flow.sh`（S21 の拡張。終わった I193 の記録の判定を削除）

## 影響範囲
- ハーネスだけ（`scripts/claude/tui-capture.sh`〔新規〕・`check-manual-test-executor.sh`・`plan-writing-rules.md`・plan-issue・test-gate・手動テストのテンプレート・`plan-reviewer.md`・テスト 3 本）。アプリ本体・DB・設定（`.claude/settings.json`・`.github/`）の変更なし

## テスト結果
（test-gate で書く）

## 計画との差分
- 計画変更記録 1（計画レビューの Warning 対応）・2（/simplify: 起動の指定を `manual` に・観測手段の一覧の写しをやめる・テストの整理）

## ロールバック
- PR を revert する（計画書 7）

## 自律判断の記録
- [plan] 対話画面のスクリプトの成立を計画の前にスパイクで確かめた（tmux で claude を起動し `/plan-` の候補を読めた）— 未知リスクを計画の前に潰すため（plan-writing-rules.md のスパイク (1)）
- [plan] テストは偽物の tmux・claude を PATH の先頭に置いて確かめ、本物は手動テストで Claude が確かめる — CI に tmux・claude があるか分からず、`.github/` は変えないため
- [implement] /simplify の指摘のうち、次は見送った: テスト用の共通の関数集を作る（テストは 1 ファイルで完結させる今の決まりに合わせる）・入力の間の 0.5 秒を外から変えられるようにする（テストのためだけの仕掛けになる。テストの時間は約 4 秒で小さい）・起動の待ちを 0.2 秒ごとにする（得は 1 回 1 秒以下）・`!` を `{Enter}` が後に続くときだけ止める（イシューで「`!` で始まる入力は送らない」と決めている）— どれも動きを変えるか、得が小さいため
- [implement] `test_i202_ledger_cleanup.sh` の N10 が、負荷の高いとき 3 回中 1 回落ちた（このイシューの変更とは関係なし。一覧 I206 の F5）。ユーザーと相談し、別のイシューとして起票する案を渡した（起票はユーザー）— 原因もファイルも I195 と関係が無いため

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate
