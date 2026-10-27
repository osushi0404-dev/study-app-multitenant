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
- 自動: 決定論ゲート 4 本すべて exit 0（review-gate 1 周目・HEAD 538aa78）。CI 全ジョブ pass（Harness Tests を含む）。gate-check OK。`test_i202_ledger_cleanup.sh` は実装前 fail=13（Red）→ 実装後 pass=128 fail=0
- 手動: No.1 OK（一覧の中身と計画のコマンドの当たり）。実施者はすべて Claude・Human の項目なし
- review-gate は 1 周で OK（止めない指摘 F1〜F8 は台帳に残し retro へ）

## 計画との差分
- 計画変更記録 1: 計画レビューの Warning（表を行ごとの規則に揃えて P6 を追加）
- 計画変更記録 2: P3・P4・P6 の入力に F1 の resolved を足した（合否を F3 だけで決めるため）・FG-P4 の写しの形・一覧の確認（F4・F5 は残す）

## ロールバック
- PR を revert する（ハーネスのスクリプト・テスト・文書・一覧ファイルだけ）

## 振り返り

### I207 振り返り（かんたんなまとめ）

#### 良かった点
- 計画の前に、2 つの穴を小さなスクリプトで実際に起こして確かめた（理由: 直す対象がはっきりし、テストの入力もそのまま使えた）
- 台帳の残りの行を「同じ回の前の行に関係なく、その行の中身だけで決める」形にした。その結果、イシューの 2 つの穴と同じ箇所にあった、止まらない向きの穴 2 つも一緒に消えた（理由: 特別な場合を足さず、規則を 1 つにしたため）
- レビューは 1 周で通り、人の手動テストも無く、最後まで止まらずに進んだ

#### 今回の問題への直接の対処
- 新しい振り分けを、このイシューの振り返りで初めて使った。そのとき、ある指摘の説明文に「KIND=app」という文字が入っていたため、欄の値（ハーネス・再現なし）に反して後続イシュー側に振り分けられた。原因は、振り分けの式が行全体（説明文まで）に当たること。これはレビュー役が指摘していた穴そのもので、実際に起きることが分かった。→ 決まりどおり、後続イシュー I208（#348）として起票した。重い側に倒れるだけなので害は小さいが、軽い指摘でイシューが生まれる連鎖を止めるという目的に反するため直す
- 残りの指摘 7 件（Low、または再現なし）は、イシューにせず一覧（docs/reviews/backlog/I207.md）に回した

#### 同じ問題を次回から防ぐ改善
- 新しく足す決まりはない。テストの入力の不備（合否が別の行で決まり、失敗を入れても捕まらなかった）は実装中にその場で見つかり、手戻りも無かったので、手順は足さない
- イシューで決まっていた「ハーネスの古いイシューの棚卸し」を I209（#349）として起票した

### I207 振り返り

#### 良かった点
- スパイク（scratchpad で `ledger_update` を直接呼ぶ）で F1・F2 を計画の前に再現した
- 台帳の残りの番号の行を行ごとの規則にし、`seen` の近道を外して、F2 と同じ根本の止まらない向きの穴 2 つ（resolved → 止める中身・止める中身 → resolved）も閉じた
- review-gate 1 周で OK・Human の項目なし

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | 予期しない問題 | retro 4-0 の振り分けの正規表現が LEDGER 行の全体（`\|` の後ろの要約まで）に当たる。計画 4.2 で「重い側に倒れるだけ」と許容したが、ハーネスの指摘の要約は欄の名前の文字を含みやすいことを見込んでいなかった（台帳の F2・この retro で実際に発生） | 台帳の残りの決まりで後続イシュー I208（#348）を起票。正規表現を欄だけに当てる形にし、D2 に要約に欄の名前の文字を含む行を足す |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| （なし） | | | | |

見送り:
- テストの入力の不備（P3・P4・P6 の合否が前の台帳の別の止める指摘で決まり、FG-P4 が捕まえられなかった）: 実装中に FG がその場で捕まえ、手戻りなし（2.7 の問 2）。新しい手順は足さない
- 計画の時点の「一覧の該当なし」が、同じブランチで作った一覧で実装対象に当たった（F4・F5）: 実装で確認して記録し、イシューの決定どおり残した。害なし（2.7 の問 1）

