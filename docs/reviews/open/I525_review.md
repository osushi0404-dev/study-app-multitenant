# I525 レビュー: 敵対的レビューの延長を引数で受け取り、Claude の Bash からサンドボックスの外で起動できるようにする

## 変更概要
- `scripts/claude/adversarial-review.sh` が延長の値を引数 `--round-limit <N>` でも受け取り、review-gate の延長の起動を `bash scripts/claude/adversarial-review.sh --round-limit 3 I###`（サンドボックスの外に出る形）にする

## 変更点
- `scripts/claude/adversarial-review.sh`: 引数 `[--round-limit <N>] I###`（順は問わない・引数が環境変数より優先）。上限の値が 1〜3 でなければ `ADVERSARIAL_ERROR: USAGE`・exit 2（環境変数の誤った値で上限を外す穴をふさいだ）。冒頭のコメント
- `.claude/skills/review-gate/SKILL.md`: 延長の起動を `bash scripts/claude/adversarial-review.sh --round-limit 3 "$ARGUMENTS"` にし、前置きしない理由を 1 文
- `scripts/claude/tests/test_i197_adversarial_process.sh`: `run` を引数を渡せる `run_args` の包みにし、A9e〜A9i・FG-A9e・FG-A9h を足した
- `scripts/claude/tests/test_i525_skill_sandbox_form.sh`（新規）: S1〜S3・FG 4 件

## 影響範囲
- Backend/Frontend/DB/Config: なし（ハーネスのスクリプト・手順書・テストだけ）

## テスト結果
- 自動: TC-01 pass=172 fail=0（計画変更 1 の後）・TC-02 pass=7 fail=0（手元・実装時）。関係する既存テスト 6 本（i181・i193・i197 ledger・i202・i205・i224）pass=6 fail=0
- 手動: No.1 OK（前置きの形は実機で DIRTY）・No.2 OK（引数の形は DIRTY なしで周が始まり、敵対的レビュー 20261116_0229 は OK・未検証 0）

## 計画との差分
- なし

## ロールバック
- このブランチのコミットを `git revert` する

## 自律判断の記録
- [plan] 案 (a)（引数で受け取る）だけを採り、(c)（装置ファイルを数えない）は採らない — (a) だけで AC1 を満たし、(c) は安全装置の確かめを緩める
- [plan] 引数と環境変数の両方があるときは引数を採り、環境変数は残す。上限の値は 1 以上の整数だけ（環境変数の誤った値が上限を外す fail-open の穴も同時にふさぐ）
- [plan] 実機の確かめ（手動 No.2）は、このイシューの敵対的レビューの 1 周目を `--round-limit 2`（既定値）で起動して行う
STAGE_DONE: plan NEXT: plan-review
- [plan-review] 計画レビュー OK（Info 3 件は対応任意。S1 の検出範囲・fail-open の是正・worktree.md は計画で扱い済みのため直さない）
STAGE_DONE: plan-review NEXT: implement
- [implement] /simplify の 4 観点: run と run_args の重複（共通化・簡素化の 2 観点）を直し、run を run_args の包みにした。見送り: USAGE のケースのリポジトリの共有（数秒の短縮より、ケースごとに分けて互いに影響しない方を採る）・S1 を env/timeout の前置きにも広げる案・DIRTY の原因の表示（サンドボックスの検知が確実でない）・worktree.md の前置き（計画で範囲外・retro の候補）
STAGE_DONE: implement NEXT: review-gate
- [review-gate] コードレビュー OK・高リスクではない（NOT_REQUIRED）。ただし台帳 F1・F2（上限の値の確かめに上の限りが無く、桁の大きな値で上限が外れる・延長 1 周の決まりを守らない）はこのイシューの目的（上限の判定を緩めない）を崩すので、一覧に回さず直す。受け付ける値を 1〜3 にする計画変更（計画変更記録 1）→ 計画レビューをやり直す
STAGE_DONE: review-gate NEXT: plan-review
- [plan-review] 再レビュー OK（Warning 3: 実装を ^[1-3]$ に直すのは implement で行う・手動 No.2 は敵対的レビューが不要の判定だったので test-gate で必ず行う・worktree.md は retro）
STAGE_DONE: plan-review NEXT: implement
- [implement] 計画変更 1 を実装（^[1-3]$・A9g に 4 と桁の大きな値）。/simplify は省いた — 正規表現 1 行とテスト 2 行の追加だけで、整理済みの差分に重い工程を回し直さない（決定論ゲートの TC-01 は流した）
STAGE_DONE: implement NEXT: review-gate
- [review-gate] 差分のレビュー OK（F1・F2 resolved）・NOT_REQUIRED。新しい Low 2 件（F6 記録の手書き換えが前提の既存の穴・F7 4 と桁の大きな値の FG が無い〔A9g7・A9g8 そのものが古い正規表現で落ちるので回帰は捕まる〕）は retro へ
STAGE_DONE: review-gate NEXT: test-gate
- [test-gate] gate-check OK。手動 No.1・No.2 とも Claude が実機で OK。No.2 で起動した敵対的レビュー（通算 1 周・OK）は高リスクでないイシューの追加の周で、gate-check の条件には入らない
STAGE_DONE: test-gate NEXT: retro
- [retro] 台帳の残り: F3 → #520 に同梱（コメント・承認の決まりが文章だけの守り）。F4〜F7 → docs/reviews/backlog/I525.md（Low／再現なし）。判定の仕組みのファイルではない（F3 は手順書）ので「最優先」は付けない
- [retro] 計画で範囲外とした worktree.md の前置きの形 → #520 に同梱（同じコメント）
- [retro] 見送り: 自分で足した上限の値の確かめの穴（F1・F2）— コードレビューがその場で捕まえ、同じ PR で直した。手戻りは計画レビュー 1 回と実装 1 回だけで、手順・観点は足さない
- [retro] 見送り: retro の途中で、パイプを付けた gh がサンドボックスの中で動き、App の鍵を読めずに失敗した（I525 と同じ種類）— すぐに気づいてパイプなしで読み直した。実害なし。手順は足さず、メモに残す

