---
name: code-review
description: "/test の前に実行。CI 完了を待機し、実装が受け入れ条件・セキュリティ・ベストプラクティスを満たしているかレビューする。高リスク判定 YES かつ FINAL_VERDICT OK の場合は敵対的レビューステージ（反証マンデートの多観点サブエージェント）を自動起動する。Blocker があれば差し戻す。"
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write, Agent
---

# /code-review

## 1. 基本レビュー（決定論ゲート実走つき）

```bash
bash scripts/claude/code-review.sh "$ARGUMENTS"
```

## 2. 出力の機械判定

スクリプト stdout の固定行（`ADVERSARIAL_STAGE:` と `FINAL_VERDICT:`）で分岐する:

- `ADVERSARIAL_STAGE: NOT_REQUIRED` → 従来どおりスクリプトの案内に従い終了する（無回帰。敵対ステージには触れない）
- `ADVERSARIAL_STAGE: REQUIRED` かつ `FINAL_VERDICT: BLOCKER` または `FINAL_VERDICT: HIGH` → 従来どおり `/fix-loop $ARGUMENTS` を案内して終了する（修正後の `/code-review` 再実行で再判定する。ステージは基本レビュー通過後にのみ走らせる）
- `ADVERSARIAL_STAGE: REQUIRED` かつ `FINAL_VERDICT: OK` → 3. の敵対的レビューステージを**ユーザー操作を待たず自動実行**する

## 3. 敵対的レビューステージ（高リスク時のみ・自動起動）

実装者・基本レビューの「合格」を反証する独立ステージ。実装者の自己レビューは判定根拠にしない（docs/runbooks/review-rules.md「高リスク変更の敵対的レビューステージ」参照）。

### 3-1. 観点とサブエージェント起動

- `.claude/review-agents/adversarial-reviewer.md` を Read し、観点ごとにプレースホルダ {ISSUE}／{PERSPECTIVE}／{KNOWN_FINDINGS} を埋めて Agent ツールで**並列**起動する（1 メッセージで複数 Agent 呼び出し）。
- 固定 3 観点（毎周回必須）:
  1. ロジック回避・実機 repro（ガード・判定・分岐の抜け道を temp repo で実測）
  2. テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）
  3. 要件・脅威モデルの網羅漏れ（AC の抜け・想定攻撃・エッジケース）
- 動的観点（最大 2・任意）: diff の内容に応じて追加する（例: ドキュメント整合、権限・設定面）。
- 1 周回 = 最大 5 エージェント並列。
- {KNOWN_FINDINGS} には先行周回で報告済みの全 findings の一覧（オーケストレーターが周回ごとに集約保持しているもの。同一イシューの過去の `docs/reviews/I###_adversarial_review_*.md` が存在する場合はそれも Read して合算）を充てる。

### 3-2. loop-until-dry と上限

- 各周回で全エージェントの `NEW_CRITICAL` / `NEW_HIGH` を集計する。
- 合計 0 の周回が出たら終了（ステージ通過）。
- 1 件以上なら 3-3 の修正を行い、次周回へ（修正の妥当性も反証対象に含める＝対応後再レビュー）。
- 上限: **最大 3 周・サブエージェント総数 15**。
- 上限到達時に新規 Critical/High が残る場合は自動 OK にせず**打ち切り**とし、最終判定を HIGH 以上に固定してユーザーへエスカレーションする（「上限到達・未収束」と明記して停止）。

### 3-3. findings の修正（依頼側が実施）

- 修正は本スキル（メインセッション）が Edit/Write で行う。レビューアのサブエージェントには修正させない。
- 修正は findings 対応の範囲に限定し、修正内容を記録に残して commit する。
- 設計判断が必要な findings はユーザーに確認して停止する（勝手に設計変更しない）。

### 3-4. 記録・結線

- 記録: `docs/reviews/I###_adversarial_review_<YYYYMMDD_HHMM>.md` を Write で作成する（周回ごとの観点・エージェント数・findings・修正内容・最終行に `VERDICT: <BLOCKER|HIGH|OK>` を 1 行だけ）。
- commit（feature ブランチのみ・develop/main では commit しない）:
  ```bash
  git add docs/reviews/I###_adversarial_review_<ts>.md
  ```
  ```bash
  git commit -m "docs(I###): adversarial-review 記録"
  ```
- PR コメント（失敗時は手動実行を案内・非ブロック）:
  ```bash
  gh pr review <PR#> --comment --body-file docs/reviews/I###_adversarial_review_<ts>.md
  ```
  記録が GitHub コメント上限 65,536 文字を超える場合は、サマリ（最終判定・周回数・findings 見出し）のみを一時ファイル経由で投稿し、詳細は記録ファイルへの参照を書く。
- 最終判定 = max(スクリプト FINAL_VERDICT, 敵対ステージ VERDICT):
  - OK → 「✅ 敵対的レビューステージ通過。`/test $ARGUMENTS` を実行してください。」と案内して終了
  - HIGH / BLOCKER → 従来どおり「`/fix-loop $ARGUMENTS` を実行してください。」と案内して終了

## 停止条件

- NOT_REQUIRED: スクリプト案内の出力をもって完了
- REQUIRED: ステージ通過（新規 Critical/High 0 の周回）・上限到達の打ち切りエスカレーション・設計判断のユーザー確認、のいずれかで停止
