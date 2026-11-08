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
- 自動: CI 全緑（Harness Tests は 1 回目が外部の 503 で落ち、流し直しで pass）。TC-01（S1〜S11・FG 4 件）・TC-02a/b・TC-03（関係するテスト 6 本）は手元で全 PASS
- 手動: M-01〜M-04 すべて OK（Claude）。実走で I222 を #427（I427）として登録し直し、使い捨ての clone で `/plan-issue` の最初のコミット（写し 1 ファイル）まで通した。Human の項目なし

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
- [review-gate] 1 回目の `code-review.sh` は `CI_WAIT: FAIL` で止まった。落ちたのは Harness Tests だけ（ほかの 5 ジョブは pass・E2E は実行中）。原因は I221 の変更ではなく、CI が shellcheck-py（v0.10.0.1）を入れるときの shellcheck 本体のダウンロードが HTTP 503 を返すこと（手元で同じ組み立てを試して同じ 503 を確認）。develop の CI（2026-11-08 09:25・I227 のマージ後）も同じ理由で落ちている。GitHub App の鍵では失敗したジョブを流し直せない（`Resource not accessible by integration`）。fix-loop で直すコードが無く、CI の設定（`.pre-commit-config.yaml`・`.github/`）を変えるのは止める条件 2 に当たるので、`STAGE_DONE:` を書かずに止める（止める条件 3）。手元では関係するテスト 6 本（TC-03）が全 PASS
- [review-gate] ユーザーが PR の画面で失敗したジョブを流し直して全緑になった後、記録のコミットを送って `code-review.sh` をやり直した: `CI_WAIT: OK`・`FINAL_VERDICT: OK`・`ADVERSARIAL_STAGE: NOT_REQUIRED`（`docs/reviews/I221_code_review_20261108_2146.md`）。台帳は Medium 3（F1 grill-me で書き戻しの失敗でも下書きを消す・F2 issue-bootstrap で登録の失敗を確かめずに下書きを消す・F3 計画開始後の grill-me が写しを既存ファイルの経路で GitHub に書き戻す）・Low 7。どれもハーネスの止める条件に当たらないので fix-loop に回さず、retro が後続へ振り分ける
- [test-gate] M-01〜M-04 を Claude が実施し、すべて OK。M-01 で I222 を #427（I427）として登録し直した。全ワークツリーの `git status` は見張りが他のワークツリーへの git を止めるので、時刻の目印と find で「手元にファイルが増えていない」を確かめた。M-03 の使い捨ての clone は、作者名の設定が無かったので clone の中だけに設定してコミットした。clone のフォルダの削除は `rm -rf` に見張りの承認が要るので行わず、セッションのスクラッチパッドに残した（リポジトリの外）
- [retro] 台帳の残り: F1・F2・F3 → #428（I428・「I221 のレビューの残り」として 1 件にまとめて起票。判定の仕組みには当たらないが、新しい流れで毎回通る手順なので本文に「ハーネスの次の作業で先に行う」と書いた）／F4〜F10 → `docs/reviews/backlog/I221.md`
- [retro] CI の Harness Tests が shellcheck の配布元の 503 で落ち、App の鍵では流し直せなかった件 → #429（I429）で起票（実害あり: 流れが止まり、ユーザーの手作業が要った。同梱先の既存イシューが無い。`.github/*` と App の権限は安全装置なのでユーザーの判断を grill-me で聞く）
- [retro] 見送り: (a) 計画の環境前提で `jq` があると書いた — 実装の最初のテストで捕まり、手戻りは置き換えだけ（feedback: その場で捕まった見逃しに手順を足さない）。(b) 見張りが、python の本文の中の `git` の文字・スクラッチパッドの `rm -rf`・他のワークツリーへの読み取りの `git -C` を止めた — どれもその場で別の手段に替えて進め、損失は無い。見張りの作り込みは増やさない（feedback: ローカルの安全装置は最小限）。(c) F1〜F3 が計画レビューを通った — コードレビューがその場で捕まえた。観点を足さない
- [retro] I189（#321・同時起票の番号の衝突）は I221 で吸収した（番号を GitHub が振る）。#321 は bot の停止で見えないので、bot が戻った後に閉じる（close で報告するやり残しに入れる）
- [retro] I222.md（app-1 の未追跡のファイル）は、#427 で登録し直したので使わない。消すかはユーザーの片付けに任せる（close で伝える）
- [close] base 追従は不要（BLOCKED・BEHIND でない）。gate-check は OK。記録（イシュー・計画・テスト・レビュー・日時つきのレビュー記録 3 件）を closed へ移し、計画書のレビュー結果のリンクを closed 向きに直した。I221 自身の close の移動（既存のイシューファイルの経路）はこの手順で通った（M-04 の close の分）。PR の説明をテンプレートで更新した