## 振り返り

### かんたんなまとめ
**良かった点**
- 計画の前に、「環境変数を前に付けるとサンドボックスの中で動いて余計なファイルが見える」ことと「引数つきの形は外で動く」ことを、実際に流して確かめた（理由: 方式の前提が正しいと分かってから計画を書けたので、実装のやり直しが無かった）
- 手動テストで、古い書き方が実機で止まることも確かめた（理由: 新しい書き方の合格が「たまたま通った」のでないと示せた）
- コードレビューが、私が足した値の確かめの穴（とても大きな数で上限が外れる・延長 1 周の決まりを守らない）を見つけ、同じ PR で直せた

**今回の問題への直接の対処**
- 延長の値を環境変数でしか渡せず、Claude の Bash ではサンドボックスの中で動いて止まっていた。→ 引数 `--round-limit` で渡せるようにし、手順書をその形にした。受け付ける値は 1〜3 に限った（延長は 1 周だけ・誤った値で上限を外さない）

**同じ問題を次回から防ぐ改善**
- 手順書に「環境変数を前に付けた起動」を書くと、珍しい道でだけ同じ止まり方が起きる。→ スキルの手順書にその形が無いことを、自動のテストで毎回確かめるようにした（このイシューで入れた）。runbook の同じ形と、「承認のときだけ」と書いた操作が機械的には守られていない件は、食い違いを洗い出す #520 に入れた

### 詳細
#### 良かった点
- 計画前のスパイク（plan-writing-rules「外部/ハーネス挙動依存のスパイク実証」）で前提を実機で成立確認した
- 手動 No.1（失敗の注入）で No.2 の合格が空でないことを示した
- review-gate の台帳 F1・F2 を、一覧に回さずイシューの目的（上限の判定を緩めない）に照らして同じ PR で直した

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | 成果 | 延長の値を環境変数の前置きでしか渡せず、`sandbox.excludedCommands` の形に当たらない | 引数 `--round-limit`（1〜3）を足し、review-gate の手順を前置きなしの形にした（このイシューで実装済み） |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | スキル・規約 | 手順書の起動の形と、サンドボックスの外に出る形の一覧を突き合わせる仕組みが無かった | スキルの手順書に前置きの起動が無いことを決定論のテストで止める（実装済み・TC-02）。runbook への拡大と、手順書が「承認のときだけ」と書いた操作の機械的な守りの有無の洗い出しは #520 に同梱 | `scripts/claude/tests/test_i525_skill_sandbox_form.sh`・#520 |
STAGE_DONE: retro NEXT: close
