# I530 レビュー: マージ前の最終確認の CI 待ちをレビュー段階の wait_ci に一本化する

## 変更概要
- マージ前の最終確認（`pr-base-sync.sh final`）の CI 待ちを、自前の判定（`ci_wait`）からレビュー段階の `code-review.sh` の `wait_ci` を呼ぶ形（`run_wait_ci`）に置き換えた。CI のチェックが未登録・一部だけのときに待たずに合格する穴をふさいだ

## 変更点
- `scripts/claude/pr-base-sync.sh`: `ci_wait` を消し `run_wait_ci`（別の bash で `wait_ci` を呼び、戻り値と `CI_WAIT:` 行を今のメッセージ・exit 1 に対応させる）を置いた。`PBS_CI_TIMEOUT`・`PBS_CI_INTERVAL` と I498 の既定の読み込みを消した。`CLEAN|HAS_HOOKS` でも CI を待つ
- `scripts/claude/code-review.sh`: `wait_ci` の前のコメントの並びと文言だけ（動きは変えない）
- `scripts/claude/tests/test_pr_base_sync.sh`: スタブを `wait_ci` の呼び方に合わせ、T22〜T26 と失敗の注入 FG1・FG2 を足した
- `scripts/claude/tests/test_i498_ci_wait_timeout.sh`: 新しい形に合わせた（環境変数・T5・T6・FG1〜FG3）
- `docs/reviews/backlog/I498.md`（F1・F2・F3・R1）・`I224.md`（F1）: 同梱して直した行を消した

## 影響範囲
- Backend/Frontend/DB: なし
- Config: ハーネスのスクリプト（`pr-base-sync.sh`・`code-review.sh` のコメント）とテスト 2 本・一覧 2 本

## テスト結果
- 自動: review-gate 2 回目で決定論ゲート 15 行すべて exit=0（test_pr_base_sync 26 ケース・test_i498 13 項目・test_i193・構文・不在の確かめ）・CI 全ジョブ合格（CI_WAIT: OK）。test-gate の gate-check OK
- 手動: No.1（Claude）は close の手順 5.5 の実際の `final` の出力で確かめる（test-gate の時点では PR が Draft で確かめにならない）

## 計画との差分
- あり（テストの組み方と期待の細部だけ。計画書の計画変更記録の 2〜5 行目）: FG2 の T3 を見ない・失敗の注入を `CASE_SCRIPT` で 1 ケースずつ流す形・T4 の正規表現・shellcheck を pre-commit 経由で

## ロールバック
- この PR のコミットを revert する

## 自律判断の記録
- [plan] I498（PR #528・マージ依頼中）のブランチを取り込んで作った — このイシューの変更点が I498 の上にしかない。#528 のマージの後にこのイシューのマージを依頼する
- [plan] 最終確認の合格の道すべて（`CLEAN|HAS_HOOKS` を含む）で CI を待つことにした — イシューの目的「全部そろって合格するまで待ってから合格と言う」の範囲。CI が終わっていれば照会 1 回で済む
- [plan] 上限・間隔の上書きを `CI_WAIT_TIMEOUT`・`CI_POLL_INTERVAL` 1 つにし、`PBS_CI_TIMEOUT`・`PBS_CI_INTERVAL` を消した — 使うのはテストだけで、2 つの名前は review-gate と値がずれる元
- [plan] 一覧の I498 F1・F2・F3・R1 と I224 F1 を同梱、I498 F4 は残した — 理由は計画書 §9
- [plan-review] 計画レビュー OK（Info 3 件）。Info の 1 件目（失敗のメッセージに gh pr checks の文字があると TC-03 が落ちる）は文言を直した。残り 2 件は対応不要 — 相対パスの前提は wait_ci が元から持つ・TC-05 の形のずれは TC-05 自身が先に落ちる
- [implement] I498 のテストの FG2 で T3 を見ないことにした — final が `wait_ci` そのものを呼ぶようになり、既定を変えても 2 つの上限が食い違わなくなった（AC2 の結果）。T3 自体は、pr-base-sync.sh に別の既定を書き戻したとき（FG1）を捕まえるので残す
- [implement] /simplify の 4 観点の指摘のうち、失敗の注入の組み方（全体の流し直し → 1 ケースずつ）・FG2 の T3 の確かめ・古いコメントと名前を直した。見送り: 共有ファイルへの切り出し（I498 で、code-review.sh を写して動かす既存のテスト 5 本以上が壊れるため採らないと決めた）・`wait_ci` に上限の行を出させる（`wait_ci` の変更はイシューの範囲外。式は code-review.sh 本体の時間切れのメッセージと同じ書き方）・合格の 2 つの分岐をまとめる（✅ の文言が変わり、手動テストの期待とずれる）・BEHIND の後に待ちを 2 回通る（安全側に倒した意図した形・一覧 I498 F4 と同じ話）・テストが `wait_ci` の内側の呼び方に合わせたスタブを持つ（本物の `wait_ci` を通して穴が塞がることを確かめるのが目的）
- [review-gate] 1 回目（4e9a85c7 の記録）は FINAL_VERDICT: BLOCKER — 台帳は OK（Low 4 件）だが、決定論ゲートの 3 行（`pre-commit run shellcheck …`・`bash -c "…"` 2 行）が実走できる形でなく fail-closed。fix-loop でゲートの書き方を直す
- [fix-loop] 案 A（ゲートの行を `classify_gate` が実走する形に分け、shellcheck は `bash -n` に置き換える）で直した — 診断レビュー PASS（`docs/reviews/I530_fix_diagnosis_review_20261116_1239.md`）。安全境界（`classify_gate`）を広げず、新しいテストのファイルも作らない最小の形。shellcheck は pre-commit と CI が流す
- [review-gate] 2 回目（差分のレビュー・`docs/reviews/I530_code_review_20261116_1242.md`）は FINAL_VERDICT: OK・ゲート 15 行すべて exit=0・CI_WAIT: OK・高リスク NO（敵対的レビュー不要）。台帳の残り Low 4 件（F1〜F4）は retro が振り分ける
- [test-gate] 手動テスト No.1 は close の手順 5.5 で確かめる（計画書 §6）。Human の項目は無いので retro へ進む
- [retro] 台帳の残り 4 件（F1・F2・F3・F4・どれも Low・再現なし）→ `docs/reviews/backlog/I530.md`（後続イシュー行きは 0 件）
- [retro] 改善案「決定論ゲートの行が実走される形かを書いた直後の検査で止める」→ 採用（新規起票 I535・#535）— 実害あり（review-gate 1 周＋fix-loop の手戻り）・同じ形が過去 4 件（I095・I122・I174・I178）で今回 5 回目・決定論のチェック（`--lint-auto-test` に `classify_gate` の分類を足す）で塞げる・同梱できる既存のイシューが無い（#523 は関係するテストを選んで流す話・#445 は run-all の話）
- [retro] 改善案「I498 の上に積んで作った進め方」→ 見送り — 問題は起きていない（#528 のマージを待ってから依頼するだけ。close で確かめる）
- [retro] 改善案「確かめ用のスクリプトがサンドボックスの中で走り test_i193 の F9 が落ちた」→ 見送り — 私の一時の確かめ方の都合で、review-gate・run-all の流し方では起きない。手戻りなし