## 自律判断の記録
- [plan] ブランチ名を `feature/I207-ledger-backlog-routing` にした — イシューの 2 つの目的（台帳の直し・一覧への振り分け）を短く表す
- [plan] 台帳の残りの番号の行は、同じ回の前の行に関係なく行の中身だけで決める（`seen` の近道を外す）— F2 と同じ箇所の止まらない向きの穴 2 つ（resolved → 止める中身・止める中身 → resolved）も同じ根本で消える（計画書 4.1・9）
- [plan] 一覧は `docs/reviews/backlog/<起点のイシュー>.md`、見る場所は plan-issue のスキル — 並行のワークツリーで衝突せず、close の glob にも当たらない。計画を作るスキルなので必ず通る（計画書 9）
- [plan] 手動テストは一覧と計画のコマンドの 1 件だけ。このイシューの retro で新しい振り分けを使ったことは retro・close で記録する — test-gate は retro の前なので確かめられない
- [plan-review] 計画レビュー OK（高リスク判定 No）。Warning 1 は表を行ごとの規則に揃えてテスト P6 を足し、Warning 2 はパイプの grep が承認なしで通ることを check-permission-prompt.sh で確かめて形を変えなかった — 方式・範囲・受け入れ条件は変えないので再レビューなし（計画変更記録 1）
- [implement] 一覧の F4（code-review.sh）・F5（test_i202）が実装対象に当たったが残す — イシューで F3〜F6 は受け入れと決まっている（計画書 9）
- [implement] /simplify の指摘のうち、D2 のテストを retro の grep 2 本をそのまま流す形にする・FG-P1/P5 の写しを 1 つにする・書き方の揃え（yn・FG-D3）を直した — 重複・起動回数が減り、retro の実際のコマンドを確かめられる
- [implement] /simplify の指摘のうち、振り分けをスクリプトのモードにする・台帳の行に FILE を持たせる・既にある番号全般の書き直し規則を 2 通りにまとめる・`seen` を前の台帳の番号の集合に置き換える・2 つの分岐をまとめる、は見送り — 前の 3 つは計画で採らないと決めた方式の変更（計画書 8・9「大きな自作のコードを足さない」）で、止める指摘の書き直しの挙動も変わる。後の 2 つは挙動は同じだが既存の FG の置き換え前の文字列の書き直しが増えるだけ
- [review-gate] 基本レビュー 1 周で OK（CI 全緑・敵対的レビュー NOT_REQUIRED・docs/reviews/I207_code_review_20261027_1942.md）。止めない指摘 F1〜F8（Medium 2・Low 6、すべて再現なし・ハーネス）は台帳に残し retro へ — 止める条件に当たらない
- [test-gate] gate-check OK・委譲された重いテストなし・手動 No.1 は Claude が実施して OK。Human の項目なし — CI（Harness Tests）が全テストを流しているので手元では流し直さない
- [retro] 台帳の残り（docs/reviews/I207_code_review_20261027_1942.md）: F2 → 後続イシュー I208（#348）（要約の `KIND=app` に振り分けの正規表現が当たった。決まりどおり。判定の仕組みのファイルではなく SECURITY=no なので最優先の印は付けない）／F1・F3・F4・F5・F6・F7・F8 → docs/reviews/backlog/I207.md
- [retro] 棚卸しを I209（#349）として起票 — I207 のイシューの制約（ユーザー指示）。I188（#319）・I192（#325）の取り下げ判断も I209 に含めた
- [retro] 予防処置は新規なし — テストの入力の不備はその場で捕まり手戻りなし（feedback: 見逃しに手順を足さない）
- [retro] I208・I209 のイシューファイルはローカル未コミットのまま（ハンドオフ invariant）
- [close] base 追従は不要（BLOCKED）・gate-check OK・最終チェックで CI 全緑。PR #347 を Ready にした

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
STAGE_DONE: close NEXT: merge
