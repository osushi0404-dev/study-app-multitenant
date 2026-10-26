# I197 レビュー: 実装の検証（レビュー）の仕組みを白紙から作り直す

## 変更概要
- 敵対的レビューを、裏で動くサブエージェント＋15 分のタイマーから、スクリプト `scripts/claude/adversarial-review.sh` が起動する別プロセス（読むだけのレビュー役 3 観点・実験役は auto＋承認なし）に作り直す
- 計画の段階で「必ず確かめる項目」の一覧を作り、項目ごとの結果（実験で確認／読んで確認／未実施）から判定を決定論で出す。未検証・報告なし・時間切れ・拒否は合格にしない
- 全部の `claude -p` の検証に `--permission-prompts none`（承認が要る操作は待たずに拒否して記録）
- （実装後に更新）

## 変更点
- （実装後に記入）

## 影響範囲
- ハーネス（`.claude/`・`scripts/claude/`・`docs/runbooks/`・テンプレート）。アプリのコード・DB・`.claude/settings.json`・見張りは変えない

## テスト結果
- （test-gate 段階で記入）

## 計画との差分
- （実装後に記入）

## ロールバック
- PR を revert する（計画 §7）

## 自律判断の記録
- [plan] I197 は track:harness だが app-1 で計画した — `docs/runbooks/worktree.md` §10「ワークツリーはトラックに固定しない」。ユーザーが app-1 で /plan-issue を実行した
- [plan] 「親が実験を実行」は、親の会話ではなく、スクリプトが起動する実験役の別プロセス（auto＋承認なし）で行う — 親の会話で実行すると確認画面で人を待ちうる。設計確認メモの形（レビュー役は読むだけ・実験は別が実行）は変えない（計画 §9）
- [plan-review] 1 回目 BLOCKER 2 件（一覧の見出し・差分の受け渡し）を直して 2 回目 OK。2 回目の Warning のうち FG の追加・S1 の論理行・数の訂正は直し、再レビューはしない — 方式・範囲・受け入れ条件を変えないため（計画変更記録 2）。高リスク判定 No なので design-security-review は通らない
- [implement] I194（#328）を GitHub でコメントして not planned で閉じた — 設計確認メモでユーザーが決めた統合・取り下げ（計画 §4.6）。I194 のイシューファイルは harness-2 にあり、このセッションからは触らない
- [implement] 07:23〜20:32（JST）の約 13 時間、作業が止まっていた — 記録では、Claude の次の返事を作る通信を出したまま進んでいない。ユーザーによると PC のスリープ。確認画面やテストの待ちではない
- [implement] /simplify（4 観点）の指摘のうち、動きを変えない整理（既定値の一元化・run_step・exp_ids の廃止・判定の分け方・テストの重複）は直した。費用の列を記録に足した。範囲を外れる・方式を変える指摘は見送り、retro で扱う（計画変更記録 3）
- [review-gate] 基本レビュー 1 回目は CI の Harness Tests が失敗（test_review_commit_lifecycle.sh の TC-C1-shellcheck。手元に shellcheck が無く、手元の run-all ではこの項目が通っていた）— 手順どおり fix-loop へ
- [fix-loop] 案 A（読み込み行に `disable=SC1091` を足す）で直した。診断・実装・テストのレビューはすべて PASS。直したファイルは 2 本なので軽微例外は使わなかった — 既存の書き方と同じで挙動を変えない。手元と CI の検査の食い違い（手元に shellcheck が無いと黙って SKIP）と、コメントだけの修正にも 3 つのレビューがかかる重さは、ユーザーとの対話（10-26）を踏まえて retro で扱う
- [review-gate] 基本レビュー 2 回目（`I197_code_review_20261026_2124.md`）は BLOCKER（Blocker 1・High 1・Medium 6・Low 2。RISK: NO で敵対的レビューの対象外）— fix-loop へ（review-gate ⇄ fix-loop は 2 回目）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
