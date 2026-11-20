# I599 レビュー: サンドボックスの中から scripts/claude/ に書いたスクリプトをレビュー前に外で流せる穴を塞ぐ

## 変更概要
-

## 変更点
-

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/settings.json`・`.claude/hooks/`（新規）・`scripts/claude/hooks/pretooluse_guard.py`・`scripts/claude/code-review.sh`・`docs/runbooks/danger-ops.md`・`docs/runbooks/harness-audit.md`・`scripts/claude/tests/`

## テスト結果
- 自動:
- 手動:

## 計画との差分
-

## ロールバック
- PR を revert する。`~/.cache/claude-reviewed-hooks/` は消してよい

## 自律判断の記録
- [plan] 中で動かす範囲を「流すスクリプトから呼ぶファイルをたどって変更に届くときだけ」にした — イシューのメモの「1 つでも違えばすべて中」では変えていないレビュー役まで中で失敗し段階ごとに人の手が要る。ユーザーに確かめ、BP と開発効率で最善のやり方で、との判断（2026-11-20）
- [plan] 判定の本体を `.claude/hooks/unreviewed.py`、フックの起動役を `.claude/hooks/reviewed-hook.sh` に置いた — `scripts/claude/` の外でサンドボックスから書けず、判定を直しても呼び元が中に回らない
- [plan] `run-all.sh`・`test-session.sh` は直さず見張りの側で入口を扱う。`code-review.sh` のゲートの実走（計画の調査で見つけた入口）を範囲に足した — イシューの実装対象から変えた。理由は計画書 9
- [plan] スパイクで「フックの書き換えの後のコマンドで外に出すかが決まる」ことを確かめた（計画書の調査結果 6）
- [plan-review] 計画レビューの Warning 2・Info 1 を直した（R9 の追加・手動 No.5・TC-20）。方式・範囲・受け入れ条件は変えないので再レビューはしない — 計画変更記録のとおり
- [design-security-review] Blocker 0。Medium 4 件の必須の防御（名前の文字を絞る・引数の `=` の形・読み取りの上限・git の安全な -c）を計画書に書き、TC-21 と TC の追加で確かめる — 計画の方式は変えない
- [implement] 判定の読み込みは `sys.modules` に登録してから行う — ファイルの場所から読み込むモジュールの dataclass は登録が無いと作れず、初回は安全側（中で動かす）に倒れた
- [implement] 当たりの規則を「`bash` のすぐ後ろが scripts/claude/ のパス」に絞った — `grep … scripts/claude/…` のような読み取り（もともと中で動く）にまで印が出て邪魔だった
- [implement] `/simplify` の指摘を取り込んだ（引数の表を一般の規則に・git の回数を減らす・写しがあれば起動役は差を見ない・見張りの読み込み失敗時の規則を写さない・TC-22）。`code-review.sh` のゲートの前置きの照合を判定に寄せる指摘は見送った — `classify_gate` が `&&` などのつなぎを UNSAFE にするので、ゲートの行は 1 つのコマンドだけ
- [implement] 手動 No.5（`.claude/hooks/` に Bash から書けない）は実装中に確かめた — `.claude/hooks/unreviewed.py` を Bash の Python で直そうとして `Read-only file system` で拒否された
- [implement] 当たりの判定を、コマンドを語に分けて「`bash` のすぐ後ろが scripts/claude/ のパス」の区切りだけにした（TC-23）— コミットのメッセージに `bash scripts/claude/…` と書いただけで `git commit` が中に回り、pre-commit が `.claude/hooks/` に書けず失敗した。読み切れないコマンドは今までどおり中で動かす
- [review-gate] `code-review.sh` はこのブランチで直したので、見張りが中で動かす。計画の R7 のとおりユーザーに `!` で流してもらった。CI の Harness Tests が落ちた（フックの登録の古い書き方を確かめる既存のテスト 2 本: test_i187_frontend_verify_config.sh ⑦・test_sessionstart_context.sh TC-11g）ので fix-loop へ
- [fix-loop] CI の 2 本の失敗は、テストの期待値を起動役の形に替えて直した（案 A・差分が最小で意図を保つ）。診断レビュー PASS
- [fix-loop] F1・F2・F4 を直した。F2 は診断の案 A の 3（同じフォルダのファイル名を見る）を実装中に「git が無視するファイルを `ls-files --ignored --directory` で数える」に替えた — 変更が無いときの早く返す道でも効き、規則が単純（無視されるフォルダはまとめて数えないので遅くならない）。方式・範囲は変えない
- [fix-loop] F7・F8 を直した（診断の案 A）。台帳の F9・F10（Low）は止める指摘でないので直さず retro に回す
- [fix-loop] F11 は列挙を足さず、置き換え・かっこを含むコマンドを読み切らずに中で動かす単純な規則にした — F1・F7・F11 と同じ種類が 3 周続いた（列挙で塞ぐ方式の限界）。普段の呼び出しは変わらない
- [review-gate] review-gate ⇄ fix-loop が 5 回目（上限）に当たり止めて聞いた。指摘の種類: 「コマンドの書き方の読み取りの取りこぼし」（F1・F7・F11）と「安全側に倒しすぎて普段の呼び出しを壊す」（F12・F13）。ユーザーの判断（2026-11-20・原文）: 「ループエンジニアリング、ハーネスエンジニアリング、グラフエンジニアリングのベストプラクティスと開発をサクサク進める(開発効率)という観点でベストなやり方で進めて。」→ 推奨の「もう 1 周だけ直す（置き換え・かっこの規則を scripts/claude/ に変更があるときだけ効かせる・当たりはコマンドの先頭の形だけ）」で進める
- [fix-loop] F12 を直した（変更があるときだけ置き換え・かっこを中に・当たりはコマンドの先頭の形）。F13 も同じ原因なので同じ直しで消えた。F14・F15（Low）は止める指摘でないので retro へ
- [review-gate] 延長の 1 周の後も HIGH（F16・F17・F18）。種類は「漏れる」と「壊す」が交互（計画書の調査結果 5）。止めて聞き、方式の見直しを推奨した。ユーザーの判断（2026-11-20・原文）: 「ループエンジニアリング、ハーネスエンジニアリング、グラフエンジニアリングのベストプラクティスと開発をサクサク進める(開発効率)という観点でベストなやり方で進めて。」→ 推奨の「方式を裏返す（既定を中に・決まったスクリプトだけを起動役が外で動かす）」で計画を第 2 版に書き直し、計画レビューからやり直す

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