## 振り返り

### かんたんなまとめ
- 良かった点:
  - 計画の前に、今の最終確認が「チェックが無いのに合格」と言う穴をスタブで再現した（直す対象を確かめてから計画した）
  - テストを先に書き、直す前のスクリプトで不合格になることを見てから直した。壊した写しで本当に捕まるかも同じテストの中で確かめている
  - 軽い指摘の一覧の 5 件（I498 の 4 件・I224 の 1 件）が、同じ直しで自然に片付いた
- 今回の問題への直接の対処: レビューの 1 回目が、コードではなく「テスト文書に書いた確かめの行の書き方」で止まった。レビューのスクリプトは決まった形の行しか走らせない（安全のため）が、その決まりに照らさずに、つないだ行・`bash -c` で包んだ行を書いた。→ 行を 1 つずつの形に分けて直し、レビューを通り直した
- 同じ問題を次回から防ぐ改善: 同じ止まり方が過去にも 4 回あった。書いた直後に走る検査は同じ文書を読んでいるのに、行の形は見ていなかった。→ 書いた直後の検査が、レビューと同じ分類で「走らない形の行」を知らせるようにするイシューを起票した（I535）

### 詳細版
#### 良かった点
- 計画前のスパイクで穴を再現（スタブで exit 0）。新しい呼び方も同じスパイクで確かめた
- TDD（T22〜T26 の赤を確認してから実装）・失敗の注入をテスト内に組み込み
- 一覧 I498 F1/F2/F3/R1・I224 F1 を同梱で解消

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | ドキュメント | auto_test のゲートの行を `classify_gate` の形に照らさずに書いた（`&&`・`bash -c`・`|`・`pre-commit run`） | fix-loop で `grep`／`! grep`／`bash -n` の 1 行ずつに分けた（ce03e80f）。ゲートの節の下に決まりを 1 行書いた |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | スキル・規約（決定論チェック） | 「実走される形」の決まりが review-gate の分類の 1 か所にしかなく、書いた直後の検査（同じ文書を読む）が呼んでいない | 書いた直後の検査（`--lint-auto-test`・PostToolUse のフック経由）で、ゲートの行を同じ分類関数にかけ、実走されない形の行を exit 1 で知らせる（分類の写しは作らない）→ I535（#535） | `scripts/claude/code-review.sh`・`scripts/claude/tests/` |

#### 5 Whys（P1）
- Why 1: review-gate がゲートの 3 行を実走せず BLOCKER にした → 行が `classify_gate` の ALLOW の形でなかった
- Why 2: 書くときに形を確かめなかった → 形の決まりを当てる仕組みが review-gate にしか無い
- Why 3: 書いた直後の検査は宣言漏れ（見出し）だけを見る作りで、行の形の分類を呼んでいない（I226 で見出しの検査だけを足した）
- 抽象化: 「ある工程で fail-closed に判定する決まりを、その入力を書く時点の検査が同じ関数で当てていない」→ 書く時点で同じ判定関数を呼べば、後の工程の 1 周を節約できる

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: fix-loop

STAGE_DONE: fix-loop NEXT: review-gate

STAGE_DONE: review-gate NEXT: test-gate

STAGE_DONE: test-gate NEXT: retro

STAGE_DONE: retro NEXT: close
