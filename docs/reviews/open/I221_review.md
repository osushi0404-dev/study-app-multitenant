# I221 レビュー: イシューの正を GitHub に一本化する

## 変更概要
- 新しいイシューは GitHub だけで管理する（I＋GitHub の番号・境目 I427）。起票のスキルは採番とファイル作成をやめて `gh issue create` にする。`/plan-issue` が計画開始時に本文の写しを `docs/issues/open/I###.md` に作ってコミットする。読む・写すの判断は `scripts/claude/issue-source.sh` にまとめる

## 変更点
- 新規 `scripts/claude/issue-source.sh`（path・body・snapshot・gh-number。境目 I427・PR の番号と `I###: ` の題名を拒否・写しは一時ファイル → mv）と `scripts/claude/tests/test_i221_issue_source.sh`
- `check-memo-body-paths.sh`・`issue-review.sh` に `--file`（下書き）。I### の探索は `issue-source.sh path` に寄せた。`issue-reviewer.md` は渡された本文をレビューする
- スキル: `issue-bootstrap`（下書き → レビュー → `gh issue create`・採番とファイル作成をやめた）・`grill-me`（GitHub の本文を読み書きする経路）・`plan-issue`（写しを作って最初のコミット・`Closes #` は gh-number）・`retro`（ハンドオフ invariant）
- ひな形 `docs/issues/templates/issue_template.md` の題名の行を外した
- 手順書: `workflow.md`（「イシューの置き場所」の節ほか）・`issue-flow.md`・`worktree.md`（§3・§8）・`dependency-audit.md`・`onboarding.md`
- 削除: `scripts/claude/next-issue-num.sh`・`scripts/claude/tests/test_next_issue_num.sh`

## 影響範囲
- Backend/Frontend/DB: なし
- Config: ハーネス（スキル・レビュー役・スクリプト・runbook・イシューのひな形）

## テスト結果
- 自動:
- 手動:

## 計画との差分
- あり（計画書の計画変更記録 1〜3）: 境目を I427＋題名の拒否に（plan-review）／JSON を python3 で読む・FG-S8 をやめる／check-memo・issue-review の探索を issue-source.sh に寄せる（/simplify）

## ロールバック
- PR を revert する（計画書 7）

## 自律判断の記録
- [plan-issue] 写しの置き場所を既存のイシューファイルと同じ `docs/issues/open/I###.md` にした — 後の段階を変えずに済み、close の移動で根本原因 ③ も補えるため
- [plan-issue] 新しいイシューの境目を I400 にした — 自前の最大 I228 と GitHub の次の番号 #427 の間。境目が無いと、別のワークツリーにしか無い既存ファイルの番号で GitHub の別のイシューを読むため（plan-review で I427＋題名の拒否に改めた。下の行）
- [plan-issue] 実走の起票は I222 の登録し直しにした — どのみち登録し直しが要り、I221 の後に扱うイシューのため
- [plan-issue] I189（#321）は吸収して取り下げる。#321 は bot の停止で見えないので、閉じるのは bot が戻った後 — 番号を GitHub が振るので衝突が起きない
- [plan-review] 計画レビューは OK（高リスクではない）。Warning 5 件をすべて直した（境目を I427 に・自前の番号の題名を拒否・`jq -j`・基準はカレントの git ルート・TC-02 を exit 0 の形に・仮の I900 を作るテストの全件）。方式・範囲・受け入れ条件は変えていないので再レビューはしない — 計画変更記録 1
- [plan-review] Info 1 件（下書きがスクラッチパッドにしか無い間にセッションが切れる）は見送り — 未登録なだけで作り直せる（計画のリスク表）
- [implement] JSON の読み取りを `jq` から `python3 -I` の json にした（`jq` がこの環境とハーネスの前提の道具に無い）。注入しても NG にならない FG-S8 をやめた — 計画変更記録 2
- [implement] /simplify の指摘で、`check-memo-body-paths.sh`・`issue-review.sh` の I### の探索を `issue-source.sh path` に寄せ、`issue-source.sh` とテストの重複を整理した。edit-target の命令・ラベルの目印・境目の数字を文書から外す・gh の --jq は見送り — 計画変更記録 3

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
