# I206 レビュー: I202 のレビューの残り（台帳の番号の合流と、中身の無い指摘の増え方を直す）

- 計画書: docs/plans/open/plan_I206.md
- イシュー: docs/issues/open/I206.md（#344）
- Draft PR: #345

## 変更概要
台帳の更新で、振り直した番号がレビュー役の新しい番号と合流する穴（I202 F1）を、振り直し先を今回のレビューの番号とも重ならない番号から振る形で直した。台帳の残りを直さずに open で書き直すと中身の無い指摘が増える穴（F8）は、止める中身のときだけ振り直し（I197-F1 の守り）、それ以外は捨てる形で直した。I202 の台帳の残り 21 件は、13 件を直し、3 件（F4・F13・F22）を見送り、5 件（F15〜F19）をそのまま残した（計画書 4.0）。確かめる 2 点は I196（#331）へ引き継いだ。

## 変更点
- `scripts/claude/code-review.sh`: `_LEDGER_PY` の `update`（番号の振り方・台帳の残りの open の書き直しの扱い）・`risk`（KIND=app の目印だけ）・`split_repro`（「なし（理由）」は再現なし）。`changed_outside_records` は git の失敗で 2。一時ファイルを 1 つのフォルダにまとめ、trap を先頭へ（途中で止まっても残らない）。見せるファイルの一覧の作成の失敗で止める。入力の見出し・台帳の残りの節の文言
- `scripts/claude/adversarial-review.sh`: `flock` の存在確認（無ければ exit 2）・鍵を取った後の締め切りの確認を 2 回分に・作業ツリーの比較を鍵の中へ
- `.claude/agents/code-reviewer.md`: 台帳の残りは直していなければ書かない・新しい指摘は新しい番号で
- `.claude/skills/review-gate/SKILL.md`・`docs/runbooks/workflow.md`・`docs/runbooks/review-rules.md`・`docs/runbooks/issue-flow.md`: `/security-review` はパスの判定が YES のとき
- テスト: `test_i202_ledger_cleanup.sh` に I206 の節（N1〜N14 と FG・34 項目）。`test_i197_review_ledger.sh` の FG-R14 の置き換え前の文字列
- 引き継ぎ（このブランチの外）: `docs/issues/open/I196.md`（未追跡）と GitHub #331 の本文に「I206 からの引き継ぎ」の節

## 影響範囲
- Backend/Frontend/DB/Config: ハーネスだけ（`scripts/claude/`・`.claude/agents/code-reviewer.md`・`.claude/skills/review-gate/SKILL.md`・`docs/runbooks/`）

## テスト結果
- 自動: 決定論ゲート 5 本すべて exit 0（review-gate 1 周目・HEAD 3f66d57）。CI 全ジョブ pass（Harness Tests を含む）。gate-check OK。`test_i202_ledger_cleanup.sh` は実装前 fail=22（Red）→ 実装後 pass=106 fail=0
- 手動: No.1 該当なし（差分のレビューの周が無い）・No.2 OK（I196.md と #331 に引き継ぎ）。実施者はすべて Claude・Human の項目なし
- review-gate は 1 周で OK（止めない指摘 F1〜F6 は台帳に残し retro へ）

## 計画との差分
- なし

## ロールバック
- PR を revert する（ハーネスのスクリプト・テスト・文書だけ）

## 自律判断の記録
- [plan] 確かめる 2 点は I196（#331）の retro へ引き継ぐ（grill-me でユーザー一任「BP とサクサクの観点で問題ないやり方で」→ 待ちで閉じられない状態を作らない案を選んだ）
- [plan] 番号の合流は、振り直し先を「前の台帳と今回のレビューの番号の最大の次」から振って直す — 1 行で、レビュー役の番号の付け方を変えずに済む
- [plan] 台帳の残りの open の書き直しは、止める中身なら振り直し、それ以外は捨てる — I197-F1 の守り（止める判定）を保ったまま、中身の比較のような壊れやすい判定を足さない
- [plan] I202 の台帳の F15〜F19 はそのまま残す — 閉じたイシューの記録は書き換えず、I206 以降の判定に影響しない
- [plan] 残り 21 件は 13 件を直し・3 件（F4・F13・F22）を見送り・5 件（F15〜F19）をそのまま残す（計画書 4.0 の表） — 見逃す向きと台帳の質を落とすものは直し、止める側に倒れていて直すとコードが大きくなるものは見送る
- [plan] テストは `test_i202_ledger_cleanup.sh` に「I206」の節を足す — 一時のリポジトリ・スタブ・通しの関数をそのまま使える
- [plan-review] 計画レビュー OK（高リスク No）。Warning 1（「なし」の後の空白）・3（mktemp の失敗）は計画変更記録 1 で直し、Warning 2（N11 は配置の確認）は計画どおり — 方式・範囲・受け入れ条件を変えないので再レビューしない
- [implement] issue-flow.md にも同じ「高リスク時は /security-review」があったので直し、N13 の対象に足した（計画変更記録 2） — 消費箇所の取りこぼしを防ぐ
- [implement] 見せるファイルの一覧は `cat … &&` でつないだ（計画変更記録 3） — `{ }` の終了コードは最後のコマンドのものだけで、計画のコード例では cat の失敗を拾えなかった（N9 で判明）
- [implement] I196 への引き継ぎに「計画レビューが Yes のときは付けない決まりなので 0 件が期待値」「スクリプトは KIND=app の目印だけを数える」を足した — I196 は高リスク Yes の見込みなので、測る人が 0 件を正常と読めるように
- [implement] /simplify の指摘のうち、変数名 `k`→`kind`・古い経緯のコメントの削除・テストの重複の関数化（`f2_same`）・`basename` を `${c##*/}` に、を直した — 読みやすさと速さ
- [implement] /simplify の指摘のうち見送り: ①`changed_outside_records` を `wait $!` にする案 → 一時ファイルの方が失敗の受け方が明示的で、計画レビューを通した形 ②`branch_own_files` と共通の関数に切り出す案 → `gate-check.sh` が使う関数に手が入り、イシューの「gate-check の挙動を変えない」に触れる ③`NO_REPRO` と `NO_REPRO_HEAD` を 1 本の正規表現にする案 → I205 からの既存の判定を書き換える範囲の広がり ④`RISK=up` を書く側で落とす案 → 前の記録（rebase 後に読む）にも効かせるには読む側の条件が要る ⑤N10 の時間を縮める・N12 のリンクを必要なコマンドだけにする案 → CI での揺れの余裕と、必要なコマンドの列挙の壊れやすさを優先（テスト全体は約 58 秒で上限 120 秒に収まる） ⑥`fresh` を必要なときだけ計算する案 → 指摘は数件で負担はごくわずか
- [review-gate] 1 周目で FINAL OK・敵対的レビュー不要（`docs/reviews/I206_code_review_20261027_1815.md`）。止めない指摘 F1〜F6 は台帳に残し retro で扱う — ハーネスの止める条件の一覧に当たらない。F5 の「再現: なし（推測。…）」が REPRO=no になり、F7 の直しが実物で効いた
- [review-gate] issue-bootstrap が作った `docs/reviews/I206_issue_review_20261027_1701.md`（未追跡）をこのブランチでコミットした — I206 の記録の一部

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
