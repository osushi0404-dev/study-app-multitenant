# I546 レビュー: 進め方の決まり（docs/runbooks・CLAUDE.md・記憶）の BP 見直し

## 変更概要
- （実装後に書く）`docs/runbooks/`・`CLAUDE.md`・記憶の進め方の決まりを、点検の結果の表（`docs/reviews/open/I546_rules_audit.md`）のとおり最新化・漏れ・最適化する

## 変更点
- （実装後に書く）

## 影響範囲
- Backend/Frontend/DB/Config: なし（文書と、文書の文字を見るテストの期待だけ）

## テスト結果
- 自動: （実装後に書く）
- 手動: （実装後に書く）

## 計画との差分
- （実装後に書く）

## ロールバック
- PR を revert する。記憶は点検の表 E から書き戻す

## 自律判断の記録
- [plan] 点検は 5 つに分けた点検役（サブエージェント）で実装の前に済ませ、結果を点検の表にした — 中身の変更案を実装の前にユーザーに聞くには点検が先に要るため。点検役の案どうしの食い違いは点検の表 §0 で決めた
- [plan] `README.md`・`docs/claude-code-structure.md`（食い違う行だけ）・テンプレート 2 本・文書の文字を見るテストを範囲に入れた — AC2・AC9 と CI を保つための付随の直し（計画書 §9）
- [plan-review] 計画レビュー OK（Warning 4 件は計画書・テスト文書に反映、再レビューなし）— 方式・範囲・受け入れ条件を変えない追記だけのため
- [plan] 決定論ゲートから `test_i193_official_flow.sh` を外した — 手元の道具の版の違いで F9 の 3 項目が文書と関係なく落ちるため。CI の `run-all.sh` が全項目を流す

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
