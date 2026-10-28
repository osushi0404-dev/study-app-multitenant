---
name: test-gate
description: "/plan-issue・/proceed の流れの中でだけ呼ぶ段階のスキル（自分から呼ばない）。レビュー済みの HEAD かを gate-check.sh で確かめ、計画書が指定した重いテスト・Claude 担当の手動テストを行い、人の手動テストがあればそこで止まる。pytest・Jest・E2E の手元での流し直しはしない（CI が正）。最後に STAGE_DONE を書く。"
argument-hint: "I###"
user-invocable: false
---

# test-gate（テスト段階）

止めてユーザーに聞くのは `docs/runbooks/workflow.md`「止めて聞く条件」に当たるとき（と、下の 4. の人の手動テスト）だけ。それ以外で決めたことは `docs/reviews/open/$ARGUMENTS_review.md` の「## 自律判断の記録」に `- [test-gate] 決めたこと — 理由` で書く。

この段階が書いてよいのは `docs/tests/`・`docs/reviews/`・`docs/issues/`・`docs/plans/` だけ。コードや手順書を直す必要が出たら、直さずに `NEXT: fix-loop` で終わる（直した後はレビューを通り直す）。

## 1. レビュー済みの HEAD か（必須・決定論）

```bash
bash scripts/claude/gate-check.sh "$ARGUMENTS"
```

- exit 0: 2. へ
- exit 1: 出力の `GATE_CHECK: FAIL REASON=<理由>` で分ける
  - `REASON=dirty`（記録の場所の外にコミットしていない変更・未追跡のファイルがある）: review-gate に戻しても直らない。この段階は記録の場所の外をコミットしない。この流れで作った一時ファイルなら消してやり直す。実装の一部（コミットし忘れ）なら `STAGE_DONE: test-gate NEXT: fix-loop` を書いて終わる（fix-loop がコミットし、review-gate に戻す）。どちらとも決められないときは止める（止める条件 3）
  - それ以外（`unreviewed`・`verdict`・`missing`）: `STAGE_DONE: test-gate NEXT: review-gate` を書いて終わる。ただし、記録の最後から 2 番目の `STAGE_DONE:` 行が `STAGE_DONE: test-gate NEXT: review-gate`（＝前回もこの段階が gate-check で戻し、その後の review-gate を通っても、また gate-check で落ちた。戻すのが 2 回続く）のときは、戻さずに止める（止める条件 3。review-gate ⇄ test-gate を繰り返さない）
  - `REASON=base`（比べる相手 origin/develop が無い）: `git fetch origin develop` をしてからもう一度実行する。それでも落ちれば止める（止める条件 3）

## 2. 自動テスト（計画駆動）

実行する自動テストは **計画書のテスト計画（`docs/tests/open/$ARGUMENTS_auto_test.md`）が正**。

- pytest・Jest・E2E は CI（`.github/workflows/ci.yml`・`e2e.yml`）が PR ごとに流しており、review-gate の `code-review.sh` が CI の完了と成功を確かめている。**手元では流し直さない**
- auto_test.md の「## 決定論ゲート（自動実走）」のうち、`code-review.sh` が「test-gate に委譲（heavy）」と記録したもの（docker・npm・pytest など）と、テストケースの表で「/test で実行する」と書かれたものは、ここで 1 つずつ実行する
  - 10 分を超えうるもの（`bash scripts/claude/tests/run-all.sh`・docker の E2E など）は、Bash ツールの `run_in_background: true` で実行し、完了の通知で結果を受け取る（前面の実行の上限 10 分で打ち切られないように）。終了コードが取れないまま終わったときは、失敗として扱う
- 1 件でも失敗したら、失敗したテスト名と内容（期待値 / 実際値 / ログの抜粋）を記録して `STAGE_DONE: test-gate NEXT: fix-loop` を書いて終わる

## 3. 記録

`docs/tests/open/$ARGUMENTS_auto_test.md` の「実行記録」に、実行したコマンド・終了コード・日時を書く。`docs/reviews/open/$ARGUMENTS_review.md` の「## テスト結果」も更新する。

## 4. 手動テスト

テスト計画書（`docs/tests/open/$ARGUMENTS_manual_test.md`）の「実施者」欄を必ず確認する。

- **実施者: Claude** の項目 → 自分で Bash/Read ツールを使って実行し、結果を表に記録する（ユーザーに依頼しない）
  - 画面の表示・遷移・入力の結果・コンソールは、`docs/runbooks/frontend-verify.md` の手順（§9 の安全上の注意を含む）で Playwright MCP を使って確かめ、同じ手順書の「画面確認」の書き方でテスト記録に書く（コミットはこのレビュー済みの HEAD）
  - 承認画面が出るか／承認なしで通るかは `bash scripts/claude/check-permission-prompt.sh` で確かめる（使い方と終了コードはスクリプトの冒頭。2 ならもう 1 回流し、それでも 2 なら NG）。ユーザーに「画面が出たか」を聞かない。承認なしで通る操作は実際に実行されるので、危ない操作は、同じ許可ルール・見張りに当たり、実行されても困らない代わりの操作で確かめる。同じ許可ルールに当たる操作は 1 回の確認でまとめる
  - 対話画面（TUI）にだけ出る表示（`/` の候補・ステータス行・ダイアログなど）は `bash scripts/claude/tui-capture.sh '<入力>'` で確かめる（使い方はスクリプトの冒頭。表示を見るだけなら `{Enter}` を送らない）
- **実施者: Human** の項目だけ → Claude の分を全部終えてから、まとめてユーザーに提示する

Claude の分で NG があれば、記録して `STAGE_DONE: test-gate NEXT: fix-loop` を書いて終わる。

Claude の分を終えたら、次の 2 つの判定を実行する（I187。どちらも記録の判定）:
```bash
bash scripts/claude/check-frontend-evidence.sh $ARGUMENTS
```
```bash
bash scripts/claude/check-manual-test-executor.sh $ARGUMENTS
```
- どちらも exit 0: 5. へ
- 0 以外: コードの不具合ではないので fix-loop に回さない。出力された不足を、自分で直してから判定をやり直す（画面確認が足りなければ上の手順で確かめて行と画像を足す。Claude で確かめられる項目が Human になっていれば Claude の行に直して自分で行う。本当に Claude で確かめられない Human の行だけ、備考に `試した手段: …` を書く。書き方は `docs/runbooks/plan-writing-rules.md`「実施者の区別」）。書くのは記録の場所と gitignore 済みの `.evidence/` だけ。直せないとき（MCP が使えないなど）は止める条件 3 に当たるかを判定する

## 5. 結線（必須）

commit/push してから、`docs/reviews/open/$ARGUMENTS_review.md` の末尾に 1 行足して commit/push する:
- Human の項目がある: `STAGE_DONE: test-gate NEXT: human-test` を書き、次の形で提示して止まる
  ```
  ## 手動テスト確認項目（Human 実施分）
  | # | 確認内容 | 操作手順 | 期待結果 | 結果(OK/NG) |
  |---|---------|---------|---------|------------|
  ```
  あわせて、ここまでに Claude が自分で決めたこと（「## 自律判断の記録」）を平易な言葉でまとめて伝え、「結果（OK、または NG と内容）を返信してください」と案内する
- Human の項目が無い: `STAGE_DONE: test-gate NEXT: retro`
