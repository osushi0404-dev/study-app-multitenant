# I498 レビュー: マージ前の最終確認の CI 待ちの上限を code-review.sh と 1 か所にまとめる

## 変更概要
- CI 待ちの上限の既定を `scripts/claude/code-review.sh` の `CI_WAIT_TIMEOUT_DEFAULT`（1980 秒）1 か所にまとめ、`scripts/claude/pr-base-sync.sh` はそこから読む
- close 手順 5.5・proceed の `merge` で、最終確認を背景の実行（`run_in_background: true`）で流す

## 変更点
- `scripts/claude/code-review.sh`: `CI_WAIT_TIMEOUT_DEFAULT=1980` を `wait_ci` の前に置き、`wait_ci` と時間切れのメッセージの `1200` をこの変数に置き換えた（計画書 4-1）
- `scripts/claude/pr-base-sync.sh`: `600` をやめ、`PBS_CI_TIMEOUT` が無いときは code-review.sh を関数だけ読み込んで既定を読む。読めない・正の整数でないときは exit 1（計画書 4-2）
- `.claude/skills/close/SKILL.md` 手順 5.5・`.claude/skills/proceed/SKILL.md` の `merge`: `run_in_background: true` で流すと書いた（計画書 4-3・4-4）
- `scripts/claude/tests/test_i498_ci_wait_timeout.sh`（新規）: T1〜T6・FG1〜FG3（計画書 4-5・auto_test TC-01）

## 影響範囲
- ハーネスのスクリプト 2 本・手順書 2 本・新しいテスト 1 本。Backend・Frontend・DB・`.github/`・`.claude/settings.json` は変えない
- review-gate の CI 待ちの既定も 1200 秒から 1980 秒に延びる

## テスト結果
- 自動: 決定論ゲート 8 行すべて exit=0（review-gate・e778d4a3）。CI 全ジョブ合格。手元では implement で関係する 4 本が合格（docs/tests/open/I498_auto_test.md）
- 手動: No.1（Claude）OK — review-gate の実際の CI 待ちが `/ 1980s` の上限で 495 秒まで待ち、`CI_WAIT: OK`（docs/tests/open/I498_manual_test.md）。人の手動テストは無し
- 実際の `pr-base-sync.sh final` の背景での実行は close の手順 5.5 で行い、結果はマージ依頼の報告に書く

## 計画との差分
- なし（`pr-base-sync.sh` の既定を読む位置は、計画書 4-2 の「`:21` の後」のとおり `LOOP_MAX` の行の後に置いた）

## ロールバック
- この PR のコミットを revert する（データ・設定の変更なし）

## 自律判断の記録
- [plan] 値の置き場所を新しい共有ファイルでなく code-review.sh の変数にした — code-review.sh を一時のフォルダに写して動かす既存のテストが 5 本以上あり、新しいファイルの読み込みを足すと写しの組み合わせを全部直す必要があるため（計画書 §9）
- [plan] 既定を 1980 秒にした（イシューの「1200 秒以上」の範囲） — CI で時間の上限を持つ一番長いジョブ（Harness Tests・30 分）より長くし、テストのジョブが延びても待ちが CI より先に諦めないようにするため（計画書 §9）
- [plan] 調べる途中で見つけた `pr-base-sync.sh` の `ci_wait` の「チェックが未登録だと待たずに通る」穴は、このイシューでは直さず retro で起票を決める — イシューの目的（待ち不足で落ちない）と逆向きの話で、マージは GitHub の承認が止めるため（計画書 §9）
- [plan-review] PLAN_VERDICT: OK（Info 3 件のみ・計画は直さない）— Info 2（TC-02 の失敗注入の結果を記録する）は implement で行う
- [implement] /simplify（4 観点）で、close の手順書の「最長 1980 秒」の数字を消し、置き場所（`CI_WAIT_TIMEOUT_DEFAULT`）だけを書く形にした — 数字の 2 つ目の写しを作らないため（計画書 4-3 の文の数字だけを外した。方式は同じ）
- [implement] /simplify の残りは見送り: `|| CI_TIMEOUT=""` の削除・時間切れメッセージを wait_ci へ移す・T3 での出力の使い回し・スタブの共通化・ci.yml の timeout-minutes との関係のテスト — どれも挙動を変えない小さな整理か、計画書 §8 R5 で決めたこと（設定の写しのテストを作らない）で、計画のコード例から外す価値が無いため
- [review-gate] FINAL_VERDICT: OK・ADVERSARIAL_STAGE: NOT_REQUIRED（docs/reviews/I498_code_review_20261116_1139.md）。Low の F1〜F4 は直さない — 止める指摘ではなく、OK の後に差分を足すとレビューのやり直しになるため。retro で振り分ける
- [retro] 台帳の残り: F1〜F4 → `docs/reviews/backlog/I498.md`（スクリプトの振り分けで全件「一覧」・後続イシュー行きは 0 件）
- [retro] `pr-base-sync.sh` の `ci_wait` がチェックの未登録で待たずに通りうる穴（計画書 §9 で見つけた）→ 一覧（`docs/reviews/backlog/I498.md` の R1）。起票しない — 実害が出ていない・マージは GitHub の承認とチェックの表示が最後に止める・直し方（`wait_ci` の期待するジョブの確かめに寄せる）が分かっているので、`pr-base-sync.sh` を次に触る計画が一覧から拾えば足りる
- [retro] 予防処置: 見送り — 同じ意味の値が 2 か所で食い違うという原因は、このイシューで値を 1 か所にし、決定論のテスト（T3・T4・FG1〜FG3）で再発を止めた。手順・観点を足す必要は無い（2.7 の問 3）
- [retro] 実装中の自分の Bash の誤り（`rm -rf` を含む複合コマンドで見張りに止められた・`sed` が一時的な bwrap のエラー）→ 見送り — その場で単体のスクリプトに書き直して手戻りなし（2.7 の問 2）

