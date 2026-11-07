# I224 計画書: GitHub への書き込み（イシューの書き換え・コメント・push）の回数を絞り、短い間に集中しないようにする

## 基本情報
- **計画書ID**: plan_I224
- **関連イシュー**: #413
- **Draft PR**: #420
- **作成根拠資料**: docs/issues/open/I224.md（設計確認メモあり）
- **実装後評価**: docs/reviews/open/I224_review.md
- **作成日**: 2026-11-07

## 1. 背景/目的
- 2026-10-30 に GitHub の操作に使っていた bot が停止された。きっかけは短い間の書き込みの集中と見ている（GitHub の説明は未着）。GitHub App（I223）に移っても、同じ量と集中のしかたなら、また止められるおそれがある
- 各段階のスキルが、段階の終わりごとに「commit/push」する作りで、1 本のイシューで push が 10 回前後になる
- 目的: push を要る 3 時点にまとめ、イシュー本文の同期を grill-me の終わりの 1 回にし、同時に複数のセッションで書き込まない決まりを書く（grill-me で確定）

### 調査結果
- **原因の概要**: 「手元に記録を残す（commit）」と「GitHub に送る（push）」が、どの段階の手順でも 1 組で書かれている。送る必要があるのは GitHub が中身を見る時点（PR を作る・CI を回す・マージの前の確認）だけなのに、段階の数だけ送っている
- **実測（2026-11-07）**: I226 のブランチへの push は 21:23〜22:27 の約 1 時間に 10 回（`git reflog show refs/remotes/origin/feature/I226-revoke-check-and-g10-scope` の `update by push` の行）。最も詰まった所は 3 分半に 4 回
- **push の指示がある場所（grep `commit/push|commit・push|コミット・push|git push`・宣言と消費の全件）**:
  - スキル: `plan-issue`（54・61・66・189・190 行）・`plan-review`（14・28・35）・`design-security-review`（141）・`implement`（93・96・97）・`review-gate`（27・98）・`fix-loop`（64）・`test-gate`（63）・`retro`（168・178）・`close`（125・144・165・168）・`proceed`（15）
  - 手順書: `docs/runbooks/workflow.md`（25・50）・`docs/runbooks/plan-writing-rules.md`（230）・`docs/runbooks/worktree.md`（82・251）
  - スクリプト: `scripts/claude/pr-base-sync.sh`（final で BEHIND のときだけ merge→push。残す）。`code-review.sh`・`plan-issue-review.sh`・`fix-review-lib.sh` は記録を commit するだけで push しない
  - 対象外: `danger-ops.md:37`・`review-rules.md:180`・`plan-reviewer.md:103`・`onboarding.md:139`（push の指示ではない）
- **push を前提にしている確認**:
  - `code-review.sh` の CI 待ち（`wait_ci`）は「PR の最新のコミット＝手元の HEAD」でなければ `CI_WAIT: NOT_PUSHED` で止まる → review-gate の CI 待ちの前に push が要る（時点 ②）。push し忘れても決定論で止まる
  - `gate-check.sh`・`flow-stage.sh`・implement の 3.5（`git diff origin/develop...HEAD`）は手元の記録・コミットだけを見る → 手元のコミットだけでも壊れない
  - `pr-base-sync.sh sync`（close の step 0）は PR の状態（base が進んだか）を見るだけで、手元の未 push のコミットに関係しない
- **GitHub の上限（grill-me で「計画で確かめる」とした件）**: 公開の上限の数字は確かめていない（調べるための外部への問い合わせを足さない）。今の量（1 時間に 15 回ほど）は、記憶の上の上限（作る操作は 1 分 80 回・1 時間 500 回ほど）より 2 桁少ない。今回は数字に頼らず「要る時点だけ送る」で減らすので、計画は上限の正確な値に依存しない
- **PR へのコメント**: `plan-issue-review.sh`・`code-review.sh`・`post-review-comment.sh` が、レビューのたびに記録を PR にコメントする（1 本で 2〜5 回）。grill-me で決めた範囲（push・イシュー本文）の外で、あなたが PR でレビューを読む導線なので、今回は変えない（§9）
- **環境前提**: 新しいツールは使わない
- **既存テスト**: `scripts/claude/tests/run-all.sh` は CI（Harness Tests）が流す。新しいテストのファイル `test_*.sh` は自動で拾われる（`run-all.sh:2`）

