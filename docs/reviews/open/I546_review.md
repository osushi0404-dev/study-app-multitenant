# I546 レビュー: 進め方の決まり（docs/runbooks・CLAUDE.md・記憶）の BP 見直し

## 変更概要
- （実装後に書く）`docs/runbooks/`・`CLAUDE.md`・記憶の進め方の決まりを、点検の結果の表（`docs/reviews/open/I546_rules_audit.md`）のとおり最新化・漏れ・最適化する

## 変更点
- （実装後に書く）

## 影響範囲
- Backend/Frontend/DB/Config: なし（文書と、文書の文字を見るテストの期待だけ）

## テスト結果
- 自動: 決定論ゲート 22 項目すべて合格（review-gate・2026-11-17）。CI 成功。i193 は手元で F9 の 3 項目だけ道具の版で落ち、CI で全項目合格
- 手動: Claude の No.1〜5 は OK。No.6（記憶のファイル 42 件の移動）はユーザーのコマンド待ち

## 計画との差分
- （実装後に書く）

## ロールバック
- PR を revert する。記憶は点検の表 E から書き戻す

## 自律判断の記録
- [plan] 点検は 5 つに分けた点検役（サブエージェント）で実装の前に済ませ、結果を点検の表にした — 中身の変更案を実装の前にユーザーに聞くには点検が先に要るため。点検役の案どうしの食い違いは点検の表 §0 で決めた
- [plan] `README.md`・`docs/claude-code-structure.md`（食い違う行だけ）・テンプレート 2 本・文書の文字を見るテストを範囲に入れた — AC2・AC9 と CI を保つための付随の直し（計画書 §9）
- [plan-review] 計画レビュー OK（Warning 4 件は計画書・テスト文書に反映、再レビューなし）— 方式・範囲・受け入れ条件を変えない追記だけのため
- [implement] 実装は 4 つの文書群（流れ・計画とレビュー・安全と依存・準備と環境）に分け、触るファイルが重ならない 4 体のサブエージェントで同時に行った — 文書の数が多く、ファイルの境目で分けると同時に書いても食い違わないため。食い違いの残りは /simplify と参照の確かめ（`check_section_refs.py`・`check_references.py`）で見た
- [implement] U1〜U7 はユーザーの返答（「はい」）どおり全部反映。U7 の GitHub の設定はユーザーの画面の操作なので、マージ依頼のときに頼む
- [implement] `docs/claude-code-structure.md` を計画より広く（写しを参照に）直した・記憶の退避先を記憶のフォルダの外にした — 計画変更記録に書き、計画レビューをやり直す
- [implement] 記憶のファイルの移動（42 件）はユーザーの `!` の 1 コマンドに頼んだ — サンドボックスが記憶のフォルダへの Bash の書き込みを止める。索引 `MEMORY.md` と残す 6 件の直しは Claude が Edit で済ませた
- [implement] /simplify（4 観点）の指摘のうち、写しの残り・参照の輪（Claude を起こす行の決まりの正が消えていた）・冗長な文・D10 の写しのテストを直した。見送り: CLAUDE.md の索引と §3 を削る案（索引は全手順書の正）・参照 1 行だけの節を消す案（スキルが節名で参照）・起票の決まりを issue-flow.md へ寄せる案・安全装置の並びを workflow.md から消す案（test_i193 S12 が求める）・i107 と i179 D3 をテストごと消す案（今回消した節と関係の無い既存の項目。消すかはテストの棚卸しで決める）・絶対ルール 5 の「記録」の定義を広げる案（絶対ルールの中身に触れる）。close 後の送り忘れの仕組みは #520 にコメントした
- [plan] 決定論ゲートから `test_i193_official_flow.sh` を外した — 手元の道具の版の違いで F9 の 3 項目が文書と関係なく落ちるため。CI の `run-all.sh` が全項目を流す

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: human-test
