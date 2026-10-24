---
name: code-review
description: "/test の前に実行。CI 完了を待機し、実装が受け入れ条件・セキュリティ・ベストプラクティスを満たしているかレビューする。高リスク判定 YES かつ FINAL_VERDICT OK の場合は敵対的レビューステージ（反証マンデートの多観点サブエージェント）を自動起動する。Blocker があれば差し戻す。"
argument-hint: "I###"
disable-model-invocation: true
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

### 3-0. 対象と上限

- 対象は `ADVERSARIAL_STAGE: REQUIRED` のときだけ（判定の正は `scripts/claude/code-review.sh`。アプリの高リスク条件、またはハーネスの「GitHub から復旧できない例外」に関わるファイルの変更）。
- 上限: **1 体 15 分・攻め筋は 1 体 3 本まで・1 周 3 体（固定 3 観点）・イシュー全体で 2 周まで**（`/code-review` をやり直しても数え直さない）。

### 3-1. 起動

1. 周回の残りを数える: 同じイシューの `docs/reviews/I###_adversarial_review_*.md` をすべて Read し、各記録の `ROUNDS:` 行の数を合計する（`ROUNDS:` 行が無い記録〔I181 より前の形式〕は、記録の中の周の見出しの数を数える。見出しも無ければ 1 周として数える）。合計が 2 以上なら起動せず、3-2 の「上限到達」へ進む。
2. 見直す範囲を決める: 過去の記録があれば、いちばん新しい記録の `REVIEWED_COMMIT:` の SHA を `{REVIEW_BASE}` にする（2 周目は前回からの差分だけ）。無ければ `origin/develop`。
3. この周の開始時の HEAD を控える（記録の `REVIEWED_COMMIT` になる）:
   ```bash
   git rev-parse HEAD
   ```
4. `.claude/review-agents/adversarial-reviewer.md` を Read し、プレースホルダ {ISSUE}／{PERSPECTIVE}／{KNOWN_FINDINGS}／{REVIEW_BASE} を埋める。固定 3 観点のサブエージェントを Agent ツールで **1 メッセージで `run_in_background: true` で起動**し、同じメッセージでタイマーを Bash ツールの `run_in_background: true` で起動する:
   ```bash
   sleep 900
   ```
   - 固定 3 観点（毎周必須・動的な観点の追加はしない）:
     1. ロジック回避・実機 repro（ガード・判定・分岐の抜け道を temp repo で実測）
     2. テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）
     3. 要件・脅威モデルの網羅漏れ（AC の抜け・想定攻撃・エッジケース）
   - {KNOWN_FINDINGS} には先行周回で報告済みの全 findings の一覧（オーケストレーターが周回ごとに集約保持しているもの。同一イシューの過去の `docs/reviews/I###_adversarial_review_*.md` が存在する場合はそれも Read して合算）を充てる。
5. 起動時に返った 3 体のエージェント ID とタイマーのタスク ID を控えておく。結果は完了通知で受け取る。
   - タイマーの完了通知が先に来たら: 完了通知がまだ来ていないエージェントの ID を `TaskStop` の `task_id` に渡して止め、その観点を記録に「時間切れ（報告なし）」と書く。時間切れの体は新規 Critical/High 0 として数えるが、時間切れだったことを最終報告に必ず書く。
   - 3 体とも先に終わったら: タイマーのタスク ID を `TaskStop` の `task_id` に渡して止める。

### 3-2. 周回と上限

- 3 体の `NEW_CRITICAL`＋`NEW_HIGH` の合計が 0 → ステージ通過。
- 1 以上 → 3-3 で修正する。修正後、通算の周回（過去の記録の `ROUNDS:` の合計＋この記録の周回）が 2 未満なら、`{REVIEW_BASE}` をこの周の `REVIEWED_COMMIT` にして 3-1 の 3〜5 で 2 周目を起動する（修正した差分だけを見る。修正の妥当性も反証対象）。
- Medium/Low だけなら次の周に進む理由にしない（記録に残し、High に直結する Medium だけ 3-3 で直す）。
- **上限到達**（通算 2 周で Critical/High が残る）: 自動 OK にせず、最終判定を HIGH 以上に固定して停止する（「上限到達・未収束」と明記）。その際、残った指摘と過去の周の指摘を**種類ごとに集計**する（種類 = 「どの仕組みのどんな穴か」を 1 行で名付けたもの。例: 「文字列の解析が bash の構文の一部を取り違える」）。ユーザーへの選択肢は次の順に出す:
  1. 同じ種類が 2 周続いていれば、先頭に「**止める場所・方式の見直し**」（列挙で塞ぐ方式の限界の疑い）
  2. 修正してもう 1 周（ユーザーの承認で 1 周だけ延長）
  3. 残りを受け入れて進む（理由を記録）

### 3-3. findings の修正（依頼側が実施）

- 修正は本スキル（メインセッション）が Edit/Write で行う。レビューアのサブエージェントには修正させない。
- 修正は findings 対応の範囲に限定し、修正内容を記録に残して commit する。
- 設計判断が必要な findings はユーザーに確認して停止する（勝手に設計変更しない）。

### 3-4. 記録・結線

- 記録: `docs/reviews/I###_adversarial_review_<YYYYMMDD_HHMM>.md` を Write で作成する（周回ごとの観点・エージェント数・時間切れの有無・findings・修正内容）。最終行の直前に機械可読行 `REVIEWED_COMMIT: <この記録の最後の周の開始時の HEAD の SHA>` と `ROUNDS: <この記録の周回数>` を 1 行ずつ、最終行に `VERDICT: <BLOCKER|HIGH|OK>` を 1 行だけ書く。
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
- REQUIRED: ステージ通過（新規 Critical/High 0 の周回）・上限到達（種類別集計つきのエスカレーション）・設計判断のユーザー確認、のいずれかで停止
