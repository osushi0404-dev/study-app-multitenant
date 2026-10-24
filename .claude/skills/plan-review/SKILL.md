---
name: plan-review
description: "/plan-issue・/proceed の流れの中でだけ呼ぶ段階のスキル（自分から呼ばない）。計画書・テスト文書を自作の計画レビュー役（plan-reviewer）でレビューし、Blocker は自分で直して再レビューする。計画の方式・範囲・受け入れ条件を変えたときも呼び直す。最後に STAGE_DONE を書く。"
argument-hint: "I###"
user-invocable: false
---

# plan-review（計画レビュー段階）

止めてユーザーに聞くのは `docs/runbooks/workflow.md`「止めて聞く条件」に当たるときだけ。それ以外で決めたことは `docs/reviews/open/$ARGUMENTS_review.md` の「## 自律判断の記録」に `- [plan-review] 決めたこと — 理由` で書く。

## 1. レビュー

計画書・テスト文書・レビュー文書を commit/push してから実行する:

```bash
bash scripts/claude/plan-issue-review.sh "$ARGUMENTS"
```

次のどれか 1 つでも当たるときは、スクリプトが判定の前に失敗したとみなす: 終了コードが 0 以外で、かつ Blocker の案内（`⛔ Blocker が残っています`）が出ていない／レビュー記録 `docs/reviews/$ARGUMENTS_plan_review_<ts>.md` が作られていない／レビュー記録のどの行にも `VERDICT:` で始まる行が無い。原因を直せるなら直して実行し直し、直せないときは止める（止める条件 3）。

## 2. 終わり方（`PLAN_VERDICT:` の行で決める）

1. `PLAN_VERDICT: OK` → 3. で `NEXT: implement`
2. `PLAN_VERDICT: HIGHRISK` → 3. で `NEXT: design-security-review`
3. `PLAN_VERDICT: BLOCKER` → 指摘を計画書・テスト文書に Edit で直し、commit/push して 1. を実行し直し、その結果で 1〜3 を判定し直す
   - 同じゲートで 2 回続けて BLOCKER なら、止める条件 3 に当たるかを判定する。範囲を狭める・別イシューに切り出すなど安全側の選択肢が取れれば、それを選んで計画書を直し、記録に書いてもう一度 1. を実行する。取れなければ止める
   - 直すのに要件・基本設計・UI/UX の判断が要る指摘は、選択肢をつけてユーザーに聞いて止める（止める条件 1）
- Warning・Info は、直せるものは直す。直した内容が方式・範囲・受け入れ条件を変えないなら、計画変更記録に 1 行書いて再レビューはしない

## 3. 結線（必須）

スクリプトが計画書に追記したレビュー記録へのリンクを含めて commit/push し、`docs/reviews/open/$ARGUMENTS_review.md` の末尾に 1 行足して commit/push する:
- `STAGE_DONE: plan-review NEXT: implement`（OK）
- `STAGE_DONE: plan-review NEXT: design-security-review`（HIGHRISK）
- 止める条件に当たって止まるときは `STAGE_DONE:` を書かない
