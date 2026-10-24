---
name: proceed
description: イシューの流れを、記録の最後の STAGE_DONE から続ける。使うのは次の 3 つの場面だけ: ユーザーが /proceed I### を打ったとき／/plan-issue から呼ばれたとき／ユーザーが人の手動テストの結果（OK、または NG と内容）を返信したとき。それ以外で自分から呼ばない。
argument-hint: "I###"
---

# /proceed

イシュー `$ARGUMENTS` の流れを、`docs/reviews/open/$ARGUMENTS_review.md`（close の後は `docs/reviews/closed/`）の最後の `STAGE_DONE:` 行から続ける。段階の順番は記録だけで決める（`scripts/claude/flow-stage.sh` が決定論で返す）。止めてユーザーに聞くのは `docs/runbooks/workflow.md`「止めて聞く条件」に当たるときだけ。

## 0. 人の手動テストの結果を受け取ったとき（返信から呼ばれた場合だけ）

1. 最後の `STAGE_DONE:` が `NEXT: human-test` であることを `flow-stage.sh` で確かめる（違えば、返信を結果として扱わず、1. へ進む）
2. 返信の結果を `docs/tests/open/$ARGUMENTS_manual_test.md` の Human の行の「実結果」に書く
3. 全部 OK なら `STAGE_DONE: human-test NEXT: retro`、NG が 1 つでもあれば NG の内容を記録して `STAGE_DONE: human-test NEXT: fix-loop` を `docs/reviews/open/$ARGUMENTS_review.md` の末尾に足して commit/push する
   （NG の後は fix-loop → review-gate → test-gate と進み、人の手動テストをもう一度依頼して止まる）

## 1. 次の段階を決める

```bash
bash scripts/claude/flow-stage.sh "$ARGUMENTS"
```

- exit 0: 出力の `NEXT_STAGE: <名前>` を見て 2. へ
- exit 2: 記録が無い・`STAGE_DONE:` が無い（このイシューは新しい流れで始めていない、または古い流れで進めている）・NEXT が読めない。理由をユーザーに伝えて止まる（古い流れのイシューを新しい流れで誤って進めない）

## 2. 段階を呼ぶ（繰り返す）

`NEXT_STAGE` に応じて、次を行い、終わったら 1. に戻る:

| NEXT_STAGE | すること |
|---|---|
| `plan-review`・`design-security-review`・`implement`・`review-gate`・`fix-loop`・`test-gate`・`retro`・`close` | Skill ツールで同じ名前のスキルを呼ぶ（引数 `$ARGUMENTS`） |
| `human-test` | `docs/tests/open/$ARGUMENTS_manual_test.md` の Human の項目と、ここまでの「## 自律判断の記録」の要点を平易に提示し、「結果（OK、または NG と内容）を返信してください」と伝えて止まる |
| `merge` | close 段階がマージを依頼済み。「GitHub で Approve & Merge をお願いします」と伝えて止まる |

段階のスキルが `STAGE_DONE:` を書かずに終わった（止める条件に当たって止まった）ときは、1. に戻らずにそのまま止まる（同じ段階を繰り返し呼ばない）。見分け方: 段階を呼ぶ前と後で `flow-stage.sh` の出力の `STAGE_COUNT:`（`STAGE_DONE:` 行の数）が増えていなければ、書かれていない（`LAST_LINE:` の行番号は、自律判断の記録に行を足すだけでずれるので見分けに使わない）。
