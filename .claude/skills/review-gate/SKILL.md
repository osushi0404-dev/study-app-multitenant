---
name: review-gate
description: "/plan-issue・/proceed の流れの中でだけ呼ぶ段階のスキル（自分から呼ばない）。CI を待ち、組み込みの /code-review（高リスク時は /security-review も）と自作のレビュー役で実装を照合し、高リスク判定 YES なら敵対的レビューを起動する。最後に STAGE_DONE を書く。"
argument-hint: "I###"
user-invocable: false
---

# review-gate（レビュー段階）

止めてユーザーに聞くのは `docs/runbooks/workflow.md`「止めて聞く条件」に当たるときだけ。それ以外で決めたことは `docs/reviews/open/$ARGUMENTS_review.md` の「## 自律判断の記録」に `- [review-gate] 決めたこと — 理由` で書く。

## 1. 基本レビュー（CI 待ち・組み込みのレビュー・決定論ゲート実走つき）

Bash ツールの `run_in_background: true` で実行し、完了の通知で結果を受け取る（CI 待ちと組み込みのレビューで、前面の実行の上限 10 分を超えうるため。背景の実行が 10 分を超えても止まらないことは 2026-10-25 に 700 秒で実測した。それより長い上限があっても、下の「判定行が無いとき」の扱いで止まる側に倒れる）:

```bash
bash scripts/claude/code-review.sh "$ARGUMENTS"
```

終了コードの扱い:
- 出力に `FINAL_VERDICT:` 行が無い（途中で止まった・背景の実行が打ち切られた）: 終了コードによらず、1 回だけ実行し直す。2 回続けば止める（止める条件 3）。判定行が無いまま先へ進まない
- exit 0: 2. へ
- exit 3（CI 待ちの時間切れ）: 1 回だけ実行し直す。2 回続けば止める（止める条件 3: 安全側の選択肢が無い）
- exit 1 で出力に `CI_WAIT: FAIL` がある: CI の失敗を直すため `STAGE_DONE: review-gate NEXT: fix-loop` を書いて終わる
- exit 1 で出力に `CI_WAIT: NOT_PUSHED` がある（PR の最新のコミットが手元の HEAD と違う）: push してから 1 回だけ実行し直す。それでも同じなら止める（止める条件 3）
- exit 1 で出力に `CI_WAIT: NO_JOBS` がある（ワークフローのジョブ名を読めない。python3 の PyYAML が無いなど）: 原因を直して 1 回だけ実行し直す。直せなければ止める（止める条件 3）
- exit 1 で出力に `CI_WAIT: NO_PR` がある（PR を調べられない・開いている PR が無い）: 原因（gh の認証・ネットワーク・PR が閉じている）を直して 1 回だけ実行し直す。直せなければ止める（止める条件 3）。CI を確かめないまま先へ進まない
- 出力に `OFFICIAL_SECURITY: FAILED` がある（高リスクの変更で組み込みの `/security-review` が動かず、HIGH になった）: 直すものが無い基盤の失敗なので fix-loop に回さず、1 回だけ実行し直す。2 回続けば止める（止める条件 3）
- それ以外の exit 1（fetch の失敗・イシューファイルが無いなど）: 出力を記録に書き、止める条件 3 に当たるかを判定する（直せる原因なら直して実行し直す）

## 2. 出力の機械判定

スクリプト stdout の固定行（`ADVERSARIAL_STAGE:` と `FINAL_VERDICT:`）で分岐する:

- `FINAL_VERDICT: BLOCKER` または `FINAL_VERDICT: HIGH` → 4. の結線で `NEXT: fix-loop`（修正の後は fix-loop が必ずこの段階に戻す）
  - **繰り返しの上限**（review-gate ⇄ fix-loop が終わらないことを防ぐ・I193）: 記録の最後の `STAGE_DONE: review-gate NEXT: fix-loop` の行が、途中に `STAGE_DONE: review-gate NEXT: test-gate` か `STAGE_DONE: implement` の行を挟まずに数えて（実装をやり直したら数え直す）、今回で 4 回目以上になるときは、止める条件 3 の安全側（範囲を狭める）として、fix-loop で直すのは Blocker・High だけにし、Medium 以下は自律判断の記録に書いて retro に回す。5 回目になるときは、fix-loop へ回さずに止める（止める条件 3。ここまで直しても新しい High が出続けるのは、止める場所・方式の見直しが要る兆し）