## 振り返り

### かんたんなまとめ
**良かった点**
- 計画の前に、手元のファイルをやめて失うもの（本文の変更の履歴・ネットワークなしで読めること・完了の記録）を実際に試してから決めた（理由: GitHub が本文の全版を残すこと・PR のマージでイシューが閉じることを確かめたので、補い方に迷いが無かった）
- 計画のレビューが「番号の境目を I400 にすると、#400〜#426 の既存のイシューを別の番号で写してしまう」を見つけた（理由: 実装の前に直せた。題名でも見分ける二重の守りにできた）
- 本物のイシュー（I222 の登録し直し）で、起票から `/plan-issue` の最初のコミットまでを通した。この振り返りの 2 件の起票も新しい手順で行い、手元にファイルは増えていない

**今回の問題への直接の対処**
- 新しい起票と grill-me の手順が、GitHub への書き込みが失敗しても下書きを消してしまう／計画を始めた後に grill-me を流すと、写しの注記を GitHub に書き戻してしまう。コードレビューで見つかったが、決まりでは止める指摘に当たらなかった。→ 後続のイシュー #428 にまとめた（新しい流れで毎回通る手順なので、ハーネスの次の作業で先に行う）
- CI のハーネスのテストが、shellcheck の配布元の一時的な障害で落ち、Claude の権限では流し直せずに流れが止まった（ユーザーに画面で流し直してもらった）。→ #429 で起票。CI の設定と GitHub App の権限は安全装置なので、直し方はユーザーに聞いて決める

**同じ問題を次回から防ぐ改善**
- 新しく足すものは無し。`jq` が無かったこと・見張りに止められた操作・レビューで見つかった 3 件は、どれもその場で捕まえて別の手段に替えられ、損失が無かったため

### 詳細版
#### 良かった点
- スパイク（userContentEdits・closedByPullRequestsReferences・PR 番号の `gh issue view`）で根本原因 ①〜③ の補い方を計画前に確定した
- plan-review の Warning 1（境目と既存の番号の重なり）で、境目 I427＋題名の拒否の二重の判定にした
- /simplify の 3 観点（再利用・簡素化・高度）が同じ重複（探索の 3 重化）を挙げ、`issue-source.sh path` に寄せた
- 実走: #427（I222 の登録し直し）・#428・#429 を新しい issue-bootstrap で登録。手元の未追跡のファイルは 0 件

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | スキル・規約 | スキルの手順のシェルの断片が、外部への書き込み（gh issue create / edit）の成否を見て後片付けをする形になっていない。写しと既存のイシューファイルを置き場所で見分けていない | #428（I428）で起票（台帳 F1〜F3） |
| C2 | 予期しない問題 | CI が毎回ネットワークから shellcheck の本体を取得し、配布元の障害で落ちる。App の鍵に Actions の書き込みが無く流し直せない | #429（I429）で起票（ユーザーの判断が要る） |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| - | - | 採用なし（見送りの理由は自律判断の記録 [retro] の行） | - | - |

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
STAGE_DONE: close NEXT: merge