## 2. 受け入れ条件
- [ ] 各段階のスキルが、push を 3 時点（① plan-issue の下書き PR の作成・② review-gate の CI 待ちの前・③ close の最後の確認の前）だけで行い、ほかの段階は手元のコミットだけにしている → TC-02
- [ ] イシュー本文の書き換え（`gh issue edit --body-file`）が grill-me の終わりの 1 回だけになっている → TC-02
- [ ] 1 本のイシューの push が 4 回以内（fix-loop の後の review-gate のやり直し 1 回ごとに +1）であることを実測で示す → M-01（I224 自身の implement より後）・retro での記録（次のイシュー 1 本の実測は、次のイシューの retro で行う。§9）
- [ ] 同時に複数のセッションで書き込まない決まりが手順書にある → TC-03
- [ ] review-gate の CI 待ち（PR の最新のコミット＝手元の HEAD）など、push を前提にしている確認が壊れていない → TC-01・M-01
- [ ] 既存のハーネステスト・CI がすべて pass する → TC-01・CI

## 3. 影響範囲
- Backend/Frontend/DB: なし
- Config/Infra: `.claude/skills/{plan-issue,plan-review,design-security-review,implement,review-gate,fix-loop,test-gate,retro,close,proceed}/SKILL.md`・`docs/runbooks/workflow.md`・`docs/runbooks/worktree.md`・`docs/runbooks/plan-writing-rules.md`・`scripts/claude/tests/test_i224_push_points.sh`（新規）・`docs/reviews/backlog/I226.md`

## 4. 変更点一覧（具体）

### 修正アプローチ
送る時点の決まりを `workflow.md` の 1 か所（正）に書き、各スキルの「commit/push」を「commit する（push しない）」に直して正を参照させる。push を残すのは 3 時点のスキルだけ。押し戻し（決まりを知らずに「commit/push」を書き足す事故）は決定論のテストで止める。

### 4-1. `docs/runbooks/workflow.md`（正）
新しい節「## GitHub への書き込みの時点（I224）」を「## 記録とつなぎ（決定論）」の前に足す:
- push するのは 3 時点だけ: ① plan-issue の下書き PR の作成（イシューファイルのコミット）② review-gate の CI 待ちの前（`code-review.sh` を流す直前。fix-loop の後のやり直しのたびを含む）③ close の最後の確認の前（記録を closed へ移すコミット。`STAGE_DONE: close NEXT: merge` もこのコミットに入れる）。ほかに `pr-base-sync.sh final` が base を取り込んだとき（BEHIND のときだけ）
- それ以外の段階の記録（STAGE_DONE・自律判断の記録・テスト結果・レビュー記録）は手元でコミットだけし、次の時点でまとめて送る。push し忘れても、review-gate の CI 待ちは `CI_WAIT: NOT_PUSHED` で止まる（決定論）
- イシュー本文の書き換え（`gh issue edit --body-file`）は grill-me の終わりの 1 回だけ。plan-issue で足す Draft PR の番号などは手元のファイルにだけ書く
- 目安: 1 本のイシューの push は 4 回以内（fix-loop の後のやり直し 1 回ごとに +1）。測り方: `git reflog show refs/remotes/origin/<ブランチ>` の `update by push` の行数
- 同時に複数のセッションで GitHub に書き込まない: 書き込む段階（plan-issue・review-gate・retro の起票・close）を、別の作業フォルダ（worktree）のセッションと重ねない。テスト用に起こすセッションは読み取りだけの鍵（I223）なので対象外。仕組みでは止めない（最後の守りは GitHub）
- 理由（1 行）: bot の停止（2026-10-30）の再発防止。量より「要る時点だけ送る」で減らす
- 同じファイルの 25 行目「implement: … → push」を「→ commit（push は review-gate の最初）」に、50 行目の「commit/push する」を「commit する（push は上の節の時点だけ）」に直す