- `FINAL_VERDICT: OK` かつ `ADVERSARIAL_STAGE: NOT_REQUIRED` → 4. の結線で `NEXT: test-gate`
- `FINAL_VERDICT: OK` かつ `ADVERSARIAL_STAGE: REQUIRED` → 3. の敵対的レビューステージを実行する

## 3. 敵対的レビューステージ（高リスク時のみ）

実装者・基本レビューの「合格」を反証する独立ステージ。実装者の自己レビューは判定根拠にしない（docs/runbooks/review-rules.md「高リスク変更の敵対的レビューステージ」参照）。

### 3-0. 対象と上限

- 対象は `ADVERSARIAL_STAGE: REQUIRED` のときだけ（判定の正は `scripts/claude/code-review.sh`。アプリの高リスク条件、またはハーネスの「GitHub から復旧できない例外」に関わるファイルの変更）。
- 上限: **1 体 15 分・攻め筋は 1 体 3 本まで・1 周 3 体（固定 3 観点）・イシュー全体で 2 周まで**（この段階をやり直しても数え直さない）。

### 3-1. 起動

1. 周回の残りを数える: 同じイシューの `docs/reviews/I###_adversarial_review_*.md` をすべて Read し、各記録の `ROUNDS:` 行の数を合計する（`ROUNDS:` 行が無い記録〔I181 より前の形式〕は、記録の中の周の見出しの数を数える。見出しも無ければ 1 周として数える）。合計が 2 以上なら起動せず、3-2 の「上限到達」へ進む。
2. 見直す範囲を決める: 過去の記録があれば、いちばん新しい記録の `REVIEWED_COMMIT:` の SHA を `{REVIEW_BASE}` にする（2 周目は前回からの差分だけ）。無ければ `origin/develop`。
3. この周の開始時の HEAD を控える（記録の `REVIEWED_COMMIT` になる）:
   ```bash
   git rev-parse HEAD
   ```
4. 固定 3 観点のサブエージェントを Agent ツールの `subagent_type: adversarial-reviewer`（定義は `.claude/agents/adversarial-reviewer.md`）で **1 メッセージで `run_in_background: true` で起動**し、同じメッセージでタイマーを Bash ツールの `run_in_background: true` で起動する。起動プロンプトには ISSUE・PERSPECTIVE・KNOWN_FINDINGS・REVIEW_BASE の値を書く（定義の本文の {ISSUE} などはこの値に読み替えられる）:
   ```bash
   bash scripts/claude/review-timer.sh 900
   ```
   （`sleep` を直接書くと settings の許可に当たらず承認画面が出るので、スクリプトで待つ）
   - 固定 3 観点（毎周必須・動的な観点の追加はしない）:
     1. ロジック回避・実機 repro（ガード・判定・分岐の抜け道を temp repo で実測）
     2. テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）
     3. 要件・脅威モデルの網羅漏れ（AC の抜け・想定攻撃・エッジケース）
   - KNOWN_FINDINGS には先行周回で報告済みの全 findings の一覧（オーケストレーターが周回ごとに集約保持しているもの。同一イシューの過去の `docs/reviews/I###_adversarial_review_*.md` が存在する場合はそれも Read して合算）を充てる。
5. 起動時に返った 3 体のエージェント ID とタイマーのタスク ID を控えておく。結果は完了通知で受け取る。
   - タイマーの完了通知が先に来たら: 完了通知がまだ来ていないエージェントの ID を `TaskStop` の `task_id` に渡して止め、その観点を記録に「時間切れ（報告なし）」と書く。**報告の無い観点を合格に数えない**（I193: 未報告を新規 Critical/High 0 と数えると、タイマーが早く鳴っただけで偽の OK になる）。時間切れの観点だけを同じ周の中で 1 回だけ起動し直し（タイマーも同じく起動し直す）、それでも報告が無ければ、その周の VERDICT は OK にしない（HIGH。上限の数え方は 1 周のまま）。時間切れだったことを最終報告に必ず書く。
   - 3 体とも先に終わったら: タイマーのタスク ID を `TaskStop` の `task_id` に渡して止める。

### 3-2. 周回と上限

