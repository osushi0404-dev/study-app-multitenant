# I207 レビュー: 台帳の残りを捨てるときに目印・重大度が消える穴を直し、軽い指摘は後続イシューにせず一覧へ回す

- 計画書: docs/plans/open/plan_I207.md
- イシュー: docs/issues/open/I207.md（#346）
- Draft PR: #347

## 変更概要
台帳の残り（止めない open の指摘）の番号の行を、同じ回の何行目でもその行の中身だけで扱うようにした。resolved は前の行へ、止める中身の open は新しい番号へ、止めない中身の open は新しい行を作らず止める側の値（重大度・SECURITY・REPRO・STOP・RISK）だけ前の行へ合流する（F1・F2）。retro の手順 4-0 は、再現のある Medium 以上・SECURITY=yes・アプリ本体だけを後続イシューにし、それ以外を軽い指摘の一覧（`docs/reviews/backlog/<起点>.md`）に回すようにし、計画（plan-issue）で一覧の該当行を見る決まりを足した。I206 の F3〜F6 を一覧の最初の行にした。

## 変更点
- `scripts/claude/code-review.sh`: `_LEDGER_PY` の `update`（`merged()` に合流を共通化・台帳の残りの番号の行の扱い）
- `scripts/claude/tests/test_i202_ledger_cleanup.sh`: I207 の節（P1〜P6・D1〜D3 と FG）。FG-L6・FG-N2・FG-N3 の置き換え前の文字列
- `.claude/skills/retro/SKILL.md` 4-0: 重さで後続イシューと一覧に振り分ける（grep 2 本）
- `.claude/skills/plan-issue/SKILL.md`: 「台帳の残りの一覧」の節
- `docs/runbooks/review-rules.md`・`.claude/agents/code-reviewer.md`・`.claude/skills/review-gate/SKILL.md`: 振り分け先の文言
- `docs/reviews/backlog/I206.md`（新規）: I206 の F3〜F6

## 影響範囲
- Backend/Frontend/DB: なし
- Config/Infra: ハーネスだけ（`scripts/claude/code-review.sh`・`scripts/claude/tests/test_i202_ledger_cleanup.sh`・`.claude/skills/retro/SKILL.md`・`.claude/skills/plan-issue/SKILL.md`・`.claude/skills/review-gate/SKILL.md`・`.claude/agents/code-reviewer.md`・`docs/runbooks/review-rules.md`・`docs/reviews/backlog/I206.md`〔新規〕）

## テスト結果
（test-gate の後に書く）

## 計画との差分
- 計画変更記録 1: 計画レビューの Warning（表を行ごとの規則に揃えて P6 を追加）
- 計画変更記録 2: P3・P4・P6 の入力に F1 の resolved を足した（合否を F3 だけで決めるため）・FG-P4 の写しの形・一覧の確認（F4・F5 は残す）

## ロールバック
- PR を revert する（ハーネスのスクリプト・テスト・文書・一覧ファイルだけ）

## 自律判断の記録
- [plan] ブランチ名を `feature/I207-ledger-backlog-routing` にした — イシューの 2 つの目的（台帳の直し・一覧への振り分け）を短く表す
- [plan] 台帳の残りの番号の行は、同じ回の前の行に関係なく行の中身だけで決める（`seen` の近道を外す）— F2 と同じ箇所の止まらない向きの穴 2 つ（resolved → 止める中身・止める中身 → resolved）も同じ根本で消える（計画書 4.1・9）
- [plan] 一覧は `docs/reviews/backlog/<起点のイシュー>.md`、見る場所は plan-issue のスキル — 並行のワークツリーで衝突せず、close の glob にも当たらない。計画を作るスキルなので必ず通る（計画書 9）
- [plan] 手動テストは一覧と計画のコマンドの 1 件だけ。このイシューの retro で新しい振り分けを使ったことは retro・close で記録する — test-gate は retro の前なので確かめられない
- [plan-review] 計画レビュー OK（高リスク判定 No）。Warning 1 は表を行ごとの規則に揃えてテスト P6 を足し、Warning 2 はパイプの grep が承認なしで通ることを check-permission-prompt.sh で確かめて形を変えなかった — 方式・範囲・受け入れ条件は変えないので再レビューなし（計画変更記録 1）
- [implement] 一覧の F4（code-review.sh）・F5（test_i202）が実装対象に当たったが残す — イシューで F3〜F6 は受け入れと決まっている（計画書 9）
- [implement] /simplify の指摘のうち、D2 のテストを retro の grep 2 本をそのまま流す形にする・FG-P1/P5 の写しを 1 つにする・書き方の揃え（yn・FG-D3）を直した — 重複・起動回数が減り、retro の実際のコマンドを確かめられる
- [implement] /simplify の指摘のうち、振り分けをスクリプトのモードにする・台帳の行に FILE を持たせる・既にある番号全般の書き直し規則を 2 通りにまとめる・`seen` を前の台帳の番号の集合に置き換える・2 つの分岐をまとめる、は見送り — 前の 3 つは計画で採らないと決めた方式の変更（計画書 8・9「大きな自作のコードを足さない」）で、止める指摘の書き直しの挙動も変わる。後の 2 つは挙動は同じだが既存の FG の置き換え前の文字列の書き直しが増えるだけ

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
