# 診断レビュー [I494]

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 対応方針 | G1 案 A は妥当です。見出しは `h2` で、`FormGroup` の直前にあります。このため `aria-labelledby` で見出しを名前に使えば、二重の見出しになりません。注意の `FormHelperText` は `FormGroup` の外にあります。そのため、`aria-describedby` には注意が出ているときだけ注意の id を足す、という書き方で成立します。固定 id は、設定画面にカードが 1 つだけなので問題ありません。 | `LearningSubjectsCard.tsx:120,137,161` |
| Info | 影響調査 | G2 の読み込み元は grep で確認しました。`LEARNING_SUBJECTS_ANCHOR` を使うのは `StartQuizCard.tsx` と `LearningSubjectsCard.tsx` だけで、テストからの import はありません。`frontend/src/constants/` はまだ存在しないため、新規作成になります。実装時は、カードが `useLocation().hash` との比較（72 行目）でも同じ定数を使い続けるようにしてください。 | `StartQuizCard.tsx:27,74` |
| Info | 影響調査 | `QuizSession.tsx:559` と `Register.tsx:502` の `FormGroup` に、同じ形（名前のないグループ）があります。範囲外なので retro で後続に回す、という扱いは妥当です。ただし、後続イシューの起票は忘れないでください。 | 診断メモの影響調査 |
| Info | 根本原因 | G1・G2 ともに症状の言い換えではなく、原因として成立しています。コードでも裏が取れました。 | — |

## 影響調査の網羅性評価
- G1 の同型箇所（`FormGroup` の全件）と、G2 の定数の使用箇所（コードとテスト）は調査済みです。私の grep とも一致しました。
- 範囲外の同型箇所は、扱いが明示されています。
- G2 の `/settings#...` を文字で書いている箇所は、E2E とテストの側で確認済みです。定数を移しても結果は変わりません。
- 重大な漏れはありません。

VERDICT: OK