- 3 体すべてが報告し、`NEW_CRITICAL`＋`NEW_HIGH` の合計が 0 → ステージ通過（この周の記録の VERDICT は OK）。報告の無い観点が残った周は通過にしない（3-1 の 5）。
- **OK の周の後に差分を足さない**（足すと、その差分を見た OK の周が無くなり、`gate-check.sh` が通さない）。High に直結する Medium を直したいときは、上限が残っていれば直してから次の周を起動する。上限が残っていなければ直さずに記録し、振り返り（retro）で扱う。
- 1 以上 → 3-3 で修正する。修正後、`bash scripts/claude/code-review.sh "$ARGUMENTS"` を 1. と同じく背景で実行し直し（直した差分を基本レビューに通す）、通算の周回（過去の記録の `ROUNDS:` の合計＋この記録の周回）が 2 未満なら、`{REVIEW_BASE}` をこの周の `REVIEWED_COMMIT` にして 3-1 の 3〜5 で 2 周目を起動する（修正した差分だけを見る。修正の妥当性も反証対象）。
- Medium/Low だけなら次の周に進む理由にしない（記録に残し、High に直結する Medium だけ上の扱いで直す）。
- **上限を使い切った後のコードの変更**: 通算 2 周を使い切った後に（最後の周が OK で終わっていても）、人の手動テストの NG などで fix-loop がコードを直して戻ってきたときは、直した差分を見る OK の周を作れないので、下の「上限到達」と同じに止める（止める条件 3。ユーザーの承認で 1 周だけ延長できる）。gate-check も、最後の敵対的レビューの後の変更を通さない
- **上限到達**（通算 2 周で Critical/High が残る）: 自動 OK にせず、最終判定を HIGH 以上に固定して止める（止める条件 3。セキュリティにかかわる指摘を受け入れて進む判断は Claude だけではしない）。「上限到達・未収束」と明記し、残った指摘と過去の周の指摘を**種類ごとに集計**する（種類 = 「どの仕組みのどんな穴か」を 1 行で名付けたもの。例: 「文字列の解析が bash の構文の一部を取り違える」）。ユーザーへの選択肢は次の順に出す:
  1. 同じ種類が 2 周続いていれば、先頭に「**止める場所・方式の見直し**」（列挙で塞ぐ方式の限界の疑い）
  2. 修正してもう 1 周（ユーザーの承認で 1 周だけ延長）
  3. 残りを受け入れて進む（理由を記録）
  - ユーザーが 3 を選んだときだけ、受け入れの記録 `docs/reviews/I###_adversarial_review_<ts>.md` を新しく作る: ユーザーの言葉（そのまま）・日時・受け入れた指摘の一覧を書き、最終行の前に `REVIEWED_COMMIT: <受け入れた時点の HEAD>` と `ROUNDS: 0`（周回に数えない）、最終行に `VERDICT: OK`（gate-check はこの記録を読んで通す）。Claude が自分で受け入れを書くことはしない（止める条件 3）

### 3-3. findings の修正（依頼側が実施）

- 修正は本スキル（メインセッション）が Edit/Write で行う。レビューアのサブエージェントには修正させない。
- 修正は findings 対応の範囲に限定し、修正内容を記録に残して commit する。
- 要件・基本設計・UI/UX の判断が要る findings だけ、ユーザーに確認して止める（止める条件 1）。技術的な直し方は自分で決めて記録する。

### 3-4. 記録

- 記録: `docs/reviews/I###_adversarial_review_<YYYYMMDD_HHMM>.md` を Write で作成する（周回ごとの観点・エージェント数・時間切れの有無・findings・修正内容）。最終行の直前に機械可読行 `REVIEWED_COMMIT: <この記録の最後の周の開始時の HEAD の SHA>` と `ROUNDS: <この記録の周回数>` を 1 行ずつ、最終行に `VERDICT: <BLOCKER|HIGH|OK>` を 1 行だけ書く。
- commit（feature ブランチのみ・develop/main では commit しない）:
  ```bash
  git add docs/reviews/I###_adversarial_review_<ts>.md
  ```
  ```bash
  git commit -m "docs(I###): adversarial-review 記録"
  ```
- PR コメント（失敗しても止めない。GitHub のコメントの上限を超えるときは、スクリプトが一部と記録への参照だけを載せる）:
  ```bash
  bash scripts/claude/post-review-comment.sh docs/reviews/I###_adversarial_review_<ts>.md
  ```
- 最終判定 = max(スクリプト FINAL_VERDICT, 敵対ステージ VERDICT)

## 4. 結線（必須）

`docs/reviews/open/$ARGUMENTS_review.md` の末尾に 1 行足して commit/push する:
- 最終判定 OK: `STAGE_DONE: review-gate NEXT: test-gate`
- 最終判定 HIGH / BLOCKER（上限到達で止める場合を除く）: `STAGE_DONE: review-gate NEXT: fix-loop`
- 止める条件に当たって止まるときは `STAGE_DONE:` を書かない（`/proceed` で再開すると、この段階からやり直す）
