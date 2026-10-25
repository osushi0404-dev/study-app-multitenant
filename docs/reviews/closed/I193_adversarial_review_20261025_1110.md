# 敵対的レビュー [I193]（2026-10-25 11:10）

## 1 周目
- 起動のきっかけ: 基本レビュー `I193_code_review_20261025_1053.md`（FINAL_VERDICT: OK・ADVERSARIAL_STAGE: REQUIRED。`.github/workflows/ci.yml` を変えたため）
- 見直す範囲: `origin/develop` から。I194 までの暫定の決まり（ユーザー決定）で、「GitHub から復旧できない例外」のファイルの変更（`.github/workflows/ci.yml` の `harness-tests` ジョブ）と、その結果を使う `code-review.sh` の `expected_ci_jobs`・`wait_ci` に絞った。範囲外の指摘は High に数えない
- 脅威モデル: 普通の書き方の事故を止める（意図的な回避は対象外）。ci.yml はフォークの PR から動くので、秘密情報・書き込み権限の漏れは対象
- エージェント数: 3（固定 3 観点）・上限 15 分。時間切れ: なし（3 体ともタイマーより先に報告）

### 観点 1: ロジック回避・実機 repro — NEW_CRITICAL 0・NEW_HIGH 0
- Medium: `expected_ci_jobs` は、途中のワークフローのファイルが読めない（名前の変更・壊れた YAML）と、それまでに読めた分だけで期待の一覧を作る（`2>/dev/null || true`）。`wait_ci` は一覧が空のときしか止めないので、読めなかったファイルのジョブを待たずに `CI_WAIT: OK` になりうる（止まらない側）。今回足した Harness Tests は ci.yml 側なので守られている。静的な読解（実機の再現は環境の制約で未実施）
- Low: 期待の一覧は PR 自身の ci.yml から作るので、PR でジョブを消すと待ちからも消える（ci.yml は例外のパスで人のレビューに回る。意図的な回避に近い）
- Low: `pip install pyyaml` の版が固定されていない（落ちる側に倒れる）

### 観点 2: テストの false-green・tautology — NEW_CRITICAL 0・NEW_HIGH 0
- 反証失敗（新しい指摘なし）。`run-all.sh` は失敗 1 本・0 本で exit 1（F9 で固定）。ci.yml は `continue-on-error`・`|| true` 無しで直接呼ぶ。全 `test_*.sh` は失敗を終了コードに反映する。C 系の期待値はテストの中で作ったワークフローとスタブの gh から決まり、実装の写しではない

### 観点 3: 要件・脅威モデルの網羅漏れ — NEW_CRITICAL 0・NEW_HIGH 0
- Low: `pip install pyyaml` の版の固定なし（観点 1 と同じ）
- 問題なしと確かめたもの: トリガーは `pull_request`（`pull_request_target` ではない）・全体に `permissions: contents: read`・秘密情報を使わない・`fetch-depth: 0`・他のジョブに依存しない・`timeout-minutes: 30`・必須チェックの手順書（branch-protection-setup.md）とジョブ名が一致

## 判定
- 3 体すべてが報告し、NEW_CRITICAL＋NEW_HIGH の合計は 0 → ステージ通過
- 修正: なし（OK の周の後に差分を足さない）。Medium 1 件・Low 2 件は retro で扱う（Medium は止まらない側の穴だが、GitHub の必須チェックが最後の守りとして残り、High に直結しない）

REVIEWED_COMMIT: 102d990aa439d53510acaa00dac6d3619be14519
ROUNDS: 1
VERDICT: OK