### 4-2. スキル（「commit/push」→「commit」・push の 3 時点）
- `plan-issue`: 手順 2 の issue の `git push -u` は残す（①）。189・190 行の「commit/push」を「commit」に。66 行（既コミット経路の docs の commit・push）は ① なので残す。GitHub のイシュー本文は同期しない旨を 1 行足す
- `plan-review`: 14・28・35 行の「commit/push」を「commit」に（レビューのスクリプトは手元のファイルを読む）
- `design-security-review`: 141 行を「commit」に
- `implement`: 93 行「commit/push して PR を更新」→「commit する（push は review-gate の最初・workflow.md の時点 ②）」。96 行の「commit/push し直して」→「commit し直して」（3.5 は `origin/develop...HEAD` を手元で見る）。97 行を「commit」に
- `review-gate`: 「## 1.」の最初に「`git push` してから」を足す（②。fix-loop の後のやり直しも同じ）。27 行の NOT_PUSHED の扱いは残す。98 行の結線を「commit」に
- `fix-loop`: 64 行を「commit」に（次の review-gate が送る）
- `test-gate`: 63 行を「commit」に
- `retro`: 168・178 行を「commit」に（起票・既存イシューへのコメントはそのまま）
- `close`: 手順 3 の commit の前に `STAGE_DONE: close NEXT: merge` を足して、このコミットで送る（③）。手順 6 は「結線は手順 3 で済み。マージ依頼だけ」に。165 行の CI 失敗の戻し（open へ戻す）は「commit/push」→「commit」（次の review-gate が送る）。このとき最後の行が `STAGE_DONE: close NEXT: fix-loop` になるので、手順 3 の `close NEXT: merge` より後の行が勝つ（`flow-stage.sh` は最後の行を読む）
- `proceed`: 15 行の「commit/push」を「commit」に

### 4-3. `docs/runbooks/worktree.md`・`docs/runbooks/plan-writing-rules.md`
- `worktree.md:82`「コミット・push する」→「コミットする」
- `worktree.md:251`「こまめに commit・push する（失うのは push していない手元の変更だけにする）」→「こまめに commit する（push は workflow.md「GitHub への書き込みの時点」の時点だけ。手元のコミットはワークツリーを消さない限り残る）」
- `plan-writing-rules.md:230`「commit/push し」→「commit し」
- 同梱（一覧 I226 F2）: `plan-writing-rules.md:90` の「付け忘れは … G6 が止める。」と後ろの「付け忘れは … G6・G7 が止める。」の重複を、後ろの 1 つにまとめる

### 4-4. `scripts/claude/tests/test_i224_push_points.sh`（新規・決定論）
決まりを知らずに「commit/push」を書き足す事故（ふつうの書き方の事故で、CI でも画面でも気づけず、停止の再発につながる）を止める。
- P1: `.claude/skills/*/SKILL.md` のうち `plan-issue`・`review-gate`・`close` 以外に、`commit/push`・`commit・push`・`コミット・push`・`git push` が無い
- P2: `plan-issue`・`review-gate`・`close` の、行の先頭（空白の後）の `git push` のコマンドの行が、ちょうど決めた数ある（`plan-issue` 2〔通常・既コミット経路〕・`review-gate` 1・`close` 1）。増えたら落ちる（実装前の数: 2・0・1）
- P3: `.claude/skills/*/SKILL.md` で `gh issue edit` を書いてよいのは `grill-me` だけ
- P4: `docs/runbooks/workflow.md` に「## GitHub への書き込みの時点」の節がある（P1〜P3 の決まりの正）
- FG: 一時フォルダの写しに `commit/push` を足す・`review-gate` の `git push` を 2 つにする・`retro` に `gh issue edit` を足す・節の見出しを消す → それぞれ落ちる（テストの中で確かめる）
- 引数でルートを渡せる形にする（写しで FG を流すため）

### 4-5. `docs/reviews/backlog/I226.md`
- 同梱した F2 の行を消す

## 5. 実装手順（ステップ）
1. 4-4 のテストを先に書き、今の版で P1〜P4 が落ちることを確かめる → TC-02 参照
2. 4-1 の正の節 → 4-2 のスキル → 4-3 の手順書（ステップ 1 の後）→ TC-02・TC-03 参照
3. 4-5 → TC-01 参照
- ステップ 2 の後、この I224 の review-gate から close までは新しいスキルで動くので、I224 自身の push の回数を M-01 で数える

## 6. テスト計画
### 自動
- テストレベル: シェルの静的な検査（手順書の文字）と既存のハーネステスト。詳細は `docs/tests/open/I224_auto_test.md`
- 再発防止: P1〜P3 の FG
### 手動
- `docs/tests/open/I224_manual_test.md`（すべて Claude。I224 自身の push の回数・review-gate の CI 待ちが壊れていないこと）

## 7. ロールバック
- PR を revert する（手順書とテストだけ。データ・設定の変更なし）