## 振り返り

### かんたんなまとめ
- 良かった点
  - テストを先に書き、直す前のスクリプトで「2 つの上限が食い違っている」と実際に落ちることを確かめてから直した（理由: テストが本当にずれを捕まえることを、直す前に示せた）
  - 値を新しいファイルに置かず、今それを持っている `code-review.sh` に置いた（理由: このスクリプトを一時フォルダに写して動かす既存のテストが 5 本以上あり、新しいファイルにすると全部を直す必要があった。既存のテストは 1 本も直さずに済んだ）
  - レビュー段階の実際の CI 待ちで、新しい上限（1980 秒）が効き、8 分 15 秒待って合格まで見届けられた（理由: この PR 自身が、直した仕組みの実地の確かめになった）
- 今回の問題への直接の対処
  - なし（受け入れ条件 4 つはすべて満たし、レビューで止める指摘も出なかった）
- 同じ問題を次回から防ぐ改善
  - 足さない。原因は「同じ意味の値を 2 か所で別々に持っていた」ことで、値を 1 か所にまとめ、ずれたら落ちるテストを入れたので、それ自体が次回の防止になっている
- 別に見つけたこと
  - 最終確認のスクリプトは、push の直後で CI のチェックがまだ登録されていないと、待たずに「合格」と言いうる。実害は出ておらず、マージは GitHub の承認が最後に止めるので、新しいイシューにはせず、軽い指摘の一覧に残した（次にこのスクリプトを触る計画が拾う）

### 詳細版
#### 良かった点
- テストの先書き（T3 が 600 と 1200 で不合格）→ 実装 → 合格。FG1〜FG3 は壊し方が当たったかを `cmp` で確かめてから不合格を見る形にし、false-green を防いだ
- 共有ファイル案を写しのテストへの影響で退け、既存の `REVIEW_LIB_SOURCE_ONLY=1` を再利用（スパイクで副作用なしを確認）
- review-gate の実行で `0s / 1980s`〜`495s / 1980s`・`CI_WAIT: OK` を観測（手動テスト No.1）

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| - | - | - | 該当なし |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| - | - | - | 該当なし（このイシューの決定論テストが予防そのもの） | - |

#### 見送り
- 「同じ意味の値の書き写し」を一般に検出する仕組み（全スクリプトの数字の既定の照合など）: 見送り — 今回の値は 1 か所にまとめ済みで、他に同種の実害が出ていない。一般の検出は誤検出が多く、`plan-writing-rules.md`「決定論テストの対象の選び方」の「設定の写しのテストを作らない」に反する
- 5 Whys（同じ意味の値の食い違い）: Why1 pr-base-sync.sh の上限が 600 のまま残った → Why2 code-review.sh の上限を延ばした I193 が、同じ値を写した別のスクリプトに気づかなかった → Why3 値が「同値」とコメントで結ばれていただけで、仕組みとして 1 つになっていなかった → 根本原因: 共有すべき設定値が複数のスクリプトに数字で写されていた（I498 固有の名前を除いても成立）→ このイシューで仕組みとして 1 つにし、テストで固定済みのため是正・予防とも追加なし

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: test-gate

STAGE_DONE: test-gate NEXT: retro

STAGE_DONE: retro NEXT: close