## 8. Risk & 回避策
- **review-gate の前に push し忘れる**: `code-review.sh` が `CI_WAIT: NOT_PUSHED` で止まり、スキルの手順どおり push して 1 回だけやり直す（決定論の守りが既にある）
- **手元だけのコミットが失われる**: ワークツリーを消したときだけ。`wt-remove.sh` は未 push のコミットがあると止まる（`worktree.md:106`）
- **close の最後の確認で CI が落ちる**: 記録を open に戻し `STAGE_DONE: close NEXT: fix-loop`（最後の行が勝つ）。次の review-gate が送る
- **テストが説明の文の「push」まで落とす**: P1 は `commit/push`・`commit・push`・`コミット・push`・`git push` の 4 つの書き方だけを見る（「push していない変更」のような説明の文は見ない）。今のスキルの説明の文（implement 87 行・review-gate 27 行）で誤検知しないことを TC-02 の実走で確かめる
- **人に見える変化**: PR の中身が段階ごとでなく、review-gate と close の前にまとめて更新される。マージの判断に使う最終の状態は変わらない

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- push は 3 時点だけ・ほかは手元のコミットだけ・イシュー本文の同期は grill-me の終わりの 1 回・間隔を空ける仕組みは入れない・目安は 4 回以内（やり直し 1 回ごとに +1）・測り方は push の履歴の行数・同時書き込みは決まりだけ

Claude が決めた（技術的な選択と理由）:
- **決まりの正は `workflow.md` の 1 節、スキルは参照だけ**（仮定・技術的）: 写しを増やさない（I195 の方針）
- **`STAGE_DONE: close NEXT: merge` を close の手順 3 のコミットに入れる**（仮定・技術的）: 手順 6 の結線のためだけの push（4 回目）を無くす。失敗時は後の行が勝つ
- **決定論のテスト P1〜P3 を足す**（仮定・技術的）: `plan-writing-rules.md`「決定論テストの対象の選び方」の 2 問 — 普通の書き方（他のスキルの写し）で気づかずに壊しうる／壊れても CI・画面・すぐ後の作業で気づけない（push が増えるだけ）、被害は停止の再発で大きい → 作る。P4（節の有無）は意図的な変更でしか消えないが、P1〜P3 の決まりの正を指すため 1 行だけ置く
- **受け入れ条件 3 の「次のイシュー 1 本の実測」は、マージの後に次のイシューの retro で行う**（イシューに明記・grill-me）: この PR の中では I224 自身の review-gate〜close の回数（3 回以内の見込み）で代わりに示す。次のイシューの retro で測ることをメモリと I224 の close の報告に書く
- **PR へのコメント（レビューの記録）は変えない**（仮定・技術的〜範囲）: grill-me で決めた範囲（push・イシュー本文）の外で、PR でレビューを読む導線を変えるのは別の判断。1 本で 2〜5 回・push の直後に続くことは記録に残す
- **GitHub の上限の正確な数字は確かめない**（仮定・技術的）: 計画は数字に依存しない
- 要件・基本設計・UI/UX の仮定: なし

台帳の残りの一覧:
- 一覧 I226 F2（`docs/runbooks/plan-writing-rules.md`）: 同梱 — 触るファイルの 1 行の重複で、直しは 1 文
- 一覧 I209 F1（`plan-writing-rules.md`）: 残す — 読み取りの API のテストの決まりで、今回の変更と関係しない
- 一覧 I209 F2・F9（`grill-me`）・F3（`implement`）・F5（`fix-loop`）・F7（`issue-bootstrap`）: 残す — どれも書き込みの時点と関係しない文言の指摘（Low・再現なし）
- 一覧 I220 F1・F3（`issue-bootstrap`）・F2・F6・F7・F8（`workflow.md`）: 残す — 起票・同梱の手順と言い回しの指摘で、今回の節と関係しない
- 一覧 I219 F1（`worktree.md`）: 残す — primary の早送りの打ち切りの記述で、今回の 82・251 行と関係しない
- 一覧 I223 B1〜B4（`FILE=-`）: 残す — bot の停止が解けるまで手を付けられない

要件適合性: 受け入れ条件の範囲を超える仕様の追加なし。エッジケース: fix-loop のやり直し（②が増える）・close の最後の確認で BEHIND（`pr-base-sync.sh final` が送る）・CI の失敗（open に戻して commit だけ）・既コミット経路の plan-issue（docs のコミットで ①）

セキュリティ影響なし（コードを変えない。手順書とテストだけ。秘密情報・認証の扱いを変えない。push を減らすだけで、push の宛先・保護ブランチの扱いは変えない）。P3/P5/P8 影響なし。P6 影響なし。P9 影響なし。

設計品質: 正を 1 か所にし、スキルは参照する。テストは合格=exit 0、FG つき。

Danger Ops（有無/手順/ロールバック）:
- 無
